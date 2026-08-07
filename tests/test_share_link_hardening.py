"""
Share link hardening tests (P3): expiry, revoke, max views, and audit
logging, exercised end-to-end through the real app.
"""
import io
import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEV_MODE", "true")

import main
import rate_limit
from database import SessionLocal
from models import AuditLog, Contract

NDA_BYTES = b"Confidentiality Agreement between Acme Corp and Beta LLC regarding arbitration and termination."


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Every test in this module registers 1-2 new users from the same
    TestClient IP ("testclient"); without resetting between tests they'd
    trip the /register rate limit (P1c) well before exercising anything
    about share links."""
    rate_limit._memory_counters.clear()
    yield
    rate_limit._memory_counters.clear()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _register(client, email):
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    client.post("/register", data={
        "email": email, "password": "Str0ngP@ssw0rd!", "confirm_password": "Str0ngP@ssw0rd!",
        "name": "Firm", "company": "", "csrf_token": token,
    })
    return token


def _upload_contract(client, token) -> int:
    files = {"file": ("nda.txt", io.BytesIO(NDA_BYTES), "text/plain")}
    r = client.post("/upload", data={"csrf_token": token}, files=files, follow_redirects=False)
    assert r.status_code == 303
    return int(r.headers["location"].split("/")[2])


def _audit_events(event_type: str, target_id: int = None):
    db = SessionLocal()
    try:
        q = db.query(AuditLog).filter(AuditLog.event_type == event_type)
        if target_id is not None:
            q = q.filter(AuditLog.target_id == target_id)
        return q.all()
    finally:
        db.close()


def test_default_share_link_never_expires_and_is_unlimited(client):
    """Backward compatibility: creating a share link with no options set
    (the pre-hardening one-click flow) behaves exactly as before —
    unlimited views, no expiry."""
    token = _register(client, "default-share@example.com")
    contract_id = _upload_contract(client, token)

    r = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token})
    assert r.status_code == 200
    data = r.json()
    assert data["expires_at"] is None
    assert data["max_views"] is None
    share_token = data["token"]

    anon = TestClient(main.app)
    for _ in range(5):
        v = anon.get(f"/shared/{share_token}")
        assert v.status_code == 200
        assert "No Longer Available" not in v.text


def test_max_views_enforced(client):
    token = _register(client, "maxviews@example.com")
    contract_id = _upload_contract(client, token)

    r = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "max_views": "2"})
    share_token = r.json()["token"]

    anon = TestClient(main.app)
    assert anon.get(f"/shared/{share_token}").status_code == 200
    assert anon.get(f"/shared/{share_token}").status_code == 200
    blocked = anon.get(f"/shared/{share_token}")
    assert blocked.status_code == 200  # HTML page, not an HTTP error
    assert "No Longer Available" in blocked.text


def test_expired_link_is_blocked(client):
    token = _register(client, "expiry@example.com")
    contract_id = _upload_contract(client, token)

    r = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "expires_in_days": "1"})
    share_token = r.json()["token"]

    # Simulate time passing by moving share_expires_at into the past directly.
    db = SessionLocal()
    try:
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        contract.share_expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    anon = TestClient(main.app)
    r2 = anon.get(f"/shared/{share_token}")
    assert r2.status_code == 200
    assert "No Longer Available" in r2.text


def test_revoked_link_is_blocked_immediately(client):
    token = _register(client, "revoke@example.com")
    contract_id = _upload_contract(client, token)

    r = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token})
    share_token = r.json()["token"]

    anon = TestClient(main.app)
    assert anon.get(f"/shared/{share_token}").status_code == 200  # works before revoke

    revoke = client.post(f"/contract/{contract_id}/share/revoke", data={"csrf_token": token})
    assert revoke.status_code == 200
    assert revoke.json() == {"revoked": True}

    blocked = anon.get(f"/shared/{share_token}")
    assert "No Longer Available" in blocked.text


def test_only_owner_can_revoke(client):
    token = _register(client, "owner@example.com")
    contract_id = _upload_contract(client, token)
    client.post(f"/contract/{contract_id}/share", data={"csrf_token": token})

    other = TestClient(main.app)
    other_token = _register(other, "not-the-owner@example.com")
    r = other.post(f"/contract/{contract_id}/share/revoke", data={"csrf_token": other_token})
    assert r.status_code == 404  # ownership check, not visible to non-owners


def test_only_owner_can_view_share_status(client):
    token = _register(client, "status-owner@example.com")
    contract_id = _upload_contract(client, token)
    client.post(f"/contract/{contract_id}/share", data={"csrf_token": token})

    other = TestClient(main.app)
    _register(other, "status-intruder@example.com")
    r = other.get(f"/contract/{contract_id}/share/status")
    assert r.status_code == 404


def test_resharing_unrevokes_and_resets_view_count(client):
    token = _register(client, "reshare@example.com")
    contract_id = _upload_contract(client, token)

    r = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "max_views": "1"})
    share_token = r.json()["token"]

    anon = TestClient(main.app)
    anon.get(f"/shared/{share_token}")  # consume the single view
    assert "No Longer Available" in anon.get(f"/shared/{share_token}").text

    client.post(f"/contract/{contract_id}/share/revoke", data={"csrf_token": token})

    # Re-share with a fresh limit: un-revokes and resets the counter.
    r2 = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "max_views": "3"})
    assert r2.status_code == 200
    status = client.get(f"/contract/{contract_id}/share/status").json()
    assert status["revoked"] is False
    assert status["view_count"] == 0

    anon2 = TestClient(main.app)
    assert anon2.get(f"/shared/{share_token}").status_code == 200
    assert "No Longer Available" not in anon2.get(f"/shared/{share_token}").text


def test_expires_in_days_rejects_out_of_range_values(client):
    token = _register(client, "badexpiry@example.com")
    contract_id = _upload_contract(client, token)

    r = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "expires_in_days": "0"})
    assert r.status_code == 400
    r2 = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "expires_in_days": "999999"})
    assert r2.status_code == 400
    r3 = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "expires_in_days": "not-a-number"})
    assert r3.status_code == 400


def test_max_views_rejects_out_of_range_values(client):
    token = _register(client, "badviews@example.com")
    contract_id = _upload_contract(client, token)

    r = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "max_views": "0"})
    assert r.status_code == 400
    r2 = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "max_views": "-5"})
    assert r2.status_code == 400


# --- Audit logging ---

def test_share_creation_is_audit_logged(client):
    token = _register(client, "audit-create@example.com")
    contract_id = _upload_contract(client, token)
    client.post(f"/contract/{contract_id}/share", data={"csrf_token": token})

    events = _audit_events("share_link_created", target_id=contract_id)
    assert len(events) == 1
    assert events[0].success is True
    assert events[0].target_type == "contract"


def test_share_revoke_is_audit_logged(client):
    token = _register(client, "audit-revoke@example.com")
    contract_id = _upload_contract(client, token)
    client.post(f"/contract/{contract_id}/share", data={"csrf_token": token})
    client.post(f"/contract/{contract_id}/share/revoke", data={"csrf_token": token})

    events = _audit_events("share_link_revoked", target_id=contract_id)
    assert len(events) == 1
    assert events[0].success is True


def test_successful_and_failed_access_attempts_are_audit_logged(client):
    token = _register(client, "audit-access@example.com")
    contract_id = _upload_contract(client, token)
    r = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "password": "hunter2"})
    share_token = r.json()["token"]

    anon = TestClient(main.app)
    get_page = anon.get(f"/shared/{share_token}")
    csrf_cookie = get_page.cookies.get("csrf_token")
    anon.post(f"/shared/{share_token}", data={"password": "wrong-password", "csrf_token": csrf_cookie})
    anon.post(f"/shared/{share_token}", data={"password": "hunter2", "csrf_token": csrf_cookie})

    events = _audit_events("share_link_accessed", target_id=contract_id)
    outcomes = [(e.success, e.detail) for e in events]
    assert (False, "wrong_password") in outcomes
    assert (True, "viewed") in outcomes


def test_view_count_increments_only_on_successful_render(client):
    token = _register(client, "viewcount@example.com")
    contract_id = _upload_contract(client, token)
    r = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token, "password": "correct-horse"})
    share_token = r.json()["token"]

    anon = TestClient(main.app)
    get_page = anon.get(f"/shared/{share_token}")
    csrf_cookie = get_page.cookies.get("csrf_token")
    # Wrong password attempts must not consume a view.
    anon.post(f"/shared/{share_token}", data={"password": "nope", "csrf_token": csrf_cookie})
    anon.post(f"/shared/{share_token}", data={"password": "nope", "csrf_token": csrf_cookie})

    status = client.get(f"/contract/{contract_id}/share/status").json()
    assert status["view_count"] == 0

    anon.post(f"/shared/{share_token}", data={"password": "correct-horse", "csrf_token": csrf_cookie})
    status2 = client.get(f"/contract/{contract_id}/share/status").json()
    assert status2["view_count"] == 1
