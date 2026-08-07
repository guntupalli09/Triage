"""
CSRF protection tests (P1b).

Covers: cookie issuance on first visit, rejection of POSTs with a missing
or mismatched token, acceptance with a matching token, and that the
Jinja `csrf_token(request)` global renders the same value embedded in a
GET-rendered form as the cookie the browser will send back.
"""
import os

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DEV_MODE", "true")

import csrf
import main


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def test_first_visit_issues_csrf_cookie(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert "csrf_token" in r.cookies
    assert len(r.cookies["csrf_token"]) > 20


def test_csrf_cookie_is_httponly():
    app = FastAPI()
    app.add_middleware(csrf.CSRFCookieMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    with TestClient(app) as c:
        r = c.get("/ping")
        set_cookie = r.headers.get("set-cookie", "")
        assert "csrf_token=" in set_cookie
        assert "httponly" in set_cookie.lower()


def test_cookie_is_stable_across_requests(client):
    r1 = client.get("/login")
    token1 = r1.cookies.get("csrf_token")
    r2 = client.get("/register")
    token2 = client.cookies.get("csrf_token")
    assert token1 == token2  # same browser session keeps the same token


def test_form_renders_matching_hidden_csrf_field(client):
    r = client.get("/login")
    cookie_token = r.cookies.get("csrf_token")
    assert f'name="csrf_token" value="{cookie_token}"' in r.text


def test_post_without_csrf_token_is_rejected(client):
    client.get("/login")  # establish the csrf cookie
    r = client.post("/login", data={"email": "a@b.com", "password": "x"})
    assert r.status_code in (403, 422)  # missing required field or explicit reject


def test_post_with_mismatched_csrf_token_is_rejected(client):
    client.get("/login")
    r = client.post("/login", data={"email": "a@b.com", "password": "x", "csrf_token": "forged-value"})
    assert r.status_code == 403


def test_post_with_valid_csrf_token_passes_csrf_layer(client):
    r = client.get("/login")
    token = r.cookies.get("csrf_token")
    r2 = client.post("/login", data={"email": "nobody@example.com", "password": "wrong", "csrf_token": token})
    # Wrong credentials, but this proves CSRF didn't block it (would be 403 otherwise) —
    # it re-renders the login form with an "Invalid email or password" error.
    assert r2.status_code == 200
    assert "Invalid email or password" in r2.text


def test_csrf_protect_dependency_rejects_missing_cookie():
    """Simulates a request with a csrf_token form field but no cookie at
    all (e.g. cookies blocked, or a raw forged POST with a guessed field
    name but no way to read/set the victim's HttpOnly cookie)."""
    app = FastAPI()

    @app.post("/protected")
    def protected(_: None = Depends(csrf.csrf_protect)):
        return {"ok": True}

    with TestClient(app) as c:
        r = c.post("/protected", data={"csrf_token": "anything"})
        assert r.status_code == 403


def test_csrf_protect_dependency_accepts_matching_cookie_and_field():
    app = FastAPI()
    app.add_middleware(csrf.CSRFCookieMiddleware)

    @app.post("/protected")
    def protected(_: None = Depends(csrf.csrf_protect)):
        return {"ok": True}

    with TestClient(app) as c:
        c.cookies.set(csrf.CSRF_COOKIE, "known-good-token")
        r = c.post("/protected", data={"csrf_token": "known-good-token"})
        assert r.status_code == 200


def test_stripe_webhook_is_exempt_from_csrf(client):
    """The webhook is authenticated by Stripe's own request signature, not
    cookies, and must remain reachable without a csrf_token field."""
    r = client.post("/stripe-webhook", content=b"{}")
    # DEV_MODE short-circuits this route to {"status": "ignored"} (200) —
    # the assertion that matters is that it's NOT blocked by CSRF (403/422).
    assert r.status_code == 200
