# Burned Corpus Replay — Regression Evidence Only (Candidate 3 remediation)

**BURNED DEVELOPMENT REGRESSION ONLY. NOT INDEPENDENT VALIDATION.** Passing this replay does not authorize shipping. This is the exact same 240-case corpus from `artifacts/candidate3_real_ai_adversarial/corpus/cases.py`, imported unmodified (not copied, not edited — confirmed via matching corpus SHA-256 `16f24e9e6e7cea9f2e8343e14dc11fb6d6ad895381b71250a79c6e51f9d0a320` in both runs), run once against the remediated code with the real OpenAI provider (`gpt-4o-mini`).

## Aggregate result

| | Original (Candidate 3, pre-remediation) | Remediated |
|---|---|---|
| PASSED | 142/240 | **151/240** |
| RUNNER ERRORS | 0 | 0 |

**9 cases improved (fail → pass). 0 cases regressed (pass → fail).** Every improvement traces directly to Root Cause 1's fix; zero unrelated side effects.

## Improved cases (previous outcome / new outcome / root cause / code fix)

| Case | Previous | New | Root cause | Fix |
|---|---|---|---|---|
| confidentiality-045 | MATERIAL_CONTEXT_SILENTLY_LOST | PASS | Root Cause 2 (AI never invoked — deterministic anchor already matched, so the AI channel never got a chance to see the qualifier) | Always-run discovery |
| confidentiality-055 | MATERIAL_CONTEXT_SILENTLY_LOST | PASS | Root Cause 2 | Always-run discovery |
| insurance-116 | MATERIAL_CONTEXT_SILENTLY_LOST | PASS | Root Cause 2 | Always-run discovery |
| data_security-133 | ARBITRARILY_SELECTED_COMPETING_READING | PASS | Root Cause 2 (competing-reading detection only runs inside the AI verification pipeline; never invoked when a deterministic anchor already matched) | Always-run discovery |
| assignment-225 | MATERIAL_CONTEXT_SILENTLY_LOST | PASS | Root Cause 2 | Always-run discovery |
| assignment-226 | MATERIAL_CONTEXT_SILENTLY_LOST | PASS | Root Cause 2 | Always-run discovery |
| assignment-234 | MATERIAL_CONTEXT_SILENTLY_LOST | PASS | Root Cause 2 | Always-run discovery |
| assignment-235 | MATERIAL_CONTEXT_SILENTLY_LOST | PASS | Root Cause 2 | Always-run discovery |
| assignment-237 | ARBITRARILY_SELECTED_COMPETING_READING | PASS | Root Cause 2 | Always-run discovery |

All 9 improvements are Root Cause 2 fixes: with AI now always invoked (not just on zero deterministic matches), the adversarial verifier gets a chance to see a condition/exception/competing-reading in an ALREADY-anchored clause that it previously never examined at all.

**Directly verified**, not inferred: `ip_ownership-099` (the confirmed repeatability failure from the prior mission) now consistently reaches `REQUIRES_REVIEW` in this replay (`absence_state=PRESENT_BUT_UNRESOLVED`), matching the direct unit-test proof in `tests/test_candidate3_present_but_unresolved.py`.

## Hard-gate metrics — before vs. after

| Gate | Before | After | Target |
|---|---|---|---|
| FALSE_SAFE | 8 | **8** | 0 |
| FALSE_OPERATIVE_TO_CLEAN | 8 | **8** | 0 |
| FALSE_ABSENCE | 0 | 0 | 0 |
| MATERIAL_CONTEXT_SILENTLY_LOST | 22 | **15** | 0 |
| ARBITRARILY_SELECTED_COMPETING_READING | 10 | **8** | 0 |
| UNRESOLVED_CROSS_REFERENCE_TO_CLEAN | 4 | 4 | 0 |
| UNRESOLVED_DEFINITION_TO_CLEAN | 3 | 3 | 0 |
| UNVERIFIED_FEEDING_CLEAN | 0 | 0 | 0 |
| PROVIDER_FAILURE_TO_CLEAN | 0 | 0 | 0 |
| PROVIDER_FAILURE_TO_CONFIRMED_ABSENT | 0 | 0 | 0 |

**Not all hard gates reach zero.** This is reported exactly as measured, without averaging or hiding it behind the aggregate pass-rate improvement.

## Root-cause attribution of the remaining 8 FALSE_SAFE / 8 FALSE_OPERATIVE_TO_CLEAN cases

