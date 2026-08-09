#!/usr/bin/env python3
"""
Benchmark harness for the Indemnification policy engine — second clause
adapter, testing whether policy_engine_core.py generalizes. Structurally
mirrors run_liability_benchmark.py (same false-safe/false-escalation/
determinism metrics, imported from the same shared core module) but scores
indemnification-specific facts: monetary treatment, trigger-category
coverage, and directional party identification (measured separately, per
the review's requirement, since indemnification's directionality is not
the same shape as Liability's).

Usage:
    python3 benchmarks/run_indemnification_benchmark.py [--out FILE.md]

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

import indemnification_policy_engine as ie
import policy_engine_core as core
from benchmarks.indemnification_corpus import CASES, DEFAULT_POLICY


@dataclass
class Policy:
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]
    required_protection_triggers_json: Optional[List[str]]
    prohibited_exposure_triggers_json: Optional[List[str]]
    require_exposure_third_party_only: bool
    require_defense_control_for_exposure: bool
    require_notice_and_cooperation_for_exposure: bool
    prohibit_uncapped_exposure: bool
    exposure_preferred_multiplier: Optional[float]
    exposure_acceptable_max_multiplier: Optional[float]
    exposure_negotiate_max_multiplier: Optional[float]


def _build_policy(overrides: Dict[str, Any]) -> Policy:
    merged = dict(DEFAULT_POLICY)
    merged.update(overrides)
    return Policy(**merged)


def _resolved_exposure(facts: Optional[ie.IndemnificationFacts], policy: Policy):
    if facts is None or not facts.obligations:
        return None
    exposure, _, _ = ie._resolve_obligations_for_side(facts.obligations, policy.contract_side)
    return exposure


def _monetary_matches(facts: Optional[ie.IndemnificationFacts], policy: Policy, expected: Any) -> bool:
    if expected is None:
        return facts is None or not facts.obligations
    exposure = _resolved_exposure(facts, policy)
    if exposure is None:
        return False
    m = exposure.monetary
    kind = expected["kind"]
    if m.kind != kind:
        return False
    if kind == "multiplier":
        return abs(m.multiplier - expected["multiplier"]) < 1e-6
    if kind == "fixed":
        return abs(m.fixed_amount - expected["fixed_amount"]) < 1e-6
    return True  # unlimited / not_stated / cross_reference


def run() -> Dict[str, Any]:
    results = []
    for c in CASES:
        policy = _build_policy(c["policy_overrides"])
        facts = ie.extract_indemnification_facts(c["text"])
        decision = ie.evaluate_indemnification_policy(facts, policy, source="Benchmark v1")

        row: Dict[str, Any] = {
            "id": c["id"], "tags": c["tags"], "notes": c["notes"],
            "expected_state": c["expected_state"], "actual_state": decision.state,
            "state_correct": decision.state == c["expected_state"],
        }

        if c["expected_exposure_monetary"] != "SKIP":
            row["monetary_scored"] = True
            row["monetary_correct"] = _monetary_matches(facts, policy, c["expected_exposure_monetary"])
        else:
            row["monetary_scored"] = False

        exposure = _resolved_exposure(facts, policy)
        trig_results = {}
        for trig, expected_treatment in c["expected_trigger_treatments"].items():
            actual = None
            if exposure is not None and trig in exposure.trigger_treatments:
                actual = exposure.trigger_treatments[trig].treatment
            trig_results[trig] = {"expected": expected_treatment, "actual": actual, "correct": actual == expected_treatment}
        row["trigger_results"] = trig_results

        if c["expected_protection_present"] != "SKIP":
            _, protection, _ = (
                ie._resolve_obligations_for_side(facts.obligations, policy.contract_side)
                if facts is not None and facts.obligations else (None, None, [])
            )
            row["protection_scored"] = True
            row["protection_correct"] = (protection is not None) == c["expected_protection_present"]
        else:
            row["protection_scored"] = False

        if c["expected_direction"] != "SKIP":
            row["direction_scored"] = True
            if exposure is None:
                row["direction_correct"] = c["expected_direction"] is None
            else:
                row["direction_correct"] = (
                    (exposure.indemnifying_role, exposure.indemnified_role) == tuple(c["expected_direction"])
                )
        else:
            row["direction_scored"] = False

        row["false_safe"] = core.is_false_safe(c["expected_state"], decision.state)
        row["false_escalation"] = core.is_false_escalation(c["expected_state"], decision.state)

        def _evaluate_once(text=c["text"], policy=policy):
            f = ie.extract_indemnification_facts(text)
            return ie.evaluate_indemnification_policy(f, policy, source="Benchmark v1")

        row["deterministic"] = core.check_deterministic(_evaluate_once, repeats=5)

        results.append(row)
    return {"rows": results}


def summarize(data: Dict[str, Any]) -> Dict[str, Any]:
    rows = data["rows"]
    n = len(rows)

    state_correct = sum(1 for r in rows if r["state_correct"])

    mon_scored = [r for r in rows if r["monetary_scored"]]
    mon_correct = sum(1 for r in mon_scored if r["monetary_correct"])

    trig_total = sum(len(r["trigger_results"]) for r in rows)
    trig_correct = sum(sum(1 for v in r["trigger_results"].values() if v["correct"]) for r in rows)

    prot_scored = [r for r in rows if r["protection_scored"]]
    prot_correct = sum(1 for r in prot_scored if r["protection_correct"])

    dir_scored = [r for r in rows if r["direction_scored"]]
    dir_correct = sum(1 for r in dir_scored if r["direction_correct"])

    requires_review_expected = [r for r in rows if r["expected_state"] == core.REQUIRES_REVIEW]

    false_safe_rows = [r for r in rows if r["false_safe"]]
    false_escalation_rows = [r for r in rows if r["false_escalation"]]
    non_deterministic_rows = [r for r in rows if not r["deterministic"]]

    return {
        "total_cases": n,
        "policy_state_accuracy": state_correct / n if n else 0.0,
        "monetary_accuracy": mon_correct / len(mon_scored) if mon_scored else None,
        "monetary_scored_n": len(mon_scored),
        "trigger_accuracy": trig_correct / trig_total if trig_total else None,
        "trigger_scored_n": trig_total,
        "protection_presence_accuracy": prot_correct / len(prot_scored) if prot_scored else None,
        "protection_scored_n": len(prot_scored),
        "direction_accuracy": dir_correct / len(dir_scored) if dir_scored else None,
        "direction_scored_n": len(dir_scored),
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
            or (r["monetary_scored"] and not r["monetary_correct"])
            or any(not v["correct"] for v in r["trigger_results"].values())
            or (r["protection_scored"] and not r["protection_correct"])
            or (r["direction_scored"] and not r["direction_correct"])
        )
        if is_failure:
            for tag in r["tags"]:
                by_tag[tag].append(r)
    return by_tag


def render_report(data: Dict[str, Any], summary: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Indemnification Policy Engine — Benchmark Report\n")
    lines.append(f"Corpus size: **{summary['total_cases']}** cases across "
                  f"{len({t for r in data['rows'] for t in r['tags']})} drafting-pattern tags. "
                  f"Second clause adapter — see benchmarks/policy_engine_core_architecture_report.md "
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

    lines.append("## Metrics\n")
    lines.append("| Metric | Result |")
    lines.append("|---|---|")
    lines.append(f"| Policy-state accuracy | {summary['policy_state_accuracy']:.1%} ({summary['total_cases']} cases) |")
    if summary["direction_accuracy"] is not None:
        lines.append(f"| Direction/party identification accuracy | {summary['direction_accuracy']:.1%} ({summary['direction_scored_n']} scored) |")
    if summary["trigger_accuracy"] is not None:
        lines.append(f"| Trigger/coverage-category accuracy | {summary['trigger_accuracy']:.1%} ({summary['trigger_scored_n']} scored) |")
    if summary["monetary_accuracy"] is not None:
        lines.append(f"| Monetary-treatment extraction accuracy | {summary['monetary_accuracy']:.1%} ({summary['monetary_scored_n']} scored) |")
    if summary["protection_presence_accuracy"] is not None:
        lines.append(f"| Protection-obligation presence accuracy | {summary['protection_presence_accuracy']:.1%} ({summary['protection_scored_n']} scored) |")
    if summary["ambiguity_recall"] is not None:
        lines.append(f"| Ambiguity detection recall (REQUIRES_REVIEW) | {summary['ambiguity_recall']:.1%} ({summary['requires_review_expected_n']} expected) |")
    lines.append(f"| False-safe rate | {fs / summary['total_cases']:.1%} |")
    lines.append(f"| False-escalation rate | {fe / summary['total_cases']:.1%} |")
    determinism_pct = 1 - summary["non_deterministic_count"] / summary["total_cases"]
    lines.append(f"| Determinism (5x repeat) | {determinism_pct:.1%} |")
    lines.append("")

    lines.append("## Release gate check\n")
    gates = [
        ("False-safe = 0", fs == 0, str(fs)),
        ("False-escalation = 0", fe == 0, str(fe)),
        ("Determinism = 100%", determinism_pct == 1.0, f"{determinism_pct:.1%}"),
    ]
    for name, passed, value in gates:
        lines.append(f"- {'PASS' if passed else 'FAIL'} — {name} (actual: {value})")
    lines.append(f"\nPolicy-state accuracy reported honestly above ({summary['policy_state_accuracy']:.1%}) — "
                 f"no fixed target was set for a first pass on a second, less-tuned adapter; the false-safe "
                 f"and false-escalation gates are the ones that must hold.\n")

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
            if r["monetary_scored"] and not r["monetary_correct"]:
                detail.append("monetary mismatch")
            bad_trig = [k for k, v in r["trigger_results"].items() if not v["correct"]]
            if bad_trig:
                detail.append(f"trigger mismatch: {', '.join(bad_trig)}")
            if r["protection_scored"] and not r["protection_correct"]:
                detail.append("protection-presence mismatch")
            if r["direction_scored"] and not r["direction_correct"]:
                detail.append("direction mismatch")
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
