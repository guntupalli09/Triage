"""
Phase 4.1 tests: policy_readiness.py — the operator-facing shadow
readiness check / dry-run cutover verification.

Benchmark and full-test-suite re-runs are monkeypatched to fast, fake
results here (the real subprocess-based gates are exercised directly by
scripts/phase4_readiness_check.py and are slow by nature — this file
tests the readiness LOGIC: metric computation and verdict composition).
"""
import os

os.environ.setdefault("DEV_MODE", "true")

import pytest

import policy_enforcement as pe
import policy_readiness as pr
import playbook_authoring as pa
from database import SessionLocal, init_db
from models import AuditLog, Playbook, PolicyPosition, PolicyPositionField, PolicyRule, User


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema():
    init_db()


def _register_db(db, email) -> int:
    user = User(email=email, password_hash="x")
    db.add(user)
    db.flush()
    return user.id


def _create_playbook(db, uid, name="RO Playbook") -> Playbook:
    playbook = Playbook(user_id=uid, name=name, template_text="x")
    db.add(playbook)
    db.flush()
    return playbook


def _passing_gate(module):
    return pr.BenchmarkGateResult(module=module, passed=True, returncode=0)


def _failing_gate(module):
    return pr.BenchmarkGateResult(module=module, passed=False, returncode=1)


_MINIMAL_CONFIG = {
    "preferred_multiplier": 1.0, "prohibit_unlimited": True,
    "required_exceptions_json": [], "require_consequential_damages_exclusion": False,
    "required_consequential_carveouts_json": [],
}


def _make_active_liability_position(db, playbook) -> PolicyPosition:
    position = PolicyPosition(
        playbook_id=playbook.id, clause_type="limitation_of_liability", status="DRAFT",
        contract_side="mutual", escalation_approval_authority="Legal Director",
        fallback_text="Approved fallback.", config_json=dict(_MINIMAL_CONFIG), source_type="MANUAL",
    )
    db.add(position)
    db.flush()
    db.add(PolicyPositionField(
        policy_position_id=position.id, field_name="require_consequential_damages_exclusion",
        value_json=False, source="MANUAL", status="ESTABLISHED",
    ))
    db.flush()
    pa.validate_position_for_activation(position)
    position.status = "ACTIVE"
    from datetime import datetime
    position.activated_at = datetime.utcnow()
    db.flush()
    return position


# ---------------------------------------------------------------------------
# Migration coverage
# ---------------------------------------------------------------------------

