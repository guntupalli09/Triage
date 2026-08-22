# Step 4A.9 — Indemnification Recognition Architecture Remediation and Cross-Adapter Capability Parity

## A. Executive Summary

Step 4A.9 redesigned indemnification's obligation-recognition gate around
an explicit discovery/structuring/verification/absence-safety separation,
closed the liability→indemnification monetary-multiplier capability gap,
promoted two independently-drifting mechanism families (self-flagged-
unresolved, chained-delegation) to shared primitives, and fixed all 13
Step 4A.8 WC. On a DEVELOPMENT REPLAY of the locked Step 4A.8 corpus (not
new independent evidence): SM-CRITICAL 16→0, WC 13→0, policy-changing
UNVERIFIED-CA 2→0, indemnification automation recall 3.2%→25.4%, overall
WCDR 8.8%→0.0%, with zero unintended regression across ten historical
benchmarks (byte-identical) and the locked Step 4A.6 corpus (byte-
identical).

A fresh 103-case development battery, built specifically with verbs and
phrasings chosen to sit OUTSIDE the newly-widened patterns, immediately
found 19 new generalization misses (12 false-absence, 7 WC) — the same
class of failure, smaller in scope, recurring on genuinely ordinary
drafting ("recompense," "make good to," "be answerable for," "points to,"
"remains an open question"). This is the sixth consecutive generation
(4A.2→4A.4→4A.6→4A.8→4A.9-replay-clean→4A.9-fresh-battery-broken-again) to
show the pattern: fix known failures → new corpus → new lexical gap. The
architecture separation introduced this step is real and valuable (it
demonstrably converts what used to be silent SM-CRITICAL failures into
safe REQUIRES_REVIEW misses whenever discovery fires even partially), but
the discovery layer's own verb set is still a closed, regex-based
enumeration and this step's own fresh evidence shows it remains breakable.

**Candidate freeze: NO.** The freeze criteria require "no systemic
ordinary-drafting recognition mechanism known to be broken," and Phase 13
found one still is. **Architecture verdict: C** — regex-centric discovery
remains too lexically brittle for indemnification recognition specifically;
a different deterministic/parser architecture, or a Phase-D-style hybrid
(non-deterministic candidate proposal gated by the deterministic
verification layer this step built), should be seriously evaluated before
another patch-and-repeat cycle.

## B. PRE Baseline

`git rev-parse HEAD` at start: `11efc0acba3ed4759a542a691bad6e1402c5a72f`
(Step 4A.8 report commit), `git status --short` clean. pytest: 1191 passed
/ 10 failed / 13 skipped / 44 errors — exact match to the Step 4A.8/4A.7.4
baseline, no drift.

## C. Step 4A.8 Failure Reproduction

Reproduced from `artifacts/step4a8/analysis/final_classification.json`
(unchanged, since production code was untouched between Step 4A.8 and the
start of Step 4A.9): CA=134, CR=96, FE=25, WC=13, SM-CRITICAL=16.

## D. SM-CRITICAL Root-Cause Analysis

All 16 trace to one pipeline gate: `extract_indemnification_facts`'s early
`if not anchors and not any(synonym match): return None`. Discovery
(anchor/synonym check) and absence were the same code path — a discovery
miss was indistinguishable from a confirmed-absent document. 15/16 used a
verb/phrase combination outside the 4-idiom closed list entirely; 1/16
(`S48-I-N-03`) used an idiom already in the list but with its "on X's
behalf" qualifier reordered, which the idiom's rigid word-order regex
didn't tolerate. Full trace and pipeline gate classification (discovery/
interpretation/verification/policy) recorded in
`artifacts/step4a9/recognition_design.md`.

## E. Existing Indemnification Recognition Architecture (before this step)

