"""Step 4B Phase A runner -- runs the 200-document multi-policy benchmark
through the REAL interaction engine (interaction_engine_core.evaluate +
interaction_rules.LAUNCH_CATALOG) and the REAL document_aggregation.
aggregate_document_state. DEVELOPMENT evidence."""
import sys
sys.path.insert(0, ".")

import json
from collections import defaultdict

import interaction_engine_core as ixc
import interaction_rules as ixr
import document_aggregation as agg
from benchmarks.step4b_phaseA_multipolicy_document_benchmark import DOCUMENTS

MATERIAL_STATES = {"HAS_CRITICAL_INTERACTION", "HAS_POLICY_VIOLATION", "REQUIRES_REVIEW", "CONFIGURATION_UNRESOLVED"}


def run():
    rows = []
    for d in DOCUMENTS:
        decisions = d["decisions"]
        policy_decisions_dict = {ct: pdec.as_dict() for ct, pdec in decisions.items()}
        interaction_results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        interaction_decisions_dict = {r.interaction_id: r.as_dict() for r in interaction_results}

        result = agg.aggregate_document_state(d["overall_risk"], policy_decisions_dict, interaction_decisions_dict, d["mode"])
        actual = result["document_state"]
        expected = d["expected_document_state"]

        fired_interactions = [r.interaction_id for r in interaction_results if r.state in ("ESCALATE", "NEGOTIATE", "REQUIRES_REVIEW", "ACCEPT_WITH_NOTE")]
        violating_policies = [ct for ct, pdec in decisions.items() if pdec.state in ("PROHIBITED", "MUST_REDLINE", "ESCALATE", "NEGOTIATE")]
        review_policies = [ct for ct, pdec in decisions.items() if pdec.state in ("REQUIRES_REVIEW", "EVALUATION_ERROR")]

        rows.append({
            "id": d["id"], "family": d["family"], "num_policies": d["num_policies"],
            "expected_document_state": expected, "actual_document_state": actual,
            "correct": actual == expected,
            "fired_interactions": fired_interactions, "violating_policies": violating_policies,
            "review_policies": review_policies, "notes": d["notes"],
        })
    return rows


def classify(rows):
    metrics = {
        "false_clean_document": [],           # expected material, aggregation said CLEAN/CLEAN_LEGACY_ATTENTION
        "lost_base_finding": [],               # a violating policy exists but document_state doesn't reflect HAS_POLICY_VIOLATION when it should be the governing state
        "lost_interaction": [],                # a fired interaction exists but document_state isn't HAS_CRITICAL_INTERACTION/REQUIRES_REVIEW appropriately
        "lost_review_finding": [],
        "wrong_document_state": [],            # any other mismatch
    }
    for r in rows:
        if r["correct"]:
            continue
        exp, act = r["expected_document_state"], r["actual_document_state"]
        if exp in MATERIAL_STATES and act not in MATERIAL_STATES:
            metrics["false_clean_document"].append(r["id"])
        if r["violating_policies"] and exp == "HAS_POLICY_VIOLATION" and act != "HAS_POLICY_VIOLATION":
            metrics["lost_base_finding"].append(r["id"])
        if r["fired_interactions"] and exp == "HAS_CRITICAL_INTERACTION" and act != "HAS_CRITICAL_INTERACTION":
            metrics["lost_interaction"].append(r["id"])
        if r["review_policies"] and exp == "REQUIRES_REVIEW" and act != "REQUIRES_REVIEW":
            metrics["lost_review_finding"].append(r["id"])
        if r["id"] not in (metrics["false_clean_document"] + metrics["lost_base_finding"] +
                            metrics["lost_interaction"] + metrics["lost_review_finding"]):
            metrics["wrong_document_state"].append(r["id"])
    return metrics


if __name__ == "__main__":
    rows = run()
    total = len(rows)
    correct = sum(1 for r in rows if r["correct"])
    print(f"Total documents: {total}")
    print(f"Correct: {correct}/{total} ({correct/total:.1%})")

    metrics = classify(rows)
    for name, ids in metrics.items():
        status = "PASS" if not ids else "FAIL"
        print(f"HARD GATE {name} == 0: {len(ids)} -> {status}")
        for cid in ids:
            row = next(r for r in rows if r["id"] == cid)
            print(f"    {cid}: expected={row['expected_document_state']} actual={row['actual_document_state']} "
                  f"family={row['family']} n={row['num_policies']}")

    print("\n=== by bucket (num_policies) ===")
    buckets = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        n = r["num_policies"]
        key = "3-4" if n <= 4 else ("5-7" if n <= 7 else "8+")
        buckets[key]["total"] += 1
        buckets[key]["correct"] += r["correct"]
    for k, v in sorted(buckets.items()):
        print(f"  {k}: {v['correct']}/{v['total']}")

    print("\n=== by family ===")
    fam = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        fam[r["family"]]["total"] += 1
        fam[r["family"]]["correct"] += r["correct"]
    for k, v in sorted(fam.items()):
        status = "OK" if v["correct"] == v["total"] else "MISMATCH"
        print(f"  {k}: {v['correct']}/{v['total']} {status}")

    with open("artifacts/step4b/phaseA_multipolicy_results.json", "w") as f:
        json.dump({"rows": rows, "metrics": metrics, "total": total, "correct": correct}, f, indent=2)
    print("\nWrote artifacts/step4b/phaseA_multipolicy_results.json")
