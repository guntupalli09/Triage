# Experiment Harness - Implementation Summary

## Commands to Run

### Single Command (All Experiments)
```bash
python experiments/run_all.py
```

### Alternative (Makefile)
```bash
make experiments
```

### Verify Setup First
```bash
python experiments/verify_setup.py
```

## Produced Files Checklist

After running `python experiments/run_all.py`, verify these files exist:

### Required Outputs
- [ ] `experiments/RESULTS.md` - Generated results report
- [ ] `experiments/results/exp1_summary.csv` - Experiment 1 metrics
- [ ] `experiments/results/exp2_determinism.csv` - Experiment 2 metrics
- [ ] `experiments/results/exp3_suppression.csv` - Experiment 3 metrics
- [ ] `experiments/results/exp4_errors.csv` - Experiment 4 error log

### Raw Artifacts (for auditing)
- [ ] `experiments/artifacts/hybrid/<doc_id>/run_01.json` ... `run_05.json` (30 docs × 5 runs = 150 files)
- [ ] `experiments/artifacts/baseline/<doc_id>/run_01.json` ... `run_05.json` (if API key set)
- [ ] `experiments/artifacts/hybrid_stress/<doc_id>/run_01.json` ... `run_10.json` (10 docs × 10 runs = 100 files)

### Dataset
- [ ] `experiments/data/ndas/public_01.txt` ... `public_15.txt` (15 files)
- [ ] `experiments/data/ndas/public_01.meta.json` ... `public_15.meta.json` (15 files)
- [ ] `experiments/data/ndas/synthetic_01.txt` ... `synthetic_15.txt` (15 files)
- [ ] `experiments/data/ndas/synthetic_01.meta.json` ... `synthetic_15.meta.json` (15 files)
- [ ] `experiments/data/ndas/synthetic_01.truth.json` ... `synthetic_15.truth.json` (15 files)

**Total**: 30 NDA documents with metadata

## File Structure

```
experiments/
├── __init__.py
├── config.py                    # Configuration constants
├── utils_io.py                  # I/O utilities
├── normalize.py                 # Normalization functions
├── metrics.py                   # Metric computation
├── run_hybrid.py                # Hybrid engine runner
├── run_baseline_llm.py          # Baseline LLM runner
├── exp1_baseline_vs_hybrid.py   # Experiment 1
├── exp2_determinism_stress.py   # Experiment 2
├── exp3_suppression_ablation.py # Experiment 3
├── exp4_error_characterization.py # Experiment 4
├── generate_results.py          # Results generator
├── run_all.py                   # Main orchestration
├── verify_setup.py              # Setup verification
├── README.md                    # Experiment documentation
├── CHECKLIST.md                 # This file
├── RESULTS.md                   # Generated (after run)
├── data/
│   ├── build_public_ndas.py
│   ├── build_synthetic_ndas.py
│   ├── README.md
│   └── ndas/                    # 30 NDA files
├── artifacts/
│   ├── hybrid/                  # Hybrid runs
│   ├── baseline/                # Baseline runs
│   └── hybrid_stress/          # Stress test runs
└── results/                     # Generated CSVs
```

## Entrypoint Discovery

**Hybrid engine runner**: `experiments/run_hybrid.py`  
**Function**: `run_hybrid_engine(text: str, suppression_enabled: bool = True) -> dict`

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
  "version": "1.0.3",
  "suppression_log": {}
}
```

## Known Limitations

1. **Suppression Toggle**: Cannot toggle suppression without modifying `RuleEngine.analyze()`. Experiment 3 documents this limitation.
2. **Baseline LLM**: Requires `OPENAI_API_KEY` environment variable. Will skip gracefully if missing.
3. **Public NDAs**: Marked as `public_template_recreated: true` (recreated from templates, not downloaded from web).

## Verification

Run before experiments:
```bash
python experiments/verify_setup.py
```

Expected output:
```
[OK] Imports successful
[OK] Engine test: 1 findings
[OK] Dataset: 30 documents found
Setup verification complete!
```

## Notes

- All experiments save raw outputs for full auditability
- Failures are reported, not hidden
- CSVs are generated programmatically from raw data
- RESULTS.md is generated programmatically (no hand-written numbers)
