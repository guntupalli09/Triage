# Confidentiality Policy Engine — Benchmark Report

Corpus size: **24** cases across 15 drafting-pattern tags. Batch A adapter — see benchmarks/policy_engine_core_architecture_report.md.

## Headline safety metric

**False-safe rate: 0 / 24 (0.0%)**

Zero false-safe cases in this run.

## False-escalation

**False-escalation rate: 0 / 24 (0.0%)**

Zero false-escalation cases in this run.

## Metrics

| Metric | Result | Scored on |
|---|---|---|
| Provision detection | 100.0% | 24 (all cases) |
| Exclusion-topic extraction accuracy | 100.0% | 2 |
| Policy-state accuracy | 100.0% | 24 (all cases) |
| False-safe rate | 0.0% | 24 (all cases) |
| False-escalation rate | 0.0% | 24 (all cases) |
| Determinism (5x repeat) | 100.0% | 24 (all cases) |

## Release gate check

- PASS — False-safe = 0 (actual: 0)
- PASS — False-escalation = 0 (actual: 0)
- PASS — Determinism = 100% (actual: 100.0%)

## Failures by drafting pattern

None.
