# Step 4A.6 — Independent Frozen Held-Out Validation: Final Report

**Status: INDEPENDENT VALIDATION, NOT A DEVELOPMENT STEP.**
**Production code: FROZEN throughout. No production file was modified. Verified byte-identical pre/post via SHA-256 (Section B).**

---

## A. Purpose and scope

Step 4A.5 hardened the Liability, Indemnification, and Payment Terms adapters
against corpora built, in part, with knowledge of prior failures, and reported
excellent numbers on that evidence: CA=113/FE=19/WC=0/SM=0/SM-CRITICAL=0/S4=0,
Automation Recall=85.6%, FE-Automatable=14.4% (frozen at commit `0c4ae54`).

Those are **development results**. Step 4A.6 exists to determine whether they
**generalize** to a genuinely new distribution of contract drafting that was
never used to design, tune, or select the implementation. This report presents
that evidence, without protecting the Step 4A.5 numbers, without optimizing the
corpus for success, without fixing anything found, and without softening any
classification after the fact.

**Headline finding: the improvements do NOT fully generalize.** A single,
repeated extraction-stage defect — not an adversarial edge case, but an
ordinary drafting convention — causes confidently wrong results across roughly
half of all liability-adapter cases in this corpus, including cases drafted at
Tier 1 (ordinary) difficulty. Two further, independent recognition-stage gaps
were found in payment-terms set-off/netting detection and indemnification
verb-phrase recognition. Full detail follows.

---

## B. Frozen-integrity verification

| | |
|---|---|
| Base commit | `0c4ae5486d7b3cdfdbfbb40be114229aef3d6b58` (`0c4ae54`) |
| Branch | `claude/triage-counsel-audit-44xogk` |
| Git status at freeze | clean |
| Git status at report time | clean except new, untracked `benchmarks/step4a6_*` and `artifacts/step4a6/*` files (evaluation artifacts only) |
| Evaluated pipeline (4 files) | `policy_engine_core.py`, `liability_policy_engine.py`, `indemnification_policy_engine.py`, `payment_terms_policy_engine.py` |
| SHA-256 pre-execution | recorded in `artifacts/step4a6/frozen_state.json` |
| SHA-256 post-execution | **byte-identical** to pre-execution, all 4 files |
| Contamination status | **CLEAN** |

No production code, regex, recognizer, vocabulary, threshold, policy logic, or
escalation behavior was changed at any point during corpus construction,
locking, execution, or analysis. Three mechanical bugs were found and fixed
**before lock** in the evaluation harness itself (wrong dataclass field names
in three corpus `kwargs` dicts — `prohibit_uncapped_exposure` →
`prohibit_unlimited` on A6-L-10; a non-existent `disputed_amounts_withholdable`
kwarg removed from A6-P-18; a `PayPolicy`-only `prohibit_set_off` kwarg removed
from the liability-adapter case A6-C-24). These are evaluation-configuration
fixes, not label or ground-truth tuning, and occurred entirely pre-lock.

---

## C. Corpus construction summary

212 semantic cases + 30 formatting mutations, built from scratch with no reuse,
paraphrase, or synonym-substitution of any case from Step 4A.2, Step 4A.4, or
any Step 4A.5 benchmark/adversarial-battery file (verified in
`artifacts/step4a6/diversity_report.md`, written and judged acceptable
**before** locking).

| Adapter | Cases (incl. compound rows) |
|---|---|
| Liability | 78 |
| Indemnification | 68 |
| Payment Terms | 66 |
| **Total (semantic)** | **212** |

| Tier | Cases | Share |
|---|---|---|
| Tier 1 (ordinary) | 51 | 24.1% |
| Tier 2 (varied) | 95 | 44.8% |
| Tier 3 (adversarial) | 66 | 31.1% |

| Label | Cases | Share |
|---|---|---|
| AUTOMATABLE | 163 | 76.9% |
| SHOULD_REVIEW | 49 | 23.1% |

37 distinct business domains, ~35-40 distinct role-name pairs, 6 intentional
compound-case companion-pair "duplicate" texts (documented, not accidental).

**Disclosed shortfall against stated family-size targets** (locked into
`benchmarks/step4a6_checksums.txt` **before** execution, not after seeing
results):

