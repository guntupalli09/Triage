"""
Unit tests for upload_security.py (P5): filename sanitization,
magic-byte/MIME sniffing, zip-bomb and PDF-bomb guards, and the pluggable
malware-scanning interface.
"""
import io
import zipfile

import pytest

import upload_security as us


# --- Filename sanitization ---

def test_sanitize_filename_strips_path_components():
    assert us.sanitize_filename("../../etc/passwd") == "passwd"
    assert us.sanitize_filename("C:\\Windows\\System32\\evil.txt") == "evil.txt"
    assert us.sanitize_filename("/var/www/uploads/../../secret.pdf") == "secret.pdf"


def test_sanitize_filename_strips_control_and_unsafe_characters():
    assert us.sanitize_filename("nda\x00.txt") == "nda.txt"
    result = us.sanitize_filename('weird<>:"|?*name.pdf')
    assert not any(c in result for c in '<>:"|?*')


def test_sanitize_filename_empty_or_blank_gets_fallback():
    assert us.sanitize_filename("") == "upload"
    assert us.sanitize_filename("   ") == "upload"
    assert us.sanitize_filename(None) == "upload"


def test_sanitize_filename_caps_length():
    long_name = ("a" * 500) + ".pdf"
    result = us.sanitize_filename(long_name)
    assert len(result) <= us.MAX_FILENAME_LENGTH
    assert result.endswith(".pdf")


def test_sanitize_filename_preserves_normal_names():
    assert us.sanitize_filename("Master Services Agreement.docx") == "Master Services Agreement.docx"
    assert us.sanitize_filename("nda_v2-final.pdf") == "nda_v2-final.pdf"


def test_sanitize_filename_strips_trailing_dots_and_spaces():
    assert us.sanitize_filename("evil.txt.   ") == "evil.txt"


# --- Magic-byte / MIME validation ---

def test_valid_pdf_signature_accepted():
    us.validate_magic_bytes(b"%PDF-1.4\n%...rest of pdf", ".pdf")  # must not raise


def test_valid_docx_signature_accepted():
    us.validate_magic_bytes(b"PK\x03\x04\x14\x00...", ".docx")  # must not raise


def test_txt_with_plain_text_accepted():
    us.validate_magic_bytes(b"This is a confidentiality agreement.", ".txt")  # must not raise


def test_exe_disguised_as_pdf_is_rejected():
    with pytest.raises(us.UploadRejected):
        us.validate_magic_bytes(b"MZ\x90\x00\x03\x00\x00\x00", ".pdf")


def test_docx_disguised_as_pdf_is_rejected():
    with pytest.raises(us.UploadRejected):
        us.validate_magic_bytes(b"PK\x03\x04rest of a real docx", ".pdf")


def test_exe_disguised_as_txt_is_rejected():
    with pytest.raises(us.UploadRejected):
        us.validate_magic_bytes(b"MZ\x90\x00\x03\x00\x00\x00binary content here", ".txt")


def test_pdf_disguised_as_txt_is_rejected():
    with pytest.raises(us.UploadRejected):
        us.validate_magic_bytes(b"%PDF-1.4 fake text file", ".txt")


def test_binary_content_with_null_bytes_disguised_as_txt_is_rejected():
    with pytest.raises(us.UploadRejected):
        us.validate_magic_bytes(b"some text\x00\x00\x00binary garbage", ".txt")


def test_empty_pdf_content_is_rejected():
    with pytest.raises(us.UploadRejected):
        us.validate_magic_bytes(b"not a pdf at all", ".pdf")


# --- Zip-bomb protection (.docx) ---

def _build_zip(entries: dict, compress=zipfile.ZIP_DEFLATED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compress) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_valid_small_docx_zip_passes():
    zip_bytes = _build_zip({"word/document.xml": "<xml>hello world</xml>"})
    us.validate_docx_zip_safety(zip_bytes)  # must not raise


def test_corrupt_zip_is_rejected():
    with pytest.raises(us.UploadRejected):
        us.validate_docx_zip_safety(b"not a zip file at all")


