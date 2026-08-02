"""
Regression detection: diffs this production run against the previous
completed one (or an explicit baseline run_id). Every comparison here is
between two runs of TriageBench Live itself — both produced by driving the
real app over HTTP/browser — so a regression found here is a regression in
the deployed product between two points in time, not an artifact of two
different measurement methods.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import aggregate as agg
from . import storage

PERFORMANCE_REGRESSION_THRESHOLD_PCT = 25.0


def _by_id(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {r["contract_id_hint"]: r for r in records if r.get("contract_id_hint")}


def compare(
    current_manifest: Dict[str, Any], current_contracts: List[Dict[str, Any]],
    current_security: List[Dict[str, Any]], current_browser: List[Dict[str, Any]],
    baseline_manifest: Dict[str, Any], baseline_contracts: List[Dict[str, Any]],
    baseline_security: List[Dict[str, Any]], baseline_browser: List[Dict[str, Any]],
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []

    cur_by_id, base_by_id = _by_id(current_contracts), _by_id(baseline_contracts)
    common_ids = set(cur_by_id) & set(base_by_id)

    newly_failing, newly_passing = [], []
    missing_findings = []
    verify_regressions, persistence_regressions, docx_regressions = [], [], []

    for cid in sorted(common_ids):
        cur, base = cur_by_id[cid], base_by_id[cid]
        cur_pass, base_pass = cur.get("overall_status") == "pass", base.get("overall_status") == "pass"
        if base_pass and not cur_pass:
            newly_failing.append(cid)
            rows.append({"kind": "contract_newly_failing", "name": cid, "detail": f"failures={cur.get('failures')}"})
        elif cur_pass and not base_pass:
            newly_passing.append(cid)

        cur_findings = (cur.get("metrics") or {}).get("findings_count")
        base_findings = (base.get("metrics") or {}).get("findings_count")
        if cur_findings is not None and base_findings is not None and cur_findings < base_findings:
            missing_findings.append(cid)
            rows.append({"kind": "findings_count_dropped", "name": cid, "detail": f"{base_findings} -> {cur_findings}"})

        cur_verify = ((cur.get("steps") or {}).get("verify") or {})
        base_verify = ((base.get("steps") or {}).get("verify") or {})
        if base_verify.get("status") == "ok" and cur_verify.get("status") != "ok":
            verify_regressions.append(cid)
            rows.append({"kind": "verify_broken", "name": cid, "detail": cur_verify.get("error", "")[:200]})

        cur_persist = ((cur.get("steps") or {}).get("persistence_after_refresh") or {})
        base_persist = ((base.get("steps") or {}).get("persistence_after_refresh") or {})
        if base_persist.get("status") == "ok" and cur_persist.get("status") != "ok":
            persistence_regressions.append(cid)
            rows.append({"kind": "persistence_broken", "name": cid, "detail": cur_persist.get("error", "")[:200]})

        cur_pkg = ((cur.get("steps") or {}).get("negotiation_package") or {})
        base_pkg = ((base.get("steps") or {}).get("negotiation_package") or {})
        if base_pkg.get("status") == "ok" and cur_pkg.get("status") != "ok":
            docx_regressions.append(cid)
            rows.append({"kind": "docx_export_broken", "name": cid, "detail": cur_pkg.get("error", "")[:200]})

    # Performance regressions
    cur_perf = agg.compute_performance_statistics(current_contracts)
    base_perf = agg.compute_performance_statistics(baseline_contracts)
    perf_regressions = []
    for step, cur_stats in cur_perf.items():
        base_stats = base_perf.get(step)
        if not base_stats or not base_stats.get("mean_ms"):
            continue
        delta_pct = (cur_stats["mean_ms"] - base_stats["mean_ms"]) / base_stats["mean_ms"] * 100
        if delta_pct >= PERFORMANCE_REGRESSION_THRESHOLD_PCT:
            perf_regressions.append({"step": step, "baseline_mean_ms": base_stats["mean_ms"],
                                      "current_mean_ms": cur_stats["mean_ms"], "delta_pct": round(delta_pct, 1)})
            rows.append({"kind": "performance_regressed", "name": step,
                         "detail": f"{base_stats['mean_ms']}ms -> {cur_stats['mean_ms']}ms ({delta_pct:+.1f}%)"})

    # Security regressions: a check that passed in the baseline now fails
    base_sec_by_check = {f["check"]: f for f in baseline_security}
    security_regressions = []
    for f in current_security:
        base_f = base_sec_by_check.get(f["check"])
        if base_f and base_f.get("passed") and not f.get("passed"):
            security_regressions.append(f["check"])
            rows.append({"kind": "security_check_newly_failing", "name": f["check"], "detail": f["detail"][:200]})

    # Browser regressions: a browser that passed now fails (only for
    # browsers actually available in both runs — never compares against a
    # skipped/unavailable browser).
    base_browser_by_name = {b["browser"]: b for b in baseline_browser}
    browser_regressions = []
    for b in current_browser:
        base_b = base_browser_by_name.get(b["browser"])
        if base_b and base_b.get("available") and b.get("available"):
            if base_b.get("overall_status") == "pass" and b.get("overall_status") != "pass":
                browser_regressions.append(b["browser"])
                rows.append({"kind": "browser_newly_failing", "name": b["browser"], "detail": b.get("overall_status")})

    summary = {
        "baseline_run_id": baseline_manifest.get("run_id"),
        "current_run_id": current_manifest.get("run_id"),
        "contracts_common": len(common_ids),
        "newly_failing_contracts": len(newly_failing),
        "newly_passing_contracts": len(newly_passing),
        "findings_count_dropped": len(missing_findings),
        "verify_regressions": len(verify_regressions),
        "persistence_regressions": len(persistence_regressions),
        "docx_export_regressions": len(docx_regressions),
        "performance_regressions": perf_regressions,
        "security_regressions": security_regressions,
        "browser_regressions": browser_regressions,
        "has_critical_regressions": bool(
            newly_failing or verify_regressions or persistence_regressions
            or docx_regressions or security_regressions or browser_regressions
        ),
        "rows": rows,
    }
    return summary


def write_report(run_id: str, comparison: Dict[str, Any]) -> Path:
    out_path = storage.config.run_dir(run_id) / "reports" / "production_regressions.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["kind", "name", "detail"])
        writer.writeheader()
        for row in comparison["rows"]:
            writer.writerow(row)
    return out_path


def run_regression(run_id: str, baseline_run_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not baseline_run_id:
        return None
    try:
        baseline_manifest = storage.read_manifest(baseline_run_id)
        baseline_contracts = storage.load_contract_results(baseline_run_id)
        baseline_security = storage.load_json(baseline_run_id, "security_results.json")
        baseline_browser = storage.load_json(baseline_run_id, "browser_results.json")
    except FileNotFoundError:
        return None

    current_manifest = storage.read_manifest(run_id)
    current_contracts = storage.load_contract_results(run_id)
    current_security = storage.load_json(run_id, "security_results.json")
    current_browser = storage.load_json(run_id, "browser_results.json")

    comparison = compare(
        current_manifest, current_contracts, current_security, current_browser,
        baseline_manifest, baseline_contracts, baseline_security, baseline_browser,
    )
    write_report(run_id, comparison)
    storage.write_json(run_id, "regression_comparison.json", comparison)
    return comparison
