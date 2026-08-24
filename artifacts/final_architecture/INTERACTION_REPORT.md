# INTERACTION_REPORT

## Wiring (re-verified Phase 0)

`interaction_engine_core.py` is called from exactly one place in
production: `policy_enforcement.py:793`, inside the `mode == "cutover"`
branch of `apply_policies_for_review()`, via
`interaction_enforcement.apply_interaction_rules(outcomes, findings_dict)`.
It is never called in `legacy` or `shadow` mode. Neither branch (this
session or the prior one) modified `interaction_engine_core.py`,
`interaction_enforcement.py`, or `interaction_rules.py`.

## Fail-closed behavior (pre-existing, re-verified)

`interaction_engine_core._gate_participants()` requires every
participating clause type to have a `PolicyDecision` in a safe state
(`state not in {NOT_APPLICABLE, REQUIRES_REVIEW, EVALUATION_ERROR}`)
before a cross-clause rule is evaluated; any unsafe/missing participant
produces `INSUFFICIENT_FACTS` for that rule, never a fabricated or
defaulted evaluation. Confirmed present, unmodified, `tests/
test_interaction_engine_core.py` passes unchanged in this session's
regression run.

## What this session verified that matters for interactions specifically

Because 7 of the 11 newly-integrated adapters needed a NEW explicit
`RECOGNITION_UNCERTAIN` → `REQUIRES_REVIEW` branch (per the prior
session's finding that their existing "nothing structured" path could
otherwise reach `ACCEPT` under a permissive playbook), this session's
work directly improves what `_gate_participants()` sees: before the
prior branch's work, a semantic-layer failure on those 7 adapters could
have produced an `ACCEPT`-shaped decision that `_gate_participants()`
would have treated as SAFE to reason over (since `ACCEPT` is not in
`_UNSAFE_PARTICIPANT_STATES`) — even though the underlying fact was
never actually established. That risk is now closed for those 7
adapters specifically, since the explicit branch prevents the
`ACCEPT`-shaped output from ever being produced from an uncertain state
in the first place.

## Not tested this session

- No test constructs a live interaction scenario where one participant's
  `PolicyDecision` came from an admitted semantic candidate (as opposed
  to a purely regex-sourced one) and confirms `interaction_engine_core`
  treats it identically. By construction this should be true (both
  produce the same `PolicyDecision` object shape), but it is asserted by
  code-path argument here, not by a direct test.
- No test exercises `interaction_engine_core.evaluate()` together with
  `POLICY_ENFORCEMENT_MODE=cutover` end-to-end through `main.py`'s
  upload/review routes (blocked in this sandbox by missing `fastapi` —
  see REGRESSION note in the prior branch's `REGRESSION_REPORT.md`,
  still true this session).

## Verdict

**INTERACTION ENGINE: PASS** at the unit/mechanism level (pre-existing,
re-verified, unmodified, unweakened). **NOT independently re-validated
end-to-end with the new fact-admission paths live** in this session.
