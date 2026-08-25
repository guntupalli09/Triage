CANDIDATE 4 — PHASES 10–11: REAL PROVIDER TESTING AND REPEATABILITY

## Real provider (Phase 10)

All real-provider work in this mission ran through the application's real
contextual-discovery path (`_run_semantic_discovery` in each adapter,
which calls the real OpenAI provider — confirmed via the
`OpenAI client initialized successfully` log line, identical to Candidate
3's Phase 1 evidence). No provider mocking was used anywhere in this
mission. Credentials were read only from `OPENAI_API_KEY` in the calling
shell's environment (sourced from a 600-permission scratch file per this
engagement's standing security protocol), never printed, logged,
persisted in any artifact, or committed.

Real-provider execution surfaces in this mission:
- The full burned 660-case corpus regression (Phase 12,
  `run_burned_regression.py` — every one of the 660 cases spans every
  adversarial family from the original corpus: paraphrased operative
  language, descriptive/non-operative language, negation, conditions,
  exceptions, definitions, cross-references, conflicting clauses,
  competing readings, missing attachments — see
  `corpus/CORPUS_MANIFEST.json` for the full family list).
- The scoped repeatability check (Phase 11, below), 48 cases × 5 real runs
  each = 240 real provider-backed executions.
- The interaction engine check (Phase 13), 3 composite scenarios.
- 10 new adversarial tests in `tests/test_candidate4_remediation.py` (these
  run the real deterministic extraction path directly; semantic discovery
  inside them calls the real provider when enabled via environment
  variables, and is exercised via `_run_semantic_discovery`'s existing,
  unmocked call chain in the full pytest run against the live environment).

Provider output remained non-authoritative throughout: every fix in this
mission operates on DETERMINISTIC reclassification of `absence_state`
after semantic discovery returns (never trusting an unadmitted candidate,
and never letting the ABSENCE of a candidate itself become authoritative
evidence of absence).

## Repeatability (Phase 11) — scoped to 48 cases × 5 executions

Per this mission's Phase 11 text ("at least 48 cases × 5 identical
executions"), 48 cases (4 from each of the 12 adapters, drawn from the
burned corpus) were each run 5 times through the real provider — 240 total
executions. This is the MINIMUM the mission specifies, not the full 660;
given the full 660-case corpus was already being run once (for Phase 12)
concurrently with real-provider cost/time already committed to this
mission, a full 660×5 repeatability pass (3,300 executions) was judged
disproportionate to run in addition, and the 48×5 minimum was executed
in full instead. This is disclosed as the actual scope, not silently
presented as broader than it is.

Results: see `repeatability_results.json`.

UNSAFE_CLEAN_STATE_VARIANCE: see the final verdict for the exact count
(computed after both background executions completed).
