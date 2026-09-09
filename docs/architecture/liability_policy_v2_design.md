# Liability Policy v2 — Typed Policy Grammar (RFC)

Status: **Approved in principle** (2026-09-08)

This document defines the generic, typed, deterministic rule vocabulary for
Limitation of Liability (LoL) and the pattern other clause adapters will
follow. It separates **policy grammar** (concepts TriageCounsel understands)
from **policy values** (firm-specific numbers and roles).

---

## 1. Goals

- Represent real-world law-firm playbooks without hard-coding one document
- Preserve v1 `config_json` semantics for all ACTIVE positions unchanged
- Store firm values in typed structures, not evaluator business logic
- Evaluate approved policy deterministically — no LLM in the decision path
- Retain per-field provenance for AI-assisted and manual authoring

---

## 2. Storage & backwards compatibility

| Mechanism | v1 (unchanged) | v2 (additive) |
|-----------|----------------|---------------|
| Enforcement fields | `PolicyPosition.config_json` (7 LoL floats/bools/lists) | `PolicyPosition.rules_v2_json` |
| Schema marker | implicit v1 | `PolicyPosition.policy_schema_version` (`1` default, `2` for v2) |
| Evaluator | `evaluate_liability_policy()` | `evaluate_liability_policy_v2()` when `policy_schema_version == 2` |
| Migration | None for ACTIVE rows | Opt-in; ambiguous v1 → v2 requires human re-approval |
| Revision hash | `config_hash_for_position()` includes v1 only today | Extended to include `rules_v2_json` when present |

**Invariant:** v1 ACTIVE positions continue to evaluate exactly as today until
a lawyer explicitly creates, migrates, and re-activates a v2 position.

---

## 3. Evaluation strategy (refinement 1)

Evaluation is **not** “always resolve to MoneyAmount first.”

```
A. Try semantic/symbolic comparison on a shared axis.
B. If operands are comparable on that axis, decide deterministically.
C. Only resolve to money when heterogeneous expressions require it.
D. If required context is unavailable → REQUIRES_REVIEW / UNRESOLVED — never guess.
```

### Examples

| Policy | Contract | Resolution needed? | Result |
|--------|----------|-------------------|--------|
| 12 months fees | 12 months fees | No | Equal (symbolic) |
| 6-month minimum | 3 months fees | No | Contract below minimum |
| GREATER_OF(12mo, $1M) | 12 months fees | Yes (mixed) | Needs `EvaluationContext` |
| 2× GENERAL_CAP | 1× annual fees | Yes (reference) | Resolve general cap first |

### Trailing-period fees ≠ annual contract value

`fees paid during the preceding 12 months` is **not** silently equated to
`annual_contract_value`. When monetary resolution is required:

- Use explicit `EvaluationContext` fields (`trailing_period_fees`, `annual_fees`, etc.)
- If the needed basis is unavailable, return `UNRESOLVED` with a reason

Symbolic comparison preserves `months: 12` without premature normalization to
`annual_fee_multiple: 1.0` at storage time.

---

## 4. Fee-relative caps (refinement 2)

```yaml
FeeRelativeCap:
  type: fee_period
  months: number          # positive
  basis: enum             # constrained, not open NLP
  scope: enum             # constrained
```

### `basis` (controlled enum)

| Value | Meaning |
|-------|---------|
| `FEES_PAID` | Fees already paid |
| `FEES_PAYABLE` | Fees payable (not yet paid) |
| `FEES_PAID_OR_PAYABLE` | Paid or payable (common drafting) |
| `CONTRACT_FEES` | Generic fees under the agreement |
| `UNRESOLVED` | Could not establish — requires lawyer interpretation |

### `scope` (controlled enum)

| Value | Meaning |
|-------|---------|
| `AGREEMENT` | Whole agreement |
| `ORDER_FORM` | Applicable order form |
| `CLAIM_RELATED_SERVICES` | Services related to the claim |
| `UNRESOLVED` | Could not establish |

If basis/scope cannot be established from source evidence, preserve the
excerpt and mark `REQUIRES_LAWYER_INTERPRETATION` — do not invent values.

---

## 5. Cap operands

```yaml
CapOperand:
  - FeeRelativeCap          # see §4
  - AnnualFeeMultipleCap    # { type: annual_fee_multiple, multiple: float }
  - FixedAmountCap          # { type: fixed_amount, money: MoneyAmount }
  - ReferenceCap            # { type: reference, ref: enum, multiplier: float }
  - UnlimitedCap            # { type: unlimited }
```

### ReferenceCap (refinement 3)

**Do not** represent `2× GENERAL_CAP` as `AnnualFeeMultipleCap`.

```json
{
  "type": "reference",
  "ref": "GENERAL_CAP",
  "multiplier": 2.0
}
```

Supports future constructs such as `GREATER_OF(2× GENERAL_CAP, $5M)` without
conflating reference multipliers with annual-fee multipliers.

Super-cap references **never** populate or mutate the primary general-cap band.

---

## 6. Cap expressions

