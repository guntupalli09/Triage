"""
Smoke tests for the TriageBench framework itself — not the corpus, not
TriageCounsel's rule quality. These validate that the benchmark
infrastructure behaves the way its design decisions promise: deterministic
sampling, resumable/crash-safe storage, correct regression diffing, and
that the ten-stage pipeline actually runs end to end against the engine.

Run with: pytest triagebench/tests/ -q
"""
from __future__ import annotations

import json

import pytest

from triagebench import config, corpus, html_extract, pipeline, regression, storage


SAMPLE_HTML = b"""<DOCUMENT>
<TYPE>EX-10.1
<TEXT>
<html><body>
<p>This Consulting Agreement (the "Agreement") is entered into by and between
Acme Corp ("Company") and Jane Roe ("Consultant").</p>
<p>1. Term. This Agreement shall commence on the Effective Date and continue
for twelve (12) months.</p>
<p>2. Indemnification. Consultant shall indemnify, defend, and hold harmless
the Company from and against any and all claims, in an uncapped amount,
regardless of the nature of the claim.</p>
<p>3. Limitation of Liability. IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR
ANY INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES.</p>
</body></html>
</TEXT>
</DOCUMENT>"""


class TestHtmlExtract:
    def test_primary_strips_sgml_and_tags(self):
        text = html_extract.extract_primary(SAMPLE_HTML)
        assert "Consulting Agreement" in text
        assert "<p>" not in text
        assert "<TYPE>" not in text

    def test_reference_extractor_agrees_with_primary_on_clean_html(self):
        primary = html_extract.extract_primary(SAMPLE_HTML)
        reference = html_extract.extract_reference(SAMPLE_HTML)
        check = html_extract.cross_check(primary, reference)
        assert check.agree, f"delta={check.word_count_delta_pct}%"


class TestCorpusSampling:
    def test_select_is_deterministic(self):
        refs = [
            corpus.ContractRef(
                contract_id=f"cat:{i:03d}", category="Employment", category_dir="Employement",
                company_name="X", form_type="8-K", date_filed="2026-01-01", cik="1", accession="a",
                exhibit=None, archive_name=f"{i}.htm", doc_path=config.REPO_ROOT, row_index=i,
            )
            for i in range(50)
        ]
        a = corpus.select(refs, limit=10, seed=42)
        b = corpus.select(refs, limit=10, seed=42)
        assert [r.contract_id for r in a] == [r.contract_id for r in b]

    def test_select_different_seed_can_differ(self):
        refs = [
            corpus.ContractRef(
                contract_id=f"cat:{i:03d}", category="Employment", category_dir="Employement",
                company_name="X", form_type="8-K", date_filed="2026-01-01", cik="1", accession="a",
                exhibit=None, archive_name=f"{i}.htm", doc_path=config.REPO_ROOT, row_index=i,
            )
            for i in range(50)
        ]
        a = corpus.select(refs, limit=10, seed=1)
        b = corpus.select(refs, limit=10, seed=2)
        assert [r.contract_id for r in a] != [r.contract_id for r in b]


class TestPipeline:
    def test_run_contract_end_to_end(self, tmp_path):
        doc = tmp_path / "sample.htm"
        doc.write_bytes(SAMPLE_HTML)
        ref = corpus.ContractRef(
            contract_id="test:sample", category="Services", category_dir="Services",
            company_name="Acme", form_type="8-K", date_filed="2026-01-01", cik="1", accession="a",
            exhibit=None, archive_name="sample.htm", doc_path=doc, row_index=0,
        )
        result = pipeline.run_contract(ref).as_dict()
        assert result["overall_status"] in ("pass", "fail")  # never "error" on a well-formed doc
        for stage in ("upload", "analysis", "rule_engine", "evidence", "review",
                      "verify", "negotiation_package", "docx_export", "replay", "audit"):
            assert result["stages"][stage]["status"] == "ok", (stage, result["stages"][stage])
        assert result["metrics"]["findings_count"] >= 1  # the sample text has an uncapped-indemnity clause
        assert result["stages"]["replay"]["deterministic"] is True

    def test_run_contract_never_raises_on_garbage_input(self, tmp_path):
        doc = tmp_path / "garbage.htm"
        doc.write_bytes(b"\x00\x01\x02not html at all")
        ref = corpus.ContractRef(
            contract_id="test:garbage", category="Services", category_dir="Services",
            company_name="X", form_type="8-K", date_filed="2026-01-01", cik="1", accession="a",
            exhibit=None, archive_name="garbage.htm", doc_path=doc, row_index=0,
        )
        result = pipeline.run_contract(ref).as_dict()
        # Garbage bytes still decode to *some* text under errors="replace",
        # so this may pass upload; the guarantee under test is just that it
        # never raises and always produces a well-formed result record.
        assert result["overall_status"] in ("pass", "fail", "error")
        assert "contract_id" in result

    def test_missing_file_is_a_recorded_failure_not_a_crash(self, tmp_path):
        ref = corpus.ContractRef(
            contract_id="test:missing", category="Services", category_dir="Services",
            company_name="X", form_type="8-K", date_filed="2026-01-01", cik="1", accession="a",
            exhibit=None, archive_name="missing.htm", doc_path=tmp_path / "missing.htm", row_index=0,
        )
        result = pipeline.run_contract(ref).as_dict()
        assert result["overall_status"] == "error"
        assert result["stages"]["upload"]["status"] == "error"
        assert result["stages"]["analysis"]["status"] == "skipped"


