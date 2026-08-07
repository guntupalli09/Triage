"""
Fixed-window rate limiting (OWASP ASVS V2.2 — anti-automation controls).

Mirrors auth.py's storage pattern deliberately: Redis-backed (shared across
Gunicorn workers/replicas, survives restarts) when REDIS_URL is configured,
falling back to an in-process dict otherwise. Multi-worker deployments
without Redis will under-count across workers (each worker enforces its own
limit) — the same known limitation auth.py already documents for sessions;
production deployments are expected to set REDIS_URL.

Usage as a FastAPI dependency:

    @app.post("/login")
    async def login(..., _: None = Depends(rate_limit("login", limit=10, window_seconds=60))):
        ...

The limiter key combines the caller-supplied bucket name with the request's
client IP, so `/login` and `/register` don't share a budget, and one IP
can't exhaust another's.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, Tuple

from fastapi import HTTPException, Request

from analytics import extract_ip

logger = logging.getLogger(__name__)

_redis_client = None
# name -> {window_start_bucket: count}. Trimmed lazily on write.
_memory_counters: Dict[str, Dict[int, int]] = {}


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis
            _redis_client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2, retry_on_timeout=True)
            _redis_client.ping()
            return _redis_client
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiting, falling back to in-memory: {e}")
            _redis_client = False
    else:
        _redis_client = False
    return None


def _check_and_increment(key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
    """Returns (allowed, retry_after_seconds)."""
    bucket = int(time.time() // window_seconds)
    redis_key = f"ratelimit:{key}:{bucket}"

    r = _get_redis()
    if r:
        try:
            pipe = r.pipeline()
            pipe.incr(redis_key, 1)
            pipe.expire(redis_key, window_seconds)
            count, _ = pipe.execute()
        except Exception as e:
            logger.warning(f"Redis rate-limit check failed, allowing request: {e}")
            return True, 0
        if count > limit:
            retry_after = window_seconds - int(time.time() % window_seconds)
            return False, max(retry_after, 1)
        return True, 0

    # In-memory fallback
    buckets = _memory_counters.setdefault(key, {})
    # Drop stale buckets so this dict can't grow unbounded across windows.
    for old_bucket in [b for b in buckets if b < bucket]:
        del buckets[old_bucket]
    buckets[bucket] = buckets.get(bucket, 0) + 1
    if buckets[bucket] > limit:
        retry_after = window_seconds - int(time.time() % window_seconds)
        return False, max(retry_after, 1)
    return True, 0


def rate_limit(name: str, limit: int, window_seconds: int):
    """FastAPI dependency factory. Raises 429 with a Retry-After header once
    `limit` requests from the same client IP hit bucket `name` within
    `window_seconds`."""

    def _dependency(request: Request) -> None:
        ip = extract_ip(request) or "unknown"
        key = f"{name}:{ip}"
        allowed, retry_after = _check_and_increment(key, limit, window_seconds)
        if not allowed:
            logger.warning(f"Rate limit exceeded: bucket={name} ip={ip}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dependency
