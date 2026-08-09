"""
Release gate: the Limitation of Liability benchmark's false-safe rate must
be zero before this engine (or its architecture) is extended to a second
clause type. See benchmarks/run_liability_benchmark.py and
benchmarks/liability_benchmark_report.md for the full corpus, metrics, and
root-cause analysis.

This test is EXPECTED TO FAIL as of the benchmark's first run — it exists
to make the gate visible in the normal test suite, not to assert the
engine is already safe. See the report's "Root-cause analysis" section for
the 5 diagnosed causes and "Recommendations" for what unblocks this gate.
Do not silence this failure by loosening the assertion, marking it xfail,
or deleting cases from the corpus to make it pass — fix the underlying
false-safe cause (primarily: the fixed-size extraction window silently
dropping superseding cap language beyond ~3000 characters) instead.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_liability_benchmark import run, summarize


def test_liability_policy_engine_has_zero_false_safe_cases():
    data = run()
    summary = summarize(data)
    false_safe_ids = [r["id"] for r in summary["false_safe_rows"]]
    assert summary["false_safe_count"] == 0, (
        f"{summary['false_safe_count']} false-safe case(s) — the engine returned "
        f"ACCEPT/ACCEPT_WITH_NOTE where the correct answer required attorney "
        f"attention: {false_safe_ids}. See benchmarks/liability_benchmark_report.md."
    )


def test_liability_policy_engine_is_fully_deterministic():
    data = run()
    non_deterministic_ids = [r["id"] for r in data["rows"] if not r["deterministic"]]
    assert non_deterministic_ids == [], (
        f"Non-deterministic output on: {non_deterministic_ids} — same input must "
        f"always produce byte-identical output."
    )
