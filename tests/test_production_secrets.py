"""
Production secret-strength and secure-cookie-default enforcement (P1d).

main.py validates APP_HMAC_SECRET/SESSION_SECRET at *import* time (mirroring
the existing STRIPE_SECRET_KEY/OPENAI_API_KEY production checks), so these
tests spawn a subprocess per case rather than importing main.py in-process —
reload-based testing of a module with this many top-level side effects
(DB init hooks, Stripe client config, route registration) is unreliable.
"""
import base64
import os
import subprocess
import sys
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_TEST_ENCRYPTION_KEY = base64.b64encode(b"k" * 32).decode("ascii")

_BASE_PROD_ENV = {
    "DEV_MODE": "false",
    "STRIPE_SECRET_KEY": "sk_live_x",
    "STRIPE_WEBHOOK_SECRET": "whsec_x",
    "OPENAI_API_KEY": "sk-x",
    "APP_HMAC_SECRET": "a" * 64,
    "SESSION_SECRET": "b" * 64,
    "ENCRYPTION_KEYS": f"k1:{_TEST_ENCRYPTION_KEY}",
    "ENCRYPTION_KEY_CURRENT": "k1",
    "DATABASE_URL": "sqlite:///:memory:",
}


def _run_import_main(env_overrides: dict) -> subprocess.CompletedProcess:
    env = {**os.environ, **_BASE_PROD_ENV, **env_overrides}
    # Import only — don't start the server; a nonzero exit / traceback means
    # a module-level ValueError was raised during import.
    code = textwrap.dedent("import main")
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_production_rejects_default_app_hmac_secret():
    result = _run_import_main({"APP_HMAC_SECRET": "dev_secret_change_me"})
    assert result.returncode != 0
    assert "APP_HMAC_SECRET" in result.stderr


def test_production_rejects_default_session_secret():
    result = _run_import_main({"SESSION_SECRET": "dev_session_secret_change_me"})
    assert result.returncode != 0
    assert "SESSION_SECRET" in result.stderr


def test_production_rejects_short_app_hmac_secret():
    result = _run_import_main({"APP_HMAC_SECRET": "short"})
    assert result.returncode != 0
    assert "APP_HMAC_SECRET" in result.stderr


def test_production_rejects_short_session_secret():
    result = _run_import_main({"SESSION_SECRET": "short"})
    assert result.returncode != 0
    assert "SESSION_SECRET" in result.stderr


def test_production_accepts_strong_secrets():
    result = _run_import_main({})
    assert result.returncode == 0, result.stderr


def test_production_defaults_secure_cookies_true_when_unset():
    env = {**os.environ, **_BASE_PROD_ENV}
    env.pop("SECURE_COOKIES", None)
    code = textwrap.dedent("import main, os; print('SECURE_COOKIES=' + os.environ['SECURE_COOKIES'])")
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "SECURE_COOKIES=true" in result.stdout


def test_production_respects_explicit_secure_cookies_false():
    """An operator can still explicitly opt out (e.g. TLS-terminating proxy
    that talks plain HTTP to the app) — the default must not override an
    explicit choice."""
    result = _run_import_main({"SECURE_COOKIES": "false"})
    assert result.returncode == 0, result.stderr


def test_dev_mode_defaults_secure_cookies_false_when_unset():
    env = {**os.environ, "DEV_MODE": "true"}
    for k in ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "APP_HMAC_SECRET", "SESSION_SECRET", "SECURE_COOKIES"):
        env.pop(k, None)
    env["DATABASE_URL"] = "sqlite:///:memory:"
    code = textwrap.dedent("import main, os; print('SECURE_COOKIES=' + os.environ['SECURE_COOKIES'])")
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "SECURE_COOKIES=false" in result.stdout


def test_dev_mode_does_not_enforce_secret_strength():
    env = {**os.environ, "DEV_MODE": "true"}
    for k in ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "APP_HMAC_SECRET", "SESSION_SECRET"):
        env.pop(k, None)
    env["DATABASE_URL"] = "sqlite:///:memory:"
    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
