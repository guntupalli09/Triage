# Step 4A.10.3 — Obligation Attribution Generalization: Final Report

## Executive verdict

**MORE HARDENING REQUIRED. Step 4A.11 is NOT authorized.**

The re-architecture materially improved false-symmetry (FS) on the
already-seen Step 4A.10.2 corpus during development (126/126 → 52/126,
a 66% reduction, used only as regression evidence). But on the
genuinely fresh, frozen, never-before-seen Step 4A.10.3 corpus, FS is
**58/116 asymmetric cases (50%)**. The fail-closed invariant the user
asked for is implemented and verified working exactly as designed —
but its own trigger condition (`value_asymmetry OR cue_present`) is
gated by `_DIFFERENTIATING_QUALIFIER_RE`, a closed cue-word list, which
this fresh corpus's differentiation phrasing largely does not match.
**The same closed-vocabulary anti-pattern this step set out to
eliminate at the discovery layer re-appeared one level down, at the
fail-closed trigger layer.** This is disclosed honestly rather than
patched with more phrases, per the standing anti-patch rule.

## What was built

1. **Discovery generalization**: `_ROLE_ATTRIBUTION_RE`'s closed
   noun/verb vocabulary gate was replaced by `_NAMED_ROLE_MENTION_RE`,
   a maximally general bare-role-name match (no verb/noun anchor at
   all), guarded by `_DOCUMENT_STRUCTURE_WORDS` (heading/section-noun
   stoplist) and by a mutual-reciprocal-structure gate
   (`len(distinct_roles) >= 3 or _MUTUAL_RECIPROCAL_RE.search(window)`)
   so the mechanism never misapplies itself to an ordinary
   single-directional "X shall indemnify Y" obligation.
2. **Fail-closed invariant**: when ≥2 distinct roles are attributed
   something in a genuinely mutual/reciprocal window, and snapshot
   comparison finds no concrete difference, the result is symmetric
   **only if** neither `value_asymmetry` (one role's snapshot has an
   establishable value, the other's doesn't) nor `cue_present`
   (`_DIFFERENTIATING_QUALIFIER_RE` matches the window) holds — subject
   to an explicit `_EQUAL_TREATMENT_CUE_RE` escape hatch when the
   drafter states equivalence outright. Otherwise the result is an
   unresolved differentiation reason, never a clean "symmetric".

Both pieces are exactly what the user asked for, and both are
demonstrably real: the discovery generalization alone recovered 7 of
12 dimension families on the 4A.10.2 dev-replay corpus, and the
fail-closed invariant is what prevents CS/CR from occurring on the new
corpus's `defense_control`/`monetary_treatment`/etc. FS cases — those
cases land on FS (verified obligation extracted, `asymmetry_reasons`
empty), not FA, confirming the mechanism runs but the trigger doesn't
fire, rather than the mechanism not running at all.

## Frozen fresh-corpus results (first and only pass, no tuning after seeing results)

Corpus: `benchmarks/step4a10_3_fresh_independent_corpus.json`, 182
cases, sha256 `d91122629fab2fb9ad326a0f32bfd4608acbc80f6b7bdb9d761e8d43227e5928`.
New role-pair vocabulary (Charterer/Shipowner, Escrow Agent/Depositor,
etc.) and new differentiation phrasing across all 12 dimensions +
compound, built after code freeze at `22eac3d`. Zero exact-text overlap
confirmed against all 3 prior corpora.

**Corpus-construction defect note**: the first lock (commit `7846782`)
used "shall make good" as its base reciprocal verb, which doesn't match
`_MUTUAL_RECIPROCAL_RE`/`_OBLIGATION_RE` (both require "indemnify"). All
182 cases returned `facts=None`, a pure discovery-layer miss unrelated
to the mechanism under test — not a valid execution. Fixed (base verb
only, reverted to "shall indemnify") per the Step 4A.8 precedent for
execution-discovered corpus defects; documented in
`artifacts/step4a10_3/corpus_defect_note.md`; original broken lock
preserved in git history; relocked before this run.

```
OVERALL: {'CS': 16, 'CR': 24, 'CA': 58, 'FS': 58, 'WC': 26}

BY TIER (asymmetric+symmetric only):
  Tier 1 (n=86): CS=16, CR=10, CA=30, FS=30
  Tier 2 (n=26): CR=14, CA=6,  FS=6
  Tier 3 (n=44): CA=22, FS=22

BY DIMENSION FAMILY (asymmetric only, n=8 each unless noted):
  causation_standard          CA=8   (fully generalized)
  claim_category               CA=8   (fully generalized)
  defense_control               FS=8   (fail-closed trigger did not fire)
  monetary_treatment            FS=8   (fail-closed trigger did not fire)
  proviso_exception             CA=8   (fully generalized)
  conditional_applicability     CA=8   (fully generalized)
  first_third_party             FS=8   (fail-closed trigger did not fire)
  negligence_fault_standard     CA=8   (fully generalized)
  scope_geographic              FS=8   (fail-closed trigger did not fire)
  cross_reference_schedule      FS=8   (fail-closed trigger did not fire)
  temporal_survival             FS=8   (fail-closed trigger did not fire)
  compound_multi_dimension      CA=8   (fully generalized)
  compound (n=20)                FS=10, CA=10

FS (dangerous) total: 58/116 asymmetric cases (50.0%)
FA (false asymmetry on genuinely symmetric): 0/40 (no regression)
WC (ambiguous cases wrongly treated clean, not routed to review): 26/26
```

