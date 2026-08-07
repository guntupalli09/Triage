"""
Application-level AES-256-GCM encryption at rest (P2 of the security
hardening pass — see docs/security/audit findings, C-02).

Envelope format (explicitly versioned so future migrations are possible):

    enc:v1:<key_id>:<base64 nonce>:<base64 ciphertext+tag>

- AES-256-GCM: authenticated encryption. Any bit-flip in the nonce or
  ciphertext (accidental corruption or deliberate tampering) makes
  decryption fail loudly (InvalidTag) instead of returning silently wrong
  plaintext.
- A fresh cryptographically random 96-bit (12-byte) nonce is generated for
  *every* encryption call via os.urandom — GCM's security guarantee
  requires a nonce never repeat under the same key, and os.urandom(12) at
  this key lifetime makes accidental reuse cryptographically negligible.
- key_id is embedded so keys can rotate: old rows keep decrypting under a
  retired key (looked up by the id in their envelope) while all new writes
  use the single currently-configured key. Retired keys are decrypt-only —
  nothing in this module ever encrypts with anything but the current key.
- Legacy (pre-encryption) plaintext rows have no "enc:v1:" prefix at all
  and are returned as-is by decrypt(); this is the ONLY case that falls
  back to plaintext. A value that *has* the prefix but fails to parse or
  fails authentication is a hard failure (DecryptionError) — it is never
  reinterpreted as plaintext. Treating a mangled ciphertext as literal
  contract text would silently corrupt data or mask tampering.

Configuration (see .env.example):
    ENCRYPTION_KEYS="k1:base64key1,k2:base64key2,..."
    ENCRYPTION_KEY_CURRENT="k2"

Keys live only in environment/secrets management — never in the database,
never logged. validate_startup() enforces this module's invariants (current
key present, well-formed, exactly 256 bits, no duplicate ids) and is called
from main.py the same way STRIPE_SECRET_KEY etc. are validated, failing
production startup outright rather than silently degrading.
"""
from __future__ import annotations

import base64
import binascii
import os
from typing import Dict, Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

ENVELOPE_PREFIX = "enc:v1:"
NONCE_BYTES = 12  # 96 bits, the size AES-GCM is designed for
KEY_BYTES = 32  # 256 bits

# A fixed, clearly-labeled dev-only key so local/test runs exercise the real
# encryption code path without requiring operators to generate a key just to
# run the app locally. Never used when ENCRYPTION_KEYS is actually set, and
# validate_startup() refuses to let this id represent the current key in
# production.
_DEV_KEY_ID = "dev-insecure-default"
_DEV_KEY = b"\x00" * KEY_BYTES  # 32 zero bytes — intentionally not secret


class EncryptionConfigError(ValueError):
    """Raised when ENCRYPTION_KEYS/ENCRYPTION_KEY_CURRENT are missing or malformed."""


class DecryptionError(ValueError):
    """Raised when a value has the enc:v1: envelope prefix but cannot be
    authenticated/decrypted — wrong key, unknown key id, corrupted or
    tampered ciphertext, or a malformed envelope. Callers must not catch
    this and fall back to treating the raw value as plaintext."""


def _parse_keys(raw: str) -> Dict[str, bytes]:
    keys: Dict[str, bytes] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            raise EncryptionConfigError(f"Malformed ENCRYPTION_KEYS entry (expected kid:base64key): {entry!r}")
        kid, b64key = entry.split(":", 1)
        kid = kid.strip()
        b64key = b64key.strip()
        if not kid:
            raise EncryptionConfigError("ENCRYPTION_KEYS entry has an empty key id")
        if kid in keys:
            raise EncryptionConfigError(f"Duplicate key id in ENCRYPTION_KEYS: {kid!r}")
        try:
            key_bytes = base64.b64decode(b64key, validate=True)
        except (binascii.Error, ValueError) as e:
            raise EncryptionConfigError(f"Key {kid!r} is not valid base64: {e}") from e
        if len(key_bytes) != KEY_BYTES:
            raise EncryptionConfigError(
                f"Key {kid!r} is {len(key_bytes) * 8} bits, must be exactly {KEY_BYTES * 8} bits (256-bit AES key)"
            )
        keys[kid] = key_bytes
    return keys


