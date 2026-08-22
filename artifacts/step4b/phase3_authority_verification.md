# Step 4B Phase 3 — Interaction Authority Invariant Verification

## Method

Empirically verified (not merely read) via `scripts/step4b_phase3_truth_tables.py`,
which constructs `PolicyDecision` fixtures directly (bypassing extraction,
per the design doc's own recommended benchmark methodology) and feeds them
through the REAL `interaction_engine_core.evaluate()` and the REAL 7
predicates in `interaction_rules.py`. 39 combinations across all 7 rules,
plus one full-catalog 5x determinism check. Full raw output:
`artifacts/step4b/phase3_truth_table_results.json`. Zero production code
changes made to produce this verification.

## Findings, A–J

**A. Required participant states.** Every rule requires ALL of its
`participating_clause_types` to have a `PolicyDecision` present with
`state` outside `{NOT_APPLICABLE, REQUIRES_REVIEW, EVALUATION_ERROR}` —
enforced once, centrally, by `_gate_participants`, not per-rule. Confirmed
empirically: every combination with a missing/NOT_APPLICABLE/
REQUIRES_REVIEW/EVALUATION_ERROR participant produced `INSUFFICIENT_FACTS`
for all 7 rules, with zero exceptions across 15 such combinations tested.

**B. Facts consumed.** `category_treatments[cat].treatment` (rules 1–5)
or `interaction_facts[key]` (rules 6–7, via the explicitly-registered
`INTERACTION_FACT_REGISTRY` extension). No rule reads any other field.

**C. Authoritative/verified.** Yes — both fact sources are themselves
adapter-computed, deterministic outputs (Step 4A architecture), never
semantic-only, never LLM-derived. `interaction_engine_core.py`/
`interaction_rules.py` import nothing from any `*_policy_engine` module's
extraction path, no LLM client, no `contract_text` parameter anywhere
(confirmed by import-level inspection in Phase 0).

**D. Participant state handling.** Empirically confirmed for every rule:
`NOT_APPLICABLE` → `INSUFFICIENT_FACTS`. `REQUIRES_REVIEW` →
`INSUFFICIENT_FACTS`. `EVALUATION_ERROR` → `INSUFFICIENT_FACTS`. Missing
entirely → `INSUFFICIENT_FACTS`. This codebase has no `NOT_ESTABLISHED`
or `CONFLICTING` PolicyDecision.state (those are Step 4A adapter-internal
concepts realized differently — see Finding on category-level ambiguity
below) — the closest analog, a per-category `treatment == "unresolved"`
on an otherwise-resolved decision, is handled by a DIFFERENT mechanism
(Rule 4), not by the generic decision-level gate, and was verified
separately (see G below).

**E. Can interaction evaluation infer/manufacture a missing fact?** No —
confirmed both by code inspection (`_gate_participants` returns `None`
for the whole `safe_decisions` dict, never a partial one; every rule
predicate does plain dict lookups against pre-gated decisions, no
defaulting, no `.get(x, some_guess)` pattern found in any of the 7
predicates) and empirically (every missing-participant case produced
`INSUFFICIENT_FACTS`, never a guessed `NOT_TRIGGERED` or a fired finding).

**F. Are UNKNOWN-like states ever treated as a known value?** No —
`interaction_facts.get(key)` returning `None` (unestablished) is checked
explicitly against `is not True` (rules 6–7) or against dict-membership
(`liability_ct.get(cat)` returning `None`, checked via `if not lt or not
it: return None`, rules 1/2/3/5) everywhere — confirmed empirically: every
"unestablished" (`None`/absent-key) interaction_facts case produced
`NOT_TRIGGERED`, never fired as if `False` or `True` were assumed.

**G. Fail-closed participant gating?** Yes, confirmed empirically with
zero exceptions across 15 gating-relevant test combinations.

**H. Ceiling enforcement — interaction never more certain than its
least-certain material participant?** Yes, structurally guaranteed by
`interaction_engine_core.evaluate()`'s own `ValueError` if a predicate
returns a state above its rule's declared `ceiling_state` (code-level
invariant, confirmed present, not merely tested) — and separately,
gating means an unresolved participant NEVER reaches a predicate at all,
so "ceiling above least-certain participant" cannot occur through that
path either.