class TestMigrationCoverage:
    def test_fully_migrated_playbook_not_in_unmigrated_list(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "readiness-migrated@example.com")
            playbook = _create_playbook(db, uid)
            rule = PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability", contract_side="mutual")
            db.add(rule)
            db.flush()
            pa.migrate_legacy_policy_rule(db, rule)
            db.commit()

            coverage = pr.compute_migration_coverage(db)
            assert playbook.id not in coverage.unmigrated_playbook_ids
        finally:
            db.close()

    def test_unmigrated_playbook_lowers_coverage_and_is_listed(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "readiness-unmigrated@example.com")
            playbook = _create_playbook(db, uid)
            db.add(PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability", contract_side="mutual"))
            db.commit()

            coverage = pr.compute_migration_coverage(db)
            assert playbook.id in coverage.unmigrated_playbook_ids
            assert coverage.coverage_pct < 100.0
        finally:
            db.close()

    def test_no_legacy_policies_at_all_is_100pct_coverage(self):
        """An empty legacy table is vacuously fully migrated — must not
        report 0% or divide by zero."""
        db = SessionLocal()
        try:
            coverage = pr.MigrationCoverage(total_legacy_liability_policies=0, migrated_active_equivalents=0)
            assert coverage.coverage_pct == 100.0
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Shadow stats
# ---------------------------------------------------------------------------

class TestShadowStats:
    def test_matching_vs_divergent_vs_error_are_counted_separately(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "readiness-shadow-stats@example.com")
            playbook = _create_playbook(db, uid)

            db.add(AuditLog(event_type=pr.SHADOW_COMPARISON_EVENT_TYPE, target_type="contract", target_id=1,
                             metadata_json={"playbook_id": playbook.id, "diverged": False, "is_error": False}))
            db.add(AuditLog(event_type=pr.SHADOW_COMPARISON_EVENT_TYPE, target_type="contract", target_id=2,
                             metadata_json={"playbook_id": playbook.id, "diverged": True, "is_error": False}))
            db.add(AuditLog(event_type=pr.SHADOW_COMPARISON_EVENT_TYPE, target_type="contract", target_id=3,
                             metadata_json={"playbook_id": playbook.id, "diverged": True, "is_error": True}))
            db.commit()

            stats = pr.compute_shadow_stats(db)
            assert stats.total_comparisons >= 3
            # Scoped assertions via delta isn't possible against a shared
            # DB across test modules, so assert the invariant instead:
            # error+diverged+matching always reconstructs total.
            assert stats.matching_comparisons + stats.divergent_comparisons + stats.evaluation_errors == stats.total_comparisons
        finally:
            db.close()

    def test_zero_comparisons_gives_none_divergence_rate_not_zero(self):
        stats = pr.ShadowStats(
            total_comparisons=0, divergent_comparisons=0, evaluation_errors=0,
            distinct_playbooks=0, distinct_contracts=0, oldest_comparison_at=None, newest_comparison_at=None,
        )
        assert stats.divergence_rate is None

    def test_run_shadow_comparison_writes_is_error_flag_distinctly(self, monkeypatch):
        """run_shadow_comparison (policy_enforcement.py) must set is_error
        separately from diverged so policy_readiness can tell an
        operational failure apart from a real semantic disagreement."""
        db = SessionLocal()
        try:
            uid = _register_db(db, "readiness-is-error@example.com")
            playbook = _create_playbook(db, uid)
            rule = PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability", contract_side="mutual",
                               preferred_multiplier=1.0, prohibit_unlimited=True)
            db.add(rule)
            db.flush()
            position = pa.migrate_legacy_policy_rule(db, rule)
            db.commit()

            def _boom(text):
                raise RuntimeError("simulated crash")

            original_funcs = pa._ENGINE_FUNCS["limitation_of_liability"]
            monkeypatch.setitem(pa._ENGINE_FUNCS, "limitation_of_liability", (_boom, original_funcs[1]))

            comparison = pe.run_shadow_comparison(db, playbook, "12. Limitation of Liability. Cap is 1x fees.")
            assert comparison["is_error"] is True
            assert comparison["diverged"] is True
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Verdict composition
# ---------------------------------------------------------------------------

