"""
production_summary.html — a single, self-contained page: the Production
Readiness Report (Go/No-Go, scores, ranked issues) up top, full supporting
detail below. Same visual language as triagebench/dashboards.py so a
reviewer moving between the engine benchmark and the live-app benchmark
isn't reorienting to a different design each time — but a distinct favicon
concept in the surrounding tooling makes clear which one they're looking
at.
"""
from __future__ import annotations

import html as htmllib
from typing import Any, Dict, List, Optional

from . import aggregate as agg
from . import readiness
from . import storage

_CSS = """
:root { color-scheme: light dark; }
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 2rem;
       background: #0b0d12; color: #e6e8ee; }
@media (prefers-color-scheme: light) { body { background: #f7f8fa; color: #1a1d24; } }
h1 { font-size: 1.6rem; margin-bottom: 0.1rem; }
.subtitle { color: #8a90a2; margin-bottom: 1.5rem; }
.verdict { font-size: 2.2rem; font-weight: 800; padding: 1.5rem 2rem; border-radius: 14px; margin: 1rem 0 2rem;
           display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; }
.verdict.go { background: rgba(51,209,122,0.12); color: #33d17a; border: 1px solid rgba(51,209,122,0.35); }
.verdict.conditional { background: rgba(245,192,74,0.12); color: #f5c04a; border: 1px solid rgba(245,192,74,0.35); }
.verdict.nogo { background: rgba(255,107,107,0.12); color: #ff6b6b; border: 1px solid rgba(255,107,107,0.35); }
.verdict .scores { font-size: 1rem; font-weight: 500; display: flex; gap: 1.5rem; color: inherit; opacity: 0.9; }
.verdict .scores b { font-size: 1.3rem; display: block; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; margin-bottom: 2rem; }
.tile { background: #151822; border: 1px solid #262b3a; border-radius: 10px; padding: 1rem; }
@media (prefers-color-scheme: light) { .tile { background: #fff; border-color: #e3e5ea; } }
.tile .val { font-size: 1.6rem; font-weight: 700; }
.tile .lbl { font-size: 0.78rem; color: #8a90a2; text-transform: uppercase; letter-spacing: 0.04em; }
.ok { color: #33d17a; } .warn { color: #f5c04a; } .bad { color: #ff6b6b; }
table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; font-size: 0.85rem; }
th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #262b3a; vertical-align: top; }
@media (prefers-color-scheme: light) { th, td { border-color: #e3e5ea; } }
th { color: #8a90a2; font-weight: 600; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.03em; }
tr:hover { background: rgba(122,162,255,0.06); }
section { margin-bottom: 2rem; }
h2 { font-size: 1.15rem; border-bottom: 1px solid #262b3a; padding-bottom: 0.4rem; }
@media (prefers-color-scheme: light) { h2 { border-color: #e3e5ea; } }
code { background: #151822; padding: 0.1rem 0.35rem; border-radius: 4px; }
@media (prefers-color-scheme: light) { code { background: #eef0f4; } }
.empty { color: #8a90a2; font-style: italic; }
.sev-critical { color: #ff6b6b; font-weight: 700; }
.sev-high { color: #ff9a5a; font-weight: 700; }
.sev-medium { color: #f5c04a; }
.sev-low, .sev-info { color: #8a90a2; }
.priority-list { list-style: none; padding: 0; }
.priority-list li { padding: 0.6rem 0.9rem; margin-bottom: 0.5rem; border-radius: 8px; background: #151822; border-left: 3px solid #ff6b6b; }
@media (prefers-color-scheme: light) { .priority-list li { background: #fff; } }
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


def generate_summary(
    run_id: str,
    manifest: Dict[str, Any],
    contract_records: List[Dict[str, Any]],
    security_findings: List[Dict[str, Any]],
    failure_results: List[Dict[str, Any]],
    concurrency_results: List[Dict[str, Any]],
    browser_results: List[Dict[str, Any]],
    db_lifecycle_results: List[Dict[str, Any]],
    regression: Optional[Dict[str, Any]],
) -> str:
    issues = readiness.collect_issues(
        contract_records, security_findings, failure_results, concurrency_results, browser_results,
        db_lifecycle_results, regression,
    )
    scores = readiness.compute_scores(contract_records, security_findings, browser_results, issues)
    priorities = readiness.top_priorities(issues)

    wf = agg.compute_workflow_statistics(contract_records)
    perf = agg.compute_performance_statistics(contract_records)
    sec_summary = agg.compute_security_summary(security_findings)
    browser_summary = agg.compute_browser_summary(browser_results)

    verdict_cls = {"GO": "go", "CONDITIONAL GO": "conditional", "NO-GO": "nogo"}[scores["verdict"]]
    verdict_html = f"""
