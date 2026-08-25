CANDIDATE 5 — CUSTOMER-OUTCOME TRUST ARCHITECTURE — FINAL VERDICT

Full evidence package in `artifacts/candidate5_remediation/`:
`BURNED_REGRESSION_AND_REPEATABILITY.md`, `TWELVE_ADAPTER_MATRIX.md`,
`AUDITABILITY_AND_REPLAY.md`, `INTERACTION_AND_AUTHORITY_SURFACES.md`,
plus raw evidence (`burned_regression_raw_results.jsonl` [round 2, final],
`burned_regression_raw_results_round1.jsonl` [round 1, for comparison],
`repeatability_results.json`, `burned_regression_analysis.json`,
`phase14_result.json`) and the scripts that produced them.

## What this mission did

Fixed 2 more generalized root causes, both traced to real, confirmed
burned-corpus failures (never to a speculative or theoretical concern):

1. **UNRESOLVED_DEFINITION_TO_CLEAN (17 -> 0):** all 17 occurrences
   traced to ONE shared pattern across `insurance`/`ip_ownership`/
   `warranties` — a capitalized term used with an explicit "as defined
   in this Agreement"/"as defined herein" self-reference that is never
   actually defined anywhere in the document. Added a shared, precision-
   guarded primitive (`policy_engine_core.self_referential_definition_
   unresolved`) that only fires on a clear self-reference combined with
   the confirmed absence of any recognizable definition clause, wired in
   as an unconditional escalation.

2. **FALSE_ABSENCE (11 -> 3) and UNVERIFIED_FEEDING_CLEAN (6 -> 0):**
   fixed by (a) adding a deterministic anchor to `ip_ownership` for the
   common title-passage construction ("Title... shall transfer/pass/vest
   to X upon Y") that previously named no IP-specific vocabulary at all
   and depended entirely on non-deterministic AI candidate admission
   (directly confirmed via repeatability re-testing before the fix:
   4/5 `NOT_APPLICABLE`, 1/5 `REQUIRES_REVIEW` on identical real-provider
   runs of the same text), and (b) broadening 6 adapters'
   `_SCHEDULE_CROSSREF_RE` patterns (confirmed broken in `warranties`:
   "as set forth in the Warranty Schedule" was missed because the
   pattern required "Schedule" immediately after "the," not "the
   Warranty Schedule") to allow one qualifying word.

Both fixes give AI discovery genuine deterministic-channel redundancy,
per this mission's Section 4 mandate, rather than leaving AI as the sole
channel for these phrasings.

20 new adversarial tests total (10 from this mission's two fix rounds,
10 carried from Candidate 4), each burned-corpus-inspired case paired
with a materially different fresh variant. Full regression suite
unchanged (215/2128/14/6, identical both before and after, confirming
zero new regressions from either round of fixes).

## Pass bar checklist (Section 25)

| Requirement | Status |
|---|---|
| 1. 8/8 hard safety gates = 0 | **NO** — 6/8 are zero; `FALSE_ABSENCE=3`, `MATERIAL_CONTEXT_SILENTLY_LOST=2` remain, both individually traced and disclosed |
| 2. Unsafe authoritative provider variance = 0 | **NO** — 3/240 executions (48 cases × 5), one a genuinely ambiguous descriptive/review boundary case, two in an adapter (`termination`) this mission did not modify (confirmed pre-existing) |
| 3. All 12 adapters consume grounded authoritative evidence safely | **YES** — confirmed (`TWELVE_ADAPTER_MATRIX.md`) |
| 4. Material unresolved definitions/references cannot become clean | **YES** — `UNRESOLVED_DEFINITION_TO_CLEAN=0` and `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN=0`, both confirmed |
| 5. Provider failures cannot become clean through lack of discovery | **PARTIAL** — true for every case this mission specifically targeted (insurance/data_security/ip_ownership's operative-anchor gap, all 3 adapters' definition-dependency gap); NOT yet true for `ip_ownership`'s "owns all deliverables" / "right, title, and interest" phrasing or `warranties`'/`sla`'s remaining 3 disclosed cases, where lack-of-discovery can still combine with genuine AI-admission variance to reach a clean/uncertain outcome |
| 6. Interaction engine propagates uncertainty | **YES** (`INTERACTION_AND_AUTHORITY_SURFACES.md`) |
| 7. Audit record can explain every authoritative result | **YES** (`AUDITABILITY_AND_REPLAY.md`) |
| 8. Historical review can be replayed from persisted/versioned evidence without requiring fresh AI rediscovery | **YES** — confirmed structurally: `apply_policies_for_review` is never invoked by any view/read path, only at upload/re-analysis time; every downstream surface reads the persisted decision |
| 9. Customer-facing authority surfaces agree | **YES** — unchanged, zero diff in the shared aggregation/rendering code |
| 10. Full regression has zero new failures | **YES** — 215/2128/14/6, identical across both fix rounds |

**7 of 10 requirements pass. Per Section 25's own rule (ALL ten must
pass), this is READY TO FREEZE CANDIDATE 5 = NO — but this is a
materially different, much stronger position than Candidate 4's verdict:
6 of 8 hard gates are now zero (up from 2 of 8), the adapter pass rate is
9/12 (up from 6/12), and every remaining gap is individually named,
traced to its exact root cause, and honestly assessed as either "not yet
fixed" (a specific anchor-vocabulary gap) or "a genuine, disclosed,
inherent real-provider admission non-determinism" (never as "acceptable"
or "close enough").**

