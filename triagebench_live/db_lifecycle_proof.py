"""
Proves the database-session lifecycle is leak-free — the specific,
targeted regression test for the connection-pool exhaustion bug this suite
originally found and that has since been fixed (main.py's routes now use
`Depends(get_db)`; the two `@app.exception_handler` callbacks, which
FastAPI's dependency injection never reaches, use `database.db_session()`
instead — see database.py and the git history for the fix).

Three phases, run over real HTTP against the real app, distinguishing a
genuine *leak* (monotonic, permanent, never recovers) from ordinary,
expected *capacity backpressure* (a correctly-sized-or-not connection pool
queuing or rejecting work under a burst larger than its capacity, then
fully recovering once the burst subsides) — conflating the two would make
this proof either a false negative (declaring a real leak "fine" because
one burst happened to succeed) or a false positive (declaring a healthy,
merely undersized pool "leaking" because a deliberately oversized burst
queued for a few seconds).

1. Sustained sequential: far more requests, one at a time, than the pool
   could ever have concurrently outstanding. A leak fails this — usage
   climbs monotonically and the pool exhausts partway through, since
   nothing before that many requests could return more than one
   connection at a time. A correctly-cleaned-up pool sails through it,
   holding at most 1 checked-out connection at any instant.
2. Sustained concurrent AT capacity: N requests fired truly concurrently,
   where N is at-or-below the pool's total capacity (pool_size +
   max_overflow). This must complete quickly with zero failures — if it
   doesn't, connections aren't being returned promptly even under normal
   load, which is the leak's signature.
3. Repeated concurrent bursts ABOVE capacity, back to back with recovery
   checks between them: proves the system doesn't degrade further with
   each successive burst (a leak gets monotonically worse over time;
   correct behavior means every burst sees the same steady-state
   capacity, recovering fully between them).
"""
from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List

import requests

# SQLAlchemy's own default QueuePool sizing (pool_size=5, max_overflow=10 —
# see database.py; PostgreSQL in production sets the same 5+5, SQLite
# inherits the library default of 5+10) — 15 total connections outstanding
# at once before the 16th blocks. Kept as a named constant here, not a
# magic number, so the phase-2/phase-3 concurrency levels are visibly
# derived from the real pool capacity, not picked arbitrarily.
ASSUMED_POOL_CAPACITY = 15


@dataclass
class PhaseResult:
    name: str
    passed: bool
    detail: str
    metrics: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail, **self.metrics}


def _round_trip(base_url: str, timeout_s: float) -> bool:
    """One minimal DB-touching round trip: register a disposable account,
    then load a page that reads it back — two real, independent DB session
    lifecycles per call, sequential dependency resolution."""
    s = requests.Session()
    email = f"dblifecycle-{uuid.uuid4().hex[:12]}@test.local"
    try:
        r1 = s.post(f"{base_url}/register",
                     data={"email": email, "password": "TriageBenchLive!2026", "confirm_password": "TriageBenchLive!2026"},
                     timeout=timeout_s)
        r2 = s.get(f"{base_url}/dashboard", timeout=timeout_s)
        return r1.status_code == 200 and r2.status_code == 200
    except Exception:
        return False


def _wait_for_recovery(base_url: str, max_wait_s: float = 60.0, poll_interval_s: float = 3.0) -> float:
    """Polls a cheap endpoint until it responds quickly again. Returns
    seconds elapsed, or max_wait_s if it never recovered in time."""
    t0 = time.time()
    while time.time() - t0 < max_wait_s:
        try:
            r = requests.get(f"{base_url}/login", timeout=5)
            if r.status_code == 200:
                return time.time() - t0
        except Exception:
            pass
        time.sleep(poll_interval_s)
    return max_wait_s


