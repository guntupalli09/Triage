"""
User-agent parsing service.

Single place where raw `User-Agent` header strings are turned into
structured browser/OS/device facts. Everything else in the codebase
(analytics.py, middleware, admin views) consumes `ParsedUserAgent` —
nothing else touches the raw UA string or the `user_agents` library.

Uses the pure-Python `user_agents` package (no C extension / binary
dependency, safe for the existing Docker image). If the package is
unavailable for any reason, falls back to a small heuristic parser so
signup and page-view tracking never breaks because of a missing
dependency.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from user_agents import parse as _ua_parse
    _HAS_USER_AGENTS = True
except ImportError:  # pragma: no cover - exercised only if dependency missing
    _HAS_USER_AGENTS = False
    logger.warning("user_agents package not installed — falling back to heuristic UA parsing")


@dataclass(frozen=True)
class ParsedUserAgent:
    browser: str | None
    browser_version: str | None
    os: str | None
    os_version: str | None
    device_type: str  # "desktop" | "mobile" | "tablet" | "bot" | "unknown"
    device_brand: str | None
    device_model: str | None
    is_mobile: bool
    is_tablet: bool
    is_desktop: bool
    is_bot: bool


_UNKNOWN = ParsedUserAgent(
    browser=None, browser_version=None, os=None, os_version=None,
    device_type="unknown", device_brand=None, device_model=None,
    is_mobile=False, is_tablet=False, is_desktop=False, is_bot=False,
)

_BOT_RE = re.compile(r"bot|crawl|spider|slurp|facebookexternalhit|preview", re.IGNORECASE)
_MOBILE_RE = re.compile(r"mobile|iphone|android(?!.*tablet)", re.IGNORECASE)
_TABLET_RE = re.compile(r"ipad|tablet", re.IGNORECASE)


def _heuristic_parse(ua_string: str) -> ParsedUserAgent:
    """Best-effort fallback used only when `user_agents` isn't installed."""
    is_bot = bool(_BOT_RE.search(ua_string))
    is_tablet = bool(_TABLET_RE.search(ua_string))
    is_mobile = not is_tablet and bool(_MOBILE_RE.search(ua_string))
    is_desktop = not (is_bot or is_mobile or is_tablet)
    device_type = "bot" if is_bot else "tablet" if is_tablet else "mobile" if is_mobile else "desktop"

    browser = None
    for name in ("Edg", "OPR", "Chrome", "Firefox", "Safari"):
        if name in ua_string:
            browser = {"Edg": "Edge", "OPR": "Opera"}.get(name, name)
            break

    os_name = None
    for token, label in (("Windows", "Windows"), ("Mac OS X", "macOS"), ("Android", "Android"),
                          ("iPhone", "iOS"), ("iPad", "iPadOS"), ("Linux", "Linux")):
        if token in ua_string:
            os_name = label
            break

    return ParsedUserAgent(
        browser=browser, browser_version=None, os=os_name, os_version=None,
        device_type=device_type, device_brand=None, device_model=None,
        is_mobile=is_mobile, is_tablet=is_tablet, is_desktop=is_desktop, is_bot=is_bot,
    )


def parse_user_agent(ua_string: str | None) -> ParsedUserAgent:
    """Parse a raw User-Agent header into structured browser/OS/device facts.

    Never raises — analytics must never be able to break a request.
    """
    if not ua_string or not ua_string.strip():
        return _UNKNOWN

    try:
        if _HAS_USER_AGENTS:
            ua = _ua_parse(ua_string)
            is_bot = bool(ua.is_bot)
            is_tablet = bool(ua.is_tablet)
            is_mobile = bool(ua.is_mobile) and not is_tablet
            is_desktop = bool(ua.is_pc) and not (is_bot or is_mobile or is_tablet)
            device_type = "bot" if is_bot else "tablet" if is_tablet else "mobile" if is_mobile else "desktop"
            return ParsedUserAgent(
                browser=ua.browser.family or None,
                browser_version=ua.browser.version_string or None,
                os=ua.os.family or None,
                os_version=ua.os.version_string or None,
                device_type=device_type,
                device_brand=ua.device.brand or None,
                device_model=ua.device.model or None,
                is_mobile=is_mobile,
                is_tablet=is_tablet,
                is_desktop=is_desktop,
                is_bot=is_bot,
            )
        return _heuristic_parse(ua_string)
    except Exception:
        logger.exception("User-agent parsing failed for UA=%r", ua_string[:200])
        return _UNKNOWN
