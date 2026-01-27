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


def generate_results_md(exp1_results, exp2_results, exp3_results, exp4_issues, baseline_executed, hybrid_times=None, baseline_times=None, stats_results=None):
    """Generate RESULTS.md from experiment data."""
    
    # Handle empty results
    exp1_results = exp1_results or []
    exp2_results = exp2_results or []
    exp3_results = exp3_results or []
    exp4_issues = exp4_issues or []
    hybrid_times = hybrid_times or []
    baseline_times = baseline_times or []
    
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

**Tests the impact of false-positive suppression on precision and recall.**

### Summary Statistics
"""
    
    if exp3_results:
        total_fp_on = sum(r.get('fp_on', 0) for r in exp3_results)
        total_fn_on = sum(r.get('fn_on', 0) for r in exp3_results)
        total_fp_off = sum(r.get('fp_off', 0) for r in exp3_results)
        total_fn_off = sum(r.get('fn_off', 0) for r in exp3_results)
        fp_reduction = total_fp_off - total_fp_on
        fp_reduction_pct = (fp_reduction / total_fp_off * 100) if total_fp_off > 0 else 0
        
        md += f"""
| Metric | Suppression ON | Suppression OFF | Change |
|--------|----------------|-----------------|--------|
| Total False Positives | {total_fp_on} | {total_fp_off} | -{fp_reduction} ({fp_reduction_pct:.1f}% reduction) |
| Total False Negatives | {total_fn_on} | {total_fn_off} | {total_fn_off - total_fn_on} |
"""
    
    md += f"""
### Per-Document Results

