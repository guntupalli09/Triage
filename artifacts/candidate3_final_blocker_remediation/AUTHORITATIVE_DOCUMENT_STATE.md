BLOCKER 5 — ONE AUTHORITATIVE DOCUMENT STATE

## Design decision: reuse, don't rebuild

`document_aggregation.aggregate_document_state(overall_risk, policy_decisions_json,
interaction_decisions_json, effective_mode)` already existed and was already proven correct
(pure, precedence-ordered, cannot report CLEAN while any actionable state exists in its own
inputs — confirmed by the pre-freeze inspection). `main._document_state_for_contract(contract)`
already wraps it correctly for the dashboard/history/review-page surfaces. Blocker 5 is a
**wiring** fix — reusing this exact existing helper on the four previously-unwired surfaces —
not a new aggregation design.

## Audit of all 9 required surfaces

| Surface | BEFORE SOURCE | AFTER SOURCE | AUTHORITATIVE? |
|---|---|---|---|
| 1. Single-contract review page (`review.html`) | `document_state` via `_document_state_for_contract` | unchanged | Yes (already correct) |
| 2. Dashboard | `document_states` dict via `_document_state_for_contract` per contract | unchanged | Yes (already correct) |
| 3. Review/history listing | `document_states` dict via `_document_state_for_contract` per contract | unchanged | Yes (already correct) |
| 4. Full Report & Audit Trail (`results.html`) | `overall_risk` only | `overall_risk` + `document_state` (NEEDS ATTENTION badge) | **Fixed** |
| 5. PDF export (`_build_pdf_bytes`, all 3 call sites: single download, batch zip, negotiation-package cover memo indirectly) | `overall_risk` only | `overall_risk` + `document_state` param (NEEDS ATTENTION line in red) | **Fixed** |
| 6. Negotiation package (`build_cover_memo_text`) | rule-engine findings only | `document_state` param prepends a NEEDS ATTENTION notice | **Fixed** |
| 7. External share link (`shared_report.html`) | `overall_risk` only | `overall_risk` + `document_state` (NEEDS ATTENTION badge) | **Fixed** |
| 8. API responses exposing overall risk/status | Internal analytics/audit-log metadata only (`overall_risk` in telemetry dicts) — not customer-facing | Unchanged — internal telemetry, not a customer authority surface | N/A (not a customer surface) |
| 9. Anonymous, token-based pay-per-use flow (`/download-pdf`, `/demo`, `/demo/start`) | `overall_risk` only, no Contract row, no policy enforcement ever runs | Unchanged | N/A — no aggregated state exists for this flow (never runs `apply_policies_for_review`); passing `document_state=None` here is accurate, not a gap |

## Required test: legacy LOW + non-clean policy/interaction/error state

Directly exercised (not through a route, since this sandbox lacks several unrelated
dependencies needed to boot the full FastAPI app — see `FULL_REGRESSION.md`):

```python
import document_aggregation as da
import review_workflow as rw

# CASE 1: legacy LOW + policy REQUIRES_REVIEW
r1 = da.aggregate_document_state('low', {'limitation_of_liability': {'state': 'REQUIRES_REVIEW'}}, None, 'shadow')
# -> 'REQUIRES_REVIEW'

# CASE 2: legacy LOW + interaction escalation
r2 = da.aggregate_document_state('low', {'limitation_of_liability': {'state': 'ACCEPT'}}, {'ix1': {'state': 'ESCALATE'}}, 'cutover')
# -> 'HAS_CRITICAL_INTERACTION'

# CASE 3: legacy LOW + evaluation error
r3 = da.aggregate_document_state('low', {'limitation_of_liability': {'state': 'EVALUATION_ERROR'}}, None, 'shadow')
# -> 'REQUIRES_REVIEW'

memo = rw.build_cover_memo_text('test.pdf', [], {}, document_state=r1['document_state'] if isinstance(r1, dict) else r1)
# memo contains "NEEDS ATTENTION" -> True
```

All three cases resolve to a non-clean authoritative state, and the memo text correctly
surfaces case 1's result. The same `document_state` string drives the identical Jinja
condition (`document_state in ('HAS_CRITICAL_INTERACTION', 'HAS_POLICY_VIOLATION',
'REQUIRES_REVIEW', 'CONFIGURATION_UNRESOLVED')`) on all four newly-wired templates/exports,
copied verbatim from the already-proven-correct `review.html` condition.

## What could not be exercised end-to-end in this sandbox

`main.py` cannot be imported in this sandbox — it requires `stripe` and `fpdf`, neither
installed, and installing every transitive dependency of the full FastAPI application was
outside this mission's scope. Both edited templates were confirmed to parse correctly via
`jinja2.Environment(loader=FileSystemLoader(...)).get_template(...)`, and both edited Python
files (`main.py`, `review_workflow.py`) compile cleanly (`python3 -m py_compile`). The
underlying aggregation and memo-text logic — the actual authoritative-state computation and
the exact conditional the templates use — was verified directly, as shown above. Full
route-level rendering (an actual PDF byte-for-byte render, an actual HTTP response) was not
exercised; this is a pre-existing sandbox limitation (the same missing dependencies already
account for several of the 46 baseline collection errors), not a gap introduced by this fix.
