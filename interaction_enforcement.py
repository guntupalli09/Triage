"""
Interaction Engine V1 — production wiring.

The one integration point named in docs/architecture/
interaction_engine_v1_design.md S11: apply_interaction_rules() is called
from policy_enforcement.apply_policies_for_review() immediately after
apply_active_policies() returns, in cutover mode only (shadow/legacy modes
never assemble a multi-clause decision set to interact over — same scoping
run_shadow_comparison already applies to liability alone). This module adds
no second evaluation path: it consumes the exact List[ClauseEvaluationOutcome]
evaluate_active_policies() already produced for this review, never re-reads
contract text, never calls an extractor, never calls evaluate_*_policy again.

Phase 4: assembles ContractDocumentFacts from outcome-carried legacy extracts
(when present) and passes them into interaction_engine_core.evaluate so
predicates can use structured cross-clause / carve-out facts instead of
relying only on lossy PolicyDecision.category_treatments.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

import interaction_engine_core as ixc
import interaction_rules as ixr
from models import Contract
from policy_enforcement import ClauseEvaluationOutcome

_STATE_SEVERITY = {
    "ESCALATE": "high",
    "REQUIRES_REVIEW": "high",
    "NEGOTIATE": "medium",
    "EVALUATION_ERROR": "high",
}


def decisions_from_outcomes(outcomes: List[ClauseEvaluationOutcome]) -> Dict[str, Any]:
    """The only bridge between policy_enforcement's clause-level output and
    the Interaction Engine: a plain Dict[clause_type, PolicyDecision],
    dropping any outcome whose own evaluation errored (outcome.decision is
    None) — an errored clause is exactly as absent to the Interaction
    Engine as a clause with no ACTIVE position at all; interaction_engine_
    core's own gating (_gate_participants) then further excludes any
    decision whose state is NOT_APPLICABLE/REQUIRES_REVIEW/EVALUATION_ERROR
    from being read by a predicate."""
    return {o.clause_type: o.decision for o in outcomes if o.decision is not None}


def document_facts_from_outcomes(outcomes: List[ClauseEvaluationOutcome]):
    """Assemble ContractDocumentFacts from extracts already attached to outcomes.

    Returns None when neither liability nor indemnification extracts are
    available — evaluate() then behaves as before Phase 4.
    """
    liability_facts = None
    indemnification_facts = None
    for outcome in outcomes:
        if outcome.legacy_facts is None:
            continue
        if outcome.clause_type == "limitation_of_liability" and liability_facts is None:
            liability_facts = outcome.legacy_facts
        elif outcome.clause_type == "indemnification" and indemnification_facts is None:
            indemnification_facts = outcome.legacy_facts
    if liability_facts is None and indemnification_facts is None:
        return None
    from contract_facts.document_assembly import assemble_document_facts_from_legacy

    return assemble_document_facts_from_legacy(
        liability_facts=liability_facts,
        indemnification_facts=indemnification_facts,
    )


def _finding_from_interaction_decision(decision: "ixc.InteractionDecision") -> Optional[Dict[str, Any]]:
    """Builds a synthetic finding shaped like policy_enforcement._finding_
    from_decision, but with finding_type="interaction_decision" (never
    "policy_decision" — review_queue.py switches on this to keep
    interaction rows visually and structurally distinct from ordinary
    clause exceptions, per design doc S9). Only actionable states produce
    a finding; NOT_TRIGGERED/INSUFFICIENT_FACTS are recorded in
    interaction_decisions_json for completeness but never shown as
    something needing attention."""
    if decision.state not in ixc.ACTIONABLE_STATES:
        return None
    return {
        "rule_id": decision.interaction_id, "rule_name": decision.label,
        "title": f"{decision.label} — {decision.state.replace('_', ' ')}",
        "severity": _STATE_SEVERITY.get(decision.state, "medium"),
        "rationale": decision.explanation,
        "matched_excerpt": None, "position": None, "context": None,
        "clause_number": None, "matched_keywords": [], "aliases": [],
        "start_index": None, "end_index": None, "exact_snippet": None, "evidence": None,
        "party_direction": None, "finding_type": "interaction_decision",
        "finding_type_label": "Cross-Policy Interaction", "confidence_breakdown": None,
        "redline": None, "policy_state": decision.state,
        "clause_type": None,
        "interaction_id": decision.interaction_id,
        "interaction_kind": decision.kind,
        "participating_clause_types": list(decision.participating_clause_types),
        "escalate_to": decision.escalate_to,
        "negotiation_ladder": [],
        "policy_source": None, "controlling_provision": None,
        "our_position": None, "counterparty_position": None,
        "evidence_report": decision.render_evidence_report(),
        "required_action": decision.required_action,
        "stale": decision.stale, "stale_reason": decision.stale_reason,
    }


def apply_interaction_rules(
    outcomes: List[ClauseEvaluationOutcome],
    findings_dict: List[Dict[str, Any]],
    *,
    document_facts=None,
) -> Dict[str, Any]:
    """Evaluates the full seven-rule launch catalog against this review's
    already-computed PolicyDecisions, appends a synthetic finding per
    actionable InteractionDecision into findings_dict (mutated in place,
    same contract as policy_enforcement's finding injection), and returns
    the full interaction_decisions dict (every rule, including NOT_
    TRIGGERED/INSUFFICIENT_FACTS outcomes) for Contract.
    interaction_decisions_json. Never raises — a rule-level exception is
    already isolated inside interaction_engine_core.evaluate() (see its
    EVALUATION_ERROR handling); this function has nothing further to
    catch, by construction.

    Phase 4: `document_facts` (optional) are structured ContractDocumentFacts.
    When omitted, they are assembled from outcome.legacy_facts when present.
    """
    decisions = decisions_from_outcomes(outcomes)
    if document_facts is None:
        document_facts = document_facts_from_outcomes(outcomes)
    interaction_decisions = ixc.evaluate(
        decisions, ixr.LAUNCH_CATALOG, document_facts=document_facts,
    )

    result: Dict[str, Any] = {}
    for decision in interaction_decisions:
        result[decision.interaction_id] = decision.as_dict()
        finding = _finding_from_interaction_decision(decision)
        if finding is not None:
            findings_dict.append(finding)
    return result

def mark_dependent_interactions_stale(contract: Contract, changed_clause_type: str, changed_label: str) -> List[str]:
    """The conservative "mark, don't recompute" half of redline
    invalidation (design doc S5.2/S5.3). Scans contract.
    interaction_decisions_json (every rule this review actually evaluated,
    per interaction_enforcement.apply_interaction_rules) for entries whose
    participating_clause_types include `changed_clause_type` and whose
    state is actionable — never NOT_TRIGGERED/INSUFFICIENT_FACTS, which
    were never shown as needing attention in the first place and gain
    nothing from a staleness flag — and records a stale flag for each in
    contract.interaction_staleness_json (mutated in place; caller commits).
    Never recomputes anything: the edited/rejected clause's free-form text
    is not re-extracted, and every OTHER interaction not touching this
    clause type is left completely untouched (S5.3's "only dependent
    interactions invalidated" requirement, made exact by participating_
    clause_types being the sole filter — no graph traversal, no rerun of
    the full rule catalog).

    Returns the list of interaction_ids newly marked stale (empty if none
    depended on this clause type, or all were already stale)."""
    interaction_decisions = contract.interaction_decisions_json or {}
    staleness = dict(contract.interaction_staleness_json or {})
    newly_marked: List[str] = []
    for interaction_id, decision_dict in interaction_decisions.items():
        if changed_clause_type not in (decision_dict.get("participating_clause_types") or []):
            continue
        if decision_dict.get("state") not in ixc.ACTIONABLE_STATES:
            continue
        if staleness.get(interaction_id, {}).get("stale"):
            continue  # already flagged -- do not overwrite an earlier reason
        staleness[interaction_id] = {
            "stale": True,
            "stale_reason": f"This interaction depends on {changed_label}, which has changed since the interaction was evaluated.",
        }
        newly_marked.append(interaction_id)
    contract.interaction_staleness_json = staleness
    return newly_marked


def merge_interaction_staleness(findings: List[Dict[str, Any]], staleness: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Applies contract.interaction_staleness_json onto a copy of the
    findings list for rendering — never mutates the stored findings_json
    (same convention review_decisions_json already follows: overrides are
    layered on at read time, the original record never changes). A
    finding with no staleness entry is returned unchanged (same object,
    not copied) — only interaction_decision findings with an active
    staleness flag are ever touched."""
    if not staleness:
        return findings
    merged = []
    for f in findings:
        entry = staleness.get(f.get("interaction_id")) if f.get("finding_type") == "interaction_decision" else None
        merged.append({**f, **entry} if entry else f)
    return merged


def clear_interaction_staleness(contract: Contract, interaction_id: str) -> bool:
    """Explicit 'Recompute' action (design doc S5.2/S9.5): a lawyer has
    looked at a stale interaction again and dismisses the flag. Does not
    recompute anything (there is nothing new to recompute against — see
    module docstring) — it only clears the flag, which is itself the
    documented, honest behavior: the interaction's evidence still reflects
    the ORIGINAL decisions, and the lawyer has confirmed that is still
    acceptable. Returns False if there was nothing to clear."""
    staleness = dict(contract.interaction_staleness_json or {})
    if interaction_id not in staleness:
        return False
    del staleness[interaction_id]
    contract.interaction_staleness_json = staleness
    return True


def verify_interaction_finding(db: DBSession, contract: Contract, finding: Dict[str, Any]) -> Dict[str, Any]:
    """Mirrors policy_enforcement.verify_policy_finding one layer up: does
    re-evaluating this interaction rule against the EXACT pinned revisions
    that produced each participating PolicyDecision reproduce the same
    interaction state? This never re-extracts or re-evaluates a
    participating clause from raw text — it replays each participant via
    the exact same mechanism verify_policy_finding already uses (pinned
    policy_position_id, config_hash-checked), then re-runs only the one
    interaction rule over the replayed decisions."""
    import playbook_authoring as pa
    from policy_enforcement import config_hash_for_position
    from models import PolicyPosition

    interaction_id = finding.get("interaction_id")
    original_state = finding.get("policy_state")
    rule = next((r for r in ixr.LAUNCH_CATALOG if r.interaction_id == interaction_id), None)
    if rule is None:
        return {
            "policy_verification": True, "verified": False,
            "replayed_state": None, "original_state": original_state,
            "reason": "This finding does not identify a known interaction rule.",
        }

    revision_meta_all = contract.policy_revision_metadata_json or {}
    replayed_decisions: Dict[str, Any] = {}
    for ct in rule.participating_clause_types:
        revision_meta = revision_meta_all.get(ct)
        if not revision_meta or revision_meta.get("policy_position_id") is None or revision_meta.get("error"):
            return {
                "policy_verification": True, "verified": False,
                "replayed_state": None, "original_state": original_state,
                "reason": f"No pinned policy revision was recorded for participating clause type {ct!r}.",
            }
        position = db.query(PolicyPosition).filter(
            PolicyPosition.id == revision_meta["policy_position_id"],
            PolicyPosition.playbook_id == contract.playbook_id,
        ).first()
        if position is None:
            return {
                "policy_verification": True, "verified": False,
                "replayed_state": None, "original_state": original_state,
                "reason": f"The exact policy revision for {ct!r} that participated in this interaction no longer exists.",
            }
        if config_hash_for_position(position) != revision_meta.get("config_hash"):
            return {
                "policy_verification": True, "verified": False,
                "replayed_state": None, "original_state": original_state,
                "reason": f"The pinned policy revision for {ct!r} no longer matches what was recorded at review time.",
            }
        extract_fn, evaluate_fn = pa._ENGINE_FUNCS[ct]
        built_rule = pa.BUILDERS[ct](position)
        facts = extract_fn(contract.contract_text)
        replayed_decisions[ct] = evaluate_fn(facts, built_rule, source=f"Verify replay — pinned revision #{position.id}")

    replayed = ixc.evaluate(replayed_decisions, [rule])
    replayed_state = replayed[0].state if replayed else None
    verified = replayed_state == original_state
    return {
        "policy_verification": True, "verified": verified,
        "replayed_state": replayed_state, "original_state": original_state,
        "reason": None if verified else "Re-evaluating this interaction against the pinned policy revisions produced a different result.",
    }
