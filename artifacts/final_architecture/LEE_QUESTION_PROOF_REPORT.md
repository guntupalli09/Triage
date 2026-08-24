# LEE_QUESTION_PROOF_REPORT

Format per this mission's Phase 17 spec. Every question's LIVE ACTION /
LIVE RESULT / SCREENSHOT fields are **NOT PERFORMED — no live-product
validation occurred this session** (see FINAL_VALIDATION_REPORT.md).
Verdicts use the mission's allowed set: PROVEN / DISPROVEN / PARTIAL /
NOT PROVABLE. Fuller reasoning and residual-risk detail for each
question lives in `artifacts/fact_admission_architecture/
LEE_QUESTION_MATRIX.md` (prior branch) — re-checked in this session where
noted, not blindly re-asserted.

---

### Q1. What stops a confidently wrong extraction from becoming a confidently wrong deterministic ruling?

**EXPECTED SAFETY PROPERTY**: descriptive/non-operative language cannot
become an admitted operative fact regardless of surface resemblance to
operative language.
**TEST DOCUMENT**: 11 distinct, naturally-varied descriptive sentences
(one per newly-integrated adapter).
**CODE/TRACE EVIDENCE**: `fact_admission.evaluate_admission()` requires
adversarial `ESTABLISHED` + grounding pass; every adapter's `test_
verifier_not_established_descriptive_language_never_admitted` test.
**VERDICT: NOT PROVABLE** (this session) — mocked evidence only; the
mission explicitly requires live-model evidence against an untouched
family for this specific question, which no session has produced yet.

---

### Q2. What counts clauses that aren't there?

**EXPECTED SAFETY PROPERTY**: `CONFIRMED_ABSENT` requires affirmative
absence logic (semantic check ran, completed, found nothing), never mere
non-recognition.
**CODE/TRACE EVIDENCE**: absence matrix (ABSENCE_MATRIX.md), all 12
adapters.
**VERDICT: PARTIAL** — proven at the code/unit-test level for all 12
adapters; unproven at corpus/live-model recall scale, and currently inert
for real users under the default `shadow` enforcement mode
(PRE_IMPLEMENTATION_MAP.md).

---

### Q3. What happens when the clause exists but the system fails to recognize it?

**EXPECTED SAFETY PROPERTY**: `RECOGNITION_UNCERTAIN` (provider
failure/error) never silently becomes absence.
**CODE/TRACE EVIDENCE**: per-adapter `test_recognition_uncertain_routes_
to_requires_review*` tests, all 12 adapters (11 new + indemnification's
own pre-existing suite).
**VERDICT: PARTIAL** — proven for the "semantic layer ran and errored"
case; NOT proven for the case the question is really asking about (a
clause missed by BOTH deterministic and semantic layers with no error
raised) — a recall question, not a code-boundary question, unmeasured.

---

### Q4. How do you know evidence attached to a decision actually supports the fact?

**EXPECTED SAFETY PROPERTY**: every AI-cited evidence quote is
mechanically re-verified against the untouched source text, independent
of the AI's own claim.
**CODE/TRACE EVIDENCE**: `fact_admission.ground_evidence_quote()`; every
adapter's `test_hallucinated_candidate_never_becomes_*`.
**VERDICT: PROVEN** — for the fact-admission layer specifically. Scope
note: does not extend to regex-only decisions, which rely on the regex
match itself as evidence (pre-existing, unchanged, out of this mission's
new-mechanism scope).

---

### Q5. Can the semantic/LLM layer ever acquire policy authority?

**EXPECTED SAFETY PROPERTY**: no code path from an AI call's return
value to a `policy_engine_core` decision state.
**CODE/TRACE EVIDENCE**: `fact_admission.py`'s vocabulary contains no
decision state; `_FORBIDDEN_FIELD_NAMES` guard; every adapter's admitted
candidate only seeds pre-existing deterministic structuring.
**VERDICT: PROVEN** — as a structural property of the code as written.
Not enforced by an automated cross-file check beyond the field-name
guard; relies on code-review discipline for future changes (residual
risk, not a present gap).

---

### Q6. What happens when two individually extracted policy facts need to be considered together?

**EXPECTED SAFETY PROPERTY**: an interaction rule never reasons over an
unsafe/missing participant fact.
**CODE/TRACE EVIDENCE**: `interaction_engine_core._gate_participants()`,
unmodified; `tests/test_interaction_engine_core.py` passes.
**VERDICT: PROVEN** for the mechanism itself; **PARTIAL** for end-to-end
behavior with the new semantic paths actually producing the facts that
feed it (not tested in combination this session — see
INTERACTION_REPORT.md).

---

### Q7. What happens when two parties look symmetric but differ on one material dimension?

**EXPECTED SAFETY PROPERTY**: asymmetry detection routes to
`REQUIRES_REVIEW` with the specific reason named, never silently resolved.
**CODE/TRACE EVIDENCE**: `policy_engine_core.detect_role_attributed_
asymmetry`, unmodified; confirmed unweakened by 100% of every touched
adapter's pre-existing regression suite passing unchanged this session.
**VERDICT: PROVEN** for the pre-existing mechanism's continued integrity;
**NOT PROVABLE** yet for a semantically-discovered (rather than
regex-found) asymmetric pair specifically — no direct test constructs
that scenario.

---

### Q8. Can a condition, proviso, schedule, cross-reference, definition, exception, or qualifier be silently stripped from the authoritative fact?

**EXPECTED SAFETY PROPERTY**: qualifiers identified by the AI's
contextual read are preserved onto the admitted fact, not dropped.
**CODE/TRACE EVIDENCE**: `CandidateMaterialFact` has the fields (Step 1
compliance); **no adapter populates them from the semantic layer** —
confirmed by code inspection this session (see ARCHITECTURE.md). Only
each adapter's own PRE-EXISTING deterministic condition detector
(`policy_engine_core.detect_condition_in_span`, unmodified) runs over
semantically-discovered text, by virtue of the candidate seeding the same
window a regex match would.
**VERDICT: PARTIAL** — the pre-existing detector is structurally
positioned to catch this for text a regex anchor would have found too,
but the AI's own qualifier-detection capability (explicitly required by
this mission's Phase 2) is not yet wired to preserve anything on the
candidate object itself. This is the clearest concrete gap surfaced by
honestly answering this question rather than asserting PROVEN.

---

### Q9. Can a user see a clean document even though some underlying policy evaluation is unresolved?

**EXPECTED SAFETY PROPERTY**: the aggregated document state is never
calmer than its own inputs support, on every surface.
**CODE/TRACE EVIDENCE**: `document_aggregation.py`'s false-clean
invariant (pre-existing); wired into all 3 surfaces (UNIFIED_STATE_REPORT.md).
**VERDICT: PARTIAL** — proven at the code level for the narrower claim;
the review-page wiring specifically has no automated HTTP-level test in
this sandbox (blocked by missing `fastapi`), and the broader mode-split
concern in UNIFIED_STATE_REPORT.md means the aggregation's inputs are
themselves narrower than "everything" in the default `shadow` mode.

---

### Q10. Can today's policy configuration change the meaning of a historical review?

**EXPECTED SAFETY PROPERTY**: a historical review remains explainable by
the exact configuration that produced it, never today's live playbook
state.
**CODE/TRACE EVIDENCE**: `policy_revision_metadata_json` +
`config_hash_for_position()`, pre-existing, unmodified.
**VERDICT: PARTIAL** — proven for the pre-existing mechanism covering
policy positions generally; **specifically unproven/open** for the new
semantic layer, which carries no version stamp anywhere yet
(REPRODUCIBILITY_REPORT.md) — a future prompt/schema change to
`fact_admission.py` would be indistinguishable from today's version in
historical data.

---

### Q11. Where can the system STILL create false confidence?

**VERDICT: NOT PROVABLE as an exhaustive claim** (by construction — see
below; must never be answered "nowhere").

Concrete, current sources, ranked:
1. Live-model recall for all 11 newly-integrated adapters is entirely
   unmeasured (Q1/Q3) — everything is mocked.
2. Condition/proviso/exception preservation from the AI's contextual read
   is not implemented (Q8) — the single clearest architectural gap this
   proof pass found.
3. The mode-gating discovery (Phase 0, this session): the ENTIRE modern
   architecture — old and new — may be inert in production today
   depending on `POLICY_ENFORCEMENT_MODE`'s actual deployed value, which
   this session cannot check. If it is inert, every "PROVEN" verdict
   above describes code that is not currently protecting any real user;
   if it is active, none of this session's claims have been validated
   against real traffic either way.
4. No version provenance for the semantic layer (Q10).
5. The review-page badge (Q9) and the interaction-engine end-to-end
   combination (Q6) both rest on code-path argument rather than direct
   execution in this sandbox.
6. 45 test files could not be collected in this sandbox at all
   (missing `fastapi`/`python-docx`/`cryptography`), so any regression
   reachable only through those paths is unverified this session, same
   as the prior branch's finding.

This list is deliberately not exhaustive by construction — an exhaustive
list would itself overclaim — but every item is specific and actionable.
