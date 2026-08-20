#!/usr/bin/env python3
"""Step 4A.9.1 Phases 7 & 12 — regex-only baseline vs hybrid A/B on the
locked 200-case benchmark (benchmarks/step4a9_1_benchmark.json)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie

with open(Path(__file__).resolve().parent.parent / "benchmarks" / "step4a9_1_benchmark.json") as f:
    CASES = json.load(f)


def recognition_outcome(text: str) -> str:
    facts = ie.extract_indemnification_facts(text)
    if facts is None:
        return "CONFIRMED_ABSENT"
    if facts.obligations:
        return "PRESENT_AND_VERIFIED"
    return facts.absence_state  # PRESENT_BUT_UNRESOLVED or RECOGNITION_UNCERTAIN


def run(hybrid: bool):
    ie.HYBRID_DISCOVERY_ENABLED = hybrid
    results = {}
    for c in CASES:
        results[c["id"]] = recognition_outcome(c["text"])
    return results


def metrics(results, label="POSITIVE"):
    by_id = {c["id"]: c for c in CASES}
    cases = [c for c in CASES if c["label"] == label]
    n = len(cases)
    outcomes = {"PRESENT_AND_VERIFIED": 0, "PRESENT_BUT_UNRESOLVED": 0, "RECOGNITION_UNCERTAIN": 0, "CONFIRMED_ABSENT": 0}
    for c in cases:
        outcomes[results[c["id"]]] += 1
    return n, outcomes


def by_family(results):
    fam = {}
    for c in CASES:
        fam.setdefault(c["family"], {"n": 0, "verified": 0, "unresolved": 0, "absent": 0})
        fam[c["family"]]["n"] += 1
        o = results[c["id"]]
        if o == "PRESENT_AND_VERIFIED":
            fam[c["family"]]["verified"] += 1
        elif o in ("PRESENT_BUT_UNRESOLVED", "RECOGNITION_UNCERTAIN"):
            fam[c["family"]]["unresolved"] += 1
        else:
            fam[c["family"]]["absent"] += 1
    return fam


def main():
    pre = run(False)
    hybrid = run(True)

    for label, results in (("regex-only (PRE)", pre), ("hybrid", hybrid)):
        print(f"\n=== {label} ===")
        n_pos, pos_out = metrics(results, "POSITIVE")
        n_neg, neg_out = metrics(results, "NEGATIVE")
        print(f"POSITIVE (n={n_pos}): {pos_out}")
        recall_verified = pos_out["PRESENT_AND_VERIFIED"] / n_pos
        recall_discovered = (pos_out["PRESENT_AND_VERIFIED"] + pos_out["PRESENT_BUT_UNRESOLVED"] + pos_out["RECOGNITION_UNCERTAIN"]) / n_pos
        false_absence_rate = pos_out["CONFIRMED_ABSENT"] / n_pos
        print(f"  recall (clean VERIFIED): {recall_verified:.1%}")
        print(f"  recall (discovered, verified-or-flagged-for-review): {recall_discovered:.1%}")
        print(f"  false-absence rate: {false_absence_rate:.1%}")
        print(f"NEGATIVE (n={n_neg}): {neg_out}")
        true_negative_rate = neg_out["CONFIRMED_ABSENT"] / n_neg
        false_positive_verified = pos_out and neg_out["PRESENT_AND_VERIFIED"]
        print(f"  true-negative rate: {true_negative_rate:.1%}")
        print(f"  FALSE clean-verified on a hard negative (dangerous): {neg_out['PRESENT_AND_VERIFIED']}")
        print(f"  routed-to-review-unnecessarily (safe but noisy): {neg_out['PRESENT_BUT_UNRESOLVED'] + neg_out['RECOGNITION_UNCERTAIN']}")
        print("By family:")
        for fam, d in sorted(by_family(results).items()):
            print(f"  {fam}: n={d['n']} verified={d['verified']} unresolved={d['unresolved']} absent={d['absent']}")

    out = {"pre": pre, "hybrid": hybrid}
    outdir = Path(__file__).resolve().parent.parent / "artifacts" / "step4a9_1"
    with open(outdir / "phase7_12_ab_results.json", "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
