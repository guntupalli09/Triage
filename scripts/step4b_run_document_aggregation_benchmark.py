"""Step 4B document-aggregation benchmark runner.

Two independent measurements against the same 104 fixtures:

1. PRE -- what production actually exposes TODAY (main.py:1203/:1231's own
   logic: a contract is "high risk" / attention-worthy if and only if
   overall_risk == "high", nothing else). Measures false-clean: cases
   where a material policy violation or critical interaction exists but
   today's logic would still classify the document as not-high-risk.

2. POST (of the new pure function only, not yet wired into production) --
   document_aggregation.aggregate_document_state's own correctness against
   the predeclared expected_document_state.
"""
import sys
sys.path.insert(0, ".")

import json
from collections import defaultdict

from document_aggregation import aggregate_document_state, DOC_CLEAN, DOC_CLEAN_LEGACY_ATTENTION
from benchmarks.step4b_document_aggregation_dev_benchmark import CASES

MATERIAL_STATES = {"HAS_CRITICAL_INTERACTION", "HAS_POLICY_VIOLATION", "REQUIRES_REVIEW", "CONFIGURATION_UNRESOLVED"}


def production_today_is_high_risk(overall_risk):
    """Exactly main.py:1203/:1231's own filter logic -- the ONLY signal
    currently exposed on the dashboard high-risk count and the /history
    risk filter."""
    return overall_risk == "high"


def run():
    rows = []
    for c in CASES:
        result = aggregate_document_state(c["overall_risk"], c["policy_decisions"], c["interaction_decisions"], c["mode"])
        actual = result["document_state"]
        expected = c["expected_document_state"]

        material_ground_truth = expected in MATERIAL_STATES
        production_flags_it = production_today_is_high_risk(c["overall_risk"])
        pre_false_clean = material_ground_truth and not production_flags_it

        rows.append({
            "id": c["id"], "family": c["family"], "mode": c["mode"],
            "expected_document_state": expected, "actual_document_state": actual,
            "correct": actual == expected,
            "pre_false_clean": pre_false_clean,
            "reasons": result["reasons"],
            "notes": c["notes"],
        })
    return rows


if __name__ == "__main__":
    rows = run()
    total = len(rows)
    correct = sum(1 for r in rows if r["correct"])
    pre_false_clean = [r["id"] for r in rows if r["pre_false_clean"]]

    print(f"Total cases: {total}")
    print(f"\n=== PRE: production's CURRENT dashboard/listing logic (overall_risk=='high' only) ===")
    print(f"false_clean (material finding exists, but production's only signal would not flag it) = "
          f"{len(pre_false_clean)}/{total}")

    by_family_fc = defaultdict(int)
    for r in rows:
        if r["pre_false_clean"]:
            by_family_fc[r["family"]] += 1
    for fam, n in sorted(by_family_fc.items()):
        print(f"    {fam}: {n}")

    print(f"\n=== POST: document_aggregation.aggregate_document_state correctness (new pure function) ===")
    print(f"Correct: {correct}/{total} ({correct/total:.1%})")
    wrong = [r for r in rows if not r["correct"]]
    for r in wrong:
        print(f"    MISMATCH {r['id']}: expected={r['expected_document_state']} actual={r['actual_document_state']} "
              f"family={r['family']} notes={r['notes']}")

    # POST false-clean: does the NEW function itself ever fail to flag a material case?
    post_false_clean = [r["id"] for r in rows
                         if r["expected_document_state"] in MATERIAL_STATES
                         and r["actual_document_state"] in (DOC_CLEAN, DOC_CLEAN_LEGACY_ATTENTION)]
    print(f"\nHARD GATE post_false_clean (new function itself reports CLEAN/CLEAN_LEGACY_ATTENTION for a material case) "
          f"== 0: {len(post_false_clean)} -> {'PASS' if not post_false_clean else 'FAIL'}")
    for cid in post_false_clean:
        print(f"    {cid}")

    print("\n=== by family (POST correctness) ===")
    by_fam = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        by_fam[r["family"]]["total"] += 1
        by_fam[r["family"]]["correct"] += r["correct"]
    for fam, v in sorted(by_fam.items()):
        print(f"  {fam}: {v['correct']}/{v['total']}")

    with open("artifacts/step4b/document_aggregation_benchmark_results.json", "w") as f:
        json.dump({"rows": rows, "total": total, "pre_false_clean_count": len(pre_false_clean),
                    "post_correct": correct, "post_false_clean_count": len(post_false_clean)}, f, indent=2)
    print("\nWrote artifacts/step4b/document_aggregation_benchmark_results.json")