class TestVerdictComposition:
    def test_ready_only_when_every_gate_passes_and_there_is_live_data(self, monkeypatch):
        db = SessionLocal()
        try:
            uid = _register_db(db, "readiness-verdict-ready@example.com")
            playbook = _create_playbook(db, uid)
            rule = PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability", contract_side="mutual")
            db.add(rule)
            db.flush()
            pa.migrate_legacy_policy_rule(db, rule)
            db.add(AuditLog(event_type=pr.SHADOW_COMPARISON_EVENT_TYPE, target_type="contract", target_id=999,
                             metadata_json={"playbook_id": playbook.id, "diverged": False, "is_error": False}))
            db.commit()

            monkeypatch.setattr(pr, "compute_migration_coverage",
                                 lambda db_: pr.MigrationCoverage(total_legacy_liability_policies=1, migrated_active_equivalents=1))
            monkeypatch.setattr(pr, "compute_shadow_stats",
                                 lambda db_: pr.ShadowStats(total_comparisons=5, divergent_comparisons=0, evaluation_errors=0,
                                                             distinct_playbooks=1, distinct_contracts=5,
                                                             oldest_comparison_at=None, newest_comparison_at=None))
            monkeypatch.setattr(pr, "run_six_adapter_benchmark_gates",
                                 lambda: [_passing_gate(m) for m in pr.SIX_ADAPTER_BENCHMARKS])
            monkeypatch.setattr(pr, "run_phase4_equivalence_gate", lambda: _passing_gate(pr.PHASE4_EQUIVALENCE_BENCHMARK))
            monkeypatch.setattr(pr, "run_full_test_suite", lambda: pr.TestSuiteResult(passed=True, returncode=0, summary_line="9999 passed"))

            report = pr.assess_readiness(db)
            assert report.verdict == "READY_FOR_CUTOVER"
            assert report.blocking_reasons == []
        finally:
            db.close()

    def test_not_ready_when_migration_incomplete(self, monkeypatch):
        db = SessionLocal()
        try:
            monkeypatch.setattr(pr, "compute_migration_coverage",
                                 lambda db_: pr.MigrationCoverage(total_legacy_liability_policies=2, migrated_active_equivalents=1, unmigrated_playbook_ids=[7]))
            monkeypatch.setattr(pr, "compute_shadow_stats",
                                 lambda db_: pr.ShadowStats(total_comparisons=5, divergent_comparisons=0, evaluation_errors=0,
                                                             distinct_playbooks=1, distinct_contracts=5,
                                                             oldest_comparison_at=None, newest_comparison_at=None))
            monkeypatch.setattr(pr, "run_six_adapter_benchmark_gates", lambda: [_passing_gate(m) for m in pr.SIX_ADAPTER_BENCHMARKS])
            monkeypatch.setattr(pr, "run_phase4_equivalence_gate", lambda: _passing_gate(pr.PHASE4_EQUIVALENCE_BENCHMARK))
            monkeypatch.setattr(pr, "run_full_test_suite", lambda: pr.TestSuiteResult(passed=True, returncode=0, summary_line="9999 passed"))

            report = pr.assess_readiness(db)
            assert report.verdict == "NOT_READY_FOR_CUTOVER"
            assert any("Migration coverage" in r for r in report.blocking_reasons)
        finally:
            db.close()

    def test_not_ready_when_live_divergence_nonzero(self, monkeypatch):
        db = SessionLocal()
        try:
            monkeypatch.setattr(pr, "compute_migration_coverage",
                                 lambda db_: pr.MigrationCoverage(total_legacy_liability_policies=1, migrated_active_equivalents=1))
            monkeypatch.setattr(pr, "compute_shadow_stats",
                                 lambda db_: pr.ShadowStats(total_comparisons=10, divergent_comparisons=1, evaluation_errors=0,
                                                             distinct_playbooks=1, distinct_contracts=10,
                                                             oldest_comparison_at=None, newest_comparison_at=None))
            monkeypatch.setattr(pr, "run_six_adapter_benchmark_gates", lambda: [_passing_gate(m) for m in pr.SIX_ADAPTER_BENCHMARKS])
            monkeypatch.setattr(pr, "run_phase4_equivalence_gate", lambda: _passing_gate(pr.PHASE4_EQUIVALENCE_BENCHMARK))
            monkeypatch.setattr(pr, "run_full_test_suite", lambda: pr.TestSuiteResult(passed=True, returncode=0, summary_line="9999 passed"))

            report = pr.assess_readiness(db)
            assert report.verdict == "NOT_READY_FOR_CUTOVER"
            assert any("diverged" in r for r in report.blocking_reasons)
        finally:
            db.close()

    def test_not_ready_when_no_live_data_yet_even_if_everything_else_passes(self, monkeypatch):
        """Zero live comparisons must never silently read as 'zero
        divergence, therefore ready' — the task explicitly requires
        reporting sample size and letting the operator decide, never
        treating absence of data as evidence of safety."""
        db = SessionLocal()
        try:
            monkeypatch.setattr(pr, "compute_migration_coverage",
                                 lambda db_: pr.MigrationCoverage(total_legacy_liability_policies=1, migrated_active_equivalents=1))
            monkeypatch.setattr(pr, "compute_shadow_stats",
                                 lambda db_: pr.ShadowStats(total_comparisons=0, divergent_comparisons=0, evaluation_errors=0,
                                                             distinct_playbooks=0, distinct_contracts=0,
                                                             oldest_comparison_at=None, newest_comparison_at=None))
            monkeypatch.setattr(pr, "run_six_adapter_benchmark_gates", lambda: [_passing_gate(m) for m in pr.SIX_ADAPTER_BENCHMARKS])
            monkeypatch.setattr(pr, "run_phase4_equivalence_gate", lambda: _passing_gate(pr.PHASE4_EQUIVALENCE_BENCHMARK))
            monkeypatch.setattr(pr, "run_full_test_suite", lambda: pr.TestSuiteResult(passed=True, returncode=0, summary_line="9999 passed"))

            report = pr.assess_readiness(db)
            assert report.verdict == "NOT_READY_FOR_CUTOVER"
            assert any("No live shadow comparisons" in r for r in report.blocking_reasons)
        finally:
            db.close()

    def test_not_ready_when_any_benchmark_gate_fails(self, monkeypatch):
        db = SessionLocal()
        try:
            monkeypatch.setattr(pr, "compute_migration_coverage",
                                 lambda db_: pr.MigrationCoverage(total_legacy_liability_policies=1, migrated_active_equivalents=1))
            monkeypatch.setattr(pr, "compute_shadow_stats",
                                 lambda db_: pr.ShadowStats(total_comparisons=5, divergent_comparisons=0, evaluation_errors=0,
                                                             distinct_playbooks=1, distinct_contracts=5,
                                                             oldest_comparison_at=None, newest_comparison_at=None))
            gates = [_passing_gate(m) for m in pr.SIX_ADAPTER_BENCHMARKS]
            gates[0] = _failing_gate(pr.SIX_ADAPTER_BENCHMARKS[0])
            monkeypatch.setattr(pr, "run_six_adapter_benchmark_gates", lambda: gates)
            monkeypatch.setattr(pr, "run_phase4_equivalence_gate", lambda: _passing_gate(pr.PHASE4_EQUIVALENCE_BENCHMARK))
            monkeypatch.setattr(pr, "run_full_test_suite", lambda: pr.TestSuiteResult(passed=True, returncode=0, summary_line="9999 passed"))

            report = pr.assess_readiness(db)
            assert report.verdict == "NOT_READY_FOR_CUTOVER"
        finally:
            db.close()

    def test_not_ready_when_test_suite_fails(self, monkeypatch):
        db = SessionLocal()
        try:
            monkeypatch.setattr(pr, "compute_migration_coverage",
                                 lambda db_: pr.MigrationCoverage(total_legacy_liability_policies=1, migrated_active_equivalents=1))
            monkeypatch.setattr(pr, "compute_shadow_stats",
                                 lambda db_: pr.ShadowStats(total_comparisons=5, divergent_comparisons=0, evaluation_errors=0,
                                                             distinct_playbooks=1, distinct_contracts=5,
                                                             oldest_comparison_at=None, newest_comparison_at=None))
            monkeypatch.setattr(pr, "run_six_adapter_benchmark_gates", lambda: [_passing_gate(m) for m in pr.SIX_ADAPTER_BENCHMARKS])
            monkeypatch.setattr(pr, "run_phase4_equivalence_gate", lambda: _passing_gate(pr.PHASE4_EQUIVALENCE_BENCHMARK))
            monkeypatch.setattr(pr, "run_full_test_suite", lambda: pr.TestSuiteResult(passed=False, returncode=1, summary_line="1 failed"))

            report = pr.assess_readiness(db)
            assert report.verdict == "NOT_READY_FOR_CUTOVER"
        finally:
            db.close()

    def test_skipping_benchmarks_or_tests_can_never_yield_ready(self, monkeypatch):
        db = SessionLocal()
        try:
            monkeypatch.setattr(pr, "compute_migration_coverage",
                                 lambda db_: pr.MigrationCoverage(total_legacy_liability_policies=1, migrated_active_equivalents=1))
            monkeypatch.setattr(pr, "compute_shadow_stats",
                                 lambda db_: pr.ShadowStats(total_comparisons=5, divergent_comparisons=0, evaluation_errors=0,
                                                             distinct_playbooks=1, distinct_contracts=5,
                                                             oldest_comparison_at=None, newest_comparison_at=None))
            report = pr.assess_readiness(db, run_benchmarks=False, run_tests=False)
            assert report.verdict == "NOT_READY_FOR_CUTOVER"
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Safe-content guarantee
# ---------------------------------------------------------------------------

class TestNoSensitiveContent:
    def test_safe_dict_never_contains_contract_or_policy_text(self, monkeypatch):
        db = SessionLocal()
        try:
            uid = _register_db(db, "readiness-safe-content@example.com")
            playbook = _create_playbook(db, uid)
            secret_fallback = "TOP SECRET FALLBACK LANGUAGE 42"
            position = _make_active_liability_position(db, playbook)
            position.fallback_text = secret_fallback
            db.commit()

            monkeypatch.setattr(pr, "run_six_adapter_benchmark_gates", lambda: [_passing_gate(m) for m in pr.SIX_ADAPTER_BENCHMARKS])
            monkeypatch.setattr(pr, "run_phase4_equivalence_gate", lambda: _passing_gate(pr.PHASE4_EQUIVALENCE_BENCHMARK))
            monkeypatch.setattr(pr, "run_full_test_suite", lambda: pr.TestSuiteResult(passed=True, returncode=0, summary_line="9999 passed"))

            report = pr.assess_readiness(db)
            safe_dict = pr.report_to_safe_dict(report)
            dump = str(safe_dict)
            assert secret_fallback not in dump
            assert "fallback" not in dump.lower() or "fallback" not in [k.lower() for k in safe_dict]
        finally:
            db.close()
