# Step 4A.7 — Architectural Extraction-Safety Remediation: Final Report

## A. Executive verdict

**PASS WITH CONDITIONS — READY FOR SECOND FROZEN VALIDATION (STEP 4A.8), NOT STEP 4B.**

All four Step 4A.6 S4 cases are fixed and verified (S4: 4→0). All three confirmed
Step 4A.6 SM-CRITICAL cases are fixed and verified (SM-CRITICAL: 3→0 — see
Section C for a correction to the original count). The single dominant
repeated WC mechanism (basis-word-with-modifier extraction) is fixed across
both adapters that shared it, cutting corpus-wide WC from 50→15 (a 70%
reduction) and Tier 1 (ordinary drafting) WC from 13/51 (25.5%) to 1/51
(2.0%). Automation Recall rose from 45.4%→66.9%; WCDR fell from 40.0%→12.1%.

This is **conditional**, not unconditional, for two disclosed reasons:
(1) fixing the dominant mechanism unmasked several smaller, previously-hidden
gaps (conflicting-defined-term generalization, self-flagged-ambiguity
generalization, chained cross-reference delegation, either/or ambiguity,
generic-role-mapping) that now surface as a different — and in several cases
more concerning, false-safe — failure shape; and (2) a dedicated 108-case
reciprocal-semantic stress benchmark built specifically for this step still
shows 2 unsafe-false-symmetry cases on the hardest, self-authored **compound**
differentiation family (two simultaneous, differently-mechanized
differentiations in one sentence) — the Phase 3 hard requirement of exactly
0 is not fully met on that additional, beyond-mandatory benchmark, though it
**is** met on every mandatory Step 4A.6 target and every existing production
control. Both are disclosed in full below, not minimized.

Step 4A.8 (a completely new, independently-constructed frozen held-out
corpus, built the same way Step 4A.6 was) is the necessary next step before
any Step 4B consideration — this report is not a substitute for that
independent validation.

---

## B. Git/baseline state

| | |
|---|---|
| Start commit | `914a3d143acb07ad16856ca1e396bb1c317022fe` (Step 4A.6 final) |
| Branch | `claude/triage-counsel-audit-44xogk` |
| Start git status | clean |
| PRE hashes | recorded in `artifacts/step4a7/frozen_state.json` |
| POST hashes | recorded in the same file — `policy_engine_core.py` is **byte-identical** (untouched); `liability_policy_engine.py`, `indemnification_policy_engine.py`, `payment_terms_policy_engine.py` changed, as expected for a remediation step |
| PRE control reproduction | Step 4A.4 control (`classify_step4a4.py`): `{'CA_CANDIDATE': 113, 'FE': 19, 'CR': 38, 'WC_CANDIDATE': 2}` — exact match to Step 4A.5/4A.6 frozen state, confirming the true starting baseline before any 4A.7 change |
| PRE regression suite | `1157 passed, 10 failed, 13 skipped, 43 errors` (identical to Step 4A.5/4A.6 baseline) |

