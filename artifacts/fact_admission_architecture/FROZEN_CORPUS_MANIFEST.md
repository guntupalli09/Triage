# FROZEN_CORPUS_MANIFEST

**Status: NOT CREATED. This gate is unfinished.**

## Why

The mission requires a fresh ≥600-case adversarial corpus, executed
exactly once against the frozen production build, with provenance
(corpus hash, production commit SHA, verifier prompt/schema version,
model/provider identifier, timestamp) recorded before execution and no
production changes permitted afterward.

Two prerequisites for that gate to mean anything were not available in
this session:

1. **A real, budgeted LLM provider credential for bulk adversarial
   execution.** Every targeted test in this pass (117 new tests) mocks
   `urllib.request.urlopen` — deliberately, since unit tests must not
   depend on network access or spend real API budget, and per this
   repository's own explicit rule (see the task's
   "NEVER expose, print, log, copy, or commit credentials from .env")
   this session did not attempt to read, discover, or spend against
   whatever provider credential may or may not be configured for this
   environment's production deployment. Running 600+ real adversarial
   cases against a live model requires a credential and a cost budget
   this session has no visibility into or authorization to spend against.
2. **Every new adapter's semantic-discovery flag defaults to `False`.**
   A frozen corpus run with the flags off would only exercise the
   pre-existing deterministic regex paths (already covered by each
   adapter's existing benchmark corpus, per PRE_IMPLEMENTATION_MAP.md
   §10) — it would not actually test the new architecture. Running it
   with the flags on is a live production-behavior change no one has
   authorized in this session.

## What would be needed to close this gate

- Explicit authorization to enable `*_SEMANTIC_DISCOVERY_ENABLED` for a
  bounded corpus run (not general production traffic).
- A funded, rate-limited Anthropic API credential scoped for this run.
- Someone to author the ≥50-cases-per-adapter corpus content itself
  (operative positives, absence, recognition-uncertainty, descriptive
  false-positives, hypotheticals, quotations, negations, conditions,
  exceptions, cross-references, role inversions, asymmetry, conflicts,
  competing interpretations, malformed evidence, provider failures per
  the mission's own list) — this is substantial legal-domain authoring
  work, not a mechanical step.
- A frozen production commit SHA to pin the run against (this branch is
  not yet merged, so there is no "production" build to freeze against
  yet in the mission's sense).

## Explicit non-substitute

The mocked test suites in `tests/test_*_fact_admission.py` (117 cases,
7-8 per adapter) are **not** a substitute for this gate and are not
represented as one anywhere in this report. They validate the pipeline's
*mechanical* behavior under every controlled response shape; they do not
validate what a real model actually decides when shown genuinely novel
adversarial contract language.
