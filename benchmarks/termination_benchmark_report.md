# Termination Policy Engine — Benchmark Report

Corpus size: **40** cases across 19 drafting-pattern tags. Third clause adapter — see benchmarks/policy_engine_core_architecture_report.md for what this run revealed about the shared core's reusability.

## Headline safety metric

**False-safe rate: 0 / 40 (0.0%)**

Zero false-safe cases in this run.

## False-escalation

**False-escalation rate: 0 / 40 (0.0%)**

Zero false-escalation cases in this run.

## Metrics

| Metric | Result | Scored on |
|---|---|---|
| Provision detection | 100.0% | 40 (all cases) |
| Trigger-type coverage accuracy | 100.0% | 4 |
| Termination-fee extraction accuracy | 100.0% | 6 |
| Survival-topic accuracy | 100.0% | 2 |
| Policy-state accuracy | 100.0% | 40 (all cases) |
| False-safe rate | 0.0% | 40 (all cases) |
| False-escalation rate | 0.0% | 40 (all cases) |
| Determinism (5x repeat) | 100.0% | 40 (all cases) |

Supplementary: ambiguity detection recall (REQUIRES_REVIEW) — 100.0% (7 expected).

## Release gate check

- PASS — False-safe = 0 (actual: 0)
- PASS — False-escalation = 0 (actual: 0)
- PASS — Determinism = 100% (actual: 100.0%)

Policy-state accuracy and the other extraction-quality metrics are reported honestly above — no fixed target is asserted for them on this first pass.

## Failures by drafting pattern

None.
