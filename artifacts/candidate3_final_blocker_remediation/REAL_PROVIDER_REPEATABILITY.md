PHASE 9 — REAL-PROVIDER REPEATABILITY

52 cases × 5 identical executions = 260 real OpenAI calls per run, two runs performed (before
and after the indemnification second-order fix). The prior 51-case set was used unmodified
plus one addition: `dev-indemnification-006-class-01`, a fresh, non-burned-corpus
indemnification case mirroring `limitation_of_liability-006`'s exact shape (monetary and
scope both genuinely established, plus a same-clause carve-out), added per the mission's
explicit instruction to represent an indemnification analogue of the liability failure shape.
`INDEMNIFICATION_RECONCILIATION_ENABLED` was turned on for this run so it actually exercises
Blocker 3's fix (previously off, meaning prior repeatability runs never touched this channel).

Historical failure classes represented and their status this run:
- `data_security-139`: not in this run's 52-case selection by name, but the general failure
  class it represents (uncertain verification + deterministic anchor present) is covered by
  this mission's own targeted adversarial tests (pattern A/B/C/D) with fresh wording, per the
  standing "no burned-corpus fixture copying" discipline. `data_security-120` (a different
  case exercising the same `PRESENT_BUT_UNRESOLVED` mechanism) appears in this run's selection
  and was stable across all 5 runs.
- `ip_ownership-080`: present in the selection, **UNSTABLE this run** — see below.
- `ip_ownership-086`: present (as `dev-ipownership-086-class-01`), stable 5/5.
- `limitation_of_liability-006`: not itself in the repeatability selection this run (it was in
  the burned corpus, replayed separately in Phase 8), but its general failure class is
  directly covered by `test_B_verification_error_with_deterministic_hit_and_full_
  establishment_stays_clean` and `test_D_irrelevant_uncertain_signal_suppressed_when_fact_
  fully_established` in the targeted adversarial suite, plus the new
  `dev-indemnification-006-class-01` indemnification analogue.

## Run 1 (Layer-1 indemnification fix only)

```
52 cases x 5 runs = 260 real calls attempted. AI_CANDIDATE_SET_VARIED: 13/52.
CANONICAL_FACT_VARIED: 3/52. POLICY_DECISION_VARIED: 5/52.
PROVIDER_INDUCED_CLEAN_STATE_VARIANCE (unsafe transitions): 2/52 (must be 0).
```
Unsafe transitions found: `ip_ownership-080` (ACCEPT↔REQUIRES_REVIEW) and
`dev-indemnification-006-class-01` (REQUIRES_REVIEW↔ACCEPT_WITH_NOTE, 4:1 split). The
indemnification instance was diagnosed as a second-order gap in the Layer-1 fix (see
`INDEMNIFICATION_RECONCILIATION.md`) and fixed (Layer 2).

## Run 2 (after the Layer-2 indemnification fix)

```
52 cases x 5 runs = 260 real calls attempted. AI_CANDIDATE_SET_VARIED: 10/52.
CANONICAL_FACT_VARIED: 3/52. POLICY_DECISION_VARIED: 4/52.
PROVIDER_INDUCED_CLEAN_STATE_VARIANCE (unsafe transitions): 1/52 (must be 0).
```
`dev-indemnification-006-class-01`: now 5/5 stable `REQUIRES_REVIEW`. The sole remaining
unsafe transition is `ip_ownership-080` (3× `REQUIRES_REVIEW`, 1× `ACCEPT`, 1×
`REQUIRES_REVIEW`), confirmed (see `TWELVE_ADAPTER_PROOF_MATRIX.md` and
`ROOT_CAUSE_REPORT.md`) to be a genuinely new, pre-existing failure class outside the scope of
this mission's five authorized blockers, and therefore intentionally not fixed.

## Result

`UNSAFE CLEAN-STATE TRANSITIONS = 1/52` (required 0). Provider output variance itself is
expected and was observed on both runs (candidate-set and canonical-fact variance are not
themselves unsafe — they reflect genuine real-provider non-determinism, correctly contained
by the architecture in 51 of 52 cases). This one confirmed exception is documented, not
silently accepted, and drives the mission's final verdict — see
`FINAL_REMEDIATION_VERDICT.md`.
