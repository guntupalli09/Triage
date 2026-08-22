#!/usr/bin/env python3
"""Step 4A.10.1 Phase 2/4 — run the operative/non-operative benchmark
(regex-only; no semantic calls needed to test structuring-regex context
discrimination)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie

BENCH = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_1_s4_benchmark.json"
CASES = json.load(open(BENCH))


def run():
    ie.HYBRID_DISCOVERY_ENABLED = False
    results = {}
    for c in CASES:
        facts = ie.extract_indemnification_facts(c["text"])
        if facts is None:
            outcome = "CONFIRMED_ABSENT"
            n_obl = 0
        elif facts.obligations:
            outcome = "PRESENT_AND_VERIFIED"
            n_obl = len(facts.obligations)
        else:
            outcome = facts.absence_state
            n_obl = 0
        results[c["id"]] = {"outcome": outcome, "n_obligations": n_obl}
    return results


def summarize(results, label):
    print(f"\n=== {label} ===")
    op = [c for c in CASES if c["label"] == "OPERATIVE"]
    nonop = [c for c in CASES if c["label"] == "NON_OPERATIVE"]
    mixed = [c for c in CASES if c["label"] == "MIXED"]

    op_verified = sum(1 for c in op if results[c["id"]]["outcome"] == "PRESENT_AND_VERIFIED")
    print(f"OPERATIVE (n={len(op)}): recall (clean VERIFIED) = {op_verified}/{len(op)} = {op_verified/len(op):.1%}")

    nonop_rejected = sum(1 for c in nonop if results[c["id"]]["outcome"] in ("CONFIRMED_ABSENT", "PRESENT_BUT_UNRESOLVED", "RECOGNITION_UNCERTAIN"))
    nonop_false_verified = sum(1 for c in nonop if results[c["id"]]["outcome"] == "PRESENT_AND_VERIFIED")
    print(f"NON_OPERATIVE (n={len(nonop)}): correctly NOT clean-verified = {nonop_rejected}/{len(nonop)} = {nonop_rejected/len(nonop):.1%}")
    print(f"  false operative extraction (clean VERIFIED on non-operative text) = {nonop_false_verified}")
    for c in nonop:
        if results[c["id"]]["outcome"] == "PRESENT_AND_VERIFIED":
            print(f"    S4 case: {c['id']} [{c['family']}]")

    mixed_verified = sum(1 for c in mixed if results[c["id"]]["outcome"] == "PRESENT_AND_VERIFIED")
    print(f"MIXED (n={len(mixed)}): clean VERIFIED (should find the genuine operative term) = {mixed_verified}/{len(mixed)} = {mixed_verified/len(mixed):.1%}")


if __name__ == "__main__":
    results = run()
    summarize(results, "S4 BENCHMARK")
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    with open(Path(__file__).resolve().parent.parent / "artifacts" / "step4a10_1" / f"s4_benchmark_{label}.json", "w") as f:
        json.dump(results, f, indent=2)
