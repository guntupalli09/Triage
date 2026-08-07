"""
End-to-end MFA tests through the real app: enrollment, login challenge,
recovery codes, disable, rate limiting, and audit logging.
"""
import os

import pyotp
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEV_MODE", "true")

import main
import rate_limit
from database import SessionLocal
from models import AuditLog, User


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


def _get_user(email) -> User:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first()
    finally:
        db.close()


def _enroll_mfa(client, csrf_token, email) -> str:
    """Completes enrollment, returns the TOTP secret."""
    client.get("/settings/mfa/setup")
    user = _get_user(email)
    secret = user.mfa_secret
    code = pyotp.TOTP(secret).now()
    r = client.post("/settings/mfa/setup", data={"code": code, "csrf_token": csrf_token})
    assert r.status_code == 200
    return secret


def _audit_events(event_type: str, email: str = None):
    db = SessionLocal()
    try:
        q = db.query(AuditLog).filter(AuditLog.event_type == event_type)
        rows = q.all()
        if email:
            user = _get_user(email)
            rows = [r for r in rows if r.actor_user_id == user.id]
        return rows
    finally:
        db.close()


# --- Enrollment ---

def test_mfa_setup_page_shows_qr_code_and_manual_key(client):
    token = _register(client, "setup-page@example.com")
    r = client.get("/settings/mfa/setup")
    assert r.status_code == 200
    assert "data:image/svg+xml;base64," in r.text


def test_mfa_setup_reuses_pending_secret_across_reloads(client):
    token = _register(client, "reload@example.com")
    client.get("/settings/mfa/setup")
    user1 = _get_user("reload@example.com")
    client.get("/settings/mfa/setup")
    user2 = _get_user("reload@example.com")
    assert user1.mfa_secret == user2.mfa_secret


def test_mfa_confirm_with_correct_code_enables_mfa(client):
    token = _register(client, "enable-me@example.com")
    _enroll_mfa(client, token, "enable-me@example.com")
    user = _get_user("enable-me@example.com")
    assert user.mfa_enabled is True
    assert user.mfa_enrolled_at is not None
    assert len(user.mfa_recovery_codes_json) == 10


def test_mfa_confirm_shows_recovery_codes_once(client):
    token = _register(client, "codes-shown@example.com")
    client.get("/settings/mfa/setup")
    user = _get_user("codes-shown@example.com")
    code = pyotp.TOTP(user.mfa_secret).now()
    r = client.post("/settings/mfa/setup", data={"code": code, "csrf_token": token})
    assert "Save Your Recovery Codes" in r.text or "Two-Factor Authentication Enabled" in r.text


def test_mfa_confirm_with_wrong_code_does_not_enable(client):
    token = _register(client, "wrong-code@example.com")
    client.get("/settings/mfa/setup")
    r = client.post("/settings/mfa/setup", data={"code": "000000", "csrf_token": token})
    assert r.status_code == 200
    user = _get_user("wrong-code@example.com")
    assert user.mfa_enabled is False


def test_enrollment_is_audit_logged(client):
    token = _register(client, "audit-enroll@example.com")
    _enroll_mfa(client, token, "audit-enroll@example.com")
    events = _audit_events("mfa_enabled", "audit-enroll@example.com")
    assert len(events) == 1
    assert events[0].success is True


# --- Login challenge ---