| Family | Actual | Target |
|---|---|---|
| grammatical_subject | 12 | 25-30 (mandatory) |
| reciprocal_scope | 10 | 25-30 (mandatory) |
| role_definition | 8 | ≥20 |
| direction_invariance | 10 | ≥20 |
| silent_miss_attack | 14 | ≥25 |
| ownership | 11 | ≥25 |
| compound | 30 | ≥30 ✓ met |

These six families did not reach their stated minimums. This is a genuine
corpus-coverage limitation of this validation, disclosed honestly rather than
padded post hoc. The findings below concerning these families should be read
as directional, not exhaustive — a larger sample in these families would very
plausibly surface more failures of the same kind, not fewer, given the failure
density already observed at the smaller sample sizes actually achieved.

Corpus locked via SHA-256 (`benchmarks/step4a6_checksums.txt`,
`benchmarks/step4a6_checksums.json`) before any execution. No case text,
label, expected result, tier, or family was modified after lock. The
corrections applied during result classification (Section E) were to my own
outcome classification/root-causing, not to the locked corpus.

---

## D. Execution and determinism

Single held-out execution via `benchmarks/run_step4a6_heldout.py` (reusing
`run_case` from `run_step4a4_heldout.py` for methodological consistency with
Step 4A.2 and Step 4A.4). Executed twice; **outputs were byte-identical**
(`diff` returned no differences) — 100% determinism confirmed. No case was
re-run individually. No result was used to select, filter, or modify the
corpus.

---

## E. Outcome classification (212 semantic cases)

