"""
Authentication utilities: password hashing, session cookies.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, Response
from sqlalchemy.orm import Session

from models import User

SESSION_SECRET = os.getenv("SESSION_SECRET", "dev_session_secret_change_me")
SESSION_COOKIE = "triage_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

# In-memory session store (maps session_token -> user_id)
# For production, use Redis or DB-backed sessions
_sessions: dict[str, dict] = {}


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


def create_session(user_id: int, response: Response) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(seconds=SESSION_MAX_AGE),
    }
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
    if not token or token not in _sessions:
        return None
    session = _sessions[token]
    if datetime.utcnow() > session["expires_at"]:
        _sessions.pop(token, None)
        return None
    return db.query(User).filter(User.id == session["user_id"]).first()


def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        _sessions.pop(token, None)
    response.delete_cookie(SESSION_COOKIE)


def check_usage_limit(user: User) -> bool:
    """Check if user is within their monthly contract limit."""
    now = datetime.utcnow()
    if user.usage_reset_at and (now - user.usage_reset_at).days >= 30:
        user.contracts_this_month = 0
        user.usage_reset_at = now
    return user.contracts_this_month < user.monthly_limit