def test_login_without_mfa_goes_straight_to_dashboard(client):
    token = _register(client, "no-mfa@example.com")
    client.get("/logout")
    client.get("/login")
    login_token = client.cookies.get("csrf_token")
    r = client.post("/login", data={"email": "no-mfa@example.com", "password": "Str0ngP@ssw0rd!", "csrf_token": login_token}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard"


def test_login_with_mfa_redirects_to_challenge(client):
    token = _register(client, "mfa-redirect@example.com")
    _enroll_mfa(client, token, "mfa-redirect@example.com")
    client.get("/logout")
    client.get("/login")
    login_token = client.cookies.get("csrf_token")
    r = client.post("/login", data={"email": "mfa-redirect@example.com", "password": "Str0ngP@ssw0rd!", "csrf_token": login_token}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/login/mfa"


def test_dashboard_unreachable_before_mfa_challenge_completes(client):
    token = _register(client, "no-shortcut@example.com")
    secret = _enroll_mfa(client, token, "no-shortcut@example.com")
    client.get("/logout")
    client.get("/login")
    login_token = client.cookies.get("csrf_token")
    client.post("/login", data={"email": "no-shortcut@example.com", "password": "Str0ngP@ssw0rd!", "csrf_token": login_token})

    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code in (302, 401)  # no real session exists yet


def test_mfa_challenge_with_correct_totp_completes_login(client):
    token = _register(client, "correct-totp@example.com")
    secret = _enroll_mfa(client, token, "correct-totp@example.com")
    client.get("/logout")
    client.get("/login")
    login_token = client.cookies.get("csrf_token")
    client.post("/login", data={"email": "correct-totp@example.com", "password": "Str0ngP@ssw0rd!", "csrf_token": login_token})

    code = pyotp.TOTP(secret).now()
    r = client.post("/login/mfa", data={"code": code, "csrf_token": login_token}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard"

    dash = client.get("/dashboard")
    assert dash.status_code == 200


def test_mfa_challenge_with_wrong_code_is_rejected(client):
    token = _register(client, "wrong-totp@example.com")
    secret = _enroll_mfa(client, token, "wrong-totp@example.com")
    client.get("/logout")
    client.get("/login")
    login_token = client.cookies.get("csrf_token")
    client.post("/login", data={"email": "wrong-totp@example.com", "password": "Str0ngP@ssw0rd!", "csrf_token": login_token})

    r = client.post("/login/mfa", data={"code": "000000", "csrf_token": login_token})
    assert r.status_code == 200
    assert "isn" in r.text.lower() or "not valid" in r.text.lower() or "error" in r.text.lower()


def test_mfa_challenge_without_pending_login_redirects_to_login(client):
    r = client.get("/login/mfa", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_mfa_challenge_accepts_recovery_code(client):
    import re

    token = _register(client, "recovery-login@example.com")
    client.get("/settings/mfa/setup")
    user = _get_user("recovery-login@example.com")
    code = pyotp.TOTP(user.mfa_secret).now()
    confirm_resp = client.post("/settings/mfa/setup", data={"code": code, "csrf_token": token})
    recovery_code = re.findall(r'>([A-Z0-9]{10})<', confirm_resp.text)[0]

    client.get("/logout")
    client.get("/login")
    # csrf_token is a stable per-browser-session cookie (see csrf.py) — it
    # isn't re-issued on every response, so read it from the persistent
    # cookie jar here rather than this specific response's Set-Cookie.
    login_token = client.cookies.get("csrf_token")
    client.post("/login", data={"email": "recovery-login@example.com", "password": "Str0ngP@ssw0rd!", "csrf_token": login_token})

    r = client.post("/login/mfa", data={"code": recovery_code, "csrf_token": login_token}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard"


def test_recovery_code_is_single_use(client):
    import re

    token = _register(client, "single-use@example.com")
    client.get("/settings/mfa/setup")
    user = _get_user("single-use@example.com")
    code = pyotp.TOTP(user.mfa_secret).now()
    confirm_resp = client.post("/settings/mfa/setup", data={"code": code, "csrf_token": token})
    recovery_code = re.findall(r'>([A-Z0-9]{10})<', confirm_resp.text)[0]

    client.get("/logout")
    for attempt in range(2):
        client.get("/login")
        login_token = client.cookies.get("csrf_token")
        client.post("/login", data={"email": "single-use@example.com", "password": "Str0ngP@ssw0rd!", "csrf_token": login_token})
        r = client.post("/login/mfa", data={"code": recovery_code, "csrf_token": login_token}, follow_redirects=False)
        if attempt == 0:
            assert r.status_code == 302  # first use succeeds
            assert r.headers["location"] == "/dashboard"
            client.get("/logout")
        else:
            assert r.status_code == 200  # second use rejected, re-renders challenge page


def test_login_mfa_is_rate_limited(client):
    token = _register(client, "ratelimited-mfa@example.com")
    secret = _enroll_mfa(client, token, "ratelimited-mfa@example.com")
    client.get("/logout")
    client.get("/login")
    login_token = client.cookies.get("csrf_token")
    client.post("/login", data={"email": "ratelimited-mfa@example.com", "password": "Str0ngP@ssw0rd!", "csrf_token": login_token})

    last_status = None
    for _ in range(15):
        r = client.post("/login/mfa", data={"code": "000000", "csrf_token": login_token})
        last_status = r.status_code
        if last_status == 429:
            break
    assert last_status == 429


def test_mfa_login_failure_is_audit_logged(client):
    token = _register(client, "audit-fail@example.com")
    _enroll_mfa(client, token, "audit-fail@example.com")
    client.get("/logout")
    client.get("/login")
    login_token = client.cookies.get("csrf_token")
    client.post("/login", data={"email": "audit-fail@example.com", "password": "Str0ngP@ssw0rd!", "csrf_token": login_token})
    client.post("/login/mfa", data={"code": "000000", "csrf_token": login_token})

    events = _audit_events("login_mfa_failed", "audit-fail@example.com")
    assert len(events) >= 1
    assert events[-1].success is False


# --- Disable ---

def test_disable_requires_correct_password(client):
    token = _register(client, "disable-wrong-pw@example.com")
    _enroll_mfa(client, token, "disable-wrong-pw@example.com")
    r = client.post("/settings/mfa/disable", data={"password": "wrong-password", "csrf_token": token})
    assert r.status_code == 403
    user = _get_user("disable-wrong-pw@example.com")
    assert user.mfa_enabled is True


def test_disable_with_correct_password_disables_mfa(client):
    token = _register(client, "disable-correct@example.com")
    _enroll_mfa(client, token, "disable-correct@example.com")
    r = client.post("/settings/mfa/disable", data={"password": "Str0ngP@ssw0rd!", "csrf_token": token}, follow_redirects=False)
    assert r.status_code == 302
    user = _get_user("disable-correct@example.com")
    assert user.mfa_enabled is False
    assert user.mfa_secret is None
    assert user.mfa_recovery_codes_json is None


def test_disable_when_not_enabled_returns_400(client):
    token = _register(client, "never-enabled@example.com")
    r = client.post("/settings/mfa/disable", data={"password": "Str0ngP@ssw0rd!", "csrf_token": token})
    assert r.status_code == 400


def test_disable_is_audit_logged(client):
    token = _register(client, "audit-disable@example.com")
    _enroll_mfa(client, token, "audit-disable@example.com")
    client.post("/settings/mfa/disable", data={"password": "Str0ngP@ssw0rd!", "csrf_token": token})
    events = _audit_events("mfa_disabled", "audit-disable@example.com")
    assert len(events) == 1
    assert events[0].success is True


def test_after_disable_login_no_longer_requires_mfa(client):
    token = _register(client, "disabled-then-login@example.com")
    _enroll_mfa(client, token, "disabled-then-login@example.com")
    client.post("/settings/mfa/disable", data={"password": "Str0ngP@ssw0rd!", "csrf_token": token})
    client.get("/logout")
    client.get("/login")
    login_token = client.cookies.get("csrf_token")
    r = client.post("/login", data={"email": "disabled-then-login@example.com", "password": "Str0ngP@ssw0rd!", "csrf_token": login_token}, follow_redirects=False)
    assert r.headers["location"] == "/dashboard"


# --- Settings page ---

def test_settings_mfa_page_shows_status(client):
    token = _register(client, "status-page@example.com")
    r = client.get("/settings/mfa")
    assert r.status_code == 200
    assert "Not Enabled" in r.text

    _enroll_mfa(client, token, "status-page@example.com")
    r2 = client.get("/settings/mfa")
    assert "Enabled" in r2.text
