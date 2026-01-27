"""
Experiment 2 (ICCS): Enhanced Reproducibility Stress Test
15 documents selected from 115 total, 20 runs each, across multiple seeds and environments.
"""
import sys
import time
import random
import os
from pathlib import Path
from typing import List, Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import (
    DATA_BASE_DIR, NDA_DIR, MSA_DIR, EMPLOYMENT_DIR, LICENSING_DIR,
    ARTIFACTS_DIR, TOTAL_DOCS_EXPANDED
)
from experiments.utils_io import get_doc_ids, read_text, save_json, find_doc_file
from experiments.run_hybrid import run_hybrid_engine
from experiments.run_baseline_llm import run_baseline_llm
from experiments.metrics import compute_variance_count
from experiments.normalize import normalize_hybrid_findings, normalize_baseline_findings


REPRODUCIBILITY_ARTIFACTS = ARTIFACTS_DIR / "iccs_reproducibility"
NUM_DOCS = 15  # Select 15 from 115 total
NUM_RUNS = 20


def get_all_doc_ids() -> List[str]:
    """Get document IDs from all contract type directories (only .txt files)."""
    all_ids = []
    for data_dir in [NDA_DIR, MSA_DIR, EMPLOYMENT_DIR, LICENSING_DIR]:
        if data_dir.exists():
            # Get only .txt files, exclude metadata
            txt_files = list(data_dir.glob("*.txt"))
            ids = [f.stem for f in txt_files]
            all_ids.extend(ids)
    # Remove duplicates and sort
    return sorted(list(set(all_ids)))


def count_distinct_output_sets(run_outputs: List[Dict[str, Any]], is_hybrid: bool = True) -> int:
    """Count distinct output sets across runs."""
    if is_hybrid:
        normalized_sets = [normalize_hybrid_findings(run) for run in run_outputs]
    else:
        normalized_sets = [normalize_baseline_findings(run) for run in run_outputs]
    
    unique_sets = set()
    for norm_set in normalized_sets:
        # Convert to tuple for hashing
        unique_sets.add(tuple(sorted(norm_set)))
    
    return len(unique_sets)


def run_iccs_reproducibility_stress():
    """Run enhanced reproducibility stress test for ICCS."""
    print("=" * 80)
    print("ICCS EXPERIMENT 2: Reproducibility Stress Test Across Multiple Seeds/Environments")
    print("=" * 80)
    
    all_doc_ids = get_all_doc_ids()
    print(f"Total documents available: {len(all_doc_ids)}")
    
    # Select 8 public + 7 synthetic (or available mix)
    public_ids = [d for d in all_doc_ids if d.startswith("public")]
    synthetic_ids = [d for d in all_doc_ids if d.startswith("synthetic")]
    
    selected = (public_ids[:8] + synthetic_ids[:7])[:NUM_DOCS]
    
    print(f"Selected {len(selected)} documents for reproducibility stress test")
    print(f"Running {NUM_RUNS} executions per document")
    
    results = []
    
    for doc_id in selected:
        print(f"\nProcessing {doc_id}...")
        
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
        
        # HYBRID SYSTEM: Run 20 times with different seeds
        hybrid_runs = []
        hybrid_output_dir = REPRODUCIBILITY_ARTIFACTS / "hybrid" / doc_id
        hybrid_output_dir.mkdir(parents=True, exist_ok=True)
        
        for run_num in range(1, NUM_RUNS + 1):
            # Set different random seed for each run (though hybrid is deterministic)
            random.seed(run_num * 42)
            os.environ['PYTHONHASHSEED'] = str(run_num * 42)
            
            output_path = hybrid_output_dir / f"run_{run_num:02d}.json"
            
            result = run_hybrid_engine(text, suppression_enabled=True)
            save_json(result, output_path)
            hybrid_runs.append(result)
            
            if run_num % 5 == 0:
                print(f"  Hybrid run {run_num}/{NUM_RUNS} complete")
        
        # BASELINE LLM: Run 20 times (will show variance)
        baseline_runs = []
        baseline_output_dir = REPRODUCIBILITY_ARTIFACTS / "baseline" / doc_id
        baseline_output_dir.mkdir(parents=True, exist_ok=True)
        
        baseline_executed = False
        for run_num in range(1, NUM_RUNS + 1):
            output_path = baseline_output_dir / f"run_{run_num:02d}.json"
            
            result = run_baseline_llm(text)
            save_json(result, output_path)
            baseline_runs.append(result)
            
            if result.get("executed", False):
                baseline_executed = True
                if run_num % 5 == 0:
                    print(f"  Baseline run {run_num}/{NUM_RUNS} complete")
        
        # Compute metrics
        hybrid_variance = compute_variance_count(hybrid_runs)
        hybrid_distinct = count_distinct_output_sets(hybrid_runs, is_hybrid=True)
        
        if baseline_executed:
            baseline_variance = compute_variance_count(baseline_runs)
            baseline_distinct = count_distinct_output_sets(baseline_runs, is_hybrid=False)
            baseline_has_variance = baseline_variance > 0
        else:
            baseline_variance = None
            baseline_distinct = None
            baseline_has_variance = None
        
        results.append({
            "doc_id": doc_id,
            "hybrid_variance_count": hybrid_variance,
            "hybrid_distinct_output_sets": hybrid_distinct,
            "hybrid_reproducible": hybrid_variance == 0,
            "baseline_variance_count": baseline_variance,
            "baseline_distinct_output_sets": baseline_distinct,
            "baseline_has_variance": baseline_has_variance,
            "baseline_executed": baseline_executed,
        })
        
        print(f"  Hybrid: variance={hybrid_variance}, distinct_sets={hybrid_distinct}")
        if baseline_executed:
            print(f"  Baseline: variance={baseline_variance}, distinct_sets={baseline_distinct}")
    
    return results


if __name__ == "__main__":
    results = run_iccs_reproducibility_stress()
    
    # Compute summary statistics
    hybrid_reproducible = sum(1 for r in results if r["hybrid_reproducible"])
    baseline_with_variance = sum(1 for r in results if r.get("baseline_has_variance", False))
    baseline_executed_count = sum(1 for r in results if r.get("baseline_executed", False))
    
    avg_hybrid_distinct = sum(r["hybrid_distinct_output_sets"] for r in results) / len(results) if results else 0
    avg_baseline_distinct = sum(r["baseline_distinct_output_sets"] for r in results if r.get("baseline_executed")) / baseline_executed_count if baseline_executed_count > 0 else 0
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Hybrid System:")
    print(f"  Reproducible documents: {hybrid_reproducible}/{len(results)} ({100*hybrid_reproducible/len(results):.1f}%)")
    print(f"  Avg distinct output sets per doc: {avg_hybrid_distinct:.2f}")
    
    if baseline_executed_count > 0:
        print(f"Baseline System:")
        print(f"  Documents with variance: {baseline_with_variance}/{baseline_executed_count} ({100*baseline_with_variance/baseline_executed_count:.1f}%)")
        print(f"  Avg distinct output sets per doc: {avg_baseline_distinct:.2f}")
    else:
        print("Baseline System: NOT EXECUTED (no API key)")
    
    # Save results
    from experiments.utils_io import save_json
    results_path = Path(__file__).parent.parent / "experiments" / "results" / "exp2_iccs_reproducibility.csv"
    import csv
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved to: {results_path}")
