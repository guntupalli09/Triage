# Step 4B Phase I — Explanation Fidelity

## Method

Read-only trace first (`artifacts/step4b/phaseI_explanation_trace.md`),
classifying every explanation path as AUTHORITATIVE, DERIVED-DETERMINISTIC,
or NON-AUTHORITATIVE LLM NARRATION. Benchmark
(`benchmarks/step4b_phaseI_explanation_fidelity_benchmark.py`, 150 cases,
meets the ≥150 target) calls the real production functions directly:
`evaluator.LLMEvaluator._verify_output_maps_to_findings`, `_validate_result`,
`evaluate()`'s `overall_risk`-forcing line, and `main.build_enhanced_issues`.

## PRE and defects found (three, all in the explanation-merge layer)

1. **Fabricated top_issues sailed through unfiltered.**
   `_verify_output_maps_to_findings` logged a warning for a non-mapping
   LLM issue but unconditionally `return True`d, and its return value was
   discarded by the caller anyway — a hallucinated finding with no
   deterministic basis would be displayed to the user as if real.
   Reproduced directly.
2. **Empty `rule_name`/title silently matched everything.** Found while
   building the benchmark: `_normalize_title("")` returns `""`, and
   Python's `"" in x` is always `True` — a finding lacking `rule_name`
   contributed an empty string that trivially "matched" every LLM issue
   title, defeating verification independent of defect #1.
3. **Displayed finding title could be entirely LLM-authored.**
   `build_enhanced_issues`'s `enhanced = llm_issue.copy()` made the LLM's
   own (possibly reframed/contradicted) title the displayed headline,
   even though the underlying match check only requires loose substring
   overlap — severity was already protected but title was not.

## Fixes

- `evaluator.py`, `_verify_output_maps_to_findings`: now filters
  `top_issues` in place (drops non-mapping/fabricated entries) instead of
  only logging; excludes empty normalized strings from all three matching
  sets.
- `main.py`, `build_enhanced_issues`: `enhanced["title"]` is now always
  forced to the deterministic finding's own title, exactly like
  `severity` already was. The LLM's own narrative (`why_it_matters`) is
  left untouched.

All three fixes are general (not per-case), confined to the explanation
layer, and do not touch any adapter, interaction rule, or aggregation
function.

## POST — 150/150 (100%), all 4 hard gates PASS

- `fabricated_material_fact_displayed = 0`
- `authority_explanation_contradiction = 0`
- `wrong_overall_risk_displayed = 0`
- `malformed_output_not_rejected = 0`

Families covered: fabricated-finding-invented (30 adversarial fabricated
titles across two batches), mixed real+fabricated, zero-findings-all-
dropped, multiple-real-findings-all-survive, adversarial title attacks
(reversed conclusion, wrong amount, wrong party, wrong clause, wrong
direction, invented condition, invented interaction, wrong governance
provenance, wrong segment claim, unsupported recommendation), evidence-
field protection, policy_decision/interaction_decision-shaped finding
protection, multi-policy-document independent per-finding protection,
governance-sensitive-narrative protection, overall_risk override attempts
(17 adversarial claimed values), malformed/missing-key model output
rejection, and forced-disclaimer.

## Two benchmark-authoring corrections (disclosed, GTD-style)

Verified against actual code before "fixing" anything:

1. `policy_decision_fields_protected`/`interaction_decision_fields_protected`/
   `governance_sensitive_narrative` originally expected `policy_state`/
   `clause_type`/`interaction_id` to survive in `build_enhanced_issues`'s
   output — but that function's output contract never included those keys
   at all (confirmed: `results.html` never references them; `review_queue.py`
   is the actual authoritative path for those fields, already validated).
   Corrected to check `title`/`severity`, this function's real protection
   surface.
2. `multi-policy-document-independent-protection` expected input order
   preserved in the output list — but `build_enhanced_issues` sorts its
   output by `(severity_rank, title)`. Corrected to an order-independent
   title→severity mapping.
3. One malformed-output case (`disclaimer=None`) was removed — a `None`
   disclaimer value is not malformed; `_validate_result` only checks key
   *presence*, then unconditionally force-overwrites the disclaimer
   regardless of its incoming value (already covered by the
   `disclaimer-always-forced` family).

## Regression

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed**.
- Phase B's 108-case dedup benchmark and Phase C's 114-case severity
  benchmark (both share `main.py`'s `build_enhanced_issues`): re-run,
  unchanged.
- 18-case real-app dashboard/listing integration suite: unchanged, 18/18.
- No adapter, interaction rule, or `POLICY_ENFORCEMENT_MODE` default
  touched. Only `evaluator.py` and `main.py`'s explanation-merge code
  changed.

## Conclusion

The explanation-authority invariant now holds for every path traced and
tested: a fabricated LLM finding cannot reach the user, and the displayed
declarative conclusion (title) and severity of a real finding cannot be
contradicted by LLM narration — only the supplementary free-text
explanation remains LLM-authored, exactly as the architecture's own
"explain, never decide" design intends.
