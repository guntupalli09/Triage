"""
TOTP-based multi-factor authentication (MFA).

Opt-in per user (no forced enrollment for anyone, including admins — that
would be a business-logic/behavior change beyond fixing the missing
capability; see docs recommending admins enable it voluntarily). Standard
6-digit time-based one-time codes (RFC 6238) compatible with any
authenticator app (Google Authenticator, Authy, 1Password, etc.), plus
single-use recovery codes for when the authenticator device is
unavailable.

Secrets and codes:
- The TOTP secret (User.mfa_secret) is encrypted at rest (EncryptedText —
  see encryption.py) since anyone who reads it can generate valid codes
  for that account indefinitely.
- Recovery codes are never stored in plaintext — only their SHA-256 hash
  (User.mfa_recovery_codes_json), the same one-way-hash pattern already
  used for password-reset tokens (models.py: User.reset_token_hash). The
  plaintext codes are shown to the user exactly once, at generation time,
  and cannot be recovered afterward — only regenerated (which invalidates
  the old set).
"""
from __future__ import annotations

import base64
import hashlib
import io
import secrets
from datetime import datetime
from typing import List, Optional, Tuple

import pyotp
import qrcode
import qrcode.image.svg

RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_LENGTH = 10
# Excludes visually ambiguous characters (0/O, 1/I/L) so codes are easy to
# transcribe correctly from a printed/handwritten copy.
_RECOVERY_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str, issuer: str = "TriageCounsel") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def qr_code_svg_data_uri(otpauth_uri: str) -> str:
    """Renders the enrollment QR code as an inline SVG data URI — no PIL
    dependency (qrcode's SVG image factory doesn't need it), so no new
    heavy/native dependency for either the Docker or Vercel deployment."""
    img = qrcode.make(otpauth_uri, image_factory=qrcode.image.svg.SvgImage)
    buf = io.BytesIO()
    img.save(buf)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def verify_totp_code(secret: str, code: str) -> bool:
    """valid_window=1 tolerates the code from the previous/next 30s step,
    covering ordinary clock drift between the user's device and the
    server without meaningfully widening the guessable window."""
    if not secret:
        return False
    code = (code or "").strip().replace(" ", "")
    if not code or not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def generate_recovery_codes(n: int = RECOVERY_CODE_COUNT) -> List[str]:
    return [
        "".join(secrets.choice(_RECOVERY_CODE_ALPHABET) for _ in range(RECOVERY_CODE_LENGTH))
        for _ in range(n)
    ]


def hash_recovery_code(code: str) -> str:
    normalized = (code or "").strip().upper().replace(" ", "").replace("-", "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_recovery_codes_record(codes: List[str]) -> List[dict]:
    """The persisted form: one-way hashes plus a used_at marker. Never the
    plaintext codes themselves."""
    return [{"hash": hash_recovery_code(c), "used_at": None} for c in codes]


def verify_and_consume_recovery_code(
    record: Optional[List[dict]], code: str
) -> Tuple[bool, Optional[List[dict]]]:
    """Returns (matched, updated_record). On a match, the specific code is
    marked used (updated_record reflects that) so it can't be reused —
    callers must persist the returned record. Returns (False, record)
    unchanged if nothing matched or the code was already used."""
    if not record or not code:
        return False, record
    code_hash = hash_recovery_code(code)
    updated = [dict(entry) for entry in record]
    for entry in updated:
        if entry.get("hash") == code_hash and not entry.get("used_at"):
            entry["used_at"] = datetime.utcnow().isoformat()
            return True, updated
    return False, record


def count_remaining_recovery_codes(record: Optional[List[dict]]) -> int:
    if not record:
        return 0
    return sum(1 for entry in record if not entry.get("used_at"))
