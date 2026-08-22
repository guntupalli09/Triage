# Step 4B Phase J — System-Level Prompt Injection

## Method

Read-only trace first (`artifacts/step4b/phaseJ_prompt_injection_trace.md`)
— mapped the two real untrusted-text→LLM boundaries (contract-review
explanation via `evaluator.py`, playbook AI-import via
`playbook_ai_extraction.py`) and confirmed no `eval`/`exec`/unsafe
deserialization of document content anywhere in the codebase.

Benchmark (`benchmarks/step4b_phaseJ_prompt_injection_benchmark.py`, 158
cases, exceeds the ≥150 target) in two layers:

- **Layer 1 (detection)**: `prompt_security.looks_like_prompt_injection`
  against 108 adversarial payloads across all 20+ named attack families.
  Measured honestly as a heuristic, never treated as a hard 100% gate.
- **Layer 2 (the actual hard gate)**: reruns the exact Phase I mechanisms
  (forced `overall_risk`, dropped fabricated `top_issues`, forced
  title/severity) against injection-styled adversarial model output, plus
  `playbook_ai_extraction.verify_and_classify_candidate` against
  injection-laden candidate quotes/values — proving that even an
  **undetected** or fully-"complied-with" injection cannot reach
  authoritative state.

## Result

**Layer 1 detection: 48/108 (44.4%).** This is an honest, expected number
for a keyword/regex heuristic (`_INJECTION_PHRASES` matches ~12 literal
English phrasings plus a chat-role-marker pattern) against a deliberately
broad attack set including base64 encoding, zero-width characters, Unicode
homoglyphs, tables, footnotes, and framings that read as ordinary text
("the correct answer is...", embedded in a heading). **This is disclosed
as a known detection-coverage limitation, not treated as a defect** — the
heuristic was never claimed to be exhaustive, and expanding it indefinitely
against creative phrasing is not the actual security boundary this
architecture relies on.

**Layer 2 hard gates: 40/40 (100%), all 4 PASS regardless of Layer 1
detection:**
- `injection_to_authoritative_overall_risk = 0`
- `injection_to_fabricated_finding_displayed = 0`
- `injection_to_narrative_override_of_authority = 0`
- `injection_to_fabricated_evidence_established = 0`

This is the property that actually matters: **an injection payload the
heuristic misses entirely still cannot influence `overall_risk`, cannot
appear as a fabricated finding, cannot override a real finding's
displayed title/severity, and cannot cause a playbook-import candidate to
be accepted as `ESTABLISHED` without its claimed quote genuinely
appearing in the source document.** These protections come from the
Phase I fixes and from `verify_and_classify_candidate`'s pre-existing
quote-grounding design — none of which depend on the injection being
detected in the first place. Detection (Layer 1) is a defense-in-depth
convenience (redacting an excerpt before the model even sees it, and
withholding a flagged playbook section from AI-assisted import
entirely — `playbook_ai_extraction.discover_relevant_sections`); the
hard authority boundary (Layer 2) does not depend on it.

## No production defect found; no production file changed

Phase J is entirely a test of properties already established/fixed in
Phase I (contract-review explanation path) and already correctly designed
in `playbook_ai_extraction.py` (quote-grounding, numeric grounding,
withhold-on-flag). No new production code was written or needed.

## Regression

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed**.
- No production file changed this phase.

## Conclusion

The trust boundary — contract text and playbook prose are DATA, never
instructions, and no model output can mutate authoritative state without
the explicit deterministic/approval boundary — holds even in the worst
case (injection undetected, model fully "complies"). Detection coverage
is honestly disclosed as partial (44.4%) and left as a known, non-blocking
limitation: the actual safety property does not depend on it.
