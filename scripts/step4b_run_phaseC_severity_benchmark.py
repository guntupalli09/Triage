"""Step 4B Phase C runner -- runs the severity/prioritization benchmark
against the three real production consumers, never reimplemented."""
import os
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/step4b_phaseC_runner.db")
import sys
sys.path.insert(0, ".")

import json
from collections import defaultdict

import main
import review_queue
import document_aggregation as agg
from benchmarks.step4b_phaseC_severity_benchmark import CASES


def _run_one(c):
    target = c["target"]
    payload = c["payload"]
    if target == "build_enhanced_issues":
        llm_result = {"top_issues": payload.get("llm_top_issues", [])}
        out = main.build_enhanced_issues(list(payload["findings"]), llm_result)
        actual = {"count": len(out)}
        if "order" in c["expected"]:
            actual["order"] = [o.get("severity") for o in out]
        return actual
    if target == "build_review_queue":
        q = review_queue.build_review_queue(payload["findings"], payload["policy_decisions"])
        d = q.as_dict()
        actual = {}
        if "policy_order_states" in c["expected"]:
            order_states = [payload["findings"][i].get("policy_state") for i in
                             sorted(range(len(payload["findings"])),
                                    key=lambda i: (review_queue.tier_rank(payload["findings"][i].get("policy_state")), i))]
            actual["policy_order_states"] = order_states
        if "passed_count" in c["expected"]:
            actual["passed_count"] = len(d.get("passed_checks", []))
            actual["policy_exception_count"] = len(d.get("policy_exception_indices", []))
        return actual
    if target == "aggregate_document_state":
        result = agg.aggregate_document_state(payload["overall_risk"], payload["policy_decisions"],
                                                payload["interaction_decisions"], payload["mode"])
        return {"document_state": result["document_state"]}
    raise ValueError(f"unknown target {target}")


def run():
    rows = []
    for c in CASES:
        actual = _run_one(c)
        correct = all(actual.get(k) == v for k, v in c["expected"].items())
        rows.append({"id": c["id"], "family": c["family"], "target": c["target"],
                     "expected": c["expected"], "actual": actual, "correct": correct, "notes": c["notes"]})
    return rows


if __name__ == "__main__":
    rows = run()
    total = len(rows)
    correct = sum(1 for r in rows if r["correct"])
    print(f"Total cases: {total}")
    print(f"Correct: {correct}/{total} ({correct/total:.1%})")

    # Hard gates
    finding_loss = [r["id"] for r in rows if r["target"] == "build_enhanced_issues" and not r["correct"]
                     and r["actual"].get("count", 0) < r["expected"].get("count", 0)]
    severity_induced_authority_change = [r["id"] for r in rows if r["target"] in ("build_review_queue", "aggregate_document_state") and not r["correct"]]
    wrong_ordering = [r["id"] for r in rows if r["target"] == "build_enhanced_issues" and not r["correct"]
                       and "order" in r["expected"] and r["actual"].get("order") != r["expected"].get("order")]

    print(f"\nHARD GATE severity_induced_authoritative_state_loss == 0: {len(severity_induced_authority_change)} -> "
          f"{'PASS' if not severity_induced_authority_change else 'FAIL'}")
    for cid in severity_induced_authority_change:
        row = next(r for r in rows if r["id"] == cid)
        print(f"    {cid}: expected={row['expected']} actual={row['actual']} ({row['notes']})")
    print(f"HARD GATE material_finding_suppression == 0: {len(finding_loss)} -> {'PASS' if not finding_loss else 'FAIL'}")
    for cid in finding_loss:
        print(f"    {cid}")
    print(f"\nSelectivity-only (presentation ordering, reported separately, not an authority failure): "
          f"wrong_ordering = {len(wrong_ordering)}")
    for cid in wrong_ordering:
        row = next(r for r in rows if r["id"] == cid)
        print(f"    {cid}: expected_order={row['expected'].get('order')} actual_order={row['actual'].get('order')}")

    print("\n=== by target ===")
    by_target = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        by_target[r["target"]]["total"] += 1
        by_target[r["target"]]["correct"] += r["correct"]
    for k, v in sorted(by_target.items()):
        print(f"  {k}: {v['correct']}/{v['total']}")

    print("\n=== by family ===")
    fam = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        fam[r["family"]]["total"] += 1
        fam[r["family"]]["correct"] += r["correct"]
    for k, v in sorted(fam.items()):
        status = "OK" if v["correct"] == v["total"] else "MISMATCH"
        print(f"  {k}: {v['correct']}/{v['total']} {status}")

    with open("artifacts/step4b/phaseC_severity_results.json", "w") as f:
        json.dump({"rows": rows, "total": total, "correct": correct}, f, indent=2, default=str)
    print("\nWrote artifacts/step4b/phaseC_severity_results.json")
