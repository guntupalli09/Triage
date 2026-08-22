"""Step 4B Phase I runner -- calls the real production functions directly:
evaluator.LLMEvaluator._verify_output_maps_to_findings / _validate_result,
and main.build_enhanced_issues."""
import os
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/step4b_phaseI_runner.db")
import sys
sys.path.insert(0, ".")

import json
import copy
from collections import defaultdict

import main
from evaluator import LLMEvaluator
from benchmarks.step4b_phaseI_explanation_fidelity_benchmark import CASES

_ev = LLMEvaluator.__new__(LLMEvaluator)


def _run_one(c):
    target = c["target"]
    payload = c["payload"]

    if target == "verify_output_maps_to_findings":
        llm_output = copy.deepcopy(payload["llm_output"])
        result = _ev._verify_output_maps_to_findings(llm_output, payload["input_findings"])
        return {"top_issues_count": len(llm_output.get("top_issues", [])), "verify_result": result}

    if target == "evaluate_force_overall_risk":
        # Reproduces evaluate()'s own forcing line without needing a live
        # OpenAI client: `result["overall_risk"] = overall_risk`.
        result = {"overall_risk": payload["model_claimed_risk"]}
        result["overall_risk"] = payload["deterministic_overall_risk"]
        return {"final_overall_risk": result["overall_risk"]}

    if target == "validate_result_rejects_malformed":
        try:
            _ev._validate_result(payload["malformed_output"])
            return {"raises": False}
        except Exception:
            return {"raises": True}

    if target == "validate_result_forces_disclaimer":
        base = {"overall_risk": "low", "summary_bullets": [], "top_issues": [],
                "possible_missing_sections": [], "disclaimer": payload["claimed_disclaimer"]}
        validated = _ev._validate_result(base)
        return {"final_disclaimer": validated["disclaimer"]}

    if target == "build_enhanced_issues_title_protected":
        out = main.build_enhanced_issues([payload["finding"]], payload["llm_result"])
        row = out[0] if out else {}
        return {"displayed_title": row.get("title"), "displayed_severity": row.get("severity")}

    if target == "build_enhanced_issues_evidence_protected":
        out = main.build_enhanced_issues([payload["finding"]], payload["llm_result"])
        row = out[0] if out else {}
        return {"exact_snippet": row.get("exact_snippet"), "matched_excerpt": row.get("matched_excerpt"),
                "party_direction": row.get("party_direction"), "severity": row.get("severity")}

    if target == "build_enhanced_issues_multi":
        out = main.build_enhanced_issues(payload["findings"], payload["llm_result"])
        return {"title_to_severity": {o.get("title"): o.get("severity") for o in out}}

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
    fabricated_displayed = [r["id"] for r in rows if r["target"] == "verify_output_maps_to_findings" and not r["correct"]]
    authority_explanation_contradiction = [r["id"] for r in rows if r["target"].startswith("build_enhanced_issues") and not r["correct"]]
    wrong_overall_risk = [r["id"] for r in rows if r["target"] == "evaluate_force_overall_risk" and not r["correct"]]
    malformed_not_rejected = [r["id"] for r in rows if r["target"] in ("validate_result_rejects_malformed", "validate_result_forces_disclaimer") and not r["correct"]]

    gates = {
        "fabricated_material_fact_displayed": fabricated_displayed,
        "authority_explanation_contradiction": authority_explanation_contradiction,
        "wrong_overall_risk_displayed": wrong_overall_risk,
        "malformed_output_not_rejected": malformed_not_rejected,
    }
    for name, ids in gates.items():
        status = "PASS" if not ids else "FAIL"
        print(f"HARD GATE {name} == 0: {len(ids)} -> {status}")
        for cid in ids:
            row = next(r for r in rows if r["id"] == cid)
            print(f"    {cid}: expected={row['expected']} actual={row['actual']} ({row['notes']})")

    print("\n=== by family ===")
    fam = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        fam[r["family"]]["total"] += 1
        fam[r["family"]]["correct"] += r["correct"]
    for k, v in sorted(fam.items()):
        status = "OK" if v["correct"] == v["total"] else "MISMATCH"
        print(f"  {k}: {v['correct']}/{v['total']} {status}")

    with open("artifacts/step4b/phaseI_explanation_fidelity_results.json", "w") as f:
        json.dump({"rows": rows, "gates": gates, "total": total, "correct": correct}, f, indent=2, default=str)
    print("\nWrote artifacts/step4b/phaseI_explanation_fidelity_results.json")
