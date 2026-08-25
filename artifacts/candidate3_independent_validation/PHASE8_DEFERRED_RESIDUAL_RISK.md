PHASE 8 — DEFERRED RESIDUAL RISK

**`ip_ownership-080` is retained as: KNOWN PRE-EXISTING RESIDUAL RISK — DEFERRED BY PRODUCT
OWNER.** It is NOT classified as fixed in this mission, and this mission takes no action on it.

- It was NOT included in the independent corpus (`corpus/CORPUS_MANIFEST.json`'s contamination
  checks explicitly exclude it, and its exact text was verified absent from the new corpus —
  see the prior mission's contamination check, re-confirmed here).
- No independent-corpus metric was adjusted, excluded, or reweighted because of this deferral —
  the hard-gate counts and pass rates in `PHASE4_HARD_SAFETY_GATES.md` and
  `PHASE5_ADAPTER_MATRIX.md` are exactly as computed, with no manipulation.
- No production code related to `ip_ownership_policy_engine.py`'s admitted-candidate qualifier-
  composition loop (the confirmed root cause) was touched during this mission — confirmed via
  `git status`/`git diff` showing zero production-code changes at any point after the Phase 0
  freeze.

## Did the new independent corpus discover the SAME failure class independently?

The independent corpus's `ip_ownership` cases (55 cases, 9 families) were investigated
specifically for this question. The confirmed hard-gate violations in `ip_ownership` this run
(6 `FALSE_ABSENCE`, 8 `UNRESOLVED_DEFINITION_TO_CLEAN`/`UNRESOLVED_CROSS_REFERENCE_TO_CLEAN`) are
a **DIFFERENT** failure shape from `ip_ownership-080`'s (which is specifically: an ADMITTED
candidate's grounded qualifier composing non-deterministically depending on real-provider
sampling, for text where deterministic `ownership_attributions` was ALREADY fully established).
The independent corpus's `ip_ownership` failures instead stem from AI discovery returning zero
candidates at all for certain ownership-transfer phrasings (a recall miss, not a composition-
variance issue) and from the `FALSE_ABSENCE` family's `conditional` template's less-common
"Title... shall transfer to X upon Y" construction not being recognized by either channel — see
`PHASE4_HARD_SAFETY_GATES.md`'s root-cause section. **No new independent instance of
`ip_ownership-080`'s specific failure class was found in this run** — but this is not itself
grounds for optimism about `ip_ownership` generally, since this run independently found several
OTHER, real hard-gate violations concentrated in the same adapter. Had a new instance of
`ip_ownership-080`'s exact class been found, this report would have flagged it as a new,
independently-discovered hard-gate failure per the mission's explicit instruction — none was.
