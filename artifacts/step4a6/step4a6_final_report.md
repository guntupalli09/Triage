# Step 4A.6 — Independent Frozen Held-Out Validation: Final Report

**Status: INDEPENDENT VALIDATION, NOT A DEVELOPMENT STEP.**
**Production code: FROZEN throughout. Verified byte-identical before, during, and after execution.**

---

## A. Frozen-code integrity

| | |
|---|---|
| Commit | `0c4ae5486d7b3cdfdbfbb40be114229aef3d6b58` (`0c4ae54`) |
| Branch | `claude/triage-counsel-audit-44xogk` |
| Git status (freeze) | clean |
| Git status (report time) | clean except new, untracked `benchmarks/step4a6_*` / `artifacts/step4a6/*` evaluation artifacts |
| Evaluated pipeline | `policy_engine_core.py`, `liability_policy_engine.py`, `indemnification_policy_engine.py`, `payment_terms_policy_engine.py` |
| PRE SHA-256 | recorded in `artifacts/step4a6/frozen_state.json` |
| POST SHA-256 | **byte-identical** to PRE, all 4 files, verified again at time of this report |
| Corpus checksum | `adcc1fe9b9fa5f468f284741e4becbc785f2488883674a88005249927b720fde` (`benchmarks/step4a6_checksums.json`) |
| Labels checksum | `c06601e90da4da067b0bfbd9f92af9324139b81b716e412ca4c378f33c001736` |
| Eval-config checksum | included per-file in `benchmarks/step4a6_checksums.json` (`run_step4a6_heldout.py` hash: `f3ce0d52ce5dcd336dd2be7d7008a0f3fbf18693354c46676613d8010af9c9f3`) |
| **Contamination status** | **CLEAN** |

Three mechanical bugs (wrong dataclass field names in three corpus `kwargs`
dicts: `prohibit_uncapped_exposure`→`prohibit_unlimited` on A6-L-10; a
non-existent `disputed_amounts_withholdable` kwarg removed from A6-P-18; a
`PayPolicy`-only `prohibit_set_off` kwarg removed from liability-adapter case
A6-C-24) were found and fixed **before lock**. These are evaluation-harness
configuration fixes, not label or ground-truth tuning.

---

## B. Corpus composition

| Adapter | Tier 1 | Tier 2 | Tier 3 | Automatable | Should Review | Total |
|---|---:|---:|---:|---:|---:|---:|
| Liability | 19 | 38 | 21 | 62 | 16 | 78 |
| Indemnification | 12 | 24 | 32 | 46 | 22 | 68 |
| Payment Terms | 20 | 33 | 13 | 55 | 11 | 66 |
| **Total** | **51** | **95** | **66** | **163** | **49** | **212** |

**Attack-family counts:**

| Family | n |
|---|---:|
| ordinary | 37 |
| varied | 35 |
| adversarial | 20 |
| compound | 30 |
| grammatical_subject | 12 |
| reciprocal_scope | 10 |
| role_definition | 8 |
| direction_invariance | 10 |
| ownership | 11 |
| silent_miss_attack | 14 |
| setoff_hard_negative | 6 |
| absence | 14 |
| structural | 5 |
| **Total** | **212** |

**Disclosed shortfall against stated family-size targets**, locked into
`benchmarks/step4a6_checksums.txt` **before execution**:

| Family | Actual | Target |
|---|---:|---|
| grammatical_subject | 12 | 25-30 (mandatory) |
| reciprocal_scope | 10 | 25-30 (mandatory) |
| role_definition | 8 | ≥20 |
| direction_invariance | 10 | ≥20 |
| silent_miss_attack | 14 | ≥25 |
| ownership | 11 | ≥25 |
| compound | 30 | ≥30 ✓ met |

These six families did not reach their stated minimums, disclosed before
locking rather than padded after seeing results. Findings in these families
should be read as directional at the achieved sample size — a larger sample
would plausibly surface more failures of the same kind, not fewer, given the
failure density already observed (e.g., ownership: 9/11 = 82% WC).

30 formatting mutations built from 30 distinct new base cases (does not count
toward the 212). 6 intentional compound-case companion-pair "duplicate"
texts, 37 distinct business domains, ~35-40 distinct role-name pairs — see
Section C.

---

## C. Diversity assessment

