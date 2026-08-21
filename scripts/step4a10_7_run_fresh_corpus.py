#!/usr/bin/env python3
"""Step 4A.10.5 (relock 5b) — the AUTHORITATIVE, untouched FROZEN execution
corpus. First and only pass. No tuning after results."""
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import indemnification_policy_engine as ie

CASES = json.load(open(Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_7_fresh_independent_corpus.json"))


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
        cls = classify(c, facts)
        results[c["id"]] = {
            "classification": cls,
            "verified": bool(facts and facts.obligations),
            "asymmetry_reasons": (facts.obligations[0].asymmetry_reasons if facts and facts.obligations else []),
        }

    with open(Path(__file__).resolve().parent.parent / "artifacts" / "step4a10_7" / "frozen_corpus_results.json", "w") as f:
        json.dump(results, f, indent=2)

    overall = Counter(r["classification"] for r in results.values())
    print("=== OVERALL ===")
    print(dict(overall))

    print("\n=== BY TIER (asymmetric+symmetric only) ===")
    for tier in ["1", "2", "3"]:
        ids = [c["id"] for c in CASES if c["tier"] == tier and c["label"] in ("SYMMETRIC", "ASYMMETRIC")]
        counts = Counter(results[cid]["classification"] for cid in ids)
        print(f"Tier {tier} (n={len(ids)}):", dict(counts))

    print("\n=== BY DIMENSION FAMILY (asymmetric only) ===")
    fam_ids = {}
    for c in CASES:
        if c["label"] == "ASYMMETRIC":
            for d in c["dimensions"]:
                fam_ids.setdefault(d, []).append(c["id"])
    for fam, ids in fam_ids.items():
        counts = Counter(results[cid]["classification"] for cid in ids)
        print(f"  {fam} (n={len(ids)}):", dict(counts))

    fs_ids = [cid for cid, r in results.items() if r["classification"] == "FS"]
    print(f"\nFS (dangerous) total: {len(fs_ids)}")
    for cid in fs_ids:
        c = next(c for c in CASES if c["id"] == cid)
        print(f"  {cid} [{c['dimensions']}] tier={c['tier']}: {c['text'][:100]}")


if __name__ == "__main__":
    main()
