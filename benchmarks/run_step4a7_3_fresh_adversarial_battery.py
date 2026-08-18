#!/usr/bin/env python3
"""Step 4A.7.3 — executes the fresh adversarial battery (120 cases, six
families) exactly once against current production code. This is a held-out
run: no fixing based on results, no re-running except to verify determinism.
Prints raw decisions to seed manual CA/CR/FE/WC/SM classification with S1-S4
severity; nothing here is final authority.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_step4a4_heldout import run_case
from benchmarks.step4a7_3_fresh_adversarial_battery import CASES


def main():
    by_family = {}
    for c in CASES:
        decision, our_position = run_case(c["adapter"], c["text"], c["kwargs"])
        by_family.setdefault(c["family"], []).append((c, decision, our_position))

    total = 0
    for family, rows in by_family.items():
        print(f"=== family: {family} ({len(rows)} cases) ===")
        for c, decision, our_position in rows:
            total += 1
            print(f"[{c['id']}] adapter={c['adapter']} tier={c.get('tier')} label={c['label']}")
            print(f"    concept: {c['concept']}")
            print(f"    reason: {c['reason']}")
            print(f"    expected_result: {c['expected_result']}")
            print(f"    STATE: {decision.state}")
            print(f"    extracted_summary: {decision.extracted_summary!r}")
            print(f"    unresolved_facts: {decision.unresolved_facts}")
            print(f"    our_position: {our_position}")
            print(f"    explanation: {decision.explanation}")
        print()
    print(f"TOTAL CASES RUN: {total}")


if __name__ == "__main__":
    main()
