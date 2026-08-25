# TARGETED_RESULTS

All counts independently reproducible via:
`python3 -m pytest tests/test_fact_admission.py tests/test_*_fact_admission.py -q`

| Suite | Tests | Result |
|---|---|---|
| `test_fact_admission.py` (shared framework) | 39 | PASS |
| `test_liability_fact_admission.py` | 8 (7 + 1 determinism/replay) | PASS |
| `test_confidentiality_fact_admission.py` | 7 | PASS |
| `test_data_security_fact_admission.py` | 7 | PASS |
| `test_ip_ownership_fact_admission.py` | 7 | PASS |
| `test_insurance_fact_admission.py` | 7 | PASS |
| `test_payment_terms_fact_admission.py` | 7 | PASS |
| `test_termination_fact_admission.py` | 7 | PASS |
| `test_warranties_fact_admission.py` | 7 | PASS |
| `test_sla_fact_admission.py` | 7 | PASS |
| `test_governing_law_fact_admission.py` | 7 | PASS |
| `test_assignment_fact_admission.py` | 7 | PASS |
| **Total** | **117** | **117 PASS, 0 FAIL** |

## Hard-gate spot checks (mocked, exercised directly in the above suites)

- Provider missing-key / network-error / malformed-JSON / empty-response /
  invalid-enum-status: every mode resolves to `VERIFICATION_ERROR` →
  `NOT_ADMITTED` → adapter's `RECOGNITION_UNCERTAIN` → `REQUIRES_REVIEW`.
  Verified for the shared module directly and for all 11 adapters via
  their `test_provider_unavailable_is_recognition_uncertain` /
  `test_recognition_uncertain_routes_to_requires_review*` pairs. **0 cases
  reached ACCEPT or NOT_APPLICABLE.**
- Fabricated/hallucinated evidence (a verifier claiming `ESTABLISHED` with
  a quote not present in the source text): caught by grounding in every
  adapter's `test_hallucinated_candidate_never_becomes_a_*` test. **0
  cases reached admission.**
- Descriptive/background/industry-standard language (the Step 15 general
  failure class, one naturally-varied instance per adapter, not the same
  sentence repeated): caught by the adversarial verifier returning
  `NOT_ESTABLISHED` in every adapter's `test_verifier_not_established_
  descriptive_language_never_admitted` test. **0 cases reached admission.**
  Important honesty note (see RESIDUAL_RISK_REGISTER.md): because these
  tests mock the verifier's *response*, they prove the pipeline correctly
  refuses to admit whatever a verifier labels `NOT_ESTABLISHED` — they do
  NOT prove a real model would actually label these particular sentences
  `NOT_ESTABLISHED` in practice. That requires live-model evidence (Step
  4A.9.2-style), which was not run for these 11 adapters in this pass.
- AI-authored policy decision: structurally impossible in every adapter —
  `fact_admission.py`'s output vocabulary contains no `policy_engine_core`
  decision state (see AUTHORITY_BOUNDARY.md), and every adapter's semantic
  path only ever seeds an existing deterministic structuring function,
  verified per-adapter by the `test_admitted_candidate_still_requires_
  deterministic_structuring` / equivalent test showing an admitted-but-
  unparseable candidate still lands on `REQUIRES_REVIEW`, never a
  fabricated decision.

## Interaction engine / document aggregation / replay

- `tests/test_interaction_engine_core.py`: pre-existing suite, unaffected
  by this work (interaction_engine_core.py was not modified), passes.
  Already implements Step 9's fail-closed participant gating (see
  PRE_IMPLEMENTATION_MAP.md §4/§7) — verified pre-existing, not re-derived.
- `document_aggregation.py`: no dedicated unit-test file exists in this
  repo (its own benchmark lives in `artifacts/step4b/`, not `tests/`);
  the review-page wiring added this session (`main.py`'s
  `_document_state_for_contract` call in `review_contract`) has no
  automated test in this pass — verified only by Jinja2 template parsing
  and manual code review (see commit `a8ab2b5`). **Gap, not closed.**
- Deterministic replay: `test_liability_fact_admission.py::
  test_admitted_fact_produces_deterministic_replay_decision` — 5 repeated
  `evaluate_liability_policy()` calls against one admitted-fact object
  produce a byte-identical `PolicyDecision` hash. Not repeated for the
  other 10 adapters in this pass (liability chosen as the reference case;
  the underlying mechanism — `policy_engine_core.decision_hash`/
  `check_deterministic` — is adapter-agnostic and pre-existing).
