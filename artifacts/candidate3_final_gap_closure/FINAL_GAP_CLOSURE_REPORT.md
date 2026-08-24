STARTING COMMIT: `0ee86e2`
REMEDIATION COMMIT (frozen, see below for exact SHA): final commit on `claude/final-trust-architecture-cutover` at time of writing this report

ROOT CAUSE A — OPERATIVE CONTEXT: **FIXED**
ROOT CAUSE B — DEPENDENCY COMPLETENESS: **FIXED**
ROOT CAUSE C — CLEAN-STATE STABILITY: **FIXED** (originally-diagnosed mechanism; see below for a second, different mechanism found via mandated testing and NOT fixed)

OPERATIVE CONTEXT SAFETY: 5/5 applicable adapters (`liability`, `indemnification`, `insurance`, `payment_terms`, `sla` — the only 5 that call `is_operative_context`; the other 7 use different structural gates, N/A with code-supported justification in `ADAPTER_SAFETY_MATRIX.md`)
DEPENDENCY COMPLETENESS: 6/6 applicable adapters for cross-reference/definition detection (`insurance`, `data_security`, `ip_ownership`, `payment_terms`, `sla`, `warranties`); **NOT 12/12** for carve-out/exception visibility (only `limitation_of_liability` fixed; `confidentiality`/`ip_ownership`/`insurance`/`warranties`/`sla`/`assignment` remain open — see `RESIDUAL_RISK_REGISTER.md`)
MATERIAL CONTEXT PRESERVATION: **NOT 12/12** — `limitation_of_liability` fixed; 6 adapters still show `MATERIAL_CONTEXT_SILENTLY_LOST` on the burned corpus (10 cases total)
COMPETING READING SAFETY: **NOT 12/12** — 7 `ARBITRARILY_SELECTED_COMPETING_READING` cases remain across `limitation_of_liability`, `payment_terms`, `ip_ownership`, `insurance`, `sla`
CROSS-REFERENCE SAFETY: 6/6 applicable adapters — `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN = 0`
DEFINITION SAFETY: 3/3 applicable adapters (`insurance`, `data_security`, `ip_ownership`) — `UNRESOLVED_DEFINITION_TO_CLEAN = 0`
PROVIDER FAIL-CLOSED: 12/12 (unaffected by this mission; re-confirmed unchanged from the prior mission's 16/16 fault-injection results — no fault-injection code was touched)

BURNED DEVELOPMENT CORPUS (240 cases, real OpenAI, regression evidence only — NOT independent validation):
FALSE_SAFE: **0** (was 8)
UNVERIFIED_FEEDING_CLEAN: **0**
FALSE_OPERATIVE_TO_CLEAN: **0** (was 8)
FALSE_ABSENCE: **0**
MATERIAL_CONTEXT_SILENTLY_LOST: **10** (was 15) — target 0, NOT MET
ARBITRARILY_SELECTED_COMPETING_READING: **7** (was 8) — target 0, NOT MET
UNRESOLVED_CROSS_REFERENCE_TO_CLEAN: **0** (was 4)
UNRESOLVED_DEFINITION_TO_CLEAN: **0** (was 3)

REAL OPENAI PROVIDER: PASS (all calls succeeded; provider connectivity and auth were never the issue)
MODEL: `gpt-4o-mini`
REAL CALLS: 240 (burned-corpus replay, final run) + 250 (repeatability test) + prior smoke/verification calls = 490+ in this mission
CASES: 240 (burned replay) / 50 (repeatability: 48 selected + `ip_ownership-080` force-included + 2 fresh dev variants)
RUNS PER CASE: 1 (replay) / 5 (repeatability)
AI CANDIDATE REPEATABILITY: 10/50 cases showed candidate-span variation (expected, permitted)
CANONICAL FACT REPEATABILITY: 4/50 cases showed `absence_state` variation
POLICY CLEAN-STATE REPEATABILITY: 3/50 cases showed decision variation
PROVIDER_INDUCED_CLEAN_STATE_VARIANCE: **1/50** — `ip_ownership-086` (a NEW instance of the unfixed carve-out-visibility gap, distinct from the now-fixed `ip_ownership-080` mechanism) — target 0, NOT MET

SELECTIVITY BEFORE: CLEAN 23.3% / NOT_CLEAN 14.2% / REQUIRES_REVIEW 39.6% / NOT_APPLICABLE 20.4% / OTHER 2.5%
SELECTIVITY AFTER: CLEAN 15.0% / NOT_CLEAN 14.2% / REQUIRES_REVIEW 43.3% / NOT_APPLICABLE 24.6% / OTHER 2.9%
REVIEW RATE BEFORE: 42.1% (REQUIRES_REVIEW + ESCALATE)
REVIEW RATE AFTER: 46.2%

INTERACTION ENGINE: PASS (36/36 interaction-scoped tests pass; no interaction-engine code touched this mission; unaffected by construction — see `INTERACTION_REGRESSION.md`)
UNIFIED DOCUMENT STATE: PASS (`overall_risk` confirmed untouched via grep; `PolicyDecision` shape unchanged; new fields are adapter-internal — see `DOCUMENT_STATE_REGRESSION.md`)

TARGETED TESTS: 20 new tests (`tests/test_candidate3_final_gap_closure.py`, 19 covering Root Causes A/B/C class-level generalization with fresh non-burned phrasing, plus 1 end-to-end sla regression), all passing
FULL REGRESSION: 1464 passed / 10 failed / 1 skipped / 46 errors (10 failed / 46 errors are the pre-existing, environment-related baseline — `test_production_secrets.py` (missing `sqlalchemy`), `test_override_learning.py`, and unrelated collection errors — independently confirmed unchanged via `git stash` A/B comparison, not new)
NEW REGRESSIONS: **0**

FINAL GAP-CLOSURE VERDICT: **FAIL**
READY FOR NEW INDEPENDENT FROZEN CORPUS: **NO**

## What this verdict means, precisely

**All three chartered root causes are fixed and independently verified against the real OpenAI provider:**

1. **Root Cause A** (operative-context adjudication) — the `is_operative_context` boolean was replaced with a proper 4-state `classify_operative_context()` result (`OPERATIVE_CONFIRMED`/`NON_OPERATIVE_CONFIRMED`/`OPERATIVE_UNRESOLVED`/`CONFLICTING_CONTEXT`), adding three new structural signal families (party-obligation anchor as a rebuttal signal, direct obligation negation, hypothetical/illustrative framing without quote marks) rather than blacklisting the 8 specific failed phrases. All 8 originally-failing burned-corpus cases fixed; a 9th latent gap (an ungated `sla` regex) found and fixed via this mission's own end-to-end re-verification, not assumed safe from the classifier-level fix alone. `FALSE_SAFE` and `FALSE_OPERATIVE_TO_CLEAN` both confirmed 0/240 on the real-provider replay.
2. **Root Cause B** (dependency completeness) — cross-reference detection broadened uniformly across 6 adapters (a shared structural fix — "the" made optional — applied identically, not six different patches) plus a new shared `EXTERNAL_DEFINITION_NOT_ATTACHED_RE` primitive separating reference DETECTION from target RESOLUTION, as required. `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN` and `UNRESOLVED_DEFINITION_TO_CLEAN` both confirmed 0/240.
3. **Root Cause C** (clean-state stability) — the exact `ip_ownership-080` mechanism (a regex word-order gap making deterministic establishment depend on AI success) is fixed and directly verified stable across 5/5 real-provider runs, PLUS two freshly-worded development variants of the identical failure class, PLUS a fix to a second, compounding bug (`_nearest_category`'s subordinate-qualifier misattribution) that the prior mission found but reverted rather than ship alongside a regression.

**This mission's own mandated testing (the burned-corpus replay and the 250-execution repeatability test) found real, additional evidence beyond the three chartered root causes, exactly as the prior mission's testing found `ip_ownership-080` beyond ITS chartered scope:**

- **`MATERIAL_CONTEXT_SILENTLY_LOST` (10 remaining) and `ARBITRARILY_SELECTED_COMPETING_READING` (7 remaining)** on the burned corpus. A fix for one instance of the MATERIAL_CONTEXT_SILENTLY_LOST class (`limitation_of_liability`'s uncapped-carve-out visibility gap, 3 cases) was designed, implemented, and verified, including correcting two related pre-existing benchmark-corpus inconsistencies. The SAME class of gap exists in `confidentiality`, `ip_ownership`, `insurance`, `warranties`, `sla`, and `assignment`, but a safe fix requires per-adapter judgment about which established facts are inherently risk-bearing (like liability's uncapped carve-outs) versus routinely benign (like confidentiality's four standard exclusions, present in nearly every well-drafted clause) — copying the liability fix blindly would create a measured, real selectivity regression for at least confidentiality. This mission did not have remaining scope to make that judgment call correctly for 6 more adapters. `ARBITRARILY_SELECTED_COMPETING_READING`'s remaining cases are a genuinely different, new mechanism (same-document direct contradiction, not an AI competing-reading or a missing-carve-out) that would require a new conflict-detection mechanism not yet designed.
- **`PROVIDER_INDUCED_CLEAN_STATE_VARIANCE = 1`** (`ip_ownership-086`, found via the mandated 250-execution repeatability test): a NEW clean-state instability case, confirmed to be the SAME unfixed carve-out-visibility mechanism as the `MATERIAL_CONTEXT_SILENTLY_LOST` finding above, not a new or different regex gap.

**Nothing here was averaged away, softened, or hidden behind the pass-rate improvement** (142→172 of 240 across the full engagement's real-AI missions). Per this mission's own Section 25 hard-stop bar, `MATERIAL_CONTEXT_SILENTLY_LOST > 0`, `ARBITRARILY_SELECTED_COMPETING_READING > 0`, and `PROVIDER_INDUCED_CLEAN_STATE_VARIANCE > 0` are each independently sufficient for FAIL, regardless of the other 5/8 burned-corpus hard gates reaching zero and regardless of all three chartered root causes being genuinely fixed and independently verified against the real provider.

## Recommended next step

A properly scoped follow-up mission, chartered specifically to design and implement, per-adapter, the "established material dependency must always be visible in the decision, calibrated to what's actually risk-bearing in that adapter's domain" principle for `confidentiality`, `ip_ownership`, `insurance`, `warranties`, `sla`, and `assignment` — explicitly requiring, for each adapter, a documented judgment call (with adversarial test evidence) about which established facts are inherently notable vs. routinely benign, not a blanket copy of the `limitation_of_liability` fix. Separately, a same-document direct-contradiction detector, designed once as a shared primitive (mirroring how `EXTERNAL_DEFINITION_NOT_ATTACHED_RE` was built once and reused) rather than 4+ adapter-local reinventions, to close the remaining `ARBITRARILY_SELECTED_COMPETING_READING` cases.

Only after these are fixed and this exact burned corpus (still burned, never independent validation) shows all 8 hard gates at zero AND the repeatability test shows `PROVIDER_INDUCED_CLEAN_STATE_VARIANCE = 0`, should a genuinely new, previously-unseen frozen corpus be built for the actual production go/no-go decision.

Do not deploy. Do not merge. Do not change `FACT_ADMISSION_MODE` or `POLICY_ENFORCEMENT_MODE` production defaults — none were changed in this mission. Per Section 27, even a COMPLETE verdict would require stopping here and waiting for explicit authorization before building the next corpus — this verdict is FAIL, so that authorization question does not arise; the next step is the follow-up remediation mission described above, not a new corpus.
