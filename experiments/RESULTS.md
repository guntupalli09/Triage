# Experiment Results

**Generated**: 2026-01-18 00:03:03  
**Python Version**: 3.13.1  
**Reproduction**: Run `python experiments/run_all.py`

## Entrypoint Discovery

**Hybrid engine runner**: `experiments/run_hybrid.py`  
**Output schema**: 
```json
{
  "findings": [
    {
      "rule_id": "H_INDEM_01",
      "severity": "high",
      "title": "...",
      "exact_snippet": "...",
      "start_index": 123,
      "end_index": 456
    }
  ],
  "overall_risk": "high",
  "version": "1.0.3"
}
```

## Experiment 1: Baseline vs Hybrid

### Summary Statistics

| Metric | Value |
|--------|-------|
| Hybrid Determinism Rate | 100.0% |
| Baseline Determinism Rate | 0.0% (Executed) |
| Baseline Avg Ungrounded Findings/Doc | 0.43 (Executed) |
| Hybrid Traceability Rate | 100.0% |
| Synthetic FP Total (Hybrid) | 14.0 |
| Synthetic FN Total (Hybrid) | 5.0 |

### Per-Document Results

| Doc ID | Hybrid Deterministic | Baseline Deterministic | Baseline Ungrounded | Hybrid Traceability | FP | FN |
|--------|---------------------|----------------------|-------------------|-------------------|-----|-----|
| public_01 | Yes | No | 0.60 | 100.0% | 0.0 | 0.0 |
| public_02 | Yes | No | 1.00 | 100.0% | 0.0 | 0.0 |
| public_03 | Yes | No | 0.80 | 100.0% | 0.0 | 0.0 |
| public_04 | Yes | No | 0.80 | 100.0% | 0.0 | 0.0 |
| public_05 | Yes | No | 0.40 | 100.0% | 0.0 | 0.0 |
| public_06 | Yes | No | 0.60 | 100.0% | 0.0 | 0.0 |
| public_07 | Yes | No | 0.80 | 100.0% | 0.0 | 0.0 |
| public_08 | Yes | No | 0.60 | 100.0% | 0.0 | 0.0 |
| public_09 | Yes | No | 0.40 | 100.0% | 0.0 | 0.0 |
| public_10 | Yes | No | 1.20 | 100.0% | 0.0 | 0.0 |
| public_11 | Yes | No | 1.00 | 100.0% | 0.0 | 0.0 |
| public_12 | Yes | No | 0.80 | 100.0% | 0.0 | 0.0 |
| public_13 | Yes | No | 1.00 | 100.0% | 0.0 | 0.0 |
| public_14 | Yes | No | 0.80 | 100.0% | 0.0 | 0.0 |
| public_15 | Yes | No | 0.80 | 100.0% | 0.0 | 0.0 |
| synthetic_01 | Yes | No | 0.60 | 100.0% | 1.0 | 0.0 |
| synthetic_02 | Yes | No | 0.00 | 100.0% | 1.0 | 0.0 |
| synthetic_03 | Yes | No | 0.00 | 100.0% | 1.0 | 0.0 |
| synthetic_04 | Yes | No | 0.00 | 100.0% | 1.0 | 1.0 |
| synthetic_05 | Yes | No | 0.40 | 100.0% | 1.0 | 1.0 |
| synthetic_06 | Yes | No | 0.00 | 100.0% | 1.0 | 1.0 |
| synthetic_07 | Yes | No | 0.00 | 100.0% | 1.0 | 1.0 |
| synthetic_08 | Yes | No | 0.00 | 100.0% | 1.0 | 1.0 |
| synthetic_09 | Yes | No | 0.40 | 100.0% | 1.0 | 0.0 |
| synthetic_10 | Yes | No | 0.00 | 100.0% | 1.0 | 0.0 |
| synthetic_11 | Yes | No | 0.00 | 100.0% | 1.0 | 0.0 |
| synthetic_12 | Yes | No | 0.00 | 100.0% | 1.0 | 0.0 |
| synthetic_13 | Yes | No | 0.00 | 100.0% | 1.0 | 0.0 |
| synthetic_14 | Yes | No | 0.00 | 100.0% | 1.0 | 0.0 |
| synthetic_15 | Yes | No | 0.00 | 100.0% | 0.0 | 0.0 |

