#!/usr/bin/env python3
"""Step 4A.7.2 — executes the role-attribution benchmark. Hard requirement:
zero false-safe (a true-positive that resolves cleanly) and zero
unnecessary escalation on ordinary role mappings."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_step4a4_heldout import run_case
from benchmarks.step4a7_2_role_attribution_benchmark import CASES

REVIEW_STATES = {"REQUIRES_REVIEW"}


def main():
    false_safe = []
    unnecessary_review = []
    for c in CASES:
        decision, _ = run_case("liability", c["text"], c["kwargs"])
        reviewed = decision.state in REVIEW_STATES
        if c["expect_review"] and not reviewed:
            false_safe.append((c["id"], c["family"], decision.state))
        elif not c["expect_review"] and reviewed:
            unnecessary_review.append((c["id"], c["family"], decision.state))

    n = len(CASES)
    print(f"Total cases: {n}")
    print(f"False-safe (true positive not escalated): {len(false_safe)}/{n}")
    print(f"Unnecessary review (negative control escalated): {len(unnecessary_review)}/{n}")
    print()
    if false_safe:
        print("=== FALSE-SAFE (HARD FAILURE) ===")
        for row in false_safe:
            print(" ", row)
    if unnecessary_review:
        print("=== UNNECESSARY REVIEW (regression) ===")
        for row in unnecessary_review:
            print(" ", row)
    print()
    print("HARD REQUIREMENT false_safe == 0:", "PASS" if not false_safe else "FAIL")
    print("HARD REQUIREMENT unnecessary_review == 0:", "PASS" if not unnecessary_review else "FAIL")


if __name__ == "__main__":
    main()
