# Step 4A.10.6 — Structural Defense-Control Generalization: Final Report

## Executive verdict

**FS = 0/124 and FA = 0/70 on a genuinely fresh, authoritative frozen
corpus, including a 30-case sub-family built specifically to test
verbs never used anywhere in this program before ("helms,"
"quarterbacks," "presides over," "shepherds," "holds the reins on") —
100% of it passed clean. 7 of 8 hard gates met; the eighth (symmetric
recall ≥95%, at 85.7%) misses only because of a separate,
already-documented, out-of-scope discovery-layer gap unrelated to
defense-control. This is genuine evidence of structural generalization,
not another successful lexical patch.**

## What changed

Step 4A.10.5's defense-control fix (`_DEFENSE_SELF_CONTROL_RE`)
enumerated verbs and was defeated on its own authoritative frozen
corpus by fresh verbs. Per the user's mandate, retargeted the
underlying proposition — *role → exercises decision/control authority
→ over the defense/response process* — rather than *role + approved
verb + defense object*:

`_classify_self_response_control` drops the verb entirely. It matches a
response-process STEM (`defen[sc]\w*`, `respon(?:se|d\w*)`, `handl\w*`,
`litigat\w*`, `settl\w*`, `strateg\w*`, `resolv\w*`/`resolut\w*` —
stems absorb noun/verb/gerund forms of the same underlying concept:
"defense"/"defending"/"defends" all match one pattern) tied
self-referentially to the local span's own subject (`against
it/itself` — never a different named role, which is the precision
guard preventing this from ever firing on a role controlling a claim
against the OTHER party). A nearby negation flips the result to an
explicit `self_no_control` value instead of being discarded, so genuine
control-vs-no-control asymmetry still escalates correctly. Abstention
(no established value) happens only when neither signal is present at
all — the same "verify or abstain" architecture as every prior step,
now driven by structural evidence instead of a verb inventory.

## Methodological discipline honored

Per the user's explicit, non-negotiable constraint, **no authoritative
frozen corpus was built until the redesign was exhausted against
explicitly non-authoritative development material**:

1. Dev-replay of all three previously-built (now non-authoritative)
   corpora — 4A.10.4, the burned 4A.10.5, and 4A.10.5b (the corpus
   whose authoritative run had found FA=10/71 from exactly this defect)
   — all showed FA=0, FS=0 under the redesign.
2. `scripts/step4a10_6_dev_adversarial_controls.py`: 11 hand-built
   adversarial cases targeting the specific risks a verb-agnostic
   structural match introduces (false establishment from unrelated
   response-process vocabulary, negation-adjacent words that aren't
   real negations, three-role list-windowing stress, genuine
   control-vs-no-control asymmetry, contrastive-conjunction-phrased
   asymmetry). This found and fixed two real, general gaps — not
   patched away, generalized:
   - A differentiation verb ("differs materially from...") governing a
     clause was being masked by a trailing "the same" *backreference*
     misread as an equal-treatment cue. Fixed via
     `_EQUAL_TREATMENT_DIFFERENTIATION_OVERRIDE_RE`.
   - The structural comparator itself was treating window-slicing
     artifacts (an early-listed role's truncated ", and" ending vs. the
     last-listed role's full sentence) as real content differences.
     Fixed generally in `role_texts_structurally_equivalent`'s
     normalizer, not defense-control-specific — this improves every
     dimension's comparison, not just this one.

Only after 11/11 adversarial cases passed and full regression was
clean was an authoritative corpus built, locked, and run exactly once.

## Authoritative frozen results (first and only pass)

Corpus: `benchmarks/step4a10_6_fresh_independent_corpus.json`, 214
cases, sha256 `d30264087cb7d53d51a0efd660ff2276ba06f9c4d1503091830b886764ab1b0c`.
New role-pair vocabulary (Aircraft Lessor/Aircraft Lessee, Technology
Licensor/Implementation Partner, Storage Provider/Depositing Client,
Underwriting Agent/Capacity Provider, Outsourcing Provider/Client
Enterprise, Import Broker/Export Broker, Facility Operator/Facility
User, Benefits Administrator/Plan Participant). Zero exact-text overlap
against all 7 prior corpora; 0/214 discovery failures.

```
OVERALL: {'CS': 60, 'CR': 17, 'CA': 124, 'WC': 13}

BY DIMENSION FAMILY (asymmetric only): ALL 12 families + compound +
defense_control_no_control (16 cases, 8 standard + 8 genuine
control-vs-no-control shape): CA = 8/8, 16/16, or 20/20 everywhere.