## Experiment 2: Determinism Stress Test

| Doc ID | Variance Count |
|--------|---------------|
| synthetic_01 | 0 |
| synthetic_02 | 0 |
| synthetic_03 | 0 |
| synthetic_04 | 0 |
| synthetic_05 | 0 |
| public_01 | 0 |
| public_02 | 0 |
| public_03 | 0 |
| public_04 | 0 |
| public_05 | 0 |

**Total Variances**: 0 (expected: 0)

## Experiment 3: Suppression Ablation

**Tests the impact of false-positive suppression on precision and recall.**

### Summary Statistics

| Metric | Suppression ON | Suppression OFF | Change |
|--------|----------------|-----------------|--------|
| Total False Positives | 24 | 24 | -0 (0.0% reduction) |
| Total False Negatives | 26 | 26 | 0 |

### Per-Document Results

| Doc ID | FP (ON) | FN (ON) | FP (OFF) | FN (OFF) | FP Reduction |
|--------|---------|---------|----------|----------|--------------|
| synthetic_01 | 1 | 0 | 1 | 0 | 0 |
| synthetic_02 | 1 | 0 | 1 | 0 | 0 |
| synthetic_03 | 1 | 0 | 1 | 0 | 0 |
| synthetic_04 | 1 | 1 | 1 | 1 | 0 |
| synthetic_05 | 1 | 1 | 1 | 1 | 0 |
| synthetic_06 | 1 | 1 | 1 | 1 | 0 |
| synthetic_07 | 1 | 1 | 1 | 1 | 0 |
| synthetic_08 | 1 | 1 | 1 | 1 | 0 |
| synthetic_09 | 1 | 0 | 1 | 0 | 0 |
| synthetic_10 | 1 | 0 | 1 | 0 | 0 |
| synthetic_11 | 1 | 0 | 1 | 0 | 0 |
| synthetic_12 | 1 | 0 | 1 | 0 | 0 |
| synthetic_13 | 1 | 0 | 1 | 0 | 0 |
| synthetic_14 | 1 | 0 | 1 | 0 | 0 |
| synthetic_15 | 0 | 0 | 0 | 0 | 0 |
| synthetic_16 | 0 | 0 | 0 | 0 | 0 |
| synthetic_17 | 0 | 2 | 0 | 2 | 0 |
| synthetic_18 | 0 | 2 | 0 | 2 | 0 |
| synthetic_19 | 2 | 2 | 2 | 2 | 0 |
| synthetic_20 | 1 | 1 | 1 | 1 | 0 |
| synthetic_21 | 1 | 1 | 1 | 1 | 0 |
| synthetic_22 | 1 | 1 | 1 | 1 | 0 |
| synthetic_23 | 0 | 1 | 0 | 1 | 0 |
| synthetic_24 | 0 | 2 | 0 | 2 | 0 |
| synthetic_25 | 2 | 2 | 2 | 2 | 0 |
| synthetic_26 | 1 | 1 | 1 | 1 | 0 |
| synthetic_27 | 0 | 1 | 0 | 1 | 0 |
| synthetic_28 | 0 | 2 | 0 | 2 | 0 |
| synthetic_29 | 2 | 0 | 2 | 0 | 0 |
| synthetic_30 | 0 | 3 | 0 | 3 | 0 |

## Experiment 4: Error Characterization

### Issues by Type

| Type | Count |
|------|-------|
| false_negative | 39 |
| false_positive | 15 |

### All Issues

