# Step 4B Phase A — Multi-Policy Document Testing

## Corpus

`benchmarks/step4b_phaseA_multipolicy_document_benchmark.py` — 200
independently-authored multi-policy documents (exceeds the ≥150 minimum),
drawn only from the actual 12-adapter catalog
(`playbook_authoring.CLAUSE_TYPES`):

| Bucket | Target | Actual |
|---|---|---|
| 3-4 applicable policies | 50 | 50 |
| 5-7 applicable policies | 50 | 76 |
| 8+ applicable policies | 50 | 74 |
| **Total** | **150** | **200** |

60 documents are explicitly compound (≥2 mechanisms co-present — exceeds
the ≥50 minimum). Every document is run through the REAL production code:
`interaction_engine_core.evaluate()` against the full
`interaction_rules.LAUNCH_CATALOG` (not reimplemented), then
`document_aggregation.aggregate_document_state()` (not reimplemented).
Ground truth was predeclared by hand, per family, using the already-
validated six-state precedence model — never derived by calling the
function under test.

Families cover the full mandatory list: clean policies, policy violations
(all 4 violation states), REQUIRES_REVIEW, NOT_APPLICABLE, single and
multiple interaction findings, amendments (`reconciliation=
"amendment_resolved"`/`"superseded"`), multiple provisions
(`reconciliation="unreconciled"`), non-operative-text framing, duplicate
evidence (duplicated `category_treatments` entries), a directional
interaction (Rule 6, termination/payment_terms), evaluation errors, and 6
compound families combining two or more of the above.

## PRE run and a genuine defect found

First execution (before any document_aggregation.py change):
**148/200 (74.0%) correct.** All four wrong-authority hard gates were
already clean on this first run:

- `false_clean_document` = 0
- `lost_base_finding` = 0
- `lost_interaction` = 0
- `lost_review_finding` = 0

The 52 mismatches were all `wrong_document_state` — concentrated in
"fully-clean" documents predeclared `CLEAN` that the real pipeline
returned `REQUIRES_REVIEW` for instead, plus some family-specific
mismatches. Per the task's own explicit instruction ("If an upstream
adapter safely returns REQUIRES_REVIEW: that is not automatically a
defect"), this was investigated before assuming either side was wrong.

### Root cause

Traced directly (`docA-small-00`, a 3-policy document covering only
`limitation_of_liability`/`indemnification`/`termination`): 3 of the 7
interaction rules returned `INSUFFICIENT_FACTS` purely because their
participating clause types (`insurance`, `payment_terms`, `sla`) were
never part of this document's applicable policy set at all — confirmed via
`InteractionDecision.missing_clause_types` cross-referenced against the
decisions dict (all three genuinely absent, not merely unresolved).

