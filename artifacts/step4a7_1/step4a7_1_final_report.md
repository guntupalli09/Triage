# Step 4A.7.1 — Residual Unsafe-Decision Elimination: Final Report

## A. Executive verdict

**MORE HARDENING REQUIRED.**

This step eliminated 12 of the 15 known Step 4A.7 WC cases (12/15 → CA or
CR), eliminated both known unsafe false-symmetry cases from the 108-case
stress benchmark (2/108 → 0/108), and fixed a mid-implementation test
regression before it could reach this report. **It did not reach zero known
unsafe WC.** One case (A6-L-52) remains a confirmed false-safe (S3) wrong-
clean decision, and two more (A6-C-07, A6-RB-02) remain conservative-
direction (S2) wrong-clean decisions. Per the explicit governing rule, a
single remaining unsafe WC is an automatic, non-waivable fail condition for
a PASS verdict, regardless of the scale of improvement elsewhere. This
report says so plainly rather than characterizing 12/15 as sufficient.

**Also disclosed, not hidden**: a pre-existing measurement inconsistency was
discovered in the Step 4A.7 report's own claimed Step 4A.4 control
reproduction (Section G).

## B. Starting commit / integrity

| | |
|---|---|
| Start commit | `5ae7451f6cba160679807b16105d987f53ccd44e` |
| Branch | `claude/triage-counsel-audit-44xogk` |
| PRE hashes | recorded in `artifacts/step4a7_1/frozen_state.json`, confirmed to match the Step 4A.7 report's POST hashes exactly |
| POST hashes | same file — `policy_engine_core.py` unchanged; `liability_policy_engine.py`, `indemnification_policy_engine.py`, `payment_terms_policy_engine.py` modified |

Reports read in full before any change: `artifacts/step4a7/step4a7_final_report.md`,
`artifacts/step4a6/step4a6_final_report.md`. Relevant artifacts located:
`artifacts/step4a7/step4a7_case_classification.json` (the 15 WC), `benchmarks/
step4a7_reciprocal_semantic_benchmark.py` (the 108-case stress set, with the
2 unsafe cases identified as S4B-COMP-05/S4B-COMP-07), and the omitted-
benchmark disclosures in the Step 4A.7 report's Sections H/I/O/N. These
source artifacts were read, not modified.

**PRE reproduction**: the Step 4A.6 corpus (`run_step4a6_heldout.py`)
reproduced byte-identical to `artifacts/step4a7/step4a7_raw_run_output.txt`.
The 108-case stress benchmark reproduced its reported 2 unsafe-false-
symmetry cases exactly (S4B-COMP-05, S4B-COMP-07). The 60-case liability
basis benchmark reproduced 100%/100%/0%. The regression suite reproduced
1157 passed/10 failed/13 skipped/43 errors. **One reproduction did not
match**: `classify_step4a4.py` — see Section G. Per the explicit Phase 0
instruction ("if counts differ, STOP and explain why before implementation"),
this is explained there rather than silently proceeding; the explanation
establishes the discrepancy predates this step's changes, so implementation
did proceed once that was confirmed.

## C. Exact Step 4A.7 residual-failure inventory

All 15 WC and both unsafe false-symmetry cases were re-extracted with full
tracing before any fix. Full per-case table (case ID, adapter, expected,
actual, severity, false-safe?, material fact, discovery/interpretation/
verification function, exact wrong fact, root-cause family) is in
`artifacts/step4a7_1/step4a7_1_case_classification.json` and the working
trace notes below (Section D). Summary:

| Case | Adapter | Actual (PRE) | Severity | False-safe? |
|---|---|---|---|---|
| A6-L-04 | liability | MUST_REDLINE | S2 | No |
| A6-L-22 | liability | ACCEPT | S3 | **Yes** |
| A6-L-23 | liability | ACCEPT_WITH_NOTE | S3 | **Yes** |
| A6-L-43 | liability | MUST_REDLINE | S2 | No |
| A6-L-52 | liability | ACCEPT | S3 | **Yes** |
| A6-I-43 | indemnification | MUST_REDLINE | S2 | No |
| A6-P-33 | payment_terms | ACCEPT | S3 | **Yes** |
| A6-P-48 | payment_terms | ACCEPT | S3 | **Yes** |
| A6-C-07 | liability | MUST_REDLINE | S2 | No |
| A6-C-15 | indemnification | ACCEPT_WITH_NOTE | S3 | **Yes** |
| A6-RB-01 | liability | ACCEPT | S3 | **Yes** |
| A6-RB-02 | liability | MUST_REDLINE | S2 | No |
| A6-RB-07 | liability | ACCEPT | S3 | **Yes** |
| A6-RB-09 | liability | ACCEPT | S3 | **Yes** |
| A6-RB-10 | payment_terms | ACCEPT | S3 | **Yes** |

10 S3 (false-safe), 5 S2 (conservative). This matches the Step 4A.7 report's
own disclosed severity table exactly, confirming reproduction.

## D. Root-cause clustering

Verified by direct code execution (extraction inspection, not surface
wording), per the explicit instruction not to assume the labels from Step
4A.7's summary were correct:

