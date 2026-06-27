"""Cross-clause validation logging."""
from __future__ import annotations

from triage_logging import get_logger

logger = get_logger(__name__)


def log_consistency_check(check_name: str, passed: bool) -> None:
    status = "PASS" if passed else "FAIL"
    logger.verify(f"Consistency: {check_name} — {status}")
