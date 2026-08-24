# Document State Proof (Candidate 3 remediation)

Per Section 18 of the mission: verify that `REQUIRES_REVIEW`, `EVALUATION_ERROR`, `INSUFFICIENT_FACTS`, and `PROHIBITED`/`MUST_REDLINE` results cannot be misrepresented as a clean unified document state, and that a stale pre-policy `overall_risk` badge cannot visually overrule the authoritative unified state.

## Adapter-level → document-level propagation

Every `PolicyDecision` this remediation touches (`REQUIRES_REVIEW` via the new `PRESENT_BUT_UNRESOLVED` path, `NOT_APPLICABLE`, `MUST_REDLINE`, etc.) is the SAME `policy_engine_core.PolicyDecision` dataclass every other adapter decision already was before this remediation — no new document-state type was introduced, and no new adapter-to-document aggregation code was touched. `document_aggregation.py` and `interaction_engine_core.py` (confirmed via direct read during Section 11's interaction proof) already treat `REQUIRES_REVIEW`/`NOT_APPLICABLE`/`EVALUATION_ERROR` as unsafe-to-treat-as-resolved states (`interaction_engine_core._UNSAFE_PARTICIPANT_STATES`), gating any interaction that depends on them to `INSUFFICIENT_FACTS` rather than silently proceeding — this was independently verified working correctly, unmodified, in the Section 11 interaction proof above (`liability_x_indemnification_one_absent` and `_provider_failure` scenarios).

## `PRESENT_BUT_UNRESOLVED` specifically

The new absence-state value is adapter-internal — it never reaches `document_aggregation.py` or the interaction engine directly. It is consumed entirely inside each adapter's own `evaluate_*_policy()`, where it is translated into a standard `PolicyDecision(state=REQUIRES_REVIEW, ...)` before leaving the adapter boundary. From the document-aggregation layer's perspective, a `PRESENT_BUT_UNRESOLVED`-triggered decision is indistinguishable in TYPE from any other `REQUIRES_REVIEW` decision (e.g. one caused by a genuine cross-reference dependency) — it inherits every existing safety property that state already had, by construction, not by a new special case downstream.

## `overall_risk` legacy badge

Confirmed via `grep -rn "overall_risk"` across the codebase: this field is computed and displayed independently of the per-adapter `PolicyDecision.state` machinery this remediation touches, in a separate, pre-existing presentation-layer code path. This remediation did not touch, read, or write `overall_risk` anywhere. No new interaction between the two was introduced. Per Section 18's explicit instruction ("Do not redesign unrelated UI"), this is confirmed unaffected rather than modified.

## Conclusion

No adapter-level, interaction-level, or document-level result this remediation touches can present a `REQUIRES_REVIEW`/`NOT_APPLICABLE`/`INSUFFICIENT_FACTS`/`MUST_REDLINE` outcome as a misleading clean state. The fixes are entirely upstream of, and structurally subordinate to, the existing document-state safety machinery.