```
text
 └─ _ANCHOR_RE ("indemnif*") OR _SYNONYM_OBLIGATION_RES (4 rigid full-
    phrase idioms)
      │
      ├─ neither matches anywhere → return None → NOT_APPLICABLE
      │  (discovery failure == absence; the Lee-2/Lee-3 surface)
      │
      └─ matched → _OBLIGATION_RE / synonym idioms / _MUTUAL_RECIPROCAL_RE
           attempt structuring
             ├─ obligation(s) built → trigger/scope/defense/monetary
             │   classification (VERIFICATION stage — already sound;
             │   role/side resolution and reciprocal-asymmetry detection
             │   already escalate correctly on failure)
             └─ no obligation structured → IndemnificationFacts(
                 clause_found=True, obligations=[]) → REQUIRES_REVIEW
                 (already existed, but UNREACHABLE for any text that
                 failed the discovery gate above)
```

## F. Recognition Architecture Redesign

Full design in `artifacts/step4a9/recognition_design.md`. Summary: (A)
broad, non-authoritative `_RISK_TRANSFER_SIGNAL_RE` — a verb cluster
requiring a nearby claim/loss noun — widens the discovery gate so it is
reached far less often for genuinely no-risk-transfer text but, critically,
is now the ONLY thing standing between "no directional obligation could be
parsed" (the existing, already-safe fallback) and `return None`; (B) 5
additional structured obligation patterns (reimbursement, loss-bearing,
duty-to-defend, protection, answer-for, plus a reordered bear-
responsibility variant) widen what can be fully STRUCTURED, not just
discovered; (C/D) the existing `if not obligations: return
IndemnificationFacts(clause_found=True, obligations=[])` fallback — already
built, previously unreachable for anchor-less text — is now the guaranteed
landing spot when discovery fires but structuring can't complete,
producing `REQUIRES_REVIEW` with an honest "risk-transfer language was
detected but could not be confidently structured" message and never
`NOT_APPLICABLE`.

## G. Locked Recognition Benchmark

`benchmarks/step4a9_recognition_benchmark.json`, 180 cases (100 positive /
80 negative, floors met exactly at the positive/negative split requested),
hash `504a023ae37cbb34d741355a02389cf0bee239b905250fcecd0fe0e6c3c2debd`,
locked and committed (`ee03665`) before any production code was touched.
Positives span canonical/variant/reimbursement/loss-bearing/duty-to-defend/
protection/answer-for/bear-responsibility verb families, passive voice,
reciprocal, IP/bodily-injury/regulatory/data/employment/tax triggers,
multi-word entity names, defined-term roles, first-party structures, a
multi-party consortium case, and an amendment-extended case. Negatives
cover insurance, limitation-of-liability, warranty, liquidated damages,
payment, refunds, breach remedies, litigation-cooperation-without-
indemnity, ordinary "responsible for" performance-scope language, releases
(the inverse direction of indemnity), non-indemnity "hold in confidence,"
and 8 varieties of unrelated boilerplate, plus a deliberately adversarial
"hold funds harmless" escrow-mechanics negative. One case-authoring defect
(a missing `{b}` template substitution in the "canonical" verb template)
was found and fixed before locking the corpus was declared final for PRE
measurement — documented as a data-construction correction, not a
ground-truth revision.

## H. Recognition Benchmark PRE

25.0% discovery recall (25/100), 100.0% precision, 0.0% false positive on
negatives. (First uncorrected PRE run, before the `{b}` template fix, read
17.0% — the corrected 25.0% is the fair baseline used throughout this
report.) `artifacts/step4a9/recognition_benchmark_PRE.txt`.

## I. Recognition Implementation

`indemnification_policy_engine.py`: added `_RISK_TRANSFER_SIGNAL_RE` +
`_CLAIM_LOSS_NOUN_RE` + `_risk_transfer_signal_present()`; widened the
early-return gate to also check this signal; added
`_SYNONYM_OBLIGATION_REIMBURSE_FULL_RE`,
`_SYNONYM_OBLIGATION_ASSUME_LIABILITY_RE`,
`_SYNONYM_OBLIGATION_STAND_IN_PLACE_RE`,
`_SYNONYM_OBLIGATION_PROTECT_FROM_SATISFY_RE`,
`_SYNONYM_OBLIGATION_ANSWER_FOR_RE`,
`_SYNONYM_OBLIGATION_BEAR_RESPONSIBILITY_REORDERED_RE`. No production
change references a Step 4A.8 case ID; every pattern is a structural verb
family, not a case-specific branch.

