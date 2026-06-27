"""
Authentication utilities: password hashing, session cookies.
Sessions backed by Redis (primary) with DB fallback for admin visibility.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, Response
from sqlalchemy.orm import Session as DBSession

from models import User, Session as SessionModel
import redis_client

SESSION_SECRET = os.getenv("SESSION_SECRET", "dev_session_secret_change_me")
SESSION_COOKIE = "triage_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

# In-memory fallback when Redis is unavailable
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


def create_session(
    user_id: int,
    response: Response,
    db: Optional[DBSession] = None,
    request: Optional[Request] = None,
) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires = now + timedelta(seconds=SESSION_MAX_AGE)

    session_data = {
        "user_id": user_id,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
    }

    # Try Redis first
    if not redis_client.session_set(token, session_data, SESSION_MAX_AGE):
        # Fallback to in-memory
        _sessions[token] = {
            "user_id": user_id,
            "created_at": now,
            "expires_at": expires,
        }

    # Also store in DB for admin visibility
    if db:
        try:
            ip = ""
            ua = ""
            if request:
                ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "")
                ua = request.headers.get("user-agent", "")[:512]
            db_session = SessionModel(
                id=token,
                user_id=user_id,
                created_at=now,
                expires_at=expires,
                ip_address=ip,
                user_agent=ua,
            )
            db.add(db_session)
            db.commit()
        except Exception:
            pass

    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=os.getenv("SECURE_COOKIES", "false").lower() == "true",
    )
    return token


def get_current_user(request: Request, db: DBSession) -> Optional[User]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    user_id = None
    now = datetime.utcnow()

    # Try Redis first
    session_data = redis_client.session_get(token)
    if session_data:
        expires = datetime.fromisoformat(session_data["expires_at"])
        if now > expires:
            redis_client.session_delete(token)
            return None
        user_id = session_data["user_id"]
    else:
        # Fallback to in-memory
        if token in _sessions:
            session = _sessions[token]
            if now > session["expires_at"]:
                _sessions.pop(token, None)
                return None
            user_id = session["user_id"]

    if user_id is None:
        return None

    return db.query(User).filter(User.id == user_id).first()


def logout(request: Request, response: Response, db: Optional[DBSession] = None):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        redis_client.session_delete(token)
        _sessions.pop(token, None)
        if db:
            try:
                db.query(SessionModel).filter(SessionModel.id == token).delete()
                db.commit()
            except Exception:
                pass
    response.delete_cookie(SESSION_COOKIE)


def check_usage_limit(user: User) -> bool:
    now = datetime.utcnow()
    if user.usage_reset_at and (now - user.usage_reset_at).days >= 30:
        user.contracts_this_month = 0
        user.usage_reset_at = now
    return user.contracts_this_month < user.monthly_limit
