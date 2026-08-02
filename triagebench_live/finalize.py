"""
Finalize a completed run: write contract_results.json, generate every CSV
report, run regression detection against the previous baseline, and render
production_summary.html (the Production Readiness Report). Kept separate
from runner.run() so reports can be regenerated standalone from an
already-completed run without re-hitting the live application.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import dashboard
from . import reports
from . import regression as regression_mod
from . import storage


def finalize(run_id: str, baseline_run_id: Optional[str] = None, set_as_latest: bool = True) -> Dict[str, Any]:
    manifest = storage.read_manifest(run_id)
    contract_records = storage.load_contract_results(run_id)
    contract_records.sort(key=lambda r: r.get("contract_id_hint") or "")

    security_findings = storage.load_json(run_id, "security_results.json")
    failure_results = storage.load_json(run_id, "failure_results.json")
    concurrency_results = storage.load_json(run_id, "concurrency_results.json")
    browser_results = storage.load_json(run_id, "browser_results.json")

    if baseline_run_id is None:
        baseline_run_id = storage.get_latest_run_id(exclude=run_id)
    comparison = regression_mod.run_regression(run_id, baseline_run_id)

    report_counts = reports.generate_all(
        run_id, contract_records, security_findings, failure_results, concurrency_results, browser_results
    )

    html = dashboard.generate_summary(
        run_id, manifest, contract_records, security_findings, failure_results,
        concurrency_results, browser_results, comparison,
    )
    dashboard.write_summary(run_id, html)

    manifest["finalized"] = True
    manifest["baseline_run_id"] = baseline_run_id
    manifest["has_critical_regressions"] = bool(comparison and comparison.get("has_critical_regressions"))
    storage.write_manifest(run_id, manifest)

    if set_as_latest:
        storage.set_latest(run_id)

    return {
        "run_id": run_id,
        "contracts_processed": len(contract_records),
        "report_counts": report_counts,
        "regression": comparison,
    }
