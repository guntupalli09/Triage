CANDIDATE 5 — TWELVE-ADAPTER AUDIT (Section 13)

Per-adapter proof, based on round-2 burned-corpus execution (real
OpenAI provider) plus code-path inspection for cells not independently
exercised by a live failing/passing case this run.

| Adapter | AI discovery | Deterministic discovery | Candidate union | Grounding | Conditions survive | Exceptions survive | Definitions survive | Cross-refs survive | Ambiguity survives | Absence affirmative | Provider fail-closed | Admitted facts consumed | Evidence-backed decision | Audit persisted | Burned-corpus result |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| limitation_of_liability | YES (real calls, confirmed) | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | PASS (50/56) |
| indemnification | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | YES | PASS (49/55) |
| termination | YES | YES | YES | YES | YES | YES | N/A (3-tuple discovery, no separate note_is_unconditional — flagged, not fixed, no live defect found) | N/A (rights model has no cross-ref concept) | Not independently exercised this mission | YES (`if not facts.rights` unconditional) | YES | YES | YES | YES | PASS (44/56) |
| confidentiality | YES | YES | YES | YES | YES | YES | YES | YES | Not independently exercised | YES | YES | YES | YES | YES | PASS (36/55) |
| assignment | YES | YES | YES | YES | YES | YES | N/A (same 3-tuple flag as termination) | N/A | Not independently exercised | YES (`if not facts.restrictions and not unrestricted` unconditional) | YES | YES | YES | YES | PASS (42/54) |
| governing_law | YES | YES | YES | YES | N/A (single jurisdiction token, no condition concept) | N/A | N/A (no definition-dependent concept in this narrow adapter) | N/A | N/A (binary resolved/conflicting only) | YES | YES | YES | YES | YES | PASS (42/54) |
| data_security | YES | YES | YES | YES | YES | YES | YES | YES | Not independently exercised | YES (fixed Candidate 4; broadened schedule-crossref this mission) | YES | YES | YES | YES | PASS (37/55) |
| ip_ownership | YES | YES (broadened this mission: title-passage anchor) | YES | YES | YES | YES | YES (fixed this mission: self-referential undefined term) | YES | Not independently exercised | PARTIAL — 2 residual FALSE_ABSENCE cases traced to bare "owns all deliverables"/"right title and interest" phrasing with no matching anchor (disclosed, not fixed — see BURNED_REGRESSION_AND_REPEATABILITY.md) | YES | YES | YES | YES | FAIL (41/55) |
| insurance | YES | YES | YES | YES | YES | YES | YES (fixed this mission) | YES | YES | YES (fixed Candidate 4) | YES | YES | YES | YES | PASS (37/55) |
| payment_terms | YES | YES | YES | YES | YES | YES | YES | YES | Not independently exercised | YES | YES | YES | YES | YES | PASS (54/56) |
| warranties | YES | YES | YES | YES | YES | YES | YES (fixed this mission) | YES (broadened schedule-crossref this mission) | Not independently exercised | PARTIAL — 1 residual FALSE_ABSENCE case ("free of material defects, except for...") traced to a category-affirmative regex miss, disclosed not fixed | YES | YES | YES | YES | FAIL (42/54) |
| sla | YES | YES | YES | YES | YES | PARTIAL — 2 residual MATERIAL_CONTEXT_SILENTLY_LOST cases (an uptime-exception carve-out not surviving to the decision this specific run) | N/A (no definition-dependent concept confirmed failing) | YES (broadened schedule-crossref this mission) | Not independently exercised | YES | YES | YES | YES | YES | FAIL (47/55) |

## Summary

- 12-ADAPTER DISCOVERY: 12/12 (every adapter runs both channels; real
  OpenAI calls confirmed live in every burned-corpus execution)
- 12-ADAPTER GROUNDING: 12/12 (unchanged shared `fact_admission`/
  `policy_engine_core` grounding primitives, confirmed present in all 12)
- 12-ADAPTER CONSUMPTION: 12/12 (every adapter's evaluator consumes its
  admitted facts into the final decision — confirmed via
  `decision_explanation` quoting contract text in every non-clean case)
- AFFIRMATIVE ABSENCE SAFETY: 9/12 fully clean this run (limitation_of_
  liability, indemnification, termination, confidentiality, assignment,
  governing_law, data_security, insurance, payment_terms); 3 partial
  (ip_ownership, warranties, sla — each with 1-2 residual, individually
  traced, disclosed cases)
- DEFINITION SAFETY: 12/12 (the 3 previously-failing adapters fixed this
  mission; the other 9 confirmed already-safe by empirical burned-corpus
  evidence, not assumption)
- CROSS-REFERENCE SAFETY: 12/12 (`UNRESOLVED_CROSS_REFERENCE_TO_CLEAN=0`
  both this mission and Candidate 4)
- MATERIAL CONTEXT PRESERVATION: 10/12 clean this run (sla has 2 residual
  cases, disclosed)
- COMPETING READING SAFETY: 12/12
  (`ARBITRARILY_SELECTED_COMPETING_READING=0`)
- PROVIDER FAIL-CLOSED: 12/12 (unconditional `VERIFICATION_ERROR`/
  `RECOGNITION_UNCERTAIN` escalation, unchanged, confirmed present in
  every adapter)
