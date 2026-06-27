"""Report generation and DB save logging."""
from __future__ import annotations

from triage_logging import get_logger

logger = get_logger(__name__)


def log_contract_saved(contract_id: int) -> None:
    logger.database(f"Contract saved (ID: {contract_id})")


def log_report_generated(contract_id: int, overall_risk: str, finding_count: int) -> None:
    logger.success(f"Report generated — ID: {contract_id}, Risk: {overall_risk}, Findings: {finding_count}")
