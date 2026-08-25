# AUTHORITY_BOUNDARY — re-verified for the final trust architecture

Core rule: **AI understands/proposes. Evidence grounds. Deterministic
code admits facts. Deterministic policy engines decide. Uncertainty goes
to human review. AI must never directly produce ACCEPT / ACCEPT_WITH_NOTE
/ NEGOTIATE / MUST_REDLINE / PROHIBITED / ESCALATE.**

This is the same invariant documented in
`artifacts/fact_admission_architecture/AUTHORITY_BOUNDARY.md`. Re-verified
in this pass, not re-derived from scratch — every mechanism cited there
was re-checked present in current code during Phase 0:

1. `fact_admission.CandidateMaterialFact`'s forbidden-field guard
   (`_FORBIDDEN_FIELD_NAMES`, `assert_authority_boundary_intact()`) —
   confirmed present, unchanged.
2. `fact_admission.py`'s output vocabulary contains no
   `policy_engine_core` decision state — confirmed by re-reading the full
   module; the new `semantic_discovery_enabled()` function added this
   session returns only `bool`, adding no new vocabulary.
3. Every adapter's admitted candidate only ever seeds a pre-existing
   deterministic structuring function (never bypasses it) — confirmed for
   all 11 newly-integrated adapters in the prior branch's per-adapter
   commits; not re-derived line-by-line again here, but the adapter files
   were not touched by this session's Phase 12 change beyond the flag
   initialization line, so this property is unaffected.
4. `interaction_engine_core.py` and `document_aggregation.py` — untouched
   by both branches; their pre-existing fail-closed behavior is a
   property of code this mission's Phase 0 re-confirmed is still wired in
   (see PRE_IMPLEMENTATION_MAP.md's interaction-engine finding).

## What is new in this pass

`fact_admission.semantic_discovery_enabled()` is a pure environment
predicate — it reads `os.environ`, does string comparison, and returns
`bool`. It has no access to contract text, no network call, and cannot
itself produce a candidate fact or a decision. It sits strictly outside
the authority boundary: it only ever answers "should the semantic
pathway run at all," never "what did it find" or "what should happen."

## Unresolved boundary question surfaced by Phase 0

The authority boundary inside `fact_admission.py` and each adapter is
sound. The **mode boundary** one layer up — `POLICY_ENFORCEMENT_MODE`
choosing between the legacy liability-only path and the full modern
engine — is a different kind of boundary, and this session found it is
not itself hardened against a misconfiguration silently reverting to a
less protective state: if `POLICY_ENFORCEMENT_MODE` is unset or
misspelled in a deployment, `get_enforcement_mode()` silently defaults to
`"shadow"`, and the user sees only the legacy liability-only result with
no error or warning surfaced anywhere in this session's investigation.
This is a **pre-existing** property (not introduced by either branch),
but it is directly relevant to Phase 16's cutover discussion and is
recorded in RESIDUAL_RISK_REGISTER.md rather than left as a silent
assumption.
