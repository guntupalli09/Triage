# UNIFIED_STATE_REPORT

## Current state (re-verified Phase 0)

`document_aggregation.aggregate_document_state()` remains the single
aggregation function, producing one of 6 states
(`HAS_CRITICAL_INTERACTION` > `HAS_POLICY_VIOLATION` > `REQUIRES_REVIEW`
> `CONFIGURATION_UNRESOLVED` > `CLEAN_LEGACY_ATTENTION`/`CLEAN`), wired
into all three user-facing surfaces:

- `/dashboard` (`main.py:1319`, since commit `d6f4875`, pre-existing)
- `/history` (`main.py:1360`, same commit, pre-existing)
- `/contract/{id}/review` (`main.py:2397`, added by the prior branch's
  commit `a8ab2b5` this session's work builds on)

The false-clean invariant ("never report a state calmer than what its
own inputs support") is a property of `document_aggregation.py` itself,
unmodified by either branch.

## What "unified" actually means today, precisely

The three surfaces render the SAME computed state, but they compute it
from `Contract.overall_risk` / `policy_decisions_json` /
`interaction_decisions_json` — three columns that are only populated
richly in `cutover` mode. In `shadow`/`legacy` mode (the default),
`policy_decisions_json` reflects only the legacy liability-only path
(see `apply_liability_policy()`), so `aggregate_document_state()` still
runs and still returns a real answer, but the "unification" is unifying
across a narrower set of actual findings than the mission's Phase 10
architecture diagram implies — extraction failures, the 11 non-liability
adapters' facts, and interaction decisions do not exist yet in that mode
for aggregation to incorporate. This is not a defect introduced by
either branch; it is the same shadow/cutover gating documented in
PRE_IMPLEMENTATION_MAP.md, restated here because it directly bears on
what "one authoritative document state" currently means in the default
deployment configuration.

## Not resolved this session

The mission's Phase 10 explicitly asks to "resolve the authority model,"
not merely wire a badge. This session did not introduce a mechanism to
detect or warn when the deployment is running in `shadow` mode while a
playbook has ACTIVE positions for adapters beyond liability (i.e., a
configuration where a lawyer believes 12-adapter coverage is active but
the mode setting means it is not). This is a real, identified gap — see
RESIDUAL_RISK_REGISTER.md — not attempted in this pass because it
requires a product/UX decision (what should the dashboard show an
operator in that state?) beyond a code-only fix.

## Verdict

**UNIFIED DOCUMENT STATE: PASS** for the narrower claim (the three
surfaces render identically from the same aggregation function, and that
function's own false-clean invariant is intact). **NOT fully resolved**
for the broader claim the mission's Phase 10 makes (a single authority
model regardless of mode) — the mode split remains a real seam.
