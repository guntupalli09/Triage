#!/usr/bin/env python3
"""Runs benchmarks/liability_ownership_benchmark.py against
liability_policy_engine.extract_liability_facts() and checks the
controlling provision's general_cap_expression against the expected
value/review outcome."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import liability_policy_engine as lpe
from benchmarks.liability_ownership_benchmark import CASES


def run():
    correct = 0
    false_safe = 0
    rows = []
    for case_id, text, expected_value, expect_review in CASES:
        facts = lpe.extract_liability_facts(text)
        cp = facts.controlling_provision if facts else None
        cap = cp.general_cap_expression if cp else None
        # A confident value requires BOTH no unresolved_reason AND at
        # least one component actually extracted — an empty component
        # list with no unresolved_reason means "no cap-shaped value found
        # near any liability concept at all" (safe: flows to MUST_REDLINE
        # downstream), which is review-safe, not a confidently-adopted
        # wrong value.
        reviewed = cap is None or bool(cap.unresolved_reason or not cap.components)
        value = cap.raw_excerpt if (cap and not reviewed) else None
        ok = (reviewed == expect_review) and (expect_review or (expected_value or "").strip() and expected_value.strip() in (value or ""))
        if expect_review and not reviewed:
            false_safe += 1  # a confident wrong/unverified value was adopted where review was required
        if ok:
            correct += 1
        rows.append((case_id, expect_review, reviewed, expected_value, value, ok))

    print(f"Corpus size: {len(CASES)}\n")
    print("| id | expect_review | got_review | expected_value | got_value | ok |")
    print("|---|---|---|---|---|---|")
    for case_id, exp_r, got_r, exp_v, got_v, ok in rows:
        print(f"| {case_id} | {exp_r} | {got_r} | {exp_v} | {got_v!r} | {'OK' if ok else 'FAIL'} |")
    print(f"\nCorrect: {correct}/{len(CASES)} ({correct/len(CASES):.1%})")
    print(f"False-safe (review required but confident value adopted): {false_safe}")
    return {"correct": correct, "total": len(CASES), "false_safe": false_safe}


if __name__ == "__main__":
    run()
