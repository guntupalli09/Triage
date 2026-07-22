"""
Security response headers middleware.

Adds the standard browser security headers to every response, plus a
Content-Security-Policy tuned to this app's actual asset usage.

CSP exceptions (documented, not accidental):
  - `script-src`/`style-src` include 'unsafe-inline': templates render
    inline <script>/<style> blocks throughout the app (no nonce plumbing
    exists yet). Tightening this to nonces is tracked as Phase 2 work
    (see docs/security/soc2_readiness_assessment.md).
  - `script-src` allows https://cdn.jsdelivr.net: the admin analytics
    dashboard loads Chart.js from jsDelivr.
  - `style-src`/`font-src` allow Google Fonts (fonts.googleapis.com /
    fonts.gstatic.com), used by every page's Inter/JetBrains Mono webfonts.
"""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

DEV_MODE = os.getenv("DEV_MODE", "false").strip().lower() == "true"

CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "object-src 'none'",
    "base-uri 'self'",
])


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        # HSTS only makes sense once the site is actually served over HTTPS;
        # sending it in local/dev http:// would be ignored by browsers anyway,
        # but we gate it explicitly to avoid confusing local testing.
        if not DEV_MODE:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        return response
