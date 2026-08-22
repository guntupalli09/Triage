#!/usr/bin/env python3
"""Runs benchmarks/step4a5_adversarial_battery.py, reusing
run_step4a4_heldout.run_case (same policy defaults as the frozen
corpus runner) and bucketing outcomes the same way
classify_step4a4.py does, so results are directly comparable."""
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.step4a5_adversarial_battery import CASES
from benchmarks.run_step4a4_heldout import run_case

CLEAN_STATES = {"ACCEPT", "ACCEPT_WITH_NOTE", "NEGOTIATE", "MUST_REDLINE", "PROHIBITED", "ESCALATE"}


def classify(label, state):
    if state == "NOT_APPLICABLE":
        return "SM"
    if state == "REQUIRES_REVIEW":
        return "CR" if label == "SHOULD_REVIEW" else "FE"
    if state in CLEAN_STATES:
        return "WC" if label == "SHOULD_REVIEW" else "CA"
    return "MANUAL"


def run():
    by_family = defaultdict(Counter)
    details = []
    for case_id, family, adapter, text, kwargs, label, note in CASES:
        decision, our_position = run_case(adapter, text, kwargs)
        bucket = classify(label, decision.state)
        by_family[family][bucket] += 1
        details.append((case_id, family, adapter, label, decision.state, bucket, note))

    print(f"{'Family':<18}{'Cases':<7}{'CA':<5}{'CR':<5}{'FE':<5}{'WC':<5}{'SM':<5}")
    totals = Counter()
    for family in ("safety", "silent_miss", "false_escalation", "compound"):
        c = by_family[family]
        n = sum(c.values())
        totals.update(c)
        print(f"{family:<18}{n:<7}{c['CA']:<5}{c['CR']:<5}{c['FE']:<5}{c['WC']:<5}{c['SM']:<5}")
    n = sum(totals.values())
    print(f"{'TOTAL':<18}{n:<7}{totals['CA']:<5}{totals['CR']:<5}{totals['FE']:<5}{totals['WC']:<5}{totals['SM']:<5}")

    print("\n--- Individual WC/SM (manual inspection required) ---")
    for case_id, family, adapter, label, state, bucket, note in details:
        if bucket in ("WC", "SM"):
            print(f"| {case_id} [{family}/{adapter}] label={label} state={state} bucket={bucket} | {note}")

    print("\n--- Individual FE (for reference) ---")
    for case_id, family, adapter, label, state, bucket, note in details:
        if bucket == "FE":
            print(f"| {case_id} [{family}/{adapter}] label={label} state={state} | {note}")

    return by_family, details


if __name__ == "__main__":
    run()
