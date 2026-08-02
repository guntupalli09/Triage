"""
Seven self-contained HTML dashboards — no CDN, no build step, no server.
Every page is a single static file with inlined CSS so `open
triagebench_runs/<run>/dashboards/overview.html` in a browser just works,
including on a laptop with no network access and in CI artifact viewers.
"""
from __future__ import annotations

import html as htmllib
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import aggregate as agg
from . import storage

_CSS = """
:root { color-scheme: light dark; }
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 2rem;
       background: #0b0d12; color: #e6e8ee; }
@media (prefers-color-scheme: light) { body { background: #f7f8fa; color: #1a1d24; } }
h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
.subtitle { color: #8a90a2; margin-bottom: 1.5rem; }
nav { display: flex; gap: 0.75rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
nav a { color: #7aa2ff; text-decoration: none; font-size: 0.85rem; padding: 0.35rem 0.7rem;
        border: 1px solid #2a2f3d; border-radius: 6px; }
nav a.active { background: #7aa2ff; color: #0b0d12; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; margin-bottom: 2rem; }
.tile { background: #151822; border: 1px solid #262b3a; border-radius: 10px; padding: 1rem; }
@media (prefers-color-scheme: light) { .tile { background: #fff; border-color: #e3e5ea; }
  nav a { border-color: #d7dae0; } }
.tile .val { font-size: 1.6rem; font-weight: 700; }
.tile .lbl { font-size: 0.78rem; color: #8a90a2; text-transform: uppercase; letter-spacing: 0.04em; }
.ok { color: #33d17a; } .warn { color: #f5c04a; } .bad { color: #ff6b6b; }
table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; font-size: 0.85rem; }
th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #262b3a; }
@media (prefers-color-scheme: light) { th, td { border-color: #e3e5ea; } }
th { color: #8a90a2; font-weight: 600; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.03em; }
tr:hover { background: rgba(122,162,255,0.06); }
.bar-track { background: #262b3a; border-radius: 4px; height: 10px; width: 140px; overflow: hidden; display:inline-block; vertical-align:middle;}
@media (prefers-color-scheme: light) { .bar-track { background: #e3e5ea; } }
.bar-fill { background: #7aa2ff; height: 100%; }
section { margin-bottom: 2rem; }
h2 { font-size: 1.1rem; border-bottom: 1px solid #262b3a; padding-bottom: 0.4rem; }
@media (prefers-color-scheme: light) { h2 { border-color: #e3e5ea; } }
code { background: #151822; padding: 0.1rem 0.35rem; border-radius: 4px; }
@media (prefers-color-scheme: light) { code { background: #eef0f4; } }
.empty { color: #8a90a2; font-style: italic; }
"""

_PAGES = [
    ("overview.html", "Overview"),
    ("rule_coverage.html", "Rule Coverage"),
    ("contract_coverage.html", "Contract Coverage"),
    ("performance.html", "Performance"),
    ("redline_quality.html", "Redline Quality"),
    ("manual_drafting.html", "Manual Drafting"),
    ("regressions.html", "Regressions"),
]


def _e(v: Any) -> str:
    return htmllib.escape(str(v)) if v is not None else ""


def _nav(active: str) -> str:
    links = "".join(
        f'<a href="{href}" class="{"active" if href == active else ""}">{label}</a>'
        for href, label in _PAGES
    )
    return f"<nav>{links}</nav>"


