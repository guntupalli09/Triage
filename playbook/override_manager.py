"""
Override Manager — attorneys can override a policy decision, but an
override NEVER modifies PolicyRule/PolicySet. It is an append-only record
referencing the PolicyDecision it overrides; no update or delete route is
ever exposed for it at the service layer.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from playbook.db_models import PolicyDecision, PolicyOverride
from playbook.policy_engine import POLICY_STATUSES
from playbook import audit_engine


class OverrideValidationError(Exception):
    pass


def record_override(
    db: Session, firm_id: int, policy_decision_id: int, attorney_user_id: int,
    reason: str, overridden_status: str, matter_id: Optional[int] = None,
    approval_required: bool = False,
) -> PolicyOverride:
    if overridden_status not in POLICY_STATUSES:
        raise OverrideValidationError(f"'{overridden_status}' is not a valid policy status")
    if not (reason or "").strip():
        raise OverrideValidationError("an override requires a non-empty reason")

    decision = db.query(PolicyDecision).filter(PolicyDecision.id == policy_decision_id).first()
    if not decision:
        raise OverrideValidationError(f"PolicyDecision {policy_decision_id} not found")

    override = PolicyOverride(
        policy_decision_id=policy_decision_id, attorney_user_id=attorney_user_id,
        matter_id=matter_id, reason=reason, overridden_status=overridden_status,
        approval_required=approval_required,
    )
    db.add(override)
    db.flush()

    audit_engine.record(
        db, firm_id=firm_id, entity_type="policy_decision", entity_id=policy_decision_id,
        action="override", actor_user_id=attorney_user_id, reason=reason,
        detail_json={"overridden_status": overridden_status, "original_status": decision.policy_status},
    )

    return override


def overrides_for_decision(db: Session, policy_decision_id: int) -> List[PolicyOverride]:
    return (
        db.query(PolicyOverride)
        .filter(PolicyOverride.policy_decision_id == policy_decision_id)
        .order_by(PolicyOverride.created_at)
        .all()
    )


def effective_status_for(db: Session, policy_decision_id: int) -> str:
    """Read-side view combining decision + override without mutating
    either: the latest override's status if one exists, else the original
    PolicyDecision.policy_status."""
    latest = (
        db.query(PolicyOverride)
        .filter(PolicyOverride.policy_decision_id == policy_decision_id)
        .order_by(PolicyOverride.created_at.desc())
        .first()
    )
    if latest:
        return latest.overridden_status
    decision = db.query(PolicyDecision).filter(PolicyDecision.id == policy_decision_id).first()
    return decision.policy_status if decision else None
