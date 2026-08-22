# Step 4B Phase H — Replay / Reproducibility

## Method

Three groups, per the task's explicit "do not merely rerun pure helper
functions" instruction:

- **Group 1 (end-to-end, real text)**: 15 documents through the REAL
  `policy_enforcement.apply_policies_for_review` orchestration entrypoint
  — real ACTIVE `PolicyPosition` rows, real adapters (`extract_fn`/
  `evaluate_fn`), real interaction engine, cutover mode — replayed twice
  each, comparing the full `policy_decisions`/`interaction_decisions`
  structure.
- **Group 2 (fixture-based, precise family coverage)**: the same accepted
  methodology as Phases A/D/E — `PolicyDecision` objects constructed
  directly, run through the REAL `interaction_engine_core.evaluate` +
  REAL `document_aggregation.aggregate_document_state` — guarantees exact
  coverage of every named family (clean, violation, review, critical
  interaction, evaluation error, multi-policy, multi-interaction,
  conditional, cross-reference, compound, old/new revision framing,
  legacy-risk-crossed, multiple distinct findings, duplicate evidence,
  multiple provisions, severity ordering, `NOT_APPLICABLE`,
  `NEGOTIATE`, configuration-unresolved).
- **Group 3 (H3 temporal replay, real DB)**: persist a review under
  configuration A, archive it, activate configuration B, reload the
  historical review (must remain A), review the identical contract text
  again under B, verify both reviews are correctly and distinctly
  attributed to their own governing `PolicyPosition` id.

**210 total scenarios** (exceeds ≥200), **561 total individual replay
executions**, **52 scenarios replayed 5x** (exceeds ≥50 — critical
interaction, multi-interaction, compound, multi-policy, and severity-
ordering families). Comparison strips non-authoritative fields
(`explanation`, `required_action`, `contract_language`,
`extracted_summary`, `policy_limit_summary`, `rule_id`, `start_index`,
`end_index`) before checking structural equality — never DB-generated
ids, timestamps, or explanation prose.

## Test-harness bugs found and fixed (not production defects)

Two setup bugs surfaced on the first run, both in this benchmark's own
fixtures, root-caused and fixed before trusting any result:

1. **Missing `ACTIVATION_REQUIRED_FIELDS`.** Directly setting
   `status="ACTIVE"` on a `PolicyPosition` (the same test-fixture shortcut
   `tests/test_policy_segments.py` uses) without seeding the required
   `PolicyPositionField` rows caused `build_policy_rule_for_enforcement`
   to raise `PolicyActivationError` at evaluation time — this is itself a
   genuine, useful confirmation of Phase F's defense-in-depth finding
   (enforcement re-validates completeness regardless of how `status` was
   set), not a defect. Fixed by seeding `pa.ACTIVATION_REQUIRED_FIELDS`
   for every fixture position, exactly as Phase F/G's own fixtures do.
2. **Missing `POLICY_ENFORCEMENT_MODE=cutover`.** `apply_policies_for_review`
   defaults to `DEFAULT_MODE="shadow"`, which reads the legacy
   `PolicyRule` table (never populated by this benchmark) instead of the
   `PolicyPosition` table — silently returning `policy_decisions=None`
   with no error. Fixed by setting the env var at the top of the test
   harness only (`get_enforcement_mode()`'s own docstring confirms it is
   read fresh from the environment every call, by design, so this has no
   effect outside the harness process).

## Result — 210/210 (100%), all 10 hard gates PASS

`fact_drift`, `ownership_drift`, `policy_decision_drift`,
`interaction_drift`, `evidence_drift`, `document_state_drift`,
`governance_drift`, `segment_drift`, `attention_state_drift`,
`authoritative_contradiction` — all 0, across all 561 individual replay
executions including the 52 five-times-repeated high-complexity scenarios
and the 15 real-database temporal-replay scenarios (H3).

No production defect found; **no production file was modified in this
phase.**

## Conclusion

Authoritative replay determinism holds at 100% across every group tested:
the full end-to-end orchestration path, the interaction engine, the
document aggregation function, and — critically for H3 — the persisted
governance/revision-provenance model survives a real configuration change
without retroactively altering a historical review's authoritative basis,
while a new review of the identical contract text under the new
configuration is correctly and distinctly attributed.

## Regression

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed**.
- No production file changed this phase, so the other benchmark suites
  (Phases A–G) are unaffected by construction.
