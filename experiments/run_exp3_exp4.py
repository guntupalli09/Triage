"""
Run only Experiments 3 and 4 (Suppression Ablation and Error Characterization).
This saves time when you only need to regenerate these specific results.
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import RESULTS_DIR, EXPERIMENTS_DIR
from experiments.exp3_suppression_ablation import run_experiment_3
from experiments.exp4_error_characterization import characterize_errors
from experiments.generate_results import save_csv
from experiments.utils_io import save_text


def main():
    """Run only Experiments 3 and 4."""
    print("=" * 80)
    print("RUNNING EXPERIMENTS 3 & 4 ONLY")
    print("=" * 80)
    
    # Experiment 3: Suppression Ablation
    print("\n[EXPERIMENT 3] Running Suppression Ablation...")
    try:
        exp3_results = run_experiment_3()
        # Determine CSV columns dynamically based on actual data
        if exp3_results:
            all_keys = set()
            for result in exp3_results:
                all_keys.update(result.keys())
            csv_columns = sorted(list(all_keys))
        else:
            csv_columns = ["doc_id", "fp_on", "fn_on", "fp_off", "fn_off", "fp_reduction", "fn_change"]
        save_csv(exp3_results, "exp3_suppression.csv", csv_columns)
        print(f"  [OK] Experiment 3 complete: {len(exp3_results)} documents processed")
        print(f"  [OK] CSV saved: {RESULTS_DIR / 'exp3_suppression.csv'}")
    except Exception as e:
        print(f"  [ERROR] Experiment 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        exp3_results = []
    
    # Experiment 4: Error Characterization
    print("\n[EXPERIMENT 4] Running Error Characterization...")
    try:
        exp4_issues = characterize_errors()
        # Determine CSV columns dynamically based on actual data
        if exp4_issues:
            all_keys = set()
            for issue in exp4_issues:
                all_keys.update(issue.keys())
            # Order columns logically
            preferred_order = ["issue_id", "doc_id", "system", "type", "category", "description", "example_rules", "missing_rules", "mitigation"]
            csv_columns = []
            # Add preferred columns in order if they exist
            for col in preferred_order:
                if col in all_keys:
                    csv_columns.append(col)
            # Add any remaining columns
            for col in sorted(all_keys):
                if col not in csv_columns:
                    csv_columns.append(col)
        else:
            csv_columns = ["issue_id", "doc_id", "system", "type", "description", "mitigation"]
        # Convert list fields to strings for CSV compatibility
        for issue in exp4_issues:
            if 'example_rules' in issue and isinstance(issue['example_rules'], list):
                issue['example_rules'] = ', '.join(str(r) for r in issue['example_rules'])
            if 'missing_rules' in issue and isinstance(issue['missing_rules'], list):
                issue['missing_rules'] = ', '.join(str(r) for r in issue['missing_rules'])
        save_csv(exp4_issues, "exp4_errors.csv", csv_columns)
        print(f"  [OK] Experiment 4 complete: {len(exp4_issues)} issues found")
        print(f"  [OK] CSV saved: {RESULTS_DIR / 'exp4_errors.csv'}")
    except Exception as e:
        print(f"  [ERROR] Experiment 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        exp4_issues = []
    
    print("\n" + "=" * 80)
    print("EXPERIMENTS 3 & 4 COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
