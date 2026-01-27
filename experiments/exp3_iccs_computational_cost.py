"""
Experiment 3 (ICCS): Computational Cost of Determinism
Measures runtime, complexity, and output variance across all 115 documents.
"""
import sys
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import (
    NDA_DIR, MSA_DIR, EMPLOYMENT_DIR, LICENSING_DIR,
    ARTIFACTS_DIR, TOTAL_DOCS_EXPANDED
)
from experiments.utils_io import get_doc_ids, read_text, save_json, find_doc_file
from experiments.run_hybrid import run_hybrid_engine
from experiments.run_baseline_llm import run_baseline_llm
from experiments.metrics import compute_variance_count
from experiments.normalize import normalize_hybrid_findings, normalize_baseline_findings


COMPUTATIONAL_COST_ARTIFACTS = ARTIFACTS_DIR / "iccs_computational_cost"


def get_all_doc_ids() -> List[str]:
    """Get document IDs from all contract type directories (only .txt files)."""
    all_ids = set()
    for data_dir in [NDA_DIR, MSA_DIR, EMPLOYMENT_DIR, LICENSING_DIR]:
        if data_dir.exists():
            # Get only .txt files, exclude metadata
            txt_files = list(data_dir.glob("*.txt"))
            ids = [f.stem for f in txt_files]
            all_ids.update(ids)
    # Return sorted list
    return sorted(list(all_ids))


def measure_hybrid_runtime(text: str, num_runs: int = 5) -> Tuple[float, float, int]:
    """
    Measure hybrid system runtime and variance.
    Returns: (mean_time, std_time, variance_count)
    """
    times = []
    runs = []
    
    for _ in range(num_runs):
        start = time.time()
        result = run_hybrid_engine(text, suppression_enabled=True)
        elapsed = time.time() - start
        times.append(elapsed)
        runs.append(result)
    
    mean_time = statistics.mean(times)
    std_time = statistics.stdev(times) if len(times) > 1 else 0.0
    variance = compute_variance_count(runs)
    
    return mean_time, std_time, variance


def measure_baseline_runtime(text: str, num_runs: int = 5) -> Tuple[float, float, int, bool]:
    """
    Measure baseline LLM runtime and variance.
    Returns: (mean_time, std_time, variance_count, executed)
    """
    times = []
    runs = []
    executed = False
    
    for _ in range(num_runs):
        start = time.time()
        result = run_baseline_llm(text)
        elapsed = time.time() - start
        
        if result.get("executed", False):
            executed = True
            times.append(elapsed)
            runs.append(result)
    
    if not executed or len(times) == 0:
        return None, None, None, False
    
    mean_time = statistics.mean(times)
    std_time = statistics.stdev(times) if len(times) > 1 else 0.0
    variance = compute_variance_count(runs)
    
    return mean_time, std_time, variance, True


def run_iccs_computational_cost():
    """Run computational cost analysis on all 115 documents."""
    print("=" * 80)
    print("ICCS EXPERIMENT 3: Computational Cost of Determinism")
    print("=" * 80)
    
    all_doc_ids = get_all_doc_ids()
    print(f"Total documents: {len(all_doc_ids)}")
    print(f"Running on all {len(all_doc_ids)} documents...")
    
    results = []
    hybrid_times = []
    baseline_times = []
    
    for idx, doc_id in enumerate(all_doc_ids, 1):
        print(f"\n[{idx}/{len(all_doc_ids)}] Processing {doc_id}...")
        
        # Find document across all contract type directories
        text_path = None
        for data_dir in [NDA_DIR, MSA_DIR, EMPLOYMENT_DIR, LICENSING_DIR]:
            text_path = find_doc_file(data_dir, doc_id, ".txt")
            if text_path:
                break
        
        if not text_path:
            print(f"  Skipping {doc_id}: text file not found")
            continue
        
        text = read_text(text_path)
        
        # Measure hybrid system
        hybrid_mean, hybrid_std, hybrid_variance = measure_hybrid_runtime(text, num_runs=3)
        hybrid_times.append(hybrid_mean)
        
        # Measure baseline (if available)
        baseline_mean, baseline_std, baseline_variance, baseline_executed = measure_baseline_runtime(text, num_runs=3)
        if baseline_executed:
            baseline_times.append(baseline_mean)
        
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
        
        print(f"  Hybrid: {hybrid_mean:.3f}s (std: {hybrid_std:.3f}s), variance={hybrid_variance}")
        if baseline_executed:
            print(f"  Baseline: {baseline_mean:.3f}s (std: {baseline_std:.3f}s), variance={baseline_variance}")
    
    # Compute summary statistics
    hybrid_avg_time = statistics.mean(hybrid_times) if hybrid_times else 0
    hybrid_avg_std = statistics.mean([r["hybrid_std_time"] for r in results]) if results else 0
    hybrid_total_variance = sum(r["hybrid_variance"] for r in results)
    
    if baseline_times:
        baseline_avg_time = statistics.mean(baseline_times)
        baseline_avg_std = statistics.mean([r["baseline_std_time"] for r in results if r["baseline_executed"]])
        baseline_total_variance = sum(r["baseline_variance"] for r in results if r["baseline_executed"])
        baseline_executed_count = sum(1 for r in results if r["baseline_executed"])
    else:
        baseline_avg_time = None
        baseline_avg_std = None
        baseline_total_variance = None
        baseline_executed_count = 0
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Hybrid System (all {len(results)} documents):")
    print(f"  Avg execution time: {hybrid_avg_time:.3f}s (std: {hybrid_avg_std:.3f}s)")
    print(f"  Total variance across all runs: {hybrid_total_variance}")
    print(f"  Reproducibility rate: {100.0 if hybrid_total_variance == 0 else 0.0}%")
    
    if baseline_executed_count > 0:
        print(f"Baseline System ({baseline_executed_count} documents):")
        print(f"  Avg execution time: {baseline_avg_time:.3f}s (std: {baseline_avg_std:.3f}s)")
        print(f"  Total variance across all runs: {baseline_total_variance}")
        print(f"  Reproducibility rate: 0.0%")
    else:
        print("Baseline System: NOT EXECUTED (no API key)")
    
    return results, {
        "hybrid_avg_time": hybrid_avg_time,
        "hybrid_avg_std": hybrid_avg_std,
        "hybrid_total_variance": hybrid_total_variance,
        "baseline_avg_time": baseline_avg_time,
        "baseline_avg_std": baseline_avg_std,
        "baseline_total_variance": baseline_total_variance,
        "baseline_executed_count": baseline_executed_count,
        "total_documents": len(results),
    }


if __name__ == "__main__":
    results, summary = run_iccs_computational_cost()
    
    # Save results
    import csv
    results_path = Path(__file__).parent.parent / "experiments" / "results" / "exp3_iccs_computational_cost.csv"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    print(f"\nResults saved to: {results_path}")
    
    # Save summary
    summary_path = Path(__file__).parent.parent / "experiments" / "results" / "exp3_iccs_computational_cost_summary.json"
    save_json(summary, summary_path)
    print(f"Summary saved to: {summary_path}")
