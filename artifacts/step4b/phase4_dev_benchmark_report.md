# Step 4B Phase 4 — 210+ Case Development Interaction Benchmark, and Phase 5

## Corpus

`benchmarks/step4b_phase4_interaction_dev_benchmark.py` — 213 unique cases,
independently authored (fresh vocabulary/structure, not copied from
`benchmarks/interaction_corpus.py`'s 54 cases or from the Phase 3 70-case
micro-benchmark). Fixture-based (`PolicyDecision` objects constructed
directly), per the design doc's own recommended methodology, isolating
interaction-predicate correctness from adapter extraction quirks —
identical rationale to Phase 3.

Rule-level breakdown (unique cases per rule; a few cases target only one
rule's evaluation even when the fixture happens to contain data another
rule's predicate would also match — reported per-rule, not inflated):

| Rule | Cases |
|---|---|
| IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY | 30 |
| IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH | 30 |
| IX_INDEMNITY_WITHIN_GENERAL_CAP | 30 |
| IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY | 30 |
| IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE | 30 |
| IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING | 33 |
| IX_SLA_PAYMENT_CREDIT_DEPENDENCY | 30 |
| **Total unique cases / rule-level evaluations** | **213 / 213** |

Each case is evaluated against exactly one rule (its own `interaction_id`),
so unique-case count and rule-level-evaluation count are identical here —
no case was counted toward more than one rule's total. Several cases
(`compound-with-r1`, `compound-noise-category`, `dev-r3-mixed-scope`, etc.)
deliberately include facts that WOULD also fire a different rule if
evaluated against it; this is noted explicitly in-case and confirmed by
manual trace, not assumed.

### Mandatory case families covered (of the 20 named in the task)

Directly exercised across the 7 rules: both-acceptable (1), violation-only
either side (2/3), both-violations-independent (4), problematic-together
(5), one-established+one-unresolved (6), one-established+one-conflicting
via category-level "unresolved" (7, Rule 4's own mechanism), one
NOT_APPLICABLE (8), missing participant (9), direction reversal (10, Rule
6's directional cases), role reversal (11, category-mismatch /
wrong-fact-key cases across rules), multiple provisions for Policy A/B (12,
13, via `reconciliation="unreconciled"`/multi-category-merge cases),
amendments (14, `reconciliation="amendment_resolved"`/`"superseded"`),
cross-reference (15), conditional applicability (16), conflicting
definitions (17, category-ambiguity + explicit `"unresolved"`-treatment
cases outside Rule 4), non-operative text (18), duplicate evidence (19,
duplicated `category_treatments` entries — each one traced against the
real `_by_category` dict-comprehension last-wins semantics before
predeclaring, per the Phase 3 `mb-r1-06` lesson), compound interaction (20).

Ground truth for every case distinguishes "no interaction exists"
(`NOT_TRIGGERED` — participants resolved, facts established, predicate's
own condition genuinely not met) from "interaction cannot be safely
determined" (`INSUFFICIENT_FACTS` — a participant is missing/unresolved/
erroring, or its own material fact is unestablished) as two structurally
distinct expected values, never conflated.

### `END_TO_END_CASES`

Declared as an empty list and deliberately left empty. End-to-end wiring
(contract text → adapters → `apply_interaction_rules`) is exercised by
`tests/test_interaction_enforcement.py` (native-extension collection
failure in this sandbox, pre-existing and already characterized in Phase 3
— see `phase3_authority_verification.md`) and by the persistence/HTTP-layer
tests cited in the Phase 4 regression run below. Building a second,
redundant end-to-end harness inside this DEVELOPMENT fixture corpus would
not add coverage beyond what those existing tests already assert, and Phase
4's own stated purpose is interaction-predicate correctness, not wiring —
so this was left unbuilt rather than padded with low-value cases. Disclosed
explicitly rather than silently dropped.

## PRE metrics (production interaction_engine_core/interaction_rules, unmodified)

Runner: `scripts/step4b_run_phase4_dev_benchmark.py`. Raw output:
`artifacts/step4b/phase4_dev_benchmark_results.json`.

- **Total: 213/213 correct (100.0%)**
- false_interaction = 0
- missed_interaction = 0
- false_authoritative_interaction = 0
- uncertainty_laundering = 0
- wrong_direction = 0
- wrong_ownership = 0
- wrong_participant = 0
- evidence_provenance_failure = 0
- duplicate_interaction = 0 (duplicated category-entry cases correctly
  resolved to whatever the real last-wins mechanism produces — verified
  against the actual mechanism before predeclaring expected values, not
  assumed)
- suppressed_interaction = 0
- Other mismatches (uncategorized): 0

By-rule: all 7 rules at 100% (30/30, 30/30, 30/30, 30/30, 30/30, 33/33, 30/30).

## Regression controls (Phase 4)

- Existing 54-case interaction benchmark (`benchmarks/run_interaction_corpus.py`
  via `benchmarks/run_interaction_benchmark.py`): still 100%, all 4 release
  gates PASS, determinism 100% — unchanged, not rewritten, not touched.
- No production file was modified to produce this PRE result.

## Phase 5 — fix only proven general defects

**No defects were found in Phase 4.** Zero cases across all measured
categories (CA/CR/FE/WC-equivalents and all 10 named safety metrics) on the
first, unmodified execution against production. There is therefore nothing
to cluster by root cause, nothing to fix, and no production file was
touched in Phase 4 or Phase 5. This is consistent with — not merely
assumed from — the Phase 3 finding of "no architectural blocker": Phase 3
verified the authority invariant abstractly across combinations; Phase 4
verified the same 7 predicates concretely across 213 independently-authored
cases spanning the 20 mandatory families, and found the same result.

Per the explicit CRITICAL BOUNDARY instruction, no Step 4A adapter code was
touched (none needed to be — Phase 4 is fixture-based and never called
adapter extraction).

## Conclusion

Phase 4 clean at 213/213 (100%), zero unsafe-classification defects across
all 10 measured metrics, all 7 rules individually clean, all 20 mandatory
case families exercised. Phase 5 requires no action. Proceeding to the
document aggregation specification and the `overall_risk` remediation work
per the explicit phase ordering.
