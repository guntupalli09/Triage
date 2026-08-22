# Step 4B Phase L — Fresh ≥300-Document Development Adversarial Battery

## Corpus

**350 documents** (exceeds the ≥300 minimum, meets the "prefer 350+"
target), in three groups, run via `scripts/step4b_run_phaseL_battery_benchmark.py`:

- **Group 1 — end-to-end real text (30 documents):** real `contract_text`
  through the real orchestration entrypoint
  `policy_enforcement.apply_policies_for_review` (cutover mode), real
  ACTIVE `PolicyPosition` rows (strict liability + indemnification
  configs), real 12-adapter dispatch, real interaction engine, real
  aggregation. Includes 18 Tier-3 documents using deliberately
  uncapped-liability language designed to trigger a real `PROHIBITED`
  decision from the real adapter.
- **Group 2 — fixture-based combination coverage (280 documents):**
  `PolicyDecision` objects constructed directly (same accepted
  methodology as Phases A/D/E/H), run through the REAL
  `interaction_engine_core.evaluate` and REAL
  `document_aggregation.aggregate_document_state`. Deterministically
  generated (fixed seed `20260822`, reproducible) combinations across all
  12 clause types' full state vocabulary, with sparse clause-type
  coverage (4–12 of 12 per document) to exercise "absence means skipped."
- **Group 3 — prompt-injection-in-full-pipeline (40 documents):** real
  `main.build_enhanced_issues` + real
  `evaluator.LLMEvaluator._verify_output_maps_to_findings`, against 8
  freshly-authored injection-styled payloads (system-override framing,
  fake JSON blocks, fake compliance-officer certification, zero-width
  characters, appendix/footnote framing) distinct from Phase J's set.

**Tiering:** Tier 1 (ordinary) 153/350 = 43.7%, Tier 2 (complex-but-realistic)
130/350 = 37.1%, Tier 3 (adversarial/edge) 67/350 = 19.1% — Tier 3 does
not dominate.

## Independence

All document text and clause phrasing (`_NEW_PARTY_NAMES`,
`_NEW_CLAUSE_PHRASINGS`, `_G1_ADVERSARIAL_LIABILITY`,
`_FRESH_INJECTION_PAYLOADS`) was freshly authored for this phase — new
company names, new sentence structures, new injection framings. Checked
directly against Phase H's `_DOCUMENTS` corpus (the most similar prior
corpus, real end-to-end text): **0 exact-string overlap**, no shared
vocabulary beyond generic sentence-starting words ("The", "Each",
"Either", "Neither", "This"). Group 2's combination-generation code
reuses proven test-harness helper functions from Phase H (`_active_position`,
config dicts) — that is harness code, not corpus content, and reuse there
is a deliberate methodology continuity, not an independence violation.

## Coverage

All 12 adapters (Group 1 direct via strict-config real text; Group 2 via
the full clause-type vocabulary in fixture combinations), all 7
interaction rules (Group 2's `ixr.LAUNCH_CATALOG` run in full each time),
sparse/partial clause coverage (Group 2), multi-policy and 3+-policy
compound documents (Group 2's 4–12 covered clause types per document),
prompt injection (Group 3), full end-to-end determinism (all groups
replay ≥2x; a subset of high-complexity Group 2 documents replay 5x).

## Metrics / Hard Blockers — all 0

- **Crashes / unhandled exceptions: 0** across all 350 documents.
- **False-clean with material exposure: 0** — Group 2's `materially_clean_ok`
  check independently verifies that any document containing a
  `PROHIBITED`/`MUST_REDLINE`/`ESCALATE`/`NEGOTIATE` policy state or an
  `ESCALATE` interaction never resolves to `CLEAN`/`CLEAN_LEGACY_ATTENTION`.
- **Authoritative replay contradiction: 0** — every document's repeated
  runs (2x, 5x for high-complexity) produced byte-identical authoritative
  structure (policy decisions, interaction decisions, document state,
  stripped of non-authoritative prose/ids).
- **Prompt injection → authoritative state: 0** — across all 40 Group 3
  documents, the displayed title/severity always matched the real
  deterministic finding (never the injected payload's claim), and the
  fabricated "unrelated issue" top_issue was dropped in every case
  (`fabricated_dropped=True` for all 40).
- **One real `PROHIBITED` violation genuinely produced by real adapters
  in Group 1's Tier-3 documents** (uncapped-liability language) —
  confirms the corpus isn't purely accepting/inert; the deterministic
  engine really does fire on adversarial real text, not just on fixtures.

**Result: 350/350 documents passed (100%).** No genuine production defect
found this phase — Phase L is a volume/coverage/independence battery on
top of already-fixed (Phases A–K) production code, not a new
investigation surface.

## Regression

No production file was modified in this phase (corpus/runner script
only). Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed**
(unchanged).

## Conclusion

The deterministic pipeline holds across a genuinely fresh, independently
authored 350-document battery spanning ordinary, complex, and adversarial
tiers, with zero crashes, zero false-clean-with-material-exposure, zero
replay contradictions, and zero prompt-injection-to-authority breaches.