```yaml
CapExpression:
  operator: SIMPLE | GREATER_OF | LESSER_OF
  operands: CapOperand[]    # 1 for SIMPLE, 2+ for compounds
```

Contract-side extraction already uses analogous structures in
`liability_policy_engine.CapExpression`. Policy-side types live in
`policy_grammar` and share comparison/resolution utilities where safe.

---

## 7. Policy bands

Bands are **not interchangeable**:

| `kind` | Purpose |
|--------|---------|
| `PREFERRED` | Target negotiation position |
| `ACCEPTABLE_FALLBACK` | OK without escalation when conditions match |
| `MAXIMUM_NEGOTIABLE` | Ceiling before escalation |
| `MINIMUM_ACCEPTABLE` | Floor — breach → hard stop |

```yaml
PolicyBand:
  kind: enum
  expression: CapExpression
  conditions: PolicyCondition[]   # empty = unconditional
  outcome_if_breached: HARD_STOP | ESCALATE | NEGOTIATE | null
```

---

## 8. Typed conditions (refinement 4)

Conditions use **field-specific value types**. Validation rejects invalid
combinations statically (e.g. `governing_law < $250000`).

| `field` | Allowed `value` type |
|---------|---------------------|
| `annual_contract_value` | `MoneyAmount` |
| `contract_value` | `MoneyAmount` |
| `liability_cap` | `CapExpression` |
| `fee_period_months` | `integer` |
| `counterparty_role` | `NormalizedRole` |
| `governing_law` | `string` (normalized jurisdiction) |
| `contract_type` | `string` / enum |

```yaml
PolicyCondition:
  field: enum
  operator: EQ | NE | LT | LTE | GT | GTE | IN | NOT_IN
  value: <field-specific type>

ConditionGroup:
  operator: AND | OR
  conditions: (PolicyCondition | ConditionGroup)[]
```

No arbitrary executable expressions. Parsed, typed, validated, evaluated by
controlled deterministic code only.

---

## 9. Carve-outs, super-caps, escalation

### CarveOutSpec

```yaml
category: enum (+ optional custom label)
applicable_party: NormalizedRole | null
treatment: OUTSIDE_GENERAL_CAP | SUPER_CAP | SEPARATE_FIXED_CAP
expression: CapExpression | null   # for SUPER_CAP / SEPARATE_FIXED
```

### SuperCapSpec

```yaml
applies_to: category[]
expression: CapExpression   # typically ReferenceCap → GENERAL_CAP
```

### EscalationRule

```yaml
when: ConditionGroup
approver: enum (supervising_partner, general_counsel, …, custom)
custom_approver_label: string | null
severity: ADVISORY | REQUIRED
```

---

## 10. Provenance

Structured rules link to `PolicyPositionField` rows via logical paths
(`bands[0].expression`, `super_caps[0]`, etc.). Each node retains:

- `source_document_id`, `source_excerpt`, `source_section`
- `extraction_method`: DETERMINISTIC | AI_ASSISTED | MANUAL
- `establishment`: ESTABLISHED | REQUIRES_LAWYER_INTERPRETATION | NOT_ESTABLISHED
- `extraction_version`, `imported_at`

Normalization must not destroy source evidence.

---

## 11. LiabilityPolicyV2 (clause adapter)

```yaml
schema_version: 2
orientation: BUY_SIDE | SELL_SIDE | MUTUAL
bands: PolicyBand[]
carve_outs: CarveOutSpec[]
super_caps: SuperCapSpec[]
escalation_rules: EscalationRule[]
prohibit_unlimited: boolean
consequential_damages: { require_exclusion, required_carveouts[] }
fallback_language: string | null   # redline prose only
```

---

## 12. Golden playbook fixtures (regression, not architecture)

| Firm | Distinct semantics |
|------|-------------------|
| **A** (Commercial Contract Review) | GREATER_OF(12mo, $1M); fallback 12mo if ACV<$250k; min 6mo; 2× super-cap |
| **B** | Preferred 2× annual; hard stop 1×; privacy 3× super-cap; no fixed floor |
| **C** | Preferred fixed $5M; IP uncapped; no fee multiplier |
| **D** | LESSER_OF($10M, 3× annual); different ACV threshold & GC approver |

All use the same grammar; only values differ.

---

## 13. Implementation order

1. Shared `policy_grammar` + validation
2. Symbolic comparison / resolution tests
3. `LiabilityPolicyV2` schema
4. Golden playbook fixtures
5. Deterministic v2 evaluator
6. Persistence + version/hash integration
7. AI-assisted import → v2
8. Workbench editor
9. End-to-end activation/review tests

**Do not implement Workbench UI before grammar and evaluator tests pass.**

---

## 14. Out of scope for v2.0

- Per-claim vs aggregate scope preferences as policy knobs
- Cross-reference-delegated caps
- Arbitrary nested logic beyond AND/OR groups
- Multi-currency comparison without explicit FX policy

Unknown constructs → `REQUIRES_LAWYER_INTERPRETATION`, not invented semantics.
