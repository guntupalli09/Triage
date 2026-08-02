"""
The ten-stage deterministic pipeline TriageBench runs against every
contract: Upload -> Analysis -> Rule Engine -> Evidence -> Review -> Verify
-> Negotiation Package -> DOCX Export -> Replay -> Audit.

Design decisions worth stating explicitly (self-documentation is a stated
requirement of this framework, not an afterthought):

- Analysis vs. Rule Engine: TriageCounsel's own code (main.py's
  run_analysis) computes both in a single RuleEngine.analyze() call — there
  is no separate "analysis" pass ahead of rule matching in production. This
  pipeline honors that reality rather than inventing a fake seam: "Analysis"
  times the analyze() call itself (chunking, rule matching, clause-quality
  and structure analysis, metadata extraction — everything analyze() does);
  "Rule Engine" is the bookkeeping pass over analyze()'s findings (severity
  counts, rules-triggered vs. rules-executed, per-rule aggregation) that a
  benchmark specifically needs and production doesn't compute as a distinct
  step. If TriageCounsel ever splits these into genuinely separate calls,
  update this mapping — don't leave the comment lying.

- Review is automated, by a fixed and documented policy (see
  _auto_decide), since there is no human reviewer in a CI benchmark. The
  policy is deliberately the most defensible default (accept every
  authored redline, flag everything else) so DOCX/negotiation-package
  generation gets exercised against production code paths on every run.

- Verify re-runs the full engine once more ("replay run") and checks EVERY
  finding reproduces exactly, by rule_id + start_index + exact_snippet —
  stronger than the production /review/verify endpoint (which checks one
  finding at a time, interactively) but built on the exact same match logic.

- Replay reuses that same second run to check the entire result set
  (finding sequence, rule_counts, overall_risk) is byte-for-byte identical
  to the first run. Verify asks "does this one finding reproduce?"; Replay
  asks "is the whole document's output deterministic end to end?" — a
  mismatch here means the engine itself is non-deterministic, independent
  of any single finding.
"""
from __future__ import annotations

import io
import time
import traceback
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import engine_bridge as eb
from . import html_extract
from .corpus import ContractRef

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass
class StageResult:
    name: str
    status: str = "pending"  # ok | fail | error | skipped
    ms: float = 0.0
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "status": self.status, "ms": round(self.ms, 3), "error": self.error, **self.data}


class _Timer:
    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = (time.perf_counter() - self._t0) * 1000.0


@dataclass
class ContractResult:
    contract_id: str
    category: str
    company_name: str
    form_type: str
    date_filed: str
    filename: str
    archive_name: str
    source_format: str
    stages: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    rule_ids_fired: List[str] = field(default_factory=list)
    overall_status: str = "pass"
    failures: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "category": self.category,
            "company_name": self.company_name,
            "form_type": self.form_type,
            "date_filed": self.date_filed,
            "filename": self.filename,
            "archive_name": self.archive_name,
            "source_format": self.source_format,
            "stages": self.stages,
            "metrics": self.metrics,
            "rule_ids_fired": self.rule_ids_fired,
            "overall_status": self.overall_status,
            "failures": self.failures,
        }


def _run_stage(name: str, fn, *args, required: bool = True, **kwargs) -> StageResult:
    result = StageResult(name=name)
    try:
        with _Timer() as t:
            data = fn(*args, **kwargs) or {}
        result.status = "ok"
        result.ms = t.ms
        result.data = data
    except Exception as exc:  # noqa: BLE001 — a contract failing must never stop the run
        result.status = "error"
        result.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=6)}"
    return result


# ---------------------------------------------------------------------------
# Stage implementations. Each returns a plain dict merged into StageResult.data.
# ---------------------------------------------------------------------------

