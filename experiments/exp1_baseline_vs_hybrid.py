"""
Experiment 1: Baseline vs Hybrid comparison.
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import (
    DATA_DIR, HYBRID_ARTIFACTS, BASELINE_ARTIFACTS,
    RUNS_PER_DOC_EXP1, TOTAL_DOCS
)
from experiments.utils_io import get_doc_ids, read_text, save_json, load_json
from experiments.run_hybrid import run_hybrid_engine
from experiments.run_baseline_llm import run_baseline_llm
from experiments.metrics import (
    check_determinism_hybrid, check_determinism_baseline,
    count_ungrounded_baseline, compute_traceability_hybrid,
    compute_fp_fn_hybrid
)


def run_experiment_1():
    """Run Experiment 1: Baseline vs Hybrid comparison."""
    print("=" * 80)
    print("EXPERIMENT 1: Baseline vs Hybrid Comparison")
    print("=" * 80)
    
    doc_ids = get_doc_ids(DATA_DIR)
    if len(doc_ids) < TOTAL_DOCS:
        print(f"Warning: Found {len(doc_ids)} docs, expected {TOTAL_DOCS}")
    
    results = []
    baseline_executed = False
    
    for doc_id in doc_ids[:TOTAL_DOCS]:
        print(f"\nProcessing {doc_id}...")
        
        text_path = DATA_DIR / f"{doc_id}.txt"
        if not text_path.exists():
            print(f"  Skipping {doc_id}: text file not found")
            continue
        
        text = read_text(text_path)
        
        # Run HYBRID 5 times
        hybrid_runs = []
        for run_num in range(1, RUNS_PER_DOC_EXP1 + 1):
            output_path = HYBRID_ARTIFACTS / doc_id / f"run_{run_num:02d}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            result = run_hybrid_engine(text, suppression_enabled=True)
            save_json(result, output_path)
            hybrid_runs.append(result)
            print(f"  Hybrid run {run_num} complete")
        
        # Run BASELINE 5 times
        baseline_runs = []
        for run_num in range(1, RUNS_PER_DOC_EXP1 + 1):
            output_path = BASELINE_ARTIFACTS / doc_id / f"run_{run_num:02d}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            result = run_baseline_llm(text)
            save_json(result, output_path)
            baseline_runs.append(result)
            
            if result.get("executed", False):
                baseline_executed = True
                print(f"  Baseline run {run_num} complete")
            else:
                print(f"  Baseline run {run_num} skipped (no API key)")
        
        # Compute metrics
        hybrid_deterministic = check_determinism_hybrid(hybrid_runs)
        baseline_deterministic = check_determinism_baseline(baseline_runs) if baseline_runs[0].get("executed") else None
        
        # Baseline ungrounded count (average across runs)
        ungrounded_counts = []
        if baseline_runs[0].get("executed"):
            for run in baseline_runs:
                ungrounded_counts.append(count_ungrounded_baseline(run, text))
        avg_ungrounded = sum(ungrounded_counts) / len(ungrounded_counts) if ungrounded_counts else None
        
        # Hybrid traceability (should be 100%)
        traceability = compute_traceability_hybrid(hybrid_runs[0])
        
        # FP/FN for synthetic docs
        fp_total = 0
        fn_total = 0
        truth_path = DATA_DIR / f"{doc_id}.truth.json"
        if truth_path.exists():
            truth = load_json(truth_path)
            fp, fn = compute_fp_fn_hybrid(hybrid_runs[0], truth)
            fp_total = fp
            fn_total = fn
        
        results.append({
            "doc_id": doc_id,
            "hybrid_deterministic": hybrid_deterministic,
            "baseline_deterministic": baseline_deterministic,
            "baseline_avg_ungrounded": avg_ungrounded,
            "hybrid_traceability": traceability,
            "fp_count": fp_total,
            "fn_count": fn_total,
            "is_synthetic": truth_path.exists(),
        })
    
    return results, baseline_executed


if __name__ == "__main__":
    results, baseline_executed = run_experiment_1()
    print(f"\nExperiment 1 complete. Baseline executed: {baseline_executed}")
