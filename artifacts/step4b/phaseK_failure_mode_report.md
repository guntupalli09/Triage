# Step 4B Phase K — Failure-Mode / Dependency-Failure Report

## Method

Read-only trace first (`phaseK_failure_mode_trace.md`). Benchmark
(`benchmarks/step4b_phaseK_failure_mode_benchmark.py`, **130 cases**,
exceeds the ≥120 minimum) attacks the real production functions directly
— never a reimplementation — through the highest realistic boundary for
each: `evaluator.LLMEvaluator.evaluate`/`_validate_result` with a fake
OpenAI client (unavailable / raising / malformed JSON / contradictory
shape), `document_aggregation.aggregate_document_state` with corrupted
decision payloads, `policy_enforcement._segment_matches_context` with
malformed `deal_value`, `main.build_enhanced_issues` with malformed
severities, `policy_enforcement.evaluate_active_policies` and
`interaction_engine_core.evaluate` with one collaborator patched to raise
(the real isolation-boundary code under test, unpatched), and
`main._document_state_for_contract` with malformed/incomplete persisted
`Contract` fields.

Runner: `scripts/step4b_run_phaseK_failure_mode_benchmark.py`.

## PRE (before this phase's fixes)

124/130 correct. 6 mismatches, all found via direct execution:

1. **Genuine production defect** — `document_aggregation.aggregate_document_state`
   (and its helpers) crashed with `AttributeError`/`TypeError` when
   `policy_decisions`/`interaction_decisions` was present but not a dict
   (e.g. a corrupted `EncryptedJSON` row decoding to a string/int/list),
   because `(x or {}).items()` is truthy for any non-empty non-dict value.
   3 cases (`history-malformed-record-3`, `-4`, `-extra-2`) reproduced
   this directly (the third via a dict-shaped `state` value crashing a
   `state in {...}` membership test — unhashable type).
2. **Genuine production defect** — `policy_enforcement._segment_matches_context`
   raised `TypeError` on a non-numeric (string) `deal_value`
   (`config-malformed-deal-value-4`): `deal_value < min` is not defined
   between `str` and `float`. The existing NaN guard (Phase G) only
   covered the numeric-but-NaN case, not the non-numeric case.
3. **Benchmark-authoring mistake** — `config-malformed-deal-value-1`
   wrongly expected `deal_value=inf` against a min-only bound (100000, no
   max) to fail the bound. Infinity is a real, comparable number that
   genuinely is `>= 100000`; this is not corrupt/unusable input, so
   matching is correct. Corrected the benchmark's expectation.
4. **Benchmark-authoring mistake** — `provider-contradictory-output-extra-0`
   wrongly tested `_validate_result` in isolation against a malformed
   `overall_risk` value. In the real `evaluate()` flow,
   `result["overall_risk"]` is unconditionally overwritten with the
   deterministic value one line *before* `_validate_result` is called
   ("never let model override computed risk") — so `_validate_result`
   structurally never sees a model-supplied `overall_risk` and correctly
   does not validate it. Corrected the benchmark's expectation.

## Fixes applied (production)

- **`document_aggregation.py`**: added `_safe_entries()` (routes every
  `.items()` call through an `isinstance(x, dict)` check, degrading a
  malformed top-level container to "no entries" rather than crashing);
  hardened `_state_of()` to only ever return a `str` state (a non-string
  `"state"` value now safely resolves to "not a recognized state" instead
  of crashing a later membership test); extended `_malformed_reasons()` to
  flag both a malformed top-level container AND a dict entry whose
  `"state"` value isn't a string — both still surface as a
  `REQUIRES_REVIEW` reason, never silently CLEAN.
- **`policy_enforcement.py`**: `_segment_matches_context` now treats any
  non-numeric (and non-`bool`) `deal_value` as "unusable" using the exact
  same fail-closed branch already used for `NaN` and `None`, instead of
  letting `<`/`>` raise `TypeError`.

## POST

**130/130 correct.** All 4 hard gates PASS:

- `dependency_failure_crashes_application = 0`
- `dependency_failure_becomes_false_clean = 0`
- `unhandled_exception_in_benchmark_harness = 0`
- `single_component_failure_not_isolated = 0`

## Regression

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed** (unchanged).
- Re-ran all prior Step 4B benchmarks: Phase A (200/200), Phase D
  (158/158), Phase E (150/150), document-aggregation (104/104), Phase F
  (174/174, all 13 hard gates PASS), Phase G (191/191, all 8 hard gates
  PASS), Phase H (210 scenarios / 561 executions, all 10 hard gates
  PASS), Phase I (150/150, all 4 hard gates PASS), Phase J (158/158,
  Layer 2's 4 hard gates PASS) — all unchanged. (Phase F/G/H's persistent
  sqlite fixture files from earlier phases had to be deleted before
  re-running in this same session — reusing them without deletion caused
  a `UNIQUE constraint failed: users.email` test-harness artifact, not a
  production regression; confirmed by a clean re-run.)

## Conclusion

Every dependency-failure family traced in `phaseK_failure_mode_trace.md`
(explanation-provider unavailable/raising/malformed/contradictory,
corrupted persisted policy/interaction state, malformed segment metadata,
malformed severity, one-adapter-raises, one-interaction-rule-raises,
malformed/incomplete history records) now degrades safely: never a crash,
never a false CLEAN, and single-component failures remain correctly
isolated from unrelated clause types/rules. Two genuine defects found and
fixed with a general root-cause mechanism (not per-case patches); two
benchmark-authoring mistakes found and corrected, disclosed above.
