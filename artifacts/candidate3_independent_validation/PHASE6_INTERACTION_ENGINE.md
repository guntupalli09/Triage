PHASE 6 — INTERACTION ENGINE (real cutover, real AI)

Method: the 3 unique composite documents from the frozen corpus's `interaction_*` family (each
scored from both participating adapters in Phase 3/4/5) were run through
`policy_enforcement.apply_policies_for_review` — the exact production entry point `main.py`
calls — under a real, isolated cutover-mode database with ACTIVE `PolicyPosition`s for all 12
clause types, `FACT_ADMISSION_MODE=enforced`, and the real OpenAI provider. Script:
`phase6_interaction_engine.py`. Raw output: `phase6_result.json`.

## Results

| Document | Policy decision A | Policy decision B | Interaction decisions |
|---|---|---|---|
| `interaction_uncapped_indemnity` (uncapped liability + uncapped indemnity) | limitation_of_liability: `MUST_REDLINE` | indemnification: `REQUIRES_REVIEW` | ALL 7 launch-catalog rules: `INSUFFICIENT_FACTS` |
| `interaction_nonpayment_vs_dispute` (nonpayment termination + dispute-withholding right) | termination: `REQUIRES_REVIEW` | payment_terms: `REQUIRES_REVIEW` | ALL 7 launch-catalog rules: `INSUFFICIENT_FACTS` |
| `interaction_sla_payment_credit` (SLA credit + payment terms) | sla: `ACCEPT` | payment_terms: `REQUIRES_REVIEW` | ALL 7 launch-catalog rules: `INSUFFICIENT_FACTS` |

## Analysis

In every one of the 3 scenarios, at least one of the two directly-relevant participating
clause types reached a non-clean state (`MUST_REDLINE`/`REQUIRES_REVIEW`) on this real-provider
run. The interaction engine's participant gate (`_UNSAFE_PARTICIPANT_STATES = {NOT_APPLICABLE,
REQUIRES_REVIEW, EVALUATION_ERROR}`) correctly refused to evaluate any rule predicate against an
unsafe participant, producing `INSUFFICIENT_FACTS` uniformly rather than guessing at a clean or
unsafe interaction outcome. This is exactly the fail-closed behavior required.

**Limitation:** because at least one participant was non-clean in each of the 3 scenarios on
this specific run (itself consistent with real, non-deterministic AI verification, not a fixed
property of the documents — `sla` reached a clean `ACCEPT` in one scenario, for instance), no
scenario in this run reached the "both participants clean" state needed to observe a launch-
catalog rule actually FIRE a positive interaction finding (e.g. `IX_IP_UNCAPPED_LIABILITY_
WITH_INDEMNITY` genuinely escalating). This is not itself a defect — it demonstrates the
engine correctly declines to fabricate a finding from incomplete/unsafe inputs — but it means
this run's evidence for the interaction engine is specifically "unsafe participants never
produce a false clean interaction," not "a genuine cross-policy conflict is correctly detected
and escalated." The latter was already demonstrated in the pre-freeze inspection's and prior
missions' testing of the shared `interaction_engine_core.evaluate` mechanism directly (unit
tests, not this corpus).

## Interaction-specific hard-gate result

No unsafe or missing participant fact produced an authoritative clean interaction decision in
any of the 3 scenarios tested. **PASS** for the property actually tested this run.
