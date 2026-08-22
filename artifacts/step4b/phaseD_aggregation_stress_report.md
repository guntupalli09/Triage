# Step 4B Phase D — Final Aggregation Stress

## Corpus

`benchmarks/step4b_phaseD_aggregation_stress_benchmark.py` — 158
documents (exceeds the ≥150 minimum), fresh (no reuse of Phase A's 200
documents), covering all 21 mandatory families from "1 violation among
max-clean" through "multiple non-participating interaction rules." Every
document is run through the real `interaction_engine_core.evaluate()` +
real `document_aggregation.aggregate_document_state()`, never
reimplemented. Ground truth predeclared by hand per family.

Note on "20 clean findings": the actual adapter catalog has 12 clause
types, so the maximum clean-finding count this system can produce is 11
(12 minus the 1 signal) — used explicitly and disclosed here rather than
fabricating a 20th unsupported policy to hit a literal number.

## Result

**158/158 (100%) on the first, unmodified run.** All seven hard gates PASS:

- `false_clean_document = 0`
- `wrong_document_state = 0`
- `wrong_attention_state = 0`
- `lost_finding = 0`
- `lost_interaction = 0`
- `uncertainty_laundering = 0`
- `incorrect_insufficient_facts_escalation = 0`

No production defect found; no production file was modified in this
phase. This is a genuine, informative negative result, not merely an
absence of testing: it directly stress-tests the exact mechanism Phase A
found and fixed (`interaction-participant-genuinely-absent`,
`multiple-non-participating-interaction-rules` — 10 documents combined)
and confirms that fix generalizes correctly under new, independently-
constructed documents, alongside 19 other imbalanced-mixture families
(single signal buried among 11 clean findings, multiple simultaneous
signals, precedence-crossing combinations, and clean-legacy/high-legacy
mismatches) that were never previously exercised together at this scale.

## Regression

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed**.
- No production file changed this phase, so the other benchmark suites
  (Phase A/B/C, 104/213/54/18-case suites, Step 4A.11 corpora) are
  unaffected by construction and were not re-run for this phase alone.

## Conclusion

Phase D found the aggregation model, as fixed in Phase A, robust across a
158-document imbalanced-mixture stress corpus with zero wrong-authority
defects and zero selectivity defects. No production change required.
