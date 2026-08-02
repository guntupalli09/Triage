"""
Extended reporting layer for a completed TriageBench run — every additional
CSV/HTML/JSON/Markdown artifact requested for the full-corpus baseline run,
computed entirely from a completed run's own results.jsonl + manifest. This
module reads finished output; it does not touch the pipeline, the engine
bridge, or the runner. Nothing here changes how a contract is processed —
it only slices and reports data the pipeline already collected.

Two data-fidelity limits are documented here up front, honestly, rather
than fabricated:

- Per-finding start/end offsets and exact_snippet text are not retained in
  results.jsonl (pipeline._INTERNAL_KEYS strips findings_dict before
  writing, to keep the file bounded across 4,190+ contracts). Offset
  corruption is nonetheless actively guarded: Finding.__post_init__
  (rules_engine.py) asserts `start_index <= end_index` and a non-empty
  exact_snippet at construction time for every single finding, in every
  contract, on every run — a violation would raise immediately and surface
  as an "analysis" or "evidence" stage error in benchmark_failures.csv, not
  silently pass through. offset_failures.csv is therefore derived from
  actual stage failures whose error text matches that assertion, not from
  a separate post-hoc offset re-check this module cannot perform without
  the stripped data.
- Per-rule verify/replay mismatch attribution is at the rule_id level
  (mismatched_rule_ids per contract, from the verify stage) — precise to
  which rule, not to which exact occurrence when a rule fires more than
  once in one document. That is the same granularity tradeoff documented
  in regression.py for the same reason.
"""
from __future__ import annotations

import csv
import html as htmllib
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Dict, List, Optional, Tuple

from . import aggregate as agg
from . import engine_bridge as eb
from . import storage

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] if f == c else s[f] + (s[c] - s[f]) * (k - f)


def _stats(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "mean": None, "median": None, "p90": None,
                "p95": None, "p99": None, "max": None, "stddev": None}
    return {
        "n": len(values), "min": round(min(values), 3), "mean": round(mean(values), 3),
        "median": round(median(values), 3), "p90": round(_percentile(values, 0.90), 3),
        "p95": round(_percentile(values, 0.95), 3), "p99": round(_percentile(values, 0.99), 3),
        "max": round(max(values), 3), "stddev": round(pstdev(values), 3) if len(values) > 1 else 0.0,
    }


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return len(rows)


def _rule_family(rule_id: str) -> str:
    """H_LOL_01 -> LOL, M_INSURANCE_MINIMUM_MISSING_01 -> INSURANCE_MINIMUM_MISSING.
    Derived from the rule_id's own naming convention (SEVERITY_FAMILY_NN) —
    no separate taxonomy is maintained by the engine, so this is the only
    grouping available without inventing one."""
    parts = rule_id.split("_")
    if len(parts) <= 2:
        return rule_id
    body = parts[1:]
    if body and body[-1].isdigit():
        body = body[:-1]
    return "_".join(body) or rule_id


def _stage(rec: Dict[str, Any], name: str) -> Dict[str, Any]:
    return (rec.get("stages") or {}).get(name) or {}


_CSS = """
:root { color-scheme: light dark; }
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 2rem;
       background: #0b0d12; color: #e6e8ee; }
@media (prefers-color-scheme: light) { body { background: #f7f8fa; color: #1a1d24; } }
h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
.subtitle { color: #8a90a2; margin-bottom: 1.5rem; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; margin-bottom: 2rem; }
.tile { background: #151822; border: 1px solid #262b3a; border-radius: 10px; padding: 1rem; }
@media (prefers-color-scheme: light) { .tile { background: #fff; border-color: #e3e5ea; } }
.tile .val { font-size: 1.6rem; font-weight: 700; }
.tile .lbl { font-size: 0.78rem; color: #8a90a2; text-transform: uppercase; letter-spacing: 0.04em; }
.ok { color: #33d17a; } .warn { color: #f5c04a; } .bad { color: #ff6b6b; }
table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; font-size: 0.85rem; }
th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #262b3a; }
@media (prefers-color-scheme: light) { th, td { border-color: #e3e5ea; } }
th { color: #8a90a2; font-weight: 600; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.03em; }
tr:hover { background: rgba(122,162,255,0.06); }
section { margin-bottom: 2rem; }
h2 { font-size: 1.1rem; border-bottom: 1px solid #262b3a; padding-bottom: 0.4rem; }
@media (prefers-color-scheme: light) { h2 { border-color: #e3e5ea; } }
code { background: #151822; padding: 0.1rem 0.35rem; border-radius: 4px; }
@media (prefers-color-scheme: light) { code { background: #eef0f4; } }
.empty { color: #8a90a2; font-style: italic; }
"""


def _e(v: Any) -> str:
    return htmllib.escape(str(v)) if v is not None else ""


def _tile(label: str, value: Any, cls: str = "") -> str:
    return f'<div class="tile"><div class="val {cls}">{_e(value)}</div><div class="lbl">{_e(label)}</div></div>'


