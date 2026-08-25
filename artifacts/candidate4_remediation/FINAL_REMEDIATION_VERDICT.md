CANDIDATE 4 — INDEPENDENT-CORPUS FAILURE-CLASS REMEDIATION — FINAL VERDICT

Full evidence package in `artifacts/candidate4_remediation/`:
`ROOT_CAUSE_MAP.md`, `EVIDENCE_STATE_MACHINE.md`, `ADAPTER_SYMMETRY_MATRIX.md`,
`PHASE10_11_REAL_PROVIDER.md`, `PHASE11_REPEATABILITY.md`,
`PHASE12_BURNED_REGRESSION.md`, `PHASE13_INTERACTION_ENGINE.md`,
`PHASE14_AUTHORITY_SURFACES.md`, `PHASE15_FULL_REGRESSION.md`, plus raw
evidence (`burned_regression_raw_results.jsonl`, `repeatability_results.json`,
`phase13_result.json`, `burned_regression_analysis.json`) and the scripts
that produced them.

## Summary of what this mission did

Diagnosed and fixed ONE generalized failure class (ROOT_CAUSE_MAP.md
Cluster 1/2): three adapters (`insurance`, `data_security`, `ip_ownership`)
silently defaulted a genuinely operative-but-unresolved deterministic
anchor match to `CONFIRMED_ABSENT` whenever AI discovery independently
returned nothing — the exact mechanism behind Candidate 3's
`UNVERIFIED_FEEDING_CLEAN` (33) and part of its `FALSE_ABSENCE` (9). Fixed
by broadening the reclassification trigger and reordering it to run after
each adapter's per-dimension policy comparison (so existing, more
specific MUST_REDLINE/NEGOTIATE findings are never downgraded). Audited
all 12 adapters (`ADAPTER_SYMMETRY_MATRIX.md`); confirmed the other 9
already had an equivalent fail-closed gate and did not need code changes.
Added 10 adversarial tests, each burned-corpus-inspired fix paired with a
materially different fresh variant, per the anti-memorization requirement.
`ip_ownership-080` remains untouched and deferred, unchanged.

## Pass-rule checklist

