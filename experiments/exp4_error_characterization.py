"""
Experiment 4: Error characterization.
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import DATA_DIR, HYBRID_ARTIFACTS, BASELINE_ARTIFACTS, STRESS_ARTIFACTS
from experiments.utils_io import load_json, get_doc_ids
from experiments.metrics import compute_variance_count, compute_fp_fn_hybrid
import traceback


def characterize_errors():
    """Characterize all observed errors and issues."""
    print("=" * 80)
    print("EXPERIMENT 4: Error Characterization")
    print("=" * 80)
    
    issues = []
    issue_id = 1
    
    # Check Experiment 1 outputs
    doc_ids = get_doc_ids(DATA_DIR)
    
    for doc_id in doc_ids:
        # Check hybrid runs for nondeterminism
        hybrid_runs = []
        for run_path in sorted((HYBRID_ARTIFACTS / doc_id).glob("run_*.json")):
            try:
                hybrid_runs.append(load_json(run_path))
            except Exception as e:
                issues.append({
                    "issue_id": f"ERR-{issue_id:04d}",
                    "doc_id": doc_id,
                    "system": "hybrid",
                    "type": "parsing_error",
                    "description": f"Failed to load {run_path.name}: {str(e)}",
                    "mitigation": "Check file integrity and JSON format"
                })
                issue_id += 1
        
        if len(hybrid_runs) >= 2:
            variance = compute_variance_count(hybrid_runs)
            if variance > 0:
                issues.append({
                    "issue_id": f"ERR-{issue_id:04d}",
                    "doc_id": doc_id,
                    "system": "hybrid",
                    "type": "nondeterminism",
                    "description": f"{variance} runs differ from run_01",
                    "mitigation": "Investigate source of non-determinism in rule engine"
                })
                issue_id += 1
        
        # Check baseline runs for parsing errors
        for run_path in sorted((BASELINE_ARTIFACTS / doc_id).glob("run_*.json")):
            try:
                baseline_run = load_json(run_path)
                if "error" in baseline_run:
                    issues.append({
                        "issue_id": f"ERR-{issue_id:04d}",
                        "doc_id": doc_id,
                        "system": "baseline",
                        "type": "parsing_error",
                        "description": f"Baseline error: {baseline_run.get('error', 'Unknown')}",
                        "mitigation": "Check OpenAI API key and response format"
                    })
                    issue_id += 1
            except Exception as e:
                issues.append({
                    "issue_id": f"ERR-{issue_id:04d}",
                    "doc_id": doc_id,
                    "system": "baseline",
                    "type": "parsing_error",
                    "description": f"Failed to load {run_path.name}: {str(e)}",
                    "mitigation": "Check file integrity and JSON format"
                })
                issue_id += 1
        
        # Check synthetic truth for FP/FN (check all contract type directories)
        from experiments.config import DATA_BASE_DIR
        truth_path = None
        for contract_dir in [DATA_BASE_DIR / "ndas", DATA_BASE_DIR / "msas", DATA_BASE_DIR / "employment", DATA_BASE_DIR / "licensing"]:
            potential_path = contract_dir / f"{doc_id}.truth.json"
            if potential_path.exists():
                truth_path = potential_path
                break
        if truth_path and truth_path.exists() and hybrid_runs:
            truth = load_json(truth_path)
            fp, fn = compute_fp_fn_hybrid(hybrid_runs[0], truth)
            
            if fp > 0:
                # Enhanced FP categorization
                fp_rules = []
                truth_absent = set(truth.get("expected_rule_ids_absent", []))
                if hybrid_runs:
                    findings = hybrid_runs[0].get("findings", [])
                    for f in findings:
                        if f.get("rule_id") in truth_absent:
                            fp_rules.append(f.get("rule_id"))
                
                fp_category = "conservative_pattern" if fp_rules else "unknown"
                fp_examples = ", ".join(fp_rules[:3]) if fp_rules else "N/A"
                
                issues.append({
                    "issue_id": f"ERR-{issue_id:04d}",
                    "doc_id": doc_id,
                    "system": "hybrid",
                    "type": "false_positive",
                    "category": fp_category,
                    "description": f"{fp} false positive(s) detected. Rules: {fp_examples}",
                    "example_rules": fp_rules[:5],  # Up to 5 examples
                    "mitigation": "Review suppression rules or add new suppression patterns. Consider context-aware matching."
                })
                issue_id += 1
            
            if fn > 0:
                # Enhanced FN categorization
                truth_present = set(truth.get("expected_rule_ids_present", []))
                if hybrid_runs:
                    findings = hybrid_runs[0].get("findings", [])
                    detected_rules = {f.get("rule_id") for f in findings}
                    missing_rules = truth_present - detected_rules
                else:
                    missing_rules = truth_present
                
                fn_category = "pattern_mismatch" if missing_rules else "unknown"
                fn_examples = ", ".join(list(missing_rules)[:3]) if missing_rules else "N/A"
                
                issues.append({
                    "issue_id": f"ERR-{issue_id:04d}",
                    "doc_id": doc_id,
                    "system": "hybrid",
                    "type": "false_negative",
                    "category": fn_category,
                    "description": f"{fn} false negative(s) - expected rules not detected. Missing: {fn_examples}",
                    "missing_rules": list(missing_rules),
                    "mitigation": "Review rule patterns for linguistic variants. Consider expanding pattern coverage or adding aliases."
                })
                issue_id += 1
    
    # Check Experiment 2 stress test
    for doc_id in doc_ids:
        stress_runs = []
        for run_path in sorted((STRESS_ARTIFACTS / doc_id).glob("run_*.json")):
            try:
                stress_runs.append(load_json(run_path))
            except:
                pass
        
        if len(stress_runs) >= 2:
            variance = compute_variance_count(stress_runs)
            if variance > 0:
                # Check if already reported
                existing = any(i["doc_id"] == doc_id and i["type"] == "nondeterminism" for i in issues)
                if not existing:
                    issues.append({
                        "issue_id": f"ERR-{issue_id:04d}",
                        "doc_id": doc_id,
                        "system": "hybrid",
                        "type": "nondeterminism",
                        "description": f"Stress test: {variance} runs differ from run_01",
                        "mitigation": "Investigate source of non-determinism in rule engine"
                    })
                    issue_id += 1
    
    return issues


if __name__ == "__main__":
    issues = characterize_errors()
    print(f"\nExperiment 4 complete. Found {len(issues)} issues.")
