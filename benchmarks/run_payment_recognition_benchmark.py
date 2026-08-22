#!/usr/bin/env python3
"""Measures whether payment_terms_policy_engine.extract_payment_facts()
ENGAGES (returns non-None / clause_found) on the labeled recognition
corpus. Run before AND after Step 4A.3's recognition hardening to show
PRE/POST recall, precision, false-negative rate, false-positive rate."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import payment_terms_policy_engine as pte
from benchmarks.payment_recognition_benchmark import CASES


def run():
    tp = fp = fn = tn = 0
    rows = []
    for case_id, text, is_positive, concept in CASES:
        facts = pte.extract_payment_facts(text)
        recognized = facts is not None and facts.clause_found
        if is_positive and recognized:
            tp += 1
        elif is_positive and not recognized:
            fn += 1
        elif not is_positive and recognized:
            fp += 1
        else:
            tn += 1
        rows.append((case_id, concept, is_positive, recognized))

    n_pos = sum(1 for c in CASES if c[2])
    n_neg = sum(1 for c in CASES if not c[2])
    recall = tp / n_pos if n_pos else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    fn_rate = fn / n_pos if n_pos else float("nan")
    fp_rate = fp / n_neg if n_neg else float("nan")

    print(f"Corpus size: {len(CASES)} ({n_pos} positive, {n_neg} negative)\n")
    print("| id | concept | expected | recognized | ok |")
    print("|---|---|---|---|---|")
    for case_id, concept, is_positive, recognized in rows:
        ok = "OK" if (is_positive == recognized) else "MISS"
        print(f"| {case_id} | {concept} | {'positive' if is_positive else 'negative'} | {recognized} | {ok} |")

    print(f"\nRecall: {recall:.1%} ({tp}/{n_pos})")
    print(f"Precision: {precision:.1%} ({tp}/{tp+fp})" if (tp + fp) else "Precision: N/A")
    print(f"False-negative rate: {fn_rate:.1%} ({fn}/{n_pos})")
    print(f"False-positive rate: {fp_rate:.1%} ({fp}/{n_neg})")
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "recall": recall, "precision": precision}


if __name__ == "__main__":
    run()
