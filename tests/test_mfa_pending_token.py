"""
Tests for auth.py's MFA-pending token helpers: create_mfa_pending(),
get_mfa_pending_user_id(), clear_mfa_pending() — the short-lived state
between a correct password and a completed login when MFA is enabled.
"""
import os
import time

os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi import Response
from starlette.requests import Request

import auth


class _FakeRequest:
    def __init__(self, cookies: dict):
        self.cookies = cookies


@pytest.fixture(autouse=True)
def _isolate_session_store(monkeypatch):
    monkeypatch.setattr(auth, "_sessions", {})
    monkeypatch.setattr(auth, "_redis_client", False)  # force in-memory path


def test_create_mfa_pending_sets_cookie_and_is_retrievable():
    response = Response()
    token = auth.create_mfa_pending(user_id=42, response=response)
    assert token

    set_cookie_header = response.headers.get("set-cookie", "")
    assert auth.MFA_PENDING_COOKIE in set_cookie_header
    assert "httponly" in set_cookie_header.lower()

    request = _FakeRequest(cookies={auth.MFA_PENDING_COOKIE: token})
    assert auth.get_mfa_pending_user_id(request) == 42


def test_mfa_pending_token_does_not_collide_with_session_store():
    """The mfapending: prefix must keep this fully separate from real
    session tokens — a stolen MFA-pending cookie must never resolve as an
    authenticated session."""
    response = Response()
    token = auth.create_mfa_pending(user_id=1, response=response)

    session_request = _FakeRequest(cookies={auth.SESSION_COOKIE: token})
    from database import SessionLocal
    db = SessionLocal()
    try:
        assert auth.get_current_user(session_request, db) is None
    finally:
        db.close()


def test_get_mfa_pending_user_id_returns_none_without_cookie():
    request = _FakeRequest(cookies={})
    assert auth.get_mfa_pending_user_id(request) is None


def test_get_mfa_pending_user_id_returns_none_for_unknown_token():
    request = _FakeRequest(cookies={auth.MFA_PENDING_COOKIE: "not-a-real-token"})
    assert auth.get_mfa_pending_user_id(request) is None


def test_clear_mfa_pending_invalidates_the_token():
    response = Response()
    token = auth.create_mfa_pending(user_id=7, response=response)
    request = _FakeRequest(cookies={auth.MFA_PENDING_COOKIE: token})

    clear_response = Response()
    auth.clear_mfa_pending(request, clear_response)

    assert auth.get_mfa_pending_user_id(request) is None
    assert "Max-Age=0" in clear_response.headers.get("set-cookie", "") or \
           clear_response.headers.get("set-cookie", "").endswith('=""') or \
           auth.MFA_PENDING_COOKIE in clear_response.headers.get("set-cookie", "")


def test_mfa_pending_token_expires(monkeypatch):
    monkeypatch.setattr(auth, "MFA_PENDING_MAX_AGE", 0)  # expires immediately
    response = Response()
    token = auth.create_mfa_pending(user_id=9, response=response)
    request = _FakeRequest(cookies={auth.MFA_PENDING_COOKIE: token})
    time.sleep(0.01)
    assert auth.get_mfa_pending_user_id(request) is None
