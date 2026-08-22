#!/usr/bin/env python3
"""Step 4A.9 — indemnification recognition benchmark runner. Measures
discovery recall/precision, false absence, and (where a positive resolves)
obligation-structuring accuracy (actor/beneficiary/direction)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie
from benchmarks.run_step4a4_heldout import IndemPolicy

with open(Path(__file__).resolve().parent / "step4a9_recognition_benchmark.json") as f:
    CASES = json.load(f)


def main():
    tp = fp = tn = fn = 0
    actor_correct = actor_total = 0
    beneficiary_correct = beneficiary_total = 0
    rows = []
    for c in CASES:
        facts = ie.extract_indemnification_facts(c["text"])
        discovered = facts is not None and len(facts.obligations) > 0
        if c["label"] == "positive":
            if discovered:
                tp += 1
            else:
                fn += 1
        else:
            if discovered:
                fp += 1
            else:
                tn += 1

        if c["label"] == "positive" and discovered and c.get("actor"):
            actor_total += 1
            obligation = facts.obligations[0]
            if obligation.indemnifying_role.strip().lower() in c["actor"].strip().lower() or \
                    c["actor"].strip().lower() in obligation.indemnifying_role.strip().lower():
                actor_correct += 1
        if c["label"] == "positive" and discovered and c.get("beneficiary"):
            beneficiary_total += 1
            obligation = facts.obligations[0]
            if obligation.indemnified_role.strip().lower() in c["beneficiary"].strip().lower() or \
                    c["beneficiary"].strip().lower() in obligation.indemnified_role.strip().lower():
                beneficiary_correct += 1

        rows.append((c["id"], c["label"], discovered))

    n_pos = tp + fn
    n_neg = tn + fp
    print(f"Total: {len(CASES)} ({n_pos} positive, {n_neg} negative)")
    print(f"Discovery recall (TP/positives): {tp}/{n_pos} = {100*tp/n_pos:.1f}%")
    print(f"Discovery precision (TP/(TP+FP)): {tp}/{tp+fp} = {100*tp/(tp+fp) if tp+fp else 0:.1f}%")
    print(f"False absence (FN/positives): {fn}/{n_pos} = {100*fn/n_pos:.1f}%")
    print(f"False positive (FP/negatives): {fp}/{n_neg} = {100*fp/n_neg:.1f}%")
    if actor_total:
        print(f"Actor accuracy (of discovered positives): {actor_correct}/{actor_total} = "
              f"{100*actor_correct/actor_total:.1f}%")
    if beneficiary_total:
        print(f"Beneficiary accuracy (of discovered positives): {beneficiary_correct}/{beneficiary_total} = "
              f"{100*beneficiary_correct/beneficiary_total:.1f}%")
    print()
    print("=== FALSE NEGATIVES (missed positives) ===")
    for id_, label, disc in rows:
        if label == "positive" and not disc:
            print(" ", id_)
    print("=== FALSE POSITIVES (wrongly discovered negatives) ===")
    for id_, label, disc in rows:
        if label == "negative" and disc:
            print(" ", id_)


if __name__ == "__main__":
    main()
