# Selectivity / Usefulness Impact (Candidate 3 final gap-closure) — FINAL

Measured directly from the 240-case burned corpus, real OpenAI provider, before this mission's changes (start of mission, commit `0ee86e2`) and after (final committed state). No arbitrary automation-rate threshold applied, per Section 19.

## Decision-state distribution, before vs. after

| State | Before (n=240) | After (n=240) | Change |
|---|---|---|---|
| ACCEPT | 56 | 33 | −23 |
| ACCEPT_WITH_NOTE | 0 | 3 | +3 |
| NEGOTIATE | 19 | 19 | 0 |
| MUST_REDLINE | 14 | 14 | 0 |
| PROHIBITED | 1 | 1 | 0 |
| ESCALATE | 6 | 7 | +1 |
| REQUIRES_REVIEW | 95 | 104 | +9 |
| NOT_APPLICABLE | 49 | 59 | +10 |

## Bucket-level summary

| Bucket | Before | After | Change |
|---|---|---|---|
| CLEAN (ACCEPT + ACCEPT_WITH_NOTE) | 56 (23.3%) | 36 (15.0%) | **−20 (−8.3 points)** |
| NOT_CLEAN (NEGOTIATE/MUST_REDLINE/PROHIBITED) | 34 (14.2%) | 34 (14.2%) | 0 |
| REQUIRES_REVIEW | 95 (39.6%) | 104 (43.3%) | +9 |
| NOT_APPLICABLE | 49 (20.4%) | 59 (24.6%) | +10 |
| OTHER (ESCALATE) | 6 (2.5%) | 7 (2.9%) | +1 |

**Review rate (REQUIRES_REVIEW + ESCALATE) rose from 42.1% to 46.2% (+4.1 points). Clean-decision rate fell from 23.3% to 15.0% (−8.3 points).** This is reported exactly as measured, in both directions — the review-rate increase is real and larger than the clean-decision decrease alone would suggest, because 10 additional cases also moved from `ACCEPT` to `NOT_APPLICABLE` (a confirmed-absent, not-reviewed-but-not-falsely-accepted outcome) rather than to `REQUIRES_REVIEW`.

## False-safe rate

**FALSE_SAFE fell from 8/240 (3.3%) to 0/240 (0%).** This is the headline number this mission was chartered to drive to zero, and it did. Every point of review-rate increase and clean-decision-rate decrease reported above should be read against this: 20 of the 20 lost clean decisions are net safety improvements (the FALSE_SAFE/FALSE_OPERATIVE_TO_CLEAN/UNRESOLVED_CROSS_REFERENCE_TO_CLEAN/UNRESOLVED_DEFINITION_TO_CLEAN cases that moved off a wrongly-clean decision), not an arbitrary tightening.

## Not a "send everything to review" outcome

Despite the review-rate increase, 15.0% of the corpus still resolves cleanly and 14.2% resolves to a clear non-clean policy position (NEGOTIATE/MUST_REDLINE/PROHIBITED) without human review — the system is not degenerating toward reviewing 100% of contracts. The corpus is deliberately adversarial (Lee-test families, contradiction/competing-reading/negation/hypothetical cases by design), so these percentages should not be read as representative of a real, non-adversarial contract population — see the burned corpus's own design notes in `artifacts/candidate3_real_ai_adversarial/PRE_RUN_MANIFEST.md`.

## Honest caveat

10 `MATERIAL_CONTEXT_SILENTLY_LOST` and 7 `ARBITRARILY_SELECTED_COMPETING_READING` cases remain in the "after" numbers above — i.e., the clean-decision-rate decrease already reported here does NOT yet include the full cost of closing those two remaining hard gates. If they were fixed the same way `limitation_of_liability`'s 3 cases were (elevating to `ACCEPT_WITH_NOTE` where appropriate, or to `REQUIRES_REVIEW`/`NEGOTIATE` where a genuine contradiction is found), the clean-decision rate would very likely fall further. This is not estimated or extrapolated here — only measured, current-state numbers are reported.
