"""
Integration tests for CSRF protection, security headers, and rate limiting,
exercised through the real FastAPI app (DEV_MODE=true, see conftest.py).
"""
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


def _get_csrf_cookie(client) -> str:
    client.get("/login")
    token = client.cookies.get("csrf_token")
    assert token, "CSRFCookieMiddleware should mint a csrf_token cookie on GET"
    return token


class TestCSRF:
    def test_post_without_token_is_rejected(self, client):
        response = client.post("/login", data={"email": "a@b.com", "password": "x"})
        assert response.status_code == 403

    def test_post_with_mismatched_token_is_rejected(self, client):
        _get_csrf_cookie(client)
        response = client.post(
            "/login",
            data={"email": "a@b.com", "password": "x", "csrf_token": "not-the-real-token"},
        )
        assert response.status_code == 403

    def test_post_with_valid_form_token_is_accepted(self, client):
        token = _get_csrf_cookie(client)
        response = client.post(
            "/login",
            data={"email": "nobody@example.com", "password": "wrong", "csrf_token": token},
        )
        # Wrong credentials, but the request must clear CSRF validation and
        # reach the route (which re-renders the login form, not a 403).
        assert response.status_code == 200
        assert "Invalid email or password" in response.text

    def test_post_with_valid_header_token_is_accepted(self, client):
        token = _get_csrf_cookie(client)
        response = client.post(
            "/login",
            data={"email": "nobody@example.com", "password": "wrong"},
            headers={"X-CSRF-Token": token},
        )
        assert response.status_code == 200
        assert "Invalid email or password" in response.text

    def test_stripe_webhook_is_exempt_from_csrf(self, client):
        # No csrf_token at all — must not 403 on CSRF grounds. It still 400s
        # because the signature is missing/invalid, which is the webhook's
        # own (correct) auth mechanism.
        response = client.post("/stripe-webhook", content=b"{}")
        assert response.status_code != 403


class TestSecurityHeaders:
    def test_headers_present_on_response(self, client):
        response = client.get("/")
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "camera=()" in response.headers.get("permissions-policy", "")
        csp = response.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_no_hsts_header_in_dev_mode(self, client):
        # DEV_MODE=true for the whole test suite (see conftest.py) — HSTS
        # would tell browsers to force HTTPS, which would break local http://
        # development.
        response = client.get("/")
        assert "strict-transport-security" not in {h.lower() for h in response.headers}


class TestRateLimiting:
    def test_login_is_rate_limited_per_ip(self, client):
        token = _get_csrf_cookie(client)
        statuses = []
        for _ in range(15):
            r = client.post(
                "/login",
                data={"email": "ratelimit@example.com", "password": "x", "csrf_token": token},
            )
            statuses.append(r.status_code)
        assert 429 in statuses, f"expected a 429 among {statuses}"

    def test_rate_limited_response_has_detail(self, client):
        token = _get_csrf_cookie(client)
        last = None
        for _ in range(15):
            last = client.post(
                "/register",
                data={
                    "email": "flood@example.com", "password": "longenough1",
                    "confirm_password": "longenough1", "csrf_token": token,
                },
            )
        assert last.status_code == 429
        assert "detail" in last.json()