Classification began from an automated match between each case's actual
`STATE` and its `expected_result` text, used strictly as a **starting point**,
per the explicit no-heuristic-as-final-authority instruction. That crude
matcher produced 133 raw "mismatches." Every one of those 133 was individually
inspected — root-caused where systemic, spot-verified against direct
`extract_*_facts()` output where the mechanism was unclear — and reclassified.
32 cases required this correction because my own free-text `expected_result`
field ("depends on policy threshold," "must NOT trigger setoff," "AUTOMATABLE
target: engage") could not be string-matched by the crude classifier even
though the actual outcome was correct; these were reclassified to CA after
manual confirmation, not discarded.

**Final classification, all 212 cases:**

| Outcome | Count | Share |
|---|---|---|
| CA (Correct Automation) | 75 | 35.4% |
| CR (Correct Review) | 27 | 12.7% |
| FE (False Escalation — safe, costs automation) | 41 | 19.3% |
| **WC (Wrong Conclusion — confidently wrong)** | **51** | **24.1%** |
| **SM (Silent Miss — evidence present, not surfaced)** | **9** | **4.2%** |
| GTD (Ground Truth Defect — my own label error) | 1 | 0.5% |
| Boundary-consistent (matches a pre-disclosed Step 4A.5 limitation, or falls within my own self-hedged expected range) | 8 | 3.8% |

**By AUTOMATABLE-labeled cases (163):** CA=74 (45.4%), FE=41 (25.2%),
**WC=35 (21.5%)**, **SM=9 (5.5%)**, boundary=3, GTD=1.

**By SHOULD_REVIEW-labeled cases (49):** CR=27 (55.1%), **WC=16 (32.7%)**,
boundary=5, CA=1 (a control case correctly and safely auto-resolved).

**By tier:**

| Tier | n | CA | CR | FE | WC | SM |
|---|---|---|---|---|---|---|
| 1 (ordinary) | 51 | 25 | 0 | 11 | **13** | 0 |
| 2 (varied) | 95 | 37 | 5 | 17 | **26** | 4 |
| 3 (adversarial) | 66 | 13 | 22 | 13 | **12** | 5 |

**By adapter:**

| Adapter | n | CA | CR | FE | WC | SM |
|---|---|---|---|---|---|---|
| Liability | 78 | 12 | 7 | 10 | **40 (51.3%)** | 4 |
| Indemnification | 68 | 18 | 16 | 25 | **7 (10.3%)** | 2 |
| Payment Terms | 66 | 45 | 4 | 6 | **4 (6.1%)** | 3 |

**Tier 1 (ordinary drafting, the primary product-readiness signal per the
governing instructions) shows a 25.5% WC rate.** This is not an
adversarial-only failure. The implementation fails on plain, non-pathological
commercial drafting at a rate that would be unacceptable in production.

---

## F. Root-cause analysis

### F.1 — Dominant mechanism: basis-word-with-modifier regex miss (liability + indemnification monetary extraction)

**Root cause.** `liability_policy_engine.py`'s multiplier-cap basis-word
regexes (`_MULTIPLIER_NUM_RE`, `_MULTIPLIER_WORD_RE`) require the token
immediately following "annual" to **be** the basis word itself (`fees`,
`rent`, `royalty`/`royalties`, `premiums`, `charges`, etc.). Real commercial
drafting routinely qualifies that noun with a domain-specific modifier —
"annual **distribution** fees," "annual **installation** fees," "annual
**service** fees," "annual **franchise royalty** fees," "annual **storage**
fees" — and the regex simply does not match when any word intervenes between
"annual" and the basis noun.

**Verified directly.** `extract_liability_facts()` on
`"...aggregate liability shall not exceed 1 times the annual distribution fees paid..."`
(A6-L-05) returns `general_cap_expression=CapExpression(structure='simple',
components=[], ...)` — an empty cap, despite the multiplier and basis being
stated in plain English immediately adjacent to the exact canonical trigger
phrase `"shall not exceed"`. The parallel case with bare "annual fees"
(A6-L-01) extracts correctly.

**Consequence.** When no cap is extracted, the downstream policy path
concludes `"Limitation-of-liability clause present but no numeric general cap
stated"` and returns **MUST_REDLINE** — the most alarming, decisive state the
adapter has, asserting that a contract has *no* liability protection when in
fact a fully quantified, often favorable cap is present in the text. This is
not merely an escalation (safe); it is a **confident, wrong, actionable claim**
that directly misrepresents the contract to whoever reads the output.

**Scale.** Confirmed by direct regex/extraction testing across 32 of the 51
liability WC cases (63%), spanning Tier 1 ordinary drafting (A6-L-05, A6-L-08,
A6-L-09, and others) through Tier 2/3 variants, and recurring in
indemnification's parallel monetary-multiplier extraction (A6-I-04, A6-I-22,
and others share the identical regex family). A related but distinct variant
— a long qualifying/exception preamble ("Notwithstanding anything... except as
otherwise provided in Section 11...") pushing the actual cap value outside the
extractor's matching window — accounts for a further handful (A6-L-11,
A6-C-07). A third, separate variant affects the fixed-dollar cap trigger
`"shall not be liable...for...exceeding $X"` phrasing (A6-L-04), which also
fails to populate `general_cap_expression.components` despite matching the
`_CAP_TRIGGER_RE` trigger list.

**Why this matters for the generalization question.** This is precisely the
Lee-Challenge "confident-but-wrong-extraction" failure mode, and it is not a
crafted adversarial trick — it is what plain commercial drafting looks like.
The Step 4A.4/4A.5 corpora that shaped and validated this code apparently used
bare "annual fees" phrasing predominantly; a corpus built independently,
without access to that corpus, immediately surfaces the gap at high frequency,
including at Tier 1.

### F.2 — Payment-terms set-off/netting recognition: real, confirmed silent misses

Three cases, each with `prohibit_set_off=True` correctly configured in policy
kwargs, describe genuine prohibited set-off/netting arrangements using
non-canonical vocabulary:

- A6-P-12: `"shall be permitted to recoup from future payments due to
  [counterparty] any amount that [counterparty] is independently obligated to
  remit... under the parties' separate revenue-sharing arrangement described
  in Exhibit C"` — a recoupment right via cross-referenced exhibit.
- A6-P-14: `"only the net difference between what [A] owes [B] and what [B]
  owes [A]... shall actually change hands"` — the set-off/netting concept
  described with **none** of the recognizer's expected vocabulary at all.
- A6-P-24: `"...the parties shall true up their respective obligations
  quarterly, with only the resulting balance actually being transferred"` —
  "true up" jargon netting.

