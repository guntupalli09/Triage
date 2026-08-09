# Indemnification Policy Engine — Benchmark Report (Phase 1 expansion)

Corpus size: **100** cases across 38 drafting-pattern tags (expanded from 43 to 100 per the Phase 1 adversarial hardening pass). Second clause adapter — see benchmarks/policy_engine_core_architecture_report.md for what this run revealed about the shared core's reusability.

## Headline safety metric

**False-safe rate: 1 / 100 (1.0%)**

- `false-reciprocal-01` (tags: reciprocal, adversarial) — expected `ESCALATE`, got `ACCEPT`

## False-escalation

**False-escalation rate: 0 / 100 (0.0%)**

Zero false-escalation cases in this run.

## 11 metrics, reported separately

| # | Metric | Result | Scored on |
|---|---|---|---|
| 1 | Provision detection | 100.0% | 100 (all cases) |
| 2 | Indemnitor identification | 100.0% | 11 |
| 3 | Indemnitee identification | 100.0% | 11 |
| 4 | Directionality (exposure vs. protection) | 100.0% | 13 |
| 5 | Covered-claim/category extraction | 90.9% | 22 |
| 6 | Reciprocal/unilateral classification | 100.0% | 20 |
| 7 | Monetary/cap treatment | 100.0% | 72 |
| 8 | Policy-state accuracy | 96.0% | 100 (all cases) |
| 9 | False-safe rate | 1.0% | 100 (all cases) |
| 10 | False-escalation rate | 0.0% | 100 (all cases) |
| 11 | Determinism (5x repeat) | 100.0% | 100 (all cases) |

Supplementary (not one of the 11): protection-obligation presence accuracy — 100.0% (7 scored).

Supplementary: ambiguity detection recall (REQUIRES_REVIEW) — 88.9% (18 expected).

## Release gate check

- FAIL — False-safe = 0 (actual: 1)
- PASS — False-escalation = 0 (actual: 0)
- PASS — Determinism = 100% (actual: 100.0%)

Policy-state accuracy and the other extraction-quality metrics are reported honestly above — no fixed target is asserted for them. Per instruction, this pass deliberately optimized for finding real failures with a corpus that was NOT authored or debugged against this implementation's output; a lower number here than the first 43-case pass is expected and is not itself a regression to fix by relabeling.

## Failures by drafting pattern

### `adversarial` — 3 failing case(s)

- `xref-03`: expected `REQUIRES_REVIEW`, got `MUST_REDLINE`
- `cap-excluded-01`: expected `PROHIBITED`, got `MUST_REDLINE`
- `false-reciprocal-01` ⚠️ FALSE-SAFE: expected `ESCALATE`, got `ACCEPT`

### `cross_referenced_cap` — 2 failing case(s)

- `xref-03`: expected `REQUIRES_REVIEW`, got `MUST_REDLINE`
- `xref-04`: expected `REQUIRES_REVIEW`, got `MUST_REDLINE`

### `special_cap` — 2 failing case(s)

- `super-cap-01`: expected `NEGOTIATE`, got `NEGOTIATE`; trigger mismatch: ip_infringement
- `super-cap-02`: expected `ESCALATE`, got `ESCALATE`; trigger mismatch: willful_misconduct

### `cap_interaction` — 1 failing case(s)

- `cap-excluded-01`: expected `PROHIBITED`, got `MUST_REDLINE`

### `reciprocal` — 1 failing case(s)

- `false-reciprocal-01` ⚠️ FALSE-SAFE: expected `ESCALATE`, got `ACCEPT`
