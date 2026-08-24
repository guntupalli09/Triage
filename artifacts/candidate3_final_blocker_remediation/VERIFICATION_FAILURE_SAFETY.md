BLOCKER 1 — VERIFICATION_ERROR MUST FAIL CLOSED

## Complete verification-state vocabulary (derived from executable code, `fact_admission.py`)

```python
_VERIFICATION_STATES = {
    ESTABLISHED, NOT_ESTABLISHED, AMBIGUOUS, INSUFFICIENT_CONTEXT,
    CONFLICTING, DEPENDENCY_UNRESOLVED, VERIFICATION_ERROR,
}
_UNSAFE_VERIFICATION_STATES = _VERIFICATION_STATES - {ESTABLISHED}  # 6 states
```

There is no separate `PROVIDER_UNAVAILABLE`/`TIMEOUT`/`MALFORMED_RESPONSE`/`EMPTY_RESPONSE`/
`UNGROUNDED` status in this codebase — every provider/network/timeout/malformed-JSON failure
inside `verify_candidate_proposition` is caught and converted to `VERIFICATION_ERROR`
(confirmed by direct code reading of `fact_admission.py`'s exception handling). "Ungrounded"
is a separate concept entirely — `GroundingResult.passed`, not a verification status.

| Status | SAFE TO IGNORE? | MUST PROPAGATE? | MUST BLOCK CLEAN? |
|---|---|---|---|
| ESTABLISHED | — (only status that can admit) | N/A | N/A |
| NOT_ESTABLISHED | No | Yes, corroboration-gated | Yes, when corroborated |
| AMBIGUOUS | No | Yes, corroboration-gated | Yes, when corroborated |
| INSUFFICIENT_CONTEXT | No | Yes, corroboration-gated | Yes, when corroborated |
| CONFLICTING | No | Yes, corroboration-gated | Yes, when corroborated |
| DEPENDENCY_UNRESOLVED | No | Yes, corroboration-gated (newly added) | Yes, when corroborated |
| VERIFICATION_ERROR | No | Yes, UNCONDITIONAL (newly added) | Yes, unconditionally |

## The fix

`fact_admission._classify_unresolved_dependency_note` (the refactored, shared core of
`first_unresolved_dependency_note`) now asserts its own completeness at runtime:

```python
assert (_CONTENT_UNCERTAIN_VERIFICATION_STATES | _INFRASTRUCTURE_FAILURE_VERIFICATION_STATES
        ) == _UNSAFE_VERIFICATION_STATES, "verification state vocabulary changed without updating this function"
```

Split into two categories:
- **Content-judgment uncertainty** (`NOT_ESTABLISHED`, `AMBIGUOUS`, `INSUFFICIENT_CONTEXT`,
  `CONFLICTING`, `DEPENDENCY_UNRESOLVED`): the verifier examined the text and reached an
  uncertain conclusion. Kept corroboration-gated on `_PARTY_OBLIGATION_ANCHOR_RE` (unchanged
  from the prior mission's fix) — a confident, correct rejection of descriptive text must not
  be second-guessed merely because the status is "uncertain."
- **Infrastructure failure** (`VERIFICATION_ERROR`): the verifier never examined the text at
  all. Escalated **unconditionally** — there is nothing to corroborate against, since no
  judgment about operative-vs-descriptive language was ever reached.

## Adversarial test proof (`tests/test_candidate3_final_blocker_remediation.py`)

- `test_verification_state_vocabulary_is_fully_enumerated` — locks the 7-state vocabulary and
  the assertion that guards against silent vocabulary drift.
- `test_every_unsafe_state_produces_a_note_when_evidence_looks_operative` — parameterized over
  all 6 unsafe states, proves each produces a non-None note.
- `test_verification_error_note_is_unconditional_within_the_shared_function` — proves
  VERIFICATION_ERROR escalates even against a generic, non-operative-looking evidence span.
- `test_A_verification_error_with_deterministic_miss_liability` /
  `test_A_verification_error_with_deterministic_miss_data_security` — the mission's required
  adversarial pattern A (regex miss + verification error) end-to-end through two adapters:
  decision is neither `ACCEPT`/`ACCEPT_WITH_NOTE` nor `NOT_APPLICABLE`.
- `test_B_verification_error_with_deterministic_hit_and_full_establishment_stays_clean` — the
  required pattern B (regex hit, fully established) end-to-end: correctly stays clean, proving
  the fix does not become "escalate everything."

## Result

`PROVIDER FAILURE FAIL-CLOSED: PASS` for the shared mechanism across all 12 adapters that
route through `fact_admission.first_unresolved_dependency_note` (11 mirror adapters directly;
indemnification via its reconciliation channel, see `INDEMNIFICATION_RECONCILIATION.md`).