**Verified directly**: `extract_payment_facts()` returns `setoff_permitted=
None` for all three. The clauses are not merely escalated for review — they
are **silently accepted** (`ACCEPT`), meaning a prohibited set-off provision
that violates configured policy would pass through undetected. Given the
explicit target for this family was SM=0, and given the direct financial
materiality of an undetected set-off/netting right, these are classified **SM,
severity SM-CRITICAL** — a policy-prohibited term silently approved is exactly
the harm class this metric exists to catch.

The recognizer's core canonical-vocabulary set-off detection otherwise
performed well: all 11 hard-negative controls (rebates, credit memos,
insurance deductibles, withhold-delivery, retained commissions,
damages-based deduction) correctly did **not** trigger false positives, and
the pre-existing `run_setoff_concept_benchmark.py` control still shows
97.6% recall / 100% precision on its own (unchanged, in-distribution) corpus.
The gap is specifically a **vocabulary-boundary** gap, not a broken mechanism.

### F.3 — Indemnification verb-phrase recognition: total non-recognition on synonym idioms

Two cases use plainly synonymous indemnification-obligation language that
does not match the recognizer's expected verb sequence:

- A6-I-09: `"...covenants and agrees, on behalf of itself and its successors
  and assigns, to indemnify, defend at its sole cost and expense, and hold
  harmless [X]..."` — the canonical "indemnify, defend, and hold harmless"
  triad is present but wrapped in an outer "covenants and agrees...to" clause
  and interrupted by "at its sole cost and expense" between "defend" and "and
  hold harmless."
- A6-I-10: `"...shall make [X] whole for, and shall assume the defense of, any
  and all third-party claims..."` — "make whole" / "assume the defense of" as
  full idiomatic substitutes for "indemnify" / "defend."

**Verified directly**: `extract_indemnification_facts()` returns
`obligations=[]` for both — a complete, silent non-recognition of an
indemnification clause that plainly exists in ordinary legal English. This is
the "recognition/absence" failure mode named directly in the governing
instructions' Lee Challenge section: the system cannot distinguish "no
indemnification clause present" from "an indemnification clause is present
but phrased with a synonym the recognizer doesn't know." Classified **SM**.

### F.4 — Minor, secondary findings (disclosed, not separately scored as hard blockers)

- **Multi-word entity-name truncation** in role attribution:
  `indemnifying_role` resolves to `'Spirits Distribution'` instead of
  `'Falconridge Wine & Spirits Distribution'`, and similarly for other
  multi-word entity names ending in common industry-descriptor words
  (A6-I-04, A6-I-08). Did not independently flip any observed decision in
  this corpus, but is a real extraction-fidelity defect worth tracking.
- **Payment-terms adapter lacks a "nothing extracted → escalate" fallback**
  that the liability/indemnification adapters appear to have for absence
  cases. A6-P-33 (payment terms explicitly deferred to a future, unexecuted
  Order Form) and A6-RB-10 (payment period delegated to an ambiguous,
  self-flagged-as-indeterminate amendment) both extract nothing and default
  to `ACCEPT` rather than surfacing "genuinely unresolved" for review.
- **Payment-terms conflicting-defined-term detection does not generalize**
  from indemnification to payment terms: A6-P-48 defines "Net 30" two
  different ways in two different sections (calendar vs. business days) and
  `net_days_conflict` remains `False`.
- One genuine **GTD** on my part: A6-C-12 expected `NEGOTIATE (2x royalties)`,
  but 2.0 exactly equals `acceptable_max_multiplier` (2.0) under the default
  policy, so `ACCEPT` is the objectively correct threshold outcome — my own
  ground truth was wrong, not the system.

### F.5 — Named Step 4A.5 fixes under direct re-attack

**Grammatical-subject misattribution** (12 cases, target 25-30, not met): 6
FE, 2 SM, 2 WC, 1 CR, 1 CA. The fix does not fully generalize — at this small
sample size, 2 of 12 cases (17%) produced a confidently wrong role
attribution on fresh subordinate-clause/passive-voice constructions not used
to design the original fix.

