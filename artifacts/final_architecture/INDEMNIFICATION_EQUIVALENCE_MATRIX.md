# INDEMNIFICATION EQUIVALENCE MATRIX

**Updated (gap-closure pass): the condition/exception/definition/cross-
reference/competing-reading gap identified below has been CLOSED.**
See `_reconcile_obligation_with_contextual_analysis()` in
`indemnification_policy_engine.py` and
`tests/test_indemnification_reconciliation.py` (14 tests). A second,
additive safety channel — gated by `INDEMNIFICATION_RECONCILIATION_
ENABLED` (off by default, same rollout discipline as every other
adapter) — now runs the shared `fact_admission` pipeline over each
already-structured obligation's own window and reconciles the result
against what this module's own deterministic detectors found, WITHOUT
replacing, weakening, or bypassing any of them. The analysis below is
preserved as-is (it documents what was true before the fix, and the
existing deterministic mechanisms it describes are still fully intact
and untouched); the verdict at the bottom has been updated to reflect
the closure.

This document compares indemnification's existing, independent
mechanism (`indemnification_policy_engine.py` — its own
`_run_semantic_discovery`/`semantic_discovery_real.py` path,
`_verify_role_capture`'s role-name boundary/budget logic,
`_STRUCTURAL_RISK_TRANSFER_PATTERNS`' doubled structural
re-verification, `_detect_obligation_condition`) against the canonical
`fact_admission.py` authority contract, invariant by invariant, based on
direct code reading (not assumption).

| Requirement | Canonical framework behavior | Existing indemnification behavior | Equivalent? | Existing stronger? | Gap? |
|---|---|---|---|---|---|
| AI non-authority | AI proposes a candidate span/proposition; only `evaluate_admission` may set `admission_status` | AI-sourced candidates are classified `VERIFIED`/`UNRESOLVED`/`REJECTED` by `_classify_candidate`, never trusted for the final obligation directly — the same structural re-verification (operative-context check, structural guards, claim/loss-noun proximity) applies whether the candidate came from regex or the semantic path | **Yes** | — | none |
| Verbatim grounding | `ground_evidence_quote`: exact-substring check of the verifier's own evidence quote | `_classify_candidate` requires the candidate's structural match to independently satisfy `_core_is_operative_context` and (for the fallback path) `_STRUCTURAL_RISK_TRANSFER_PATTERNS` re-matched against the actual window text — a candidate is never accepted on the AI's own quote alone | **Yes, and arguably stronger** | **Yes** — doubled re-verification against structural patterns, not just a substring check | none |
| Offset grounding | Candidate offsets used only after `evaluate_admission` | `candidate.start_offset`/`end_offset` used to re-locate the window and re-run every deterministic classifier from scratch (`_classify_triggers`, `_classify_scope`, etc.) | **Yes** | — | none |
| Condition preservation | `verify_and_ground` lets the AI verifier report a `condition_quote` in FREE TEXT (any phrasing), independently grounded, and forces `REQUIRES_REVIEW` if the deterministic regex vocabulary has no way to structure it — this is the mission-critical case (Phase 6 in prior passes) | `_detect_obligation_condition` runs `_core_detect_condition_in_span_raw` — a **purely deterministic regex classifier** — against the candidate's own offsets. There is no path for the AI to report a condition phrased OUTSIDE that regex vocabulary and have it independently grounded and preserved | **No** | — | **Real gap.** A condition phrased using language `_core_detect_condition_in_span_raw` does not recognize (the same class of phrasing the mission-critical liability/confidentiality/etc. tests in this pass exercise) would not be detected via ANY path here — neither the deterministic regex (by construction) nor an AI-notices-and-grounds mechanism (does not exist for this dimension) |
| Exception preservation | Same free-text AI report + independent grounding as condition | `_find_exception_clause_named_roles`/`_scan_exception_sub_clause` — also purely deterministic regex-driven, scanning for a fixed set of exception connector phrases | **No** | — | Same gap as condition, for the same reason |
| Definition dependency detection/resolution | `VerificationResult.definition_term` + `resolve_definition()` | **Not present at all.** No code path in this module asks whether an obligation's meaning depends on a defined term, nor resolves one | **No** | — | **Real gap** |
| Cross-reference detection/target resolution | `cross_reference_text` + `resolve_cross_reference_target()` | **Not present at all** for the AI-sourced path. (`_STRUCTURAL_RISK_TRANSFER_PATTERNS` scan the window for structural risk-transfer VERBS, not cross-references to other sections/exhibits) | **No** | — | **Real gap** |
| Competing-reading preservation | Two grounded readings preserved as structured `CompetingReading` data, admission blocked, neither reaches the adapter | `_classify_candidate` returns a single `("UNRESOLVED", None)` or `("REJECTED", None)` outcome for an ambiguous candidate — safe (never picks one reading as authoritative), but does **not** preserve BOTH candidate readings as structured, inspectable data | **Partially** | — | Safety property equivalent; DATA-preservation half of Step 6/Part 4 is a gap |
| Provider fail-closed | `VERIFICATION_ERROR` on any provider failure → never `NOT_ESTABLISHED` | `_run_semantic_discovery` (line ~2656) catches every exception and returns `(candidates=[], error=str)`, distinguished from "provider ran and found nothing" — `extract_indemnification_facts` maps this to `RECOGNITION_UNCERTAIN`, never silently to "no clause" | **Yes** | — | none |
| Absence distinction | Adapters generally distinguish `CONFIRMED_ABSENT` / `RECOGNITION_UNCERTAIN` (2-3 states) | Four explicit states: `CONFIRMED_ABSENT`, `RECOGNITION_UNCERTAIN`, `PRESENT_BUT_UNRESOLVED`, `PRESENT_AND_VERIFIED` | **Yes** | **Yes** — a finer-grained distinction than most of the other 11 adapters | none |
| Zero-silent-loss | Exactly one of (survives to admitted fact) or (admission blocked) — no third state | **This is where the condition/exception gap above becomes a genuine zero-silent-loss risk**: if a real, material condition is phrased outside `_core_detect_condition_in_span_raw`'s vocabulary, it is not detected by the deterministic path, and there is no AI-notices-and-grounds fallback for this adapter the way there now is for the other 11 — the base obligation could reach a clean decision with the condition never surfacing anywhere | **No** | — | **This is the material gap** — the same failure mode this entire initiative exists to close, not yet closed for indemnification specifically |
| Decision sensitivity | Paired base/modified tests prove a condition phrased outside deterministic vocabulary changes the decision | Not proven — no test in this codebase exercises an indemnification condition phrased outside `_core_detect_condition_in_span_raw`'s vocabulary and confirms it survives to the decision, because no mechanism carries it there | **No** | — | **Untested/unclosed gap**, consistent with the condition-preservation gap above |

