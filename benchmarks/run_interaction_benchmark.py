#!/usr/bin/env python3
"""
Interaction Engine V1 — independent adversarial benchmark.

Runs benchmarks/interaction_corpus.py's cases at the decision level (per
docs/architecture/interaction_engine_v1_design.md S10.1) against
interaction_engine_core.evaluate() + interaction_rules.LAUNCH_CATALOG —
the exact same function policy_enforcement.apply_policies_for_review
calls in production, never a second evaluation path.

Categories this file does NOT re-cover, by design (already covered as
real DB/HTTP integration tests, not decision-level fixtures, per the
design doc's own "decision-level fixtures + a smaller end-to-end subset"
split):
  - redline invalidation / stale interaction prevention / policy revision
    pinning / "one participating clause changed" / "unrelated clause
    changed" -> tests/test_interaction_enforcement.py (TestMarkDependent
    InteractionsStale, TestVerifyInteractionFinding) and
    tests/test_interaction_review_http.py (TestInvalidationHTTPFlow),
    all exercised against a real database and, for the HTTP suite, real
    upload/review/decision routes.
  - end-to-end wiring (real contract text -> real adapters -> interaction
    engine) -> tests/test_interaction_enforcement.py's
    TestApplyInteractionRulesWiring and TestFailureIsolation.
This file's own gates (below) cover what only a dedicated adversarial
corpus can: false-interaction / missed-high-risk / false-safe / stale-
after-change / false-invalidation-of-unrelated / determinism, at the
interaction-predicate level, independent of any adapter's own benchmark.
"""
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import interaction_engine_core as ixc
import interaction_rules as ixr
from interaction_corpus import CASES, InteractionCase

# States that mean "the correct answer required attention" -- used for the
# false-safe gate, mirroring policy_engine_core.FALSE_SAFE_EXPECTED_STATES.
ATTENTION_STATES = {"ESCALATE", "REQUIRES_REVIEW"}
# States that mean "nothing to see here" -- a false-safe is the engine
# reporting one of these when an ATTENTION_STATES outcome was expected.
SAFE_STATES = {"NOT_TRIGGERED", "ACCEPT_WITH_NOTE"}
HIGH_RISK_KIND_STATES = {"ESCALATE"}  # CONFLICT-tier: a "missed configured high-risk interaction"


def run() -> Dict[str, List[dict]]:
    """Runs every case once and returns {case_id: [{interaction_id, expected, actual, pass}, ...]}."""
    results: Dict[str, List[dict]] = {}
    for case in CASES:
        decisions = case.decisions
        actual_by_id = {d.interaction_id: d.state for d in ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)}
        rows = []
        for interaction_id, expected_state in case.expected.items():
            actual_state = actual_by_id.get(interaction_id)
            rows.append({
                "interaction_id": interaction_id, "expected": expected_state,
                "actual": actual_state, "pass": actual_state == expected_state,
            })
        results[case.case_id] = rows
    return results


def check_deterministic_all() -> Dict[str, bool]:
    out = {}
    for case in CASES:
        out[case.case_id] = ixc.check_deterministic(lambda c=case: ixc.evaluate(c.decisions, ixr.LAUNCH_CATALOG))
    return out


def summarize(results: Dict[str, List[dict]]) -> dict:
    total_assertions = sum(len(rows) for rows in results.values())
    failed_assertions = [
        (case_id, row) for case_id, rows in results.items() for row in rows if not row["pass"]
    ]

    false_interactions = 0  # expected NOT_TRIGGERED/INSUFFICIENT_FACTS, engine fired something else
    missed_high_risk = 0    # expected ESCALATE (CONFLICT-tier), engine did not produce it
    false_safe = 0          # expected attention state, engine reported a safe state
    false_escalation_like = 0  # expected a clear/resolvable outcome, engine abstained (INSUFFICIENT_FACTS/REQUIRES_REVIEW) instead

    for case_id, row in failed_assertions:
        expected, actual = row["expected"], row["actual"]
        if expected in ("NOT_TRIGGERED",) and actual not in ("NOT_TRIGGERED",):
            false_interactions += 1
        if expected in HIGH_RISK_KIND_STATES and actual != expected:
            missed_high_risk += 1
        if expected in ATTENTION_STATES and actual in SAFE_STATES:
            false_safe += 1
        if expected not in ("INSUFFICIENT_FACTS", "REQUIRES_REVIEW") and actual in ("INSUFFICIENT_FACTS", "REQUIRES_REVIEW") and expected != actual:
            false_escalation_like += 1

    determinism = check_deterministic_all()
    non_deterministic = [cid for cid, ok in determinism.items() if not ok]

    accuracy = 100.0 * (total_assertions - len(failed_assertions)) / total_assertions if total_assertions else 100.0

    return {
        "total_cases": len(CASES),
        "total_assertions": total_assertions,
        "failed_assertions": failed_assertions,
        "false_interactions": false_interactions,
        "missed_high_risk": missed_high_risk,
        "false_safe": false_safe,
        "false_escalation_like": false_escalation_like,
        "determinism_pct": 100.0 * (len(CASES) - len(non_deterministic)) / len(CASES) if CASES else 100.0,
        "non_deterministic_cases": non_deterministic,
        "interaction_state_accuracy_pct": round(accuracy, 1),
    }


