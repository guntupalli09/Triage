# Step 4A.9.1 — Phase 0: Baseline Reproduction (PRE evidence)

- HEAD at start: `1c5d60efe7c5af378165493aa6ef1f98f0792698`
- `git status --short`: clean (no uncommitted changes)
- Production file hashes: see `phase0_hashes.txt`

## pytest

`1191 passed, 10 failed, 13 skipped, 44 errors` (the 10 failed / 44 errors are
pre-existing, unrelated infra/import issues — same counts as every prior
checkpoint since Step 4A.7.x; not touched by this step).

## Fresh 103-case battery (Step 4A.9 Phase 13 corpus)

Re-ran `benchmarks/run_step4a9_fresh_battery.py` twice
(`phase0_fresh_battery_run1.txt` / `run2.txt`) — byte-identical to each other
AND byte-identical to `artifacts/step4a9/fresh_battery_run1.txt` (the
Step 4A.9 recorded run). This is the frozen PRE baseline for this step.

**19 misses (documented in `step4a9_final_report.md` Section U), carried
forward verbatim as PRE evidence — NOT re-derived, NOT fixed here:**

- 12 false-absence (indemnification): verbs "make good to," "recompense...
  in full for," "be answerable to... and shall settle on...'s behalf" — none
  in `_RISK_TRANSFER_SIGNAL_RE`'s verb cluster.
- 7 WC: chained-delegation "points to" as a connective verb (liability/
  indemnification/payment_terms); conditional "certification...completed"
  and self-flagged "remaining an open point"/"remains an open question."

0 false positives on the 6 hard negatives in that battery.

## Historical benchmarks

Not re-run individually in Phase 0 — Step 4A.9's Section (regression sweep)
already confirmed zero selectivity drift on HEAD `1c5d60e`, and HEAD has not
moved since. Will be re-run as part of Phase 8+ regression once hybrid code
lands, to prove the hybrid change itself doesn't drift them.

This baseline is what Phases 12/13/19/20 compare the hybrid architecture
against.