FS (dangerous) total: 0/124
```

**Symmetric family breakdown:**
```
genuinely_symmetric_defense_control (fresh verbs):  CS=30/30  (100%)
genuinely_symmetric_other_paraphrase:               CS=10/10 (100%)
genuinely_symmetric_cue:                            CS=10/15 (CR=5, pre-existing gap)
genuinely_symmetric_generic:                        CS=10/15 (CR=5, pre-existing gap)
```

**FA = 0/70 (0%).** Every single one of this step's own target
family — genuinely symmetric drafting using defense-control verbs this
program has never used before ("helms," "quarterbacks," "presides
over," "shepherds," "holds the reins on") — passed clean.

## The remaining CR=10 (recall gap), root-caused

All 10 are SYMMETRIC-labeled cases returning `verified=False`
(`facts.obligations` empty) — the SAME pre-existing, already-documented
discovery-layer gap from the Step 4A.10.5 report: non-canonical
mutual-opener phrasing ("Either party shall indemnify and hold harmless
the other...", explicit-equal-treatment openers not using the exact
"Each party shall indemnify the other" shape) doesn't match either the
dedicated reciprocal-opener regex or `_OBLIGATION_RE`'s generic
two-role capture. This is unrelated to defense-control, unrelated to
this step's redesign, and was NOT touched here (out of scope; confirmed
via production-hash checkpoint that the discovery/structuring code
paths are byte-identical to before this step).

## Hard gates — honest evaluation

| Gate | Target | Result | Met? |
|---|---|---|---|
| FS | 0 | 0/124 | **YES** |
| S3/S4 false symmetry | 0 | 0 (all ASYMMETRIC cases are S4; none false-symmetric) | **YES** |
| FA | ≤5% | 0/70 = 0% | **YES** |
| Symmetric recall | ≥95% | 60/70 = 85.7% (of ALL symmetric cases); 60/60 = 100% (of cases the discovery layer could parse at all) | **NO** on the strict reading; **YES** on the discovery-adjusted reading |
| Symmetric precision | ≥98% | 60/60 = 100% | **YES** |
| UNVERIFIED material facts feeding clean symmetry | 0 | 0 (checked directly: no CS case has `self_flagged_unresolved` or an unresolved role-side conflict) | **YES** |
| Authoritative determinism | 100% | Re-ran the same locked corpus against the same locked code: byte-identical output | **YES** |
| Zero regression of historical safety controls | required | `step4a7_reciprocal_semantic_benchmark`/`indemnification_asymmetry_benchmark` byte-identical; 213/213 relevant unit tests pass; dev benchmarks/controls unchanged (FS=0/FA=0 throughout, one minor disclosed CR↔WC shift within the review bucket); S4 false-operative-extraction unchanged at 0/50 | **YES** |

**7 of 8 gates unambiguously met.** The recall gate is the one genuine
miss, and it is entirely attributable to a different, already-known,
out-of-scope limitation (discovery-layer opener-phrase recognition) —
**not** to the defense-control mechanism this step targeted, which
scored 100% (30/30) on its own dedicated fresh-verb test family and
100% (0 FA) overall.

## Lee Challenge (LEE-5) status

**SOLVED on the safety axis**, now confirmed across four independent
frozen corpora (4A.10.4, the burned 4A.10.5, 4A.10.5b, and 4A.10.6) —
719 total independently-generated asymmetric test cases, zero
false-symmetric results.

**Selectivity/automation axis: materially improved, one narrow
documented gap remains.** FA=0 and precision=100% on this corpus — a
genuinely different result from every prior step in this sub-program,
none of which reached zero. The recall shortfall is a distinct,
separately-scoped discovery problem (non-canonical opener recognition),
not a defense-control or fail-closed-invariant problem.

## Step 4A.11 / 4B authorization

**Step 4A.11: still NOT authorized**, strictly — one of eight gates
was specified and it was not met on the strict reading. But the
character of what's left has changed: this is the first step in the
whole 4A.10.x program where FS=0 AND FA=0 both held simultaneously on
an authoritative, never-seen corpus. The remaining recall gap is a
narrow, well-understood, disclosed, OUT-OF-SCOPE discovery-layer issue
(non-canonical mutual-opener recognition) that predates this entire
sub-program and has nothing to do with symmetry/differentiation
comparison at all.

**Recommendation**: authorize a narrowly-scoped **Step 4A.10.7 —
Reciprocal Opener Discovery Generalization** (generalize the
mutual-opener/`_OBLIGATION_RE` recognition the same structural way
role-attribution and defense-control were generalized, rather than
requiring one specific phrase shape) before revisiting 4A.11. If that
closes the recall gate on a fifth independent frozen corpus with FS=0
and FA still at or near 0%, all eight gates would be met and 4A.11
would have real, multi-corpus, cross-dimension evidence behind it
rather than a single passing run.

**Step 4B: NOT authorized** (unchanged).
