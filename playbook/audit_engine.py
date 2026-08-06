"""
Audit Engine — the single write path for AuditEntry rows, used by every
other module (Decision Engine, Override Manager, Version Manager) instead
of each writing AuditEntry rows ad hoc, plus the read side for the audit
trail API/UI.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from playbook.db_models import AuditEntry


def record(
    db: Session, firm_id: int, entity_type: str, entity_id: int, action: str,
    actor_user_id: Optional[int] = None, playbook_version: Optional[str] = None,
    rule_engine_version: Optional[str] = None, reason: Optional[str] = None,
    attorney_comments: Optional[str] = None, detail_json: Optional[Dict[str, Any]] = None,
) -> AuditEntry:
    entry = AuditEntry(
        firm_id=firm_id, entity_type=entity_type, entity_id=entity_id, action=action,
        actor_user_id=actor_user_id, playbook_version=playbook_version,
        rule_engine_version=rule_engine_version, reason=reason,
        attorney_comments=attorney_comments, detail_json=detail_json,
    )
    db.add(entry)
    db.flush()
    return entry


def query(
    db: Session, firm_id: int, entity_type: Optional[str] = None, entity_id: Optional[int] = None,
    actor_user_id: Optional[int] = None, since: Optional[datetime] = None, limit: int = 500,
) -> List[AuditEntry]:
    q = db.query(AuditEntry).filter(AuditEntry.firm_id == firm_id)
    if entity_type is not None:
        q = q.filter(AuditEntry.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditEntry.entity_id == entity_id)
    if actor_user_id is not None:
        q = q.filter(AuditEntry.actor_user_id == actor_user_id)
    if since is not None:
        q = q.filter(AuditEntry.created_at >= since)
    return q.order_by(AuditEntry.created_at.desc()).limit(limit).all()


def build_audit_trail_text(db: Session, firm_id: int, entity_type: str, entity_id: int) -> str:
    """Plain-text export in the same spirit as review_workflow.py's
    build_audit_trail_text, sourced from AuditEntry rows instead of
    review_decisions_json — every recorded action against one entity,
    timestamped, in order."""
    entries = query(db, firm_id, entity_type=entity_type, entity_id=entity_id, limit=10_000)
    entries = sorted(entries, key=lambda e: e.created_at)
    lines = [f"Audit Trail — {entity_type} #{entity_id}", "=" * 60, ""]
    for e in entries:
        lines.append(f"[{e.created_at.isoformat()}] {e.action}")
        if e.actor_user_id:
            lines.append(f"  Actor: user #{e.actor_user_id}")
        if e.reason:
            lines.append(f"  Reason: {e.reason}")
        if e.attorney_comments:
            lines.append(f"  Comments: {e.attorney_comments}")
        lines.append("")
    if not entries:
        lines.append("No audit entries recorded.")
    return "\n".join(lines)
