"""Step 4B document-level aggregation — a pure function computing an
explicit, authoritative document-level review state from the three
independent, already-persisted fact sources (Contract.overall_risk,
Contract.policy_decisions_json, Contract.interaction_decisions_json),
without recomputing or overriding any of them.

See artifacts/step4b/document_aggregation_spec.md for the full state model
and the mode-behavior investigation this is built on.

FALSE-CLEAN INVARIANT: this function must never report a state calmer than
what its own inputs support. It never guesses, infers, or upgrades an
unresolved/missing input into a clean one -- an input that is absent
(policy_decisions is None, e.g. cutover with no resolvable playbook) is
itself a signal (CONFIGURATION_UNRESOLVED), never silently skipped.

This module is intentionally NOT wired into main.py's dashboard/listing
queries in this increment -- see the spec's Non-Goals section. It is a
pure function over already-computed data, safe to call read-only against
existing rows without any schema change, and is exercised here only by its
own development benchmark.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

DOC_HAS_CRITICAL_INTERACTION = "HAS_CRITICAL_INTERACTION"
DOC_HAS_POLICY_VIOLATION = "HAS_POLICY_VIOLATION"
DOC_REQUIRES_REVIEW = "REQUIRES_REVIEW"
DOC_CONFIGURATION_UNRESOLVED = "CONFIGURATION_UNRESOLVED"
DOC_CLEAN = "CLEAN"
DOC_CLEAN_LEGACY_ATTENTION = "CLEAN_LEGACY_ATTENTION"

# Ordered most-to-least severe -- first match in aggregate_document_state wins.
_STATE_PRECEDENCE = (
    DOC_HAS_CRITICAL_INTERACTION,
    DOC_HAS_POLICY_VIOLATION,
    DOC_REQUIRES_REVIEW,
    DOC_CONFIGURATION_UNRESOLVED,
)

_POLICY_VIOLATION_STATES = {"PROHIBITED", "MUST_REDLINE", "ESCALATE", "NEGOTIATE"}
_POLICY_REVIEW_STATES = {"REQUIRES_REVIEW", "EVALUATION_ERROR"}
_INTERACTION_CRITICAL_STATES = {"ESCALATE"}
_INTERACTION_REVIEW_STATES = {"REQUIRES_REVIEW", "INSUFFICIENT_FACTS", "EVALUATION_ERROR"}


def _interaction_is_genuinely_inapplicable(decision: Dict[str, Any], policy_decisions: Optional[Dict[str, Any]]) -> bool:
    """An INSUFFICIENT_FACTS interaction whose EVERY missing/unsafe
    participating clause type is entirely absent from this document's own
    policy_decisions (never evaluated at all -- e.g. the playbook has no
    ACTIVE position for that clause type, see policy_enforcement.
    evaluate_active_policies: "absence of an ACTIVE position ... clause
    type is simply skipped") means this rule's own participants were never
    part of this document's applicable policy set -- no interaction is
    possible here, structurally, not merely uncertain. Distinguished from
    a participant that WAS evaluated but came back NOT_APPLICABLE/
    REQUIRES_REVIEW/EVALUATION_ERROR (present as a key in policy_decisions,
    just unsafe to reason over) -- that case is genuine uncertainty and
    must still escalate to document-level REQUIRES_REVIEW.

    Root-caused via benchmarks/step4b_phaseA_multipolicy_document_benchmark.py:
    a document covered by a playbook lacking e.g. an SLA/Insurance/Payment-
    Terms position would otherwise always show REQUIRES_REVIEW purely from
    interaction rules needing those uncovered clause types -- never a
    false-clean/wrong-authority defect (INSUFFICIENT_FACTS is always the
    safe direction), but a material selectivity defect that would make the
    document-level REQUIRES_REVIEW state nearly universal for any playbook
    not covering all 6 interaction-participating clause types."""
    missing = decision.get("missing_clause_types") or []
    if not missing:
        return False
    pd = policy_decisions or {}
    return all(ct not in pd for ct in missing)


def _interaction_review_reasons(interaction_decisions: Optional[Dict[str, Any]], policy_decisions: Optional[Dict[str, Any]]) -> list:
    reasons = []
    for interaction_id, decision in (interaction_decisions or {}).items():
        state = decision.get("state")
        if state not in _INTERACTION_REVIEW_STATES:
            continue
        if state == "INSUFFICIENT_FACTS" and _interaction_is_genuinely_inapplicable(decision, policy_decisions):
            continue
        reasons.append(f"interaction {interaction_id} state={state}")
    return reasons


def aggregate_document_state(
    overall_risk: Optional[str],
    policy_decisions: Optional[Dict[str, Any]],
    interaction_decisions: Optional[Dict[str, Any]],
    mode: str,
) -> Dict[str, Any]:
    """Returns {"document_state": <one of the 6 states>, "reasons": [...]}.

    `policy_decisions` / `interaction_decisions` are the raw
    Contract.policy_decisions_json / Contract.interaction_decisions_json
    dicts (clause_type/interaction_id -> decision dict with a "state" key),
    exactly as persisted -- never re-derived from contract_text here.
    `mode` is the enforcement mode active when this contract was reviewed
    (policy_enforcement.get_enforcement_mode()'s return value) -- passed in
    explicitly rather than read from the environment inside this function,
    so a caller can evaluate historical contracts against the mode that
    was actually in effect for them (they may not match today's mode).
    """
    reasons = []

    for interaction_id, decision in (interaction_decisions or {}).items():
        if decision.get("state") in _INTERACTION_CRITICAL_STATES:
            reasons.append(f"interaction {interaction_id} state={decision.get('state')}")
    if reasons:
        return {"document_state": DOC_HAS_CRITICAL_INTERACTION, "reasons": reasons}

    for clause_type, decision in (policy_decisions or {}).items():
        if decision.get("state") in _POLICY_VIOLATION_STATES:
            reasons.append(f"policy {clause_type} state={decision.get('state')}")
    if reasons:
        return {"document_state": DOC_HAS_POLICY_VIOLATION, "reasons": reasons}

    for clause_type, decision in (policy_decisions or {}).items():
        if decision.get("state") in _POLICY_REVIEW_STATES:
            reasons.append(f"policy {clause_type} state={decision.get('state')}")
    reasons.extend(_interaction_review_reasons(interaction_decisions, policy_decisions))
    if reasons:
        return {"document_state": DOC_REQUIRES_REVIEW, "reasons": reasons}

    if mode == "cutover" and policy_decisions is None:
        return {"document_state": DOC_CONFIGURATION_UNRESOLVED,
                "reasons": ["cutover mode active but no policy_decisions resolved for this contract"]}

    if overall_risk == "high":
        return {"document_state": DOC_CLEAN_LEGACY_ATTENTION,
                "reasons": ["no deterministic policy/interaction finding, but legacy overall_risk=high"]}

    return {"document_state": DOC_CLEAN, "reasons": []}
