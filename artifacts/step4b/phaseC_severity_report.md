# Step 4B Phase C — Severity / Prioritization

## Read-only trace

Searched the whole non-test/non-experiment codebase for `severity`, `tier`,
`priority`, `risk`, `rank`, and `escalation level` structures. Three real
production consumers of a per-finding `severity` string were identified as
touching the findings/attention pipeline; everything else traced was
either purely presentation (three-score `risk_dashboard.py` display
scores; PDF headline labels) or a separate, already-governed legacy
system with its own change-control process (`severity_scoring.py`'s
"Severity Framework v1.1," which feeds only the legacy `overall_risk`
computation and is explicitly out of scope per its own module docstring —
"Any issue discovered while using this engine that appears to require
changing the frozen factors or ceiling rules ... must NOT be patched here").

1. **`main.build_enhanced_issues`** — sorts `all_issues` by
   `(severity_order.get(severity, 9), title)`. Presentation ordering only;
   confirmed no truncation follows the sort.
2. **`review_queue.build_review_queue`** — confirmed by direct code read
   (`review_queue.py:39-44`'s own comment: "never inferred from severity
   text or document position") to order/classify strictly by `TIER_RANK`,
   keyed on `policy_state`. The word "severity" appears in this file only
   in that one comment — the field itself is never read.
3. **`document_aggregation.aggregate_document_state`** — confirmed by
   direct code read: the word "severity" does not appear anywhere in
   `document_aggregation.py`. It reads only `state`/`missing_clause_types`
   keys.

`_STATE_SEVERITY` (`policy_enforcement.py:457`) is one-directional
(`state → severity` label, e.g. `PROHIBITED → "critical"`) — confirmed no
reverse path exists anywhere (severity never selects or gates a `state`).

## Benchmark

`benchmarks/step4b_phaseC_severity_benchmark.py` — 114 cases (exceeds the
≥100 target), calling all three real consumers directly, covering every
named family: same finding/same evidence/same rule/multiple findings with
crossed severities, low+high, critical+low, REQUIRES_REVIEW+low-violation,
REQUIRES_REVIEW+critical-violation, interaction+base-finding with crossed
severities, same-severity+different-policies, same-severity+different-
evidence, missing/unknown/malformed severity (including non-hashable
types), legacy-risk-high+low-severity-finding, legacy-risk-low+critical-
severity-finding.

## PRE result and a genuine crash found

First run raised `TypeError: unhashable type: 'dict'` inside
`build_enhanced_issues`'s own sort key — not a soft mismatch, a hard
crash. Root cause: `severity_order.get(x.get("severity", "low"), 9)`
calls `dict.get()` with the finding's raw `severity` value as the lookup
key; a non-hashable value (a `dict`/`list` — deliberately included in the
`malformed-severity` family to test "malformed severity where production
accepts external/stored values," per the task's own instruction) raises
inside `dict.get()` itself, before the `.get()`'s own default-value
fallback ever has a chance to apply. Because `severity` is read back from
persisted `findings_json` (JSON-typed, so nothing at the schema level
guarantees it stays a string across all historical/legacy rows or a
future bug elsewhere), this is a real reachable failure mode — and
because it crashes inside a `.sort()` over the WHOLE list, it would 500
the entire contract report (detail page, review page, and shared report,
all three consumers of `build_enhanced_issues`), not merely drop or
mis-order the one malformed finding. A severity-metadata bug turning into
a full-page outage is exactly the kind of "system around the fact"
failure this phase exists to catch, even though it's an availability
defect rather than a wrong-authority one.

## Fix

`main.py`, `build_enhanced_issues`: wrapped the severity lookup in a
`_severity_rank()` helper that catches `TypeError` from a non-hashable
value and falls back to the same "sorts last" rank (`9`) already used for
any other unrecognized severity string — matching the function's own
existing intent, just made robust to a type it previously couldn't handle
at all. General, minimal (defensive `try/except` around one lookup, plus
`str()`-coercing the title tie-break for symmetry). No change to which
findings are included or how they're deduplicated (Phase B's fix,
untouched).

## POST

**114/114 (100%)**. Both hard gates PASS:
- `severity_induced_authoritative_state_loss = 0`
- `material_finding_suppression = 0`
- (reported separately, not an authority failure) `wrong_ordering = 0`

## Conclusion

The severity-authority invariant was already satisfied by design across
all three real consumers — `review_queue.py` and `document_aggregation.py`
never read `severity` at all, and `build_enhanced_issues` only uses it for
display order, never for inclusion/suppression. The one genuine defect
found (an availability crash on a malformed value, not an authority
violation) was root-caused, fixed generally, and verified clean. Per the
task's own instruction ("If PRE is clean [of authority defects]: do not
modify production [beyond what's needed]"), no other change was made —
in particular, `review_queue.py`, `document_aggregation.py`, and the
legacy `severity_scoring.py` framework are all untouched.

## Regression

- Full `pytest tests/`: **1975 passed, 14 skipped, 0 failed**.
- Phase A 200-doc benchmark: 200/200, unchanged.
- Phase B 108-case benchmark: 108/108, unchanged.
- 104-case aggregation, 213-case interaction, 54-case historical, 18-case
  real-app integration suites: all unchanged.
- Step 4A.11 393-case and 167-case corpora: both still WC=0, all hard
  gates PASS — no Step 4A regression.
