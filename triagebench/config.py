"""
Central configuration and path layout for TriageBench.

Everything the framework reads or writes lives under two roots:

  Benchmark - TC/          — the fixed input corpus (never written to)
  triagebench_runs/        — every run's output, kept forever (append-only
                              history is what makes regression detection
                              possible; nothing here is ever deleted by the
                              framework itself)

A run is identified by RUN_ID, a sortable timestamp-based string, so runs
naturally order chronologically on disk without reading their contents.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_ROOT = REPO_ROOT / "Benchmark - TC"
RUNS_ROOT = REPO_ROOT / "triagebench_runs"
LATEST_POINTER = RUNS_ROOT / "LATEST_RUN.json"

CATEGORIES = ["Employement", "Purchases", "Lease", "Services"]

# Category folder names are the corpus's own (one is a typo upstream —
# "Employement" — preserved verbatim so paths keep matching the source
# archive; the *reported* category label is normalized separately).
CATEGORY_LABELS = {
    "Employement": "Employment",
    "Purchases": "Purchases",
    "Lease": "Lease",
    "Services": "Services",
}


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_dir(run_id: str) -> Path:
    return RUNS_ROOT / run_id


@dataclass
class BenchmarkConfig:
    run_id: str = field(default_factory=new_run_id)
    workers: int = max(1, (os.cpu_count() or 2) - 1)
    limit: Optional[int] = None
    per_category_limit: Optional[int] = None
    categories: List[str] = field(default_factory=lambda: list(CATEGORIES))
    seed: int = 20260101  # fixed default: sampling is deterministic by default
    resume: bool = False
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    label: Optional[str] = None  # free-text run label (e.g. "pre-release", "nightly")

    @property
    def out_dir(self) -> Path:
        return run_dir(self.run_id)
