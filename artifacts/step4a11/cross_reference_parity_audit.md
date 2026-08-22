# Step 4A.11 — Cross-Reference Parity Audit (liability, payment_terms)

Per the phase-2 continuation instruction: before moving to the 120-case
adversarial battery, audit whether the shared SOURCE→REFERENCE→TARGET
infrastructure built in `policy_engine_core.py` during Phase 1 (for
indemnification) should also be wired into liability and payment_terms,
using the four required questions. Not wired mechanically for
architectural symmetry — evaluated per-adapter on the evidence.

## Liability (`liability_policy_engine.py`)

1. **Does it contain material facts that can be delegated through
   cross-reference?** Yes — a Limitation-of-Liability clause commonly
   delegates its cap to a named Schedule/Exhibit/Order Form elsewhere in
   the document ("the cap set forth in Schedule C").

2. **Does its existing implementation already establish equivalent
   provenance safely?** Yes. `_resolve_cross_reference` (liability_
   policy_engine.py:1362) already implements a fail-closed chain that
   predates this step: it searches the full document for the named
   reference target, locates a candidate cap value near each occurrence,
   independently re-verifies each candidate against the liability CONCEPT
   (via `_has_liability_concept_nearby`, itself already scoped to the
   containing sentence with comma-delimited sub-clause disqualifier
   handling — a more granular concept check than Phase 1's target-body
   disqualifier regex), and returns `(None, reason)` — never a guess — on
   a missing target, a target with no nearby value, a value not anchored
   to the liability concept, or multiple distinct anchored values. This
   is structurally the same SOURCE→REFERENCE→TARGET→CONCEPT→VALUE shape
   Phase 1 built for indemnification, independently developed for
   liability earlier in this program.

3. **Known cases where a nearby/referenced value can be mis-owned?** No
   open defect found in this audit. The disqualifying-concept-in-same-
   sub-clause-only scoping (Step 4A.1) and the "resolved only if every
   anchored candidate agrees" rule already guard the two failure modes
   Phase 1's `_XREF_TARGET_UNRELATED_CONCEPT_RE`/multi-value check guard
   for indemnification.

4. **Would the shared resolver materially improve verification?** No
   clear case found. Liability's own mechanism uses a different but
   comparably safe strategy (search for the literal reference LABEL text
   anywhere in the document, rather than parsing a structural
   Section/Schedule HEADING the way `locate_target_provision` does) —
   suited to LoL's typically freeform reference style ("Schedule C," "the
   Order Form"). Replacing a mature, already-tested, already-fail-closed
   mechanism with the newer shared one would risk a real regression for
   an unproven gain, and duplicate rather than share the disqualifier
   logic (the concept checks are genuinely different: LoL's own-sentence,
   comma-scoped disqualifier vs. Phase 1's target-body-prefix
   disqualifier).

**Disposition: NOT wired.** Documented evidence above supports leaving
liability's existing cross-reference mechanism as-is — it already meets
the phase's own safety bar, independently developed to the same
standard. No PRE benchmark was built for a change that isn't being made.

## Payment Terms (`payment_terms_policy_engine.py`)

1. **Does it contain material facts that can be delegated through
   cross-reference?** Yes, but differently: `_SCHEDULE_CROSSREF_RE`
   (payment_terms_policy_engine.py:443) detects delegation phrases
   pointing at an Order Form, SOW/Statement of Work, Schedule, or
   Exhibit. Order Forms and SOWs are frequently genuinely SEPARATE
   documents not present in the contract text being analyzed at all —
   unlike indemnification's typical "Section 9" in-document reference,
   a meaningful fraction of these targets cannot exist in `full_text`
   regardless of resolver sophistication.

2. **Does its existing implementation already establish equivalent
   provenance safely?** Partially, and conservatively. The current
   mechanism is a boolean detector only — no target lookup, no value
   extraction is attempted. When `schedule_cross_reference` is true and
   no other payment dimension was independently established, this
   deterministically routes to REQUIRES_REVIEW ("material payment terms
   are delegated to a referenced Order Form/SOW/Schedule not included in
   this text"). This is safe (never a false-clean fact) but strictly less
   capable than Phase 1's resolver: it never attempts resolution even
   when the referenced Schedule/Exhibit IS present in the same document
   text.

3. **Known cases where a nearby/referenced value can be mis-owned?** Not
   found in this audit — because no resolution is ever attempted, there
   is no mis-ownership path today; the cost is lost automation, not a
   safety gap.

4. **Would the shared resolver materially improve verification?**
   Plausibly, but narrowly and at nontrivial cost. The gain is limited to
   the sub-case where the referenced Schedule/Exhibit is genuinely
   in-document (Order Form/SOW references would still correctly fail
   closed under either mechanism, since the target simply isn't in
   `full_text`). Realizing that gain requires adapter-specific CONCEPT
   verification for potentially several distinct payment dimensions
   (net_days, late_fee_rate, price_increase_percent each need their own
   "is this number actually about THIS dimension, not a different one
   nearby" check) — proportional in scope to the monetary-concept work
   Phase 1 built for indemnification, not a mechanical rewire.

**Disposition: NOT wired this session.** The safety bar is already met
(conservative REQUIRES_REVIEW, never a false-clean delegated fact); the
available automation gain is real but bounded and requires dedicated
adapter-specific development this session's remaining scope does not
cover safely. Moved to the post-Phase-2 backlog: build a dedicated PRE
DEV benchmark for in-document Schedule/Exhibit payment-term delegation,
then adapter-specific concept verification per dimension, before wiring.

## Summary

| Adapter | Existing mechanism meets Phase 1's safety bar? | Wire shared resolver? |
|---|---|---|
| Indemnification | N/A (built this step) | Done (Phase 1) |
| Liability | Yes — independently, already fail-closed | No — mature, safe, different strategy; no evidence of benefit |
| Payment Terms | Partially — safe but non-resolving | Not this session — real but bounded gain, needs dedicated concept-verification work first |

No production code was changed by this audit. No safety gate is affected
either way: all three adapters currently fail closed on an unresolved
cross-reference, before and after this audit.
