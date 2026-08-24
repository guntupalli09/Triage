# Candidate 2 — Remediation Report

## CANDIDATE 2 COMMIT

`dc11333d432ec1fed5c81340178a5bfd43f4b291` (see also the exact reference at
the end of this document).

Predecessor: FROZEN_COMMIT `f94c4c319f828c4e0072af9305d409a03964d237`
(FINAL VALIDATION VERDICT: FAIL, SHIP NOT AUTHORIZED — see
`artifacts/final_frozen_validation/FINAL_VALIDATION_REPORT.md`).

## ROOT CAUSES FOUND

Full analysis: `artifacts/candidate2_remediation/ROOT_CAUSE_MAP.md`.

6 observed failures, resolved to **4 distinct root causes**, 2 of them
confirmed shared across adapters via `policy_engine_core.py`:

1. **Confidentiality asymmetry** (confidentiality-06) — the asymmetry
   comparator only ran on a single mutual-opener ("each party shall...")
   sentence shape; two SEPARATE directional sentences bypassed it entirely.
   A second, masking sub-defect (a duration-classification window wide
   enough to bleed a second obligation's "indefinitely" into the first
   obligation's own duration) was found and fixed in the same pass.
2. **Data security time normalization** (data_security-02) — the
   breach-notification-window parser only recognized hours and digit-days;
   spelled-out numbers and calendar-day phrasing fell through unconverted,
   and ambiguous units (business days) were silently dropped rather than
   forced to review.
3. **Data security negated obligation** (data_security-05) — an explicit
   disclaimer ("Vendor shall have no obligation to notify...") was treated
   as if the fact were simply absent, rather than as an affirmatively
   disclaimed obligation the policy still needs to see. A masking
   window-direction bug (the negation scan only looked FORWARD from the
   anchor, missing a negation verb phrase that precedes it in natural
   sentence order) was found and fixed in the same pass.
4/5. **Insurance and SLA false-operative→clean** (insurance-04, sla-04) —
   SHARED root cause: neither adapter called the existing
   `policy_engine_core.is_operative_context()` primitive that
   liability/indemnification/payment_terms already trust to reject
   descriptive/background language. The primitive itself also lacked a
   structural cue for "industry-norm descriptive framing + explicit
   not-yet-agreed language" (found via corpus replay, this cue's original
   version also missed the passive-voice paraphrase "have not yet been
   agreed" — fixed to generalize past both). A third, adapter-local
   sub-defect in insurance (no `found_anything` negative-control gate,
   unlike sla/warranties) was found via the Candidate 1 corpus replay and
   fixed in the same pass, together with a further correction so that gate
   does not discard a genuinely operative-but-underspecified obligation
   (e.g. coverage delegated to an unincluded exhibit).
6. **Indemnification material context silent loss** (indemnification-07) —
   the backward-reference qualifier detector only ever fired when TWO
   conflicting backward-references to the same section existed; a single,
   unopposed "Notwithstanding Section N, ..." qualifier was invisible to
   both the codebase's regex vocabulary (leading-"notwithstanding" surface
   form) and the "needs 2+ to fire" gate.

## SHARED FIXES (policy_engine_core.py)

- `is_operative_context()`: added `_INDUSTRY_NORM_DESCRIPTIVE_RE` +
  `_NOT_YET_AGREED_RE` dual-signal gate (industry-norm framing AND
  not-yet-agreed language required together, to avoid suppressing a
  genuinely operative clause that merely opens with a benign industry
  lead-in). `_NOT_YET_AGREED_RE` further generalized to match passive
  voice ("have not yet been agreed"), not only active voice.
- New function `detect_backward_referenced_qualifier()`: generalizes the
  existing `detect_conflicting_backward_conditions()` to the single-
  reference case, and adds a new `_NOTWITHSTANDING_SECTION_QUALIFIER_RE`
  surface form (leading "Notwithstanding Section N, ...") alongside the
  existing "the obligation under Section N... shall apply only..." form.
  The original function is left completely unchanged (still used
  elsewhere for the 2+-conflicting-reference case).

## ADAPTER-SPECIFIC FIXES

- **confidentiality_policy_engine.py**: bounded the duration-classification
  window to the next NAMED/MUTUAL obligation's start (fixing the window-
  bleed masking defect); added a new comparison branch in
  `evaluate_confidentiality_policy()` that runs `_compare_confidentiality_
  attribution()` on independently-resolved `exposure`/`protection`
  obligations (not just a single mutual-opener match) whenever
  `require_mutual_confidentiality` is set.
- **data_security_policy_engine.py**: `_classify_breach_notification()`
  rewritten to parse spelled-out numbers (via the shared
  `word_number_alternation`/`parse_multiplier_token` primitives) and
  calendar-day phrasing (converted via a fixed `_HOURS_PER_CALENDAR_DAY`
  constant), to fail closed (`breach_notification_ambiguous_unit=True`,
  forcing `REQUIRES_REVIEW`) on ambiguous business-day phrasing rather than
  manufacturing a converted value, and to detect explicit disclaimers via
  a widened backward negation scan (fixing the window-direction masking
  defect) — surfaced as `breach_notification_explicitly_disclaimed`, which
  forces `MUST_REDLINE` whenever the policy requires any breach-
  notification period.
