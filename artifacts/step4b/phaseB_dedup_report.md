# Step 4B Phase B — Deduplication/Suppression Development Benchmark

## Method

Read-only inventory first (`artifacts/step4b/phaseB_deduplication_inventory.md`),
identifying `main.build_enhanced_issues` as the one real suppression/
merge/dedup point in the findings-display pipeline. Benchmark
(`benchmarks/step4b_phaseB_deduplication_benchmark.py`, 108 cases, exceeds
the ≥100 minimum) calls that production function directly — never a
reimplementation — with constructed `findings_dict` lists shaped exactly
like the real dicts `rules_engine.analyze()`,
`policy_enforcement._finding_from_decision`, and
`interaction_enforcement._finding_from_interaction_decision` produce.
Ground truth is a predeclared expected output count per case, covering all
14 named attack families.

## PRE (production, unmodified)

**48/108 correct.** All 60 failures were `materially_distinct_finding_suppression`
(`0` `duplicate_finding_leakage`), concentrated in exactly the 4 families
that construct two genuinely distinct occurrences of the same `rule_id`:
`same-policy-different-clauses` (0/8), `same-policy-different-clauses-volume`
(0/40), `same-policy-repeated-in-amendment` (0/6),
`superseded-plus-operative-clause` (0/6). Every other family — where the
attack targets a DIFFERENT rule_id/interaction_id pair, or a true exact
duplicate — was already correct pre-fix.

## Root cause

`build_enhanced_issues`'s dedup key was `rule_id` alone
(`seen_rule_ids = set()`), silently collapsing two genuinely distinct
findings from the same rule at two different clause locations —
contradicting `rules_engine.analyze()`'s own documented internal contract,
which deliberately keys its dedup on `(rule_id, clause_number)` precisely
to preserve this distinction. Reproduced directly against production
before writing any fix (see the inventory doc).

## Fix

`main.py`, `build_enhanced_issues`: dedup key changed from `rule_id` to
`(rule_id, start_index, end_index, clause_number)`. General, not a
per-case patch — verified to correctly preserve `policy_decision`/
`interaction_decision` synthetic findings' existing (already-correct)
uniqueness, since each is one-per-clause-type/interaction-id-per-review by
construction regardless of the added location fields.

## POST

**108/108 (100%)**, both hard gates PASS:
- `materially_distinct_finding_suppression = 0`
- `duplicate_finding_leakage = 0`

## Regression

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed** (run after
  this fix, before the benchmark existed — see session record; re-run
  after the benchmark below for a final confirmation).
- Phase A 200-document benchmark: unaffected (does not call
  `build_enhanced_issues`) — not re-run for this specific fix, verified by
  code-path inspection (Phase A only exercises `interaction_engine_core`/
  `document_aggregation`).
- 104-case aggregation, 213-case interaction, 54-case historical, 18-case
  real-app integration suites: unaffected by this fix (none call
  `build_enhanced_issues`); re-verified together with the full pytest run
  in this session's checkpoint.
- Step 4A.11 393-case and 167-case corpora: unaffected (neither exercises
  `main.py`'s display layer; both operate directly against the adapter
  layer) — not re-run for this specific fix since no adapter/extraction
  file was touched.

## Conclusion

Phase B found and fixed one genuine, general suppression defect (never a
"wrong-authority" one — the two findings were both correctly *derived*,
only one was silently hidden from display) via a targeted, production-
code-calling benchmark. Fix is minimal (one line, one dedup key), general
(not per-ID), and does not touch `rules_engine.py`, any adapter, or the
interaction engine.
