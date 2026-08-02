"""
Aggregation layer: turns the flat list of per-contract result records
(benchmark_results.json) into every rollup the reports and dashboards need
— rule statistics, contract statistics, coverage, performance, failures.

Kept separate from reports.py/dashboards.py so both consume the exact same
numbers instead of two slightly different recomputations of "coverage" or
"failure rate" drifting apart over time.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Any, Dict, List, Optional

STAGE_ORDER = [
    "upload", "analysis", "rule_engine", "evidence", "review", "verify",
    "negotiation_package", "docx_export", "replay", "audit", "independent_parsing",
]


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def compute_rule_engine_ruleset(records: List[Dict[str, Any]]) -> List[str]:
    """All rule_ids known to the engine, sourced from the engine itself (not
    just rules seen firing) so "never triggered" rules are visible at all."""
    try:
        from . import engine_bridge as eb
        return sorted(r.rule_id for r in eb.get_engine().rules)
    except Exception:
        # Fallback for report regeneration in an environment without the
        # engine importable: union of everything observed firing.
        seen = set()
        for rec in records:
            seen.update(rec.get("rule_ids_fired") or [])
        return sorted(seen)


def compute_rule_statistics(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-finding review detail (edited text, rejection reasons) isn't kept
    in the slim per-contract record (see pipeline._INTERNAL_KEYS —
    findings_dict/decisions are dropped before writing results.jsonl to keep
    it a manageable size across thousands of contracts). Under the fixed CI
    review policy (_auto_decide: accepted iff a redline template exists for
    that rule_id, flagged otherwise — never rejected/edited, since there is
    no human judgment in a CI run), accepted/flagged counts ARE exactly
    recoverable without the full findings_dict: they're just triggered-count
    split by whether the rule_id is in the redline-template registry. See
    engine_bridge.redline_covered_rule_ids()."""
    all_rule_ids = compute_rule_engine_ruleset(records)
    try:
        from . import engine_bridge as eb
        covered = eb.redline_covered_rule_ids()
    except Exception:
        covered = set()

    triggered_count: Dict[str, int] = defaultdict(int)
    contracts_with_rule: Dict[str, set] = defaultdict(set)

    for rec in records:
        rule_ids = rec.get("rule_ids_fired") or []
        for rid in rule_ids:
            triggered_count[rid] += 1
            contracts_with_rule[rid].add(rec["contract_id"])

    rows = []
    for rid in all_rule_ids:
        n = triggered_count.get(rid, 0)
        has_redline = rid in covered
        rows.append({
            "rule_id": rid,
            "times_triggered": n,
            "times_accepted": n if has_redline else 0,
            "times_flagged_manual_drafting": 0 if has_redline else n,
            "times_rejected": 0,   # no human reviewer in CI — see policy note above
            "times_edited": 0,     # no human reviewer in CI — see policy note above
            "has_redline_template": has_redline,
            "contracts_triggered_in": len(contracts_with_rule.get(rid, set())),
            "never_triggered": n == 0,
        })
    rows.sort(key=lambda r: (-r["times_triggered"], r["rule_id"]))
    return rows


