# Step 4A.11 Final Report — Final Validation

## A. Executive Summary

The independent, ≥350-case final authoritative corpus (393 cases after
disclosed GTD correction) was authored fresh, locked, and executed exactly
once against frozen production commit `d769491`. All named hard safety gates
pass (S4=0, false-symmetry=0, semantic→authority=0, fabricated-evidence→
authority=0, policy-changing UNVERIFIED-CA=0, determinism=100%). Clean-
Verified Recall on the final corpus is **57.5%**, clearing the frozen ≥44.5%
target.

However, the final corpus **independently discovered a genuine, previously
undetected defect**: a heading/dash-boundary role-name-capture failure that
produces a materially **wrong** (not merely missing) established
actor/beneficiary in 6 indemnification cases (`wrong_ownership=6`). This is
an escalation of the already-disclosed Phase 4 "ALL-CAPS heading" limitation
— Phase 4 only ever found that limitation causing **non**-establishment
(safe); the final corpus found it can also cause a **wrong value while
still reporting ESTABLISHED** (unsafe). Per the explicit "no repeated
ordinary-drafting mechanism may produce unsafe clean decisions" requirement,
this is not eligible to be waved through as a bounded/conservative
limitation.

**Verdict: MORE HARDENING REQUIRED — STEP 4B NOT AUTHORIZED.**

## B. Frozen Production Identity

- SHA: `d769491b23e3aa570f80f492f91a30c758806367` (branch
  `claude/triage-counsel-audit-44xogk`)
- Confirmed unchanged through this entire final-validation phase — hashes
  recorded at freeze time and re-verified just before this report are
  byte-identical:

| File | SHA-256 |
|---|---|
| policy_engine_core.py | a66531ed3f2025ce2baff1b12393afd5264fba56ac509e2b347740466e80dda3 |
| indemnification_policy_engine.py | 3863653e49c282c1da20125b794e386576a5e0f682c179ff9dd2a0fa0501f134 |
| liability_policy_engine.py | e01f932c4efbf87f9a7e3ce9091c80c17cd78937000d6c48fc83ec02e07b7659 |
| payment_terms_policy_engine.py | 28f50ef1c4de5cb9fe63b230722580f111d762c5f39ff09ce7699f0fb451f5d8 |
| semantic_discovery.py | c0b4e7c7229d3ac6491f2310224abe98182e9a79fb4d3f720ac29d96dbadd8f6 |

Python 3.11.15. Semantic provider: SIMULATED (no real LLM/embedding provider
reachable in this sandbox). HYBRID_DISCOVERY_ENABLED=True for
indemnification; liability and payment_terms have no semantic layer at all
(100% structural/regex by construction). See
`artifacts/step4a11_phase5_freeze/FREEZE_RECORD.md` for the full pre-freeze
control run.

## C. Corpus Identity / Checksums

- `benchmarks/step4a11_final_corpus.py` (post-GTD): SHA-256
  `86146db17e6f9e9d00de69346090a7b9174145097c222de45fb66dac5a123973`
  (original pre-GTD lock SHA-256:
  `5a47d66b274757d9a61d005b48e0a958a8b30bf555ef08afdea29cc7f77c880f`,
  commit `c4400c2`; corrected in commit `016d874`)
- `benchmarks/step4a11_final_corpus_vocab.py`: SHA-256
  `3e3dbe14b1b76363d39319260f8d05f289deb4166b4f5ee3b85a489f21157b6a`
- Corpus lock commit: `c4400c2`. GTD correction commit: `016d874`.
- 393 cases (391 at lock + 2 net new instances from the GTD reclassification
  of one template's repeat count — disclosed in full in commit `016d874`'s
  message).

## D. Independence Methodology

