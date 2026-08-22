# Step 4B Phase O — Full Pre-Freeze Regression

Every suite the standing instructions named, re-run in this session
against the current tree (HEAD at the time of this report: `173652b`,
Phase N). **Zero unexplained regressions.**

## Step 4A.11 legacy corpora (regression evidence, locked corpora)

| Suite | Result | Hard gates |
|---|---|---|
| Locked 393-case final corpus (`scripts/step4a11_run_final_corpus.py`) | CA=196 CR=52 FE=139 WC=0 SM=7, Clean-Verified Recall 58.4% (≥44.5% target) | `false_structural_establishment=0` PASS, `wrong_ownership=0` PASS, `SM=7` — **matches the originally-disclosed, already-accepted freeze value exactly** (`artifacts/step4a11_phase6_freeze/STEP_4A11_FINAL_REPORT.md`: "CA=196 CR=52 FE=139 WC=6 SM=7 ... None of the 7 SM cases are SM-CRITICAL"); `semantic_authority_diffs=0` PASS; `determinism=100%` (5x repeat) PASS |
| Fresh 167-case remediation-validation corpus (`scripts/step4a11_run_remediation_validation_corpus.py`) | CA=108 CR=12 FE=47 WC=0, Automation Recall 69.7% | `wrong_ownership/wrong-role-clean=0` PASS, `semantic_authority_diffs=0` PASS, `determinism=100%` PASS |

## Interaction / integration suites (run inside `pytest tests/`)

- **213-case interaction adversarial corpus** (`benchmarks/interaction_corpus.py` + `benchmarks/run_interaction_benchmark.py`, wrapped by `tests/test_interaction_benchmark_gate.py`): `false_interactions=0`, `missed_high_risk=0`, `false_safe=0`, `determinism_pct=100.0`, state accuracy 100% — all pass as part of the pytest run below.
- **Historical/legacy interaction enforcement suite** (`tests/test_interaction_enforcement.py`, `tests/test_interaction_review_http.py`): all pass as part of the pytest run below.
- **104-case document-aggregation benchmark** (`scripts/step4b_run_document_aggregation_benchmark.py`, re-run standalone this phase): 104/104, hard gate `post_false_clean=0` PASS.
- **18-case real-app dashboard/history integration suite** (`tests/test_step4b_dashboard_listing_integration.py`, exercised end-to-end via `TestClient` + real DB rows, not the pure function alone): all pass as part of the pytest run below.

## Full pytest

`pytest tests/`: **1975 passed, 14 skipped, 0 failed** — includes all 12
per-adapter benchmark gates (`test_*_benchmark_gate.py`), the interaction
gate, the dashboard/history integration suite, and every other test file
in the repository. Re-run fresh this phase; identical result to every
prior phase's regression check this session.

## Every Step 4B phase benchmark (A–N), re-run fresh this phase

| Phase | Cases/Scenarios | Result | Hard gates |
|---|---|---|---|
| Document-aggregation (pre-Phase-A) | 104 | 104/104 | `post_false_clean=0` PASS |
| A — multi-policy | 200 | 200/200 | 5/5 PASS |
| B — deduplication | 108 | 108/108 | 2/2 PASS |
| C — severity | 114 | 114/114 | 2/2 PASS |
| D — aggregation stress | 158 | 158/158 | 7/7 PASS |
| E — compound | 150 | 150/150 | 6/6 PASS |
| F — governance | 174 | 174/174 | 13/13 PASS |
| G — segment | 191 | 191/191 | 8/8 PASS |
| H — replay | 210 scenarios / 561 executions | 210/210 | 10/10 PASS |
| I — explanation fidelity | 150 | 150/150 | 4/4 PASS |
| J — prompt injection | 158 (Layer 1 detection 44.4%, disclosed, not gated) | 158/158 (Layer 2) | 4/4 PASS |
| K — failure mode | 130 | 130/130 | 4/4 PASS |
| L — fresh battery | 350 | 350/350 | 4/4 PASS |
| M — trust audit | 254 decisions audited | n/a (audit, not pass/fail) | 2/2 PASS |
| N — false absence | 163 | 163/163 | 1/1 PASS |

**Total Step 4B development-phase case count: 2,563** (104+200+108+114+158+150+174+191+561+150+158+130+350+254+163, counting Phase H's individual replay executions), plus the two Step 4A.11 legacy corpora (393+167=560) and the full pytest suite (1975+14).

## Artifact-noise note (not a regression)

Re-running `scripts/step4b_run_phaseF_governance_benchmark.py` produced a
diff in `artifacts/step4b/phaseF_governance_results.json` limited entirely
to Python object `repr()` memory addresses embedded in a few cases' free-
text `notes` field (e.g. `<models.PolicyPosition object at 0x7f...>`) —
non-deterministic per-process addresses, not a change in `passed`, hard
gate counts, or any authoritative content. Discarded (`git checkout --`)
rather than committed, since it is not a real result change.

## Conclusion

**Zero unexplained regressions** across the full legacy corpora, all
pytest-wrapped suites, and all fourteen Step 4B development-phase
benchmarks. The one non-zero legacy metric (`SM=7` in the locked 393-case
corpus) is the exact, previously-disclosed, already-accepted value from
the original Step 4A.11 freeze — confirmed unchanged, not a new finding.
Full pre-freeze regression is clean; proceeding to Phase P (candidate
freeze) evaluation.
