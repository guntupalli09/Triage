PRE-FREEZE INSPECTION — INSPECTION ONLY, NO CODE CHANGED

# Authority Flow Tree — what can and cannot influence an authoritative decision

Legend: 🤖 PROBABILISTIC (AI/LLM output) · 🔒 DETERMINISTIC (regex/code, reproducible)
· ⚡ AUTHORITY BOUNDARY (the one point where 🤖 must convert to 🔒 or be discarded)

```
🤖 discover_candidate_spans (fact_admission.py:442-473)
     — proposes evidence_span + offsets, offsets verified by EXACT
       substring search against the real document text before the
       candidate is allowed to exist at all (never trusts model-reported
       offsets) — this is the first 🔒 checkpoint, inside a 🤖-initiated step
       │
       ▼
🤖 verify_candidate_proposition (fact_admission.py:557-626)
     — AI adversarially verifies the proposition against the candidate span
     — returns status ∈ {ESTABLISHED, NOT_ESTABLISHED, AMBIGUOUS,
       INSUFFICIENT_CONTEXT, CONFLICTING, DEPENDENCY_UNRESOLVED,
       VERIFICATION_ERROR}
     — malformed/contradictory output (ESTABLISHED with no evidence_quote)
       forced to VERIFICATION_ERROR (fact_admission.py:615-619) — 🔒 anti-
       malformed-output defense INSIDE the 🤖 step
       │
       ▼
🔒 ground_evidence_quote / ground_qualifiers (fact_admission.py:634-690)
     — exact substring re-verification of every claimed quote (evidence,
       condition, exception, cross-reference) — a fabricated/paraphrased
       quote fails here, unconditionally, regardless of verifier confidence
       │
       ▼
🔒 resolve_definition / resolve_cross_reference_target (696-805)
     — regex-only; AI is NEVER trusted for what a defined term or a
       cross-referenced section actually says — only for WHETHER one was
       mentioned
       │
       ▼
🔒 ground_competing_readings (808-826)
     — independently grounds EACH of up to 2 claimed alternative readings
       │
       ▼
⚡ evaluate_admission (fact_admission.py:829-950) — THE AUTHORITY BOUNDARY
     ADMITTED requires ALL of:
       • verification.status == ESTABLISHED            (🔒 gate on 🤖 output)
       • grounding.passed                                (🔒)
       • no unresolved definition/cross-reference         (🔒)
       • fewer than 2 independently-grounded competing readings (🔒)
       • every claimed qualifier itself grounds           (🔒)
     Any other combination → NOT_ADMITTED — no exception, no override.
     CandidateMaterialFact has NO policy_state/decision/accept field —
     structurally cannot skip this boundary (assert_authority_boundary_intact,
     fact_admission.py:305-316)
       │
       ├── ADMITTED ──────────────────────┐
       │                                  ▼
       │                    🔒 adapter's deterministic structuring
       │                       (_extract_provision / equivalent) —
       │                       the ADMITTED span is re-parsed by the SAME
       │                       regex machinery a raw anchor would be; it
       │                       NEVER bypasses deterministic structuring to
       │                       become a policy value directly
       │
       └── NOT_ADMITTED ──────────────────┐
                                           ▼
                          🔒 first_unresolved_dependency_note
                             (fact_admission.py:1013-1130) — the ONE place
                             a NOT_ADMITTED candidate's failure can still
                             reach the decision, via 4 ordered checks:
                               1. unresolved definition dependency
                               2. unresolved cross-reference dependency
                               3. ≥2 grounded competing readings
                               4. generic uncertain-verification catch-all,
                                  gated on _PARTY_OBLIGATION_ANCHOR_RE
                                  matching the candidate's own evidence_span
                                  (policy_engine_core.py:1795-1801) — LIVE-
                                  TESTED: fires on named-party+modal
                                  obligation text, not on generic descriptive
                                  subjects (verified in this audit)
                             ⚠ NOTE: none of these 4 checks fire for
                             VERIFICATION_ERROR status — see 🚨 below.
       │
       ▼
🔒 adapter's evaluate_*_policy — THE ONLY PLACE A PolicyDecision.state
   IS EVER ASSIGNED. Confirmed by direct code reading (liability + spot-
   checks of all 12): ACCEPT/ACCEPT_WITH_NOTE/NEGOTIATE/ESCALATE always
   come from a deterministically-extracted numeric/categorical value
   (never an AI value directly); any non-None AI-sourced condition/
   exception/unresolved-note forces REQUIRES_REVIEW.
       │
       ▼
🔒 interaction_engine_core.evaluate — consumes ONLY already-decided
   PolicyDecision objects, gates on _UNSAFE_PARTICIPANT_STATES
   {NOT_APPLICABLE, REQUIRES_REVIEW, EVALUATION_ERROR} → INSUFFICIENT_FACTS,
   never calls a rule predicate on unsafe input
       │
       ▼
🔒 document_aggregation.aggregate_document_state — pure, deterministic,
   precedence-ordered; cannot report CLEAN while any REQUIRES_REVIEW/
   EVALUATION_ERROR/INSUFFICIENT_FACTS/PROHIBITED/MUST_REDLINE/ESCALATE/
   NEGOTIATE/ESCALATE-interaction exists in its own inputs
```