---

CANDIDATE 5 SHA:
`3a0c4df` (working tree at time of this verdict; production-code changes
at `78e520c` and `b2bfdca`)

ARCHITECTURE:
PASS — the target architecture (parallel candidate discovery -> union ->
contextual analysis -> grounding -> reconciliation -> canonical fact ->
12 adapters -> interaction engine -> authoritative result -> persisted
record -> multiple read surfaces) was already substantially in place from
prior missions; this mission's contribution was closing 2 more general
gaps in the reconciliation layer (absence-affirmation and definition-
dependency handling), not restructuring the architecture itself.

12-ADAPTER DISCOVERY:
12/12

12-ADAPTER GROUNDING:
12/12

12-ADAPTER CONSUMPTION:
12/12

AFFIRMATIVE ABSENCE SAFETY:
9/12 (ip_ownership, warranties, sla partial — see TWELVE_ADAPTER_MATRIX.md)

DEFINITION SAFETY:
12/12

CROSS-REFERENCE SAFETY:
12/12

MATERIAL CONTEXT PRESERVATION:
10/12 (sla has 2 residual cases)

COMPETING READING SAFETY:
12/12

PROVIDER FAIL-CLOSED:
12/12

INTERACTION ENGINE:
PASS

AUDITABILITY:
PASS

HISTORICAL REPLAY:
PASS

AUTHORITY SURFACES:
PASS

REAL OPENAI:
PASS — never mocked; exercised across 2 full 660-case regression rounds
(1,320 real calls) plus 2 repeatability rounds (480 real executions) plus
2 interaction-engine checks

REPEATABILITY:
48 cases × 5 real-provider executions (240 runs)

UNSAFE AUTHORITATIVE VARIANCE:
3

HARMLESS INTERMEDIATE VARIANCE:
0 distinct cases observed this run (every non-unsafe case was fully
stable across all 5 executions)

BURNED 660 REGRESSION (round 2, final):

FALSE_SAFE:
0

FALSE_OPERATIVE_TO_CLEAN:
0

UNVERIFIED_FEEDING_CLEAN:
0

FALSE_ABSENCE:
3

MATERIAL_CONTEXT_SILENTLY_LOST:
2

ARBITRARILY_SELECTED_COMPETING_READING:
0

UNRESOLVED_CROSS_REFERENCE_TO_CLEAN:
0

UNRESOLVED_DEFINITION_TO_CLEAN:
0

TOTAL CORRECT:
521/660 (78.9%)

SAFE REVIEW/ESCALATION:
86/660 (13.0%) false-escalation cases — conservative, never dangerous

FALSE POSITIVE:
0 (no authoritative violation reached without grounded, contract-traceable evidence)

FALSE NEGATIVE:
3 confirmed FALSE_ABSENCE cases (the highest-severity kind); a further
share of 83 MISSED_OPERATIVE_FACT occurrences landed in an already-non-
clean bucket for the wrong specific reason (lower severity — the
customer still got a review signal)

UNSAFE CLEAN:
0

FULL REGRESSION:
215 failed, 2128 passed, 14 skipped, 6 errors (identical before and
after both fix rounds this mission — see baseline established in
Candidate 3/4's PHASE10/PHASE15 reports for the pre-existing-environment-
artifact explanation of the 215/6 baseline)

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

READY TO FREEZE CANDIDATE 5:
NO

## Why, in plain terms

Real, substantial, honestly-measured progress: 6 of 8 hard gates now
verify at zero (up from 2 of 8 at the start of this mission), the
12-adapter pass rate improved from 6/12 to 9/12, and the two most severe
gates (`FALSE_SAFE`, `FALSE_OPERATIVE_TO_CLEAN`) have now held at zero
across three consecutive missions and multiple independent real-provider
runs. Both fixes this mission made were general, root-cause-targeted,
paired with fresh adversarial tests, and verified not to regress the
existing test suite or the two non-negotiable gates.

But two hard gates remain non-zero, and the repeatability check —
measuring exactly the customer-significant authority transitions this
mission asked to prioritize — found 3 unsafe transitions, not 0. Per
Section 25's own explicit rule, this is not a passing result, and this
report does not present it as one. No new architecture was invented, no
speculative remediation was rushed through to chase a clean number (the
"right, title, and interest" anchor addition and the bare-"deliverables"
anchor broadening were both identified as possible further fixes and
DELIBERATELY left undone this mission, per Section 21's own instruction
against patching individual corpus sentences and against low-value
purity chasing under time pressure), and every remaining gap is named,
traced, and disclosed rather than hidden inside an aggregate pass rate.
No production config was changed, nothing was deployed or merged, and no
new independent corpus was created.
