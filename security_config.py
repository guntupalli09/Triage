"""
Centralized production security configuration.

`validate_production_config()` fails application startup when running in
production (DEV_MODE=false) with insecure defaults: missing/weak
APP_HMAC_SECRET or SESSION_SECRET, a localhost/http BASE_URL, or
SECURE_COOKIES not enabled. It never blocks development.

See docs/security/soc2_readiness_assessment.md and README.md for the
full list of required production environment variables.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

DEV_MODE = os.getenv("DEV_MODE", "false").strip().lower() == "true"
SECURE_COOKIES = os.getenv("SECURE_COOKIES", "false").strip().lower() == "true"

# Values shipped as examples/defaults in this repo (.env.example, code
# fallbacks) — never acceptable in production.
_INSECURE_SECRET_VALUES = {
    "dev_secret_change_me",
    "dev_session_secret_change_me",
    "change_me_to_a_random_secret",
    "changeme",
    "change_me",
    "secret",
}
_MIN_SECRET_LENGTH = 32


def _is_weak_secret(value: str) -> bool:
    if not value:
        return True
    if value.strip().lower() in _INSECURE_SECRET_VALUES:
        return True
    if len(value) < _MIN_SECRET_LENGTH:
        return True
    return False


def validate_production_config() -> None:
    """Raise RuntimeError if production configuration is insecure.

    No-op when DEV_MODE=true, so local development is never blocked.
    """
    if DEV_MODE:
        return

    errors = []

    app_hmac_secret = os.getenv("APP_HMAC_SECRET", "")
    if _is_weak_secret(app_hmac_secret):
        errors.append(
            "APP_HMAC_SECRET is missing, a known default, or shorter than "
            f"{_MIN_SECRET_LENGTH} characters. Generate one with: openssl rand -hex 32"
        )

    session_secret = os.getenv("SESSION_SECRET", "")
    if _is_weak_secret(session_secret):
        errors.append(
            "SESSION_SECRET is missing, a known default, or shorter than "
            f"{_MIN_SECRET_LENGTH} characters. Generate one with: openssl rand -hex 32"
        )

    base_url = os.getenv("BASE_URL", "").strip()
    if not base_url:
        errors.append("BASE_URL must be set in production.")
    elif "localhost" in base_url or "127.0.0.1" in base_url:
        errors.append("BASE_URL must not point at localhost/127.0.0.1 in production.")
    elif not base_url.startswith("https://"):
        errors.append("BASE_URL must use https:// in production.")

    if not SECURE_COOKIES:
        errors.append("SECURE_COOKIES must be set to 'true' in production.")

    if errors:
        message = "Refusing to start: insecure production configuration:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        logger.critical(message)
        raise RuntimeError(message)

    logger.info("Production secret and configuration validation passed.")
