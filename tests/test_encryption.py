"""
Unit tests for encryption.py — AES-256-GCM encryption at rest (P2).
"""
import base64

import pytest

import encryption


def _key(byte: bytes = b"k") -> str:
    return base64.b64encode(byte * 32).decode("ascii")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Every test starts with a clean encryption env — no leakage from the
    real .env (if any) or from a previous test's monkeypatched keys."""
    monkeypatch.delenv("ENCRYPTION_KEYS", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY_CURRENT", raising=False)


def test_roundtrip_with_dev_default_key():
    """No ENCRYPTION_KEYS configured — falls back to the fixed dev key, but
    the actual encrypt/decrypt code path still runs for real."""
    ciphertext = encryption.encrypt("Confidential: NDA between Acme and Beta Corp")
    assert ciphertext.startswith("enc:v1:")
    assert encryption.decrypt(ciphertext) == "Confidential: NDA between Acme and Beta Corp"


def test_roundtrip_with_configured_key(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    ct = encryption.encrypt("some contract text")
    assert encryption.decrypt(ct) == "some contract text"


def test_every_encryption_uses_a_fresh_unique_nonce(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    a = encryption.encrypt("same plaintext")
    b = encryption.encrypt("same plaintext")
    assert a != b  # different nonce -> different ciphertext even for identical plaintext
    nonce_a = a.split(":")[3]
    nonce_b = b.split(":")[3]
    assert nonce_a != nonce_b
    assert encryption.decrypt(a) == "same plaintext"
    assert encryption.decrypt(b) == "same plaintext"


def test_new_writes_always_use_the_current_key_id(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key(b'a')},k2:{_key(b'b')}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k2")
    ct = encryption.encrypt("x")
    kid = ct.split(":")[2]
    assert kid == "k2"


def test_retired_key_still_decrypts(monkeypatch):
    """Encrypt under k1 while it's current, rotate current to k2, and
    confirm the k1-encrypted value still decrypts (retired keys stay
    decrypt-capable)."""
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key(b'a')},k2:{_key(b'b')}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    old_ciphertext = encryption.encrypt("rotate me")

    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k2")
    assert encryption.decrypt(old_ciphertext) == "rotate me"
    # And new writes now use k2, not k1.
    new_ciphertext = encryption.encrypt("fresh")
    assert new_ciphertext.split(":")[2] == "k2"


def _split_envelope(ct: str):
    """enc:v1:<kid>:<nonce_b64>:<ciphertext_b64> -> (kid, nonce_b64, ciphertext_b64)."""
    parts = ct.split(":")
    assert len(parts) == 5 and parts[0] == "enc" and parts[1] == "v1", ct
    return parts[2], parts[3], parts[4]


def test_tampered_ciphertext_fails_closed(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    ct = encryption.encrypt("sensitive")
    kid, nonce_b64, ciphertext_b64 = _split_envelope(ct)
    raw = bytearray(base64.b64decode(ciphertext_b64))
    raw[0] ^= 0xFF  # corrupt one byte of the ciphertext
    tampered = f"enc:v1:{kid}:{nonce_b64}:{base64.b64encode(bytes(raw)).decode()}"
    with pytest.raises(encryption.DecryptionError):
        encryption.decrypt(tampered)


def test_tampered_nonce_fails_closed(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    ct = encryption.encrypt("sensitive")
    kid, nonce_b64, ciphertext_b64 = _split_envelope(ct)
    raw = bytearray(base64.b64decode(nonce_b64))
    raw[0] ^= 0xFF  # corrupt one byte of the nonce
    tampered = f"enc:v1:{kid}:{base64.b64encode(bytes(raw)).decode()}:{ciphertext_b64}"
    with pytest.raises(encryption.DecryptionError):
        encryption.decrypt(tampered)


def test_wrong_key_fails_closed(monkeypatch):
    """Ciphertext produced under one key set; decrypt attempted after the
    env has rotated to a completely different, non-overlapping key set —
    the referenced key id no longer exists at all."""
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key(b'a')}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    ct = encryption.encrypt("secret")

    monkeypatch.setenv("ENCRYPTION_KEYS", f"k9:{_key(b'z')}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k9")
    with pytest.raises(encryption.DecryptionError, match="Unknown encryption key id"):
        encryption.decrypt(ct)


def test_missing_key_id_referenced_in_envelope_fails_closed(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    forged = f"enc:v1:does-not-exist:{base64.b64encode(b'x'*12).decode()}:{base64.b64encode(b'y'*16).decode()}"
    with pytest.raises(encryption.DecryptionError, match="Unknown encryption key id"):
        encryption.decrypt(forged)


def test_legacy_plaintext_passes_through_unchanged():
    legacy = "This confidentiality agreement was written before encryption existed."
    assert encryption.decrypt(legacy) == legacy


def test_malformed_envelope_is_not_treated_as_plaintext(monkeypatch):
    """A value that HAS the enc:v1: prefix but is otherwise garbage must
    raise, never be silently returned as if it were plaintext — that would
    hide data corruption or tampering as if it were a legitimate contract."""
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    with pytest.raises(encryption.DecryptionError):
        encryption.decrypt("enc:v1:onlytwoparts:nope")
    with pytest.raises(encryption.DecryptionError):
        encryption.decrypt("enc:v1:k1:not-valid-base64!!!:also-not-base64!!!")


def test_none_and_empty_values_pass_through(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    assert encryption.encrypt(None) is None
    assert encryption.encrypt("") == ""
    assert encryption.decrypt(None) is None
    assert encryption.decrypt("") == ""


def test_is_encrypted_helper(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    assert encryption.is_encrypted(encryption.encrypt("x")) is True
    assert encryption.is_encrypted("plain text") is False
    assert encryption.is_encrypted(None) is False
    assert encryption.is_encrypted("") is False


# --- validate_startup() ---

def test_validate_startup_requires_keys_in_production():
    with pytest.raises(encryption.EncryptionConfigError):
        encryption.validate_startup(dev_mode=False)


def test_validate_startup_ok_in_dev_without_keys():
    encryption.validate_startup(dev_mode=True)  # must not raise


def test_validate_startup_passes_with_valid_keys(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    encryption.validate_startup(dev_mode=False)  # must not raise


def test_validate_startup_rejects_wrong_length_key(monkeypatch):
    short_key = base64.b64encode(b"too-short").decode()
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{short_key}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    with pytest.raises(encryption.EncryptionConfigError, match="256"):
        encryption.validate_startup(dev_mode=False)


def test_validate_startup_rejects_malformed_entry(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", "not-a-valid-entry-no-colon")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    with pytest.raises(encryption.EncryptionConfigError):
        encryption.validate_startup(dev_mode=False)


def test_validate_startup_rejects_duplicate_key_ids(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key(b'a')},k1:{_key(b'b')}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    with pytest.raises(encryption.EncryptionConfigError, match="Duplicate"):
        encryption.validate_startup(dev_mode=False)


def test_validate_startup_rejects_unknown_current_key(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "does-not-exist")
    with pytest.raises(encryption.EncryptionConfigError):
        encryption.validate_startup(dev_mode=False)


def test_validate_startup_rejects_missing_current_when_keys_set(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.delenv("ENCRYPTION_KEY_CURRENT", raising=False)
    with pytest.raises(encryption.EncryptionConfigError):
        encryption.validate_startup(dev_mode=False)
