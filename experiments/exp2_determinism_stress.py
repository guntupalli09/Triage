"""
Experiment 2: Determinism stress test (10 docs, 10 runs each).
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import DATA_DIR, STRESS_ARTIFACTS, RUNS_PER_DOC_EXP2, STRESS_TEST_DOCS
from experiments.utils_io import get_doc_ids, read_text, save_json
from experiments.run_hybrid import run_hybrid_engine
from experiments.metrics import compute_variance_count


def run_experiment_2():
    """Run Experiment 2: Determinism stress test."""
    print("=" * 80)
    print("EXPERIMENT 2: Determinism Stress Test")
    print("=" * 80)
    
    doc_ids = get_doc_ids(DATA_DIR)
    
    # Prefer mix of public and synthetic, prioritize high-risk synthetic
    synthetic_ids = [d for d in doc_ids if d.startswith("synthetic")]
    public_ids = [d for d in doc_ids if d.startswith("public")]
    
    # Select 5 synthetic + 5 public (or available)
    selected = (synthetic_ids[:5] + public_ids[:5])[:STRESS_TEST_DOCS]
    
    print(f"Selected {len(selected)} documents for stress test")
    
    results = []
    
    for doc_id in selected:
        print(f"\nProcessing {doc_id}...")
        
        text_path = DATA_DIR / f"{doc_id}.txt"
        if not text_path.exists():
            print(f"  Skipping {doc_id}: text file not found")
            continue
        
        text = read_text(text_path)
        
        # Run 10 times
        runs = []
        for run_num in range(1, RUNS_PER_DOC_EXP2 + 1):
            output_path = STRESS_ARTIFACTS / doc_id / f"run_{run_num:02d}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            result = run_hybrid_engine(text, suppression_enabled=True)
            save_json(result, output_path)
            runs.append(result)
            print(f"  Run {run_num} complete")
        
        # Compute variance
        variance = compute_variance_count(runs)
        
        results.append({
            "doc_id": doc_id,
            "variance_count": variance,
        })
        
        if variance > 0:
            print(f"  WARNING: {variance} runs differ from run_01")
    
    return results


if __name__ == "__main__":
    results = run_experiment_2()
    print(f"\nExperiment 2 complete. Found {sum(r['variance_count'] for r in results)} total variances")
