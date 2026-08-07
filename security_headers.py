"""
Security response headers middleware (OWASP ASVS V14 / OWASP Secure Headers).

Applies browser-enforced defenses on every response: HSTS, a Content-Security-
Policy, clickjacking protection, MIME-sniffing protection, referrer
minimization, and a restrictive Permissions-Policy.

The CSP intentionally keeps 'unsafe-inline' for script-src/style-src because
the existing templates use inline <script>/onclick/style attributes
throughout the app (base_app.html, dashboard.html, review.html, etc.).
Removing that would require a template-by-template rewrite to a nonce/hash
scheme, which is out of scope for a security-hardening pass that must not
change application behavior. frame-ancestors, object-src, base-uri, and
form-action are still fully enforced and provide the primary clickjacking/
injection-scope protections that don't depend on inline-script tightening.
"""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware

# Third-party origins actually referenced by the templates today (Google
# Fonts stylesheet + font files, Chart.js on the admin dashboard). Keep this
# list in sync with template <link>/<script src> tags.
_FONT_CSS_SRC = "https://fonts.googleapis.com"
_FONT_SRC = "https://fonts.gstatic.com"
_CHARTJS_SRC = "https://cdn.jsdelivr.net"


def _build_csp() -> str:
    directives = [
        "default-src 'self'",
        f"script-src 'self' 'unsafe-inline' {_CHARTJS_SRC}",
        f"style-src 'self' 'unsafe-inline' {_FONT_CSS_SRC}",
        f"font-src 'self' data: {_FONT_SRC}",
        "img-src 'self' data: https:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests",
    ]
    return "; ".join(directives)


_CSP_VALUE = _build_csp()

# HSTS only makes sense to advertise once the deployment actually terminates
# TLS; advertising it over plain HTTP (e.g. local dev) is harmless but
# pointless, so gate it the same way cookies already are.
_SECURE_DEPLOYMENT = os.getenv("SECURE_COOKIES", "false").strip().lower() == "true"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(self), "
            "usb=(), interest-cohort=()"
        )
        response.headers["Content-Security-Policy"] = _CSP_VALUE
        # Legacy header for older browsers that don't understand CSP framing;
        # X-Frame-Options above already covers modern ones.
        response.headers.setdefault("X-XSS-Protection", "0")

        if _SECURE_DEPLOYMENT:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response
