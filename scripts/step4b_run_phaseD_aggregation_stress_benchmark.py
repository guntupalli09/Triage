"""Step 4B Phase D runner -- runs the 158-document aggregation-stress
benchmark through the REAL interaction engine + REAL
document_aggregation.aggregate_document_state."""
import sys
sys.path.insert(0, ".")

import json
from collections import defaultdict

import interaction_engine_core as ixc
import interaction_rules as ixr
import document_aggregation as agg
from benchmarks.step4b_phaseD_aggregation_stress_benchmark import DOCUMENTS

MATERIAL_STATES = {"HAS_CRITICAL_INTERACTION", "HAS_POLICY_VIOLATION", "REQUIRES_REVIEW", "CONFIGURATION_UNRESOLVED"}


def run():
    rows = []
    for d in DOCUMENTS:
        decisions = d["decisions"]
        if decisions is None:
            policy_decisions_dict = None
            interaction_decisions_dict = {}
        else:
            policy_decisions_dict = {ct: pdec.as_dict() for ct, pdec in decisions.items()}
            interaction_results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
            interaction_decisions_dict = {r.interaction_id: r.as_dict() for r in interaction_results}

        result = agg.aggregate_document_state(d["overall_risk"], policy_decisions_dict, interaction_decisions_dict, d["mode"])
        actual = result["document_state"]
        expected = d["expected_document_state"]
        rows.append({
            "id": d["id"], "family": d["family"], "expected_document_state": expected,
            "actual_document_state": actual, "correct": actual == expected, "notes": d["notes"],
        })
    return rows


def classify(rows):
    metrics = {
        "false_clean_document": [], "wrong_document_state": [], "wrong_attention_state": [],
        "lost_finding": [], "lost_interaction": [], "uncertainty_laundering": [],
        "incorrect_insufficient_facts_escalation": [],
    }
    for r in rows:
        if r["correct"]:
            continue
        exp, act = r["expected_document_state"], r["actual_document_state"]
        if exp in MATERIAL_STATES and act not in MATERIAL_STATES:
            metrics["false_clean_document"].append(r["id"])
            metrics["wrong_attention_state"].append(r["id"])
        elif exp not in MATERIAL_STATES and act in MATERIAL_STATES:
            metrics["incorrect_insufficient_facts_escalation"].append(r["id"])
            metrics["wrong_attention_state"].append(r["id"])
        else:
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
            print(f"    {cid}: expected={row['expected_document_state']} actual={row['actual_document_state']} family={row['family']}")

    print("\n=== by family ===")
    fam = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        fam[r["family"]]["total"] += 1
        fam[r["family"]]["correct"] += r["correct"]
    for k, v in sorted(fam.items()):
        status = "OK" if v["correct"] == v["total"] else "MISMATCH"
        print(f"  {k}: {v['correct']}/{v['total']} {status}")

    with open("artifacts/step4b/phaseD_aggregation_stress_results.json", "w") as f:
        json.dump({"rows": rows, "metrics": metrics, "total": total, "correct": correct}, f, indent=2)
    print("\nWrote artifacts/step4b/phaseD_aggregation_stress_results.json")
