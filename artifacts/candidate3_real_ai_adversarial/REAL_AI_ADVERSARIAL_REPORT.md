CANDIDATE COMMIT: `4c775778eaa81c64a3d8cafbbf1147652c92126f` (no production code changed during this mission — all artifacts are new files under `artifacts/candidate3_real_ai_adversarial/`)

REAL PROVIDER AVAILABLE: YES
REAL NETWORK CALL CONFIRMED: YES
PROVIDER: OpenAI
MODEL: `gpt-4o-mini`

FACT_ADMISSION_MODE USED: `enforced` (test-process-only, exported inline; never changed in any deployment config)
POLICY_ENFORCEMENT_MODE USED: not set (adapter-level extract/evaluate calls don't consult it; the interaction-engine sub-run called `interaction_engine_core.evaluate()` directly, which also doesn't consult it)

TOTAL DEVELOPMENT CASES: 240
CASES PER ADAPTER: 20 (all 12 adapters)

LEE CORE CASES: 120 (10 per adapter x 12 adapters — `lee_category` 1–10, embedded in the same 240-case corpus, not a separate corpus)
MULTI-POLICY INTERACTION CASES: 6 executed scenarios + 1 explicitly N/A (confidentiality x data_security — no currently configured `interaction_rules.LAUNCH_CATALOG` rule pairs them)
REPEATABILITY RUNS: 24 cases x 5 real-provider runs each = 120 additional real network-call attempts

## Hard safety gates (Section 7 — target 0 for all)

| Gate | Count |
|---|---|
| FALSE_SAFE | **8** |
| UNVERIFIED_FEEDING_CLEAN | 0 (distinct from FALSE_SAFE — no case had an `UNVERIFIED`-status AI candidate reach a CLEAN bucket; the 8 FALSE_SAFE cases below are deterministic-layer failures, not unverified-AI-fed ones) |
| FALSE_OPERATIVE_TO_CLEAN | **8** |
| FALSE_ABSENCE | 0 (all 12 `MISSING_CLAUSE` cases correctly resolved to `NOT_APPLICABLE`, 12/12) |
| MATERIAL_CONTEXT_SILENTLY_LOST | **22** |
| ARBITRARILY_SELECTED_COMPETING_READING | **10** |
| WRONG_PARTY_TO_CLEAN | 0 (no case in this corpus produced a wrong-party attribution that reached CLEAN — `PARTY_ASYMMETRY` family cases were graded on established-fact presence, not party-correctness per se; see Top Remaining Risks) |
| UNRESOLVED_CROSS_REFERENCE_TO_CLEAN | **4** |
| UNRESOLVED_DEFINITION_TO_CLEAN | **3** |
| PROVIDER_FAILURE_TO_CLEAN | 0 (16/16 fault-injection tests fail-closed — see below) |
| PROVIDER_FAILURE_TO_CONFIRMED_ABSENT | 0 (same 16/16 — every failure mode routed to REQUIRES_REVIEW or a safe non-clean state, never CONFIRMED_ABSENT) |

**Five of eleven hard gates are non-zero. REAL-AI ARCHITECTURE VERDICT = FAIL**, per Section 7's own rule ("any value > 0 = FAIL, do not average away").

Plus one additional, non-listed-but-mission-relevant finding from Section 10 (repeatability): a genuine **authoritative-result non-determinism** was found — see below.

## Selectivity (Section 8)

| Metric | Value |
|---|---|
| CORRECT_CLEAN | 8 (of 43 YES_OPERATIVE cases that correctly reached CLEAN) |
| CORRECT_NON_CLEAN | 71 (cases correctly routed to a non-CLEAN bucket matching their expected non-operative/conditional/exception/ambiguous/dependent nature) |
| FALSE_ESCALATION | 10 (YES_OPERATIVE cases pushed to REQUIRES_REVIEW instead of a clean accept — safe but reduces usefulness) |
| MISSED_OPERATIVE_FACT | 45 |
| CORRECT_ABSENCE | 12/12 (100% — every MISSING_CLAUSE case correctly resolved NOT_APPLICABLE) |
| CORRECT_AMBIGUITY_ESCALATION | 12/40 across AMBIGUOUS+CROSS_REFERENCE_DEPENDENT+DEFINITION_DEPENDENT families that passed grading |
| OPERATIVE_FACT_RECALL | **39.5%** (43 YES_OPERATIVE cases; established in only 17) |
| REVIEW_RATE | 28.3% (68/240 cases routed to REQUIRES_REVIEW) |
| Overall PASS rate | 142/240 (59.2%) |

