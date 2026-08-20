# Step 4A.10.2 — False-Symmetry Closure: Final Report

## A. Executive Verdict

**MORE HARDENING REQUIRED — severe.** The development-benchmark fix
(Phase 3-10) genuinely worked: it closed all 12 originally-demonstrated
false-symmetry cases (12->0) and all 8 dev-control cases (8->0), with 0
regression across pytest, 11 historical benchmarks, and the Step 4A.10.1
fresh battery. But on the independently-authored, frozen 226-case
corpus — built without inspecting the fix's regex vocabulary, per the
task's own instruction — **126/126 (100%) of the asymmetric cases FAILED
(FS)**, and 32/40 ambiguous cases wrongly reached a clean decision (WC).
Root cause, confirmed directly: **100% of the 126 FS cases never reach the
comparison logic at all** — `_ROLE_ATTRIBUTION_RE`'s vocabulary
("obligation(s)" / "is liable/responsible for") does not cover the
independently-chosen but entirely ordinary vocabulary ("duty," "is
answerable for") used throughout the fresh corpus. This is the same
narrow-vocabulary failure pattern this entire program has repeatedly
found and is meant to break — now demonstrated one layer deeper, at the
symmetry-ATTRIBUTION stage rather than the obligation-discovery stage.
Per the frozen-execution and anti-patch rules, **no code was changed
after seeing this result.**

## B. Baseline Identity

Step 4A.10.1 production commit: `73f0e40`. Frozen candidate SHA (after
this step's fix, before independent corpus): `58761f7`. Report commit:
this file's commit.

## C. Production Integrity

Clean at every checkpoint: pre-work (`production_hashes_pre.txt`), frozen
(`production_hashes_frozen.txt`), and post-frozen-run
(`production_hashes_post_frozen_run.txt`) — all three byte-identical.
`git diff` empty throughout. **PASS.**

## D. Original 12-Case Reproduction

All 12 reproduced exactly (6 `cross_reference` + 6 `temporal_survival`).
For the representative cases: extracted evidence, comparison result,
exact responsible path (`detect_role_attributed_asymmetry` never invoked
for `cross_reference` — 0 attribution matches; invoked but no comparable
snapshot field for `temporal_survival`), confirmed directly this session
and consistent with Step 4A.10.1's own findings.

## E. Ground-Truth Adjudication

All 12 original labels independently re-examined: all 12 are **TRUE
FALSE-SYMMETRY DEFECTS** — no ground-truth defects found (both dimensions
represent objectively, unambiguously material differences: different
external schedule references per party; "survives indefinitely" vs.
"terminates upon expiration" is a categorical, not stylistic, difference).

## F. Root-Cause Clusters

Two clusters, matching Step 4A.10.1's own precedent: (1) **NORMALIZATION
gap** — `temporal_survival` had no snapshot field at all (survival was
simply not represented); (2) **DISCOVERY/EVIDENCE-OWNERSHIP gap** —
`cross_reference` never even reached the comparison stage because no
detector recognized "Schedule N for Role" as a role-relevant structural
pattern at all. Both are architecture-representation gaps, not
comparison-logic bugs — matching Step 4A.10.2's own Phase 5 audit finding.

## G. Failure Matrix

| Case family | Root cause | Extraction correct? | Normalization correct? | Comparison correct? | Severity |
|---|---|---|---|---|---|
| cross_reference (6) | EVIDENCE OWNERSHIP (no detector) | N/A (never reached) | N/A | N/A | S4 |
| temporal_survival (6) | NORMALIZATION (no snapshot field) | Yes (attribution found) | No (no field) | N/A (nothing to compare) | S4 |

## H. Symmetry Architecture Audit

Full text: `architecture_audit.md`. Key finding: `_snapshot_indemnity_
attribution` had exactly 6 fields (monetary, scope, defense_control,
triggers, broad_beneficiary, causation_standard) — no representation for
survival/temporal or cross-referenced schedules. UNKNOWN fields are
correctly never treated as equivalent (every comparison line is gated on
both sides being non-default) — the danger was narrower: a dimension with
NO representation AT ALL produces an empty `reasons` list indistinguishable
from "checked and equal."

## I. Three-State Comparison Assessment

Implemented for both new dimensions via the existing pattern (EQUIVALENT
if both sides state a value and it matches; DIFFERENT if both state a
value and it differs; UNRESOLVED/not-compared if either side has no
value) — matching how `causation_standard` already worked. Confirmed
correct on the 26-case dev controls (Section J/M) and the 132-case
development benchmark (Section verified: FS 12->0).

## J. Development Benchmark PRE

26 dev controls (locked `a431cd4`, hash in `dev_controls_hash_PRELOCK.txt`):
`survival_temporal`: FS=4/8 CS=5/8. `schedule_cross_reference`: FS=4/8
CS=4/8. 132-case symmetry benchmark: FS=12 (unchanged from Step 4A.10.1).

## K. Implementation

Two additions to `indemnification_policy_engine.py`: (1) `_classify_
survival` — normalized (magnitude, unit) classifier recognizing
indefinite/none/bounded-period survival language, added as a genuine new
snapshot field and comparison dimension (mirrors `causation_standard`
exactly); (2) `_SCHEDULE_REFERENCE_PER_ROLE_RE` + a dedicated detector in
`_detect_reciprocal_asymmetry` for "Schedule/Exhibit/Appendix/Annex N for
Role" (both orderings), flagging when two named roles are bound to two
DIFFERENT external references, on the principled ground that the clause
text cannot verify the referenced documents' equivalence. Two real bugs
found and fixed during this implementation: a missing `(?-i:...)`
case-sensitivity guard (caused "and" to be swallowed as part of a role
name under `re.I`) and a word-order gap (fixed via a second regex
alternative).

## L. Original Failures POST

12/12 -> `CA`. Dev controls: 8/8 FS -> 0 FS (`CA`=8 total across both
families in the final dev-control run).

## M. Development Benchmark POST

132-case benchmark: **CS=19 (unchanged), CR=29 (unchanged), CA=72 (up
from 18 originally / 60 after Step 4A.10.1), FS=0 (down from 12).**
Symmetric precision on this benchmark: 19/19 = 100%. Asymmetric recall:
72/72 = 100%. **Both development-benchmark targets (>=95% recall, >=98%
precision) exceeded — on the development benchmark.**

## N. Transient Regressions Encountered

One, found and fixed during implementation (not shipped): the case-
sensitivity bug above was caught by re-running the historical `step4a7_
reciprocal_semantic_benchmark` and finding `S4B-NEG-02`-adjacent behavior
still correct only after the fix — actually this step's own regex bug was
caught via direct dev-control testing before it ever reached a historical
regression run. No regression shipped in the frozen candidate.

## O. Historical Regression Before Freeze

Full pytest (1210 passed, unchanged), 11 historical benchmarks
(byte-identical diffs against the Step 4A.10.1 baseline), the Step
4A.10.1 S4 benchmark (unchanged, 0 false operative extraction), and the
Step 4A.10.1 fresh 100-case battery (unchanged, 0 WC/FS/SM) — all clean
BEFORE the freeze.

## P. Frozen Candidate SHA

`58761f76211cd4c4db5958181830d7d853d9bf30`.

## Q. Independent Corpus Methodology

226 cases, built AFTER code freeze, from legal/commercial concepts (a
party's indemnification duty differing from its counterpart's along a
policy-material dimension), using vocabulary and document framings
(SaaS/colocation/reseller/underwriting/import-brokerage/data-processing
role pairs) not present in the development benchmark or dev controls.
Zero exact-text overlap confirmed programmatically against both prior
corpora. Per the task's own instruction, the fix's regex vocabulary was
NOT consulted while authoring — this is precisely why the corpus
independently landed on "duty"/"answerable" phrasing the fix's
attribution regex doesn't recognize, rather than the "obligation"/
"liable"/"responsible" vocabulary the fix was built and tested against.

## R. Independent Corpus Composition

226 cases: 60 SYMMETRIC / 126 ASYMMETRIC / 40 AMBIGUOUS. Tiers: 112
ordinary (Tier 1, exceeds the >=100 floor) / 72 varied (Tier 2) / 42
adversarial (Tier 3). 12 dimension families x8 + 30 compound (exceeds all
Phase 15/16 floors). Locked (`3f38574`) before execution;
`independent_corpus_hash_PRELOCK.txt`.

## S. Corpus Lock/Checksums

`benchmarks/step4a10_2_independent_corpus.json`, SHA-256
`ce436f35ba9847332f9f910874a425990c4cec1eb0bbfb60f5cec291b86e9a82`.
Production hashes re-confirmed unchanged immediately before execution.

## T. Frozen Corpus Results

Overall: **CS=8, CR=60, FS=126, WC=32.** (No `CA` at all — not one
asymmetric case was both discovered AND correctly flagged.)

## U. Ordinary-Drafting Results

Tier 1 (n=112, symmetric+asymmetric only): CS=8, CR=32, **FS=72/80
asymmetric = 90% false-symmetry rate on ordinary commercial drafting** —
this is the single most important, and most damning, number in this
report: the task explicitly warns "if ordinary drafting still produces
false symmetry, that is a major failure," and it does, severely.

## V. Asymmetry-Family Results

Every one of the 12 dimension families scored **8/8 FS (100% failure)**,
including causation_standard and defense_control — the two dimensions
that were ALREADY working well before this step even began (Step
4A.10.1's dev benchmark showed these at or near 100% CA). This confirms
the failure is not specific to the 2 dimensions this step targeted; it is
a vocabulary-coverage failure affecting the ENTIRE attribution mechanism
uniformly, because every one of this corpus's templates used "duty"
instead of "obligation."

## W. Compound-Case Results

30/30 compound cases: FS. Same root cause (vocabulary), not a distinct
compound-specific failure.

## X. S1/S2/S3/S4

All 126 FS classified **S4** (per this step's own conservative default,
consistent with Step 4A.10.1's practice) — every one represents a
genuinely material, policy-relevant asymmetry (monetary, causation,
defense-control, temporal, etc.) that a clean symmetric read would hide
from a reviewing lawyer.

## Y. False-Symmetry Analysis

Root cause confirmed directly and precisely: `126/126 (100%)` of the FS
cases have **fewer than 2 role attributions found by `_ROLE_ATTRIBUTION_
RE` at all** — the comparison/normalization logic this step built
(Sections H-K) is never even reached. This is NOT a failure of the
survival/schedule-reference fixes specifically (which work correctly when
attribution succeeds, as the 132-case development benchmark shows) — it
is a failure of the shared attribution-detection layer underneath ALL 12
dimensions, unmasked by this step's corpus because, per instruction, the
corpus was built without consulting that layer's vocabulary.

## Z. False-Asymmetry/Selectivity Analysis

False asymmetry: 0 (no symmetric case was wrongly flagged asymmetric).
Symmetric precision on the frozen corpus: 8/8 = 100% (of the cases that
verified at all) but only 8/60 (13%) of genuinely symmetric cases even
reached a clean decision — the remaining 52/60 safely fell to `CR`
(same vocabulary mismatch, safe direction). **Asymmetric recall: 0/126 =
0%.** Selectivity is not the story here — safety itself failed on the
asymmetric side.

## AA. UNKNOWN/Equivalence Audit

0 cases of UNKNOWN silently becoming EQUIVALENT through the comparison
logic itself (the logic that runs is correct, per Section M). The
mechanism failure is entirely upstream of any UNKNOWN-handling question.

## AB. Step 4A.10 Replay

Not re-run with the real semantic provider this step (budget/decision
disclosed, not hidden — see Section AL). Regex-only (`arm_a`) discovery
confirmed unchanged: 137/220 positive false-absence (regex-only baseline,
identical to every prior checkpoint), **0/174 S4 on hard negatives**
(unchanged) — confirming this step's symmetry-only changes do not touch
the discovery/absence-state code paths at all (verified by code
inspection: `_classify_survival`/`_SCHEDULE_REFERENCE_PER_ROLE_RE` are
called only from `_detect_reciprocal_asymmetry`, never from `extract_
indemnification_facts`'s discovery/gate logic).

## AC. Step 4A.10.1 Replay

S4 benchmark re-run: **OPERATIVE 50.0% (unchanged), NON_OPERATIVE 100%
(unchanged, 0 false operative extraction), MIXED 80% (unchanged).** No
regression of the Step 4A.10.1 mechanism.

## AD. Material-Fact Trust Audit

Not meaningfully performable this step: the frozen corpus produced only
8 genuinely clean (`CS`) decisions (far below the 100-decision target),
because the primary finding IS that almost nothing reaches a clean
decision on this corpus. All 8 available `CS` decisions were regex-
sourced with directly inspectable evidence spans — no UNVERIFIED material
dimension fed any of them.

## AE. Evidence Provenance

For the 8 `CS` and 0 `CA` decisions that did occur, provenance is fully
traceable (raw excerpt, attribution match, snapshot values) — consistent
with every prior step. Not the locus of failure this step.

## AF. Determinism

Not separately re-measured with repeated runs this step (deterministic
regex-only code; Step 4A.10.1 already established 100% authoritative
determinism for this code family, and nothing in this step's change
introduces any source of run-to-run variability — pure regex/dataclass
logic, no randomness, no live calls in Arm A/symmetry logic).

## AG. Full Regression

pytest: 1210 passed / 10 failed / 14 skipped / 44 errors — identical to
every checkpoint since Step 4A.10. 11 historical benchmarks: byte-
identical. **0 new regressions** — the failure mode discovered this step
is a GENERALIZATION gap, not a regression.

## AH. Operative-Recall Observation

Unchanged: 50.0% (20/40) on the Step 4A.10.1 S4 benchmark, exactly as
before. Not addressed, not regressed. Carried forward for Step 4A.11 as
instructed.

## AI. Hard Gates

| Gate | Requirement | Result |
|---|---|---|
| FS-1 | S4 false symmetry > 0 | **FAIL** (126) |
| FS-2 | S3 false symmetry > 0 | PASS (0 — all classified S4, none S3) |
| FS-3 | FS produces wrong clean policy decision > 0 | **FAIL** (every FS case is, by definition, a missed-asymmetry event; whether it also reaches a *clean ACCEPT* downstream policy decision was not separately traced to the policy-evaluation layer this step, but the discovery-level failure alone is disqualifying) |
| FS-4 | Policy-material UNKNOWN silently treated as EQUIVALENT > 0 | PASS (0 — Section AA) |
| FS-5 | Asymmetric ordinary Tier-1 false-symmetry rate > 2% | **FAIL** (90%, Section U) |
| FS-6 | New S4 outside symmetry mechanism > 0 | PASS (0 — Section AB/AC) |
| FS-7 | Policy-changing UNVERIFIED-CA > 0 | PASS (0) |
| FS-8 | Semantic direct authority > 0 | PASS (0 — this step touched no semantic code) |
| FS-9 | Authoritative determinism < 100% | PASS (100%, deterministic regex logic) |

**5/9 PASS, 4/9 FAIL** (including the two most important: FS-1 and FS-5).

## AJ. Selectivity Gates

Symmetric precision: 100% (of what verified) but only 13% coverage.
Asymmetric recall: **0%** (target >=95% — catastrophic miss). False-
asymmetry rate: 0%. **FAIL** on the primary safety-relevant selectivity
gate (asymmetric recall).

## AK. Lee Challenge

LEE-5 specifically requires frozen-corpus evidence, not development-
benchmark evidence, to claim SOLVED. **LEE-5 remains UNSOLVED** — the
frozen, independent corpus shows materially asymmetric reciprocal
obligations become falsely symmetric (or fall to a safe-but-uninformative
review-routing default) in the overwhelming majority of cases when
phrased with entirely ordinary vocabulary the development fix never saw.
All other LEE items unchanged from Step 4A.10.1 (this step's failure is
confined to the symmetry mechanism; it did not touch discovery,
provenance, determinism, or outage handling).

## AL. Remaining Limitations

1. **The core limitation, stated plainly**: `_ROLE_ATTRIBUTION_RE`
   (the shared gate for ALL 12 symmetry dimensions, not just the 2 this
   step targeted) recognizes only "[Role]('s)? obligation(s)" and "[Role]
   is liable/responsible for" as attribution shapes. Ordinary synonyms
   ("duty," "is answerable for," "is accountable for," "bound to," "shall
   answer for") are entirely unrecognized, and this single gap defeats
   the ENTIRE symmetry-comparison mechanism regardless of which
   downstream dimension a difference falls under.
2. Given this, the 2 specific fixes built this step (survival/temporal,
   schedule cross-reference) are UNPROVEN outside the "obligation"/
   "liable"/"responsible" vocabulary — they were never given a fair test
   on this corpus because the corpus's role phrasing defeated them before
   they could run.
3. Step 4A.10 replay (Arm C, real provider) not re-executed this step —
   disclosed budget/relevance decision, not a hidden gap; regex-only
   discovery confirmed unaffected by code inspection and direct testing.
4. Ambiguous-case handling also showed a real gap (32/40 AMBIGUOUS
   wrongly reached a clean decision) via the same vocabulary mechanism
   ("remains an open question" not recognized by `SELF_FLAGGED_
   UNRESOLVED_RE`) — a related but distinct finding worth flagging for
   the same future hardening pass.

## AM. Step 4A.11 Authorization

**NOT AUTHORIZED.** Multiple Phase 30 preconditions fail decisively
(S4 false symmetry = 0 required, actual 126; asymmetric recall >=95%
required, actual 0%). This is a more severe blocker than Step 4A.10.1
left behind, not a resolved one — the true bottleneck (attribution-layer
vocabulary breadth) was not visible until this step's genuinely
independent corpus exposed it. A future step should target the
`_ROLE_ATTRIBUTION_RE` vocabulary itself as a GENERAL mechanism problem
(the same "closed vocabulary as the only gate" pattern already diagnosed
and fixed for indemnification-EXISTENCE discovery in Step 4A.9, and for
the S4/non-operative-text problem in Step 4A.10.1) — likely widening the
attribution shape to a broader, well-justified set of duty/obligation
synonyms, or restructuring the mechanism away from an attribution-noun-
phrase requirement entirely, before re-attempting a frozen independent
validation of false-symmetry closure.

## AN. Step 4B Recommendation

**NO.** Unchanged and, if anything, more clearly premature than before —
this step surfaced a broader, more severe gap in the same subsystem, not
a narrower one.
