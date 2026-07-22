"""
Tests for Google OIDC ID token verification (google_oauth.py).

`verify_id_token` delegates signature/issuer/audience/expiry verification
to google-auth's `id_token.verify_oauth2_token`, so these tests mock that
call rather than hitting Google's real JWKS endpoint over the network.
"""
from unittest.mock import patch

import pytest

import google_oauth


def test_build_auth_url_includes_state_and_nonce(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    url = google_oauth.build_auth_url("https://example.com/callback", state="s3cr3t-state", nonce="n0nce-value")
    assert "state=s3cr3t-state" in url
    assert "nonce=n0nce-value" in url
    assert "client_id=test-client-id" in url


def test_verify_id_token_delegates_to_google_auth_library(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    fake_claims = {
        "iss": "https://accounts.google.com",
        "aud": "test-client-id",
        "email": "user@example.com",
        "email_verified": True,
        "sub": "1234567890",
        "nonce": "expected-nonce",
    }
    with patch("google_oauth.google_id_token.verify_oauth2_token", return_value=fake_claims) as mock_verify:
        claims = google_oauth.verify_id_token("fake.jwt.token", expected_nonce="expected-nonce")

    mock_verify.assert_called_once()
    args, kwargs = mock_verify.call_args
    assert args[0] == "fake.jwt.token"
    assert kwargs.get("audience") == "test-client-id"
    assert claims["email"] == "user@example.com"


def test_verify_id_token_rejects_invalid_issuer(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    fake_claims = {"iss": "https://evil.example.com", "aud": "test-client-id"}
    with patch("google_oauth.google_id_token.verify_oauth2_token", return_value=fake_claims):
        with pytest.raises(ValueError, match="Invalid issuer"):
            google_oauth.verify_id_token("fake.jwt.token")


def test_verify_id_token_rejects_nonce_mismatch(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    fake_claims = {
        "iss": "accounts.google.com",
        "aud": "test-client-id",
        "nonce": "attacker-supplied-nonce",
    }
    with patch("google_oauth.google_id_token.verify_oauth2_token", return_value=fake_claims):
        with pytest.raises(ValueError, match="nonce"):
            google_oauth.verify_id_token("fake.jwt.token", expected_nonce="the-real-nonce")


def test_verify_id_token_propagates_google_auth_verification_failure(monkeypatch):
    """A bad signature, expired token, or audience mismatch is caught by
    google-auth itself, before our own checks run — we must not swallow it."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    with patch(
        "google_oauth.google_id_token.verify_oauth2_token",
        side_effect=ValueError("Token used too early/late"),
    ):
        with pytest.raises(ValueError, match="too early/late"):
            google_oauth.verify_id_token("fake.jwt.token")


def test_is_configured_requires_both_client_id_and_secret(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    assert google_oauth.is_configured() is False

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    assert google_oauth.is_configured() is True