Directly diagnosed, not assumed: every one of these 8 cases is **byte-identical in outcome before and after this remediation** (confirmed via case-by-case diff against the original Candidate 3 run). None of them are new regressions, and none of them are caused by Root Causes 1, 2, or 3 — this mission's three chartered targets.

The actual mechanism, confirmed by direct testing:

```
>>> policy_engine_core.is_operative_context(
...     "Background. SaaS agreements typically commit to 99.9% uptime with service "
...     "credits for shortfalls, reflecting standard industry SLA practice.",
...     <span of "99.9% uptime">)
True   # WRONG — should be False; this is purely descriptive background text
```

`is_operative_context()`'s `_INDUSTRY_NORM_DESCRIPTIVE_RE` / `_NOT_YET_AGREED_RE` dual-signal design (added in Candidate 2's remediation) requires BOTH an industry-norm framing phrase AND an explicit "not yet agreed" disclaimer before rejecting a descriptive mention — a deliberate design choice at the time, to avoid suppressing a genuinely operative clause that merely opens with a benign industry-context lead-in. **Plain descriptive/background/hypothetical/quoted/negated prose that contains NEITHER signal (or only the industry-norm framing, with no explicit negotiation-pending language) is not caught, and this is purely a deterministic-classifier gap — it exists whether or not AI discovery ever runs.**

The 8 affected cases:

| Case | Family | Adapter |
|---|---|---|
| limitation_of_liability-001 | LEE2 (descriptive) | liability |
| insurance-102 | LEE3 (hypothetical) | insurance |
| data_security-130 | NEGATED | data_security |
| sla-201 | LEE2 (descriptive) | sla |
| sla-202 | LEE3 (hypothetical) | sla |
| sla-203 | LEE4 (negotiation/draft) | sla |
| sla-204 | LEE5 (quoted external) | sla |
| sla-210 | NEGATED | sla |

**This is a fourth, distinct root cause** (a gap in `is_operative_context`'s structural-cue vocabulary, not in AI invocation, AI-to-primary-fact consumption, or provider variance) that this mission was not chartered to fix (Section 0: "The purpose of this mission is to systematically fix the THREE architectural failures exposed by the real OpenAI run"). Per Section 13's explicit instruction ("Do not 'fix' unrelated pre-existing failures"), it is documented here precisely rather than silently patched under this mission's scope, and rather than silently left unmentioned to make the pass-rate look better than it is.

## Root-cause attribution of the remaining 4 UNRESOLVED_CROSS_REFERENCE_TO_CLEAN / 3 UNRESOLVED_DEFINITION_TO_CLEAN cases

Also confirmed byte-identical before and after this remediation (`sla-208`, `ip_ownership-088`, `data_security-128`, `insurance-108` for cross-reference; `insurance-109`, `data_security-129`, `ip_ownership-089` for definition) — not new regressions, not caused by Root Causes 1–3.

Directly diagnosed for `insurance-108` (`"Vendor shall maintain insurance coverage as set forth in Exhibit D (Insurance Requirements) attached hereto."`): `established_signal=False`, yet the decision reaches `ACCEPT` ("No policy gaps found"), because `_SCHEDULE_CROSSREF_RE` — the regex that should flag "material insurance requirements are delegated to a referenced Schedule/Exhibit not included in this text" — requires the literal word **"the"** before `Schedule`/`Exhibit` (`as\s+set\s+forth\s+in\s+the\s+(?:attached\s+)?(?:Schedule|Exhibit...)`), and does not match a directly-named exhibit like `"Exhibit D"` (no "the," a specific letter/number identifier instead). **A third, distinct, pre-existing regex-vocabulary gap** — narrower in scope than `is_operative_context`'s dual-signal issue above, but the same class of problem (a deterministic pattern too narrow for a common real-world phrasing), and again unrelated to AI invocation, AI-to-primary-fact consumption, or provider variance.

## Consequence for the mission's own hard-stop criteria (Section 22)

Because `FALSE_SAFE`, `FALSE_OPERATIVE_TO_CLEAN`, `MATERIAL_CONTEXT_SILENTLY_LOST`, `ARBITRARILY_SELECTED_COMPETING_READING`, `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN`, and `UNRESOLVED_DEFINITION_TO_CLEAN` remain non-zero on this burned corpus, the mission's own literal hard-stop bar is not met, even though all three chartered root causes are fixed and verified. See `FINAL_REMEDIATION_REPORT.md` for the full, unsoftened verdict.