**Reciprocal-pair trigger-level scope exclusion** (10 cases, target 25-30, not
met): 5 CR, 3 FE, 2 WC. The 2 WC cases (out of a sample far below target) show
the same underlying gap Step 4A.5 disclosed as unresolved — the reciprocal
equality check does not compare `trigger_treatments`, so a fresh,
differently-worded trigger-category or causation-standard differentiation
(A6-I-23's differentiated causation standard, not previously anticipated by
either generation) can still pass as symmetric.

**Both previously-disclosed residual weaknesses reproduce under new wording,
at meaningfully small sample sizes that likely understate their true
frequency** given the corpus-coverage shortfall documented in Section C.

---

## G. Control re-runs (NOT part of Step 4A.6's own held-out metrics)

### G.1 — Step 4A.4 immutable corpus

`python3 benchmarks/classify_step4a4.py` reproduces the frozen result exactly:
`Auto-bucket counts: {'CA_CANDIDATE': 113, 'FE': 19, 'CR': 38, 'WC_CANDIDATE':
2}` — identical to the Step 4A.4 final report, including the same 2 raw
heuristic WC_CANDIDATE cases (A4-H-04, A4-H-05) that report already manually
resolved to non-WC (defensible ESCALATE) and reported as WC=0. **This confirms
the harness and the frozen production code behave identically to Step 4A.5's
frozen state** — the Step 4A.6 failures above are a genuine corpus-coverage
generalization gap, not evaluation-environment drift.

### G.2 — Step 4A.2 immutable corpus

`python3 benchmarks/classify_step4a2_v2.py` reproduces its historical raw
auto-bucket shape: `{'NEEDS_MANUAL': 40, 'FE': 25, 'CR': 30, 'CA': 16, 'WC':
7}`. Given time constraints, the 7 raw WC_CANDIDATE and 40 NEEDS_MANUAL rows
were **not** individually re-triaged to final WC/SM status in this pass (Step
4A.2's own final report already performed that manual work and arrived at
WC=0/SM=0). This control confirms the corpus still runs and produces the same
raw distribution shape; it does not independently re-verify the 4A.2 WC=0
conclusion at full rigor. This is disclosed as a limitation of this control,
not asserted as a fresh WC=0 confirmation.

### G.3 — Named existing benchmark controls

12 of ~13 located dedicated mechanism benchmarks were re-run against the
frozen code and show no regression from their known baseline behavior:

| Benchmark | Result |
|---|---|
| `run_liability_benchmark.py` | 1 known pre-existing failure (`unheaded-08`, unquantified_cap) — unchanged |
| `run_indemnification_benchmark.py` | 1 known pre-existing failure (`cap-excluded-01`) — unchanged |
| `run_payment_terms_benchmark.py` | 0 failures |
| `run_role_resolution_benchmark.py` | Conflict precision 100%, recall 94.4% |
| `run_liability_concept_benchmark.py` | ran clean, no reported failures |
| `run_payment_recognition_benchmark.py` | Recall 100%, precision 95.7% |
| `run_liability_ownership_benchmark.py` | 42/42 correct, 0 false-safe |
| `run_indemnification_asymmetry_benchmark.py` | 19/19 scored correct, 0 false-safe |
| `run_setoff_concept_benchmark.py` | Recall 97.6%, precision 100% |
| `run_role_boundary_benchmark.py` | 100% recall/precision |
| `run_bystander_discrimination_benchmark.py` | Recall 100%, precision 88.0% |
| `run_direction_invariance_benchmark.py` | 37/40 correct-automatic-or-review, 3 unsafe-automatic (pre-existing, disclosed) |
| `run_step4a5_adversarial_battery.py` | matches its documented compound-mechanism REQUIRES_REVIEW behavior |

All of these confirm the frozen implementation behaves exactly as it did at
the end of Step 4A.5 on its own in-distribution controls — the Step 4A.6
findings are additive evidence about **out-of-distribution generalization**,
not evidence of any drift or regression in previously-validated behavior.

### G.4 — Full regression suite

`python3 -m pytest tests/ -q --continue-on-collection-errors` →
**1157 passed, 10 failed, 13 skipped, 43 errors** — an **exact match** to the
Step 4A.5 baseline. No regression.

---

## H. Hard-gate evaluation

Per the governing instructions, these gates are evaluated on evidence, not on
an invented industry benchmark:

