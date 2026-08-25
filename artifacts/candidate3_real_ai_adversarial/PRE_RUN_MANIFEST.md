# Candidate 3 — Real-AI Adversarial Qualification — Pre-Run Manifest

## 1. Commit / working tree

- HEAD commit: `4c775778eaa81c64a3d8cafbbf1147652c92126f`
- Branch: `claude/final-trust-architecture-cutover`
- `git status`: clean working tree, 0 ahead/0 behind `origin/claude/final-trust-architecture-cutover`
  at the time this manifest was written.
- Python: `3.11.15 (main, Mar 3 2026, 09:26:23) [GCC 13.3.0]`
- Manifest written: `2026-08-24T08:35:20Z`

## 2. Runtime configuration (no secrets)

- `FACT_ADMISSION_MODE`: unset in the ambient shell. **Set to `enforced` for
  the test process only** (exported inline for each corpus-run invocation;
  never written to a persisted `.env`, never changed in any deployment
  config).
- `POLICY_ENFORCEMENT_MODE`: unset in the ambient shell. Left unset for
  adapter-level extract/evaluate calls (which don't consult it); set to
  `cutover` only for the Section 11 interaction-engine sub-run, in the same
  test-process-only manner.
- `OPENAI_API_KEY`: **present** (confirmed as a boolean only — see Section 3
  of this manifest; the value itself is never printed, logged, or written
  to any tracked file). Held only in a `600`-permission file outside the
  git working tree, deleted at the end of this mission.
- Model actually called: `gpt-4o-mini` (read from `fact_admission._MODEL`
  at runtime, not assumed) via `https://api.openai.com/v1/chat/completions`.

## 3. Credential confirmation (no secret exposed)

```
$ source <scratch env file>
$ python3 -c "import os; print(bool(os.environ.get('OPENAI_API_KEY')))"
True
```

No portion of the key is reproduced anywhere in this document or in any
other artifact this mission produces.

## 4. Both real-AI call paths, traced from CURRENT production code

### Path A — shared `fact_admission.py` framework (11 of 12 adapters)

`fact_admission.py:_call_model` (line 362) — the sole HTTP call site for
this path. Confirmed via direct read of the current file (not carried over
from any prior report): POSTs to `https://api.openai.com/v1/chat/completions`,
model `gpt-4o-mini`, `Authorization: Bearer <OPENAI_API_KEY>`,
`response_format: {"type": "json_object"}`. Reads
`os.environ.get("OPENAI_API_KEY")` if no `api_key` kwarg is supplied (no
adapter passes one). Every one of: liability, confidentiality,
payment_terms, ip_ownership, insurance, data_security, governing_law,
termination, warranties, sla, assignment calls
`fact_admission.discover_candidate_spans()` then
`fact_admission.verify_and_ground()` per candidate (confirmed via
`grep -n "_fa\.\(discover_candidate_spans\|verify_and_ground\)" *.py`, one
call site pair per adapter file). Each is gated by its own
`<ADAPTER>_SEMANTIC_DISCOVERY_ENABLED` module constant, itself read at
import time from `fact_admission.semantic_discovery_enabled()`: the
adapter-specific env var wins if set at all, otherwise the global
`FACT_ADMISSION_MODE=enforced` switch applies. Indemnification's SECOND,
additive reconciliation channel (`INDEMNIFICATION_RECONCILIATION_ENABLED`,
line 106) also routes through this same `verify_and_ground` at line 148.

### Path B — `semantic_discovery_real.py` (indemnification's PRIMARY discovery)

Indemnification does **not** use `fact_admission.discover_candidate_spans`
for its primary obligation discovery. Instead
(`indemnification_policy_engine.py:173-177`, `_discover_candidate_spans`):

```python
def _discover_candidate_spans(text: str, concept: str):
    if SEMANTIC_PROVIDER == "REAL":
        from semantic_discovery_real import discover_candidate_spans_real
        return discover_candidate_spans_real(text, concept)
    return _discover_candidate_spans_simulated(text, concept)
```

`HYBRID_DISCOVERY_ENABLED = True` by default (line 80) but
`SEMANTIC_PROVIDER = "SIMULATED"` by default (line 89) — a **hardcoded
module constant, not an environment variable**. To exercise the real
OpenAI path for indemnification's primary discovery, this mission's test
harness sets `indemnification_policy_engine.SEMANTIC_PROVIDER = "REAL"` at
process start (a Python-process-local attribute override, not a file edit
— reverted implicitly when the process exits; nothing on disk changes).
This is an important, previously undocumented architectural asymmetry
between indemnification and the other 11 adapters, recorded here rather
than silently worked around.

The AI-discovered span from Path B does **not** go through
`fact_admission.verify_and_ground`'s adversarial verify/ground/admit
pipeline. Instead, the verbatim-grounded span (offsets located via exact
substring search in `semantic_discovery_real.py`, identical safety
property to Path A) is handed to indemnification's own pre-existing
deterministic structuring code — the SAME regex-based role/party/monetary/
condition parsing that runs on a regex-discovered span. This is a
different mechanism from the other 11 adapters but preserves the same
authority invariant: the AI only ever proposes a grounded text span; only
deterministic code decides what it means or whether it becomes an
authoritative fact. This asymmetry is exercised and reported on explicitly
in `EXECUTABLE_PATH.md`, not glossed over as "the same architecture as
everyone else."

## 5. Scope declaration

This manifest, and the corpus/run that follows it, is a DEVELOPMENT /
RED-TEAM exercise. It is explicitly **not** independent validation. Per
Section 13 of the mission: the corpus is hashed before execution, run
once, and any defect discovered is recorded against this exact commit
before any remediation is attempted — remediation, if any, is a SEPARATE,
later step, never folded into "the first run's" results.
