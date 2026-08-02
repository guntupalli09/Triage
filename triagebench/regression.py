"""
Regression detection: diffs the current run against the previous completed
run (or an explicit --baseline run_id) and reports what changed.

Granularity note, stated up front because it shapes every function below:
the per-contract record kept in results.jsonl retains which rule_ids fired
on a contract (`rule_ids_fired`) but not the exact-position finding list
(start_index/end_index/exact_snippet) — that detail lives only in-memory
during a run (see pipeline._INTERNAL_KEYS) to keep results.jsonl a bounded
size across thousands of contracts run after run after run. Consequently
"new/missing findings" here is computed at (contract_id, rule_id)
granularity: "rule X started/stopped firing on contract Y" — not at
individual finding-occurrence granularity. That is still exactly the signal
that matters for regression triage (a rule newly firing or newly silent on
a real document), and is a documented, deliberate precision/storage
tradeoff, not an oversight.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import aggregate as agg
from . import storage

COVERAGE_REGRESSION_THRESHOLD_PCT = 5.0   # coverage drop >= this on a contract is flagged
PERFORMANCE_REGRESSION_THRESHOLD_PCT = 25.0  # stage mean_ms increase >= this is flagged


def _by_id(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {r["contract_id"]: r for r in records}


def compare(
    current_records: List[Dict[str, Any]],
    current_manifest: Dict[str, Any],
    baseline_records: List[Dict[str, Any]],
    baseline_manifest: Dict[str, Any],
) -> Dict[str, Any]:
    cur_by_id = _by_id(current_records)
    base_by_id = _by_id(baseline_records)
    common_ids = set(cur_by_id) & set(base_by_id)
    new_ids = set(cur_by_id) - set(base_by_id)
    removed_ids = set(base_by_id) - set(cur_by_id)

    rows: List[Dict[str, Any]] = []

    for cid in new_ids:
        rows.append({"kind": "contract_new_in_run", "contract_id": cid, "detail": "not present in baseline run"})
    for cid in removed_ids:
        rows.append({"kind": "contract_missing_from_run", "contract_id": cid, "detail": "was in baseline, absent now"})

    new_findings_rules: List[Tuple[str, str]] = []
    missing_findings_rules: List[Tuple[str, str]] = []
    coverage_regressions = []
    coverage_improvements = []
    export_changes = []
    docx_changes = []
    parser_changes = []
    verify_regressions = []
    replay_regressions = []

    for cid in sorted(common_ids):
        cur, base = cur_by_id[cid], base_by_id[cid]
        cur_rules = set(cur.get("rule_ids_fired") or [])
        base_rules = set(base.get("rule_ids_fired") or [])

        for rid in sorted(cur_rules - base_rules):
            new_findings_rules.append((cid, rid))
            rows.append({"kind": "new_finding_rule", "contract_id": cid, "detail": rid})
        for rid in sorted(base_rules - cur_rules):
            missing_findings_rules.append((cid, rid))
            rows.append({"kind": "missing_finding_rule", "contract_id": cid, "detail": rid})

        cur_cov = (cur.get("metrics") or {}).get("redline_coverage_pct")
        base_cov = (base.get("metrics") or {}).get("redline_coverage_pct")
        if cur_cov is not None and base_cov is not None:
            delta = cur_cov - base_cov
            if delta <= -COVERAGE_REGRESSION_THRESHOLD_PCT:
                coverage_regressions.append(cid)
                rows.append({"kind": "coverage_regressed", "contract_id": cid, "detail": f"{base_cov} -> {cur_cov}"})
            elif delta >= COVERAGE_REGRESSION_THRESHOLD_PCT:
                coverage_improvements.append(cid)
                rows.append({"kind": "coverage_improved", "contract_id": cid, "detail": f"{base_cov} -> {cur_cov}"})

        cur_dx = (cur.get("stages") or {}).get("docx_export", {})
        base_dx = (base.get("stages") or {}).get("docx_export", {})
        if cur_dx.get("status") != base_dx.get("status") or cur_dx.get("counts_consistent") != base_dx.get("counts_consistent"):
            docx_changes.append(cid)
            rows.append({
                "kind": "docx_export_changed", "contract_id": cid,
                "detail": f"status {base_dx.get('status')}->{cur_dx.get('status')}, "
                          f"counts_consistent {base_dx.get('counts_consistent')}->{cur_dx.get('counts_consistent')}",
            })

        cur_np = (cur.get("stages") or {}).get("negotiation_package", {})
        base_np = (base.get("stages") or {}).get("negotiation_package", {})
        if cur_np.get("status") != base_np.get("status"):
            export_changes.append(cid)
            rows.append({
                "kind": "negotiation_package_status_changed", "contract_id": cid,
                "detail": f"{base_np.get('status')} -> {cur_np.get('status')}",
            })

        cur_up = (cur.get("stages") or {}).get("upload", {})
        base_up = (base.get("stages") or {}).get("upload", {})
        cur_words = (cur.get("metrics") or {}).get("words")
        base_words = (base.get("metrics") or {}).get("words")
        if cur_up.get("status") != base_up.get("status") or (
            cur_words and base_words and abs(cur_words - base_words) / max(cur_words, base_words) > 0.08
        ):
            parser_changes.append(cid)
            rows.append({
                "kind": "parser_output_changed", "contract_id": cid,
                "detail": f"words {base_words} -> {cur_words}; upload {base_up.get('status')} -> {cur_up.get('status')}",
            })

        cur_verify_ok = (cur.get("stages") or {}).get("verify", {}).get("verified")
        base_verify_ok = (base.get("stages") or {}).get("verify", {}).get("verified")
        if base_verify_ok is True and cur_verify_ok is False:
            verify_regressions.append(cid)
            rows.append({"kind": "verify_newly_failing", "contract_id": cid, "detail": ""})

        cur_replay_ok = (cur.get("stages") or {}).get("replay", {}).get("deterministic")
        base_replay_ok = (base.get("stages") or {}).get("replay", {}).get("deterministic")
        if base_replay_ok is True and cur_replay_ok is False:
            replay_regressions.append(cid)
            rows.append({"kind": "replay_newly_nondeterministic", "contract_id": cid, "detail": ""})

    # Corpus-wide rule appear/disappear (a rule that fired anywhere in the
    # baseline run's selected contracts but nowhere in the current run's, or
    # vice versa) — independent of per-contract diffing above, since the
    # selected sample can differ between runs (different --limit/--seed).
    cur_rule_stats = {r["rule_id"]: r for r in agg.compute_rule_statistics(current_records)}
    base_rule_stats = {r["rule_id"]: r for r in agg.compute_rule_statistics(baseline_records)}
    rules_disappeared = [
        rid for rid, s in base_rule_stats.items()
        if s["times_triggered"] > 0 and cur_rule_stats.get(rid, {}).get("times_triggered", 0) == 0
    ]
    rules_newly_firing = [
        rid for rid, s in cur_rule_stats.items()
        if s["times_triggered"] > 0 and base_rule_stats.get(rid, {}).get("times_triggered", 0) == 0
    ]
    for rid in rules_disappeared:
        rows.append({"kind": "rule_disappeared_corpuswide", "contract_id": "", "detail": rid})
    for rid in rules_newly_firing:
        rows.append({"kind": "rule_newly_firing_corpuswide", "contract_id": "", "detail": rid})

    perf_cur = agg.compute_performance_statistics(current_records)
    perf_base = agg.compute_performance_statistics(baseline_records)
    perf_regressions = []
    for stage, cur_stats in perf_cur.items():
        base_stats = perf_base.get(stage)
        if not base_stats or not base_stats.get("mean_ms"):
            continue
        delta_pct = (cur_stats["mean_ms"] - base_stats["mean_ms"]) / base_stats["mean_ms"] * 100
        if delta_pct >= PERFORMANCE_REGRESSION_THRESHOLD_PCT:
            perf_regressions.append({"stage": stage, "baseline_mean_ms": base_stats["mean_ms"], "current_mean_ms": cur_stats["mean_ms"], "delta_pct": round(delta_pct, 1)})
            rows.append({
                "kind": "performance_regressed", "contract_id": "", "detail":
                f"{stage}: {base_stats['mean_ms']}ms -> {cur_stats['mean_ms']}ms ({delta_pct:+.1f}%)",
            })

    summary = {
        "baseline_run_id": baseline_manifest.get("run_id"),
        "current_run_id": current_manifest.get("run_id"),
        "contracts_common": len(common_ids),
        "contracts_new_in_run": len(new_ids),
        "contracts_missing_from_run": len(removed_ids),
        "new_finding_rule_occurrences": len(new_findings_rules),
        "missing_finding_rule_occurrences": len(missing_findings_rules),
        "coverage_regressions": len(coverage_regressions),
        "coverage_improvements": len(coverage_improvements),
        "docx_export_changes": len(docx_changes),
        "negotiation_package_changes": len(export_changes),
        "parser_changes": len(parser_changes),
        "verify_newly_failing": len(verify_regressions),
        "replay_newly_nondeterministic": len(replay_regressions),
        "rules_disappeared_corpuswide": rules_disappeared,
        "rules_newly_firing_corpuswide": rules_newly_firing,
        "performance_regressions": perf_regressions,
        "has_critical_regressions": bool(
            missing_findings_rules or rules_disappeared or verify_regressions or replay_regressions or coverage_regressions or docx_changes
        ),
        "rows": rows,
    }
    return summary


def write_report(run_id: str, comparison: Dict[str, Any]) -> Path:
    out_path = storage.config.run_dir(run_id) / "reports" / "regression_report.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["kind", "contract_id", "detail"])
        writer.writeheader()
        for row in comparison["rows"]:
            writer.writerow(row)
    return out_path


def run_regression(run_id: str, baseline_run_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Returns the comparison dict, or None if there is no baseline to
    compare against (first-ever run — not an error, just nothing to diff)."""
    if not baseline_run_id:
        return None
    try:
        baseline_manifest = storage.read_manifest(baseline_run_id)
        baseline_records = storage.load_results(baseline_run_id)
    except FileNotFoundError:
        return None
    current_manifest = storage.read_manifest(run_id)
    current_records = storage.load_results(run_id)
    comparison = compare(current_records, current_manifest, baseline_records, baseline_manifest)
    write_report(run_id, comparison)
    storage.write_json(run_id, "regression_comparison.json", comparison)
    return comparison
