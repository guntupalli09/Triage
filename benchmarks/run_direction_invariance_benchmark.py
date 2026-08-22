#!/usr/bin/env python3
"""Runs benchmarks/direction_invariance_benchmark.py against
indemnification_policy_engine.evaluate_indemnification_policy, using
the same policy dataclass shape as run_step4a4_heldout.py."""
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie
from benchmarks.direction_invariance_benchmark import CASES
from benchmarks.run_step4a4_heldout import IndemPolicy


CLEAN_STATES = {"ACCEPT", "ACCEPT_WITH_NOTE", "NEGOTIATE", "MUST_REDLINE", "PROHIBITED", "ESCALATE"}


def run():
    unsafe_automatic = 0
    unnecessary_review = 0
    correct = 0
    rows = []
    for case_id, text, kwargs, expected_bucket, note in CASES:
        policy = IndemPolicy(**kwargs)
        facts = ie.extract_indemnification_facts(text)
        decision = ie.evaluate_indemnification_policy(facts, policy)
        actual_bucket = "REQUIRES_REVIEW" if decision.state == "REQUIRES_REVIEW" else (
            "AUTOMATIC" if decision.state in CLEAN_STATES else "OTHER"
        )
        ok = actual_bucket == expected_bucket
        if ok:
            correct += 1
        elif expected_bucket == "REQUIRES_REVIEW" and actual_bucket == "AUTOMATIC":
            unsafe_automatic += 1
        elif expected_bucket == "AUTOMATIC" and actual_bucket == "REQUIRES_REVIEW":
            unnecessary_review += 1
        rows.append((case_id, expected_bucket, actual_bucket, decision.state, ok, note))

    print(f"Corpus size: {len(CASES)}\n")
    for case_id, expected_bucket, actual_bucket, state, ok, note in rows:
        if not ok:
            tag = "UNSAFE-AUTOMATIC" if (expected_bucket == "REQUIRES_REVIEW" and actual_bucket == "AUTOMATIC") else "MISS"
            print(f"| {case_id} | expected={expected_bucket} actual={actual_bucket} ({state}) | {tag} | {note}")
    print(f"\nCorrect-automatic-on-invariant / correct-review-on-sensitive: {correct}/{len(CASES)} ({correct/len(CASES):.1%})")
    print(f"Unsafe-automatic count (direction-sensitive case resolved automatically): {unsafe_automatic}")
    print(f"Unnecessary-review count (direction-invariant case escalated): {unnecessary_review}")
    return {"correct": correct, "total": len(CASES), "unsafe_automatic": unsafe_automatic, "unnecessary_review": unnecessary_review}


if __name__ == "__main__":
    run()
