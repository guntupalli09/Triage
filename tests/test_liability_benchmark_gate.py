"""
Release gate for the Limitation of Liability policy engine — the complete
quality gate, not just the safety gate. See benchmarks/run_liability_benchmark.py
and benchmarks/liability_benchmark_report.md for the full corpus, metrics,
and root-cause analysis.

Do not silence a failure here by loosening an assertion, marking it xfail,
or deleting/relabeling corpus cases to make it pass — fix the underlying
cause. Ground-truth corrections belong in benchmarks/liability_corpus.py,
justified individually in that case's `notes`, never made merely to raise
a number here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_liability_benchmark import run, summarize


def test_zero_false_safe_cases():
    """The hard safety gate: the engine must never return ACCEPT/
    ACCEPT_WITH_NOTE where the correct answer required attorney attention."""
    data = run()
    summary = summarize(data)
    false_safe_ids = [r["id"] for r in summary["false_safe_rows"]]
    assert summary["false_safe_count"] == 0, (
        f"{summary['false_safe_count']} false-safe case(s): {false_safe_ids}. "
        f"See benchmarks/liability_benchmark_report.md."
    )


def test_policy_state_accuracy_above_95_percent():
    data = run()
    summary = summarize(data)
    assert summary["policy_state_accuracy"] > 0.95, (
        f"Policy-state accuracy {summary['policy_state_accuracy']:.1%} <= 95% target."
    )


def test_general_cap_extraction_accuracy_above_98_percent():
    data = run()
    summary = summarize(data)
    acc = summary["general_cap_accuracy"] or 0.0
    assert acc > 0.98, f"General-cap extraction accuracy {acc:.1%} <= 98% target."


def test_category_treatment_accuracy_above_95_percent():
    data = run()
    summary = summarize(data)
    acc = summary["category_treatment_accuracy"] or 0.0
    assert acc > 0.95, f"Category-treatment accuracy {acc:.1%} <= 95% target."


def test_liability_policy_engine_is_fully_deterministic():
    data = run()
    non_deterministic_ids = [r["id"] for r in data["rows"] if not r["deterministic"]]
    assert non_deterministic_ids == [], (
        f"Non-deterministic output on: {non_deterministic_ids} — same input must "
        f"always produce byte-identical output."
    )
