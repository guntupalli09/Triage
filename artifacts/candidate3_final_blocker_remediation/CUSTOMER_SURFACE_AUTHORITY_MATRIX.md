PHASE 11 — CUSTOMER SURFACE AUTHORITY MATRIX

Controlled cases used (see `AUTHORITATIVE_DOCUMENT_STATE.md` for the exact reproduction):
CASE 1: `overall_risk="low"`, policy state `REQUIRES_REVIEW` → aggregated `REQUIRES_REVIEW`.
CASE 2: `overall_risk="low"`, interaction state `ESCALATE` → aggregated `HAS_CRITICAL_INTERACTION`.
CASE 3: `overall_risk="low"`, evaluation error → aggregated `REQUIRES_REVIEW`.

| Surface | Reads document_state? | Shows correct non-clean signal for all 3 cases? |
|---|---|---|
| Review page | Yes (pre-existing) | Yes |
| Dashboard | Yes (pre-existing) | Yes |
| History | Yes (pre-existing) | Yes |
| Full Report | Yes (fixed this mission) | Yes — NEEDS ATTENTION badge added next to the risk label |
| PDF export | Yes (fixed this mission, all 3 call sites) | Yes — red NEEDS ATTENTION line added below "Overall Risk:" |
| Negotiation package | Yes (fixed this mission, cover memo) | Yes — NEEDS ATTENTION notice prepended to the memo text |
| External share | Yes (fixed this mission) | Yes — NEEDS ATTENTION badge added below the risk badge |

No surface still presents LOW/CLEAN as authoritative when the aggregated state is non-clean.
BLOCKER REMAINS: **No.**
