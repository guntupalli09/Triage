#!/usr/bin/env python3
"""Step 4A.8 — single frozen execution of the locked independent corpus
against production code. Captures raw output only; no classification here."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_step4a4_heldout import run_case
from benchmarks.step4a8_corpus import CASES, MUTATIONS


def dump_decision(d, our_position):
    return dict(
        state=d.state,
        extracted_summary=d.extracted_summary,
        unresolved_facts=list(d.unresolved_facts),
        explanation=d.explanation,
        our_position=our_position,
        controlling_provision=d.controlling_provision,
        category_treatments=d.category_treatments,
    )


def main():
    print(f"# Step 4A.8 held-out run — {len(CASES)} semantic + {len(MUTATIONS)} formatting mutations\n")
    for c in CASES:
        decision, our_position = run_case(c["adapter"], c["text"], c["kwargs"])
        out = dump_decision(decision, our_position)
        print(f"=== {c['id']} [{c['adapter']}/tier{c['tier']}/{','.join(c['families'])}] "
              f"gt_result={c['expected_result']} gt_review={c['review']} ===")
        print(f"STATE: {out['state']}")
        print(f"extracted_summary: {out['extracted_summary']!r}")
        print(f"unresolved_facts: {out['unresolved_facts']}")
        print(f"our_position: {out['our_position']}")
        print(f"explanation: {out['explanation']}")
        print()

    print(f"\n# FORMATTING MUTATIONS — {len(MUTATIONS)}\n")
    for m in MUTATIONS:
        decision, our_position = run_case(m["adapter"], m["text"], m["kwargs"])
        out = dump_decision(decision, our_position)
        print(f"=== {m['id']} base={m['base_id']} kind={m['mutation_kind']} "
              f"gt_result={m['expected_result']} ===")
        print(f"STATE: {out['state']}")
        print(f"extracted_summary: {out['extracted_summary']!r}")
        print(f"unresolved_facts: {out['unresolved_facts']}")
        print()


if __name__ == "__main__":
    main()
