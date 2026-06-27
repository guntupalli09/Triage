"""Upload receive, file validation, text extraction logging."""
from __future__ import annotations

from triage_logging import get_logger

logger = get_logger(__name__)


def log_file_received(filename: str, size_bytes: int) -> None:
    size_kb = size_bytes / 1024
    if size_kb > 1024:
        size_str = f"{size_kb / 1024:.1f} MB"
    else:
        size_str = f"{size_kb:.0f} KB"
    logger.upload(f"File received: {filename} ({size_str})")


def log_file_validated(filename: str, file_type: str) -> None:
    logger.upload(f"Validated: {filename} (type: {file_type})")


def log_text_extracted(char_count: int) -> None:
    logger.parser(f"Text extracted ({char_count:,} chars)")


def log_file_rejected(filename: str, reason: str) -> None:
    logger.warning(f"File rejected: {filename} — {reason}")
