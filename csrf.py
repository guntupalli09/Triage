"""
CSRF protection via a double-submit-cookie pattern.

Every response gets a `csrf_token` cookie (a random value, minted once per
browser and reused across page loads/tabs) via `CSRFCookieMiddleware`.
Every state-changing route additionally declares `Depends(verify_csrf)`,
which requires that same token be echoed back — as a hidden form field
(`csrf_token`) for plain HTML form posts, or an `X-CSRF-Token` header for
`fetch()` calls — matching the cookie exactly (constant-time comparison).

This works because a cross-site page can neither read our cookie (same
origin policy) nor set a custom header on a simple cross-site form POST,
so it cannot reproduce a matching token. `SameSite=Lax` on the cookie
itself is a second, independent layer of defense.

`verify_csrf` is a normal FastAPI dependency (not middleware) so it reads
`csrf_token` through the same `Form(...)` machinery as the route itself —
FastAPI parses the request body once and shares it across all
dependencies and the endpoint, so there's no risk of the double body-read
deadlocks that come with consuming `request.form()` inside a
`BaseHTTPMiddleware` (a documented Starlette/anyio footgun with stacked
`BaseHTTPMiddleware`s). The cookie-minting middleware never touches the
request body, only response headers, so it's safe as middleware.

Exempt: the Stripe webhook, authenticated via HMAC signature verification
(`Stripe-Signature` header) instead — it's called by Stripe's servers,
not a browser, and never carries our cookie. It simply never gets
`Depends(verify_csrf)` attached.
"""
from __future__ import annotations

import hmac
import os
import secrets
from typing import Optional

from fastapi import Form, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
CSRF_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days

SECURE_COOKIES = os.getenv("SECURE_COOKIES", "false").strip().lower() == "true"


def _new_token() -> str:
    return secrets.token_urlsafe(32)


class CSRFCookieMiddleware(BaseHTTPMiddleware):
    """Mints the csrf_token cookie and exposes it on request.state for
    templates — never reads the request body, so it's safe to stack with
    other BaseHTTPMiddleware instances."""

    async def dispatch(self, request: Request, call_next):
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        request.state.csrf_token = cookie_token or _new_token()

        response = await call_next(request)

        if not cookie_token:
            response.set_cookie(
                CSRF_COOKIE_NAME, request.state.csrf_token,
                max_age=CSRF_COOKIE_MAX_AGE, httponly=False, samesite="lax",
                secure=SECURE_COOKIES,
            )
        return response


async def verify_csrf(request: Request, csrf_token: Optional[str] = Form(default=None)) -> None:
    """FastAPI dependency: attach to every state-changing browser route
    (`dependencies=[Depends(verify_csrf)]`) except trusted webhooks."""
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    submitted = request.headers.get(CSRF_HEADER_NAME) or csrf_token
    if not cookie_token or not submitted or not hmac.compare_digest(cookie_token, submitted):
        raise HTTPException(
            status_code=403,
            detail="Your session has expired or this request could not be verified. Please refresh the page and try again.",
        )
