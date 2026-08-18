#!/usr/bin/env python3
"""Runs benchmarks/indemnification_asymmetry_benchmark.py against
indemnification_policy_engine.extract_indemnification_facts() and checks
whether the mutual/reciprocal obligation's asymmetry_reasons is non-empty
as expected. Cases with expect=None are non-mutual (no mechanism engaged)
or genuinely ambiguous — reported but not scored pass/fail."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie
from benchmarks.indemnification_asymmetry_benchmark import CASES


def run():
    correct = total_scored = false_safe = 0
    rows = []
    for case_id, text, expect in CASES:
        facts = ie.extract_indemnification_facts(text)
        reciprocal = [o for o in (facts.obligations if facts else []) if o.is_mutual_reciprocal]
        detected = bool(reciprocal and reciprocal[0].asymmetry_reasons)
        if expect is None:
            note = "informational (non-mutual or ambiguous) — not scored"
        else:
            total_scored += 1
            ok = detected == expect
            if ok:
                correct += 1
            if expect is True and not detected:
                false_safe += 1  # a real asymmetry went undetected -> treated as symmetric
            note = "OK" if ok else "FAIL"
        rows.append((case_id, expect, detected, note))

    print(f"Corpus size: {len(CASES)} ({total_scored} scored, {len(CASES) - total_scored} informational)\n")
    print("| id | expected | detected | note |")
    print("|---|---|---|---|")
    for case_id, expect, detected, note in rows:
        print(f"| {case_id} | {expect} | {detected} | {note} |")
    print(f"\nScored correct: {correct}/{total_scored} ({correct/total_scored:.1%})" if total_scored else "")
    print(f"False-safe (real asymmetry undetected): {false_safe}")
    return {"correct": correct, "total_scored": total_scored, "false_safe": false_safe}


if __name__ == "__main__":
    run()
