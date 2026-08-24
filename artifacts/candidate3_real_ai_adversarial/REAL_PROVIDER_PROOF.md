# Candidate 3 — Real Provider Proof (both distinct call paths)

Both calls made through the APPLICATION'S OWN functions (`fact_admission.
discover_candidate_spans` and `semantic_discovery_real.
discover_candidate_spans_real`), not a standalone scratch script hitting
OpenAI directly. No response was mocked. The credential was read from an
environment variable in-process and is not reproduced here.

## Path A — shared framework (`fact_admission.py`)

- REAL_PROVIDER = OpenAI
- REAL_NETWORK_CALL = YES
- MODEL = `gpt-4o-mini` (read from `fact_admission._MODEL` at call time)
- MOCK = NO
- APPLICATION_CALL_PATH = YES (`fact_admission.discover_candidate_spans`)
- Timestamp: `2026-08-24T08:39:55.507Z`
- Latency: 2228.2 ms
- Token usage: 277 input / 29 output
- Success/failure: success (`fact_admission.CALL_LOG[-1]["status"] == "ok"`)
- Resulting candidate status: 1 candidate proposed, grounded via exact
  substring search (`start_offset`/`end_offset` resolved, not None)

## Path B — indemnification's dedicated module (`semantic_discovery_real.py`)

- REAL_PROVIDER = OpenAI
- REAL_NETWORK_CALL = YES
- MODEL = `gpt-4o-mini` (read from `semantic_discovery_real._MODEL` at call time)
- MOCK = NO
- APPLICATION_CALL_PATH = YES (`semantic_discovery_real.discover_candidate_spans_real`)
- Timestamp: `2026-08-24T08:39:57.735Z`
- Latency: 1383.5 ms
- Token usage: 318 input / 31 output
- Success/failure: success
- Resulting candidate status: 1 candidate proposed, grounded via exact
  substring search

Both of this application's real-AI call paths are confirmed live and
functioning against the current OpenAI credential. Proceeding to the
adversarial corpus.
