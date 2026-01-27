# Running ICCS Experiments

## Overview

Two new ICCS-specific experiments need to be run:

1. **Experiment 2**: Enhanced Reproducibility Stress Test
   - 15 documents selected from 115 total
   - 20 runs per document (300 total hybrid runs + 300 baseline runs)
   - Tests across multiple seeds and environments

2. **Experiment 3**: Computational Cost of Determinism
   - All 115 documents
   - 3 runs per document (345 total hybrid runs + 345 baseline runs)
   - Measures runtime, complexity, and output variance

## Estimated Time

- Experiment 2: ~1-2 hours (depending on baseline LLM API rate limits)
- Experiment 3: ~1-2 hours (depending on baseline LLM API rate limits)
- **Total: 2-4 hours**

## Running the Experiments

### Option 1: Full Run (Recommended)

```bash
cd c:\Users\gvksg\Desktop\Triage
python experiments/run_iccs_full.py
```

This will:
- Run Experiment 2 (15 docs × 20 runs)
- Run Experiment 3 (115 docs × 3 runs)
- Save results to `experiments/results/`
- Print summary statistics

### Option 2: Quick Test (5 runs per doc)

```bash
cd c:\Users\gvksg\Desktop\Triage
python experiments/run_iccs_experiments_quick.py
```

This runs a quick test with fewer runs to verify everything works.

## After Running

Once experiments complete, run:

```bash
python experiments/UPDATE_ICCS_PAPER_WITH_RESULTS.py
```

This will:
- Read the results CSV files
- Compute summary statistics
- Print values to update in the paper

## Updating the Paper

After getting results, update `IEEE paper/ICCS_PAPER_LATEX.MD`:

1. **Table 2 (Reproducibility Stress Test)**: Update with actual reproducibility rates and distinct output sets
2. **Table 3 (Computational Cost)**: Update with actual runtime measurements
3. **Experiment 2 text**: Update with actual percentages (e.g., "87% of documents show variance")
4. **Experiment 3 text**: Update with actual runtime values

## Files Created

- `experiments/results/exp2_iccs_reproducibility.csv`
- `experiments/results/exp3_iccs_computational_cost.csv`
- `experiments/results/exp3_iccs_computational_cost_summary.json`
