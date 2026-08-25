CANDIDATE 5 — AUDITABILITY AND HISTORICAL REPLAY (Sections 11-12)

Verified by code inspection (pre-existing architecture from prior
missions, unmodified by Candidate 5 — this mission adds no new
persistence code, only confirms what already exists satisfies the
requirement):

## Reproducibility without fresh AI rediscovery

`policy_enforcement.apply_policies_for_review` (the real production
entry point) is called from exactly 2 places in `main.py` — both at
upload/re-analysis time (lines 1516, 1659). It is NEVER called again
merely to VIEW an already-analyzed contract. Its result
(`policy_decisions`, `policy_revision_metadata`, `interaction_decisions`)
is persisted to `Contract.policy_decisions_json` /
`Contract.policy_revision_metadata_json` / `Contract.interaction_
decisions_json`. Every downstream surface — `view_contract` (results
page), the PDF builder, the negotiation-package cover memo, and the
external share renderer — reads these PERSISTED columns directly; none
of them re-invoke AI or re-run the policy engine. This means:

- The exact playbook position pinned at analysis time
  (`policy_revision_metadata_json`'s per-clause-type `policy_position_id`
  and revision) is what any later view/replay reads — not whatever the
  playbook looks like today.
- The exact AI-discovered/admitted evidence, grounded facts, conditions,
  exceptions, definitions, and cross-reference resolutions that fed the
  original decision are embedded in the persisted decision record's
  `unresolved_facts`/`category_treatments`/`explanation` fields — the
  decision object IS the audit record, not a pointer that requires
  rerunning discovery to reconstruct.
- "Verify/Replay" a historical contract means reading these same
  persisted columns again — this already cannot require re-discovering
  yesterday's facts with today's AI, because the code path that would do
  that (`apply_policies_for_review`) is structurally never invoked by any
  read path.

## What is NOT yet separately persisted (an honest, disclosed gap)

The provider/model identifier (e.g. "OpenAI"/"gpt-4o-mini"), a
prompt/schema version number, and the application commit SHA at analysis
time are NOT currently stored as explicit fields alongside
`policy_decisions_json`. This means a fully complete forensic
reconstruction ("exactly which model, which prompt version, which code
commit produced this decision") is not yet possible purely from the
database — only the DECISION ITSELF (which adapter, which state, which
evidence, which policy position) is guaranteed reproducible, which is
the customer-facing-critical piece (Section 0/12's "WHY was this
flagged?"). Adding those provenance fields is a real, valuable follow-up
that this mission explicitly deprioritizes per its own P0-P3 ordering
(Section 21: auditability of the DECISION is P1; forensic provenance of
which exact model/prompt version produced it is lower-value without a
concrete customer or compliance requirement driving it, and was not
found to be needed to answer "why was this flagged" in any of this
mission's real-provider testing).

## Audit trail: contract text -> decision

For every non-clean decision produced during this mission's real-
provider testing, `unresolved_facts`/`notes` fields quote the exact
contract language and name the specific policy requirement or missing
element — confirmed via direct inspection of `burned_regression_raw_
results.jsonl`'s `decision_explanation` field for every non-`ACCEPT`
case. No "AI says so" or "regex matched" appears anywhere in any
decision's explanation text; every one traces contract excerpt -> named
gap -> policy state.

AUDITABILITY: PASS
HISTORICAL REPLAY: PASS
