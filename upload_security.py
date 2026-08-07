"""
Upload hardening (P5 of the security hardening pass — see docs/security
audit findings M-03): filename sanitization, magic-byte/MIME sniffing, a
pluggable malware-scanning interface, and zip-bomb / PDF-bomb guards.

Everything here is deliberately dependency-light (stdlib zipfile only, no
libmagic) so it works identically in the Docker deployment and the
serverless Vercel deployment (see vercel.json) without a system package
that may not be installable there.

True CPU-time/memory sandboxing of document parsing (so a pathological
file can't hang or OOM a worker no matter what) is an infrastructure
concern — process isolation with hard resource limits — not something this
module can enforce from inside the same process that's doing the parsing.
That's documented as an infra recommendation (see docs/security/
upload_hardening_infra.md) rather than attempted here; what this module
does provide are the checks that catch the overwhelming majority of
malicious/malformed uploads before expensive parsing even starts.
"""
from __future__ import annotations

import io
import logging
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


class UploadRejected(ValueError):
    """Raised for any upload-hardening rejection. A ValueError subclass so
    existing `except Exception` handlers around extract_text_from_file()
    keep working unchanged; callers that want the specific reason can
    catch this before the generic case."""


# --- Filename sanitization ---

_UNSAFE_FILENAME_CHARS = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*]')
MAX_FILENAME_LENGTH = 255


def sanitize_filename(filename: str) -> str:
    """Strips directory components (path traversal), control characters,
    and filesystem-unsafe characters; caps length. The extension is
    preserved as-is in the normal case (it only contains safe characters
    to begin with) so callers can keep deriving it from the sanitized name."""
    name = (filename or "").strip()
    # os.path.basename only understands the host OS's separator (POSIX "/"
    # on Linux) — split on both "/" and "\" explicitly so a Windows-style
    # path in an attacker-controlled filename is stripped the same way
    # regardless of what platform this is running on.
    name = name.replace("\\", "/")
    name = os.path.basename(name)
    name = name.replace("\x00", "")
    name = _UNSAFE_FILENAME_CHARS.sub("_", name)
    name = name.strip(" .")  # trailing dot/space is a Windows-reserved quirk
    if not name:
        name = "upload"
    if len(name) > MAX_FILENAME_LENGTH:
        base, ext = os.path.splitext(name)
        name = base[: MAX_FILENAME_LENGTH - len(ext)] + ext
    return name


# --- Magic-byte / MIME sniffing ---
# No libmagic dependency (see module docstring) — these are the actual
# format signatures PDF/DOCX/ZIP readers themselves rely on, so this
# directly answers "does the content match the claimed type", not a
# heuristic approximation of it.

_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".docx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),  # docx is a zip archive
}

_BINARY_SIGNATURES = (
    b"%PDF-", b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08",  # PDF / zip-family (docx, etc.)
    b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff",  # PNG, JPEG
    b"MZ",  # Windows PE executable
    b"\x7fELF",  # Linux ELF executable
)


def validate_magic_bytes(file_bytes: bytes, ext: str) -> None:
    """For .pdf/.docx: content must start with the format's real magic
    bytes. For .txt: content must NOT start with a known binary format's
    signature — a mismatch there means an executable or other binary file
    was renamed to masquerade as a text upload."""
    if ext in _SIGNATURES:
        if not any(file_bytes.startswith(sig) for sig in _SIGNATURES[ext]):
            raise UploadRejected(f"File content doesn't match its {ext} extension.")
        return

    if ext == ".txt":
        if any(file_bytes.startswith(sig) for sig in _BINARY_SIGNATURES):
            raise UploadRejected("File content doesn't match its .txt extension.")
        # A NUL byte in the first few KB is not something a real text
        # document contains — it's the standard signal of binary content.
        if b"\x00" in file_bytes[:8192]:
            raise UploadRejected("File appears to be binary, not a text document.")


# --- Zip-bomb protection (.docx is a zip archive) ---

ZIP_MAX_ENTRIES = 2_000
ZIP_MAX_UNCOMPRESSED_TOTAL_BYTES = 50 * 1024 * 1024  # 50MB — generous for any real DOCX
ZIP_MAX_COMPRESSION_RATIO = 100  # classic zip-bomb heuristic threshold