def stage_upload(doc_path: Path) -> Dict[str, Any]:
    raw = doc_path.read_bytes()
    ext = doc_path.suffix.lower()
    if ext in (".htm", ".html"):
        text = html_extract.extract_primary(raw)
        fmt = "html"
    elif ext == ".txt":
        text = raw.decode("utf-8", errors="ignore")
        fmt = "txt"
    else:
        raise ValueError(f"Unsupported corpus file type: {ext}")
    if not text.strip():
        raise ValueError("Upload produced empty text")
    words = len(text.split())
    return {
        "contract_text": text,
        "raw_bytes": raw,
        "source_format": fmt,
        "characters": len(text),
        "words": words,
        "pages": max(1, round(words / 500)),
    }


def stage_analysis(contract_text: str) -> Dict[str, Any]:
    analysis = eb.get_engine().analyze(contract_text)
    return {"analysis": analysis}


def stage_rule_engine(analysis: Dict[str, Any]) -> Dict[str, Any]:
    findings = analysis["findings"]
    counts = analysis.get("rule_counts", {})
    rules_triggered = sorted({f.rule_id for f in findings})
    return {
        "rules_executed": eb.rules_total(),
        "rules_triggered": len(rules_triggered),
        "rules_never_fired_here": eb.rules_total() - len(rules_triggered),
        "rule_ids_fired": rules_triggered,
        "findings_count": len(findings),
        "critical": counts.get("critical", 0),
        "high": counts.get("high", 0),
        "medium": counts.get("medium", 0),
        "low": counts.get("low", 0),
        "overall_risk": analysis.get("overall_risk"),
        "signature_readiness": analysis.get("signature_readiness"),
        "engine_version": analysis.get("version"),
    }


def stage_evidence(analysis: Dict[str, Any]) -> Dict[str, Any]:
    findings = analysis["findings"]
    metadata = analysis.get("metadata", {})
    contradiction_log = analysis.get("contradiction_log", {})
    findings_dict = [
        {
            "rule_id": f.rule_id, "rule_name": f.rule_name, "title": f.title,
            "severity": f.severity.value, "rationale": f.rationale,
            "matched_excerpt": f.matched_excerpt, "position": f.position,
            "context": f.context, "clause_number": f.clause_number,
            "matched_keywords": f.matched_keywords, "aliases": f.aliases,
            "start_index": f.start_index, "end_index": f.end_index,
            "exact_snippet": f.exact_snippet, "evidence": f.evidence,
            "party_direction": f.party_direction,
            "finding_type": f.finding_type,
            "finding_type_label": eb.FINDING_TYPE_LABELS.get(f.finding_type, f.finding_type),
            "confidence_breakdown": eb.build_confidence_breakdown(f, contradiction_log).as_dict(),
            "redline": eb.render_redline(f, metadata),
        }
        for f in findings
    ]
    with_redline = sum(1 for f in findings_dict if f.get("redline"))
    overlap_candidates = _count_overlaps(findings_dict)
    coverage = (with_redline / len(findings_dict) * 100.0) if findings_dict else 100.0
    return {
        "findings_dict": findings_dict,
        "redline_count": with_redline,
        "manual_drafting_count": len(findings_dict) - with_redline,
        "redline_coverage_pct": round(coverage, 2),
        "overlapping_findings_candidates": overlap_candidates,
    }


def _count_overlaps(findings_dict: List[Dict[str, Any]]) -> int:
    """Findings whose [start_index, end_index) span overlaps another
    finding's span — informational (the docx export stage independently
    measures how many actually collide during redline placement)."""
    spans = sorted(
        ((f["start_index"], f["end_index"]) for f in findings_dict if f.get("start_index") is not None),
    )
    overlaps = 0
    prev_end = -1
    for start, end in spans:
        if start < prev_end:
            overlaps += 1
        prev_end = max(prev_end, end)
    return overlaps


