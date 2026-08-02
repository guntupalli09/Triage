"""
Configuration and path layout for TriageBench Live.

Deliberately separate from triagebench/config.py: this suite targets a
*deployed* application (BASE_URL), not the local corpus/engine, and its run
history lives in its own directory so a live production run is never
confused with (or diffed against) an in-process engine benchmark run.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_ROOT = REPO_ROOT / "triagebench_live_runs"
LATEST_POINTER = RUNS_ROOT / "LATEST_RUN.json"

DEFAULT_BASE_URL = os.getenv("TRIAGEBENCH_LIVE_BASE_URL", "http://127.0.0.1:8000")

# A real customer's browser waits for these; we do too, with a ceiling so a
# hung backend fails the check instead of hanging the whole suite forever.
DEFAULT_HTTP_TIMEOUT_S = 60
ANALYSIS_TIMEOUT_S = 90  # upload's response IS the completed analysis (synchronous) — see workflow.py

CATEGORIES = ["Employement", "Purchases", "Lease", "Services"]


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_dir(run_id: str) -> Path:
    return RUNS_ROOT / run_id


@dataclass
class LiveConfig:
    run_id: str = field(default_factory=new_run_id)
    base_url: str = DEFAULT_BASE_URL
    workers: int = 4
    limit: Optional[int] = None
    per_category_limit: Optional[int] = 5
    categories: List[str] = field(default_factory=lambda: list(CATEGORIES))
    seed: int = 20260101
    resume: bool = False
    label: Optional[str] = None
    run_security: bool = True
    run_failure_tests: bool = True
    run_concurrency: bool = True
    run_browser: bool = True
    run_db_lifecycle_proof: bool = True
    browsers: List[str] = field(default_factory=lambda: ["chromium", "firefox", "webkit", "msedge"])
    timeout_s: int = DEFAULT_HTTP_TIMEOUT_S
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None

    @property
    def out_dir(self) -> Path:
        return run_dir(self.run_id)