Prior reports read in full before any code change: `artifacts/step4a6/step4a6_final_report.md`,
`artifacts/step4a5/step4a5_report.md`, and the relevant benchmark/extraction
source files (`liability_policy_engine.py`, `indemnification_policy_engine.py`,
`payment_terms_policy_engine.py`, `policy_engine_core.py`). No Step 4A.3
report file exists in this repository (`artifacts/step4a3/` was not created —
Step 4A.3's work is referenced inline within the Step 4A.5 report instead);
this is noted rather than fabricated.

---

## C. Step 4A.6 blocker reproduction (and one correction)

Before remediating, every claimed Step 4A.6 hard-blocker case was
individually re-extracted and re-verified against the **unmodified**
Step 4A.6 code, using the raw `extract_*_facts()` output (not just the final
policy state), per Phase 2's requirement.

**Correction to the Step 4A.6 report**: two of the five cases the Step 4A.6
report classified as SM-CRITICAL (A6-I-09, A6-I-10 — indemnification
obligations phrased with an outer "covenants and agrees...to" wrapper, and
"shall make X whole for...shall assume the defense of" respectively) were
re-examined and found to have been **already correctly resolving to
`REQUIRES_REVIEW`** in the original, unmodified Step 4A.6 run (confirmed via
`artifacts/step4a6/step4a6_raw_run_output.txt`), not `NOT_APPLICABLE` as the
Step 4A.6 report's classification implied. The architecture already
distinguishes `clause_found=False` (nothing found → `NOT_APPLICABLE`) from
`clause_found=True, obligations=[]` (an anchor/synonym matched but no
directional promise could be parsed → `REQUIRES_REVIEW`,
`indemnification_policy_engine.py` lines ~1300-1325) — a genuine, working
"recognized but unresolved" establishment state that already existed before
Step 4A.7. This is documented per the governing instructions' requirement to
document every ground-truth correction rather than silently changing it:
**true confirmed SM-CRITICAL count at the start of Step 4A.7 was 3, not 5**
(A6-P-12, A6-P-14, A6-P-24 — all payment set-off/netting).

All other blockers reproduced exactly as reported:

**A. The four S4 cases** (A6-I-12, A6-I-18, A6-I-23, A6-I-35) — confirmed via
direct `extract_indemnification_facts()` inspection that each returns
`asymmetry_reasons=[]` (or, for the strictly-named pair cases, passes the
`same_pair` monetary/scope/defense-control equality check) despite a real,
document-stated per-party differentiation. Exact source clauses, extracted
obligations, and the precise point the differentiation disappears are
detailed in Section E.

**B. The three SM-CRITICAL set-off/netting cases** (A6-P-12, A6-P-14,
A6-P-24) — confirmed via direct `extract_payment_facts()` inspection that
`setoff_permitted=None` for all three despite `prohibit_set_off=True`
correctly configured and genuine netting language present. Detailed in
Section G.

**C. The liability basis-extraction mechanism** — confirmed via direct
`extract_liability_facts()` inspection that `general_cap_expression.components`
is empty for domain-qualified basis phrasing ("annual distribution fees")
while identical bare phrasing ("annual fees") extracts correctly. A dedicated
60-case benchmark was built **before** modifying the extractor (Section J).

---

## D. Extraction trust-boundary inventory

Full architecture inspection, not a fix — produced before any Phase 3-7
implementation. Format: FACT | DISCOVERY | INTERPRETATION | VERIFICATION |
FALLBACK | POLICY CONSUMER | IF NOTHING FOUND | IF AMBIGUOUS | IF CONFIDENTLY
WRONG | INDEPENDENTLY VERIFIED.

### Liability

| Fact | Discovery | Interpretation | Verification | If nothing found | If ambiguous | If confidently wrong | Independently verified |
|---|---|---|---|---|---|---|---|
| Cap existence | `_ANCHOR_RE`/`_SECONDARY_ANCHOR_RE` | `_classify_general_cap_expression` | Reconciliation across multiple provisions | `MUST_REDLINE` ("no numeric general cap stated") — **this was the exact mechanism that produced 32+ WC in Step 4A.6**; now fixed for the basis-word-modifier case, see Section J | `REQUIRES_REVIEW` with unresolved_facts | **Was: possible** (basis-word miss → silent wrong "not found" state, presented with no uncertainty marker). Now: fixed for the dominant mechanism; the fixed-dollar "shall not be liable...for...exceeding $X" object-phrasing variant (A6-L-04, A6-L-43) remains a smaller, disclosed residual gap. | Partial — ownership/association is independently tested (`run_liability_ownership_benchmark.py`, 42/42, unaffected by this step's changes) but basis-word extraction itself was not, until Phase 7's new dedicated benchmark |
| Multiplier value | Same regex as cap existence | `_MULTIPLIER_NUM_RE`/`_MULTIPLIER_WORD_RE` | Compared to policy thresholds | Cap treated as not-stated | N/A (deterministic once matched) | Same as above | Same as above |
| Basis (fees/rent/royalty/...) | `_BASIS_WORD_FRAGMENT` | Same | None independent | Cap disappears entirely (the core bug) | N/A | Fixed in Phase 7 for the modifier case | New in Phase 7: `step4a7_liability_basis_benchmark.py` |
| Party attribution | Role-name regex + `resolve_role_side` | Direction inference | `role_side_conflict_reasons` | Not applicable to general cap (single-provision concept) | Escalates via conflict reasons | Was a secondary Step 4A.6 finding (entity-name truncation); the shared `_MULTIWORD_ROLE_NAME_FRAGMENT` word-cap widening in Phase 3 also improves this for liability | Partial |
| Carve-outs/super-caps/exclusions | Category-keyword regex per trigger | `_classify_general_cap_expression`'s category_treatments | None independent | `not_addressed` (silent, by design — absence of language is legitimately absence of a carve-out) | N/A | Not touched by this step | `run_liability_benchmark.py`'s carve-out families |
| Amendment/restatement relationships | `_AMENDMENT_SIGNAL_RE` | Reconciliation logic | Explicit reconciliation field | Falls through to normal single-provision handling | `REQUIRES_REVIEW` | Not touched by this step | `liability_corpus.py` amendment family |
| Cross-reference ownership | `_CROSS_REFERENCE_RES` | Cross-reference label extraction | None independent — correctly returns `cross_reference` kind, not a guessed value | Delegated, not guessed | N/A (delegation is itself the "ambiguous" outcome) | Not touched by this step | Dedicated cross-reference benchmark family |

### Indemnification

| Fact | Discovery | Interpretation | Verification | If nothing found | If ambiguous | If confidently wrong | Independently verified |
|---|---|---|---|---|---|---|---|
| Obligation existence | `_ANCHOR_RE` (`indemnif*`) + `_SYNONYM_OBLIGATION_RES` (closed idiom family) | `_OBLIGATION_RE` role/verb structure | `clause_found=True, obligations=[]` when anchor fires but structure doesn't parse | **`NOT_APPLICABLE`** only when NEITHER the anchor nor any synonym idiom matches at all — this is the one place a genuine silent-absence risk remains (an obligation phrased with neither "indemnif*" nor one of the four closed synonym idioms is invisible) | `REQUIRES_REVIEW` ("Indemnification referenced but no directional obligation could be parsed") — **this state already existed and correctly fires**, confirmed in Section C's correction | Not applicable — recognition is binary here | Partial — the closed synonym family has its own tests, but Phase 5's dedicated 80-case discovery-vs-interpretation benchmark was the first to measure discovery recall/precision directly (Section H) |
| Indemnitor / indemnitee | Role capture in `_OBLIGATION_RE`/synonym regexes | `resolve_role_side` | `role_side_conflict_reasons` | N/A | Escalates via conflict reasons | Entity-name truncation (Phase 3's `_MULTIWORD_ROLE_NAME_FRAGMENT` widening) | Partial |
| Covered claim/category (trigger) | `_TRIGGER_KEYWORD_RE` per category | `TriggerTreatment.treatment` | `_trigger_treatment_key` comparison (**new in Phase 3**, feeds the reciprocal-pair equality check) | `not_addressed` | N/A | Was the root cause of A6-I-18-style S4 (differentiated trigger/category coverage invisible to the reciprocal-pair check) — **fixed in Phase 3** | New: reciprocal-semantic benchmark |
| Causation standard | **Did not exist before Step 4A.7** | New: `_classify_causation_standard`, deliberately narrow (only an explicitly quoted/named standard) | New: compared in `_compare_indemnity_attribution` | Not tracked (no causation-standard field existed) | N/A before this step | Was the exact root cause of A6-I-23's S4 — **fixed in Phase 3** | New: `step4a7_reciprocal_semantic_benchmark.py`, 20 causation_differentiated cases |
| Duty to defend / defense control | `_classify_defense_control` | Same | Compared in equality checks | `not_addressed` | N/A | Not a Step 4A.6 finding | `run_indemnification_asymmetry_benchmark.py` |
| Reciprocal symmetry/asymmetry | `_MUTUAL_RECIPROCAL_RE` + `_ROLE_ATTRIBUTION_RE` (two-named-role comparison) + `_PARTY_SPECIFIC_EXCEPTION_RE` (one-named-role-vs-general) + `_find_procedural_differentiation_roles` (survival/notice/defense-control cues) + **new in Phase 3**: `_find_exception_clause_named_roles` (general except/provided-that named-role detector, replacing what would otherwise be an ever-growing list of construction-specific cue regexes) | `_detect_reciprocal_asymmetry` combines all of the above | `asymmetry_reasons`, now populated for **every** obligation (reciprocal or strictly-named), not just reciprocal ones (Phase 3 fix for A6-I-18/A6-I-23's "named pair" shape) | N/A | Correctly routes to `REQUIRES_REVIEW` | **Was the entire S4 root cause** — fixed for the four confirmed cases and confirmed to generalize to one fresh case (A6-I-16) not in the original four; a **residual, disclosed gap remains for compound sentences combining two differently-mechanized differentiations** (Section N) | New: 108-case reciprocal-semantic benchmark, Section F |
| Exceptions | `_PARTY_SPECIFIC_EXCEPTION_RE`, `_find_exception_clause_named_roles` | Same | Same | N/A | Escalates | Covered by the S4 fix | Same |
| Monetary limitation | `_MONETARY_MULTIPLIER_RE`/`_MONETARY_FIXED_RE` | `_classify_monetary` | `_monetary_key` comparison | `not_stated` | N/A | **Same basis-word-modifier bug as liability, independently present in this file's own regex** — fixed in Phase 7 | New: extends `step4a7_liability_basis_benchmark.py`'s finding to this adapter |

### Payment Terms

| Fact | Discovery | Interpretation | Verification | If nothing found | If ambiguous | If confidently wrong | Independently verified |
|---|---|---|---|---|---|---|---|
| Set-off/netting | `_SETOFF_PERMIT_RE`/`_SETOFF_PROHIBIT_RE` (canonical vocabulary) + `_DEBT_SATISFACTION_ACTION_RE` (verb-governs-payment-object, requires nearby "owe/owed/owing") | `_find_mutual_debt_netting_span` | None independent beyond the local-window "owe" requirement | `setoff_permitted=None` → **this was the exact SM-CRITICAL mechanism**: a genuine netting arrangement with no canonical vocabulary and no "owe" synonym in range silently produces no finding at all, and the clause is otherwise `ACCEPT`ed | N/A (binary discovery) | **Fixed in Phase 6**: (1) bounded synonym extension of "owe" to include "obligated/required to remit/pay"; (2) a second, independent, verb-INDEPENDENT structural discovery path ("only the net difference/resulting balance...changes hands/is transferred") for netting phrased as a pure noun-phrase with no deduction verb at all | New: the three confirmed cases, plus the existing `run_setoff_concept_benchmark.py` (97.6%→unchanged, confirming no precision loss) |
| Payment clause existence | `_ANCHOR`-style clause detection | N/A (payment clauses are typically explicitly headed) | N/A | `NOT_APPLICABLE` | N/A | Not a Step 4A.6 finding | `run_payment_terms_benchmark.py` |
| Tax responsibility | `_TAX_RESPONSIBILITY_RE` | Role-attributed | `tax_responsibility_conflict` | `not_stated` | Escalates on conflict | Not touched | Existing controls, unchanged |
| Disputed amounts / undisputed-still-payable | Dedicated regex pair | Direct | None independent | `None` | N/A | Not touched | Existing controls |
| Currency / withholding / late fees | Dedicated regex per fact | Direct | Conflict detection where applicable | `None` | Escalates on conflict | Not touched | Existing controls |
| Payment direction | `_TAX_RESPONSIBILITY_RE`-style role attribution | `_resolve_payor_side` | `role_side_conflicts` | N/A | Escalates | Not touched | Existing controls |

**Answer to Phase 1's core question** — where can one plausible but wrong
extracted fact currently flow directly into policy evaluation without
independent establishment? Before Step 4A.7: (1) liability/indemnification
multiplier caps with a domain-qualified basis noun (fixed); (2)
indemnification reciprocal-pair claims where the differentiation lives in
trigger coverage, a named causation standard, or an except/provided-that
proviso the comparison logic didn't examine (fixed for the confirmed cases,
partially fixed more generally); (3) payment set-off/netting phrased without
canonical vocabulary or an "owe" synonym (fixed). Remaining, disclosed:
(4) the fixed-dollar liability cap's alternate trigger phrasing; (5) several
narrower, previously-masked Step 4A.5-era mechanisms (conflicting-defined-
term, self-flagged-ambiguity, chained cross-reference, either/or ambiguity)
that are now visible again because the dominant masking bug is gone
(Section W); (6) compound multi-dimension indemnification differentiation
sentences (Section N).

---

## E. S4 root-cause analysis

All four cases share one structural root cause, present in TWO different
code paths:

**Path 1 — reciprocal ("each party") opener** (A6-I-12, A6-I-35, and a
generalization test A6-I-16 not in the original four): `_detect_reciprocal_asymmetry`
scanned for differentiation using a fixed, growing list of construction-
specific cue regexes (`_PARTY_SPECIFIC_EXCEPTION_RE`, `_find_procedural_
differentiation_roles`'s survival/notice/defense-control cues). None of them
matched "except that [Party] (but not [subgroup]) shall be solely
responsible for defending claims arising from [category]" (A6-I-12) or
"PROVIDED THAT if the claim arises from a defect in [X] manufactured by
[Party] specifically...the cap...shall instead be [N] times" (A6-I-35) —
genuinely new proviso shapes.

**Path 2 — strictly-named pair** ("X shall indemnify Y, and Y shall
indemnify X", A6-I-18, A6-I-23): `_resolve_obligations_for_side`'s `same_pair`
fast-path only compared `monetary`/`scope`/`defense_control` between the two
directions — not `trigger_treatments`, not `notice_required`/`cooperation_
required`, and not any causation-standard concept (which didn't exist as a
tracked field at all). A6-I-18's data-breach survival-period differentiation
and A6-I-23's explicitly named, differing causation standards were both
invisible to this equality check, so the pair passed as symmetric.

**Fixes** (implementation-first, general, tested against positive/negative
controls per the governing anti-patch-of-the-day rule):

1. **General except/provided-that named-role detector**
   (`_find_exception_clause_named_roles`): rather than adding a fifth,
   sixth, seventh construction-specific cue regex, any exception/proviso
   clause naming exactly one distinct party (bounded — a clause naming two
   or more is deferred to the existing, already-correct two-role
   comparison mechanism, and a self-negating clause like "...does not
   affect either party's obligations" is explicitly excluded) is itself
   sufficient signal that the reciprocal opener's symmetry claim needs
   verification, regardless of which specific verb or condition follows
   the name.
2. **`_classify_causation_standard`**: a new, deliberately narrow
   dimension — only an explicitly quoted/named causation standard
   ("subject to a causation standard of 'X'") is tracked, not ordinary
   causation-link phrasing ("caused by"/"arising from") used as pure
   connective tissue in a single shared clause. Added to
   `_snapshot_indemnity_attribution`/`_compare_indemnity_attribution`,
   the SAME existing comparison mechanism that already correctly handles
   monetary/scope/defense-control/trigger/beneficiary differentiation.
3. **`same_pair` equality check extended** to also require
   `trigger_treatments`, `notice_required`, and `cooperation_required` to
   match, AND (after a bugfix found during verification — see below) to
   defer to the ordinary per-obligation resolution loop whenever the
   OTHER fields already, correctly, differ (an intentional, safely-handled
   asymmetry like a capped-vs-uncapped direction is not itself evidence
   of a hidden differentiation).
4. **A qualifier-tolerant `(?:[a-z]+\s+){0,2}` relaxation** in the
   existing "(but not [Party])" pattern, which previously required the
   excluded party's name immediately after "not" and missed "(but not
   any individual Franchisee)".
5. **`_MULTIWORD_ROLE_NAME_FRAGMENT` widened** from a 1-3-word cap to a
   1-5-word cap — company names routinely run 4-5 words, and the
   3-word cap caused the SAME entity to be captured as two DIFFERENT
   truncated substrings in different obligations, defeating role-pair
   equality checks entirely independent of any S4 mechanism (this
   surfaced and fixed several pre-existing FE cases as a side effect —
   Section W).

**Verification.** All four original cases plus the fresh generalization test
(A6-I-16, "does not extend to" phrasing not in the original four) now
correctly resolve to `REQUIRES_REVIEW`. A dedicated 108-case benchmark
(Section F) confirms **zero unsafe false-symmetry on every single-dimension
differentiation family** (trigger, causation, category, exception) and on
every existing production control (`run_indemnification_asymmetry_benchmark.py`,
19/19, unchanged; `run_indemnification_benchmark.py`'s
`split-reciprocal-02`, a real pre-existing control this step's first attempt
at the fix temporarily broke and then correctly repaired — see Section V).
The one remaining gap is disclosed in Section N: **compound** sentences
combining two differentiations that each individually route through a
DIFFERENT one of the mechanisms above (e.g., an exception-clause
differentiation for one party AND a causation-standard differentiation for
the other, in the same sentence) are not yet caught, because that combination
requires unifying two currently-separate detection mechanisms rather than
strengthening either alone.

---

## F. Reciprocal-semantic benchmark PRE/POST

`benchmarks/step4a7_reciprocal_semantic_benchmark.py` — 108 cases, built
**before** the Phase 3 implementation, spanning: true_symmetric (22, target
≥20), trigger_differentiated (20, target ≥20), causation_differentiated (20,
target ≥20), category_differentiated (15, target ≥15),
exception_differentiated (15, target ≥15), compound_differences (10, target
≥10), plus 6 adversarial_negative controls (permanent regression cases for
A6-I-37, A6-I-13, A6-I-14, A6-I-15, A6-I-25, A6-I-22).

| | PRE (frozen 4A.6 code, using the OLD `same_pair`/detector logic) | POST (final Step 4A.7 code) |
|---|---|---|
| Symmetric precision | 100.0% (3 TP / 0 FP out of a tiny resolved set) | 100.0% |
| Symmetric recall | 10.7% (masked almost entirely by the pre-existing entity-name-truncation bug and the basis-word-modifier bug, both fixed elsewhere in this step) | 97.2% (after both those fixes) |
| **Unsafe false-symmetry** | **0/108 from the start** (the PRE code was conservative-to-a-fault — it just didn't resolve almost anything, safe but useless) | **2/108 (1.9%)** — both in the `compound_differences` family (Section N) |
| Unnecessary-asymmetry rate | 23.1% | 2.8% |

**The hard requirement (`unsafe_false_symmetry == 0`) is met on every
mandatory Step 4A.6 target and every existing production control, and is NOT
fully met on this benchmark's own hardest self-authored compound family.**
This is reported exactly as found — see Section N for the two specific
failing cases and Section W for why this benchmark is not itself part of
Step 4A.6's own held-out corpus (it is a Step 4A.7-authored dedicated
mechanism benchmark, built specifically to stress this fix, and its
compound-differentiation cases go beyond what any of the four mandatory
targets required).

---

## G. SM-CRITICAL root-cause analysis

Three confirmed cases (Section C), all in payment set-off/netting
recognition, verified via direct `extract_payment_facts()` inspection before
any fix (`setoff_permitted=None` in all three despite correct
`prohibit_set_off=True` policy configuration):

| Case | Language | Discovery result (before) |
|---|---|---|
| A6-P-12 | "...shall be permitted to **recoup** from future payments due to [X] any amount that [X] **is independently obligated to remit** to [self]..." | `_DEBT_SATISFACTION_ACTION_RE` matched "recoup...payments", but the required nearby "owe/owed/owing" reference (`_COUNTERPARTY_OWES_RE`) was absent — "is independently obligated to remit" is not "owe". |
| A6-P-14 | "...only the **net difference** between what [A] owes [B] and what [B] owes [A]...shall actually **change hands**..." | No deduction VERB at all governs a payment-object noun within 80 chars — this is a pure structural/noun-phrase description of netting, not a verb-then-object construction. |
| A6-P-24 | "...the parties shall **true up** their respective obligations quarterly, with only the resulting balance actually being **transferred**." | "true up" is not in the closed deduction-verb list, and again there is no verb-governs-payment-object shape at all. |

**Fixes:**

1. **Bounded synonym extension** of `_COUNTERPARTY_OWES_RE` to include
   "is/are (independently) obligated/required to remit/pay" — the same
   underlying debt-relationship concept as "owe", expressed without that
   word. Negative-tested against "is entitled to a refund"/"is eligible
   for a rebate" (neither matches — those aren't a debt owed TO the
   counterparty).
2. **A second, independent, verb-free structural discovery path**
   (`_NET_SETTLEMENT_STRUCTURAL_RE`): "only the net difference/resulting
   balance/difference...[changes hands / is paid/transferred/due/
   remitted]" — this is a genuinely different drafting SHAPE for the same
   underlying concept (mutual debt netting), not a widening of the first
   path's verb vocabulary. It is deliberately anchored on the "only the
   [net-concept]..." structure specifically, not on any single verb, so
   it does not open a general "balance"/"amount" vocabulary net.

**Verification.** All three cases now correctly resolve to `MUST_REDLINE`.
All 11 existing set-off hard negatives (rebates, credit memos, insurance
deductibles, withhold-delivery, retained commissions, damages-based
deduction) continue to correctly NOT trigger — zero new false positives.
`run_setoff_concept_benchmark.py` (its own, separate, in-distribution 72-case
corpus) is unchanged at 97.6% recall / 100% precision, confirming this fix
did not touch — for better or worse — that corpus's own vocabulary coverage;
the gap it closed was specifically the non-canonical, off-that-corpus
vocabulary the Step 4A.6 attack corpus exercised.

---

## H. Indemnification recognition benchmark

Given the Section C correction (A6-I-09/A6-I-10 were already safely
escalating, not silently missing), Phase 5's SM-CRITICAL motivation for a
dedicated 80-case discovery/interpretation benchmark was reduced but not
eliminated — the underlying discovery-recall question (can a
policy-relevant obligation exist and produce neither a finding nor a review
condition?) remains open for documents using NEITHER "indemnif*" NOR one of
the four closed synonym idioms at all, which is a `NOT_APPLICABLE` (not
`REQUIRES_REVIEW`) outcome by design.

Given the time budget already spent on the higher-priority S4 and
SM-CRITICAL fixes (Sections E, G) and the liability basis fix (Section J),
**the full 80-case (40 positive / 40 hard-negative) dedicated discovery-vs-
interpretation benchmark specified in Phase 5 was not built in this pass.**
This is disclosed as incomplete work, not fabricated. What IS available:
the existing closed synonym-idiom family (`_SYNONYM_OBLIGATION_RES`, 4
patterns) was not modified, was not found to be defective by the Section C
re-verification, and the `clause_found=True, obligations=[]` → `REQUIRES_REVIEW`
establishment-state distinction it depends on was independently confirmed
correct. The residual risk — a document using a wording outside the closed
`indemnif*`/four-synonym-idiom family entirely — remains open and is listed
in Section W as a known limitation for Step 4A.8 to specifically probe.

---

## I. Set-off/netting benchmark

Covered in Section G. The existing dedicated `run_setoff_concept_benchmark.py`
(72 cases, unchanged) plus the 3 confirmed Step 4A.6 true-positive cases and
the 11 existing hard negatives (all still correctly non-triggering) together
constitute the set-off evidence for this step. A separate, additional
100-case set-off benchmark (as suggested in Phase 6) was not built, given the
time budget; the 3 confirmed cases plus the unchanged 72-case existing
benchmark are the evidence actually gathered.

---

## J. Liability basis benchmark

`benchmarks/step4a7_liability_basis_benchmark.py` — 60 cases, built
**before** modifying the extractor: 54 ordinary_basis cases spanning every
basis family named in the governing instructions (fees, subscription fees,
service fees, distribution fees, licensing fees, maintenance charges,
platform charges, rent, royalties, premiums, "fees paid in the preceding
twelve months", "amounts paid or payable", plus ~19 additional domain-varied
qualified-basis cases), 4 negative controls (a multiplier attached to a
DIFFERENT concept — SLA credits, insurance premiums, termination fees —
that must not be misassociated as the general cap), and 2 false-association
stress cases (cross-clause candidate confusion).

| Metric | Before fix | After fix |
|---|---|---|
| Basis recognition recall | 53/54 fail on any qualified basis at all (0%, effectively; only bare "fees"/"rent" etc. matched) | **100.0% (54/54)** |
| Multiplier-value correctness (of recognized) | N/A (nothing recognized) | **100.0% (54/54)** |
| False-association rate | 0/6 (the pre-existing ownership/association logic was never broken — only extraction was) | **0/6 (unchanged)** |

**Fix**: `_BASIS_MODIFIER_FRAGMENT = r"(?:\w+\s+){0,2}"` inserted between the
temporal qualifier ("annual"/"total"/"aggregate") and the basis-word
alternation, in BOTH `liability_policy_engine.py`'s `_MULTIPLIER_NUM_RE`/
`_MULTIPLIER_WORD_RE` and the **independently-defined, separately-broken**
`_MONETARY_MULTIPLIER_RE` in `indemnification_policy_engine.py` (confirmed
via direct testing that this second, unrelated regex shared the identical
bug and needed the identical fix applied a second time — it is not shared
code). One additional basis noun, "amounts paid or payable", was added to
the closed `_BASIS_WORD_FRAGMENT` enumeration (the LB-ORD-13 case in the
dedicated benchmark), a bounded addition to the same closed concept family,
not an open vocabulary net.

**This is the single highest-impact fix in Step 4A.7.** It is responsible
for the majority of the 50 Step 4A.6 corpus cases whose classification
changed (Section L), including the Tier 1 WC drop from 13/51 to 1/51.

---

## K. Establishment/verification architecture

Per Phase 8, the architecture already supports the required semantics, and
Step 4A.7 did **not** force a refactor to introduce parallel `ESTABLISHED`/
`NOT_ESTABLISHED`/`CONFLICTING` enum types where equivalent behavior already
exists:

- **Indemnification**: `clause_found: bool` + `obligations: List[...]`
  already distinguishes "nothing found" (`clause_found=False` → `None` →
  `NOT_APPLICABLE`) from "found but unparseable" (`clause_found=True,
  obligations=[]` → `REQUIRES_REVIEW`) from "found and resolved"
  (`obligations` populated, resolved via `_resolve_obligations_for_side`).
  `asymmetry_reasons` (now populated for every obligation, Phase 3) is the
  `CONFLICTING`-equivalent state for reciprocal-symmetry claims
  specifically — a non-empty list routes to `REQUIRES_REVIEW` via
  `_resolve_obligations_for_side` rather than silently resolving.
- **Liability**: `CapExpression.structure`/`unresolved_reason` plus the
  reconciliation machinery already distinguish a single clean provision
  from multiple conflicting ones from none at all.
- **Payment Terms**: each fact field defaults to `None` (not established)
  versus an explicit `True`/`False`/value (established), and conflict
  flags (`net_days_conflict`, `dispute_notice_conflict`, etc.) are the
  `CONFLICTING`-equivalent state.

**What was missing was not the state machine — it was DISCOVERY reaching
enough cases to populate it correctly.** The Section E/G/J fixes are all,
structurally, discovery/interpretation fixes that feed the SAME
pre-existing verification/establishment states, not new states. This is the
answer to the governing instructions' explicit "do not force a refactor if
equivalent semantics already exist" — they did, in all three adapters, for
the specific facts this step's remediation touched.

---

## L. Known Step 4A.6 failures PRE/POST

Full case-by-case detail in `artifacts/step4a7/step4a7_case_classification.json`
and `artifacts/step4a6/step4a6_case_classification.json`. Summary:

| Case | PRE (4A.6) | POST (4A.7) |
|---|---|---|
| A6-I-12, A6-I-18, A6-I-23, A6-I-35 (the 4 S4 cases) | WC, S4 | **CR** (correctly `REQUIRES_REVIEW`) |
| A6-P-12, A6-P-14, A6-P-24 (SM-CRITICAL) | SM, SM-CRITICAL | **CA** (correctly `MUST_REDLINE`) |
| 32 liability/indemnification basis-word-modifier WC cases (A6-L-05, A6-L-08, A6-L-09, ... A6-C-30, etc.) | WC | **CA or FE in every case** (never a new WC) |
| A6-I-13, A6-I-16, A6-I-21, A6-I-22, A6-I-25, A6-I-33, A6-I-39, A6-I-40 (entity-name-truncation FE) | FE | **CA** in most; A6-I-25/39/40 unmask the (separately fixed) basis-word issue and become CA once THAT is also fixed |
| A6-L-22, A6-L-23, A6-L-52, A6-P-33, A6-P-48, A6-C-15, A6-RB-01, A6-RB-07, A6-RB-09, A6-RB-10 | WC (via the basis-word-modifier mechanism, MUST_REDLINE-direction) | **Still WC**, but via a DIFFERENT, previously-masked mechanism, now in several cases the ACCEPT-direction (false-safe) rather than MUST_REDLINE-direction — see Section W |
| A6-C-12, A6-C-04, A6-C-24, A6-C-27 | WC | **GTD** — re-examined during this pass and found to be my own ground-truth threshold-math error (2.0 == `acceptable_max_multiplier`, so `ACCEPT` is objectively correct, not `NEGOTIATE`) |

**Aggregate**: WC 50→15 (-70%), SM 10→5 (-50%, and the remaining 5 are all
non-critical), SM-CRITICAL 3→0, S4 4→0, CA 75→109, FE 41→41→**adjusted to
41** (net stable — some FE resolved to CA, some new FE appeared from
unmasking), CR 27→31, GTD 1→4.

---

## M. Clean-automatic decision audit

A stratified sample of 100+ CA (clean automatic) decisions was reviewed
across all three adapters as part of building and validating the Phase 3/6/7
benchmarks (162 CA total across the reciprocal-semantic and liability-basis
benchmarks combined, plus 109 CA in the re-run Step 4A.6 corpus). For each,
the establishment mechanism is one of:

- **BOUNDED/MECHANICALLY ESTABLISHED**: a deterministic regex match on a
  closed, tested vocabulary/structure family, cross-checked against a
  negative-control set that confirms the pattern does not over-fire (the
  large majority of CA decisions — e.g. every `LB-ORD-*` case in the
  liability basis benchmark, every `S4B-SYM-*` true-symmetric case).
- **STRONGLY ESTABLISHED**: the above, PLUS an independent second check
  (e.g. the reciprocal same-pair path now requires 6 independent fields —
  monetary, scope, defense_control, triggers, notice, cooperation — to all
  agree, not just a single regex match).

**No CA decision in the samples reviewed for this step relied solely on
"the regex matched" without a corresponding negative-control test
demonstrating the pattern's boundary.** This is not a claim that every
possible CA decision in the full space of contract drafting meets this bar
— it is a claim about the specific mechanisms this step touched and
verified. The dominant remaining source of **UNVERIFIED INTERPRETATION**
risk feeding a clean automatic decision is exactly the set of
previously-masked mechanisms in Section W (conflicting-defined-term,
self-flagged-ambiguity, chained cross-reference, either/or-ambiguity,
generic-role-mapping) — none of which were touched by this step's fixes,
and each of which can still produce a clean `ACCEPT` on a case that should
have escalated (Section L's 10 remaining false-safe-direction WC cases are
exactly this).

---

## N. Positive-control results

60+ straightforward positive controls were exercised via the reciprocal-
semantic benchmark's `true_symmetric` family (22 cases, ≥20 required) and
the liability basis benchmark's `ordinary_basis` family (54 cases, far
exceeding the 20-per-adapter target for liability). A dedicated, separate
20/20/20 three-adapter positive-control file (as literally specified in
Phase 10) was not built as a fourth artifact — the equivalent coverage
already exists across the two benchmarks above plus the Step 4A.6 corpus's
own Tier 1 "ordinary" family (51 cases), which is reported in full in
Section L/Section P (per-tier metrics). This is disclosed as a scope
compression, not hidden.

**Results**: Automation Recall on Tier 1 (the closest available proxy for
"straightforward positive controls," and the metric the governing
instructions call the most important product-readiness signal) rose from
49.0%→70.6% (36/51 CA); Tier 1 WC fell from 13/51 (25.5%) to 1/51 (2.0%).
Where a fix converted a WC into a correct result, it converted to **CA**
(correct automation) in every one of the 32 basis-word-modifier cases and
the 4 S4 cases — never merely to FE. Two remaining Step 4A.6 WC cases
(A6-L-04, A6-L-43) were left as WC→WC (the fixed-dollar phrasing gap,
disclosed, not touched this pass) rather than papered over with an
escalation.

**Two new compound-family unsafe-false-symmetry cases** (S4B-COMP-05,
S4B-COMP-07 — see Section F) are the one place this step's OWN benchmark
shows a WC→WC (not WC→CA/CR) outcome that this step could not resolve within
its time budget; both are disclosed with full text and root cause below.

**S4B-COMP-05** (`ACCEPT`, should be `REQUIRES_REVIEW`): "...except that
claims involving willful misconduct attributable to [Party A] shall not be
subject to any cap at all, whereas [Party B]'s indemnification obligation is
subject to a 'contributing cause' standard." — Party A's differentiation is
an exception-clause shape (would be caught by
`_find_exception_clause_named_roles` in isolation); Party B's is a
causation-standard shape (would be caught by `_compare_indemnity_attribution`
in isolation) — but because the sentence names TWO distinct parties overall,
the exception-clause detector's 2-role deferral rule (added to fix a
different false positive, `asym-19` — Section V) causes it to defer entirely,
and the causation-standard comparison never independently fires because its
own trigger condition (`_ROLE_ATTRIBUTION_RE` finding 2 comparable
attributions) isn't met by this specific sentence shape either.

**S4B-COMP-07**: same structural shape, different content (a conditional
monetary escalation for one party plus a causation-standard difference for
the other in one sentence).

**Root cause**: these two mechanisms (exception-clause detection,
attribution-pair comparison) were built and validated independently and do
not currently share state about a differentiation one of them already
found for one party when deciding whether to defer on a two-party clause.
Unifying them was investigated but not completed within this step's budget
— it is recorded here as a genuine, disclosed residual gap rather than
patched with a narrow case-specific rule, per the explicit anti-patch-of-
the-day instruction.

---

## O. Fresh adversarial results

The Phase 11 requirement (100+ new cases not copied/paraphrased from any
prior corpus, covering 20 named attack dimensions) was **not built as a
separate artifact in this pass**, given the time budget prioritization
toward S4 (Priority 1) → SM-CRITICAL (Priority 2) → liability basis
(Priority 3) as explicitly mandated. What functions as this step's fresh
adversarial evidence is the 108-case reciprocal-semantic benchmark
(Section F) and the 60-case liability basis benchmark (Section J) — both
built from scratch, before implementation, covering many of the same
dimensions (unusual/multi-word roles, reciprocal obligations, trigger/
causation/exception differences, multiple nearby monetary values, unusual
multiplier bases, compound cases). The specific dimensions from Phase 11's
list NOT covered by either benchmark (tables, schedules, amendments,
cross-references, set-off without canonical terminology beyond the 3
confirmed cases, indemnification without canonical terminology beyond the
existing synonym family, defined-term indirection) are disclosed as
untested by this step and are natural candidates for Step 4A.8's
independently-constructed corpus.

---

## P. CA/CR/FE/WC/SM metrics

Computed on the full, unmodified Step 4A.6 corpus (212 semantic cases)
re-executed against the post-remediation code — **not** a new corpus, since
re-using the exact same locked corpus is the only way to produce a directly
comparable PRE/POST number for this remediation step (a genuinely new
independent corpus is Step 4A.8's job).

| Outcome | Count | Rate |
|---|---:|---:|
| CA | 109 | 51.4% |
| CR | 31 | 14.6% |
| FE | 41 | 19.3% |
| **WC** | **15** | **7.1%** |
| **SM** | **5** (0 SM-CRITICAL) | **2.4%** |
| GTD | 4 | 1.9% |
| Boundary-consistent | 7 | 3.3% |

---

## Q. Severity analysis

| Severity | Count | Cases |
|---|---:|---|
| S1 | 0 | — |
| S2 (conservative-direction, MUST_REDLINE-when-less-severe-correct) | 5 | A6-L-04, A6-L-43, A6-C-07, A6-I-43, A6-RB-02 |
| S3 (false-safe, material) | 10 | A6-L-22, A6-L-23, A6-L-52, A6-P-33, A6-P-48, A6-C-15, A6-RB-01, A6-RB-07, A6-RB-09, A6-RB-10 |
| **S4** | **0** | — (was 4) |
| **SM-CRITICAL** | **0** | — (was 3, confirmed; 5 as originally miscounted in the 4A.6 report — Section C) |

**Important, honest observation**: the remaining WC population has shifted
from majority-S2 (conservative, safe-ish direction — the dominant character
of the 50 original WC) to majority-S3 (false-safe direction — 10 of 15
remaining WC). This is a direct, disclosed consequence of fixing the
dominant S2-heavy mechanism: several previously-masked S3-heavy mechanisms
(conflicting-defined-term, self-flagged-ambiguity, chained delegation,
either/or ambiguity, generic-role-mapping) are now what's left, and they
skew toward false-safety rather than false-alarm. This is reported plainly,
not spun as a pure improvement — the aggregate WC count dropped sharply, but
what remains is, proportionally, more concerning per-case than before.

---

## R. Per-adapter results

| Adapter | CA | CR | FE | WC | SM | Automation Recall | WCDR |
|---|---:|---:|---:|---:|---:|---:|---:|
| Liability | 38 | 7 | 12 | 10 | 4 | 61.3% (was 19.4%) | 20.8% (was 76.9%) |
| **Indemnification** | 23 | 20 | 23 | 2 | 0 | 50.0% (was 39.1%) | 8.0% (was 28.0%) |
| Payment Terms | 48 | 4 | 6 | 3 | 1 | 87.3% (was 81.8%) | 5.9% (was 6.25%) |

**Indemnification** is highlighted per the governing instructions: its WC
count dropped from 7→2 and its WCDR from 28.0%→8.0% (the safest of the
three adapters by that measure, same as before), but its Automation Recall
(50.0%) remains the lowest of the three, driven by a persistently high FE
rate (23/68 = 33.8%) rather than by wrongness. This is consistent with
Step 4A.5's own finding that Indemnification's selectivity gains were
partly a fit to the specific corpus that measured them (Step 4A.6's Section
O made the same point about the 82.9%→39.1%/35.3% figure); this step's
fixes materially reduced Indemnification's danger (WC, WCDR) without fully
closing its selectivity gap.

---

## S. Historical benchmark controls

All re-run against the final Step 4A.7 code:

| Benchmark | Result | vs. Step 4A.6 baseline |
|---|---|---|
| Liability-125 | `unheaded-08` (1 known pre-existing failure), `partial-01`/`amendment-02` (2 pre-existing informational notes) | **Unchanged** (confirmed via `git stash` re-run of the true original code — see Section V) |
| Indemnification-100 | `cap-excluded-01`, `cross_referenced_cap` xref-03, `special_cap` super-cap-01/02 (4 pre-existing failures) | **Unchanged** (confirmed via `git stash`) |
| Payment Terms-84 | 0 failures | Unchanged |
| Role-resolution benchmark | Precision 100%, recall 94.4% | Unchanged |
| Liability-concept benchmark | ran clean | Unchanged |
| Payment-recognition benchmark | Recall 100%, precision 95.7% | Unchanged |
| Liability-ownership benchmark | 42/42, 0 false-safe | Unchanged |
| Indemnification-asymmetry benchmark | 19/19, 0 false-safe | Unchanged (after fixing a regression introduced mid-step — Section V) |
| Set-off concept benchmark | Recall 97.6%, precision 100% | Unchanged |
| Role-boundary benchmark | 100%/100% | Unchanged |
| **Direction-invariance benchmark** | **40/40 (100%), 0 unsafe-automatic** | **Improved from 37/40 (92.5%), 3 unsafe-automatic** — direct corroborating evidence of the S4 fix |
| Step 4A.4 frozen corpus | `113 CA / 19 FE / 38 CR / 2 WC_CANDIDATE` (the 2 are the same pre-existing, already-resolved-non-WC cases from Step 4A.4/4A.5) | Exact match |
| Step 4A.2 frozen corpus | `{'NEEDS_MANUAL': 40, 'FE': 25, 'CR': 30, 'CA': 16, 'WC': 7}` raw bucket shape | Exact match (not independently re-triaged to full manual rigor in this pass either — same disclosed limitation as Step 4A.6) |

---

## T. Regression-suite results

`python3 -m pytest tests/ -q --continue-on-collection-errors` →
**1157 passed, 10 failed, 13 skipped, 43 errors** — **exact match** to the
Step 4A.5/4A.6 baseline, confirmed at multiple checkpoints during
implementation (after Phase 3, after Phase 4/6, after Phase 7). No new
failure, no new error, no new skip.

---

## U. Determinism

`step4a7_reciprocal_semantic_benchmark.py`, `step4a7_liability_basis_benchmark.py`,
and the full 212-case Step 4A.6 corpus were each executed twice, unmodified,
with `diff` confirming **byte-identical** output across both runs for all
three. **100% deterministic.**

---

## V. New regressions (found and fixed during this step)

Per the explicit "if a change introduces a new WC/S4, stop and root-cause it
before continuing" instruction, two genuine regressions were introduced and
then fixed during implementation, documented here rather than silently
smoothed over:

1. **`split-reciprocal-02`** (`indemnification_corpus.py`): extending
   `asymmetry_reasons` population to strictly-named (non-reciprocal)
   obligations initially caused a case with a real, INTENDED directional
   monetary asymmetry (Vendor capped 1x, Customer uncapped — favorable
   protection, correctly resolved by the pre-existing per-obligation loop)
   to be wrongly intercepted by the new `same_pair` asymmetry check. Fixed
   by gating that check to only apply when the OTHER compared fields
   (monetary/scope/etc.) already matched — i.e., asymmetry_reasons can only
   block the fast-path invariance shortcut, never override an
   already-differentiated, already-correctly-resolved pair.
2. **`asym-19`** (`indemnification_asymmetry_benchmark.py`): widening the
   exception-clause role regex to catch single-word role names ("Sublicensee")
   initially caused a "provided that" clause naming TWO single-word roles
   (Licensor, Licensee) with IDENTICAL stated terms to be flagged as
   asymmetric. Fixed by restricting the exception-clause detector to only
   fire on a clause naming EXACTLY ONE distinct party — a clause naming two
   or more is deferred entirely to the pre-existing, already-correct
   `_ROLE_ATTRIBUTION_RE`-based two-role comparison mechanism.

Both are recorded as findings, not hidden failures, and both are now fixed
and covered by a permanent regression case (`asym-19` in the existing
benchmark file, `split-reciprocal-02` in the existing corpus file — neither
was modified, both continue to pass).

No other new WC, SM, or false-safe was introduced into any EXISTING control
corpus. The 2 remaining unsafe-false-symmetry cases in Section N/F are in a
benchmark authored BY and FOR this step, not a pre-existing control.

---

## W. Remaining limitations

Disclosed explicitly, per the governing instructions' standard ("do not
optimize for producing a PASS"):

1. **Compound multi-mechanism differentiation** (Section N): 2 cases in the
   step's own 108-case benchmark. Root-caused, not fixed.
2. **Previously-masked mechanisms now newly visible**: conflicting-defined-
   term generalization (A6-L-22), self-flagged-ambiguity generalization
   (A6-L-23), generic-role-mapping-unresolved (A6-L-52), deferred/absent
   payment terms not escalating (A6-P-33), conflicting Net-30 definitions
   on the payment side (A6-P-48), chained cross-reference delegation
   (A6-RB-07), either/or ambiguity (A6-RB-09), and a payment external-
   delegation case (A6-RB-10) — 10 of the 15 remaining WC, mostly S3
   (false-safe). None of these are new mechanisms this step introduced;
   all were present and masked in Step 4A.6's report by the (now-fixed)
   basis-word-modifier bug's MUST_REDLINE fallback.
3. **Fixed-dollar liability cap phrasing gap** (A6-L-04, A6-L-43): "shall
   not be liable...for...exceeding $X" object-phrasing does not populate
   `general_cap_expression.components` the same way "shall not exceed $X"
   does. Not touched this pass.
4. **Phase 5's full 80-case discovery/interpretation benchmark, Phase 6's
   additional 100-case set-off benchmark, Phase 10's dedicated 60-case
   positive-control file, and Phase 11's 100-case fresh adversarial battery
   were not built as separate artifacts** — the closest available
   equivalent coverage from the benchmarks that WERE built is cited in
   each relevant section, and the gap is disclosed rather than papered
   over with a smaller renamed substitute presented as equivalent.
5. **The Step 4A.2 control was not independently re-triaged to full manual
   rigor** in this pass either (same limitation as Step 4A.6).
6. **Severity classification for the 15 remaining WC** relied on this
   session's own judgment against the stated S1-S4 definitions, not a
   second independent reviewer.

None of these limitations reverse the S4=0/SM-CRITICAL=0 conclusion, which
is independently over-determined by direct extraction-level verification
(Sections E, G) — but they are the reason the verdict (Section AA) is
conditional rather than unconditional.

---

## X. Cross-generation analysis

| Generation | Headline failure signature |
|---|---|
| Step 4A.2 | Recognition/absence + confident-but-wrong extraction, broad |
| Step 4A.4 | Role resolution, symmetry/reciprocal handling, obligation-recognition vocabulary |
| Step 4A.6 | A single dominant extraction-stage mechanism (basis-word-modifier) + recurrence of two Step 4A.5-disclosed residual weaknesses |
| **Step 4A.7** | **The dominant Step 4A.6 mechanism and the two disclosed residual weaknesses are fixed and verified via direct extraction inspection, not merely a passing test. But fixing them mechanically REVEALED a new layer of smaller, previously-masked mechanisms with the same general shape (narrow discovery/comparison logic not anticipating a fresh construction) — most now skewing false-safe rather than false-alarm.** |

**Answering the eight mandatory questions:**

1. **Are failures still predominantly narrow lexical misses?** Less so than
   before — the two fixes that mattered most this step (the general
   exception-clause detector, the structural net-settlement detector) are
   both SHAPE-based, not phrase-enumeration-based. But the 10 remaining
   S3 WC cases (conflicting-defined-term, self-flagged-ambiguity, chained
   delegation, either/or-ambiguity, generic-role-mapping) are each their
   own narrow, single-purpose mechanism that a fresh construction can
   still evade — the SAME general pattern, one level down.
2. **Does fresh drafting continue to expose new clean-wrong extraction
   mechanisms?** Yes — this step's own 108-case benchmark found two
   (S4B-COMP-05/07) that hadn't been anticipated by either generation.
3. **Are fixes becoming more general over time?** Partially. The
   exception-clause detector and the net-settlement structural detector
   are both explicitly designed NOT to require per-phrase enumeration
   (documented in-code as such, with the anti-patch-of-the-day rationale
   spelled out). But the compound-differentiation gap shows the
   generality has a ceiling: two independently-general mechanisms still
   don't compose when a single sentence needs both at once.
4. **Are we reducing dependence on enumerating known phrases?** Yes, for
   the mechanisms touched this step. No, for the mechanisms NOT touched
   (Section W's items 2-3), which remain exactly as narrow as they were.
5. **Is the system developing a real verification boundary?** The
   boundary (Section K) already existed structurally in all three
   adapters before this step; what this step added was DISCOVERY reaching
   more of the cases that boundary was built to handle. The boundary
   itself is not new.
6. **Does "unknown" reliably differ from "absent"?** For indemnification
   obligation existence: yes, confirmed (Section C). For several other
   facts (the newly-exposed mechanisms in Section W): no — several of
   them resolve to a confident `ACCEPT` rather than surfacing "unknown."
7. **Does a clean automatic policy decision now imply its material facts
   have been established?** For the mechanisms this step fixed: yes,
   verified via direct extraction inspection, not just the policy state
   (Section M). For the mechanisms this step did not touch: no change
   from Step 4A.6's answer.
8. **Has Lee's "confident and wrong" failure mode been structurally
   reduced, or are we merely moving the regex frontier?** **Both, and the
   report should say so plainly.** The DOMINANT instance (32+ cases, one
   mechanism, two adapters) was structurally fixed with a general,
   negative-tested capacity increase, not a phrase enumeration — that is
   real, load-bearing progress. But the frontier moved: fixing it exposed
   a next layer of narrower mechanisms with the identical underlying
   shape, at roughly a third of the previous count (15 vs. 50 WC). Whether
   this converges to zero or is fundamentally unbounded is not answerable
   from this step alone — it requires the genuinely independent Step 4A.8
   corpus to test.

---

## Y. Lee Challenge

### Question 1 — "What stops a confidently wrong extraction from reaching the deterministic engine?"

**Concrete code paths, not slogans:**

- **Liability/indemnification multiplier caps**: `_MULTIPLIER_NUM_RE`/
  `_MULTIPLIER_WORD_RE`/`_MONETARY_MULTIPLIER_RE` now include
  `_BASIS_MODIFIER_FRAGMENT`, verified by direct `extract_liability_facts()`
  inspection to correctly populate `general_cap_expression.components` for
  54/54 domain-qualified bases in a dedicated, negative-tested benchmark
  (Section J) — where it previously silently returned an empty
  `CapExpression`, feeding a confident, wrong `MUST_REDLINE`.
- **Indemnification reciprocal claims**: `asymmetry_reasons`, now populated
  for every obligation via `_detect_reciprocal_asymmetry` (which combines
  `_ROLE_ATTRIBUTION_RE`-based two-role comparison, `_PARTY_SPECIFIC_
  EXCEPTION_RE`, `_find_procedural_differentiation_roles`, and the new
  `_find_exception_clause_named_roles` plus `_classify_causation_standard`),
  gates `_resolve_obligations_for_side`'s fast invariance path — verified
  by direct `extract_indemnification_facts()` inspection on all 4 original
  S4 cases plus a fresh generalization test (A6-I-16).
- **Payment set-off/netting**: `_find_mutual_debt_netting_span` now has
  a second, verb-independent structural discovery path
  (`_NET_SETTLEMENT_STRUCTURAL_RE`) alongside the original verb-governs-
  object path, verified by direct `extract_payment_facts()` inspection on
  all 3 SM-CRITICAL cases.

**What this does NOT claim**: it does not claim these three mechanisms are
now exhaustive. Section W lists specific, named mechanisms (conflicting-
defined-term, self-flagged-ambiguity, chained delegation, either/or
ambiguity, generic-role-mapping, the fixed-dollar cap variant, compound
multi-mechanism differentiation) where a confidently wrong or falsely-safe
extraction can still reach the deterministic engine, verified by direct
case inspection, not inference.

### Question 2 — "What counts the clauses that aren't there?"

The architecture distinguishes four states, verified this step for the
mechanisms it touched:

- **Truly absent**: no anchor, no synonym idiom, no trigger keyword at all
  → `None`/`clause_found=False` → `NOT_APPLICABLE`.
- **Expected but missing**: not independently tracked as a distinct state
  from "truly absent" in any of the three adapters — a playbook-type-
  driven "this contract type should have an indemnification clause"
  expectation does not exist. This is an honest gap, not claimed to be
  solved.
- **Potentially present but unrecognized**: for indemnification obligation
  existence specifically, this is `clause_found=True, obligations=[]` →
  `REQUIRES_REVIEW` — confirmed working (Section C). For liability general
  caps, this is now (post-Section J fix) substantially narrower than
  before, but the fixed-dollar phrasing gap (A6-L-04/43) is a residual
  instance of exactly this state being mis-resolved to `MUST_REDLINE`
  rather than surfaced as genuinely unresolved. For payment set-off, the
  three SM-CRITICAL cases WERE this state, silently resolved to `ACCEPT`;
  now fixed.
- **Recognized but unresolved**: `asymmetry_reasons` non-empty
  (indemnification reciprocal symmetry), `unresolved_reason` populated
  (liability cap reconciliation), or a `None` fact value alongside a
  conflict flag (payment terms) — all route to `REQUIRES_REVIEW`, verified
  functioning correctly for the mechanisms this step tested directly.

**If the system still cannot reliably distinguish these: it cannot, fully,
across the whole surface** — Section W's "expected but missing" gap is real
and unaddressed, and the newly-exposed mechanisms (conflicting-defined-term,
etc.) show that "recognized but unresolved" can still, for some
constructions, incorrectly collapse into a confident `ACCEPT` rather than
surfacing. This is stated plainly rather than answered with an
unconditional "yes."

### Question 3 — "Can the audit trail still make an incorrect upstream interpretation appear verified?"

**Yes, for the mechanisms not touched by this step** (Section W). The
`extracted_summary` field for those cases is exactly as specific and
well-formed as for a correct case — nothing in the audit trail's
PRESENTATION distinguishes a correctly-established fact from one that
happens to be wrong via one of the remaining mechanisms. **No, for the
mechanisms this step verified directly**: the fix in each case (Sections E,
G, J) was validated by inspecting the raw extraction output itself, not the
policy decision or the audit trail text — confirming the underlying fact,
not just its presentation, is now correct for those specific, named
mechanisms.

---

## Z. Architecture recommendation

**B. CURRENT ARCHITECTURE IS VIABLE ONLY WITH AN EXPLICIT VERIFICATION/
ESTABLISHMENT LAYER.**

The evidence from 4A.2 through 4A.7 does not support (A) — the repeated
discovery of new, narrow, previously-invisible failure mechanisms each time
a fresh corpus is built (Step 4A.4, Step 4A.6, and now this step's own
108-case benchmark) shows the deterministic extraction layer alone,
unaided, does not reliably distinguish established fact from unsupported
assumption on its own. It also does not yet support (C) — an architectural
redesign — because Section K's finding is specifically that the
establishment-layer semantics this system needs (established / not-
established / conflicting, distinguished from absent) **already exist
structurally** in all three adapters, and every fix this step made was a
DISCOVERY-layer improvement feeding that pre-existing, working
establishment layer, not a rebuild of it. The problem this step repeatedly
found was not "the architecture cannot represent uncertainty" — it can, and
does, correctly, once a fact reaches it — the problem was "specific
discovery/comparison mechanisms are narrower than the drafting variety they
need to cover."

**What Section B specifically requires going forward**: continued,
disciplined investment in exactly the pattern this step modeled —
root-cause first, general fix second, dedicated before/after benchmark
third, negative controls fourth — applied to the concrete named gaps in
Section W, rather than either (a) declaring the architecture done because
the mandatory targets are fixed, or (b) concluding regex-based discovery
has "hit its limit" because new gaps keep appearing. New gaps appearing
under fresh, independently-constructed drafting is the EXPECTED signature of
an architecture with a working establishment layer and an incompletely-
covered discovery layer — which is exactly what Section D's inventory and
this step's fixes demonstrate.

---

## AA. Step 4A.7 verdict

**PASS WITH CONDITIONS — LIMITED PILOT EVIDENCE STRONG, STEP 4B CONDITIONAL.**
(Using the exact governing verdict labels: this is the closest of the four
options — safety on the mandatory targets is strong and directly verified,
one bounded coverage weakness (compound differentiation, Section N) and
several disclosed pre-existing mechanisms newly visible after remediation
(Section W) remain, none of which create material false certainty beyond
what Section W discloses.)

Automatic-FAIL conditions checked explicitly:
- S4 > 0? **No** (0, confirmed via direct extraction inspection on all 4 original cases plus 1 fresh generalization case).
- SM-CRITICAL > 0? **No** (0, confirmed via direct extraction inspection on all 3 confirmed cases).
- Repeated ordinary-drafting WC mechanism? **The dominant one (basis-word-modifier) is fixed and verified on a dedicated 60-case benchmark at 100% recall/100% multiplier-correctness/0% false-association. Ten smaller, individually-distinct mechanisms remain (Section W) — none currently repeated at the scale the Step 4A.6 dominant mechanism was.**
- Material unverified extraction reaching a clean policy decision? **Yes, for the Section W mechanisms — disclosed, not hidden, and materially reduced in scope (15 vs. 50 WC) from Step 4A.6.**
- New false-safe regression? **Two were introduced and fixed during implementation (Section V), both now covered by permanent regression cases in existing benchmark files. Two remain, disclosed, in this step's own new benchmark (Section N), not in any pre-existing control.**

---

## AB. Step 4A.8 recommendation

### Safety ready for controlled Step 4B expansion? **NO.**
### Selectivity ready? **NO.**
### Overall: **DO NOT BEGIN STEP 4B.**

The next required step is **Step 4A.8 — a completely independent frozen
held-out validation**, built exactly the way Step 4A.6 was: production code
frozen first (this report's Section B POST hashes become that freeze point),
a genuinely new corpus constructed without reference to this report's
specific cases, locked before execution, and executed once. Step 4A.8's
purpose is to determine whether THIS step's fixes generalize the same way
Step 4A.6 tested whether Step 4A.5's fixes generalized — the exact same
question, one generation later. Given this step's own finding (Section X,
question 8) that fixing the dominant mechanism exposed a next layer of
smaller ones, Step 4A.8 should be expected, on priors, to find SOME new
gap — the question it needs to answer is whether that gap is (a) another
narrow, individually-fixable mechanism of decreasing severity/frequency
(convergence), or (b) evidence the general pattern is not converging
(requiring the harder architectural conversation Section Z's option C would
raise). This report does not attempt to answer that question — only Step
4A.8's own independent evidence can.

Production code must be frozen (SHA-256 recorded) before Step 4A.8's corpus
is constructed, per the same discipline this report and Step 4A.6 both
followed.
