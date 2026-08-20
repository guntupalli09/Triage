#!/usr/bin/env python3
"""Step 4A.10.2 Phase 7/9 — run dev controls for the 2 root-cause families."""
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import indemnification_policy_engine as ie

CASES = json.load(open(Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_2_dev_controls.json"))


def classify(case, facts):
    gt = case["label"]
    verified = bool(facts and facts.obligations)
    asymmetry = any(o.asymmetry_reasons for o in facts.obligations) if facts and facts.obligations else False
    reviewed = (facts is None) or (not facts.obligations)
    if gt == "SYMMETRIC":
        if verified and not asymmetry:
            return "CS"
        return "FA" if (verified and asymmetry) else "CR"
    if gt == "ASYMMETRIC":
        if verified and asymmetry:
            return "CA"
        if reviewed:
            return "CR"
        return "FS"
    if gt == "AMBIGUOUS":
        return "CR" if (reviewed or asymmetry) else "WC"
    return "UNKNOWN"


def main():
    ie.HYBRID_DISCOVERY_ENABLED = False
    results = {}
    for c in CASES:
        facts = ie.extract_indemnification_facts(c["text"])
        results[c["id"]] = {"classification": classify(c, facts),
                             "verified": bool(facts and facts.obligations),
                             "asymmetry_reasons": (facts.obligations[0].asymmetry_reasons if facts and facts.obligations else [])}
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    by_fam = {}
    for c in CASES:
        by_fam.setdefault(c["family"], Counter())[results[c["id"]]["classification"]] += 1
    print(f"=== DEV CONTROLS ({label}) ===")
    for fam, counts in by_fam.items():
        print(fam, dict(counts))
    overall = Counter(r["classification"] for r in results.values())
    print("overall:", dict(overall))
    with open(Path(__file__).resolve().parent.parent / "artifacts" / "step4a10_2" / f"dev_controls_{label}.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
