"""
Tests for production secret/config enforcement (security_config.py).
"""
import importlib

import pytest

import security_config


def _reload_with_env(monkeypatch, **env):
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    return importlib.reload(security_config)


PROD_OK_ENV = dict(
    DEV_MODE="false",
    APP_HMAC_SECRET="a" * 32,
    SESSION_SECRET="b" * 32,
    BASE_URL="https://example.com",
    SECURE_COOKIES="true",
)


def test_dev_mode_never_blocks(monkeypatch):
    mod = _reload_with_env(monkeypatch, DEV_MODE="true", APP_HMAC_SECRET=None,
                            SESSION_SECRET=None, BASE_URL=None, SECURE_COOKIES=None)
    mod.validate_production_config()  # must not raise


def test_production_with_valid_config_passes(monkeypatch):
    mod = _reload_with_env(monkeypatch, **PROD_OK_ENV)
    mod.validate_production_config()  # must not raise


@pytest.mark.parametrize("overrides,expected_fragment", [
    ({"APP_HMAC_SECRET": "dev_secret_change_me"}, "APP_HMAC_SECRET"),
    ({"APP_HMAC_SECRET": "short"}, "APP_HMAC_SECRET"),
    ({"SESSION_SECRET": "dev_session_secret_change_me"}, "SESSION_SECRET"),
    ({"SESSION_SECRET": None}, "SESSION_SECRET"),
    ({"BASE_URL": "http://localhost:8000"}, "BASE_URL"),
    ({"BASE_URL": "http://example.com"}, "BASE_URL"),
    ({"BASE_URL": None}, "BASE_URL"),
    ({"SECURE_COOKIES": "false"}, "SECURE_COOKIES"),
])
def test_production_rejects_insecure_config(monkeypatch, overrides, expected_fragment):
    env = dict(PROD_OK_ENV)
    env.update(overrides)
    mod = _reload_with_env(monkeypatch, **env)
    with pytest.raises(RuntimeError) as exc_info:
        mod.validate_production_config()
    assert expected_fragment in str(exc_info.value)


def test_secure_cookies_flag_reflects_env(monkeypatch):
    mod = _reload_with_env(monkeypatch, DEV_MODE="true", SECURE_COOKIES="true")
    assert mod.SECURE_COOKIES is True
    mod = _reload_with_env(monkeypatch, DEV_MODE="true", SECURE_COOKIES="false")
    assert mod.SECURE_COOKIES is False


@pytest.fixture(autouse=True, scope="module")
def _restore_module_state():
    """Reload security_config once more after this file's tests, reflecting
    the test suite's real env (DEV_MODE=true, see conftest.py) — reload()
    mutates the shared module object in sys.modules, and other test modules
    importing security_config would otherwise see whatever state the last
    test in this file left behind."""
    yield
    importlib.reload(security_config)
