# Selectivity / Usefulness Impact (Candidate 3 final gap-closure)

Reported honestly, without an arbitrary automation-rate threshold, per Section 12.

## What changed, directly measured (deterministic path, no real-provider call needed)

15 previously-mis-decided cases (8 Root Cause A `FALSE_SAFE`/`FALSE_OPERATIVE_TO_CLEAN` + 7 Root Cause B `UNRESOLVED_CROSS_REFERENCE_TO_CLEAN`/`UNRESOLVED_DEFINITION_TO_CLEAN`) plus `ip_ownership-080` (Root Cause C) now correctly move from `ACCEPT` (a clean, no-review decision) to `REQUIRES_REVIEW`/`ESCALATE`/`NOT_APPLICABLE`. This is a **selectivity cost, by design**: each of these 16 cases was a confirmed safety defect (a document the pipeline should have flagged for human review, that it was instead silently clearing). Fixing a `FALSE_SAFE` always trades "fewer clean decisions" for "no longer wrong" — that is the entire point of the fix, and it should not be reported as a net negative.

## What did NOT change

Zero previously-correct `REQUIRES_REVIEW`/`ESCALATE`/`NOT_APPLICABLE` decisions became `ACCEPT` as a side effect of any of these fixes (verified directly: full regression suite shows 0 new regressions across 1464 tests, including every adapter's own benchmark-gate corpus, which is dominated by cases whose CORRECT answer is a clean `ACCEPT`). The anti-over-suppression control tests (`test_industry_lead_in_with_real_party_obligation_stays_operative`, the `conflict-02`/`conflict-01` benchmark cases, the "the Schedule/Exhibit" phrasing regression control) all confirm the fixes did not widen suppression beyond the specific confirmed-broken shapes.

## Full-corpus rate, honestly scoped

The exact aggregate review-rate / clean-decision-rate / false-safe-rate shift across the full 240-case burned corpus (the number this section ultimately wants) requires re-running that corpus against the real OpenAI provider, since roughly 3/4 of its cases only exercise the AI-discovery path at all (per `REAL_AI_ADVERSARIAL_REPORT.md`'s finding that only 59/240 cases triggered any real AI call in the original run). That real-provider replay is a separate, explicitly-required step of this mission (Section 9) and had not yet been executed at the time this document was written, pending API credential availability in this session — see `BURNED_CORPUS_REGRESSION.md` (this mission's copy) for its result once run. This section reports precisely what is known now (the deterministic-path impact on the 16 specific fixed cases) rather than estimating or extrapolating a full-corpus percentage that hasn't actually been measured.
