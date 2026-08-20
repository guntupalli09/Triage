#!/usr/bin/env python3
"""Step 4A.10 Phase 26/27 — semantic variability + three-level determinism.
Reduced sample size (30 docs, not 75) and run count (5, not 10) under the
task's own "if API cost/runtime permits" / "prefer 10 if feasible"
allowance -- disclosed explicitly, not a hidden shortcut."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie
import semantic_discovery_real as sdr

ROOT = Path(__file__).resolve().parent.parent
CASES = json.load(open(ROOT / "benchmarks" / "step4a10_benchmark.json"))
N_RUNS = 5

by_bucket = {"tier1": [], "tier2": [], "tier3": [], "negative": [], "noncanonical": []}
for c in CASES:
    if c["label"] == "NEGATIVE" and not c.get("injection"):
        by_bucket["negative"].append(c)
    elif c["label"] == "POSITIVE":
        by_bucket[f"tier{c['tier']}"].append(c)
        if not c["canonical"]:
            by_bucket["noncanonical"].append(c)

SAMPLE = []
seen_ids = set()
for bucket, n in [("tier1", 8), ("tier2", 6), ("tier3", 6), ("negative", 6), ("noncanonical", 4)]:
    for c in by_bucket[bucket][:n]:
        if c["id"] not in seen_ids:
            SAMPLE.append(c)
            seen_ids.add(c["id"])
SAMPLE = SAMPLE[:30]


def run_once(text):
    ie.HYBRID_DISCOVERY_ENABLED = True
    ie.SEMANTIC_PROVIDER = "REAL"
    facts = ie.extract_indemnification_facts(text)
    if facts is None:
        return "CONFIRMED_ABSENT", []
    return (("PRESENT_AND_VERIFIED" if facts.obligations else facts.absence_state),
            [o.discovery_source for o in facts.obligations])


def main():
    results = {}
    t0 = time.perf_counter()
    for i, c in enumerate(SAMPLE):
        runs = []
        for _ in range(N_RUNS):
            outcome, sources = run_once(c["text"])
            runs.append({"outcome": outcome, "sources": sources})
        results[c["id"]] = {"label": c["label"], "tier": c.get("tier"), "runs": runs}
        print(f"  {i + 1}/{len(SAMPLE)} done ({time.perf_counter() - t0:.1f}s elapsed)", file=sys.stderr)

    with open(ROOT / "artifacts" / "step4a10" / "phase26_27_variability_raw.json", "w") as f:
        json.dump(results, f, indent=2)

    # Analysis
    contradictory_clean = 0
    review_absent_flicker = 0
    fully_stable = 0
    for cid, r in results.items():
        outcomes = set(x["outcome"] for x in r["runs"])
        verified_flags = set(x["outcome"] == "PRESENT_AND_VERIFIED" for x in r["runs"])
        if len(outcomes) == 1:
            fully_stable += 1
        if len(verified_flags) > 1:
            contradictory_clean += 1
        review_absent_outcomes = {"PRESENT_BUT_UNRESOLVED", "RECOGNITION_UNCERTAIN", "CONFIRMED_ABSENT"}
        if outcomes <= review_absent_outcomes and len(outcomes) > 1:
            review_absent_flicker += 1

    summary = {
        "n_documents": len(SAMPLE),
        "n_runs_per_document": N_RUNS,
        "fully_stable_documents": fully_stable,
        "documents_with_any_outcome_change": len(SAMPLE) - fully_stable,
        "contradictory_clean_authoritative_decision_count": contradictory_clean,
        "review_vs_absent_boundary_flicker_count": review_absent_flicker,
    }
    print(json.dumps(summary, indent=2))
    with open(ROOT / "artifacts" / "step4a10" / "phase26_27_variability_summary.json", "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
