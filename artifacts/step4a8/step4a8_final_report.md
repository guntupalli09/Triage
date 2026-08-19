# Step 4A.8 — Final Frozen Independent Held-Out Validation

## A. Executive Verdict

**FAIL — MORE HARDENING REQUIRED.**

On a genuinely independent, held-out corpus, the frozen system produced
**16 SM-CRITICAL cases** — a real, capped, sell-side indemnification
exposure obligation, drafted in unambiguous (if non-canonical) English,
reported as `NOT_APPLICABLE` ("no indemnification clause was found in this
contract, so the policy has nothing to evaluate against"). SM-CRITICAL > 0
is a non-negotiable hard gate under Step 4A.8's own predeclared rules; no
aggregate metric can override it. The verdict is FAIL regardless of every
other number in this report.

A second, independent, corpus-wide finding compounds this: indemnification's
monetary-multiplier extraction does not recognize the "one (1) times" /
"two (2) times" spelled-out-number-with-parenthetical-numeral convention at
all — a convention liability's own extractor has explicitly supported since
an earlier step. Across all 97 indemnification cases in this corpus, **zero**
produced a verified numeric multiplier value. Indemnification's automation
recall on this corpus is 3.2% (2/63 ground-truth-automatic cases), against
a predeclared floor of 45%.

A third, smaller-magnitude but structurally important finding: of the 13
confirmed Wrong-Clean (WC) cases, all trace to the exact 4 mechanism
classes Step 4A.7.4 already targeted (conditional-applicability,
self-flagged-unresolved-scope, conflicting-defined-term, chained-delegation)
— but with fresh, ordinary paraphrases of the same underlying concept
("has not yet been independently confirmed" instead of "not yet verified";
"the parties have not yet agreed whether" instead of "not yet reached
agreement"; "in turn defers to" instead of "in turn cross-references"). The
fixes did not generalize past their own development phrasing.

## B. Frozen SHA Verification

```
$ git rev-parse HEAD
8ce89f87362778032ddbaea11b54b1f829d8b7c6
$ git status --short
(clean)
```

SHA-256 of the four production modules recorded in
`artifacts/step4a8/frozen_production_hashes.json` before any corpus
construction began, and re-verified byte-identical at three checkpoints:
immediately after corpus lock, immediately before the frozen execution, and
at report time (Phase 19). `git diff <frozen SHA> -- <production files>`
is empty at every checkpoint. **Production integrity: PASS.**

## C. Historical Baseline Reproduction (Phase 0)

Before corpus construction, every historical control was rerun against the
frozen SHA and recorded in `artifacts/step4a8/phase0_baseline/`:

- pytest: **1191 passed, 10 failed, 13 skipped, 44 errors** — exact match to
  the expected Step 4A.7.4 baseline, no drift.
- Step 4A.6 locked corpus, liability-ownership (42/42), bystander-
  discrimination (22/22 recall, 3 known FP), role-resolution (94.4% recall,
  1 known miss), IP-ownership (100%), indemnification benchmark (2 known
  pre-existing failures), indemnification-asymmetry (19/19), reciprocal-
  semantic (0/108 unsafe false-symmetry), payment-recognition (100%
  recall), payment-terms benchmark, role-attribution benchmark (0/15
  false-safe), 4A.7.3 fresh battery, 4A.7.5 material-fact audit, 4A.7.6
  absence audit — all reproduced their known Step 4A.7.4 numbers exactly.

No STOP condition triggered. Proceeded to corpus construction.

## D. Corpus-Construction Methodology

Corpus written in `scripts/step4a8_generate_corpus.py`, a Python generator
that assigns every case's ground truth (expected facts, expected result,
AUTOMATIC/SHOULD_REVIEW classification, presence/absence expectation,
rationale, severity-if-wrong) at authoring time, before any execution.
Kwargs were validated only by constructing the policy dataclasses directly
(`LolPolicy(**kwargs)` etc.) — never by calling `extract_*_facts` or
`evaluate_*_policy`, and never by inspecting a decision.

Domains/entities (laundry services, industrial welding, elevator
maintenance, pest-control franchising, medical billing, court reporting,
forklift leasing, vending routes, janitorial staffing, well drilling, fire
suppression, crane rental, scaffold erection, EV-charging install, 3D
printing, mobile notary, self-storage management, upholstery restoration,
appliance repair, staffing agencies, freight forwarding, cold storage,
uniform rental, alarm monitoring, golf-course maintenance, marina slips,
hunting guides, ATM servicing, coin laundry routes, custom furniture,
skydiving, home inspection, wine-cellar climate systems, escape rooms,
axe-throwing, boat detailing, pet grooming, commercial kitchen repair,
piano tuning, mold remediation, chimney sweeps, fencing, karaoke/bounce-
house rental, and ~40 more) were chosen and cross-checked against every
prior corpus's own domain list (Step 4A.2/4A.4/4A.6/4A.7.x) before writing
a single case — none overlap.

## E. Contamination Controls

- No prior case text was copied, paraphrased, or lightly mutated (verified
  by construction — every clause was authored fresh against these new
  domains).
- Corpus was not executed against production code during construction
  (Rule #4) — the generator script computes ground truth purely from its
  own template logic; no `run_case` call appears anywhere in
  `scripts/step4a8_generate_corpus.py`.
- One case (`S48-L-T3-I-02`) needed a post-lock, pre-classification
  correction: its `text` field was a 1-element Python list (a trailing-comma
  typo) rather than a string, causing a `TypeError` crash on the *first*
  execution attempt before any output was produced or inspected. This is a
  data-construction defect, not a ground-truth revision — documented in
  `corpus_manifest.json`'s `gtd_corrections` and re-hashed/re-committed
  before the real frozen execution began.
- 40 ground-truth-defect (GTD) corrections were made *after* seeing output,
  all individually justified in Section R/Q below (not silently absorbed
  into a green count) — these are the only post-execution corpus
  interpretations, and none altered any case's *text*, only which taxonomy
  bucket (CA/CR/WC/FE) the case's *known, already-committed* text and
  ground truth fields resolve to.

## F. Corpus Manifest

From `artifacts/step4a8/corpus_manifest.json` (commit `6d46f33`, corrected
in `59aefbf`):

- **284 semantic cases**, **32 formatting mutations** — 316 total executions
  (floor was 240 + 30 = 270).
- Tiers: Tier1=126, Tier2=87, Tier3=71 (floors 100/80/60, all met).
- Adapters: liability=97, indemnification=97, payment_terms=90 (floor 75
  each, met).
- Review ground truth: AUTOMATIC=212, SHOULD_REVIEW=72 (floors 150/70, met).
- Attack families: A=80, B=65, C=8, D=47, E=39, F=19, G=14, H=24, I=21,
  J=6, K=5, L=5, M=3, N=30 (Family E floor 30 met at 39; Family N floor 30
  met exactly, with 10 cases combining 3+ mechanisms, floor 10 met exactly).

## G. Predeclared Gates

Recorded in `artifacts/step4a8/predeclared_gates.md` before execution,
frozen thereafter. See Section AI for evaluation against them.

## H. Ground-Truth Methodology

Every case carries `expected_facts`, `expected_result` (the specific
predicted state string), `review` (AUTOMATIC/SHOULD_REVIEW), optional
`presence` (absence-audit classification), `rationale`, and
`severity_if_wrong`, all authored before execution. Classification (Phase
8) did not trust the final label alone: every WC/SM-CRITICAL candidate's
`unresolved_facts`/`explanation` was inspected and, where the actual state
diverged from `expected_result` for a reason unrelated to a real system
defect (a wrong exact-state prediction on my part, e.g. predicting
`ESCALATE` where the codebase's own consistent convention is
`MUST_REDLINE` for fixed-dollar caps; or predicting `ACCEPT` for a
single-obligation clause with a non-generic-vocabulary party name where
Step 4A.7.3 already established REQUIRES_REVIEW is the correct, safe,
by-design outcome), that was logged as a **GTD correction**, not silently
counted as a system failure or silently counted as a pass.

## I. Overall Results

| Class | Count |
|---|---|
| CA (Correct Automatic) | 134 |
| CR (Correct Review) | 96 |
| FE (False Escalation) | 25 |
| WC (Wrong Clean) | 13 |
| SM (Silent Miss, non-critical) | 0 |
| **SM-CRITICAL** | **16** |
| GTD corrections applied | 40 |

284 semantic cases total.

## J. Per-Adapter Results

| Adapter | CA | CR | FE | WC | SM-CRITICAL |
|---|---|---|---|---|---|
| liability | 61 | 25 | 5 | 6 | 0 |
| indemnification | 2 | 64 | 15 | 0 | 16 |
| payment_terms | 71 | 7 | 5 | 7 | 0 |

Indemnification's CA count (2) is not a rounding artifact — it is the
direct, corpus-wide consequence of Finding #2 (Section Z).

## K. Per-Tier Results

| Tier | CA | CR | FE | WC | SM-CRITICAL |
|---|---|---|---|---|---|
| Tier 1 (ordinary) | 83 | 24 | 4 | 0 | **15** |
| Tier 2 (structural) | 41 | 29 | 16 | 1 | 0 |
| Tier 3 (adversarial/compound) | 10 | 43 | 5 | 12 | 1 |

**15 of the 16 SM-CRITICAL cases are Tier 1 — ordinary, non-adversarial
commercial drafting.** This is the single most important number in this
report: it is not an adversarial-corner-case failure, it is a failure on
the kind of drafting Phase 15 explicitly warns must be robust regardless
of adversarial performance elsewhere.

## L. Attack-Family Results

Family D (indemnification recognition, fresh synonym idioms): 15/15 cases
resulted in SM-CRITICAL (100% failure rate on this family — every fresh,
non-canonical risk-transfer phrasing tested was silently treated as no
clause at all). Families F/G/H/I (conditional-applicability, self-flagged-
scope, conflicting-definitions, chained-delegation): 13 WC across both
liability and payment_terms, root-caused in Section Z. Family C (ownership
contamination): 2/8 near-misses worth flagging — see Section R. Family E
(reciprocal semantics): 0 unsafe false-symmetry (the hard gate this family
exists to test is clean), but 10 genuine-symmetry negative controls
misfired into MUST_REDLINE for the unrelated monetary-multiplier reason
(Finding #2), not a symmetry-detection defect.

## M. Compound-Case Results (Family N, 30 cases)

CA=0, CR=17, FE=3, WC=4 (S48-L-N-06, S48-P-N-01, S48-P-N-03, S48-P-N-07),
SM-CRITICAL=1 (S48-I-N-03 — a 4-mechanism compound case using the fresh
"bear full responsibility... on X's behalf" synonym with the "on X's
behalf" phrase reordered before rather than after the claim noun, which by
itself broke recognition entirely). Zero unsafe false-symmetry, zero false
absence outside the one SM-CRITICAL case, zero wrong-ownership/wrong-role-
attribution failures among the compound cases. The compound WC rate (4/30 =
13.3%) is higher than the corpus-wide WC rate (13/284 = 4.6%), consistent
with Step 4A.6/4A.7's own finding that individually-correct mechanisms can
still fail when composed — though here the composition itself did not
introduce a NEW failure mode; each compound WC/SM-CRITICAL case's failure
traces to one of the same root causes already present in the non-compound
corpus (Section Z), just co-occurring with other mechanisms in the same
clause.

## N. Formatting Robustness (Phase 17)

32 mutations across line-break insertion, tab indentation, numbered-list
reformatting, bullet reformatting, all-caps headings, extra whitespace,
section-number style changes, parenthetical layout changes, and semicolon-
to-newline conversion, each applied to a genuinely presentation-only degree
(verified: none of the 32 mutations altered the extracted `state` relative
to its semantic source case). **Format invariance rate: 32/32 = 100%.**
Formatting robustness is not where this system's problems live.

## O-R. CA / CR / FE / WC Analysis

**CA (134).** Spot-checked across all three adapters: liability and
payment_terms CA decisions consistently show a directly-quoted, unambiguous
value in `controlling_provision.excerpt` matching `extracted_summary` — the
same ESTABLISHED pattern confirmed in the Step 4A.7.5 material-fact audit.
The 2 indemnification CA cases (`S48-I-E-SYM-08`, `S48-I-H-02`) are flagged
separately in Section U — their monetary fact is UNVERIFIED, not
ESTABLISHED, and the clean label is coincidental (their `contract_side`
configuration means the unverified monetary value falls on the PROTECTION
side, which the current policy design does not gate).

**CR (96).** The largest single cluster (31 cases) is the "single,
non-reciprocal obligation, unusual-but-realistic company name, directional
contract_side" shape — REQUIRES_REVIEW is genuinely correct here (Step
4A.7.3 already established the system cannot determine "who is us" from an
ordinary company name without either generic-vocabulary matching or
reciprocal/named-pair term-invariance, and guessing would be the actual
defect). These were originally mis-predicted AUTOMATIC in this corpus's own
ground truth and corrected as GTD (Section H).

**FE (25).** 18/25 are the E-family (genuinely symmetric reciprocal
indemnity) negative controls landing on MUST_REDLINE for the unrelated
Finding #2 reason (monetary-multiplier non-recognition), not a symmetry-
detection false positive — the reciprocal-asymmetry mechanism itself is not
implicated. The remaining 7 are scattered: one liability contamination
near-miss where a liquidated-damages distractor's $150,000 figure was
extracted instead of the real 2x general cap (Section Z, Finding #4 —
concerning even though the ultimate ESCALATE outcome was still safe), one
long-sentence basis-extraction range limitation, and five miscellaneous.

**WC (13).** Fully adjudicated in Section Z (Finding #3) — every one
traces to a fresh paraphrase of an already-known-and-previously-"fixed"
mechanism. None reach S4: the hidden fact in every case is bounded (a
multiplier within the 1x-3x band already tolerated elsewhere in the policy
ladder, or a payment-period difference of days, not an unbounded/unknown
exposure) — consistent with the S3 severity already established for this
mechanism family in Step 4A.7.3/4A.7.4.

## S. Silent Miss Analysis

SM (non-critical) = 0. **SM-CRITICAL = 16**, all indemnification, all
Family D/N (fresh-synonym recognition failures), fully detailed in Section
Z, Finding #1. Any SM-CRITICAL is a hard blocker per Phase 10/21 — met here
16 times over, not once.

## T. S1–S4 Severity

| Severity | Count | Composition |
|---|---|---|
| S1 | 0 | — |
| S2 | 8 | the 8 liability fixed-dollar ESCALATE/MUST_REDLINE GTD label mismatches (reclassified CR, no severity assigned as a defect) |
| S3 | 13 | the 13 confirmed WC (Section Z, Finding #3) |
| S4 | 0 | — |
| **SM-CRITICAL** | **16** | Section Z, Finding #1 — outside the S1-S4 scale by definition, and the single blocking finding of this report |

## U. Material-Fact Establishment Audit

For every CA case, the policy-changing material fact's basis was
inspected. 132/134 are ESTABLISHED (direct textual match, same standard as
Step 4A.7.5). **2/134 are UNVERIFIED**: `S48-I-E-SYM-08` and `S48-I-H-02`
— both indemnification, both resolve ACCEPT with `extracted_summary`
literally reading "Exposure: n/a; Protection: present" with no monetary
figure anywhere in the explanation, because Finding #2 (Section Z) means
the multiplier was never extracted at all. Under the CURRENT policy
configuration (which only gates the EXPOSURE-side multiplier, not
PROTECTION-side), this does not change today's clean label — but it is a
genuine, policy-changing-under-a-plausible-alternate-configuration
UNVERIFIED fact feeding a CA decision, and is reported as a hard finding
per Phase 11's explicit instruction, not hidden inside the CA count.

## V. Absence Audit

Family L/K cases (9 total) classify as: CONFIRMED_ABSENT=3 (all correct —
`S48-L-L-01`, `S48-I-L-01`, `S48-P-L-01`, the genuine-absence negative
controls), EXPECTED_BUT_MISSING=2 (`S48-L-L-02`, `S48-P-K-02`, both
correctly MUST_REDLINE/NOT_APPLICABLE), PRESENT_AND_EXTRACTED=3 (the K-01,
K-03, N-05 payment-recognition-generalization controls, all correct),
**RECOGNITION_UNCERTAIN → actually FALSE ABSENCE = the 16 SM-CRITICAL
cases**, which are not part of the Family-L/K set at all — they are Family
D cases whose absence classification only becomes visible by cross-
referencing `actual_state == NOT_APPLICABLE` against a corpus-authored
presence guarantee. **False absence rate, measured against every case
where a real clause was authored to be present: 16/205 = 7.8%** (205 =
count of semantic cases where `presence` was not explicitly `None` with a
genuine-absence label, i.e. every case where a clause genuinely exists).
This is a materially worse false-absence rate than Step 4A.7.6's 0% —
because that audit's 34 cases never happened to test non-canonical
indemnification synonym phrasing at this volume; this corpus did, on
purpose (Family D), and it found the gap immediately.

## W. Wrong-Clean Decision Rate

Overall WCDR = 13 / 147 clean-automatic decisions actually produced =
**8.8%** (predeclared ceiling: 8% — narrowly exceeded). Per-adapter: liability
6/67=9.0%, indemnification 0/2=0%*, payment_terms 7/78=9.0% (*indemnification's
denominator is degenerate because of Finding #2 — 0% here reflects a broken
denominator, not a safety success). Unsafe-case rate (S3+S4+SM-CRITICAL)/284
= (13+0+16)/284 = **10.2%**.

## X. Automation / Selectivity

| Metric | Value | Predeclared floor/ceiling |
|---|---|---|
| Overall Automation Recall | 133/212 = 62.7% | ≥ 55% (met) |
| Liability Automation Recall | 60/73 = 82.2% | ≥ 45% (met) |
| Indemnification Automation Recall | 2/63 = **3.2%** | ≥ 45% (**failed**) |
| Payment-terms Automation Recall | 71/76 = 93.4% | ≥ 45% (met) |
| Overall FE rate | 25/212 = 11.8% | ≤ 20% (met) |
| Overall WCDR | 13/147 = 8.8% | ≤ 8% (narrowly failed) |
| Tier-1 WCDR | 0/83 = 0.0% | ≤ 3% (met — see caveat below) |

Tier-1 WCDR meeting its ceiling is not the good news it looks like: 15 of
Tier 1's problems are SM-CRITICAL, a category the WCDR formula does not
count at all. Reading WCDR in isolation here would be exactly the kind of
"aggregate accuracy overriding a hard gate" Phase 21/22 explicitly forbid.

## Y. Tier-1 Ordinary-Drafting Analysis

Tier 1 (126 cases): CA=83 (65.9%), CR=24, FE=4, WC=0, **SM-CRITICAL=15
(11.9%)**. Zero WC in Tier 1 sounds like a clean pass; it is not — nearly
1 in 8 ordinary Tier-1 cases is a case where the system was silently blind
to a real obligation. This is precisely the scenario Phase 15 warns about:
"a repeated WC mechanism in Tier 1 is a hard generalization failure even
if overall metrics look strong" — substitute SM-CRITICAL for WC and the
same warning applies with more force, since SM-CRITICAL is strictly worse
than WC (WC at least shows a decision; SM-CRITICAL shows nothing at all).

## Z. Root-Cause Clustering of Failures

**Finding #1 — indemnification's obligation-recognition regex family is a
closed enumeration, not a semantic match, and 100% of fresh (but entirely
ordinary) risk-transfer phrasing outside that enumeration is silently
dropped.** `_SYNONYM_OBLIGATION_RES` in `indemnification_policy_engine.py`
recognizes exactly 4 fixed idioms plus the canonical "shall indemnify,
defend, and hold harmless." Every one of 15 fresh Family D phrasings
("shall be responsible for, and shall reimburse X in full for," "shall
assume all liability for, and undertakes to make X whole in respect of,"
"shall stand in X's place in defending against, and shall bear the cost of
resolving," "shall protect X from, and satisfy on X's behalf, any
third-party claim arising from") — none copied from or resembling any
production regex source, each independently plausible legal drafting —
produced `NOT_APPLICABLE`. A 16th case (`S48-I-N-03`) shows the same defect
class can also break a phrase the system supposedly already handles: "shall
bear full responsibility for defending and satisfying, **on Client's
behalf**, any third-party claim" reorders the existing "on X's behalf"
qualifier to precede rather than follow "any claim," and the exact,
rigidly-ordered regex `defending\s+and\s+satisfying\s+(?:such|any)\s+claims?\s+on`
no longer matches. **This is architectural, not a missing case in a list**:
adding four more idioms to the enumeration would not fix the underlying
problem, which is that indemnification obligation recognition has no
fallback path for "a party assumes financial/defense responsibility for a
third party's claim" stated in language the enumeration didn't anticipate.

**Finding #2 — indemnification's monetary-multiplier regex never received
liability's own "spelled-out number + parenthetical numeral" fix.**
`liability_policy_engine.py` has two multiplier alternatives: a bare-digit
form (`\d+(?:\.\d+)?`) and a dedicated word-number form
(`\b(one|two|three|...)\s*(?:\(\d+\))?\s*times?`) added specifically to
handle "one (1) times" / "two (2) times" drafting. `indemnification_policy_
engine.py`'s `_MONETARY_MULTIPLIER_RE` has only the bare-digit form. Every
one of this corpus's 97 indemnification cases used the spelled-out
convention (a deliberate, realistic choice — this convention is at least as
common in real legal drafting as bare digits, and is TriageCounsel's own
established liability-side convention). Result: zero indemnification cases
in this corpus produced a verified numeric multiplier. Downstream this
manifests two ways: (a) on the EXPOSURE side, the existing "exposure states
no monetary treatment at all" check correctly, safely, but over-broadly
fires `MUST_REDLINE` — safe but commercially unusable at scale (this is why
indemnification's automation recall is 3.2%, and why 18 genuinely-symmetric
E-family negative controls misfire); (b) on the PROTECTION-only side, the
same non-extraction produces a **clean ACCEPT with an unverified monetary
fact** (Section U), because protection-side monetary isn't gated by the
current policy design at all.

**Finding #3 — the 4A.7.4 fixes for conditional-applicability, self-
flagged-unresolved-scope, conflicting-defined-term, and chained-delegation
are narrow lexical patches, not semantic detectors, and do not generalize
past their own development phrasing.** All 13 confirmed WC:

| Case | Family | GT phrase | What the regex requires | Actual phrase used |
|---|---|---|---|---|
| S48-L-T2-07 | B (greater-of) | — | `whichever is (?:the )?greater` | "whichever **amount** is greater" |
| S48-L-T3-F-02 | F | conditional | `not yet (?:been )?verified\|determined` | "has not yet been independently **confirmed**" |
| S48-L-T3-G-01 | G | self-flagged | `not yet reached agreement` | "have not yet **agreed whether**" |
| S48-L-T3-H-01 | H | conflicting term | `and separately in Section` | "and **is separately defined** in Section" |
| S48-L-T3-I-01 | I | chained delegation | `cross-references\|references\|incorporates` | "in turn **defers to**" |
| S48-P-F-01 | F | conditional | `not yet being determined` | "not yet **having been** determined" |
| S48-P-F-02 | F | conditional | `not yet verified\|determined` | "has not yet **made** this election" |
| S48-P-G-01 | G | self-flagged | `not yet reached agreement` | "have not yet **agreed whether**" |
| S48-P-G-02 | G | self-flagged | `not yet (?:been )?determined` | "determination **has yet been reached**" |
| S48-L-N-06 | F+G (compound) | both | verified/determined; under negotiation | "has not yet been **fixed**"; "remaining **unresolved**" |
| S48-P-N-01 | F+J (compound) | conditional | verified/determined | "has not yet **elected** to join" |
| S48-P-N-03 | G+K (compound) | self-flagged | `determination having yet been made` (liability-only fix) | same exact phrase — **never ported to payment_terms** |
| S48-P-N-07 | F+G+J (compound) | both | under negotiation | "**remains unresolved**" (no "under negotiation") |

Every row is a synonym, tense variant, or word-order variant of a phrase
the corresponding regex already handles. `S48-P-N-03` is the clearest
single proof of non-generalization across the codebase itself: the exact
phrase `determination having yet been made` was added to liability's
`_SELF_FLAGGED_AMBIGUITY_RE` in Step 4A.7.4 (case F3-D-11) and never
propagated to payment_terms' own self-flagged detector, despite the
identical concept being independently maintained in both adapters.

**Finding #4 (lower-severity, worth tracking) — a liquidated-damages
distractor was adopted over the real general cap in one Family C
contamination test** (`S48-L-T3-C-03`): the extractor read the $150,000
liquidated-damages ceiling instead of the separately-stated "two (2) times
the annual purchase-order value" general cap. The outcome (`ESCALATE`) was
still safe only because fixed-dollar values always escalate for manual
comparison regardless of magnitude — a coincidence of that particular
policy branch, not evidence the contamination itself was handled correctly.

## AA. Determinism

Two full, byte-identical runs of all 316 executions (`diff` = 0 lines).
**Determinism: 100%.**

## AB. Production-Integrity Verification

Confirmed at three checkpoints (Section B). **PASS.**

## AC. Historical-Control Reproduction

Confirmed post-execution: Step 4A.6 corpus re-run is byte-identical to the
Phase 0 baseline; pytest reproduces 1191/10/13/44 exactly. Harness is
stable; these controls are not evidence the held-out corpus passed (Phase
20) — they only confirm nothing shifted under the held-out run itself.

## AD. Cross-Generation Analysis: 4A.2 → 4A.4 → 4A.6 → 4A.8

| Generation | Known WC | S4 | SM-CRITICAL | Note |
|---|---|---|---|---|
| 4A.2 | 29 / 108 semantic | 1 confirmed | — | first independent validation |
| 4A.4 | 12 | — | present | |
| 4A.6 | 4 confirmed | 4 confirmed | present | major ordinary-drafting cap failure |
| 4A.7–4A.7.4 (development) | 0 (at freeze) | 0 | 0 | targeted fixes against 4A.6/4A.7.3's own findings |
| **4A.8 (independent)** | 13 | 0 | **16** | — |

1. **Is WC decreasing across genuinely independent corpora?** Numerically
   yes (29 → 12 → 4 → 13), though 4A.8's WC count sits between 4A.4 and
   4A.6, not below 4A.6 — and WC alone understates 4A.8's severity because
   SM-CRITICAL (a category more dangerous than WC) is counted separately.
2. **Is S4 eliminated on genuinely unseen drafting?** Yes — 0 confirmed S4
   in this corpus, a real improvement over 4A.6's 4 confirmed.
3. **Is SM-CRITICAL eliminated?** **No.** 16 found, the worst SM-CRITICAL
   count of any generation reported in this history, on a category
   (indemnification recognition) that was not itself the direct target of
   any single named 4A.7.x fix.
4. **Are ordinary Tier-1 cases now robust?** No — Tier 1 carries 15/16 of
   this generation's SM-CRITICAL cases.
5. **Are failures moving from systemic/common drafting toward genuinely
   difficult edge cases?** No. Finding #1/#2 are Tier-1, common-drafting,
   whole-adapter-scope failures, not edge cases.
6. **Are fixes generalizing beyond the development corpora?** No — Finding
   #3 demonstrates the opposite directly: every 4A.7.4 fix tested against
   a fresh paraphrase of its own target concept failed to generalize.
7. **Is FE/selectivity commercially acceptable?** Marginal outside
   indemnification (liability 82%, payment 93% automation recall); inside
   indemnification, no (3.2%).
8. **Does compound drafting still expose unsafe interactions?** Yes, at a
   higher rate than the non-compound corpus (13.3% vs 4.6% WC rate), though
   without a genuinely NEW failure mode beyond Findings #1–#3 recombined.
9. **Has the architecture broken the historical pattern (benchmark green →
   new corpus → new lexical failure → false certainty)?** **No.** This
   report is itself the fifth consecutive instance of that exact pattern:
   Steps 4A.7–4A.7.4 closed every known WC on their own development and
   fresh-battery corpora, declared 0/0/0/0 at freeze, and Step 4A.8 — the
   very next genuinely independent corpus — immediately found new,
   substantial, previously-invisible failures, including the worst
   SM-CRITICAL count of any generation.

## AE. Lee Challenge

- **LEE-1** (plausible-but-wrong fact → clean decision): **PARTIALLY
  SOLVED.** The material-fact audit found only 2/134 CA cases with an
  UNVERIFIED fact (Section U) — narrow in count, but real, and directly
  caused by Finding #2.
- **LEE-2** (clause present but unrecognized, treated as absent): **UNSOLVED.**
  This is exactly Finding #1 — 16 confirmed instances.
- **LEE-3** (nothing extracted silently becomes evidence of absence):
  **UNSOLVED.** Identical to LEE-2 in this corpus; `NOT_APPLICABLE` was
  produced with no unresolved_facts, no hedge, no signal distinguishing
  "confirmed absent" from "extraction gave up."
- **LEE-4** (clean audit trail from a materially unverified interpretation):
  **PARTIALLY SOLVED.** The 2 UNVERIFIED-CA cases in Section U produce a
  fully-formed, confident-looking `explanation` string with no hedge
  language.
- **LEE-5** (asymmetric reciprocal obligations falsely normalized to
  symmetry): **SOLVED** on this corpus — 0/39 Family E cases showed unsafe
  false-symmetry; every genuine asymmetry (monetary/scope/defense-
  control/trigger, Section L) correctly escalated.
- **LEE-6** (escalate rather than guess when a fact can't be established):
  **PARTIALLY SOLVED.** True for liability and payment_terms generally
  (Finding #3's WC cases are the exception, not the rule, within those two
  adapters); **false** for indemnification specifically, where the failure
  mode is not "guess" but "go silent" (Finding #1), which is worse than
  guessing because it doesn't even surface as a decision to second-guess.
- **LEE-7** (do the protections generalize to unseen drafting?): **UNSOLVED.**
  This is the central question Step 4A.8 exists to answer, and the answer
  from this corpus is no, in the most direct and structural way possible:
  the mechanisms tested here are not the same drafting used to build the
  protections, and both a whole-adapter recognition gap and every single
  fresh-phrasing test of Step 4A.7.4's own mechanisms failed.

## AF. Remaining Known Limitations

- Classification depended on programmatic gt/actual comparison plus full
  manual adjudication of every WC and SM-CRITICAL candidate (32 cases total
  individually root-caused) and documented GTD reasoning for every
  reclassification (40 cases); the 134 CA and 96 CR cases were spot-checked
  rather than each individually narrated in this document, consistent with
  the material-fact-audit methodology already established in Step 4A.7.5,
  given the corpus's scale.
- The corpus does not include non-English or heavily jurisdiction-specific
  drafting, multi-currency payment terms beyond USD, or scanned/OCR-quality
  text degradation — all out of scope for this step as specified.

## AG. Architecture Verdict

**C. ARCHITECTURE STILL HAS MATERIAL GENERALIZATION GAPS REQUIRING TARGETED
HARDENING.**

Not D: liability and payment_terms, while not clean, show real signal that
targeted regex hardening measurably improves safety without regressing
selectivity (0 S4 this generation vs. 4 in 4A.6; 82%/93% automation recall
outside indemnification). Not A or B: indemnification's recognition
architecture (a closed idiom enumeration) and cross-adapter fix propagation
(Finding #3's `S48-P-N-03`) are structural problems that repeated regex
patching has not resolved and, on this evidence, will not resolve by
continuing the same pattern of "find a failure, add a phrase to the
enumeration, declare 0 known WC, repeat" — Step 4A.8 is the fifth
demonstration that this specific loop produces green dashboards on
development corpora and new failures on the next independent one.

## AH. Hard-Gate Evaluation (Phase 21)

| Gate | Result |
|---|---|
| S4 > 0 | 0 — met |
| SM-CRITICAL > 0 | **16 — FAILED** |
| Policy-changing UNVERIFIED fact feeding CA > 0 | 2 (Section U) — **FAILED** |
| Repeated ordinary-drafting (Tier-1) S3 WC mechanism | 0 literal WC, but 15 Tier-1 SM-CRITICAL — **FAILED** in spirit and Section K's letter |
| Unsafe false-symmetry recurring systematically | 0 — met |
| False absence creating unsafe clean decision | 16 — **FAILED** |
| Wrong-provision substitution creating unsafe clean decision | 0 confirmed (Finding #4 was safe by coincidence, not a substitution into a clean decision) — met |
| Production code changed during validation | No — met |
| Corpus modified after seeing output except documented GTD | No — met |
| Determinism < 100% | No, 100% — met |

**Result: FAIL.** Four of ten hard gates failed; any one failure is
sufficient to block PASS.

## AI. Generalization-Gate Evaluation (Phase 22)

| Metric | Threshold | Actual | Met? |
|---|---|---|---|
| Overall WCDR | ≤ 8% | 8.8% | No (narrowly) |
| Tier-1 WCDR | ≤ 3% | 0.0% | Yes (see Section Y caveat) |
| Overall FE rate | ≤ 20% | 11.8% | Yes |
| Minimum overall Automation Recall | ≥ 55% | 62.7% | Yes |
| Minimum per-adapter Automation Recall | ≥ 45% | indemnification 3.2% | **No** |

Moot given the hard-gate failures above (Phase 21/22: generalization gates
cannot promote a PASS/FAIL determination the hard gates have already
settled), but recorded per the required methodology.

## AJ. Step 4A.8 Final Verdict

**FAIL — MORE HARDENING REQUIRED.**

## AK. Step 4B Recommendation

**NO — MORE HARDENING REQUIRED**, specifically on the currently-hardened
adapters before any expansion. Two concrete, scoped priorities emerge
directly from this report and should be the basis of the next hardening
step (not undertaken here, per Phase 23):

1. Indemnification's obligation-recognition mechanism needs an
   architectural review, not another idiom added to the enumeration —
   Finding #1 shows the enumeration approach has an unbounded false-negative
   surface against ordinary legal-drafting variation.
2. Indemnification's monetary-multiplier regex needs the same
   spelled-out-number accommodation liability already has (Finding #2) —
   this alone, if fixed, would likely resolve a large share of both the
   automation-recall failure and the UNVERIFIED-fact finding, and is the
   most mechanically straightforward of the findings in this report.

Both should go through the same discipline used in Steps 4A.7.3/4A.7.4
(root-cause, general fix, dedicated before/after benchmark, full regression
sweep) — and, per this report's own central finding, whatever comes out of
that hardening should itself be validated against a *third* independent
corpus before any Step 4B expansion is considered, since Step 4A.8 is now
direct evidence that passing on development/fresh-battery corpora does not
predict passing on the next unseen one.