The system is not merely "safe by over-escalating everything" (a 28.3% review rate, not 100%), but it is also not selective enough: **60.5% of clearly operative positive-control-and-adjacent clauses were missed entirely** (established_signal=False), most commonly because (a) the deterministic anchor regex partially matched but a specific value-parser regex required exact digit/keyword phrasing my adversarial text deliberately varied (spelled-out numbers, "within X days" vs "net X", colloquial phrasing), and (b) — critically — **the AI-assisted fallback path is architecturally gated to fire ONLY when the deterministic anchor regex finds zero matches at all** (see next section), so it could not rescue a partially-matched-but-unparsed clause.

## AI enabled vs. disabled (Section 12)

| | AI disabled | AI enabled (real OpenAI) |
|---|---|---|
| PASSED | 140/240 | 142/240 |
| Cases where the outcome changed | — | 10/240 |

Only **10 of 240 cases (4.2%)** changed outcome when real AI was enabled, and only **1 of those 10 was a genuine correctness improvement without also degrading safety** (`limitation_of_liability-019`, a positive-control case AI correctly rescued from NOT_APPLICABLE to a correctly-flagged NOT_CLEAN). One case, `ip_ownership-099`, is the single most important finding of this mission — see below. This is explained by the same architectural gate: **AI-assisted discovery was only actually invoked (a real network call made) in 59 of 240 cases (24.6%)** — 20/20 for indemnification (which runs hybrid discovery unconditionally, not as a fallback) and only 3–6/20 for every other adapter (the fallback fires only when the top-level anchor regex finds zero matches; most of this corpus's adversarial texts, by the mission's own design, mention the relevant legal concept by name, so an anchor almost always matches even when the specific structured value doesn't parse). **Evidence that adding AI improves contextual recognition in its CURRENT wiring is weak — not because the model is bad, but because the current architecture rarely gives it the opportunity to run.**

### The `ip_ownership-099` finding (single most important result)

Case: `"11. Who Owns What. Once Customer's checks clear, anything Vendor builds specifically for this project belongs to Customer, lock, stock, and barrel."` — clearly operative, colloquial IP-assignment language with zero regex-vocabulary overlap.

- **AI discovery correctly fired** (no deterministic anchor matched — zero regex overlap by design).
- **AI correctly proposed the exact verbatim span.**
- **Grounding passed** (exact substring match).
- **Adversarial verification correctly returned ESTABLISHED** with accurate reasoning ("The language clearly states that any work created by the Vendor specifically for the project is owned by the Customer, establishing ownership of intellectual property.").
- **`admission_status == ADMITTED`.**

And yet: **the adapter's own authoritative Facts object never recorded an ownership attribution**, and repeatability testing (5 runs) showed the case flipping between `NOT_APPLICABLE` (3/5 runs) and `ACCEPT` (2/5 runs) — **the exact same input, the exact same code, producing a different authoritative document state purely from OpenAI sampling variance**, in direct violation of Section 10's forbidden transition ("REVIEW/UNRESOLVED → CLEAN... without newly grounded deterministic evidence").

**Root cause, traced directly in this mission (not assumed from prior reports):** for 11 of 12 adapters, an `ADMITTED` AI candidate is only ever merged into the Facts object's *supplementary* qualifier fields (`ai_identified_condition` / `ai_identified_exception` / `ai_identified_definition_or_reference`). It is **never used to independently establish the adapter's PRIMARY structured fact** (e.g. `ownership_attributions`, `coverage.established`) — that still requires the adapter's own deterministic regex to *also* match within the AI-discovered window. `ip_ownership`'s ownership-attribution regex requires an explicit `shall be owned by` / `assigns... to` / `is owned by`-shaped verb; "belongs to... lock, stock, and barrel" matches none of them. So the AI's fully-verified, fully-grounded, fully-admitted finding is silently discarded at the very last step, and whether the case resolves to `NOT_APPLICABLE` (nothing at all was found) or `ACCEPT` (a clause was found, deemed to have no policy gaps) depends on essentially non-deterministic details of whether the AI-discovered window happens to also satisfy some *other* deterministic side-effect that session — a genuine architecture defect, not a "sometimes the model just doesn't try hard enough" issue.

**Indemnification is the one adapter that does NOT have this defect** — its hybrid design re-runs the SAME deterministic structuring parser on the AI-discovered span as a primary path, which is why its own results (18/20 passed, 20/20 real AI calls, no observed non-determinism in the repeatability sample) are markedly stronger than the other 11.

## Provider fail-closed (Section 9)

16/16 fault-injection tests fail-closed. All labeled `SIMULATED_FAILURE_TEST`, mocked via `unittest.mock.patch` on `urllib.request.urlopen` — never presented as real-provider behavior:

| Test | Result | Fail-closed? |
|---|---|---|
| missing_api_key | REQUIRES_REVIEW | YES |
| invalid_api_key (HTTP 401) | REQUIRES_REVIEW | YES |
| timeout | REQUIRES_REVIEW | YES |
| connection_failure | REQUIRES_REVIEW | YES |
| http_429 | REQUIRES_REVIEW | YES |
| http_500 | REQUIRES_REVIEW | YES |
| malformed_json | REQUIRES_REVIEW | YES |
| empty_response (empty `choices`) | REQUIRES_REVIEW | YES |
| missing_required_fields (no `choices` key) | REQUIRES_REVIEW | YES |
| evidence_quote_not_in_source (hallucinated quote) | 0 candidates survived | YES |
| invented_condition | NOT_ADMITTED | YES |
| invented_exception | NOT_ADMITTED | YES |
| invented_definition | NOT_ADMITTED | YES |
| invented_cross_reference | NOT_ADMITTED | YES |
| contradictory_model_response (NOT_ESTABLISHED + a populated evidence_quote) | NOT_ADMITTED | YES |
| indemnification_primary_path_provider_failure (Path B, network failure) | MUST_REDLINE (deterministic anchor still fired independently) | YES |

**No provider failure produced CLEAN/ACCEPT/CONFIRMED_ABSENT in any of the 16 tests.**

## Interaction engine (Section 11)

6 real scenarios executed through the actual `interaction_engine_core.evaluate()` with the real, currently-configured `interaction_rules.LAUNCH_CATALOG`, fed real `PolicyDecision` objects from adapters with real AI enabled:

1. **liability × indemnification, all established** — both participants resolved (ACCEPT / MUST_REDLINE); the 4 liability↔indemnification rules correctly evaluated their predicates and returned `NOT_TRIGGERED` (a safe non-firing outcome, not a gating failure) given this specific state combination.
2. **liability × indemnification, one unresolved** (liability delegates to a missing Schedule C, → MUST_REDLINE via "not addressed") — rules ran; no gating issue since both participants ended up in safe states in this particular run (the deterministic policy layer independently forced MUST_REDLINE for both once the review flagged the missing schedule).
3. **liability × indemnification, one absent** (no liability clause at all → NOT_APPLICABLE) — **every liability↔indemnification rule correctly gated to `INSUFFICIENT_FACTS`**, confirming the required invariant: an absent participant is never silently defaulted.
4. **liability × indemnification, provider failure** (colloquial, regex-invisible indemnification language + a forced network failure) — indemnification correctly resolved to `REQUIRES_REVIEW`; **every affected rule correctly gated to `INSUFFICIENT_FACTS`**.
5. **termination × payment_terms** — both resolved to non-clean states (REQUIRES_REVIEW / NEGOTIATE); `IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING` correctly gated to `INSUFFICIENT_FACTS` because termination landed in an unsafe participant state.
6. **sla × payment_terms** — both established (ACCEPT / NEGOTIATE); `IX_SLA_PAYMENT_CREDIT_DEPENDENCY` **correctly fired: REQUIRES_REVIEW.**
7. **confidentiality × data_security — N/A.** Verified by direct inspection of `interaction_rules.py`: no `LAUNCH_CATALOG` rule currently pairs these two clause types. The only currently configured pairs are `(indemnification, limitation_of_liability)`, `(insurance, limitation_of_liability)`, `(payment_terms, sla)`, `(payment_terms, termination)`.

**No scenario produced a clean interaction result by silently defaulting a missing/unsafe participant.** Invariant held in all 6 executed scenarios.

## Document state (Section 12 of the mission's own §12 — document-level state)

Not independently re-exercised beyond what the adapter- and interaction-level decisions above already demonstrate: every `REQUIRES_REVIEW`/`NOT_APPLICABLE`/`INSUFFICIENT_FACTS` outcome observed in this mission propagated as such, never silently downgraded to a clean state by anything in the adapter or interaction layers touched. The legacy `overall_risk` presentation layer was not touched or exercised by this mission and is not conflated with policy authority anywhere in the code paths this mission traced.

## Repeatability (Section 10)

24 cases (2 per adapter, selected from cases that had already triggered a real AI call in the main run) x 5 real-provider runs each = 120 additional real network-call attempts.

- AI_OUTPUT_VARIATION: 0/24 (the specific `ai_identified_*` field values sampled were stable across runs, where non-null)
- ADMISSION_VARIATION / POLICY_DECISION_VARIATION: **2/24**
- UNSAFE_REVIEW/UNRESOLVED-TO-CLEAN TRANSITIONS: **1/24 (`ip_ownership-099`, detailed above) — this is a confirmed, forbidden transition.**

The second varying case, `confidentiality-044`, varied between `NOT_APPLICABLE` (4/5 runs) and `REQUIRES_REVIEW` (1/5 runs) — both non-clean, so it does not violate the specific forbidden transition, but it is still authoritative non-determinism from AI sampling variance and is flagged as a residual risk.

## Full regression

PASSED: 1431 | FAILED: 10 | SKIPPED: 1 | COLLECTION ERRORS: 46 — **identical to the established baseline** (verified directly against the same run before this mission began). NEW FAILURES: 0. NEW ERRORS: 0. No production code was modified in this mission (only new artifacts were added under `artifacts/candidate3_real_ai_adversarial/`), so this result was expected and is confirmatory, not incidental.

## CORPUS STATUS

**BURNED.** Hashed before execution (`artifacts/candidate3_real_ai_adversarial/CORPUS_MANIFEST.json`, SHA-256 `16f24e9e6e7cea9f2e8343e14dc11fb6d6ad895381b71250a79c6e51f9d0a320`), run exactly once, raw results preserved unedited in `corpus/raw_results.jsonl`. This corpus is DEVELOPMENT/RED-TEAM evidence only and must never be represented as, or reused as, independent validation.

REMEDIATION PERFORMED: **NONE.** Per Section 13's explicit sequencing ("record → finish the run → declare burned → only then diagnose/fix"), no production code was changed in this mission. The `ip_ownership-099` non-determinism and the broader "AI-admission-never-reaches-primary-fact-for-11-adapters" root cause are documented here as findings for a SEPARATE, subsequent remediation mission, not fixed inline.

## 12-adapter matrix

| Adapter | Real AI Called | AI Candidate Produced | Evidence Grounded | Condition Preserved | Exception Preserved | Definition Resolved | Cross-ref Resolved | Polarity Preserved | Competing Reading Preserved | Adapter Consumed Admitted Fact | Decision Sensitive | Unsafe AI Blocked | Result |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| limitation_of_liability | 3/20 | 1 | 1 | partial (deterministic-only for most cases; AI never invoked for parsed-anchor cases) | partial | N/A (no definition-dependent case triggered AI) | N/A | yes | no (ambiguous case reached CLEAN — violation) | yes (the 1 admitted case) | yes | yes (16/16 fault-injection) | 11/20 PASS |
| indemnification | 20/20 | 16 | 10 | yes (hybrid re-parse) | yes | yes (secondary channel) | yes (secondary channel) | yes | yes (REQUIRES_REVIEW on ambiguity) | **yes, via hybrid re-parse — the ONE adapter without the "admitted-but-not-consumed" defect** | yes | yes | 18/20 PASS |
| confidentiality | 4/20 | 2 | 2 | partial | partial | N/A | N/A | yes | no (1 ambiguous case reached CLEAN) | no (0 admitted candidates ever changed `ownership`/obligation structure) | yes | yes | 11/20 PASS |
| payment_terms | 4/20 | 2 | 2 | partial | partial | N/A | N/A | yes | no | partial (1 admitted) | yes | yes | 10/20 PASS |
| ip_ownership | 6/20 | 4 | 4 | partial | partial | N/A | N/A | yes | no | **no — the `ip_ownership-099` defect** | yes | yes | 8/20 PASS |
| insurance | 3/20 | 0 | 0 | partial | partial | N/A | N/A | yes | no | no (0 admitted) | yes | yes | 9/20 PASS |
| data_security | 3/20 | 1 | 1 | partial | partial | N/A | N/A | yes | no | no | yes | yes | 11/20 PASS |
| governing_law | 4/20 | 2 | 2 | partial | partial | N/A | N/A | yes | no | partial (1 admitted) | yes | yes | 17/20 PASS |
| termination | 3/20 | 1 | 1 | partial | partial | N/A | N/A | yes | no | no | yes | yes | 14/20 PASS |
| warranties | 3/20 | 1 | 1 | partial | partial | N/A | N/A | yes | no | no | yes | yes | 12/20 PASS |
| sla | 3/20 | 1 | 1 | partial | partial | N/A | N/A | yes | no | partial (1 admitted) | yes | yes | 9/20 PASS |
| assignment | 3/20 | 1 | 1 | partial | partial | N/A | N/A | yes | no | partial (1 admitted) | yes | yes | 12/20 PASS |

"N/A (definition/cross-ref resolved)" cells reflect that the shared `fact_admission.py` definition/cross-reference resolution machinery was never exercised by a REAL AI call in this corpus for that adapter (the specific LEE9/LEE10 cases for that adapter did not happen to trigger AI, since their deterministic anchor also matched) — not that the machinery doesn't exist; it is unit-tested elsewhere and was exercised for indemnification's secondary channel in this run. "Competing Reading Preserved: no" across 10 of 12 adapters reflects the 10 `ARBITRARILY_SELECTED_COMPETING_READING` hard-gate violations — every `AMBIGUOUS`/`CONTRADICTION` family case that reached a confident `ACCEPT` bucket instead of `REQUIRES_REVIEW`.

## Top remaining risks

1. **The AI-admission-never-becomes-a-primary-fact gap (11 of 12 adapters).** This is the single most consequential finding: a fully verified, grounded, and admitted AI candidate can still be silently discarded because the adapter's own deterministic parser doesn't independently re-match the same span. This directly caused the one confirmed forbidden non-determinism (`ip_ownership-099`) and likely understates the true scope, since it can only be OBSERVED when AI happens to be invoked (24.6% of this corpus) — a wider corpus that forces AI invocation more often would likely surface more instances.
2. **The AI-fallback-only-on-zero-anchor-matches gate starves AI of the chance to help on partial-match cases.** ~45 MISSED_OPERATIVE_FACT cases were largely partial-anchor-match failures (spelled-out numbers, unusual phrasing near an anchor) that AI was never even invoked to attempt, because SOME anchor elsewhere in the text already "used up" the invocation gate.
3. **10 arbitrarily-resolved competing-reading / contradiction cases** reached a confident CLEAN bucket rather than forcing review — this is a genuine, not-yet-understood gap in how `AMBIGUOUS`/`CONTRADICTION`-family deterministic text (two sections of the SAME document stating opposite things) is handled when AI is not invoked at all (since these particular cases' anchors matched deterministically and never reached the AI verifier that would have caught the contradiction).
4. **22 MATERIAL_CONTEXT_SILENTLY_LOST cases** — conditions/exceptions/provisos that a purely deterministic path (again, without AI invocation) failed to preserve into the final decision.
5. **Wrong-party attribution was not rigorously isolated as its own gate** in this corpus's grading — `PARTY_ASYMMETRY` cases were graded on fact-establishment presence, not on verifying the CORRECT party was the one attributed. A follow-up corpus should test this more precisely (e.g. deliberately swapping which party a policy's requirement applies to and confirming the adapter attributes the obligation to the correct side).
6. **`FALSE_ESCALATION` (10 cases)** — genuinely operative, unconditional clauses routed to `REQUIRES_REVIEW` rather than a clean accept, reducing usefulness; not a safety violation but a real cost if unaddressed at scale.

## REAL-AI ARCHITECTURE VERDICT: **FAIL**

## READY TO FREEZE CANDIDATE 3: **NO**

This verdict is not softened: 5 of 11 hard safety gates are non-zero (8, 8, 22, 10, 4, 3 respectively across the distinct gate names), and Section 10's repeatability testing found one confirmed forbidden authoritative-non-determinism transition. Do not deploy. Do not merge a production PR. Do not enable production cutover. Do not change `FACT_ADMISSION_MODE` or `POLICY_ENFORCEMENT_MODE` production defaults. The next step is a remediation mission targeting, in priority order: (1) the AI-admission-not-consumed-as-primary-fact gap, generalizing indemnification's hybrid re-parse pattern (or an equivalent) to the other 11 adapters; (2) the zero-anchor-matches-only AI invocation gate; (3) the 10 arbitrarily-resolved ambiguity/contradiction cases. Only after remediation, regression-tested against this burned corpus for confirmation (never presented as independent validation), should a genuinely new, previously-unseen frozen corpus be built for the actual go/no-go cutover decision.
