CANDIDATE 3 — FREEZE MANIFEST

## Frozen candidate

BRANCH: `claude/final-trust-architecture-cutover`
FROZEN_CANDIDATE_SHA: `d2820362b2a9c7641b2fe294fbfc1a04ccf6df3e`
UTC_TIMESTAMP: `2026-08-24T22:34:54Z`
GIT STATUS AT FREEZE: clean (`git status --porcelain` → empty output)

**No production code was modified after this point in this mission.** This mission is
validation-only, per the mission's own explicit constraint. Any production-code change
during this mission would invalidate the freeze and halt the mission; none occurred.

## Accepted #1–#5 fixes verified present at FROZEN_CANDIDATE_SHA

| Blocker | Verification |
|---|---|
| 1 — VERIFICATION_ERROR propagation | `fact_admission.py:1105-1106`: `_INFRASTRUCTURE_FAILURE_VERIFICATION_STATES = {VERIFICATION_ERROR}` plus the completeness assertion against `_UNSAFE_VERIFICATION_STATES` |
| 2 — Materiality-safe note suppression | `liability_policy_engine.py:1884`: `t.established and t.treatment not in ("not_addressed", "unresolved")` (the fixed, non-trivially-true gate) |
| 3 — Indemnification reconciliation | `indemnification_policy_engine.py:159,269`: `_GENERIC_EXCEPTION_SIGNAL_RE` and its use in the materiality gate |
| 4 — Indemnification real provider | `indemnification_policy_engine.py:117`: `INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED` env-gated `SEMANTIC_PROVIDER` resolution |
| 5 — Authoritative document state | `main.py`: 25 occurrences of `document_state` across the review page, dashboard, history, Full Report, PDF export (3 call sites), negotiation package, and external share link |

## Deferred residual risk (explicitly NOT fixed, NOT counted as resolved)

**`ip_ownership-080`** — KNOWN PRE-EXISTING RESIDUAL RISK — DEFERRED BY PRODUCT OWNER.
Documented in `artifacts/candidate3_final_blocker_remediation/ROOT_CAUSE_REPORT.md`,
`REAL_PROVIDER_REPEATABILITY.md`, and `FINAL_REMEDIATION_VERDICT.md` as a confirmed,
real-provider-reproduced `ACCEPT`↔`REQUIRES_REVIEW` unsafe clean-state transition in
`ip_ownership_policy_engine.py`'s admitted-candidate qualifier-composition loop
(~line 720), structurally unrelated to Blockers 1–5. Remains open. This mission does not
touch this code, does not remove it from the residual-risk register, and does not include
`ip_ownership-080` (the burned corpus case) in the new independent corpus built in Phase 2.

## Relevant architecture/configuration at freeze (repository defaults — NOT changed by this mission)

```
$ grep -n "^DEFAULT_MODE" policy_enforcement.py
DEFAULT_MODE = "shadow"
$ python3 -c "import fact_admission as fa; print(fa.semantic_discovery_enabled('LIABILITY_SEMANTIC_DISCOVERY_ENABLED'))"
False
```
`POLICY_ENFORCEMENT_MODE` default: `shadow` (repository default, unchanged).
`FACT_ADMISSION_MODE` default: unset/disabled (repository default, unchanged).
AI provider: OpenAI, model `gpt-4o-mini` (hardcoded in `fact_admission.py`/
`semantic_discovery_real.py` — the only model this codebase is configured to call).
This mission activates `FACT_ADMISSION_MODE=enforced`/`POLICY_ENFORCEMENT_MODE=cutover` ONLY
as process-local environment variables for the validation run's own Python process — never
written to any repository file, `.env`, or deployment configuration. See Phase 1 evidence in
this same directory.

## Test baseline at freeze (recorded, not modified during this mission)

```
$ python3 -m pytest -q --continue-on-collection-errors
10 failed, 1491 passed, 1 skipped, 46 errors in 53.19s
```
Identical to the final state of the prior blocker-remediation mission — confirms nothing
drifted between that mission's completion and this validation mission's start.

## Freeze declaration

```
FROZEN_CANDIDATE_SHA=d2820362b2a9c7641b2fe294fbfc1a04ccf6df3e
```

From this point forward in this mission, no production-code modification is permitted. All
subsequent phases operate against this exact commit, using only environment-variable
configuration and new, additive artifact/corpus files under `artifacts/`.
