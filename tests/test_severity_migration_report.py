"""Tests for the migration comparison report (Task 5) — architecture doc
§12 Phase 2/3. Validates the report-generation logic itself, not the
substance of any particular legal-severity disagreement (those are
documented, not asserted as correct, in the architecture doc §5.1)."""

from rules_engine import Severity
from severity_scoring import ScoredRule, FactorVector, validate_ruleset
from scripts.generate_migration_report import build_report, _confidence
from scripts.severity_migration_sample import MIGRATION_SAMPLE


def test_migration_sample_has_no_hard_validation_errors():
    result = validate_ruleset(MIGRATION_SAMPLE)
    assert result["errors"] == []


def test_migration_sample_legacy_severity_is_never_absent():
    # Task 4: every migrated rule must preserve its legacy severity.
    for rule in MIGRATION_SAMPLE:
        assert rule.legacy_severity is not None, f"{rule.rule_id} is missing legacy_severity"


def test_build_report_never_mutates_legacy_severity():
    before = {r.rule_id: r.legacy_severity for r in MIGRATION_SAMPLE}
    build_report(MIGRATION_SAMPLE)
    after = {r.rule_id: r.legacy_severity for r in MIGRATION_SAMPLE}
    assert before == after, "migration report must be read-only w.r.t. legacy_severity (architecture doc §12)"


def test_build_report_flags_changed_rules_correctly():
    rows = build_report(MIGRATION_SAMPLE)
    by_id = {r.rule_id: r for r in rows}
    assert by_id["H_LOL_01"].changed is False
    assert by_id["M_LEASE_CAM_UNCAPPED_01"].changed is True
    assert by_id["M_LEASE_CAM_UNCAPPED_01"].direction == "upgrade"
    assert by_id["H_ASSIGN_CHANGE_CTRL_01"].direction == "downgrade"


def test_known_contestable_rule_never_gets_high_or_medium_confidence():
    contestable = next(r for r in MIGRATION_SAMPLE if r.known_contestable)
    assert _confidence(contestable) == "low"


def test_ceiling_derived_changes_always_get_high_confidence():
    rows = build_report(MIGRATION_SAMPLE)
    for row in rows:
        if row.method == "ceiling":
            assert row.confidence == "high", (
                f"{row.rule_id}: a ceiling-derived tier traces to a single named, "
                f"citable legal fact and should never be reported as low-confidence."
            )


def test_recommendation_never_silently_resolves_a_boundary_case():
    rows = build_report(MIGRATION_SAMPLE)
    for row in rows:
        if row.confidence == "low" and row.changed:
            assert "defer" in row.recommendation.lower(), (
                f"{row.rule_id}: a low-confidence CHANGED result must defer to attorney "
                f"review, never assert 'adopt new severity' on its own."
            )