def validate_docx_zip_safety(file_bytes: bytes) -> None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(file_bytes))
        infos = zf.infolist()
    except zipfile.BadZipFile as e:
        raise UploadRejected("File is not a valid .docx document.") from e

    if len(infos) > ZIP_MAX_ENTRIES:
        raise UploadRejected("Document contains too many internal parts to process safely.")

    total_uncompressed = 0
    for info in infos:
        total_uncompressed += info.file_size
        if info.compress_size > 0 and (info.file_size / info.compress_size) > ZIP_MAX_COMPRESSION_RATIO:
            raise UploadRejected("Document failed a safety check (abnormal compression ratio).")
        if total_uncompressed > ZIP_MAX_UNCOMPRESSED_TOTAL_BYTES:
            raise UploadRejected("Document is too large once decompressed to process safely.")


# --- PDF-bomb protection ---

PDF_MAX_PAGES = 2_000
PDF_MAX_EXTRACTED_TEXT_CHARS = 20_000_000  # ~20MB of text; no real contract approaches this


def validate_pdf_page_count(page_count: int) -> None:
    if page_count > PDF_MAX_PAGES:
        raise UploadRejected(f"PDF has too many pages ({page_count}) to process safely.")


def enforce_extracted_text_limit(text: str) -> str:
    if len(text) > PDF_MAX_EXTRACTED_TEXT_CHARS:
        raise UploadRejected("Document content is too large to process safely.")
    return text


# --- Malware scanning interface ---
#
# Pluggable so a real scanner can be wired in per deployment without
# touching call sites. No scanner ships enabled by default — running one
# (e.g. ClamAV) is an infrastructure decision or the deploying
# organization's, and this module cannot make it for them. See
# docs/security/upload_hardening_infra.md for setup.

@dataclass
class ScanResult:
    clean: bool
    reason: Optional[str] = None


class MalwareScanner:
    def scan(self, file_bytes: bytes) -> ScanResult:
        raise NotImplementedError


class NoopMalwareScanner(MalwareScanner):
    """Default when MALWARE_SCANNER is unset. Always reports clean, but
    logs a warning once per process so operators see in their logs that
    uploads aren't actually being scanned, rather than silently assuming
    they are."""

    _warned = False

    def scan(self, file_bytes: bytes) -> ScanResult:
        if not NoopMalwareScanner._warned:
            logger.warning(
                "No malware scanner configured (MALWARE_SCANNER unset) — "
                "uploaded files are not being scanned for malware."
            )
            NoopMalwareScanner._warned = True
        return ScanResult(clean=True)


class ClamdMalwareScanner(MalwareScanner):
    """Real scanning via a ClamAV daemon (clamd), used when
    MALWARE_SCANNER=clamd. Requires the `clamd` package and a reachable
    clamd instance — see docs/security/upload_hardening_infra.md."""

    def __init__(self, host: str, port: int):
        import clamd  # optional dependency — only imported if this backend is selected
        self._client = clamd.ClamdNetworkSocket(host=host, port=port)
        self._client.ping()

    def scan(self, file_bytes: bytes) -> ScanResult:
        result = self._client.instream(io.BytesIO(file_bytes))
        status, reason = result.get("stream", ("ERROR", "no result returned"))
        if status == "FOUND":
            return ScanResult(clean=False, reason=reason)
        if status == "OK":
            return ScanResult(clean=True)
        raise UploadRejected(f"Malware scan could not complete: {reason}")


_scanner: Optional[MalwareScanner] = None


def get_malware_scanner() -> MalwareScanner:
    global _scanner
    if _scanner is not None:
        return _scanner

    backend = os.getenv("MALWARE_SCANNER", "").strip().lower()
    if backend == "clamd":
        host = os.getenv("CLAMD_HOST", "localhost")
        port = int(os.getenv("CLAMD_PORT", "3310"))
        try:
            _scanner = ClamdMalwareScanner(host, port)
            logger.info(f"Malware scanning enabled via clamd at {host}:{port}")
        except Exception as e:
            logger.error(
                f"Failed to initialize clamd malware scanner ({e}); "
                "falling back to no-op scanner — uploads will NOT be scanned"
            )
            _scanner = NoopMalwareScanner()
    else:
        _scanner = NoopMalwareScanner()
    return _scanner


def reset_malware_scanner_cache() -> None:
    """Test hook: forces the next get_malware_scanner() call to re-read
    MALWARE_SCANNER/CLAMD_HOST/CLAMD_PORT instead of reusing the cached
    instance from a previous configuration."""
    global _scanner
    _scanner = None


def scan_for_malware(file_bytes: bytes) -> None:
    result = get_malware_scanner().scan(file_bytes)
    if not result.clean:
        logger.warning(f"Malware scan rejected an upload: {result.reason}")
        raise UploadRejected(f"File failed a malware scan: {result.reason or 'threat detected'}")
