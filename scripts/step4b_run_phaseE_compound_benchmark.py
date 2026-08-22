"""Step 4B Phase E runner -- runs the 150-document compound-interaction
benchmark through the REAL interaction engine + REAL
document_aggregation.aggregate_document_state."""
import sys
sys.path.insert(0, ".")

import json
from collections import defaultdict

import interaction_engine_core as ixc
import interaction_rules as ixr
import document_aggregation as agg
from benchmarks.step4b_phaseE_compound_benchmark import DOCUMENTS

ACTIONABLE_IX = ("ESCALATE", "NEGOTIATE", "REQUIRES_REVIEW", "ACCEPT_WITH_NOTE")


def run():
    rows = []
    for d in DOCUMENTS:
        decisions = d["decisions"]
        policy_decisions_dict = {ct: pdec.as_dict() for ct, pdec in decisions.items()}
        interaction_results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        interaction_decisions_dict = {r.interaction_id: r.as_dict() for r in interaction_results}
        actual_n_fired = sum(1 for r in interaction_results if r.state in ACTIONABLE_IX)

        result = agg.aggregate_document_state(d["overall_risk"], policy_decisions_dict, interaction_decisions_dict, d["mode"])
        actual = result["document_state"]
        expected = d["expected_document_state"]
        rows.append({
            "id": d["id"], "family": d["family"], "expected_document_state": expected,
            "actual_document_state": actual, "state_correct": actual == expected,
            "expected_n_fired": d["n_interactions_fired"], "actual_n_fired": actual_n_fired,
            "n_fired_correct": actual_n_fired == d["n_interactions_fired"],
            "notes": d["notes"],
        })
    return rows


def classify(rows):
    metrics = {
        "base_finding_suppression": [], "interaction_suppression": [], "wrong_participant": [],
        "uncertainty_laundering": [], "false_clean_document": [], "wrong_attention_state": [],
    }
    MATERIAL = {"HAS_CRITICAL_INTERACTION", "HAS_POLICY_VIOLATION", "REQUIRES_REVIEW", "CONFIGURATION_UNRESOLVED"}
    for r in rows:
        if not r["state_correct"]:
            exp, act = r["expected_document_state"], r["actual_document_state"]
            if exp in MATERIAL and act not in MATERIAL:
                metrics["false_clean_document"].append(r["id"])
                metrics["wrong_attention_state"].append(r["id"])
        if not r["n_fired_correct"]:
            if r["actual_n_fired"] < r["expected_n_fired"]:
                metrics["interaction_suppression"].append(r["id"])
    return metrics


if __name__ == "__main__":
    rows = run()
    total = len(rows)
    state_correct = sum(1 for r in rows if r["state_correct"])
    n_fired_correct = sum(1 for r in rows if r["n_fired_correct"])
    print(f"Total documents: {total}")
    print(f"Document-state correct: {state_correct}/{total} ({state_correct/total:.1%})")
    print(f"Interaction-count correct: {n_fired_correct}/{total} ({n_fired_correct/total:.1%})")

    metrics = classify(rows)
    for name, ids in metrics.items():
        status = "PASS" if not ids else "FAIL"
        print(f"HARD GATE {name} == 0: {len(ids)} -> {status}")
        for cid in ids:
            row = next(r for r in rows if r["id"] == cid)
            print(f"    {cid}: expected_state={row['expected_document_state']} actual_state={row['actual_document_state']} "
                  f"expected_n={row['expected_n_fired']} actual_n={row['actual_n_fired']} family={row['family']}")

    print("\n=== by family ===")
    fam = defaultdict(lambda: {"total": 0, "state_correct": 0, "n_correct": 0})
    for r in rows:
        fam[r["family"]]["total"] += 1
        fam[r["family"]]["state_correct"] += r["state_correct"]
        fam[r["family"]]["n_correct"] += r["n_fired_correct"]
    for k, v in sorted(fam.items()):
        status = "OK" if v["state_correct"] == v["total"] and v["n_correct"] == v["total"] else "MISMATCH"
        print(f"  {k}: state={v['state_correct']}/{v['total']} n_fired={v['n_correct']}/{v['total']} {status}")

    with open("artifacts/step4b/phaseE_compound_results.json", "w") as f:
        json.dump({"rows": rows, "metrics": metrics, "total": total,
                    "state_correct": state_correct, "n_fired_correct": n_fired_correct}, f, indent=2)
    print("\nWrote artifacts/step4b/phaseE_compound_results.json")
