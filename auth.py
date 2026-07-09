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


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}:{h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":", 1)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(computed.hex(), h)
    except Exception:
        return False


RESET_TOKEN_MAX_AGE = 60 * 60  # 1 hour


def make_reset_token(user: User) -> str:
    """Stateless, single-use password-reset token.

    The signature covers the user's current password hash, so the token
    stops verifying the moment the password changes — no token table needed.
    """
    expires = int((datetime.utcnow() + timedelta(seconds=RESET_TOKEN_MAX_AGE)).timestamp())
    payload = f"{user.id}.{expires}"
    sig = hmac.new(
        SESSION_SECRET.encode(), f"{payload}.{user.password_hash}".encode(), hashlib.sha256
    ).hexdigest()[:32]
    return f"{payload}.{sig}"


def verify_reset_token(token: str, db: Session) -> Optional[User]:
    """Return the user for a valid, unexpired reset token, else None."""
    try:
        uid_s, exp_s, sig = token.split(".")
        uid, expires = int(uid_s), int(exp_s)
    except (ValueError, AttributeError):
        return None
    if expires < int(datetime.utcnow().timestamp()):
        return None
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        return None
    expected = hmac.new(
        SESSION_SECRET.encode(), f"{uid}.{expires}.{user.password_hash}".encode(), hashlib.sha256
    ).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected):
        return None
    return user


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


def create_session(user_id: int, response: Response) -> str:
    token = secrets.token_urlsafe(32)
    _store_session(token, {
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(seconds=SESSION_MAX_AGE)).isoformat(),
    })
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=os.getenv("SECURE_COOKIES", "false").lower() == "true",
    )
    return token


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
        return None
    return db.query(User).filter(User.id == session["user_id"]).first()


def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        _delete_session(token)
    response.delete_cookie(SESSION_COOKIE)


def check_usage_limit(user: User) -> bool:
    """Check if user is within their monthly contract limit."""
    now = datetime.utcnow()
    if user.usage_reset_at and (now - user.usage_reset_at).days >= 30:
        user.contracts_this_month = 0
        user.usage_reset_at = now
    return user.contracts_this_month < user.monthly_limit
