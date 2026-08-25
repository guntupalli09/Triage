PHASE 4 — HARD SAFETY GATES (one-shot execution, 660 cases, real OpenAI, no tuning after results)

Preserved raw results: `artifacts/candidate3_independent_validation/raw_results.jsonl` (committed
verbatim, not edited after generation).

## Required gates

| Gate | Count | Required |
|---|---|---|
| FALSE_SAFE | **0** | 0 |
| UNVERIFIED_FEEDING_CLEAN | **33** | 0 |
| FALSE_ABSENCE | **9** | 0 |
| FALSE_OPERATIVE_TO_CLEAN | **0** | 0 |
| MATERIAL_CONTEXT_SILENTLY_LOST | **3** | 0 |
| ARBITRARILY_SELECTED_COMPETING_READING | **6** | 0 |
| UNRESOLVED_CROSS_REFERENCE_TO_CLEAN | **9** | 0 |
| UNRESOLVED_DEFINITION_TO_CLEAN | **17** | 0 |

**5 of 8 hard gates are non-zero. This independent validation run FAILS the hard safety gate
requirement.** A 74.2% aggregate pass rate (490/660) does not offset this — per the mission's
own instruction, "a 99% accuracy result with one FALSE_SAFE is a FAIL," and this run has
multiple hard-gate categories with real counts.

## Gate definitions used (documented for auditability)

`FALSE_SAFE`, `FALSE_OPERATIVE_TO_CLEAN`, `MATERIAL_CONTEXT_SILENTLY_LOST`,
`ARBITRARILY_SELECTED_COMPETING_READING`, `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN`,
`UNRESOLVED_DEFINITION_TO_CLEAN` are computed by the SAME, already-validated `_grade` function
reused (imported, unmodified) from `replay_final_gap_closure.py` — the identical grading rubric
applied to three prior burned corpora in this repository's history.

`UNVERIFIED_FEEDING_CLEAN` and `FALSE_ABSENCE` are not named in `_grade` and were newly
operationalized for this mission (see `analyze_results.py`):
- `FALSE_ABSENCE`: the case's expected label is NOT `MISSING_CLAUSE` (i.e., the clause
  genuinely exists) but the decision bucket is `NOT_APPLICABLE` (the system reports no such
  clause was found at all).
- `UNVERIFIED_FEEDING_CLEAN`: the case's expected label is NOT `NO_NOT_OPERATIVE` and NOT
  `MISSING_CLAUSE` (i.e., something genuinely operative is present) AND `established_signal`
  is `False` (nothing was deterministically or AI-verified) AND the decision bucket is `CLEAN`
  (`ACCEPT`/`ACCEPT_WITH_NOTE`). Cases where the clause is genuinely NOT operative
  (`NO_NOT_OPERATIVE` — negated/descriptive language) are correctly excluded: for those,
  `established=False` + `CLEAN` is the CORRECT, safe outcome (a confirmed negation reaching a
  clean decision is not "unverified feeding clean," it is "confirmed absent feeding clean").
  An earlier version of this analysis script incorrectly included `NO_NOT_OPERATIVE` cases and
  reported 51; this was caught and corrected before this report was finalized (verified against
  `iv-insurance-0273`, a correctly-negated "no obligation to obtain insurance" clause that was
  being wrongly counted as a violation) — see `analyze_results.py`'s git history in this same
  commit for the correction.

## Root-cause investigation (representative sample, not exhaustive re-debugging of all 77 flagged cases)

Two DISTINCT, both-real contributing factors were identified by direct investigation:

**1. A genuine, real AI-discovery recall limitation, concentrated in `insurance`, `ip_ownership`,
`warranties`, `sla`, and `data_security`.** For several cases, `discover_candidate_spans`'s real
OpenAI call returned ZERO candidates for text a competent human reviewer would recognize as
operative (e.g. `iv-insurance-0274`'s trace shows `"candidates_found": []` for "Provider shall
maintain liability coverage of at least $1 million, provided that such coverage shall only be
required for the duration of any on-site work..."). This is the same class of limitation this
repository's own prior burned-corpus reports have repeatedly classified as "AI recall
limitation, not a safety violation" (44 `MISSED_OPERATIVE_FACT` cases in the most recent burned
240-case replay, explicitly non-hard-gate) — **but this validation mission's own gate design
(`UNVERIFIED_FEEDING_CLEAN`) deliberately treats the SAME underlying event (nothing established,
yet reaching a clean decision) as a hard gate rather than a lenient non-gate**, per this
mission's explicit instruction to calculate it. This is not a contradiction with the prior
corpora's methodology — it is this mission's own, stricter bar, applied honestly.

