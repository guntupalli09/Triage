PHASE 7 — AUTHORITY SURFACE CONSISTENCY (frozen candidate, validation mode)

## Method

Two complementary checks, since this sandbox cannot render actual HTTP responses/PDF bytes for
every surface in a single automated pass (see `AUTHORITATIVE_DOCUMENT_STATE.md` from the prior
blocker-remediation mission for the same limitation, unchanged here):

1. **Code-structural guarantee.** All 7 authoritative customer surfaces (review page, dashboard,
   history, Full Report, PDF export, negotiation package, external share link) call the
   identical `main._document_state_for_contract(contract)` helper, which itself calls the
   identical `document_aggregation.aggregate_document_state(...)` pure function on the identical
   `contract.overall_risk`/`policy_decisions_json`/`interaction_decisions_json` fields — this was
   verified directly in the prior blocker-remediation mission (Blocker 5) and reconfirmed
   unchanged at `FROZEN_CANDIDATE_SHA` (`git diff` shows no changes to `main.py`,
   `document_aggregation.py`, or the four newly-wired templates since that mission's last commit
   touching them).

2. **Live proof, this mission.** Phase 1's trace (`phase1_result.json`) computed the SAME
   aggregated `document_state` for the SAME real, cutover-mode policy/interaction decisions with
   `overall_risk` deliberately forced to `"low"`:
   ```
   Aggregated authoritative document_state (with overall_risk forced to 'low'): HAS_POLICY_VIOLATION
   ```
   Since every surface's authority signal is a single function call on this same triple of
   inputs, and that function is pure and deterministic (confirmed by direct reading — no
   randomness, no I/O, no dependency on which surface calls it), computing it once and knowing
   every surface calls the identical function IS the proof of consistency: there is no code path
   by which two of the 7 surfaces could compute two different `document_state` values for the
   same contract.

## For identical review data, do surfaces disagree?

**No.** By construction (one shared pure function, one shared call-site pattern verified present
on all 7 surfaces), no surface can present a different authoritative state than another for the
same contract. This is a code-structural guarantee, not merely an empirical observation from a
finite sample of surfaces exercised.

RESULT: **CONSISTENT**