<div class="verdict {verdict_cls}">
  <div>{_e(scores['verdict'])}</div>
  <div class="scores">
    <div>Readiness<br><b>{scores['readiness_score']}/100</b></div>
    <div>Commercial Readiness<br><b>{scores['commercial_readiness_score']}/100</b></div>
    <div>Critical<br><b>{scores['critical_count']}</b></div>
    <div>High<br><b>{scores['high_count']}</b></div>
    <div>Medium<br><b>{scores['medium_count']}</b></div>
  </div>
</div>
"""

    priorities_html = "<ul class='priority-list'>" + "".join(f"<li>{_e(p)}</li>" for p in priorities) + "</ul>"

    issues_by_sev = {"critical": [], "high": [], "medium": [], "low": []}
    for i in issues:
        issues_by_sev.setdefault(i.severity, []).append(i)

    def issue_rows(sev):
        return [[f'<span class="sev-{sev}">{_e(i.title)}</span>', _e(i.source), _e(i.detail)[:400]]
                for i in issues_by_sev.get(sev, [])]

    db_lifecycle_passed = sum(1 for f in db_lifecycle_results if f.get("passed"))
    db_lifecycle_total = len(db_lifecycle_results)

    tiles = "".join([
        _tile("Contracts tested", wf["contracts_processed"]),
        _tile("Workflow pass rate", f"{scores['workflow_pass_rate_pct']}%",
              "ok" if scores["workflow_pass_rate_pct"] >= 95 else "warn"),
        _tile("DB session lifecycle", f"{db_lifecycle_passed}/{db_lifecycle_total}",
              "ok" if db_lifecycle_total and db_lifecycle_passed == db_lifecycle_total else ("bad" if db_lifecycle_total else "warn")),
        _tile("Security checks passed", f"{sec_summary['total_checks'] - sec_summary['failed_checks']}/{sec_summary['total_checks']}",
              "ok" if sec_summary["all_passed"] else "bad"),
        _tile("Browsers available", len(browser_summary["browsers_available"])),
        _tile("Browsers passed", len(browser_summary["browsers_passed"]),
              "ok" if browser_summary["browsers_passed"] == browser_summary["browsers_available"] else "warn"),
        _tile("Failure-injection checks", len(failure_results)),
        _tile("Concurrency checks", len(concurrency_results)),
    ])

    db_lifecycle_rows = [
        [f['name'], "✓ pass" if f["passed"] else "✗ FAIL", _e(f['detail'])]
        for f in db_lifecycle_results
    ]

    perf_rows = [[step, str(v["count"]), f"{v['mean_ms']} ms", f"{v['p95_ms']} ms", f"{v['max_ms']} ms"]
                 for step, v in perf.items()]

    browser_rows = [
        [b["browser"], "yes" if b.get("available") else "no", _e(b.get("overall_status")),
         "; ".join(s["name"] for s in b.get("steps", []) if s["status"] in ("fail", "error")) or "—"]
        for b in browser_results
    ]

    security_rows = [
        [f['check'], "✓" if f["passed"] else "✗", f"<span class='sev-{f['severity']}'>{_e(f['severity'])}</span>", _e(f['detail'])[:300]]
        for f in security_findings
    ]

    contract_failure_rows = [
        [r["contract_id_hint"], r["category"], r["filename"], r["overall_status"], r["failed_steps"], _e(r["first_error"])[:200]]
        for r in agg.compute_contract_failures(contract_records)
    ]

    regression_html = ""
    if regression:
        crit = regression["has_critical_regressions"]
        regression_html = f"""