class TestStorageResumability:
    def test_append_and_read_completed_ids(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "RUNS_ROOT", tmp_path)
        run_id = "test-run"
        storage.ensure_run_dir(run_id)
        storage.append_result(run_id, {"contract_id": "a", "overall_status": "pass"})
        storage.append_result(run_id, {"contract_id": "b", "overall_status": "pass"})
        assert storage.read_completed_ids(run_id) == {"a", "b"}

    def test_torn_last_line_is_skipped_not_fatal(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "RUNS_ROOT", tmp_path)
        run_id = "test-run"
        storage.ensure_run_dir(run_id)
        storage.append_result(run_id, {"contract_id": "a", "overall_status": "pass"})
        # Simulate a crash mid-write: an incomplete JSON line appended.
        with storage.results_jsonl_path(run_id).open("a") as f:
            f.write('{"contract_id": "b", "overall_st')
        assert storage.read_completed_ids(run_id) == {"a"}


class TestRegression:
    def _rec(self, cid, rule_ids, coverage=50.0, docx_status="ok", verify_ok=True, replay_ok=True, words=100):
        return {
            "contract_id": cid,
            "rule_ids_fired": rule_ids,
            "metrics": {"redline_coverage_pct": coverage, "words": words},
            "stages": {
                "docx_export": {"status": docx_status, "counts_consistent": True},
                "negotiation_package": {"status": "ok"},
                "upload": {"status": "ok"},
                "verify": {"verified": verify_ok},
                "replay": {"deterministic": replay_ok},
            },
        }

    def test_detects_missing_finding_rule(self):
        baseline = [self._rec("c1", ["H_LOL_01", "M_INSURANCE_01"])]
        current = [self._rec("c1", ["M_INSURANCE_01"])]
        cmp_ = regression.compare(current, {"run_id": "cur"}, baseline, {"run_id": "base"})
        kinds = {r["kind"] for r in cmp_["rows"]}
        assert "missing_finding_rule" in kinds
        assert cmp_["has_critical_regressions"] is True

    def test_clean_run_has_no_critical_regressions(self):
        baseline = [self._rec("c1", ["M_INSURANCE_01"])]
        current = [self._rec("c1", ["M_INSURANCE_01"])]
        cmp_ = regression.compare(current, {"run_id": "cur"}, baseline, {"run_id": "base"})
        assert cmp_["has_critical_regressions"] is False

    def test_detects_verify_newly_failing(self):
        baseline = [self._rec("c1", ["M_INSURANCE_01"], verify_ok=True)]
        current = [self._rec("c1", ["M_INSURANCE_01"], verify_ok=False)]
        cmp_ = regression.compare(current, {"run_id": "cur"}, baseline, {"run_id": "base"})
        assert cmp_["verify_newly_failing"] == 1
        assert cmp_["has_critical_regressions"] is True

    def test_detects_coverage_regression(self):
        baseline = [self._rec("c1", ["M_INSURANCE_01"], coverage=50.0)]
        current = [self._rec("c1", ["M_INSURANCE_01"], coverage=10.0)]
        cmp_ = regression.compare(current, {"run_id": "cur"}, baseline, {"run_id": "base"})
        assert cmp_["coverage_regressions"] == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
