# Step 4B Phase G — Segment Selection

## Method

Read-only trace first (`artifacts/step4b/phaseG_segment_trace.md`) —
confirmed the 4 implemented segmentation dimensions, the specificity-based
selection algorithm, and that `contract_side` is not a segmentation
dimension at all (a separate adapter-evaluation-time concern, out of
scope). Benchmark (`scripts/step4b_run_phaseG_segment_benchmark.py`) — 191
cases (exceeds the ≥150 target, plus ≥50 combined governance×segment
cases), running the REAL `resolve_segment_position`/
`snapshot_active_positions` against real `PolicyPosition` rows in a real
SQLite database.

## PRE result and a genuine defect found

First run: **180/191 (94.2%)**. Two distinct causes:

### 1. Genuine defect: NaN silently bypasses a numeric segment bound

`_segment_matches_context`'s deal-value bound checks
(`policy_enforcement.py:266-283`) used `deal_value < min` / `deal_value >
max` to reject a non-matching context. Under IEEE754, `nan < x` and
`nan > x` are **both** `False` — so a `deal_value=nan` context silently
**satisfied** a `>= min` (and would equally satisfy a `<= max`) bound it
should never satisfy, causing the wrong (non-GLOBAL, segment-restricted)
`PolicyPosition` to be selected as governing instead of falling back to
GLOBAL. This is exactly the failure mode Phase G's own invariant warns
against — a malformed/corrupt metadata value must fail closed, never
silently select the wrong governing configuration. A non-numeric string
value (e.g. `"not-a-number"`) already failed loudly (`TypeError`, caught
and treated as an acceptable outcome by the benchmark); NaN was the one
malformed numeric value that failed *silently and wrongly* instead.

**Fix** (`policy_enforcement.py`, `_segment_matches_context`): added an
explicit `deal_value_is_nan` check (`isinstance(deal_value, float) and
deal_value != deal_value` — the standard NaN self-inequality test) and
folded it into both bound checks, so NaN now fails closed exactly like
`None` does. Minimal, general (not tied to one case), touches only the
one function.

### 2. Benchmark-authoring correction (disclosed, GTD-style)

`overlapping-ranges-broad-and-narrow` predeclared that a numerically
narrower deal-value range should win over a numerically broader one when
both match. Verified against the actual `_segment_specificity` function
before "fixing" anything: specificity counts the number of **constrained
fields**, not range width — a broad range with both min and max set has
the identical specificity (2) to a narrow range with both set. This is
therefore a genuine tie, correctly resolved by the documented lowest-id
tie-break (the position created first wins), not a "narrower wins" rule.
Corrected the benchmark's expectation to match verified, documented
behavior, and disclosed the underlying product question explicitly as a
**limitation, not a bug**: range width does not currently factor into
specificity ranking. Whether it should is a product decision outside this
audit's authority to make unilaterally — flagged for the final report,
not silently implemented.

## POST — 191/191 (100%), all 8 hard gates PASS

`wrong_segment`, `arbitrary_segment`, `ambiguous_segment_clean`,
`missing_metadata_clean`, `wrong_revision_via_segment`,
`wrong_policy_via_segment`, `false_clean_from_segment`,
`historical_segment_mutation` — all 0.

Families covered: single exact match; fallback to GLOBAL; no match with
no fallback (correctly skipped, not guessed); inclusive lower/upper
deal-value boundaries; overlapping ranges; missing metadata (fails closed
to GLOBAL); malformed metadata (`None`, non-numeric string, **NaN**,
negative, numeric-string) — all now fail closed or raise loudly, never
silently wrong; wrong business unit/customer type; conflicting
(partial-match) metadata; archived/disabled segments never governing;
segment revision mismatch (old archived, new active, same segment tuple);
two equally-specific segments (deterministic tie-break, disclosed); broad
vs. narrow (differing specificity) segments; the same contract metadata
evaluated correctly under two different playbook revisions; and 50
combined governance×segment cases (old revision+old segment, new
revision+changed segment, active revision with multiple segment
candidates, inactive-but-matching revision never governing, active
revision with no matching segment correctly skipped).

## Regression

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed**.
- Phase F's 174-case governance benchmark re-run after this fix (shares
  `policy_enforcement.py`): unchanged, **174/174**.
- No adapter, interaction rule, or `POLICY_ENFORCEMENT_MODE` default
  touched. Only `policy_enforcement.py`'s `_segment_matches_context`
  changed.

## Conclusion

The segment-selection authority invariant — deterministic match or
explicit fallback/skip, never a guess — holds after fixing the one
silent-wrong-match defect (NaN). The disclosed range-width-vs-specificity
limitation is a product question, not an authority defect, and is left
for the final report rather than acted on unilaterally.