- **S4 > 0?** No S4 classification was applied to any case in this pass
  (severity tiers beyond WC/SM were not separately assigned given time
  constraints — see Section J limitations). **Not independently confirmed
  either way; treated as unresolved, which itself is not a basis for a PASS
  verdict.**
- **SM-CRITICAL > 0?** **YES.** A6-P-12, A6-P-14, A6-P-24 (silent set-off
  misses with direct financial materiality) are classified SM-CRITICAL.
  **HARD BLOCKER TRIGGERED.**
- **Repeated WC/SM mechanism?** **YES, unambiguously.** The basis-word-
  modifier regex miss (Section F.1) recurs across at least 32 independently
  drafted cases spanning all three difficulty tiers and two adapters.
  **HARD BLOCKER TRIGGERED.**

**Both stated hard-blocker conditions are met. Step 4B may not begin under
this implementation's current state, regardless of any other metric in this
report.**

---

## I. Product-readiness questions (answered from evidence only)

1. **Does the system correctly automate ordinary (Tier 1) commercial
   drafting at a rate that would be acceptable in production?** No. Tier 1
   WC rate is 25.5% (13/51), driven almost entirely by the basis-word-
   modifier regex gap on liability multiplier caps — a construction ("annual
   [domain-word] fees") that appears routinely in real contracts.
2. **Does the system fail safely when it fails?** No, not uniformly. FE
   (safe over-escalation) accounts for 19.3% of cases, but WC (confident,
   wrong, actionable) accounts for a larger 24.1%, and SM (silent,
   undetected) for 4.2%. The dominant failure mode in this corpus is unsafe.
3. **Do the two named Step 4A.5 residual weaknesses (grammatical-subject
   misattribution, reciprocal-pair trigger-level scope exclusion) recur under
   fresh wording?** Yes, both recur, at non-trivial rates (2/12 and 2/10
   respectively) even at samples below the intended target size.
4. **Is the SM=0 result from Step 4A.4/4A.5 evidence of a genuinely absent
   failure mode, or evidence of a corpus that didn't probe hard enough?**
   The latter. Three confirmed SM-CRITICAL cases in payment-terms set-off
   recognition alone demonstrate the mechanism can be silently defeated by
   vocabulary the tuning corpora didn't include.
5. **Is the 85.6% Automation Recall from Step 4A.4 representative of
   real-world automation quality?** No. It was measured on evidence available
   during hardening. On this independent corpus, of AUTOMATABLE-labeled
   cases, only 45.4% were correctly auto-resolved (CA); 21.5% were
   confidently *wrong* (WC) and 5.5% were silently missed (SM).
6. **Does traceability (the system explaining its extracted_summary /
   unresolved_facts) substitute for correctness?** No. The clearest
   demonstration: A6-L-05 through A6-L-09 and many others report a clean,
   specific, traceable `extracted_summary` of `'Limitation-of-liability
   clause present but no numeric general cap stated'` — a confident,
   well-formed explanation that is simply **false**; the cap is present and
   quantified in the source text. Traceable output and correct output are
   not the same thing, and this corpus demonstrates the gap directly.
7. **Is the failure pattern concentrated in adversarial drafting, or does it
   reach ordinary drafting?** It reaches ordinary drafting. The dominant
   mechanism (F.1) is triggered by domain-typical noun phrases, not by any
   adversarial construction, and appears at Tier 1 as readily as at Tier 3.

---

## J. Verdict

**FAIL — DO NOT PROCEED TO STEP 4B.**

This is the correct one of the four possible verdicts (PASS;
PASS-WITH-CONDITIONS; FAIL, requires fixes before any further validation;
FAIL, hard blocker) given: two independent hard-blocker conditions triggered
(Section H), a Tier-1 WC rate of 25.5%, and a dominant single mechanism
(Section F.1) responsible for the majority of liability-adapter failures that
is not adversarial in nature and would be expected to recur at similar or
higher frequency on any additional real-world corpus.

This is explicitly **not** a repudiation of Step 4A.5's own claims about the
evidence available during hardening — 4A.4's control reproduction (Section
G.1) confirms that evidence was reproduced faithfully and the code has not
drifted. It is a repudiation of the inference that those numbers describe
production-ready generalization. They do not.

