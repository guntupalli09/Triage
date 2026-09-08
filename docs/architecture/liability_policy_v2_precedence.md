# Liability Policy v2 — Deterministic Evaluation Precedence

This document defines the **explicit decision hierarchy** for
`evaluate_liability_policy_v2()`. Behavior must not depend on incidental
Python iteration order over `policy.bands` or `policy.escalation_rules`.

## Decision states (most to least severe for reviewers)

| State | Meaning |
|-------|---------|
| `PROHIBITED` | Hard stop — do not accept |
| `ESCALATE` | Required approver escalation |
| `REQUIRES_REVIEW` | Insufficient facts or unresolved comparison |
| `ACCEPT_WITH_NOTE` | Within acceptable fallback band |
| `ACCEPT` | Meets or exceeds preferred band |

There is no separate `NEGOTIATE` / `MUST_REDLINE` band in v2 schema today;
gaps below preferred without a matching fallback escalate to `ESCALATE`.

## Evaluation steps (fixed order)

```
1. Policy schema invalid          → REQUIRES_REVIEW
2. Contract cap unlimited         → PROHIBITED (if prohibit_unlimited) else ESCALATE
3. Hard-stop minimum breach       → PROHIBITED
   (MINIMUM_ACCEPTABLE + outcome_if_breached=HARD_STOP, contract cap symbolically LT minimum)
4. Escalation rules               → ESCALATE when conditions TRUE;
                                    REQUIRES_REVIEW when any condition UNRESOLVED
5. Preferred band                 → ACCEPT when contract cap >= preferred (symbolic or monetary);
                                    else continue
6. Acceptable fallback bands      → ACCEPT_WITH_NOTE when conditions TRUE (or no conditions)
                                    and contract cap <= fallback expression;
                                    REQUIRES_REVIEW when band conditions UNRESOLVED
7. No band matched                → ESCALATE
8. Comparison UNRESOLVED          → REQUIRES_REVIEW (never guess)
```

## Precedence rules

### Hard stops override everything downstream

A contract cap below the policy minimum **always** returns `PROHIBITED`
before fallback or preferred evaluation — even when a conditional fallback
would otherwise accept the cap (e.g. ACV < $250k + 12 months acceptable).

### Escalation overrides fallback/preferred

When an escalation rule's condition group evaluates **TRUE**, the decision
is `ESCALATE` before any fallback acceptance.

When escalation conditions are **UNRESOLVED** (missing deal context), the
decision is `REQUIRES_REVIEW` — not skipped as “not triggered.”

### Tri-state condition semantics

| Result | Band applicability |
|--------|-------------------|
| `TRUE` | Band may apply |
| `FALSE` | Band does not apply |
| `UNRESOLVED` | Band might apply — conservative `REQUIRES_REVIEW` if outcome would change |

Missing ACV, fees, role, or governing law must **never** silently coerce to
`FALSE`.

### Currency safety

Fixed-amount comparisons require matching currency. Cross-currency pairs
return `INCOMPARABLE` / `UNRESOLVED` — never numeric comparison without an
explicit deterministic FX input (not supported today).

### ReferenceCap resolution

- Allowed target: `GENERAL_CAP` only
- Maximum reference depth: 1 (super-cap → resolved general cap)
- No cycles (only one reference target exists)
- Super-cap references never mutate or populate the general-cap band

## Implementation

See `liability_evaluator_v2.evaluate_liability_policy_v2()` and
`policy_grammar/conditions.py` for the authoritative code path.
