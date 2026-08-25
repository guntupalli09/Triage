CANDIDATE 5 — BURNED 660-CASE REGRESSION AND REPEATABILITY

Two rounds were run against the real OpenAI provider, both integrity-
verified (660/660 unique case_ids, exact match to the corpus, zero
malformed lines):

- **Round 1** (`burned_regression_raw_results_round1.jsonl`): after
  closing the UNRESOLVED_DEFINITION_TO_CLEAN root cause
  (`self_referential_definition_unresolved`, wired into insurance/
  ip_ownership/warranties).
- **Round 2** (`burned_regression_raw_results.jsonl`, the final/reported
  round): after ALSO adding the ip_ownership title-passage deterministic
  anchor and broadening 6 adapters' `_SCHEDULE_CROSSREF_RE` patterns to
  allow a qualifying word before Schedule/Exhibit/SOW.

## Hard safety gates — final (round 2)

| Gate | Candidate 4 | Round 1 | Round 2 (final) | Required |
|---|---|---|---|---|
| FALSE_SAFE | 0 | 0 | **0** | 0 |
| FALSE_OPERATIVE_TO_CLEAN | 0 | 0 | **0** | 0 |
| UNVERIFIED_FEEDING_CLEAN | 6 | 0 | **0** | 0 |
| FALSE_ABSENCE | 11 | 7 | **3** | 0 |
| MATERIAL_CONTEXT_SILENTLY_LOST | 4 | 2 | **2** | 0 |
| ARBITRARILY_SELECTED_COMPETING_READING | 0 | 0 | **0** | 0 |
| UNRESOLVED_CROSS_REFERENCE_TO_CLEAN | 0 | 0 | **0** | 0 |
| UNRESOLVED_DEFINITION_TO_CLEAN | 17 | 0 | **0** | 0 |

**6 of 8 hard gates are now zero (up from 2 of 8 at the start of this
mission). 2 remain non-zero: `FALSE_ABSENCE=3`, `MATERIAL_CONTEXT_
SILENTLY_LOST=2`.**

## Other customer-facing accuracy metrics (round 2, per this mission's
explicit request not to hide behind hard-gate numbers alone)

- TOTAL CORRECT: 521/660 (78.9%)
- CORRECT_CLEAN: 37
- CORRECT_NON_CLEAN: 484
- SAFE REVIEW/ESCALATION (conservative, non-clean when a cleaner answer
  might have been possible — never dangerous, just cautious):
  `FALSE_ESCALATION` = 86 of 660 (13.0%)
- FALSE POSITIVE (an authoritative violation without grounded support):
  0 — confirmed by `FALSE_OPERATIVE_TO_CLEAN=0` and manual inspection of
  every non-`REQUIRES_REVIEW` escalating decision's `unresolved_facts`/
  `notes`, each traceable to a specific, grounded contract span
- FALSE NEGATIVE (a genuinely operative, material fact missed entirely,
  landing at a clean state): the 3 `FALSE_ABSENCE` cases above, plus a
  fraction of the 83 `MISSED_OPERATIVE_FACT` failure-class occurrences
  that landed in a NON-clean bucket already (i.e., correctly escalated
  for the WRONG underlying reason, or correctly not-clean but the
  specific fact wasn't the one identified) — these are lower severity
  than the 3 true `FALSE_ABSENCE` cases because the customer still gets
  a "needs review" signal, just not the most precise one
- UNSAFE CLEAN: 0 (`FALSE_SAFE=0` confirmed both rounds)

## Root cause of the 2 remaining non-zero gates

Both are now concentrated in `ip_ownership` (2 `FALSE_ABSENCE`),
`warranties` (1 `FALSE_ABSENCE`), and `sla` (2 `MATERIAL_CONTEXT_
SILENTLY_LOST`) — all texts that use ownership/warranty/SLA vocabulary
this mission did NOT add a deterministic anchor for (`"owns all
deliverables"` without the word "work product"; `"right, title, and
interest"` boilerplate; an SLA carve-out clause). Each was individually
confirmed (deterministic-only, no AI) to have zero anchor match, meaning
the outcome for these SPECIFIC phrasings still depends entirely on
AI-candidate admission. Two of these (`ip_ownership`'s "right, title,
and interest" boilerplate) were identified as fixable via one more
narrow, low-risk anchor addition, but this mission deliberately stopped
short of adding it: per this mission's own Section 2 instruction ("Fix
THIS GENERAL FAILURE CLASS. Do not patch individual corpus sentences"),
a single-case-motivated regex addition without broader corpus evidence
of the SAME pattern recurring elsewhere is exactly the kind of narrow
patch this mission is designed to avoid, and adding a broader anchor
(e.g. bare "deliverables") was assessed and REJECTED as carrying a real
risk of over-triggering `ip_ownership` on unrelated SLA/payment-terms/
warranties sections that happen to mention "deliverables" without any
ownership content — a P2/P3 precision risk this mission's priority order
(Section 21) explicitly ranks below stopping to reassess rather than
rushing a fix under time pressure. This is disclosed as a genuine,
named, un-fixed gap, not hidden inside an aggregate number.

## Repeatability (48 cases × 5 real-provider executions = 240 runs, both rounds)

| | Round 1 | Round 2 (final) |
|---|---|---|
| UNSAFE AUTHORITATIVE VARIANCE | 2 | **3** |

Round 2's 3 unsafe transitions: `iv-ip_ownership-0218` (a genuinely
ambiguous "descriptive vs. needs-review" boundary case — "It is common
... though ownership has not yet been addressed for this particular
engagement" — flipped `NOT_APPLICABLE`/`REQUIRES_REVIEW` 4:1 across 5
runs) and `iv-termination-0433`/`iv-termination-0436` (an adapter this
mission did NOT modify at all — confirmed via `git diff` — so this
variance is necessarily pre-existing, not introduced this mission).

This mission's own Section 5 explicitly forbids solving this via
majority voting, retries, or temperature tricks. No such workaround was
attempted. The honest result is that real OpenAI candidate admission
remains genuinely non-deterministic for a small number of boundary-line
phrasings, and when NO deterministic anchor exists for that phrasing
(confirmed case-by-case, not assumed), the authoritative outcome can
still vary run-to-run. `UNSAFE AUTHORITATIVE VARIANCE = 0` is NOT met.

HARMLESS INTERMEDIATE VARIANCE: not separately tallied as a distinct
metric this run (all 45 non-unsafe cases were FULLY stable across all 5
runs — identical state every time — so there was no harmless-but-varying
explanatory text to separately categorize in this particular sample).
