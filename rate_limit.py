"""
Redis-backed rate limiting.

Built directly on `limits` (the same rate-limiting engine slowapi wraps),
using Redis as the counter store in production — set via `REDIS_URL`,
shared across all gunicorn workers — and falling back to an in-process
memory store when `REDIS_URL` is unset (fine for rate limiting, unlike
sessions: no data-loss risk, and it never blocks local dev).

Two independent axes are enforced:
  - `enforce_ip_limit`: keyed by client IP, catches distributed single-IP
    abuse and general scraping/flooding.
  - `enforce_account_limit`: keyed by account identifier (email, user id,
    share token) instead of IP, so an attacker rotating source IPs is
    still throttled per target account.

Limit expressions may be graduated/cascading (e.g. "5/minute;20/hour"):
a short burst window catches spikes immediately while a longer window
caps sustained lower-rate abuse — this is our "progressive" throttling
control (see docs/security/soc2_readiness_assessment.md for the full
table of endpoint limits and rationale).

We call `limits` directly, via a manual `enforce_*` call at the top of
each route handler, rather than slowapi's `@limiter.limit(...)`
decorator: that decorator re-wraps the endpoint's signature, which
breaks FastAPI's parameter resolution on this codebase's routes that
combine `from __future__ import annotations` with `UploadFile`/
`List[UploadFile]` parameters (upload, batch-upload).
"""
from __future__ import annotations

import os

from fastapi import HTTPException, Request
from limits import parse
from limits.storage import storage_from_string
from limits.strategies import FixedWindowRateLimiter

REDIS_URL = os.getenv("REDIS_URL", "").strip()
STORAGE_URI = REDIS_URL if REDIS_URL else "memory://"

_storage = storage_from_string(STORAGE_URI)
_strategy = FixedWindowRateLimiter(_storage)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforce(key: str, limit_expr: str, message: str) -> None:
    for raw_item in limit_expr.split(";"):
        item = parse(raw_item.strip())
        if not _strategy.hit(item, key):
            raise HTTPException(status_code=429, detail=message)


def enforce_ip_limit(request: Request, bucket: str, limit_expr: str = "20/minute") -> None:
    """Rate-limit by client IP address. Raises HTTPException(429) when exceeded."""
    key = f"{bucket}:ip:{_client_ip(request)}"
    _enforce(key, limit_expr, "Too many requests. Please slow down and try again shortly.")


def enforce_account_limit(bucket: str, identifier: str, limit_expr: str = "5/minute") -> None:
    """Rate-limit by account identifier (email, user id, share token), independent
    of IP. Raises HTTPException(429) when exceeded."""
    if not identifier:
        return
    key = f"{bucket}:acct:{identifier.strip().lower()}"
    _enforce(key, limit_expr, "Too many attempts for this account. Please wait a bit before trying again.")
