"""
Bearer-token authentication for Word / Google Docs / API clients.

Session cookies stay the browser path. Integration clients cannot reliably
carry third-party cookies inside Office/Google iframes, so they present a
hashed API token in ``Authorization: Bearer …``.

The plaintext token is shown once at issuance (login or explicit mint)
and only a SHA-256 hash is stored. Revocation is an UPDATE of revoked_at
— the token row is retained for audit.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence, Tuple

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from models import ApiToken, User
import tenancy

TOKEN_BYTES = 32
TOKEN_PREFIX_LEN = 8
DEFAULT_TTL_DAYS = 30
DEFAULT_SCOPES = (
    "integration",
    "contracts.read",
    "contracts.write",
    "playbooks.read",
    "portfolio.search",
    "portfolio.report",
    "intake.submit",
)


def _hash_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def mint_token(
    db: Session,
    user: User,
    *,
    name: str = "Integration token",
    client_kind: str = "api",
    scopes: Optional[Sequence[str]] = None,
    ttl_days: int = DEFAULT_TTL_DAYS,
) -> Tuple[ApiToken, str]:
    tenancy.ensure_user_tenant(db, user)
    plaintext = "tc_" + secrets.token_urlsafe(TOKEN_BYTES)
    prefix = plaintext[:TOKEN_PREFIX_LEN]
    row = ApiToken(
        tenant_id=user.tenant_id,
        user_id=user.id,
        name=name[:255],
        token_prefix=prefix,
        token_hash=_hash_token(plaintext),
        scopes_json=list(scopes) if scopes is not None else list(DEFAULT_SCOPES),
        expires_at=datetime.utcnow() + timedelta(days=ttl_days) if ttl_days else None,
        client_kind=client_kind,
    )
    db.add(row)
    db.flush()
    return row, plaintext


def revoke_token(db: Session, token: ApiToken) -> None:
    token.revoked_at = datetime.utcnow()
    db.flush()


def _extract_bearer(request: Request) -> Optional[str]:
    header = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


def authenticate_bearer(db: Session, request: Request) -> Optional[User]:
    plaintext = _extract_bearer(request)
    if not plaintext:
        return None
    token_hash = _hash_token(plaintext)
    row = db.query(ApiToken).filter(ApiToken.token_hash == token_hash).first()
    if row is None:
        return None
    if row.revoked_at is not None:
        return None
    if row.expires_at is not None and datetime.utcnow() > row.expires_at:
        return None
    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        return None
    if user.tenant_id != row.tenant_id:
        return None
    row.last_used_at = datetime.utcnow()
    tenancy.ensure_user_tenant(db, user)
    request.state.api_token = row
    return user


def require_bearer_user(db: Session, request: Request) -> User:
    user = authenticate_bearer(db, request)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API token.")
    return user


def token_has_scope(request: Request, scope: str) -> bool:
    row = getattr(request.state, "api_token", None)
    if row is None:
        return False
    scopes = row.scopes_json or []
    return scope in scopes or "integration" in scopes


def require_scope(request: Request, scope: str) -> None:
    if not token_has_scope(request, scope):
        raise HTTPException(status_code=403, detail=f"API token is missing required scope: {scope}")


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
