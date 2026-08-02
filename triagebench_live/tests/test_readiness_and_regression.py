"""
Smoke tests for the pure-logic parts of TriageBench Live: readiness scoring
and regression comparison. These use fabricated result records — no network,
no browser, no engine — to validate the scoring/diffing rules themselves.
"""
from __future__ import annotations

import pytest

from triagebench_live import readiness
from triagebench_live import regression


def _contract(cid, status="pass", findings=5, verify_ok=True, persist_ok=True, pkg_ok=True):
    return {
        "contract_id_hint": cid, "category": "Employment", "company_name": "X", "filename": f"{cid}.txt",
        "live_contract_id": 1, "test_email": "x@test.local",
        "metrics": {"findings_count": findings, "accepted": 1, "rejected": 0, "edited": 0, "flagged": 1, "commented": 1},
        "overall_status": status, "failures": [] if status == "pass" else ["verify"],
        "steps": {
            "signup": {"status": "ok", "ms": 100},
            "upload_and_analysis": {"status": "ok", "ms": 500},
            "review_page_load": {"status": "ok", "ms": 80},
            "verify": {"status": "ok" if verify_ok else "fail", "ms": 200, "error": None if verify_ok else "mismatch"},
            "persistence_after_refresh": {"status": "ok" if persist_ok else "fail", "ms": 60},
            "finalize": {"status": "ok", "ms": 90},
            "negotiation_package": {"status": "ok" if pkg_ok else "error", "ms": 300},
        },
    }


class TestReadinessScoring:
    def test_all_passing_yields_go(self):
        contracts = [_contract(f"c{i}") for i in range(10)]
        security = [{"check": "idor", "passed": True, "severity": "critical", "detail": ""}]
        browsers = [{"browser": "chromium", "available": True, "overall_status": "pass", "steps": []}]
        issues = readiness.collect_issues(contracts, security, [], [], browsers, None)
        scores = readiness.compute_scores(contracts, security, browsers, issues)
        assert scores["verdict"] == "GO"
        assert scores["critical_count"] == 0

    def test_failed_critical_security_check_forces_nogo(self):
        contracts = [_contract(f"c{i}") for i in range(10)]
        security = [{"check": "idor_download_package", "passed": False, "severity": "critical", "detail": "leak"}]
        browsers = [{"browser": "chromium", "available": True, "overall_status": "pass", "steps": []}]
        issues = readiness.collect_issues(contracts, security, [], [], browsers, None)
        scores = readiness.compute_scores(contracts, security, browsers, issues)
        assert scores["verdict"] == "NO-GO"
        assert scores["critical_count"] >= 1

    def test_db_pool_exhaustion_detected_as_critical_infra_issue(self):
        contracts = [_contract("c0")]
        contracts[0]["steps"]["finalize"]["error"] = (
            "ReadTimeout ... sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached, "
            "connection timed out"
        )
        issues = readiness.collect_issues(contracts, [], [], [], [], None)
        titles = [i.title for i in issues]
        assert any("connection pool exhaustion" in t.lower() for t in titles)
        assert any(i.severity == "critical" for i in issues)

    def test_unavailable_browser_never_penalized(self):
        contracts = [_contract(f"c{i}") for i in range(5)]
        browsers = [
            {"browser": "chromium", "available": True, "overall_status": "pass", "steps": []},
            {"browser": "firefox", "available": False, "overall_status": "skipped", "steps": []},
        ]
        issues = readiness.collect_issues(contracts, [], [], [], browsers, None)
        assert not any("firefox" in i.title.lower() for i in issues)


class TestRegression:
    def test_newly_failing_contract_is_critical(self):
        baseline = [_contract("c1", status="pass")]
        current = [_contract("c1", status="fail", verify_ok=False)]
        cmp_ = regression.compare(
            {"run_id": "cur"}, current, [], [],
            {"run_id": "base"}, baseline, [], [],
        )
        assert cmp_["newly_failing_contracts"] == 1
        assert cmp_["has_critical_regressions"] is True

    def test_clean_rerun_has_no_regressions(self):
        baseline = [_contract("c1")]
        current = [_contract("c1")]
        cmp_ = regression.compare(
            {"run_id": "cur"}, current, [], [],
            {"run_id": "base"}, baseline, [], [],
        )
        assert cmp_["has_critical_regressions"] is False

    def test_security_regression_detected(self):
        base_sec = [{"check": "idor_report_page", "passed": True, "severity": "critical", "detail": ""}]
        cur_sec = [{"check": "idor_report_page", "passed": False, "severity": "critical", "detail": "now leaks"}]
        cmp_ = regression.compare(
            {"run_id": "cur"}, [], cur_sec, [],
            {"run_id": "base"}, [], base_sec, [],
        )
        assert "idor_report_page" in cmp_["security_regressions"]
        assert cmp_["has_critical_regressions"] is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
