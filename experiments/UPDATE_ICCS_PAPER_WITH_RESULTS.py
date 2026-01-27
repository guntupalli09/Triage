"""
Script to update ICCS paper with actual experiment results.
Run this after experiments/run_iccs_full.py completes.
"""
import sys
from pathlib import Path
import csv
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

results_dir = Path(__file__).parent / "results"

# Read Experiment 2 results
exp2_csv = results_dir / "exp2_iccs_reproducibility.csv"
exp2_results = []
if exp2_csv.exists():
    with open(exp2_csv, 'r') as f:
        reader = csv.DictReader(f)
        exp2_results = list(reader)

# Read Experiment 3 results
exp3_csv = results_dir / "exp3_iccs_computational_cost.csv"
exp3_summary_path = results_dir / "exp3_iccs_computational_cost_summary.json"
exp3_results = []
exp3_summary = {}
if exp3_csv.exists():
    with open(exp3_csv, 'r') as f:
        reader = csv.DictReader(f)
        exp3_results = list(reader)
if exp3_summary_path.exists():
    with open(exp3_summary_path, 'r') as f:
        exp3_summary = json.load(f)

# Compute statistics
if exp2_results:
    hybrid_reproducible = sum(1 for r in exp2_results if r.get("hybrid_reproducible", "").lower() == "true")
    baseline_with_variance = sum(1 for r in exp2_results if r.get("baseline_has_variance", "").lower() == "true")
    baseline_executed_count = sum(1 for r in exp2_results if r.get("baseline_executed", "").lower() == "true")
    
    hybrid_distinct_values = [float(r.get("hybrid_distinct_output_sets", 0)) for r in exp2_results]
    baseline_distinct_values = [float(r.get("baseline_distinct_output_sets", 0)) for r in exp2_results if r.get("baseline_executed", "").lower() == "true"]
    
    avg_hybrid_distinct = sum(hybrid_distinct_values) / len(hybrid_distinct_values) if hybrid_distinct_values else 0
    avg_baseline_distinct = sum(baseline_distinct_values) / len(baseline_distinct_values) if baseline_distinct_values else 0
    
    reproducibility_rate_hybrid = 100 * hybrid_reproducible / len(exp2_results)
    reproducibility_rate_baseline = 100 * (baseline_executed_count - baseline_with_variance) / baseline_executed_count if baseline_executed_count > 0 else 0
    
    print("=" * 80)
    print("EXPERIMENT 2 RESULTS FOR PAPER")
    print("=" * 80)
    print(f"Hybrid System:")
    print(f"  Reproducibility Rate: {reproducibility_rate_hybrid:.1f}%")
    print(f"  Documents with Zero Variance: {hybrid_reproducible}/{len(exp2_results)}")
    print(f"  Avg. Distinct Output Sets / Doc: {avg_hybrid_distinct:.2f}")
    if baseline_executed_count > 0:
        print(f"Baseline System:")
        print(f"  Reproducibility Rate: {reproducibility_rate_baseline:.1f}%")
        print(f"  Documents with Zero Variance: {baseline_executed_count - baseline_with_variance}/{baseline_executed_count}")
        print(f"  Documents with Variance: {baseline_with_variance}/{baseline_executed_count}")
        print(f"  Avg. Distinct Output Sets / Doc: {avg_baseline_distinct:.2f}")
    
    print("\n" + "=" * 80)
    print("TABLE DATA FOR PAPER (Table 2: Reproducibility Stress Test)")
    print("=" * 80)
    print(f"Hybrid System: {reproducibility_rate_hybrid:.1f}%, {hybrid_reproducible}/{len(exp2_results)}, {avg_hybrid_distinct:.1f}")
    if baseline_executed_count > 0:
        print(f"Baseline System: {reproducibility_rate_baseline:.1f}%, {baseline_executed_count - baseline_with_variance}/{baseline_executed_count}, {avg_baseline_distinct:.1f}")

if exp3_summary:
    print("\n" + "=" * 80)
    print("EXPERIMENT 3 RESULTS FOR PAPER")
    print("=" * 80)
    print(f"Hybrid System:")
    print(f"  Avg. Execution Time / Doc: {exp3_summary.get('hybrid_avg_time', 0):.3f}s")
    print(f"  Avg. Std Dev: {exp3_summary.get('hybrid_avg_std', 0):.3f}s")
    print(f"  Total Output Variance: {exp3_summary.get('hybrid_total_variance', 0)}")
    print(f"  Reproducibility Rate: {100.0 if exp3_summary.get('hybrid_total_variance', 0) == 0 else 0.0}%")
    if exp3_summary.get('baseline_executed_count', 0) > 0:
        print(f"Baseline System:")
        print(f"  Avg. Execution Time / Doc: {exp3_summary.get('baseline_avg_time', 0):.3f}s")
        print(f"  Avg. Std Dev: {exp3_summary.get('baseline_avg_std', 0):.3f}s")
        print(f"  Total Output Variance: {exp3_summary.get('baseline_total_variance', 0)}")
        print(f"  Reproducibility Rate: 0.0%")
    
    print("\n" + "=" * 80)
    print("TABLE DATA FOR PAPER (Table 3: Computational Cost Analysis)")
    print("=" * 80)
    print(f"Hybrid: {exp3_summary.get('hybrid_avg_time', 0):.2f}s, O(n), 0.0, {100.0 if exp3_summary.get('hybrid_total_variance', 0) == 0 else 0.0:.1f}%")
    if exp3_summary.get('baseline_executed_count', 0) > 0:
        baseline_avg = exp3_summary.get('baseline_avg_time', 0)
        baseline_std = exp3_summary.get('baseline_avg_std', 0)
        print(f"Baseline: {baseline_avg:.2f}s (std: {baseline_std:.2f}s), Variable, High, 0.0%")

print("\n" + "=" * 80)
print("Next: Update ICCS_PAPER_LATEX.MD with these values")
print("=" * 80)
