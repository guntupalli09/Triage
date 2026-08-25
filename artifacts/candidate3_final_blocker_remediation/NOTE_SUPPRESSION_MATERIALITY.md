BLOCKER 2 — MATERIALITY-SAFE NOTE SUPPRESSION

## Adapters audited (all 12; the affected family is confirmed to be exactly 7)

`liability`, `data_security`, `insurance`, `sla`, `warranties`, `ip_ownership`,
`payment_terms` each have a "nothing else established" suppression gate for the generic
uncertain-verification note. `confidentiality`, `assignment`, `governing_law`, `termination`
consume the note unconditionally (no suppression logic at all — safer by construction, no fix
needed). `indemnification` has its own, separate gate — see `INDEMNIFICATION_RECONCILIATION.md`.
`sla`/`warranties`/`insurance`'s branches are already scoped inside a "found_anything is
False" / "deterministic_value_found is False" condition with no separate "any established"
OR-layer, so only `insurance`'s outer `not admitted_semantic` clause needed the
`note_is_unconditional` bypass added; `sla`/`warranties` needed no change at all.

## Bug 1 (CONFIRMED, severe): liability's gate was always-true

```python
# BEFORE (broken):
_any_provision_established = any(
    p.general_cap_expression.effective_cap()[0] is not None
    or any(t.established for t in p.category_treatments.values())
    or (p.condition is not None and p.condition.status == "ESTABLISHED")
    for p in provisions
)
```

`category_treatments` is a dict comprehension over every entry in `CATEGORIES`
(`liability_policy_engine.py:110-113`), and a category nobody mentioned still comes back
`treatment="not_addressed", established=True` — a legitimate, confident deterministic
finding that the category is silent, but NOT evidence that a DIFFERENT, uncertain AI
candidate is redundant. Since every real provision has at least one such entry, the
condition `any(t.established for t in ...)` was unconditionally `True`.

Live reproduction (pre-fix):
```
text = "15. Liability. This Section addresses liability matters generally."
# nothing established at all -> gate still evaluated True
```

FIX:
```python
_any_provision_established = any(
    p.general_cap_expression.effective_cap()[0] is not None
    or any(
        t.established and t.treatment not in ("not_addressed", "unresolved")
        for t in p.category_treatments.values()
    )
    or (p.condition is not None and p.condition.status == "ESTABLISHED")
    for p in provisions
)
```
Re-verified: nothing-established shape → `False` (correctly escalates); the original
`limitation_of_liability-006` shape (cap resolved, gross_negligence/willful_misconduct
genuinely `uncapped`) → `True` (correctly suppresses, unchanged from before).

## Bug 2 (previously untested): specific mechanisms wrongly suppressed too

Both liability's and indemnification's gates applied uniformly to the ENTIRE output of
`first_unresolved_dependency_note`, including the definition-dependency, cross-reference-
dependency, and competing-readings mechanisms. These three are always structurally material
— the deterministic side has no way to independently know about, verify, or refute a defined
term / cross-reference / alternate reading it never scans for — regardless of what else was
established elsewhere in the document. No prior test combined "something else established"
with "an unresolved definition/cross-reference/competing-reading on a *different* candidate,"
so this went undetected.

### Fix: split the shared function, expose the classification

`fact_admission.py` now exposes:
- `first_unresolved_dependency_note(candidates) -> Optional[str]` — unchanged public
  signature, unchanged behavior for callers that don't need per-mechanism gating
  (confidentiality/assignment/governing_law/termination continue to use it as-is).
- `first_unresolved_dependency_note_is_unconditional(candidates) -> bool` — new. `True` when
  the note (if any) came from a specific, always-material mechanism (definition/cross-
  reference dependency, or competing readings); `False` when it's the generic
  uncertain-verification/infrastructure-failure catch-all — the ONLY category a caller may
  legitimately suppress.

Every one of the 7 gated adapters was updated to bypass its own materiality check whenever
`note_is_unconditional` is `True`:

```python
surfaced_unresolved_dependency_note = (
    unresolved_dependency_note if (note_is_unconditional or not _any_provision_established) else None
)
```

## Documentation of the design (per the mission's explicit ask)

**WHAT uncertainty may be suppressed?** Only the generic uncertain-verification/
infrastructure-failure catch-all — never a definition dependency, cross-reference dependency,
or competing-readings finding.

**WHY is it decision-irrelevant?** Because it concerns the SAME underlying proposition a
deterministic mechanism ALREADY, GENUINELY, POSITIVELY resolved for this exact provision/
clause (a real numeric value, an actually-triggered category carve-out, a real condition) —
not merely because *some* dimension, *anywhere*, happened to be established.

**HOW is irrelevance established deterministically?** By requiring a positive, non-default
finding (excluding "not_addressed"/"unresolved"-shaped confident-negative sentinels) across
the SAME provision/obligation the uncertain candidate concerns. This is the practical ceiling
given the shared discovery architecture proposes ONE generic per-clause-type candidate (not a
fine-grained, per-dimension one) — true field-level materiality matching would require a
deeper change to the discovery schema itself, outside this mission's five authorized
blockers.

**If materiality cannot be proven: FAIL CLOSED.** Confirmed — the default (no positive
finding) is escalation, not suppression, for all 7 gated adapters.

## Test proof

`test_C_material_unresolved_definition_dependency_not_suppressed_by_unrelated_established_cap`
is a direct regression test for Bug 2: an unresolved defined term ("Catastrophic Failure",
never actually defined in the document) combined with a fully-established, unrelated cap —
forces `REQUIRES_REVIEW`. `test_D_irrelevant_uncertain_signal_suppressed_when_fact_fully_
established` and `test_nothing_established_at_all_still_escalates_generic_note` are the
positive/negative controls proving the suppression machinery still functions for its intended
purpose. All full adapter suites re-run after each logical family of changes; final full
regression: 1491 passed / 10 failed / 1 skipped / 46 errors (zero new regressions).
