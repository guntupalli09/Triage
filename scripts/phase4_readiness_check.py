#!/usr/bin/env python3
"""
Phase 4.1 — Production Shadow Readiness check / dry-run cutover
verification.

This is the ONE operator-facing command for both jobs the Phase 4.1 task
asked for, because they are the same computation: "would cutover be safe
right now" and "verify every cutover prerequisite without touching
anything" are the same set of checks, run read-only. This script NEVER
sets, unsets, or reads-for-the-purpose-of-changing
POLICY_ENFORCEMENT_MODE — see policy_readiness.assess_readiness, which
only reads existing DB state and re-runs the existing benchmark/test-
suite scripts as isolated subprocesses.

Usage:
    python -m scripts.phase4_readiness_check
    python -m scripts.phase4_readiness_check --json
    python -m scripts.phase4_readiness_check --dry-run-cutover   # identical
                                                                  # behavior;
                                                                  # explicit
                                                                  # framing
    python -m scripts.phase4_readiness_check --skip-benchmarks --skip-tests
        # fast iteration only — a report produced this way can NEVER be
        # READY_FOR_CUTOVER (see policy_readiness.assess_readiness), since
        # "we didn't check" is not evidence of "it's fine."

Exit code: 0 when READY_FOR_CUTOVER, 1 when NOT_READY_FOR_CUTOVER — safe
to use as a CI/deployment gate directly.

No user contract text, policy config values, fallback language, evidence
excerpts, or other sensitive content is read, computed, or printed by
this script at any point — see policy_readiness.py's module docstring
for how that is enforced by construction, not just by convention.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
os.environ.setdefault("DEV_MODE", "true")

from database import SessionLocal, init_db
import analytics_models  # noqa: F401 — registers the full schema (User.acquisition relationship etc.)
import policy_readiness as pr


def _format_report(report: pr.ReadinessReport) -> str:
    d = pr.report_to_safe_dict(report)
    lines = ["# Phase 4.1 Production Shadow Readiness Report", ""]
    lines.append(f"Generated: {d['generated_at']}")
    lines.append(f"Current POLICY_ENFORCEMENT_MODE: `{d['current_mode']}`")
    lines.append("")

    m = d["migration_coverage"]
    lines.append("## 1. Migration coverage")
    lines.append(f"- Total legacy limitation_of_liability PolicyRule rows: {m['total_legacy_liability_policies']}")
    lines.append(f"- Migrated to an equivalent ACTIVE PolicyPosition: {m['migrated_active_equivalents']}")
    lines.append(f"- Unmigrated: {m['unmigrated_count']} (playbook_ids={m['unmigrated_playbook_ids']})")
    lines.append(f"- Coverage: {m['coverage_pct']}%")
    lines.append("")

    s = d["live_shadow_comparisons"]
    lines.append("## 2. Live shadow-mode comparison history")
    lines.append(f"- Total comparisons recorded: **{s['total']}**  <- sample size; not a synthetic minimum")
    lines.append(f"- Matching: {s['matching']}")
    lines.append(f"- Divergent: {s['divergent']}")
    lines.append(f"- Evaluation errors (migrated path could not run): {s['evaluation_errors']}")
    rate = "n/a (no comparisons yet)" if s["divergence_rate"] is None else f"{s['divergence_rate']:.4%}"
    lines.append(f"- Divergence rate: {rate}")
    lines.append(f"- Distinct playbooks exercised: {s['distinct_playbooks_exercised']}")
    lines.append(f"- Distinct contracts/reviews exercised: {s['distinct_contracts_exercised']}")
    lines.append(f"- Oldest comparison: {s['oldest_comparison_at']}")
    lines.append(f"- Newest comparison: {s['newest_comparison_at']}")
    lines.append("")
    lines.append(
        "**This script does not decide whether the sample size above is large enough.** "
        "That is an explicit deployment-operator judgment call, not an automated one — see the "
        "task's own instruction not to invent a synthetic minimum contract count."
    )
    lines.append("")

    lines.append("## 3. Six-adapter benchmark gates (current status)")
    for name, status in d["six_adapter_benchmark_gates"].items():
        lines.append(f"- {status} — {name}")
    lines.append("")

    lines.append("## 4. Phase 4 109-case offline equivalence gate")
    lines.append(f"- {d['phase4_109case_equivalence_gate']}")
    lines.append("")

    lines.append("## 5. Full test suite")
    lines.append(f"- {d['full_test_suite']['status']} — {d['full_test_suite']['summary']}")
    lines.append("")

    lines.append("## Verdict")
    lines.append(f"**{d['verdict']}**")
    if d["blocking_reasons"]:
        lines.append("")
        lines.append("Blocking reasons:")
        for reason in d["blocking_reasons"]:
            lines.append(f"- {reason}")
    lines.append("")
    lines.append(
        "This report does not change POLICY_ENFORCEMENT_MODE. Flipping it to `cutover` remains a "
        "separate, explicit, human-authorized deployment action — see docs/architecture/phase4_cutover.md."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit the machine-readable report instead of markdown.")
    parser.add_argument("--dry-run-cutover", action="store_true",
                         help="Identical behavior to the default; explicit framing for CI/audit logs.")
    parser.add_argument("--skip-benchmarks", action="store_true",
                         help="Skip re-running the six-adapter + Phase 4 benchmarks (fast iteration only; "
                              "report can never be READY_FOR_CUTOVER when this is set).")
    parser.add_argument("--skip-tests", action="store_true",
                         help="Skip re-running the full test suite (fast iteration only; report can never be "
                              "READY_FOR_CUTOVER when this is set).")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        report = pr.assess_readiness(db, run_benchmarks=not args.skip_benchmarks, run_tests=not args.skip_tests)
    finally:
        db.close()

    if args.json:
        print(json.dumps(pr.report_to_safe_dict(report), indent=2))
    else:
        print(_format_report(report))

    return 0 if report.verdict == "READY_FOR_CUTOVER" else 1


if __name__ == "__main__":
    sys.exit(main())
