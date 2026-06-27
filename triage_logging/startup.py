"""Server startup diagnostics banner."""
from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys
import time
from typing import Optional

from triage_logging import get_logger

logger = get_logger(__name__)


def _get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).decode().strip()
    except Exception:
        return "unknown"


def _pkg_version(pkg: str) -> str:
    try:
        return importlib.metadata.version(pkg)
    except Exception:
        return "N/A"


def _check_postgres(database_url: str) -> str:
    if "sqlite" in database_url:
        return "SQLite (dev mode)"
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url, pool_pre_ping=True)
        start = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ms = int((time.perf_counter() - start) * 1000)
        engine.dispose()
        return f"Connected ({ms}ms)"
    except Exception as e:
        return f"FAILED: {e}"


def _check_redis(redis_url: Optional[str]) -> str:
    if not redis_url:
        return "Not configured"
    try:
        import redis as r
        start = time.perf_counter()
        client = r.from_url(redis_url, socket_connect_timeout=3)
        client.ping()
        ms = int((time.perf_counter() - start) * 1000)
        client.close()
        return f"Connected ({ms}ms)"
    except Exception as e:
        return f"FAILED: {e}"


def _check_openai() -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return "Not configured"
    return "Configured"


def print_startup_banner(
    workers: int = 1,
    rule_count: int = 0,
    playbook_count: int = 0,
    environment: str = "Development",
    database_url: str = "",
    redis_url: Optional[str] = None,
) -> None:
    line = "═" * 62
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    fastapi_ver = _pkg_version("fastapi")
    pg_status = _check_postgres(database_url)
    redis_status = _check_redis(redis_url)
    openai_status = _check_openai()
    git_commit = _get_git_commit()

    banner = f"""
{line}
  TRIAGE DETERMINISTIC ENGINE v2.0.0
{line}
Python................{py_ver}
FastAPI...............{fastapi_ver}
Workers...............{workers}
PostgreSQL............{pg_status}
Redis.................{redis_status}
OpenAI................{openai_status}
Rule Library..........{rule_count} rules
Playbooks.............{playbook_count}
Environment...........{environment}
Git Commit............{git_commit}
{line}
"""
    for ln in banner.strip().split("\n"):
        logger.info(ln)
