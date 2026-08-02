"""
The orchestrator: turns a BenchmarkConfig + a corpus selection into a
completed run on disk.

Fault tolerance, concretely: `_worker` is the single point where a contract
is processed, and it is wrapped in a bare except so that literally nothing —
not an engine bug, not a corrupt source file, not an out-of-memory regex
blowup — can take down the run. A worker-process crash (e.g. a segfault in a
C extension) is handled one level up, by ProcessPoolExecutor surfacing a
BrokenProcessPool; the runner catches that too and restarts a fresh pool for
the remaining contracts rather than losing the whole run.

Resumability, concretely: results are appended to results.jsonl as each
contract finishes (storage.append_result), not batched in memory and written
once at the end. `--resume <run_id>` re-reads that file, computes the set of
already-completed contract_ids, and only schedules what's left. This means
killing the process (or the machine) at any point loses at most the handful
of contracts that were in flight, never the whole run.
"""
from __future__ import annotations

import json
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from typing import List, Optional

from . import config as cfg
from . import corpus
from . import storage
from .pipeline import run_contract


def _worker(ref: corpus.ContractRef) -> dict:
    try:
        return run_contract(ref).as_dict()
    except Exception as exc:  # noqa: BLE001 — absolute last line of defense
        return {
            "contract_id": ref.contract_id,
            "category": ref.category,
            "company_name": ref.company_name,
            "form_type": ref.form_type,
            "date_filed": ref.date_filed,
            "filename": ref.filename,
            "archive_name": ref.archive_name,
            "source_format": "",
            "stages": {},
            "metrics": {},
            "rule_ids_fired": [],
            "overall_status": "error",
            "failures": [f"worker_crash: {type(exc).__name__}: {exc}"],
        }


def _git_info() -> tuple[Optional[str], Optional[str]]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=cfg.REPO_ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cfg.REPO_ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
        return commit, branch
    except Exception:
        return None, None


def run(config: cfg.BenchmarkConfig) -> str:
    """Executes (or resumes) a benchmark run and returns its run_id.
    Reports/dashboards/regression are NOT generated here — call
    `finalize(run_id)` afterward (kept separate so a resumed run doesn't
    regenerate reports until the corpus pass is actually complete, and so
    reports can be regenerated standalone from an already-completed run)."""
    run_id = config.run_id
    storage.ensure_run_dir(run_id)

    all_refs = corpus.discover(config.categories)
    selected = corpus.select(
        all_refs, limit=config.limit, per_category_limit=config.per_category_limit, seed=config.seed
    )

    if config.git_commit is None or config.git_branch is None:
        commit, branch = _git_info()
        config.git_commit = config.git_commit or commit
        config.git_branch = config.git_branch or branch

    manifest_path = cfg.run_dir(run_id) / "benchmark_manifest.json"
    if config.resume and manifest_path.exists():
        manifest = storage.read_manifest(run_id)
    else:
        manifest = {
            "run_id": run_id,
            "label": config.label,
            "git_commit": config.git_commit,
            "git_branch": config.git_branch,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "workers": config.workers,
            "seed": config.seed,
            "categories": config.categories,
            "limit": config.limit,
            "per_category_limit": config.per_category_limit,
            "corpus_total_discovered": len(all_refs),
            "corpus_selected": len(selected),
            "corpus_by_category": {
                cat: sum(1 for r in all_refs if r.category_dir == cat) for cat in config.categories
            },
            "selected_contract_ids": [r.contract_id for r in selected],
            "status": "running",
        }
        storage.write_manifest(run_id, manifest)

    completed_ids = storage.read_completed_ids(run_id) if config.resume else set()
    pending = [r for r in selected if r.contract_id not in completed_ids]

    print(
        f"[triagebench] run_id={run_id} selected={len(selected)} "
        f"already_done={len(completed_ids)} pending={len(pending)} workers={config.workers}"
    )

    t0 = time.time()
    processed = 0
    while pending:
        try:
            with ProcessPoolExecutor(max_workers=config.workers) as pool:
                futures = {pool.submit(_worker, ref): ref for ref in pending}
                remaining_after_crash = []
                for fut in as_completed(futures):
                    ref = futures[fut]
                    try:
                        record = fut.result()
                    except BrokenProcessPool:
                        remaining_after_crash.append(ref)
                        continue
                    storage.append_result(run_id, record)
                    processed += 1
                    if processed % 50 == 0 or processed == len(pending):
                        elapsed = time.time() - t0
                        print(f"[triagebench] {processed}/{len(pending)} done ({elapsed:.1f}s elapsed)")
                pending = remaining_after_crash
        except BrokenProcessPool:
            # The pool itself died before any future could be dispatched
            # (e.g. immediate OOM). Recompute pending from what's actually
            # on disk and retry with a fresh pool rather than losing the run.
            completed_ids = storage.read_completed_ids(run_id)
            pending = [r for r in selected if r.contract_id not in completed_ids]
            print(f"[triagebench] process pool crashed; restarting with {len(pending)} contracts remaining")
            continue

    manifest["status"] = "completed"
    manifest["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest["duration_seconds"] = round(time.time() - t0, 2)
    storage.write_manifest(run_id, manifest)
    return run_id
