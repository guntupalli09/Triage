PHASE 1 — ACTIVATE THE INTENDED ARCHITECTURE IN VALIDATION (evidence summary)

Full raw output preserved in `phase1_result.json`. Script: `phase1_cutover_trace.py`.

## Runtime configuration proof (not merely code inspection — executed and printed at runtime)

```
POLICY_ENFORCEMENT_MODE (as read by the running app): cutover
FACT_ADMISSION_MODE global switch active: True
  LIABILITY_SEMANTIC_DISCOVERY_ENABLED: True
  INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED: True
  CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED: True
  PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED: True
  IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED: True
  INSURANCE_SEMANTIC_DISCOVERY_ENABLED: True
  DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED: True
  GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED: True
  TERMINATION_SEMANTIC_DISCOVERY_ENABLED: True
  WARRANTIES_SEMANTIC_DISCOVERY_ENABLED: True
  SLA_SEMANTIC_DISCOVERY_ENABLED: True
  ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED: True
2026-08-24T22:42:25 INFO [evaluator] OpenAI client initialized successfully
```

Configuration was set via `os.environ[...]` inside this validation script's own process only —
never written to any repository file, `.env`, or deployment configuration. `DEV_MODE=true` and
an isolated, temporary sqlite database (`/tmp/candidate3_independent_validation.sqlite3`,
deleted after the run) were used so this validation could exercise the real application code
without touching any persistent or shared state. The API key was read from the calling shell's
environment and never printed, logged, or written by this script.

## Executable path trace (real call into `policy_enforcement.apply_policies_for_review`, the exact function `main.py` calls)

A single, freshly-authored test document (not part of the independent corpus, not from any
burned corpus) touching 5 clause types was submitted to a playbook with ACTIVE
`PolicyPosition`s for all 12 clause types:

```
mode dispatched: cutover
policy_decisions present: True
policy_revision_metadata present: True
interaction_decisions present (proves cutover branch, not shadow): True

Per-clause-type decisions reached:
  limitation_of_liability: ESCALATE
  indemnification: REQUIRES_REVIEW
  termination: NOT_APPLICABLE
  confidentiality: REQUIRES_REVIEW
  assignment: NOT_APPLICABLE
  governing_law: NEGOTIATE
  data_security: REQUIRES_REVIEW
  ip_ownership: NOT_APPLICABLE
  insurance: NOT_APPLICABLE
  payment_terms: ACCEPT
  warranties: NOT_APPLICABLE
  sla: NOT_APPLICABLE

Interaction engine decisions reached:
  IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY: INSUFFICIENT_FACTS
  IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH: INSUFFICIENT_FACTS
  IX_INDEMNITY_WITHIN_GENERAL_CAP: INSUFFICIENT_FACTS
  IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY: INSUFFICIENT_FACTS
  IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE: INSUFFICIENT_FACTS
  IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING: INSUFFICIENT_FACTS
  IX_SLA_PAYMENT_CREDIT_DEPENDENCY: INSUFFICIENT_FACTS

Aggregated authoritative document_state (with overall_risk forced to 'low'): HAS_POLICY_VIOLATION
```

This confirms the executable path genuinely reaches: extraction → normalization → real AI
contextual discovery (the ESCALATE/REQUIRES_REVIEW/NEGOTIATE decisions above required real
OpenAI calls to reach, confirmed by the `OpenAI client initialized successfully` log line and
by the liability decision correctly recognizing the document's gross-negligence exception via
the Blocker-2-fixed category classifier) → deterministic grounding → canonical fact admission
→ all 12 adapters → the interaction engine (correctly declining to fabricate a finding given
unsafe participants) → aggregated authoritative document state, which correctly overrides a
forced-`"low"` legacy `overall_risk` to `HAS_POLICY_VIOLATION` (Blocker 5's fix proven live, not
just by code inspection).

**Cutover was genuinely reached. Validation is not invalidated at this phase.**
