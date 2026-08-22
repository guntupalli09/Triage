# Step 4A.10.1 — S4 Closure + False-Symmetry Safety Gate: Final Report

## A. Executive Verdict

**MORE HARDENING REQUIRED** (not PASS, not PASS WITH CONDITIONS). Objective
A (S4 closure) is **fully achieved**: all 3 original Step 4A.10 S4 cases
close via a general mechanism (0 remaining, confirmed on frozen-corpus
replay and full regression), with 0 net cost to discovery recall or
clean-verified recall. Objective B (false-symmetry gate) is **partially
achieved**: a general safety-net mechanism reduced dangerous false
symmetry from 54/72 (75%) to 12/72 (17%) on the locked benchmark — a real,
regression-tested, 78% reduction — but 12 cases remain (two structural
dimensions: cross-reference allocation and temporal/survival asymmetry),
so Gates 10/11 (S4/S3 false symmetry = 0) do not clear. Per the task's own
rule, no averaging compensates for an unmet hard gate — the honest verdict
is that more work remains before authorizing Step 4A.11.

## B. Baseline Identity

Baseline: `5afbda918e23223ce9572f706062b6c8a73389ee` (Step 4A.10 candidate
SHA). Session HEAD at start: `565c81f`, clean tree, files byte-identical
to Step 4A.10's final checkpoint (`production_hashes_final.txt`).
Production commit after this step's changes: `e0255ff608f908bf000dbb24f6774b382aa7f61b`.
Files changed: `policy_engine_core.py`, `indemnification_policy_engine.py`.

## C. Step 4A.10 S4 Reproduction

All 3 S4 cases (`S4A10-0371`/`0381`/`0391`) individually reproduced,
regex-only, with exact case text, extracted evidence, extracted fact,
policy decision, and the precise responsible function
(`_OBLIGATION_RE.search(text)` matching literal text inside a quoted,
explicitly-negated prompt-injection payload). Full detail:
`baseline_reproduction.md`.

## D. S4 Root Cause

Compound of (B) quoted-example text treated as operative + (F) negation/
meta-language of that quoted material ignored — a general property of the
pipeline (zero structural-context awareness in any structuring regex), not
limited to the 3 demonstrated sentences. Full analysis:
`s4_root_cause.md`.

## E. Operative/Non-Operative Benchmark Methodology

100 cases, locked BEFORE any fix (`8a0e940`): 40 genuine operative / 50
non-operative across 5 structural families (10 each: quoted example,
drafting instruction, descriptive-about-clause, prompt injection, negated
example) / 10 mixed (decoy + genuine operative term in the same document).
`s4_benchmark_hash_PRELOCK.txt`.

## F. S4 Benchmark PRE

`s4_benchmark_PRE_output.txt`: OPERATIVE recall 50.0% (20/40, a
pre-existing unrelated structuring-regex limitation, unaffected by this
step). NON_OPERATIVE: 18/50 (36%) false operative extraction, spanning
ALL 5 families — confirming this generalizes well beyond the 3
originally-found cases. MIXED: 10/10 "verified," but (confirmed by
direct inspection) **100% of those verifications were sourced from the
DECOY, not the genuine clause** — meaning the PRE-fix number was
misleadingly good; it was actually certifying fabricated evidence.

## G. S4 Implementation

`is_operative_context()` (`policy_engine_core.py`): a general,
adapter-agnostic structural-cue check (quotation-introducing framing,
forward/backward negation of quoted material scoped to the same-or-
adjacent clause via a clause-boundary heuristic, meta-instructional
framing, descriptive-about-clause framing) wired into all 3
indemnification structuring entry points (main `_OBLIGATION_RE` loop,
`_SYNONYM_OBLIGATION_RES` loop, `_verify_semantic_candidate`). Iterated
twice on real bugs found via the locked benchmark itself (an `e.g.,`
word-boundary regex bug; a too-broad negation window that suppressed a
GENUINE operative clause in the MIXED family) — both root-caused and
fixed, not patched around.

## H. S4 Benchmark POST

Final: OPERATIVE 50.0% (unchanged — 0 regression), NON_OPERATIVE 50/50
(100%, 0 false operative extraction, down from 18), MIXED 8/10 (80%) now
correctly verifying the GENUINE clause (confirmed via `raw_excerpt`
inspection), not the decoy — the 2 remaining MIXED misses are a
pre-existing, unrelated regex-vocabulary gap (`"requires X to indemnify
Y"` phrasing not covered by `_OBLIGATION_RE`), safely routed to
`REQUIRES_REVIEW`, not a regression from this fix.

