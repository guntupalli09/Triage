"""
Tests for POST /internal/retention/cleanup (P9's "secure delete API" for
platforms that schedule jobs over HTTP, e.g. Vercel Cron Jobs).
"""
import io
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEV_MODE", "true")

import main
import rate_limit
from database import SessionLocal
from models import AuditLog, Contract


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    rate_limit._memory_counters.clear()
    yield
    rate_limit._memory_counters.clear()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def test_endpoint_404s_when_cron_secret_not_configured(client, monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    r = client.post("/internal/retention/cleanup")
    assert r.status_code == 404


def test_endpoint_rejects_missing_bearer_token(client, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-secret-value")
    r = client.post("/internal/retention/cleanup")
    assert r.status_code == 403


def test_endpoint_rejects_wrong_bearer_token(client, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-secret-value")
    r = client.post("/internal/retention/cleanup", headers={"Authorization": "Bearer wrong-value"})
    assert r.status_code == 403


def test_endpoint_accepts_correct_bearer_token(client, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-secret-value")
    monkeypatch.delenv("CONTRACT_RETENTION_DAYS", raising=False)
    r = client.post("/internal/retention/cleanup", headers={"Authorization": "Bearer test-secret-value"})
    assert r.status_code == 200
    assert r.json()["retention_days"] is None  # retention not configured, but auth succeeded


def test_wrong_token_attempt_is_audit_logged(client, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-secret-value")
    client.post("/internal/retention/cleanup", headers={"Authorization": "Bearer nope"})

    db = SessionLocal()
    try:
        events = db.query(AuditLog).filter(AuditLog.event_type == "retention_cleanup_denied").all()
        assert len(events) >= 1
        assert events[-1].detail == "invalid_cron_secret"
    finally:
        db.close()


def test_successful_run_is_audit_logged_with_stats(client, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-secret-value")
    monkeypatch.setenv("CONTRACT_RETENTION_DAYS", "30")
    client.post("/internal/retention/cleanup", headers={"Authorization": "Bearer test-secret-value"})

    db = SessionLocal()
    try:
        events = db.query(AuditLog).filter(AuditLog.event_type == "retention_cleanup_run").all()
        assert len(events) >= 1
        assert "found" in events[-1].metadata_json
        assert "deleted" in events[-1].metadata_json
    finally:
        db.close()


def test_endpoint_actually_deletes_expired_contracts(client, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-secret-value")

    token_r = client.get("/register")
    csrf = token_r.cookies.get("csrf_token")
    client.post("/register", data={
        "email": "retention-http@example.com", "password": "Str0ngP@ssw0rd!",
        "confirm_password": "Str0ngP@ssw0rd!", "name": "T", "company": "", "csrf_token": csrf,
    })
    files = {"file": ("nda.txt", io.BytesIO(b"Confidentiality agreement text."), "text/plain")}
    up = client.post("/upload", data={"csrf_token": csrf}, files=files, follow_redirects=False)
    contract_id = int(up.headers["location"].split("/")[2])

    db = SessionLocal()
    try:
        from datetime import datetime, timedelta
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        contract.created_at = datetime.utcnow() - timedelta(days=400)
        db.commit()
    finally:
        db.close()

    monkeypatch.setenv("CONTRACT_RETENTION_DAYS", "30")
    r = client.post("/internal/retention/cleanup", headers={"Authorization": "Bearer test-secret-value"})
    assert r.status_code == 200
    assert r.json()["deleted"] == 1

    db = SessionLocal()
    try:
        assert db.query(Contract).filter(Contract.id == contract_id).first() is None
    finally:
        db.close()
