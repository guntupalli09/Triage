"""Step 4B Phase B runner -- runs the deduplication/suppression benchmark
directly against main.build_enhanced_issues (production code, not
reimplemented). DEVELOPMENT evidence."""
import os
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/step4b_phaseB_runner.db")
import sys
sys.path.insert(0, ".")

import json
from collections import defaultdict

import main
from benchmarks.step4b_phaseB_deduplication_benchmark import CASES


def run():
    rows = []
    for c in CASES:
        llm_result = {"top_issues": c.get("llm_top_issues", [])}
        out = main.build_enhanced_issues(list(c["findings"]), llm_result)
        actual_count = len(out)
        rows.append({
            "id": c["id"], "family": c["family"], "expected_count": c["expected_count"],
            "actual_count": actual_count, "correct": actual_count == c["expected_count"],
            "input_count": len(c["findings"]), "notes": c["notes"],
        })
    return rows


def classify(rows):
    metrics = {"materially_distinct_finding_suppression": [], "duplicate_finding_leakage": []}
    for r in rows:
        if r["correct"]:
            continue
        if r["actual_count"] < r["expected_count"]:
            metrics["materially_distinct_finding_suppression"].append(r["id"])
        elif r["actual_count"] > r["expected_count"]:
            metrics["duplicate_finding_leakage"].append(r["id"])
    return metrics


if __name__ == "__main__":
    rows = run()
    total = len(rows)
    correct = sum(1 for r in rows if r["correct"])
    print(f"Total cases: {total}")
    print(f"Correct: {correct}/{total} ({correct/total:.1%})")

    metrics = classify(rows)
    for name, ids in metrics.items():
        status = "PASS" if not ids else "FAIL"
        print(f"HARD GATE {name} == 0: {len(ids)} -> {status}")
        for cid in ids:
            row = next(r for r in rows if r["id"] == cid)
            print(f"    {cid}: expected={row['expected_count']} actual={row['actual_count']} family={row['family']} ({row['notes']})")

    print("\n=== by family ===")
    fam = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        fam[r["family"]]["total"] += 1
        fam[r["family"]]["correct"] += r["correct"]
    for k, v in sorted(fam.items()):
        status = "OK" if v["correct"] == v["total"] else "MISMATCH"
        print(f"  {k}: {v['correct']}/{v['total']} {status}")

    with open("artifacts/step4b/phaseB_dedup_results.json", "w") as f:
        json.dump({"rows": rows, "metrics": metrics, "total": total, "correct": correct}, f, indent=2)
    print("\nWrote artifacts/step4b/phaseB_dedup_results.json")
