"""
Google Sign-In (OpenID Connect) helpers.

Standard library only — no extra dependencies. The ID token is fetched
directly from Google's token endpoint over TLS, so per Google's OIDC docs
it can be decoded without signature verification; we still validate the
issuer, audience, and expiry claims.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.parse
import urllib.request

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
VALID_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


def _client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def _client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "").strip()


def is_configured() -> bool:
    return bool(_client_id() and _client_secret())


def build_auth_url(redirect_uri: str, state: str) -> str:
    params = {
        "client_id": _client_id(),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange the authorization code for tokens at Google's token endpoint."""
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": _client_id(),
        "client_secret": _client_secret(),
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def decode_id_token(id_token: str) -> dict:
    """Decode the ID token payload and validate issuer, audience, and expiry."""
    parts = id_token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed id_token")
    claims = json.loads(_b64url_decode(parts[1]))
    if claims.get("iss") not in VALID_ISSUERS:
        raise ValueError(f"Invalid issuer: {claims.get('iss')}")
    if claims.get("aud") != _client_id():
        raise ValueError("id_token audience does not match GOOGLE_CLIENT_ID")
    if float(claims.get("exp", 0)) < time.time():
        raise ValueError("id_token expired")
    return claims
