CANDIDATE 4 — PHASE 1: SHARED EVIDENCE-STATE MODEL

## Existing states mapped first (per this mission's explicit instruction not
to blindly add a new enum if equivalent states already exist)

Two existing, orthogonal state families already cover the requested
semantics:

**1. `fact_admission.py`'s verification-state vocabulary** (per-candidate,
before admission): `ESTABLISHED`, `NOT_ESTABLISHED`, `AMBIGUOUS`,
`INSUFFICIENT_CONTEXT`, `CONFLICTING`, `DEPENDENCY_UNRESOLVED`,
`VERIFICATION_ERROR`. `_UNSAFE_VERIFICATION_STATES` = every state except
`ESTABLISHED`. Only `ESTABLISHED` candidates are admitted
(`ADMISSION_STATUS = ADMITTED`); everything else is either discarded (with
a surfaced note, per Candidate 3's Blocker 1/2 fix) or, for
`VERIFICATION_ERROR` specifically, unconditionally escalated regardless of
corroboration.

Mapping to the mission's requested vocabulary:
- `ESTABLISHED_PRESENT` = `ESTABLISHED` (admitted)
- `AMBIGUOUS` = `AMBIGUOUS` (already exists, unchanged)
- `CONFLICTING` = `CONFLICTING` (already exists, unchanged)
- `DEFINITION_UNRESOLVED` / `CROSS_REFERENCE_UNRESOLVED` = the two specific,
  unconditional mechanisms inside `_classify_unresolved_dependency_note`
  (definition dependency, cross-reference dependency) — already exist as
  distinguishable NOTE TEXT, not as separate top-level verification states,
  because both currently share the `DEPENDENCY_UNRESOLVED` verification
  state at the candidate level. This is intentional: the DOWNSTREAM
  consequence (must never feed a clean decision) is identical for both, so
  collapsing them into one verification state while preserving the
  distinguishing note text for human-facing explanation is not a loss of
  safety-relevant information.
- `PROVIDER_UNAVAILABLE` / `VERIFICATION_ERROR` = `VERIFICATION_ERROR`
  (already exists, unconditionally escalated per Candidate 3 Blocker 1)
- `INSUFFICIENT_EVIDENCE` = `INSUFFICIENT_CONTEXT` (already exists,
  unchanged)
- `NOT_ESTABLISHED` = a candidate the AI proposed but which verification
  positively disproved against the source text — this is the ONLY state
  that legitimately contributes toward absence, and even then only when
  paired with confirmed deterministic non-match (see below).

**2. Each adapter's own `absence_state` field** (per-document, after
extraction — this is the layer Candidate 3's and this mission's hard gates
actually operate on): `CONFIRMED_ABSENT` (default), `RECOGNITION_
UNCERTAIN` (provider outage/error with no deterministic match either),
`PRESENT_BUT_UNRESOLVED` (something operative found, nothing verifiable
structured), and, in `indemnification`/`payment_terms`/`termination`,
`DEPENDENCY_UNRESOLVED` and `PRESENT_AND_VERIFIED`.

Mapping:
- `ESTABLISHED_ABSENT` = `CONFIRMED_ABSENT` reached ONLY when (a) no
  deterministic anchor matched at all, AND (b) semantic discovery ran
  successfully and found nothing, AND (c) no admitted candidate, note, or
  operative anchor exists. This is "affirmatively proven absence" in the
  only sense a regex+AI system can support it: genuine total silence
  across both channels, not a partial/ambiguous signal.
- `ABSENCE_UNVERIFIED` / `PRESENT_BUT_UNRESOLVED` = the same state (this
  mission's requested name and the codebase's existing name for the
  identical concept).
- `PROVIDER_UNAVAILABLE` = `RECOGNITION_UNCERTAIN`.

## The critical requirement, verified

**"UNKNOWN must never collapse into ABSENT."** Before Cluster 1's fix
(Phase 0), this invariant was VIOLATED in three adapters (insurance,
data_security, ip_ownership): a genuinely operative anchor with unresolved
content silently defaulted to `CONFIRMED_ABSENT`. After the fix, reaching
`CONFIRMED_ABSENT` requires the adapter's own `found_anything`-equivalent
signal to be False — i.e., genuinely nothing (no admitted candidate, no
note, no operative anchor) was found by any channel. Verified by
`tests/test_candidate4_remediation.py`'s negative-control tests
(`test_insurance_genuinely_nothing_stays_not_applicable`, `test_ip_
ownership_genuinely_nothing_stays_absent`) alongside the positive
reclassification tests.

**"UNRESOLVED must never collapse into CLEAN."** Verified structurally:
every adapter's evaluator either (a) returns `REQUIRES_REVIEW` directly
when `absence_state` is `PRESENT_BUT_UNRESOLVED`/`RECOGNITION_UNCERTAIN`/
`DEPENDENCY_UNRESOLVED` and nothing more specific was found (the
restructured fallback, Phase 0 Cluster 2), or (b) surfaces the unresolved
signal as an `unresolved_facts` entry that forces `REQUIRES_REVIEW`
unconditionally via each adapter's `if unresolved: return REQUIRES_REVIEW`
gate (unchanged, pre-existing architecture, confirmed present in all 12
adapters via `grep -c "if unresolved:" *_policy_engine.py`).

## Prefer one shared mechanism vs. twelve bespoke patches — decision

A single shared `fact_admission.classify_absence_authority(...)` helper
was drafted and rejected for THIS remediation pass: `insurance`,
`data_security`, and `ip_ownership` each track a different shape of
"was anything specific established" (per-coverage-type limits;
per-topic booleans/enums; per-dimension token sets), and each adapter's
evaluator has a different, already-precise per-dimension comparison loop
that must run BEFORE the generic fallback (Cluster 2). Forcing these
through one shared function would require either (a) a lowest-common-
denominator boolean that loses which SPECIFIC dimension is unresolved
(degrading the `unresolved_facts`/`required_action` explanation text every
adapter already provides), or (b) a shared function taking 3+ adapter-
specific callback parameters, which is not meaningfully simpler or safer
than the current, consistent PATTERN applied identically three times. The
shared element that DOES generalize — and is already shared, unchanged by
this mission — is `fact_admission`'s verification-state vocabulary and
`policy_engine_core.is_operative_context`, which all three fixes reuse
directly rather than reimplementing.

## What changed

No new top-level state was added. `first_unresolved_dependency_note` /
`first_unresolved_dependency_note_is_unconditional` (Candidate 3) are
unchanged. Three adapters' `absence_state` RECLASSIFICATION LOGIC
(when `CONFIRMED_ABSENT` is downgraded to `PRESENT_BUT_UNRESOLVED`) was
broadened and reordered, per Phase 0's Cluster 1/2 findings.
