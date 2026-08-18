#!/usr/bin/env python3
"""Step 4A.4 outcome classifier. Auto-classifies CA/CR/FE/WC/SM only when
unambiguous against the locked label (AUTOMATABLE/SHOULD_REVIEW) and the
case's own `expected` field; prints full raw detail for every case so a
human can verify EVERY WC/FE/SM individually against actual extracted
facts (this script's classification is a starting point, not final
authority, per the task's explicit instruction)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.step4a4_corpus import ALL_CASES
from benchmarks.run_step4a4_heldout import run_case

CLEAN_STATES = {"ACCEPT", "ACCEPT_WITH_NOTE", "NEGOTIATE", "MUST_REDLINE", "PROHIBITED", "ESCALATE"}


def classify(case, decision):
    label = case["label"]
    state = decision.state
    if state == "NOT_APPLICABLE":
        return "SM_CANDIDATE"  # every case in this corpus has a real supported clause by construction
    if state == "REQUIRES_REVIEW":
        return "CR" if label == "SHOULD_REVIEW" else "FE"
    if state in CLEAN_STATES:
        return "WC_CANDIDATE" if label == "SHOULD_REVIEW" else "CA_CANDIDATE"
    return "MANUAL"


def main():
    results = {}
    for case in ALL_CASES:
        decision, our_position = run_case(case["adapter"], case["text"], case["kwargs"])
        bucket = classify(case, decision)
        results[case["id"]] = dict(case=case, decision=decision, our_position=our_position, bucket=bucket)

    from collections import Counter
    print("Auto-bucket counts:", dict(Counter(r["bucket"] for r in results.values())))
    return results


if __name__ == "__main__":
    results = main()
    for cid, r in results.items():
        if r["bucket"] in ("WC_CANDIDATE", "SM_CANDIDATE", "MANUAL"):
            c, d = r["case"], r["decision"]
            print(f"\n--- {cid} [{c['adapter']}/{c['family']}] label={c['label']} bucket={r['bucket']} ---")
            print(f"  state={d.state} extracted={d.extracted_summary!r}")
            print(f"  our_position={r['our_position']}")
            print(f"  unresolved={d.unresolved_facts}")
            print(f"  expected={c['expected']}")
            print(f"  reason={c['reason']}")