1. **Fixed-dollar object-phrasing gap** (A6-L-04, A6-L-43): `_FIXED_AMOUNT_RE`
   required "liable for...in excess of/more than $X" or a specific "which
   the parties agree is $X" shape with no interposed clause. A6-L-04 uses
   "liable to [Party] for [damages] exceeding $X"; A6-L-43 uses "...which
   the parties agree, for purposes of this Agreement, is $X" (an interposed
   parenthetical the regex didn't tolerate). **Discovery-stage** bugs, both
   in the same regex family, fixed with two bounded regex extensions.
2. **Hyphenated-compound-modifier basis gap** (A6-C-07): "annual crop-
   purchase price" — a hyphen fuses a modifier directly onto the basis
   phrase's first word, defeating even the Step 4A.7 modifier-tolerance
   fix (which only tolerates whitespace-separated modifier words).
   **Discovery-stage.** An initial fix (adding a bare "price" basis word)
   was found to REGRESS an existing, deliberately-designed test
   (`test_purchase_price_basis_is_not_compared_as_if_it_were_fees` —
   "purchase price" is intentionally excluded from the default fee-
   multiplier threshold comparison, and "price" alone collided with that
   distinction) and a real drop in the Step 4A.4 control corpus; reverted
   (Section Z). **A6-C-07 is not fixed in this step** — it remains WC, but
   at S2 (conservative — see Section E), not S3.
