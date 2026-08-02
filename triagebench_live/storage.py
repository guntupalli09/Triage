"""
Run storage for TriageBench Live — same append-only, resumable pattern as
triagebench/storage.py (results.jsonl written incrementally, a run is only
ever pointed to as a regression baseline once it finishes), kept as an
independent module/namespace so a live-app run is never confused with an
in-process engine benchmark run.
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
    return d


def write_manifest(run_id: str, manifest: Dict[str, Any]) -> None:
    (config.run_dir(run_id) / "production_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )


def read_manifest(run_id: str) -> Dict[str, Any]:
    return json.loads((config.run_dir(run_id) / "production_manifest.json").read_text(encoding="utf-8"))


def contract_results_path(run_id: str) -> Path:
    return config.run_dir(run_id) / "contract_results.jsonl"


def append_contract_result(run_id: str, record: Dict[str, Any]) -> None:
    with contract_results_path(run_id).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str))
        f.write("\n")


def read_completed_ids(run_id: str) -> set:
    path = contract_results_path(run_id)
    if not path.exists():
        return set()
    ids = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["contract_id_hint"])
            except (json.JSONDecodeError, KeyError):
                continue
    return ids


def iter_contract_results(run_id: str) -> Iterator[Dict[str, Any]]:
    path = contract_results_path(run_id)
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
            cid = rec.get("contract_id_hint")
            if cid in seen:
                continue
            seen.add(cid)
            yield rec


def load_contract_results(run_id: str) -> List[Dict[str, Any]]:
    return list(iter_contract_results(run_id))


def write_json(run_id: str, filename: str, payload: Any) -> None:
    (config.run_dir(run_id) / filename).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def load_json(run_id: str, filename: str) -> Any:
    return json.loads((config.run_dir(run_id) / filename).read_text(encoding="utf-8"))


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
    return None if run_id == exclude else run_id


def list_run_ids() -> List[str]:
    if not config.RUNS_ROOT.exists():
        return []
    return sorted(
        p.name for p in config.RUNS_ROOT.iterdir()
        if p.is_dir() and (p / "production_manifest.json").exists()
    )
