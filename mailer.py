"""
Outbound email. Uses SMTP when configured via environment variables
(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_STARTTLS);
logs and reports failure otherwise so callers can fall back gracefully.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def email_configured() -> bool:
    return bool(os.getenv("SMTP_HOST"))


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True only if handed to the SMTP server."""
    host = os.getenv("SMTP_HOST")
    if not host:
        logger.warning("SMTP not configured (SMTP_HOST unset); email to %s not sent: %s", to, subject)
        return False

    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_FROM", "no-reply@triagecounsel.com")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    port = int(os.getenv("SMTP_PORT", "587"))
    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            if os.getenv("SMTP_STARTTLS", "true").lower() != "false":
                server.starttls()
            user = os.getenv("SMTP_USER")
            password = os.getenv("SMTP_PASSWORD")
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        return False
