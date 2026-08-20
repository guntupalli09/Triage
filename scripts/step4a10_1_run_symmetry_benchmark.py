#!/usr/bin/env python3
"""Step 4A.10.1 Phase 7/10 — run the false-symmetry benchmark."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie

BENCH = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_1_symmetry_benchmark.json"
CASES = json.load(open(BENCH))


def classify(case, facts):
    gt = case["label"]
    if facts is None or not facts.obligations:
        got_review = True
        asymmetry_found = False
    else:
        asymmetry_found = any(o.asymmetry_reasons for o in facts.obligations)
        got_review = False

    if gt == "AMBIGUOUS":
        return "CR" if (got_review or asymmetry_found) else "FE_missed_ambiguity"
    if gt == "SYMMETRIC":
        if asymmetry_found:
            return "FA"
        if got_review:
            return "CR"
        return "CS"
    if gt == "ASYMMETRIC":
        if asymmetry_found:
            return "CA"
        if got_review:
            return "CR"
        return "FS"  # dangerous: asymmetric but neither flagged nor routed to review
    return "UNKNOWN"


def run():
    ie.HYBRID_DISCOVERY_ENABLED = False
    results = {}
    for c in CASES:
        facts = ie.extract_indemnification_facts(c["text"])
        cls = classify(c, facts)
        reasons = []
        if facts and facts.obligations:
            for o in facts.obligations:
                reasons.extend(o.asymmetry_reasons)
        results[c["id"]] = {"classification": cls, "asymmetry_reasons": reasons,
                             "n_obligations": len(facts.obligations) if facts else 0}
    return results


def summarize(results, label):
    from collections import Counter
    print(f"\n=== {label} ===")
    counts = Counter(r["classification"] for r in results.values())
    print(dict(counts))
    fs_cases = [cid for cid, r in results.items() if r["classification"] == "FS"]
    print(f"FS (False Symmetry, dangerous) count: {len(fs_cases)}")
    for cid in fs_cases:
        c = next(c for c in CASES if c["id"] == cid)
        print(f"  {cid} [{c['dimension']}]: {c['text'][:100]}")
    return counts


if __name__ == "__main__":
    results = run()
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    summarize(results, f"SYMMETRY BENCHMARK ({label})")
    with open(Path(__file__).resolve().parent.parent / "artifacts" / "step4a10_1" / f"symmetry_benchmark_{label}.json", "w") as f:
        json.dump(results, f, indent=2)
