"""
Rate limiting tests (P1c). No Redis is available in the test environment,
so these exercise the in-memory fallback path directly, plus an end-to-end
check that a real route (POST /login) actually returns 429 once its bucket
is exhausted.
"""
import os

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

import rate_limit

os.environ.setdefault("DEV_MODE", "true")


@pytest.fixture(autouse=True)
def _isolate_state(monkeypatch):
    """Every test gets a fresh in-memory counter table and no Redis, so
    tests can't leak rate-limit state into each other or depend on a
    Redis instance being reachable in CI."""
    monkeypatch.setattr(rate_limit, "_memory_counters", {})
    monkeypatch.setattr(rate_limit, "_redis_client", False)  # False = "checked, unavailable"
    monkeypatch.delenv("REDIS_URL", raising=False)


def test_allows_requests_under_the_limit():
    for _ in range(5):
        allowed, retry_after = rate_limit._check_and_increment("k", limit=5, window_seconds=60)
        assert allowed is True
        assert retry_after == 0


def test_blocks_requests_over_the_limit():
    for _ in range(5):
        rate_limit._check_and_increment("k", limit=5, window_seconds=60)
    allowed, retry_after = rate_limit._check_and_increment("k", limit=5, window_seconds=60)
    assert allowed is False
    assert retry_after > 0


def test_different_keys_have_independent_budgets():
    for _ in range(5):
        rate_limit._check_and_increment("bucket-a", limit=5, window_seconds=60)
    # bucket-a is now exhausted; bucket-b must still be fresh.
    allowed, _ = rate_limit._check_and_increment("bucket-b", limit=5, window_seconds=60)
    assert allowed is True


def _app_with_limited_route():
    app = FastAPI()

    @app.post("/limited")
    def limited(_: None = Depends(rate_limit.rate_limit("limited-route", limit=3, window_seconds=60))):
        return {"ok": True}

    return app


def test_dependency_returns_429_with_retry_after_header():
    app = _app_with_limited_route()
    with TestClient(app) as c:
        for _ in range(3):
            r = c.post("/limited")
            assert r.status_code == 200
        r = c.post("/limited")
        assert r.status_code == 429
        assert "Retry-After" in r.headers


def test_dependency_keys_by_client_ip(monkeypatch):
    """Two different client IPs must not share a budget."""
    from analytics import extract_ip as real_extract_ip

    calls = {"ip": "1.2.3.4"}

    def fake_extract_ip(request):
        return calls["ip"]

    monkeypatch.setattr(rate_limit, "extract_ip", fake_extract_ip)

    app = _app_with_limited_route()
    with TestClient(app) as c:
        for _ in range(3):
            assert c.post("/limited").status_code == 200
        assert c.post("/limited").status_code == 429

        calls["ip"] = "5.6.7.8"
        assert c.post("/limited").status_code == 200  # fresh budget for the new IP


def test_login_route_rate_limited_after_repeated_attempts():
    """End-to-end: hammering POST /login from the same client eventually
    gets a 429 instead of an infinite budget for credential stuffing."""
    import main
    with TestClient(main.app) as c:
        last_status = None
        for _ in range(15):
            r = c.post("/login", data={"email": "nobody@example.com", "password": "wrong"})
            last_status = r.status_code
            if last_status == 429:
                break
        assert last_status == 429
