"""
Redis client for Triage.

Provides session storage, rate limiting, caching, and job queue support.
Falls back gracefully when Redis is unavailable.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")

_client = None
_available = False

KEY_PREFIX = "triage:"
SESSION_PREFIX = f"{KEY_PREFIX}session:"
RATE_PREFIX = f"{KEY_PREFIX}rate:"
CACHE_PREFIX = f"{KEY_PREFIX}cache:"
JOB_PAYLOAD_PREFIX = f"{KEY_PREFIX}job_payload:"


def _get_client():
    global _client, _available
    if _client is not None:
        return _client
    if not REDIS_URL:
        _available = False
        return None
    try:
        import redis
        _client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            retry_on_timeout=True,
        )
        _client.ping()
        _available = True
        logger.info("Redis connected")
        return _client
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")
        _available = False
        _client = None
        return None


def is_available() -> bool:
    _get_client()
    return _available


def session_set(token: str, data: Dict[str, Any], ttl_seconds: int = 2592000) -> bool:
    client = _get_client()
    if not client:
        return False
    try:
        client.setex(f"{SESSION_PREFIX}{token}", ttl_seconds, json.dumps(data, default=str))
        return True
    except Exception as e:
        logger.error(f"Redis session_set error: {e}")
        return False


def session_get(token: str) -> Optional[Dict[str, Any]]:
    client = _get_client()
    if not client:
        return None
    try:
        data = client.get(f"{SESSION_PREFIX}{token}")
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"Redis session_get error: {e}")
        return None


def session_delete(token: str) -> bool:
    client = _get_client()
    if not client:
        return False
    try:
        client.delete(f"{SESSION_PREFIX}{token}")
        return True
    except Exception as e:
        logger.error(f"Redis session_delete error: {e}")
        return False


def rate_limit_check(key: str, limit: int, window_seconds: int = 60) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    client = _get_client()
    if not client:
        return True
    try:
        full_key = f"{RATE_PREFIX}{key}"
        current = client.incr(full_key)
        if current == 1:
            client.expire(full_key, window_seconds)
        return current <= limit
    except Exception:
        return True


def cache_get(key: str) -> Optional[str]:
    client = _get_client()
    if not client:
        return None
    try:
        return client.get(f"{CACHE_PREFIX}{key}")
    except Exception:
        return None


def cache_set(key: str, value: str, ttl_seconds: int = 300) -> bool:
    client = _get_client()
    if not client:
        return False
    try:
        client.setex(f"{CACHE_PREFIX}{key}", ttl_seconds, value)
        return True
    except Exception:
        return False


def store_job_payload(job_id: str, payload: str, ttl_seconds: int = 3600) -> bool:
    client = _get_client()
    if not client:
        return False
    try:
        client.setex(f"{JOB_PAYLOAD_PREFIX}{job_id}", ttl_seconds, payload)
        return True
    except Exception as e:
        logger.error(f"Redis store_job_payload error: {e}")
        return False


def get_job_payload(job_id: str) -> Optional[str]:
    client = _get_client()
    if not client:
        return None
    try:
        return client.get(f"{JOB_PAYLOAD_PREFIX}{job_id}")
    except Exception:
        return None


def enqueue_job(queue_name: str, job_data: Dict[str, Any]) -> bool:
    client = _get_client()
    if not client:
        return False
    try:
        client.rpush(f"{KEY_PREFIX}queue:{queue_name}", json.dumps(job_data, default=str))
        return True
    except Exception as e:
        logger.error(f"Redis enqueue error: {e}")
        return False


def dequeue_job(queue_name: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
    client = _get_client()
    if not client:
        return None
    try:
        result = client.blpop(f"{KEY_PREFIX}queue:{queue_name}", timeout=timeout)
        if result:
            return json.loads(result[1])
        return None
    except Exception:
        return None