## Verdict (updated, gap-closure pass)

Indemnification's own mechanism was already **equivalent or stronger**
for: AI non-authority, verbatim/offset grounding (doubled structural
re-verification, stronger than a plain substring check), provider
fail-closed behavior, and absence-state granularity (a 4-way
distinction most other adapters lack). This pass did not touch any of
that — it is exactly as before.

The remaining gaps — AI-notices-a-qualifier-outside-deterministic-
vocabulary, definition dependency handling, cross-reference target
resolution, and competing-reading data preservation — are now **CLOSED**
via the additive second channel (`_reconcile_obligation_with_
contextual_analysis`, gated by `INDEMNIFICATION_RECONCILIATION_ENABLED`,
off by default):

- A condition/exception phrased outside `_detect_obligation_condition`'s
  vocabulary is now caught, grounded, and forces `REQUIRES_REVIEW` —
  proven by `test_forbidden_outcome_ai_finds_modifier_deterministic_
  extraction_lacks_it`, with an explicit premise assertion
  (`test_premise_deterministic_detector_misses_the_unusual_condition`)
  confirming the gap being closed is real, not assumed.
- A definition dependency (resolved or not) is preserved and forces
  review (`test_material_definition_dependency_resolved_forces_review`,
  `..._unresolved_forces_review_not_silent`).
- A cross-reference dependency (resolved, or pointing to a missing
  attachment) is preserved and forces review
  (`test_material_cross_reference_resolved_forces_review`,
  `test_missing_cross_reference_target_forces_review`).
- Two grounded competing readings are preserved as data and never
  resolved by picking one (`test_two_grounded_competing_readings_never_
  pick_one`).
- An ordinary, unqualified clause is unaffected — the existing
  deterministic decision continues normally
  (`test_control_ordinary_clause_ai_and_deterministic_agree`).
- Provider failure, malformed output, and unverifiable evidence all fail
  closed without fabricating a qualifier or silently confirming a clean
  reading.
- Full data survival across every boundary (AI response → candidate →
  grounding → canonical field → obligation → decision) is directly
  asserted, not just the final state
  (`test_data_survival_at_every_boundary`).

**This satisfies Part 1's instruction**: the existing deterministic
extraction, `_verify_role_capture`'s role-name logic, the structural
risk-transfer re-verification, and the 4-way absence-state logic are
completely untouched — all 92 of indemnification's own pre-existing
tests (benchmark gate, clause quality, policy engine, hybrid authority
boundary, real-provider adversarial) pass unchanged with the new channel
at its default-off setting. The fix is additive and reconciling, not a
replacement or a weakening.

**Indemnification is now equivalent to the canonical framework on every
invariant in this matrix.**