| Doc ID | FP (ON) | FN (ON) | FP (OFF) | FN (OFF) | FP Reduction |
|--------|---------|---------|----------|----------|--------------|
"""
    
    for r in exp3_results:
        fp_on = r.get('fp_on', 0)
        fn_on = r.get('fn_on', 0)
        fp_off = r.get('fp_off', 0)
        fn_off = r.get('fn_off', 0)
        fp_reduction = r.get('fp_reduction', fp_off - fp_on)
        md += f"| {r.get('doc_id', 'N/A')} | {fp_on} | {fn_on} | {fp_off} | {fn_off} | {fp_reduction} |\n"
    
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

| Issue ID | Doc ID | System | Type | Category | Description | Mitigation |
|----------|--------|--------|------|----------|-------------|------------|
"""
    
    for issue in exp4_issues:
        category = issue.get('category', 'N/A')
        md += f"| {issue.get('issue_id', 'N/A')} | {issue.get('doc_id', 'N/A')} | {issue.get('system', 'N/A')} | {issue.get('type', 'N/A')} | {category} | {issue.get('description', 'N/A')[:80]}... | {issue.get('mitigation', 'N/A')[:60]}... |\n"
    
    # Performance Timing (if measured)
    if hybrid_times or baseline_times:
        md += f"""
## Performance Timing

**Measured**: Execution time per document across all runs

| System Component | Avg Time / Doc (s) | Min (s) | Max (s) | Std Dev (s) | N |
|-----------------|-------------------|---------|---------|-------------|---|
"""
        if hybrid_times:
            import statistics
            avg_hybrid = statistics.mean(hybrid_times)
            min_hybrid = min(hybrid_times)
            max_hybrid = max(hybrid_times)
            std_hybrid = statistics.stdev(hybrid_times) if len(hybrid_times) > 1 else 0.0
            md += f"| Deterministic Rule Engine | {avg_hybrid:.2f} | {min_hybrid:.2f} | {max_hybrid:.2f} | {std_hybrid:.2f} | {len(hybrid_times)} |\n"
        
        if baseline_times:
            import statistics
            avg_baseline = statistics.mean(baseline_times)
            min_baseline = min(baseline_times)
            max_baseline = max(baseline_times)
            std_baseline = statistics.stdev(baseline_times) if len(baseline_times) > 1 else 0.0
            md += f"| Pure LLM Baseline | {avg_baseline:.2f} | {min_baseline:.2f} | {max_baseline:.2f} | {std_baseline:.2f} | {len(baseline_times)} |\n"
        
        md += "\n"
    
    # Statistical Analysis Section
    if stats_results:
        md += f"""
## Statistical Significance Analysis

### McNemar's Test (Determinism Comparison)
"""
        mcnemar = stats_results.get("mcnemar_determinism")
        if mcnemar and not mcnemar.get("error"):
            md += f"""
- **Statistic**: {mcnemar.get('statistic', 'N/A'):.4f}
- **p-value**: {mcnemar.get('p_value', 'N/A'):.4f}
- **Significant**: {'Yes' if mcnemar.get('significant') else 'No'} (α=0.05)
- **Interpretation**: {mcnemar.get('interpretation', 'N/A')}
"""
        else:
            md += "- Not computed (baseline not executed or insufficient data)\n"
        
        md += f"""
### Confidence Intervals
"""
        ungrounded_ci = stats_results.get("ungrounded_ci")
        if ungrounded_ci and ungrounded_ci.get("mean") is not None:
            md += f"""
**Baseline Ungrounded Findings per Document**:
- Mean: {ungrounded_ci.get('mean', 0):.2f}
- 95% CI: [{ungrounded_ci.get('lower_bound', 0):.2f}, {ungrounded_ci.get('upper_bound', 0):.2f}]
- Std Dev: {ungrounded_ci.get('std_dev', 0):.2f}
- N: {ungrounded_ci.get('n', 0)}
"""
        
        suppression_ci = stats_results.get("suppression_fp_ci")
        if suppression_ci:
            md += f"""
**Suppression Impact (False Positives)**:
- With Suppression: Mean={suppression_ci['on'].get('mean', 0):.2f}, 95% CI=[{suppression_ci['on'].get('lower_bound', 0):.2f}, {suppression_ci['on'].get('upper_bound', 0):.2f}]
- Without Suppression: Mean={suppression_ci['off'].get('mean', 0):.2f}, 95% CI=[{suppression_ci['off'].get('lower_bound', 0):.2f}, {suppression_ci['off'].get('upper_bound', 0):.2f}]
"""
            suppression_test = stats_results.get("suppression_t_test")
            if suppression_test:
                md += f"""
- **Paired t-test**: t={suppression_test.get('statistic', 0):.4f}, p={suppression_test.get('p_value', 0):.4f}
- **Interpretation**: {suppression_test.get('interpretation', 'N/A')}
"""
        
        cohens_d = stats_results.get("cohens_d_determinism")
        if cohens_d and cohens_d.get("cohens_d") is not None:
            md += f"""
### Effect Size (Cohen's d)
- **Cohen's d**: {cohens_d.get('cohens_d', 0):.3f}
- **Magnitude**: {cohens_d.get('magnitude', 'N/A')}
- **Interpretation**: {cohens_d.get('interpretation', 'N/A')}
"""
        
        chi_square = stats_results.get("chi_square_fp_fn")
        if chi_square and not chi_square.get("error"):
            md += f"""
### Chi-Square Test (FP/FN by Contract Type)
- **Statistic**: {chi_square.get('statistic', 0):.4f}
- **p-value**: {chi_square.get('p_value', 0):.4f}
- **Significant**: {'Yes' if chi_square.get('significant') else 'No'} (α=0.05)
- **Interpretation**: {chi_square.get('interpretation', 'N/A')}
"""
        
        md += "\n"
    
    md += f"""
## Notes

- **Baseline Execution**: {'Executed with OpenAI API' if baseline_executed else 'NOT EXECUTED - OpenAI API key not set in environment or baseline runs failed'}
- **Suppression Toggle**: Now available (core engine updated)
- **Statistical Tests**: All p-values reported with α=0.05 significance level
- **All raw outputs**: Available in `experiments/artifacts/`
- **All CSVs**: Available in `experiments/results/`
- **Statistical analysis**: Available in `experiments/results/statistical_analysis.json`
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
