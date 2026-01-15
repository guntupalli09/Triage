"""
Generate RESULTS.md from experiment CSVs.
"""
import csv
import sys
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.config import RESULTS_DIR, EXPERIMENTS_DIR


def generate_results_md(exp1_results, exp2_results, exp3_results, exp4_issues, baseline_executed):
    """Generate RESULTS.md from experiment data."""
    
    # Handle empty results
    exp1_results = exp1_results or []
    exp2_results = exp2_results or []
    exp3_results = exp3_results or []
    exp4_issues = exp4_issues or []
    
    md = f"""# Experiment Results

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Python Version**: {sys.version.split()[0]}  
**Reproduction**: Run `python experiments/run_all.py`

## Entrypoint Discovery

**Hybrid engine runner**: `experiments/run_hybrid.py`  
**Output schema**: 
```json
{{
  "findings": [
    {{
      "rule_id": "H_INDEM_01",
      "severity": "high",
      "title": "...",
      "exact_snippet": "...",
      "start_index": 123,
      "end_index": 456
    }}
  ],
  "overall_risk": "high",
  "version": "1.0.3"
}}
```

## Experiment 1: Baseline vs Hybrid

### Summary Statistics

"""
    
    if exp1_results:
        hybrid_det_rate = sum(1 for r in exp1_results if r.get('hybrid_deterministic', False)) / len(exp1_results) * 100
        baseline_det_results = [r for r in exp1_results if r.get('baseline_deterministic') is not None]
        baseline_det_rate = sum(1 for r in baseline_det_results if r.get('baseline_deterministic', False)) / len(baseline_det_results) * 100 if baseline_det_results else 0.0
        baseline_ungrounded_vals = [r.get('baseline_avg_ungrounded') for r in exp1_results if r.get('baseline_avg_ungrounded') is not None]
        avg_ungrounded = sum(baseline_ungrounded_vals) / len(baseline_ungrounded_vals) if baseline_ungrounded_vals else 0.0
        hybrid_traceability = sum(r.get('hybrid_traceability', 0) for r in exp1_results) / len(exp1_results) * 100 if exp1_results else 0.0
        synthetic_fp = sum(r.get('fp_count', 0) for r in exp1_results if r.get('is_synthetic', False))
        synthetic_fn = sum(r.get('fn_count', 0) for r in exp1_results if r.get('is_synthetic', False))
        
        md += f"""| Metric | Value |
|--------|-------|
| Hybrid Determinism Rate | {hybrid_det_rate:.1f}% |
| Baseline Determinism Rate | {baseline_det_rate:.1f}% ({'Executed' if baseline_executed else 'NOT EXECUTED - OpenAI API key missing'}) |
| Baseline Avg Ungrounded Findings/Doc | {avg_ungrounded:.2f} ({'Executed' if baseline_executed else 'N/A'}) |
| Hybrid Traceability Rate | {hybrid_traceability:.1f}% |
| Synthetic FP Total (Hybrid) | {synthetic_fp} |
| Synthetic FN Total (Hybrid) | {synthetic_fn} |
"""
    else:
        md += "**No results available**\n"
    
    md += """
### Per-Document Results

| Doc ID | Hybrid Deterministic | Baseline Deterministic | Baseline Ungrounded | Hybrid Traceability | FP | FN |
|--------|---------------------|----------------------|-------------------|-------------------|-----|-----|
"""
    
    for r in exp1_results:
        baseline_det = "N/A" if r.get('baseline_deterministic') is None else ("Yes" if r.get('baseline_deterministic') else "No")
        baseline_ung = "N/A" if r.get('baseline_avg_ungrounded') is None else f"{r.get('baseline_avg_ungrounded', 0):.2f}"
        md += f"| {r.get('doc_id', 'N/A')} | {'Yes' if r.get('hybrid_deterministic') else 'No'} | {baseline_det} | {baseline_ung} | {r.get('hybrid_traceability', 0)*100:.1f}% | {r.get('fp_count', 0)} | {r.get('fn_count', 0)} |\n"
    
    md += f"""
## Experiment 2: Determinism Stress Test

| Doc ID | Variance Count |
|--------|---------------|
"""
    
    for r in exp2_results:
        md += f"| {r.get('doc_id', 'N/A')} | {r.get('variance_count', 0)} |\n"
    
    total_variances = sum(r.get('variance_count', 0) for r in exp2_results)
    md += f"\n**Total Variances**: {total_variances} (expected: 0)\n"
    
    md += f"""
## Experiment 3: Suppression Ablation

**NOTE**: Suppression cannot be toggled without modifying core engine. Results show suppression ON only.

| Doc ID | FP (ON) | FN (ON) | FP (OFF) | FN (OFF) | Note |
|--------|---------|---------|----------|----------|------|
"""
    
    for r in exp3_results:
        fp_off = "N/A" if r.get('fp_off') is None else str(r.get('fp_off', 0))
        fn_off = "N/A" if r.get('fn_off') is None else str(r.get('fn_off', 0))
        md += f"| {r.get('doc_id', 'N/A')} | {r.get('fp_on', 0)} | {r.get('fn_on', 0)} | {fp_off} | {fn_off} | {r.get('note', '')} |\n"
    
    md += f"""
## Experiment 4: Error Characterization

### Issues by Type

| Type | Count |
|------|-------|
"""
    
    type_counts = {}
    for issue in exp4_issues:
        issue_type = issue.get('type', 'unknown')
        type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
    
    for issue_type, count in sorted(type_counts.items()):
        md += f"| {issue_type} | {count} |\n"
    
    md += f"""
### All Issues

| Issue ID | Doc ID | System | Type | Description | Mitigation |
|----------|--------|--------|------|-------------|------------|
"""
    
    for issue in exp4_issues:
        md += f"| {issue.get('issue_id', 'N/A')} | {issue.get('doc_id', 'N/A')} | {issue.get('system', 'N/A')} | {issue.get('type', 'N/A')} | {issue.get('description', 'N/A')} | {issue.get('mitigation', 'N/A')} |\n"
    
    md += f"""
## Notes

- **Baseline Execution**: {'Executed with OpenAI API' if baseline_executed else 'NOT EXECUTED - OpenAI API key not set in environment or baseline runs failed'}
- **Suppression Toggle**: Not available without core engine modification (documented limitation)
- **All raw outputs**: Available in `experiments/artifacts/`
- **All CSVs**: Available in `experiments/results/`
"""
    
    return md


def save_csv(data, filename, fieldnames):
    """Save data to CSV file."""
    path = RESULTS_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


if __name__ == "__main__":
    # This is called from run_all.py with data
    pass
