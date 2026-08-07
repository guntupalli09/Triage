"""
Google Sign-In (OpenID Connect) helpers.

The ID token's RS256 signature is verified against Google's published JWKS
(https://www.googleapis.com/oauth2/v3/certs) using PyJWT, in addition to the
issuer/audience/expiry claim checks. Signature verification is the standard
OIDC requirement and is what actually proves the token was issued by Google
and unmodified in transit — claim checks alone (the previous implementation)
only reject *malformed* or *mismatched* tokens, not forged ones. PyJWT's
PyJWKClient fetches/caches the key set using stdlib urllib under the hood,
so this adds no HTTP-client dependency beyond PyJWT + cryptography.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
JWKS_ENDPOINT = "https://www.googleapis.com/oauth2/v3/certs"
VALID_ISSUERS = ("https://accounts.google.com", "accounts.google.com")

# Module-level so the fetched key set is cached (and reused) across requests
# within a worker process. PyJWKClient's own cache (default lifespan: 5
# minutes) handles picking up Google's periodic key rotation.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(JWKS_ENDPOINT, cache_jwk_set=True, lifespan=300)
    return _jwks_client


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


def decode_id_token(id_token: str) -> dict:
    """Verify the ID token's RS256 signature against Google's JWKS, then
    validate issuer, audience, and expiry. Raises ValueError on any failure
    (malformed token, unknown/rotated signing key, bad signature, wrong
    issuer/audience, or expiry) so callers can keep their existing
    `except Exception` handling around this call."""
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=_client_id(),
            # Google uses both forms across token versions; verified below.
            options={"verify_iss": False},
        )
    except PyJWTError as e:
        raise ValueError(f"id_token signature verification failed: {e}") from e

    if claims.get("iss") not in VALID_ISSUERS:
        raise ValueError(f"Invalid issuer: {claims.get('iss')}")
    return claims
