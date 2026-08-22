"""Step 4B Phase 3 — runs the 70-case adversarial authority micro-benchmark
against production interaction_engine_core/interaction_rules. DEVELOPMENT
evidence -- may be iterated against."""
import sys
sys.path.insert(0, ".")

import json
import interaction_engine_core as ixc
import interaction_rules as ixr
from benchmarks.step4b_phase3_authority_microbenchmark import CASES

RULES_BY_ID = {r.interaction_id: r for r in ixr.LAUNCH_CATALOG}


def run():
    rows = []
    for c in CASES:
        rule = RULES_BY_ID[c["interaction_id"]]
        result = ixc.evaluate(c["decisions"], [rule])[0]
        rows.append({
            "id": c["id"], "interaction_id": c["interaction_id"], "attack": c["attack"],
            "expected_state": c["expected_state"], "actual_state": result.state,
            "correct": result.state == c["expected_state"],
            "evidence_present": all(
                result.participating_provisions.get(ct) is not None
                for ct in c["decisions"] if ct in rule.participating_clause_types
            ),
            "notes": c["notes"],
        })
    return rows


def classify(rows):
    false_authoritative = []  # expected NOT_TRIGGERED/INSUFFICIENT_FACTS but fired an actionable state
    uncertainty_laundering = []  # expected a safe/gated outcome but got a MORE confident wrong one
    missing_evidence = []
    wrong_state_other = []
    for r in rows:
        if not r["correct"]:
            if r["expected_state"] in ("NOT_TRIGGERED", "INSUFFICIENT_FACTS") and r["actual_state"] in ixc.ACTIONABLE_STATES:
                false_authoritative.append(r["id"])
            elif r["expected_state"] == "INSUFFICIENT_FACTS" and r["actual_state"] == "NOT_TRIGGERED":
                uncertainty_laundering.append(r["id"])
            else:
                wrong_state_other.append(r["id"])
        if r["actual_state"] in ixc.ACTIONABLE_STATES and not r["evidence_present"]:
            missing_evidence.append(r["id"])
    return {
        "false_authoritative_interaction": false_authoritative,
        "uncertainty_laundering": uncertainty_laundering,
        "missing_evidence_interaction": missing_evidence,
        "wrong_state_other_mismatch": wrong_state_other,
    }


if __name__ == "__main__":
    rows = run()
    correct = sum(1 for r in rows if r["correct"])
    print(f"Total cases: {len(rows)}")
    print(f"Correct: {correct}/{len(rows)} ({correct/len(rows):.1%})")

    metrics = classify(rows)
    print(f"\nHARD GATE false_authoritative_interaction == 0: {len(metrics['false_authoritative_interaction'])} -> "
          f"{'PASS' if not metrics['false_authoritative_interaction'] else 'FAIL'}")
    for cid in metrics["false_authoritative_interaction"]:
        print(f"    {cid}")
    print(f"HARD GATE uncertainty_laundering == 0: {len(metrics['uncertainty_laundering'])} -> "
          f"{'PASS' if not metrics['uncertainty_laundering'] else 'FAIL'}")
    for cid in metrics["uncertainty_laundering"]:
        print(f"    {cid}")
    print(f"HARD GATE missing_evidence_interaction == 0: {len(metrics['missing_evidence_interaction'])} -> "
          f"{'PASS' if not metrics['missing_evidence_interaction'] else 'FAIL'}")
    for cid in metrics["missing_evidence_interaction"]:
        print(f"    {cid}")
    print(f"\nOther mismatches (not classified as unsafe, but wrong -- needs review): "
          f"{len(metrics['wrong_state_other_mismatch'])}")
    for cid in metrics["wrong_state_other_mismatch"]:
        row = next(r for r in rows if r["id"] == cid)
        print(f"    {cid}: expected={row['expected_state']} actual={row['actual_state']} ({row['notes']})")

    print("\n=== by rule ===")
    from collections import defaultdict
    by_rule = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        by_rule[r["interaction_id"]]["total"] += 1
        by_rule[r["interaction_id"]]["correct"] += r["correct"]
    for rid, v in sorted(by_rule.items()):
        print(f"  {rid}: {v['correct']}/{v['total']}")

    with open("artifacts/step4b/phase3_microbenchmark_results.json", "w") as f:
        json.dump({"rows": rows, "metrics": metrics}, f, indent=2)
    print("\nWrote artifacts/step4b/phase3_microbenchmark_results.json")
