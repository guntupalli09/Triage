"""
Cloudflare Turnstile verification for public-facing forms (register, contact,
forgot-password). Free, privacy-friendly CAPTCHA alternative.

Set TURNSTILE_SITE_KEY / TURNSTILE_SECRET_KEY to enable. If unset, verification
is skipped (fails open) so local/dev environments keep working without setup —
this must be configured in production.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx
from fastapi import Request

logger = logging.getLogger(__name__)

TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "").strip()
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "").strip()
VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def is_configured() -> bool:
    return bool(TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY)


async def verify(request: Request, token: Optional[str]) -> bool:
    """Verify a Turnstile response token. Returns True if the form submission
    should proceed (either verification passed, or Turnstile isn't configured)."""
    if not is_configured():
        return True
    if not token:
        return False
    ip = request.client.host if request.client else None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(VERIFY_URL, data={
                "secret": TURNSTILE_SECRET_KEY,
                "response": token,
                "remoteip": ip or "",
            })
        return bool(resp.json().get("success"))
    except Exception as e:
        logger.warning(f"Turnstile verification request failed: {e}")
        return False
