"""
Experiment 3: Suppression ablation study.
NOTE: Current implementation does not support toggling suppression without code changes.
This experiment documents the limitation and runs with suppression ON only.
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import DATA_DIR
from experiments.utils_io import get_doc_ids, read_text, load_json, find_doc_file
from experiments.run_hybrid import run_hybrid_engine
from experiments.metrics import compute_fp_fn_hybrid


def run_experiment_3():
    """
    Run Experiment 3: Suppression ablation.
    
    Tests the impact of false-positive suppression on precision and recall.
    Runs hybrid engine with suppression ON and OFF to measure differences.
    """
    print("=" * 80)
    print("EXPERIMENT 3: Suppression Ablation")
    print("=" * 80)
    print("Testing suppression ON vs OFF to measure impact on FP/FN rates.")
    print("=" * 80)
    
    doc_ids = get_doc_ids(DATA_DIR)
    synthetic_ids = [d for d in doc_ids if d.startswith("synthetic")]
    
    results = []
    
    for doc_id in synthetic_ids:
        print(f"\nProcessing {doc_id}...")
        
        text_path = find_doc_file(DATA_DIR, doc_id, ".txt")
        truth_path = find_doc_file(DATA_DIR, doc_id, ".truth.json")
        
        if not text_path or not text_path.exists():
            print(f"  Skipping {doc_id}: text file not found")
            continue
        
        if not truth_path or not truth_path.exists():
            print(f"  Skipping {doc_id}: truth file not found")
            continue
        
        text = read_text(text_path)
        truth = load_json(truth_path)
        
        # Run with suppression ON
        result_on = run_hybrid_engine(text, suppression_enabled=True)
        fp_on, fn_on = compute_fp_fn_hybrid(result_on, truth)
        
        # Run with suppression OFF
        result_off = run_hybrid_engine(text, suppression_enabled=False)
        fp_off, fn_off = compute_fp_fn_hybrid(result_off, truth)
        
        results.append({
            "doc_id": doc_id,
            "fp_on": fp_on,
            "fn_on": fn_on,
            "fp_off": fp_off,
            "fn_off": fn_off,
            "fp_reduction": fp_off - fp_on,  # How many FPs were suppressed
            "fn_change": fn_off - fn_on,  # Did suppression cause any FNs?
        })
    
    return results


if __name__ == "__main__":
    results = run_experiment_3()
    print(f"\nExperiment 3 complete. Processed {len(results)} synthetic documents.")
