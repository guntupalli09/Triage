"""
Regenerate RESULTS.md from existing experiment artifacts and CSVs.
This loads results from completed experiments without re-running them.
"""
import sys
from pathlib import Path
import csv
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import RESULTS_DIR, EXPERIMENTS_DIR, HYBRID_ARTIFACTS, BASELINE_ARTIFACTS
from experiments.generate_results import generate_results_md
from experiments.utils_io import save_text, load_json
from experiments.statistical_analysis import compute_all_statistics


def load_exp1_results():
    """Load Experiment 1 results from CSV."""
    csv_path = RESULTS_DIR / "exp1_summary.csv"
    if not csv_path.exists():
        return []
    
    results = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert string booleans to actual booleans
            row['hybrid_deterministic'] = row.get('hybrid_deterministic', '').lower() == 'true'
            baseline_det = row.get('baseline_deterministic', '')
            row['baseline_deterministic'] = None if baseline_det == '' or baseline_det.lower() == 'none' else (baseline_det.lower() == 'true')
            
            # Convert numeric fields
            for key in ['baseline_avg_ungrounded', 'hybrid_traceability', 'fp_count', 'fn_count']:
                if key in row and row[key]:
                    try:
                        row[key] = float(row[key])
                    except:
                        row[key] = 0
            
            row['is_synthetic'] = row.get('is_synthetic', '').lower() == 'true'
            results.append(row)
    
    return results


def load_exp2_results():
    """Load Experiment 2 results from CSV."""
    csv_path = RESULTS_DIR / "exp2_determinism.csv"
    if not csv_path.exists():
        return []
    
    results = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'variance_count' in row:
                try:
                    row['variance_count'] = int(row['variance_count'])
                except:
                    row['variance_count'] = 0
            results.append(row)
    
    return results


def load_exp3_results():
    """Load Experiment 3 results from CSV."""
    csv_path = RESULTS_DIR / "exp3_suppression.csv"
    if not csv_path.exists():
        return []
    
    results = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for key in ['fp_on', 'fn_on', 'fp_off', 'fn_off', 'fp_reduction', 'fn_change']:
                if key in row and row[key]:
                    try:
                        row[key] = int(row[key])
                    except:
                        row[key] = 0
            results.append(row)
    
    return results


def load_exp4_results():
    """Load Experiment 4 results from CSV."""
    csv_path = RESULTS_DIR / "exp4_errors.csv"
    if not csv_path.exists():
        return []
    
    results = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    
    return results


def load_timing_data():
    """Load timing data from artifacts if available."""
    hybrid_times = []
    baseline_times = []
    
    # Try to load timing from hybrid artifacts
    if HYBRID_ARTIFACTS.exists():
        for doc_dir in HYBRID_ARTIFACTS.iterdir():
            if doc_dir.is_dir():
                for run_file in doc_dir.glob("run_*.json"):
                    try:
                        data = load_json(run_file)
                        if 'execution_time' in data:
                            hybrid_times.append(data['execution_time'])
                    except:
                        pass
    
    # Try to load timing from baseline artifacts
    if BASELINE_ARTIFACTS.exists():
        for doc_dir in BASELINE_ARTIFACTS.iterdir():
            if doc_dir.is_dir():
                for run_file in doc_dir.glob("run_*.json"):
                    try:
                        data = load_json(run_file)
                        if 'execution_time' in data:
                            baseline_times.append(data['execution_time'])
                    except:
                        pass
    
    return hybrid_times, baseline_times


def check_baseline_executed():
    """Check if baseline was executed by looking at artifacts."""
    if not BASELINE_ARTIFACTS.exists():
        return False
    
    baseline_files = list(BASELINE_ARTIFACTS.glob("**/run_*.json"))
    if not baseline_files:
        return False
    
    # Check a sample file
    try:
        sample = load_json(baseline_files[0])
        return sample.get("executed", False)
    except:
        return False


def main():
    """Regenerate RESULTS.md from existing experiment data."""
    print("=" * 80)
    print("REGENERATING RESULTS.md FROM EXISTING EXPERIMENT DATA")
    print("=" * 80)
    
    # Load all experiment results
    print("\n[Loading] Experiment 1 results...")
    exp1_results = load_exp1_results()
    print(f"  Loaded {len(exp1_results)} documents")
    
    print("\n[Loading] Experiment 2 results...")
    exp2_results = load_exp2_results()
    print(f"  Loaded {len(exp2_results)} documents")
    
    print("\n[Loading] Experiment 3 results...")
    exp3_results = load_exp3_results()
    print(f"  Loaded {len(exp3_results)} documents")
    
    print("\n[Loading] Experiment 4 results...")
    exp4_issues = load_exp4_results()
    print(f"  Loaded {len(exp4_issues)} issues")
    
    print("\n[Loading] Timing data...")
    hybrid_times, baseline_times = load_timing_data()
    print(f"  Hybrid timing measurements: {len(hybrid_times)}")
    print(f"  Baseline timing measurements: {len(baseline_times)}")
    
    print("\n[Checking] Baseline execution status...")
    baseline_executed = check_baseline_executed()
    print(f"  Baseline executed: {baseline_executed}")
    
    print("\n[Computing] Statistical analysis...")
    try:
        stats_results = compute_all_statistics(exp1_results, exp3_results)
        # Convert numpy types to native Python types for JSON serialization
        def convert_to_native(obj):
            import numpy as np
            if isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_native(item) for item in obj]
            return obj
        
        stats_results = convert_to_native(stats_results)
        stats_path = RESULTS_DIR / "statistical_analysis.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats_results, f, indent=2)
        print(f"  Statistical analysis complete")
    except Exception as e:
        print(f"  Statistical analysis failed: {e}")
        import traceback
        traceback.print_exc()
        stats_results = {}
    
    print("\n[Generating] RESULTS.md...")
    try:
        results_md = generate_results_md(
            exp1_results, 
            exp2_results, 
            exp3_results, 
            exp4_issues, 
            baseline_executed, 
            hybrid_times, 
            baseline_times, 
            stats_results
        )
        results_path = EXPERIMENTS_DIR / "RESULTS.md"
        save_text(results_md, results_path)
        print(f"  [OK] RESULTS.md generated at {results_path}")
    except Exception as e:
        print(f"  [ERROR] RESULTS.md generation FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("REGENERATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
