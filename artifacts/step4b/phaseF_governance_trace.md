# Step 4B Phase F — Playbook Governance: Read-Only Trace

Read directly from `models.py`, `playbook_authoring.py`, `policy_enforcement.py`,
`main.py` — production code is authority; design-doc comments were used
only as pointers to where to verify, never trusted standalone (each claim
below is followed by the exact function/line that enforces it).

## F1 — Governance object model

- **`Playbook`** (`models.py:249`) — the top-level container a review is
  performed against (`Contract.playbook_id`). No lifecycle of its own.
- **`PolicyRule`** (`models.py:274`) — the legacy, pre-authoring liability-
  only rule row, no lifecycle, still what `legacy`/`shadow` modes read.
  Out of scope for governance (never has a revision/approval concept).
- **`PolicyPosition`** (`models.py:381`) — the actual governed object.
  `status ∈ {DRAFT, NEEDS_REVIEW, APPROVED, ACTIVE, ARCHIVED}`
  (`POLICY_POSITION_STATUSES`, `models.py:348`). **Revisions are copied
  rows, not mutated rows, not a version-numbered single row**: editing an
  ACTIVE position creates a brand-new row (`status=DRAFT`) with
  `config_json`/fields copied from the ACTIVE row — confirmed in
  `get_or_build_editable_position` (`playbook_authoring.py:1010-1061`) and
  enforced defensively a second time in `apply_position_update`
  (`playbook_authoring.py:1123-1141`, raises `PolicyEnforcementGuardError`
  if ever called on a `status=="ACTIVE"` row). There is no separate
  "playbook revision" concept — each `(playbook_id, clause_type, segment)`
  family has its own independent row-chain.
- **`PolicyPositionField`** (`models.py:454`) — per-field provenance
  (EXTRACTED/INFERRED/MANUAL, evidence excerpt) within one `PolicyPosition`
  row — copied alongside the row on revision (loop in
  `get_or_build_editable_position`, skipping any field already superseded).
- **`PolicyPositionApproval`** (`models.py:532`) — one row per lifecycle
  transition (`_record_transition`, `playbook_authoring.py:1202`) —
  MARKED_REVIEWED/APPROVED/ACTIVATED/REVERTED/ARCHIVED, each carrying
  `from_status`/`to_status`/actor/timestamp/reason. This is the audit
  trail of who moved a position through the lifecycle and when — an
  append-only log, never edited or deleted by any code path found.
- **Segment identity** — `(segment_business_unit, segment_customer_type,
  segment_deal_value_min, segment_deal_value_max)` on `PolicyPosition`
  itself (`models.py:437-440`), part of the row's own identity (the "at
  most one ACTIVE row" invariant is scoped per segment tuple, not merely
  per clause_type — `activate_position`, see below).
- **Contract-side provenance** — `Contract.policy_revision_metadata_json`
  (one entry per clause_type: `policy_position_id`, `config_hash`,
  `revision_activated_at`, `source_type` — `_revision_metadata_for`,
  `policy_enforcement.py:379-386`) and `Contract.policy_decisions_json`
  (the actual decision content) are both persisted at review time and
  never recomputed afterward (confirmed: every `main.py` route that
  displays a contract's policy decisions reads these two columns directly
  off the `Contract` row, never re-calls `apply_policies_for_review`).

## F2 — Twelve questions, answered from code

1. **Can multiple active revisions exist simultaneously?** Only across
   *different segments* for the same `(playbook_id, clause_type)` — by
   design, not ambiguity (`activate_position`'s sibling-archive query is
   scoped by segment tuple, `playbook_authoring.py:1255-1269`). Within one
   exact segment, no: activating a new row always archives the existing
   ACTIVE sibling in the same transaction first.
2. **What prevents Draft from governing?** `snapshot_active_positions`
   (`policy_enforcement.py:339-343`) filters `PolicyPosition.status ==
   "ACTIVE"` at the SQL level — a DRAFT row is never fetched into the
   dict evaluation reads from, let alone reasoned about.
3. **What prevents Needs Review from governing?** Same SQL filter — only
   `status=="ACTIVE"` is ever queried. Separately, `activate_position`
   itself refuses any status other than `APPROVED`
   (`playbook_authoring.py:1251-1252`, raises `PositionLifecycleError`),
   so NEEDS_REVIEW can never even reach ACTIVE without passing through
   APPROVED first.
4. **Is Approved distinct from Active?** Yes — an APPROVED row is not
   queried by `snapshot_active_positions` either; only the subsequent,
   separately-gated `activate_position` call moves it to ACTIVE.
5. **What happens when an Active position is edited?**
   `get_or_build_editable_position` returns a new `status=DRAFT` row,
   copying content — the ACTIVE row itself is never touched.
