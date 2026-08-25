# ADVERSARIAL_TEST_MATRIX

Per-adapter adversarial families actually exercised (mocked provider
responses — see the honesty note in every section below and in
FROZEN_CORPUS_MANIFEST.md: these prove the pipeline's mechanical response
to a given verifier verdict, not that a real model produces that verdict).

| Family | Covered? | Where |
|---|---|---|
| Ordinary operative language → admitted | YES, all 12 adapters | each adapter's `test_verified_semantic_candidate_*` / `test_admitted_candidate_*` |
| Descriptive/industry-background language → NOT admitted | YES, all 11 newly-integrated adapters, one distinct natural sentence per adapter (not the same sentence reused) | each adapter's `test_verifier_not_established_descriptive_language_never_admitted` |
| Hypothetical/example language | NOT separately tested — folded into the general NOT_ESTABLISHED family above rather than a distinct test per adapter | — |
| Quoted third-party language | NOT separately tested | — |
| Drafting instruction / recital / negotiation commentary | NOT separately tested | — |
| Rejected/negated language | NOT separately tested | — |
| Definition-only language | NOT separately tested | — |
| Fabricated/hallucinated evidence | YES, all 12 adapters | each adapter's `test_hallucinated_candidate_never_becomes_*` |
| Provider timeout/network error | YES, shared module level (`fact_admission.py`) | `test_verify_network_error_is_verification_error`, `test_discovery_network_error_raises` |
| Malformed provider JSON | YES, shared module level | `test_verify_malformed_json_is_verification_error` |
| Invalid enum status | YES, shared module level | `test_verify_invalid_enum_status_is_verification_error` |
| Contradictory output (ESTABLISHED with no evidence) | YES, shared module level | `test_verify_established_without_evidence_quote_is_contradictory` |
| Unresolved dependency blocks admission | YES, shared module level | `test_admission_unresolved_dependency_blocks_admission_even_if_established` |
| Unresolved conflict blocks admission | YES, shared module level | `test_admission_unresolved_conflict_blocks_admission_even_if_established` |
| Deterministic structuring still gates an admitted candidate | YES, several adapters explicitly (liability, confidentiality, termination, governing_law, assignment) — an admitted-but-unparseable candidate correctly lands on REQUIRES_REVIEW | see e.g. `test_admitted_candidate_still_requires_deterministic_structuring` |
| Deterministic replay (same facts → same decision) | YES, liability only | `test_admitted_fact_produces_deterministic_replay_decision` |
| Prompt injection in document text | NOT tested this session — indemnification's own prior suite (`test_step4a9_2_real_provider_adversarial.py`) covers this for its own pathway; not re-tested for the 11 newly-integrated adapters' shared-framework path in this session |
| Cross-policy interaction disagreement | NOT tested this session — `interaction_engine_core.py`'s own pre-existing suite covers the mechanism in isolation, not combined with the new semantic paths |
| Dependency/schedule-exhibit-unavailable failures | Covered generically by the `DEPENDENCY_UNRESOLVED`/`has_unresolved_dependency` gate at the shared-module level; not adapter-specifically tested with a real schedule/exhibit scenario |

## Honest assessment

This matrix is **narrower than the mission's Phase 6 requirement**, which
asks for materially distinct adversarial families (hypothetical, example,
quoted, drafting instruction, recital, rejected, negated, definition-only,
etc.) tested per adapter. What exists today tests the single
NOT_ESTABLISHED outcome broadly (proving the pipeline correctly refuses
admission whenever the verifier says NOT_ESTABLISHED, for any reason) but
does not exercise a distinct mocked response for each named category per
adapter. Building that out to the mission's full specification (12
adapters × ~10 adversarial families each) was not completed in this
session — flagged here rather than represented as done.
