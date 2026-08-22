#!/usr/bin/env python3
"""Step 4A.9 Phase 13 — fresh development battery runner."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_step4a4_heldout import run_case

with open(Path(__file__).resolve().parent / "step4a9_fresh_battery.json") as f:
    CASES = json.load(f)


def main():
    for c in CASES:
        decision, our_position = run_case(c["adapter"], c["text"], c["kwargs"])
        print(f"=== {c['id']} [{c['adapter']}] gt={c['expected_result']} note={c['note']} ===")
        print(f"STATE: {decision.state}")
        print(f"extracted_summary: {decision.extracted_summary!r}")
        print(f"unresolved_facts: {decision.unresolved_facts}")
        print(f"explanation: {decision.explanation}")
        print()


if __name__ == "__main__":
    main()
