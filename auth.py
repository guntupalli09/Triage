"""
Authentication utilities: password hashing, session cookies.
Uses Redis for session storage in production, falls back to in-memory for development.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, Response
from sqlalchemy.orm import Session

from models import User

logger = logging.getLogger(__name__)

SESSION_SECRET = os.getenv("SESSION_SECRET", "dev_session_secret_change_me")
SESSION_COOKIE = "triage_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

# Redis-backed sessions for production (survives restarts, shared across workers)
_redis_client = None
_sessions: dict[str, dict] = {}

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
            logger.info("Redis session store connected")
            return _redis_client
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to in-memory sessions: {e}")
            _redis_client = False
    else:
        _redis_client = False
    return None


# OWASP-recommended minimum for PBKDF2-HMAC-SHA256 (2023 guidance). Existing
# hashes were created with the old 100_000-iteration default; the iteration
# count is stored in the hash string itself so old hashes keep verifying
# correctly while every new/changed password gets the stronger setting.
PBKDF2_ITERATIONS = 210_000
_LEGACY_PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"{PBKDF2_ITERATIONS}:{salt}:{h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        parts = stored.split(":")
        if len(parts) == 3:
            iterations, salt, h = int(parts[0]), parts[1], parts[2]
        else:
            # Legacy format: "salt:hash", always hashed at the old iteration count.
            iterations = _LEGACY_PBKDF2_ITERATIONS
            salt, h = parts
        computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
        return hmac.compare_digest(computed.hex(), h)
    except Exception:
        return False


_user_sessions: dict[int, set[str]] = {}  # in-memory fallback: user_id -> {token, ...}


def _store_session(token: str, data: dict):
    r = _get_redis()
    if r:
        r.setex(f"session:{token}", SESSION_MAX_AGE, json.dumps(data, default=str))
    else:
        _sessions[token] = data


def _load_session(token: str) -> Optional[dict]:
    r = _get_redis()
    if r:
        raw = r.get(f"session:{token}")
        if raw:
            return json.loads(raw)
        return None
    return _sessions.get(token)


def _delete_session(token: str):
    r = _get_redis()
    if r:
        r.delete(f"session:{token}")
    else:
        _sessions.pop(token, None)


def _index_user_session(user_id: int, token: str):
    """Track this token against its owning user so all of a user's sessions
    can be revoked together (e.g. on password change)."""
    r = _get_redis()
    if r:
        r.sadd(f"user_sessions:{user_id}", token)
        r.expire(f"user_sessions:{user_id}", SESSION_MAX_AGE)
    else:
        _user_sessions.setdefault(user_id, set()).add(token)


def _unindex_user_session(user_id: int, token: str):
    r = _get_redis()
    if r:
        r.srem(f"user_sessions:{user_id}", token)
    else:
        _user_sessions.get(user_id, set()).discard(token)


def invalidate_all_sessions(user_id: int):
    """Revoke every active session for a user (all devices). Call this on
    password change/reset so a stolen session cookie doesn't survive it."""
    r = _get_redis()
    if r:
        key = f"user_sessions:{user_id}"
        tokens = r.smembers(key)
        for token in tokens:
            r.delete(f"session:{token}")
        r.delete(key)
    else:
        tokens = _user_sessions.pop(user_id, set())
        for token in tokens:
            _sessions.pop(token, None)


def create_session(user_id: int, response: Response) -> str:
    token = secrets.token_urlsafe(32)
    _store_session(token, {
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(seconds=SESSION_MAX_AGE)).isoformat(),
    })
    _index_user_session(user_id, token)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=os.getenv("SECURE_COOKIES", "false").lower() == "true",
    )
    return token


def mark_mfa_verified(request: Request) -> None:
    """Flag this session as having passed the admin TOTP challenge, so the
    user isn't asked for a code on every single admin request."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return
    session = _load_session(token)
    if not session:
        return
    session["mfa_verified"] = True
    _store_session(token, session)


def is_mfa_verified(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return False
    session = _load_session(token)
    return bool(session and session.get("mfa_verified"))


def get_current_user(request: Request, db: Session) -> Optional[User]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    session = _load_session(token)
    if not session:
        return None
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.utcnow() > expires_at:
        _delete_session(token)
        _unindex_user_session(session["user_id"], token)
        return None
    return db.query(User).filter(User.id == session["user_id"]).first()


def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session = _load_session(token)
        _delete_session(token)
        if session:
            _unindex_user_session(session["user_id"], token)
    response.delete_cookie(SESSION_COOKIE)


def check_usage_limit(user: User) -> bool:
    """Check if user is within their monthly contract limit."""
    now = datetime.utcnow()
    if user.usage_reset_at and (now - user.usage_reset_at).days >= 30:
        user.contracts_this_month = 0
        user.usage_reset_at = now
    return user.contracts_this_month < user.monthly_limit
