"""
Compliance Reporter — pure deterministic aggregation over PolicyDecision/
PolicyOverride. No LLM, no free text summarization; every number here is a
direct count or arithmetic mean over already-persisted rows.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from playbook.db_models import PolicyDecision, PolicyEvaluation, PolicyOverride, PolicyRule
from playbook.policy_engine import POLICY_STATUSES


def _decisions_query(db: Session, firm_id: int, matter_id: Optional[int] = None, since: Optional[datetime] = None):
    q = (
        db.query(PolicyDecision)
        .join(PolicyEvaluation, PolicyDecision.evaluation_id == PolicyEvaluation.id)
        .join(PolicyRule, PolicyDecision.policy_rule_id == PolicyRule.id, isouter=True)
    )
    # Firm scoping: every decision traces back to a firm either via its
    # matched PolicyRule's PolicySet, or — for NOT_APPLICABLE decisions with
    # no matched rule — via the evaluation's own matter/contract_type, which
    # is always resolved within one firm's hierarchy at evaluation time.
    from playbook.db_models import PolicySet
    q = q.outerjoin(PolicySet, PolicyRule.policy_set_id == PolicySet.id)
    q = q.filter((PolicySet.firm_id == firm_id) | (PolicyDecision.policy_rule_id.is_(None)))
    if matter_id is not None:
        q = q.filter(PolicyEvaluation.matter_id == matter_id)
    if since is not None:
        q = q.filter(PolicyDecision.created_at >= since)
    return q


def counts_by_status(db: Session, firm_id: int, matter_id: Optional[int] = None, since: Optional[datetime] = None) -> Dict[str, int]:
    counts = {status: 0 for status in POLICY_STATUSES}
    rows = _decisions_query(db, firm_id, matter_id, since).with_entities(PolicyDecision.policy_status, func.count()).group_by(PolicyDecision.policy_status).all()
    for status, n in rows:
        counts[status] = n
    return counts


def most_violated_policies(db: Session, firm_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    rows = (
        _decisions_query(db, firm_id)
        .filter(PolicyDecision.policy_status.in_(["PROHIBITED", "ESCALATE"]))
        .filter(PolicyDecision.policy_rule_id.isnot(None))
        .with_entities(PolicyDecision.policy_rule_id, PolicyRule.title, func.count())
        .group_by(PolicyDecision.policy_rule_id, PolicyRule.title)
        .order_by(func.count().desc())
        .limit(limit)
        .all()
    )
    return [{"policy_rule_id": rid, "title": title, "violation_count": n} for rid, title, n in rows]


def most_overridden_policies(db: Session, firm_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    from playbook.db_models import PolicySet
    rows = (
        db.query(PolicyRule.id, PolicyRule.title, func.count(PolicyOverride.id))
        .join(PolicyDecision, PolicyDecision.policy_rule_id == PolicyRule.id)
        .join(PolicyOverride, PolicyOverride.policy_decision_id == PolicyDecision.id)
        .join(PolicySet, PolicyRule.policy_set_id == PolicySet.id)
        .filter(PolicySet.firm_id == firm_id)
        .group_by(PolicyRule.id, PolicyRule.title)
        .order_by(func.count(PolicyOverride.id).desc())
        .limit(limit)
        .all()
    )
    return [{"policy_rule_id": rid, "title": title, "override_count": n} for rid, title, n in rows]


def average_negotiation_score(db: Session, firm_id: int, matter_id: Optional[int] = None) -> Optional[float]:
    """Mean of matched PolicyRule.risk_score across every non-COMPLIANT,
    non-NOT_APPLICABLE decision (NEGOTIABLE/PARTIALLY_COMPLIANT/PROHIBITED/
    ESCALATE) that has a firm-authored risk_score to average. None if no
    such decision has a scored PolicyRule."""
    rows = (
        _decisions_query(db, firm_id, matter_id)
        .filter(PolicyDecision.policy_status.notin_(["COMPLIANT", "NOT_APPLICABLE"]))
        .filter(PolicyRule.risk_score.isnot(None))
        .with_entities(PolicyRule.risk_score)
        .all()
    )
    scores = [r[0] for r in rows]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 2)


def summary(db: Session, firm_id: int, matter_id: Optional[int] = None) -> Dict[str, Any]:
    return {
        "counts_by_status": counts_by_status(db, firm_id, matter_id),
        "most_violated_policies": most_violated_policies(db, firm_id),
        "most_overridden_policies": most_overridden_policies(db, firm_id),
        "average_negotiation_score": average_negotiation_score(db, firm_id, matter_id),
    }