---

## K. Step 4B decision

**NO-GO**, unconditionally, given the two hard-blocker conditions in Section
H. No "controlled" or partial Step 4B is recommended, because the dominant
failure mechanism (F.1) is not isolated to a narrow, excludable slice of
drafting — it is triggered by an ordinary, common construction across the
liability adapter, which is one of the three adapters this system is meant to
cover. A "controlled" rollout limited to, say, payment-terms only would still
carry the confirmed SM-CRITICAL set-off/netting gap (Section F.2). There is no
currently-defensible restricted scope under which Step 4B could safely begin.

The defensible next step is a **Step 4A.7 remediation-and-re-validation
cycle**: fix the three root-caused mechanisms in Section F.1-F.3 in
production code (now permitted, since Step 4A.6 is complete and its verdict
recorded), then run a **new**, independently-constructed held-out corpus
(not this one, not a mutation of this one) before any Step 4B consideration.

---

## L. Lee Challenge status (evaluated on this step's own evidence only)

- **Confident-but-wrong-extraction**: **STRONGLY ADDRESSED — AS A CONFIRMED,
  UNRESOLVED RISK.** This report does not merely acknowledge the risk exists
  in the abstract; it demonstrates it directly and repeatedly (Section F.1,
  32+ confirmed instances; Section I.6's `extracted_summary` example).
  Independent attacks confirm the mechanism, at meaningful scale, in ordinary
  drafting. The verifier that exists in production code did not catch or
  prevent any of these — the confidently wrong `MUST_REDLINE` states were
  returned as final, non-review outcomes.
- **Recognition/absence**: **STRONGLY ADDRESSED — AS A CONFIRMED, UNRESOLVED
  RISK.** Section F.3 demonstrates total silent non-recognition
  (`obligations=[]`) of plainly-worded indemnification clauses using
  synonymous verbs. Section F.2 demonstrates the same for payment set-off
  clauses using non-canonical vocabulary. Both are direct, verified instances
  of the system being unable to distinguish "clause genuinely absent" from
  "clause present, vocabulary unrecognized."
- **False-confidence-from-traceability**: **STRONGLY ADDRESSED.** Section
  I.6 shows a specific, verified case where the system's traceable,
  well-formed `extracted_summary` output is confidently false. The presence
  of a clear evidence trail did not correlate with the correctness of the
  underlying extraction in these cases; if anything, the well-formed,
  specific phrasing of the false claim (`"present but no numeric general cap
  stated"`) makes it more, not less, likely to be trusted by a downstream
  reader.

No credit is given here merely because production code contains verification
logic (defined-term-conflict checks, differentiation checks, ownership
resolution, etc.) — those mechanisms exist and, per Section G.3, perform well
**on their own in-distribution controls**. The finding is that independent,
freshly-drafted attacks demonstrate real, repeated, non-adversarial failure
**upstream** of those verifiers, in extraction and recognition, which no
amount of downstream verification logic can correct if the fact was never
extracted or the clause was never recognized in the first place.

---

## M. Known limitations of this validation

- Six mandated attack families did not reach their stated minimum sample
  sizes (Section C); findings in those families are directional, not
  exhaustive.
- Formal S1-S4 severity tiers were not independently assigned to every WC/SM
  case; SM-CRITICAL was assigned to the 3 set-off cases based on direct
  financial materiality, but a full severity pass across all 51 WC and 9 SM
  cases was not completed given time constraints.
- The Step 4A.2 control (Section G.2) reproduces its raw bucket shape but was
  not independently re-triaged to a fresh WC=0/SM=0 confirmation at full
  manual rigor.
- Root-causing was performed to the point of a confirmed, verified mechanism
  for the great majority of WC/SM cases, but a small number of individually
  classified cases relied on defensible judgment calls (documented inline in
  the classification data at
  `/tmp/.../scratchpad/step4a6_final_classification3.json` during this
  session) rather than a second independent verification pass.

These limitations affect completeness, not the direction of the verdict: the
two hard-blocker conditions in Section H are independently over-determined by
the evidence gathered, and would not be reversed by closing any of the gaps
above.