<section><h2>Regression vs. baseline {_e(regression['baseline_run_id'])}</h2>
<p class="{'bad' if crit else 'ok'}">{'⚠ Critical regressions detected' if crit else '✓ No critical regressions detected'}</p>
<div class="tiles">
{_tile('Newly failing contracts', regression['newly_failing_contracts'], 'bad' if regression['newly_failing_contracts'] else 'ok')}
{_tile('Verify regressions', regression['verify_regressions'], 'bad' if regression['verify_regressions'] else 'ok')}
{_tile('Persistence regressions', regression['persistence_regressions'], 'bad' if regression['persistence_regressions'] else 'ok')}
{_tile('DOCX export regressions', regression['docx_export_regressions'], 'bad' if regression['docx_export_regressions'] else 'ok')}
{_tile('Security regressions', len(regression['security_regressions']), 'bad' if regression['security_regressions'] else 'ok')}
{_tile('Browser regressions', len(regression['browser_regressions']), 'bad' if regression['browser_regressions'] else 'ok')}
</div>
</section>
"""
    else:
        regression_html = '<section><h2>Regression vs. baseline</h2><p class="empty">No baseline run available yet (first run).</p></section>'

    body = f"""
<h1>TriageBench Live — Production Readiness Report</h1>
<p class="subtitle">Run <code>{_e(run_id)}</code> against <code>{_e(manifest.get('base_url'))}</code> ·
commit <code>{_e(manifest.get('git_commit') or '—')}</code> · {_e(manifest.get('started_at'))} → {_e(manifest.get('finished_at'))}</p>

{verdict_html}

<section><h2>Top engineering priorities</h2>{priorities_html}</section>

<div class="tiles">{tiles}</div>

<section><h2>Database session lifecycle proof ({db_lifecycle_passed}/{db_lifecycle_total})</h2>
<p>Targeted regression test for the specific connection-pool exhaustion bug this suite originally found and
that was fixed (main.py routes now use <code>Depends(get_db)</code>; the two exception handlers use
<code>database.db_session()</code> — see <code>triagebench_live/db_lifecycle_proof.py</code> and
<code>triagebench_live/README.md</code> for the full methodology and incident writeup).</p>
{_table(['Phase', 'Result', 'Detail'], db_lifecycle_rows, 'Not run this session.')}
</section>

{regression_html}

<section><h2>Critical blockers ({len(issues_by_sev['critical'])})</h2>{_table(['Issue', 'Source', 'Detail'], issue_rows('critical'), 'None — no critical blockers.')}</section>
<section><h2>High priority issues ({len(issues_by_sev['high'])})</h2>{_table(['Issue', 'Source', 'Detail'], issue_rows('high'), 'None.')}</section>
<section><h2>Medium priority issues ({len(issues_by_sev['medium'])})</h2>{_table(['Issue', 'Source', 'Detail'], issue_rows('medium'), 'None.')}</section>

<section><h2>Performance</h2>{_table(['Step', 'N', 'Mean', 'P95', 'Max'], perf_rows)}</section>

<section><h2>Browser results</h2>{_table(['Browser', 'Available', 'Status', 'Failed steps'], browser_rows)}</section>

<section><h2>Security checks ({sec_summary['total_checks']})</h2>{_table(['Check', 'Passed', 'Severity', 'Detail'], security_rows)}</section>

<section><h2>Contract-level failures</h2>{_table(['Contract', 'Category', 'Filename', 'Status', 'Failed steps', 'First error'], contract_failure_rows, 'None — every contract journey passed.')}</section>

<section><h2>Scope and methodology</h2>
<p>Every check in this report was executed over real HTTP (and, for the browser suite, a real Chromium
instance) against a running instance of the application — no engine module was imported, no database
was queried directly, and no authentication was bypassed. See <code>triagebench_live/README.md</code>
for the full methodology, what this suite deliberately does not measure (server CPU/memory, since a
black-box HTTP client cannot observe a remote process's resource usage), and how the readiness score
is computed (<code>triagebench_live/readiness.py</code>).</p>
</section>
"""

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>TriageBench Live — Production Readiness Report</title>
<style>{_CSS}</style></head><body>{body}</body></html>"""


def write_summary(run_id: str, html: str) -> None:
    (storage.config.run_dir(run_id) / "production_summary.html").write_text(html, encoding="utf-8")
