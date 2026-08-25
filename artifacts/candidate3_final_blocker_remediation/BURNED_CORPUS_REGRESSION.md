PHASE 8 — BURNED CORPUS REGRESSION (240 cases, real OpenAI, REGRESSION EVIDENCE ONLY)

Corpus, expected outcomes, hash, and labels were NOT modified. Replayed via the existing,
unaltered `artifacts/candidate3_final_gap_closure/burned_corpus_replay/replay_final_gap_closure.py`.

RESULT: 189/240 passed.

## Hard gates (all 8, required 0/240)

| Gate | Count |
|---|---|
| FALSE_SAFE | 0 |
| UNVERIFIED_FEEDING_CLEAN | 0 |
| FALSE_OPERATIVE_TO_CLEAN | 0 |
| FALSE_ABSENCE | 0 |
| MATERIAL_CONTEXT_SILENTLY_LOST | 0 |
| ARBITRARILY_SELECTED_COMPETING_READING | 0 |
| UNRESOLVED_CROSS_REFERENCE_TO_CLEAN | 0 |
| UNRESOLVED_DEFINITION_TO_CLEAN | 0 |

**8/8 hard gates: ZERO.**

Non-hard-gate residuals (AI recall limitations, not safety violations, per this replay
script's own classification): 44 `MISSED_OPERATIVE_FACT`, 7 `FALSE_OPERATIVE_NON_CLEAN`.

## Case-level comparison against the immediately-prior successful burned replay
(`artifacts/candidate3_final_gap_closure/burned_corpus_replay/raw_results.jsonl` as it stood
after the Candidate 3 zero-silent-loss follow-up mission, commit `520fbd0`)

IMPROVED: 0 cases
UNCHANGED SAFE: 189/240 (identical pass count, identical failure-class counts and identical
case-by-case pass/fail split — same 44 `MISSED_OPERATIVE_FACT` and 7 `FALSE_OPERATIVE_NON_CLEAN`)
REGRESSED: 0 cases
NEW FAILURE CLASS: none — no case newly produced any of the 8 hard-gate failure classes, or
any failure class not already present in the pre-mission baseline.

No forbidden new failure was found. No corpus expectation was changed to compensate for
anything.
