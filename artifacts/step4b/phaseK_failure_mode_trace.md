# Step 4B Phase K — Failure-Mode / Dependency-Failure Trace

Read-only trace of every point where an external or internal dependency
can fail, be unavailable, or hand back a corrupted/malformed value, and
what the production code actually does in each case. Traced from code,
not from filenames or design docs.

## 1. Explanation/semantic provider (OpenAI) — `evaluator.py`

- `LLMEvaluator.__init__`: if no `OPENAI_API_KEY`, `self.client = None`.
  If `OpenAI(api_key=...)` construction itself raises, the exception is
  caught and logged; `self.client` stays `None`.
- `evaluate()`: `if not self.client: ... return None` — the "provider
  unavailable" path returns `None`, never raises, never fabricates.
- The entire `client.chat.completions.create(...)` call, `json.loads`, and
  post-processing (`_validate_result`, `_verify_output_maps_to_findings`)
  are wrapped in one `try/except Exception` (evaluator.py:351-387) that
  logs and returns `None` on ANY failure — network exception, malformed
  JSON, or a `_validate_result` `ValueError` for wrong-shaped output.
  **This means every provider-failure family (unavailable, raises,
  malformed JSON, internally-inconsistent shape) collapses to the same
  safe `None` return** — callers (`main.py`) already treat `None` as "no
  LLM explanation available" and fall back to
  `create_fallback_response`/deterministic-only findings. No special
  casing per exception type exists or is needed.
- `_validate_result` itself: requires 5 specific keys present, requires
  `summary_bullets`/`top_issues`/`possible_missing_sections` to be lists,
  and unconditionally force-overwrites `disclaimer`. It does NOT validate
  `overall_risk`'s value/type — because by the time it is called (from
  `evaluate()`, line 366-368), `result["overall_risk"]` has *already* been
  force-overwritten with the deterministic value one line earlier. A
  malformed `overall_risk` from the model can therefore never actually
  reach `_validate_result` in the real flow.

## 2. Document aggregation — `document_aggregation.py`

- `aggregate_document_state` reads three already-persisted inputs
  (`overall_risk`, `policy_decisions`, `interaction_decisions`) and a
  `mode` string. Prior to this phase (Phase F/G/H's fixes plus an
  in-session fix earlier this phase), any of these being `None` was
  handled; but a non-`None`, non-dict value for `policy_decisions`/
  `interaction_decisions` (e.g. a corrupted `EncryptedJSON` column
  decoding to a bare string, int, or list) was NOT — `(x or {}).items()`
  is truthy for any non-empty non-dict value, so `.items()` was called
  directly on it, raising `AttributeError`/`TypeError`. Reproduced
  directly, fixed this phase (see Result section).
- A dict entry's own `"state"` field being non-string (e.g. itself a dict)
  passed `isinstance(decision, dict)` but then crashed a `state in
  {...}` membership test with `TypeError: unhashable type`. Also fixed
  this phase.

## 3. Segment matching — `policy_enforcement._segment_matches_context`

- Already hardened (Phase G) against `NaN` silently satisfying a numeric
  bound. Not hardened against a non-numeric `deal_value` (e.g. a string
  from malformed contract metadata) — `deal_value < position.segment_deal_value_min`
  raises `TypeError: '<' not supported between instances of 'str' and 'float'`.
  Reproduced directly, fixed this phase.

## 4. `main.build_enhanced_issues`

- Already hardened (Phase C) against an unhashable/unrecognized `severity`
  value via `_severity_rank`'s `try/except TypeError` — confirmed still
  correct, no new defect found here this phase.

## 5. `policy_enforcement.evaluate_active_policies` — one-adapter isolation

- Already designed (requirement 11, confirmed correct in Phases A/D/E/H)
  to catch any exception from one clause type's `extract_fn`/`evaluate_fn`
  and record it as an isolated error outcome (`decision=None,
  error=f"{type(exc).__name__}"`), while every other clause type's
  evaluation proceeds from the same `active_positions` snapshot,
  unaffected. Verified directly this phase across all 12 adapters by
  patching one clause type's `extract_fn` to raise and confirming the
  other 11 still produce real decisions.

## 6. `interaction_engine_core.evaluate` — one-rule isolation

- Same isolation contract, one level up: one rule's `predicate` raising is
  caught and recorded as `EVALUATION_ERROR`, every other rule (from the
  same fixed `LAUNCH_CATALOG` list) still evaluates normally. Verified
  directly this phase across a spread of rule indices.

## 7. `main._document_state_for_contract` — dashboard/history read path

- Thin wrapper: reads three fields off a `Contract` row and calls
  `document_aggregation.aggregate_document_state`. Inherits that
  function's crash surface exactly — the Phase 2 fixes above (top-level
  non-dict payload, non-string state value) directly fix this path too,
  since it is the same function.
