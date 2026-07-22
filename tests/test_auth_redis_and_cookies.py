"""
Tests for Redis fail-closed session storage and secure cookie enforcement
(auth.py, database.py).
"""
import importlib

import pytest

import auth
import database


def _reload_auth_with_env(monkeypatch, **env):
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    return importlib.reload(auth)


@pytest.fixture(autouse=True, scope="module")
def _restore_auth_module():
    yield
    importlib.reload(auth)


class TestRedisFailClosed:
    def test_dev_mode_falls_back_to_in_memory_without_redis_url(self, monkeypatch):
        mod = _reload_auth_with_env(monkeypatch, DEV_MODE="true", REDIS_URL=None)
        mod.init_redis_or_fail()  # must not raise
        assert mod._redis_client is False

    def test_production_without_redis_url_fails_startup(self, monkeypatch):
        mod = _reload_auth_with_env(monkeypatch, DEV_MODE="false", REDIS_URL=None)
        with pytest.raises(RuntimeError, match="REDIS_URL is required"):
            mod.init_redis_or_fail()

    def test_production_with_unreachable_redis_fails_startup(self, monkeypatch):
        mod = _reload_auth_with_env(
            monkeypatch, DEV_MODE="false", REDIS_URL="redis://localhost:1/0",
        )
        with pytest.raises(RuntimeError, match="Redis is required in production"):
            mod.init_redis_or_fail()

    def test_dev_mode_with_unreachable_redis_falls_back(self, monkeypatch):
        mod = _reload_auth_with_env(
            monkeypatch, DEV_MODE="true", REDIS_URL="redis://localhost:1/0",
        )
        mod.init_redis_or_fail()  # must not raise
        assert mod._redis_client is False

    def test_database_wait_for_redis_fails_closed_in_production(self, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "false")
        monkeypatch.delenv("REDIS_URL", raising=False)
        with pytest.raises(RuntimeError, match="REDIS_URL is required"):
            database.wait_for_redis()

    def test_database_wait_for_redis_skips_in_dev_mode(self, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "true")
        monkeypatch.delenv("REDIS_URL", raising=False)
        database.wait_for_redis()  # must not raise


class TestSecureCookies:
    def test_secure_cookies_false_by_default_in_dev(self, monkeypatch):
        mod = _reload_auth_with_env(monkeypatch, SECURE_COOKIES=None)
        assert mod.SECURE_COOKIES is False

    def test_secure_cookies_true_when_configured(self, monkeypatch):
        mod = _reload_auth_with_env(monkeypatch, SECURE_COOKIES="true")
        assert mod.SECURE_COOKIES is True

    def test_create_session_sets_secure_flag_from_config(self, monkeypatch):
        mod = _reload_auth_with_env(monkeypatch, DEV_MODE="true", SECURE_COOKIES="true", REDIS_URL=None)
        mod.init_redis_or_fail()

        from starlette.responses import Response
        response = Response()
        mod.create_session(user_id=1, response=response)

        set_cookie_headers = response.headers.getlist("set-cookie")
        session_cookie = next(h for h in set_cookie_headers if h.startswith(f"{mod.SESSION_COOKIE}="))
        assert "; secure" in session_cookie.lower()
        assert "httponly" in session_cookie.lower()
        assert "samesite=lax" in session_cookie.lower()

    def test_create_session_omits_secure_flag_when_disabled(self, monkeypatch):
        mod = _reload_auth_with_env(monkeypatch, DEV_MODE="true", SECURE_COOKIES="false", REDIS_URL=None)
        mod.init_redis_or_fail()

        from starlette.responses import Response
        response = Response()
        mod.create_session(user_id=1, response=response)

        set_cookie_headers = response.headers.getlist("set-cookie")
        session_cookie = next(h for h in set_cookie_headers if h.startswith(f"{mod.SESSION_COOKIE}="))
        assert "; secure" not in session_cookie.lower()
