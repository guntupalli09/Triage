"""
Run storage: everything about how one benchmark run is persisted to disk.

Layout, under triagebench_runs/<RUN_ID>/:

  manifest.json            — what this run is: config, corpus digest, contract list
  results.jsonl            — one line per completed contract, appended as it
                              finishes (never rewritten) — this is what makes
                              a run resumable and crash-safe: a killed process
                              loses at most the one contract mid-flight, and
                              restarting with --resume re-reads this file to
                              know what's already done
  benchmark_results.json   — results.jsonl materialized into a single JSON
                              array, written once at finalize
  benchmark_summary.json   — aggregate statistics over the whole run
  reports/*.csv            — the eleven CSV reports
  dashboards/*.html        — the seven HTML dashboards

triagebench_runs/LATEST_RUN.json is a pointer updated only when a run
finishes successfully — regression detection reads it to find the baseline
to diff against, and a run that crashed mid-way is never mistaken for a
valid baseline because it never gets pointed to.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from . import config


def ensure_run_dir(run_id: str) -> Path:
    d = config.run_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "reports").mkdir(exist_ok=True)
    (d / "dashboards").mkdir(exist_ok=True)
    return d


def write_manifest(run_id: str, manifest: Dict[str, Any]) -> None:
    path = config.run_dir(run_id) / "benchmark_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")


def read_manifest(run_id: str) -> Dict[str, Any]:
    path = config.run_dir(run_id) / "benchmark_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def results_jsonl_path(run_id: str) -> Path:
    return config.run_dir(run_id) / "results.jsonl"


def append_result(run_id: str, record: Dict[str, Any]) -> None:
    path = results_jsonl_path(run_id)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str))
        f.write("\n")


def read_completed_ids(run_id: str) -> set:
    path = results_jsonl_path(run_id)
    if not path.exists():
        return set()
    ids = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["contract_id"])
            except (json.JSONDecodeError, KeyError):
                continue  # a torn last line from a crash mid-write — skip it, it'll rerun
    return ids


def iter_results(run_id: str) -> Iterator[Dict[str, Any]]:
    path = results_jsonl_path(run_id)
    if not path.exists():
        return
    seen = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = rec.get("contract_id")
            if cid in seen:
                continue  # resumed runs may reprocess a contract that was
                # mid-write when a previous attempt crashed — last full
                # write for a given id would already be `seen` as first
                # occurrence here since jsonl is append-only in id order
                # of completion; de-dupe defensively regardless
            seen.add(cid)
            yield rec


def load_results(run_id: str) -> List[Dict[str, Any]]:
    return list(iter_results(run_id))


def write_json(run_id: str, filename: str, payload: Any) -> None:
    path = config.run_dir(run_id) / filename
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def load_json(run_id: str, filename: str) -> Any:
    path = config.run_dir(run_id) / filename
    return json.loads(path.read_text(encoding="utf-8"))


def set_latest(run_id: str) -> None:
    config.RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    config.LATEST_POINTER.write_text(
        json.dumps({"run_id": run_id, "path": str(config.run_dir(run_id))}, indent=2), encoding="utf-8"
    )


def get_latest_run_id(exclude: Optional[str] = None) -> Optional[str]:
    if not config.LATEST_POINTER.exists():
        return None
    data = json.loads(config.LATEST_POINTER.read_text(encoding="utf-8"))
    run_id = data.get("run_id")
    if run_id == exclude:
        return None
    return run_id


def list_run_ids() -> List[str]:
    if not config.RUNS_ROOT.exists():
        return []
    return sorted(
        p.name for p in config.RUNS_ROOT.iterdir()
        if p.is_dir() and (p / "benchmark_manifest.json").exists()
    )
