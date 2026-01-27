"""
Main experiment orchestration script.
Run all experiments and generate results.
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import (
    DATA_DIR, RESULTS_DIR, EXPERIMENTS_DIR,
    NUM_PUBLIC_NDAS, NUM_SYNTHETIC_NDAS,
    NUM_SYNTHETIC_MSAS, NUM_SYNTHETIC_EMPLOYMENT, NUM_SYNTHETIC_LICENSING,
    NDA_DIR, MSA_DIR, EMPLOYMENT_DIR, LICENSING_DIR
)
from experiments.data.build_public_ndas import build_public_ndas
from experiments.data.build_synthetic_ndas import build_synthetic_ndas
from experiments.data.build_synthetic_msas import build_synthetic_msas
from experiments.data.build_synthetic_employment import build_synthetic_employment
from experiments.data.build_synthetic_licensing import build_synthetic_licensing
from experiments.exp1_baseline_vs_hybrid import run_experiment_1
from experiments.exp2_determinism_stress import run_experiment_2
from experiments.exp3_suppression_ablation import run_experiment_3
from experiments.exp4_error_characterization import characterize_errors
from experiments.generate_results import generate_results_md, save_csv
from experiments.statistical_analysis import compute_all_statistics
from experiments.utils_io import save_text, save_json


def main():
    """Run all experiments."""
    print("=" * 80)
    print("EXPERIMENT HARNESS - IEEE Paper Experiments")
    print("=" * 80)
    
    # Step 0: Build dataset if needed (all contract types)
    print("\n[STEP 0] Building dataset...")
    
    # Build NDAs
    public_files = list(NDA_DIR.glob("public_*.txt")) if NDA_DIR.exists() else []
    synthetic_nda_files = list(NDA_DIR.glob("synthetic_*.txt")) if NDA_DIR.exists() else []
    
    if len(public_files) < NUM_PUBLIC_NDAS:
        print("  Building public NDAs...")
        build_public_ndas()
    else:
        print(f"  Found {len(public_files)} public NDAs, skipping build")
    
    if len(synthetic_nda_files) < NUM_SYNTHETIC_NDAS:
        print("  Building synthetic NDAs...")
        build_synthetic_ndas()
    else:
        print(f"  Found {len(synthetic_nda_files)} synthetic NDAs, skipping build")
    
    # Build MSAs
    msa_files = list(MSA_DIR.glob("msa_*.txt")) if MSA_DIR.exists() else []
    if len(msa_files) < NUM_SYNTHETIC_MSAS:
        print("  Building synthetic MSAs...")
        build_synthetic_msas()
    else:
        print(f"  Found {len(msa_files)} synthetic MSAs, skipping build")
    
    # Build Employment Agreements
    emp_files = list(EMPLOYMENT_DIR.glob("emp_*.txt")) if EMPLOYMENT_DIR.exists() else []
    if len(emp_files) < NUM_SYNTHETIC_EMPLOYMENT:
        print("  Building synthetic Employment Agreements...")
        build_synthetic_employment()
    else:
        print(f"  Found {len(emp_files)} synthetic Employment Agreements, skipping build")
    
    # Build Licensing Agreements
    lic_files = list(LICENSING_DIR.glob("lic_*.txt")) if LICENSING_DIR.exists() else []
    if len(lic_files) < NUM_SYNTHETIC_LICENSING:
        print("  Building synthetic Licensing Agreements...")
        build_synthetic_licensing()
    else:
        print(f"  Found {len(lic_files)} synthetic Licensing Agreements, skipping build")
    
    # Step 1: Experiment 1
    print("\n[STEP 1] Running Experiment 1: Baseline vs Hybrid...")
    baseline_executed = False
    hybrid_times = []
    baseline_times = []
    try:
        exp1_results, baseline_executed, hybrid_times, baseline_times = run_experiment_1()
        save_csv(
            exp1_results,
            "exp1_summary.csv",
            ["doc_id", "hybrid_deterministic", "baseline_deterministic", "baseline_avg_ungrounded", 
             "hybrid_traceability", "fp_count", "fn_count", "is_synthetic"]
        )
        print(f"  Experiment 1 complete: {len(exp1_results)} documents processed")
        print(f"  Baseline executed: {baseline_executed}")
        if hybrid_times:
            print(f"  Hybrid timing: {len(hybrid_times)} measurements collected")
        if baseline_times:
            print(f"  Baseline timing: {len(baseline_times)} measurements collected")
    except Exception as e:
        print(f"  Experiment 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        exp1_results = []
        hybrid_times = []
        baseline_times = []
        # Check if baseline was executed by looking at artifacts
        from experiments.config import BASELINE_ARTIFACTS
        from experiments.utils_io import load_json
        baseline_files = list(BASELINE_ARTIFACTS.glob("**/run_*.json"))
        if baseline_files:
            try:
                sample_result = load_json(baseline_files[0])
                baseline_executed = sample_result.get("executed", False)
                print(f"  Baseline execution status from artifacts: {baseline_executed}")
            except Exception as ex:
                print(f"  Could not check baseline artifacts: {ex}")
    print(f"  Experiment 1 complete: {len(exp1_results)} documents processed")
    
    # Step 2: Experiment 2
    print("\n[STEP 2] Running Experiment 2: Determinism Stress Test...")
    try:
        exp2_results = run_experiment_2()
        save_csv(
            exp2_results,
            "exp2_determinism.csv",
            ["doc_id", "variance_count"]
        )
        print(f"  Experiment 2 complete: {len(exp2_results)} documents processed")
    except Exception as e:
        print(f"  Experiment 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        exp2_results = []
    
    # Step 3: Experiment 3
    print("\n[STEP 3] Running Experiment 3: Suppression Ablation...")
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
        print(f"  Experiment 3 complete: {len(exp3_results)} documents processed")
    except Exception as e:
        print(f"  Experiment 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        exp3_results = []
    
    # Step 4: Experiment 4
    print("\n[STEP 4] Running Experiment 4: Error Characterization...")
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
        save_csv(exp4_issues, "exp4_errors.csv", csv_columns)
        print(f"  Experiment 4 complete: {len(exp4_issues)} issues found")
    except Exception as e:
        print(f"  Experiment 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        exp4_issues = []
    
    # Step 5: Statistical Analysis
    print("\n[STEP 5] Computing Statistical Significance Tests...")
    stats_results = {}
    try:
        stats_results = compute_all_statistics(exp1_results, exp3_results)
        save_json(stats_results, RESULTS_DIR / "statistical_analysis.json")
        print("  Statistical analysis complete")
        print(f"  Saved to: {RESULTS_DIR / 'statistical_analysis.json'}")
    except Exception as e:
        print(f"  Statistical analysis FAILED: {e}")
        import traceback
        traceback.print_exc()
        stats_results = {}
    
    # Step 6: Generate RESULTS.md
    print("\n[STEP 6] Generating RESULTS.md...")
    try:
        results_md = generate_results_md(exp1_results, exp2_results, exp3_results, exp4_issues, baseline_executed, hybrid_times, baseline_times, stats_results)
        results_path = EXPERIMENTS_DIR / "RESULTS.md"
        save_text(results_md, results_path)
        print(f"  RESULTS.md generated at {results_path}")
    except Exception as e:
        print(f"  RESULTS.md generation FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Final check: Verify baseline execution status from artifacts
    # This ensures we report correctly even if Experiment 1 failed
    if not baseline_executed:
        from experiments.config import BASELINE_ARTIFACTS
        from experiments.utils_io import load_json
        baseline_files = list(BASELINE_ARTIFACTS.glob("**/run_*.json"))
        if baseline_files:
            try:
                sample_result = load_json(baseline_files[0])
                if sample_result.get("executed", False):
                    baseline_executed = True
                    print(f"\nNote: Baseline execution detected from artifacts ({len(baseline_files)} files found)")
            except:
                pass
    
    print("\n" + "=" * 80)
    print("ALL EXPERIMENTS COMPLETE")
    print("=" * 80)
    print(f"\nResults:")
    print(f"  - RESULTS.md: {results_path}")
    print(f"  - CSVs: {RESULTS_DIR}")
    print(f"  - Artifacts: experiments/artifacts/")
    print(f"\nBaseline execution status: {'EXECUTED' if baseline_executed else 'NOT EXECUTED (OpenAI API key missing)'}")


if __name__ == "__main__":
    main()
