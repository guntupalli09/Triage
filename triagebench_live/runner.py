"""
Orchestrator: turns a LiveConfig into a completed production run on disk.

Concurrency model: contract workflows run in a ThreadPoolExecutor, not a
process pool — every step here is I/O-bound (waiting on the network), so
threads are the right tool (unlike triagebench/runner.py's CPU-bound regex
work, which genuinely needs process-level parallelism). `--workers` also
directly controls how much simultaneous load this suite puts on the target
server; see README.md for why the default is deliberately conservative (a
real, reproducible connection-pool exhaustion bug was found in this exact
codebase during development of this suite — hammering a target with high
concurrency is itself an adversarial act this framework should perform
deliberately, at a controlled level, not accidentally at an uncontrolled
one).

Resumability mirrors triagebench/runner.py: contract results append to
`contract_results.jsonl` as each finishes; `--resume` reads what's already
there and only schedules what's left.
"""
from __future__ import annotations

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from . import concurrency as concurrency_mod
from . import config as cfg
from . import corpus_source
from . import failure_tests as failure_mod
from . import security as security_mod
from . import storage
from .browser import run_browser_suite
from .workflow import run_contract_workflow


def _git_info():
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


def _worker(base_url: str, payload, timeout_s: int) -> dict:
    try:
        return run_contract_workflow(base_url, payload, timeout_s=timeout_s).as_dict()
    except Exception as exc:  # noqa: BLE001 — absolute last line of defense
        return {
            "contract_id_hint": payload.contract_id_hint, "category": payload.category,
            "company_name": payload.company_name, "filename": payload.filename, "test_email": "",
            "live_contract_id": None, "steps": {}, "metrics": {}, "overall_status": "error",
            "failures": [f"worker_crash: {type(exc).__name__}: {exc}"],
        }


def run(config: cfg.LiveConfig) -> str:
    run_id = config.run_id
    storage.ensure_run_dir(run_id)

    payloads = corpus_source.discover_payloads(
        categories=config.categories, limit=config.limit,
        per_category_limit=config.per_category_limit, seed=config.seed,
    )

    if config.git_commit is None or config.git_branch is None:
        commit, branch = _git_info()
        config.git_commit = config.git_commit or commit
        config.git_branch = config.git_branch or branch

    manifest_path = cfg.run_dir(run_id) / "production_manifest.json"
    if config.resume and manifest_path.exists():
        manifest = storage.read_manifest(run_id)
    else:
        manifest = {
            "run_id": run_id, "label": config.label, "base_url": config.base_url,
            "git_commit": config.git_commit, "git_branch": config.git_branch,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "workers": config.workers, "seed": config.seed, "categories": config.categories,
            "limit": config.limit, "per_category_limit": config.per_category_limit,
            "contracts_selected": len(payloads),
            "run_security": config.run_security, "run_failure_tests": config.run_failure_tests,
            "run_concurrency": config.run_concurrency, "run_browser": config.run_browser,
            "status": "running",
        }
        storage.write_manifest(run_id, manifest)

    completed_ids = storage.read_completed_ids(run_id) if config.resume else set()
    pending = [p for p in payloads if p.contract_id_hint not in completed_ids]

    print(f"[triagebench-live] run_id={run_id} target={config.base_url} "
          f"selected={len(payloads)} already_done={len(completed_ids)} pending={len(pending)} "
          f"workers={config.workers}")

    t0 = time.time()
    processed = 0
    with ThreadPoolExecutor(max_workers=config.workers) as pool:
        futures = {pool.submit(_worker, config.base_url, p, config.timeout_s): p for p in pending}
        for fut in as_completed(futures):
            record = fut.result()  # _worker never raises — see its own try/except
            storage.append_contract_result(run_id, record)
            processed += 1
            if processed % 5 == 0 or processed == len(pending):
                print(f"[triagebench-live] {processed}/{len(pending)} contracts done ({time.time() - t0:.1f}s elapsed)")

    # Suites that exercise the app but aren't per-contract: security,
    # adversarial failure injection, concurrency, and (optionally, since it
    # is the slowest by far) real-browser validation. Each is wrapped
    # independently — the same fault-isolation principle as the per-contract
    # loop above applies here too: a suite that can't complete (e.g. the
    # target server degraded enough mid-run to stop responding, exactly what
    # happened during this suite's own development — see README) is recorded
    # as a suite-level failure, not a reason to abandon the whole run and
    # every result already collected.
    suite_errors: List[str] = []

    def _run_suite(name: str, enabled: bool, fn):
        if not enabled:
            return []
        print(f"[triagebench-live] running {name} suite...")
        try:
            return [item.as_dict() for item in fn()]
        except Exception as exc:  # noqa: BLE001
            msg = f"{name} suite could not complete: {type(exc).__name__}: {exc}"
            print(f"[triagebench-live] WARNING: {msg}")
            suite_errors.append(msg)
            return [{
                "check": f"{name}_suite_incomplete", "name": f"{name}_suite_incomplete",
                "passed": False, "severity": "critical", "detail": msg,
            }]

    security_findings = _run_suite("security", config.run_security,
                                    lambda: security_mod.run_security_suite(config.base_url, config.timeout_s))
    storage.write_json(run_id, "security_results.json", security_findings)

    failure_results = _run_suite("failure-injection", config.run_failure_tests,
                                  lambda: failure_mod.run_failure_suite(config.base_url, config.timeout_s))
    storage.write_json(run_id, "failure_results.json", failure_results)

    concurrency_results = _run_suite("concurrency", config.run_concurrency,
                                      lambda: concurrency_mod.run_concurrency_suite(config.base_url, config.timeout_s))
    storage.write_json(run_id, "concurrency_results.json", concurrency_results)

    browser_results = []
    if config.run_browser:
        print(f"[triagebench-live] running browser suite ({config.browsers})...")
        try:
            browser_results = [b.as_dict() for b in run_browser_suite(config.base_url, config.browsers, config.timeout_s)]
        except Exception as exc:  # noqa: BLE001
            msg = f"browser suite could not complete: {type(exc).__name__}: {exc}"
            print(f"[triagebench-live] WARNING: {msg}")
            suite_errors.append(msg)
    storage.write_json(run_id, "browser_results.json", browser_results)

    if suite_errors:
        manifest["suite_errors"] = suite_errors

    manifest["status"] = "completed"
    manifest["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest["duration_seconds"] = round(time.time() - t0, 2)
    storage.write_manifest(run_id, manifest)
    return run_id
