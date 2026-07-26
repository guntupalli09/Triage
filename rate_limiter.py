"""
Fixed-window request rate limiting for sensitive public endpoints
(login, register, password reset, contact).

Uses Redis when available (shared across workers/dynos), falling back to an
in-process dict otherwise. Mirrors the storage pattern already used for
sessions in auth.py.
"""
from __future__ import annotations

import os
import time
import logging
from typing import Optional

from fastapi import HTTPException, Request

import analytics

logger = logging.getLogger(__name__)

_redis_client = None
_counters: dict[str, tuple[int, float]] = {}  # key -> (count, window_start)


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis
            _redis_client = redis.from_url(redis_url, decode_responses=True, socket_timeout=5, retry_on_timeout=True)
            _redis_client.ping()
            return _redis_client
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiting, falling back to in-memory: {e}")
            _redis_client = False
    else:
        _redis_client = False
    return None


def _check_and_increment(key: str, limit: int, window_seconds: int) -> bool:
    """Returns True if the request is allowed, False if the limit was exceeded."""
    r = _get_redis()
    if r:
        pipe = r.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, window_seconds, nx=True)
        count, _ = pipe.execute()
        return int(count) <= limit

    now = time.time()
    count, window_start = _counters.get(key, (0, now))
    if now - window_start >= window_seconds:
        count, window_start = 0, now
    count += 1
    _counters[key] = (count, window_start)
    return count <= limit


def enforce_rate_limit(request: Request, bucket: str, limit: int, window_seconds: int) -> None:
    """Raise HTTP 429 if the caller has exceeded `limit` requests to `bucket`
    within `window_seconds`, keyed by client IP."""
    ip = analytics.extract_ip(request) or "unknown"
    key = f"ratelimit:{bucket}:{ip}"
    if not _check_and_increment(key, limit, window_seconds):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
