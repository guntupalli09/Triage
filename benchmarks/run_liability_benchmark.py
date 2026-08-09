#!/usr/bin/env python3
"""
Benchmark harness for the Limitation-of-Liability policy engine.

Scores structured fact extraction and final policy-state evaluation
independently against benchmarks/liability_corpus.py's labeled corpus, then
reports metrics with the false-safe rate — how often the engine returns
ACCEPT/ACCEPT_WITH_NOTE when the correct answer required attorney
attention — as the headline number. Overall accuracy is informative but
secondary: a system that is 95% accurate but produces even one confident
false ACCEPT is worse for this product than one that is 80% accurate and
never does.

Usage:
    python3 benchmarks/run_liability_benchmark.py [--verbose] [--out FILE.md]

Exit code is non-zero only when the false-safe count is non-zero — that is
the release gate. Overall-accuracy shortfalls are reported but do not fail
the run; several corpus categories are deliberately structured beyond
today's extraction model (greater-of/lesser-of, per-claim vs aggregate,
cross-references, amendments) specifically to surface those gaps for
review, not to be silently "fixed" by loosening the scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import liability_policy_engine as lpe
from benchmarks.liability_corpus import CASES, DEFAULT_POLICY

FALSE_SAFE_EXPECTED_STATES = {
    lpe.NEGOTIATE, lpe.MUST_REDLINE, lpe.PROHIBITED, lpe.ESCALATE, lpe.REQUIRES_REVIEW,
}
FALSE_SAFE_ACTUAL_STATES = {lpe.ACCEPT, lpe.ACCEPT_WITH_NOTE}


@dataclass
class Policy:
    preferred_multiplier: Optional[float]
    acceptable_max_multiplier: Optional[float]
    negotiate_max_multiplier: Optional[float]
    prohibit_unlimited: bool
    required_exceptions_json: Optional[List[str]]
    fallback_text: Optional[str]
    escalation_approval_authority: Optional[str]
    contract_side: str


def _build_policy(overrides: Dict[str, Any]) -> Policy:
    merged = dict(DEFAULT_POLICY)
    merged.update(overrides)
    return Policy(**merged)


def _general_cap_matches(facts: Optional[lpe.LiabilityFacts], expected: Any) -> bool:
    if expected is None:
        return facts is None
    if facts is None:
        return False
    kind = expected["kind"]
    if kind == "not_stated":
        return facts.general_cap is None and facts.general_cap_established
    if kind == "unresolved":
        return not facts.general_cap_established
    if facts.general_cap is None or facts.general_cap.kind != kind:
        return False
    if kind == "fee_multiplier":
        return abs(facts.general_cap.multiplier - expected["multiplier"]) < 1e-6
    if kind == "fixed_amount":
        return abs(facts.general_cap.fixed_amount - expected["fixed_amount"]) < 1e-6
    return True  # "unlimited"


def _decision_hash(decision: lpe.PolicyDecision) -> str:
    return hashlib.sha256(json.dumps(decision.as_dict(), sort_keys=True).encode()).hexdigest()


def run() -> Dict[str, Any]:
    results = []
    for c in CASES:
        policy = _build_policy(c["policy_overrides"])
        facts = lpe.extract_liability_facts(c["text"])
        decision = lpe.evaluate_liability_policy(facts, policy, source="Benchmark v1")

        row: Dict[str, Any] = {
            "id": c["id"], "tags": c["tags"], "notes": c["notes"],
            "expected_state": c["expected_state"], "actual_state": decision.state,
            "state_correct": decision.state == c["expected_state"],
        }

        if c["expected_general_cap"] != "SKIP":
            row["general_cap_scored"] = True
            row["general_cap_correct"] = _general_cap_matches(facts, c["expected_general_cap"])
        else:
            row["general_cap_scored"] = False

        cat_results = {}
        for cat, expected_treatment in c["expected_category_treatments"].items():
            actual = None
            if facts is not None and cat in facts.category_treatments:
                actual = facts.category_treatments[cat].treatment
            cat_results[cat] = {"expected": expected_treatment, "actual": actual, "correct": actual == expected_treatment}
        row["category_results"] = cat_results

        if c["expected_consequential_excluded"] != "SKIP":
            actual_cd = facts.consequential_damages_excluded if facts is not None else None
            row["consequential_scored"] = True
            row["consequential_correct"] = actual_cd == c["expected_consequential_excluded"]
        else:
            row["consequential_scored"] = False

        if c["expected_mutuality"] != "SKIP":
            actual_mut = facts.mutuality if facts is not None else None
            row["mutuality_scored"] = True
            row["mutuality_correct"] = actual_mut == c["expected_mutuality"]
        else:
            row["mutuality_scored"] = False

        row["false_safe"] = (
            c["expected_state"] in FALSE_SAFE_EXPECTED_STATES and decision.state in FALSE_SAFE_ACTUAL_STATES
        )

        # Determinism: re-run 5x, hash the full decision dict each time.
        hashes = {_decision_hash(decision)}
        for _ in range(4):
            f2 = lpe.extract_liability_facts(c["text"])
            d2 = lpe.evaluate_liability_policy(f2, policy, source="Benchmark v1")
            hashes.add(_decision_hash(d2))
        row["deterministic"] = len(hashes) == 1

        results.append(row)
    return {"rows": results}


def summarize(data: Dict[str, Any]) -> Dict[str, Any]:
    rows = data["rows"]
    n = len(rows)

    state_correct = sum(1 for r in rows if r["state_correct"])

    gc_scored = [r for r in rows if r["general_cap_scored"]]
    gc_correct = sum(1 for r in gc_scored if r["general_cap_correct"])

    cat_total = sum(len(r["category_results"]) for r in rows)
    cat_correct = sum(sum(1 for v in r["category_results"].values() if v["correct"]) for r in rows)

    conseq_scored = [r for r in rows if r["consequential_scored"]]
    conseq_correct = sum(1 for r in conseq_scored if r["consequential_correct"])

    requires_review_expected = [r for r in rows if r["expected_state"] == lpe.REQUIRES_REVIEW]
    requires_review_caught = sum(1 for r in requires_review_expected if r["actual_state"] == lpe.REQUIRES_REVIEW)

    false_safe_rows = [r for r in rows if r["false_safe"]]
    non_deterministic_rows = [r for r in rows if not r["deterministic"]]

    return {
        "total_cases": n,
        "policy_state_accuracy": state_correct / n if n else 0.0,
        "general_cap_accuracy": gc_correct / len(gc_scored) if gc_scored else None,
        "general_cap_scored_n": len(gc_scored),
        "category_treatment_accuracy": cat_correct / cat_total if cat_total else None,
        "category_treatment_scored_n": cat_total,
        "consequential_accuracy": conseq_correct / len(conseq_scored) if conseq_scored else None,
        "consequential_scored_n": len(conseq_scored),
        "ambiguity_recall": (
            len([r for r in requires_review_expected if r["actual_state"] == lpe.REQUIRES_REVIEW])
            / len(requires_review_expected) if requires_review_expected else None
        ),
        "requires_review_expected_n": len(requires_review_expected),
        "requires_review_caught_n": requires_review_caught,
        "false_safe_count": len(false_safe_rows),
        "false_safe_rows": false_safe_rows,
        "non_deterministic_count": len(non_deterministic_rows),
        "non_deterministic_rows": non_deterministic_rows,
    }


def failures_by_tag(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    by_tag: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in data["rows"]:
        is_failure = (
            not r["state_correct"]
            or (r["general_cap_scored"] and not r["general_cap_correct"])
            or any(not v["correct"] for v in r["category_results"].values())
            or (r["consequential_scored"] and not r["consequential_correct"])
        )
        if is_failure:
            for tag in r["tags"]:
                by_tag[tag].append(r)
    return by_tag


def render_report(data: Dict[str, Any], summary: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Limitation of Liability Policy Engine — Benchmark Report\n")
    lines.append(f"Corpus size: **{summary['total_cases']}** cases across "
                  f"{len({t for r in data['rows'] for t in r['tags']})} drafting-pattern tags.\n")

    lines.append("## Headline safety metric\n")
    fs = summary["false_safe_count"]
    lines.append(f"**False-safe rate: {fs} / {summary['total_cases']} "
                 f"({fs / summary['total_cases']:.1%})** — cases where the correct answer required "
                 f"attorney attention (NEGOTIATE / MUST_REDLINE / PROHIBITED / ESCALATE / "
                 f"REQUIRES_REVIEW) but the engine returned ACCEPT or ACCEPT_WITH_NOTE.\n")
    if fs:
        lines.append("**This is the release gate. Any non-zero count here blocks release "
                      "regardless of overall accuracy.**\n")
        for r in summary["false_safe_rows"]:
            lines.append(f"- `{r['id']}` (tags: {', '.join(r['tags'])}) — expected "
                         f"`{r['expected_state']}`, got `{r['actual_state']}`")
        lines.append("")
    else:
        lines.append("Zero false-safe cases in this run.\n")

    lines.append("## Metrics\n")
    lines.append("| Metric | Result | Target |")
    lines.append("|---|---|---|")
    lines.append(f"| Policy-state accuracy | {summary['policy_state_accuracy']:.1%} ({summary['total_cases']} cases) | >95% |")
    if summary["general_cap_accuracy"] is not None:
        lines.append(f"| General-cap extraction accuracy | {summary['general_cap_accuracy']:.1%} ({summary['general_cap_scored_n']} scored) | >98% |")
    if summary["category_treatment_accuracy"] is not None:
        lines.append(f"| Category-treatment accuracy | {summary['category_treatment_accuracy']:.1%} ({summary['category_treatment_scored_n']} scored) | >95% |")
    if summary["consequential_accuracy"] is not None:
        lines.append(f"| Consequential-damages-exclusion accuracy | {summary['consequential_accuracy']:.1%} ({summary['consequential_scored_n']} scored) | — |")
    if summary["ambiguity_recall"] is not None:
        lines.append(f"| Ambiguity detection recall (REQUIRES_REVIEW) | {summary['ambiguity_recall']:.1%} ({summary['requires_review_caught_n']}/{summary['requires_review_expected_n']}) | very high |")
    lines.append(f"| False-safe rate | {fs / summary['total_cases']:.1%} ({fs}/{summary['total_cases']}) | ≈0% |")
    lines.append(f"| Determinism (5x repeat, byte-identical) | {summary['total_cases'] - summary['non_deterministic_count']}/{summary['total_cases']} identical | 100% |")
    lines.append("")

    if summary["non_deterministic_count"]:
        lines.append("### Non-deterministic cases (should never happen — investigate immediately)\n")
        for r in summary["non_deterministic_rows"]:
            lines.append(f"- `{r['id']}`")
        lines.append("")

    lines.append("## Failures by drafting pattern\n")
    lines.append("Grouped by tag so recurring gaps in one drafting pattern are visible together, "
                  "rather than as N isolated case failures. Extraction logic was not modified to "
                  "force individual cases to pass — these are the actual current gaps.\n")
    by_tag = failures_by_tag(data)
    for tag in sorted(by_tag, key=lambda t: -len(by_tag[t])):
        rows = by_tag[tag]
        lines.append(f"### `{tag}` — {len(rows)} failing case(s)\n")
        for r in rows:
            detail = [f"expected state `{r['expected_state']}`, got `{r['actual_state']}`"]
            if r["general_cap_scored"] and not r["general_cap_correct"]:
                detail.append("general-cap extraction mismatch")
            bad_cats = [k for k, v in r["category_results"].items() if not v["correct"]]
            if bad_cats:
                detail.append(f"category mismatch: {', '.join(bad_cats)}")
            if r["consequential_scored"] and not r["consequential_correct"]:
                detail.append("consequential-damages fact mismatch")
            marker = " ⚠️ FALSE-SAFE" if r["false_safe"] else ""
            lines.append(f"- `{r['id']}`{marker}: {'; '.join(detail)}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
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
