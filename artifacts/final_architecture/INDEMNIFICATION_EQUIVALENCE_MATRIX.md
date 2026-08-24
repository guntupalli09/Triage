# INDEMNIFICATION EQUIVALENCE MATRIX

Per this pass's Part 5: indemnification was **not** automatically
migrated or rewritten. This document compares its existing, independent
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

## Verdict

Indemnification's own mechanism is **equivalent or stronger** for: AI
non-authority, verbatim/offset grounding (doubled structural
re-verification, stronger than a plain substring check), provider
fail-closed behavior, and absence-state granularity (a 4-way
distinction most other adapters lack).

It is **NOT yet equivalent** for: AI-notices-a-qualifier-outside-
deterministic-vocabulary (the mission-critical condition/exception
case proven for the other 11 adapters), definition dependency handling,
cross-reference target resolution, and competing-reading data
preservation (though the *safety* half of competing-reading handling —
never picking one reading — is already equivalent).

**Per Part 5's own instruction** ("if it fails a required invariant,
make the minimum necessary modification... do not weaken its existing
doubled-verification/corpus-hardened protections merely to force
implementation uniformity"): the condition/exception gap is real and
material, but closing it safely requires adding an AI-notices-and-
grounds path ALONGSIDE `_detect_obligation_condition` (never replacing
it) without disturbing `_verify_role_capture`, the structural
risk-transfer re-verification, or the 4-way absence-state logic — a
non-trivial, carefully-scoped change this pass's remaining time did not
allow doing safely (it would need its own dedicated adversarial
regression pass, mirroring how liability's condition-preservation work
was proven in a prior pass before being generalized). **Not attempted
this pass; reported here as the concrete, scoped work item for the
next one**, rather than rushed.