def test_too_many_entries_is_rejected():
    entries = {f"file{i}.xml": "x" for i in range(us.ZIP_MAX_ENTRIES + 10)}
    zip_bytes = _build_zip(entries)
    with pytest.raises(us.UploadRejected):
        us.validate_docx_zip_safety(zip_bytes)


def test_high_compression_ratio_is_rejected():
    """Classic zip-bomb shape: a tiny compressed entry that expands to a
    huge uncompressed size."""
    huge_repetitive_content = "0" * (5 * 1024 * 1024)  # highly compressible
    zip_bytes = _build_zip({"bomb.xml": huge_repetitive_content}, compress=zipfile.ZIP_DEFLATED)
    with pytest.raises(us.UploadRejected):
        us.validate_docx_zip_safety(zip_bytes)


def test_total_uncompressed_size_limit_is_rejected():
    entries = {}
    remaining = us.ZIP_MAX_UNCOMPRESSED_TOTAL_BYTES + (10 * 1024 * 1024)
    chunk = "a" * (1024 * 1024)
    i = 0
    while remaining > 0:
        entries[f"part{i}.xml"] = chunk
        remaining -= len(chunk)
        i += 1
    zip_bytes = _build_zip(entries, compress=zipfile.ZIP_STORED)
    with pytest.raises(us.UploadRejected):
        us.validate_docx_zip_safety(zip_bytes)


# --- PDF-bomb protection ---

def test_pdf_page_count_within_limit_passes():
    us.validate_pdf_page_count(10)  # must not raise


def test_pdf_page_count_over_limit_is_rejected():
    with pytest.raises(us.UploadRejected):
        us.validate_pdf_page_count(us.PDF_MAX_PAGES + 1)


def test_extracted_text_within_limit_passes():
    assert us.enforce_extracted_text_limit("short text") == "short text"


def test_extracted_text_over_limit_is_rejected():
    huge_text = "x" * (us.PDF_MAX_EXTRACTED_TEXT_CHARS + 1)
    with pytest.raises(us.UploadRejected):
        us.enforce_extracted_text_limit(huge_text)


# --- Malware scanning interface ---

def test_noop_scanner_reports_clean(monkeypatch):
    monkeypatch.delenv("MALWARE_SCANNER", raising=False)
    us.reset_malware_scanner_cache()
    us.scan_for_malware(b"any content")  # must not raise


def test_scan_for_malware_rejects_when_scanner_reports_dirty(monkeypatch):
    class _FakeDirtyScanner(us.MalwareScanner):
        def scan(self, file_bytes: bytes) -> us.ScanResult:
            return us.ScanResult(clean=False, reason="Eicar-Test-Signature")

    monkeypatch.setattr(us, "get_malware_scanner", lambda: _FakeDirtyScanner())
    with pytest.raises(us.UploadRejected, match="Eicar-Test-Signature"):
        us.scan_for_malware(b"malicious content")


def test_scan_for_malware_passes_when_scanner_reports_clean(monkeypatch):
    class _FakeCleanScanner(us.MalwareScanner):
        def scan(self, file_bytes: bytes) -> us.ScanResult:
            return us.ScanResult(clean=True)

    monkeypatch.setattr(us, "get_malware_scanner", lambda: _FakeCleanScanner())
    us.scan_for_malware(b"harmless content")  # must not raise


def test_unconfigured_backend_falls_back_to_noop(monkeypatch):
    monkeypatch.delenv("MALWARE_SCANNER", raising=False)
    us.reset_malware_scanner_cache()
    scanner = us.get_malware_scanner()
    assert isinstance(scanner, us.NoopMalwareScanner)


def test_clamd_backend_falls_back_to_noop_when_clamd_unreachable(monkeypatch):
    """clamd isn't installed/running in this environment — selecting that
    backend must degrade to no-op (with a logged error) rather than crash
    the app at startup or on first upload."""
    monkeypatch.setenv("MALWARE_SCANNER", "clamd")
    monkeypatch.setenv("CLAMD_HOST", "no-such-host.invalid")
    us.reset_malware_scanner_cache()
    scanner = us.get_malware_scanner()
    assert isinstance(scanner, us.NoopMalwareScanner)
    monkeypatch.delenv("MALWARE_SCANNER", raising=False)
    us.reset_malware_scanner_cache()
