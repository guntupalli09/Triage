"""
CSRF protection — synchronizer token delivered via an HttpOnly cookie
(OWASP ASVS V4.2.2 / CSRF Cheat Sheet "signed double submit cookie" pattern,
adapted so JS never needs to read the cookie directly).

How it works:
  1. CSRFCookieMiddleware ensures every visitor has a random `csrf_token`
     cookie, generating one on first visit and stashing it on
     `request.state.csrf_token` so the *same* request that creates it can
     also render it into a form.
  2. Templates embed that value as a hidden `<input name="csrf_token">`
     (via the `csrf_token(request)` Jinja global) in every browser form, and
     as a `<meta name="csrf-token">` tag for JS-driven fetch() calls to read.
  3. State-changing routes depend on `csrf_protect`, which compares the
     submitted `csrf_token` form field against the cookie value with a
     constant-time comparison.

Because the cookie is HttpOnly, an attacker's cross-site page can neither
read it to forge a matching hidden field, nor set it to a chosen value
(SameSite=Lax also blocks the cookie from riding along on a cross-site
POST in the first place — this token is deliberate defense in depth on top
of that, since SameSite enforcement varies across older browsers/proxies).

Exemptions: routes that don't rely on cookie-based auth for the write itself
(the Stripe webhook, verified by Stripe's own request signature) don't use
this dependency.
"""
from __future__ import annotations

import hmac
import os
import secrets

from fastapi import Form, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

CSRF_COOKIE = "csrf_token"
CSRF_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # matches auth.py's SESSION_MAX_AGE


def _secure_cookie() -> bool:
    return os.getenv("SECURE_COOKIES", "false").strip().lower() == "true"


class CSRFCookieMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        existing = request.cookies.get(CSRF_COOKIE)
        token = existing or secrets.token_urlsafe(32)
        request.state.csrf_token = token

        response = await call_next(request)

        if not existing:
            response.set_cookie(
                CSRF_COOKIE,
                token,
                max_age=CSRF_COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
                secure=_secure_cookie(),
            )
        return response


def get_csrf_token(request: Request) -> str:
    """Jinja global (`csrf_token(request)`): the token for this request,
    whether freshly minted this request or read from an existing cookie."""
    return getattr(request.state, "csrf_token", "") or request.cookies.get(CSRF_COOKIE, "")


def csrf_protect(request: Request, csrf_token: str = Form(...)) -> None:
    """FastAPI dependency for state-changing form routes. 403s on a missing
    or mismatched token instead of letting the request through silently —
    an expired/absent cookie must fail closed, not open."""
    cookie_value = request.cookies.get(CSRF_COOKIE, "")
    if not cookie_value or not csrf_token or not hmac.compare_digest(cookie_value, csrf_token):
        raise HTTPException(
            status_code=403,
            detail="Your session security token is missing or expired. Please refresh the page and try again.",
        )