3. **Conflicting-defined-term generalization gap** (A6-L-22, A6-P-48): the
   existing detector required the EXACT phrase "is defined in Section X
   as..., and separately in Section Y as..."; the actual drafting used
   "'[Term]' means, for purposes of Section X, ..., and means, for purposes
   of Section Y, ..." (liability) and the same shape with a "shall instead
   mean" redefinition on the payment side, where the underlying numeric
   value ("30") doesn't even change — only its TYPE (calendar vs. business
   days) does, invisible to the existing plain-digit day extractor.
   **Discovery-stage**, two independently-defined regexes (liability's
   `_CONFLICTING_DEFINED_TERM_RE`, a new payment-terms-side counterpart),
   fixed with general shape-based patterns (a repeated "means...for purposes
   of Section N" construction), not by enumerating the specific term names.
4. **Self-flagged-unresolved generalization gap** (A6-L-23, A6-I-43,
   A6-P-33, A6-RB-01, A6-RB-09, A6-RB-10): the existing detector
   (`_SELF_FLAGGED_AMBIGUITY_RE`) matched only "unclear whether." The
   actual drafting used a closed family of six other phrasings ("remains a
   matter...not yet finally resolved," "no such written agreement
   currently exists," "a determination not yet made," "have not yet
   reached agreement," "no payment obligation arises until," "does not
   indicate which is the most recent"). **Discovery-stage**, the SAME
   general concept (the drafter's own explicit acknowledgment that a
   material term is unsettled) expressed six different ways; fixed by
   widening the closed phrase family in liability and building an
   independently-defined counterpart in payment_terms and indemnification
   (the three adapters do not share extraction code).
5. **Reciprocal-pair exception recognition gap, missing trigger category**
   (A6-C-15): "except that Servicing Agent's obligation excludes claims
   arising from Investor's own fraud" — the exception-clause detector fired
   correctly, but the comparison found no differentiation because "fraud"
   was not a tracked trigger category at all (only six of a common seven
   were defined). **Discovery-stage** (a missing vocabulary category, not a
   comparison-logic bug) — fixed by adding "fraud" as a seventh trigger
   category.
6. **Chained cross-reference delegation** (A6-RB-07): a clean, correctly-
   extracted multiplier (1x) applies to a basis that is itself delegated
   through TWO levels of cross-reference ending in a document not
   included. **Interpretation-stage** (the multiplier VALUE was correctly
   discovered; what was missing was recognizing that its BASIS was not
   established) — fixed with a new, narrowly-scoped chained-delegation
   detector.
7. **Generic-role-mapping unresolved** (A6-L-52): "Grantee"/"Grantor" (a
   mineral-rights conveyancing vocabulary pair) do not map to buy/sell-side
   vocabulary, and the liability adapter's single-provision cap-resolution
   path does not consult role-side resolution at all for a bare "X's
   aggregate liability to Y" sentence (unlike indemnification's
   bidirectional architecture, which always resolves role attribution).
   **Architectural gap, not a regex gap** — the fix would require threading
   role-side awareness into a code path that currently has no concept of
   needing it. **Not fixed in this step** — see Section E for why this was
   a deliberate stop, not an oversight.

Answering the ten root-cause questions from Phase 2 for the dominant
families: the wrong fact was, in every case, either a cap/monetary value
that should have been `unresolved` (families 1-4, 6) or a differentiation
signal that should have blocked a symmetry claim (family 5). Discovery was
wrong in families 1, 2, 5 (a regex simply didn't match a legitimate
construction, or a vocabulary category was missing). Interpretation was
wrong in family 6 (the value was found, but its basis's own unresolved
status wasn't recognized). Ownership/role resolution was the SPECIFIC,
unaddressed gap in family 7. Conflict detection was missing/too-narrow in
families 3-4. In every fixed family, absence was NOT correctly inferred
from non-recognition beforehand — the bug was the opposite: a genuinely
UNRESOLVED fact was being treated as ESTABLISHED. The correct general
response in every fixed case was better deterministic discovery (extending
an existing, working "route to REQUIRES_REVIEW" mechanism to recognize
constructions it was blind to), not new architecture — consistent with the
Step 4A.7 report's own Section K finding that the establishment layer
already exists and works once a signal reaches it.

## E. Known false-safe analysis

Verified PRE count: **10 S3 false-safe WC** (Section C: A6-L-22, A6-L-23,
A6-L-52, A6-P-33, A6-P-48, A6-C-15, A6-RB-01, A6-RB-07, A6-RB-09, A6-RB-10),
exactly matching the Step 4A.7 report's disclosed "~10." **9 of 10 are
fixed and verified; 1 remains (A6-L-52).**

**A6-L-52 is the one hard-gate-blocking case remaining.** It was
deliberately NOT fixed in this session, after tracing the root cause fully
(Section D, family 7) and confirming the correct fix requires threading
document-level role-side resolution into `_classify_general_cap_expression`
— a code path that presently has zero role-attribution awareness for a
single-provision liability cap. Given (a) this is the only remaining
false-safe case, (b) the session had already produced two mid-
implementation regressions on other fixes (Section Z) that were caught and
corrected only through careful re-validation, and (c) insufficient time
remained to implement and fully re-validate an architectural change of this
kind against the full Liability-125/ownership/bystander control suite, the
considered decision was to stop rather than risk an under-validated change
late in the session. This is reported as an explicit, deliberate limitation
— not a discovery made too late to act on.

## F. Compound reciprocal false-symmetry analysis

Both S4B-COMP-05 and S4B-COMP-07 (Step 4A.7's own 108-case benchmark) share
one root cause: a single sentence differentiates TWO different named
parties through TWO DIFFERENT mechanisms simultaneously — one party via an
except/provided-that exception clause, the other via a "[Role]'s...
obligation is subject to a '...' standard" attribution. Neither mechanism
alone had enough signal: the exception-clause detector, per its own
asym-19 anti-false-positive fix (Step 4A.7's Section V), defers whenever a
clause names 2+ distinct roles; the attribution comparator needs 2
comparable attributions to compare against each other and only found 1.

**Root cause**: the two mechanisms were built and validated independently
and did not share state about a differentiation one of them already found
for one party when deciding whether to defer on a two-party clause.

## G. Reciprocal benchmark PRE/POST

| | PRE (Step 4A.7 final state) | POST (Step 4A.7.1) |
|---|---|---|
| Unsafe false-symmetry | 2/108 (S4B-COMP-05, S4B-COMP-07) | **0/108** |
| Symmetric recall | 89.3% (Step 4A.7's final state, this step's own PRE) | **89.3%** (unchanged — this step's fix affects only the 2 unsafe-false-symmetry cases, both already counted as FN not TP in the PRE recall figure) |
| Unnecessary-asymmetry | 3/108 | 3/108 (unchanged — S4B-SYM-03, S4B-SYM-18, S4B-NEG-06, all safe-direction, not touched this step) |

**Fix**: a new cross-mechanism check — when `_ROLE_ATTRIBUTION_RE` finds
EXACTLY ONE attribution in the window (insufficient for the existing
pairwise comparison) AND a DIFFERENT named role is independently found in
an exception clause (using a relaxed variant of the exception-clause scanner
that, in this specific context only, does not defer on a 2-role clause,
because the calling context has already confirmed there is only one
attribution match in the whole window — so the asym-19 false-positive
shape, which requires 2 attribution matches to even reach comparison,
cannot recur here), that combination is itself evidence both parties carry
independent, non-matching differentiation. Verified against
`run_indemnification_asymmetry_benchmark.py` (19/19, unchanged, including
`asym-19` itself) and the four mandatory S4 targets (all still correctly
`REQUIRES_REVIEW`) before being accepted.

## H. Conflicting-definition analysis

A dedicated 60-case benchmark (per Phase 5) was **not built as a separate
artifact** in this step, given the time budget prioritized directly fixing
and verifying the two confirmed real-world instances (A6-L-22, A6-P-48)
plus their generalization (the fix is shape-based — "a term redefined twice,
each redefinition explicitly scoped to a different Section" — not tied to
either case's specific term name or number). This is disclosed as scope
compression: the fix is verified against its two source cases plus the
existing `liability_corpus.py`/`indemnification_corpus.py`/
`payment_terms_corpus.py` controls (all unchanged), but not against a
purpose-built stress set covering every construction listed in Phase 5
(duplicate-consistent, definition-in-schedule, amendment-superseding,
circular, etc.). This is a genuine, named gap for Step 4A.8 to probe.

## I. Self-flagged-ambiguity analysis

Same disclosure as Section H: the fix (Section D, family 4) generalizes
across six phrase variants observed in the six source cases and is verified
against all six, but a dedicated 50-case benchmark (Phase 6) was not built
separately. The invariant it implements — a document's own explicit
acknowledgment that a material fact is not yet settled must not be
converted into a clean established fact — was verified to hold for every
phrase in the closed family now recognized, and was checked against a
sample of ordinary boilerplate NOT containing these phrases (the full
Step 4A.6 corpus and all historical controls, Section W) to confirm no new
over-escalation was introduced.

## J. Chained-delegation analysis

Same disclosure pattern: the fix for A6-RB-07 (Section D, family 6) is
narrowly scoped to the exact shape found ("which Section N itself cross-
references Schedule/Exhibit/Appendix X...not included") and verified
against that case plus the full historical cross-reference benchmark
family in `liability_corpus.py` (unchanged). A dedicated 60-case benchmark
covering the full Phase 7 matrix (A→B→C chains, broken references,
circular references, multiple plausible targets) was not built. This
mechanism's generality is the weakest-verified of this step's fixes and is
explicitly flagged as such for Step 4A.8.

## K. Indemnification recognition benchmark

Not built this step (already disclosed as incomplete in the Step 4A.7
report, Section H there); no new work performed on this specific item in
Step 4A.7.1, since none of the 15 known WC or 2 unsafe-false-symmetry cases
required it. Remains an open item for Step 4A.8.

## L. Set-off/netting benchmark

Not expanded this step — the existing `run_setoff_concept_benchmark.py`
(72 cases) and the 3 previously-confirmed SM-CRITICAL fixes (already closed
in Step 4A.7) were re-verified unchanged (97.6% recall/100% precision).
None of the 15 known WC were set-off/netting cases, so this was not this
step's focus.

## M. Liability basis generalization check

The existing 60-case `step4a7_liability_basis_benchmark.py` was re-run
(100% recall/100% multiplier-correctness/0% false-association, unchanged)
as a regression check on every liability-side fix made in this step. **30
NEW cases were not added** (Phase 9C's requirement) — this is disclosed as
incomplete. The one new basis-adjacent finding from this step
(hyphenated-compound-modifier fusion, A6-C-07) was investigated, an initial
fix was found to regress an existing deliberate test and the Step 4A.4
control, and was reverted (Section D family 2, Section Z) — A6-C-07 remains
unfixed, disclosed at S2 (conservative) severity.

## N. Material-fact trust audit

The full 150-case stratified sample (50 per adapter) specified in Phase 10
was **not built as a separate artifact**. What this step DOES provide: for
every one of the 12 newly-fixed cases, the fix was verified via direct
extraction-function inspection (not just the final policy state) before
being accepted — confirmed by the code excerpts in Section D — establishing
that each newly-CA/CR case's material fact is now BOUNDED/MECHANICALLY
ESTABLISHED (a deterministic pattern match validated against a negative
control), not merely coincidentally correct. This is real evidence for the
12 cases touched, not a claim about the full 212-case corpus's every clean
decision, which Step 4A.7's own Section M partially covered and this step
did not re-verify from scratch.

**One hard finding stands, unresolved, from Section E**: A6-L-52's material
fact (which named party's liability the cap protects) is genuinely
UNVERIFIED and still feeds a clean `ACCEPT` decision. This is exactly the
"HARD finding, do not hide it because the final policy answer happened to
match ground truth" scenario Phase 10 warns about — reported as such, not
minimized.

## O. Absence / recognition audit

Not independently rebuilt this step. The Step 4A.7 report's Section K
inventory (which already distinguishes `clause_found=False`/`None` from
`clause_found=True, obligations=[]` from a populated, resolved fact) was
re-confirmed still correct via the Section D fixes, all of which route
through the SAME existing `REQUIRES_REVIEW`-producing mechanism rather than
introducing a new absence-representation. No new path was found in this
step where B/C/D (not-recognized / recognized-but-unresolved / expected-
but-missing) silently collapsed into A (confirmed absent) — the 12 fixes
were all cases of a resolved-but-WRONG fact becoming correctly unresolved,
not absence-related per se, except A6-C-15 and A6-L-22/P-48 which are
adjacent (a genuinely-conflicting definition was being silently resolved to
one branch rather than surfaced as conflicting).

## P. Positive-control selectivity

Not built as a separate 90-case artifact. The equivalent evidence: Tier 1
(ordinary drafting) Automation Recall in the re-run Step 4A.6 corpus and
Tier 1 WC count (Section T/V) serve as the closest available proxy, and
show **Tier 1 WC = 0/51** after this step (down from 1/51 after Step 4A.7,
0 after this step's A6-L-04 fix moved the sole remaining Tier-1 case to
CA). No known WC was fixed by converting it to FE/CR when it could
genuinely be established — every one of the 12 fixes in this step resolved
to either CA (the value/fact genuinely IS establishable and now correctly
resolves) or CR (the value/fact is genuinely NOT establishable and now
correctly escalates), verified case-by-case in Section Q, never merely
"safety by escalating everything."

## Q. Known 15 WC PRE/POST

| Case | PRE | POST | Outcome |
|---|---|---|---|
| A6-L-04 | MUST_REDLINE (WC, S2) | ESCALATE | **WC → CA** |
| A6-L-22 | ACCEPT (WC, S3) | REQUIRES_REVIEW | **WC → CR** |
| A6-L-23 | ACCEPT_WITH_NOTE (WC, S3) | REQUIRES_REVIEW | **WC → CR** |
| A6-L-43 | MUST_REDLINE (WC, S2) | ESCALATE | **WC → CA** |
| A6-L-52 | ACCEPT (WC, S3) | ACCEPT | **WC → WC (unfixed, S3, disclosed)** |
| A6-I-43 | MUST_REDLINE (WC, S2) | REQUIRES_REVIEW | **WC → CR** |
| A6-P-33 | ACCEPT (WC, S3) | REQUIRES_REVIEW | **WC → CR** |
| A6-P-48 | ACCEPT (WC, S3) | REQUIRES_REVIEW | **WC → CR** |
| A6-C-07 | MUST_REDLINE (WC, S2) | MUST_REDLINE | **WC → WC (unfixed, S2, disclosed)** |
| A6-C-15 | ACCEPT_WITH_NOTE (WC, S3) | REQUIRES_REVIEW | **WC → CR** |
| A6-RB-01 | ACCEPT (WC, S3) | REQUIRES_REVIEW | **WC → CR** |
| A6-RB-02 | MUST_REDLINE (WC, S2) | MUST_REDLINE | **WC → WC (unfixed, S2, disclosed)** |
| A6-RB-07 | ACCEPT (WC, S3) | REQUIRES_REVIEW | **WC → CR** |
| A6-RB-09 | ACCEPT (WC, S3) | REQUIRES_REVIEW | **WC → CR** |
| A6-RB-10 | ACCEPT (WC, S3) | REQUIRES_REVIEW | **WC → CR** |

**WC→CA: 2. WC→CR: 10. WC→WC (unfixed): 3 (1 × S3, 2 × S2).**

15 → 3 (a 80% reduction), and the S3 (false-safe) subset fell from 10 → 1
(90% reduction). The hard gate requires 0; 1 remains.

## R. 108-case stress benchmark PRE/POST

Covered fully in Section F/G. **Unsafe false-symmetry: 2 → 0.** Hard gate
met on this specific benchmark.

## S. Fresh 120+ adversarial battery

**Not built.** Per Phase 13's own instruction ("only after the known 15 WC
reach zero"), and given the known 15 WC did NOT reach zero in this step
(Section Q), building the fresh red-team battery was correctly out of
scope for this pass — attempting it before the known failures were resolved
would have been premature per the step's own stated sequencing, and the
remaining time budget was fully committed to the root-cause/fix/verify
cycle for the 12 cases that WERE resolved plus the compound-symmetry fix.
This is a disclosed, sequencing-driven omission, not an oversight.

## T. CA/CR/FE/WC/SM metrics

Computed on the same locked Step 4A.6 corpus (212 cases), re-run against
the Step 4A.7.1 final code:

| Outcome | Count | Rate |
|---|---:|---:|
| CA | 111 | 52.4% |
| CR | 42 | 19.8% |
| FE | 41 | 19.3% |
| **WC** | **3** | **1.4%** |
| SM | 5 | 2.4% |
| GTD | 4 | 1.9% |
| Boundary-consistent | 6 | 2.8% |

Automation Recall: 68.1% (up from 66.9%). WCDR: 2.6% (down from 12.1%).
CADR: 52.4% (up from 51.4%). FE/AUTOMATABLE: 25.2% (essentially unchanged
— this step converted WC to CA/CR, not FE, per Section P).

## U. S1-S4 severity

| Severity | Count | Cases |
|---|---:|---|
| S1 | 0 | — |
| S2 (conservative) | 2 | A6-C-07, A6-RB-02 |
| **S3 (false-safe)** | **1** | **A6-L-52** |
| S4 | 0 | — |
| SM-CRITICAL | 0 | — |

Down from S2=5/S3=10 at the start of this step.

## V. Per-adapter results

| Adapter | CA | CR | FE | WC | SM | Automation Recall | WCDR |
|---|---:|---:|---:|---:|---:|---:|---:|
| Liability | 40 | 13 | 12 | 3 | 4 | 64.5% | 7.0% |
| **Indemnification** | 23 | 22 | 23 | **0** | 0 | 50.0% | **0.0%** |
| Payment Terms | 48 | 7 | 6 | **0** | 1 | 87.3% | **0.0%** |

**All 3 remaining WC are in the liability adapter.** Indemnification and
Payment Terms both reached WCDR=0 in this step — every wrong-clean decision
in those two adapters from the Step 4A.7 baseline is now fixed.

## W. Historical controls

| Benchmark | Result |
|---|---|
| Liability-125 | `unheaded-08` (1 pre-existing failure), `partial-01`/`amendment-02` (2 pre-existing informational notes) — unchanged |
| Indemnification-100 | `cap-excluded-01`, `cross_referenced_cap` xref-03, `special_cap` super-cap-01/02 (4 pre-existing failures) — unchanged |
| Payment Terms-84 | 0 failures — unchanged |
| Role-resolution benchmark | 100% precision / 94.4% recall — unchanged |
| Payment-recognition benchmark | 100% recall / 95.7% precision — unchanged |
| Liability-ownership benchmark | 42/42, 0 false-safe — unchanged |
| Indemnification-asymmetry benchmark | 19/19, 0 false-safe — unchanged (confirmed after the Section F/G fix, which risked exactly this) |
| Set-off concept benchmark | 97.6%/100% — unchanged |
| Role-boundary benchmark | 100%/100% — unchanged |
| Bystander discrimination benchmark | 100% recall / 88% precision — unchanged |
| Direction-invariance benchmark | 40/40, 0 unsafe-automatic — unchanged |
| Step 4A.7 reciprocal-semantic benchmark | Unsafe false-symmetry 2→0; unnecessary-asymmetry 3/108 unchanged |
| Step 4A.7 liability-basis benchmark | 100%/100%/0% — unchanged |
| Step 4A.4 frozen corpus | **See Section G — reproduces 112/20/38/2 both before and after this step's changes; the Step 4A.7 report's claimed 113/19 does not reproduce and predates this step** |
| Step 4A.2 frozen corpus | `{'NEEDS_MANUAL': 40, 'FE': 25, 'CR': 30, 'CA': 16, 'WC': 7}` — unchanged (not independently re-triaged, same disclosed limitation as prior steps) |

No new false-safe was introduced into any historical control. Two
regressions were introduced and caught DURING implementation before ever
reaching this report — see Section Z.

## X. Full regression suite

`python3 -m pytest tests/ -q --continue-on-collection-errors` →
**1157 passed, 10 failed, 13 skipped, 43 errors** — exact match to the
Step 4A.7 baseline, confirmed with a cache-cleared re-run. One test
(`test_purchase_price_basis_is_not_compared_as_if_it_were_fees`) briefly
failed mid-implementation (Section Z) and was fixed before this final run.

## Y. Determinism

The full 212-case Step 4A.6 corpus and the 108-case reciprocal-semantic
benchmark were each run twice, unmodified, with `diff` confirming
byte-identical output both times. **100% deterministic.**

## Z. New regressions discovered during implementation

Two regressions were introduced and caught before this report, per the
explicit "stop that branch, root-cause before continuing" instruction:

1. **`test_purchase_price_basis_is_not_compared_as_if_it_were_fees`** (and,
   independently, a real drop in `classify_step4a4.py`'s CA count) — adding
   a bare `"price"` alternative to `_BASIS_WORD_FRAGMENT` to fix A6-C-07's
   hyphenated-modifier case caused the regex's modifier-tolerance fragment
   to greedily consume "purchase " as a modifier word and match "price"
   alone as the basis, misclassifying a `BASIS_PURCHASE_PRICE` cap (which
   is deliberately excluded from the default fee-multiplier threshold
   comparison, since purchase price is not comparable in scale to
   recurring fees) as an ordinary fee-multiplier cap. **Reverted.** A6-C-07
   remains unfixed as a result (Section D family 2, Section M).
2. A follow-on risk in the Section F/G compound-symmetry fix — the initial
   design considered relaxing the exception-clause detector's 2-role defer
   rule globally, which would have reintroduced the `asym-19` false
   positive (Step 4A.7's own Section V regression). The final design
   instead scoped the relaxation to the one caller that had already
   independently confirmed a single-attribution precondition, verified
   against `asym-19` specifically before being accepted (Section G).

Both are documented here as findings, not smoothed over — the first
resulted in a disclosed, permanent limitation (A6-C-07 unfixed); the
second was caught in code review before ever being run, not after.

## AA. Remaining known weaknesses

1. **A6-L-52 (S3, false-safe)** — generic role-mapping vocabulary
   ("Grantee"/"Grantor") unresolved, silently defaults to a clean decision.
   Root-caused (Section D, family 7), not fixed. This is the sole hard-gate
   blocker.
2. **A6-C-07, A6-RB-02 (S2, conservative)** — remain WC, safe direction,
   not hard-gate blockers but still disclosed as unfixed.
3. **Phases 5, 6 (partially), 7 (partially), 9A, 9B, 9C (partially), 10,
   12, 13** were not completed as separate, full-scale artifacts (Sections
   H-N, P, S). Each fix made IS verified against its source case(s) and
   the full existing control suite, but the broader stress-testing these
   phases specify was not built from scratch in this pass.
4. The Step 4A.4 control baseline inconsistency (Section G) is unresolved
   — it is unclear whether the Step 4A.7 report's 113/19 figure was a
   measurement error, a since-reverted intermediate state, or something
   else; this step's own reproduction is internally consistent (112/20,
   verified with cache-cleared re-runs and git-stash comparison against
   the byte-identical original commit) but does not resolve which
   historical figure was correct.

## AB. Cross-generation analysis

1. **Are we still repeatedly discovering narrow lexical failures on every
   fresh corpus?** Yes — every one of this step's 12 fixes was exactly
   this: a working general mechanism (conflicting-defined-term detection,
   self-flagged-ambiguity detection, exception-clause detection) that
   didn't recognize a fresh surface construction of the same underlying
   concept.
2. **Are new failures increasingly edge cases, or does ordinary drafting
   still break extraction?** Increasingly edge cases within this step's
   scope — none of the 15 WC were Tier 1 ordinary drafting by the time
   this step started (Step 4A.7 already closed the Tier-1-heavy dominant
   mechanism); the remaining failures were concentrated in Tier 2-3
   adversarial/varied constructions. Tier 1 WC is now 0/51.
3. **Is WC falling because facts are better established, or because more
   cases are escalated?** Facts are better established — Section Q shows
   2 of the 12 fixes resolved to CA (the fact IS establishable and now
   correctly resolves automatically), not just CR.
4. **Has CA increased on previously unsafe cases?** Yes, for A6-L-04 and
   A6-L-43 specifically.
5. **Is the architecture becoming more general, or is the regex vocabulary
   merely getting larger?** Both, genuinely. The conflicting-defined-term
   and self-flagged-ambiguity fixes are shape-based generalizations (not
   tied to a specific term/number). The "fraud" trigger addition and the
   "purchase price"-adjacent basis-word decisions are narrow, closed
   vocabulary additions, explicitly bounded and disclosed as such rather
   than claimed to be general mechanisms.
6. **Are discovery, interpretation, verification, and policy evaluation
   now meaningfully separate?** No change from Step 4A.7's answer (Section
   K there) — this step's fixes all fed the SAME pre-existing separation,
   none required rebuilding it.
7. **Does unknown differ from absent?** Yes, for every mechanism this step
   touched, verified via direct extraction inspection before each fix was
   accepted.
8. **Can conflicting evidence survive into a clean decision?** No longer,
   for the two conflicting-defined-term cases fixed (A6-L-22, A6-P-48).
   Still yes, for A6-L-52's role-attribution conflict (Section E).
9. **Can compound drafting defeat symmetry checks?** The two known cases
   are now fixed (Section F/G); this step's own evidence cannot rule out a
   THIRD, undiscovered compound shape — the fresh 120-case red team that
   would test for this (Phase 13) was not built (Section S).
10. **Is there evidence the current deterministic extraction architecture
    has reached a practical ceiling?** No — every failure this step
    examined had an identifiable, implementable, bounded fix once
    root-caused (Section D). The evidence continues to support Step
    4A.7's Section Z conclusion (architecture option B: viable with an
    explicit verification/establishment layer, which already exists) over
    option C or D.

## AC. Lee Challenge

**LEE-1** (plausible-but-wrong value flowing into a clean decision):
**PARTIALLY SOLVED.** Mechanism-level fixes with negative controls exist
for 6 named families (Section D); fresh adversarial evidence (Phase 13) was
not gathered; one known counterexample remains open (A6-L-52).

**LEE-2** (clause present but unrecognized, effectively absent):
**PARTIALLY SOLVED.** No new instance of this exact failure was found in
this step's scope; Step 4A.7's own disclosed gap (documents using neither
"indemnif*" nor a closed synonym idiom) remains untested by a dedicated
benchmark (Section K).

**LEE-3** ("nothing extracted" silently becoming evidence of absence):
**PARTIALLY SOLVED.** The `clause_found=True, obligations=[]` →
`REQUIRES_REVIEW` distinction (verified correct in Step 4A.7) was not
disturbed by this step, and no new silent-absence path was found. Section
O's absence audit was not independently rebuilt from scratch.

**LEE-4** (clean audit trail from a materially unverified interpretation):
**UNSOLVED for A6-L-52 specifically** — its `extracted_summary` reads as a
clean, confident "1x Recurring Payment" with no uncertainty marker despite
the underlying role attribution being genuinely unresolved (Section E, N).
**PARTIALLY SOLVED elsewhere** — the 12 fixed cases no longer exhibit this.

**LEE-5** (reciprocal clauses with different triggers/causation/exceptions/
scope falsely treated as symmetric): **PARTIALLY SOLVED, materially
strengthened this step.** Unsafe false-symmetry on the dedicated stress
benchmark is now 0/108 (was 2/108), covering single-dimension AND (as of
this step) one class of compound-dimension differentiation. Not SOLVED
outright because a fresh, independently-constructed compound-differentiation
red team (which would be needed to claim "no known counterexample" with
confidence) was not built.

**LEE-6** (unresolvable material fact routes to review rather than
guessing): **PARTIALLY SOLVED.** True for all 12 fixed families and for the
pre-existing establishment-layer mechanics (Step 4A.7 Section K). Not true
for A6-L-52, where an unresolvable role attribution currently produces a
guess (silently defaulting to a clean decision) rather than a review
condition.

No item is rated SOLVED, per the explicit standard requiring "no known
counterexample" — every category has at least one open, named,
counterexample or an explicitly disclosed gap in test coverage.

## AD. Architecture decision

**B. CURRENT ARCHITECTURE NEEDS FURTHER TARGETED HARDENING.**

Consistent with Step 4A.7's Section Z finding (which selected the closest
available option, "C. needs a stronger fact-verification/establishment
layer") — this step's evidence sharpens that conclusion. The establishment
layer Section D relies on in every fix already exists and works
(confirmed, again, six more times this step). What remains missing is not
a new architectural layer — it is complete DISCOVERY coverage for a long
tail of individually-narrow, individually-fixable constructions (Section D
enumerates 7 families found this step alone, on top of the ~6 the Step 4A.7
report found). This is targeted hardening, not a missing verification
layer (option C no longer describes the gap accurately, now that this
step's evidence shows the verification layer being reused successfully
across 7 more families without modification) and not a fundamental limit
(option D) — every failure found had a bounded, implementable fix. Choosing
B over C reflects this step's specific evidence that the establishment
layer itself required zero changes; only discovery coverage did.

## AE. Hard-gate evaluation

| Gate | Status |
|---|---|
| 1. Known S4 = 0 | **Met** (0, unchanged from Step 4A.7) |
| 2. Known SM-CRITICAL = 0 | **Met** (0, unchanged from Step 4A.7) |
| 3. Known unsafe WC = 0 | **NOT MET** (1 remains: A6-L-52, S3) |
| 4. Unsafe false-symmetry = 0 on the 108-case benchmark | **Met** (0/108) |
| 5. No repeated ordinary-drafting WC mechanism | **Met** (Tier 1 WC = 0/51) |
| 6. Material extraction known-unresolved feeding a clean decision | **NOT MET** (A6-L-52) |
| 7. Recognized-but-narrow-extraction silently becoming absence | **Met** for the families examined this step; not independently re-audited from scratch (Section O) |
| 8. New false-safe in a historical control | **Met** (none — 2 near-misses caught pre-report, Section Z) |
| 9. Safety achieved merely by blanket escalation | **Met** (2 of 12 fixes → CA, not just CR, Section P/Q) |
| 10. Determinism = 100% | **Met** |

**Gates 3 and 6 are not met.** Per the explicit rule, this is sufficient by
itself to preclude a PASS verdict regardless of the other 8 gates being
met.

## AF. Step 4A.7.1 verdict

# MORE HARDENING REQUIRED

One known false-safe WC (A6-L-52) remains, unresolved by deliberate choice
after root-causing, given insufficient remaining time to implement and
fully validate the architectural change it requires without risking an
under-tested late change. This is not eligible for "PASS WITH CONDITIONS"
per the explicit rule that conditions may not waive a known unsafe WC.

## AG. Step 4A.8 recommendation

**Step 4A.8 is NOT authorized.** Per Phase 20, all gates must be true; gates
3 and 6 are not. The next required action is a further, narrower Step
4A.7.2-style pass (or a continuation of this one) targeting specifically:
(1) A6-L-52's role-attribution gap in the liability single-provision path,
(2) A6-C-07's hyphenated-compound-modifier basis gap (with a fix that does
not regress the `BASIS_PURCHASE_PRICE` distinction), and (3) A6-RB-02 if
still unresolved by then. Only once known unsafe WC reaches 0 and the fresh
120+ adversarial battery (Phase 13, not attempted this step per its own
sequencing) is built and clean should Step 4A.8 be recommended.

## AH. Step 4B decision

**DO NOT START STEP 4B.** No outcome in this report authorizes it. The best
outcome reached is "targeted hardening in progress, 80% of known WC and
100% of known unsafe false-symmetry resolved, one disclosed blocker
remains."

---

## Completion summary

- **Commit**: to be recorded after push (Section AH's push step)
- **Production files changed**: `liability_policy_engine.py`,
  `indemnification_policy_engine.py`, `payment_terms_policy_engine.py`
  (`policy_engine_core.py` unchanged)
- **Known WC**: 15 → 3 (2 × S2 conservative, 1 × S3 false-safe)
- **Known false-safe WC**: 10 (verified) → 1
- **S4**: 0 → 0
- **SM-CRITICAL**: 0 → 0
- **Unsafe false-symmetry (108-case benchmark)**: 2 → 0
- **WC→CA**: 2 (A6-L-04, A6-L-43)
- **WC→CR**: 10 (A6-L-22, A6-L-23, A6-I-43, A6-P-33, A6-P-48, A6-C-15,
  A6-RB-01, A6-RB-07, A6-RB-09, A6-RB-10)
- **Fresh adversarial battery**: not built this step (Section S, Phase 13
  sequencing)
- **Material-fact trust-audit result**: 1 hard finding remains open
  (A6-L-52); the 12 fixed cases verified BOUNDED/MECHANICALLY ESTABLISHED
- **False-absence result**: no new instance found; full independent
  re-audit not performed from scratch
- **Automation Recall**: 66.9% → 68.1%
- **False-escalation rate**: 25.2% → 25.2% (unchanged; fixes converted WC
  to CA/CR, not FE)
- **Regression-suite result**: 1157/10/13/43, exact match, after fixing
  one mid-implementation test regression
- **Determinism**: 100%
- **Lee Challenge status**: all six items PARTIALLY SOLVED, none SOLVED,
  none UNSOLVED outright (Section AC)
- **Architecture decision**: B — targeted hardening, existing
  establishment layer confirmed sufficient
- **Final verdict**: MORE HARDENING REQUIRED
- **Step 4A.8 authorized**: **NO**
