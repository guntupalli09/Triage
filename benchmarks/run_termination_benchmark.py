#!/usr/bin/env python3
"""
Benchmark harness for the Termination policy engine — third clause
adapter, testing whether policy_engine_core.py generalizes to a third
reasoning shape (a catalog of independently-true contingent rights,
rather than Liability's comparative value or Indemnification's directed
obligation graph). Structurally mirrors run_indemnification_benchmark.py.

Usage:
    python3 benchmarks/run_termination_benchmark.py [--out FILE.md]

Exit code is non-zero only when the false-safe count is non-zero.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import termination_policy_engine as te
import policy_engine_core as core
from benchmarks.termination_corpus import CASES, DEFAULT_POLICY


@dataclass
class Policy:
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]
    require_mutual_convenience_termination: bool
    min_notice_days_against_us: Optional[int]
    min_cure_days_against_us: Optional[int]
    prohibit_immediate_termination_for_cause: bool
    required_survival_topics_json: Optional[List[str]]
    prohibit_uncapped_termination_fee: bool
    fee_preferred_multiplier: Optional[float]
    fee_acceptable_max_multiplier: Optional[float]
    fee_negotiate_max_multiplier: Optional[float]


def _build_policy(overrides: Dict[str, Any]) -> Policy:
    merged = dict(DEFAULT_POLICY)
    merged.update(overrides)
    return Policy(**merged)


def _fee_matches(facts: Optional[te.TerminationFacts], expected: Any) -> bool:
    if facts is None:
        return False
    f = facts.fee
    if f.kind != expected["kind"]:
        return False
    if expected["kind"] == "multiplier":
        return abs(f.multiplier - expected["multiplier"]) < 1e-6
    if expected["kind"] == "fixed":
        return abs(f.fixed_amount - expected["fixed_amount"]) < 1e-6
    return True  # unlimited / not_stated / not_mentioned


def run() -> Dict[str, Any]:
    results = []
    for c in CASES:
        policy = _build_policy(c["policy_overrides"])
        facts = te.extract_termination_facts(c["text"])
        decision = te.evaluate_termination_policy(facts, policy, source="Benchmark v1")

        row: Dict[str, Any] = {
            "id": c["id"], "tags": c["tags"], "notes": c["notes"],
            "expected_state": c["expected_state"], "actual_state": decision.state,
            "state_correct": decision.state == c["expected_state"],
        }

        # --- Provision detection ---
        clause_detected = facts is not None and facts.clause_found
        expected_clause_detected = c["expected_state"] != core.NOT_APPLICABLE
        row["provision_detection_correct"] = clause_detected == expected_clause_detected

        # --- Trigger-type coverage ---
        if c["expected_trigger_types"] != "SKIP":
            row["trigger_types_scored"] = True
            actual_types = {r.trigger_type for r in facts.rights} if facts else set()
            row["trigger_types_correct"] = actual_types == c["expected_trigger_types"]
        else:
            row["trigger_types_scored"] = False

        # --- Termination fee ---
        if c["expected_fee"] != "SKIP":
            row["fee_scored"] = True
            row["fee_correct"] = _fee_matches(facts, c["expected_fee"])
        else:
            row["fee_scored"] = False

        # --- Survival topic presence ---
        if c["expected_survival_present"] != "SKIP":
            row["survival_scored"] = True
            actual = {
                topic: (facts.survival_topics.get(topic).present if facts and topic in facts.survival_topics else False)
                for topic in c["expected_survival_present"]
            }
            row["survival_correct"] = actual == c["expected_survival_present"]
        else:
            row["survival_scored"] = False

        row["false_safe"] = core.is_false_safe(c["expected_state"], decision.state)
        row["false_escalation"] = core.is_false_escalation(c["expected_state"], decision.state)

        def _evaluate_once(text=c["text"], policy=policy):
            f = te.extract_termination_facts(text)
            return te.evaluate_termination_policy(f, policy, source="Benchmark v1")

        row["deterministic"] = core.check_deterministic(_evaluate_once, repeats=5)

        results.append(row)
    return {"rows": results}


def summarize(data: Dict[str, Any]) -> Dict[str, Any]:
    rows = data["rows"]
    n = len(rows)

    def _rate(key_scored: str, key_correct: str):
        scored = [r for r in rows if r.get(key_scored)]
        correct = sum(1 for r in scored if r.get(key_correct))
        return (correct / len(scored) if scored else None), len(scored)

    provision_correct = sum(1 for r in rows if r["provision_detection_correct"])
    state_correct = sum(1 for r in rows if r["state_correct"])

    trigger_acc, trigger_n = _rate("trigger_types_scored", "trigger_types_correct")
    fee_acc, fee_n = _rate("fee_scored", "fee_correct")
    survival_acc, survival_n = _rate("survival_scored", "survival_correct")

    requires_review_expected = [r for r in rows if r["expected_state"] == core.REQUIRES_REVIEW]

    false_safe_rows = [r for r in rows if r["false_safe"]]
    false_escalation_rows = [r for r in rows if r["false_escalation"]]
    non_deterministic_rows = [r for r in rows if not r["deterministic"]]

    return {
        "total_cases": n,
        "provision_detection_accuracy": provision_correct / n if n else 0.0,
        "trigger_type_accuracy": trigger_acc, "trigger_type_scored_n": trigger_n,
        "fee_accuracy": fee_acc, "fee_scored_n": fee_n,
        "survival_accuracy": survival_acc, "survival_scored_n": survival_n,
        "policy_state_accuracy": state_correct / n if n else 0.0,
        "ambiguity_recall": (
            len([r for r in requires_review_expected if r["actual_state"] == core.REQUIRES_REVIEW])
            / len(requires_review_expected) if requires_review_expected else None
        ),
        "requires_review_expected_n": len(requires_review_expected),
        "false_safe_count": len(false_safe_rows),
        "false_safe_rows": false_safe_rows,
        "false_escalation_count": len(false_escalation_rows),
        "false_escalation_rows": false_escalation_rows,
        "non_deterministic_count": len(non_deterministic_rows),
        "non_deterministic_rows": non_deterministic_rows,
    }


def failures_by_tag(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    by_tag: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in data["rows"]:
        is_failure = (
            not r["state_correct"]
            or not r["provision_detection_correct"]
            or (r.get("trigger_types_scored") and not r.get("trigger_types_correct"))
            or (r.get("fee_scored") and not r.get("fee_correct"))
            or (r.get("survival_scored") and not r.get("survival_correct"))
        )
        if is_failure:
            for tag in r["tags"]:
                by_tag[tag].append(r)
    return by_tag


def render_report(data: Dict[str, Any], summary: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Termination Policy Engine — Benchmark Report\n")
    lines.append(f"Corpus size: **{summary['total_cases']}** cases across "
                  f"{len({t for r in data['rows'] for t in r['tags']})} drafting-pattern tags. "
                  f"Third clause adapter — see benchmarks/policy_engine_core_architecture_report.md "
                  f"for what this run revealed about the shared core's reusability.\n")

    fs = summary["false_safe_count"]
    lines.append("## Headline safety metric\n")
    lines.append(f"**False-safe rate: {fs} / {summary['total_cases']} ({fs / summary['total_cases']:.1%})**\n")
    if fs:
        for r in summary["false_safe_rows"]:
            lines.append(f"- `{r['id']}` (tags: {', '.join(r['tags'])}) — expected `{r['expected_state']}`, got `{r['actual_state']}`")
        lines.append("")
    else:
        lines.append("Zero false-safe cases in this run.\n")

    fe = summary["false_escalation_count"]
    lines.append("## False-escalation\n")
    lines.append(f"**False-escalation rate: {fe} / {summary['total_cases']} ({fe / summary['total_cases']:.1%})**\n")
    if fe:
        for r in summary["false_escalation_rows"]:
            lines.append(f"- `{r['id']}` (tags: {', '.join(r['tags'])}) — expected `{r['expected_state']}`, got `{r['actual_state']}`")
        lines.append("")
    else:
        lines.append("Zero false-escalation cases in this run.\n")

    determinism_pct = 1 - summary["non_deterministic_count"] / summary["total_cases"]

    lines.append("## Metrics\n")
    lines.append("| Metric | Result | Scored on |")
    lines.append("|---|---|---|")
    lines.append(f"| Provision detection | {summary['provision_detection_accuracy']:.1%} | {summary['total_cases']} (all cases) |")
    if summary["trigger_type_accuracy"] is not None:
        lines.append(f"| Trigger-type coverage accuracy | {summary['trigger_type_accuracy']:.1%} | {summary['trigger_type_scored_n']} |")
    if summary["fee_accuracy"] is not None:
        lines.append(f"| Termination-fee extraction accuracy | {summary['fee_accuracy']:.1%} | {summary['fee_scored_n']} |")
    if summary["survival_accuracy"] is not None:
        lines.append(f"| Survival-topic accuracy | {summary['survival_accuracy']:.1%} | {summary['survival_scored_n']} |")
    lines.append(f"| Policy-state accuracy | {summary['policy_state_accuracy']:.1%} | {summary['total_cases']} (all cases) |")
    lines.append(f"| False-safe rate | {fs / summary['total_cases']:.1%} | {summary['total_cases']} (all cases) |")
    lines.append(f"| False-escalation rate | {fe / summary['total_cases']:.1%} | {summary['total_cases']} (all cases) |")
    lines.append(f"| Determinism (5x repeat) | {determinism_pct:.1%} | {summary['total_cases']} (all cases) |")
    lines.append("")
    if summary["ambiguity_recall"] is not None:
        lines.append(f"Supplementary: ambiguity detection recall (REQUIRES_REVIEW) — "
                     f"{summary['ambiguity_recall']:.1%} ({summary['requires_review_expected_n']} expected).\n")

    lines.append("## Release gate check\n")
    gates = [
        ("False-safe = 0", fs == 0, str(fs)),
        ("False-escalation = 0", fe == 0, str(fe)),
        ("Determinism = 100%", determinism_pct == 1.0, f"{determinism_pct:.1%}"),
    ]
    for name, passed, value in gates:
        lines.append(f"- {'PASS' if passed else 'FAIL'} — {name} (actual: {value})")
    lines.append(f"\nPolicy-state accuracy and the other extraction-quality metrics are reported "
                 f"honestly above — no fixed target is asserted for them on this first pass.\n")

    if summary["non_deterministic_count"]:
        lines.append("### Non-deterministic cases\n")
        for r in summary["non_deterministic_rows"]:
            lines.append(f"- `{r['id']}`")
        lines.append("")

    lines.append("## Failures by drafting pattern\n")
    by_tag = failures_by_tag(data)
    if not by_tag:
        lines.append("None.\n")
    for tag in sorted(by_tag, key=lambda t: -len(by_tag[t])):
        rows = by_tag[tag]
        lines.append(f"### `{tag}` — {len(rows)} failing case(s)\n")
        for r in rows:
            detail = [f"expected `{r['expected_state']}`, got `{r['actual_state']}`"]
            if not r["provision_detection_correct"]:
                detail.append("provision-detection mismatch")
            if r.get("trigger_types_scored") and not r.get("trigger_types_correct"):
                detail.append("trigger-type mismatch")
            if r.get("fee_scored") and not r.get("fee_correct"):
                detail.append("fee mismatch")
            if r.get("survival_scored") and not r.get("survival_correct"):
                detail.append("survival mismatch")
            marker = " ⚠️ FALSE-SAFE" if r["false_safe"] else (" ⚠️ FALSE-ESCALATION" if r["false_escalation"] else "")
            lines.append(f"- `{r['id']}`{marker}: {'; '.join(detail)}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    data = run()
    summary = summarize(data)
    report = render_report(data, summary)
    print(report)

    if args.out:
        Path(args.out).write_text(report)
        print(f"\nReport written to {args.out}", file=sys.stderr)

    if summary["false_safe_count"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
