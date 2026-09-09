"""
Unit tests for audit_log.py: it must never raise (a broken audit write
must not break the user-facing action), and it must record exactly what
it's given.
"""
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DEV_MODE", "true")

import audit_log
from database import Base
from models import AuditLog, User
import analytics_models  # noqa: F401


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit_test.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_record_event_writes_expected_fields(db_session):
    from database import SessionLocal
    verify = SessionLocal()
    try:
        verify.query(AuditLog).filter(AuditLog.event_type == "share_link_created").delete()
        verify.commit()
    finally:
        verify.close()
    audit_log.record_event(
        db_session, "share_link_created",
        actor_user_id=1, target_type="contract", target_id=42,
        success=True, detail=None, metadata={"has_password": True},
    )
    verify = SessionLocal()
    try:
        row = verify.query(AuditLog).filter(AuditLog.target_id == 42).one()
    finally:
        verify.close()
    assert row.event_type == "share_link_created"
    assert row.actor_user_id == 1
    assert row.target_type == "contract"
    assert row.target_id == 42
    assert row.success is True
    assert row.metadata_json == {"has_password": True}
    assert row.created_at is not None


def test_record_event_survives_db_failure(db_session, monkeypatch):
    """A broken audit write must not raise into the caller — the action
    being audited (e.g. revoking a share link) must still succeed."""
    def _boom():
        raise RuntimeError("db exploded")

    monkeypatch.setattr("audit_log.SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "commit", _boom)
    audit_log.record_event(db_session, "share_link_revoked", target_type="contract", target_id=1)
    # No exception propagated — that's the whole point of this test.


def test_record_event_without_request_has_no_ip_or_user_agent(db_session):
    from database import SessionLocal
    verify = SessionLocal()
    try:
        verify.query(AuditLog).filter(AuditLog.target_id == 1, AuditLog.event_type == "share_link_created").delete()
        verify.commit()
    finally:
        verify.close()
    audit_log.record_event(db_session, "share_link_created", target_type="contract", target_id=1)
    verify = SessionLocal()
    try:
        row = verify.query(AuditLog).filter(AuditLog.target_id == 1, AuditLog.event_type == "share_link_created").one()
    finally:
        verify.close()
    assert row.ip_address is None
    assert row.user_agent is None
