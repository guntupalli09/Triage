"""
Immutable audit event recording (P3: share-link events; P7 extends this
with more event types — login/logout/upload/delete/export/playbook/
policy/admin/failed-authorization).

record_event() only ever INSERTs an AuditLog row. Nothing in this codebase
updates or deletes them — that immutability is an application-level
convention (no route exposes edit/delete for audit_logs), documented here
so future contributors don't accidentally break it.

Deliberately does not raise: a failure to write an audit record must never
break the user-facing action it's describing (e.g. a contract share
succeeding is the important thing; if the audit insert itself fails, that's
logged and swallowed, not surfaced as a 500 to the user).

Audit writes always use a private DB session (same pattern as
analytics.record_event) so a failed audit insert can never db.rollback()
an in-flight business transaction such as an AI import.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from analytics import extract_ip
from database import SessionLocal
from models import AuditLog

logger = logging.getLogger(__name__)


def record_event(
    db: Session,
    event_type: str,
    *,
    request=None,
    actor_user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    success: Optional[bool] = None,
    detail: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Write one audit row. The ``db`` parameter is retained for call-site
    compatibility but is never used — audit persistence is isolated so it
    cannot commit or roll back a caller's open transaction."""
    _ = db
    session = SessionLocal()
    try:
        entry = AuditLog(
            event_type=event_type,
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=target_id,
            ip_address=extract_ip(request) if request is not None else None,
            user_agent=(request.headers.get("user-agent") if request is not None else None),
            success=success,
            detail=detail,
            metadata_json=metadata,
        )
        session.add(entry)
        session.commit()
    except Exception:
        logger.exception(f"Failed to record audit event: {event_type}")
        session.rollback()
    finally:
        session.close()
