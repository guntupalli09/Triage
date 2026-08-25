# ADAPTER_MATRIX — Final Trust Architecture

This supersedes `artifacts/fact_admission_architecture/ADAPTER_MATRIX.md`
for status purposes; that document's detailed per-adapter dimension
mapping (material facts, absence semantics per adapter, the full 7-state
absence matrix) is re-affirmed here by reference rather than duplicated,
having been re-verified in Phase 0 of this pass (see
PRE_IMPLEMENTATION_MAP.md: 12/12 adapters confirmed to have
`_run_semantic_discovery`, 11/12 confirmed on the shared framework).

## Status (12/12, re-verified this session)

| # | Adapter | Shared framework integration | Env-var configurable (this session) | Production enabled |
|---|---|---|---|---|
| 1 | limitation_of_liability | YES | YES (`LIABILITY_SEMANTIC_DISCOVERY_ENABLED` or `FACT_ADMISSION_MODE=enforced`) | No — both env vars unset by default |
| 2 | indemnification | NO — own pre-existing, separately-frozen mechanism (`semantic_discovery_real.py` / `SEMANTIC_PROVIDER`, still a hardcoded constant, NOT converted to env-var this session — deliberately left untouched, see ARCHITECTURE.md) | NO | No — `SEMANTIC_PROVIDER` hardcoded `"SIMULATED"` |
| 3 | confidentiality | YES | YES | No |
| 4 | payment_terms | YES | YES | No |
| 5 | ip_ownership | YES | YES | No |
| 6 | insurance | YES | YES | No |
| 7 | data_security | YES | YES | No |
| 8 | governing_law | YES | YES | No |
| 9 | termination | YES | YES | No |
| 10 | warranties | YES | YES | No |
| 11 | sla | YES | YES | No |
| 12 | assignment | YES | YES | No |

**No adapter's semantic pathway is enabled in any environment by
default.** Enabling requires an explicit environment variable AND (per
PRE_IMPLEMENTATION_MAP.md's Phase-0 finding) `POLICY_ENFORCEMENT_MODE=cutover`
for the decision to even reach a user, since the semantic pathway only
runs inside `apply_active_policies()`, itself only called in cutover mode.

## No adapter is marked COMPLETE without executable tests (per mission requirement)

Every row above has executable tests: 7-8 tests per adapter in
`tests/test_<adapter>_fact_admission.py` (prior branch) plus this
session's 7 tests for the env-var mechanism itself
(`tests/test_fact_admission_env_config.py`), all passing — see
TARGETED_RESULTS in the prior branch's artifacts and this branch's
regression run (1266 passed, 0 new regressions, confirmed in this
session's commit `2b2f826`).

## Real gaps not yet closed for any of the 12 adapters (see RESIDUAL_RISK_REGISTER.md)

- No adapter's `CandidateMaterialFact` usage populates the
  condition/proviso/exception/cross_reference/schedule_dependency/
  competing_interpretation fields from the semantic layer's own read of
  context — see ARCHITECTURE.md.
- No adapter has been tested against a real model at scale (all targeted
  tests mock the provider response).
- No adapter's semantic-layer decision carries a version stamp in
  `policy_revision_metadata_json` (see REPRODUCIBILITY_REPORT.md).