- **insurance_policy_engine.py**: wired `is_operative_context()` into the
  per-coverage-type anchor loop; added a `found_anything` negative-control
  gate (mirroring sla/warranties) so a wholly non-operative clause is
  discarded exactly like "nothing here at all" — while an admitted
  semantic candidate, or ANY genuinely operative top-level anchor match
  (even one that never resolves to a specific named coverage type),
  correctly keeps the clause visible to the existing "policy requires X
  coverage but the clause doesn't address it" / cross-referenced-exhibit
  logic instead of discarding it.
- **sla_policy_engine.py**: wired `is_operative_context()` into the uptime-
  percent and service-credit anchor loops (sla already had its own
  `found_anything` gate, so no equivalent adapter-local sub-defect existed
  here).
- **indemnification_policy_engine.py**: replaced the call site that only
  used `detect_conflicting_backward_conditions()` with the new
  `detect_backward_referenced_qualifier()`, merging its result into the
  obligation's existing `ConditionEvidence` via `_merge_condition_evidence`.

## DEFECT VERIFICATION (against Candidate 1's exact confirmed failures)

| # | Defect | Candidate 1 (frozen) | Candidate 2 | Ground truth | PASS? |
|---|---|---|---|---|---|
| 1 | confidentiality-06 asymmetry | CLEAN (ACCEPT) | NEGOTIATE (NOT_CLEAN) | NOT_CLEAN | **PASS** |
| 2 | data_security-02 time normalization | CLEAN (ACCEPT) | ESCALATE | NOT_CLEAN | **PASS** (no longer CLEAN; ESCALATE is a safe non-clean state) |
| 3 | data_security-05 negated obligation | CLEAN (ACCEPT) | MUST_REDLINE (NOT_CLEAN) | NOT_CLEAN | **PASS** |
| 4 | insurance-04 false-operative | CLEAN (ACCEPT) | NOT_APPLICABLE | NOT_APPLICABLE | **PASS** |
| 5 | sla-04 false-operative | CLEAN (ACCEPT) | NOT_APPLICABLE | NOT_APPLICABLE | **PASS** |
| 6 | indemnification-07 material context silent loss | NOT_CLEAN (masked by unrelated MUST_REDLINE) | REQUIRES_REVIEW | REQUIRES_REVIEW | **PASS** |

All 6 confirmed defects now produce a safe, non-CLEAN, and (for 5 of 6)
ground-truth-matching decision. Verified via a full replay of the SAME
burned, hashed 74-case corpus (see CANDIDATE 1 CORPUS REPLAY below) — the
corpus file itself (`cases.py`) was imported unmodified, never copied or
edited; SHA-256 `dcf7c43c698c1857c202a692a4d3f86595399a3ff07d61584a08e6a957488d8c`
matches the original frozen hash exactly.

## 12-ADAPTER ADVERSARIAL SWEEP

Full detail: `artifacts/candidate2_remediation/CROSS_ADAPTER_SWEEP.md`.

Summary: descriptive-vs-operative was probed directly against all 7
adapters not wired to `is_operative_context` (confidentiality, ip_ownership,
data_security, governing_law, termination, warranties, assignment) with the
same adversarial shape that broke insurance/sla; none are exposed today,
because each independently requires a first-person obligation verb before
attributing any fact (a narrower, adapter-local gate, not the shared
primitive). This is recorded as residual, out-of-scope follow-up risk, not
silently closed. Negated-vs-affirmative was probed across all 12 adapters
with no false extraction found. Condition/exception preservation,
cross-sentence/cross-section modifiers, and cross-reference dimensions are
covered by each adapter's own existing permanent regression suite plus the
new defect-specific families added in this mission; competing-readings and
AI-provider dimensions are explicitly marked N/A (untouched by any
Candidate 2 fix) with reasons stated.

## REAL AI PROVIDER TEST

**PROVIDER AVAILABLE: NO** — `ANTHROPIC_API_KEY` is not set in this
environment (confirmed via direct inspection, not inferred).
**PROVIDER USED:** none (no live call was attempted).
**REAL PROVIDER CALL EXECUTED: NO.**

This is the same environment constraint documented in Mission A's
`FINAL_VALIDATION_REPORT.md`. No credentials were invented, printed,
logged, or committed, and no second secret-management mechanism was
introduced. All 6 Candidate 2 fixes are deterministic (regex/structural)
changes in the extraction and evaluation layers; none touch
`fact_admission.py`'s provider-call, grounding, or reconciliation code.
The existing fail-closed behavior when no provider is configured
(`ProviderUnavailable` → `RECOGNITION_UNCERTAIN` → `REQUIRES_REVIEW`, never
`ACCEPT`) is unchanged and is exercised by each adapter's own existing
mocked-provider unit tests (which use `unittest.mock.patch` on
`urllib.request.urlopen`, not a real network call, and are already
disclosed as such in their own docstrings/imports) — mocks used for these
unit tests do not constitute live-provider proof, and are not represented
as such here.

