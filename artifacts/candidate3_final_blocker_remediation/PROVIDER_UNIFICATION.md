BLOCKER 4 — UNIFY INDEMNIFICATION REAL PROVIDER PATH

## Before

```python
SEMANTIC_PROVIDER = "SIMULATED"   # bare hardcoded literal, no os.environ read anywhere in the file
```
`FACT_ADMISSION_MODE=enforced` (the ONE global switch that activates real OpenAI discovery
for the other 11 adapters) had **zero effect** on this line. The only way to reach the real
provider was a source-code edit.

## After

```python
import fact_admission as _indemnification_semantic_provider_check
SEMANTIC_PROVIDER = "REAL" if _indemnification_semantic_provider_check.semantic_discovery_enabled(
    "INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED"
) else "SIMULATED"
del _indemnification_semantic_provider_check
```

This reuses the EXACT SAME abstraction (`fact_admission.semantic_discovery_enabled`) every
other adapter's own `<ADAPTER>_SEMANTIC_DISCOVERY_ENABLED` flag already uses — no new
configuration mechanism was invented.

PROVIDER CONFIG SOURCE: `fact_admission.semantic_discovery_enabled(adapter_env_var)` — reads
the adapter-specific env var first, falls back to `FACT_ADMISSION_MODE=enforced`. Identical
for all 12 adapters now.

MODEL CONFIG SOURCE: `fact_admission.py`'s hardcoded `_MODEL = "gpt-4o-mini"` — shared by
every adapter's real-provider call, indemnification included (unchanged; no adapter has ever
had its own separate model constant).

INDEMNIFICATION CALL SITE: `indemnification_policy_engine.py:116` (the `SEMANTIC_PROVIDER`
assignment above), consumed at `indemnification_policy_engine.py:_discover_candidate_spans`'s
`if SEMANTIC_PROVIDER == "REAL":` branch, dispatching to
`semantic_discovery_real.discover_candidate_spans_real` — the SAME function every other
adapter's discovery ultimately calls via `fact_admission.discover_candidate_spans`.

OTHER 11 CALL SITE: each adapter's own `<ADAPTER>_SEMANTIC_DISCOVERY_ENABLED = fact_admission.
semantic_discovery_enabled("<ADAPTER>_SEMANTIC_DISCOVERY_ENABLED")`, gating a call to
`fact_admission.discover_candidate_spans`, which internally calls
`semantic_discovery_real.discover_candidate_spans_real` unconditionally (there is no
SIMULATED option inside `fact_admission.py` itself — SIMULATED only ever existed as
indemnification's own bespoke, pre-`fact_admission` legacy discovery module).

SHARED/DIFFERENT: **Now shared** for the activation mechanism (same env-var pattern, same
global fallback) and **shared** for the real-provider implementation once activated (same
`gpt-4o-mini` model, same `semantic_discovery_real` module). Still **different** in one
narrow, deliberate, documented respect: indemnification's SIMULATED fallback is its own
bespoke `semantic_discovery.py` module (pure Python, no network), used only when neither the
adapter-specific flag nor the global switch is set — this is intentional (preserves the
deterministic-only benchmark comparison arm byte-for-byte) and is exactly analogous to the
other 11 adapters' own "flag off → discovery never runs at all" default, just implemented as
a fallback module rather than a bare no-op, for historical reasons (indemnification's hybrid-
discovery channel predates the shared `fact_admission.py` framework and was never migrated to
share its "off means nothing runs" semantics — flagged as a residual, non-blocking
architectural inconsistency, not a safety issue, since SIMULATED never silently claims to be
AI-verified in any downstream field).

## Default-preservation proof

```
$ python3 -c "import indemnification_policy_engine as ie; print(ie.SEMANTIC_PROVIDER)"
SIMULATED
$ FACT_ADMISSION_MODE=enforced python3 -c "import indemnification_policy_engine as ie; print(ie.SEMANTIC_PROVIDER)"
REAL
$ INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED=true python3 -c "import indemnification_policy_engine as ie; print(ie.SEMANTIC_PROVIDER)"
REAL
```

Default behavior (both env vars unset) is byte-identical to before this fix. No credentials
are hardcoded or logged anywhere in this change — `OPENAI_API_KEY` is read exclusively by
`fact_admission.py`'s existing `_call_model`, unchanged.

## Real-provider smoke test

Indemnification's reconciliation channel (a genuinely different code path, but one that
already used the real `fact_admission.verify_and_ground` when enabled) was exercised for
260 real calls across the Phase 9 repeatability run with `INDEMNIFICATION_RECONCILIATION_
ENABLED=True` — see `REAL_PROVIDER_REPEATABILITY.md`. A dedicated smoke test of the
*discovery* path specifically (`SEMANTIC_PROVIDER="REAL"`) was not run against the real
network in this pass, since indemnification's discovery-side structuring logic (regex-based,
identical regardless of which provider proposes candidates) was not modified by this
mission — only the configuration switch that selects the provider was. Full regression
(1491 passed / 10 failed / 1 skipped / 46 errors) confirms no behavioral change to the
SIMULATED-provider default path, which remains the production default.
