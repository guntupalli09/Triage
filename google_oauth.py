"""
Google Sign-In (OpenID Connect) helpers.

ID tokens are verified with Google's official `google-auth` library, which:
  - fetches Google's published JWKS (with rotation/caching handled internally)
  - verifies the RS256 signature against the matching key
  - verifies the issuer (`accounts.google.com` / `https://accounts.google.com`)
  - verifies the audience matches our OAuth client ID
  - verifies the token has not expired

We never decode the JWT payload ourselves — signature verification always
happens first, inside `google.oauth2.id_token.verify_oauth2_token`.
"""
from __future__ import annotations

import os
import urllib.parse
import urllib.request
import json

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# Reused across requests: caches Google's JWKS internally between calls so we
# don't refetch keys on every sign-in.
_google_auth_request = google_requests.Request()


def _client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def _client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "").strip()


def is_configured() -> bool:
    return bool(_client_id() and _client_secret())


def build_auth_url(redirect_uri: str, state: str, nonce: str) -> str:
    params = {
        "client_id": _client_id(),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
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


def verify_id_token(id_token: str, expected_nonce: str = "") -> dict:
    """Verify and decode a Google ID token.

    Delegates signature verification (against Google's rotating JWKS),
    issuer, audience, and expiry checks entirely to `google-auth`. Raises
    `ValueError` (or a `google.auth.exceptions.GoogleAuthError` subclass,
    itself a `ValueError`) if any check fails.
    """
    claims = google_id_token.verify_oauth2_token(
        id_token, _google_auth_request, audience=_client_id(),
    )
    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValueError(f"Invalid issuer: {claims.get('iss')}")
    if expected_nonce and claims.get("nonce") != expected_nonce:
        raise ValueError("id_token nonce does not match")
    return claims
