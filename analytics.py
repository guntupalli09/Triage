"""
First-party acquisition & product analytics service.

This module is the *only* place request-level analytics data is parsed
and turned into database rows. Middleware, the OAuth flow, and every
route handler that wants to record something call into these functions
rather than re-implementing IP/UA/UTM parsing locally.

Two things are cached per-request on `request.state` so repeated calls
within the same request never redo work:

- `request.state._tc_context`  → RequestContext (see `get_context`)

Everything here is defensive: analytics must never be able to break a
page view, a signup, an OAuth login, or a contract upload. Every public
function catches its own exceptions.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

from fastapi import Request
from sqlalchemy.orm import Session as DBSession

from channel_classifier import classify_channel as _classify_channel
from database import SessionLocal
from geo_service import GeoResult, geolocate
from ua_service import ParsedUserAgent, parse_user_agent

logger = logging.getLogger(__name__)

UTM_PARAMS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")
CLICK_ID_PARAMS = ("gclid", "fbclid", "msclkid", "ttclid", "li_fat_id")

FIRST_TOUCH_COOKIE = "tc_first_touch"
FIRST_TOUCH_MAX_AGE = 60 * 60 * 24 * 400  # 400 days, GA4 convention
SESSION_COOKIE = "tc_sid"
SESSION_MAX_AGE = 60 * 30  # 30 minutes of inactivity ends a session

_SECURE_COOKIES = os.getenv("SECURE_COOKIES", "false").strip().lower() == "true"


# ---------------------------------------------------------------------------
# Low-level extractors — each does exactly one thing, called once per
# request by `get_context()` / `build_context()`.
# ---------------------------------------------------------------------------

def extract_headers(request: Request) -> dict[str, str]:
    """All request headers, lowercased keys."""
    return {k.lower(): v for k, v in request.headers.items()}


def _valid_ip_or_none(value: Optional[str]) -> Optional[str]:
    """Proxy headers are client-influenced. Validate before trusting one —
    an unvalidated value can reach a Postgres INET column and fail the
    insert (analytics writes are caught, but that silently drops the row)."""
    if not value:
        return None
    try:
        import ipaddress
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def extract_ip(request: Request, headers: Optional[Mapping[str, str]] = None) -> str:
    """Best client IP, honoring common proxy/CDN conventions in priority order.
    Falls back to the socket-level peer address (always a valid IP) if every
    proxy header is absent or fails to parse as an address."""
    headers = headers if headers is not None else extract_headers(request)
    candidate = (
        _valid_ip_or_none(headers.get("cf-connecting-ip"))
        or _valid_ip_or_none(headers.get("x-real-ip"))
        or _valid_ip_or_none((headers.get("x-forwarded-for", "").split(",") or [""])[0])
    )
    if candidate:
        return candidate
    return request.client.host if request.client else ""


def extract_language(request: Request, headers: Optional[Mapping[str, str]] = None) -> Optional[str]:
    headers = headers if headers is not None else extract_headers(request)
    raw = headers.get("accept-language", "")
    if not raw:
        return None
    return raw.split(",")[0].split(";")[0].strip() or None


def extract_referrer(request: Request, headers: Optional[Mapping[str, str]] = None) -> Optional[str]:
    headers = headers if headers is not None else extract_headers(request)
    return headers.get("referer") or None


def _referring_domain(referrer: Optional[str], own_host: str) -> Optional[str]:
    if not referrer:
        return None
    try:
        domain = (urlparse(referrer).netloc or "").lower()
        if not domain or domain == own_host.lower():
            return None  # internal navigation isn't an acquisition referrer
        return domain
    except Exception:
        return None


def extract_query_parameters(request: Request) -> str:
    return str(request.url.query or "")


def extract_utm(request: Request) -> dict[str, Optional[str]]:
    qp = request.query_params
    return {key: qp.get(key) or None for key in UTM_PARAMS}


def extract_click_ids(request: Request) -> dict[str, Optional[str]]:
    qp = request.query_params
    return {key: qp.get(key) or None for key in CLICK_ID_PARAMS}


def extract_browser(ua: ParsedUserAgent) -> tuple[Optional[str], Optional[str]]:
    return ua.browser, ua.browser_version


def extract_os(ua: ParsedUserAgent) -> tuple[Optional[str], Optional[str]]:
    return ua.os, ua.os_version


def extract_device(ua: ParsedUserAgent) -> ParsedUserAgent:
    """Device facts are already fully captured on ParsedUserAgent; this
    accessor exists so callers don't need to reach into ua_service directly."""
    return ua


