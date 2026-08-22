# Step 4B Phase F — Playbook Governance

## Method

Read-only trace first (`artifacts/step4b/phaseF_governance_trace.md`) —
answers all 12 required questions directly from `models.py`/
`playbook_authoring.py`/`policy_enforcement.py`, each with the exact
function/line enforcing the claim, never inferred from design docs.

Benchmark (`scripts/step4b_run_phaseF_governance_benchmark.py`, combined
corpus+runner given the stateful nature of this phase) — 174 cases
(exceeds the ≥150 target), executing the REAL lifecycle functions
(`mark_ready_for_review`, `approve_position`, `activate_position`,
`return_to_draft`, `get_or_build_editable_position`,
`apply_position_update`) and REAL revision-pinning functions
(`snapshot_active_positions`, `config_hash_for_position`,
`verify_policy_finding`) against a real SQLite-backed database, never
mocked or reimplemented.

## PRE / defect found

The read-only trace itself, backed by a direct empirical reproduction
(not merely reading code), found one genuine defect before any benchmark
case was written: **`POST /playbooks/{id}/delete` could permanently
destroy a historical review's governing-revision provenance.**
`Playbook.policy_positions` carries `cascade="all, delete-orphan"`
(`models.py:270`); reproduced directly — created a `Playbook` with an
`ACTIVE` `PolicyPosition`, a `Contract` whose `policy_revision_metadata_json`
pinned that position's id, then called `db.delete(playbook); db.commit()`
exactly as the route does. The delete succeeded silently and the
`PolicyPosition` row was hard-deleted. The `Contract`'s own decision
content survives, but `verify_policy_finding` can no longer locate the
exact revision that produced it — a reproducibility/provenance defect per
this task's own F7 classification, not "automatically harmless" merely
because the finding itself is still stored.

Everything else traced — DRAFT/NEEDS_REVIEW never reaching
`snapshot_active_positions`, `activate_position`'s strict `APPROVED`-only
gate, `get_or_build_editable_position`'s copy-on-write revision model,
`apply_position_update`'s defense-in-depth refusal to touch an ACTIVE
row, `resolve_segment_position`'s deterministic specificity-ranked
selection, and the persisted (never dynamically re-derived)
`policy_decisions_json`/`policy_revision_metadata_json` — was already
correct by design and construction.

## Fix

`main.py`, `playbook_delete`: refuses deletion (`409`) when any
`Contract.playbook_id` references the playbook, directing the user to
stop using it for new reviews instead of deleting it — consistent with
the "archive, never destroy" pattern `PolicyPosition` itself already
uses for superseded revisions. No schema change; a business-logic guard
against the existing, already-indexed `Contract.playbook_id` foreign key.

## POST — 174/174 (100%), all 13 hard gates PASS

- `draft_authority = 0`
- `needs_review_authority = 0`
- `inactive_authority = 0`
- `wrong_revision_authority = 0`
- `ambiguous_governing_revision = 0`
- `historical_revision_mutation = 0`
- `historical_policy_mutation = 0`
- `untraceable_governing_revision = 0`
- `dynamic_current_state_dependency = 0`
- `wrong_playbook = 0`
- `wrong_policy_position = 0`
- `false_clean_from_missing_governance = 0`
- `arbitrary_candidate_selection = 0`

Families covered: draft/needs-review/approved-inactive never governing;
active governing; illegal transitions rejected at the function level
(`PositionLifecycleError`); editing an ACTIVE position always creates a
new DRAFT (never mutates), with a second defense-in-depth check;
old-active→new-active supersession (archives, never deletes); archived
revisions remain fetchable by id; a historical review's pinned
`policy_position_id` identifies its exact governing revision; the same
contract reviewed legitimately under revision N and then N+1 keeps two
distinct, correctly-attributed pins; no-active-revision is skipped, never
guessed; multiple active candidates (segments) resolve deterministically
and repeatably; missing and corrupt (hash-mismatched) revision references
both fail cleanly (`verified=False`, never a fabricated replay); the
playbook-delete guard now correctly blocks deletion of a
history-carrying playbook while still allowing deletion of an unused one;
and editing a position after a review leaves that review's persisted
decision completely unaffected.

## Regression

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed**.
- No adapter, interaction rule, or `POLICY_ENFORCEMENT_MODE` default
  touched. Only `main.py`'s `playbook_delete` route was changed.
- Other Step 4B benchmark suites (A–E) are unaffected by construction
  (none exercise the playbook-delete route or governance lifecycle).

## Conclusion

The governance authority invariant — every authoritative review must have
exactly one deterministically identifiable governing policy configuration
— holds for every code path traced and tested, after fixing the one
deletion-cascade gap that could have destroyed it. Phase G (segment
selection) may proceed; segment resolution was already substantially
verified as part of this phase's "multiple active candidates" family
(`resolve_segment_position`), and Phase G will extend that coverage with
its own dedicated benchmark per the task's required families.