**2. A genuine, real architectural asymmetry across adapters.** `warranties` and `sla` both have
an explicit `found_anything`-style gate: when an anchor fires but NOTHING at all (deterministic
or AI) is found, they force `NOT_APPLICABLE` rather than falling through to `ACCEPT`. `insurance`
has a narrower version of this same gate (`if not deterministic_value_found and admitted_semantic:
PRESENT_BUT_UNRESOLVED`) that only engages when an AI candidate WAS admitted — if AI discovery
itself returns nothing (as in the recall-miss cases above), `insurance` falls through to a bare
`ACCEPT` ("no policy gaps found") rather than an escalated state, because the default test
policy used in this replay does not itself require any specific coverage. Confirmed directly:
```
$ python3 -c "import insurance_policy_engine as ipe; print(ipe.extract_insurance_facts(
    '13. Insurance. Provider shall maintain liability coverage of at least \$1 million.'
  ).absence_state)"
CONFIRMED_ABSENT
```
This is a genuine, reproducible product characteristic, independent of any corpus-authoring
choice.

**3. A contributing corpus-authoring inconsistency, disclosed per the mission's explicit
requirement to document any genuinely demonstrable corpus-construction defect independently
(NOT used to edit the frozen corpus or dismiss the finding).** Five of the nine `insurance`
adversarial-family templates (conditional/exception/cross_reference/definition/ambiguous) used
generic "liability coverage" phrasing rather than a named coverage type
("commercial general liability insurance," used consistently only in the `operative` template).
Confirmed directly: the deterministic `cgl` coverage-type classifier recognizes "commercial
general liability insurance" but not generic "liability coverage" — `established=True` for the
former, `established=False` for the latter on otherwise-identical policy text. This inconsistency
made several `insurance` cases genuinely harder to recognize than intended, contributing to (but
not fully explaining, since the AI channel independently also missed the same text) `insurance`'s
disproportionate share of `UNVERIFIED_FEEDING_CLEAN`/`UNRESOLVED_CROSS_REFERENCE_TO_CLEAN`/
`UNRESOLVED_DEFINITION_TO_CLEAN`/`ARBITRARILY_SELECTED_COMPETING_READING` (12-13 of each gate's
count is `insurance`-attributable). A small number of `ip_ownership`'s `FALSE_ABSENCE` cases
(the `conditional` family: "Title to the deliverables shall transfer to Recipient upon...")
similarly used a less-common ownership-transfer construction, deliberately chosen to avoid any
resemblance to the deferred `ip_ownership-080` defect's exact "shall be owned exclusively by X
upon Y" phrasing — that deliberate avoidance produced phrasing the deterministic and AI channels
both failed to recognize.

**This finding is reported, not used to alter the verdict.** Per the mission's explicit
instruction, no case was edited, no expected label was changed, and no case was removed from the
frozen corpus as a result of this investigation. The raw counts above are unmodified. Even
setting aside every case attributable to the `insurance`-template inconsistency entirely, real,
non-`insurance` instances remain in every one of the 5 non-zero gates (e.g. `iv-ip_ownership-0220`,
`iv-warranties-0510`, `iv-sla-0563`, `iv-assignment-0617`, `iv-termination-0651`,
`iv-data_security-0375`), so this validation run's FAIL verdict does not depend on the
`insurance`-specific finding alone.

## Other required metrics

- FALSE_ESCALATION (expected `NO_NOT_OPERATIVE`, decision not absent/clean): 80/660
- CONSERVATIVE_REVIEW_RATE: 403/660 = 61.1%
- CORRECT_CLEAN: 45
- CORRECT_NON_CLEAN: 445
- Overall pass rate: 490/660 = 74.2%
- Non-hard-gate diagnostics observed: `MISSED_OPERATIVE_FACT` (81), `UNEXPECTED_NON_ABSENT_BUCKET`
  (36), `FALSE_OPERATIVE_NON_CLEAN` (12), `FALSE_OPERATIVE_ON_MISSING_CLAUSE` (6) — all
  pre-existing, non-hard-gate diagnostic categories per the established grading rubric.
