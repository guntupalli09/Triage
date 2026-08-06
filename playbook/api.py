"""
JSON API surface for the policy enforcement engine — new /api/policy/*
router, included into the existing FastAPI app via one
`app.include_router(...)` line in main.py. Does not modify or replace any
existing HTML-form-coupled route.

Every handler resolves the current user's Firm and scopes all reads/writes
to it (see playbook/repository.py's firm-scoping discipline) — a request
for another firm's data returns 404, never 403, to avoid confirming that
the resource exists at all.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from auth import get_current_user
from database import get_db
from models import Contract, User
from playbook import repository, override_manager, version_manager, audit_engine, compliance_reporter
from playbook.decision_engine import DecisionEngine
from playbook.repository import NotFoundError
from playbook.schemas import (
    MatterCreate, ContractTypeCreate, PolicySetCreate, PolicyRuleCreate,
    PolicyRuleUpdate, OverrideCreate, PolicySetImport,
)

router = APIRouter(prefix="/api/policy", tags=["policy"])


def _current_user(request: Request, db: DBSession = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _current_firm_id(user: User = Depends(_current_user)) -> int:
    if not user.default_firm_id:
        raise HTTPException(status_code=404, detail="No firm is associated with this account yet")
    return user.default_firm_id


def _rule_to_dict(rule) -> dict:
    return {
        "id": rule.id, "policy_set_id": rule.policy_set_id, "policy_topic": rule.policy_topic,
        "bound_rule_ids": rule.bound_rule_ids_json, "title": rule.title, "status": rule.status,
        "preferred_position": rule.preferred_position, "fallback_position": rule.fallback_position,
        "approved_redline": rule.approved_redline, "minimum_requirement": rule.minimum_requirement,
        "maximum_requirement": rule.maximum_requirement, "business_reason": rule.business_reason,
        "legal_reason": rule.legal_reason, "risk_score": rule.risk_score, "severity": rule.severity,
        "approval_required": rule.approval_required, "escalation_owner": rule.escalation_owner,
        "jurisdiction": rule.jurisdiction,
        "applies_to_contract_types": rule.applies_to_contract_types_json,
        "exceptions": rule.exceptions_json,
    }


def _policy_set_to_dict(ps) -> dict:
    return {
        "id": ps.id, "name": ps.name, "description": ps.description,
        "status": ps.status, "version": f"{ps.version_major}.{ps.version_minor}",
        "scope": {
            "organization_id": ps.organization_id, "practice_group_id": ps.practice_group_id,
            "client_id": ps.client_id, "matter_id": ps.matter_id, "contract_type_id": ps.contract_type_id,
        },
        "author_user_id": ps.author_user_id, "approved_by_user_id": ps.approved_by_user_id,
        "approval_date": ps.approval_date, "effective_date": ps.effective_date,
        "previous_version_id": ps.previous_version_id, "deprecated": ps.deprecated,
        "legacy_playbook_id": ps.legacy_playbook_id,
        "rules": [_rule_to_dict(r) for r in ps.rules],
    }


def _decision_to_dict(d) -> dict:
    return {
        "id": d.id, "finding_key": d.finding_key, "rule_id": d.rule_id,
        "policy_rule_id": d.policy_rule_id, "policy_status": d.policy_status, "reason": d.reason,
        "preferred_position": d.preferred_position, "fallback_position": d.fallback_position,
        "escalation_required": d.escalation_required, "escalation_owner": d.escalation_owner,
        "matched_policy_set_id": d.matched_policy_set_id,
        "matched_policy_rule_version": d.matched_policy_rule_version,
    }


# ---------------------------------------------------------------------------
# Firm / hierarchy
# ---------------------------------------------------------------------------

@router.get("/firms/me")
def get_my_firm(firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    firm = repository.get_firm(db, firm_id)
    tree = repository.list_hierarchy(db, firm_id)
    return {
        "id": firm.id, "name": firm.name, "slug": firm.slug,
        "organizations": [
            {
                "id": o["id"], "name": o["name"],
                "practice_groups": [
                    {
                        "id": pg["id"], "name": pg["name"],
                        "clients": [
                            {
                                "id": c["id"], "name": c["name"],
                                "matters": [{"id": m.id, "name": m.name, "matter_number": m.matter_number} for m in c["matters"]],
                            }
                            for c in pg["clients"]
                        ],
                    }
                    for pg in o["practice_groups"]
                ],
            }
            for o in tree["organizations"]
        ],
        "contract_types": [{"id": ct.id, "name": ct.name, "slug": ct.slug} for ct in tree["contract_types"]],
    }


@router.post("/matters")
def create_matter(payload: MatterCreate, firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    try:
        matter = repository.create_matter(db, firm_id, payload.client_id, payload.name, payload.matter_number)
        db.commit()
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": matter.id, "client_id": matter.client_id, "name": matter.name, "matter_number": matter.matter_number}


@router.post("/contract-types")
def create_contract_type(payload: ContractTypeCreate, firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    ct = repository.create_contract_type(db, firm_id, payload.name, payload.slug)
    db.commit()
    return {"id": ct.id, "name": ct.name, "slug": ct.slug}


# ---------------------------------------------------------------------------
# PolicySet / PolicyRule
# ---------------------------------------------------------------------------

@router.get("/sets")
def list_policy_sets(
    organization_id: Optional[int] = None, practice_group_id: Optional[int] = None,
    client_id: Optional[int] = None, matter_id: Optional[int] = None,
    contract_type_id: Optional[int] = None, status: Optional[str] = None,
    firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db),
):
    sets = repository.list_policy_sets(
        db, firm_id, organization_id, practice_group_id, client_id, matter_id, contract_type_id, status,
    )
    return [_policy_set_to_dict(ps) for ps in sets]


@router.post("/sets")
def create_policy_set(
    payload: PolicySetCreate, firm_id: int = Depends(_current_firm_id),
    user: User = Depends(_current_user), db: DBSession = Depends(get_db),
):
    ps = repository.create_draft_policy_set(
        db, firm_id, payload.name, author_user_id=user.id, description=payload.description,
        organization_id=payload.organization_id, practice_group_id=payload.practice_group_id,
        client_id=payload.client_id, matter_id=payload.matter_id, contract_type_id=payload.contract_type_id,
    )
    db.commit()
    return _policy_set_to_dict(ps)


@router.get("/sets/{policy_set_id}")
def get_policy_set_detail(policy_set_id: int, firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    try:
        ps = repository.get_policy_set(db, firm_id, policy_set_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _policy_set_to_dict(ps)


@router.post("/sets/{policy_set_id}/rules")
def add_policy_rule(
    policy_set_id: int, payload: PolicyRuleCreate, firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db),
):
    try:
        rule = repository.add_rule(
            db, firm_id, policy_set_id,
            policy_topic=payload.policy_topic, title=payload.title, status=payload.status,
            bound_rule_ids_json=payload.bound_rule_ids,
            preferred_position=payload.preferred_position, fallback_position=payload.fallback_position,
            approved_redline=payload.approved_redline, minimum_requirement=payload.minimum_requirement,
            maximum_requirement=payload.maximum_requirement, business_reason=payload.business_reason,
            legal_reason=payload.legal_reason, risk_score=payload.risk_score, severity=payload.severity,
            approval_required=payload.approval_required, escalation_owner=payload.escalation_owner,
            jurisdiction=payload.jurisdiction,
            applies_to_contract_types_json=payload.applies_to_contract_types,
            exceptions_json=payload.exceptions,
        )
        db.commit()
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    return _rule_to_dict(rule)


@router.patch("/rules/{rule_id}")
def patch_policy_rule(rule_id: int, payload: PolicyRuleUpdate, firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    try:
        rule = repository.update_rule(db, firm_id, rule_id, **payload.model_dump(exclude_unset=True))
        db.commit()
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    return _rule_to_dict(rule)


# ---------------------------------------------------------------------------
# Version manager
# ---------------------------------------------------------------------------

@router.post("/sets/{policy_set_id}/clone")
def clone_policy_set(policy_set_id: int, firm_id: int = Depends(_current_firm_id), user: User = Depends(_current_user), db: DBSession = Depends(get_db)):
    try:
        draft = version_manager.clone(db, firm_id, policy_set_id, actor_user_id=user.id)
        db.commit()
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    return _policy_set_to_dict(draft)


@router.post("/sets/{policy_set_id}/publish")
def publish_policy_set(policy_set_id: int, firm_id: int = Depends(_current_firm_id), user: User = Depends(_current_user), db: DBSession = Depends(get_db)):
    try:
        ps = version_manager.publish(db, firm_id, policy_set_id, approved_by_user_id=user.id)
        db.commit()
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    return _policy_set_to_dict(ps)


@router.post("/sets/{policy_set_id}/rollback")
def rollback_policy_set(policy_set_id: int, to_version_id: int, firm_id: int = Depends(_current_firm_id), user: User = Depends(_current_user), db: DBSession = Depends(get_db)):
    try:
        ps = version_manager.rollback(db, firm_id, policy_set_id, to_version_id, actor_user_id=user.id)
        db.commit()
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    return _policy_set_to_dict(ps)


@router.get("/sets/{policy_set_id}/compare/{other_id}")
def compare_policy_sets(policy_set_id: int, other_id: int, firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    try:
        return version_manager.compare_versions(db, firm_id, policy_set_id, other_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sets/{policy_set_id}/archive")
def archive_policy_set(policy_set_id: int, firm_id: int = Depends(_current_firm_id), user: User = Depends(_current_user), db: DBSession = Depends(get_db)):
    try:
        ps = version_manager.archive(db, firm_id, policy_set_id, actor_user_id=user.id)
        db.commit()
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    return _policy_set_to_dict(ps)


@router.get("/sets/{policy_set_id}/export")
def export_policy_set(policy_set_id: int, firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    try:
        return version_manager.export_policy_set(db, firm_id, policy_set_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sets/import")
def import_policy_set(payload: PolicySetImport, firm_id: int = Depends(_current_firm_id), user: User = Depends(_current_user), db: DBSession = Depends(get_db)):
    ps = version_manager.import_policy_set(db, firm_id, payload.model_dump(), actor_user_id=user.id)
    db.commit()
    return _policy_set_to_dict(ps)


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------

@router.post("/evaluations/{contract_id}")
def run_evaluation(contract_id: int, firm_id: int = Depends(_current_firm_id), user: User = Depends(_current_user), db: DBSession = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    evaluation = DecisionEngine.evaluate(
        db, contract_id=contract.id, findings=contract.findings_json or [],
        firm_id=firm_id, rule_engine_version=contract.rule_engine_version or "unknown",
        matter_id=contract.matter_id,
    )
    contract.policy_evaluation_id = evaluation.id
    db.commit()
    return {
        "id": evaluation.id, "contract_id": evaluation.contract_id,
        "resolved_policy_set_ids": evaluation.resolved_policy_set_ids_json,
        "decisions": [_decision_to_dict(d) for d in evaluation.decisions],
    }


@router.get("/evaluations/{contract_id}")
def get_evaluation(contract_id: int, user: User = Depends(_current_user), db: DBSession = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract or not contract.policy_evaluation_id:
        raise HTTPException(status_code=404, detail="No policy evaluation found for this contract")
    from playbook.db_models import PolicyEvaluation
    evaluation = db.query(PolicyEvaluation).filter(PolicyEvaluation.id == contract.policy_evaluation_id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="No policy evaluation found for this contract")
    return {
        "id": evaluation.id, "contract_id": evaluation.contract_id,
        "resolved_policy_set_ids": evaluation.resolved_policy_set_ids_json,
        "decisions": [_decision_to_dict(d) for d in evaluation.decisions],
    }


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------

@router.post("/decisions/{decision_id}/override")
def override_decision(decision_id: int, payload: OverrideCreate, firm_id: int = Depends(_current_firm_id), user: User = Depends(_current_user), db: DBSession = Depends(get_db)):
    try:
        override = override_manager.record_override(
            db, firm_id=firm_id, policy_decision_id=decision_id, attorney_user_id=user.id,
            reason=payload.reason, overridden_status=payload.overridden_status,
            matter_id=payload.matter_id, approval_required=payload.approval_required,
        )
        db.commit()
    except override_manager.OverrideValidationError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": override.id, "policy_decision_id": override.policy_decision_id,
        "overridden_status": override.overridden_status, "reason": override.reason,
        "created_at": override.created_at,
    }


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

@router.get("/audit")
def query_audit(
    entity_type: Optional[str] = None, entity_id: Optional[int] = None,
    firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db),
):
    entries = audit_engine.query(db, firm_id, entity_type=entity_type, entity_id=entity_id)
    return [
        {
            "id": e.id, "entity_type": e.entity_type, "entity_id": e.entity_id, "action": e.action,
            "actor_user_id": e.actor_user_id, "reason": e.reason, "attorney_comments": e.attorney_comments,
            "detail": e.detail_json, "created_at": e.created_at,
        }
        for e in entries
    ]


# ---------------------------------------------------------------------------
# Compliance reports
# ---------------------------------------------------------------------------

@router.get("/reports/summary")
def report_summary(matter_id: Optional[int] = None, firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    return compliance_reporter.summary(db, firm_id, matter_id)


@router.get("/reports/most-violated")
def report_most_violated(firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    return compliance_reporter.most_violated_policies(db, firm_id)


@router.get("/reports/most-overridden")
def report_most_overridden(firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    return compliance_reporter.most_overridden_policies(db, firm_id)


@router.get("/reports/negotiation-score")
def report_negotiation_score(matter_id: Optional[int] = None, firm_id: int = Depends(_current_firm_id), db: DBSession = Depends(get_db)):
    return {"average_negotiation_score": compliance_reporter.average_negotiation_score(db, firm_id, matter_id)}
