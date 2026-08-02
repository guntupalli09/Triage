"""
Rollups shared by every CSV report and by production_summary.html — one
place computing "how many contracts failed", "which stage is slowest",
"which security checks failed" so the report generators can't drift apart
on the same number, mirroring triagebench/aggregate.py's role for the
in-process benchmark.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Any, Dict, List, Optional

STEP_ORDER = [
    "signup", "login", "upload_and_analysis", "analysis_verification", "review_page_load",
    "review_decisions", "persistence_after_refresh", "verify", "finalize",
    "negotiation_package", "logout",
]


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] if f == c else s[f] + (s[c] - s[f]) * (k - f)


def compute_workflow_statistics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(records)
    status_counts = defaultdict(int)
    step_status_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for rec in records:
        status_counts[rec.get("overall_status", "unknown")] += 1
        for step_name, step in (rec.get("steps") or {}).items():
            step_status_counts[step_name][step.get("status", "unknown")] += 1

    totals = defaultdict(int)
    for rec in records:
        m = rec.get("metrics", {})
        for k in ("accepted", "rejected", "edited", "flagged", "commented", "findings_count"):
            totals[k] += m.get(k) or 0

    return {
        "contracts_processed": n,
        "status_counts": dict(status_counts),
        "pass_rate_pct": round(status_counts["pass"] / n * 100, 2) if n else None,
        "step_status_counts": {k: dict(v) for k, v in step_status_counts.items()},
        "decision_totals": dict(totals),
    }


def compute_performance_statistics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    perf: Dict[str, List[float]] = defaultdict(list)
    for rec in records:
        for step_name in STEP_ORDER:
            step = (rec.get("steps") or {}).get(step_name)
            if step and isinstance(step.get("ms"), (int, float)):
                perf[step_name].append(step["ms"])

    out = {}
    for step_name, values in perf.items():
        if not values:
            continue
        out[step_name] = {
            "count": len(values),
            "mean_ms": round(mean(values), 3),
            "median_ms": round(median(values), 3),
            "p95_ms": round(_percentile(values, 0.95), 3),
            "max_ms": round(max(values), 3),
            "min_ms": round(min(values), 3),
        }
    return out


def compute_contract_failures(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for rec in records:
        if rec.get("overall_status") != "pass":
            failing_steps = [
                name for name, s in (rec.get("steps") or {}).items()
                if s.get("status") in ("fail", "error")
            ]
            rows.append({
                "contract_id_hint": rec.get("contract_id_hint"),
                "category": rec.get("category"),
                "filename": rec.get("filename"),
                "live_contract_id": rec.get("live_contract_id"),
                "overall_status": rec.get("overall_status"),
                "failed_steps": ";".join(rec.get("failures") or failing_steps),
                "first_error": next(
                    (s.get("error") for s in (rec.get("steps") or {}).values() if s.get("error")), ""
                ),
            })
    return rows


def compute_security_summary(security_findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_severity = defaultdict(int)
    failed = [f for f in security_findings if not f.get("passed")]
    for f in failed:
        by_severity[f.get("severity", "unknown")] += 1
    return {
        "total_checks": len(security_findings),
        "failed_checks": len(failed),
        "failed_by_severity": dict(by_severity),
        "all_passed": len(failed) == 0,
    }


def compute_browser_summary(browser_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "browsers_attempted": [r["browser"] for r in browser_results],
        "browsers_available": [r["browser"] for r in browser_results if r.get("available")],
        "browsers_unavailable": [r["browser"] for r in browser_results if not r.get("available")],
        "browsers_passed": [r["browser"] for r in browser_results if r.get("overall_status") == "pass"],
        "browsers_failed": [r["browser"] for r in browser_results if r.get("available") and r.get("overall_status") != "pass"],
    }
