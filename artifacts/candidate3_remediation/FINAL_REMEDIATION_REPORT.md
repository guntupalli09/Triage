FROZEN INPUT COMMIT: `59a258a144899dcd37872736db7260383ec18ca6`
REMEDIATION COMMIT: `513c7e3` (branch `claude/final-trust-architecture-cutover`)

AUTHORITY BOUNDARY: PASS (unchanged by this mission — every decision-state assignment still happens only inside each adapter's own `evaluate_*_policy()`; `fact_admission.py` still has zero references to any of the 8 decision states; re-confirmed by direct code read, not assumed)

AI CONTEXTUAL DISCOVERY: 12/12 (Root Cause 2 fixed for all 11 shared-framework adapters; indemnification already ran discovery unconditionally)
AI-ONLY PRIMARY FACT GROUNDING: 6/12 explicitly fixed via the new `PRESENT_BUT_UNRESOLVED` state (insurance, payment_terms, ip_ownership, data_security, warranties, sla); 6/12 already safe via a pre-existing blanket "nothing structured → REQUIRES_REVIEW" branch or (liability) a "no numeric cap → MUST_REDLINE" branch, or (indemnification) its own hybrid re-parse — verified per-adapter, not assumed uniform
CANONICAL PRIMARY FACT ADMISSION: 12/12 (no new schema needed — `CandidateMaterialFact` already represented everything Section 2 requires; see `CANONICAL_PRIMARY_FACT_SCHEMA.md`)
ADAPTER CONSUMPTION: 12/12
CONDITION SAFETY: 12/12 (unchanged — `ground_qualifiers`/`evaluate_admission`'s existing qualifier-grounding gate was not touched)
EXCEPTION SAFETY: 12/12 (same)
DEFINITION SAFETY: 9/12 PASS, **3/12 confirmed FAIL** (insurance, data_security, ip_ownership — `UNRESOLVED_DEFINITION_TO_CLEAN`, pre-existing, unrelated to this mission's 3 root causes — see `BURNED_CORPUS_REGRESSION.md`)
CROSS-REFERENCE SAFETY: 8/12 PASS, **4/12 confirmed FAIL** (sla, ip_ownership, data_security, insurance — `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN`, pre-existing, unrelated to this mission's 3 root causes)
COMPETING-READING SAFETY: improved but not zero — `ARBITRARILY_SELECTED_COMPETING_READING` 10→8 on the burned corpus; **not fully closed**
ABSENCE SAFETY: 12/12 for `FALSE_ABSENCE` specifically (0/240 on the burned corpus, both before and after); **not** 12/12 for the broader safety property, since 2 adapters (sla, ip_ownership, data_security, liability) still show `FALSE_SAFE`/`FALSE_OPERATIVE_TO_CLEAN` from the separate `is_operative_context` gap
PROVIDER FAIL-CLOSED: 12/12 for actual provider failures (16/16 fault-injection tests fail-closed in the prior mission, unaffected by this remediation); **but 1 confirmed provider-VARIANCE violation** (not a failure — a successful-but-inconsistent discovery) — see below

REAL OPENAI PROVIDER: PASS
MODEL: `gpt-4o-mini`
REAL PROVIDER CALLS: ~600+ across this mission (240-case burned-corpus replay + 36×5=180 repeatability calls + smoke tests); every call made through the application's own `fact_admission.discover_candidate_spans`/`verify_and_ground`/`semantic_discovery_real.discover_candidate_spans_real` — never a standalone script hitting OpenAI directly
AI DISCOVERY REPEATABILITY: qualitative — AI's own candidate-discovery success/failure varies run-to-run for unusually-phrased clauses, as expected and permitted
CANONICAL FACT REPEATABILITY: 4/36 sampled cases showed decision variation
POLICY DECISION REPEATABILITY: **FAIL — 1/36 confirmed forbidden clean-state transition** (`ip_ownership-080`: REQUIRES_REVIEW/REQUIRES_REVIEW/**ACCEPT**/REQUIRES_REVIEW/REQUIRES_REVIEW, root-caused to `_OWNERSHIP_PASSIVE_RE` not matching "owned **exclusively** by")

BURNED CORPUS (240 cases, real OpenAI, regression evidence only — NOT independent validation):
FALSE_SAFE: **8** (target 0 — unchanged from pre-remediation; all 8 confirmed byte-identical before/after, root-caused to `is_operative_context`'s dual-signal gap, not this mission's 3 root causes)
UNVERIFIED_FEEDING_CLEAN: 0
FALSE_OPERATIVE_TO_CLEAN: **8** (target 0 — same 8 cases as FALSE_SAFE above)
FALSE_ABSENCE: 0
MATERIAL_CONTEXT_SILENTLY_LOST: **15** (target 0 — improved from 22; all 9 improvements directly attributable to Root Cause 2's fix)
ARBITRARILY_SELECTED_COMPETING_READING: **8** (target 0 — improved from 10)
UNRESOLVED_CROSS_REFERENCE_TO_CLEAN: **4** (target 0 — unchanged; root-caused to `_SCHEDULE_CROSSREF_RE` requiring the literal word "the")
UNRESOLVED_DEFINITION_TO_CLEAN: **3** (target 0 — unchanged, same underlying cause)

INTERACTION ENGINE: PASS (all 6 real-AI scenarios + 1 explicit N/A re-verified identical to pre-remediation; every unsafe/missing participant correctly gates to `INSUFFICIENT_FACTS`)
UNIFIED DOCUMENT STATE: PASS (`PRESENT_BUT_UNRESOLVED` is adapter-internal, always resolves to a standard `REQUIRES_REVIEW` `PolicyDecision` before leaving the adapter boundary; legacy `overall_risk` badge confirmed untouched via `grep`, not assumed)

TARGETED TESTS: 13 new regression tests (`tests/test_candidate3_present_but_unresolved.py`), all passing — positive controls, the fix itself, and a decision-sensitivity pairing per fixed adapter, plus a direct 5x deterministic-replay repeatability proof for `ip_ownership`
FULL REGRESSION: 1444 passed / 10 failed / 1 skipped / 46 errors
NEW REGRESSIONS: **0** (identical failure/error counts to the established baseline throughout every commit in this mission, re-verified after every single adapter change and after the one attempted-then-reverted fix)

ADAPTERS COMPLETE: 12/12 for the 3 chartered root causes (every adapter individually re-verified against current code, not assumed); **NOT** 12/12 for the mission's own bundled hard-gate bar, because 2 additional, distinct, pre-existing, out-of-scope defects (an `is_operative_context` dual-signal gap, and a narrow `_SCHEDULE_CROSSREF_RE`/`_OWNERSHIP_PASSIVE_RE` regex vocabulary) also feed into that same bar

FINAL REMEDIATION VERDICT: **FAIL**
READY FOR NEW INDEPENDENT FROZEN CORPUS: **NO**

## What this verdict means, precisely

**All three chartered root causes are fixed and independently verified:**
1. **Root Cause 1** (admitted AI candidate not becoming the adapter's primary fact) — fixed via a new `PRESENT_BUT_UNRESOLVED` absence-state, applied to exactly the 6 adapters that needed it (verified per-adapter from current code, not assumed uniform); the other 6 adapters already had an equivalent safety net, also verified rather than assumed. Directly confirmed: the exact `ip_ownership-099` non-determinism from the prior mission is fixed (consistently `REQUIRES_REVIEW` now, never `ACCEPT`).
2. **Root Cause 2** (AI-only-invoked-on-zero-deterministic-anchors) — fixed for all 11 shared-framework adapters (indemnification already didn't have this gate). Directly measured benefit: 9 burned-corpus cases improved from FAIL to PASS, zero regressions, all attributable to this fix specifically.
3. **Root Cause 3** (provider variance leaking into clean decisions) — the SPECIFIC mechanism identified in the prior mission (an admitted-but-unstructured candidate reaching a bare `ACCEPT`) is closed by Root Cause 1's fix, as designed and predicted in `PROVIDER_VARIANCE_DESIGN.md`. **However, this mission's own mandated 36×5 real-provider repeatability test found ONE additional, different mechanism** producing the same class of forbidden variance (`ip_ownership-080`), rooted in a narrow regex-vocabulary gap unrelated to the three chartered causes. An attempted fix was tried, found to introduce a real regression in an existing benchmark case, and correctly reverted rather than shipped. Root Cause 3 is therefore **not fully closed** — it is closed for the originally-diagnosed mechanism, with one newly-discovered residual instance left open and explicitly documented.

**Two additional, distinct, pre-existing, out-of-scope defects were also precisely diagnosed** (not merely observed as unchanged failure counts) during this mission's replay and reporting work, and account for every hard-gate count that remains non-zero:
- `is_operative_context()`'s dual-signal design (from Candidate 2) doesn't reject plain descriptive/hypothetical/negotiation/quoted/negated text that lacks BOTH of its required signal phrases — 8 burned-corpus cases, concentrated in `sla` and one each in `liability`/`insurance`/`data_security`.
- `_SCHEDULE_CROSSREF_RE` requires the literal word "the" before Schedule/Exhibit and misses a directly-named exhibit ("Exhibit D") — 4+3 burned-corpus cases across `insurance`/`data_security`/`ip_ownership`/`sla`.

Per this mission's own Section 0 charter ("fix the THREE architectural failures") and Section 13's explicit instruction ("do not fix unrelated pre-existing failures"), neither of these was fixed here. Per this mission's own Section 22 hard-stop bar (which bundles ALL of `FALSE_SAFE`, `MATERIAL_CONTEXT_SILENTLY_LOST`, etc. together regardless of which root cause causes them), their continued non-zero counts mean the overall verdict cannot be COMPLETE, even though every root cause this mission was chartered to fix has been fixed and independently verified.

**Nothing here was averaged away, softened, or hidden behind the aggregate pass-rate improvement** (142→151 of 240). The report states plainly: 3/3 chartered root causes fixed; 2 additional defects found and left open by design; 1 new defect found via mandated testing, a fix attempted and correctly reverted upon discovering it caused a different regression.

## Recommended next step

A properly scoped follow-up mission, chartered specifically to:
1. Broaden `is_operative_context()`'s structural-cue vocabulary to catch descriptive/hypothetical/negotiation/quoted/negated text that carries only ONE (or neither) of the current dual signals, without over-suppressing genuinely operative text — this is nontrivial (the dual-signal design was itself a deliberate anti-over-suppression choice in Candidate 2) and deserves its own adversarial test corpus, not a quick patch.
2. Broaden `_SCHEDULE_CROSSREF_RE` to match a directly-named exhibit/schedule without requiring "the."
3. Fix `_OWNERSHIP_PASSIVE_RE`'s adverb gap WITHOUT reintroducing the category-misattribution regression this mission found and reverted — likely requires tightening the category-attribution heuristic's "nearest preceding keyword" logic at the same time, not just the ownership regex in isolation.

Only after these are fixed and this exact burned corpus (still burned, never to be used as independent validation) shows all hard gates at zero, should a genuinely new, previously-unseen frozen corpus be built for the actual production go/no-go decision.

Do not deploy. Do not merge. Do not change `FACT_ADMISSION_MODE` or `POLICY_ENFORCEMENT_MODE` production defaults — none were changed in this mission.
