# Experiment Harness

Reproducible experiment framework for IEEE paper evaluation.

## Quick Start

Run all experiments:
```bash
python experiments/run_all.py
```

Or use Makefile:
```bash
make experiments
```

## Structure

```
experiments/
├── data/
│   ├── ndas/              # 30 NDA documents (15 public, 15 synthetic)
│   ├── build_public_ndas.py
│   └── build_synthetic_ndas.py
├── artifacts/             # Raw experiment outputs
│   ├── hybrid/           # Hybrid engine runs
│   ├── baseline/         # Baseline LLM runs
│   └── hybrid_stress/   # Stress test runs
├── results/              # Generated CSVs and tables
├── run_all.py            # Main orchestration script
├── run_hybrid.py         # Hybrid engine runner
├── run_baseline_llm.py   # Baseline LLM runner
├── exp1_baseline_vs_hybrid.py
├── exp2_determinism_stress.py
├── exp3_suppression_ablation.py
├── exp4_error_characterization.py
└── RESULTS.md            # Generated results report
```

## Experiments

### Experiment 1: Baseline vs Hybrid
- Compares determinism, hallucinations, traceability
- 30 documents, 5 runs each
- Output: `results/exp1_summary.csv`

### Experiment 2: Determinism Stress Test
- 10 documents, 10 runs each
- Output: `results/exp2_determinism.csv`

### Experiment 3: Suppression Ablation
- Tests false-positive suppression impact
- 15 synthetic documents
- Output: `results/exp3_suppression.csv`
- **Note**: Suppression toggle not available without core engine modification

### Experiment 4: Error Characterization
- Categorizes all observed failures
- Output: `results/exp4_errors.csv`

## Requirements

- Python 3.8+
- `openai` package (optional, for baseline LLM)
- All dependencies from `requirements.txt`

## Baseline LLM

If `OPENAI_API_KEY` is not set, baseline experiments will be skipped and marked as "NOT EXECUTED" in results.

## Outputs

- **RESULTS.md**: Programmatically generated results report
- **CSV files**: All metrics in `results/`
- **Raw artifacts**: All run outputs in `artifacts/`
