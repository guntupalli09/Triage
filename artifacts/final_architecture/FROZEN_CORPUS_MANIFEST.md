# FROZEN_CORPUS_MANIFEST

**Status: NOT CREATED. This gate is unfinished, same as the prior
branch's equivalent report — re-confirmed, not re-attempted, because
nothing in this session changed the underlying blockers.**

## Why (unchanged from the prior branch's manifest)

1. No confirmed, budgeted, live LLM provider credential for bulk (≥600
   case) adversarial execution is available to this session. This
   session did not attempt to discover, read, or spend against whatever
   credential may be configured for the actual production deployment,
   per the mission's own explicit prohibition on exposing/using
   credentials outside the application's normal mechanism.
2. Every semantic-discovery flag remains off by default (Phase 12 of
   this session made them environment-configurable, but did not enable
   any of them). A corpus run with flags off would not exercise the new
   architecture at all.
3. **New this session**: even with flags on, `POLICY_ENFORCEMENT_MODE`
   would also need to be `"cutover"` for a corpus run to reach the
   modern engine's decision path at all through the normal
   `apply_policies_for_review()` entry point (see
   PRE_IMPLEMENTATION_MAP.md). A corpus harness could call
   `extract_*_facts`/`evaluate_*_policy` directly, bypassing the mode
   check — but that would validate the adapters in isolation, not the
   actual production decision path the mission's Phase 14 asks to
   validate ("run in shadow against representative reviews" /
   "construct a fresh final corpus" against the frozen candidate as
   deployed).
4. Authoring ≥50 adversarial cases per adapter (600+ total) covering the
   mission's full family list (ordinary, unusual, false-operative traps,
   absence, recognition failure, competing interpretations, definitions,
   exceptions, provisos, cross-references, schedules, asymmetry, monetary
   values, dates, provider failures, malformed responses, prompt
   injection, interaction cases, dependency failures) is substantial
   legal-domain authoring work not attempted in this session.

## What would close this gate

Same four prerequisites as the prior branch's manifest: authorization to
enable specific flags for a bounded run, a funded rate-limited
credential, corpus authoring, and a frozen commit SHA to pin against
(this branch is not merged; there is no "production" build in the
mission's sense to freeze against yet).

## Explicit non-substitute

The 124 mocked tests in `tests/test_*_fact_admission.py` +
`test_fact_admission.py` + `test_fact_admission_env_config.py` (117 + 7)
validate mechanical pipeline behavior under controlled response shapes.
They are not represented anywhere in this report as a substitute for a
live-model frozen corpus.
