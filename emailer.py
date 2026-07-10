"""
Transactional email sending.

Supports two providers, checked in order:
  1. Resend HTTP API  — set RESEND_API_KEY (recommended on Vercel)
  2. Any SMTP server  — set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD

EMAIL_FROM sets the sender address for both (e.g. "Triage Counsel <no-reply@yourdomain.com>").
Standard library only — no extra dependencies.
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"
DEFAULT_FROM = "Triage Counsel <onboarding@resend.dev>"


def is_configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY", "").strip()) or bool(os.getenv("SMTP_HOST", "").strip())


def send_email(to: str, subject: str, html: str, text: str) -> None:
    """Send an email; raises on failure so callers can react."""
    sender = os.getenv("EMAIL_FROM", "").strip() or DEFAULT_FROM
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    if resend_key:
        _send_via_resend(resend_key, sender, to, subject, html, text)
        return
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    if smtp_host:
        _send_via_smtp(smtp_host, sender, to, subject, html, text)
        return
    raise RuntimeError("No email provider configured (set RESEND_API_KEY or SMTP_HOST)")


def _send_via_resend(api_key: str, sender: str, to: str, subject: str, html: str, text: str) -> None:
    payload = json.dumps({
        "from": sender, "to": [to], "subject": subject, "html": html, "text": text,
    }).encode()
    req = urllib.request.Request(
        RESEND_ENDPOINT,
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()
    logger.info(f"Password email sent via Resend to {to}")


def _send_via_smtp(host: str, sender: str, to: str, subject: str, html: str, text: str) -> None:
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(host, port, timeout=15) as server:
        server.starttls()
        if user:
            server.login(user, password)
        server.sendmail(sender, [to], msg.as_string())
    logger.info(f"Password email sent via SMTP to {to}")