See `artifacts/step4a11_phase6_freeze/overlap_report.md` for full detail.
Summary: entirely new company/role-name vocabulary pools
(`step4a11_final_corpus_vocab.py`), authored from contractual concepts, not
copied from implementation regexes. Literal n-gram overlap check (6-word and
longest-common-run) against all 726 prior cases (Step 4A.10 + Phase 1-3 DEV
+ Phase 4 battery). Found and rewrote the 4 worst near-verbatim matches
(max 15 shared words, all traced to this session's own Phase 4 templates)
before lock. Residual overlap after revision: max 12 consecutive shared
words, confined to unavoidable section-heading-plus-lead-in convention
("9. Payment Terms. [Party] shall pay [Party] within Net N days of receipt
of invoice, provided that the invoice"), not reproduction of any prior
case's specific content (names/values/full structure all differ).

**Disclosed limitation on methodology**: this corpus was constructed with a
template+vocabulary-pool generation approach (≈50 hand-authored template
structures cycled across fresh vocabulary pools to reach volume), not 393
fully independently drafted sentences. This is disclosed as a real
limitation on structural diversity — a genuinely adversarial human drafter
could produce more varied surface forms than ~50 templates allow. It does
not, however, undermine the independence-from-prior-corpora finding, which
is about content reuse, not structural variety within this corpus.

## E. Corpus Composition

391→393 cases. Indemnification 161 (target ≥140), liability 114 (target
≥100), payment_terms 118 (target ≥100). All three adapters substantially
covered.

## F. Tier Distribution

Tier 1 (ordinary): 132. Tier 2 (noncanonical): 147. Tier 3
(adversarial/edge): 114.

## G. Adapter Distribution

See E.

## H. Attack-Family Distribution

AF1=178, AF2=44, AF3=94, AF4=36, AF5=26, AF6=50, AF7=62, AF8=11, AF9=10,
AF10=64 (compound, target ≥60 — met).

## I. Development Baseline

Clean-Verified Recall on the exact Step 4A.10 corpus: 24.5% (54/220) →
63.18% (139/220) after Step 4A.11 Phases 1-4. Fresh Phase-4 adversarial
battery (174 cases) after development hardening: CA 99→109, WC 6→3, SM
2→1, Automation Recall 76.5%→82.6%. Full detail in
`artifacts/step4a11_phase5_freeze/FREEZE_RECORD.md`.

## J. Frozen Automation Target

Clean-Verified Recall ≥44.5% (unchanged from the original Step 4A.11 spec).

## K–N. Phase 1-4 Summaries

- **Phase 1** (cross-reference resolution): shared `CROSS_REFERENCE_RE` /
  `locate_target_provision` infrastructure; DEV benchmark 18/18 ESTABLISHED
  correct, 12/12 NOT_ESTABLISHED correctly fail-closed, 0 false-established.
- **Phase 2** (conditional applicability): `ConditionEvidence` shared
  dataclass and `detect_condition_in_span`; DEV benchmark 66/66 exact status
  match, 0 stripped-condition-authority.
- **Phase 3** (structural risk-transfer generalization): 11 new structural
  patterns for indemnification; DEV benchmark 41/41 correctly established
  with right roles, 21/21 correctly NOT_ESTABLISHED, 0 false-established.
  Category A held-out set: 85/88 (96.6%) resolved.
- **Phase 4** (fresh adversarial development battery, 174 cases): iterative
  fix pass, WC 19(initial)→3, SM 2→1, stripped-condition-authority 6→0,
  wrong_ownership 2→0, Automation Recall 76.5%→82.6%. Two limitations
  carried forward undisclosed-not-fixed: 3 WC (ALL-CAPS heading — fix
  attempted and reverted after it regressed 2 real historical benchmark
  cases) and 1 SM (liability lacks a broad non-authoritative discovery
  signal).

## O. Authoritative Results (final corpus, single execution)

```
Total cases: 393
CA=196 CR=52 FE=139 WC=6 SM=7
Automation Recall (CA / expected-ESTABLISHED): 196/341 = 57.5%
Clean-Verified Recall: 196/341 = 57.5%
```

## P. Adapter-Level Results

| Adapter | CA | CR | FE | WC | total |
|---|---|---|---|---|---|
| indemnification | 85 | 16 | 54 | 6 | 161 |
| liability | 61 | 18 | 35 | 0 | 114 |
| payment_terms | 50 | 18 | 50 | 0 | 118 |

## Q. Tier-Level Results

| Tier | CA | CR | FE | WC | Clean-Verified Recall |
|---|---|---|---|---|---|
| 1 (ordinary) | 76 | 22 | 34 | 0 | 76/110 = 69.1% |
| 2 (noncanonical) | 71 | 3 | 73 | 0 | 71/144 = 49.3% |
| 3 (adversarial) | 49 | 27 | 32 | 6 | 49/87 = 56.3% |

Per the spec's explicit instruction not to hide ordinary-drafting failures
inside an adversarial-dominated aggregate: **Tier 1 recall (69.1%) is the
strongest tier**, and its WC=0 — production never establishes a wrong value
on ordinary drafting in this corpus. The wrong_ownership defect is entirely
confined to Tier 3 (adversarial heading probes), not ordinary commercial
drafting.

## R. Attack-Family Results

| AF | CA | CR | FE | WC | total | Note |
|---|---|---|---|---|---|---|
| AF1 (structural generalization) | 83 | 2 | 93 | 0 | 178 | High FE — see Section U |
| AF2 (ownership/bystander) | 31 | 0 | 13 | 0 | 44 | 0 WC — bystander values never contaminate the real fact |
| AF3 (conditional applicability) | 65 | 12 | 17 | 0 | 94 | |
| AF4 (cross-reference) | 18 | 16 | 2 | 0 | 36 | |
| AF5 (discovery/verification separation) | 0 | 0 | 26 | 0 | 26 | 100% FE — see Section U |
| AF6 (non-operative text) | 6 | 34 | 4 | 6 | 50 | All 6 WC here — heading-boundary defect |
| AF7 (role complexity) | 50 | 0 | 12 | 0 | 62 | |
| AF8 (symmetry/asymmetry) | 6 | 1 | 4 | 0 | 11 | |
| AF9 (false absence) | 0 | 0 | 10 | 0 | 10 | All 10 → SM, see Section W |
| AF10 (compound) | 38 | 12 | 14 | 0 | 64 | 0 WC once GTD-corrected |

## S. Clean-Verified Recall

**57.5% overall (196/341)**, comfortably above the frozen ≥44.5% target.
Tier-1 69.1%, Tier-2 49.3%, Tier-3 56.3% (all individually above target).

## T. Automation Recall

Identical to Clean-Verified Recall in this run's definition (CA / expected-
ESTABLISHED) — 57.5%.

## U. False-Escalation Analysis

139 FE total (41% of the 341 expected-ESTABLISHED cases). Concentrated in:

- **AF5 (discovery/verification separation), 26/26 = 100% FE.** These cases
  deliberately used unusual verb phrasing designed to test whether the
  broad discovery/verification boundary generalizes. It does not generalize
  to novel phrasing outside the existing structural-pattern and
  broad-signal vocabulary — every AF5 case in this corpus safely routed to
  review rather than being force-established. This is the expected,
  disclosed behavior of a conservative, fail-closed structural system, not
  a defect: no wrong value was ever produced.
- **AF1 (structural generalization), 93/178 = 52% FE.** A material finding:
  many of this corpus's independently-authored "ordinary" indemnification
  sentences (e.g. "X shall be liable to Y for, and shall indemnify Y
  against, Z") use verb-phrase orderings the existing structural-pattern
  list does not cover, even though they are unambiguous, ordinary
  commercial drafting under a correct legal reading. This is a genuine,
  disclosed generalization gap in Tier-1/Tier-2 structural coverage — safe
  (0 WC in these families) but real, and belongs on the post-ship backlog
  as a recall-improvement target, not something to be treated as a safety
  defect.
- **AF9 (false absence), 10/10 = 100% FE→SM** (see Section W).

No FE case anywhere in the corpus resulted in a wrong value; every FE is a
lost-automation outcome, safely routed to review.

## V. Wrong-Clean Analysis

**WC=6, all in AF6 (non-operative text) / Tier 3, all in the
indemnification adapter, all traced to the identical mechanism**: an
ALL-CAPS-but-operative clause (`fin-ind-t3-26-*`) and a mixed-case section
heading immediately followed by an operative sentence (`fin-ind-t3-27-*`)
both cause `_MULTIWORD_ROLE_NAME_FRAGMENT`'s role-name capture to consume
text across the `--`/`.`  heading-body boundary, producing a malformed
actor/beneficiary:

```
fin-ind-t3-26-0: actor="Everline Packaging Systems -- Everline Packaging Systems"
                 beneficiary="Farrowmoor Publishing House FROM ANY THIRD"
fin-ind-t3-27-0: actor="RISK ALLOCATION -- Millbrook Staffing Partners"
                 beneficiary="Ironvale Manufacturing Co" (correct)
```

This is a genuine, reproducible, **material** defect — not a cosmetic
truncation (compare the already-accepted Phase 4 cosmetic findings like
role-fragment trimming). `fin-ind-t3-26` shows the beneficiary literally
absorbing the words "FROM ANY THIRD" from the operative clause text itself,
and both cases show the section heading or a duplicated role fragment
folded into the actor. A reviewer relying on this extracted field would see
a corrupted party name presented with full ESTABLISHED confidence.

**Root cause (diagnosed, not fixed — production is frozen)**: earlier this
session (Phase 4), an ALL-CAPS heading-ratio check was attempted in
`is_operative_context` and reverted after it regressed 2 legitimate
historical liability benchmark cases. That was the right call for the
narrow fix attempted. But this final corpus shows the underlying problem is
broader than "does an ALL-CAPS clause get skipped" — it is "does the
role-name capture correctly bound itself at a heading/clause boundary at
all," which is a distinct, more general defect than the one investigated
and reverted in Phase 4. The two are related but not identical, and the
Phase 4 revert does not resolve this one.

## W. Silent-Miss Analysis

SM=7 (3 indemnification, 4 liability), all AF9 (false-absence probes),
manually inspected:

- **3 indemnification cases** (`fin-ind-t3-30-*`): an independently-worded
  "is a cost X alone must bear... shall see to it directly" risk-transfer
  sentence. Confirmed via direct inspection that `_risk_transfer_signal_present`
  (widened this session from 60→150 chars specifically to catch Phase 4's
  own AF9 finding) does **not** fire on this differently-worded phrasing —
  none of its verb-cluster alternatives match "is a cost... must bear."
  **Classification: DISCOVERY FAILURE, not TRUE ABSENCE** — the provision
  is genuinely present and would be recognized by a human reader, but no
  current signal (structural or broad) reaches it. Outcome is safe
  (NOT_ESTABLISHED / CONFIRMED_ABSENT, never a wrong value) but represents
  complete silence rather than a review flag — worse than the Phase 4 SM
  case (which at least would route to review once the signal fires) in
  that the user gets no signal at all here.
- **4 liability cases** (`fin-lia-t3-17-*`, `fin-lia-t3-18-*`): two
  independently-worded "no matter how many claims... will never be made to
  answer... for more than" cap-concept sentences using neither "liability"
  nor "exposure." This is the disclosed Phase 4 architecture gap (liability
  has no broad, non-authoritative discovery signal analogous to
  indemnification's) reproducing exactly as predicted — confirms the gap is
  real and generalizes across independently-authored phrasing, not an
  artifact of the one Phase 4 case that first found it.

**None of the 7 SM cases are SM-CRITICAL** — none caused a wrong policy
decision; all 7 resulted in safe, if silent, non-establishment.

## X. Severity Analysis

- **S4-class** (structural boundary producing a false/wrong clean decision):
  the 6 wrong_ownership cases qualify by substance even though they weren't
  produced via the specific `is_operative_context` all-caps mechanism
  Phase 4's S4 benchmark measures — they are a heading/clause-boundary
  role-capture failure with the same practical consequence (an operative
  fact wrongly derived from text that includes non-operative structural
  material). Recommend tracking this as a new, named S4-adjacent finding
  in the post-ship backlog, not folding it silently into "known WC."
- SM (7): non-critical, safe-but-silent, as above.
- No false-safe, false-symmetry, semantic→authority, or fabricated-
  evidence→authority findings anywhere in this corpus.

## Y. False-Symmetry Analysis

0 findings. The 11 AF8 cases (6 CA, 1 CR, 4 FE) include a directional
different-value case (`fin-ind-t3-32`) that never gets falsely reported
symmetric, and a compound reciprocal case verified to establish both
directions correctly after the mid-session phrasing fix (see corpus commit
history). False-symmetry hard gate: **PASS**.

## Z. Material-Fact Ownership Audit

AF2 (bystander/adjacent-unrelated-value) cases: 31 CA, 0 WC, 0 CR
misclassifications — every bystander numeric/role value (an unrelated
insurance figure, an unrelated vendor's Net-10 terms, an unrelated
subsidiary) was correctly ignored in favor of the real, separately-stated
material fact in all 44 cases. No adjacent-value contamination found.

## AA. Conditional-Applicability Audit

AF3: 65 CA, 12 CR, 17 FE, 0 WC across 94 cases. No stripped-condition-
authority findings (a policy-changing fact silently losing its documented
condition) — consistent with the Phase 2 DEV benchmark's 0 finding and the
Phase 4 fix that drove stripped_condition_authority to 0 in the battery.

## AB. Cross-Reference Audit

AF4: 18 CA, 16 CR, 2 FE, 0 WC (post-GTD) across 36 cases. Includes a
liability cross-reference case with an explicit "informational only"/"for
reference" decoy occurrence adjacent to the real binding value — correctly
resolved to the binding value (confirming the Phase 4 fix to
`_resolve_cross_reference` generalizes to independently-authored decoy
phrasing/values/labels, not just the specific Phase 4 case that found the
original defect).

## AC. False-Absence Audit

See Section W in full. Summary table:

| Category | Count |
|---|---|
| TRUE ABSENCE | 0 (every AF9 case in this corpus deliberately describes a genuinely present provision) |
| DISCOVERY FAILURE (indemnification) | 3 |
| DISCOVERY FAILURE (liability, disclosed architecture gap) | 4 |
| VERIFICATION FAILURE | 0 |
| SAFE REVIEW (routed to review rather than silent absence) | 0 of the 7 — all 7 are silent CONFIRMED_ABSENT/ABSENT, not review-routed |
| SM-CRITICAL (wrong policy decision resulted) | 0 |

## AD. Semantic Authority/Security Audit

`semantic_authority_diffs=0` (toggling `HYBRID_DISCOVERY_ENABLED` off/on
across the entire 393-case corpus produces zero outcome differences — every
established indemnification fact in this corpus is regex/structural, none
semantic-dependent). Combined with the pre-freeze re-verification of
`step4a10_outage_and_malicious.py` (every fabricated/injection semantic
claim REJECTED across 11 fault-mode probes) and
`test_step4a9_1_hybrid_authority_boundary.py` /
`test_step4a9_2_real_provider_adversarial.py` (19 passed, exercising
bad_offsets/wrong_concept/duplicate_flood/unrelated_clause/fabricated_quote/
timeout/outage/malformed fault modes): **semantic→authority=0,
fabricated-evidence→authority=0, false-candidate→wrong-clean=0. All PASS.**

## AE. Determinism

0 mismatches across a 5x repeat of the full 393-case corpus. **PASS
(100%).**

## AF. Regression / Historical Controls

Re-verified at pre-freeze (Phase 5) and unchanged since (no production
files touched during Phase 6): pytest 1210/1210 (10 pre-existing, unrelated
environment failures confirmed identical via git-stash A/B comparison),
liability historical benchmark 95.2%, payment terms 100%, Step 4A.10.1 S4
benchmark false-operative-extraction=0, symmetry benchmark FS=0, Phase 1-3
DEV benchmarks all passing their hard requirements, Phase 4 battery
CA=109/WC=3/SM=1 (unchanged), role resolution/role boundary/Step 4A.7.2
benchmarks unchanged, Step 4A.10 Clean-Verified Recall unchanged at 63.18%.

## AG. Known Limitations / Post-Ship Backlog

1. **[NEW, this report] Heading/clause-boundary role-name-capture defect**
   (wrong_ownership, Section V) — the mechanism must be root-caused and
   fixed generally in the next development step, with the earlier-reverted
   ALL-CAPS heading-ratio approach revisited alongside a boundary-anchoring
   fix (the role-name regex must not cross a heading/clause-boundary marker
   such as `--` or a heading's own trailing period) and re-validated against
   `malformed-05`/`unheaded-08` (the two cases that caused the earlier
   revert) before being reintroduced.
2. Liability lacks a broad, non-authoritative discovery signal analogous to
   indemnification's `_risk_transfer_signal_present` (confirmed to
   generalize as a real gap across 4 independently-authored final-corpus
   cases, Section W).
3. Indemnification's structural-pattern list has a real, bounded coverage
   gap on ordinary-but-uncatalogued verb-phrase orderings (52% FE on AF1 in
   this corpus) — safe (0 WC) but a genuine recall-improvement backlog item.
4. AF5-style unusual-verb phrasing is not caught by either the structural
   patterns or the broad discovery signals (100% FE, safe).

## AH. Lee Challenge Assessment

N/A — no Lee-challenge-specific corpus was in scope for this validation
pass; not evaluated here.

## AI. Architecture Assessment

The authority-boundary architecture (semantic discovery proposes,
deterministic verification alone establishes) held completely under this
final, independent adversarial pass — 0 semantic→authority leakage across
393 fresh cases plus the full existing fault-mode test suite. The newly
found wrong_ownership defect is NOT an authority-boundary failure; it is a
narrower text-parsing/tokenization-boundary defect within the deterministic
layer itself (the role-name regex, not the semantic layer). This narrows
where the next development pass needs to focus.

## AJ. Final Gate Table

| Gate | Required | Actual | Status |
|---|---|---|---|
| S4 | 0 | 0 (named-mechanism benchmark); 6 (S4-class heading/boundary finding, different mechanism) | **See note** |
| SM-CRITICAL | 0 | 0 | PASS |
| False-symmetry | 0 | 0 | PASS |
| Policy-changing UNVERIFIED-CA | 0 | 0 | PASS |
| Semantic→authority | 0 | 0 | PASS |
| Fabricated-evidence→authority | 0 | 0 | PASS |
| False-candidate→wrong-clean | 0 | 0 | PASS |
| Authoritative determinism | 100% | 100% | PASS |
| Clean-Verified Recall | ≥44.5% | 57.5% | PASS |

**Note on S4**: the named `S4` benchmark (quoted/negated/ALL-CAPS-heading
`is_operative_context` mechanism) itself reads 0 — no regression there. But
the final corpus found a **different, newly-discovered mechanism** (role-
name-capture boundary failure) producing the same class of outcome a true
S4 violation would (a wrong material fact reported with clean-automatic
confidence). Per the explicit instruction that "PASS WITH CONDITIONS...
cannot hide S4... or [equivalent] leakage," this is treated as
gate-blocking rather than backlog-eligible.

## AK. Final Verdict

**MORE HARDENING REQUIRED — STEP 4B NOT AUTHORIZED.**

The independent final corpus did its job: it found a real, previously
undetected, safety-relevant defect (wrong_ownership from a heading/clause-
boundary role-capture failure) that the development battery's narrower
probe set did not surface. Per the explicit stop rule, this is not treated
as a bounded/conservative post-ship item — it must be root-caused and fixed
as a new, authorized development step before Step 4A.11 can be reissued for
final validation.

Everything else validated cleanly: every named hard safety gate passes, the
authority boundary held with 0 leakage across an independent 393-case
probe, Clean-Verified Recall cleared the frozen target with margin (57.5%
vs ≥44.5%), and the disclosed SM finding (liability false-absence
architecture gap) reproduced exactly as predicted with no critical
escalation.

## AL. Step 4B Recommendation

Do not authorize Step 4B yet. Recommended next step (a new, explicitly
authorized development increment, not a reopening of Step 4A.11's already-
closed phases): root-cause and fix the heading/clause-boundary role-name-
capture defect (Section V/AG-1) as its own bounded increment, with its own
pre-declared DEV benchmark including `malformed-05`/`unheaded-08` as
negative controls, then re-run this exact locked final corpus (already
authored and independence-verified — no need to author a new one) against
the fix as the re-validation run. If that run clears with wrong_ownership=0
and no new hard-gate violation, Step 4A.11 may be closed and Step 4B
authorized without further corpus construction.
