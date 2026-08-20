# Step 4A.10.1 Phase 13 — Authority-Boundary Recheck (post-fix)

Re-audited after both Step 4A.10.1 changes (the operative-context gate and
the false-symmetry safety net) to confirm neither accidentally opened a
semantic-authority path.

## `is_operative_context` (policy_engine_core.py)

Pure text-structural function: takes `(text, match_start, match_end)` —
plain Python `str` and `int` offsets already established by a
DETERMINISTIC regex match (either the main `_OBLIGATION_RE`/
`_SYNONYM_OBLIGATION_RES` loop over raw document text, or
`_verify_semantic_candidate`'s re-run of those SAME regexes against an
already-verbatim-validated candidate span). It reads no semantic output,
no `discovery_metadata`, no model-provided confidence/interpretation —
only the surrounding characters of the document itself. It can only
return `True`/`False`; `False` causes the calling loop to `continue`
(skip building an obligation), never to fabricate one. **No new
authority path.**

## False-symmetry safety net (`detect_role_attributed_asymmetry`,
policy_engine_core.py)

Also pure text-structural: `_DIFFERENTIATING_QUALIFIER_RE` is checked
against `local_texts[role]`, which is built the same way the pre-existing
`snapshot_fn` inputs always were — a bounded window of the DOCUMENT TEXT
around a deterministic `_ROLE_ATTRIBUTION_RE` match. The safety net can
only ADD a reason string to `asymmetry_reasons` (routing a decision toward
`REQUIRES_REVIEW`), never remove a reason, never set a role/side/cap/
policy-outcome field directly, and never reads anything semantic-sourced.
Its only effect is to make the system LESS willing to certify clean
symmetry, strictly in the safe direction. **No new authority path.**

## `_ROLE_ATTRIBUTION_RE` widening

Purely additive alternation on an existing regex already used only within
the asymmetry-comparison pathway (never the main obligation-structuring
path, never fed by semantic candidates). Widening it can only cause MORE
attribution comparisons to run (more scrutiny), never grant any new
component authority over a fact. **No new authority path.**

## Verification against the same 10 checks from Step 4A.10 Phase 2/Section F

All 10 checks (semantic actor labels / directionality / monetary values /
policy recommendations / non-verbatim evidence / invalid offsets /
unsupported metadata / semantic absence / provider outage / candidate
confidence) remain governed by the IDENTICAL code paths audited in Step
4A.10 (`_verify_semantic_candidate`, `_run_semantic_discovery`,
`extract_indemnification_facts`'s absence-state gate) — none of those
functions were touched by this step's changes; only the internals of the
deterministic structuring/comparison logic that they call INTO were
changed. **Conclusion: unchanged, still CONFIRMED, PASS.**
