CANDIDATE 4 — PHASE 13: INTERACTION ENGINE

Reused Candidate 3's Phase 6 script (`phase6_interaction_engine.py`,
copied to `phase13_interaction_engine.py` with only path adjustments — no
logic changes) to re-exercise the REAL interaction engine, via
`policy_enforcement.apply_policies_for_review`, against the same 3
composite interaction-scenario documents from the burned corpus, under
real cutover-equivalent configuration (`FACT_ADMISSION_MODE=enforced`,
`POLICY_ENFORCEMENT_MODE=cutover`) and the real OpenAI provider.

Raw output: `phase13_result.json`.

## Result

All 7 launch-catalog interaction rules returned `INSUFFICIENT_FACTS` for
all 3 scenarios — identical fail-closed behavior to Candidate 3's Phase 6
result. Confirmed live:

```
=== interaction_uncapped_indemnity ===
  policy_decisions: {'limitation_of_liability': 'MUST_REDLINE', 'indemnification': 'REQUIRES_REVIEW', ...}
  interaction_decisions: {... all 7 rules: 'INSUFFICIENT_FACTS'}
=== interaction_nonpayment_vs_dispute ===
  policy_decisions: {'termination': 'REQUIRES_REVIEW', 'payment_terms': 'REQUIRES_REVIEW', ...}
  interaction_decisions: {... all 7 rules: 'INSUFFICIENT_FACTS'}
=== interaction_sla_payment_credit ===
  policy_decisions: {'payment_terms': 'REQUIRES_REVIEW', 'warranties': 'REQUIRES_REVIEW', 'sla': 'ACCEPT', ...}
  interaction_decisions: {... all 7 rules: 'INSUFFICIENT_FACTS'}
```

Note the third scenario: `sla` reaches `ACCEPT` (an adapter this mission
did not modify) while other required participants remain `REQUIRES_REVIEW`
or `NOT_APPLICABLE`. The interaction engine correctly does not manufacture
a positive finding merely because one of several participants happens to
be clean — `_UNSAFE_PARTICIPANT_STATES` gating (unchanged this mission)
still refuses to evaluate any rule predicate when a required participant
is unsafe/unresolved. No unsafe clean interaction was manufactured.

This mission did not modify `interaction_engine_core.py` or any
interaction-rule definition. As with Candidate 3's Phase 6, no scenario in
this fixed set of 3 composite documents reached "all participants clean"
in this run, so a positive interaction firing was not observed here either
— this remains a limitation of the fixed test-scenario set, not a defect
(documented identically to Candidate 3's Phase 6 report).
