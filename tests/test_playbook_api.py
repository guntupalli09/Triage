"""Integration tests for playbook/api.py — the /api/policy/* JSON surface,
run against an isolated in-memory database via FastAPI dependency override
so these tests never touch the app's real on-disk database."""
import os
import secrets
from datetime import datetime, timedelta

# main.py refuses to import outside DEV_MODE without a configured Stripe key
# (a pre-existing production safety check unrelated to this test) — default
# it on here so this file is runnable standalone, without requiring every
# caller to remember to set it in the environment first.
os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import auth
import database
import models  # noqa: F401
import analytics_models  # noqa: F401
import playbook.db_models  # noqa: F401


@pytest.fixture
def client_and_session():
    import main  # imported lazily so DEV_MODE/env is already set by the time FastAPI wires routes

    # StaticPool: a bare "sqlite:///:memory:" engine hands out a fresh,
    # empty in-memory database on every new connection unless pinned to a
    # single shared connection — without this, requests made after the
    # fixture's own setup connection closes would hit tables that don't exist.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    database.Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[database.get_db] = override_get_db

    db = TestSessionLocal()
    user = models.User(email="api_test@example.com", name="API Test", plan="professional")
    db.add(user); db.commit(); db.refresh(user)

    token = secrets.token_urlsafe(32)
    auth._store_session(token, {
        "user_id": user.id,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
    })

    client = TestClient(main.app)
    client.cookies.set("triage_session", token)

    yield client, db, user

    db.close()
    main.app.dependency_overrides.pop(database.get_db, None)


def test_unauthenticated_request_is_401(client_and_session):
    client, db, user = client_and_session
    client.cookies.delete("triage_session")
    r = client.get("/api/policy/firms/me")
    assert r.status_code == 401


def test_user_without_firm_gets_404_not_500(client_and_session):
    client, db, user = client_and_session
    r = client.get("/api/policy/firms/me")
    assert r.status_code == 404
    assert "detail" in r.json()


def test_full_policy_set_lifecycle(client_and_session):
    client, db, user = client_and_session
    from playbook.migration import run_legacy_playbook_migration
    run_legacy_playbook_migration(db)

    r = client.get("/api/policy/firms/me")
    assert r.status_code == 200
    firm_data = r.json()
    client_id = firm_data["organizations"][0]["practice_groups"][0]["clients"][0]["id"]

    r = client.post("/api/policy/matters", json={"client_id": client_id, "name": "Matter 1"})
    assert r.status_code == 200
    matter_id = r.json()["id"]

    r = client.post("/api/policy/sets", json={"name": "Test Set", "matter_id": matter_id})
    assert r.status_code == 200
    ps_id = r.json()["id"]
    assert r.json()["status"] == "draft"

    r = client.post(f"/api/policy/sets/{ps_id}/rules", json={
        "policy_topic": "INDEM", "title": "Indemnification", "status": "prohibited",
    })
    assert r.status_code == 200

    r = client.post(f"/api/policy/sets/{ps_id}/publish")
    assert r.status_code == 200
    assert r.json()["status"] == "published"

    r = client.get(f"/api/policy/sets/{ps_id}")
    assert r.status_code == 200
    assert len(r.json()["rules"]) == 1

    r = client.get("/api/policy/audit")
    assert r.status_code == 200
    assert any(e["action"] == "publish" for e in r.json())


def test_tenant_isolation_returns_404_not_403(client_and_session):
    client, db, user = client_and_session
    from playbook.migration import run_legacy_playbook_migration
    from playbook.db_models import Firm, PolicySet
    run_legacy_playbook_migration(db)

    other_firm = Firm(name="Other Firm", slug="other-firm")
    db.add(other_firm); db.flush()
    other_ps = PolicySet(firm_id=other_firm.id, name="Other Firm's Set", status="draft", version_major=1, version_minor=0)
    db.add(other_ps); db.commit()

    r = client.get(f"/api/policy/sets/{other_ps.id}")
    assert r.status_code == 404


def test_publishing_draft_twice_is_conflict(client_and_session):
    client, db, user = client_and_session
    from playbook.migration import run_legacy_playbook_migration
    run_legacy_playbook_migration(db)

    r = client.post("/api/policy/sets", json={"name": "Test Set 2"})
    ps_id = r.json()["id"]
    r = client.post(f"/api/policy/sets/{ps_id}/publish")
    assert r.status_code == 200

    r = client.post(f"/api/policy/sets/{ps_id}/publish")
    assert r.status_code == 409