def failures_by_tag(results: Dict[str, List[dict]]) -> Dict[str, List[str]]:
    by_case = {c.case_id: c for c in CASES}
    out: Dict[str, List[str]] = defaultdict(list)
    for case_id, rows in results.items():
        if any(not r["pass"] for r in rows):
            for tag in by_case[case_id].tags:
                out[tag].append(case_id)
    return out


def render_report(results: Dict[str, List[dict]], summary: dict) -> str:
    lines = ["# Interaction Engine V1 — Adversarial Benchmark Report", ""]
    lines.append(f"Corpus: {summary['total_cases']} cases, {summary['total_assertions']} interaction-level assertions.")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Interaction-state accuracy | {summary['interaction_state_accuracy_pct']}% |")
    lines.append(f"| False interaction | {summary['false_interactions']} |")
    lines.append(f"| Missed configured high-risk interaction | {summary['missed_high_risk']} |")
    lines.append(f"| False-safe interaction outcome | {summary['false_safe']} |")
    lines.append(f"| False abstention (expected resolvable, engine abstained) | {summary['false_escalation_like']} |")
    lines.append(f"| Determinism (5x repeat) | {summary['determinism_pct']}% |")
    lines.append("")
    lines.append("## Release gate check")
    lines.append("")
    def gate(name, actual, ok):
        return f"- {'PASS' if ok else 'FAIL'} — {name} (actual: {actual})"
    lines.append(gate("False interaction = 0", summary["false_interactions"], summary["false_interactions"] == 0))
    lines.append(gate("Missed configured high-risk interaction = 0", summary["missed_high_risk"], summary["missed_high_risk"] == 0))
    lines.append(gate("False-safe interaction outcome = 0", summary["false_safe"], summary["false_safe"] == 0))
    lines.append(gate("Determinism = 100%", f"{summary['determinism_pct']}%", summary["determinism_pct"] == 100.0))
    lines.append("")
    lines.append(
        "Stale-interaction-after-change=0 and false-invalidation-of-unrelated-interaction=0 are proven "
        "against a real database and real HTTP routes in tests/test_interaction_enforcement.py "
        "(TestMarkDependentInteractionsStale) and tests/test_interaction_review_http.py "
        "(TestInvalidationHTTPFlow) — not re-asserted here, since those gates are about the persistence/"
        "HTTP layer, not the pure interaction predicate this corpus targets. See that test run's own "
        "pass/fail count for those two gates."
    )
    lines.append("")
    if summary["failed_assertions"]:
        lines.append("## Failures")
        lines.append("")
        for case_id, row in summary["failed_assertions"]:
            lines.append(f"- `{case_id}` / `{row['interaction_id']}`: expected `{row['expected']}`, got `{row['actual']}`")
        lines.append("")
    else:
        lines.append("## Failures")
        lines.append("")
        lines.append("None.")
        lines.append("")
    tags = failures_by_tag(results)
    if tags:
        lines.append("## Failures by tag")
        lines.append("")
        for tag, case_ids in sorted(tags.items()):
            lines.append(f"- `{tag}`: {len(case_ids)} case(s) — {', '.join(case_ids)}")
    return "\n".join(lines)


def main():
    results = run()
    summary = summarize(results)
    print(render_report(results, summary))
    gates_pass = (
        summary["false_interactions"] == 0 and summary["missed_high_risk"] == 0
        and summary["false_safe"] == 0 and summary["determinism_pct"] == 100.0
    )
    sys.exit(0 if gates_pass else 1)


if __name__ == "__main__":
    main()
