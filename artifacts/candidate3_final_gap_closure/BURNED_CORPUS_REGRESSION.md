# Burned Corpus Replay — DEVELOPMENT REGRESSION — BURNED CORPUS — NOT INDEPENDENT VALIDATION

Same frozen 240-case corpus (`artifacts/candidate3_real_ai_adversarial/corpus/cases.py`), imported unmodified (SHA-256 `16f24e9e6e7cea9f2e8343e14dc11fb6d6ad895381b71250a79c6e51f9d0a320`, confirmed unchanged), run against this mission's final code state with the real OpenAI provider (`gpt-4o-mini`). Full raw output: `burned_corpus_replay/raw_results.jsonl`.

Three replay runs were executed as fixes landed (142→151 baseline at mission start → 168 → 167 → **172/240 final**); each result below is from the final run, against the final committed code.

## Hard-gate results (Section 17)

| Gate | Mission start (commit `0ee86e2`) | Final (this mission) | Target |
|---|---|---|---|
| FALSE_SAFE | 8 | **0** | 0 |
| UNVERIFIED_FEEDING_CLEAN | 0 | **0** | 0 |
| FALSE_OPERATIVE_TO_CLEAN | 8 | **0** | 0 |
| FALSE_ABSENCE | 0 | **0** | 0 |
| MATERIAL_CONTEXT_SILENTLY_LOST | 15 | **10** | 0 |
| ARBITRARILY_SELECTED_COMPETING_READING | 8 | **7** | 0 |
| UNRESOLVED_CROSS_REFERENCE_TO_CLEAN | 4 | **0** | 0 |
| UNRESOLVED_DEFINITION_TO_CLEAN | 3 | **0** | 0 |

**5 of 8 hard gates reached zero. 2 remain non-zero: MATERIAL_CONTEXT_SILENTLY_LOST=10, ARBITRARILY_SELECTED_COMPETING_READING=7.** Per Section 25/17, this means the mission's overall hard-gate bar is **not met**. Reported exactly as measured — not averaged, not hidden behind the pass-rate improvement (142→172/240).

## What closed Root Causes A/B/C (verified zero across all three replay runs)

- **FALSE_SAFE / FALSE_OPERATIVE_TO_CLEAN → 0**: `classify_operative_context()`'s new signal families (Root Cause A) plus the `data_security` breach-notification-disclaimer fix (found via this mission's own re-verification, not one of the 3 originally-chartered mechanisms, but the same class of "material fact silently absorbed into a clean decision" defect).
- **UNRESOLVED_CROSS_REFERENCE_TO_CLEAN / UNRESOLVED_DEFINITION_TO_CLEAN → 0**: the six broadened cross-reference regexes plus the new shared `EXTERNAL_DEFINITION_NOT_ATTACHED_RE` primitive (Root Cause B).

## Remaining 10 MATERIAL_CONTEXT_SILENTLY_LOST cases

| Case | Adapter | Family |
|---|---|---|
| confidentiality-054 | confidentiality | BACKWARD_QUALIFIER |
| ip_ownership-095 | ip_ownership | FORWARD_QUALIFIER |
| ip_ownership-096 | ip_ownership | LONG_DISTANCE |
| insurance-105 | insurance | LEE6 |
| insurance-106 | insurance | LEE7 |
| insurance-116 | insurance | LONG_DISTANCE |
| warranties-185 | warranties | LEE6 |
| sla-214 | sla | BACKWARD_QUALIFIER |
| sla-216 | sla | LONG_DISTANCE |
| assignment-236 | assignment | LONG_DISTANCE |

**Root cause, directly diagnosed (not assumed) via `limitation_of_liability`'s 3 identical-shape cases, which WERE fixed this mission**: a deterministically-established material modifier (a carve-out, exclusion, or cross-section qualifier) is correctly discovered and structured into the adapter's own internal facts (confirmed directly for `confidentiality-054`: `exclusions_present` correctly reachable once the `public_knowledge` regex is broadened to include "publicly available"), but the FINAL decision only surfaces it as a note/escalation when the specific POLICY CONFIGURATION explicitly names that category — an unconfigured (but real) carve-out is invisible in the output, same shape as `limitation_of_liability`'s fixed defect.

