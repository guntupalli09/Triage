# TEST_PLAN

## Targeted architecture tests (written before regression, per mission Step 13)

For `fact_admission.py` (39 tests, `tests/test_fact_admission.py`):
authority-boundary guard, discovery fail-closed on every provider-failure
mode (missing key, network error, malformed JSON, hallucinated quote),
verifier fail-closed on every mode (missing key, network error, malformed
JSON, empty response, invalid enum, contradictory ESTABLISHED-with-no-
evidence), grounding (exact-substring pass/fail, fabricated evidence),
and the admission gate (every unsafe verification status → NOT_ADMITTED,
unresolved dependency/conflict block admission even when ESTABLISHED,
defensive handling of an unrecognized future status).

For each of the 11 newly-integrated adapters (7 tests each, `tests/
test_<adapter>_fact_admission.py`): disabled-by-default no-op, provider-
outage → RECOGNITION_UNCERTAIN (never CONFIRMED_ABSENT), that state
routing to REQUIRES_REVIEW (never NOT_APPLICABLE/ACCEPT), confirmed-
absent-when-discovery-runs-clean, hallucinated-quote rejection, a genuine
end-to-end admission (discovery → adversarial verify ESTABLISHED →
grounding pass → structuring succeeds), and the Step 15 descriptive-
language regression (an adversarial NOT_ESTABLISHED verdict must never be
admitted). Liability additionally carries a Step 18 determinism/replay
test.

## Regression (Step 19)

Every pre-existing test file for a touched adapter re-run before that
adapter's commit — see individual commit messages for per-adapter counts.
Full suite re-run after all 12 adapters closed — see REGRESSION_REPORT.md
for the categorized final count.

## What this plan does NOT cover (see RESIDUAL_RISK_REGISTER.md)

- A live-provider adversarial benchmark (the equivalent of indemnification's
  own Step 4A.9.2, 200 real API calls) for any of the 11 newly-integrated
  adapters. All targeted tests above are mocked — they exercise the code
  paths and failure-mode handling exhaustively, but do not validate real
  model behavior against real adversarial contract language.
- The mission's Step 20 fresh 600-case frozen corpus. Not created — see
  FROZEN_CORPUS_MANIFEST.md.
- The mission's Step 21 live triagecounsel.com validation. Not performed —
  see LIVE_PRODUCT_PROOF_REPORT.md.
