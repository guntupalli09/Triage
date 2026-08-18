#!/usr/bin/env python3
"""Measures whether payment_terms_policy_engine's set-off/mutual-debt-
netting detection (facts.setoff_permitted or facts.setoff_prohibited)
engages on benchmarks/setoff_concept_benchmark.py. Run PRE and POST the
Step 4A.5 SM-CRITICAL fix."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import payment_terms_policy_engine as pte
from benchmarks.setoff_concept_benchmark import CASES


def run():
    tp = fp = fn = tn = 0
    rows = []
    for case_id, text, is_positive, note in CASES:
        facts = pte.extract_payment_facts(text)
        detected = bool(facts and facts.setoff_permitted is not None)
        if is_positive and detected:
            tp += 1
        elif is_positive and not detected:
            fn += 1
        elif not is_positive and detected:
            fp += 1
        else:
            tn += 1
        rows.append((case_id, is_positive, detected, note))

    n_pos = sum(1 for c in CASES if c[2])
    n_neg = sum(1 for c in CASES if not c[2])
    recall = tp / n_pos if n_pos else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    fn_rate = fn / n_pos if n_pos else float("nan")
    fp_rate = fp / n_neg if n_neg else float("nan")

    print(f"Corpus size: {len(CASES)} ({n_pos} positive, {n_neg} negative)\n")
    for case_id, is_positive, detected, note in rows:
        ok = "OK" if (is_positive == detected) else "MISS"
        if ok == "MISS":
            print(f"| {case_id} | {'positive' if is_positive else 'negative'} | detected={detected} | {ok} | {note}")
    print(f"\nRecall: {recall:.1%} ({tp}/{n_pos})")
    print(f"Precision: {precision:.1%} ({tp}/{tp+fp})" if (tp + fp) else "Precision: N/A")
    print(f"False-negative rate: {fn_rate:.1%} ({fn}/{n_pos})")
    print(f"False-positive rate: {fp_rate:.1%} ({fp}/{n_neg})")
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "recall": recall, "precision": precision}


if __name__ == "__main__":
    run()
