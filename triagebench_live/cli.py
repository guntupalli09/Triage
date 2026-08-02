"""
Command-line entrypoint: `python -m triagebench_live <command>`.

Exit codes (CI-friendly): 0 = GO; 1 = CONDITIONAL GO or NO-GO (or, with
--fail-on-error, any contract errored); 2 = the run itself could not
complete (an infrastructure problem with the test harness, not a quality
signal about the target application).
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config as cfg
from . import finalize as finalize_mod
from . import runner
from . import storage


def _cmd_run(args: argparse.Namespace) -> int:
    categories = args.category or list(cfg.CATEGORIES)
    browsers = args.browser or ["chromium", "firefox", "webkit", "msedge"]
    config = cfg.LiveConfig(
        run_id=args.run_id or (args.resume if args.resume else cfg.new_run_id()),
        base_url=args.base_url,
        workers=args.workers,
        limit=args.limit,
        per_category_limit=args.per_category,
        categories=categories,
        seed=args.seed,
        resume=bool(args.resume),
        label=args.label,
        run_security=not args.no_security,
        run_failure_tests=not args.no_failure_tests,
        run_concurrency=not args.no_concurrency,
        run_browser=not args.no_browser,
        browsers=browsers,
        timeout_s=args.timeout,
    )

    try:
        run_id = runner.run(config)
    except Exception as exc:  # noqa: BLE001
        print(f"[triagebench-live] RUN FAILED TO COMPLETE: {exc}", file=sys.stderr)
        return 2

    result = finalize_mod.finalize(run_id, baseline_run_id=args.baseline, set_as_latest=not args.no_latest)
    regression = result["regression"]

    from . import aggregate as agg, readiness
    contract_records = storage.load_contract_results(run_id)
    security_findings = storage.load_json(run_id, "security_results.json")
    failure_results = storage.load_json(run_id, "failure_results.json")
    concurrency_results = storage.load_json(run_id, "concurrency_results.json")
    browser_results = storage.load_json(run_id, "browser_results.json")
    try:
        db_lifecycle_results = storage.load_json(run_id, "db_lifecycle_results.json")
    except FileNotFoundError:
        db_lifecycle_results = []
    issues = readiness.collect_issues(
        contract_records, security_findings, failure_results, concurrency_results, browser_results,
        db_lifecycle_results, regression,
    )
    scores = readiness.compute_scores(contract_records, security_findings, browser_results, issues)

    print(f"\n[triagebench-live] run {run_id} complete against {config.base_url}.")
    print(f"  contracts processed : {result['contracts_processed']}")
    print(f"  verdict             : {scores['verdict']}")
    print(f"  readiness score     : {scores['readiness_score']}/100")
    print(f"  commercial score    : {scores['commercial_readiness_score']}/100")
    print(f"  critical / high     : {scores['critical_count']} / {scores['high_count']}")
    print(f"  report              : {cfg.run_dir(run_id) / 'production_summary.html'}")
    if regression:
        print(f"  regression baseline : {regression['baseline_run_id']} "
              f"({'CRITICAL REGRESSIONS' if regression['has_critical_regressions'] else 'clean'})")
    else:
        print("  regression baseline : none (first run)")

    if scores["verdict"] != "GO":
        return 1
    if args.fail_on_error:
        status_counts = agg.compute_workflow_statistics(contract_records)["status_counts"]
        if status_counts.get("error", 0) > 0:
            return 1
    return 0


def _cmd_finalize(args: argparse.Namespace) -> int:
    result = finalize_mod.finalize(args.run_id, baseline_run_id=args.baseline, set_as_latest=not args.no_latest)
    print(json.dumps(result, indent=2, default=str))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    for run_id in storage.list_run_ids():
        manifest = storage.read_manifest(run_id)
        print(f"{run_id}  status={manifest.get('status')}  target={manifest.get('base_url')}  "
              f"contracts={manifest.get('contracts_selected')}  label={manifest.get('label')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="triagebench_live", description="TriageCounsel production/staging validation suite")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Execute a production validation run")
    run_p.add_argument("--base-url", type=str, default=cfg.DEFAULT_BASE_URL,
                        help="Base URL of the deployed instance to test (default: %(default)s)")
    run_p.add_argument("--workers", type=int, default=cfg.LiveConfig().workers,
                        help="Concurrent contract workflows (default: %(default)s — deliberately conservative, see README)")
    run_p.add_argument("--limit", type=int, default=None)
    run_p.add_argument("--per-category", type=int, default=5)
    run_p.add_argument("--category", action="append", default=None)
    run_p.add_argument("--seed", type=int, default=cfg.LiveConfig().seed)
    run_p.add_argument("--resume", type=str, default=None)
    run_p.add_argument("--run-id", type=str, default=None)
    run_p.add_argument("--label", type=str, default=None)
    run_p.add_argument("--baseline", type=str, default=None)
    run_p.add_argument("--no-latest", action="store_true")
    run_p.add_argument("--no-security", action="store_true")
    run_p.add_argument("--no-failure-tests", action="store_true")
    run_p.add_argument("--no-concurrency", action="store_true")
    run_p.add_argument("--no-browser", action="store_true")
    run_p.add_argument("--browser", action="append", default=None,
                        help="Browser(s) to test (repeatable): chromium, firefox, webkit, msedge")
    run_p.add_argument("--timeout", type=int, default=cfg.DEFAULT_HTTP_TIMEOUT_S)
    run_p.add_argument("--fail-on-error", action="store_true")
    run_p.set_defaults(func=_cmd_run)

    fin_p = sub.add_parser("finalize", help="Regenerate reports for a completed run")
    fin_p.add_argument("run_id")
    fin_p.add_argument("--baseline", type=str, default=None)
    fin_p.add_argument("--no-latest", action="store_true")
    fin_p.set_defaults(func=_cmd_finalize)

    list_p = sub.add_parser("list", help="List past runs")
    list_p.set_defaults(func=_cmd_list)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
