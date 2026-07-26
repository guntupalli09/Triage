"""
TOTP second factor for the admin panel. The admin account is a single
hardcoded email/password gate with full visibility into every user's data —
worth a second factor beyond just a password.

Set ADMIN_TOTP_SECRET (a base32 secret — generate with
`python -c "import pyotp; print(pyotp.random_base32())"`) and enroll it in
an authenticator app (Google Authenticator, 1Password, etc.) using the
provisioning URI from `provisioning_uri()`. If unset, MFA is skipped
(fails open) so local/dev environments don't need it configured — this
must be set in production.
"""
from __future__ import annotations

import os

import pyotp

ADMIN_ACCOUNT_NAME = "admin@triagecounsel"
ISSUER = "Triage Counsel"


def _secret() -> str:
    return os.getenv("ADMIN_TOTP_SECRET", "").strip()


def is_configured() -> bool:
    return bool(_secret())


def provisioning_uri() -> str:
    return pyotp.TOTP(_secret()).provisioning_uri(name=ADMIN_ACCOUNT_NAME, issuer_name=ISSUER)


def verify_code(code: str) -> bool:
    secret = _secret()
    if not secret:
        return True
    if not code or not code.strip():
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)
