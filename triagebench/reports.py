"""
Eleven CSV reports, generated from the same aggregate.py rollups the HTML
dashboards use. CSV (not just JSON) is the deliverable here on purpose:
these are meant to be opened in Excel/Sheets by people who are not going to
read benchmark_results.json, and diffed with `git diff`/`csv-diff` in CI.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from . import aggregate as agg
from . import storage


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def generate_all(run_id: str, records: List[Dict[str, Any]], manifest: Dict[str, Any]) -> Dict[str, int]:
    out_dir = storage.config.run_dir(run_id) / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: Dict[str, int] = {}

    rule_stats = agg.compute_rule_statistics(records)
    _write_csv(out_dir / "rule_statistics.csv", rule_stats, [
        "rule_id", "times_triggered", "times_accepted", "times_flagged_manual_drafting",
        "times_rejected", "times_edited", "has_redline_template", "contracts_triggered_in", "never_triggered",
    ])
    counts["rule_statistics.csv"] = len(rule_stats)

    contract_stats = agg.compute_contract_statistics(records)
    _write_csv(out_dir / "contract_statistics.csv", contract_stats, [
        "contract_id", "category", "company_name", "filename", "form_type", "date_filed",
        "pages", "words", "findings_count", "critical", "high", "medium", "low", "overall_risk",
        "redline_count", "manual_drafting_count", "redline_coverage_pct", "overlapping_findings_candidates",
        "analysis_ms", "verify_ms", "docx_export_ms", "replay_ms", "overall_status", "failures",
    ])
    counts["contract_statistics.csv"] = len(contract_stats)

    coverage = agg.compute_coverage_statistics(records)
    coverage_rows = [{"category": cat, **vals} for cat, vals in coverage["by_category"].items()]
    coverage_rows.insert(0, {
        "category": "OVERALL",
        "mean_coverage_pct": coverage["overall_mean_coverage_pct"],
        "n": len(records),
    })
    _write_csv(out_dir / "coverage_statistics.csv", coverage_rows, ["category", "mean_coverage_pct", "n"])
    counts["coverage_statistics.csv"] = len(coverage_rows)

    perf = agg.compute_performance_statistics(records)
    perf_rows = [{"stage": stage, **vals} for stage, vals in perf.items()]
    _write_csv(out_dir / "performance_statistics.csv", perf_rows, [
        "stage", "count", "mean_ms", "median_ms", "p95_ms", "max_ms", "min_ms",
    ])
    counts["performance_statistics.csv"] = len(perf_rows)

    manual = agg.compute_manual_drafting_statistics(records)
    _write_csv(out_dir / "manual_drafting_statistics.csv", manual, [
        "contract_id", "category", "filename", "findings_count", "manual_drafting_count", "manual_drafting_pct",
    ])
    counts["manual_drafting_statistics.csv"] = len(manual)

    redline = agg.compute_redline_statistics(records)
    _write_csv(out_dir / "redline_statistics.csv", redline, [
        "contract_id", "category", "filename", "redline_count", "redline_coverage_pct",
        "overlapping_findings_candidates", "skipped_redlines_in_docx",
    ])
    counts["redline_statistics.csv"] = len(redline)

    verification = agg.compute_verification_statistics(records)
    _write_csv(out_dir / "verification_statistics.csv", verification, [
        "contract_id", "category", "filename", "verify_status", "verified_count", "total",
        "mismatched_count", "mismatched_rule_ids", "replay_status", "replay_deterministic",
    ])
    counts["verification_statistics.csv"] = len(verification)

    parser_failures = agg.compute_parser_failures(records)
    _write_csv(out_dir / "parser_failures.csv", parser_failures, [
        "contract_id", "category", "filename", "kind", "detail",
    ])
    counts["parser_failures.csv"] = len(parser_failures)

    docx_failures = agg.compute_docx_failures(records)
    _write_csv(out_dir / "docx_failures.csv", docx_failures, [
        "contract_id", "category", "filename", "kind", "detail",
    ])
    counts["docx_failures.csv"] = len(docx_failures)

    bench_failures = agg.compute_benchmark_failures(records)
    _write_csv(out_dir / "benchmark_failures.csv", bench_failures, [
        "contract_id", "category", "filename", "overall_status", "failed_stages",
    ])
    counts["benchmark_failures.csv"] = len(bench_failures)

    # regression_report.csv is written by regression.py (needs the previous
    # run to diff against) — an empty placeholder here keeps the file
    # present and openable even for a run with no baseline yet.
    regression_path = out_dir / "regression_report.csv"
    if not regression_path.exists():
        _write_csv(regression_path, [], ["kind", "contract_id", "detail"])
    counts["regression_report.csv"] = 0

    return counts
