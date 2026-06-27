"""Evidence excerpt indexing logging."""
from __future__ import annotations

from triage_logging import get_logger

logger = get_logger(__name__)


def log_evidence_indexed(finding_count: int) -> None:
    logger.verify(f"Evidence indexed: {finding_count} findings with anchored excerpts")