## I. Original Three S4 Results

All 3 reproduce as `PRESENT_BUT_UNRESOLVED` post-fix (both in isolated
testing and on the full Step 4A.10 corpus replay, Section Q). **S4: known
3 -> 0.**

## J. False-Symmetry Definition

20 required comparison dimensions defined; CS/CA/CR/FS/FA classification
scheme defined. Full text: `false_symmetry_definition.md`.

## K. False-Symmetry Benchmark Methodology

132 cases (exceeds the 120 minimum), indemnification-focused (per the
task's own note that failures concentrate there) — liability/payment_terms
symmetry NOT covered this pass, disclosed as a scope reduction. 40
genuinely symmetric / 72 asymmetric (12 dimensions x6) / 20 ambiguous.
Locked before any symmetry-logic change (`a07700b`).

## L. False-Symmetry PRE

`symmetry_PRE_output.txt`: CS=19, CR=29, CA=18, **FS=54 (75% of the 72
asymmetric cases)**, FE(missed-ambiguity)=12. FS spans 8 of 12 required
dimensions entirely (only causation-standard, defense-control, and
compound cases were caught pre-fix).

## M. False-Symmetry Root Causes

Single general root cause (not 8 separate bugs): the specific-dimension
snapshot comparators (`_compare_indemnity_attribution`) are each a closed
keyword vocabulary, and silently treat "my classifier doesn't recognize
this phrasing" as equivalent to "confirmed equivalent" — the exact
inversion of the required safety property. Full analysis:
`false_symmetry_root_cause.md`.

## N. False-Symmetry Implementation

Two general mechanisms in `policy_engine_core.py`: (1) a safety net in
`detect_role_attributed_asymmetry` — when the specific comparators find
no difference AND at least one attributed role's local text contains a
structural differentiating-qualifier cue (a family of markers: "only,"
"does not apply," "capped at"/"uncapped," "conditioned on," "different,"
etc. — not a per-case phrase list), the differentiation is reported as
UNCONFIRMED rather than silently presumed equivalent; (2) an additive
widening of `_ROLE_ATTRIBUTION_RE` to also recognize "[Role] is
liable/responsible for" as an attribution shape (was previously 0 matches
for this common drafting pattern, unrelated to any specific test
sentence). One false positive was found via regression testing (`"while"`/
`"whereas"` used as neutral connectives, not asymmetry markers, in a
genuinely-symmetric historical control case) and removed from the cue
list — caught and fixed, not shipped.

## O. False-Symmetry POST

