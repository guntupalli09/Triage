# Fault Injection Re-verification (Phase 10)

Re-ran `artifacts/candidate3_real_ai_adversarial/provider_failure/run_fault_injection.py` (unmodified — no fault-injection code was touched this mission) against the final commit state.

| Case | Result |
|---|---|
| missing_api_key | REQUIRES_REVIEW — fail-closed |
| invalid_api_key | REQUIRES_REVIEW — fail-closed |
| timeout | REQUIRES_REVIEW — fail-closed |
| connection_failure | REQUIRES_REVIEW — fail-closed |
| http_429 | REQUIRES_REVIEW — fail-closed |
| http_500 | REQUIRES_REVIEW — fail-closed |
| malformed_json | REQUIRES_REVIEW — fail-closed |
| empty_response | REQUIRES_REVIEW — fail-closed |
| missing_required_fields | REQUIRES_REVIEW — fail-closed |
| evidence_quote_not_in_source | CANDIDATES_DISCARDED — fail-closed |
| invented_condition | NOT_ADMITTED (BLOCKED) — fail-closed |
| invented_exception | NOT_ADMITTED (BLOCKED) — fail-closed |
| invented_definition | NOT_ADMITTED (BLOCKED) — fail-closed |
| invented_cross_reference | NOT_ADMITTED (BLOCKED) — fail-closed |
| contradictory_model_response | NOT_ADMITTED (BLOCKED) — fail-closed |
| indemnification_primary_path_provider_failure | MUST_REDLINE (NOT_CLEAN) — fail-closed |

**16/16 fail-closed**, identical to the prior mission's result. Expected: this mission's changes are confined to `policy_engine_core.py` (new detection primitives, never touching `_call_model`/HTTP call sites) and 9 adapters' deterministic structuring/evaluation logic (never touching how provider errors are caught or how candidates are admitted/rejected). No provider-failure-handling code path was modified.