def _auto_decide(findings_dict: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """CI review policy (documented, fixed, applied identically every run —
    see module docstring): accept every authored redline; flag everything
    else for manual drafting. This is the most production-representative
    automatic choice available (it exercises the real accept path end to
    end) without pretending a human reviewed the contract."""
    decisions: Dict[str, Dict[str, Any]] = {}
    for idx, f in enumerate(findings_dict):
        key = eb.finding_key(idx, f["rule_id"])
        action = "accepted" if f.get("redline") else "flagged"
        eb.validate_decision(key, action, bool(f.get("redline")), reason=None, edited_text=None)
        decisions[key] = {"action": action, "rule_id": f["rule_id"], "decided_at": "benchmark"}
    return decisions


def stage_review(findings_dict: List[Dict[str, Any]]) -> Dict[str, Any]:
    decisions = _auto_decide(findings_dict)
    progress = eb.compute_progress(findings_dict, decisions)
    return {
        "decisions": decisions,
        "progress": progress.as_dict(),
        "is_complete": progress.is_complete or len(findings_dict) == 0,
    }


def stage_verify(contract_text: str, findings_dict: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Re-runs the full engine (the "replay run") and checks EVERY finding
    reproduces by rule_id + start_index + exact_snippet — the same match
    rule production's /review/verify endpoint uses, applied exhaustively
    instead of to one finding at a time."""
    replay = eb.get_engine().analyze(contract_text)
    replay_findings = replay["findings"]
    index = {}
    for f in replay_findings:
        index.setdefault((f.rule_id, f.start_index), []).append(f)

    mismatched: List[str] = []
    for f in findings_dict:
        candidates = index.get((f["rule_id"], f["start_index"]), [])
        match = next((c for c in candidates if c.exact_snippet == f["exact_snippet"]), None)
        if match is None:
            mismatched.append(f["rule_id"])

    return {
        "_replay_analysis": replay,
        "verified_count": len(findings_dict) - len(mismatched),
        "total": len(findings_dict),
        "mismatched_count": len(mismatched),
        "mismatched_rule_ids": mismatched,
        "verified": len(mismatched) == 0,
    }


def stage_negotiation_package(
    filename: str, contract_text: str, findings_dict: List[Dict[str, Any]], decisions: Dict[str, Any]
) -> Dict[str, Any]:
    docx_bytes, skipped = eb.build_redlined_docx(
        filename, contract_text, findings_dict, decisions, author="TriageBench CI Reviewer"
    )
    memo_text = eb.build_cover_memo_text(filename, findings_dict, decisions)
    audit_text = eb.build_audit_trail_text(filename, eb.engine_version(), findings_dict, decisions)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"Redlined_{filename}.docx", docx_bytes)
        zf.writestr("Cover_Memo.txt", memo_text)
        zf.writestr("Audit_Trail.txt", audit_text)
    package_bytes = buf.getvalue()

    return {
        "_docx_bytes": docx_bytes,
        "_memo_text": memo_text,
        "_audit_text": audit_text,
        "package_size_bytes": len(package_bytes),
        "docx_size_bytes": len(docx_bytes),
        "skipped_redlines": skipped,
        "skipped_redline_count": len(skipped),
    }


def stage_docx_export(docx_bytes: bytes, decisions: Dict[str, Any], skipped_redlines: List[str]) -> Dict[str, Any]:
    """Validates DOCX integrity independently of python-docx: raw zip
    structure, well-formed XML on every OOXML part touched by
    docx_export.py's manual zip surgery, and that the number of tracked
    insertions/deletions/comments in the XML matches what the decisions map
    says should be there — catching a docx_export.py bug that silently drops
    or duplicates a redline, not just one that corrupts the zip outright.

    expected_redline_count excludes `skipped_redlines`: build_redlined_docx
    deliberately skips an accepted/edited redline whose span overlaps an
    earlier one already placed in the document (see its own docstring/
    module comment on overlap handling) — that is documented, correct
    behavior, not a defect, so a skipped redline must not be counted as
    "should have appeared but didn't"."""
    if not zipfile.is_zipfile(io.BytesIO(docx_bytes)):
        raise ValueError("not a valid zip/docx container")

    zf = zipfile.ZipFile(io.BytesIO(docx_bytes))
    names = set(zf.namelist())
    required = {"[Content_Types].xml", "word/document.xml", "word/_rels/document.xml.rels"}
    missing = required - names
    if missing:
        raise ValueError(f"docx missing required parts: {sorted(missing)}")

    xml_parts_checked = []
    for part in ("word/document.xml", "word/settings.xml", "word/styles.xml", "[Content_Types].xml"):
        if part in names:
            ET.fromstring(zf.read(part))  # raises ParseError on malformed XML
            xml_parts_checked.append(part)

    has_comments = "word/comments.xml" in names
    if has_comments:
        ET.fromstring(zf.read("word/comments.xml"))
        xml_parts_checked.append("word/comments.xml")

    doc_root = ET.fromstring(zf.read("word/document.xml"))
    ins_count = len(doc_root.findall(f".//{W_NS}ins"))
    del_count = len(doc_root.findall(f".//{W_NS}del"))
    comment_ref_count = len(doc_root.findall(f".//{W_NS}commentReference"))
    comments_defined = len(ET.fromstring(zf.read("word/comments.xml")).findall(f"{W_NS}comment")) if has_comments else 0

    expected_redlines = sum(1 for d in decisions.values() if d.get("action") in ("accepted", "edited"))
    expected_redlines -= len(skipped_redlines)

    # python-docx round-trip: production's own reader must be able to open
    # what production's own writer produced.
    from docx import Document as _Document
    _Document(io.BytesIO(docx_bytes))

    return {
        "zip_valid": True,
        "xml_parts_valid": xml_parts_checked,
        "ins_count": ins_count,
        "del_count": del_count,
        "comment_reference_count": comment_ref_count,
        "comments_defined_count": comments_defined,
        "expected_redline_count": expected_redlines,
        "counts_consistent": ins_count == expected_redlines and comment_ref_count == comments_defined,
        "python_docx_roundtrip_ok": True,
    }


def stage_replay(primary_analysis: Dict[str, Any], replay_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic-output check: the entire result of two independent
    analyze() calls on the same text must match exactly. A mismatch here is
    an engine non-determinism bug, not a benchmark false positive — regex
    matching over the same immutable string cannot legitimately differ."""
    def signature(analysis):
        return sorted(
            (f.rule_id, f.start_index, f.end_index, f.exact_snippet)
            for f in analysis["findings"]
        )

    sig_a, sig_b = signature(primary_analysis), signature(replay_analysis)
    diff = set(sig_a) ^ set(sig_b)
    deterministic = (
        sig_a == sig_b
        and primary_analysis.get("overall_risk") == replay_analysis.get("overall_risk")
        and primary_analysis.get("rule_counts") == replay_analysis.get("rule_counts")
    )
    return {
        "deterministic": deterministic,
        "findings_count_a": len(sig_a),
        "findings_count_b": len(sig_b),
        "signature_diff_count": len(diff),
    }


def stage_audit(
    audit_text: str, findings_dict: List[Dict[str, Any]], decisions: Dict[str, Any], progress: Dict[str, Any]
) -> Dict[str, Any]:
    unresolved = audit_text.count("Decision: UNRESOLVED")
    return {
        "audit_text_length": len(audit_text),
        "audit_line_blocks": len(findings_dict),
        "unresolved_count": unresolved,
        "review_complete": bool(progress.get("is_complete")) or len(findings_dict) == 0,
    }


def stage_independent_parsing(raw_bytes: bytes, primary_text: str, source_format: str) -> Dict[str, Any]:
    if source_format != "html":
        return {"applicable": False}
    reference_text = html_extract.extract_reference(raw_bytes)
    check = html_extract.cross_check(primary_text, reference_text)
    return {
        "applicable": True,
        "primary_words": check.primary_words,
        "reference_words": check.reference_words,
        "word_count_delta_pct": check.word_count_delta_pct,
        "agree": check.agree,
    }


def _skip(name: str, reason: str) -> Dict[str, Any]:
    return StageResult(name=name, status="skipped", error=reason).as_dict()


# Keys stripped from a stage's public `data` before it's written into the
# per-contract JSON record — internal handoff values only (full analysis
# objects, raw docx bytes, findings dicts) that the next stage needs in
# memory but that would bloat benchmark_results.json (and, for the findings
# list, duplicate confidence/redline detail already reported per-rule in
# rule_statistics.csv) if serialized once per contract per run.
_INTERNAL_KEYS = {
    "analysis", "_replay_analysis", "findings_dict", "_docx_bytes",
    "_memo_text", "_audit_text", "decisions", "raw_bytes", "contract_text",
}


def _public(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if k not in _INTERNAL_KEYS}


def run_contract(ref: ContractRef) -> ContractResult:
    """Runs all ten stages for one contract. Never raises — every stage is
    wrapped so a single contract's failure (of any kind, at any stage)
    cannot stop or corrupt the benchmark run; it is recorded as a failure on
    this contract's record and the runner moves on to the next one."""
    result = ContractResult(
        contract_id=ref.contract_id,
        category=ref.category,
        company_name=ref.company_name,
        form_type=ref.form_type,
        date_filed=ref.date_filed,
        filename=ref.filename,
        archive_name=ref.archive_name,
        source_format="",
    )
    stages = result.stages

    # 1. Upload
    up = _run_stage("upload", stage_upload, ref.doc_path)
    stages["upload"] = _public(up.as_dict())
    if up.status != "ok":
        result.overall_status = "error"
        result.failures.append("upload")
        _fill_remaining_skipped(stages, "upload failed")
        return result

    result.source_format = up.data["source_format"]
    contract_text = up.data["contract_text"]
    raw_bytes = up.data["raw_bytes"]
    result.metrics.update({
        "characters": up.data["characters"], "words": up.data["words"], "pages": up.data["pages"],
    })

    # 2. Analysis (RuleEngine.analyze — see module docstring)
    an = _run_stage("analysis", stage_analysis, contract_text)
    stages["analysis"] = _public(an.as_dict())
    if an.status != "ok":
        result.overall_status = "error"
        result.failures.append("analysis")
        _fill_remaining_skipped(stages, "analysis failed", skip_from="rule_engine")
        stages["independent_parsing"] = _run_and_publish(
            "independent_parsing", stage_independent_parsing, raw_bytes, contract_text, result.source_format
        )
        return result
    analysis = an.data["analysis"]

    # 3. Rule Engine (bookkeeping over analysis's findings)
    re_ = _run_stage("rule_engine", stage_rule_engine, analysis)
    stages["rule_engine"] = _public(re_.as_dict())
    if re_.status == "ok":
        result.rule_ids_fired = re_.data.get("rule_ids_fired", [])
        result.metrics.update({
            k: re_.data[k] for k in
            ("findings_count", "critical", "high", "medium", "low", "overall_risk",
             "rules_executed", "rules_triggered", "signature_readiness")
            if k in re_.data
        })
    else:
        result.failures.append("rule_engine")

    # 4. Evidence
    ev = _run_stage("evidence", stage_evidence, analysis)
    stages["evidence"] = _public(ev.as_dict())
    if ev.status != "ok":
        result.overall_status = "error"
        result.failures.append("evidence")
        _fill_remaining_skipped(stages, "evidence failed", skip_from="review")
        stages["independent_parsing"] = _run_and_publish(
            "independent_parsing", stage_independent_parsing, raw_bytes, contract_text, result.source_format
        )
        return result
    findings_dict = ev.data["findings_dict"]
    result.metrics.update({
        "redline_count": ev.data["redline_count"],
        "manual_drafting_count": ev.data["manual_drafting_count"],
        "redline_coverage_pct": ev.data["redline_coverage_pct"],
        "overlapping_findings_candidates": ev.data["overlapping_findings_candidates"],
    })

    # 5. Review (automated CI policy — see _auto_decide)
    rv = _run_stage("review", stage_review, findings_dict)
    stages["review"] = _public(rv.as_dict())
    if rv.status != "ok":
        result.overall_status = "error"
        result.failures.append("review")
        _fill_remaining_skipped(stages, "review failed", skip_from="verify")
        stages["independent_parsing"] = _run_and_publish(
            "independent_parsing", stage_independent_parsing, raw_bytes, contract_text, result.source_format
        )
        return result
    decisions = rv.data["decisions"]

    # 6. Verify (exhaustive replay match)
    vf = _run_stage("verify", stage_verify, contract_text, findings_dict)
    stages["verify"] = _public(vf.as_dict())
    replay_analysis = vf.data.get("_replay_analysis") if vf.status == "ok" else None
    if vf.status != "ok" or not vf.data.get("verified", False):
        result.failures.append("verify")
        if vf.status == "ok":
            result.overall_status = "fail"
        else:
            result.overall_status = "error"

    # 7. Negotiation Package
    np_ = _run_stage(
        "negotiation_package", stage_negotiation_package, ref.filename, contract_text, findings_dict, decisions
    )
    stages["negotiation_package"] = _public(np_.as_dict())
    if np_.status != "ok":
        result.overall_status = "error"
        result.failures.append("negotiation_package")
        _fill_remaining_skipped(stages, "negotiation_package failed", skip_from="docx_export")
        if replay_analysis is not None:
            stages["replay"] = _run_and_publish("replay", stage_replay, analysis, replay_analysis)
        stages["independent_parsing"] = _run_and_publish(
            "independent_parsing", stage_independent_parsing, raw_bytes, contract_text, result.source_format
        )
        return result
    docx_bytes = np_.data["_docx_bytes"]
    audit_text = np_.data["_audit_text"]
    skipped_redlines = np_.data.get("skipped_redlines", [])

    # 8. DOCX Export validation
    dx = _run_stage("docx_export", stage_docx_export, docx_bytes, decisions, skipped_redlines)
    stages["docx_export"] = _public(dx.as_dict())
    if dx.status != "ok" or not dx.data.get("counts_consistent", True):
        result.failures.append("docx_export")
        result.overall_status = "fail" if result.overall_status == "pass" else result.overall_status

    # 9. Replay (whole-result determinism, using verify's replay run)
    if replay_analysis is not None:
        rp = _run_stage("replay", stage_replay, analysis, replay_analysis)
        stages["replay"] = _public(rp.as_dict())
        if rp.status != "ok" or not rp.data.get("deterministic", False):
            result.failures.append("replay")
            result.overall_status = "fail" if result.overall_status == "pass" else result.overall_status
    else:
        stages["replay"] = _skip("replay", "verify stage did not produce a replay run")

    # 10. Audit
    ad = _run_stage("audit", stage_audit, audit_text, findings_dict, decisions, rv.data.get("progress", {}))
    stages["audit"] = _public(ad.as_dict())
    if ad.status != "ok":
        result.failures.append("audit")

    # Independent parsing cross-check (parallel concern, not part of the
    # main chain — runs regardless of downstream stage outcomes as long as
    # upload succeeded).
    stages["independent_parsing"] = _run_and_publish(
        "independent_parsing", stage_independent_parsing, raw_bytes, contract_text, result.source_format
    )
    if stages["independent_parsing"].get("status") == "ok" and stages["independent_parsing"].get("applicable") and not stages["independent_parsing"].get("agree", True):
        result.failures.append("independent_parsing")
        result.overall_status = "fail" if result.overall_status == "pass" else result.overall_status

    if not result.failures:
        result.overall_status = "pass"
    return result


def _run_and_publish(name: str, fn, *args, **kwargs) -> Dict[str, Any]:
    return _public(_run_stage(name, fn, *args, **kwargs).as_dict())


_PIPELINE_ORDER = [
    "upload", "analysis", "rule_engine", "evidence", "review", "verify",
    "negotiation_package", "docx_export", "replay", "audit", "independent_parsing",
]


def _fill_remaining_skipped(stages: Dict[str, Any], reason: str, skip_from: Optional[str] = None) -> None:
    start = _PIPELINE_ORDER.index(skip_from) if skip_from else 0
    for name in _PIPELINE_ORDER[start:]:
        if name not in stages:
            stages[name] = _skip(name, reason)