**I. Does evidence from both participants survive?** Yes — confirmed
empirically: `evidence_present=True` (both participating
`controlling_provision` dicts present in `participating_provisions`) on
every fired/NOT_TRIGGERED result tested. For `INSUFFICIENT_FACTS`
results, `participating_provisions` includes whatever evidence WAS
available (the resolved participant's own `controlling_provision`) plus
`None` for the missing one — confirmed via direct code read of
`evaluate()`'s `INSUFFICIENT_FACTS` branch, which builds
`participating_provisions` from `decisions[ct].controlling_provision if ct
in decisions else None` for EVERY declared participating clause type, not
just the safe ones — so evidence for a partially-available interaction is
never silently dropped.

**J. Does directionality/ownership survive?** Yes for Rule 6 (the only
genuinely directional rule in the launch catalog) — verified by tracing
`termination_policy_engine.py`'s own `category_treatments` construction
(lines ~715–725): built EXCLUSIVELY from `their_rights` (rights the
COUNTERPARTY holds against us, resolved via `holder_side` vs. the
playbook's configured `contract_side`, itself Step-4A adapter logic, not
part of this remediation's scope). A right WE hold is never included in
`category_treatments`, so Rule 6's `non_payment: immediate` check can
never fire on our own side's right by construction — directionality is
resolved upstream, correctly, before the interaction layer ever sees the
fact. Rules 1–5, 7 are non-directional category/presence matches by
design (no party-role comparison is part of their predicate at all), so
directionality is not applicable to them.

## Presence-only-substitute discrepancy — resolved

**Conclusion: (E) — recommended in the design doc, not implemented, and
correctly excluded from the current 7-rule launch catalog. Not a code
gap requiring action.**

Evidence: `interaction_rules.py` contains no reference to
`confidentiality_of_personal_data` or any Confidentiality×Data-Security
predicate (confirmed by direct grep — zero matches). What DOES exist is
an entirely different, WITHIN-adapter mechanism:
`data_security_policy_engine.py`'s own `evaluate_data_security_policy`
checks its own extracted `facts.confidentiality_of_personal_data` against
a playbook-configured `require_confidentiality_of_personal_data` boolean
(`data_security_policy_engine.py:763`) — this is a single-clause policy
requirement internal to the Data Security adapter, not a cross-policy
interaction, and it answers a narrower, different question ("does Data
Security's OWN text affirmatively state confidentiality of personal
data") than the design doc's recommended substitute ("does a SEPARATE
Confidentiality clause exist at all"). The design doc's own §3.10 summary
table explicitly scopes "V1 launch catalog: rules 1-7" to the 7 rules
that are, in fact, exactly `interaction_rules.LAUNCH_CATALOG`'s 7 rules —
the presence-only substitute for the excluded pair (design doc's "rule
11") was recommended in the body text (§3.5) but never promoted into the
"rules 1-7" launch set the same document's own summary commits to
shipping. This is documentation drift in the design doc (a recommendation
not carried through to its own summary table), not a missing production
behavior — production correctly implements what its own governing
document actually committed to shipping. No remediation needed.

## Adversarial micro-benchmark

`benchmarks/step4b_phase3_authority_microbenchmark.py` (70 cases, 10 per
rule) + runner `scripts/step4b_run_phase3_microbenchmark.py`. Attacks:
missing participant, unresolved participant, category-level ambiguity
(the CONFLICTING-analog), false applicability, insufficient evidence,
duplicated participant/category entries, one-safe-one-unsafe input,
uncertainty laundering, wrong participant key.

**Result: 70/70 correct (100%) after one disclosed GTD correction.**

- `false_authoritative_interaction = 0` — PASS
- `uncertainty_laundering = 0` — PASS
- `missing_evidence_interaction = 0` — PASS
- Wrong-direction / wrong-owner interaction: 0 by construction — every
  directional case (Rule 6) exercised the adapter-scoped `their_rights`
  boundary already verified in Finding J; no case produced a
  counterparty-attributed finding from an our-side-only fact.
- Evidence-provenance loss: 0 — `evidence_present` (both available
  participating `controlling_provision`s survive into the result) was
  checked on every actionable-state row across all 70 cases.

**One GTD correction, disclosed**: `mb-r1-06` (duplicated category
entries) was originally predeclared `expected_state=ESCALATE` with a note
claiming "last duplicate wins," but the actual last-wins value
(`within_general_cap`) does NOT satisfy the rule's trigger condition
(`uncapped`/`super_cap`) — the case's own predeclared expectation
contradicted its own documented reasoning. Verified directly via
`_by_category`'s dict-comprehension behavior before correcting to
`NOT_TRIGGERED`. This was a corpus-authoring error, not a production
defect, and the mismatch was in the SAFE direction (engine correctly
declined to fire; my ground truth wrongly expected it to). Full
before/after: `git log` on `benchmarks/step4b_phase3_authority_microbenchmark.py`.

## Regression controls

- Existing 54-case interaction benchmark (`benchmarks/run_interaction_corpus.py`
  via `benchmarks/run_interaction_benchmark.py`): still 100%, all 4 release
  gates PASS, determinism 100% — unchanged, not rewritten, not replaced
  (per explicit instruction).
- `tests/test_interaction_engine_core.py` + `tests/test_interaction_benchmark_gate.py`:
  36/36 passed.
- `tests/test_interaction_enforcement.py`: could not collect in this
  sandbox (`ModuleNotFoundError: _cffi_backend`, a pyo3/cffi native-extension
  issue) — this is the same class of pre-existing, environment-level
  collection failure already confirmed unrelated to this session's work
  during Step 4A.11 (dotenv/httpx2 missing deps caused identical
  collection errors, confirmed via git-stash A/B comparison then). Not
  re-verified via stash comparison this turn since no production file has
  been touched in Step 4B at all yet — the error is structurally identical
  in kind (missing native/optional dependency at import time, not a test
  assertion failure) to the already-characterized class.

## Phase 3 conclusion

**No architectural blocker found.** All three of Phase 3's own gates
(dev benchmark, presence-only-substitute discrepancy, 70-case
micro-benchmark) are clean. Proceeding directly to Phase 4 (210+ case
development interaction benchmark) per the explicit "do not ask for
permission between phases" instruction.
