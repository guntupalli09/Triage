#!/usr/bin/env python3
"""Step 4A.10.1 Phase 11 — run the fresh adversarial battery, first and
only pass (no tuning after seeing results)."""
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie

CASES = json.load(open(Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_1_fresh_battery.json"))


def classify(case, facts):
    gt = case["label"]
    verified = bool(facts and facts.obligations)
    asymmetry = any(o.asymmetry_reasons for o in facts.obligations) if facts and facts.obligations else False
    reviewed = (facts is None) or (not facts.obligations)

    if gt == "OPERATIVE":
        return "CA" if verified else ("CR" if reviewed else "SM")
    if gt == "NON_OPERATIVE":
        return "CA" if not verified else "WC"
    if gt == "CONTROL":
        return "CA" if not verified else "WC"
    if gt == "SYMMETRIC":
        if verified and not asymmetry:
            return "CA"
        if reviewed or asymmetry:
            return "CR"
        return "WC"
    if gt == "ASYMMETRIC":
        if verified and asymmetry:
            return "CA"
        if reviewed:
            return "CR"
        return "FS"
    if gt == "AMBIGUOUS":
        return "CR" if (reviewed or asymmetry) else "WC"
    if gt == "COMPOUND":
        # ground truth for compound cases is nuanced (decoy + asymmetric genuine term);
        # correct = flagged asymmetric OR routed to review, never a clean unflagged verify
        if verified and not asymmetry:
            return "WC"
        return "CA" if asymmetry else "CR"
    return "UNKNOWN"


def main():
    ie.HYBRID_DISCOVERY_ENABLED = False
    results = {}
    for c in CASES:
        facts = ie.extract_indemnification_facts(c["text"])
        results[c["id"]] = {"classification": classify(c, facts),
                             "verified": bool(facts and facts.obligations),
                             "asymmetry": any(o.asymmetry_reasons for o in facts.obligations) if facts and facts.obligations else False}
    counts = Counter(r["classification"] for r in results.values())
    print(counts)
    for sev_class in ("WC", "FS", "SM"):
        bad = [cid for cid, r in results.items() if r["classification"] == sev_class]
        if bad:
            print(f"{sev_class}: {bad}")
    with open(Path(__file__).resolve().parent.parent / "artifacts" / "step4a10_1" / "fresh_battery_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
