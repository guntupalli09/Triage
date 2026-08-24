# REPRODUCIBILITY_REPORT

## Pre-existing mechanism (re-verified, unmodified)

`Contract.policy_revision_metadata_json` (models.py) pins
`policy_position_id` / `revision_activated_at` / a deterministic
`config_hash` (`policy_enforcement.config_hash_for_position()`) per
clause type, per review, independent of the current live playbook state.
`interaction_engine_core.decision_snapshot()`/`interaction_decision_hash()`
provide the equivalent for interaction decisions. Confirmed present in
this session's Phase 0 pass; not modified.

## Gap, confirmed still open

No `semantic_verifier_version` or `verifier_prompt_schema_version` field
exists anywhere in `policy_revision_metadata_json` or any other persisted
column. `fact_admission.py` has no `__version__` constant and no version
string is threaded into any `PolicyDecision` or stored metadata. This was
identified in the prior branch's `PRE_IMPLEMENTATION_MAP.md` §11 and
remains unclosed after this session — not fixed, because doing so
requires deciding where the version should be threaded (a new key in
`policy_revision_metadata_json`, populated by `policy_enforcement.py` at
evaluation time) and this session prioritized the Phase 0 findings and
Phase 12 env-var work over this item, both of which were assessed as
higher-value given the confirmed shadow-mode default (a reproducibility
gap for a subsystem that has never run for real users yet is lower
urgency than clarifying whether it runs at all).

## Historical replay test coverage

`tests/test_liability_fact_admission.py::
test_admitted_fact_produces_deterministic_replay_decision` (prior
branch) confirms `policy_engine_core.decision_hash()` is stable across 5
repeated `evaluate_liability_policy()` calls against one fixed,
already-admitted fact set. Not repeated for the other 10
newly-integrated adapters or for a full `apply_policies_for_review()` +
`interaction_engine_core.evaluate()` combined replay in this session.

## Verdict

**HISTORICAL REPLAY: PARTIAL PASS.** The underlying determinism
primitive (`decision_hash`/`check_deterministic`) is proven sound and
exercised for one adapter. The version-provenance gap for the NEW
semantic layer specifically remains open. Since no flag is enabled by
default and mode defaults to shadow, no live decision exists today that
this gap could actually corrupt — but it must be closed before Phase 16
cutover for any adapter whose flag is enabled.
