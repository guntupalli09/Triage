# Step 4B Phase 1 — System-Level Result Model

## Clause-level state vocabulary (already well-defined, confirmed in code)

`PolicyDecision.state` (`policy_engine_core.py`): `ACCEPT | ACCEPT_WITH_NOTE
| NEGOTIATE | MUST_REDLINE | PROHIBITED | ESCALATE | REQUIRES_REVIEW |
NOT_APPLICABLE`.

`review_queue.py` (confirmed by direct reading, not inferred) already keeps
these correctly distinct:
- `PASSED_STATES = (ACCEPT, ACCEPT_WITH_NOTE)` — the sole definition of
  "passed."
- `NOT_APPLICABLE` — clause found not to apply; distinct from "passed" and
  from "not evaluated."
- A clause type absent from `policy_decisions` entirely (no ACTIVE policy
  covers it, or the current mode never evaluates it) is neither "passed"
  nor "not applicable" — it is invisible to `build_review_queue`, which is
  itself a finding (see Open Item 5 below).
- `EVALUATION_ERROR` — the adapter itself raised; explicitly excluded from
  the passed/not-applicable scan (`evaluation_error_clause_types` guard in
  `build_review_queue`), never silently absorbed into "passed."

This vocabulary already satisfies the letter of Step 4B's Phase 1
requirement at the CLAUSE level: `NOT_APPLICABLE` (provision genuinely
doesn't apply) is never collapsed with "clause never evaluated" (invisible
by omission, not a false NOT_APPLICABLE) or with `EVALUATION_ERROR`
("provision verified acceptable" vs. "verifier failed").

## Interaction-level state vocabulary (already well-defined, confirmed in code)

`InteractionDecision.state` (`interaction_engine_core.py`): `ESCALATE |
NEGOTIATE | REQUIRES_REVIEW | ACCEPT_WITH_NOTE | NOT_TRIGGERED |
INSUFFICIENT_FACTS | EVALUATION_ERROR`.

- `NOT_TRIGGERED` — every participant present and resolved; the rule's
  predicate looked and found nothing (recorded, not dropped — confirmed:
  `evaluate()` appends one `InteractionDecision` per registered rule,
  every review, unconditionally).
- `INSUFFICIENT_FACTS` — distinct from `NOT_TRIGGERED` specifically so it
  is never mistaken for "clean" (confirmed via the module's own docstring
  and `_gate_participants` logic — this is the concrete code-level
  instance of Step 4B's "REQUIRES_REVIEW upstream must not disappear
  merely because another policy passes" principle, already implemented
  for the interaction layer specifically).

## Document-level state — THE GAP

**No document-level result-state field exists that incorporates
`policy_decisions_json` or `interaction_decisions_json`.**

Traced definitively (not inferred): `Contract.overall_risk` (`low | medium
| high`) is the only document-level summary field found anywhere in
`main.py`. It is set exactly once per review, from `rule_engine.analyze
(contract_text)["overall_risk"]` — computed inside `run_analysis()`, which
runs and returns BEFORE `policy_enforcement.apply_policies_for_review()` is
even called (main.py: `run_analysis` call at line 1358; `apply_policies_
for_review` call at line 1392). Confirmed by exhaustive search: every
assignment of `overall_risk` in `main.py` (6 total) reads it from
`analysis["overall_risk"]` — none reads from `policy_result` or
`interaction_decisions` in any form, and nothing downstream recomputes,
adjusts, or merges it with the policy/interaction layer's output.

**This field is actively used as a document-level verdict in production
UI/query paths**, not merely stored inertly:
- `main.py:1203` — a dashboard query filters contracts by
  `Contract.overall_risk == "high"` to build a "high risk contracts" list.
- `main.py:1231` — a listing endpoint filters by `overall_risk` as a
  request parameter.
- `main.py:1590-1592` — a UI badge/label is driven directly by
  `overall_risk`.

**Concrete failure scenario this enables** (a false-clean document by
construction, not merely by adversarial phrasing): a contract with
entirely benign language from the LEGACY rule engine's own pattern list
(`overall_risk = "low"`), but which — in `cutover` mode — produces an
`ESCALATE`-state `PolicyDecision` (e.g. `PROHIBITED` unlimited liability)
or an `ESCALATE`-kind `InteractionDecision` (e.g. Rule 1's flagship
IP-uncapped-liability-with-indemnity CONFLICT), would still show
`overall_risk = "low"` and would NOT appear in the "high risk contracts"
dashboard filter at `main.py:1203`, even though the review page itself
(which separately renders `ReviewQueueSummary.needs_attention` and
`.interactions_needing_attention`) would show the exception. **The
per-review page is not necessarily false-clean (both signals are present
there); the cross-review dashboard/listing surface is false-clean by
construction for any query keyed on `overall_risk` alone.**

This is exactly the class of defect Step 4B Phase 12 (False-Clean Document
Test) is designed to catch, found here by static tracing before any
document-level test corpus was built — it does not require an adversarial
document to demonstrate; it is a direct, provable consequence of
`overall_risk`'s computation order, confirmed by reading the code, not by
running a test case against it (though Phase 12 must still build the
document-level corpus to measure the FULL false-clean rate across all
mechanisms, not just this one).

## Recommendation carried into Phase 11 (Final Review Aggregation)

Step 4B's Phase 11 cannot define a deterministic aggregation truth table
until this gap is resolved, because there is currently no document-level
field to aggregate INTO. Recommended (not yet implemented — this is a
Phase 1 finding, not a Phase-1-authorized production change): a new
document-level field, computed AFTER `apply_policies_for_review` returns,
as a pure function of `(rule_engine overall_risk, policy_decisions,
interaction_decisions)` — never overwriting `overall_risk` itself (which
remains a legitimate, narrower "what did the legacy pattern list find"
signal), but a new, explicitly-named field (e.g.
`Contract.review_verdict`) whose truth table is exactly what Phase 11
must specify: any `PROHIBITED`/`ESCALATE`-state policy decision or
`ESCALATE`-kind interaction finding forces the verdict away from
"clean," `REQUIRES_REVIEW`/`INSUFFICIENT_FACTS` anywhere forces it away
from "clean" without necessarily being a "violation," and the dashboard/
listing surfaces at `main.py:1203`/`:1231` must be migrated to filter on
the new field, not `overall_risk` alone, once it exists.

## Open items carried forward

1. Whether `NOT_APPLICABLE` at the clause level is currently distinguished
   in the UI from "never evaluated" (invisible-by-omission) — code-level
   distinction exists in `review_queue.py`; UI-level rendering not yet
   traced (`templates/review.html` not read in this pass).
2. The `evaluator.py` LLM-generated `overall_risk` field in its OWN output
   schema (`_build_prompt`'s target JSON includes `"overall_risk"`) is
   forcibly overwritten by the deterministic value immediately after the
   LLM call returns (`evaluator.py:328`, `result["overall_risk"] =
   overall_risk`) — confirmed the LLM cannot override this field, but this
   is the SAME legacy-rule-engine-only `overall_risk`, so the LLM
   explanation layer inherits the same blindness to policy/interaction
   decisions described above, which is itself relevant to Phase 18
   (Explanation Fidelity) once that phase is reached.
