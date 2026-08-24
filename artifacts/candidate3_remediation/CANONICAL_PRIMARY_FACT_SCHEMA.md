# Canonical Primary-Fact Schema (Candidate 3 remediation)

## Decision: do not build a new twelve-way schema; add one new absence-state value to the existing per-adapter vocabulary

Per Section 2 of the mission ("Use the shared fact-admission schema and adapter-specific composition where necessary") and Section 8's instruction to "choose the smallest architecture that proves the invariant": `PRE_IMPLEMENTATION_MAP.md` establishes that the actual defect is not a missing schema (every adapter already has a `CandidateMaterialFact` → `verify_and_ground()` → `ADMITTED`/`NOT_ADMITTED` pipeline, and every adapter already re-parses admitted candidates' offsets through its own deterministic structuring code) — it is a **missing terminal state** for the specific outcome "AI's proposition was independently verified ESTABLISHED and grounded, but the adapter's own narrower value-extraction regex could not structure a specific primary-fact value from it."

### The new state: `PRESENT_BUT_UNRESOLVED`

Added to every shared-framework adapter's `absence_state` vocabulary (already a plain string constant per adapter, matching this codebase's existing convention — no new Enum, no new dataclass):

```
CONFIRMED_ABSENT       -- neither channel found anything
RECOGNITION_UNCERTAIN  -- provider errored/timed out/malformed output
DEPENDENCY_UNRESOLVED  -- (existing, liability/payment_terms only) candidate's cross-ref/definition dependency unresolved
PRESENT_BUT_UNRESOLVED -- NEW: an admitted (ESTABLISHED, grounded) AI candidate exists for
                          this document, but no deterministic value-extraction regex could
                          structure a specific primary-fact value from its window
```

`evaluate_<adapter>_policy()` routes `PRESENT_BUT_UNRESOLVED` to `REQUIRES_REVIEW` — never `ACCEPT`, never `NOT_APPLICABLE` — using the SAME `if facts.absence_state == "RECOGNITION_UNCERTAIN": return REQUIRES_REVIEW` branch pattern every adapter already has (extended to also match `PRESENT_BUT_UNRESOLVED`), so this is an additive one-line branch change per adapter, not a rewrite of the evaluation function.

### Why this satisfies Section 2's "canonical admitted fact" requirement without a new schema

Section 2 lists what a canonical admitted fact must be "capable of representing at minimum" (party, directionality, value, condition, exception, cross-reference, etc.). All of these are **already representable** — `CandidateMaterialFact` already carries `obligated_party`, `beneficiary_party`, `scope`, `trigger`, `condition`, `exception`, `cross_reference`, `definition_resolution`, `competing_readings`, and `admission_status`/`non_admission_reason` as provenance (`fact_admission.py:159-247`). What was missing was not a field on the schema — it was the **downstream consumer's willingness to treat "ADMITTED but not deterministically structurable into MY narrow value field" as a distinct, safe, visible outcome** rather than silently falling through to whatever the adapter's default branch happens to be. `PRESENT_BUT_UNRESOLVED` is exactly that consumer-side fix.

### Zero-silent-loss compliance (Section 4)

An admitted candidate's condition/exception/definition-dependency/cross-reference are, as before, merged onto `ai_identified_condition`/`ai_identified_exception`/`ai_identified_definition_or_reference` — unchanged by this remediation, since Candidate 2's remediation and the original fact-admission architecture already grounds and blocks admission on any ungrounded qualifier (`evaluate_admission()`, `fact_admission.py:919-929`). `PRESENT_BUT_UNRESOLVED` only changes what happens to the PRIMARY proposition when it can't be structured — every qualifier already gets independent, correct treatment via the existing admission gates.

### Indemnification is unaffected

Indemnification's structuring parser already treats an unparseable-but-risk-transfer-signal-bearing span as `UNRESOLVED` (its own existing vocabulary, `indemnification_policy_engine.py:2752-2754`, routed to REQUIRES_REVIEW territory already) — it independently reached the same design point this remediation generalizes to the other 11. No change made to indemnification.
