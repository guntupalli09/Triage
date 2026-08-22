# Step 4B — Document Aggregation Specification, Dev Benchmark, and Bounded Function

## Scope of this increment

Per the explicit phase ordering ("only after the interaction layer is
characterized/hardened, return to the Phase 1 `overall_risk` finding...
construct a document aggregation specification first... build a >=100-case
development benchmark with PRE-measurement before any aggregation
changes... then implement bounded aggregation remediation"), this
increment covers:

1. `artifacts/step4b/document_aggregation_spec.md` — the specification,
   including the required investigation of `POLICY_ENFORCEMENT_MODE`
   shadow/cutover behavior (traced directly in `policy_enforcement.py`,
   not assumed).
2. `document_aggregation.py` — the bounded aggregation function
   (`aggregate_document_state`), a pure function over already-persisted
   fields.
3. `benchmarks/step4b_document_aggregation_dev_benchmark.py` — 104
   independently-authored cases.
4. `scripts/step4b_run_document_aggregation_benchmark.py` — PRE/POST
   measurement.

**Explicitly NOT done in this increment** (see spec §4 Non-Goals, and the
continuation note at the end of this report): wiring `aggregate_document_state`
into `main.py`'s dashboard count, `/history` filter, or any persisted
column. No production file (`main.py`, `models.py`, any `*_policy_engine.py`,
`interaction_*.py`) was modified. `document_aggregation.py` is a new,
additive module — nothing existing imports or calls it yet.

## PRE measurement (production's actual current behavior)

Production's dashboard high-risk count (`main.py:1203`) and `/history` risk
filter (`main.py:1231`) both reduce to exactly one boolean:
`Contract.overall_risk == "high"`. Measured against the 104-case benchmark's
predeclared ground truth (which of the 6 aggregation states each case
represents):

**false_clean = 71/104 (68.3%)** — cases where a material policy violation,
critical interaction, unresolved review item, or unresolved cutover
configuration exists, but `overall_risk == "high"` alone would not flag it.
Broken down by family in `artifacts/step4b/document_aggregation_benchmark_results.json`
— every family that constructs a policy/interaction finding with
`overall_risk` set to `"low"` or `"medium"` (the overwhelming majority of
real-world cases, since most legacy pattern-match risk is not `"high"`)
contributes to this count. This number is the concrete size of the Phase 1
finding, not an estimate.

This is expected and consistent with Phase 1/§2 of the spec: production
was never designed to read `policy_decisions_json`/`interaction_decisions_json`
at these surfaces, so of course it does not.

## POST measurement (new function's own correctness)

First run surfaced one genuine defect in the new module (not production
code — this module was written this session and had not yet been
executed against any benchmark): `_POLICY_REVIEW_STATES` omitted
`EVALUATION_ERROR`, so a policy decision that failed to evaluate
(`agg-policy-evaluation-error-*`, 3 cases) was silently treated as clean
rather than surfaced as `REQUIRES_REVIEW`. This is exactly the kind of
"uncertainty disappearing during aggregation" the task's core invariant
warns against, caught by the benchmark's negative-control case for that
exact scenario before this module was used anywhere. Fixed by adding
`EVALUATION_ERROR` to `_POLICY_REVIEW_STATES` (`document_aggregation.py`).
Re-run: **104/104 correct (100%), post_false_clean = 0** — hard gate PASS.

This defect-then-fix cycle happened entirely within this session's own new,
unwired module, before any locked/frozen validation — it is standard
development iteration, not a violation of the "no tuning after execution"
discipline (which applies to a corpus that has already been locked and
executed once as a final validation instrument; this 104-case corpus is
explicitly DEVELOPMENT evidence per the task's own framing and may be
iterated against).

## Mode investigation summary (full detail in the spec, §2)

- `DEFAULT_MODE = "shadow"`. In shadow AND legacy modes,
  `apply_policies_for_review` never calls the 12-adapter layer or the
  Interaction Engine at all — `interaction_decisions` is unconditionally
  `None`, and `policy_decisions` is always the single legacy liability-only
  decision. Only cutover invokes `apply_active_policies` +
  `interaction_enforcement.apply_interaction_rules`.
- The false-clean gap measured above is therefore only reachable in
  cutover mode for the interaction-layer and multi-adapter-layer families;
  the benchmark's `shadow-mode`/`legacy-mode` family (10 cases) confirms
  the new function's behavior is correctly constrained to what shadow mode
  can actually produce (single legacy liability decision only — still
  correctly flags a violation there, per `agg-shadow-legacy-liability-violation`).
- No change to `DEFAULT_MODE` was made or is recommended by this work.
- A pre-existing, unrelated UX safeguard (`is_policy_authoritative()` /
  `enforcement_disclosure()`, built for a prior "P0-2" finding) already
  governs whether a Playbook LOOKS like it's deciding a review — traced
  and confirmed this Step 4B work does not need to touch or duplicate it.

## Dashboard/listing safety family

`dashboard-listing-safety` (10 cases: 7 policy-violation-state variants +
3 interaction-ESCALATE variants, all at `overall_risk == "low"`) is a
direct test of the exact scenario named in the task: "a contract cannot
disappear from every user-visible attention queue merely because legacy
overall_risk was low." The new function correctly reports
`HAS_POLICY_VIOLATION`/`HAS_CRITICAL_INTERACTION` on all 10 (10/10). This
proves the FUNCTION's correctness on this scenario — it does not yet prove
the DASHBOARD is safe, since the function is not wired into `main.py` yet
(see below).

## Conclusion and required continuation point

The specification, mode investigation, and bounded aggregation function
are complete and verified: PRE=71/104 false-clean under today's actual
production logic, POST=104/104 correct with 0 false-clean under the new
function, one genuine defect found and fixed during development (disclosed
above), all before any production wiring.

**What remains, and is explicitly NOT claimed as done:** wiring
`aggregate_document_state` into the actual dashboard count query, the
`/history` filter, and any other surface that currently reads
`Contract.overall_risk` alone for attention-queue purposes. That step
requires either (a) computing the aggregation at read time in each of
those `main.py` handlers (no schema change, but touches live query/handler
code and needs its own request-level testing), or (b) persisting the
aggregated state as a new column (a schema migration, a larger and more
reversible-with-more-effort change). Neither has been done or decided in
this increment — this is the exact continuation point for the next Step
4B session. No verdict on Step 4B's dashboard/listing safety gate should
be treated as satisfied until that wiring exists and is itself tested
against a running dashboard, per the task's explicit instruction not to
assume UI behavior from backend state alone.
