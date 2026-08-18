#!/usr/bin/env python3
"""Step 4A.6 — FIRST independent frozen held-out execution against the
FROZEN Step 4A.5 implementation (commit 0c4ae54). Does not modify any
production file. Reuses run_step4a4_heldout.run_case (the same policy-
construction and evaluation harness used for the prior two independent
validations) for methodological consistency. Prints raw actual output
for every case, auditable against the locked label/ground-truth fields."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_step4a4_heldout import run_case
from benchmarks.step4a6_corpus import ALL_CASES
from benchmarks.step4a6_formatting_mutations import MUT_CASES


def main():
    for c in ALL_CASES:
        decision, our_position = run_case(c["adapter"], c["text"], c["kwargs"])
        print(f"\n=== {c['id']} [{c['adapter']}/tier{c['tier']}/{c['family']}] label={c['label']} ===")
        print(f"STATE: {decision.state}")
        print(f"extracted_summary: {decision.extracted_summary!r}")
        print(f"unresolved_facts: {decision.unresolved_facts}")
        print(f"our_position: {our_position}")
        print(f"CONCEPT: {c['concept']}")
        print(f"EXPECTED_RESULT: {c['expected_result']}")
        print(f"REASON: {c['reason']}")

    print("\n\n########## FORMATTING MUTATIONS ##########")
    for m in MUT_CASES:
        decision, our_position = run_case(m["adapter"], m["text"], m["kwargs"])
        print(f"\n=== {m['id']} (base={m['base']}, {m['mutation_type']}) ===")
        print(f"STATE: {decision.state}")
        print(f"extracted_summary: {decision.extracted_summary!r}")
        print(f"unresolved_facts: {decision.unresolved_facts}")


if __name__ == "__main__":
    main()
