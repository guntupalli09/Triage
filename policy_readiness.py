"""
Phase 4.1: Production Shadow Readiness.

An operator-facing readiness check that answers ONE question: is this
deployment safe to move POLICY_ENFORCEMENT_MODE from "shadow" to
"cutover"? It changes nothing — no mode flip, no data mutation, no engine
behavior change. It only reads existing state (AuditLog shadow-comparison
history, PolicyRule/PolicyPosition migration coverage) and re-runs the
existing, unmodified release-gate benchmarks and test suite to report
their CURRENT status.

Every value in ReadinessReport is a count, id, boolean, timestamp, or
status string — never contract text, policy config values, fallback
language, or excerpts. This is enforced by construction: nothing in this
module ever reads Contract.contract_text, PolicyPosition.config_json,
PolicyPosition.fallback_text, or PolicyPositionField.evidence_excerpt: it
only reads AuditLog.metadata_json (already scrubbed by
policy_enforcement.run_shadow_comparison — see that function's own
docstring) and row counts/ids/timestamps from PolicyRule/PolicyPosition.

See docs/architecture/phase4_cutover.md for the cutover condition this
report exists to evidence, and scripts/phase4_readiness_check.py for the
operator-facing CLI (also the dry-run cutover verification command).
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

import policy_enforcement as pe
from models import AuditLog, PolicyPosition, PolicyRule

_REPO_ROOT = Path(__file__).resolve().parent

SIX_ADAPTER_BENCHMARKS = [
    "benchmarks.run_liability_benchmark",
    "benchmarks.run_indemnification_benchmark",
    "benchmarks.run_termination_benchmark",
    "benchmarks.run_confidentiality_benchmark",
    "benchmarks.run_assignment_benchmark",
    "benchmarks.run_governing_law_benchmark",
]
PHASE4_EQUIVALENCE_BENCHMARK = "benchmarks.run_phase4_shadow_benchmark"
SHADOW_COMPARISON_EVENT_TYPE = "phase4_shadow_comparison"


# ---------------------------------------------------------------------------
# Migration coverage
# ---------------------------------------------------------------------------

@dataclass
class MigrationCoverage:
    total_legacy_liability_policies: int
    migrated_active_equivalents: int
    unmigrated_playbook_ids: List[int] = field(default_factory=list)

    @property
    def unmigrated_count(self) -> int:
        return len(self.unmigrated_playbook_ids)

    @property
    def coverage_pct(self) -> float:
        if self.total_legacy_liability_policies == 0:
            return 100.0
        return 100.0 * self.migrated_active_equivalents / self.total_legacy_liability_policies


def compute_migration_coverage(db: DBSession) -> MigrationCoverage:
    total = db.query(PolicyRule).filter(PolicyRule.clause_type == "limitation_of_liability").count()
    unmigrated = pe.find_unmigrated_liability_policies(db)
    return MigrationCoverage(
        total_legacy_liability_policies=total,
        migrated_active_equivalents=total - len(unmigrated),
        unmigrated_playbook_ids=unmigrated,
    )


# ---------------------------------------------------------------------------
# Live shadow-comparison history (from AuditLog — never raw contract/policy
# content; see policy_enforcement.run_shadow_comparison)
# ---------------------------------------------------------------------------

@dataclass
class ShadowStats:
    total_comparisons: int
    divergent_comparisons: int  # real semantic divergence, is_error excluded
    evaluation_errors: int  # migrated path couldn't run at all
    distinct_playbooks: int
    distinct_contracts: int
    oldest_comparison_at: Optional[datetime]
    newest_comparison_at: Optional[datetime]

    @property
    def matching_comparisons(self) -> int:
        return self.total_comparisons - self.divergent_comparisons - self.evaluation_errors

    @property
    def divergence_rate(self) -> Optional[float]:
        """None (not 0.0) when there is no data — a readiness report must
        never imply "we checked and it's fine" when there is simply
        nothing to check yet."""
        if self.total_comparisons == 0:
            return None
        return self.divergent_comparisons / self.total_comparisons


def compute_shadow_stats(db: DBSession) -> ShadowStats:
    rows = db.query(AuditLog).filter(AuditLog.event_type == SHADOW_COMPARISON_EVENT_TYPE).all()

    total = len(rows)
    divergent = 0
    errors = 0
    playbook_ids = set()
    contract_ids = set()
    timestamps: List[datetime] = []

    for row in rows:
        meta = row.metadata_json or {}
        is_error = bool(meta.get("is_error"))
        diverged = bool(meta.get("diverged"))
        if is_error:
            errors += 1
        elif diverged:
            divergent += 1
        pb_id = meta.get("playbook_id")
        if pb_id is not None:
            playbook_ids.add(pb_id)
        if row.target_id is not None:
            contract_ids.add(row.target_id)
        if row.created_at is not None:
            timestamps.append(row.created_at)

    return ShadowStats(
        total_comparisons=total,
        divergent_comparisons=divergent,
        evaluation_errors=errors,
        distinct_playbooks=len(playbook_ids),
        distinct_contracts=len(contract_ids),
        oldest_comparison_at=min(timestamps) if timestamps else None,
        newest_comparison_at=max(timestamps) if timestamps else None,
    )


# ---------------------------------------------------------------------------
# Release-gate re-verification — re-runs the EXISTING, unmodified benchmark
# scripts/test suite as subprocesses (isolated in-memory DBs, no shared
# state with the readiness check's own db session) and reports their
# current pass/fail, never re-implementing their scoring logic here.
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkGateResult:
    module: str
    passed: bool
    returncode: int


def _run_module_as_gate(module: str, *, timeout: int = 300) -> BenchmarkGateResult:
    result = subprocess.run(
        [sys.executable, "-m", module], cwd=str(_REPO_ROOT),
        capture_output=True, text=True, timeout=timeout,
    )
    return BenchmarkGateResult(module=module, passed=(result.returncode == 0), returncode=result.returncode)


def run_six_adapter_benchmark_gates() -> List[BenchmarkGateResult]:
    return [_run_module_as_gate(m) for m in SIX_ADAPTER_BENCHMARKS]


def run_phase4_equivalence_gate() -> BenchmarkGateResult:
    return _run_module_as_gate(PHASE4_EQUIVALENCE_BENCHMARK)


@dataclass
class TestSuiteResult:
    passed: bool
    returncode: int
    summary_line: str  # e.g. "1534 passed, 13 skipped" — pytest's own last summary line, no test content


def run_full_test_suite(*, timeout: int = 900) -> TestSuiteResult:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"], cwd=str(_REPO_ROOT),
        capture_output=True, text=True, timeout=timeout,
    )
    summary_line = ""
    for line in reversed(result.stdout.splitlines()):
        stripped = line.strip()
        if stripped and ("passed" in stripped or "failed" in stripped or "error" in stripped):
            summary_line = stripped
            break
    return TestSuiteResult(passed=(result.returncode == 0), returncode=result.returncode, summary_line=summary_line)


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

@dataclass
class ReadinessReport:
    generated_at: datetime
    current_mode: str
    migration: MigrationCoverage
    shadow: ShadowStats
    six_adapter_gates: List[BenchmarkGateResult]
    phase4_equivalence_gate: BenchmarkGateResult
    test_suite: TestSuiteResult
    verdict: str  # "READY_FOR_CUTOVER" | "NOT_READY_FOR_CUTOVER"
    blocking_reasons: List[str]


def assess_readiness(db: DBSession, *, run_benchmarks: bool = True, run_tests: bool = True) -> ReadinessReport:
    """Computes every readiness signal and the final verdict. Never
    mutates POLICY_ENFORCEMENT_MODE, never writes to PolicyRule/
    PolicyPosition/PolicyPositionField/PolicyPositionApproval — read-only
    against the DB, and the benchmark/test-suite re-runs are subprocesses
    against their own isolated in-memory databases."""
    migration = compute_migration_coverage(db)
    shadow = compute_shadow_stats(db)
    current_mode = pe.get_enforcement_mode()

    six_adapter_gates = run_six_adapter_benchmark_gates() if run_benchmarks else []
    phase4_gate = run_phase4_equivalence_gate() if run_benchmarks else BenchmarkGateResult(
        module=PHASE4_EQUIVALENCE_BENCHMARK, passed=False, returncode=-1,
    )
    test_suite = run_full_test_suite() if run_tests else TestSuiteResult(passed=False, returncode=-1, summary_line="(skipped)")

    blocking: List[str] = []

    if migration.unmigrated_count > 0:
        blocking.append(
            f"Migration coverage is {migration.coverage_pct:.1f}%, not 100% — "
            f"{migration.unmigrated_count} legacy liability polic{'y' if migration.unmigrated_count == 1 else 'ies'} "
            f"lack an equivalent ACTIVE PolicyPosition (playbook_ids={migration.unmigrated_playbook_ids})."
        )

    if shadow.total_comparisons == 0:
        blocking.append(
            "No live shadow comparisons recorded yet — there is no live evidence to evaluate. "
            "This is reported, not assumed passing: 0 comparisons is not the same as 0 divergences."
        )
    else:
        if shadow.divergent_comparisons > 0:
            blocking.append(
                f"{shadow.divergent_comparisons} of {shadow.total_comparisons} live shadow comparisons "
                f"diverged (rate={shadow.divergence_rate:.4%}). Root-cause every divergence before proceeding "
                f"— do not normalize away."
            )
        if shadow.evaluation_errors > 0:
            blocking.append(
                f"{shadow.evaluation_errors} live shadow comparisons could not evaluate the migrated path at all."
            )

    if run_benchmarks:
        failing_adapters = [g.module for g in six_adapter_gates if not g.passed]
        if failing_adapters:
            blocking.append(f"Six-adapter benchmark gate(s) currently failing: {failing_adapters}")
        if not phase4_gate.passed:
            blocking.append("Phase 4 109-case offline equivalence gate is currently failing.")
    else:
        blocking.append("Benchmark gates were not run for this report (run_benchmarks=False) — status unknown.")

    if run_tests:
        if not test_suite.passed:
            blocking.append(f"Full test suite is currently failing ({test_suite.summary_line or 'see output'}).")
    else:
        blocking.append("Full test suite was not run for this report (run_tests=False) — status unknown.")

    verdict = "READY_FOR_CUTOVER" if not blocking else "NOT_READY_FOR_CUTOVER"

    return ReadinessReport(
        generated_at=datetime.utcnow(), current_mode=current_mode, migration=migration, shadow=shadow,
        six_adapter_gates=six_adapter_gates, phase4_equivalence_gate=phase4_gate, test_suite=test_suite,
        verdict=verdict, blocking_reasons=blocking,
    )


def report_to_safe_dict(report: ReadinessReport) -> Dict[str, Any]:
    """JSON-serializable projection of ReadinessReport. Every field here
    is a count, id, boolean, timestamp, or short status string — audited
    by hand against the dataclass fields above; nothing here is sourced
    from contract text, policy config, or evidence excerpts."""
    return {
        "generated_at": report.generated_at.isoformat(),
        "current_mode": report.current_mode,
        "verdict": report.verdict,
        "blocking_reasons": report.blocking_reasons,
        "migration_coverage": {
            "total_legacy_liability_policies": report.migration.total_legacy_liability_policies,
            "migrated_active_equivalents": report.migration.migrated_active_equivalents,
            "unmigrated_count": report.migration.unmigrated_count,
            "unmigrated_playbook_ids": report.migration.unmigrated_playbook_ids,
            "coverage_pct": round(report.migration.coverage_pct, 2),
        },
        "live_shadow_comparisons": {
            "total": report.shadow.total_comparisons,
            "divergent": report.shadow.divergent_comparisons,
            "matching": report.shadow.matching_comparisons,
            "evaluation_errors": report.shadow.evaluation_errors,
            "divergence_rate": report.shadow.divergence_rate,
            "distinct_playbooks_exercised": report.shadow.distinct_playbooks,
            "distinct_contracts_exercised": report.shadow.distinct_contracts,
            "oldest_comparison_at": report.shadow.oldest_comparison_at.isoformat() if report.shadow.oldest_comparison_at else None,
            "newest_comparison_at": report.shadow.newest_comparison_at.isoformat() if report.shadow.newest_comparison_at else None,
        },
        "six_adapter_benchmark_gates": {
            g.module.rsplit(".", 1)[-1]: ("PASS" if g.passed else "FAIL") for g in report.six_adapter_gates
        },
        "phase4_109case_equivalence_gate": "PASS" if report.phase4_equivalence_gate.passed else "FAIL",
        "full_test_suite": {
            "status": "PASS" if report.test_suite.passed else "FAIL",
            "summary": report.test_suite.summary_line,
        },
    }
