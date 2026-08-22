# Step 4B Final Validation — Corpus Lock Manifest

## Corpus artifact

`benchmarks/step4b_final_corpus.py`
SHA-256: `84c004f92e8dd8642a674b1a1494cea6b5a0b923e71e1f9851b7a38737721164`

## Case count

**503 documents** (exceeds the ≥450 minimum, meets the "target 500" goal).

## Tier distribution

| Tier | Count | % |
|---|---|---|
| Tier 1 (ordinary) | 229 | 45.5% |
| Tier 2 (complex-but-realistic) | 173 | 34.4% |
| Tier 3 (adversarial/edge) | 101 | 20.1% |

Meets the required distribution (T1 ≥45%, T2 ≈30–35%, T3 ≈20–25%).

## Kind distribution

| Kind | Count |
|---|---|
| fixture (interaction/aggregation, real functions, authored PolicyDecision-shaped payloads) | 200 |
| real_text (real 12-adapter pipeline against real contract text) | 40 |
| governance (DB-backed scenarios) | 26 |
| segment (DB-backed scenarios) | 26 |
| explanation (adversarial explanation-provider fidelity) | 78 |
| injection (fresh prompt-injection attacks) | 78 |
| failure (dependency-failure/degraded-state) | 55 |

## Coverage confirmed at lock time

- All 12 adapters represented (fixture sampling + `real_text`'s per-clause-type phrasing).
- All 7 interaction rules deliberately fired ≥4 times each (28 dedicated documents), plus incidentally fired again in the 45 `compound-multi-interaction` and 55 `high-complexity-replay-pool` documents.
- 100 documents with ≥3 applicable policy areas (well above the ≥100 minimum — nearly the entire fixture/real-text population qualifies).
- 100 documents causing ≥2 simultaneously-relevant interaction rules (`compound-multi-interaction` 45 + `high-complexity-replay-pool` 55), above the ≥60 minimum.
- All 6 document-level states exercised explicitly (`all-six-document-states` family, 12 documents) plus incidentally throughout every other fixture family.
- Governance: 12 named scenarios (active/historical/superseded revision, playbook-changed-after-review, deletion-attempted-with-dependency, multiple playbooks, missing playbook, stale reference, configuration unresolved, draft/needs-review/approved-not-yet-active never governing) across 26 documents.
- Segment: 13 named scenarios (global, business-unit, customer-type, deal-value, multi-dimension, overlapping/tie-break, missing metadata, NaN, invalid numeric, exact lower/upper boundary, just-below-boundary, no match) across 26 documents.
- Replay pool: 100 documents flagged high-complexity (`high-complexity-replay-pool` 55 + `compound-multi-interaction` 45), exceeds the ≥75 minimum.
- Explanation fidelity: 78 documents across all 12 named adversarial families (reversed conclusion, wrong amount/owner/direction/evidence, fabricated evidence, wrong playbook revision, wrong segment, invented interaction, missing uncertainty, false certainty, unsupported recommendation).
- Prompt injection: 78 documents across 14 placement families (operative clause, non-operative recital, heading, table cell, appendix, metadata field, document title, quoted text, cross-referenced section, playbook-like text, fake system/developer message, fake JSON tool output, Unicode-obfuscated).
- Failure modes: 55 documents across 10 named scenarios (provider timeout x2, malformed/empty model output, missing policy/interaction payload, corrupt stored decision, adapter evaluation error, missing governance provenance, invalid segment metadata).

## Independence / overlap analysis

Checked directly against `scripts/step4b_run_phaseL_battery_benchmark.py` (the
largest, most similar prior corpus — 350 documents) and
`benchmarks/step4b_phaseJ_prompt_injection_benchmark.py` (the prior
injection corpus):

- **Company/party names**: 0 overlap (`_PARTIES` here vs. Phase L's `_NEW_PARTY_NAMES` / Phase M's boilerplate — disjoint sets, checked programmatically).
- **Quoted string literals ≥25 chars**: 1 trivial overlap found (`"Real Deterministic Finding {i}"`, a generic label template, not corpus content) vs. Phase L; 0 overlap vs. Phase J's injection payload set.
- Ground truth is computed via `_expected_document_state()`, an independent reimplementation of `document_aggregation.py`'s documented precedence rule, and via direct reading of `interaction_rules.py`'s documented predicate conditions for each of the 7 rules — never by running production and observing its output.

No near-duplicate template families were found; no rewriting was required before lock.

## Ground truth authorship

Every case's `expected` value was written into `benchmarks/step4b_final_corpus.py`
at authoring time, before this corpus was ever executed against production.
`_expected_document_state()` and the per-rule firing conditions embedded in
Group F's recipes are derived from the frozen specification (source code
docstrings), not from observed production behavior.

## Lock declaration

This corpus is now **LOCKED**. No further edits to
`benchmarks/step4b_final_corpus.py` are permitted after the commit
recorded below, except a disclosed, individually-documented ground-truth
correction meeting all six conditions in the governing instructions
(independent reasoning, not production-derived; documented; production
byte-identical; checksum change disclosed; before/after reported).