def compute_contract_statistics(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for rec in records:
        m = rec.get("metrics", {})
        stages = rec.get("stages", {})
        rows.append({
            "contract_id": rec["contract_id"],
            "category": rec.get("category"),
            "company_name": rec.get("company_name"),
            "filename": rec.get("filename"),
            "form_type": rec.get("form_type"),
            "date_filed": rec.get("date_filed"),
            "pages": m.get("pages"),
            "words": m.get("words"),
            "findings_count": m.get("findings_count"),
            "critical": m.get("critical"),
            "high": m.get("high"),
            "medium": m.get("medium"),
            "low": m.get("low"),
            "overall_risk": m.get("overall_risk"),
            "redline_count": m.get("redline_count"),
            "manual_drafting_count": m.get("manual_drafting_count"),
            "redline_coverage_pct": m.get("redline_coverage_pct"),
            "overlapping_findings_candidates": m.get("overlapping_findings_candidates"),
            "analysis_ms": stages.get("analysis", {}).get("ms"),
            "verify_ms": stages.get("verify", {}).get("ms"),
            "docx_export_ms": stages.get("negotiation_package", {}).get("ms"),
            "replay_ms": stages.get("replay", {}).get("ms"),
            "overall_status": rec.get("overall_status"),
            "failures": ";".join(rec.get("failures") or []),
        })
    return rows


def compute_performance_statistics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    perf: Dict[str, List[float]] = defaultdict(list)
    for rec in records:
        stages = rec.get("stages", {})
        for stage_name in STAGE_ORDER:
            s = stages.get(stage_name)
            if s and isinstance(s.get("ms"), (int, float)):
                perf[stage_name].append(s["ms"])

    out = {}
    for stage_name, values in perf.items():
        if not values:
            continue
        out[stage_name] = {
            "count": len(values),
            "mean_ms": round(mean(values), 3),
            "median_ms": round(median(values), 3),
            "p95_ms": round(_percentile(values, 0.95), 3),
            "max_ms": round(max(values), 3),
            "min_ms": round(min(values), 3),
        }
    return out


def compute_coverage_statistics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    coverages = [
        r["metrics"]["redline_coverage_pct"]
        for r in records
        if r.get("metrics", {}).get("redline_coverage_pct") is not None
    ]
    by_category: Dict[str, List[float]] = defaultdict(list)
    for r in records:
        cov = r.get("metrics", {}).get("redline_coverage_pct")
        if cov is not None:
            by_category[r.get("category", "unknown")].append(cov)

    return {
        "overall_mean_coverage_pct": round(mean(coverages), 2) if coverages else None,
        "overall_median_coverage_pct": round(median(coverages), 2) if coverages else None,
        "by_category": {
            cat: {"mean_coverage_pct": round(mean(vals), 2), "n": len(vals)}
            for cat, vals in by_category.items()
        },
    }


def compute_manual_drafting_statistics(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for rec in records:
        m = rec.get("metrics", {})
        manual = m.get("manual_drafting_count") or 0
        if manual:
            rows.append({
                "contract_id": rec["contract_id"],
                "category": rec.get("category"),
                "filename": rec.get("filename"),
                "findings_count": m.get("findings_count"),
                "manual_drafting_count": manual,
                "manual_drafting_pct": round(manual / m["findings_count"] * 100, 2) if m.get("findings_count") else None,
            })
    rows.sort(key=lambda r: -(r["manual_drafting_count"] or 0))
    return rows


def compute_redline_statistics(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for rec in records:
        m = rec.get("metrics", {})
        rows.append({
            "contract_id": rec["contract_id"],
            "category": rec.get("category"),
            "filename": rec.get("filename"),
            "redline_count": m.get("redline_count"),
            "redline_coverage_pct": m.get("redline_coverage_pct"),
            "overlapping_findings_candidates": m.get("overlapping_findings_candidates"),
            "skipped_redlines_in_docx": (rec.get("stages", {}).get("negotiation_package") or {}).get("skipped_redline_count"),
        })
    rows.sort(key=lambda r: -(r["redline_count"] or 0))
    return rows


def compute_verification_statistics(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for rec in records:
        v = rec.get("stages", {}).get("verify", {})
        rp = rec.get("stages", {}).get("replay", {})
        rows.append({
            "contract_id": rec["contract_id"],
            "category": rec.get("category"),
            "filename": rec.get("filename"),
            "verify_status": v.get("status"),
            "verified_count": v.get("verified_count"),
            "total": v.get("total"),
            "mismatched_count": v.get("mismatched_count"),
            "mismatched_rule_ids": ";".join(v.get("mismatched_rule_ids") or []),
            "replay_status": rp.get("status"),
            "replay_deterministic": rp.get("deterministic"),
        })
    return rows


def compute_parser_failures(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for rec in records:
        up = rec.get("stages", {}).get("upload", {})
        ip = rec.get("stages", {}).get("independent_parsing", {})
        if up.get("status") != "ok":
            rows.append({
                "contract_id": rec["contract_id"], "category": rec.get("category"), "filename": rec.get("filename"),
                "kind": "upload_failed", "detail": up.get("error"),
            })
        if ip.get("status") == "ok" and ip.get("applicable") and not ip.get("agree", True):
            rows.append({
                "contract_id": rec["contract_id"], "category": rec.get("category"), "filename": rec.get("filename"),
                "kind": "independent_parse_disagreement",
                "detail": f"word_count_delta_pct={ip.get('word_count_delta_pct')}",
            })
    return rows


def compute_docx_failures(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for rec in records:
        dx = rec.get("stages", {}).get("docx_export", {})
        if dx.get("status") != "ok":
            rows.append({
                "contract_id": rec["contract_id"], "category": rec.get("category"), "filename": rec.get("filename"),
                "kind": "docx_export_error", "detail": dx.get("error"),
            })
        elif not dx.get("counts_consistent", True):
            rows.append({
                "contract_id": rec["contract_id"], "category": rec.get("category"), "filename": rec.get("filename"),
                "kind": "docx_counts_inconsistent",
                "detail": f"ins={dx.get('ins_count')} expected={dx.get('expected_redline_count')} "
                          f"comment_refs={dx.get('comment_reference_count')} comments_defined={dx.get('comments_defined_count')}",
            })
    return rows


def compute_benchmark_failures(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for rec in records:
        if rec.get("overall_status") != "pass":
            rows.append({
                "contract_id": rec["contract_id"],
                "category": rec.get("category"),
                "filename": rec.get("filename"),
                "overall_status": rec.get("overall_status"),
                "failed_stages": ";".join(rec.get("failures") or []),
            })
    return rows


def compute_summary(records: List[Dict[str, Any]], manifest: Dict[str, Any]) -> Dict[str, Any]:
    n = len(records)
    status_counts = defaultdict(int)
    for rec in records:
        status_counts[rec.get("overall_status", "unknown")] += 1

    stage_failure_counts: Dict[str, int] = defaultdict(int)
    for rec in records:
        for f in rec.get("failures") or []:
            stage_failure_counts[f] += 1

    rule_stats = compute_rule_statistics(records)
    never_fired = [r["rule_id"] for r in rule_stats if r["never_triggered"]]
    most_fired = rule_stats[:15]

    coverage = compute_coverage_statistics(records)
    performance = compute_performance_statistics(records)

    findings_totals = {
        "critical": sum((r.get("metrics", {}).get("critical") or 0) for r in records),
        "high": sum((r.get("metrics", {}).get("high") or 0) for r in records),
        "medium": sum((r.get("metrics", {}).get("medium") or 0) for r in records),
        "low": sum((r.get("metrics", {}).get("low") or 0) for r in records),
    }

    verify_fail = sum(1 for r in records if (r.get("stages", {}).get("verify", {}).get("verified") is False))
    replay_nondeterministic = sum(
        1 for r in records if r.get("stages", {}).get("replay", {}).get("deterministic") is False
    )
    docx_fail = len(compute_docx_failures(records))
    parser_fail = len(compute_parser_failures(records))

    return {
        "run_id": manifest.get("run_id"),
        "label": manifest.get("label"),
        "git_commit": manifest.get("git_commit"),
        "git_branch": manifest.get("git_branch"),
        "started_at": manifest.get("started_at"),
        "finished_at": manifest.get("finished_at"),
        "duration_seconds": manifest.get("duration_seconds"),
        "contracts_selected": manifest.get("corpus_selected"),
        "contracts_processed": n,
        "status_counts": dict(status_counts),
        "pass_rate_pct": round(status_counts["pass"] / n * 100, 2) if n else None,
        "findings_totals": findings_totals,
        "rules_executed_per_contract": len(compute_rule_engine_ruleset(records)),
        "rules_never_fired_count": len(never_fired),
        "rules_never_fired": never_fired,
        "top_firing_rules": most_fired,
        "coverage": coverage,
        "performance": performance,
        "verify_failures": verify_fail,
        "replay_nondeterministic_count": replay_nondeterministic,
        "docx_failures": docx_fail,
        "parser_failures": parser_fail,
        "stage_failure_counts": dict(stage_failure_counts),
    }
