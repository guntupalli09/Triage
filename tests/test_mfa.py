"""
Unit tests for mfa.py: TOTP secret/code handling and recovery codes.
"""
import time

import pyotp
import pytest

import mfa


def test_generate_secret_is_valid_base32():
    secret = mfa.generate_secret()
    assert len(secret) >= 16
    pyotp.TOTP(secret)  # must not raise


def test_provisioning_uri_contains_issuer_and_email():
    secret = mfa.generate_secret()
    uri = mfa.provisioning_uri(secret, "attorney@lawfirm.example")
    assert uri.startswith("otpauth://totp/")
    assert "TriageCounsel" in uri
    assert "attorney" in uri


def test_qr_code_svg_data_uri_is_well_formed():
    secret = mfa.generate_secret()
    uri = mfa.provisioning_uri(secret, "attorney@lawfirm.example")
    data_uri = mfa.qr_code_svg_data_uri(uri)
    assert data_uri.startswith("data:image/svg+xml;base64,")


def test_verify_totp_code_accepts_current_code():
    secret = mfa.generate_secret()
    code = pyotp.TOTP(secret).now()
    assert mfa.verify_totp_code(secret, code) is True


def test_verify_totp_code_rejects_wrong_code():
    secret = mfa.generate_secret()
    assert mfa.verify_totp_code(secret, "000000") is False


def test_verify_totp_code_rejects_code_from_a_different_secret():
    secret_a = mfa.generate_secret()
    secret_b = mfa.generate_secret()
    code_for_b = pyotp.TOTP(secret_b).now()
    assert mfa.verify_totp_code(secret_a, code_for_b) is False


def test_verify_totp_code_rejects_malformed_input():
    secret = mfa.generate_secret()
    assert mfa.verify_totp_code(secret, "") is False
    assert mfa.verify_totp_code(secret, "abcdef") is False
    assert mfa.verify_totp_code(secret, "12345") is False  # too short
    assert mfa.verify_totp_code(secret, "1234567") is False  # too long
    assert mfa.verify_totp_code(None, "123456") is False
    assert mfa.verify_totp_code(secret, None) is False


def test_verify_totp_code_tolerates_adjacent_time_step():
    secret = mfa.generate_secret()
    totp = pyotp.TOTP(secret)
    previous_step_code = totp.at(int(time.time()) - 30)
    assert mfa.verify_totp_code(secret, previous_step_code) is True


def test_generate_recovery_codes_are_unique_and_correct_count():
    codes = mfa.generate_recovery_codes()
    assert len(codes) == mfa.RECOVERY_CODE_COUNT
    assert len(set(codes)) == mfa.RECOVERY_CODE_COUNT
    for code in codes:
        assert len(code) == mfa.RECOVERY_CODE_LENGTH


def test_recovery_code_alphabet_excludes_ambiguous_characters():
    codes = mfa.generate_recovery_codes(n=200)
    joined = "".join(codes)
    for ambiguous in "0O1IL":
        assert ambiguous not in joined


def test_build_recovery_codes_record_stores_hashes_not_plaintext():
    codes = mfa.generate_recovery_codes()
    record = mfa.build_recovery_codes_record(codes)
    assert len(record) == len(codes)
    for entry, code in zip(record, codes):
        assert entry["hash"] != code
        assert entry["hash"] == mfa.hash_recovery_code(code)
        assert entry["used_at"] is None


def test_verify_and_consume_recovery_code_matches_and_marks_used():
    codes = mfa.generate_recovery_codes()
    record = mfa.build_recovery_codes_record(codes)
    matched, updated = mfa.verify_and_consume_recovery_code(record, codes[3])
    assert matched is True
    assert updated[3]["used_at"] is not None
    # Other codes untouched.
    assert all(e["used_at"] is None for i, e in enumerate(updated) if i != 3)


def test_verify_and_consume_recovery_code_rejects_unknown_code():
    codes = mfa.generate_recovery_codes()
    record = mfa.build_recovery_codes_record(codes)
    matched, updated = mfa.verify_and_consume_recovery_code(record, "NOTAREALCODE")
    assert matched is False
    assert updated == record


def test_verify_and_consume_recovery_code_is_single_use():
    codes = mfa.generate_recovery_codes()
    record = mfa.build_recovery_codes_record(codes)
    matched1, record = mfa.verify_and_consume_recovery_code(record, codes[0])
    assert matched1 is True
    matched2, record = mfa.verify_and_consume_recovery_code(record, codes[0])
    assert matched2 is False  # already used


def test_verify_and_consume_recovery_code_is_case_and_format_insensitive():
    codes = mfa.generate_recovery_codes()
    record = mfa.build_recovery_codes_record(codes)
    variant = codes[0].lower()
    matched, _ = mfa.verify_and_consume_recovery_code(record, variant)
    assert matched is True


def test_verify_and_consume_recovery_code_handles_empty_record():
    matched, updated = mfa.verify_and_consume_recovery_code(None, "ANYCODE123")
    assert matched is False
    assert updated is None


def test_count_remaining_recovery_codes():
    codes = mfa.generate_recovery_codes()
    record = mfa.build_recovery_codes_record(codes)
    assert mfa.count_remaining_recovery_codes(record) == len(codes)
    _, record = mfa.verify_and_consume_recovery_code(record, codes[0])
    assert mfa.count_remaining_recovery_codes(record) == len(codes) - 1
    assert mfa.count_remaining_recovery_codes(None) == 0
    assert mfa.count_remaining_recovery_codes([]) == 0
