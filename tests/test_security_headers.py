"""
Security headers middleware tests (Priority 1a of the enterprise security
hardening pass — see docs/security/audit findings).
"""
import importlib
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# main.py validates production-only env vars (Stripe, etc.) at import time;
# run this test module the same way local/dev instances run.
os.environ.setdefault("DEV_MODE", "true")

import main
import security_headers


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def test_content_security_policy_present(client):
    r = client.get("/health")
    csp = r.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp


def test_frame_options_denies_framing(client):
    r = client.get("/health")
    assert r.headers.get("X-Frame-Options") == "DENY"


def test_content_type_options_nosniff(client):
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


def test_referrer_policy_restrictive(client):
    r = client.get("/health")
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_permissions_policy_present(client):
    r = client.get("/health")
    pp = r.headers.get("Permissions-Policy")
    assert pp is not None
    assert "geolocation=()" in pp


def _minimal_app_with_middleware() -> FastAPI:
    app = FastAPI()
    app.add_middleware(security_headers.SecurityHeadersMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_hsts_absent_when_not_secure_deployment(monkeypatch):
    """HSTS must not be advertised for a deployment that hasn't opted into
    SECURE_COOKIES=true (i.e. isn't guaranteed to be served over HTTPS)."""
    monkeypatch.setattr(security_headers, "_SECURE_DEPLOYMENT", False)
    app = _minimal_app_with_middleware()
    with TestClient(app) as c:
        r = c.get("/ping")
        assert r.headers.get("Strict-Transport-Security") is None


def test_hsts_present_when_secure_deployment(monkeypatch):
    """Once the deployment sets SECURE_COOKIES=true (HTTPS is guaranteed),
    HSTS must be advertised so browsers enforce it on future visits."""
    monkeypatch.setattr(security_headers, "_SECURE_DEPLOYMENT", True)
    app = _minimal_app_with_middleware()
    with TestClient(app) as c:
        r = c.get("/ping")
        assert "max-age=" in r.headers.get("Strict-Transport-Security", "")


def test_secure_deployment_flag_reads_env_at_import_time(monkeypatch):
    """Guards against a future refactor accidentally reading SECURE_COOKIES
    per-request instead of once at import (the current, intentional design:
    it mirrors how auth.py gates the Secure cookie flag)."""
    monkeypatch.setenv("SECURE_COOKIES", "true")
    importlib.reload(security_headers)
    assert security_headers._SECURE_DEPLOYMENT is True

    monkeypatch.setenv("SECURE_COOKIES", "false")
    importlib.reload(security_headers)
    assert security_headers._SECURE_DEPLOYMENT is False