def _load_config() -> tuple[Dict[str, bytes], str]:
    """Returns (all_keys_by_id, current_key_id). Uses the fixed dev key only
    when ENCRYPTION_KEYS is completely unset — an operator who sets
    ENCRYPTION_KEYS gets real key validation even in DEV_MODE."""
    raw = os.getenv("ENCRYPTION_KEYS", "").strip()
    if not raw:
        return {_DEV_KEY_ID: _DEV_KEY}, _DEV_KEY_ID

    keys = _parse_keys(raw)
    current = os.getenv("ENCRYPTION_KEY_CURRENT", "").strip()
    if not current:
        raise EncryptionConfigError("ENCRYPTION_KEY_CURRENT is required when ENCRYPTION_KEYS is set")
    if current not in keys:
        raise EncryptionConfigError(f"ENCRYPTION_KEY_CURRENT={current!r} is not one of the keys in ENCRYPTION_KEYS")
    return keys, current


def validate_startup(dev_mode: bool) -> None:
    """Call once at process startup (mirrors the existing STRIPE_SECRET_KEY /
    APP_HMAC_SECRET production checks in main.py). Raises EncryptionConfigError
    — which callers should let propagate to abort startup — if the
    configuration is missing or malformed in production."""
    raw = os.getenv("ENCRYPTION_KEYS", "").strip()
    if not dev_mode and not raw:
        raise EncryptionConfigError(
            "ENCRYPTION_KEYS is required in production. Generate one with: "
            "openssl rand -base64 32, then set ENCRYPTION_KEYS=\"k1:<value>\" "
            "and ENCRYPTION_KEY_CURRENT=k1."
        )
    # _load_config() raises EncryptionConfigError on any malformed/duplicate/
    # wrong-length key or missing/unknown current key id — let it propagate.
    keys, current = _load_config()
    if not dev_mode and current == _DEV_KEY_ID:
        raise EncryptionConfigError("Refusing to start in production with the insecure default encryption key")


def encrypt(plaintext: Optional[str]) -> Optional[str]:
    """Encrypts with the current key, using a fresh random nonce. None and
    the empty string pass through unchanged (nothing to protect, and it
    keeps NOT NULL/empty-string columns from growing an envelope around
    nothing)."""
    if not plaintext:
        return plaintext

    keys, current_kid = _load_config()
    key = keys[current_kid]
    nonce = os.urandom(NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)

    return (
        f"{ENVELOPE_PREFIX}{current_kid}:"
        f"{base64.b64encode(nonce).decode('ascii')}:"
        f"{base64.b64encode(ciphertext).decode('ascii')}"
    )


def is_encrypted(value: Optional[str]) -> bool:
    return bool(value) and value.startswith(ENVELOPE_PREFIX)


def decrypt(value: Optional[str]) -> Optional[str]:
    """Legacy plaintext (no enc:v1: prefix at all) passes through unchanged.
    A value carrying the prefix that fails to parse or fails GCM
    authentication raises DecryptionError — it is never treated as
    plaintext instead."""
    if not value or not is_encrypted(value):
        return value

    body = value[len(ENVELOPE_PREFIX):]
    parts = body.split(":", 2)
    if len(parts) != 3:
        raise DecryptionError("Malformed encrypted envelope: expected key_id:nonce:ciphertext")
    kid, b64nonce, b64ciphertext = parts

    keys, _current_kid = _load_config()
    key = keys.get(kid)
    if key is None:
        raise DecryptionError(f"Unknown encryption key id in envelope: {kid!r}")

    try:
        nonce = base64.b64decode(b64nonce, validate=True)
        ciphertext = base64.b64decode(b64ciphertext, validate=True)
    except (binascii.Error, ValueError) as e:
        raise DecryptionError(f"Malformed encrypted envelope (bad base64): {e}") from e

    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    except InvalidTag as e:
        raise DecryptionError(
            "Decryption failed authentication — ciphertext is corrupted, tampered "
            "with, or was encrypted under a different key than key id "
            f"{kid!r} currently maps to."
        ) from e

    return plaintext.decode("utf-8")


class EncryptedText(TypeDecorator):
    """SQLAlchemy column type: transparently encrypts on write and decrypts
    on read, so model/route code keeps using `contract.contract_text` as a
    plain string with no call-site changes. Only fires on an actual
    INSERT/UPDATE of this column (process_bind_param) — merely reading a
    row and not reassigning the attribute does not cause a re-write, so
    reads never silently re-encrypt a row under a newer key (that's what
    the backfill script is for).
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)
