CANDIDATE 3 — FREEZE + INDEPENDENT CUTOVER VALIDATION — FINAL VERDICT

Full evidence package in `artifacts/candidate3_independent_validation/`:
`FREEZE_MANIFEST.md`, `PHASE1_CUTOVER_ACTIVATION_EVIDENCE.md`, `corpus/CORPUS_MANIFEST.json`,
`corpus/CORPUS_FREEZE_DECLARATION.txt`, `PHASE4_HARD_SAFETY_GATES.md`,
`PHASE5_ADAPTER_MATRIX.md`, `PHASE6_INTERACTION_ENGINE.md`,
`PHASE7_AUTHORITY_SURFACE_CONSISTENCY.md`, `PHASE8_DEFERRED_RESIDUAL_RISK.md`,
`PHASE10_FULL_REGRESSION.md`, plus raw evidence (`raw_results.jsonl`, `phase1_result.json`,
`phase6_result.json`, `phase4_5_analysis.json`) and the scripts that produced them.

## Pass-rule checklist

| Requirement | Status |
|---|---|
| Exact candidate remained frozen | **YES** — zero production-code changes at any point after Phase 0 (`git diff` against `d2820362` returns empty for everything outside this artifacts directory) |
| Corpus was genuinely unseen | **YES** — zero exact-text overlap with either burned corpus, confirmed programmatically; freshly authored for this mission without inspecting any Candidate 3 failure log |
| Corpus was frozen before execution | **YES** — hash computed and files made read-only before Phase 3 ran |
| Real provider was exercised | **YES** — 660 + 6 (Phase 1/6) real OpenAI calls, confirmed via live log output |
| FACT_ADMISSION_MODE=enforced was exercised | **YES** — confirmed live at runtime (Phase 1) |
| POLICY_ENFORCEMENT_MODE=cutover was exercised | **YES** — confirmed live at runtime, `interaction_decisions present: True` proves the cutover branch specifically (Phase 1) |
| All 12 adapters executed | **YES** — every adapter present with real cases and real decisions in `raw_results.jsonl` |
| Interaction engine executed | **YES** — real `apply_policies_for_review` call, 7 launch-catalog rules evaluated (Phase 6) |
| All eight hard safety gates = 0 | **NO — 5 of 8 are non-zero** (see below) |
| Authoritative surfaces are consistent | **YES** (Phase 7) |
| No post-result tuning occurred | **YES** — raw results preserved verbatim; the two analysis-script corrections made (see `PHASE4_HARD_SAFETY_GATES.md`) were to the GATE DEFINITION/SCORING LOGIC before its final run, not to any case, expected label, or decision after seeing results — no case was re-run, no code was changed, no expected label was altered |

**The single failing requirement — all eight hard safety gates at zero — is sufficient by the
mission's own explicit rule to require `AUTHORIZED FOR CUTOVER = NO`.**

---

FROZEN_CANDIDATE_SHA: `d2820362b2a9c7641b2fe294fbfc1a04ccf6df3e`
CORPUS_SHA256: `102acc23327d19737e206706404999beafaf03cca6db976b9e0e45cdb8093e38`
CORPUS_SIZE: `660`

FACT_ADMISSION_MODE: `enforced` (validation-process environment variable only; repository default remains unset/disabled)
POLICY_ENFORCEMENT_MODE: `cutover` (validation-process environment variable only; repository default remains `shadow`)
REAL_PROVIDER: `OpenAI`
MODEL: `gpt-4o-mini`

12 ADAPTERS EXECUTED: YES
INTERACTION ENGINE EXECUTED: YES

FALSE_SAFE: 0
UNVERIFIED_FEEDING_CLEAN: 33
FALSE_ABSENCE: 9
FALSE_OPERATIVE_TO_CLEAN: 0
MATERIAL_CONTEXT_SILENTLY_LOST: 3
ARBITRARILY_SELECTED_COMPETING_READING: 6
UNRESOLVED_CROSS_REFERENCE_TO_CLEAN: 9
UNRESOLVED_DEFINITION_TO_CLEAN: 17

FALSE_ESCALATION: 80
CORRECT_CLEAN: 45
CORRECT_NON_CLEAN: 445

AUTHORITY SURFACE CONSISTENCY: CONSISTENT

KNOWN DEFERRED RISK:
ip_ownership-080 — retained as deferred by product owner, not fixed, not included in the new
corpus, not a source of any metric adjustment; the new corpus's own ip_ownership hard-gate
findings are a different failure shape (AI-discovery recall miss + a less-common phrasing not
recognized by either channel), not a new instance of the same defect.

NEW REGRESSIONS: 0 (see `PHASE10_FULL_REGRESSION.md` for the full accounting of a significant,
fully-disclosed validation-sandbox environment change — installing packages needed to prove
cutover was genuinely reached at runtime — that altered which tests collect at all, with zero
change to any previously-passing test's outcome and zero production-code change of any kind)

FINAL INDEPENDENT VALIDATION:
FAIL

AUTHORIZED FOR CUTOVER:
NO

## Summary of why

This was a genuine, one-shot, unseen, real-provider, real-cutover-configuration validation —
every procedural requirement of the mission was met faithfully: the candidate stayed frozen,
the corpus was genuinely new and frozen before execution, the real provider and real cutover
configuration were proven reached at runtime (not merely asserted), all 12 adapters and the
interaction engine executed for real, and no result was tuned after the fact. The five
authorized architectural blockers from the prior remediation mission held up under this
independent pressure: `FALSE_SAFE` and `FALSE_OPERATIVE_TO_CLEAN` — the two most severe gate
categories — are both zero across 660 genuinely new cases.

However, five of the eight required hard gates are non-zero: 33 `UNVERIFIED_FEEDING_CLEAN`,
9 `FALSE_ABSENCE`, 3 `MATERIAL_CONTEXT_SILENTLY_LOST`, 6 `ARBITRARILY_SELECTED_COMPETING_
READING`, 9 `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN`, 17 `UNRESOLVED_DEFINITION_TO_CLEAN`. Root-
cause investigation (documented in full in `PHASE4_HARD_SAFETY_GATES.md`) found these are
concentrated in 7 of 12 adapters and trace to two real, distinct causes: a genuine AI-discovery
recall limitation (the same class of limitation this repository's prior burned corpora
classified as non-hard-gate, but which this mission's own, stricter gate design correctly
surfaces as a hard failure when it results in a clean decision) and a genuine architectural
asymmetry where several adapters (insurance in particular) lack the same "nothing found by any
channel → escalate" gate that `warranties`/`sla` already have. A disclosed, non-corpus-editing
finding also identified an authoring inconsistency in some `insurance` templates that
contributed to but does not fully explain that adapter's share of the findings — real,
non-`insurance` instances remain in every non-zero gate regardless.

Per the mission's own decision rule, this is sufficient for `FINAL INDEPENDENT VALIDATION: FAIL`
and `AUTHORIZED FOR CUTOVER: NO`, regardless of the otherwise-successful procedural execution of
this validation. No Vercel production variable was changed, no PR was created, nothing was
merged, and nothing was deployed, per the mission's absolute stop instruction. This complete
evidence package is provided for review; production activation remains separately authorized
only after this review.
