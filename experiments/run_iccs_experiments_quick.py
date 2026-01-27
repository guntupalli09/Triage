"""
Quick version of ICCS experiments for testing (fewer runs per document).
For full results, use run_iccs_experiments.py
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import (
    NDA_DIR, MSA_DIR, EMPLOYMENT_DIR, LICENSING_DIR,
    ARTIFACTS_DIR
)
from experiments.utils_io import get_doc_ids, read_text, save_json, find_doc_file
from experiments.run_hybrid import run_hybrid_engine
from experiments.run_baseline_llm import run_baseline_llm
from experiments.metrics import compute_variance_count
from experiments.normalize import normalize_hybrid_findings, normalize_baseline_findings
import time
import statistics
import csv


def get_all_doc_ids():
    """Get document IDs from all contract type directories."""
    all_ids = []
    for data_dir in [NDA_DIR, MSA_DIR, EMPLOYMENT_DIR, LICENSING_DIR]:
        if data_dir.exists():
            ids = get_doc_ids(data_dir)
            all_ids.extend(ids)
    return all_ids


def count_distinct_output_sets(run_outputs, is_hybrid=True):
    """Count distinct output sets across runs."""
    if is_hybrid:
        normalized_sets = [normalize_hybrid_findings(run) for run in run_outputs]
    else:
        normalized_sets = [normalize_baseline_findings(run) for run in run_outputs]
    
    unique_sets = set()
    for norm_set in normalized_sets:
        unique_sets.add(tuple(sorted(norm_set)))
    
    return len(unique_sets)


def run_exp2_quick():
    """Quick version: 15 docs, 5 runs each (instead of 20)."""
    print("=" * 80)
    print("ICCS EXPERIMENT 2: Reproducibility Stress Test (QUICK MODE: 5 runs)")
    print("=" * 80)
    
    all_doc_ids = get_all_doc_ids()
    print(f"Total documents available: {len(all_doc_ids)}")
    
    public_ids = [d for d in all_doc_ids if d.startswith("public")]
    synthetic_ids = [d for d in all_doc_ids if d.startswith("synthetic")]
    
    selected = (public_ids[:8] + synthetic_ids[:7])[:15]
    print(f"Selected {len(selected)} documents")
    
    results = []
    NUM_RUNS = 5  # Quick mode: 5 runs instead of 20
    
    for doc_id in selected:
        print(f"\nProcessing {doc_id}...")
        
        text_path = None
        for data_dir in [NDA_DIR, MSA_DIR, EMPLOYMENT_DIR, LICENSING_DIR]:
            text_path = find_doc_file(data_dir, doc_id, ".txt")
            if text_path:
                break
        
        if not text_path:
            continue
        
        text = read_text(text_path)
        
        # Hybrid: 5 runs
        hybrid_runs = []
        for run_num in range(1, NUM_RUNS + 1):
            result = run_hybrid_engine(text, suppression_enabled=True)
            hybrid_runs.append(result)
        
        # Baseline: 5 runs
        baseline_runs = []
        baseline_executed = False
        for run_num in range(1, NUM_RUNS + 1):
            result = run_baseline_llm(text)
            baseline_runs.append(result)
            if result.get("executed", False):
                baseline_executed = True
        
        hybrid_variance = compute_variance_count(hybrid_runs)
        hybrid_distinct = count_distinct_output_sets(hybrid_runs, is_hybrid=True)
        
        if baseline_executed:
            baseline_variance = compute_variance_count(baseline_runs)
            baseline_distinct = count_distinct_output_sets(baseline_runs, is_hybrid=False)
        else:
            baseline_variance = None
            baseline_distinct = None
        
        results.append({
            "doc_id": doc_id,
            "hybrid_variance_count": hybrid_variance,
            "hybrid_distinct_output_sets": hybrid_distinct,
            "hybrid_reproducible": hybrid_variance == 0,
            "baseline_variance_count": baseline_variance,
            "baseline_distinct_output_sets": baseline_distinct,
            "baseline_has_variance": baseline_variance > 0 if baseline_variance is not None else None,
            "baseline_executed": baseline_executed,
        })
    
    return results


def run_exp3_quick():
    """Quick version: Sample 30 docs from 115 for computational cost."""
    print("=" * 80)
    print("ICCS EXPERIMENT 3: Computational Cost (QUICK MODE: 30 docs)")
    print("=" * 80)
    
    all_doc_ids = get_all_doc_ids()
    print(f"Total documents available: {len(all_doc_ids)}")
    
    # Sample 30 documents
    sample_size = min(30, len(all_doc_ids))
    sampled = all_doc_ids[:sample_size]
    print(f"Sampling {sample_size} documents for computational cost analysis...")
    
    results = []
    hybrid_times = []
    baseline_times = []
    
    for idx, doc_id in enumerate(sampled, 1):
        print(f"\n[{idx}/{sample_size}] Processing {doc_id}...")
        
        text_path = None
        for data_dir in [NDA_DIR, MSA_DIR, EMPLOYMENT_DIR, LICENSING_DIR]:
            text_path = find_doc_file(data_dir, doc_id, ".txt")
            if text_path:
                break
        
        if not text_path:
            continue
        
        text = read_text(text_path)
        
        # Measure hybrid (3 runs)
        hybrid_runs = []
        times = []
        for _ in range(3):
            start = time.time()
            result = run_hybrid_engine(text, suppression_enabled=True)
            elapsed = time.time() - start
            times.append(elapsed)
            hybrid_runs.append(result)
        
        hybrid_mean = statistics.mean(times)
        hybrid_std = statistics.stdev(times) if len(times) > 1 else 0.0
        hybrid_variance = compute_variance_count(hybrid_runs)
        hybrid_times.append(hybrid_mean)
        
        # Measure baseline (3 runs)
        baseline_runs = []
        baseline_times_list = []
        baseline_executed = False
        for _ in range(3):
            start = time.time()
            result = run_baseline_llm(text)
            elapsed = time.time() - start
            if result.get("executed", False):
                baseline_executed = True
                baseline_times_list.append(elapsed)
                baseline_runs.append(result)
        
        if baseline_executed and baseline_times_list:
            baseline_mean = statistics.mean(baseline_times_list)
            baseline_std = statistics.stdev(baseline_times_list) if len(baseline_times_list) > 1 else 0.0
            baseline_variance = compute_variance_count(baseline_runs)
            baseline_times.append(baseline_mean)
        else:
            baseline_mean = None
            baseline_std = None
            baseline_variance = None
        
        results.append({
            "doc_id": doc_id,
            "hybrid_mean_time": hybrid_mean,
            "hybrid_std_time": hybrid_std,
            "hybrid_variance": hybrid_variance,
            "baseline_mean_time": baseline_mean,
            "baseline_std_time": baseline_std,
            "baseline_variance": baseline_variance,
            "baseline_executed": baseline_executed,
        })
    
    # Summary
    hybrid_avg = statistics.mean(hybrid_times) if hybrid_times else 0
    hybrid_avg_std = statistics.mean([r["hybrid_std_time"] for r in results]) if results else 0
    hybrid_total_var = sum(r["hybrid_variance"] for r in results)
    
    if baseline_times:
        baseline_avg = statistics.mean(baseline_times)
        baseline_avg_std = statistics.mean([r["baseline_std_time"] for r in results if r["baseline_executed"]])
        baseline_total_var = sum(r["baseline_variance"] for r in results if r["baseline_executed"])
        baseline_count = sum(1 for r in results if r["baseline_executed"])
    else:
        baseline_avg = None
        baseline_avg_std = None
        baseline_total_var = None
        baseline_count = 0
    
    summary = {
        "hybrid_avg_time": hybrid_avg,
        "hybrid_avg_std": hybrid_avg_std,
        "hybrid_total_variance": hybrid_total_var,
        "baseline_avg_time": baseline_avg,
        "baseline_avg_std": baseline_avg_std,
        "baseline_total_variance": baseline_total_var,
        "baseline_executed_count": baseline_count,
        "total_documents": len(results),
    }
    
    return results, summary


def main():
    """Run quick ICCS experiments."""
    print("=" * 80)
    print("ICCS EXPERIMENTS - QUICK MODE")
    print("=" * 80)
    print("Note: This is a quick test. For full results, use run_iccs_experiments.py")
    print("=" * 80)
    
    # Experiment 2
    exp2_results = run_exp2_quick()
    
    # Experiment 3
    exp3_results, exp3_summary = run_exp3_quick()
    
    # Save results
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Save Exp 2
    exp2_csv = results_dir / "exp2_iccs_reproducibility.csv"
    if exp2_results:
        with open(exp2_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=exp2_results[0].keys())
            writer.writeheader()
            writer.writerows(exp2_results)
        print(f"\nExperiment 2 results saved to: {exp2_csv}")
    
    # Save Exp 3
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
    
    # Print summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
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
        print(f"    Documents with Variance: {baseline_with_variance}/{baseline_executed_count}")
        print(f"    Avg. Distinct Output Sets / Doc: {avg_baseline_distinct:.2f}")
    
    print(f"\nExperiment 3 (Computational Cost):")
    print(f"  Hybrid System:")
    print(f"    Avg. Execution Time / Doc: {exp3_summary['hybrid_avg_time']:.3f}s")
    print(f"    Output Variance: {exp3_summary['hybrid_total_variance']}")
    if exp3_summary['baseline_executed_count'] > 0:
        print(f"  Baseline System:")
        print(f"    Avg. Execution Time / Doc: {exp3_summary['baseline_avg_time']:.3f}s (std: {exp3_summary['baseline_avg_std']:.3f}s)")
        print(f"    Output Variance: {exp3_summary['baseline_total_variance']}")


if __name__ == "__main__":
    main()