def detect_country(geo: GeoResult) -> Optional[str]:
    return geo.country


def detect_region(geo: GeoResult) -> Optional[str]:
    return geo.region


def detect_city(geo: GeoResult) -> Optional[str]:
    return geo.city


def detect_timezone(geo: GeoResult) -> Optional[str]:
    return geo.timezone


def detect_isp(geo: GeoResult) -> Optional[str]:
    return geo.isp


def detect_asn(geo: GeoResult) -> Optional[str]:
    return geo.asn


def classify_channel(
    referring_domain: Optional[str],
    utm: Optional[Mapping[str, Optional[str]]] = None,
    click_ids: Optional[Mapping[str, Optional[str]]] = None,
) -> str:
    return _classify_channel(referring_domain, utm, click_ids)


# ---------------------------------------------------------------------------
# RequestContext — the single parse-once-per-request bundle.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RequestContext:
    ip: str
    x_forwarded_for: Optional[str]
    x_real_ip: Optional[str]
    user_agent: str
    ua: ParsedUserAgent
    referrer: Optional[str]
    referring_domain: Optional[str]
    landing_page: str
    query_string: str
    utm: dict[str, Optional[str]]
    click_ids: dict[str, Optional[str]]
    language: Optional[str]
    geo: GeoResult
    channel: str
    session_id: str
    is_new_session: bool
    request_id: str


def build_context(request: Request, *, geo_network_fallback: bool = False) -> RequestContext:
    """Parse everything about this request exactly once. Never raises —
    on any internal failure returns the most degraded-but-valid context
    possible so callers always get *something*."""
    try:
        headers = extract_headers(request)
        ip = extract_ip(request, headers)
        ua_string = headers.get("user-agent", "")
        ua = parse_user_agent(ua_string)
        referrer = extract_referrer(request, headers)
        own_host = headers.get("host", request.url.hostname or "")
        referring_domain = _referring_domain(referrer, own_host)
        utm = extract_utm(request)
        click_ids = extract_click_ids(request)
        geo = geolocate(ip, headers, allow_network_fallback=geo_network_fallback)
        channel = classify_channel(referring_domain, utm, click_ids)
        session_id, is_new_session = _read_session_id(request)

        return RequestContext(
            ip=ip,
            x_forwarded_for=headers.get("x-forwarded-for"),
            x_real_ip=headers.get("x-real-ip"),
            user_agent=ua_string,
            ua=ua,
            referrer=referrer,
            referring_domain=referring_domain,
            landing_page=str(request.url.path),
            query_string=extract_query_parameters(request),
            utm=utm,
            click_ids=click_ids,
            language=extract_language(request, headers),
            geo=geo,
            channel=channel,
            session_id=session_id,
            is_new_session=is_new_session,
            request_id=getattr(request.state, "request_id", "") or "",
        )
    except Exception:
        logger.exception("analytics.build_context failed — returning degraded context")
        sid = secrets.token_urlsafe(18)
        return RequestContext(
            ip="", x_forwarded_for=None, x_real_ip=None, user_agent="",
            ua=parse_user_agent(None), referrer=None, referring_domain=None,
            landing_page=str(request.url.path) if request else "",
            query_string="", utm={k: None for k in UTM_PARAMS},
            click_ids={k: None for k in CLICK_ID_PARAMS}, language=None,
            geo=GeoResult(), channel="Unknown", session_id=sid,
            is_new_session=True, request_id="",
        )


