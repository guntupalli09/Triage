"""
CI release gate for the Interaction Engine V1 adversarial benchmark
(benchmarks/interaction_corpus.py + benchmarks/run_interaction_benchmark.py).
Mirrors the exact pattern every adapter's own test_*_benchmark_gate.py
already uses — a thin pytest wrapper around the standalone benchmark
script's own summarize() so these gates run in the standard `pytest tests/`
suite and CI, not only via manual invocation.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("DEV_MODE", "true")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmarks"))

from run_interaction_benchmark import run, summarize  # noqa: E402


def test_zero_false_interactions():
    summary = summarize(run())
    assert summary["false_interactions"] == 0, summary["failed_assertions"]


def test_zero_missed_high_risk_interactions():
    summary = summarize(run())
    assert summary["missed_high_risk"] == 0, summary["failed_assertions"]


def test_zero_false_safe_interaction_outcomes():
    summary = summarize(run())
    assert summary["false_safe"] == 0, summary["failed_assertions"]


def test_fully_deterministic():
    summary = summarize(run())
    assert summary["determinism_pct"] == 100.0, summary["non_deterministic_cases"]


def test_interaction_state_accuracy_100_percent():
    # Every assertion in this hand-built corpus has a known-correct
    # expected value (unlike an adapter's own extraction-accuracy metric,
    # which tolerates some slack against a large hand-labeled corpus) --
    # 100% is the bar here, not a percentage threshold, since a wrong
    # interaction predicate result is never an acceptable "close enough."
    summary = summarize(run())
    assert summary["interaction_state_accuracy_pct"] == 100.0, summary["failed_assertions"]
