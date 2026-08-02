"""
Scoring: turns everything TriageBench Live observed into the Production
Readiness Report's verdict — Go/No-Go, a readiness score, and a ranked
issue list. The scoring rules are explicit and named here (not buried in
dashboard HTML templating) so the verdict is auditable: anyone can read
this file and see exactly why a run got the score/verdict it did.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from . import aggregate as agg

DB_POOL_EXHAUSTION_MARKERS = ("QueuePool", "connection timed out", "TimeoutError")


@dataclass
class Issue:
    severity: str  # critical | high | medium | low
    title: str
    detail: str
    source: str

    def as_dict(self) -> Dict[str, Any]:
        return {"severity": self.severity, "title": self.title, "detail": self.detail, "source": self.source}


def _detect_infra_issues(contract_records: List[Dict[str, Any]]) -> List[Issue]:
    """Regression guard, not a currently-open bug: this originally detected
    DB connection-pool exhaustion from main.py's `next(get_db())` pattern
    (a real, reproducible bug TriageBench Live's own development run
    found). That has since been fixed — every route now uses
    `Depends(get_db)`, the two `@app.exception_handler` callbacks use
    `database.db_session()` — and `db_lifecycle_proof.py` is the dedicated,
    targeted test that actively proves the fix under load rather than
    waiting to notice it by accident. This scan stays in place as a
    trip-wire: if the same failure signature ever reappears (a future
    route added with `next(get_db())` again, a new leak elsewhere), it is
    caught here immediately rather than only showing up as sporadic
    unrelated-looking contract failures."""
    hangs = 0
    for rec in contract_records:
        for step in (rec.get("steps") or {}).values():
            err = step.get("error") or ""
            if any(marker in err for marker in DB_POOL_EXHAUSTION_MARKERS):
                hangs += 1
    if hangs == 0:
        return []
    return [Issue(
        severity="critical",
        title="Database connection pool exhaustion under sustained load",
        detail=(
            f"{hangs} request(s) across this run failed or hung with a SQLAlchemy QueuePool timeout. "
            f"This exact failure signature was previously caused by main.py calling `db = next(get_db())` "
            f"directly instead of `Depends(get_db)`/`database.db_session()` — that was fixed, so this "
            f"reproducing again means either a new call site regressed back to the old pattern, or a "
            f"genuinely different leak. See db_lifecycle_proof.csv for the targeted, isolated reproduction."
        ),
        source="infrastructure",
    )]


def collect_issues(
    contract_records: List[Dict[str, Any]],
    security_findings: List[Dict[str, Any]],
    failure_results: List[Dict[str, Any]],
    concurrency_results: List[Dict[str, Any]],
    browser_results: List[Dict[str, Any]],
    db_lifecycle_results: Optional[List[Dict[str, Any]]] = None,
    regression: Optional[Dict[str, Any]] = None,
) -> List[Issue]:
    issues: List[Issue] = []
    issues.extend(_detect_infra_issues(contract_records))

    # The targeted DB session-lifecycle proof (db_lifecycle_proof.py) is
    # the single most direct signal in this run — a failure here means the
    # exact bug class this suite was built to catch is present right now,
    # so it is always critical regardless of which phase failed.
    for f in (db_lifecycle_results or []):
        if not f.get("passed"):
            issues.append(Issue(
                "critical", f"DB session lifecycle: {f['name']}", f["detail"], "db_lifecycle",
            ))

    for f in security_findings:
        if not f.get("passed"):
            issues.append(Issue(f.get("severity", "medium"), f"Security: {f['check']}", f["detail"], "security"))

    for r in failure_results:
        if not r.get("passed"):
            issues.append(Issue(r.get("severity", "medium"), f"Failure injection: {r['name']}", r["detail"], "failure_injection"))

    for c in concurrency_results:
        if not c.get("passed"):
            issues.append(Issue(c.get("severity", "medium"), f"Concurrency: {c['name']}", c["detail"], "concurrency"))

    contract_failures = agg.compute_contract_failures(contract_records)
    error_count = sum(1 for r in contract_failures if r["overall_status"] == "error")
    fail_count = sum(1 for r in contract_failures if r["overall_status"] == "fail")
    n = len(contract_records) or 1
    if error_count:
        issues.append(Issue(
            "critical" if error_count / n > 0.1 else "high",
            "Contract workflow errors",
            f"{error_count}/{n} contract journeys hit an unexpected error (not a validation failure — "
            f"an exception, timeout, or unreachable step). See contract_results.csv / production_failures.csv.",
            "workflow",
        ))
    if fail_count:
        issues.append(Issue(
            "high" if fail_count / n > 0.1 else "medium",
            "Contract workflow validation failures",
            f"{fail_count}/{n} contract journeys completed but failed a validation assertion "
            f"(e.g. DOCX validator disagreement, persistence mismatch). See contract_results.csv.",
            "workflow",
        ))

    for b in browser_results:
        if b.get("available") and b.get("overall_status") != "pass":
            failed_steps = [s["name"] for s in b.get("steps", []) if s["status"] in ("fail", "error")]
            issues.append(Issue("high", f"Browser failure: {b['browser']}",
                                 f"steps failed: {failed_steps}", "browser"))

    perf = agg.compute_performance_statistics(contract_records)
    for step, stats in perf.items():
        if stats.get("p95_ms", 0) > 8000:
            issues.append(Issue("medium", f"Slow step: {step}",
                                 f"p95={stats['p95_ms']}ms, mean={stats['mean_ms']}ms across {stats['count']} runs "
                                 f"— exceeds the 8s p95 budget for a synchronous customer-facing action.",
                                 "performance"))

    if regression:
        for kind_count, title in [
            ("newly_failing_contracts", "Newly failing contracts vs. baseline"),
            ("verify_regressions", "Verify regressed vs. baseline"),
            ("persistence_regressions", "Persistence regressed vs. baseline"),
            ("docx_export_regressions", "DOCX export regressed vs. baseline"),
        ]:
            count = regression.get(kind_count, 0)
            if count:
                issues.append(Issue("critical", title, f"{count} contract(s) affected — see regressions.", "regression"))
        for check in regression.get("security_regressions", []):
            issues.append(Issue("critical", f"Security regression: {check}",
                                 "This check passed in the baseline run and fails now.", "regression"))
        for browser in regression.get("browser_regressions", []):
            issues.append(Issue("high", f"Browser regression: {browser}",
                                 "This browser passed in the baseline run and fails now.", "regression"))
        for pr in regression.get("performance_regressions", []):
            issues.append(Issue("medium", f"Performance regression: {pr['step']}",
                                 f"{pr['baseline_mean_ms']}ms -> {pr['current_mean_ms']}ms ({pr['delta_pct']:+.1f}%)",
                                 "regression"))

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    issues.sort(key=lambda i: order.get(i.severity, 9))
    return issues


def compute_scores(
    contract_records: List[Dict[str, Any]], security_findings: List[Dict[str, Any]],
    browser_results: List[Dict[str, Any]], issues: List[Issue],
) -> Dict[str, Any]:
    n = len(contract_records) or 1
    wf = agg.compute_workflow_statistics(contract_records)
    workflow_pass_rate = (wf["pass_rate_pct"] or 0) / 100.0

    sec_summary = agg.compute_security_summary(security_findings)
    security_pass_rate = 1.0 - (sec_summary["failed_checks"] / max(sec_summary["total_checks"], 1))

    available_browsers = [b for b in browser_results if b.get("available")]
    browser_pass_rate = (
        sum(1 for b in available_browsers if b.get("overall_status") == "pass") / len(available_browsers)
        if available_browsers else None
    )

    critical_count = sum(1 for i in issues if i.severity == "critical")
    high_count = sum(1 for i in issues if i.severity == "high")
    medium_count = sum(1 for i in issues if i.severity == "medium")

    # Weighted composite: workflow correctness matters most (customers
    # experience it directly on every contract), security and browser
    # compatibility next, each further reduced by a flat penalty per
    # critical/high issue so a single severe bug can't be diluted away by
    # an otherwise-large passing sample.
    base = (
        workflow_pass_rate * 55
        + security_pass_rate * 25
        + (browser_pass_rate if browser_pass_rate is not None else workflow_pass_rate) * 20
    )
    penalty = critical_count * 20 + high_count * 8 + medium_count * 2
    readiness_score = max(0, round(base - penalty))

    # Commercial readiness additionally weighs whether the negotiation
    # package / DOCX deliverable — the thing a paying customer actually
    # sends to a counterparty — works, since that is the product's core
    # commercial promise, not just "the app didn't crash."
    docx_ok_count = sum(
        1 for r in contract_records
        if ((r.get("steps") or {}).get("negotiation_package") or {}).get("status") == "ok"
    )
    docx_rate = docx_ok_count / n
    commercial_score = max(0, round(readiness_score * 0.6 + docx_rate * 100 * 0.4 - penalty * 0.3))

    if critical_count > 0:
        verdict = "NO-GO"
    elif high_count > 3 or readiness_score < 70:
        verdict = "CONDITIONAL GO"
    else:
        verdict = "GO"

    return {
        "workflow_pass_rate_pct": round(workflow_pass_rate * 100, 1),
        "security_pass_rate_pct": round(security_pass_rate * 100, 1),
        "browser_pass_rate_pct": round(browser_pass_rate * 100, 1) if browser_pass_rate is not None else None,
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "readiness_score": readiness_score,
        "commercial_readiness_score": commercial_score,
        "verdict": verdict,
    }


def top_priorities(issues: List[Issue], limit: int = 5) -> List[str]:
    picks = []
    for i in issues:
        if i.severity not in ("critical", "high"):
            continue
        picks.append(f"[{i.severity.upper()}] {i.title}")
        if len(picks) >= limit:
            break
    if not picks:
        picks = [f"[{i.severity.upper()}] {i.title}" for i in issues[:limit]]
    return picks or ["No outstanding issues — maintain current test coverage as the product evolves."]
