"""
Analytics middleware.

Runs once per request and handles everything that would otherwise be
duplicated across route handlers:

- Mints/refreshes the analytics session cookie (`tc_sid`) and, on a brand
  new session, writes the `user_sessions` row.
- Sets the long-lived first-touch attribution cookie exactly once per
  visitor, so marketing attribution (referrer/UTM/landing page) survives
  the Google OAuth redirect round-trip and any gap before signup.
- Automatically records a `page_view` event for ordinary HTML page loads,
  so route handlers don't need to call `analytics.record_event(..., "page_view")`
  themselves.
- Stashes the parsed `RequestContext` on `request.state` so downstream
  route handlers reuse it via `analytics.get_context(request)` instead of
  re-parsing headers/UA/geo.

Analytics failures here are always caught and logged — this middleware
must never turn a working request into a 500.
"""
from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import analytics
from database import SessionLocal

logger = logging.getLogger(__name__)

# Paths that should never be parsed, cookied, or counted as a page view:
# static assets, health/metrics probes, SEO files, and server-to-server
# webhooks (Stripe) which aren't browser navigations at all.
_EXCLUDED_PREFIXES = (
    "/static", "/health", "/robots.txt", "/sitemap.xml",
    "/stripe-webhook", "/config", "/favicon.ico",
)


def _is_excluded(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in _EXCLUDED_PREFIXES)


def _current_user_id(request: Request):
    """Best-effort lookup of the logged-in user for this request, using a
    throwaway DB session so it can never interfere with the route's own
    session/transaction."""
    from auth import get_current_user

    db = SessionLocal()
    try:
        user = get_current_user(request, db)
        return user.id if user else None
    except Exception:
        return None
    finally:
        db.close()


class AnalyticsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        excluded = _is_excluded(path)

        if not excluded:
            try:
                # Build (and cache on request.state) once, up front, so
                # route handlers downstream reuse the exact same context.
                analytics.get_context(request)
            except Exception:
                logger.exception("AnalyticsMiddleware: context build failed")
                excluded = True  # don't attempt cookie/event work below either

        response = await call_next(request)

        if excluded:
            return response

        try:
            ctx = analytics.get_context(request)
            analytics.apply_session_cookie(response, ctx)
            analytics.ensure_first_touch_cookie(request, response)

            user_id = _current_user_id(request) if (ctx.is_new_session or _is_trackable_page_view(request, response)) else None

            if ctx.is_new_session:
                analytics.record_session_start(request, user_id=user_id)

            if _is_trackable_page_view(request, response):
                analytics.record_event(request, "page_view", user_id=user_id)
        except Exception:
            logger.exception("AnalyticsMiddleware: post-processing failed")

        return response


def _is_trackable_page_view(request: Request, response) -> bool:
    if request.method != "GET":
        return False
    if response.status_code != 200:
        return False
    content_type = response.headers.get("content-type", "")
    return content_type.startswith("text/html")