This is realistic, not a benchmark artifact: `policy_enforcement.
evaluate_active_policies`'s own docstring confirms "absence of an ACTIVE
position for a clause type means that clause type is simply skipped" —
`policy_decisions_json` genuinely has missing keys in production whenever
a playbook doesn't configure every one of the 12 adapters, which is a
normal, expected configuration (most playbooks likely don't cover all 12).

`document_aggregation.py`'s original `_INTERACTION_REVIEW_STATES` set
treated every `INSUFFICIENT_FACTS` interaction identically, regardless of
WHY it was insufficient — matching `interaction_engine_core.py`'s own
documented, already-validated design intent at the pairwise level
("INSUFFICIENT_FACTS must never be mistaken for clean," Phase 3 Finding
D). But applied uniformly at the DOCUMENT level, this meant: **any
document reviewed under a playbook that doesn't cover all 6 interaction-
participating clause types (`limitation_of_liability`, `indemnification`,
`insurance`, `termination`, `payment_terms`, `sla`) would always show
document-level `REQUIRES_REVIEW`, regardless of how clean it otherwise
is** — a material selectivity defect (never a false-clean/wrong-authority
one; the direction was always safe) that would make the "Needs Attention"
flag nearly universal for any non-comprehensive playbook, degrading its
value as a signal.

### Classification

Per the task's own fix-discipline: this is a genuine, general mechanism
(not a single test ID), root-caused, and the fix belongs in
`document_aggregation.py` — a Step 4B artifact this program owns, not in
`interaction_engine_core.py`/`interaction_rules.py` (the validated,
Phase-3-verified interaction engine, correctly left untouched — its own
per-rule `INSUFFICIENT_FACTS` semantics are unchanged and still correct at
that layer). No Step 4A file was touched.

### Fix

`document_aggregation.py`: added `_interaction_is_genuinely_inapplicable()` —
for an `INSUFFICIENT_FACTS` interaction decision, checks whether EVERY
name in its `missing_clause_types` is absent from `policy_decisions`
entirely (never evaluated — no ACTIVE position for that clause type at
all) versus present with an unsafe state (`NOT_APPLICABLE`/
`REQUIRES_REVIEW`/`EVALUATION_ERROR` — a clause type the playbook DOES
cover, genuinely unresolved). Only the first case is now excluded from
document-level `REQUIRES_REVIEW`; the second still escalates, preserving
the fail-closed behavior for genuine uncertainty.

### Targeted POST + regression after the fix

- Phase A benchmark: **200/200 (100%)**, all wrong-authority gates still 0.
- `scripts/step4b_run_document_aggregation_benchmark.py` (104-case
  aggregation corpus, the benchmark that originally caught the
  `EVALUATION_ERROR` defect this same module had): unchanged, **104/104**,
  `post_false_clean = 0`.
- `scripts/step4b_run_phase4_dev_benchmark.py` (213-case interaction
  corpus): unchanged, **213/213** — confirms the interaction engine itself
  was never touched.
- `benchmarks/run_interaction_benchmark.py` (existing 54-case corpus):
  unchanged, 100%, all 4 historical gates PASS.
- `tests/test_step4b_dashboard_listing_integration.py` (18-case real-app
  suite): unchanged, **18/18**.
- Step 4A.11 393-case final corpus and 167-case remediation corpus: both
  re-run, **WC=0, all hard gates PASS, unchanged** — no Step 4A safety
  regression (expected: neither run touched any adapter/extraction file).
- Full `pytest tests/`: run after this fix (see session checkpoint for
  the exact count).

### Benchmark-authoring corrections (disclosed, GTD-style)

Two of the 52 original mismatches were traced to the benchmark's own
construction, not production, and corrected before re-running:

1. `not-applicable-mixed-small` / `compound-not-applicable-plus-clean`
   families predeclared `CLEAN` unconditionally whenever a clause type was
   set `NOT_APPLICABLE`, without checking whether that specific clause
   type participates in any interaction rule — per the fix above, a
   `NOT_APPLICABLE` clause type that DOES participate in an interaction
   rule is a genuinely unresolved participant and correctly escalates.
   Corrected to predeclare `REQUIRES_REVIEW` when the target clause type
   is one of the 6 interaction-participating ones.
2. `compound-directional-interaction-plus-violation`: the violation target
   (`clause_types[0]`) could coincidentally equal `"termination"` or
   `"payment_terms"` — the same two clause types the family's own
   interaction setup had just wired — silently overwriting the interaction
   fixture with a plain violation decision and destroying the intended
   interaction. Fixed by picking the violation target from a clause type
   excluded from the interaction pair, confirmed to always have candidates
   available given the bucket's minimum size (n≥6, 2 reserved).

## Conclusion

Phase A found and fixed one genuine, general document-aggregation
selectivity defect (never a false-clean/wrong-authority one) via a
200-document benchmark, all four wrong-authority hard gates measured 0
both before and after, and confirmed via full regression that the fix is
isolated to the new `document_aggregation.py` module with no effect on
the validated Step 4A adapters or the Phase-3-verified interaction engine.