## CANDIDATE 1 CORPUS REPLAY

**NOT INDEPENDENT VALIDATION. Passing this corpus does NOT authorize
shipping.**

Re-ran the SAME frozen, hashed 74-case corpus
(`artifacts/final_frozen_validation/corpus/cases.py`, imported unmodified)
against Candidate 2's code via
`artifacts/candidate2_remediation/corpus_replay/replay_candidate2.py`,
writing results to `candidate2_raw_results.jsonl` (the original
`artifacts/final_frozen_validation/raw_results.jsonl` from Mission A was
never touched — confirmed via `git status`/`git checkout` after an initial
accidental overwrite was caught and reverted).

Two pre-existing harness-fixture bugs in the corpus RUNNER (not the
frozen, hashed `cases.py` itself, and not production code) were corrected
in this replay-only copy, analogous to the FakePolicy attribute-name fixes
already made under Mission A's Rule #1 exception for the validation harness:
- `contract_side` fixture default was the literal string `"vendor"` across
  11 of 12 policy fixtures, but every adapter's real Protocol requires
  `"sell_side"`/`"buy_side"`/`"mutual"` — `"vendor"` matches none of them,
  silently short-circuiting side-resolution logic (confirmed by direct
  code reading of `_resolve_obligations_for_side()`). Corrected to
  `"sell_side"` (matching the one fixture, indemnification, that was
  already correct).
- `_DataSecurityPolicy`'s `max_breach_notification_hours` fixture field
  (used by the data_security-05 case's policy override) is not read by
  `evaluate_data_security_policy()` at all (the real fields are
  `acceptable_max_breach_notification_hours` /
  `require_fixed_breach_notification_period`) — added a `__post_init__`
  back-compat alias, the same pattern already used elsewhere in this
  runner for `_TerminationPolicy`/`_AssignmentPolicy`.

Both were caught because fixing them changed a defect's replay outcome;
each was verified via direct code inspection (not assumed) before being
treated as a harness bug rather than a production defect, and both bugs
predate Candidate 2 (present in the original, frozen `run_corpus.py`,
meaning Mission A's original run of these specific cases exercised
different — and in confidentiality-06's case, entirely bypassed — code
paths than intended; this does not change Mission A's FAIL verdict, since
the corpus's OTHER cases and Mission A's own live code-reading of the
defects were unaffected).

Full-corpus diff (Candidate 1 vs. Candidate 2, same 74 cases): 10 of 74
cases changed bucket. The 6 targeted defects (table above) all changed
from unsafe to safe. insurance-05 and insurance-06 (not in the confirmed-
defect list) were also affected mid-fix by the insurance found_anything
gate; both were caught via this same replay, fixed with the anchor-level
operative-context check documented above, and now reproduce their
ORIGINAL Candidate 1 bucket exactly (NOT_CLEAN in both cases) — confirmed
zero regression. The pre-existing false-safe set (`indemnification-06`,
`ip_ownership-02`, `ip_ownership-05`, `assignment-05` — none of them in
Mission B's 6-defect scope) is unchanged from Candidate 1's original run;
not addressed in this mission.

## FULL REGRESSION

Baseline (FROZEN_COMMIT, re-verified directly in a worktree during this
mission): **10 failed / 1357 passed / 1 skipped / 46 errors** (the
FREEZE_MANIFEST's "45 errors" was a minor miscount in Mission A; the true
frozen-commit collection-error count is 46, confirmed by running pytest
against `f94c4c3` directly in an isolated worktree).

Candidate 2 (final): **10 failed / 1431 passed / 1 skipped / 46 errors.**

- Failed count: identical (10 — same pre-existing failures).
- Error count: identical (46 — same pre-existing collection errors).
- Passed count: +74 (30 Candidate 2 regression tests: 6 confidentiality +
  13 data_security + 12 insurance/sla shared-primitive + 9 indemnification
  backward-reference; the remaining +44 come from Mission A's own corpus-
  validation-era test additions between the frozen baseline and this
  mission's starting point, not from Candidate 2).

**NEW REGRESSIONS: 0.**

## IMPLEMENTATION VERDICT: COMPLETE

## READY FOR NEW INDEPENDENT CORPUS: YES

No new independent corpus was created in this mission. No deployment, no
production cutover, and no change to `FACT_ADMISSION_MODE` or
`POLICY_ENFORCEMENT_MODE` production configuration were made. Candidate 2
must subsequently be evaluated against a NEW, previously-unseen frozen
corpus; only that new validation can authorize production cutover.

## CANDIDATE 2 COMMIT (final)

`dc11333d432ec1fed5c81340178a5bfd43f4b291`

(branch `claude/final-trust-architecture-cutover`, on top of predecessor
commits `fb61b97` and `84e1581`/`85d54c8` which carry the same mission's
earlier defect fixes and regression tests.)
