"""
Shared review persistence used by web upload, Word/Google clients, intake
promotion, and revision import.

Keeps policy_enforcement / interaction_enforcement as the authority. This
module only stamps tenancy, stores the frozen analysis snapshot, and
indexes canonical facts. It never re-derives policy from an LLM.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from models import Contract, IntegrationAction, Playbook, User
import audit_log
import canonical_index
import tenancy


def persist_reviewed_contract(
    db: Session,
    user: User,
    *,
    contract_text: str,
    filename: str,
    analysis: Dict[str, Any],
    policy_result: Dict[str, Any],
    playbook: Optional[Playbook] = None,
    source: str = "web",
    display_name: Optional[str] = None,
    contract_type: Optional[str] = None,
    counterparty: Optional[str] = None,
    workspace_id: Optional[int] = None,
    parent_contract_id: Optional[int] = None,
    revision_number: int = 1,
    intake_request_id: Optional[int] = None,
    review_status: str = "in_review",
    review_context: Optional[Dict[str, Any]] = None,
    deviations: Any = None,
    batch_id: Optional[str] = None,
) -> Contract:
    tenancy.ensure_user_tenant(db, user)
    review_context = review_context or {}
    document_facts = policy_result.get("document_facts")
    if document_facts is not None and hasattr(document_facts, "as_dict"):
        document_facts = document_facts.as_dict()

    contract = Contract(
        user_id=user.id,
        tenant_id=user.tenant_id,
        workspace_id=workspace_id or user.workspace_id,
        filename=filename,
        display_name=(display_name or filename)[:255],
        contract_type=contract_type,
        counterparty=counterparty,
        source=source,
        review_status=review_status,
        parent_contract_id=parent_contract_id,
        revision_number=revision_number,
        intake_request_id=intake_request_id,
        contract_text=contract_text,
        overall_risk=analysis.get("overall_risk"),
        findings_json=analysis.get("findings_dict"),
        llm_result_json=analysis.get("llm_result"),
        rule_counts_json=analysis.get("rule_counts"),
        rule_engine_version=analysis.get("version"),
        analysis_completed=True,
        playbook_id=playbook.id if playbook is not None else None,
        deviations_json=deviations,
        review_business_unit=review_context.get("business_unit"),
        review_customer_type=review_context.get("customer_type"),
        review_deal_value=review_context.get("deal_value"),
        policy_decisions_json=policy_result.get("policy_decisions"),
        policy_revision_metadata_json=policy_result.get("policy_revision_metadata"),
        interaction_decisions_json=policy_result.get("interaction_decisions"),
        document_facts_json=document_facts,
        signature_readiness=analysis.get("signature_readiness"),
        payment_terms_json=analysis.get("payment_terms"),
        blocking_findings_json=analysis.get("blocking_findings"),
        policy_blocked_findings_json=analysis.get("policy_blocked_findings"),
        legal_risk_score=(analysis.get("risk_dashboard") or {}).get("legal_risk_score"),
        business_risk_score=(analysis.get("risk_dashboard") or {}).get("business_risk_score"),
        negotiation_difficulty_score=(analysis.get("risk_dashboard") or {}).get("negotiation_difficulty_score"),
        risk_dashboard_json=analysis.get("risk_dashboard"),
        structure_report_json=analysis.get("structure_report"),
        clause_quality_json=analysis.get("clause_quality"),
        metadata_json=analysis.get("metadata"),
        risk_balance_json=analysis.get("risk_balance"),
        batch_id=batch_id,
    )
    db.add(contract)
    db.flush()
    canonical_index.upsert_fact_index(db, contract)
    return contract


def record_integration_action(
    db: Session,
    user: User,
    *,
    client_kind: str,
    action: str,
    contract_id: Optional[int] = None,
    finding_key: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    request=None,
) -> None:
    tenancy.ensure_user_tenant(db, user)
    row = IntegrationAction(
        tenant_id=user.tenant_id,
        contract_id=contract_id,
        actor_user_id=user.id,
        client_kind=client_kind,
        action=action,
        finding_key=finding_key,
        payload_json=payload,
    )
    db.add(row)
    db.flush()
    audit_log.record_event(
        db, f"integration_{action}", request=request, actor_user_id=user.id,
        target_type="contract", target_id=contract_id, success=True,
        metadata={"client_kind": client_kind, "finding_key": finding_key},
    )


def serialize_finding(index: int, finding: Dict[str, Any], *, stale_map: Optional[Dict[str, Any]] = None, policy_stale: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    import review_workflow
    key = finding.get("finding_key") or review_workflow.finding_key(index, finding.get("rule_id") or str(index))
    clause_type = finding.get("clause_type")
    stale = None
    if finding.get("finding_type") == "interaction_decision" and stale_map:
        stale = stale_map.get(finding.get("interaction_id") or finding.get("rule_id"))
    elif clause_type and policy_stale:
        stale = policy_stale.get(clause_type)
    redline = finding.get("redline") if isinstance(finding.get("redline"), dict) else None
    return {
        "finding_key": key,
        "rule_id": finding.get("rule_id"),
        "title": finding.get("title"),
        "policy_area": finding.get("finding_type_label") or finding.get("clause_type") or finding.get("rule_name"),
        "clause_type": clause_type,
        "finding_type": finding.get("finding_type") or "rule_engine",
        "outcome": finding.get("policy_state") or finding.get("state"),
        "severity": finding.get("severity"),
        "explanation": finding.get("rationale") or finding.get("explanation"),
        "evidence": finding.get("exact_snippet") or finding.get("matched_excerpt") or finding.get("contract_language"),
        "start_index": finding.get("start_index"),
        "end_index": finding.get("end_index"),
        "suggested_comment": (redline or {}).get("comment") or finding.get("rationale"),
        "suggested_redline": (redline or {}).get("proposed_text") or (redline or {}).get("replacement"),
        "redline": redline,
        "stale": bool(stale.get("stale")) if isinstance(stale, dict) else bool(finding.get("stale")),
        "stale_reason": (stale or {}).get("stale_reason") if isinstance(stale, dict) else finding.get("stale_reason"),
        "interaction_id": finding.get("interaction_id"),
        "why_this_decision": finding.get("explanation") or finding.get("rationale"),
    }


def serialize_review(contract: Contract) -> Dict[str, Any]:
    import change_aware
    import interaction_enforcement as ixe
    findings = list(contract.findings_json or [])
    findings = ixe.merge_interaction_staleness(findings, contract.interaction_staleness_json)
    policy_stale = change_aware.policy_staleness_map(contract)
    stale_map = {k: v for k, v in (contract.interaction_staleness_json or {}).items() if not str(k).startswith("_")}
    return {
        "id": contract.id,
        "filename": contract.filename,
        "display_name": contract.display_name or contract.filename,
        "contract_type": contract.contract_type,
        "counterparty": contract.counterparty,
        "source": contract.source or "web",
        "review_status": contract.review_status or ("finalized" if contract.review_finalized_at else "in_review"),
        "playbook_id": contract.playbook_id,
        "overall_risk": contract.overall_risk,
        "created_at": contract.created_at.isoformat() if contract.created_at else None,
        "review_finalized_at": contract.review_finalized_at.isoformat() if contract.review_finalized_at else None,
        "revision_number": contract.revision_number,
        "parent_contract_id": contract.parent_contract_id,
        "workspace_id": contract.workspace_id,
        "findings": [serialize_finding(i, f, stale_map=stale_map, policy_stale=policy_stale) for i, f in enumerate(findings) if isinstance(f, dict)],
        "policy_decisions": contract.policy_decisions_json,
        "interaction_decisions": contract.interaction_decisions_json,
        "review_decisions": contract.review_decisions_json,
        "document_facts": contract.document_facts_json,
        "policy_staleness": policy_stale,
    }
