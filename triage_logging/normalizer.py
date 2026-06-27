"""Text normalization logging."""
from __future__ import annotations

from triage_logging import get_logger

logger = get_logger(__name__)


def log_normalization(original_len: int, normalized_len: int) -> None:
    logger.info(f"Normalized text: {original_len:,} → {normalized_len:,} chars")
