"""
Run full ICCS experiments on all 115 documents.
This will take significant time (especially with baseline LLM calls).
"""
import sys
from pathlib import Path
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("ICCS EXPERIMENTS - FULL RUN")
print("=" * 80)
print("This will run:")
print("  Experiment 2: 15 documents × 20 runs = 300 hybrid runs + 300 baseline runs")
print("  Experiment 3: All 115 documents × 3 runs = 345 hybrid runs + 345 baseline runs")
print("Estimated time: 2-4 hours (depending on API rate limits)")
print("=" * 80)
print()

response = input("Continue? (yes/no): ")
if response.lower() != 'yes':
    print("Aborted.")
    sys.exit(0)

from experiments.exp2_iccs_reproducibility_stress import run_iccs_reproducibility_stress
from experiments.exp3_iccs_computational_cost import run_iccs_computational_cost
from experiments.utils_io import save_json
import csv

start_time = time.time()

# Experiment 2: Reproducibility Stress Test
print("\n" + "=" * 80)
print("EXPERIMENT 2: Reproducibility Stress Test")
print("=" * 80)
exp2_start = time.time()
exp2_results = run_iccs_reproducibility_stress()
exp2_elapsed = time.time() - exp2_start
print(f"\nExperiment 2 completed in {exp2_elapsed/60:.1f} minutes")

# Save Experiment 2 results
results_dir = Path(__file__).parent / "results"
results_dir.mkdir(parents=True, exist_ok=True)

exp2_csv = results_dir / "exp2_iccs_reproducibility.csv"
if exp2_results:
    with open(exp2_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=exp2_results[0].keys())
        writer.writeheader()
        writer.writerows(exp2_results)
    print(f"Experiment 2 results saved to: {exp2_csv}")

# Experiment 3: Computational Cost
print("\n" + "=" * 80)
print("EXPERIMENT 3: Computational Cost Analysis")
print("=" * 80)
exp3_start = time.time()
exp3_results, exp3_summary = run_iccs_computational_cost()
exp3_elapsed = time.time() - exp3_start
print(f"\nExperiment 3 completed in {exp3_elapsed/60:.1f} minutes")

# Save Experiment 3 results
exp3_csv = results_dir / "exp3_iccs_computational_cost.csv"
if exp3_results:
    with open(exp3_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=exp3_results[0].keys())
        writer.writeheader()
        writer.writerows(exp3_results)
    print(f"Experiment 3 results saved to: {exp3_csv}")

exp3_summary_path = results_dir / "exp3_iccs_computational_cost_summary.json"
save_json(exp3_summary, exp3_summary_path)
print(f"Experiment 3 summary saved to: {exp3_summary_path}")

total_elapsed = time.time() - start_time
print("\n" + "=" * 80)
print(f"ALL EXPERIMENTS COMPLETE (Total time: {total_elapsed/60:.1f} minutes)")
print("=" * 80)

# Print summary for paper
print("\n" + "=" * 80)
print("RESULTS SUMMARY FOR PAPER")
print("=" * 80)

# Experiment 2 summary
hybrid_reproducible = sum(1 for r in exp2_results if r["hybrid_reproducible"])
baseline_with_variance = sum(1 for r in exp2_results if r.get("baseline_has_variance", False))
baseline_executed_count = sum(1 for r in exp2_results if r.get("baseline_executed", False))
avg_hybrid_distinct = sum(r["hybrid_distinct_output_sets"] for r in exp2_results) / len(exp2_results) if exp2_results else 0
avg_baseline_distinct = sum(r["baseline_distinct_output_sets"] for r in exp2_results if r.get("baseline_executed")) / baseline_executed_count if baseline_executed_count > 0 else 0

print(f"\nExperiment 2 (Reproducibility Stress Test - 15 docs, 20 runs each):")
print(f"  Hybrid System:")
print(f"    Reproducibility Rate: {100*hybrid_reproducible/len(exp2_results):.1f}%")
print(f"    Documents with Zero Variance: {hybrid_reproducible}/{len(exp2_results)}")
print(f"    Avg. Distinct Output Sets / Doc: {avg_hybrid_distinct:.2f}")
if baseline_executed_count > 0:
    baseline_reproducible = baseline_executed_count - baseline_with_variance
    print(f"  Baseline System:")
    print(f"    Reproducibility Rate: {100*baseline_reproducible/baseline_executed_count:.1f}%")
    print(f"    Documents with Zero Variance: {baseline_reproducible}/{baseline_executed_count}")
    print(f"    Documents with Variance: {baseline_with_variance}/{baseline_executed_count}")
    print(f"    Avg. Distinct Output Sets / Doc: {avg_baseline_distinct:.2f}")

# Experiment 3 summary
print(f"\nExperiment 3 (Computational Cost - {exp3_summary['total_documents']} documents):")
print(f"  Hybrid System:")
print(f"    Avg. Execution Time / Doc: {exp3_summary['hybrid_avg_time']:.3f}s")
print(f"    Avg. Std Dev: {exp3_summary['hybrid_avg_std']:.3f}s")
print(f"    Total Output Variance: {exp3_summary['hybrid_total_variance']}")
print(f"    Reproducibility Rate: {100.0 if exp3_summary['hybrid_total_variance'] == 0 else 0.0}%")
if exp3_summary['baseline_executed_count'] > 0:
    print(f"  Baseline System:")
    print(f"    Avg. Execution Time / Doc: {exp3_summary['baseline_avg_time']:.3f}s")
    print(f"    Avg. Std Dev: {exp3_summary['baseline_avg_std']:.3f}s")
    print(f"    Total Output Variance: {exp3_summary['baseline_total_variance']}")
    print(f"    Reproducibility Rate: 0.0%")

print("\n" + "=" * 80)
print("Next step: Update ICCS_PAPER_LATEX.MD with these results")
print("=" * 80)
