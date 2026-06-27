"""Suppression engine check logging."""
from __future__ import annotations

from triage_logging import get_logger

logger = get_logger(__name__)


def log_suppression_check(rule_id: str, result: str) -> None:
    logger.suppress(f"{rule_id}: {result}")