def get_context(request: Request) -> RequestContext:
    """Memoized per-request accessor. The middleware calls build_context()
    once; everything downstream (route handlers, event recorders) should
    call this instead of build_context() directly."""
    cached = getattr(request.state, "_tc_context", None)
    if cached is not None:
        return cached
    ctx = build_context(request)
    request.state._tc_context = ctx
    return ctx


def _read_session_id(request: Request) -> tuple[str, bool]:
    existing = request.cookies.get(SESSION_COOKIE)
    if existing:
        return existing, False
    return secrets.token_urlsafe(24), True


def apply_session_cookie(response, ctx: RequestContext) -> None:
    """Refresh the sliding-window session cookie on the outgoing response."""
    response.set_cookie(
        SESSION_COOKIE, ctx.session_id, max_age=SESSION_MAX_AGE,
        httponly=True, samesite="lax", secure=_SECURE_COOKIES,
    )


# ---------------------------------------------------------------------------
# First-touch capture — survives the Google OAuth redirect round-trip and
# arbitrarily long gaps between first visit and eventual signup.
# ---------------------------------------------------------------------------

def _encode_first_touch(ctx: RequestContext) -> str:
    payload = {
        "referrer": ctx.referrer,
        "referring_domain": ctx.referring_domain,
        "landing_page": ctx.landing_page,
        "query_string": ctx.query_string,
        "utm": ctx.utm,
        "click_ids": ctx.click_ids,
        "session_id": ctx.session_id,
        "request_id": ctx.request_id,
        "captured_at": datetime.utcnow().isoformat(),
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_first_touch(raw: str) -> Optional[dict]:
    try:
        return json.loads(base64.urlsafe_b64decode(raw.encode()).decode())
    except Exception:
        return None


def ensure_first_touch_cookie(request: Request, response) -> None:
    """Set the first-touch marketing-attribution cookie exactly once per
    visitor. No-op if it's already present. Never raises."""
    try:
        if request.cookies.get(FIRST_TOUCH_COOKIE):
            return
        ctx = get_context(request)
        response.set_cookie(
            FIRST_TOUCH_COOKIE, _encode_first_touch(ctx), max_age=FIRST_TOUCH_MAX_AGE,
            httponly=True, samesite="lax", secure=_SECURE_COOKIES,
        )
    except Exception:
        logger.exception("Failed to set first-touch cookie")


def get_first_touch(request: Request) -> Optional[dict]:
    raw = request.cookies.get(FIRST_TOUCH_COOKIE)
    if not raw:
        return None
    return _decode_first_touch(raw)


# ---------------------------------------------------------------------------
# Acquisition persistence
# ---------------------------------------------------------------------------

def persist_user_acquisition(db: DBSession, user, request: Request) -> Optional[Any]:
    """Write the immutable signup snapshot for `user`, once. Safe to call
    on every login/signup path — no-ops if a row already exists.

    Marketing attribution (referrer/UTM/landing page/click IDs) comes from
    the first-touch cookie so it survives the Google OAuth redirect and
    any delay between first visit and signup completion. Device/geo/IP
    come from *this* request, since that's the actual signup moment.
    """
    from analytics_models import UserAcquisition  # local import avoids a hard cycle at module load

    try:
        existing = db.query(UserAcquisition).filter(UserAcquisition.user_id == user.id).first()
        if existing:
            return existing

        ctx = get_context(request)
        first_touch = get_first_touch(request) or {}
        utm = first_touch.get("utm") or ctx.utm
        click_ids = first_touch.get("click_ids") or ctx.click_ids
        referring_domain = first_touch.get("referring_domain") or ctx.referring_domain
        channel = classify_channel(referring_domain, utm, click_ids)

        # The cached per-request context intentionally skips the network
        # geo fallback so ordinary page views stay fast. Signup is rare
        # relative to total traffic and the data is permanent, so it's
        # worth a best-effort upgrade here if cheap sources found nothing.
        geo = ctx.geo
        if geo.country is None and ctx.ip:
            geo = geolocate(ctx.ip, extract_headers(request), allow_network_fallback=True)

        ipv4, ipv6 = _split_ip_family(ctx.ip)

        row = UserAcquisition(
            user_id=user.id,
            signup_timestamp=datetime.utcnow(),
            signup_ip=ipv4,
            signup_ipv6=ipv6,
            signup_country=detect_country(geo),
            signup_region=detect_region(geo),
            signup_city=detect_city(geo),
            signup_timezone=detect_timezone(geo),
            signup_latitude=geo.latitude,
            signup_longitude=geo.longitude,
            signup_user_agent=ctx.user_agent or None,
            browser=ctx.ua.browser,
            browser_version=ctx.ua.browser_version,
            os=ctx.ua.os,
            os_version=ctx.ua.os_version,
            device_type=ctx.ua.device_type,
            device_brand=ctx.ua.device_brand,
            device_model=ctx.ua.device_model,
            is_mobile=ctx.ua.is_mobile,
            is_tablet=ctx.ua.is_tablet,
            is_desktop=ctx.ua.is_desktop,
            language=ctx.language,
            screen_resolution=None,  # only obtainable client-side; populated via /analytics/client-hints if added later
            viewport=None,
            signup_referrer=first_touch.get("referrer") or ctx.referrer,
            signup_referring_domain=referring_domain,
            landing_page=first_touch.get("landing_page") or ctx.landing_page,
            query_string=first_touch.get("query_string") or ctx.query_string,
            utm_source=utm.get("utm_source"),
            utm_medium=utm.get("utm_medium"),
            utm_campaign=utm.get("utm_campaign"),
            utm_term=utm.get("utm_term"),
            utm_content=utm.get("utm_content"),
            gclid=click_ids.get("gclid"),
            fbclid=click_ids.get("fbclid"),
            msclkid=click_ids.get("msclkid"),
            ttclid=click_ids.get("ttclid"),
            li_fat_id=click_ids.get("li_fat_id"),
            session_id=first_touch.get("session_id") or ctx.session_id,
            first_request_id=first_touch.get("request_id") or ctx.request_id,
            x_forwarded_for=ctx.x_forwarded_for,
            x_real_ip=ctx.x_real_ip,
            asn=detect_asn(geo),
            isp=detect_isp(geo),
            acquisition_channel=channel,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        logger.exception("persist_user_acquisition failed for user_id=%s", getattr(user, "id", None))
        db.rollback()
        return None


def _split_ip_family(ip: str) -> tuple[Optional[str], Optional[str]]:
    if not ip:
        return None, None
    return (ip, None) if ":" not in ip else (None, ip)


# ---------------------------------------------------------------------------
# Session tracking
# ---------------------------------------------------------------------------

def record_session_start(request: Request, user_id: Optional[int] = None) -> None:
    """Create the user_sessions row for a newly-minted session_id. Uses a
    private DB session so it never interferes with the caller's transaction."""
    from analytics_models import UserSession

    ctx = get_context(request)
    if not ctx.is_new_session:
        return

    db = SessionLocal()
    try:
        row = UserSession(
            user_id=user_id,
            session_id=ctx.session_id,
            started_at=datetime.utcnow(),
            ip=ctx.ip or None,
            country=detect_country(ctx.geo),
            browser=ctx.ua.browser,
            os=ctx.ua.os,
            device=ctx.ua.device_type,
            user_agent=ctx.user_agent or None,
            landing_page=ctx.landing_page,
            referrer=ctx.referrer,
            is_authenticated=user_id is not None,
        )
        db.add(row)
        db.commit()
    except Exception:
        logger.exception("record_session_start failed")
        db.rollback()
    finally:
        db.close()


def end_session(request: Request) -> None:
    """Mark the current session as ended (called on explicit logout)."""
    from analytics_models import UserSession

    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return
    db = SessionLocal()
    try:
        row = db.query(UserSession).filter(UserSession.session_id == session_id).first()
        if row and not row.ended_at:
            row.ended_at = datetime.utcnow()
            db.commit()
    except Exception:
        logger.exception("end_session failed")
        db.rollback()
    finally:
        db.close()


def mark_session_authenticated(request: Request, user) -> None:
    """Flip is_authenticated on the current session row once a visitor logs in."""
    from analytics_models import UserSession

    session_id = request.cookies.get(SESSION_COOKIE) or get_context(request).session_id
    db = SessionLocal()
    try:
        row = db.query(UserSession).filter(UserSession.session_id == session_id).first()
        if row:
            row.is_authenticated = True
            if row.user_id is None:
                row.user_id = user.id
            db.commit()
    except Exception:
        logger.exception("mark_session_authenticated failed")
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Event tracking
# ---------------------------------------------------------------------------

def build_event(
    request: Optional[Request],
    event_type: str,
    *,
    user_id: Optional[int] = None,
    page: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Pure event-payload builder — no DB access. Useful for logging,
    testing, or feeding an external queue in addition to Postgres."""
    if request is not None:
        ctx = get_context(request)
        return {
            "user_id": user_id,
            "session_id": ctx.session_id,
            "event_type": event_type,
            "event_timestamp": datetime.utcnow(),
            "page": page or ctx.landing_page,
            "ip": ctx.ip or None,
            "country": detect_country(ctx.geo),
            "referrer": ctx.referrer,
            "metadata": metadata,
        }
    return {
        "user_id": user_id,
        "session_id": None,
        "event_type": event_type,
        "event_timestamp": datetime.utcnow(),
        "page": page,
        "ip": None,
        "country": None,
        "referrer": None,
        "metadata": metadata,
    }


def record_event(
    request: Optional[Request],
    event_type: str,
    *,
    user=None,
    user_id: Optional[int] = None,
    page: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Fire-and-forget product event write. Uses its own short-lived DB
    session (not the caller's) so an analytics write can never roll back
    or block a business transaction. Never raises.
    """
    from analytics_models import UserEvent

    resolved_user_id = user_id if user_id is not None else getattr(user, "id", None)
    payload = build_event(request, event_type, user_id=resolved_user_id, page=page, metadata=metadata)

    db = SessionLocal()
    try:
        row = UserEvent(
            user_id=payload["user_id"],
            session_id=payload["session_id"],
            event_type=payload["event_type"],
            event_timestamp=payload["event_timestamp"],
            page=payload["page"],
            ip=payload["ip"],
            country=payload["country"],
            referrer=payload["referrer"],
            event_metadata=payload["metadata"],
        )
        db.add(row)
        db.commit()
    except Exception:
        logger.exception("record_event failed for event_type=%s", event_type)
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Contract upload tracking
# ---------------------------------------------------------------------------

def build_contract_event(
    request: Request,
    *,
    contract_id: Optional[int],
    user_id: Optional[int],
    filename: str,
    file_bytes: bytes,
    status: str,
    processing_time: Optional[float] = None,
):
    """Build (but don't commit) a ContractEvent row so callers can add it
    to the same DB session/transaction as the Contract row itself."""
    from analytics_models import ContractEvent

    ctx = get_context(request)
    return ContractEvent(
        contract_id=contract_id,
        user_id=user_id,
        session_id=ctx.session_id,
        event_timestamp=datetime.utcnow(),
        upload_ip=ctx.ip or None,
        country=detect_country(ctx.geo),
        browser=ctx.ua.browser,
        device=ctx.ua.device_type,
        user_agent=ctx.user_agent or None,
        filename=filename,
        sha256=hashlib.sha256(file_bytes).hexdigest(),
        filesize=len(file_bytes),
        processing_time=processing_time,
        status=status,
    )
