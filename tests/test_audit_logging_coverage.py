"""
Enterprise audit logging coverage tests (P7): login/logout, account
create/delete, uploads, exports, playbook changes, admin access, and
failed authorization all produce AuditLog rows. Share-link events are
already covered by test_share_link_hardening.py (P3); contract deletion
by test_contract_deletion.py (P4).
"""
import io
import os

import pytest
from fastapi.testclient import TestClient
from fpdf import FPDF

os.environ.setdefault("DEV_MODE", "true")

import main
import rate_limit
from database import SessionLocal
from models import AuditLog

NDA_BYTES = b"Confidentiality agreement between Acme Corp and Beta LLC with termination and arbitration clauses."


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


def _events(event_type: str, target_id=None):
    db = SessionLocal()
    try:
        q = db.query(AuditLog).filter(AuditLog.event_type == event_type)
        if target_id is not None:
            q = q.filter(AuditLog.target_id == target_id)
        return q.all()
    finally:
        db.close()


def test_account_created_is_audit_logged(client):
    _register(client, "audit-signup@example.com")
    events = _events("account_created")
    assert any(e.success is True for e in events)


def test_successful_login_is_audit_logged(client):
    email = "audit-login@example.com"
    token = _register(client, email)
    client.get("/logout")  # end the session register() left us in
    client.get("/login")
    # The csrf_token cookie was already issued on an earlier response in
    # this session (register()'s first request) and isn't re-sent on every
    # subsequent response — read it from the persistent cookie jar, not
    # this specific response's Set-Cookie (which won't be present).
    login_token = client.cookies.get("csrf_token")
    client.post("/login", data={"email": email, "password": "Str0ngP@ssw0rd!", "csrf_token": login_token})

    events = _events("login")
    assert any(e.success is True for e in events)


def test_failed_login_is_audit_logged(client):
    r = client.get("/login")
    token = r.cookies.get("csrf_token")
    client.post("/login", data={"email": "nobody@example.com", "password": "wrong", "csrf_token": token})

    events = _events("login_failed")
    assert len(events) >= 1
    assert events[-1].success is False
    assert events[-1].detail == "invalid_credentials"


def test_logout_is_audit_logged(client):
    token = _register(client, "audit-logout@example.com")
    client.get("/logout")
    events = _events("logout")
    assert any(e.success is True for e in events)


def test_account_deletion_is_audit_logged(client):
    token = _register(client, "audit-delete-account@example.com")
    r = client.post("/settings/delete-account", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code in (302, 303)
    events = _events("account_deleted")
    assert any(e.success is True and e.metadata_json.get("email") == "audit-delete-account@example.com" for e in events)


def test_contract_upload_is_audit_logged(client):
    token = _register(client, "audit-upload@example.com")
    contract_id = _upload_contract(client, token)
    events = _events("contract_uploaded", target_id=contract_id)
    assert len(events) == 1
    assert events[0].success is True


def test_pdf_export_is_audit_logged(client):
    token = _register(client, "audit-export-pdf@example.com")
    contract_id = _upload_contract(client, token)
    r = client.get(f"/contract/{contract_id}/pdf")
    assert r.status_code == 200

    events = _events("contract_exported", target_id=contract_id)
    assert any(e.detail == "pdf" for e in events)


def test_playbook_create_update_delete_are_audit_logged(client):
    token = _register(client, "audit-playbook@example.com")
    files = {"file": ("template.txt", io.BytesIO(b"Standard NDA template with confidentiality terms."), "text/plain")}
    r = client.post(
        "/playbooks/new",
        data={"name": "Standard NDA", "contract_type": "NDA", "description": "", "csrf_token": token},
        files=files, follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    from models import Playbook
    db = SessionLocal()
    try:
        playbook = db.query(Playbook).filter(Playbook.name == "Standard NDA").first()
        assert playbook is not None
        playbook_id = playbook.id
    finally:
        db.close()

    created = _events("playbook_created", target_id=playbook_id)
    assert len(created) == 1

    client.post(
        f"/playbooks/{playbook_id}/edit",
        data={"name": "Standard NDA v2", "contract_type": "NDA", "description": "", "csrf_token": token},
    )
    updated = _events("playbook_updated", target_id=playbook_id)
    assert len(updated) == 1

    client.post(f"/playbooks/{playbook_id}/delete", data={"csrf_token": token})
    deleted = _events("playbook_deleted", target_id=playbook_id)
    assert len(deleted) == 1
    assert deleted[0].metadata_json.get("name") == "Standard NDA v2"


def test_non_admin_accessing_admin_route_is_audit_logged_as_denied(client):
    token = _register(client, "audit-notadmin@example.com")
    r = client.get("/admin")
    assert r.status_code == 403

    events = _events("admin_access_denied")
    assert any(e.detail == "not_admin" and e.metadata_json.get("path") == "/admin" for e in events)


def test_admin_dashboard_access_is_audit_logged(monkeypatch):
    """The audit_log call in admin_dashboard() runs immediately after the
    require_admin() check succeeds, before the route's own (pre-existing,
    unrelated to this security pass) analytics queries — see
    docs/security/known_issues.md for the SQLite date-cast bug those
    queries hit. raise_server_exceptions=False lets this test observe the
    audit write despite that unrelated route bug, rather than depending on
    a clean 200 response the route doesn't currently produce."""
    admin_email = "admin-audit-test@example.com"
    monkeypatch.setattr(main, "ADMIN_EMAIL", admin_email)
    with TestClient(main.app, raise_server_exceptions=False) as c:
        token = _register(c, admin_email)
        c.get("/admin")

    events = _events("admin_dashboard_accessed")
    assert any(e.success is True for e in events)