## 🚨 Confirmed leaks across the boundary (probabilistic signal lost, not converted)

1. **VERIFICATION_ERROR is invisible to `first_unresolved_dependency_note`.**
   `_UNCERTAIN_VERIFICATION_STATES = {NOT_ESTABLISHED, AMBIGUOUS, INSUFFICIENT_CONTEXT,
   CONFLICTING}` (fact_admission.py, verified live in this audit via direct source
   inspection) **excludes `VERIFICATION_ERROR`**. If `discover_candidate_spans`
   succeeds (a real, offset-grounded span exists) but the per-candidate
   `verify_candidate_proposition` call then fails on a provider error, the resulting
   `VERIFICATION_ERROR` candidate is silently invisible to every one of the 12
   adapters' absence-state logic. If deterministic regex also finds nothing, this
   collapses to `NOT_APPLICABLE` (clean "no clause") despite the AI having proposed a
   real span and the failure being a provider error, not a confirmed absence. This is
   a 🤖→NOTHING leak, not a 🤖→🔒 conversion — the failure evaporates instead of
   escalating.

2. **The "nothing else established" suppression gate can drop a genuinely unrelated
   candidate's uncertainty.** In liability (`_any_provision_established`,
   liability_policy_engine.py:1853-1859) and the structurally identical
   `_any_established` gates in data_security/insurance/sla/warranties/ip_ownership/
   payment_terms, an uncertain-verification note is suppressed the moment **any**
   deterministic fact for that clause type is already established — even if the
   uncertain candidate concerns a **separate, materially different** fact elsewhere in
   the document. This was added deliberately to stop `limitation_of_liability-006`-
   shaped flapping (an already-resolved fact's OWN redundant AI signal flip-flopping),
   and is proven correct for that exact shape (live-reproduced in this audit), but as
   written it is not scoped to "redundant with the SAME fact" — it is scoped to "ANY
   fact in this clause type," which is broader than the flapping case it was built to
   fix.

3. **Indemnification's reconciliation `else` branch has no equivalent gate at all** —
   `obligation.ai_identified_unreconciled_context` is set unconditionally from
   `first_unresolved_dependency_note`'s output whenever it fires, with no check
   against whatever the obligation's own monetary/scope treatment already
   established. This is the same class of leak as #2, but *unguarded*, and was never
   included in the repeatability corpus that measured "0/51 unsafe transitions."

4. **A materially-different, non-anchor-matching admitted candidate can be dropped
   outright** in liability: `semantic_qualifiers_by_start.get(anchor_start)`
   (liability_policy_engine.py:1805) only merges an admitted AI candidate into a
   provision if its own `start_offset` exactly matches an existing deterministic
   anchor's start. A second, independently-admitted liability provision (a genuinely
   separate condition/exception on a different sentence) found only by AI, with a
   deterministic anchor already present elsewhere in the document, is silently
   dropped — acknowledged in the adapter's own comment as "a known, narrower scope
   than the other 11 adapters."

None of these four leaks produce a raw-AI-driven ACCEPT (the hard admission gate at
`evaluate_admission` still holds in all four cases) — they produce a **premature or
incorrect CLEAN/absence classification by discarding a safety signal**, which is the
distinction the verdict document treats as an architectural blocker rather than the
most severe "raw AI creates ACCEPT" category.