Full pre-lock audit in `artifacts/step4a6/diversity_report.md`. Summary:
212 semantic cases, 206 unique text bodies (the 6 repeats are intentional
compound companion pairs scoring the same document on two adapters, not
accidental duplication). No small set of templates with renamed entities —
sentence structures vary across plain single-obligation sentences (Tier 1),
heavily-qualified run-ons with boilerplate (Tier 2), passive-voice/
subordinate-clause constructions (grammatical-subject family), tabular/
field:value structures, multi-sentence cross-referencing definitions
(role-definition family), and two-sentence (not run-on) reciprocal
structures. Where a shape recurs intentionally (e.g., "X shall indemnify...
and Y shall indemnify... in each case..." for the reciprocal family), it is
because that shape is the object under test. No case, sentence skeleton, or
role-name pair is reused from Step 4A.2, Step 4A.4, or any Step 4A.5
benchmark/adversarial-battery file. This is not a paraphrased regression
corpus.

---

## D. Overall outcomes

| Outcome | Count | Rate |
|---|---:|---:|
| CA | 75 | 35.4% |
| CR | 27 | 12.7% |
| FE | 41 | 19.3% |
| **WC** | **50** | **23.6%** |
| **SM** | **10** | **4.7%** |
| GTD | 1 | 0.5% |
| Boundary-consistent* | 8 | 3.8% |

*Boundary-consistent = matches a pre-disclosed Step 4A.5 architectural
limitation (the SO-33 cost-of-cover/set-off boundary) or falls within a
ground-truth range I explicitly self-hedged as multiply-acceptable before
execution. Not a defect newly discovered by Step 4A.6.

One case (A6-C-12) is GTD: I labeled a 2x-royalty multiplier cap as expecting
`NEGOTIATE`, but 2.0 exactly equals the default policy's
`acceptable_max_multiplier` (2.0), so `ACCEPT` is the objectively correct
threshold outcome — my ground truth was wrong, not the system.

---

## E. Safety metrics

| Metric | Value |
|---|---:|
| WCDR (WC / automatic decisions, i.e. WC/(CA+WC)) | 50/125 = **40.0%** |
| Unsafe Case Rate (WC / valid cases) | 50/212 = **23.6%** |
| Silent Miss Rate (SM / valid cases) | 10/212 = **4.7%** |
| S1 | 3 |
| S2 | 37 |
| S3 | 6 |
| **S4** | **4** |
| **SM-CRITICAL** | **5** |

**S4 cases** (false-safe: a genuinely differentiated/asymmetric indemnification
provision silently resolved as if symmetric — see Section R): A6-I-12,
A6-I-18, A6-I-23, A6-I-35.

**SM-CRITICAL cases** (a policy-relevant provision's *entire existence*, or a
policy-prohibited term, silently disappears): A6-I-09, A6-I-10 (indemnification
obligation recognized as `obligations=[]` — total non-recognition of a
plainly-worded clause), A6-P-12, A6-P-14, A6-P-24 (prohibited set-off/netting
silently accepted, `setoff_permitted=None` despite correctly configured
policy and real netting language).

Both hard-blocker gates (S4>0, SM-CRITICAL>0) are independently triggered.

---

## F. Selectivity

| Metric | Value |
|---|---:|
| Automation Recall (CA/AUTOMATABLE) | 74/163 = **45.4%** |
| FE/AUTOMATABLE | 41/163 = **25.2%** |
| Automatic Decision Rate ((n-CR-FE)/n) | 144/212 = **67.9%** |
| CADR (CA/n) | 75/212 = **35.4%** |

All four warning-signal thresholds from the governing instructions are
crossed: Automation Recall (45.4% < 70%), FE/AUTOMATABLE (25.2% > 25%,
marginally), Liability adapter Automation Recall (19.4% < 60%), and Tier 1
Automation Recall (49.0%, materially below 90%).

---

## G. Per-adapter metrics

| Adapter | n | CA | CR | FE | WC | SM | Automation Recall | FE/AUTO | WCDR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Liability | 78 | 12 | 7 | 10 | **40** | 4 | 19.4% | 16.1% | 76.9% |
| **Indemnification** | 68 | 18 | 16 | 25 | **7** | 2 | 39.1% | 54.3% | 28.0% |
| Payment Terms | 66 | 45 | 4 | 6 | 3 | 4 | 81.8% | 10.9% | 6.25% |

**Indemnification** shows the lowest WCDR (28.0%) and lowest WC count (7) of
the three adapters — the reciprocal/differentiation and grammatical-subject
fixes from Step 4A.5 hold up comparatively well against *wrongness*, but
Indemnification's Automation Recall (39.1%) is still the second-worst of the
three, dragged down by a high FE rate (54.3%) — conservative rather than
unsafe, but far short of Step 4A.5's 82.9% frozen-corpus figure (Section O).
**Liability is the dangerous outlier**: WCDR of 76.9% means more than
three-quarters of its confident, non-review decisions in this corpus were
wrong, driven almost entirely by the single mechanism in Section F.1 below.

---

## H. Difficulty-tier metrics

| Tier | n | CA | CR | FE | WC | SM | Automation Recall | FE/AUTO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **1 (ordinary)** | 51 | 25 | 0 | 11 | **13** | 0 | 49.0% | 21.6% |
| 2 (varied) | 95 | 37 | 5 | 17 | **25** | 5 | 46.3% | 21.3% |
| 3 (adversarial) | 66 | 13 | 22 | 13 | 12 | 5 | 40.6% | 40.6% |

**Tier 1 is the most important number in this report.** On plain, ordinary,
non-adversarial commercial drafting, the WC rate is 13/51 = **25.5%**, and
Automation Recall is 49.0% — nowhere near the ≥90% standard this validation
was designed to check for. This is not a system that fails only under attack;
it fails on ordinary drafting at a materially higher rate than is acceptable
for any production automation claim. Per the explicit instruction ("If
ordinary drafting produces substantial FE/WC/SM, do not recommend
expansion"), Tier 1 alone is sufficient grounds not to expand.

---

## I. Grammatical-subject attack results

12 cases (target 25-30, not met — see Section B).

| CA | CR | FE | WC | SM |
|---:|---:|---:|---:|---:|
| 1 | 1 | 6 | 2 | 2 |

Root causes: the 2 WC and 2 SM cases involve subordinate-clause and
passive-voice constructions not present in the Step 4A.5 fix's training
examples, where the grammatical subject of the operative verb is a bystander
entity. FE (6/12) shows the system defaults to conservative escalation on
most fresh constructions it doesn't confidently resolve — safe, but far from
the "distinguish clear-ownership from genuinely-unresolvable" standard this
family is meant to test.

**Did the disclosed Step 4A.5 weakness reproduce? YES.** At a 4/12 = 33% rate
combining WC+SM, on a sample smaller than intended, this is not a resolved
weakness — it is a confirmed, recurring one under fresh wording.

---

## J. Reciprocal-scope attack results

10 cases (target 25-30, not met).

| CR | FE | WC |
|---:|---:|---:|
| 5 | 3 | 2 |

The 2 WC cases (A6-I-12, A6-I-18, both S4 — see Section E/R) demonstrate the
exact disclosed gap: the reciprocal equality check does not compare
`trigger_treatments`, so a fresh trigger-category exclusion or differentiated
causation standard (A6-I-23, a novel differentiation dimension not previously
anticipated by either generation, also WC/S4) passes as symmetric. 5
genuinely-symmetric control cases correctly resolved (CR), confirming the
mechanism is not simply broken — it has a specific, bounded, and still-open
gap.

**Did the disclosed weakness reproduce? YES.**

---

## K. Role/direction generalization

| Family | n | CA | CR | FE | WC | SM |
|---|---:|---:|---:|---:|---:|---:|
| role_definition | 8 | 1 | 1 | 1 | 4 | 1 |
| direction_invariance | 10 | 4 | 1 | 4 | 1 | 0 |
| ownership (bystander/candidate) | 11 | 0 | 1 | 0 | 9 | 0 |
| bystander discrimination (dedicated control benchmark, in-distribution) | 25 | — | — | — | — | — |

Role definition is the weakest of these families (4/8 WC = 50%), largely
driven by the same basis-word/entity-truncation mechanisms rather than a
role-definition-specific defect. Direction-invariance held up comparatively
well (1/10 WC). **Ownership is a severe outlier: 9/11 WC (82%)** — nearly
every candidate-ownership case in this corpus triggered the Section F.1
mechanism (multiple numeric candidates including a qualified-fee-noun
liability cap), which starved the ownership-resolution logic of a correctly
extracted candidate to disambiguate in the first place. The dedicated,
in-distribution `run_bystander_discrimination_benchmark.py` control (Section
X) still shows 100% recall / 88% precision — confirming the *bystander*
mechanism itself is intact; the ownership family's failures in this corpus
are downstream of extraction, not a bystander-discrimination regression.

---

## L. Payment recognition / silent-miss attacks

14 dedicated cases (target ≥25, not met) plus 6 set-off hard negatives.

**Payment SM = 4** (A6-P-12, A6-P-14, A6-P-24 — all SM-CRITICAL, confirmed
via direct `setoff_permitted=None` inspection — and A6-RB-06, a
non-critical external-delegation SM). All other recognition attacks in this
family (tax/VAT/withholding/ordinal-timing/dispute-window variants,
A6-P-06 through A6-P-23) resolved correctly (10/14 CA).

**Step 4A.5's SM elimination did NOT fully generalize.** It generalized well
to vocabulary variation within the categories it was tuned on (tax
allocation, timing, disputes), but the specific mechanism most explicitly
targeted by this attack family — set-off/netting described without
canonical vocabulary — still produces silent, undetected policy violations
on non-canonical phrasing ("recoup...independently obligated to remit" via
cross-referenced exhibit; pure net-difference description with zero
recognizer vocabulary; "true up" jargon).

---

## M. Set-off/netting attacks

| | Result |
|---|---|
| True positives correctly recognized | 8/11 (A6-P-06,07,08,10,15,21,22,23 type true positives among silent_miss_attack + dedicated set-off cases) |
| True positives silently missed (SM) | 3 (A6-P-12, A6-P-14, A6-P-24) |
| Hard negatives correctly NOT triggered | 11/11 (A6-P-11, 25, 26, 28, 29, 30 plus the dedicated `setoff_hard_negative` family, 5/6 with A6-P-27 boundary-consistent) |
| False positives (hard negative wrongly flagged) | 0 |
| False negatives (true positive wrongly cleared) | 3 (same as SM above) |
| WC attributable to set-off specifically | 0 (failures here are pure silent misses, not confident wrong values) |
| SM attributable to set-off specifically | 3, all SM-CRITICAL |

The dedicated, in-distribution `run_setoff_concept_benchmark.py` control
still reports 97.6% recall / 100% precision (Section X) — unchanged from
Step 4A.5. The independently-constructed attack corpus in this step
demonstrates that recall figure does not extend to genuinely novel netting
vocabulary. **The system has not "solved silent misses by massively
over-recognizing ordinary credits/deductions"** — precision on hard negatives
remains perfect — but it has not solved the underlying recall gap either; it
has simply not yet been asked, until now, about phrasing far enough outside
its tuned vocabulary.

---

## N. Liability ownership

Candidate/value/basis ownership performance in this corpus is poor: 9/11
(82%) of the dedicated `ownership` family produced WC. Inspection (Section
F.1/R) shows this is not a contamination or cross-candidate confusion
problem — the dedicated distractor mechanisms (insurance limits, SLA
credits, termination fees, rent, reversed-direction premiums, stacked
distractors) are, where checked, correctly excluded as candidates. The
failure is upstream: the genuine liability-cap candidate itself frequently
fails to extract at all (Section F.1's basis-word-modifier gap), leaving
the ownership-resolution stage with no correct candidate to select, and the
adapter falls through to a default `MUST_REDLINE`/"no cap found" state
that is wrong not because ownership was misattributed, but because the
value was never seen.

---

## O. Indemnification selectivity

Independent Step 4A.6 Automation Recall for Indemnification: **39.1%**
(18/68 cases... using the AUTOMATABLE-labeled denominator specifically:
18 CA / 51 AUTOMATABLE-labeled indemnification cases = **35.3%**).

This does **not** reproduce Step 4A.5's frozen-corpus figure of 82.9%, and
sits closer to (though still above) Step 4A.4's original pre-hardening
37.1%. This is the most direct evidence in this report that Indemnification's
Step 4A.5 improvement was substantially a fit to the Step 4A.4 corpus's
specific vocabulary and structures rather than a generalized fix: the
underlying mechanisms (reciprocal differentiation, role resolution,
obligation-verb recognition) each show confirmed, independently-verified
gaps in this corpus (Sections F.3, J, K) that did not exist — or were not
detectable — in the corpus that measured the 82.9% figure. Indemnification's
WCDR (28.0%) is the best of the three adapters, meaning what it *does*
resolve confidently is comparatively more often right than Liability's — but
it resolves far less than Payment Terms, and its FE/AUTOMATABLE (54.3%) shows
the conservatism did not translate into correctness so much as into
deferral.

---

## P. Compound cases

30 cases, 6 companion pairs testing cross-adapter/cross-clause independence.
Outcome distribution: CA=9, CR=5, FE=7, WC=8, GTD=1.

**No logically inconsistent adapter outputs were observed** between companion
pairs (e.g., A6-C-22/23's deliberately-conflicted-liability +
deliberately-clean-indemnification pair correctly kept the two clauses'
ambiguity from leaking into each other in both directions). The 8 WC in this
family are attributable to the same root causes already identified
elsewhere (6 to Section F.1's basis-word-modifier gap on the liability side
of a compound document — A6-C-04, A6-C-07, A6-C-16, A6-C-19, A6-C-24,
A6-C-27/30; 2 to the reciprocal-scope gap — A6-C-15), not to any new
cross-adapter contamination mechanism. The interaction engine itself was not
modified and no evidence surfaced of a defect specific to combining
adapters.

---

## Q. Absence/recognition results

**YES — policy-relevant provisions existed but failed to produce either a
finding or a review condition, on 6 confirmed occurrences:**

| Case | Adapter | What existed | What happened |
|---|---|---|---|
| A6-L-41 | Liability | Clean 2x general cap, with category caps tracked separately | `NOT_APPLICABLE` — cap invisible |
| A6-L-48 | Liability | Clean buy-side role resolution via Licensee's own conduct | `NOT_APPLICABLE` — resolved as if nothing found |
| A6-L-50 | Liability | Clean sell-side resolution via Operator's own licensing conduct | `NOT_APPLICABLE` |
| A6-L-56 | Liability | Clean, unambiguous proviso-qualified cap | `NOT_APPLICABLE` |
| A6-I-09 | Indemnification | A full indemnify/defend/hold-harmless obligation, phrased with an outer "covenants and agrees...to" wrapper | `obligations=[]` — the clause is invisible to the recognizer |
| A6-I-10 | Indemnification | A full indemnification obligation phrased as "make whole for" / "assume the defense of" | `obligations=[]` |

Additionally, A6-P-12/14/24 (Section L/M) are a variant of this same concern
specific to a *sub-fact* rather than an entire clause: the payment clause is
recognized, but the set-off/netting sub-fact within it silently disappears
(`setoff_permitted=None`), and A6-RB-06's genuinely-ambiguous external
delegation likewise resolves to `NOT_APPLICABLE` rather than surfacing for
review.

This is a direct, repeated, independently-confirmed instance of Lee's
original concern: rules fire on what they find, and multiple genuinely
present, policy-relevant provisions in this corpus produced neither a
finding nor a review condition.

---

## R. Wrong-clean analysis

50 WC total. Grouped by root-cause mechanism (full case-by-case detail in
`artifacts/step4a6/step4a6_case_classification.json`):

| Mechanism | Cases | Severity | Adapter(s) | Shared/Local |
|---|---:|---|---|---|
| Basis-word-with-modifier regex miss (multiplier/basis extraction requires bare "annual fees/rent/royalty/premiums/charges"; fails on any domain modifier, e.g. "annual distribution fees") | 32 | S1 (3), S2 (29) | Liability, Indemnification | **Shared**, dominant mechanism |
| Long qualifying/exception preamble defeats extraction window before the cap value | 2 | S2 | Liability | Shared |
| Fixed-dollar "shall not be liable...for...exceeding $X" object-phrasing miss | 1 | S2 | Liability | Local variant of same extraction family |
| Reciprocal-pair trigger-level/causation-standard differentiation not compared, passes as symmetric | 4 | **S4** | Indemnification | Shared (disclosed Step 4A.5 residual weakness, confirmed recurring) |
| Genuinely-ambiguous case resolved without review flag (role mapping, deferred/未executed payment terms, conflicting Net-30 definition, open-ended future qualifier, ambiguous external delegation) | 6 | S3 | Liability, Payment Terms, Indemnification | Mixed, no single shared mechanism |
| Generic role-mapping unresolved but no directional verb recognized, yet resolved automatically | 1 | S3 | Liability | Local |
| GTD (my own threshold-math error) | — | n/a | — | Not a system defect |

**Every WC case, expected/actual, severity, adapter, and earliest failure
stage is recorded in `artifacts/step4a6/step4a6_case_classification.json`.**
The earliest failure stage for the dominant 32-case mechanism is
**extraction** (the multiplier/basis regex never populates
`general_cap_expression.components`, verified directly via
`extract_liability_facts()`); it is not a downstream policy-evaluation or
review-gate defect — the fact is simply never seen.

---

## S. Silent-miss analysis

10 SM total, 5 SM-CRITICAL:

| Case | Adapter | What was missed | SM-CRITICAL? |
|---|---|---|---|
| A6-L-41 | Liability | Clean general cap | No |
| A6-L-48 | Liability | Clean role resolution | No |
| A6-L-50 | Liability | Clean role resolution | No |
| A6-L-56 | Liability | Clean, unambiguous proviso cap | No |
| A6-I-09 | Indemnification | Entire indemnification obligation (synonym-verb phrasing) | **Yes** |
| A6-I-10 | Indemnification | Entire indemnification obligation ("make whole"/"assume the defense of") | **Yes** |
| A6-P-12 | Payment Terms | Prohibited recoupment/set-off via cross-referenced exhibit | **Yes** |
| A6-P-14 | Payment Terms | Prohibited netting, described with zero recognizer vocabulary | **Yes** |
| A6-P-24 | Payment Terms | Prohibited netting ("true up" jargon) | **Yes** |
| A6-RB-06 | Payment Terms | Genuinely ambiguous external payment-period delegation | No |

All 5 SM-CRITICAL cases were independently verified by direct inspection of
`extract_*_facts()` output (not inferred from the policy decision alone).

---

## T. False-escalation analysis

41 FE, grouped:

- **Conservative-direction root causes tied to the same extraction gaps that
  cause WC elsewhere** (e.g., an ambiguous-looking multiplier basis
  triggering `REQUIRES_REVIEW` rather than `MUST_REDLINE`/`ACCEPT`): a
  meaningful minority, concentrated in Indemnification (25 of 41 total FE are
  in Indemnification alone).
- **Broad conservatism on fresh grammatical-subject constructions**: 6 of 12
  grammatical_subject-family cases resolved as FE rather than a confident
  correct or incorrect result — the system defaults to escalation when it
  cannot confidently resolve a novel subordinate-clause/passive-voice
  structure, which is safe but limits usefulness.
- **Tier 3 concentration**: FE/AUTOMATABLE is 40.6% at Tier 3 versus ~21% at
  Tiers 1-2 — adversarial drafting does push more cases to conservative
  escalation, as intended, but Tier 1's own 21.6% FE/AUTOMATABLE is still
  well above the ≤25% comfort threshold's margin and, combined with Tier 1's
  25.5% WC rate, shows FE is not simply "safety absorbing the risk that would
  otherwise be WC" — both are elevated together.

**FE remains adapter-concentrated (Indemnification) rather than
architecture-wide**, but is not confined to a single narrow mechanism the way
the dominant WC cause is — it reflects broad conservatism across several
Indemnification recognition/differentiation paths simultaneously.

---

## U. Formatting robustness

30 mutations across ALL-CAPS, mid-sentence line breaks, semicolons replacing
periods, bulleted/numbered/lettered lists, quoted-term variants (including
straight-vs-curly-quote), OCR-like whitespace, heading removal/insertion, and
unrelated-boilerplate-paragraph merging, built from 30 distinct new base
cases spanning all three adapters and compound documents.

**29/30 (96.7%) preserved the base case's actual output state exactly.**

One mutation flipped: `A6-L-46-FMT-caps` (ALL-CAPS transformation of a
grammatical-subject-attack case) changed from `REQUIRES_REVIEW` (base) to
`ACCEPT` (mutated) — a genuine, independently-discovered case-sensitivity
gap in the grammatical-subject/role-recognition path, not previously
identified. This is an additional, smaller-scale confirmation of the same
family of fragility documented in Section I/F.

---

## V. Determinism

The full 212-case + 30-mutation corpus was executed twice via
`benchmarks/run_step4a6_heldout.py`, unmodified, with no intervening changes.
`diff` between the two complete raw outputs returned **zero differences**.
**100% deterministic**, as required.

---

## W. Historical controls

### Step 4A.4 (control only — not part of Step 4A.6's own held-out metrics)

`python3 benchmarks/classify_step4a4.py` →
`{'CA_CANDIDATE': 113, 'FE': 19, 'CR': 38, 'WC_CANDIDATE': 2}` — an **exact**
reproduction of the frozen Step 4A.5 state, including the same 2 raw
heuristic WC_CANDIDATE rows (A4-H-04, A4-H-05) that the original Step 4A.5
report already manually resolved to defensible non-WC outcomes (reported
final: WC=0, SM=0). This confirms the harness and frozen production code
behave identically to Step 4A.5's frozen state — the Step 4A.6 findings above
are a genuine out-of-distribution generalization gap, not evaluation
environment drift.

### Step 4A.2 (control only)

`python3 benchmarks/classify_step4a2_v2.py` reproduces its historical raw
auto-bucket shape: `{'NEEDS_MANUAL': 40, 'FE': 25, 'CR': 30, 'CA': 16, 'WC':
7}`. Given time constraints, the 7 raw `WC` and 40 `NEEDS_MANUAL` rows were
**not** individually re-triaged to a fresh WC=0/SM=0/S4=0 confirmation at
full manual rigor in this pass — the original Step 4A.2/4A.5 reports already
performed that work and reported WC=0/SM=0/S4=0. This control confirms the
corpus still runs and produces the same raw distribution shape on frozen
code; it is disclosed as a partial, not full, re-verification of that
historical conclusion.

---

## X. Existing benchmark controls

All re-run unmodified against frozen code:

| Benchmark | Result |
|---|---|
| `run_liability_benchmark.py` (Liability-125) | 1 known pre-existing failure (`unheaded-08`, unquantified_cap) — unchanged from Step 4A.5 |
| `run_indemnification_benchmark.py` (Indemnification-100) | 1 known pre-existing failure (`cap-excluded-01`) — unchanged |
| `run_payment_terms_benchmark.py` (Payment-84) | 0 failures |
| `run_role_resolution_benchmark.py` | Conflict precision 100%, recall 94.4%, false-conflict rate 0% |
| `run_liability_concept_benchmark.py` | ran clean, no reported failures |
| `run_payment_recognition_benchmark.py` | Recall 100% (45/45), precision 95.7% |
| `run_liability_ownership_benchmark.py` | 42/42 correct, 0 false-safe |
| `run_indemnification_asymmetry_benchmark.py` | 19/19 scored correct, 0 false-safe |
| `run_setoff_concept_benchmark.py` | Recall 97.6% (41/42), precision 100% |
| `run_role_boundary_benchmark.py` (multi-word role) | 100% recall/precision |
| `run_bystander_discrimination_benchmark.py` | Recall 100% (22/22), precision 88.0% |
| `run_direction_invariance_benchmark.py` | 37/40 correct, 3 unsafe-automatic (pre-existing, disclosed) |
| `run_step4a5_adversarial_battery.py` | matches its documented compound-mechanism REQUIRES_REVIEW behavior |

All confirm the frozen implementation behaves exactly as it did at the end of
Step 4A.5 on its own in-distribution controls. The Step 4A.6 findings are
additive evidence about out-of-distribution generalization, not evidence of
drift or regression.

---

## Y. Regression suite

`python3 -m pytest tests/ -q --continue-on-collection-errors` →
**1157 passed, 10 failed, 13 skipped, 43 errors** — an **exact match** to the
Step 4A.5 baseline. No delta, no regression.

---

## Z. Cross-generation analysis

| Generation | Corpus | Headline failure signature |
|---|---|---|
| Step 4A.2 | Original discovery | Recognition/absence + confident-but-wrong extraction, broad |
| Step 4A.4 | Second independent frozen corpus | CA=81/FE=39/WC=12/SM=12/SM-CRITICAL=1 across role resolution, symmetry/reciprocal handling, obligation-recognition vocabulary |
| **Step 4A.6** | **Third independent frozen corpus (this report)** | **WC=50/SM=10/SM-CRITICAL=5/S4=4**, dominated by a single extraction-stage mechanism (basis-word-with-modifier regex miss) plus recurrence of the two Step 4A.5-disclosed residual weaknesses |

**Are the same architectural failures recurring under new language? Yes,
directly.** Two of Step 4A.5's own explicitly-disclosed residual weaknesses
(grammatical-subject misattribution, reciprocal-pair trigger-level scope
exclusion) reproduce in this corpus at the same conceptual mechanism, just
under fresh wording (Sections I, J). More significantly, the *general
pattern* that drove Step 4A.4's original findings — confident extraction
that silently fails on drafting variation the tuning corpus didn't include —
recurs as the single dominant Step 4A.6 mechanism (Section F.1/R), just
relocated to a different specific regex (multiplier basis-word matching
rather than the mechanisms Step 4A.4 originally found). This is the most
important conclusion of this report: **each hardening pass has fixed the
specific failures its own tuning corpus surfaced, without addressing the
general property — narrow, literal-pattern extraction that does not
generalize to drafting variation outside its tuning distribution — that
keeps producing new instances of the same failure class.** The percentages
are not comparable across generations (different corpora, different
distributions), but the recurrence of the *mechanism shape* is comparable,
and it has recurred a third time.

---

## Product-readiness questions (answered from evidence only)

**1. Does independent evidence now support that confidently wrong extraction
is being prevented rather than merely patched on known examples?** No.
Section F.1/R demonstrates, via direct extraction inspection, that a single
narrow regex condition (bare "annual fees" vs. any qualified variant)
determines whether a real, quantified liability cap is seen at all — and
when it is not seen, the system does not merely escalate, it asserts a
confident, wrong `MUST_REDLINE`. This is the same class of failure Step
4A.4 found and Step 4A.5 patched for its own specific triggers; it recurs
here for a different specific trigger.

**2. Does independent evidence support that policy-relevant provisions are
not silently disappearing?** No. Section Q lists 6 confirmed occurrences of
an existing, policy-relevant provision producing neither a finding nor a
review condition, plus 3 further confirmed instances where a sub-fact
(prohibited set-off) silently disappears within an otherwise-recognized
clause.

**3. Is verify-or-review generalizing to unseen drafting?** Partially. The
review gate correctly triggers on the majority of genuinely ambiguous
Tier 3 cases (CR=22/66 at Tier 3, the highest CR share of any tier) and on
most hard-negative controls (set-off, bystander discrimination). It does not
generalize on the reciprocal-scope differentiation family (4 confirmed S4
misses) or on several individually-varied absence/ownership cases.

**4. Is the system still over-escalating ordinary automatable language?**
Yes, but this is now the *secondary* concern relative to under-escalating
(WC). Tier 1 FE/AUTOMATABLE is 21.6%; Tier 1 WC is 25.5%. Both are elevated
simultaneously — the system is neither uniformly over-cautious nor uniformly
overconfident; it is inconsistent in a way that tracks the specific
extraction mechanism in play for each case.

**5. Is Indemnification now useful enough automatically?** No. Independent
Automation Recall (35.3% of AUTOMATABLE-labeled cases; 39.1% of all
Indemnification cases) sits far below Step 4A.5's frozen-corpus 82.9% and
close to Step 4A.4's original 37.1%. See Section O.

**6. Do the two disclosed 4A.5 weaknesses remain material?** Yes, both
confirmed recurring under fresh wording (Sections I, J), including 4 of the
reciprocal-scope failures rated S4 (the most severe WC category).

**7. Would you trust this implementation for a supervised historical-contract
pilot where a lawyer still reviews the output?** Only if "review" means a
human independently re-reads every liability-adapter output rather than
relying on the system's stated confidence — because the dominant failure
mode here is not "the system flags uncertainty," it is "the system states a
specific, well-formed, wrong conclusion with no visible uncertainty marker"
(Section F.1's `extracted_summary` example). A lawyer who trusted the
system's own confidence signal, rather than independently re-reading every
output, would be materially misled on roughly a quarter of liability
determinations and on confirmed asymmetric-indemnification and
prohibited-set-off cases. That is not what "supervised pilot" is generally
understood to mean in practice, and I would not represent this
implementation as ready for that pilot mode without the Section K
remediation recommendation being completed first.

---

## Verdict

# FAIL — ARCHITECTURAL REDESIGN REQUIRED (of the extraction layer specifically)

More precisely, of the four options, this sits at **HARDENING REQUIRED**,
escalated by the following consideration: the failure is not confined to a
bounded, describable set of edge cases (which "HARDENING REQUIRED" alone
would imply is fixable by targeted patches) — the same *shape* of failure
(narrow literal-pattern extraction that silently fails outside its exact
tuning distribution) has now recurred across three independent validation
generations (4A.2, 4A.4, 4A.6) against three different specific triggers each
time. Given the explicit instruction that "FAIL — ARCHITECTURAL REDESIGN
REQUIRED" applies "only if the new corpus demonstrates that the current
architecture fundamentally cannot distinguish verified evidence from
unsupported assumptions," and given Section F.1's repeated demonstration that
a confident, specific, wrong claim (`"no numeric general cap stated"`) is
produced with no distinguishable difference in presentation from a correct
one — the same traceable, well-formed `extracted_summary` format regardless
of whether the extraction succeeded — the evidence supports the stronger of
the two failing verdicts. **HARDENING REQUIRED is the floor; the recurrence
across three generations is evidence the floor may not be sufficient**,
and is reported as a genuine, unresolved tension between the two verdict
options rather than resolved by fiat. Do not proceed as though this were a
routine HARDENING REQUIRED finding without weighing the cross-generation
recurrence in Section Z.

Independent of which of these two labels is preferred: **S4>0 and
SM-CRITICAL>0 are both independently confirmed. Step 4B may not begin under
this implementation's current state, under any verdict label.**

---

## Step 4B decision

- **Safety ready for controlled Step 4B expansion?** **NO.**
- **Selectivity ready?** **NO.**
- **Overall: DO NOT BEGIN STEP 4B.**

No "controlled" partial Step 4B is recommended. The dominant failure
mechanism (Section F.1) is not isolated to a narrow, excludable slice of
drafting — it is triggered by an ordinary, common construction ("annual
[domain-word] fees") across the Liability adapter, one of the three adapters
this system is meant to cover, and a "controlled" rollout limited to
Payment Terms alone would still carry the confirmed SM-CRITICAL set-off/
netting gap (Section L/M). There is no currently-defensible restricted scope
under which Step 4B could safely begin.

The defensible next step is a **Step 4A.7 remediation-and-re-validation
cycle**: fix the three root-caused mechanisms in Sections F.1/F.3/L in
production code (now permitted, since Step 4A.6 is complete and its verdict
recorded), specifically by generalizing the extraction mechanism's pattern
matching rather than adding more literal trigger phrases one at a time (the
approach that produced the recurrence documented in Section Z), then run a
**new**, independently-constructed held-out corpus (not this one, not a
mutation of this one) before any Step 4B consideration.

---

# Lee Challenge Status

### Concern 1 — Confident but wrong extraction
**STRONGLY ADDRESSED — as a confirmed, unresolved risk, not as a solved
problem.** This report does not merely acknowledge the risk exists in the
abstract; Section F.1/R demonstrates it directly and repeatedly (32+
confirmed instances, verified via direct `extract_liability_facts()`
inspection, not inferred from the policy decision alone). Independent
attacks confirm the mechanism at meaningful scale, in ordinary (Tier 1)
drafting. The verifier that exists in production code did not catch or
prevent any of these — the confidently wrong `MUST_REDLINE` states were
returned as final, non-review, authoritative outcomes.

### Concern 2 — Recognition/absence
**STRONGLY ADDRESSED — as a confirmed, unresolved risk.** Section Q lists 6
directly-verified occurrences of total non-recognition (`obligations=[]`,
`NOT_APPLICABLE` on a clean resolvable clause) plus 3 further confirmed
sub-fact disappearances (prohibited set-off silently accepted). Both are
direct, verified instances of the system being unable to distinguish "clause
genuinely absent" from "clause present, vocabulary or construction not
recognized."

### Concern 3 — False confidence from traceability
**STRONGLY ADDRESSED.** Section F.1's `extracted_summary` example is the
clearest demonstration available: the system's traceable, well-formed,
specific explanation (`'Limitation-of-liability clause present but no
numeric general cap stated'`) is confidently false — the cap is present and
quantified in the source text. The presence of a clear, specific evidence
trail did not correlate with the correctness of the underlying extraction;
if anything, the specificity of the false claim makes it more, not less,
likely to be trusted by a downstream reader than a vaguer hedge would be.

No credit is given here merely because production code contains verification
logic (defined-term-conflict checks, differentiation checks, ownership
resolution) — those mechanisms exist and, per Section X, perform well **on
their own in-distribution controls**. The finding is that independent,
freshly-drafted attacks demonstrate real, repeated, non-adversarial failure
**upstream** of those verifiers, in extraction and recognition, which no
amount of downstream verification logic can correct if the fact was never
extracted or the clause was never recognized in the first place.

---

## Known limitations of this validation

- Six mandated attack families did not reach their stated minimum sample
  sizes (Section B); findings in those families are directional, not
  exhaustive, and the achieved failure density suggests a larger sample
  would surface more, not fewer, failures.
- The Step 4A.2 control (Section W) reproduces its raw bucket shape but was
  not independently re-triaged to a fresh WC=0/SM=0/S4=0 confirmation at
  full manual rigor in this pass.
- Severity classification (S1-S4) for all 50 WC cases was completed in this
  pass (Section E/R), but relied on my own judgment applied consistently
  against the stated definitions rather than a second independent reviewer.

These limitations affect completeness of coverage, not the direction of the
verdict: the hard-blocker conditions in Section E (S4>0, SM-CRITICAL>0) are
independently over-determined by directly-verified evidence and would not be
reversed by closing any of the gaps above.
