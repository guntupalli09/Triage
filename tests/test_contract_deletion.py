"""
Per-contract deletion tests (P4).
"""
import io
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ.setdefault("DEV_MODE", "true")

import main
import rate_limit
from database import SessionLocal, engine as app_engine
from models import AuditLog, Contract
from analytics_models import ContractEvent

NDA_BYTES = b"Confidentiality agreement between Acme Corp and Beta LLC with arbitration and termination clauses."


@pytest.fixture(autouse=True)
def _reset_rate_limits():
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


def test_owner_can_delete_their_own_contract(client):
    token = _register(client, "delete-owner@example.com")
    contract_id = _upload_contract(client, token)

    r = client.post(f"/contract/{contract_id}/delete", data={"csrf_token": token})
    assert r.status_code == 200
    assert r.json() == {"deleted": True}

    db = SessionLocal()
    try:
        assert db.query(Contract).filter(Contract.id == contract_id).first() is None
    finally:
        db.close()


def test_deleted_contract_is_unreachable_via_every_route(client):
    token = _register(client, "delete-unreachable@example.com")
    contract_id = _upload_contract(client, token)
    client.post(f"/contract/{contract_id}/delete", data={"csrf_token": token})

    assert client.get(f"/contract/{contract_id}/review").status_code == 404
    assert client.get(f"/contract/{contract_id}/pdf").status_code == 404
    assert client.get(f"/contract/{contract_id}/share/status").status_code == 404
    assert client.post(f"/contract/{contract_id}/delete", data={"csrf_token": token}).status_code == 404


def test_other_users_contract_cannot_be_deleted(client):
    token = _register(client, "victim@example.com")
    contract_id = _upload_contract(client, token)

    attacker = TestClient(main.app)
    attacker_token = _register(attacker, "attacker@example.com")
    r = attacker.post(f"/contract/{contract_id}/delete", data={"csrf_token": attacker_token})
    assert r.status_code == 404

    # Still there for the real owner.
    db = SessionLocal()
    try:
        assert db.query(Contract).filter(Contract.id == contract_id).first() is not None
    finally:
        db.close()


def test_deletion_removes_extracted_text_and_findings_from_the_database(client):
    """The row itself is gone — contract_text, findings_json, and every
    derived analysis field are removed, not just hidden from the UI."""
    token = _register(client, "delete-content@example.com")
    contract_id = _upload_contract(client, token)

    client.post(f"/contract/{contract_id}/delete", data={"csrf_token": token})

    with app_engine.connect() as conn:
        row = conn.execute(text("SELECT COUNT(*) FROM contracts WHERE id = :id"), {"id": contract_id}).scalar()
    assert row == 0


def test_deletion_cascades_to_contract_events(client):
    token = _register(client, "delete-events@example.com")
    contract_id = _upload_contract(client, token)

    db = SessionLocal()
    try:
        events_before = db.query(ContractEvent).filter(ContractEvent.contract_id == contract_id).count()
        assert events_before >= 1  # upload records a ContractEvent (see analytics.build_contract_event)
    finally:
        db.close()

    client.post(f"/contract/{contract_id}/delete", data={"csrf_token": token})

    db = SessionLocal()
    try:
        events_after = db.query(ContractEvent).filter(ContractEvent.contract_id == contract_id).count()
        assert events_after == 0
    finally:
        db.close()


def test_deleting_a_shared_contract_makes_the_share_link_unreachable(client):
    token = _register(client, "delete-shared@example.com")
    contract_id = _upload_contract(client, token)
    share = client.post(f"/contract/{contract_id}/share", data={"csrf_token": token})
    share_token = share.json()["token"]

    anon = TestClient(main.app)
    assert anon.get(f"/shared/{share_token}").status_code == 200

    client.post(f"/contract/{contract_id}/delete", data={"csrf_token": token})

    anon2 = TestClient(main.app)
    assert anon2.get(f"/shared/{share_token}").status_code == 404


def test_deletion_requires_csrf_token(client):
    token = _register(client, "delete-csrf@example.com")
    contract_id = _upload_contract(client, token)
    r = client.post(f"/contract/{contract_id}/delete")  # no csrf_token field
    assert r.status_code in (403, 422)

    db = SessionLocal()
    try:
        assert db.query(Contract).filter(Contract.id == contract_id).first() is not None
    finally:
        db.close()


def test_deletion_requires_authentication(client):
    token = _register(client, "delete-auth@example.com")
    contract_id = _upload_contract(client, token)

    anon = TestClient(main.app)
    r = anon.post(f"/contract/{contract_id}/delete", data={"csrf_token": "whatever"})
    assert r.status_code in (302, 401, 403)

    db = SessionLocal()
    try:
        assert db.query(Contract).filter(Contract.id == contract_id).first() is not None
    finally:
        db.close()


def test_deletion_is_audit_logged(client):
    token = _register(client, "delete-audit@example.com")
    contract_id = _upload_contract(client, token)
    client.post(f"/contract/{contract_id}/delete", data={"csrf_token": token})

    db = SessionLocal()
    try:
        events = db.query(AuditLog).filter(
            AuditLog.event_type == "contract_deleted", AuditLog.target_id == contract_id,
        ).all()
        assert len(events) == 1
        assert events[0].success is True
        assert events[0].metadata_json.get("filename") == "nda.txt"
    finally:
        db.close()


def test_deleting_nonexistent_contract_returns_404(client):
    token = _register(client, "delete-missing@example.com")
    r = client.post("/contract/999999/delete", data={"csrf_token": token})
    assert r.status_code == 404


def test_deleting_one_contract_does_not_affect_others(client):
    token = _register(client, "delete-selective@example.com")
    contract_id_1 = _upload_contract(client, token)
    contract_id_2 = _upload_contract(client, token)

    client.post(f"/contract/{contract_id_1}/delete", data={"csrf_token": token})

    assert client.get(f"/contract/{contract_id_1}/review").status_code == 404
    assert client.get(f"/contract/{contract_id_2}/review").status_code == 200
