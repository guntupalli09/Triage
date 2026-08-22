#!/usr/bin/env python3
"""Step 4A.7 Phase 3 — executes the reciprocal-semantic benchmark and
reports symmetric precision/recall + the hard-required unsafe-false-
symmetry rate (must be 0)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_step4a4_heldout import run_case
from benchmarks.step4a7_reciprocal_semantic_benchmark import CASES

RESOLVED_STATES = {"ACCEPT", "ACCEPT_WITH_NOTE"}


def main():
    tp = fp = tn = fn = 0  # symmetric positive = "resolves automatically"
    unsafe_false_symmetry = []
    unnecessary_asymmetry = []
    for c in CASES:
        decision, _ = run_case("indemnification", c["text"], c["kwargs"])
        resolved = decision.state in RESOLVED_STATES
        if c["expect_symmetric"]:
            if resolved:
                tp += 1
            else:
                fn += 1
                unnecessary_asymmetry.append((c["id"], c["family"], decision.state))
        else:
            if resolved:
                fp += 1
                unsafe_false_symmetry.append((c["id"], c["family"], decision.state))
            else:
                tn += 1

    n = len(CASES)
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    print(f"Total cases: {n}")
    print(f"TP={tp} FP={fp} TN={tn} FN={fn}")
    print(f"Symmetric precision: {precision:.1%}")
    print(f"Symmetric recall: {recall:.1%}")
    print(f"Unsafe false-symmetry rate: {len(unsafe_false_symmetry)}/{n} = {len(unsafe_false_symmetry)/n:.1%}")
    print(f"Unnecessary-asymmetry rate: {len(unnecessary_asymmetry)}/{n} = {len(unnecessary_asymmetry)/n:.1%}")
    print()
    if unsafe_false_symmetry:
        print("=== UNSAFE FALSE-SYMMETRY (HARD FAILURE) ===")
        for row in unsafe_false_symmetry:
            print(" ", row)
    if unnecessary_asymmetry:
        print("=== UNNECESSARY ASYMMETRY (over-escalation, safe but not free) ===")
        for row in unnecessary_asymmetry:
            print(" ", row)
    print()
    print("HARD REQUIREMENT unsafe_false_symmetry == 0:", "PASS" if not unsafe_false_symmetry else "FAIL")


if __name__ == "__main__":
    main()