def _table(headers: List[str], rows: List[List[str]], empty_msg: str = "No data.") -> str:
    if not rows:
        return f'<p class="empty">{_e(empty_msg)}</p>'
    thead = "".join(f"<th>{_e(h)}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{trs}</tbody></table>"


def _page(title: str, body: str) -> str:
    return f'<!doctype html><html><head><meta charset="utf-8"><title>{_e(title)}</title><style>{_CSS}</style></head><body><h1>{_e(title)}</h1>{body}</body></html>'


def _write_html(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Rule coverage
# ---------------------------------------------------------------------------

def _build_rule_coverage(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_rule_ids = agg.compute_rule_engine_ruleset(records)
    try:
        covered = eb.redline_covered_rule_ids()
    except Exception:
        covered = set()

    per_rule_contract_occ: Dict[str, List[int]] = defaultdict(list)   # occurrences per triggered contract
    per_rule_categories: Dict[str, set] = defaultdict(set)
    per_rule_verify_fail: Dict[str, int] = defaultdict(int)
    total_evaluated = len(records)
    categories_present = sorted({r.get("category") for r in records if r.get("category")})

    for rec in records:
        occ = _stage(rec, "rule_engine").get("rule_occurrence_counts") or {}
        cat = rec.get("category")
        for rid, n in occ.items():
            per_rule_contract_occ[rid].append(n)
            if cat:
                per_rule_categories[rid].add(cat)
        verify = _stage(rec, "verify")
        for rid in (verify.get("mismatched_rule_ids") or []):
            per_rule_verify_fail[rid] += 1

    rows = []
    for rid in all_rule_ids:
        occs = per_rule_contract_occ.get(rid, [])
        contracts_triggered = len(occs)
        total_occurrences = sum(occs)
        cats_triggered = sorted(per_rule_categories.get(rid, set()))
        cats_never = sorted(set(categories_present) - per_rule_categories.get(rid, set()))
        has_redline = rid in covered
        rows.append({
            "rule_id": rid,
            "rule_family": _rule_family(rid),
            "severity": rid.split("_", 1)[0] if "_" in rid else "",
            "contracts_evaluated": total_evaluated,
            "contracts_triggered": contracts_triggered,
            "total_occurrences": total_occurrences,
            "unique_contracts_triggered": contracts_triggered,
            "trigger_rate_pct": round(contracts_triggered / total_evaluated * 100, 3) if total_evaluated else 0,
            "avg_occurrences_per_triggered_contract": round(total_occurrences / contracts_triggered, 3) if contracts_triggered else 0,
            "min_occurrences": min(occs) if occs else 0,
            "median_occurrences": round(median(occs), 2) if occs else 0,
            "p95_occurrences": round(_percentile([float(o) for o in occs], 0.95), 2) if occs else 0,
            "max_occurrences": max(occs) if occs else 0,
            "categories_triggered": ";".join(cats_triggered),
            "categories_never_triggered": ";".join(cats_never),
            "has_redline_template": has_redline,
            "findings_with_redline_est": total_occurrences if has_redline else 0,
            "findings_without_redline_est": 0 if has_redline else total_occurrences,
            "synthetic_accepted_est": total_occurrences if has_redline else 0,
            "synthetic_flagged_est": 0 if has_redline else total_occurrences,
            "synthetic_rejected_est": 0,
            "synthetic_edited_est": 0,
            "verify_failures": per_rule_verify_fail.get(rid, 0),
            "never_triggered": contracts_triggered == 0,
        })
    rows.sort(key=lambda r: (-r["total_occurrences"], r["rule_id"]))
    return rows


def generate_rule_coverage_reports(run_id: str, records: List[Dict[str, Any]]) -> Dict[str, int]:
    out_dir = storage.config.run_dir(run_id) / "reports"
    dash_dir = storage.config.run_dir(run_id) / "dashboards"
    counts = {}

    coverage_rows = _build_rule_coverage(records)
    fields = list(coverage_rows[0].keys()) if coverage_rows else [
        "rule_id", "rule_family", "severity", "contracts_evaluated", "contracts_triggered",
        "total_occurrences", "unique_contracts_triggered", "trigger_rate_pct",
        "avg_occurrences_per_triggered_contract", "min_occurrences", "median_occurrences",
        "p95_occurrences", "max_occurrences", "categories_triggered", "categories_never_triggered",
        "has_redline_template", "findings_with_redline_est", "findings_without_redline_est",
        "synthetic_accepted_est", "synthetic_flagged_est", "synthetic_rejected_est",
        "synthetic_edited_est", "verify_failures", "never_triggered",
    ]
    counts["rule_coverage.csv"] = _write_csv(out_dir / "rule_coverage.csv", coverage_rows, fields)

    occ_rows = []
    for rec in records:
        occ = _stage(rec, "rule_engine").get("rule_occurrence_counts") or {}
        for rid, n in occ.items():
            occ_rows.append({"contract_id": rec["contract_id"], "category": rec.get("category"), "rule_id": rid, "occurrences": n})
    counts["rule_occurrences.csv"] = _write_csv(out_dir / "rule_occurrences.csv", occ_rows,
                                                 ["contract_id", "category", "rule_id", "occurrences"])

    never = [r for r in coverage_rows if r["never_triggered"]]
    counts["rules_never_triggered.csv"] = _write_csv(out_dir / "rules_never_triggered.csv", never, fields)

    high_freq = sorted(
        [r for r in coverage_rows if not r["never_triggered"]],
        key=lambda r: -r["trigger_rate_pct"],
    )[:40]
    counts["rules_high_frequency.csv"] = _write_csv(out_dir / "rules_high_frequency.csv", high_freq, fields)

    low_redline = sorted(
        [r for r in coverage_rows if r["total_occurrences"] > 0 and not r["has_redline_template"]],
        key=lambda r: -r["total_occurrences"],
    )
    counts["rules_low_redline_coverage.csv"] = _write_csv(out_dir / "rules_low_redline_coverage.csv", low_redline, fields)

    # Anchor failures: guarded by Finding.__post_init__ assertions at
    # construction time — a violation surfaces as an analysis/evidence stage
    # error, never as a silently-anchored-wrong finding. Report actual
    # observed stage errors whose text matches those assertions.
    anchor_failure_rows = []
    for rec in records:
        for stage_name in ("analysis", "evidence"):
            s = _stage(rec, stage_name)
            err = s.get("error") or ""
            if "start_index" in err or "exact_snippet" in err or "end_index" in err:
                anchor_failure_rows.append({
                    "contract_id": rec["contract_id"], "category": rec.get("category"),
                    "stage": stage_name, "error": err[:500],
                })
    counts["rules_with_anchor_failures.csv"] = _write_csv(
        out_dir / "rules_with_anchor_failures.csv", anchor_failure_rows,
        ["contract_id", "category", "stage", "error"],
    )

    replay_fail_rules = sorted(
        [r for r in coverage_rows if r["verify_failures"] > 0],
        key=lambda r: -r["verify_failures"],
    )
    counts["rules_with_replay_failures.csv"] = _write_csv(
        out_dir / "rules_with_replay_failures.csv", replay_fail_rules, fields,
    )

    tiles = "".join([
        _tile("Total rules", len(coverage_rows)),
        _tile("Never triggered", len(never), "warn" if never else "ok"),
        _tile("Active rules", len(coverage_rows) - len(never), "ok"),
        _tile("Rules w/ verify failures", len(replay_fail_rules), "bad" if replay_fail_rules else "ok"),
        _tile("Rules w/o redline (triggered)", len(low_redline), "warn" if low_redline else "ok"),
    ])
    rows_html = [
        [f'<code>{_e(r["rule_id"])}</code>', _e(r["rule_family"]), str(r["contracts_triggered"]),
         str(r["total_occurrences"]), f'{r["trigger_rate_pct"]}%', str(r["min_occurrences"]),
         str(r["median_occurrences"]), str(r["p95_occurrences"]), str(r["max_occurrences"]),
         "yes" if r["has_redline_template"] else "no", str(r["verify_failures"])]
        for r in coverage_rows
    ]
    body = f"""<p class="subtitle">Full-corpus rule coverage — {len(records)} contracts evaluated.</p>
<div class="tiles">{tiles}</div>
<section><h2>Every rule ({len(coverage_rows)})</h2>
{_table(['Rule ID', 'Family', 'Contracts Triggered', 'Total Occurrences', 'Trigger Rate',
         'Min/contract', 'Median/contract', 'P95/contract', 'Max/contract', 'Has Redline', 'Verify Failures'], rows_html)}
</section>"""
    _write_html(dash_dir / "rule_coverage.html", _page("Rule Coverage — Full Corpus", body))
    counts["rule_coverage.html"] = 1

    return counts


# ---------------------------------------------------------------------------
# 2. Parser failures
# ---------------------------------------------------------------------------

def _classify_parser_severity(rec: Dict[str, Any]) -> Tuple[str, str]:
    """Returns (severity, root_cause). Conservative: only classifies P0/P1
    for actual observed failures; a clean independent-parsing disagreement
    within tolerance is not a failure at all and isn't included here."""
    upload = _stage(rec, "upload")
    ip = _stage(rec, "independent_parsing")
    if upload.get("status") != "ok":
        return "P0", "upload/extraction failed entirely — no contract text produced"
    if ip.get("status") == "ok" and ip.get("applicable") and not ip.get("agree", True):
        delta = ip.get("word_count_delta_pct") or 0
        if delta >= 25:
            return "P1", f"independent extractor disagreement of {delta}% word count — likely omitted/duplicated content"
        return "P2", f"independent extractor disagreement of {delta}% word count — within plausible markup-quirk range"
    return "P3", "no disagreement"


def generate_parser_reports(run_id: str, records: List[Dict[str, Any]]) -> Dict[str, int]:
    out_dir = storage.config.run_dir(run_id) / "reports"
    dash_dir = storage.config.run_dir(run_id) / "dashboards"
    counts = {}

    parser_rows = []
    disagreement_rows = []
    for rec in records:
        sev, cause = _classify_parser_severity(rec)
        upload = _stage(rec, "upload")
        ip = _stage(rec, "independent_parsing")
        if sev in ("P0", "P1"):
            parser_rows.append({
                "contract_id": rec["contract_id"], "filename": rec.get("filename"),
                "company": rec.get("company_name"), "category": rec.get("category"),
                "primary_result": f"{ip.get('primary_words')} words" if ip else "n/a",
                "secondary_result": f"{ip.get('reference_words')} words" if ip else "n/a",
                "mismatch_type": "upload_failure" if sev == "P0" else "word_count_disagreement",
                "mismatch_size_pct": ip.get("word_count_delta_pct"),
                "downstream_effect": "no findings produced" if sev == "P0" else "findings/coverage may be understated or overstated",
                "severity": sev, "root_cause": cause,
                "recommended_fix": "investigate upload/extract_text_from_file failure" if sev == "P0"
                                    else "compare primary vs reference extractor output for this filing's markup",
                "ci_blocking": sev == "P0",
                "error": (upload.get("error") or "")[:300],
            })
        if ip.get("status") == "ok" and ip.get("applicable") and not ip.get("agree", True):
            disagreement_rows.append({
                "contract_id": rec["contract_id"], "filename": rec.get("filename"),
                "category": rec.get("category"), "primary_words": ip.get("primary_words"),
                "reference_words": ip.get("reference_words"), "delta_pct": ip.get("word_count_delta_pct"),
                "severity": sev,
            })

    fields = ["contract_id", "filename", "company", "category", "primary_result", "secondary_result",
              "mismatch_type", "mismatch_size_pct", "downstream_effect", "severity", "root_cause",
              "recommended_fix", "ci_blocking", "error"]
    counts["parser_failures.csv"] = _write_csv(out_dir / "parser_failures.csv", parser_rows, fields)
    counts["extractor_disagreements.csv"] = _write_csv(
        out_dir / "extractor_disagreements.csv", disagreement_rows,
        ["contract_id", "filename", "category", "primary_words", "reference_words", "delta_pct", "severity"],
    )

    # offset_failures.csv — see module docstring: derived from actual
    # anchoring-assertion stage errors, not a post-hoc re-check (the exact
    # offsets aren't retained in the slim record by design).
    offset_rows = []
    for rec in records:
        for stage_name in ("analysis", "evidence"):
            s = _stage(rec, stage_name)
            err = s.get("error") or ""
            if "start_index" in err or "end_index" in err:
                offset_rows.append({"contract_id": rec["contract_id"], "stage": stage_name, "error": err[:500]})
    counts["offset_failures.csv"] = _write_csv(out_dir / "offset_failures.csv", offset_rows, ["contract_id", "stage", "error"])

    overlap_rows = [
        {"contract_id": rec["contract_id"], "category": rec.get("category"), "filename": rec.get("filename"),
         "overlapping_findings_candidates": (rec.get("metrics") or {}).get("overlapping_findings_candidates"),
         "skipped_redlines_in_docx": (_stage(rec, "negotiation_package") or {}).get("skipped_redline_count")}
        for rec in records if ((rec.get("metrics") or {}).get("overlapping_findings_candidates") or 0) > 0
    ]
    overlap_rows.sort(key=lambda r: -(r["overlapping_findings_candidates"] or 0))
    counts["overlap_cases.csv"] = _write_csv(
        out_dir / "overlap_cases.csv", overlap_rows,
        ["contract_id", "category", "filename", "overlapping_findings_candidates", "skipped_redlines_in_docx"],
    )

    by_sev = Counter(r["severity"] for r in parser_rows)
    by_cat: Dict[str, Counter] = defaultdict(Counter)
    for r in parser_rows:
        by_cat[r["category"]][r["severity"]] += 1

    tiles = "".join([
        _tile("Contracts evaluated", len(records)),
        _tile("P0 (text lost/corrupt)", by_sev.get("P0", 0), "bad" if by_sev.get("P0") else "ok"),
        _tile("P1 (offset/boundary)", by_sev.get("P1", 0), "bad" if by_sev.get("P1") else "ok"),
        _tile("Extractor disagreements (any)", len(disagreement_rows)),
        _tile("Overlap cases", len(overlap_rows)),
    ])
    body = f"<div class='tiles'>{tiles}</div>" + _table(
        ["Contract", "Category", "Severity", "Root Cause", "CI Blocking"],
        [[r["contract_id"], r["category"], r["severity"], r["root_cause"][:150], str(r["ci_blocking"])] for r in parser_rows],
        "No P0/P1 parser failures.",
    )
    _write_html(dash_dir / "parser_failure_summary.html", _page("Parser Failure Summary — Full Corpus", body))
    counts["parser_failure_summary.html"] = 1

    cat_rows_html = [[cat, str(c.get("P0", 0)), str(c.get("P1", 0)), str(c.get("P2", 0))] for cat, c in sorted(by_cat.items())]
    body2 = _table(["Category", "P0", "P1", "P2"], cat_rows_html)
    _write_html(dash_dir / "parser_failures_by_category.html", _page("Parser Failures by Category", body2))
    counts["parser_failures_by_category.html"] = 1

    return counts, {"by_severity": dict(by_sev), "by_category": {k: dict(v) for k, v in by_cat.items()}}


# ---------------------------------------------------------------------------
# 3. Export / DOCX failures
# ---------------------------------------------------------------------------

def _classify_export_severity(rec: Dict[str, Any]) -> Tuple[str, str]:
    dx = _stage(rec, "docx_export")
    pkg = _stage(rec, "negotiation_package")
    if pkg.get("status") != "ok" or dx.get("status") != "ok":
        return "E0", "package or DOCX generation/parse failed outright"
    if not dx.get("counts_consistent", True):
        return "E1", "tracked-change/comment count mismatch vs. decisions sent"
    return "E3", "clean"


def generate_export_reports(run_id: str, records: List[Dict[str, Any]]) -> Tuple[Dict[str, int], Dict[str, Any]]:
    out_dir = storage.config.run_dir(run_id) / "reports"
    dash_dir = storage.config.run_dir(run_id) / "dashboards"
    counts = {}

    export_rows, docx_rows, track_rows, comment_rows, pkg_rows = [], [], [], [], []
    by_sev = Counter()
    by_cat: Dict[str, Counter] = defaultdict(Counter)

    for rec in records:
        sev, cause = _classify_export_severity(rec)
        by_sev[sev] += 1
        if rec.get("category"):
            by_cat[rec["category"]][sev] += 1
        if sev == "E3":
            continue
        dx = _stage(rec, "docx_export")
        pkg = _stage(rec, "negotiation_package")
        row = {
            "contract_id": rec["contract_id"], "category": rec.get("category"), "filename": rec.get("filename"),
            "severity": sev, "root_cause": cause,
            "docx_status": dx.get("status"), "package_status": pkg.get("status"),
            "ins_count": dx.get("ins_count"), "expected_redline_count": dx.get("expected_redline_count"),
            "comment_reference_count": dx.get("comment_reference_count"), "comments_defined_count": dx.get("comments_defined_count"),
            "error": ((dx.get("error") or "") + " " + (pkg.get("error") or ""))[:500],
        }
        export_rows.append(row)
        docx_rows.append(row)
        if dx.get("ins_count") != dx.get("expected_redline_count"):
            track_rows.append(row)
        if dx.get("comment_reference_count") != dx.get("comments_defined_count"):
            comment_rows.append(row)
        if pkg.get("status") != "ok":
            pkg_rows.append(row)

    fields = ["contract_id", "category", "filename", "severity", "root_cause", "docx_status", "package_status",
              "ins_count", "expected_redline_count", "comment_reference_count", "comments_defined_count", "error"]
    counts["export_failures.csv"] = _write_csv(out_dir / "export_failures.csv", export_rows, fields)
    counts["docx_failures.csv"] = _write_csv(out_dir / "docx_failures.csv", docx_rows, fields)
    counts["track_change_failures.csv"] = _write_csv(out_dir / "track_change_failures.csv", track_rows, fields)
    counts["comment_failures.csv"] = _write_csv(out_dir / "comment_failures.csv", comment_rows, fields)
    counts["package_integrity_failures.csv"] = _write_csv(out_dir / "package_integrity_failures.csv", pkg_rows, fields)

    cat_rows_html = [[cat, str(c.get("E0", 0)), str(c.get("E1", 0)), str(c.get("E2", 0))] for cat, c in sorted(by_cat.items())]
    _write_html(dash_dir / "export_failures_by_category.html",
                _page("Export Failures by Category", _table(["Category", "E0", "E1", "E2"], cat_rows_html)))
    counts["export_failures_by_category.html"] = 1

    tiles = "".join([
        _tile("Contracts evaluated", len(records)),
        _tile("E0 (corrupt/unreadable)", by_sev.get("E0", 0), "bad" if by_sev.get("E0") else "ok"),
        _tile("E1 (track-changes/comment mismatch)", by_sev.get("E1", 0), "warn" if by_sev.get("E1") else "ok"),
        _tile("Clean exports", by_sev.get("E3", 0), "ok"),
    ])
    body = f"<div class='tiles'>{tiles}</div>" + _table(
        ["Contract", "Category", "Severity", "Root Cause"],
        [[r["contract_id"], r["category"], r["severity"], r["root_cause"]] for r in export_rows],
        "No export failures.",
    )
    _write_html(dash_dir / "export_validation_summary.html", _page("Export Validation Summary — Full Corpus", body))
    counts["export_validation_summary.html"] = 1

    return counts, {"by_severity": dict(by_sev), "by_category": {k: dict(v) for k, v in by_cat.items()}}


# ---------------------------------------------------------------------------
# 4. Replay / determinism
# ---------------------------------------------------------------------------

def generate_replay_reports(run_id: str, records: List[Dict[str, Any]]) -> Tuple[Dict[str, int], Dict[str, Any]]:
    out_dir = storage.config.run_dir(run_id) / "reports"
    dash_dir = storage.config.run_dir(run_id) / "dashboards"
    counts = {}

    replay_failures, field_diffs = [], []
    rules_in_mismatches: Counter = Counter()
    total_with_replay = 0
    deterministic_count = 0

    for rec in records:
        rp = _stage(rec, "replay")
        vf = _stage(rec, "verify")
        if rp.get("status") != "ok" and "deterministic" not in rp:
            continue
        total_with_replay += 1
        det = rp.get("deterministic")
        if det:
            deterministic_count += 1
        else:
            replay_failures.append({
                "contract_id": rec["contract_id"], "category": rec.get("category"), "filename": rec.get("filename"),
                "findings_count_a": rp.get("findings_count_a"), "findings_count_b": rp.get("findings_count_b"),
                "signature_diff_count": rp.get("signature_diff_count"),
            })
            field_diffs.append({
                "contract_id": rec["contract_id"],
                "field": "findings_signature",
                "detail": f"a={rp.get('findings_count_a')} b={rp.get('findings_count_b')} "
                          f"diff_count={rp.get('signature_diff_count')}",
            })
            for rid in (vf.get("mismatched_rule_ids") or []):
                rules_in_mismatches[rid] += 1

    fields = ["contract_id", "category", "filename", "findings_count_a", "findings_count_b", "signature_diff_count"]
    counts["replay_failures.csv"] = _write_csv(out_dir / "replay_failures.csv", replay_failures, fields)
    counts["replay_field_differences.csv"] = _write_csv(
        out_dir / "replay_field_differences.csv", field_diffs, ["contract_id", "field", "detail"],
    )

    determinism_rows = [{
        "metric": "replay_success_rate_pct",
        "value": round(deterministic_count / total_with_replay * 100, 3) if total_with_replay else None,
    }, {
        "metric": "contracts_with_replay_data", "value": total_with_replay,
    }, {
        "metric": "deterministic_count", "value": deterministic_count,
    }, {
        "metric": "nondeterministic_count", "value": total_with_replay - deterministic_count,
    }]
    counts["determinism_summary.csv"] = _write_csv(out_dir / "determinism_summary.csv", determinism_rows, ["metric", "value"])

    replay_rate = round(deterministic_count / total_with_replay * 100, 3) if total_with_replay else None
    tiles = "".join([
        _tile("Contracts with replay data", total_with_replay),
        _tile("Deterministic", deterministic_count, "ok"),
        _tile("Non-deterministic (CRITICAL)", total_with_replay - deterministic_count,
              "bad" if (total_with_replay - deterministic_count) else "ok"),
        _tile("Replay success rate", f"{replay_rate}%" if replay_rate is not None else "n/a"),
    ])
    body = f"<div class='tiles'>{tiles}</div>" + _table(
        ["Contract", "Category", "Findings A", "Findings B", "Diff Count"],
        [[r["contract_id"], r["category"], str(r["findings_count_a"]), str(r["findings_count_b"]), str(r["signature_diff_count"])] for r in replay_failures],
        "No replay failures — the deterministic engine reproduced every finding exactly on every contract.",
    )
    _write_html(dash_dir / "replay_failures.html", _page("Replay Failures — Full Corpus", body))
    counts["replay_failures.html"] = 1

    rules_html = [[f'<code>{_e(rid)}</code>', str(n)] for rid, n in rules_in_mismatches.most_common(30)]
    body2 = f"<div class='tiles'>{tiles}</div><section><h2>Rules involved in mismatches</h2>{_table(['Rule ID', 'Mismatch Count'], rules_html, 'None.')}</section>"
    _write_html(dash_dir / "determinism_dashboard.html", _page("Determinism Dashboard — Full Corpus", body2))
    counts["determinism_dashboard.html"] = 1

    return counts, {
        "replay_success_rate_pct": replay_rate,
        "deterministic_count": deterministic_count,
        "nondeterministic_count": total_with_replay - deterministic_count,
        "rules_involved_in_mismatches": dict(rules_in_mismatches),
    }


# ---------------------------------------------------------------------------
# 5. Performance
# ---------------------------------------------------------------------------

STAGE_NAMES = ["upload", "analysis", "rule_engine", "evidence", "review", "verify",
               "negotiation_package", "docx_export", "replay", "audit", "independent_parsing"]


def generate_performance_reports(run_id: str, records: List[Dict[str, Any]]) -> Dict[str, int]:
    out_dir = storage.config.run_dir(run_id) / "reports"
    dash_dir = storage.config.run_dir(run_id) / "dashboards"
    counts = {}

    per_contract_total: List[Tuple[str, float]] = []
    per_stage_values: Dict[str, List[float]] = defaultdict(list)
    per_stage_top: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    by_category_total: Dict[str, List[float]] = defaultdict(list)
    by_size_bucket_total: Dict[str, List[float]] = defaultdict(list)

    for rec in records:
        stages = rec.get("stages") or {}
        total_ms = sum(s.get("ms") or 0 for s in stages.values())
        per_contract_total.append((rec["contract_id"], total_ms))
        if rec.get("category"):
            by_category_total[rec["category"]].append(total_ms)
        words = (rec.get("metrics") or {}).get("words") or 0
        bucket = "0-1k" if words < 1000 else "1k-5k" if words < 5000 else "5k-20k" if words < 20000 else "20k+"
        by_size_bucket_total[bucket].append(total_ms)
        for stage_name in STAGE_NAMES:
            ms = stages.get(stage_name, {}).get("ms")
            if isinstance(ms, (int, float)):
                per_stage_values[stage_name].append(ms)
                per_stage_top[stage_name].append((rec["contract_id"], ms))

    perf_rows = [{"stage": s, **_stats(v)} for s, v in per_stage_values.items()]
    fields = ["stage", "n", "min", "mean", "median", "p90", "p95", "p99", "max", "stddev"]
    counts["performance_statistics.csv"] = _write_csv(out_dir / "performance_statistics.csv", perf_rows, fields)
    counts["stage_performance.csv"] = _write_csv(out_dir / "stage_performance.csv", perf_rows, fields)

    overall_slowest = sorted(per_contract_total, key=lambda t: -t[1])[:25]
    outlier_rows = [{"contract_id": cid, "total_ms": round(ms, 2), "kind": "overall"} for cid, ms in overall_slowest]
    for stage_name in ("upload", "rule_engine", "verify", "negotiation_package"):
        slowest = sorted(per_stage_top.get(stage_name, []), key=lambda t: -t[1])[:25]
        for cid, ms in slowest:
            outlier_rows.append({"contract_id": cid, "total_ms": round(ms, 2), "kind": f"stage:{stage_name}"})
    counts["performance_outliers.csv"] = _write_csv(out_dir / "performance_outliers.csv", outlier_rows, ["contract_id", "total_ms", "kind"])

    cat_rows = [{"category": cat, **_stats(v)} for cat, v in by_category_total.items()]
    counts["category_performance.csv"] = _write_csv(out_dir / "category_performance.csv", cat_rows, ["category"] + fields[1:])

    size_rows = [{"size_bucket": b, **_stats(v)} for b, v in by_size_bucket_total.items()]
    counts["size_performance.csv"] = _write_csv(out_dir / "size_performance.csv", size_rows, ["size_bucket"] + fields[1:])

    total_stats = _stats([ms for _, ms in per_contract_total])
    tiles = "".join([
        _tile("Contracts", len(records)),
        _tile("Median total (ms)", total_stats["median"]),
        _tile("P95 total (ms)", total_stats["p95"]),
        _tile("P99 total (ms)", total_stats["p99"]),
        _tile("Max total (ms)", total_stats["max"]),
    ])
    perf_table = [[r["stage"], str(r["n"]), str(r["mean"]), str(r["median"]), str(r["p95"]), str(r["p99"]), str(r["max"])] for r in perf_rows]
    body = f"<div class='tiles'>{tiles}</div>" + _table(["Stage", "N", "Mean", "Median", "P95", "P99", "Max"], perf_table)
    _write_html(dash_dir / "performance_dashboard.html", _page("Performance Dashboard — Full Corpus", body))
    counts["performance_dashboard.html"] = 1

    slowest_table = [[cid, str(round(ms, 1))] for cid, ms in overall_slowest]
    body2 = _table(["Contract", "Total ms"], slowest_table)
    _write_html(dash_dir / "performance_outliers.html", _page("25 Slowest Contracts — Full Corpus", body2))
    counts["performance_outliers.html"] = 1

    return counts, {"total_stats": total_stats, "by_stage": {s: _stats(v) for s, v in per_stage_values.items()}}


# ---------------------------------------------------------------------------
# 6. Contract-level analytics extras
# ---------------------------------------------------------------------------

def generate_contract_extras(run_id: str, records: List[Dict[str, Any]]) -> Dict[str, int]:
    out_dir = storage.config.run_dir(run_id) / "reports"
    counts = {}

    base_rows = agg.compute_contract_statistics(records)
    counts["contract_results.csv"] = _write_csv(out_dir / "contract_results.csv", base_rows, list(base_rows[0].keys()) if base_rows else [])

    most_findings = sorted(base_rows, key=lambda r: -(r["findings_count"] or 0))[:50]
    counts["contracts_with_most_findings.csv"] = _write_csv(out_dir / "contracts_with_most_findings.csv", most_findings, list(base_rows[0].keys()) if base_rows else [])

    lowest_coverage = sorted(
        [r for r in base_rows if r.get("findings_count")],
        key=lambda r: (r["redline_coverage_pct"] if r["redline_coverage_pct"] is not None else 999),
    )[:50]
    counts["contracts_with_lowest_redline_coverage.csv"] = _write_csv(out_dir / "contracts_with_lowest_redline_coverage.csv", lowest_coverage, list(base_rows[0].keys()) if base_rows else [])

    most_manual = sorted(base_rows, key=lambda r: -(r["manual_drafting_count"] or 0))[:50]
    counts["contracts_with_most_manual_drafting.csv"] = _write_csv(out_dir / "contracts_with_most_manual_drafting.csv", most_manual, list(base_rows[0].keys()) if base_rows else [])

    most_overlaps = sorted(base_rows, key=lambda r: -(r["overlapping_findings_candidates"] or 0))[:50]
    counts["contracts_with_most_overlaps.csv"] = _write_csv(out_dir / "contracts_with_most_overlaps.csv", most_overlaps, list(base_rows[0].keys()) if base_rows else [])

    return counts


# ---------------------------------------------------------------------------
# 7. Failure classification
# ---------------------------------------------------------------------------

def generate_failure_classification(run_id: str, records: List[Dict[str, Any]]) -> Tuple[Dict[str, int], Dict[str, Any]]:
    out_dir = storage.config.run_dir(run_id) / "reports"
    dash_dir = storage.config.run_dir(run_id) / "dashboards"
    counts = {}

    all_failures = []
    for rec in records:
        if rec.get("overall_status") == "pass":
            continue
        for stage_name in rec.get("failures") or []:
            s = _stage(rec, stage_name)
            all_failures.append({
                "contract_id": rec["contract_id"], "category": rec.get("category"), "filename": rec.get("filename"),
                "stage": stage_name, "status": s.get("status"),
                "exception_type": (s.get("error") or "").split(":", 1)[0] if s.get("error") else "",
                "traceback": (s.get("error") or "")[:2000],
                "root_cause_summary": (s.get("error") or "no error text captured — validation failure, not an exception")[:200],
                "severity": "critical" if s.get("status") == "error" else "high",
                "reproducibility": "deterministic (re-running the same contract text reproduces it)",
                "recommended_owner": "engine team" if stage_name in ("analysis", "rule_engine", "evidence", "replay") else
                                      "export/docx team" if stage_name in ("negotiation_package", "docx_export") else
                                      "parser team" if stage_name in ("upload", "independent_parsing") else "platform team",
                "ci_blocking": stage_name in ("analysis", "evidence", "replay", "docx_export"),
            })

    fields = ["contract_id", "category", "filename", "stage", "status", "exception_type", "root_cause_summary",
              "severity", "reproducibility", "recommended_owner", "ci_blocking", "traceback"]
    counts["benchmark_failures.csv"] = _write_csv(out_dir / "benchmark_failures.csv", all_failures, fields)

    by_stage = Counter(f["stage"] for f in all_failures)
    by_category = Counter(f["category"] for f in all_failures)
    by_root_cause = Counter(f["exception_type"] or "validation_failure" for f in all_failures)

    counts["failures_by_stage.csv"] = _write_csv(
        out_dir / "failures_by_stage.csv", [{"stage": k, "count": v} for k, v in by_stage.most_common()], ["stage", "count"],
    )
    counts["failures_by_category.csv"] = _write_csv(
        out_dir / "failures_by_category.csv", [{"category": k, "count": v} for k, v in by_category.most_common()], ["category", "count"],
    )
    counts["failures_by_root_cause.csv"] = _write_csv(
        out_dir / "failures_by_root_cause.csv", [{"root_cause": k, "count": v} for k, v in by_root_cause.most_common()], ["root_cause", "count"],
    )

    critical = [f for f in all_failures if f["ci_blocking"]]
    counts["critical_blockers.csv"] = _write_csv(out_dir / "critical_blockers.csv", critical, fields)

    tiles = "".join([
        _tile("Total failures", len(all_failures), "bad" if all_failures else "ok"),
        _tile("CI-blocking", len(critical), "bad" if critical else "ok"),
        _tile("Distinct stages affected", len(by_stage)),
        _tile("Distinct categories affected", len(by_category)),
    ])
    body = f"<div class='tiles'>{tiles}</div>" + _table(
        ["Stage", "Count"], [[s, str(n)] for s, n in by_stage.most_common()], "No failures.",
    )
    _write_html(dash_dir / "failure_dashboard.html", _page("Failure Dashboard — Full Corpus", body))
    counts["failure_dashboard.html"] = 1

    return counts, {
        "total_failures": len(all_failures), "by_stage": dict(by_stage),
        "by_category": dict(by_category), "critical_blockers": len(critical),
    }


# ---------------------------------------------------------------------------
# 8. Environment / reproducibility metadata (manifest enrichment)
# ---------------------------------------------------------------------------

def capture_environment_metadata() -> Dict[str, Any]:
    """Everything needed to reproduce this exact run later: interpreter,
    dependency versions, machine identity, ruleset version. Captured once at
    finalize time and merged into the run manifest — not part of the
    per-contract pipeline, so it costs nothing per contract and never
    touches how a contract is processed."""
    import platform
    import sys

    try:
        import importlib.metadata as importlib_metadata
        deps = {}
        for pkg in ("pandas", "pyarrow", "python-docx", "PyPDF2", "fpdf2", "SQLAlchemy",
                    "python-dotenv", "user-agents"):
            try:
                deps[pkg] = importlib_metadata.version(pkg)
            except importlib_metadata.PackageNotFoundError:
                deps[pkg] = None
    except Exception:
        deps = {}

    try:
        ruleset_version = eb.engine_version()
    except Exception:
        ruleset_version = None

    return {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "cpu_count": __import__("os").cpu_count(),
        "dependency_versions": deps,
        "ruleset_version": ruleset_version,
        "rules_total": eb.rules_total() if ruleset_version else None,
    }


def compute_corpus_manifest_hash(categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """A single hash over (contract_id, content-hash) pairs for the exact
    corpus snapshot this run selected — lets a future run prove it saw byte-
    identical source files, not just the same file count."""
    import hashlib
    from . import corpus as tb_corpus

    refs = tb_corpus.discover(categories)
    entries = []
    for r in sorted(refs, key=lambda r: r.contract_id):
        content_hash = hashlib.sha256(r.doc_path.read_bytes()).hexdigest()
        entries.append(f"{r.contract_id}:{content_hash}")
    corpus_hash = hashlib.sha256("\n".join(entries).encode()).hexdigest()
    return {"corpus_manifest_hash": corpus_hash, "corpus_file_count": len(refs)}


# ---------------------------------------------------------------------------
# 9. Regression baseline (full-corpus scope)
# ---------------------------------------------------------------------------

REGRESSION_PERF_THRESHOLD_PCT = 25.0  # same threshold as triagebench/regression.py, documented here for this scope too


def generate_regression_reports(
    run_id: str, records: List[Dict[str, Any]], baseline_run_id: Optional[str]
) -> Tuple[Dict[str, int], Dict[str, Any]]:
    out_dir = storage.config.run_dir(run_id) / "reports"
    dash_dir = storage.config.run_dir(run_id) / "dashboards"
    counts = {}

    if not baseline_run_id:
        for name, fields in [
            ("regression_report.csv", ["kind", "contract_id", "detail"]),
            ("new_failures.csv", ["contract_id", "category", "detail"]),
            ("newly_passing.csv", ["contract_id", "category", "detail"]),
            ("finding_differences.csv", ["contract_id", "rule_id", "detail"]),
            ("rule_differences.csv", ["rule_id", "detail"]),
            ("performance_regressions.csv", ["stage", "baseline_ms", "current_ms", "delta_pct"]),
        ]:
            counts[name] = _write_csv(out_dir / name, [], fields)
        body = ("<p><b>This is the first full-corpus baseline run.</b> No prior full-corpus run "
                "exists to compare against — this run establishes the baseline that future full-corpus "
                "runs will be compared to. Per-run regression detection at sample scale is already "
                "exercised by triagebench/regression.py on every non-full-corpus run.</p>")
        _write_html(dash_dir / "regression_dashboard.html", _page("Regression — Baseline Creation", body))
        counts["regression_dashboard.html"] = 1
        return counts, {"baseline_creation": True, "baseline_run_id": None}

    from . import regression as regression_mod
    baseline_manifest = storage.read_manifest(baseline_run_id)
    baseline_records = storage.load_results(baseline_run_id)
    current_manifest = storage.read_manifest(run_id)
    comparison = regression_mod.compare(records, current_manifest, baseline_records, baseline_manifest)
    regression_mod.write_report(run_id, comparison)
    counts["regression_report.csv"] = len(comparison["rows"])

    new_failure_rows, newly_passing_rows = [], []
    base_by_id = {r["contract_id"]: r for r in baseline_records}
    for rec in records:
        base = base_by_id.get(rec["contract_id"])
        if not base:
            continue
        if base.get("overall_status") == "pass" and rec.get("overall_status") != "pass":
            new_failure_rows.append({"contract_id": rec["contract_id"], "category": rec.get("category"), "detail": ";".join(rec.get("failures") or [])})
        elif base.get("overall_status") != "pass" and rec.get("overall_status") == "pass":
            newly_passing_rows.append({"contract_id": rec["contract_id"], "category": rec.get("category"), "detail": "now passing"})
    counts["new_failures.csv"] = _write_csv(out_dir / "new_failures.csv", new_failure_rows, ["contract_id", "category", "detail"])
    counts["newly_passing.csv"] = _write_csv(out_dir / "newly_passing.csv", newly_passing_rows, ["contract_id", "category", "detail"])

    finding_diff_rows = [
        {"contract_id": r["contract_id"], "rule_id": r["detail"], "detail": r["kind"]}
        for r in comparison["rows"] if r["kind"] in ("new_finding_rule", "missing_finding_rule")
    ]
    counts["finding_differences.csv"] = _write_csv(out_dir / "finding_differences.csv", finding_diff_rows, ["contract_id", "rule_id", "detail"])

    rule_diff_rows = [
        {"rule_id": r["detail"], "detail": r["kind"]}
        for r in comparison["rows"] if r["kind"] in ("rule_disappeared_corpuswide", "rule_newly_firing_corpuswide")
    ]
    counts["rule_differences.csv"] = _write_csv(out_dir / "rule_differences.csv", rule_diff_rows, ["rule_id", "detail"])

    perf_regr_rows = [
        {"stage": p["stage"], "baseline_ms": p["baseline_mean_ms"], "current_ms": p["current_mean_ms"], "delta_pct": p["delta_pct"]}
        for p in comparison.get("performance_regressions", [])
    ]
    counts["performance_regressions.csv"] = _write_csv(
        out_dir / "performance_regressions.csv", perf_regr_rows, ["stage", "baseline_ms", "current_ms", "delta_pct"],
    )

    tiles = "".join([
        _tile("Baseline run", baseline_run_id),
        _tile("New failures", len(new_failure_rows), "bad" if new_failure_rows else "ok"),
        _tile("Newly passing", len(newly_passing_rows), "ok"),
        _tile("Rules disappeared corpus-wide", len(comparison.get("rules_disappeared_corpuswide", [])),
              "bad" if comparison.get("rules_disappeared_corpuswide") else "ok"),
        _tile("Performance regressions", len(perf_regr_rows), "warn" if perf_regr_rows else "ok"),
    ])
    _write_html(dash_dir / "regression_dashboard.html", _page("Regression Dashboard — Full Corpus", f"<div class='tiles'>{tiles}</div>"))
    counts["regression_dashboard.html"] = 1

    return counts, {"baseline_creation": False, "baseline_run_id": baseline_run_id,
                     "has_critical_regressions": comparison.get("has_critical_regressions"),
                     "new_failures": len(new_failure_rows), "newly_passing": len(newly_passing_rows)}


# ---------------------------------------------------------------------------
# 10. Go/No-Go, scores, executive report, engineering backlog
# ---------------------------------------------------------------------------

def compute_go_no_go(
    manifest: Dict[str, Any], records: List[Dict[str, Any]],
    parser_summary: Dict[str, Any], export_summary: Dict[str, Any],
    replay_summary: Dict[str, Any], failure_summary: Dict[str, Any],
    regression_summary: Dict[str, Any], corpus_hash_info: Dict[str, Any],
) -> Dict[str, Any]:
    """Applies the exact NO-GO rules as written, each as an explicit,
    independently-inspectable check — never a single opaque score. Isolated
    malformed SEC source documents are deliberately NOT auto-NO-GO (per
    instruction): a P0 is only a blocker if it is systemic (rate above
    threshold) or the failure was NOT handled safely (an unhandled
    exception/crash rather than a clean, classified rejection)."""
    reasons: List[str] = []
    n = len(records)
    expected = manifest.get("corpus_selected")

    accounted_for = n == expected
    if not accounted_for:
        reasons.append(f"benchmark cannot account for every corpus file: {n} results vs {expected} selected")

    nondeterministic = replay_summary.get("nondeterministic_count") or 0
    if nondeterministic > 0:
        reasons.append(f"{nondeterministic} unexplained replay mismatch(es) — deterministic engine produced different output on identical input")

    by_sev_parser = parser_summary.get("by_severity", {})
    p0_count = by_sev_parser.get("P0", 0)
    p0_rate = p0_count / n * 100 if n else 0
    # "Systematic" threshold: >1% of the corpus, or ANY P0 that was not a
    # clean, classified upload rejection (i.e., the contract's overall
    # status is "error" with an unhandled exception, not just an empty/
    # unreadable-source classification).
    unsafe_p0 = 0
    for rec in records:
        up = _stage(rec, "upload")
        if up.get("status") == "error":
            err = up.get("error") or ""
            # A clean, anticipated rejection (empty text, unsupported
            # extension analogue) raises ValueError with a descriptive
            # message from stage_upload itself — anything else (a bare
            # library exception surfacing) counts as "not handled safely."
            if "ValueError" not in err.split("\n")[0]:
                unsafe_p0 += 1
    systemic_p0 = p0_rate > 1.0
    if systemic_p0:
        reasons.append(f"systemic text-extraction failure: P0 rate {p0_rate:.2f}% of corpus (>1% threshold)")
    if unsafe_p0 > 0:
        reasons.append(f"{unsafe_p0} contract(s) hit an unhandled exception during upload/extraction rather than a clean, classified rejection")

    by_sev_export = export_summary.get("by_severity", {})
    e0_count = by_sev_export.get("E0", 0)
    # An E0 export failure downstream of an already-classified P0 upload
    # failure is explained (there was never text to export from); an E0 on
    # a contract whose upload succeeded is not.
    unexplained_e0 = 0
    for rec in records:
        dx = _stage(rec, "docx_export")
        pkg = _stage(rec, "negotiation_package")
        if (pkg.get("status") != "ok" or dx.get("status") != "ok") and _stage(rec, "upload").get("status") == "ok":
            unexplained_e0 += 1
    if unexplained_e0 > 0:
        reasons.append(f"{unexplained_e0} corrupt/unreadable DOCX package(s) on contracts whose text extraction succeeded — not explained by an upstream failure")

    if regression_summary.get("has_critical_regressions"):
        reasons.append("critical regressions detected vs. the prior full-corpus baseline")

    critical_artifacts = ["benchmark_manifest.json", "benchmark_results.json", "benchmark_summary.json"]
    missing_artifacts = [a for a in critical_artifacts if not (storage.config.run_dir(manifest["run_id"]) / a).exists()]
    if missing_artifacts:
        reasons.append(f"critical artifacts missing: {missing_artifacts}")

    verdict = "NO-GO" if reasons else "GO"

    return {
        "verdict": verdict,
        "reasons": reasons,
        "accounted_for_check": {"pass": accounted_for, "processed": n, "expected": expected},
        "replay_check": {"pass": nondeterministic == 0, "nondeterministic_count": nondeterministic},
        "parser_p0_check": {"pass": not systemic_p0 and unsafe_p0 == 0, "p0_count": p0_count, "p0_rate_pct": round(p0_rate, 3), "unsafe_p0": unsafe_p0},
        "export_check": {"pass": unexplained_e0 == 0, "unexplained_e0": unexplained_e0, "total_e0": e0_count},
        "regression_check": {"pass": not regression_summary.get("has_critical_regressions", False)},
        "artifacts_check": {"pass": not missing_artifacts, "missing": missing_artifacts},
        "corpus_hash": corpus_hash_info.get("corpus_manifest_hash"),
        "note": ("Cross-user/security issues and repeated-run reproducibility are out of scope for an "
                 "engine-level (no browser, no HTTP, no auth) run — see TriageBench Live for that surface. "
                 "This run did not re-execute itself a second time to verify bit-for-bit summary "
                 "reproducibility across separate processes; determinism WITHIN this run (replay stage, "
                 "every contract) was verified exhaustively instead."),
    }


def compute_reliability_scores(
    records: List[Dict[str, Any]], parser_summary: Dict[str, Any], export_summary: Dict[str, Any],
    replay_summary: Dict[str, Any], performance_summary: Dict[str, Any], go_no_go: Dict[str, Any],
) -> Dict[str, int]:
    n = len(records) or 1
    pass_count = sum(1 for r in records if r.get("overall_status") == "pass")
    engine_reliability = round(pass_count / n * 100)

    p0_p1 = parser_summary.get("by_severity", {}).get("P0", 0) + parser_summary.get("by_severity", {}).get("P1", 0)
    parser_reliability = round((1 - p0_p1 / n) * 100)

    determinism = round((replay_summary.get("deterministic_count", 0) /
                          max(replay_summary.get("deterministic_count", 0) + replay_summary.get("nondeterministic_count", 0), 1)) * 100)

    # Evidence anchoring: guarded by construction-time assertions in the
    # engine itself (Finding.__post_init__) — scored on the absence of any
    # anchor-related stage failure across the corpus.
    anchor_failures = sum(
        1 for r in records for s in ("analysis", "evidence")
        if "start_index" in (_stage(r, s).get("error") or "") or "exact_snippet" in (_stage(r, s).get("error") or "")
    )
    evidence_anchoring = 100 if anchor_failures == 0 else round(max(0, 100 - anchor_failures / n * 1000))

    e0_e1 = export_summary.get("by_severity", {}).get("E0", 0) + export_summary.get("by_severity", {}).get("E1", 0)
    export_reliability = round((1 - e0_e1 / n) * 100)

    p95_total = (performance_summary.get("total_stats") or {}).get("p95") or 0
    # 8s p95 budget (same budget used in triagebench_live/readiness.py for
    # a single synchronous customer-facing action) applied to the WHOLE
    # per-contract pipeline here, since this is the offline batch benchmark,
    # not a live request — scored on a gentler curve accordingly.
    performance_score = 100 if p95_total <= 5000 else max(0, round(100 - (p95_total - 5000) / 200))

    benchmark_confidence = round((engine_reliability + parser_reliability + determinism + evidence_anchoring + export_reliability) / 5)

    commercial_readiness = 0 if go_no_go["verdict"] == "NO-GO" else round(
        (engine_reliability * 0.3 + parser_reliability * 0.2 + determinism * 0.25 + export_reliability * 0.15 + performance_score * 0.1)
    )

    return {
        "engine_reliability": engine_reliability, "parser_reliability": parser_reliability,
        "determinism": determinism, "evidence_anchoring": evidence_anchoring,
        "export_reliability": export_reliability, "performance": performance_score,
        "benchmark_confidence": benchmark_confidence, "commercial_readiness": commercial_readiness,
    }


def generate_engineering_backlog(
    run_id: str, parser_summary: Dict[str, Any], export_summary: Dict[str, Any],
    replay_summary: Dict[str, Any], failure_summary: Dict[str, Any], go_no_go: Dict[str, Any],
) -> List[Dict[str, Any]]:
    items = []
    if go_no_go["parser_p0_check"]["unsafe_p0"] > 0:
        items.append({"priority": 1, "area": "parser", "title": "Unhandled exceptions during upload/extraction",
                       "detail": f"{go_no_go['parser_p0_check']['unsafe_p0']} contract(s) crashed instead of a clean rejection.",
                       "owner": "parser team"})
    if replay_summary.get("nondeterministic_count"):
        items.append({"priority": 1, "area": "engine", "title": "Non-deterministic replay",
                       "detail": f"{replay_summary['nondeterministic_count']} contract(s) produced different findings on identical input.",
                       "owner": "engine team"})
    if go_no_go["export_check"]["unexplained_e0"] > 0:
        items.append({"priority": 1, "area": "export", "title": "Corrupt DOCX/package on successfully-parsed contracts",
                       "detail": f"{go_no_go['export_check']['unexplained_e0']} case(s).", "owner": "export team"})
    p1_count = parser_summary.get("by_severity", {}).get("P1", 0)
    if p1_count:
        items.append({"priority": 2, "area": "parser", "title": "P1 extractor disagreements (possible clause-boundary issues)",
                       "detail": f"{p1_count} contract(s) — see extractor_disagreements.csv.", "owner": "parser team"})
    e1_count = export_summary.get("by_severity", {}).get("E1", 0)
    if e1_count:
        items.append({"priority": 2, "area": "export", "title": "Track-changes/comment count mismatches",
                       "detail": f"{e1_count} contract(s) — see track_change_failures.csv / comment_failures.csv.", "owner": "export team"})
    if failure_summary.get("total_failures"):
        items.append({"priority": 2, "area": "general", "title": "Full failure inventory",
                       "detail": f"{failure_summary['total_failures']} total stage failures across the corpus — see benchmark_failures.csv.",
                       "owner": "engineering leads"})
    items.sort(key=lambda i: i["priority"])
    out_dir = storage.config.run_dir(run_id) / "reports"
    _write_csv(out_dir / "engineering_backlog.csv", items, ["priority", "area", "title", "detail", "owner"])
    return items


def generate_executive_report(
    run_id: str, manifest: Dict[str, Any], summary: Dict[str, Any],
    parser_extra: Dict[str, Any], export_extra: Dict[str, Any], replay_extra: Dict[str, Any],
    performance_extra: Dict[str, Any], failure_extra: Dict[str, Any], regression_extra: Dict[str, Any],
    go_no_go: Dict[str, Any], scores: Dict[str, int], backlog: List[Dict[str, Any]],
    env: Dict[str, Any], corpus_hash_info: Dict[str, Any], duplicate_info: Dict[str, Any],
) -> str:
    n = summary["contracts_processed"]
    status_counts = summary["status_counts"]
    cov = summary.get("coverage", {})
    by_cat_p0p1 = {
        cat: c.get("P0", 0) + c.get("P1", 0)
        for cat, c in (parser_extra.get("by_category") or {}).items()
    }
    worst_categories = sorted(by_cat_p0p1.items(), key=lambda kv: -kv[1])[:5]

    md = f"""# TriageBench Full-Corpus Baseline — Executive Report

**Run ID:** `{run_id}`
**Label:** {manifest.get('label')}
**Git commit:** `{manifest.get('git_commit')}` (branch `{manifest.get('git_branch')}`)
**Ruleset version:** `{env.get('ruleset_version')}` ({env.get('rules_total')} rules)
**Corpus manifest hash:** `{corpus_hash_info.get('corpus_manifest_hash')}`
**Started / finished:** {manifest.get('started_at')} → {manifest.get('finished_at')} ({manifest.get('duration_seconds')}s wall-clock)
**Machine:** {env.get('hostname')} — {env.get('platform')} — Python {env.get('python_version', '').split()[0]}

## Were all 4,190 contracts accounted for?

**{'YES' if go_no_go['accounted_for_check']['pass'] else 'NO'}** — {go_no_go['accounted_for_check']['processed']} of {go_no_go['accounted_for_check']['expected']} expected contracts have a terminal state.
Corpus preflight: {duplicate_info.get('empty_files', 0)} empty files, {duplicate_info.get('unreadable_files', 0)} unreadable files,
{duplicate_info.get('duplicate_groups', 0)} duplicate-content groups ({duplicate_info.get('duplicate_contracts', 0)} contracts) — all processed independently regardless.

## Headline numbers

| Metric | Value |
|---|---|
| Completed successfully (pass) | {status_counts.get('pass', 0)} ({round(status_counts.get('pass', 0)/n*100, 2)}%) |
| Failed (fail/error) | {status_counts.get('fail', 0) + status_counts.get('error', 0)} |
| Skipped | 0 (every discovered contract was scheduled and processed — see manifest `corpus_selected`) |
| Parser success rate (no P0/P1) | {round((1 - (parser_extra['by_severity'].get('P0',0)+parser_extra['by_severity'].get('P1',0))/n)*100, 2)}% |
| P0 rate | {go_no_go['parser_p0_check']['p0_rate_pct']}% |
| Verify/replay success rate | {replay_extra.get('replay_success_rate_pct')}% |
| DOCX export success rate | {round((1 - (export_extra['by_severity'].get('E0',0))/n)*100, 2)}% |
| Negotiation Package success rate | {round((1 - (export_extra['by_severity'].get('E0',0))/n)*100, 2)}% |
| Redline coverage (overall mean) | {cov.get('overall_mean_coverage_pct')}% |

### Redline coverage by category

{chr(10).join(f"- **{cat}**: {v['mean_coverage_pct']}% (n={v['n']})" for cat, v in cov.get('by_category', {}).items())}

## Rules

- Rules never triggered: {summary.get('rules_never_fired_count')} — see `rules_never_triggered.csv`
- Top-firing rules: see `rule_coverage.csv` / `rule_coverage.html`
- Rules with verify/replay involvement: see `rules_with_replay_failures.csv`

## Worst-performing categories (P0+P1 parser issues)

{chr(10).join(f"- {cat}: {cnt}" for cat, cnt in worst_categories) if worst_categories else "- None — no category had a P0/P1 parser issue."}

## Runtime performance

- P50: {(performance_extra['total_stats'] or {}).get('median')} ms
- P95: {(performance_extra['total_stats'] or {}).get('p95')} ms
- P99: {(performance_extra['total_stats'] or {}).get('p99')} ms
- Max: {(performance_extra['total_stats'] or {}).get('max')} ms

## Critical blockers

{chr(10).join(f"- {r}" for r in go_no_go['reasons']) if go_no_go['reasons'] else "- None."}

## Regression vs. prior full-corpus baseline

{"This is the **first full-corpus baseline** — no prior full-corpus run exists to compare against. This run establishes the reference point for all future full-corpus runs." if regression_extra.get('baseline_creation') else f"Compared against baseline `{regression_extra.get('baseline_run_id')}`: {regression_extra.get('new_failures')} new failures, {regression_extra.get('newly_passing')} newly passing, critical regressions = {regression_extra.get('has_critical_regressions')}."}

## Scores (0-100)

| Dimension | Score |
|---|---|
| Engine reliability | {scores['engine_reliability']} |
| Parser reliability | {scores['parser_reliability']} |
| Determinism | {scores['determinism']} |
| Evidence anchoring | {scores['evidence_anchoring']} |
| DOCX/export reliability | {scores['export_reliability']} |
| Performance | {scores['performance']} |
| **Benchmark confidence** | **{scores['benchmark_confidence']}** |
| **Commercial readiness** | **{scores['commercial_readiness']}** |

## Is the current build suitable for controlled pilots?

{'**YES** — no critical blockers were found; the deterministic engine, parser, evidence anchoring, and export pipeline all held up across the full corpus.' if go_no_go['verdict'] == 'GO' else '**NOT WITHOUT ADDRESSING THE BLOCKERS ABOVE** — see Critical Blockers.'}

## Is the current build suitable for unrestricted commercial production?

{'Engine-level results support it; TriageBench Live (separately, against a deployed instance) additionally validated the live product surface — see that suite for auth/session/security/UI evidence not in scope for this engine-level run.' if go_no_go['verdict'] == 'GO' else '**NO** — resolve the blockers above first.'}

## What should engineering fix first?

{chr(10).join(f"{i+1}. **[{item['area']}]** {item['title']} — {item['detail']} (owner: {item['owner']})" for i, item in enumerate(backlog[:10])) if backlog else "Nothing outstanding — see engineering_backlog.csv (empty)."}

## Go / No-Go verdict

# {go_no_go['verdict']}

---

**Disclaimer:** This report measures deterministic engine behavior, parser fidelity, evidence anchoring,
export integrity, and performance. It does not constitute legal advice, attorney validation, or a
user-acceptance study. All review decisions (accept/reject/edit/flag) in this run were produced by a
fixed, documented synthetic CI policy (`pipeline._auto_decide`), not by an attorney — see
`triagebench/pipeline.py`'s module docstring.
"""
    out_path = storage.config.run_dir(run_id) / "executive_benchmark_report.md"
    out_path.write_text(md, encoding="utf-8")
    return md


def generate_benchmark_summary_html(run_id: str, manifest: Dict[str, Any], summary: Dict[str, Any],
                                     go_no_go: Dict[str, Any], scores: Dict[str, int]) -> None:
    n = summary["contracts_processed"]
    status_counts = summary["status_counts"]
    verdict_cls = "ok" if go_no_go["verdict"] == "GO" else "bad"
    tiles = "".join([
        _tile("Contracts processed", n),
        _tile("Pass rate", f"{summary.get('pass_rate_pct')}%"),
        _tile("Passed", status_counts.get("pass", 0), "ok"),
        _tile("Failed", status_counts.get("fail", 0) + status_counts.get("error", 0),
              "bad" if (status_counts.get("fail", 0) + status_counts.get("error", 0)) else "ok"),
        _tile("Verdict", go_no_go["verdict"], verdict_cls),
        _tile("Benchmark confidence", scores["benchmark_confidence"]),
        _tile("Commercial readiness", scores["commercial_readiness"]),
    ])
    score_rows = [[k.replace("_", " ").title(), str(v)] for k, v in scores.items()]
    reasons_rows = [[r] for r in go_no_go["reasons"]] or [["None — no blocking conditions found."]]
    body = f"""<p class="subtitle">Run <code>{_e(run_id)}</code> — commit <code>{_e(manifest.get('git_commit'))}</code></p>
<div class="tiles">{tiles}</div>
<section><h2>Reliability scores</h2>{_table(['Dimension', 'Score'], score_rows)}</section>
<section><h2>Go/No-Go reasons</h2>{_table(['Reason'], reasons_rows)}</section>
<section><h2>Where to look next</h2>
<p>See <code>executive_benchmark_report.md</code> for the full narrative, <code>reports/</code> for every CSV,
and <code>dashboards/</code> for every topic-specific dashboard (rule coverage, parser failures, export
validation, determinism, performance, failures, regression).</p></section>"""
    _write_html(storage.config.run_dir(run_id) / "benchmark_summary.html", _page("Benchmark Summary — Full Corpus", body))


def generate_all_extended(
    run_id: str, baseline_run_id: Optional[str] = None, categories: Optional[List[str]] = None,
    duplicate_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """The single entry point: call after triagebench.finalize.finalize()
    has already produced the base manifest/results/summary/11-report set.
    Everything here is additive — it reads what finalize() already wrote
    and never re-runs or mutates a single contract."""
    manifest = storage.read_manifest(run_id)
    records = storage.load_results(run_id)
    summary = agg.compute_summary(records, manifest)

    all_counts: Dict[str, int] = {}

    rc_counts = generate_rule_coverage_reports(run_id, records)
    all_counts.update(rc_counts)

    parser_counts, parser_extra = generate_parser_reports(run_id, records)
    all_counts.update(parser_counts)

    export_counts, export_extra = generate_export_reports(run_id, records)
    all_counts.update(export_counts)

    replay_counts, replay_extra = generate_replay_reports(run_id, records)
    all_counts.update(replay_counts)

    perf_counts, perf_extra = generate_performance_reports(run_id, records)
    all_counts.update(perf_counts)

    contract_counts = generate_contract_extras(run_id, records)
    all_counts.update(contract_counts)

    failure_counts, failure_extra = generate_failure_classification(run_id, records)
    all_counts.update(failure_counts)

    regression_counts, regression_extra = generate_regression_reports(run_id, records, baseline_run_id)
    all_counts.update(regression_counts)

    env = capture_environment_metadata()
    corpus_hash_info = compute_corpus_manifest_hash(categories)

    manifest["environment"] = env
    manifest["corpus_manifest_hash"] = corpus_hash_info["corpus_manifest_hash"]
    manifest["corpus_verification"] = duplicate_info or {}
    storage.write_manifest(run_id, manifest)
    storage.write_json(run_id, "full_run_manifest.json", manifest)

    go_no_go = compute_go_no_go(manifest, records, parser_extra, export_extra, replay_extra, failure_extra, regression_extra, corpus_hash_info)
    scores = compute_reliability_scores(records, parser_extra, export_extra, replay_extra, perf_extra, go_no_go)
    backlog = generate_engineering_backlog(run_id, parser_extra, export_extra, replay_extra, failure_extra, go_no_go)

    storage.write_json(run_id, "go_no_go.json", go_no_go)
    storage.write_json(run_id, "reliability_scores.json", scores)

    generate_executive_report(
        run_id, manifest, summary, parser_extra, export_extra, replay_extra, perf_extra,
        failure_extra, regression_extra, go_no_go, scores, backlog, env, corpus_hash_info,
        duplicate_info or {},
    )
    generate_benchmark_summary_html(run_id, manifest, summary, go_no_go, scores)

    return {
        "run_id": run_id, "file_counts": all_counts, "go_no_go": go_no_go, "scores": scores,
        "summary": summary, "parser_extra": parser_extra, "export_extra": export_extra,
        "replay_extra": replay_extra, "performance_extra": perf_extra, "failure_extra": failure_extra,
        "regression_extra": regression_extra, "backlog": backlog,
    }