## Root cause of the remaining 58 FS

For each FS dimension family, the differentiation phrasing chosen for
this fresh corpus is real English that a human reader would recognize
as asymmetric, but:
- it establishes no field `_snapshot_indemnity_attribution` currently
  recognizes (e.g. "keeps sole command over the defense" vs. "holds no
  corresponding command" — no monetary/scope/trigger/etc. dimension
  matches this vocabulary), so `value_asymmetry` is false (both
  snapshots are equally empty), and
- it doesn't match `_DIFFERENTIATING_QUALIFIER_RE`'s cue list (e.g.
  "exposure tops out at nine months' fees" / "carries no ceiling
  whatsoever", "duty stretches to X as well as Y" / "confined strictly
  to Y", "duty reaches claims arising anywhere on earth" / "confined to
  claims arising within the European Union"), so `cue_present` is also
  false.

Both trigger conditions are themselves closed-vocabulary gates. The
architecture is correct — discover broadly, compare structurally,
fail closed on ambiguity — but the ambiguity-detection cue list
(`_DIFFERENTIATING_QUALIFIER_RE`) is exactly the kind of narrow,
enumerable list Step 4A.10.2 already diagnosed as the wrong
abstraction one layer up. **Extending that list with the eight phrases
this corpus happened to use would repeat the exact failure cycle the
user explicitly warned against**, so no such patch was applied.

A genuinely general fix would need the cue-presence check itself to be
structural rather than lexical — e.g., detecting that a sentence
predicates two *different* clause-final phrases about two named roles
in parallel position (a syntactic asymmetry-of-predication signal),
rather than matching against a fixed list of qualifier words. That is
architecture work beyond this step's scope and is flagged as the
concrete next problem for whichever step follows.

## Secondary finding: AMBIGUOUS cases (WC = 26/26)

All 26 genuinely-ambiguous cases (e.g. "the parties note that whether
X's duty carries the same ceiling as Y's remains open pending a future
amendment") were verified with no asymmetry reasons at all — treated
as clean, not routed to review. This is a separate, pre-existing gap
(the mechanism has no "insufficient information to conclude anything"
signal distinct from "found nothing therefore symmetric" for this
class of hedge language) and is disclosed here for completeness; it
was not the target of this step and is not scored against the
Lee-5/FS gate, which concerns ASYMMETRIC-labeled ground truth.

## Regression / integrity checks

- Production hashes: unchanged pre-implementation → post-freeze →
  post-frozen-execution (`PRODUCTION UNCHANGED` at every checkpoint).
- `step4a7_reciprocal_semantic_benchmark` and
  `indemnification_asymmetry_benchmark`: byte-identical vs.
  pre-4A.10.1 baseline (no regression).
- Policy-engine unit tests (`test_indemnification_policy_engine.py`,
  `test_indemnification_benchmark_gate.py`,
  `test_indemnification_clause_quality.py`,
  `test_liability_policy_engine.py`, and 5 other adjacent-policy test
  files): 209/209 passed. (Full-repo `pytest` collection errors on
  ~44 unrelated files due to missing `httpx2`/pyo3 environment issues
  in this container, not caused by this change; isolated to files with
  zero relationship to the indemnification/policy-engine-core code
  touched here.)
- Step 4A.10.1 S4 operative/non-operative benchmark: false-operative
  extraction remains 0/50 (unchanged).
- Dev benchmarks/controls (132-case symmetry benchmark, 26-case dev
  controls): remain fully clean, FS=0/FA=0, as at freeze.

## Lee Challenge (LEE-5) status

**NOT SOLVED.** Materially asymmetric reciprocal obligations still
become falsely symmetric on unseen drafting at a 50% rate for a
majority of dimension families. The invariant the user specified
("failure to establish two comparable reciprocal obligation snapshots
must never produce a clean symmetric conclusion") is implemented
correctly as a mechanism, but its own ambiguity-detection cue is not
yet general enough to catch the differentiation language this fresh
corpus used. This is architecturally the same problem, recurring one
layer deeper — expected, given the honest diagnosis above, and not
grounds for claiming resolution.

## Step 4A.11 / 4B authorization

**Step 4A.11: NOT authorized.** Per the user's explicit instruction,
this survives only if the fresh frozen corpus shows the invariant
holding; it does not (50% FS on asymmetric fresh-vocabulary cases).
**Step 4B: NOT authorized** (unchanged).

## Recommended next step (not undertaken here, pending user direction)

Replace `_DIFFERENTIATING_QUALIFIER_RE`'s lexical cue list with a
structural signal: detect that two named-role windows predicate
non-identical clause content in syntactically parallel position (e.g.
by comparing normalized trailing-clause structure/token overlap
between the two windows rather than matching either against a fixed
phrase list). This targets the actual recurring defect — a closed
vocabulary gating a safety mechanism — rather than adding the eight
newly-observed phrases, which would only repeat the cycle again on the
next corpus.
