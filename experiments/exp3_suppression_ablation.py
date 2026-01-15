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
from experiments.utils_io import get_doc_ids, read_text, load_json
from experiments.run_hybrid import run_hybrid_engine
from experiments.metrics import compute_fp_fn_hybrid


def run_experiment_3():
    """
    Run Experiment 3: Suppression ablation.
    
    NOTE: The current RuleEngine.analyze() method always applies suppression.
    To properly test suppression ON vs OFF, we would need to modify the core engine
    to accept a suppression_enabled parameter. Per constraints, we do not modify
    core logic. This experiment runs with suppression ON and documents the limitation.
    """
    print("=" * 80)
    print("EXPERIMENT 3: Suppression Ablation")
    print("=" * 80)
    print("NOTE: Suppression cannot be toggled without modifying core engine.")
    print("Running with suppression ON only. Limitation documented in results.")
    print("=" * 80)
    
    doc_ids = get_doc_ids(DATA_DIR)
    synthetic_ids = [d for d in doc_ids if d.startswith("synthetic")]
    
    results = []
    
    for doc_id in synthetic_ids:
        print(f"\nProcessing {doc_id}...")
        
        text_path = DATA_DIR / f"{doc_id}.txt"
        truth_path = DATA_DIR / f"{doc_id}.truth.json"
        
        if not text_path.exists() or not truth_path.exists():
            print(f"  Skipping {doc_id}: missing files")
            continue
        
        text = read_text(text_path)
        truth = load_json(truth_path)
        
        # Run with suppression ON (only option available)
        result_on = run_hybrid_engine(text, suppression_enabled=True)
        fp_on, fn_on = compute_fp_fn_hybrid(result_on, truth)
        
        # For OFF, we would need to modify core engine
        # Documenting as limitation
        fp_off = None
        fn_off = None
        
        results.append({
            "doc_id": doc_id,
            "fp_on": fp_on,
            "fn_on": fn_on,
            "fp_off": fp_off,
            "fn_off": fn_off,
            "note": "Suppression OFF not available without core engine modification"
        })
    
    return results


if __name__ == "__main__":
    results = run_experiment_3()
    print(f"\nExperiment 3 complete. Processed {len(results)} synthetic documents.")
