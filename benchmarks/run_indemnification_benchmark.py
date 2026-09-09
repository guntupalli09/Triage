#!/usr/bin/env python3
"""
Benchmark harness for the Indemnification policy engine — second clause
adapter, testing whether policy_engine_core.py generalizes. Structurally
mirrors run_liability_benchmark.py (same false-safe/false-escalation/
determinism metrics, imported from the same shared core module) but scores
indemnification-specific facts.

Per the Phase 1 hardening pass (100+ case corpus), 11 metrics are reported
SEPARATELY rather than folded into a single "accuracy" number, so a strong
number in one dimension (e.g. policy-state accuracy) can't visually paper
over a weak one in another (e.g. indemnitor/indemnitee identification):

  1. Provision detection        (clause found vs. genuinely absent)
  2. Indemnitor identification  (who promises, on our resolved exposure)
  3. Indemnitee identification  (who is promised to, on our resolved exposure)
  4. Directionality             (exposure vs. protection assigned to the right side)
  5. Covered-claim/category extraction (trigger treatments)
  6. Reciprocal/unilateral classification
  7. Monetary/cap treatment extraction
  8. Policy-state accuracy
  9. False-safe rate            (safety gate)
  10. False-escalation rate     (safety gate)
  11. Determinism               (safety gate)

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
    permitted_exposure_triggers_json: Optional[List[str]]
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


def _resolved_exposure_protection(facts: Optional[ie.IndemnificationFacts], policy: Policy):
    if facts is None or not facts.obligations:
        return None, None
    exposure, protection, _ = ie._resolve_obligations_for_side(facts.obligations, policy.contract_side)
    return exposure, protection


def _monetary_matches(exposure, expected: Any) -> bool:
    if expected is None:
        return exposure is None
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


# Tags that mark a case as expecting at least one mutual/reciprocal
# ("each party" / "the parties shall mutually indemnify") obligation to be
# present in extraction. "split_provisions" cases are functionally
# reciprocal in outcome but are drafted as two separate directional
# obligations, not "each party" phrasing — they must NOT classify as
# mutual/reciprocal, which is exactly the distinction this metric checks.
_EXPECT_RECIPROCAL_TAGS = {"reciprocal"}
_EXPECT_NOT_RECIPROCAL_TAGS = {"split_provisions", "asymmetric", "unilateral"}


def _expected_reciprocal_classification(tags: List[str]) -> Optional[bool]:
    tagset = set(tags)
    if tagset & _EXPECT_NOT_RECIPROCAL_TAGS:
        return False
    if tagset & _EXPECT_RECIPROCAL_TAGS:
        return True
    return None  # not asserted for this case


def run() -> Dict[str, Any]:
    results = []
    for c in CASES:
        policy = _build_policy(c["policy_overrides"])
        facts = ie.extract_indemnification_facts(c["text"])
        decision = ie.evaluate_indemnification_policy(facts, policy, source="Benchmark v1")
        exposure, protection = _resolved_exposure_protection(facts, policy)

        row: Dict[str, Any] = {
            "id": c["id"], "tags": c["tags"], "notes": c["notes"],
            "expected_state": c["expected_state"], "actual_state": decision.state,
            "state_correct": decision.state == c["expected_state"],
        }

        # --- 1. Provision detection ---
        # A clause is "detected" when facts is not None and clause_found —
        # independent of whether a directional obligation could be parsed
        # from it. Ground truth: every NOT_APPLICABLE-labeled case in this
        # corpus is NOT_APPLICABLE specifically because no real clause
        # exists (destroyed anchor, explicit negation, or genuine absence);
        # every other label implies the clause itself was found, even if
        # its structure couldn't be parsed (REQUIRES_REVIEW).
        clause_detected = facts is not None and facts.clause_found
        expected_clause_detected = c["expected_state"] != core.NOT_APPLICABLE
        row["provision_detection_correct"] = clause_detected == expected_clause_detected

        # --- 2 & 3. Indemnitor / indemnitee identification ---
        if c["expected_direction"] != "SKIP":
            row["direction_scored"] = True
            if exposure is None:
                indemnitor_correct = c["expected_direction"] is None
                indemnitee_correct = c["expected_direction"] is None
            else:
                indemnitor_correct = exposure.indemnifying_role == c["expected_direction"][0]
                indemnitee_correct = exposure.indemnified_role == c["expected_direction"][1]
            row["indemnitor_correct"] = indemnitor_correct
            row["indemnitee_correct"] = indemnitee_correct
        else:
            row["direction_scored"] = False

        # --- 4. Directionality (exposure/protection assigned to the right side) ---
        directionality_checks = []
        if c["expected_direction"] != "SKIP":
            if exposure is None:
                directionality_checks.append(c["expected_direction"] is None)
            else:
                directionality_checks.append(
                    (exposure.indemnifying_role, exposure.indemnified_role) == tuple(c["expected_direction"])
                )
        if c["expected_protection_present"] != "SKIP":
            directionality_checks.append((protection is not None) == c["expected_protection_present"])
        if directionality_checks:
            row["directionality_scored"] = True
            row["directionality_correct"] = all(directionality_checks)
        else:
            row["directionality_scored"] = False
        # kept for the pre-existing protection-presence table row
        if c["expected_protection_present"] != "SKIP":
            row["protection_scored"] = True
            row["protection_correct"] = (protection is not None) == c["expected_protection_present"]
        else:
            row["protection_scored"] = False

        # --- 5. Covered-claim / category (trigger) extraction ---
        trig_results = {}
        for trig, expected_treatment in c["expected_trigger_treatments"].items():
            actual = None
            if exposure is not None and trig in exposure.trigger_treatments:
                actual = exposure.trigger_treatments[trig].treatment
            trig_results[trig] = {"expected": expected_treatment, "actual": actual, "correct": actual == expected_treatment}
        row["trigger_results"] = trig_results

        # --- 6. Reciprocal / unilateral classification ---
        expected_reciprocal = _expected_reciprocal_classification(c["tags"])
        if expected_reciprocal is not None and facts is not None:
            actual_reciprocal = any(o.is_mutual_reciprocal for o in facts.obligations)
            row["reciprocal_scored"] = True
            row["reciprocal_correct"] = actual_reciprocal == expected_reciprocal
        else:
            row["reciprocal_scored"] = False

        # --- 7. Monetary/cap treatment ---
        if c["expected_exposure_monetary"] != "SKIP":
            row["monetary_scored"] = True
            row["monetary_correct"] = _monetary_matches(exposure, c["expected_exposure_monetary"])
        else:
            row["monetary_scored"] = False

        # --- 8-10. Policy-state / false-safe / false-escalation ---
        row["false_safe"] = core.is_false_safe(c["expected_state"], decision.state)
        row["false_escalation"] = core.is_false_escalation(c["expected_state"], decision.state)

        # --- 11. Determinism ---
        def _evaluate_once(text=c["text"], policy=policy):
            f = ie.extract_indemnification_facts(text)
            return ie.evaluate_indemnification_policy(f, policy, source="Benchmark v1")

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

    indemnitor_acc, indemnitor_n = _rate("direction_scored", "indemnitor_correct")
    indemnitee_acc, indemnitee_n = _rate("direction_scored", "indemnitee_correct")
    directionality_acc, directionality_n = _rate("directionality_scored", "directionality_correct")
    reciprocal_acc, reciprocal_n = _rate("reciprocal_scored", "reciprocal_correct")
    monetary_acc, monetary_n = _rate("monetary_scored", "monetary_correct")
    prot_acc, prot_n = _rate("protection_scored", "protection_correct")

    trig_total = sum(len(r["trigger_results"]) for r in rows)
    trig_correct = sum(sum(1 for v in r["trigger_results"].values() if v["correct"]) for r in rows)

    requires_review_expected = [r for r in rows if r["expected_state"] == core.REQUIRES_REVIEW]

    false_safe_rows = [r for r in rows if r["false_safe"]]
    false_escalation_rows = [r for r in rows if r["false_escalation"]]
    non_deterministic_rows = [r for r in rows if not r["deterministic"]]

    return {
        "total_cases": n,

        "provision_detection_accuracy": provision_correct / n if n else 0.0,

        "indemnitor_accuracy": indemnitor_acc, "indemnitor_scored_n": indemnitor_n,
        "indemnitee_accuracy": indemnitee_acc, "indemnitee_scored_n": indemnitee_n,
        "directionality_accuracy": directionality_acc, "directionality_scored_n": directionality_n,

        "trigger_accuracy": trig_correct / trig_total if trig_total else None,
        "trigger_scored_n": trig_total,

        "reciprocal_classification_accuracy": reciprocal_acc, "reciprocal_scored_n": reciprocal_n,

        "monetary_accuracy": monetary_acc, "monetary_scored_n": monetary_n,

        "policy_state_accuracy": state_correct / n if n else 0.0,

        "protection_presence_accuracy": prot_acc, "protection_scored_n": prot_n,

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
            or (r.get("direction_scored") and (not r.get("indemnitor_correct") or not r.get("indemnitee_correct")))
            or (r.get("directionality_scored") and not r.get("directionality_correct"))
            or (r.get("reciprocal_scored") and not r.get("reciprocal_correct"))
            or (r.get("monetary_scored") and not r.get("monetary_correct"))
            or (r.get("protection_scored") and not r.get("protection_correct"))
            or any(not v["correct"] for v in r["trigger_results"].values())
        )
        if is_failure:
            for tag in r["tags"]:
                by_tag[tag].append(r)
    return by_tag


def render_report(data: Dict[str, Any], summary: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Indemnification Policy Engine — Benchmark Report (Phase 1 expansion)\n")
    lines.append(f"Corpus size: **{summary['total_cases']}** cases across "
                  f"{len({t for r in data['rows'] for t in r['tags']})} drafting-pattern tags "
                  f"(expanded from 43 to {summary['total_cases']} per the Phase 1 adversarial "
                  f"hardening pass). Second clause adapter — see "
                  f"benchmarks/policy_engine_core_architecture_report.md for what this run revealed "
                  f"about the shared core's reusability.\n")

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

    lines.append("## 11 metrics, reported separately\n")
    lines.append("| # | Metric | Result | Scored on |")
    lines.append("|---|---|---|---|")
    lines.append(f"| 1 | Provision detection | {summary['provision_detection_accuracy']:.1%} | {summary['total_cases']} (all cases) |")
    if summary["indemnitor_accuracy"] is not None:
        lines.append(f"| 2 | Indemnitor identification | {summary['indemnitor_accuracy']:.1%} | {summary['indemnitor_scored_n']} |")
    if summary["indemnitee_accuracy"] is not None:
        lines.append(f"| 3 | Indemnitee identification | {summary['indemnitee_accuracy']:.1%} | {summary['indemnitee_scored_n']} |")
    if summary["directionality_accuracy"] is not None:
        lines.append(f"| 4 | Directionality (exposure vs. protection) | {summary['directionality_accuracy']:.1%} | {summary['directionality_scored_n']} |")
    if summary["trigger_accuracy"] is not None:
        lines.append(f"| 5 | Covered-claim/category extraction | {summary['trigger_accuracy']:.1%} | {summary['trigger_scored_n']} |")
    if summary["reciprocal_classification_accuracy"] is not None:
        lines.append(f"| 6 | Reciprocal/unilateral classification | {summary['reciprocal_classification_accuracy']:.1%} | {summary['reciprocal_scored_n']} |")
    if summary["monetary_accuracy"] is not None:
        lines.append(f"| 7 | Monetary/cap treatment | {summary['monetary_accuracy']:.1%} | {summary['monetary_scored_n']} |")
    lines.append(f"| 8 | Policy-state accuracy | {summary['policy_state_accuracy']:.1%} | {summary['total_cases']} (all cases) |")
    lines.append(f"| 9 | False-safe rate | {fs / summary['total_cases']:.1%} | {summary['total_cases']} (all cases) |")
    lines.append(f"| 10 | False-escalation rate | {fe / summary['total_cases']:.1%} | {summary['total_cases']} (all cases) |")
    lines.append(f"| 11 | Determinism (5x repeat) | {determinism_pct:.1%} | {summary['total_cases']} (all cases) |")
    lines.append("")
    if summary["protection_presence_accuracy"] is not None:
        lines.append(f"Supplementary (not one of the 11): protection-obligation presence accuracy — "
                     f"{summary['protection_presence_accuracy']:.1%} ({summary['protection_scored_n']} scored).\n")
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
                 f"honestly above — no fixed target is asserted for them. Per instruction, this pass "
                 f"deliberately optimized for finding real failures with a corpus that was NOT "
                 f"authored or debugged against this implementation's output; a lower number here "
                 f"than the first 43-case pass is expected and is not itself a regression to fix "
                 f"by relabeling.\n")

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
            if r.get("direction_scored") and not r.get("indemnitor_correct"):
                detail.append("indemnitor mismatch")
            if r.get("direction_scored") and not r.get("indemnitee_correct"):
                detail.append("indemnitee mismatch")
            if r.get("directionality_scored") and not r.get("directionality_correct"):
                detail.append("directionality mismatch")
            if r.get("reciprocal_scored") and not r.get("reciprocal_correct"):
                detail.append("reciprocal/unilateral classification mismatch")
            if r["monetary_scored"] and not r["monetary_correct"]:
                detail.append("monetary mismatch")
            bad_trig = [k for k, v in r["trigger_results"].items() if not v["correct"]]
            if bad_trig:
                detail.append(f"trigger mismatch: {', '.join(bad_trig)}")
            if r["protection_scored"] and not r["protection_correct"]:
                detail.append("protection-presence mismatch")
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
