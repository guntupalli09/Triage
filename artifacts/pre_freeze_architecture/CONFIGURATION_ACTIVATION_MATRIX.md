PRE-FREEZE INSPECTION — INSPECTION ONLY, NO CODE CHANGED

# Configuration / Activation Matrix

No setting below was changed. All values are read-only observations of current HEAD `7bf099f`.

| Feature | Current default | Required production value | Code consumer | Effect | Verified? |
|---|---|---|---|---|---|
| `FACT_ADMISSION_MODE` | unset → disabled (empty string ≠ "enforced") | `enforced` | `fact_admission.semantic_discovery_enabled` (fact_admission.py:134-148) | global fallback for every adapter's AI-discovery flag when that adapter's own env var is unset | Yes, read directly |
| `POLICY_ENFORCEMENT_MODE` | unset → `"shadow"` (`DEFAULT_MODE`, policy_enforcement.py:52) | `cutover` | `policy_enforcement.get_enforcement_mode` (policy_enforcement.py:140-153), read fresh every call | shadow/legacy: only `limitation_of_liability` runs, via the legacy `apply_liability_policy` path; interaction engine never runs (`interaction_decisions=None` hard-set, policy_enforcement.py:809). cutover: all 12 clause types run (subject to per-playbook ACTIVE-position gating) + interaction engine | Yes, read directly and confirmed via `git show`/direct code read this session |
| `LIABILITY_SEMANTIC_DISCOVERY_ENABLED` | `False` | set (or rely on `FACT_ADMISSION_MODE=enforced`) | liability_policy_engine.py:1633-1635 | gates AI discovery for this adapter specifically | Yes |
| `ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED` | `False` | same | assignment_policy_engine.py:190-192 | same | Yes |
| `CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED` | `False` | same | confidentiality_policy_engine.py:244-246 | same | Yes |
| `DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED` | `False` | same | data_security_policy_engine.py:528-530 | same | Yes |
| `GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED` | `False` | same | governing_law_policy_engine.py:134-136 | same | Yes |
| `INSURANCE_SEMANTIC_DISCOVERY_ENABLED` | `False` | same | insurance_policy_engine.py:340-342 | same | Yes |
| `IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED` | `False` | same | ip_ownership_policy_engine.py:563-565 | same | Yes |
| `PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED` | `False` | same | payment_terms_policy_engine.py:654-656 | same | Yes |
| `SLA_SEMANTIC_DISCOVERY_ENABLED` | `False` | same | sla_policy_engine.py:422-424 | same | Yes |
| `TERMINATION_SEMANTIC_DISCOVERY_ENABLED` | `False` | same | termination_policy_engine.py:410-412 | same | Yes |
| `WARRANTIES_SEMANTIC_DISCOVERY_ENABLED` | `False` | same | warranties_policy_engine.py:404-406 | same | Yes |
| **`indemnification` discovery provider** | `SEMANTIC_PROVIDER = "SIMULATED"` — **hardcoded, no env var of any kind** | requires an actual source-code edit to `"REAL"` | indemnification_policy_engine.py:80,89,174 | **`FACT_ADMISSION_MODE=enforced` has zero effect on this adapter's primary discovery channel** — it is always the non-AI simulator | Yes — grepped the whole file, zero `os.environ`/`os.getenv` references tied to `SEMANTIC_PROVIDER` |
| `INDEMNIFICATION_RECONCILIATION_ENABLED` | `False` | env-gated like the other 11 adapters' flags | indemnification_policy_engine.py:104-106 | gates indemnification's ONLY genuinely real-AI, `fact_admission`-backed channel (reconciliation of already-found obligations, never discovery of new ones) | Yes |
| AI model | `gpt-4o-mini`, hardcoded | — | fact_admission.py:332, semantic_discovery_real.py:50-52 | no env override exists to change model | Yes |
| Temperature/sampling | not set at all in the request body | — | fact_admission.py:370-378 | OpenAI API default (1.0) applies implicitly; no determinism control | Yes |
| Provider timeout | 30s, hardcoded | — | fact_admission.py:333 | any slower response is treated as a failure | Yes |
| Retry behavior | **none** — single attempt | — | `_call_model` (fact_admission.py:364-413) | any transient failure fails closed immediately (safe) but has no self-heal | Yes |
| `OPENAI_API_KEY` presence check | no startup-time check | should exist for cutover deployments | fact_admission.py:365-368 (raises `ProviderUnavailable` per-call, not at boot) | a missing key silently degrades every cutover-mode review to "everything needs manual review" rather than failing to start with a clear error | Yes |
| Startup migration-coverage gate | only checks `limitation_of_liability` | should cover all 12 clause types per the module's own docstring | `verify_migration_coverage_or_fail_closed` → `find_unmigrated_liability_policies` (policy_enforcement.py:736-744) | cutover mode can start even if the other 11 clause types have no migrated ACTIVE PolicyPosition equivalent — the module's own docstring (lines 31-36) is stale, describing "six clause types" when 12 are registered | Yes |
| Per-playbook ACTIVE PolicyPosition coverage | playbook-dependent, no global default | full 12-clause-type coverage per playbook intended for a genuine cutover | `evaluate_active_policies` (policy_enforcement.py:449-451) | a clause type with no ACTIVE position on a given playbook is silently skipped for that review, by design (not an error) | Yes |

## With FACT_ADMISSION_MODE=enforced and POLICY_ENFORCEMENT_MODE=cutover (both traced, neither set)

| Question | Answer | Basis |
|---|---|---|
| Real OpenAI contextual discovery? | **YES for 11/12 adapters; NO for indemnification's primary discovery channel** | indemnification_policy_engine.py:80,89 — hardcoded `SIMULATED`, no env path to `REAL` |
| Canonical fact admission (`evaluate_admission`)? | YES — pure function, runs identically regardless of mode flags whenever a `VerificationResult`/`GroundingResult` exists | fact_admission.py:829 |
| All 12 adapters? | YES the code path supports all 12 (`pa.CLAUSE_TYPES`, playbook_authoring.py:87), but actual per-document coverage depends on each playbook's ACTIVE PolicyPosition set — a playbook lacking one for a clause type silently skips it | policy_enforcement.py:418-458 |
| Interaction engine? | YES, unconditionally inside the cutover branch | policy_enforcement.py:786-793 |
| Unified document aggregation? | YES — this is a read-time function, not gated by either env var; it runs on every render regardless of mode | document_aggregation.py:149-198; `main.py:1276`'s `effective_mode` for it is itself an *approximation*, not a stored fact |

## Hidden flags that could leave part of the architecture inactive even with both flags set correctly

1. `indemnification_policy_engine.SEMANTIC_PROVIDER = "SIMULATED"` — no environment override exists at all (the single most consequential finding in this matrix).
2. Per-clause-type ACTIVE `PolicyPosition` coverage on the specific playbook being used.
3. The startup fail-closed migration-coverage gate only validates `limitation_of_liability`, not the other 11 — a cutover deployment can boot with 11 unmigrated clause types and no startup error.
4. No startup-time `OPENAI_API_KEY` presence check for `FACT_ADMISSION_MODE=enforced` deployments.
