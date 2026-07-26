"""
Application-level encryption for sensitive text columns (currently
Contract.contract_text — the raw uploaded document text).

Set CONTRACT_ENCRYPTION_KEY (a Fernet key: `Fernet.generate_key()`) to enable.
If unset, text is stored as plaintext (dev-friendly default) — set this in
production so a database or backup leak doesn't expose full document text.

Rows written before this was enabled stay plaintext and are still readable;
new writes are encrypted. There is no forced migration of historical rows.
"""
from __future__ import annotations

import logging
import os

from sqlalchemy.types import TypeDecorator, Text

logger = logging.getLogger(__name__)

_PREFIX = "enc:v1:"
_fernet = None
_fernet_init_attempted = False


def _get_fernet():
    global _fernet, _fernet_init_attempted
    if _fernet_init_attempted:
        return _fernet
    _fernet_init_attempted = True
    key = os.getenv("CONTRACT_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(key.encode())
    except Exception as e:
        logger.error(f"Invalid CONTRACT_ENCRYPTION_KEY, storing contract text as plaintext: {e}")
        _fernet = None
    return _fernet


class EncryptedText(TypeDecorator):
    """Transparently encrypts on write / decrypts on read when
    CONTRACT_ENCRYPTION_KEY is configured. Falls back to plaintext
    (still readable) when it isn't, or for rows written before it was."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        fernet = _get_fernet()
        if not fernet:
            return value
        return _PREFIX + fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None or not value.startswith(_PREFIX):
            return value
        fernet = _get_fernet()
        if not fernet:
            # Key not configured but row is encrypted — can't read it back.
            return None
        try:
            return fernet.decrypt(value[len(_PREFIX):].encode()).decode()
        except Exception:
            logger.error("Failed to decrypt contract text (wrong/rotated key?)")
            return None
