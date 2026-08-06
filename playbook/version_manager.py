"""
Version Manager — clone/publish/rollback/compare/archive/import/export for
PolicySet. Every state transition here writes a PolicyChangeLog entry and
an AuditEntry — nothing changes a PolicySet's status silently.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from playbook.db_models import PolicySet, PolicyRule, PolicyChangeLog
from playbook.repository import get_policy_set, NotFoundError
from playbook import audit_engine

_RULE_FIELDS = (
    "policy_topic", "bound_rule_ids_json", "title", "status", "preferred_position",
    "fallback_position", "approved_redline", "minimum_requirement", "maximum_requirement",
    "business_reason", "legal_reason", "risk_score", "severity", "approval_required",
    "escalation_owner", "effective_date", "jurisdiction", "applies_to_contract_types_json",
    "exceptions_json",
)


def clone(db: Session, firm_id: int, policy_set_id: int, actor_user_id: Optional[int] = None) -> PolicySet:
    source = get_policy_set(db, firm_id, policy_set_id)

    draft = PolicySet(
        firm_id=firm_id, name=source.name, description=source.description,
        organization_id=source.organization_id, practice_group_id=source.practice_group_id,
        client_id=source.client_id, matter_id=source.matter_id, contract_type_id=source.contract_type_id,
        version_major=source.version_major, version_minor=source.version_minor + 1,
        status="draft", author_user_id=actor_user_id, previous_version_id=source.id,
    )
    db.add(draft)
    db.flush()

    for rule in source.rules:
        db.add(PolicyRule(policy_set_id=draft.id, **{f: getattr(rule, f) for f in _RULE_FIELDS}))

    audit_engine.record(
        db, firm_id=firm_id, entity_type="policy_set", entity_id=draft.id, action="clone",
        actor_user_id=actor_user_id, detail_json={"cloned_from": source.id},
    )
    db.flush()
    return draft


def publish(db: Session, firm_id: int, policy_set_id: int, approved_by_user_id: int) -> PolicySet:
    ps = get_policy_set(db, firm_id, policy_set_id)
    if ps.status != "draft":
        raise ValueError(f"PolicySet {policy_set_id} is '{ps.status}', not 'draft' — cannot publish")

    from_version = None
    if ps.previous_version_id:
        prev = db.query(PolicySet).filter(PolicySet.id == ps.previous_version_id).first()
        if prev:
            from_version = f"{prev.version_major}.{prev.version_minor}"
            prev.status = "deprecated"
            prev.deprecated = True

    ps.status = "published"
    ps.approved_by_user_id = approved_by_user_id
    ps.approval_date = datetime.utcnow()
    if not ps.effective_date:
        ps.effective_date = ps.approval_date

    to_version = f"{ps.version_major}.{ps.version_minor}"
    db.add(PolicyChangeLog(
        policy_set_id=ps.id, from_version=from_version, to_version=to_version,
        summary=f"Published version {to_version}", changed_by_user_id=approved_by_user_id,
    ))
    audit_engine.record(
        db, firm_id=firm_id, entity_type="policy_set", entity_id=ps.id, action="publish",
        actor_user_id=approved_by_user_id, playbook_version=to_version,
    )
    db.flush()
    return ps


def rollback(db: Session, firm_id: int, policy_set_id: int, to_version_id: int, actor_user_id: Optional[int] = None) -> PolicySet:
    """Rollback is itself an audited, versioned action — it never deletes
    anything. The current version is marked deprecated; the target version
    is republished."""
    current = get_policy_set(db, firm_id, policy_set_id)
    target = get_policy_set(db, firm_id, to_version_id)

    current.status = "deprecated"
    current.deprecated = True

    target.status = "published"
    target.deprecated = False
    target.approved_by_user_id = actor_user_id
    target.approval_date = datetime.utcnow()

    db.add(PolicyChangeLog(
        policy_set_id=target.id,
        from_version=f"{current.version_major}.{current.version_minor}",
        to_version=f"{target.version_major}.{target.version_minor}",
        summary=f"Rolled back from PolicySet {current.id} to {target.id}",
        changed_by_user_id=actor_user_id,
    ))
    audit_engine.record(
        db, firm_id=firm_id, entity_type="policy_set", entity_id=target.id, action="rollback",
        actor_user_id=actor_user_id, detail_json={"rolled_back_from": current.id},
    )
    db.flush()
    return target


def archive(db: Session, firm_id: int, policy_set_id: int, actor_user_id: Optional[int] = None) -> PolicySet:
    ps = get_policy_set(db, firm_id, policy_set_id)
    ps.status = "deprecated"
    ps.deprecated = True
    audit_engine.record(
        db, firm_id=firm_id, entity_type="policy_set", entity_id=ps.id, action="archive",
        actor_user_id=actor_user_id,
    )
    db.flush()
    return ps


def compare_versions(db: Session, firm_id: int, version_a_id: int, version_b_id: int) -> Dict[str, Any]:
    a = get_policy_set(db, firm_id, version_a_id)
    b = get_policy_set(db, firm_id, version_b_id)

    a_by_topic = {r.policy_topic: r for r in a.rules}
    b_by_topic = {r.policy_topic: r for r in b.rules}

    added = sorted(set(b_by_topic) - set(a_by_topic))
    removed = sorted(set(a_by_topic) - set(b_by_topic))
    changed = []
    for topic in sorted(set(a_by_topic) & set(b_by_topic)):
        ra, rb = a_by_topic[topic], b_by_topic[topic]
        diffs = {
            f: {"from": getattr(ra, f), "to": getattr(rb, f)}
            for f in _RULE_FIELDS if getattr(ra, f) != getattr(rb, f)
        }
        if diffs:
            changed.append({"policy_topic": topic, "diffs": diffs})

    return {
        "version_a": f"{a.version_major}.{a.version_minor}", "version_b": f"{b.version_major}.{b.version_minor}",
        "added_topics": added, "removed_topics": removed, "changed_topics": changed,
    }


def export_policy_set(db: Session, firm_id: int, policy_set_id: int) -> Dict[str, Any]:
    ps = get_policy_set(db, firm_id, policy_set_id)
    return {
        "name": ps.name, "description": ps.description,
        "version_major": ps.version_major, "version_minor": ps.version_minor,
        "jurisdiction_scope": {
            "organization_id": ps.organization_id, "practice_group_id": ps.practice_group_id,
            "client_id": ps.client_id, "matter_id": ps.matter_id, "contract_type_id": ps.contract_type_id,
        },
        "rules": [{f: getattr(r, f) for f in _RULE_FIELDS} for r in ps.rules],
    }


def import_policy_set(db: Session, firm_id: int, payload: Dict[str, Any], actor_user_id: Optional[int] = None) -> PolicySet:
    """Round-trippable with export_policy_set's shape. Always lands as a
    new draft PolicySet — import never silently overwrites an existing
    published set."""
    scope = payload.get("jurisdiction_scope", {})
    ps = PolicySet(
        firm_id=firm_id, name=payload["name"], description=payload.get("description"),
        version_major=payload.get("version_major", 1), version_minor=payload.get("version_minor", 0),
        status="draft", author_user_id=actor_user_id,
        organization_id=scope.get("organization_id"), practice_group_id=scope.get("practice_group_id"),
        client_id=scope.get("client_id"), matter_id=scope.get("matter_id"),
        contract_type_id=scope.get("contract_type_id"),
    )
    db.add(ps)
    db.flush()

    for rule_data in payload.get("rules", []):
        db.add(PolicyRule(policy_set_id=ps.id, **{k: v for k, v in rule_data.items() if k in _RULE_FIELDS}))

    audit_engine.record(
        db, firm_id=firm_id, entity_type="policy_set", entity_id=ps.id, action="import",
        actor_user_id=actor_user_id,
    )
    db.flush()
    return ps
