"""Document parsing and clause segmentation logging."""
from __future__ import annotations

from triage_logging import get_logger

logger = get_logger(__name__)


def log_clauses_detected(count: int) -> None:
    logger.parser(f"{count} clauses detected")


def log_parse_error(filename: str, error: str) -> None:
    logger.error(f"Parse error for {filename}: {error}")
