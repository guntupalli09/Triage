# Experiment Results

**Generated**: 2026-01-15 12:03:41  
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
| Baseline Avg Ungrounded Findings/Doc | 0.44 (Executed) |
| Hybrid Traceability Rate | 100.0% |
| Synthetic FP Total (Hybrid) | 14 |
| Synthetic FN Total (Hybrid) | 5 |

### Per-Document Results

| Doc ID | Hybrid Deterministic | Baseline Deterministic | Baseline Ungrounded | Hybrid Traceability | FP | FN |
|--------|---------------------|----------------------|-------------------|-------------------|-----|-----|
| public_01 | Yes | No | 0.80 | 100.0% | 0 | 0 |
| public_02 | Yes | No | 0.60 | 100.0% | 0 | 0 |
| public_03 | Yes | No | 0.80 | 100.0% | 0 | 0 |
| public_04 | Yes | No | 0.60 | 100.0% | 0 | 0 |
| public_05 | Yes | No | 0.60 | 100.0% | 0 | 0 |
| public_06 | Yes | No | 0.40 | 100.0% | 0 | 0 |
| public_07 | Yes | No | 1.20 | 100.0% | 0 | 0 |
| public_08 | Yes | No | 1.00 | 100.0% | 0 | 0 |
| public_09 | Yes | No | 0.80 | 100.0% | 0 | 0 |
| public_10 | Yes | No | 0.80 | 100.0% | 0 | 0 |
| public_11 | Yes | No | 1.00 | 100.0% | 0 | 0 |
| public_12 | Yes | No | 0.80 | 100.0% | 0 | 0 |
| public_13 | Yes | No | 0.80 | 100.0% | 0 | 0 |
| public_14 | Yes | No | 0.60 | 100.0% | 0 | 0 |
| public_15 | Yes | No | 0.80 | 100.0% | 0 | 0 |
| synthetic_01 | Yes | No | 0.40 | 100.0% | 1 | 0 |
| synthetic_02 | Yes | No | 0.00 | 100.0% | 1 | 0 |
| synthetic_03 | Yes | No | 0.00 | 100.0% | 1 | 0 |
| synthetic_04 | Yes | No | 0.00 | 100.0% | 1 | 1 |
| synthetic_05 | Yes | No | 0.60 | 100.0% | 1 | 1 |
| synthetic_06 | Yes | No | 0.00 | 100.0% | 1 | 1 |
| synthetic_07 | Yes | No | 0.00 | 100.0% | 1 | 1 |
| synthetic_08 | Yes | No | 0.00 | 100.0% | 1 | 1 |
| synthetic_09 | Yes | No | 0.60 | 100.0% | 1 | 0 |
| synthetic_10 | Yes | No | 0.00 | 100.0% | 1 | 0 |
| synthetic_11 | Yes | No | 0.00 | 100.0% | 1 | 0 |
| synthetic_12 | Yes | No | 0.00 | 100.0% | 1 | 0 |
| synthetic_13 | Yes | No | 0.00 | 100.0% | 1 | 0 |
| synthetic_14 | Yes | No | 0.00 | 100.0% | 1 | 0 |
| synthetic_15 | Yes | No | 0.00 | 100.0% | 0 | 0 |

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

**NOTE**: Suppression cannot be toggled without modifying core engine. Results show suppression ON only.

| Doc ID | FP (ON) | FN (ON) | FP (OFF) | FN (OFF) | Note |
|--------|---------|---------|----------|----------|------|
| synthetic_01 | 1 | 0 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_02 | 1 | 0 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_03 | 1 | 0 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_04 | 1 | 1 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_05 | 1 | 1 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_06 | 1 | 1 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_07 | 1 | 1 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_08 | 1 | 1 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_09 | 1 | 0 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_10 | 1 | 0 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_11 | 1 | 0 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_12 | 1 | 0 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_13 | 1 | 0 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_14 | 1 | 0 | N/A | N/A | Suppression OFF not available without core engine modification |
| synthetic_15 | 0 | 0 | N/A | N/A | Suppression OFF not available without core engine modification |

## Experiment 4: Error Characterization

### Issues by Type

| Type | Count |
|------|-------|
| false_negative | 5 |
| false_positive | 14 |

### All Issues

| Issue ID | Doc ID | System | Type | Description | Mitigation |
|----------|--------|--------|------|-------------|------------|
| ERR-0001 | synthetic_01 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0002 | synthetic_02 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0003 | synthetic_03 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0004 | synthetic_04 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0005 | synthetic_04 | hybrid | false_negative | 1 false negative(s) - expected rules not detected | Review rule patterns or add new rules |
| ERR-0006 | synthetic_05 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0007 | synthetic_05 | hybrid | false_negative | 1 false negative(s) - expected rules not detected | Review rule patterns or add new rules |
| ERR-0008 | synthetic_06 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0009 | synthetic_06 | hybrid | false_negative | 1 false negative(s) - expected rules not detected | Review rule patterns or add new rules |
| ERR-0010 | synthetic_07 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0011 | synthetic_07 | hybrid | false_negative | 1 false negative(s) - expected rules not detected | Review rule patterns or add new rules |
| ERR-0012 | synthetic_08 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0013 | synthetic_08 | hybrid | false_negative | 1 false negative(s) - expected rules not detected | Review rule patterns or add new rules |
| ERR-0014 | synthetic_09 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0015 | synthetic_10 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0016 | synthetic_11 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0017 | synthetic_12 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0018 | synthetic_13 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |
| ERR-0019 | synthetic_14 | hybrid | false_positive | 1 false positive(s) detected | Review suppression rules or add new suppression patterns |

## Notes

- **Baseline Execution**: Executed with OpenAI API
- **Suppression Toggle**: Not available without core engine modification (documented limitation)
- **All raw outputs**: Available in `experiments/artifacts/`
- **All CSVs**: Available in `experiments/results/`
