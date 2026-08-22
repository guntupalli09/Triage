# Step 4B Phase N — False-Clean / False-Absence Audit

## Method

`scripts/step4b_run_phaseN_false_absence_audit.py`, **163 cases** (exceeds
the ≥150 minimum), calling real production functions throughout
(`document_aggregation.aggregate_document_state`,
`interaction_engine_core.evaluate`, `main.build_enhanced_issues`,
`main._needs_attention`/`_document_state_for_contract`,
`policy_enforcement.resolve_segment_position`). Every case is framed
around one question: **did the system say/imply CLEAN because it failed
to notice something?** — distinct from ordinary accuracy testing
(Phases A/D/E/L), which asks "did it compute the right answer."

Families:

1. **Attention-filter omission (12)** — direct audit of the dashboard/
   history layer's own consumer functions across all 6 document states.
   Includes a targeted check that `CLEAN_LEGACY_ATTENTION` — deliberately
   excluded from `main._DOCUMENT_MATERIAL_STATES`/`_needs_attention` by
   design — remains independently visible via `overall_risk == "high"`
   (the dashboard template's own "High" badge), confirmed directly rather
   than merely trusted from the trace: this is a non-redundant design
   choice (the row already shows "High" from `overall_risk`; a second
   "Needs Attention" badge would be redundant), never a suppression.
2. **Clause false absence (55)** — deterministically generated sparse
   coverage (1–11 of 12 clause types) with a randomly-placed violation:
   confirms sparse coverage of unrelated clause types never suppresses a
   real violation present elsewhere in the same document.
3. **Interaction false absence (14)** — for every one of the 7
   `LAUNCH_CATALOG` rules, two paired cases: (a) one participant present
   but in an unsafe state (`REQUIRES_REVIEW`) — genuine uncertainty, must
   still block CLEAN via `INSUFFICIENT_FACTS`; (b) every participant
   entirely uncovered by the playbook — genuinely inapplicable, correctly
   *allowed* to resolve CLEAN, verified as a deliberate, checked
   allowance (the Phase D-established distinction), not an accidental gap.
4. **Finding suppression (30)** — 2–6 distinct violations per case at
   different locations, confirming `main.build_enhanced_issues` never
   drops or collides any of them (no accidental dedup, no title overwrite
   hiding one finding behind another).
5. **Governance omission (20)** — no active playbook (`policy_decisions
   is None`, cutover mode) must never resolve to CLEAN.
6. **Segment-selection omission (20)** — no matching segment among
   candidates must resolve to `None` (clause type simply skipped), never
   a guessed fallback.
7. **Dependency-failure-as-absence (12)** — re-verifies Phase K's fix
   under this phase's false-absence framing: a corrupted policy/
   interaction decision entry must never be misread as "no issue."

## PRE

162/163 (one benchmark-authoring mistake found and corrected): case
`attention-filter-3` originally used `("low", None, None, True)` intending
to test "cutover mode with no resolvable policy → CONFIGURATION_UNRESOLVED."
But `main._document_state_for_contract` only infers cutover mode from
`interaction_decisions_json is not None` — with `interaction_decisions_json`
also `None`, the function correctly (per its own documented, deliberately
conservative design) treats the row as ambiguous legacy/shadow-shaped and
does **not** escalate. This is documented, intended behavior, not a
production defect. Corrected the case to
`interaction_decisions_json={}` (the genuine positive signal of a
cutover-shaped review with nothing else to disclose) alongside
`policy_decisions_json=None`, which does correctly escalate.

## POST

**163/163 passed.** Hard gate `dangerous_false_absence_to_clean == 0` →
**PASS**.

## No production defect found; no production file changed

Every family traced to an already-correct mechanism from Phases D/F/G/K:
sparse coverage's "absence means skipped" semantics, the genuinely-
inapplicable/genuinely-uncertain interaction distinction, governance/
segment fail-closed behavior, and the Phase K malformed-entry hardening.
Phase N's contribution is auditing these specifically through a
false-absence lens and through the dashboard/history consumer layer
directly (not previously exercised end-to-end from that entry point) —
confirming no omission exists there either.

## Regression

No production file modified this phase. Full `pytest tests/`: **1975
passed, 14 skipped, 0 failed** (unchanged).

## Conclusion

Across every false-absence family audited — clause coverage gaps,
interaction participant gaps, finding collisions, governance/segment
omission, dependency failure, and the dashboard's own attention filter —
the system never silently resolves to CLEAN by failing to notice
something. The one CLEAN-permitting path found (genuinely inapplicable
interactions) is a deliberate, previously-established, and now
re-confirmed design choice, not an omission.
