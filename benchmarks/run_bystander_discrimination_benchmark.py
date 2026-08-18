#!/usr/bin/env python3
"""Runs benchmarks/bystander_discrimination_benchmark.py against
policy_engine_core.resolve_role_side."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import policy_engine_core as pec
from benchmarks.bystander_discrimination_benchmark import CASES


def run():
    tp = fp = fn = tn = 0
    rows = []
    for case_id, role, text, expected_side, is_positive, note in CASES:
        side, reason = pec.resolve_role_side(role, text)
        if is_positive:
            # Positive: either a specific side must be confirmed, or (when
            # expected_side is None) a genuine CONFLICT reason is required.
            if expected_side is None:
                ok = side is None and reason is not None
            else:
                ok = side == expected_side
            if ok:
                tp += 1
            else:
                fn += 1
        else:
            # Negative: bystander-only text must resolve to the GENERIC
            # mapping with no escalation reason at all.
            ok = side == expected_side and reason is None
            if ok:
                tn += 1
            else:
                fp += 1
        rows.append((case_id, is_positive, side, reason, ok, note))

    n_pos = sum(1 for c in CASES if c[4])
    n_neg = sum(1 for c in CASES if not c[4])
    recall = tp / n_pos if n_pos else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    fp_rate = fp / n_neg if n_neg else float("nan")
    fn_rate = fn / n_pos if n_pos else float("nan")

    print(f"Corpus size: {len(CASES)} ({n_pos} positive, {n_neg} negative)\n")
    for case_id, is_positive, side, reason, ok, note in rows:
        if not ok:
            print(f"| {case_id} | {'positive' if is_positive else 'negative'} | side={side} reason={reason!r} | MISS | {note}")
    print(f"\nRecall (genuine evidence correctly resolved): {recall:.1%} ({tp}/{n_pos})")
    print(f"Precision: {precision:.1%} ({tp}/{tp+fp})" if (tp + fp) else "Precision: N/A")
    print(f"False-negative rate: {fn_rate:.1%} ({fn}/{n_pos})")
    print(f"False-positive rate (bystander wrongly escalated/misresolved): {fp_rate:.1%} ({fp}/{n_neg})")
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "recall": recall, "precision": precision}


if __name__ == "__main__":
    run()