**Why this mission does not extend the `limitation_of_liability` fix to the other 5 adapters**: the fix that worked for `limitation_of_liability` (elevate to `ACCEPT_WITH_NOTE` whenever ANY established "uncapped" carve-out isn't already required) is semantically specific to liability's domain, where an uncapped carve-out for a real risk category is inherently notable every time. The same blanket rule does NOT generalize safely to `confidentiality`: its four standard exclusions (public-domain, independently-developed, third-party-rightful, required-by-law) are ROUTINELY present in nearly every well-drafted confidentiality clause and are normatively GOOD, not risk-bearing — forcing `ACCEPT_WITH_NOTE` on every one of them would flag the overwhelming majority of ordinary confidentiality clauses, a direct, measured violation of Section 19's selectivity requirement, not a safety improvement. `insurance`, `warranties`, `sla`, and `assignment`'s cases require the same category-by-category judgment (which specific established fact is inherently risk-bearing vs. routinely benign) that this mission did not have remaining scope to perform correctly, adapter by adapter, without risking either a new selectivity regression or a superficial fix that doesn't actually address the semantic question. **Reported as an open, understood, NOT fixed gap** — see `RESIDUAL_RISK_REGISTER.md`.

## Remaining 7 ARBITRARILY_SELECTED_COMPETING_READING cases

| Case | Adapter | Family |
|---|---|---|
| limitation_of_liability-017 | limitation_of_liability | CONTRADICTION |
| payment_terms-067 | payment_terms | LEE8 |
| ip_ownership-087 | ip_ownership | LEE8 |
| ip_ownership-097 | ip_ownership | CONTRADICTION |
| insurance-107 | insurance | LEE8 |
| insurance-117 | insurance | CONTRADICTION |
| sla-217 | sla | CONTRADICTION |

**Root cause, directly diagnosed for `limitation_of_liability-017`** (`"...liability shall not exceed one times the fees... For clarity, Vendor's liability under this Agreement shall be unlimited and Section 15 shall not apply."`): this is a genuine, DETERMINISTICALLY-VISIBLE textual contradiction within the same document (two directly conflicting statements about the same cap, not an ambiguous AI-proposed reading) — a different mechanism than `fact_admission.ground_competing_readings` (which handles AI-discovered competing interpretations of ambiguous language), and not currently covered by any adapter's own conflict-detection logic, which was built for two clauses disagreeing on a categorical dimension (e.g. `claims_made_occurrence_conflict`), not for a later clause explicitly overriding/nullifying an earlier one's cap value entirely. `LEE8`-family cases (`payment_terms-067`, `ip_ownership-087`, `insurance-107`) are structurally similar: two sections of the SAME document giving genuinely incompatible values with no reconciling language, which the current controlling-provision-selection logic resolves by simply picking one match (typically the first or most specific) rather than recognizing the pair as an unresolved conflict.

**Not fixed this mission**: building a general "does a later statement in the same document directly override/nullify an earlier established value" detector, safely, across 4+ adapters with different value-comparison semantics (a numeric cap vs. a due-date vs. an ownership category vs. a coverage-scope description), is a genuinely new mechanism this mission did not have scope to design and verify without risking either false conflict-flagging on legitimate multi-provision drafting (e.g. a general cap with a legitimately DIFFERENT super-cap for one category, which is NOT a contradiction) or an incomplete, adapter-specific patch. **Reported as an open, understood, NOT fixed gap** — see `RESIDUAL_RISK_REGISTER.md`.

## Consequence

Per Section 25, `MATERIAL_CONTEXT_SILENTLY_LOST > 0` and `ARBITRARILY_SELECTED_COMPETING_READING > 0` are each independently sufficient for **FINAL GAP-CLOSURE VERDICT: FAIL**, regardless of the other 6/8 gates reaching zero and regardless of the substantial, independently-verified closure of Root Causes A, B, and C. See `FINAL_GAP_CLOSURE_REPORT.md`.
