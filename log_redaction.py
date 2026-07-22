"""
Log redaction filter.

Applied to the root logger's handlers so it covers every module logger in
the app (they all propagate up to root). Scrubs values that should never
land in logs: passwords, API keys, OAuth/session tokens, and session ids —
even if a future log line accidentally interpolates one directly instead
of going through a structured field.

This is a defense-in-depth backstop, not a replacement for simply not
logging secrets in the first place — call sites should still avoid
logging raw request bodies, tokens, or credentials.
"""
from __future__ import annotations

import logging
import re

_REDACTED = "***REDACTED***"

_PATTERNS = [
    # OpenAI API keys
    (re.compile(r"sk-[A-Za-z0-9_-]{16,}"), "sk-" + _REDACTED),
    # Stripe secret/webhook keys
    (re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{8,}"), "sk_" + _REDACTED),
    (re.compile(r"whsec_[A-Za-z0-9]{8,}"), "whsec_" + _REDACTED),
    # Bearer tokens in Authorization headers — must run before the generic
    # key/value pattern below, or "Authorization: " gets redacted first and
    # leaves the actual "Bearer <token>" value exposed.
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._-]{8,}"), r"\1" + _REDACTED),
    # key=value / key: value / "key": "value" style fields carrying secrets
    (
        re.compile(
            r'(?i)((?:password|passwd|current_password|new_password|'
            r"access_token|refresh_token|id_token|api_key|apikey|"
            r'client_secret|session_id|triage_session|csrf_token)'
            r'["\']?\s*[:=]\s*["\']?)([^\s,&"\'}]{1,500})',
        ),
        r"\1" + _REDACTED,
    ),
]


def _redact(message: str) -> str:
    redacted = message
    for pattern, repl in _PATTERNS:
        redacted = pattern.sub(repl, redacted)
    return redacted


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = _redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def install(logger: logging.Logger | None = None) -> None:
    """Attach the redaction filter to every handler on the given logger
    (root logger by default), so it applies to all propagated log records."""
    target = logger or logging.getLogger()
    for handler in target.handlers:
        handler.addFilter(RedactingFilter())
