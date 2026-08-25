# Real-Provider Repeatability Test (Candidate 3 final gap-closure, Section 18)

50 cases (4 per adapter × 12 adapters = 48, plus `ip_ownership-080` force-included as a burned regression case, plus 2 fresh development-only `ip_ownership-080`-failure-class variants) × 5 independent real-provider runs = **250 real OpenAI calls** (exceeds the required ≥240). Model: `gpt-4o-mini`. Full raw output: `repeatability/repeatability_final_results.json`.

## Results, measured separately per Section 18

| Dimension | Result |
|---|---|
| AI candidate-set stability | 10/50 cases showed the discovered candidate span(s) vary run-to-run (expected and permitted — AI's own recall varies) |
| Canonical-fact (absence_state) stability | 4/50 cases showed `absence_state` vary run-to-run |
| Policy-decision stability | 3/50 cases showed the final decision `state` vary run-to-run |
| **PROVIDER_INDUCED_CLEAN_STATE_VARIANCE** | **1/50 — a confirmed, forbidden clean-state transition** |

## `ip_ownership-080`: CONFIRMED FIXED

`REQUIRES_REVIEW` in all 5/5 runs (previously `REQUIRES_REVIEW, REQUIRES_REVIEW, ACCEPT, REQUIRES_REVIEW, REQUIRES_REVIEW` before this mission). `absence_state=CONFIRMED_ABSENT` in all 5 runs (the deterministic ownership regex now establishes `work_product: Client` correctly and consistently, so the outcome no longer depends on AI at all for this exact phrasing). Root Cause C's originally-diagnosed mechanism is closed and directly verified — not merely inferred from the code fix.

Both fresh `dev-ipownership-080-class` variants (freshly worded, same failure shape — an adverb between "owned" and "by") are also perfectly stable: `class-01` reaches `ACCEPT` in 5/5 runs, `class-02` reaches `REQUIRES_REVIEW` in 5/5 runs. Neither depends on AI discovery success.

## `ip_ownership-099`: safe variance (per Section 18's explicit carve-out)

`REQUIRES_REVIEW` ×4, `NOT_APPLICABLE` ×1 — never touches a clean state. Acceptable.

## `ip_ownership-086`: a NEW, confirmed forbidden clean-state transition

**Not previously identified — found by this mission's own mandated repeatability test.** Case text (LEE7 family): `"Work product shall be owned by Customer, except for Vendor's pre-existing background IP incorporated into the deliverables, which Vendor retains."` Run states: `ACCEPT, REQUIRES_REVIEW, REQUIRES_REVIEW, ACCEPT, REQUIRES_REVIEW`.

**Root cause, directly traced**: "Work product shall be owned by Customer" deterministically establishes `ownership_attributions["work_product"]["Customer"]` in every run (stable, `absence_state=CONFIRMED_ABSENT` in all 5 runs — the deterministic layer itself never varies). The variance comes entirely from whether the AI-discovered background-IP carve-out ("Vendor retains pre-existing background IP") is successfully admitted in a given run. This is the exact same mechanism already identified and left unfixed in `BURNED_CORPUS_REGRESSION.md`'s `MATERIAL_CONTEXT_SILENTLY_LOST` analysis for `ip_ownership` (LEE6/LEE7 carve-out visibility gap) — confirmation that the same unfixed gap also produces genuine clean-state instability, not just a static burned-corpus miss. **Not fixed in this mission** — see `RESIDUAL_RISK_REGREGISTER.md` for why extending `limitation_of_liability`'s carve-out-surfacing fix to `ip_ownership` requires adapter-specific judgment this mission did not complete.

## `termination-179`: safe variance

`REQUIRES_REVIEW` ×1, `NOT_APPLICABLE` ×4 — never touches a clean state. Acceptable per Section 18's carve-out.

## Consequence

Per Section 25's explicit hard-stop condition, `PROVIDER_INDUCED_CLEAN_STATE_VARIANCE > 0` (measured: 1) is independently sufficient for **FINAL GAP-CLOSURE VERDICT: FAIL**. Root Cause C's originally-diagnosed mechanism (the specific `ip_ownership-080` regex gap) is fixed and directly verified stable across both the burned case and two fresh development variants. But this mission's own mandated repeatability testing found a SECOND, different clean-state-instability mechanism (`ip_ownership-086`, the same unfixed carve-out-visibility gap already documented in `BURNED_CORPUS_REGRESSION.md`), exactly mirroring how the Candidate 3 remediation mission's repeatability testing found `ip_ownership-080` itself as a residual beyond the originally-chartered scope. This is reported as new, mandated-testing-discovered evidence, not softened or folded into the "Root Cause C: FIXED" claim.
