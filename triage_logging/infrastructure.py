"""Redis, PostgreSQL, worker pool event logging."""
from __future__ import annotations

from typing import Dict, Optional

from triage_logging import get_logger

logger = get_logger(__name__)


def log_worker_processing(worker_id: str, job_id: int) -> None:
    logger.engine(f"[{worker_id}] Processing Job #{job_id}")


def log_redis_event(action: str, key: str = "") -> None:
    detail = f" ({key})" if key else ""
    logger.cache(f"Redis: {action}{detail}")


def log_postgres_event(action: str, detail: str = "") -> None:
    extra = f" ({detail})" if detail else ""
    logger.database(f"Postgres: {action}{extra}")


def log_audit_event(action: str) -> None:
    logger.audit(f"Audit: {action}")


def log_latency_warning(service: str, latency_s: float, threshold_s: float) -> None:
    logger.warning(f"{service} latency > {threshold_s}s ({latency_s:.1f}s)")


def log_performance_summary(stages: Dict[str, int]) -> None:
    line = "─" * 36
    logger.engine(line)
    logger.engine("Performance")
    logger.engine(line)
    total = 0
    for stage, ms in stages.items():
        dots = "." * max(1, 28 - len(stage))
        logger.engine(f"{stage}{dots}{ms} ms")
        total += ms
    logger.engine(line)
    logger.engine(f"Total                   {total} ms")


def log_memory_usage(before_mb: float, after_mb: float, peak_mb: float) -> None:
    logger.info(f"Memory Before Analysis      {before_mb:.0f} MB")
    logger.info(f"Memory After Analysis       {after_mb:.0f} MB")
    logger.info(f"Peak                        {peak_mb:.0f} MB")


def log_job_completion(
    analysis_id: str,
    execution_time_s: float,
    rules_loaded: int,
    rules_executed: int,
    rules_triggered: int,
    rules_suppressed: int,
    errors: int,
    warnings: int,
    memory_before_mb: Optional[float] = None,
    memory_after_mb: Optional[float] = None,
    memory_peak_mb: Optional[float] = None,
) -> None:
    line = "═" * 62
    logger.success(line)
    logger.success(f"  COMPLETED — {analysis_id}")
    logger.success(f"  Execution Time: {execution_time_s:.2f} sec")
    logger.success(
        f"  Rules Loaded: {rules_loaded}  |  Executed: {rules_executed}  |  "
        f"Triggered: {rules_triggered}  |  Suppressed: {rules_suppressed}"
    )
    logger.success(f"  Errors: {errors}  |  Warnings: {warnings}")
    if memory_before_mb is not None:
        logger.success(
            f"  Memory: {memory_before_mb:.0f} MB → {memory_after_mb:.0f} MB "
            f"(peak {memory_peak_mb:.0f} MB)"
        )
    logger.success(line)
