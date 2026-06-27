"""Per-category rule execution, slow rule detection logging."""
from __future__ import annotations

from typing import Dict, List

from triage_logging import get_logger

logger = get_logger(__name__)

SLOW_THRESHOLD_MS = 50


def log_rule_categories(categories: Dict[str, int]) -> None:
    line = "─" * 36
    logger.engine(line)
    logger.engine("Rule Categories")
    logger.engine(line)
    for cat, count in sorted(categories.items()):
        dots = "." * max(1, 28 - len(cat))
        logger.engine(f"{cat}{dots}{count} rules")
    logger.engine(line)
    total = sum(categories.values())
    logger.engine(f"Total Loaded          {total} Rules")


def log_rule_result(rule_id: str, elapsed_ms: float, triggered: bool) -> None:
    status = "MATCH" if triggered else "PASS"
    slow = "  ⚠ SLOW" if elapsed_ms > SLOW_THRESHOLD_MS else ""
    if triggered:
        logger.match(f"{rule_id:<20} {elapsed_ms:.0f}ms{slow}")
    else:
        logger.rule(f"{rule_id:<20} {elapsed_ms:.0f}ms{slow}")


def log_rule_match(rule_id: str, excerpt: str) -> None:
    short = excerpt[:80].replace("\n", " ")
    logger.match(f'{rule_id} Triggered — "{short}"')


def log_suppression_result(rule_id: str, suppressed: bool, reason: str = "") -> None:
    if suppressed:
        logger.suppress(f"{rule_id}: Suppressed — {reason}")
    else:
        logger.suppress(f"{rule_id}: No suppression matched")
