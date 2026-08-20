#!/usr/bin/env python3
"""Step 4A.9.1 Phase 19 — classify PRE (regex-only) vs hybrid on the
Step 4A.9 fresh 103-case battery. Not a new corpus — development replay."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie
from benchmarks.run_step4a4_heldout import run_case

with open(Path(__file__).resolve().parent.parent / "benchmarks" / "step4a9_fresh_battery.json") as f:
    CASES = json.load(f)


def classify(decision, expected):
    got = decision.state
    if got == expected:
        return "MATCH"
    if got == "NOT_APPLICABLE" and expected != "NOT_APPLICABLE":
        return "FALSE_ABSENCE"
    if expected == "NOT_APPLICABLE" and got != "NOT_APPLICABLE":
        return "FALSE_POSITIVE"
    return "MISMATCH"


def run_all(hybrid: bool):
    ie.HYBRID_DISCOVERY_ENABLED = hybrid
    out = {}
    for c in CASES:
        decision, _ = run_case(c["adapter"], c["text"], c["kwargs"])
        out[c["id"]] = classify(decision, c["expected_result"])
    return out


def main():
    pre = run_all(False)
    hybrid = run_all(True)
    recovered, regressed, still_bad = [], [], []
    for cid in pre:
        p, h = pre[cid], hybrid[cid]
        if p != "MATCH" and h == "MATCH":
            recovered.append((cid, p, h))
        elif p == "MATCH" and h != "MATCH":
            regressed.append((cid, p, h))
        elif p != "MATCH" and h != "MATCH":
            still_bad.append((cid, p, h))
    print(f"PRE non-matching: {sum(1 for v in pre.values() if v != 'MATCH')}")
    print(f"HYBRID non-matching: {sum(1 for v in hybrid.values() if v != 'MATCH')}")
    print(f"Recovered by hybrid: {len(recovered)}")
    for r in recovered:
        print(" ", r)
    print(f"Regressed by hybrid: {len(regressed)}")
    for r in regressed:
        print(" ", r)
    print(f"Still non-matching under hybrid: {len(still_bad)}")
    for r in still_bad:
        print(" ", r)
    result = {"pre": pre, "hybrid": hybrid, "recovered": recovered, "regressed": regressed, "still_bad": still_bad}
    with open(Path(__file__).resolve().parent.parent / "artifacts" / "step4a9_1" / "phase19_classification.json", "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
