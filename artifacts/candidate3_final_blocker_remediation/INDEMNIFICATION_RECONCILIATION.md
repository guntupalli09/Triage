BLOCKER 3 — INDEMNIFICATION RECONCILIATION

## Architecture (unchanged deterministic core, additive safety channel)

```
EXISTING INDEMNIFICATION DETERMINISTIC EXTRACTION (unchanged: 4-signal
absence gate, per-direction obligation structuring, monetary/scope/
condition detection, role-pair-aware dedup)
                    +
     AI CONTEXTUAL DISCOVERY (reconciliation channel only — this
     mission does NOT touch primary obligation discovery's own
     structure, only which provider backs it; see PROVIDER_UNIFICATION.md)
                    ↓
     fact_admission.verify_and_ground over the SAME obligation window
     the deterministic detectors already scanned
                    ↓
              RECONCILIATION
              /            \
     consistent (nothing      material disagreement /
     beyond deterministic)    unresolved dependency /
        ↓                     uncaptured exception
   existing deterministic         ↓
   policy evaluation,         obligation.ai_identified_unreconciled_context
   UNCHANGED                  set -> forces REQUIRES_REVIEW at
                               evaluate_indemnification_policy
```

The deterministic parser was never replaced or weakened — `_reconcile_obligation_with_
contextual_analysis` only ever ADDS a note to `obligation.ai_identified_unreconciled_context`;
it cannot alter `monetary`, `scope`, or the deterministic `condition` field.

## The two-layer fix

**Layer 1 (original gap):** the `else` branch (verification uncertain/failed) consumed
`first_unresolved_dependency_note`'s output completely unguarded. Fixed with a gate mirroring
liability's: unconditional notes (definition/cross-reference/competing-readings) always
escalate; the generic catch-all is suppressed only when this SAME obligation's own monetary,
scope, and condition are already genuinely, positively established.

**Layer 2 (second-order gap, found by this mission's own repeatability testing):** unlike
liability, indemnification has NO deterministic classifier that can positively confirm "this
named carve-out category was checked and found absent" (liability's `category_treatments`
does this per Blocker 2's fix). `obligation.condition.status == "UNCONDITIONAL"` is
structurally ambiguous between "genuinely no exception exists" and "an exception exists in
the text but the condition detector didn't structure it." Monetary/scope being established
says nothing about whether a same-clause exception was missed. Fixed with a general (not
corpus-specific), standard legal-drafting exception-vocabulary check
(`_GENERIC_EXCEPTION_SIGNAL_RE`: except/excluding/other than/with the exception of/carve-out/
shall not apply to/does not apply to/notwithstanding/provided that/unless) — when this
vocabulary appears in the window AND the deterministic condition detector never resolved
anything beyond UNCONDITIONAL, the note is never suppressed, regardless of monetary/scope.
Monetary/scope were also tightened from OR to AND.

## The 12 required test cases

| # | Case | Result |
|---|---|---|
| 1 | deterministic finds operative obligation; AI agrees | Covered by existing indemnification test suite (unchanged); stays clean |
| 2 | deterministic misses unusual wording; AI finds + grounds it | Covered by existing `test_indemnification_reconciliation.py` tests (unchanged behavior) |
| 3 | deterministic finds clean obligation; AI identifies material condition | `test_material_definition_dependency_resolved_forces_review` and siblings (pre-existing, still pass) |
| 4 | AI identifies material exception/carve-out | `test_indemnification_material_gap_plus_provider_error_forces_review` (new) + `dev-indemnification-006-class-01` (real-provider repeatability, 5/5 stable REQUIRES_REVIEW after the fix) |
| 5 | AI identifies descriptive/non-operative language | Covered by shared `is_operative_context`/verifier rejection path (unchanged) |
| 6 | AI verification fails | `test_provider_timeout_never_silently_confirms_clean`, `test_malformed_ai_output_never_silently_confirms_clean` (pre-existing, both pass — confirmed correctly suppressed for exception-free text) |
| 7 | AI and deterministic materially disagree | `test_unverifiable_evidence_never_becomes_authoritative` (pre-existing, unaffected — grounding failure, never admitted) |
| 8 | competing readings | `test_two_grounded_competing_readings_never_pick_one` (pre-existing, now protected by `first_unresolved_dependency_note_is_unconditional`'s unconditional treatment) |
| 9 | definition dependency unresolved | `test_material_definition_dependency_unresolved_forces_review_not_silent` (pre-existing, passes) |
| 10 | cross-reference unresolved | `test_missing_cross_reference_target_forces_review` (pre-existing, passes) |
| 11 | provider unavailable | `test_provider_timeout_never_silently_confirms_clean` + `test_indemnification_analogue_of_liability_006_stays_clean` (new) + `test_indemnification_material_gap_plus_provider_error_forces_review` (new) |
| 12 | provider returns malformed result | `test_malformed_ai_output_never_silently_confirms_clean` (pre-existing, passes) |

FORBIDDEN outcomes ("material disagreement/uncertainty → ACCEPT" or "→ NOT_APPLICABLE") were
not found in any of the 12 cases after both fix layers.

## Zero existing indemnification safety regressions

`python3 -m pytest -q tests/test_indemnification_reconciliation.py` (the pre-existing suite):
25 passed, 0 failed, after both fix layers. Full indemnification-adjacent test count in the
whole-suite regression is unchanged from baseline.

## Real-provider proof

Repeatability run (52 cases × 5 = 260 real calls), first pass (Layer 1 fix only):
`dev-indemnification-006-class-01` showed 4/5 `REQUIRES_REVIEW` + 1/5 `ACCEPT_WITH_NOTE` — an
unsafe transition. Second pass (after Layer 2 fix): 5/5 `REQUIRES_REVIEW`, stable.
