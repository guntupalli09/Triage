#!/usr/bin/env python3
"""Runs benchmarks/role_boundary_benchmark.py against
indemnification_policy_engine.extract_indemnification_facts, embedding
each case's role fragment into a full obligation sentence and checking
that the extracted indemnifying_role matches the expected role EXACTLY
(neither truncated nor over-captured)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie
from benchmarks.role_boundary_benchmark import CASES


def _build_sentence(role_fragment: str) -> str:
    if role_fragment.isupper():
        return f"8. INDEMNIFICATION. {role_fragment} SHALL INDEMNIFY, DEFEND, AND HOLD HARMLESS COUNTERPARTY FROM THIRD-PARTY CLAIMS ARISING FROM NEGLIGENCE, UP TO A CAP OF 1 TIMES THE FEES PAID."
    return f"8. Indemnification. {role_fragment} shall indemnify, defend, and hold harmless Counterparty from third-party claims arising from negligence, up to a cap of 1 times the fees paid."


def run():
    tp = fp = fn = tn = 0
    rows = []
    for case_id, fragment, _kind, is_positive, note in CASES:
        text = _build_sentence(fragment)
        facts = ie.extract_indemnification_facts(text)
        extracted = facts.obligations[0].indemnifying_role if (facts and facts.obligations) else None
        expected_role = fragment.split("(")[0].strip() if not is_positive and "(" in fragment else fragment
        # For negative cases the "expected" is the correctly-bounded
        # short name — success means extracted == expected_role (i.e.
        # the boundary did NOT over-capture the nearby entity/connector).
        # For positive cases, success means the full multi-word name was
        # captured without truncation.
        correct = extracted is not None and extracted.strip() == expected_role.strip()
        if is_positive and correct:
            tp += 1
        elif is_positive and not correct:
            fn += 1
        elif not is_positive and correct:
            tn += 1
        else:
            fp += 1
        rows.append((case_id, is_positive, extracted, expected_role, correct, note))

    n_pos = sum(1 for c in CASES if c[3])
    n_neg = sum(1 for c in CASES if not c[3])
    recall = tp / n_pos if n_pos else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    fp_rate = fp / n_neg if n_neg else float("nan")
    fn_rate = fn / n_pos if n_pos else float("nan")

    print(f"Corpus size: {len(CASES)} ({n_pos} positive, {n_neg} negative)\n")
    for case_id, is_positive, extracted, expected_role, correct, note in rows:
        if not correct:
            print(f"| {case_id} | {'positive' if is_positive else 'negative'} | extracted={extracted!r} expected={expected_role!r} | MISS | {note}")
    print(f"\nExact-boundary recall (positives): {recall:.1%} ({tp}/{n_pos})")
    print(f"Precision: {precision:.1%} ({tp}/{tp+fp})" if (tp + fp) else "Precision: N/A")
    print(f"False-negative rate (positives): {fn_rate:.1%} ({fn}/{n_pos})")
    print(f"False-positive rate (over-capture on negatives): {fp_rate:.1%} ({fp}/{n_neg})")
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "recall": recall, "precision": precision}


if __name__ == "__main__":
    run()
