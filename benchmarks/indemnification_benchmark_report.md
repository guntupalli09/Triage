# Indemnification Policy Engine — Benchmark Report

Corpus size: **43** cases across 18 drafting-pattern tags. Second clause adapter — see benchmarks/policy_engine_core_architecture_report.md for what this run revealed about the shared core's reusability.

## Headline safety metric

**False-safe rate: 0 / 43 (0.0%)**

Zero false-safe cases in this run.

## False-escalation

**False-escalation rate: 0 / 43 (0.0%)**

Zero false-escalation cases in this run.

## Metrics

| Metric | Result |
|---|---|
| Policy-state accuracy | 100.0% (43 cases) |
| Direction/party identification accuracy | 100.0% (4 scored) |
| Trigger/coverage-category accuracy | 100.0% (7 scored) |
| Monetary-treatment extraction accuracy | 100.0% (34 scored) |
| Protection-obligation presence accuracy | 100.0% (4 scored) |
| Ambiguity detection recall (REQUIRES_REVIEW) | 100.0% (7 expected) |
| False-safe rate | 0.0% |
| False-escalation rate | 0.0% |
| Determinism (5x repeat) | 100.0% |

## Release gate check

- PASS — False-safe = 0 (actual: 0)
- PASS — False-escalation = 0 (actual: 0)
- PASS — Determinism = 100% (actual: 100.0%)

Policy-state accuracy reported honestly above (100.0%) — no fixed target was set for a first pass on a second, less-tuned adapter; the false-safe and false-escalation gates are the ones that must hold.

## Failures by drafting pattern

None.