6. **New revision or mutation?** New revision (new row, new id). Verified
   twice: the authoring-flow function's own behavior, and
   `apply_position_update`'s defensive `PolicyEnforcementGuardError` if
   ever called on a `status=="ACTIVE"` row regardless of caller.
7. **Can a historical review identify its exact governing revision?**
   Yes — `Contract.policy_revision_metadata_json[clause_type].policy_position_id`
   plus `config_hash` (a content hash, not just an id) is pinned at review
   time. `verify_policy_finding` (`policy_enforcement.py:819-873`) replays
   against that EXACT `policy_position_id`, by id, "regardless of whether
   it is still ACTIVE today," and separately re-checks
   `config_hash_for_position(position) != revision_meta.get("config_hash")`
   as a second, independent integrity check.
8. **Can deletion/archival/supersession destroy historical provenance?**
   **Archival/supersession: no** — `activate_position` only ever flips
   `status` to `ARCHIVED`, the row and its id persist physically forever.
   **Deletion: YES — a genuine defect, found and fixed this phase** (see
   §F-defect below): `Playbook.policy_positions` carries
   `cascade="all, delete-orphan"` (`models.py:270`), so
   `POST /playbooks/{id}/delete` hard-deleted every `PolicyPosition` row
   for that playbook, including ones a historical `Contract`'s pinned
   `policy_position_id` still points to — reproduced directly against a
   real SQLite-backed `Contract`/`Playbook`/`PolicyPosition` fixture before
   this session's fix (see below).
9. **Can changing the active revision change an OLD review's apparent
   basis?** No — `Contract.policy_decisions_json`/`policy_revision_metadata_json`
   are persisted at review time and never recomputed; every display route
   reads them directly off the row. `snapshot_active_positions` is only
   ever called once, at review time, for a NEW review.
10. **What happens with no active revision?** That clause type is "simply
    skipped" (`evaluate_active_policies`'s own docstring,
    `policy_enforcement.py:408-413`) — if NO clause type has an ACTIVE
    position at all, `apply_active_policies` returns `None` for the whole
    playbook (`policy_enforcement.py:568-569`), which
    `apply_policies_for_review`'s cutover branch turns into
    `policy_decisions=None` (`policy_enforcement.py:767-768`) — the exact
    input `document_aggregation.aggregate_document_state` (Step 4B's own
    work) maps to `CONFIGURATION_UNRESOLVED`, never a guessed clean state.
11. **What happens with multiple eligible candidates?** Only reachable via
    segments (two ACTIVE rows for the same clause_type, different
    segments). `resolve_segment_position` (`policy_enforcement.py:298-313`)
    picks the single most-specific match deterministically (specificity
    score, ties broken by lowest id — never arbitrary/random), and returns
    `None` (skip, not a guess) if no candidate's segment constraints are
    satisfied by the reviewed contract's context.
12. **Snapshotted or dynamically dependent on current DB state?**
    **Snapshotted.** `snapshot_active_positions` is taken once per review;
    the resulting decisions and revision metadata are persisted
    immediately (`main.py:1411-1413`) and never re-derived from the
    database on a later read.

## Authority invariant (F3)

**Every authoritative review must have exactly one deterministically
identifiable governing policy configuration** — confirmed structurally
true for the architecture as designed (per-clause-type pinned
`policy_position_id` + content hash, immutable-by-construction revision
rows, deterministic segment resolution) — **with exactly one violation
found**: the playbook-delete cascade could destroy the very row that
identity points to. Fixed this session (see below); the invariant now
holds for every code path found.

## Defect found and fixed

**Historical revision destruction via playbook deletion.** Reproduced
directly: created a `Playbook` with an `ACTIVE` `PolicyPosition`, a
`Contract` whose `policy_revision_metadata_json` pins that position's id,
then called `db.delete(playbook); db.commit()` exactly as
`POST /playbooks/{id}/delete` does. Result: delete succeeded silently
(SQLite does not enforce the dangling `Contract.playbook_id` FK by
default), and the `PolicyPosition` row was hard-deleted via the ORM
cascade. The `Contract`'s own `policy_decisions_json` (the actual decision
content) survives untouched, but `verify_policy_finding` can no longer
locate the exact revision that produced it — a genuine provenance/
reproducibility defect exactly per this task's F7 classification ("stores
the final finding but cannot establish which policy revision produced
it... NOT automatically harmless").

**Fix** (`main.py`, `playbook_delete`): refuses deletion (`409`) if any
`Contract.playbook_id` references the playbook, with a message directing
the user to stop using it for new reviews instead — consistent with the
existing "archive, never destroy" philosophy `PolicyPosition` itself
already uses. No schema change; a business-logic guard only, since the
existing `Contract.playbook_id` foreign key is already indexed and
sufficient to answer "has this playbook ever been used for a review."

Full benchmark, PRE/POST, and regression: see
`artifacts/step4b/phaseF_governance_report.md`.