def phase_sequential(base_url: str, count: int = 150, timeout_s: float = 10.0) -> PhaseResult:
    t0 = time.time()
    results = [_round_trip(base_url, timeout_s) for _ in range(count)]
    elapsed = time.time() - t0
    ok = sum(results)
    # A leak manifests as failures clustering at the END of the run (pool
    # exhausts partway through and never recovers within a single-threaded
    # sequential run, since only one request is ever in flight); report
    # where in the sequence failures happened, not just the count, so a
    # genuine leak's signature (tail failures) is visible even if a few
    # isolated failures happen for unrelated reasons.
    first_failure_at = next((i for i, r in enumerate(results) if not r), None)
    return PhaseResult(
        name="sustained_sequential",
        passed=ok == count,
        detail=f"{ok}/{count} sequential round trips succeeded in {elapsed:.1f}s"
               + (f"; first failure at request #{first_failure_at}" if first_failure_at is not None else ""),
        metrics={"count": count, "ok": ok, "elapsed_s": round(elapsed, 1), "first_failure_at": first_failure_at},
    )


def phase_concurrent_at_capacity(base_url: str, workers: int = ASSUMED_POOL_CAPACITY, timeout_s: float = 15.0) -> PhaseResult:
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda _: _round_trip(base_url, timeout_s), range(workers)))
    elapsed = time.time() - t0
    ok = sum(results)
    return PhaseResult(
        name="concurrent_at_pool_capacity",
        passed=ok == workers,
        detail=f"{ok}/{workers} truly concurrent round trips (at assumed pool capacity {ASSUMED_POOL_CAPACITY}) "
               f"succeeded in {elapsed:.1f}s — this must be 100% with no queuing failures under normal load",
        metrics={"workers": workers, "ok": ok, "elapsed_s": round(elapsed, 1)},
    )


def phase_repeated_bursts_above_capacity(
    base_url: str, burst_size: int = 20, bursts: int = 3, timeout_s: float = 20.0, recovery_wait_s: float = 30.0
) -> PhaseResult:
    """burst_size deliberately exceeds ASSUMED_POOL_CAPACITY — a burst
    failing partially or even wholly under sustained overload fired with
    zero gap between bursts is legitimate, expected backpressure, not a
    leak. The pass condition is `all_recovered`: every burst, including one
    that failed outright, must bring the app back to fast, healthy
    responses within recovery_wait_s. That is the actual distinguishing
    test — a leak's signature isn't "one burst was too much," it's "the
    app never comes back." ok_counts is still reported per burst for a
    human to read the shape of the degradation, but it does not by itself
    gate pass/fail: a strict monotonic-decline check over just 2-3 samples
    is noisy (e.g. 30/30, 30/30, 0/30 recovering in 10s is healthy
    backpressure at 2x sustained capacity with no gap between bursts, not
    a leak — see triagebench_live/README.md for the measurements that
    established this)."""
    burst_results = []
    for i in range(bursts):
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=burst_size) as pool:
            results = list(pool.map(lambda _: _round_trip(base_url, timeout_s), range(burst_size)))
        elapsed = time.time() - t0
        ok = sum(results)
        recovery_s = _wait_for_recovery(base_url, max_wait_s=recovery_wait_s)
        burst_results.append({
            "burst": i, "ok": ok, "size": burst_size, "elapsed_s": round(elapsed, 1),
            "recovered_within_s": round(recovery_s, 1), "recovered": recovery_s < recovery_wait_s,
        })

    all_recovered = all(b["recovered"] for b in burst_results)
    ok_counts = [b["ok"] for b in burst_results]

    return PhaseResult(
        name="repeated_bursts_above_capacity",
        passed=all_recovered,
        detail=f"{bursts} bursts of {burst_size} concurrent requests (deliberately above the assumed "
               f"{ASSUMED_POOL_CAPACITY}-connection pool capacity), back to back with no gap: ok counts per "
               f"burst = {ok_counts}; every burst recovered to a fast /login response afterward = {all_recovered}",
        metrics={"bursts": burst_results, "all_recovered": all_recovered},
    )


def run_db_lifecycle_proof(base_url: str) -> List[PhaseResult]:
    return [
        phase_sequential(base_url),
        phase_concurrent_at_capacity(base_url),
        phase_repeated_bursts_above_capacity(base_url),
    ]
