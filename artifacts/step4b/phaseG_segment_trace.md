# Step 4B Phase G — Segment Selection: Read-Only Trace

## G1 — Segment model

Implemented segmentation dimensions (`models.py:437-440`,
`POLICY_POSITION_SEGMENT_FIELDS`): **`segment_business_unit`**,
**`segment_customer_type`**, **`segment_deal_value_min`**,
**`segment_deal_value_max`** — a `(business_unit, customer_type,
deal_value_min, deal_value_max)` tuple stored directly on `PolicyPosition`
(not a separate `Segment` table). All-`None` is the GLOBAL segment.

- **Storage**: on `PolicyPosition` itself — segment identity is part of
  the row's own identity, not a foreign relationship.
- **Relation to playbooks**: scoped within one `(playbook_id, clause_type)`
  family; a playbook can have multiple ACTIVE positions per clause type,
  one per distinct segment tuple.
- **Relation to policy positions**: 1:1 — one `PolicyPosition` carries
  exactly one segment tuple (or GLOBAL).
- **Contract metadata → segment selection**: `Contract.review_business_unit`,
  `Contract.review_customer_type`, `Contract.review_deal_value` (set by the
  reviewing user at upload time, `main.py:1388-1390`), passed as
  `context={"business_unit":..., "customer_type":..., "deal_value":...}`
  into `snapshot_active_positions` → `resolve_segment_position`.
- **Fallback**: the GLOBAL position (all segment fields `None`) always
  matches any context (`_segment_matches_context`,
  `policy_enforcement.py:266-283`) — it is the fallback by construction,
  not a separately-flagged "default" record.
- **Priorities**: `_segment_specificity` (`policy_enforcement.py:286-295`) —
  a simple count of non-`None` segment fields; more-specific wins.
- **Overlapping segments**: allowed — e.g. an Enterprise-only position and
  a `deal_value >= 1_000_000` position can both be ACTIVE simultaneously
  for the same clause type; `resolve_segment_position` picks the single
  most-specific match, ties broken by lowest `id` (deterministic, never
  random).
- **Missing metadata**: fails closed — a position with a `None`-valued
  segment field it constrains that the context doesn't supply causes
  `_segment_matches_context` to return `False` for that position (a
  missing `deal_value` in context fails any position setting a
  min/max bound; a missing `business_unit`/`customer_type` fails any
  position constraining it).
- **`contract_side`**: confirmed NOT part of segment selection at all —
  `_segment_matches_context` never reads it. It is a separate
  `PolicyPosition` column consumed by the clause-type adapters at
  evaluation time (asymmetric buy-side/sell-side obligations), baked into
  `config_hash_for_position`'s content hash, but plays no role in
  *which* position is selected. Not a Phase G dimension — out of scope
  for segment selection, in scope for the underlying adapter's own
  Step 4A behavior (already validated, not reopened here).
- **Persistence with the review**: the SELECTED position's identity is
  persisted (`policy_revision_metadata_json[clause_type].policy_position_id`,
  same mechanism as Phase F) — the segment tuple itself is not separately
  stored, but is fully recoverable by looking up that pinned
  `PolicyPosition` row's own segment columns.

## G2 — Segment authority invariant, verified

- **Exactly one deterministic match → used.** Confirmed:
  `resolve_segment_position` returns exactly one position when exactly one
  candidate's segment constraints are satisfied.
- **No match → explicit fallback only if configured (GLOBAL), else
  skipped.** Confirmed: if no candidate matches (including no GLOBAL
  position existing at all), `resolve_segment_position` returns `None` —
  `snapshot_active_positions` simply omits that clause type from the
  result dict — the same "absence means skipped" contract as an
  uncovered clause type, never a guessed value.
- **Multiple incompatible matches → fail closed?** Not applicable in the
  strict sense the task describes ("incompatible" segments conflicting) —
  the architecture doesn't allow two candidates to both be the *single*
  most-specific match without a documented, deterministic tie-break
  (lowest id). Tested directly (below) as "two equally specific
  segments" — deterministic, not a guess, but flagged as worth product
  attention if it were ever to select between two segments an author
  intended to be mutually exclusive (see conclusion).
- **Missing required metadata → fail closed unless deterministic
  default exists.** Confirmed: GLOBAL is the only "default," and it only
  applies because it sets no constraints, not because the code
  special-cases missing metadata.

Full benchmark, PRE/POST, and regression: see
`artifacts/step4b/phaseG_segment_report.md`.
