# Step 4A.10 Phase 1 — Reproduction of the Step 4A.9.2 Control

Re-ran the UNMODIFIED Step 4A.9.2 corpus (`benchmarks/step4a9_1_benchmark.json`,
same 200 cases) against the frozen `5afbda9` code, one fresh pass, real
provider, real network calls (raw: `phase1_control_repro_raw.json`, log:
`phase1_control_repro_output.txt`).

| Metric | Step 4A.9.2 (2 runs) | Phase 1 reproduction |
|---|---|---|
| `novel_unseen` (30) recovery | 30/30, 30/30 | **29/30** |
| Positive false-absence rate | 0.0%, 0.0% | 0.8% (1/120) |
| Clean-VERIFIED recall | 15.8%, 15.8% | **15.8% (19/120) — exact match** |
| Hard-negative false clean facts | 0/80, 0/80 | **0/80 — exact match** |
| Hard-negative false-candidate rate | 3.8%, 1.2% | 2.5% (within the same observed range) |
| Semantic candidate -> direct authority | 0, 0 | **0 — exact match** |

## Verdict: reproduces within previously-documented variance — PROCEED

The single `novel_unseen` miss (`29/30` vs `30/30` both prior runs) is a
1-case flicker of exactly the kind Step 4A.9.2 Section E already
documented and quantified (3/200, 1.5%, concentrated at the
`PRESENT_BUT_UNRESOLVED` <-> `CONFIRMED_ABSENT`/`RECOGNITION_UNCERTAIN`
boundary — never the accept boundary). It is NOT a new failure mode, it is
NOT a change in production code (hashes unchanged, confirmed Phase 0), and
it does not touch the load-bearing safety numbers: clean-VERIFIED recall
and hard-negative false-clean-fact count reproduced EXACTLY. This is not a
"material" control failure under the task's own definition (which reserves
STOP for exactly that kind of load-bearing metric moving). Proceeding to
Phase 2+ without any production-code change.
