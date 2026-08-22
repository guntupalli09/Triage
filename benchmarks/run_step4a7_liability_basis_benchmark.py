#!/usr/bin/env python3
"""Step 4A.7 Phase 7 — executes the liability basis benchmark. Measures
basis recognition, multiplier value recognition, and false-positive/
false-association rate separately."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_step4a4_heldout import lpe
from benchmarks.step4a7_liability_basis_benchmark import CASES


def main():
    basis_tp = basis_fn = 0
    mult_correct = mult_wrong = 0
    false_association = 0
    failures = []
    for c in CASES:
        facts = lpe.extract_liability_facts(c["text"])
        cp = facts.controlling_provision.general_cap_expression if facts and facts.controlling_provision else None
        components = cp.components if cp else []
        recognized = bool(components)

        if c["family"] == "ordinary_basis":
            if recognized:
                basis_tp += 1
                got_mult = components[0].multiplier if components else None
                if got_mult == c["expect_multiplier"]:
                    mult_correct += 1
                else:
                    mult_wrong += 1
                    failures.append((c["id"], "wrong multiplier", got_mult, c["expect_multiplier"]))
            else:
                basis_fn += 1
                failures.append((c["id"], "basis not recognized", None, c["expect_multiplier"]))
        elif c["family"] in ("negative_control", "false_association"):
            got_mult = components[0].multiplier if components else None
            if c["expect_multiplier"] is None and got_mult is not None:
                false_association += 1
                failures.append((c["id"], "false association", got_mult, None))

    n_ordinary = sum(1 for c in CASES if c["family"] == "ordinary_basis")
    n_neg = sum(1 for c in CASES if c["family"] in ("negative_control", "false_association"))
    print(f"Total cases: {len(CASES)} ({n_ordinary} ordinary_basis, {n_neg} negative/false-association)")
    print(f"Basis recognition recall: {basis_tp}/{n_ordinary} = {basis_tp/n_ordinary:.1%}")
    print(f"Multiplier-value correctness (of recognized): {mult_correct}/{basis_tp} = {mult_correct/basis_tp:.1%}" if basis_tp else "n/a")
    print(f"False-association rate (negative controls wrongly adopted): {false_association}/{n_neg} = {false_association/n_neg:.1%}")
    print()
    if failures:
        print("=== FAILURES ===")
        for f in failures:
            print(" ", f)


if __name__ == "__main__":
    main()
