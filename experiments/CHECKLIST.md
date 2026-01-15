# Experiment Harness Checklist

## Files Created

### Core Infrastructure
- [x] `experiments/config.py` - Configuration constants
- [x] `experiments/utils_io.py` - I/O utilities
- [x] `experiments/normalize.py` - Normalization functions
- [x] `experiments/metrics.py` - Metric computation
- [x] `experiments/run_hybrid.py` - Hybrid engine runner
- [x] `experiments/run_baseline_llm.py` - Baseline LLM runner

### Dataset
- [x] `experiments/data/build_public_ndas.py` - Public NDA builder
- [x] `experiments/data/build_synthetic_ndas.py` - Synthetic NDA builder
- [x] `experiments/data/README.md` - Dataset documentation
- [x] `experiments/data/ndas/` - 30 NDA files (15 public, 15 synthetic)

### Experiments
- [x] `experiments/exp1_baseline_vs_hybrid.py` - Experiment 1
- [x] `experiments/exp2_determinism_stress.py` - Experiment 2
- [x] `experiments/exp3_suppression_ablation.py` - Experiment 3
- [x] `experiments/exp4_error_characterization.py` - Experiment 4

### Orchestration
- [x] `experiments/run_all.py` - Main orchestration script
- [x] `experiments/generate_results.py` - Results generator
- [x] `experiments/verify_setup.py` - Setup verification
- [x] `experiments/README.md` - Experiment documentation
- [x] `Makefile` - Make targets

## Directories Created

- [x] `experiments/`
- [x] `experiments/data/ndas/`
- [x] `experiments/artifacts/`
- [x] `experiments/artifacts/hybrid/`
- [x] `experiments/artifacts/baseline/`
- [x] `experiments/artifacts/hybrid_stress/`
- [x] `experiments/results/`

## Commands to Run

```bash
# Verify setup
python experiments/verify_setup.py

# Run all experiments
python experiments/run_all.py

# Or use Makefile
make experiments
```

## Expected Outputs

After running `python experiments/run_all.py`:

1. **CSV Files** (in `experiments/results/`):
   - `exp1_summary.csv`
   - `exp2_determinism.csv`
   - `exp3_suppression.csv`
   - `exp4_errors.csv`

2. **RESULTS.md** (in `experiments/`):
   - Programmatically generated report
   - All tables and metrics

3. **Raw Artifacts** (in `experiments/artifacts/`):
   - `hybrid/<doc_id>/run_01.json` ... `run_05.json`
   - `baseline/<doc_id>/run_01.json` ... `run_05.json`
   - `hybrid_stress/<doc_id>/run_01.json` ... `run_10.json`

## Known Limitations

1. **Suppression Toggle**: Cannot toggle suppression without modifying core engine (documented in Experiment 3)
2. **Baseline LLM**: Requires `OPENAI_API_KEY` environment variable (will skip if missing)
3. **Public NDAs**: Marked as `public_template_recreated: true` (recreated from templates, not downloaded)

## Verification

Run verification:
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