def _page(title: str, active: str, body: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>TriageBench — {_e(title)}</title>
<style>{_CSS}</style></head>
<body>
<h1>TriageBench — {_e(title)}</h1>
{_nav(active)}
{body}
</body></html>"""


def _tile(label: str, value: Any, cls: str = "") -> str:
    return f'<div class="tile"><div class="val {cls}">{_e(value)}</div><div class="lbl">{_e(label)}</div></div>'


def _bar(pct: float) -> str:
    pct = max(0.0, min(100.0, pct or 0.0))
    return f'<span class="bar-track"><span class="bar-fill" style="width:{pct:.1f}%"></span></span> {pct:.1f}%'


def _table(headers: List[str], rows: List[List[str]], empty_msg: str = "No data.") -> str:
    if not rows:
        return f'<p class="empty">{_e(empty_msg)}</p>'
    thead = "".join(f"<th>{_e(h)}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{trs}</tbody></table>"


def generate_all(run_id: str, records: List[Dict[str, Any]], manifest: Dict[str, Any],
                  summary: Dict[str, Any], regression: Optional[Dict[str, Any]]) -> None:
    out_dir = storage.config.run_dir(run_id) / "dashboards"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "overview.html").write_text(_overview(records, manifest, summary, regression), encoding="utf-8")
    (out_dir / "rule_coverage.html").write_text(_rule_coverage(records), encoding="utf-8")
    (out_dir / "contract_coverage.html").write_text(_contract_coverage(records), encoding="utf-8")
    (out_dir / "performance.html").write_text(_performance(records, summary), encoding="utf-8")
    (out_dir / "redline_quality.html").write_text(_redline_quality(records, summary), encoding="utf-8")
    (out_dir / "manual_drafting.html").write_text(_manual_drafting(records), encoding="utf-8")
    (out_dir / "regressions.html").write_text(_regressions(regression), encoding="utf-8")


def _overview(records, manifest, summary, regression) -> str:
    status_counts = summary.get("status_counts", {})
    tiles = "".join([
        _tile("Contracts processed", summary.get("contracts_processed", 0)),
        _tile("Pass rate", f"{summary.get('pass_rate_pct', 0)}%",
              "ok" if (summary.get("pass_rate_pct") or 0) >= 99 else "warn"),
        _tile("Passed", status_counts.get("pass", 0), "ok"),
        _tile("Failed", status_counts.get("fail", 0), "warn" if status_counts.get("fail") else ""),
        _tile("Errored", status_counts.get("error", 0), "bad" if status_counts.get("error") else ""),
        _tile("Rules never fired", summary.get("rules_never_fired_count", 0)),
        _tile("Verify failures", summary.get("verify_failures", 0), "bad" if summary.get("verify_failures") else ""),
        _tile("Non-deterministic replays", summary.get("replay_nondeterministic_count", 0),
              "bad" if summary.get("replay_nondeterministic_count") else ""),
        _tile("DOCX failures", summary.get("docx_failures", 0), "bad" if summary.get("docx_failures") else ""),
        _tile("Parser failures", summary.get("parser_failures", 0), "bad" if summary.get("parser_failures") else ""),
        _tile("Mean redline coverage", f"{summary.get('coverage', {}).get('overall_mean_coverage_pct')}%"),
        _tile("Duration", f"{summary.get('duration_seconds', 0)}s"),
    ])

    cat_rows = [
        [cat, str(n)] for cat, n in (manifest.get("corpus_by_category") or {}).items()
    ]
    top_rules_rows = [
        [r["rule_id"], str(r["times_triggered"]), str(r["contracts_triggered_in"])]
        for r in summary.get("top_firing_rules", [])
    ]

    reg_banner = ""
    if regression:
        crit = regression.get("has_critical_regressions")
        reg_banner = f"""<section><h2>Regression vs. baseline {_e(regression.get('baseline_run_id'))}</h2>
        <p class="{'bad' if crit else 'ok'}">
        {'⚠ Critical regressions detected — see regressions.html' if crit else '✓ No critical regressions detected'}
        </p></section>"""
    else:
        reg_banner = '<section><h2>Regression vs. baseline</h2><p class="empty">No baseline run available yet (first run, or run with --no-baseline).</p></section>'

    body = f"""
<div class="tiles">{tiles}</div>
{reg_banner}
<section><h2>Run metadata</h2>
<table><tbody>
<tr><td>Run ID</td><td><code>{_e(manifest.get('run_id'))}</code></td></tr>
<tr><td>Label</td><td>{_e(manifest.get('label') or '—')}</td></tr>
<tr><td>Git commit</td><td><code>{_e(manifest.get('git_commit') or '—')}</code></td></tr>
<tr><td>Git branch</td><td>{_e(manifest.get('git_branch') or '—')}</td></tr>
<tr><td>Started / finished</td><td>{_e(manifest.get('started_at'))} → {_e(manifest.get('finished_at'))}</td></tr>
<tr><td>Corpus selected</td><td>{_e(manifest.get('corpus_selected'))} of {_e(manifest.get('corpus_total_discovered'))} discovered</td></tr>
</tbody></table>
</section>
<section><h2>Corpus by category</h2>{_table(['Category', 'Contracts'], cat_rows)}</section>
<section><h2>Top-firing rules</h2>{_table(['Rule ID', 'Times Triggered', 'Contracts'], top_rules_rows)}</section>
"""
    return _page("Overview", "overview.html", body)


def _rule_coverage(records) -> str:
    rows = agg.compute_rule_statistics(records)
    trows = [
        [
            f'<code>{_e(r["rule_id"])}</code>',
            str(r["times_triggered"]),
            str(r["times_accepted"]),
            str(r["times_flagged_manual_drafting"]),
            str(r["contracts_triggered_in"]),
            '<span class="bad">never fired</span>' if r["never_triggered"] else '<span class="ok">active</span>',
        ]
        for r in rows
    ]
    never = [r for r in rows if r["never_triggered"]]
    body = f"""
<div class="tiles">
{_tile('Total rules', len(rows))}
{_tile('Never fired', len(never), 'warn' if never else 'ok')}
{_tile('Active rules', len(rows) - len(never), 'ok')}
</div>
<section><h2>Every rule ({len(rows)})</h2>
{_table(['Rule ID', 'Times Triggered', 'Times Accepted', 'Flagged (manual drafting)', 'Contracts Triggered In', 'Status'], trows)}
</section>
"""
    return _page("Rule Coverage", "rule_coverage.html", body)


def _contract_coverage(records) -> str:
    rows = sorted(
        agg.compute_contract_statistics(records),
        key=lambda r: (r.get("redline_coverage_pct") if r.get("redline_coverage_pct") is not None else 999),
    )
    trows = [
        [
            _e(r["category"]), _e(r["filename"]), str(r["findings_count"] or 0),
            _bar(r["redline_coverage_pct"] or 0), _e(r["overall_risk"]),
            f'<span class="{"ok" if r["overall_status"]=="pass" else "bad"}">{_e(r["overall_status"])}</span>',
        ]
        for r in rows[:500]
    ]
    body = f"""
<p>{len(rows)} contracts, sorted by redline coverage (lowest first). Showing up to 500 — see reports/contract_statistics.csv for the full set.</p>
{_table(['Category', 'Filename', 'Findings', 'Redline Coverage', 'Overall Risk', 'Status'], trows)}
"""
    return _page("Contract Coverage", "contract_coverage.html", body)


def _performance(records, summary) -> str:
    perf = summary.get("performance", {})
    max_mean = max((v["mean_ms"] for v in perf.values()), default=1) or 1
    trows = [
        [
            _e(stage), str(v["count"]), f'{v["mean_ms"]} ms', f'{v["median_ms"]} ms',
            f'{v["p95_ms"]} ms', f'{v["max_ms"]} ms',
            _bar(v["mean_ms"] / max_mean * 100),
        ]
        for stage, v in perf.items()
    ]
    body = f"""
{_table(['Stage', 'N', 'Mean', 'Median', 'P95', 'Max', 'Relative'], trows)}
"""
    return _page("Performance", "performance.html", body)


def _redline_quality(records, summary) -> str:
    rows = sorted(agg.compute_redline_statistics(records), key=lambda r: -(r["redline_count"] or 0))
    trows = [
        [_e(r["category"]), _e(r["filename"]), str(r["redline_count"] or 0),
         _bar(r["redline_coverage_pct"] or 0), str(r["overlapping_findings_candidates"] or 0),
         str(r["skipped_redlines_in_docx"] or 0)]
        for r in rows[:300]
    ]
    cov = summary.get("coverage", {})
    body = f"""
<div class="tiles">
{_tile('Mean coverage', f"{cov.get('overall_mean_coverage_pct')}%")}
{_tile('Median coverage', f"{cov.get('overall_median_coverage_pct')}%")}
</div>
<section><h2>By category</h2>
{_table(['Category', 'Mean Coverage', 'N'], [[c, f"{v['mean_coverage_pct']}%", str(v['n'])] for c, v in cov.get('by_category', {}).items()])}
</section>
<section><h2>Top contracts by redline volume (top 300)</h2>
{_table(['Category', 'Filename', 'Redlines', 'Coverage', 'Overlap Candidates', 'Skipped in DOCX'], trows)}
</section>
"""
    return _page("Redline Quality", "redline_quality.html", body)


def _manual_drafting(records) -> str:
    rows = agg.compute_manual_drafting_statistics(records)
    trows = [
        [_e(r["category"]), _e(r["filename"]), str(r["findings_count"] or 0),
         str(r["manual_drafting_count"]), _bar(r["manual_drafting_pct"] or 0)]
        for r in rows[:300]
    ]
    body = f"""
<p>{len(rows)} contracts have at least one finding with no authored redline (needs manual attorney drafting). Showing top 300 by volume.</p>
{_table(['Category', 'Filename', 'Findings', 'Manual Drafting Count', 'Manual Drafting %'], trows)}
"""
    return _page("Manual Drafting", "manual_drafting.html", body)


def _regressions(regression: Optional[Dict[str, Any]]) -> str:
    if not regression:
        body = '<p class="empty">No baseline run available — this is either the first run, or the previous run failed to complete. Regression detection begins automatically once a baseline exists.</p>'
        return _page("Regressions", "regressions.html", body)

    tiles = "".join([
        _tile("New finding-rule occurrences", regression["new_finding_rule_occurrences"]),
        _tile("Missing finding-rule occurrences", regression["missing_finding_rule_occurrences"],
              "bad" if regression["missing_finding_rule_occurrences"] else "ok"),
        _tile("Coverage regressions", regression["coverage_regressions"], "bad" if regression["coverage_regressions"] else "ok"),
        _tile("Coverage improvements", regression["coverage_improvements"], "ok"),
        _tile("DOCX export changes", regression["docx_export_changes"], "bad" if regression["docx_export_changes"] else "ok"),
        _tile("Parser changes", regression["parser_changes"], "bad" if regression["parser_changes"] else "ok"),
        _tile("Verify newly failing", regression["verify_newly_failing"], "bad" if regression["verify_newly_failing"] else "ok"),
        _tile("Replay newly non-deterministic", regression["replay_newly_nondeterministic"],
              "bad" if regression["replay_newly_nondeterministic"] else "ok"),
    ])

    rules_gone = regression.get("rules_disappeared_corpuswide", [])
    rules_new = regression.get("rules_newly_firing_corpuswide", [])
    perf_regr = regression.get("performance_regressions", [])

    rows_table = [
        [_e(r["kind"]), _e(r["contract_id"] or "—"), _e(r["detail"])]
        for r in regression.get("rows", [])[:1000]
    ]

    body = f"""
<p>Comparing run <code>{_e(regression['current_run_id'])}</code> against baseline <code>{_e(regression['baseline_run_id'])}</code>.</p>
<div class="tiles">{tiles}</div>
<section><h2>Rules disappeared corpus-wide</h2>{_table(['Rule ID'], [[f'<code>{_e(r)}</code>'] for r in rules_gone], 'None.')}</section>
<section><h2>Rules newly firing corpus-wide</h2>{_table(['Rule ID'], [[f'<code>{_e(r)}</code>'] for r in rules_new], 'None.')}</section>
<section><h2>Performance regressions (&ge;25% slower)</h2>
{_table(['Stage', 'Baseline Mean', 'Current Mean', 'Delta'],
        [[p['stage'], f"{p['baseline_mean_ms']}ms", f"{p['current_mean_ms']}ms", f"{p['delta_pct']}%"] for p in perf_regr], 'None.')}
</section>
<section><h2>All changes (first 1000)</h2>{_table(['Kind', 'Contract ID', 'Detail'], rows_table)}</section>
"""
    return _page("Regressions", "regressions.html", body)
