"""
Google ID token signature verification tests (P1e).

Exercises google_oauth.decode_id_token() against real RS256-signed JWTs
built with a locally generated key pair (no network access to Google's
JWKS endpoint is made or needed) — the JWKS client lookup is monkeypatched
to return the test key, isolating exactly the verification logic this
change added.
"""
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import google_oauth

CLIENT_ID = "test-client-id.apps.googleusercontent.com"


@pytest.fixture(scope="module")
def keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _make_token(private_key, *, iss="https://accounts.google.com", aud=CLIENT_ID,
                 exp_delta=3600, extra_claims=None):
    now = int(time.time())
    claims = {
        "iss": iss,
        "aud": aud,
        "sub": "1234567890",
        "email": "attorney@lawfirm.example",
        "email_verified": True,
        "iat": now,
        "exp": now + exp_delta,
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key-1"})


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJWKClient:
    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey(self._public_key)


@pytest.fixture()
def patch_jwks(monkeypatch, keypair):
    _private, public_key = keypair

    def _fake_get_client():
        return _FakeJWKClient(public_key)

    monkeypatch.setattr(google_oauth, "_get_jwks_client", _fake_get_client)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")


def test_valid_token_is_accepted(patch_jwks, keypair):
    private_key, _ = keypair
    token = _make_token(private_key)
    claims = google_oauth.decode_id_token(token)
    assert claims["email"] == "attorney@lawfirm.example"
    assert claims["sub"] == "1234567890"


def test_token_signed_with_wrong_key_is_rejected(patch_jwks):
    forged_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _make_token(forged_private_key)  # signed with a DIFFERENT key than the JWKS returns
    with pytest.raises(ValueError, match="signature"):
        google_oauth.decode_id_token(token)


def test_expired_token_is_rejected(patch_jwks, keypair):
    private_key, _ = keypair
    token = _make_token(private_key, exp_delta=-3600)
    with pytest.raises(ValueError):
        google_oauth.decode_id_token(token)


def test_wrong_audience_is_rejected(patch_jwks, keypair):
    private_key, _ = keypair
    token = _make_token(private_key, aud="some-other-app.apps.googleusercontent.com")
    with pytest.raises(ValueError):
        google_oauth.decode_id_token(token)


def test_wrong_issuer_is_rejected(patch_jwks, keypair):
    private_key, _ = keypair
    token = _make_token(private_key, iss="https://evil.example.com")
    with pytest.raises(ValueError, match="Invalid issuer"):
        google_oauth.decode_id_token(token)


def test_alternate_valid_issuer_form_is_accepted(patch_jwks, keypair):
    """Google emits both 'accounts.google.com' and 'https://accounts.google.com'
    across token versions; both must remain accepted (pre-existing behavior,
    unchanged by adding signature verification)."""
    private_key, _ = keypair
    token = _make_token(private_key, iss="accounts.google.com")
    claims = google_oauth.decode_id_token(token)
    assert claims["iss"] == "accounts.google.com"


def test_malformed_token_is_rejected(patch_jwks):
    with pytest.raises(ValueError):
        google_oauth.decode_id_token("not-a-real-jwt")


def test_none_algorithm_token_is_rejected(patch_jwks):
    """Classic JWT bypass: a token with alg=none and no signature must not
    be accepted just because it has well-formed claims."""
    now = int(time.time())
    unsigned = jwt.encode(
        {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "sub": "x",
         "email": "x@example.com", "email_verified": True,
         "iat": now, "exp": now + 3600},
        key=None, algorithm="none",
    )
    with pytest.raises(ValueError):
        google_oauth.decode_id_token(unsigned)