| Requirement | Status |
|---|---|
| All 12 adapters obey the authority invariants | **PARTIAL** — 3 adapters fixed and verified; 9 audited and confirmed already-safe by code-path inspection (see ADAPTER_SYMMETRY_MATRIX.md's disclosed audit-depth limitations) |
| All 8 burned-corpus hard gates = 0 | **NO** — 4 of 8 remain non-zero (see below) |
| Real-provider repeatability has zero unsafe clean-state variance | **NO** — 2 of 240 executions (48 cases × 5) showed unsafe CLEAN↔NONCLEAN variance, both confirmed pre-existing (not introduced by this mission) |
| Provider failures fail closed | **YES** — unchanged, unconditional `VERIFICATION_ERROR`/`RECOGNITION_UNCERTAIN` escalation confirmed present in all 12 adapters |
| Interaction engine propagates uncertainty | **YES** — re-verified live (Phase 13): all 7 rules return `INSUFFICIENT_FACTS` across all 3 composite scenarios |
| All authority surfaces agree | **YES** — confirmed unchanged (Phase 14): zero diff in `document_aggregation.py`/`main.py`/`review_workflow.py`/templates |
| Full regression introduces zero new failures | **YES** — 215/2108/14/6 vs. baseline 215/2108/14/7 (Phase 15) |
| No production activation/configuration was changed | **YES** — `FACT_ADMISSION_MODE`/`POLICY_ENFORCEMENT_MODE` production defaults untouched; no Vercel change; no deploy; no merge |

**Per this mission's own Section 21 rule, ANY failing requirement forces
`READY TO FREEZE CANDIDATE 4 = NO`. Two independent requirements fail
here (hard gates, repeatability), so this is unambiguous.**

---

CANDIDATE 4 COMMIT:
`92991f9` (working tree at time of this verdict; production-code changes
specifically at `96e0500`)

ROOT CAUSES IDENTIFIED:
1 generalized root cause (ROOT_CAUSE_MAP.md Cluster 1: operative
deterministic anchor + AI-discovery recall miss silently defaults to
CONFIRMED_ABSENT), with 1 associated precision-preserving restructuring
(Cluster 2: fallback ordering relative to per-dimension comparisons),
affecting 3 of 12 adapters (insurance, data_security, ip_ownership).

SHARED EVIDENCE STATE MODEL:
PASS — existing states (`fact_admission`'s verification-state vocabulary
plus each adapter's `absence_state` field) already cover the mission's
requested semantics; no new enum needed. UNKNOWN→ABSENT and
UNRESOLVED→CLEAN collapses were confirmed eliminated for the 3 fixed
adapters via live tests; confirmed structurally absent in the other 9.

AI CONTEXTUAL ANALYSIS:
12/12 (unchanged architecture; real OpenAI provider exercised throughout
this mission's testing, never mocked)

DETERMINISTIC GROUNDING:
12/12 (unchanged shared `fact_admission`/`policy_engine_core` primitives)

ADAPTER CONSUMPTION:
12/12 (confirmed via ADAPTER_SYMMETRY_MATRIX.md — every adapter consumes
admitted evidence into its decision; not merely discovered and discarded)

ABSENCE SAFETY:
9/12 verified safe against this mission's specific failure class (3
fixed this mission, 6 confirmed already-safe by code inspection); 3
(termination, assignment via a documented but non-live-defect 3-tuple
`_run_semantic_discovery` gap) flagged with a disclosed, non-blocking
consistency note

DEFINITION SAFETY:
11/12 confirmed safe (unconditional bypass present); `UNRESOLVED_
DEFINITION_TO_CLEAN` remains non-zero (17) in the burned-corpus run —
NOT because a resolved definition is dropped, but because the
CANDIDATE carrying it is never admitted in the first place for specific
`ip_ownership`/`insurance`/`warranties` phrasings (an admission-recall
issue, not a definition-composition issue — see PHASE12_BURNED_REGRESSION.md)

CROSS-REFERENCE SAFETY:
12/12 on this run — `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN` reached 0 (down
from 9), directly attributable to this mission's fix

MATERIAL CONTEXT PRESERVATION:
9/12 clean on this run (`MATERIAL_CONTEXT_SILENTLY_LOST`=4, concentrated
in termination/assignment/sla — adapters this mission did not modify;
pre-existing, not newly introduced)

COMPETING-READING SAFETY:
12/12 on this run — `ARBITRARILY_SELECTED_COMPETING_READING` reached 0
(down from 6), directly attributable to this mission's fix

PROVIDER FAIL-CLOSED:
12/12 (unconditional `VERIFICATION_ERROR` escalation, unchanged and
confirmed present in every adapter)

INTERACTION ENGINE:
PASS (Phase 13 — fail-closed behavior re-confirmed live)

AUTHORITY SURFACES:
PASS (Phase 14 — confirmed unchanged/consistent)

REAL PROVIDER:
PASS (never mocked; real OpenAI exercised throughout Phases 10-13)

REPEATABILITY:
46/48 stable (240 total executions)
UNSAFE CLEAN-STATE VARIANCE: 2

BURNED 660-CASE REGRESSION:

FALSE_SAFE:
0

FALSE_OPERATIVE_TO_CLEAN:
0

UNVERIFIED_FEEDING_CLEAN:
6 (down from 33)

FALSE_ABSENCE:
11 (up from 9 — see PHASE12_BURNED_REGRESSION.md's honest root-cause
explanation: dominated by a real-provider admission-non-determinism
class this mission's fix does not reach, confirmed via Phase 11)

MATERIAL_CONTEXT_SILENTLY_LOST:
4 (up from 3 — pre-existing, in adapters this mission did not modify)

ARBITRARILY_SELECTED_COMPETING_READING:
0 (down from 6)

UNRESOLVED_CROSS_REFERENCE_TO_CLEAN:
0 (down from 9)

UNRESOLVED_DEFINITION_TO_CLEAN:
17 (unchanged)

FULL REGRESSION:
215 failed, 2108 passed, 14 skipped, 6 errors (vs. baseline 215/2108/14/7
— see PHASE15_FULL_REGRESSION.md)

NEW REGRESSIONS:
0

PRODUCTION CONFIG CHANGED:
NO

DEPLOYED:
NO

NEW INDEPENDENT CORPUS CREATED:
NO

FINAL REMEDIATION VERDICT:
FAIL

READY TO FREEZE CANDIDATE 4:
NO

## Why, in plain terms

This mission made real, verifiable, honestly-measured progress: 2 of the
6 previously-failing hard gates were fully closed (`ARBITRARILY_
SELECTED_COMPETING_READING`, `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN`), a
third was cut by 82% (`UNVERIFIED_FEEDING_CLEAN`, 33→6), the two
non-negotiable gates stayed at zero throughout every phase, `data_
security` moved from FAIL to PASS on the adapter matrix, and repeatability
testing directly proved the remaining instability (`FALSE_ABSENCE`,
`UNRESOLVED_DEFINITION_TO_CLEAN`) is a genuine, pre-existing real-provider
admission non-determinism for text with no deterministic anchor at all —
not a defect this mission's own code changes introduced or could
responsibly hide.

But the mission's own bar is "ALL EIGHT hard gates = 0" and "UNSAFE
CLEAN-STATE VARIANCE = 0," and neither is met. Per Section 21's explicit
instruction — "if ANY requirement fails: READY TO FREEZE CANDIDATE 4 =
NO. Stop. Do not create another corpus. Do not deploy. Do not weaken the
gate. Do not reinterpret a nonzero safety gate as acceptable." — this
verdict is FAIL, and no further action beyond this evidence package is
taken. No Vercel variable was changed, nothing was merged, nothing was
deployed, and no new independent corpus was created. This mission's work
is a genuine step toward Candidate 4, not a claim that Candidate 4 is
ready.
