"""
Data retention / scheduled cleanup tests (P9): retention.py's
configuration parsing and cleanup logic.
"""
import os
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DEV_MODE", "true")

import retention
from database import Base
from models import AuditLog, Contract, User
import analytics_models  # noqa: F401


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'retention_test.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session, engine
    session.close()


def _make_user(db) -> User:
    user = User(email="firm@example.com", password_hash="x")
    db.add(user)
    db.commit()
    return user


def _make_contract(db, engine, user, *, days_old: int) -> Contract:
    contract = Contract(user_id=user.id, filename=f"c{days_old}.txt", contract_text="placeholder")
    db.add(contract)
    db.commit()
    created_at = datetime.utcnow() - timedelta(days=days_old)
    with engine.begin() as conn:
        conn.execute(text("UPDATE contracts SET created_at = :d WHERE id = :id"), {"d": created_at, "id": contract.id})
    db.expire_all()
    return db.query(Contract).filter(Contract.id == contract.id).first()


# --- get_retention_days() ---

def test_retention_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CONTRACT_RETENTION_DAYS", raising=False)
    assert retention.get_retention_days() is None


def test_retention_days_parsed_from_env(monkeypatch):
    monkeypatch.setenv("CONTRACT_RETENTION_DAYS", "90")
    assert retention.get_retention_days() == 90


def test_invalid_retention_days_disables_retention(monkeypatch):
    monkeypatch.setenv("CONTRACT_RETENTION_DAYS", "not-a-number")
    assert retention.get_retention_days() is None


def test_zero_or_negative_retention_days_disabled(monkeypatch):
    monkeypatch.setenv("CONTRACT_RETENTION_DAYS", "0")
    assert retention.get_retention_days() is None
    monkeypatch.setenv("CONTRACT_RETENTION_DAYS", "-5")
    assert retention.get_retention_days() is None


# --- find_expired_contracts() ---

def test_finds_only_contracts_older_than_retention(db_session):
    db, engine = db_session
    user = _make_user(db)
    old = _make_contract(db, engine, user, days_old=100)
    recent = _make_contract(db, engine, user, days_old=5)

    expired = retention.find_expired_contracts(db, retention_days=30)
    expired_ids = {c.id for c in expired}
    assert old.id in expired_ids
    assert recent.id not in expired_ids


# --- run_cleanup() ---

def test_run_cleanup_is_noop_when_retention_not_configured(db_session, monkeypatch):
    db, engine = db_session
    monkeypatch.delenv("CONTRACT_RETENTION_DAYS", raising=False)
    user = _make_user(db)
    _make_contract(db, engine, user, days_old=1000)

    stats = retention.run_cleanup(db)
    assert stats == {"retention_days": None, "found": 0, "deleted": 0, "errors": 0}
    assert db.query(Contract).count() == 1  # nothing deleted


def test_run_cleanup_deletes_expired_contracts(db_session, monkeypatch):
    db, engine = db_session
    monkeypatch.setenv("CONTRACT_RETENTION_DAYS", "30")
    user = _make_user(db)
    old = _make_contract(db, engine, user, days_old=100)
    recent = _make_contract(db, engine, user, days_old=5)

    stats = retention.run_cleanup(db)
    assert stats["deleted"] == 1
    assert stats["found"] == 1

    remaining_ids = {c.id for c in db.query(Contract).all()}
    assert old.id not in remaining_ids
    assert recent.id in remaining_ids


def test_run_cleanup_dry_run_deletes_nothing(db_session, monkeypatch):
    db, engine = db_session
    monkeypatch.setenv("CONTRACT_RETENTION_DAYS", "30")
    user = _make_user(db)
    _make_contract(db, engine, user, days_old=100)

    stats = retention.run_cleanup(db, dry_run=True)
    assert stats["found"] == 1
    assert stats["deleted"] == 0
    assert db.query(Contract).count() == 1


def test_run_cleanup_records_audit_events(db_session, monkeypatch):
    db, engine = db_session
    monkeypatch.setenv("CONTRACT_RETENTION_DAYS", "30")
    user = _make_user(db)
    old = _make_contract(db, engine, user, days_old=100)

    retention.run_cleanup(db)

    events = db.query(AuditLog).filter(AuditLog.event_type == "contract_auto_deleted").all()
    assert len(events) == 1
    assert events[0].target_id == old.id
    assert events[0].actor_user_id is None  # system action, not the owning user
    assert events[0].detail == "retention_policy_expired"
    assert events[0].metadata_json.get("owner_user_id") == user.id


def test_run_cleanup_with_no_expired_contracts(db_session, monkeypatch):
    db, engine = db_session
    monkeypatch.setenv("CONTRACT_RETENTION_DAYS", "365")
    user = _make_user(db)
    _make_contract(db, engine, user, days_old=5)

    stats = retention.run_cleanup(db)
    assert stats == {"retention_days": 365, "found": 0, "deleted": 0, "errors": 0}
