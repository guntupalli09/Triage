"""
Finalize a completed (or resumed-to-completion) run: materialize
results.jsonl into the three top-level JSON outputs, generate every CSV
report and HTML dashboard, and run regression detection against the
previous baseline. Kept separate from runner.run() so reports can be
regenerated standalone from an already-completed run (e.g. after fixing a
bug in a report generator) without re-running the corpus.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import aggregate as agg
from . import dashboards
from . import regression as regression_mod
from . import reports
from . import storage


def finalize(run_id: str, baseline_run_id: Optional[str] = None, set_as_latest: bool = True) -> Dict[str, Any]:
    manifest = storage.read_manifest(run_id)
    records = storage.load_results(run_id)
    records.sort(key=lambda r: r["contract_id"])  # deterministic output ordering

    storage.write_json(run_id, "benchmark_results.json", records)

    summary = agg.compute_summary(records, manifest)
    storage.write_json(run_id, "benchmark_summary.json", summary)

    report_counts = reports.generate_all(run_id, records, manifest)

    if baseline_run_id is None:
        baseline_run_id = storage.get_latest_run_id(exclude=run_id)
    comparison = regression_mod.run_regression(run_id, baseline_run_id)

    dashboards.generate_all(run_id, records, manifest, summary, comparison)

    manifest["finalized"] = True
    manifest["baseline_run_id"] = baseline_run_id
    manifest["has_critical_regressions"] = bool(comparison and comparison.get("has_critical_regressions"))
    storage.write_manifest(run_id, manifest)

    if set_as_latest:
        storage.set_latest(run_id)

    return {
        "run_id": run_id,
        "contracts_processed": len(records),
        "report_counts": report_counts,
        "summary": summary,
        "regression": comparison,
    }
