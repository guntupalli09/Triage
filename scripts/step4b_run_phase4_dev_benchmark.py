"""Step 4B Phase 4 — runs the 210+ case development interaction benchmark
against production interaction_engine_core/interaction_rules. DEVELOPMENT
evidence -- PRE measurement, may be iterated against per the explicit
Phase 4/5 instructions. Not a final frozen corpus."""
import sys
sys.path.insert(0, ".")

import json
from collections import defaultdict

import interaction_engine_core as ixc
import interaction_rules as ixr
from benchmarks.step4b_phase4_interaction_dev_benchmark import CASES

RULES_BY_ID = {r.interaction_id: r for r in ixr.LAUNCH_CATALOG}

ACTIONABLE = ixc.ACTIONABLE_STATES  # ESCALATE, NEGOTIATE, REQUIRES_REVIEW, ACCEPT_WITH_NOTE (per rule ceiling)


def run():
    rows = []
    for c in CASES:
        rule = RULES_BY_ID[c["interaction_id"]]
        result = ixc.evaluate(c["decisions"], [rule])[0]
        participating_present = [ct for ct in rule.participating_clause_types if ct in c["decisions"]]
        rows.append({
            "id": c["id"], "interaction_id": c["interaction_id"], "family": c["family"],
            "expected_state": c["expected_state"], "actual_state": result.state,
            "correct": result.state == c["expected_state"],
            "evidence_present": all(
                result.participating_provisions.get(ct) is not None
                for ct in participating_present
            ),
            "notes": c["notes"],
        })
    return rows


def classify(rows):
    metrics = {
        "false_interaction": [],           # expected NOT_TRIGGERED, got an actionable state (false positive interaction)
        "missed_interaction": [],          # expected an actionable state, got NOT_TRIGGERED
        "false_authoritative_interaction": [],  # expected NOT_TRIGGERED/INSUFFICIENT_FACTS, got actionable
        "uncertainty_laundering": [],      # expected INSUFFICIENT_FACTS, got NOT_TRIGGERED or an actionable state
        "wrong_direction": [],
        "wrong_ownership": [],
        "wrong_participant": [],
        "evidence_provenance_failure": [],
        "duplicate_interaction": [],
        "suppressed_interaction": [],      # expected actionable, got INSUFFICIENT_FACTS despite facts being present
        "wrong_state_other_mismatch": [],
    }
    for r in rows:
        exp, act = r["expected_state"], r["actual_state"]
        if not r["correct"]:
            if exp == "NOT_TRIGGERED" and act in ACTIONABLE:
                metrics["false_interaction"].append(r["id"])
                metrics["false_authoritative_interaction"].append(r["id"])
            elif exp in ACTIONABLE and act == "NOT_TRIGGERED":
                metrics["missed_interaction"].append(r["id"])
            elif exp == "INSUFFICIENT_FACTS" and act in ACTIONABLE:
                metrics["uncertainty_laundering"].append(r["id"])
                metrics["false_authoritative_interaction"].append(r["id"])
            elif exp == "INSUFFICIENT_FACTS" and act == "NOT_TRIGGERED":
                metrics["uncertainty_laundering"].append(r["id"])
            elif exp in ACTIONABLE and act == "INSUFFICIENT_FACTS":
                metrics["suppressed_interaction"].append(r["id"])
            else:
                metrics["wrong_state_other_mismatch"].append(r["id"])

        if "wrong-participant-key" in r["family"] and act != "INSUFFICIENT_FACTS":
            metrics["wrong_participant"].append(r["id"])
        if "role-reversal" in r["family"] and act in ACTIONABLE and not r["correct"]:
            metrics["wrong_direction"].append(r["id"])
            metrics["wrong_ownership"].append(r["id"])
        if r["actual_state"] in ACTIONABLE and not r["evidence_present"]:
            metrics["evidence_provenance_failure"].append(r["id"])

    return metrics


if __name__ == "__main__":
    rows = run()
    correct = sum(1 for r in rows if r["correct"])
    total = len(rows)
    print(f"Total unique cases: {total}")
    print(f"Correct: {correct}/{total} ({correct/total:.1%})")

    metrics = classify(rows)
    for name in ["false_interaction", "missed_interaction", "false_authoritative_interaction",
                 "uncertainty_laundering", "wrong_direction", "wrong_ownership", "wrong_participant",
                 "evidence_provenance_failure", "duplicate_interaction", "suppressed_interaction"]:
        ids = metrics[name]
        print(f"{name} = {len(ids)}" + (f"  -> {ids}" if ids else ""))

    print(f"\nOther mismatches (needs review): {len(metrics['wrong_state_other_mismatch'])}")
    for cid in metrics["wrong_state_other_mismatch"]:
        row = next(r for r in rows if r["id"] == cid)
        print(f"    {cid}: expected={row['expected_state']} actual={row['actual_state']} family={row['family']} ({row['notes']})")

    print("\n=== by rule ===")
    by_rule = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        by_rule[r["interaction_id"]]["total"] += 1
        by_rule[r["interaction_id"]]["correct"] += r["correct"]
    for rid, v in sorted(by_rule.items()):
        print(f"  {rid}: {v['correct']}/{v['total']}")

    with open("artifacts/step4b/phase4_dev_benchmark_results.json", "w") as f:
        json.dump({"rows": rows, "metrics": metrics, "total_unique_cases": total}, f, indent=2)
    print("\nWrote artifacts/step4b/phase4_dev_benchmark_results.json")
