CANDIDATE 4 — PHASE 14: AUTHORITY SURFACES

Confirmed via `git diff d2820362 HEAD -- document_aggregation.py main.py review_workflow.py templates/` (empty output): none of the shared aggregation code (`document_aggregation.aggregate_document_state`) or its wiring into `results.html`, the PDF builder, the negotiation-package cover memo, or `shared_report.html` was touched during this mission. This mission's changes are confined to three adapters' `extract_*_facts`/`evaluate_*_policy` functions (`insurance_policy_engine.py`, `data_security_policy_engine.py`, `ip_ownership_policy_engine.py`) plus one benchmark-corpus expectation update and new tests.

Each of these three adapters' `PolicyDecision.state` (the per-clause-type
decision that feeds `policy_decisions` into `aggregate_document_state`) is
now, if anything, MORE likely to report `REQUIRES_REVIEW` in the specific
cases this mission targeted (operative-but-unresolved content), never
LESS likely to report a non-clean state. Since `aggregate_document_state`
treats `REQUIRES_REVIEW`/any non-ACCEPT policy decision as contributing to
`HAS_POLICY_VIOLATION`/`REQUIRES_REVIEW` document states (unchanged
precedence logic), this mission's fixes can only ever make the
aggregated authoritative document state MORE conservative for the
affected adapters, never less — so the Candidate 3 Phase 7 authority-
surface consistency finding (the same `document_state` reaches every
customer-facing surface without disagreement, because they all read the
identical wrapper function) continues to hold without re-verification of
every individual surface, since the shared wrapper and every call site are
byte-for-byte unchanged.

`AUTHORITY SURFACE CONSISTENCY: CONSISTENT` (unchanged from Candidate 3;
re-confirmed structurally, not re-tested per-surface this mission, since
no code on that path changed).
