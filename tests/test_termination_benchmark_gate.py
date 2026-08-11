"""
Release gate for the Termination policy engine (third clause adapter).
Mirrors tests/test_liability_benchmark_gate.py and
tests/test_indemnification_benchmark_gate.py's discipline: false-safe and
false-escalation must be zero, determinism must be 100%. No fixed
policy-state-accuracy target is asserted yet — this is a first pass on a
40-case corpus authored and debugged in the same session, the same
evidentiary caveat noted for Indemnification's own first pass.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_termination_benchmark import run, summarize


def test_zero_false_safe_cases():
    data = run()
    summary = summarize(data)
    false_safe_ids = [r["id"] for r in summary["false_safe_rows"]]
    assert summary["false_safe_count"] == 0, (
        f"{summary['false_safe_count']} false-safe case(s): {false_safe_ids}."
    )


def test_zero_false_escalation_cases():
    data = run()
    summary = summarize(data)
    false_escalation_ids = [r["id"] for r in summary["false_escalation_rows"]]
    assert summary["false_escalation_count"] == 0, (
        f"{summary['false_escalation_count']} false-escalation case(s): {false_escalation_ids}."
    )


def test_fully_deterministic():
    data = run()
    non_deterministic_ids = [r["id"] for r in data["rows"] if not r["deterministic"]]
    assert non_deterministic_ids == [], f"Non-deterministic output on: {non_deterministic_ids}"
