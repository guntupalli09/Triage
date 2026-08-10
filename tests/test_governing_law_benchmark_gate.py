"""
Release gate for the Governing Law policy engine (Batch A adapter 3 of
3). Mirrors the established discipline: false-safe and false-escalation
must be zero, determinism must be 100%.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_governing_law_benchmark import run, summarize


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
