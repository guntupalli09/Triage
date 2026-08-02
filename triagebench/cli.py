"""
Command-line entrypoint: `python -m triagebench <command>`.

Commands:
  run        Execute (or resume) a benchmark run, then finalize it
             (reports + dashboards + regression detection).
  finalize   Regenerate reports/dashboards/regression for an already-
             completed run, without re-running the corpus.
  list       List past runs.

Exit codes (CI-friendly): 0 = success and no critical regressions;
1 = benchmark ran but found critical regressions or contract failures
above threshold; 2 = the run itself could not complete.
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
    config = cfg.BenchmarkConfig(
        run_id=args.run_id or (args.resume if args.resume else cfg.new_run_id()),
        workers=args.workers,
        limit=args.limit,
        per_category_limit=args.per_category,
        categories=categories,
        seed=args.seed,
        resume=bool(args.resume),
        label=args.label,
    )

    try:
        run_id = runner.run(config)
    except Exception as exc:  # noqa: BLE001
        print(f"[triagebench] RUN FAILED TO COMPLETE: {exc}", file=sys.stderr)
        return 2

    result = finalize_mod.finalize(
        run_id, baseline_run_id=args.baseline, set_as_latest=not args.no_latest
    )
    summary = result["summary"]
    regression = result["regression"]

    print(f"\n[triagebench] run {run_id} complete.")
    print(f"  contracts processed : {summary['contracts_processed']}")
    print(f"  pass rate           : {summary['pass_rate_pct']}%")
    print(f"  status counts       : {summary['status_counts']}")
    print(f"  reports             : {cfg.run_dir(run_id) / 'reports'}")
    print(f"  dashboards          : {cfg.run_dir(run_id) / 'dashboards'} (open overview.html)")

    if regression:
        crit = regression["has_critical_regressions"]
        print(f"  regression baseline : {regression['baseline_run_id']} "
              f"({'CRITICAL REGRESSIONS' if crit else 'clean'})")
    else:
        print("  regression baseline : none (first run)")

    if args.fail_on_regression and regression and regression["has_critical_regressions"]:
        return 1
    if args.fail_on_error and summary["status_counts"].get("error", 0) > 0:
        return 1
    return 0


def _cmd_finalize(args: argparse.Namespace) -> int:
    result = finalize_mod.finalize(args.run_id, baseline_run_id=args.baseline, set_as_latest=not args.no_latest)
    print(json.dumps({k: v for k, v in result.items() if k != "summary"}, indent=2, default=str))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    for run_id in storage.list_run_ids():
        manifest = storage.read_manifest(run_id)
        print(f"{run_id}  status={manifest.get('status')}  "
              f"contracts={manifest.get('corpus_selected')}  label={manifest.get('label')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="triagebench", description="TriageCounsel continuous quality benchmark")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Execute a benchmark run")
    run_p.add_argument("--workers", type=int, default=cfg.BenchmarkConfig().workers)
    run_p.add_argument("--limit", type=int, default=None, help="Total contracts to sample (deterministic)")
    run_p.add_argument("--per-category", type=int, default=None, help="Max contracts per category")
    run_p.add_argument("--category", action="append", default=None, help="Restrict to one category (repeatable)")
    run_p.add_argument("--seed", type=int, default=cfg.BenchmarkConfig().seed)
    run_p.add_argument("--resume", type=str, default=None, help="run_id to resume")
    run_p.add_argument("--run-id", type=str, default=None, help="Explicit run_id (default: timestamp)")
    run_p.add_argument("--label", type=str, default=None)
    run_p.add_argument("--baseline", type=str, default=None, help="run_id to diff against (default: latest completed run)")
    run_p.add_argument("--no-latest", action="store_true", help="Don't update LATEST_RUN.json")
    run_p.add_argument("--fail-on-regression", action="store_true", help="Exit 1 if critical regressions found")
    run_p.add_argument("--fail-on-error", action="store_true", help="Exit 1 if any contract errored")
    run_p.set_defaults(func=_cmd_run)

    fin_p = sub.add_parser("finalize", help="Regenerate reports/dashboards for a completed run")
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