## J. Recognition Benchmark POST

68.0% discovery recall (68/100), 100.0% precision (unchanged), 0.0% false
positive on negatives (unchanged). Actor/beneficiary accuracy 100%/100% of
discovered positives (both PRE and POST). **True false-absence (facts is
None on a genuine positive): 0/100**, verified directly by code inspection,
not inferred from the recall number — the 32 remaining misses all
correctly fall to `REQUIRES_REVIEW` via the `obligations=[]` safety net.
`artifacts/step4a9/recognition_benchmark_POST.txt`. 2x-determinism-verified
(byte-identical).

## K. False-Absence Analysis

0/100 false absence on the locked recognition benchmark (Section J). On
the reused-as-absence-audit 180-case benchmark (Phase 12; see Section T):
TRUE_ABSENCE 79/80 negatives, PRESENT_BUT_UNRESOLVED 1/80 (the escrow
"hold funds harmless" hard negative — correctly non-authoritative, not a
false positive), FALSE_ABSENCE 0/100 positives, PRESENT_AND_ESTABLISHED
68/100, PRESENT_BUT_UNRESOLVED 32/100.

## L. Monetary Multiplier Parity Audit

Liability's `_MULTIPLIER_WORD_RE` (spelled-out number + optional
parenthetical numeral + "times") had no indemnification counterpart;
indemnification's `_MONETARY_MULTIPLIER_RE` matched bare digits only.
Digits, decimals, and the `x`/`times` connector were already at parity;
basis-noun vocabulary was correctly and deliberately NOT unified (liability
tracks purchase-price/contract-value/order-form-value bases indemnification
has no equivalent for — documented in both files' existing comments).
Moved the number-parsing primitive (`WORD_NUMBERS` dict,
`word_number_alternation()`, `parse_multiplier_token()`) to
`policy_engine_core.py`; liability now imports it (proving it's genuinely
shared, not duplicated); indemnification gained a new
`_MONETARY_MULTIPLIER_WORD_RE` built on the same primitive. Verified across
the full 1x–10x range in the Phase 13 fresh battery (`S49-DEV-I-MULT-01`
through `-10`): all ten resolve correctly (7 correctly ESCALATE as
exceeding the negotiable ceiling; 3 correctly ACCEPT/ACCEPT_WITH_NOTE/
NEGOTIATE within it). No dedicated 80-case cross-adapter benchmark was
built separately from the recognition benchmark + fresh battery, given
time constraints — this is a disclosed scope reduction from Phase 6's
literal ask, not a hidden one; the ten-value range test plus the ~90
recognition-benchmark positives that also exercise a "one (1) times"
multiplier provide comparable practical coverage.

## M. Shared-vs-Adapter-Local Architecture Decision

Number parsing (WORD_NUMBERS): SHARED — no adapter-specific semantics.
Basis-noun vocabulary: ADAPTER-LOCAL — genuinely differs (documented,
pre-existing rationale, unchanged). Self-flagged-unresolved core phrase
family: SHARED as of this step — no adapter-specific semantics in "the
document itself says X isn't settled yet"; adapter-specific extras
(payment's "no invoice shall issue until," liability's "no such [X]
currently exists") stay local. Chained-delegation core shape: SHARED
(already was, from Step 4A.7.3; widened this step). Conditional-
applicability core shape: SHARED (already was, from Step 4A.7.4; widened
this step) for liability/payment_terms; indemnification's bifurcated-cap-
tier variant is a genuinely different shape and correctly stayed local
(see Section N).

## N. Cross-Adapter Parity Matrix

Full matrix in `artifacts/step4a9/cross_adapter_parity_matrix.md`. Headline
finding: `determination having yet been made` was added to liability in
Step 4A.7.4 and never propagated to payment_terms despite the identical
concept applying there (`S48-P-N-03`) — now impossible to recur for this
mechanism family, since it's a single shared regex both adapters import.

## O. 13-WC Generalization Root-Cause Analysis

| Case | 4A.7.4's intended abstraction | What was actually implemented | Why it escaped | Scope of fix applied |
|---|---|---|---|---|
| S48-L-T2-07 | "greater-of ambiguity must not silently resolve" | `whichever is (the) greater` | interposed noun ("whichever AMOUNT is greater") not tolerated | liability-local regex widened |
| S48-L-T3-F-02, S48-P-F-01, S48-P-F-02 | "a conditional proviso whose own precondition is unresolved must escalate" | closing-verb pair {verified, determined}, "provided that" anchor only | new verbs (confirmed/made/elected), new tense (having been), new anchor (unless...in which case) not tolerated | shared regex widened (verb set, tense, anchor) |
| S48-L-T3-G-01, S48-P-G-01, S48-P-G-02, S48-L-N-06, S48-P-N-01, S48-P-N-03, S48-P-N-07 | "the document itself flags a fact as unsettled" | 3 independently-maintained per-adapter phrase lists | new phrasings ("have not yet agreed whether," "remains unresolved" bare, "determination has yet been reached") missing from ALL THREE; one existing liability phrase never propagated to payment_terms | **promoted to one shared regex**, closing both the phrasing gaps and the propagation gap at once |
| S48-L-T3-H-01 | "a self-defined term given two values must not silently pick one" | `and separately in Section` | "and IS SEPARATELY DEFINED in Section" (verb spelled out) not tolerated | liability-local regex widened |
| S48-L-T3-I-01 | "a chain of cross-references ending outside the document must escalate" | verb set {cross-references, references, incorporates} | "in turn DEFERS TO" not tolerated | shared regex widened |

Every one of the 13 was a **lexical** gap in an otherwise structurally
sound mechanism (none were adapter-local-when-they-should-be-shared in
isolation, except the self-flagged family, which was both lexically
incomplete AND wrongly un-shared at once). 4 of 5 mechanism families are
now shared; the fixes are general regex widenings stated independently of
any specific Step 4A.8 case wording (verified: Section O's "why it escaped"
column describes a linguistic PATTERN, not a sentence).

## P. General Mechanism Fixes

Documented with root cause / general invariant / positive controls
(the pre-existing benchmark suites, all unchanged) / negative controls (the
same suites' negative cases, all unchanged) / before/after metric, in the
Step 4A.9 Phase 5-8 commit message (`bc38044`) and Sections F/L/O above. No
fix was a bare "add phrase X" without a stated general invariant — each
widening is described in its own code comment as the underlying linguistic
SHAPE being generalized, not the specific failing sentence.

## Q. Step 4A.8 PRE→POST Development Replay

| Metric | PRE (Step 4A.8) | POST (this step, replay) |
|---|---|---|
| CA | 134 | 148 |
| CR | 96 | 110 |
| FE | 25 | 26 |
| WC | 13 | **0** |
| SM | 0 | 0 |
| SM-CRITICAL | 16 | **0** |
| S3 | 13 | 0 |
| S4 | 0 | 0 |
| UNVERIFIED-CA | 2 | **0** |
| False absence | 16 | **0** |
| WCDR | 8.8% | **0.0%** |
| Automation Recall (overall) | 62.7% | 69.3% |
| Automation Recall (liability) | 82.2% | 82.2% |
| Automation Recall (indemnification) | **3.2%** | **25.4%** |
| Automation Recall (payment_terms) | 93.4% | 93.4% |

All Phase 10 hard development targets met: S4=0, SM-CRITICAL=0,
policy-changing UNVERIFIED-CA=0, known S3 false-safe WC=0, false absence
causing unsafe outcome=0. Indemnification automation recall improved
materially (nearly 8x) without blanket escalation — FE rate moved only
11.8%→12.3% (not a spike), and the improvement is traceable to two
distinct, legitimate causes: 14 cases now correctly resolve CA (monetary
fix), and 15 formerly-SM-CRITICAL cases now correctly resolve CR
(recognized, but safely escalate on already-validated role/side-
attribution grounds — not a new escalation mechanism, the pre-existing
Step 4A.7.3 one, simply now reachable).

**This is a DEVELOPMENT REPLAY of the corpus used to design these very
fixes — it is not independent evidence of generalization.** See Section U.

## R. Indemnification Automation/Selectivity

Post-fix: 25.4% automation recall (replay), 68% discovery recall / 100%
precision (locked recognition benchmark). Both are real improvements and
both remain well below liability/payment_terms' 80-90%+ levels — the
residual gap is the honest, disclosed cost of a still-incomplete
enumeration, not a hidden one.

## S. Material-Fact Trust Audit

Re-ran `benchmarks/run_step4a7_5_material_fact_audit.py`: 46 clean
indemnification decisions available from that script's existing corpus
pool (short of the 50/60 target — the pool wasn't rebuilt to include the
new Step 4A.8/4A.9 corpora given time constraints, a disclosed scope
reduction). **0 UNVERIFIED** among all facts audited across all three
adapters. Directly verified separately (not relying on the audit script
alone): all 16 indemnification CA cases in the Step 4A.8 replay have a
genuinely ESTABLISHED (not `not_stated`) monetary fact — 0/16, confirming
Section Q's UNVERIFIED-CA=0 finding by a second, independent method.

## T. Absence Audit

Computed directly from the 180-case locked recognition benchmark (Section
K) — chosen over building a separate 60-case audit because the recognition
benchmark already IS a rigorously-designed absence audit at 3x the required
scale, with the same TRUE_ABSENCE/FALSE_ABSENCE/PRESENT_BUT_UNRESOLVED/
PRESENT_AND_ESTABLISHED categories Phase 12 asks for. Results in Section K.

## U. Fresh 100-Case Development Battery

103 cases (60 indemnification / 20 liability / 23 payment_terms — floors
met), built with domains and phrasings distinct from both Step 4A.8 and the
Step 4A.9 recognition benchmark, deliberately including verbs/phrases
chosen to sit OUTSIDE the newly-widened patterns as a genuine generalization
stress test. **19 new misses found: 12 false-absence (indemnification,
verbs "make good to," "recompense... in full for," "be answerable to...
and shall settle on...'s behalf" — none in `_RISK_TRANSFER_SIGNAL_RE`'s
verb cluster), 7 WC (chained-delegation "points to" as a connective verb,
not in the widened set, appearing in liability/indemnification/
payment_terms; conditional "certification...completed" and self-flagged
"remaining an open point"/"remains an open question," also not in the
widened sets).** 0 false positives on 6 hard negatives (ordinary
"responsible for," "make good," "recompense," insurance, termination,
force-majeure clauses correctly stayed `NOT_APPLICABLE`). Cross-adapter
propagation fix confirmed working on a fresh payment_terms case
(`S49-DEV-P-SF-PORT-01`). Word-number multiplier confirmed correct across
the full 1x-10x range. All 4 fresh reciprocal-asymmetry cases correctly
escalated. Not fixed — Phase 13 is deliberately evidence-gathering, and
patching these specific verbs now would be exactly the "add phrase X,
repeat" cycle this step exists to evaluate, not resolve by continuing.
2x-determinism-verified (byte-identical).

## V. New Findings

1. The discovery-signal safety net (`_RISK_TRANSFER_SIGNAL_RE`) is itself
   still a closed verb-cluster enumeration, not a semantic classifier — it
   is WIDER than the structuring patterns but not unbounded, and Section U
   shows it can still be defeated by ordinary vocabulary choices.
2. A regex character-class bug was found and fixed during this step's own
   work (not a residual Step 4A.8 finding): `CONDITIONAL_UNVERIFIED_
   PRECONDITION_RE`'s `[^.]{0,200}?` lookahead window was silently
   truncated by any decimal point inside a section number ("Section 6.7")
   appearing between the anchor and the target phrase — fixed to
   `(?:[^.]|\.\d){0,200}?`. Worth noting because it shows even a
   "generalized" fix can carry its own narrow, undiscovered lexical
   assumption.
3. Indemnification's `_CONDITIONAL_CAP_ESCALATION_RE` (bifurcated-cap-tier
   shape) remains adapter-local and was not tested against the shared
   PROVIDED-THAT/UNLESS proviso mechanism's own generalizations in this
   step — a real, disclosed gap for a future step to close.

## W. Determinism

100% across all four new/re-run corpora this step touched: recognition
benchmark (2x, byte-identical), Step 4A.8 replay (2x, byte-identical),
fresh battery (2x, byte-identical), and every historical benchmark
(byte-identical to its pre-change run via git-stash diff).

## X. Regression Results

pytest: 1191 passed / 10 failed / 13 skipped / 44 errors, unchanged at
every checkpoint. Locked Step 4A.6 corpus: byte-identical at every
checkpoint. All 10 historical benchmarks (liability-ownership, bystander-
discrimination, role-resolution, IP-ownership, indemnification,
indemnification-asymmetry, reciprocal-semantic, payment-recognition,
payment-terms, role-attribution): byte-identical via git-stash before/
after diff at every checkpoint. Zero unintended selectivity change
anywhere in the codebase this step touched.

## Y. Remaining Known Limitations

- The discovery-signal verb cluster is finite; Section U proves it.
- Indemnification's automation recall (25.4%) remains well below the other
  two adapters' — a real commercial-usability cost of the remaining
  recognition gap, not fully resolved by this step.
- The monetary-multiplier parity audit did not get its own dedicated
  80-case benchmark separate from the recognition benchmark and fresh
  battery, a disclosed scope reduction from Phase 6's literal ask.
- The material-fact audit pool (46 indemnification decisions) fell short
  of the 50-60 target; the underlying finding (0 UNVERIFIED) was
  independently re-confirmed by a second method, but the volume target
  itself wasn't met.
- Indemnification's conditional-cap-escalation mechanism was not
  cross-checked against the shared conditional-precondition mechanism's
  own recent widening (Section V.3).

## Z. Lee Challenge Reassessment

- **LEE-1**: **SOLVED** on both the recognition benchmark and the Step
  4A.8 replay (0 UNVERIFIED-CA, verified two independent ways). Not tested
  against Section U's fresh-battery misses specifically, since those
  correctly escalate rather than reaching a clean decision at all.
- **LEE-2** / **LEE-3**: **PARTIALLY SOLVED.** Solved on the Step 4A.8
  corpus and the locked recognition benchmark (0/100, 0/16 false absence).
  **Not solved** in general — Section U's fresh battery reproduced the
  identical failure mode (false absence on ordinary drafting) at smaller
  but nonzero scale, on genuinely new phrasing built specifically to probe
  this.
- **LEE-4**: **SOLVED** on every corpus this step measured — no clean
  decision in the Step 4A.8 replay or recognition benchmark traces to an
  unverified fact.
- **LEE-5**: **SOLVED** — 0 unsafe false-symmetry across every corpus this
  step and Step 4A.8 measured, including 4 fresh reciprocal-asymmetry cases
  in Section U.
- **LEE-6**: **PARTIALLY SOLVED.** True for liability/payment_terms
  broadly and now largely true for indemnification's VERIFICATION stage
  (once discovery/structuring succeed, the system reliably escalates
  rather than guesses). **Not fully true** for indemnification's DISCOVERY
  stage — Section U shows discovery itself can still silently fail rather
  than triggering a "possibly present, unverifiable" escalation, for verbs
  outside the (now wider, still closed) cluster.
- **LEE-7**: **UNSOLVED.** This step's own fresh evidence (Section U) is
  direct proof: the exact mechanisms built and fixed this step, tested
  against corpora built to develop them, pass; tested against corpora built
  after and specifically to avoid that development vocabulary, they do not
  fully generalize. Per this report's own instructions, LEE-7 cannot be
  declared solved from development corpora regardless — but this step goes
  further and shows a *negative* result even on its own immediate fresh
  test, before Step 4A.10 is ever run.

## AA. Regex-Centric Architecture Decision

**C — REGEX-CENTRIC DISCOVERY REMAINS TOO LEXICALLY BRITTLE; A DIFFERENT
DETERMINISTIC/PARSER ARCHITECTURE IS REQUIRED** (with a specific
recommendation toward D-style hybrid discovery as the concrete next
design, not open-ended redesign).

Reasoning: Step 4A.9 did what targeted deterministic hardening (verdict B)
is supposed to do — root-caused precisely, built general (not case-
specific) fixes, verified them against a benchmark and a corpus built
independently for that purpose, and got real, measured, regression-free
improvement (SM-CRITICAL 16→0 on the corpus that motivated the fix). If
verdict B were the right characterization, that improvement should have
held up against a fresh test built specifically to exercise the SAME
general mechanisms with different vocabulary. It didn't, immediately and
without needing an adversarial search — ordinary synonyms ("recompense,"
"make good," "points to," "remains an open question") were enough. The
underlying reason is structural, not a matter of not having tried hard
enough: any regex-based verb cluster, however wide, has an edge, and every
edge is a place where a real drafter's ordinary word choice can fall
outside it. The discovery/structuring/verification/absence-safety
SEPARATION this step introduced is the right shape of solution and should
be kept — it is why failures now degrade to safe REQUIRES_REVIEW misses
(WC) rather than silent NOT_APPLICABLE misses (SM-CRITICAL) far more often
than before. What should change is the DISCOVERY layer's implementation:
a broader, non-deterministic candidate-proposal mechanism (verdict D),
gated by exactly the deterministic structuring/verification layer already
built and validated this step, would let discovery recall grow without
requiring an ever-longer enumerated verb list, while preserving every
safety property this step demonstrated the verification layer already has.

## AB. Candidate-Freeze Decision

**NO.**

Checklist against Phase 17's stated minimum:
- known S3/S4 false-safe = 0: met on the 4A.8 replay (0/0); **not met** in
  general — Section U found 7 new WC.
- SM-CRITICAL = 0: met on the 4A.8 replay; **not met** in general —
  Section U found 12 new false-absence cases of the identical class.
- policy-changing UNVERIFIED-CA = 0: met, no contrary evidence found.
- unsafe false-symmetry = 0: met, no contrary evidence found.
- known false absence causing unsafe outcome = 0: met on the 4A.8 replay;
  **not met** in general — same 12 cases as above.
- 100% determinism: met.
- no systemic ordinary-drafting recognition mechanism known to be broken:
  **not met** — Section U is exactly this, found by this step's own
  evidence-gathering phase before Step 4A.10 was ever reached.
- meaningful indemnification automation recovery without blanket
  escalation: met (3.2%→25.4%, FE rate stable).

Six of eight criteria pass; two do not, and per Phase 21's own governing
principle throughout this whole effort ("these cannot be overridden by
aggregate accuracy"), a partial pass is not a pass.

## AC. Step 4A.10 Recommendation

Do not run Step 4A.10 (the next genuinely independent frozen validation)
yet — it would very likely reproduce Section U's finding at frozen-
validation scale rather than surfacing new information, since Section U
already demonstrates the residual gap on deliberately-chosen ordinary
vocabulary. Recommend a bounded, explicitly-scoped Step 4A.9.1 first: (a)
evaluate the Phase-D hybrid-discovery direction concretely (what would
"candidate proposal gated by deterministic verification" look like as a
committed design, not just a recommendation) or, if that is out of scope
for now, (b) at minimum broaden `_RISK_TRANSFER_SIGNAL_RE`'s verb cluster
using the 12 Section U false-absence verbs as a genuinely-new (not
Step-4A.8-recycled) evidence source, then re-run a SECOND fresh battery
built independently of both this step's and Step 4A.8's vocabulary to test
whether the gap is closing or merely relocating. Only once a fresh battery
built specifically to defeat the current mechanism fails to find new
false-absence/WC cases should Step 4A.10 be run.

## AD. Step 4B Recommendation

**NO — MORE HARDENING REQUIRED.** Unchanged from Step 4A.8; Step 4A.9 did
not reach the bar Step 4A.8 set for reconsidering this question, and its
own fresh evidence argues against reconsidering it yet.
