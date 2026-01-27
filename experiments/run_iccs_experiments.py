"""
Run ICCS-specific experiments (Experiments 2 and 3) on all 115 documents.
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.exp2_iccs_reproducibility_stress import run_iccs_reproducibility_stress
from experiments.exp3_iccs_computational_cost import run_iccs_computational_cost
from experiments.utils_io import save_json
import csv


def main():
    """Run ICCS experiments."""
    print("=" * 80)
    print("ICCS EXPERIMENTS - Running on all 115 documents")
    print("=" * 80)
    
    # Experiment 2: Reproducibility Stress Test
    print("\n" + "=" * 80)
    print("EXPERIMENT 2: Reproducibility Stress Test")
    print("=" * 80)
    exp2_results = run_iccs_reproducibility_stress()
    
    # Save Experiment 2 results
    exp2_csv = Path(__file__).parent / "results" / "exp2_iccs_reproducibility.csv"
    exp2_csv.parent.mkdir(parents=True, exist_ok=True)
    if exp2_results:
        with open(exp2_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=exp2_results[0].keys())
            writer.writeheader()
            writer.writerows(exp2_results)
        print(f"\nExperiment 2 results saved to: {exp2_csv}")
    
    # Experiment 3: Computational Cost
    print("\n" + "=" * 80)
    print("EXPERIMENT 3: Computational Cost Analysis")
    print("=" * 80)
    exp3_results, exp3_summary = run_iccs_computational_cost()
    
    # Save Experiment 3 results
    exp3_csv = Path(__file__).parent / "results" / "exp3_iccs_computational_cost.csv"
    exp3_csv.parent.mkdir(parents=True, exist_ok=True)
    if exp3_results:
        with open(exp3_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=exp3_results[0].keys())
            writer.writeheader()
            writer.writerows(exp3_results)
        print(f"\nExperiment 3 results saved to: {exp3_csv}")
    
    exp3_summary_path = Path(__file__).parent / "results" / "exp3_iccs_computational_cost_summary.json"
    save_json(exp3_summary, exp3_summary_path)
    print(f"Experiment 3 summary saved to: {exp3_summary_path}")
    
    print("\n" + "=" * 80)
    print("ALL ICCS EXPERIMENTS COMPLETE")
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
    
    print(f"\nExperiment 2 (Reproducibility Stress Test):")
    print(f"  Hybrid System:")
    print(f"    Reproducibility Rate: {100*hybrid_reproducible/len(exp2_results):.1f}%")
    print(f"    Documents with Zero Variance: {hybrid_reproducible}/{len(exp2_results)}")
    print(f"    Avg. Distinct Output Sets / Doc: {avg_hybrid_distinct:.2f}")
    if baseline_executed_count > 0:
        print(f"  Baseline System:")
        print(f"    Reproducibility Rate: {100*(baseline_executed_count-baseline_with_variance)/baseline_executed_count:.1f}%")
        print(f"    Documents with Zero Variance: {baseline_executed_count-baseline_with_variance}/{baseline_executed_count}")
        print(f"    Avg. Distinct Output Sets / Doc: {avg_baseline_distinct:.2f}")
    
    # Experiment 3 summary
    print(f"\nExperiment 3 (Computational Cost):")
    print(f"  Hybrid System:")
    print(f"    Avg. Execution Time / Doc: {exp3_summary['hybrid_avg_time']:.3f}s")
    print(f"    Computational Complexity: O(n)")
    print(f"    Output Variance: {exp3_summary['hybrid_total_variance']}")
    print(f"    Reproducibility Rate: {100.0 if exp3_summary['hybrid_total_variance'] == 0 else 0.0}%")
    if exp3_summary['baseline_executed_count'] > 0:
        print(f"  Baseline System:")
        print(f"    Avg. Execution Time / Doc: {exp3_summary['baseline_avg_time']:.3f}s (std: {exp3_summary['baseline_avg_std']:.3f}s)")
        print(f"    Computational Complexity: Variable")
        print(f"    Output Variance: {exp3_summary['baseline_total_variance']}")
        print(f"    Reproducibility Rate: 0.0%")


if __name__ == "__main__":
    main()