| Issue ID | Doc ID | System | Type | Category | Description | Mitigation |
|----------|--------|--------|------|----------|-------------|------------|
| ERR-0001 | emp_01 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_INDEM_01, H_ATTFEE... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0002 | emp_03 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01, H_IP_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0003 | emp_05 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_INDEM_01, H_ATTFEE... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0004 | emp_06 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0005 | emp_08 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01, H_IP_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0006 | emp_10 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_INDEM_01, H_ATTFEE... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0007 | emp_12 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01, H_IP_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0008 | emp_14 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_INDEM_01, H_ATTFEE... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0009 | emp_16 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0010 | emp_17 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0011 | emp_18 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_INDEM_01, H_ATTFEE... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0012 | emp_20 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_INDEM_01, H_ATTFEE... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0013 | lic_01 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_INDEM_01, H_LOL_CA... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0014 | lic_03 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0015 | lic_05 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0016 | lic_07 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0017 | lic_08 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0018 | lic_09 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0019 | lic_11 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0020 | lic_13 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0021 | lic_15 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0022 | msa_01 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_INDEM_01, H_ATTFEE... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0023 | msa_03 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0024 | msa_05 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0025 | msa_06 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0026 | msa_08 | hybrid | false_negative | pattern_mismatch | 2 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0027 | msa_10 | hybrid | false_negative | pattern_mismatch | 4 false negative(s) - expected rules not detected. Missing: H_INDEM_01, H_LOL_CA... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0028 | msa_11 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0029 | msa_13 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0030 | msa_14 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0031 | msa_15 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0032 | msa_17 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: H_INDEM_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0033 | msa_17 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0034 | msa_18 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0035 | msa_20 | hybrid | false_negative | pattern_mismatch | 3 false negative(s) - expected rules not detected. Missing: H_LOL_CARVEOUT_01, H... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0036 | synthetic_01 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0037 | synthetic_02 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0038 | synthetic_03 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0039 | synthetic_04 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0040 | synthetic_04 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_ATTFEE_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0041 | synthetic_05 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0042 | synthetic_05 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_INDEM_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0043 | synthetic_06 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0044 | synthetic_06 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: H_IP_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0045 | synthetic_07 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0046 | synthetic_07 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: M_CONF_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0047 | synthetic_08 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0048 | synthetic_08 | hybrid | false_negative | pattern_mismatch | 1 false negative(s) - expected rules not detected. Missing: M_CONF_01... | Review rule patterns for linguistic variants. Consider expan... |
| ERR-0049 | synthetic_09 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0050 | synthetic_10 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0051 | synthetic_11 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0052 | synthetic_12 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0053 | synthetic_13 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |
| ERR-0054 | synthetic_14 | hybrid | false_positive | conservative_pattern | 1 false positive(s) detected. Rules: L_GOVLAW_01... | Review suppression rules or add new suppression patterns. Co... |

## Statistical Significance Analysis

### McNemar's Test (Determinism Comparison)
- Not computed (baseline not executed or insufficient data)

### Confidence Intervals

**Baseline Ungrounded Findings per Document**:
- Mean: 0.43
- 95% CI: [0.28, 0.58]
- Std Dev: 0.40
- N: 30

**Suppression Impact (False Positives)**:
- With Suppression: Mean=0.80, 95% CI=[0.57, 1.03]
- Without Suppression: Mean=0.80, 95% CI=[0.57, 1.03]

- **Paired t-test**: t=nan, p=nan
- **Interpretation**: Paired t-test: Suppression does not significantly reduces FPs (p=nan)

### Effect Size (Cohen's d)
- **Cohen's d**: 0.000
- **Magnitude**: none
- **Interpretation**: No variance - perfect agreement


## Notes

- **Baseline Execution**: Executed with OpenAI API
- **Suppression Toggle**: Now available (core engine updated)
- **Statistical Tests**: All p-values reported with α=0.05 significance level
- **All raw outputs**: Available in `experiments/artifacts/`
- **All CSVs**: Available in `experiments/results/`
- **Statistical analysis**: Available in `experiments/results/statistical_analysis.json`
