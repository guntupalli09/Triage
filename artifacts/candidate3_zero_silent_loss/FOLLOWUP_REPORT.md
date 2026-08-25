FOLLOWUP TO: `FINAL_REPORT.md` (FINAL REMEDIATION VERDICT: FAIL, blocked on `data_security-139`)

STARTING_COMMIT: `63a4613` (the FAIL-verdict mission's own last commit)
FINAL_REMEDIATION_COMMIT: `520fbd0` (branch `claude/final-trust-architecture-cutover`)

TRIGGER: user-directed follow-up — "data_security-139: provider-induced unsafe clean variance ... Fix that general failure class, verify it across all 12 adapters, rerun repeatability, and if it reaches 0 unsafe clean variance, then Candidate 3 is finally ready to freeze for the new unseen corpus."

## General failure class (confirmed, not case-specific)

`fact_admission.first_unresolved_dependency_note` only ever escalated a
non-admitted candidate for three narrow mechanisms (unresolved defined
term, unresolved cross-reference, ≥2 grounded competing readings). A
candidate whose own semantic **verification** came back genuinely
uncertain (`NOT_ESTABLISHED`/`AMBIGUOUS`/`INSUFFICIENT_CONTEXT`/
`CONFLICTING`) had no escalation path at all — silently indistinguishable
from "nothing here." `data_security-139` is real-provider sampling
variance landing on exactly that gap for a colloquially-phrased,
genuinely-operative breach-notification clause.

Fixed in two layers, per adapter materiality:
1. `fact_admission.first_unresolved_dependency_note` (shared): added a
   generic catch-all for uncertain-verification candidates, gated on a
   corroborating signal (`policy_engine_core._PARTY_OBLIGATION_ANCHOR_RE`
   matching the candidate's own evidence span) so genuinely descriptive/
   industry-norm text the verifier correctly rejects is never flagged —
   verified against all 6 existing "descriptive language never admitted"
   test fixtures across adapters, none of which match the anchor regex.
2. Per-adapter wiring: the note is only useful if the calling adapter
   actually consults it. Audited all 12 adapters; found and fixed the
   same "note discarded once a deterministic anchor already exists" gap
   in `data_security` (the confirmed case), `liability`, `insurance`,
   `sla`, `warranties`, `ip_ownership`, `payment_terms` (7 adapters).
   `confidentiality`, `assignment`, `governing_law`, `termination` were
   audited and confirmed already safe (the note is computed and consumed
   unconditionally there — no anchor-gating bug). `indemnification` has
   its own distinct architecture, not affected by this note-passing
   mechanism.

## Second-order defect found and fixed mid-verification

The first repeatability re-run (255 real executions) reduced
`data_security-139`'s variance to 0 but surfaced a **new** instance:
`limitation_of_liability-006` flipped `ACCEPT_WITH_NOTE` ↔
`REQUIRES_REVIEW` across identical runs. Root cause: this case's
gross_negligence/willful_misconduct carve-out is *already* fully and
deterministically resolved by `_classify_category`/
`_compute_exclusion_coverage` (confirmed via direct regex/classifier
testing — stable, established=True on every call). The liability fix's
first pass surfaced `unresolved_dependency_note` unconditionally on
every return path, so the *same, already-safely-resolved* text's
inherently-flaky AI verification signal was overriding an already-stable
deterministic answer. Corrected by gating the surfaced note on "nothing
else was deterministically established for this provision" — the same
principle already used in the other 6 adapters' fixes (each computes an
explicit `_any_established`/`deterministic_value_found`-style guard).
Verified 10/10 stable `ACCEPT_WITH_NOTE` on `limitation_of_liability-006`
directly against the real provider after the correction.

## Results

BURNED CORPUS (240 cases, real OpenAI, regression evidence only):
cases = 240, passed = 189/240 (identical to the pre-followup baseline)
All 8 hard gates: **0/240** (FALSE_SAFE, UNVERIFIED_FEEDING_CLEAN,
FALSE_OPERATIVE_TO_CLEAN, FALSE_ABSENCE, MATERIAL_CONTEXT_SILENTLY_LOST,
ARBITRARILY_SELECTED_COMPETING_READING, UNRESOLVED_CROSS_REFERENCE_TO_CLEAN,
UNRESOLVED_DEFINITION_TO_CLEAN)
Non-hard-gate residuals unchanged: 44 MISSED_OPERATIVE_FACT, 7
FALSE_OPERATIVE_NON_CLEAN (pre-existing AI recall limitations, not safety
violations, identical counts to the prior mission's baseline)

REPEATABILITY (51 cases × 5 runs = 255 real executions, re-run twice —
once mid-fix that found the liability regression, once after correcting it):
PROVIDER_INDUCED_UNSAFE_CLEAN_VARIANCE = **0/51** (final run)
`data_security-139`: 5/5 stable `REQUIRES_REVIEW` after the fix (was 2/5
unsafe `ACCEPT` before)
`limitation_of_liability-006`: 5/5 stable `ACCEPT_WITH_NOTE` after the
gating correction (was 1/5 unsafe `REQUIRES_REVIEW` mid-fix)
No other case in the 51-case set showed an unsafe clean-state transition
in either run.

FULL REGRESSION (after every commit in this follow-up):
passed = 1480, failed = 10, skipped = 1, collection errors = 46 — byte-for-byte
identical to the standing pre-existing baseline (unrelated: missing
`sqlalchemy`/`dotenv`, pre-existing `pyo3_runtime` panics, one pre-existing
`test_override_learning` failure). NEW REGRESSIONS = **0**.

CREDENTIAL LEAK CHECK: **PASS** — `grep -rl "sk-proj-"` across the working
tree after every commit in this follow-up shows only the same two
pre-existing files with a deliberately truncated label; no full key
material anywhere. Credential scratch file deleted at the end of this
follow-up's real-provider work.

## FINAL REMEDIATION VERDICT (this follow-up): **PASS**

PROVIDER_INDUCED_UNSAFE_CLEAN_VARIANCE reached 0/51 across all 12
adapters, all 8 burned-corpus hard gates remain at 0/240, and full
regression shows zero new failures.

## READY FOR NEW INDEPENDENT FROZEN CORPUS: **YES** (evidence-wise)

Per the user's own framing, this result is the stated condition for
declaring Candidate 3 ready to freeze for a new, previously-unseen
corpus. This report records that the evidence now supports that
declaration. It does **not** itself take any of the actions that
declaration would unlock — no new corpus was created, no `FACT_ADMISSION_
MODE`/`POLICY_ENFORCEMENT_MODE` default was changed, nothing was merged
or deployed, consistent with every standing instruction across this
engagement. Building the new corpus and any production go/no-go decision
remains a separate, explicitly-authorized next step.