`symmetry_benchmark_POST_FINAL.json`: CS=19 (unchanged — 0 new false
positives on genuinely symmetric cases), CR=29 (unchanged), **CA=60 (up
from 18), FS=12 (down from 54, a 78% reduction)**. Remaining 12: 6
`cross_reference` (role named only as object of a preposition, "for
{role}," no attribution verb at all — 0 attribution matches, safety net
never invoked) + 6 `temporal_survival` (removing the over-broad "while"/
"whereas"/"survives"/"indefinitely"/"terminates upon" cues to fix the
regression above also removed this dimension's only working signal).
**S4/S3 false symmetry: 12, not 0 — Gates 10/11 do not clear.**

## P. Fresh Adversarial Battery

100 NEW cases (`5f4c793`), not derived from the S4 or symmetry
benchmarks: 30 operative-boundary, 40 reciprocal/asymmetry, 15 compound,
15 ordinary-drafting controls. Result: **CA=40, CR=60, WC=0, FS=0, SM=0.**
Zero dangerous outcomes on a genuinely independent mini held-out check —
though note the reciprocal/asymmetry family's specific phrasing
("bear the cost of any claim," not the "X's obligation ... while Y's"
shape the symmetry fix targets) mostly landed safely in CR via the
existing conservative fallback rather than exercising the NEW mechanism
directly; this battery is evidence of safety, not full proof the fix
generalizes to arbitrary future phrasing.

## Q. Step 4A.10 Frozen-Corpus Replay

Locked corpus (`benchmarks/step4a10_benchmark.json`), UNMODIFIED, real
provider, one fresh pass. PRE (Step 4A.10) vs POST (this step):

| Metric | PRE | POST |
|---|---|---|
| S4 (false clean on hard negative) | 3 | **0** |
| Clean-VERIFIED recall | 24.5% | 24.5% (unchanged) |
| All-positive discovered rate | 97.7% | 98.2% |
| Tier-1 discovered rate | 100.0% | 100.0% (unchanged) |
| Noncanonical discovered rate | 96.7% | 97.3% |

7 cases changed outcome; 3 are the target S4 closures. Of the other 4,
directly confirmed (via `arm_a`, the pure-regex-no-API arm, being
byte-identical PRE vs POST for all 4) that **none are caused by this
step's code changes** — they are live-provider-call variance on a single,
already-documented hard template (Step 4A.10 Section U's "Section 8/
Section 10 conflicting definitions" case), consistent with the
previously-measured ~1.5% flicker rate. **No material regression on
hybrid discovery, Tier-1 recall, or noncanonical recall.**

## R. Discovery Regression Check

Covered in Section Q — no material regression.

## S. Authority-Boundary Audit

Re-audited post-fix: both new mechanisms (`is_operative_context`, the
false-symmetry safety net) are pure text-structural functions operating
only on deterministic regex-match offsets against document text; neither
reads semantic output, `discovery_metadata`, or model confidence; neither
can set an authoritative field, only skip building one (S4 fix) or add a
reason string that routes toward REQUIRES_REVIEW (symmetry fix — strictly
safety-improving direction). Full detail: `phase13_authority_recheck.md`.
**Semantic interpretation -> authoritative fact: 0. Fabricated evidence ->
authoritative fact: 0. False semantic candidate -> wrong clean fact: 0.
Provider outage -> confirmed absence: 0** (unchanged from Step 4A.10,
governed by the same untouched functions).

## T. Material-Fact Trust Audit

54 clean (`PRESENT_AND_VERIFIED`) decisions on the Step 4A.10 corpus
replay, **100% REGEX-sourced (0 SEMANTIC)**. Policy-changing UNVERIFIED
feeding CA: **0.**

## U. Determinism

Authoritative determinism: confirmed via the `arm_a` identity check
(Section Q) that the deterministic structuring/verification/symmetry
logic itself produces byte-identical output given identical input — the
only observed variability (4/394 cases) was in the live semantic
provider's candidate proposals, not in what a fixed set of candidates
does once verified. **Contradictory clean policy decisions: 0** (the set
of `PRESENT_AND_VERIFIED` cases before and after included the same 54
cases minus the fixed 0-vs-3 S4 events — no clean decision flipped to a
DIFFERENT clean decision; only unresolved/absent states flickered).
Dedicated N-repeats-per-document determinism reruns (as in Step 4A.10
Phase 26/27) were not separately re-executed this step given the direct,
stronger evidence already available from the frozen-corpus replay itself.

## V. Historical Regressions

Full pytest: **1210 passed, 10 failed, 14 skipped, 44 errors — identical**
to the Step 4A.10 baseline (`pytest_post_symmetry_fix2.txt`). All 9
Step-4A.10-era historical benchmarks (liability, liability-ownership,
payment-recognition, payment-terms, role-boundary, role-resolution,
bystander-discrimination, direction-invariance, liability-concept) —
**byte-identical output**, 0 diffs. Two additional targeted historical
controls specifically covering reciprocal/asymmetry logic:
`step4a7_reciprocal_semantic_benchmark` (89.3% symmetric recall PRE;
one regression found and fixed, confirmed byte-identical to baseline
after the fix) and `indemnification_asymmetry_benchmark` (byte-identical,
0 diff throughout). **0 new regressions in the final committed state.**

## W. Selectivity PRE->POST

Automation Recall / Clean-Verified Recall: unchanged at 24.5% (Section Q)
— **S4 was closed without any blanket-escalation cost.** False-symmetry
fix: CA (correctly-flagged-asymmetric) rose from 18 to 60 on the locked
benchmark (more true positives correctly caught), CS (correctly-symmetric)
held exactly at 19 (0 new unnecessary escalations on genuinely symmetric
cases) — the safety improvement here also came at effectively zero
selectivity cost on this benchmark. **Verdict: SAFETY IMPROVED, NO
SELECTIVITY REGRESSION DETECTED** on either fix.

## X. Lee Challenge Recheck

| # | Question | Status |
|---|---|---|
| 1 | Plausible-but-incorrect fact reaches clean decision? | Unchanged from Step 4A.10 (PARTIALLY SOLVED) — not this step's focus |
| 2 | Provision exists but treated as absent? | Unchanged (SOLVED) |
| 3 | Nothing extracted = evidence of absence? | Unchanged (SOLVED) |
| 4 | Audit trail looks verified without independent establishment? | Unchanged (SOLVED) |
| 5 | Asymmetric reciprocal obligations treated as symmetric? | **PARTIALLY SOLVED** — was UNSOLVED/uninstrumented in Step 4A.10; now 78% of demonstrated false symmetry closed, 12/72 (17%) remains on the locked benchmark across 2 dimensions |
| 6 | Unestablished policy-critical facts route to review? | Unchanged (SOLVED) |
| 7 | Discovery generalizes beyond development vocabulary? | Unchanged (SOLVED) |
| 8 | Probabilistic discovery improves recall without authority? | Unchanged (SOLVED) |
| 9 | Semantic nondeterminism alters clean decisions? | Unchanged (SOLVED) |
| 10 | Provider failure silently creates false absence? | Unchanged (SOLVED) |
| 11 | Non-operative/literal/example/instructional text becomes authoritative evidence? | **SOLVED** — 0/50 false operative extraction on the locked benchmark (down from 18/50), original 3 S4 cases closed, confirmed on frozen-corpus replay and a fresh independent battery (0/30 non-operative false positives) |

## Y. Hard Gates

| Gate | Requirement | Result |
|---|---|---|
| 1 | S4 > 0 | **PASS** (0) |
| 2 | SM-CRITICAL > 0 | PASS (0) |
| 3 | Policy-changing UNVERIFIED feeding CA > 0 | PASS (0) |
| 4 | Semantic interpretation directly controls authoritative fact > 0 | PASS (0) |
| 5 | Fabricated/non-verbatim evidence becomes authoritative > 0 | PASS (0) |
| 6 | False semantic candidate becomes wrong clean fact > 0 | PASS (0) |
| 7 | Provider outage becomes confirmed absence > 0 | PASS (0) |
| 8 | Contradictory clean authoritative decision > 0 | PASS (0) |
| 9 | Evidence provenance missing for clean decision > 0 | PASS (0) |
| 10 | S4 unsafe false symmetry > 0 | **FAIL** (12 remaining FS cases, all treated as S4-severity per this step's own conservative classification) |
| 11 | S3 unsafe false symmetry > 0 | **FAIL** (same 12 cases; not separately split into S3/S4 sub-severity given the conservative default) |
| 12 | Non-operative text produces wrong clean authoritative policy fact > 0 | PASS (0) |

**10/12 PASS, 2/12 FAIL.**

## Z. Remaining Limitations

1. False symmetry: `cross_reference` (role named only as a preposition
   object, no attribution verb — the attribution-detection mechanism
   never even activates) and `temporal_survival` (the specific cue words
   needed were removed after they caused a real false positive, and no
   replacement was found within this step's scope) dimensions remain
   unprotected — 12/72 dangerous false-symmetry cases on the locked
   benchmark.
2. False-symmetry benchmark scoped to indemnification only; liability/
   payment_terms symmetry not evaluated.
3. S3 vs. S4 sub-severity not distinguished for the false-symmetry
   findings — all 12 treated conservatively as S4-equivalent.
4. Dedicated N-repeats determinism study (Step 4A.10 Phase 26/27 style)
   not separately re-run this step; relied on the frozen-corpus replay's
   `arm_a` identity check as equivalent, stronger evidence instead.
5. OPERATIVE recall on the S4 benchmark remains at 50% — a pre-existing,
   unrelated structuring-regex limitation (already Step 4A.10's Section
   U's #1 bottleneck bucket), correctly out of scope for this step but
   still a real limitation on what fraction of genuinely operative text
   reaches a clean decision.

## AA. Step 4A.11 Authorization

**NOT AUTHORIZED YET.** Gates 10/11 remain unmet. Recommend a narrowly
scoped follow-up (not a full Step 4A.10.2) closing the 2 remaining
false-symmetry dimensions specifically — likely requiring: (a) a
preposition-based attribution shape ("for {role}" as object, without a
possessive/verb attribution) to close `cross_reference`; (b) a properly
VALUE-aware temporal comparison (comparing what the survival terms
actually state, e.g. "indefinitely" vs. a bounded expiration event, not
merely the presence of a word) to close `temporal_survival` without
reintroducing the "while"/"whereas"-as-neutral-connective false positive.
Once both close with 0 regression (same discipline as this step: lock
before fixing, root-cause, verify against full regression), Step 4A.11
(deterministic verification automation hardening, using the Section U
bottleneck taxonomy from Step 4A.10) may proceed.

## AB. Step 4B Recommendation

**NO.** Unchanged from Step 4A.10 — this step does not reach the
end-to-end automation question at all; it exists solely to close the
Step 4A.10 hard-gate gaps, one of which (S4) is now closed and one of
which (false symmetry) is partially closed. Step 4B remains multiple
steps away regardless of this step's outcome.
