# REGRESSION_REPORT

Full suite: `python3 -m pytest tests/ -q -p no:cacheprovider --continue-on-collection-errors`

## Final counts (this branch, HEAD `aa0e1ef` and after)

| Category | Count | Detail |
|---|---|---|
| PASS | 1259 | includes 117 new fact-admission tests (see TARGETED_RESULTS.md) + all pre-existing adapter/core suites, unchanged |
| FAIL | 10 | **all pre-existing, unrelated to this work** — see below |
| SKIP | 1 | pre-existing, unrelated |
| ENVIRONMENT BLOCKED (collection error) | 45 files | **all pre-existing, unrelated** — see below |
| NEW REGRESSION | **0** | |

## FAIL detail (10) — pre-existing, confirmed unrelated

- `test_override_learning.py::TestPatternsForPlaybookDBIntegration::
  test_scoped_to_one_playbook_and_finds_real_pattern` — requires a live DB
  connection this sandbox doesn't have.
- `test_production_secrets.py` (9 cases) — all require importing `main.py`
  in a subprocess, which requires `fastapi` and `python-dotenv`, neither
  installed in this sandbox (confirmed via direct reproduction:
  `ModuleNotFoundError: No module named 'dotenv'`).

None of these 10 touch `fact_admission.py`, any `*_policy_engine.py` file,
`document_aggregation.py`, `interaction_engine_core.py`, `main.py`'s
review/dashboard routes, or `upload_security.py` — confirmed by reading
each failure's traceback (all are environment/dependency failures at
import or DB-connection time, not assertion failures against this
session's changes).

## ENVIRONMENT BLOCKED detail (45 files) — pre-existing, confirmed unrelated

All 45 fail at **collection** (before any test body runs) with
`ModuleNotFoundError` for one of: `fastapi`, `python-docx`, `dotenv`, or a
`pyo3_runtime.PanicException` from the `cryptography` package's Rust
extension inside this sandbox. Reproduced directly for a sample:
`tests/test_docx_export.py` → `ModuleNotFoundError: No module named
'docx'`; `tests/test_csrf.py` / `tests/test_demo_routes.py` →
`ModuleNotFoundError: No module named 'fastapi'`. This sandbox does not
have the project's full dependency set installed (confirmed:
`pip install pytest` was required just to run any test at all). This is a
pre-existing environment limitation, not something introduced or
discoverable-as-different by this session's changes — the same 45 files
failed identically before any Phase 2 adapter work began (verified by
running the full suite at the start of this session, before touching any
adapter, and recording the identical file list).

**Honesty note**: this means `interaction_enforcement.py`,
`policy_enforcement.py`'s own test suite (`test_phase4_policy_enforcement.py`,
`test_phase4_rollback.py`), `review_queue.py`, and the dashboard/history/
review-page wiring (`test_step4b_dashboard_listing_integration.py`) could
**not** be regression-tested end-to-end in this sandbox. Their unit-level
logic that doesn't require `fastapi`/DB was exercised indirectly (e.g.
`interaction_engine_core.py`'s own suite, which has no such dependency,
passed), but the full HTTP-route-level regression for `main.py`'s changes
in this session (the review-page badge, the ingestion gate) was verified
only via Jinja2 template parsing, `ast.parse`, and manual code review —
**not** via an actual running server. This is a real verification gap,
not claimed as closed.

## Conclusion

Zero new regressions from this session's 12-adapter integration work.
All pre-existing failures/errors were independently reproduced and
confirmed environment-caused, not logic defects this work introduced or
uncovered.
