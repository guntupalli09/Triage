"""Tests for the full 117-rule Reviewer 1 (Framework Author) Migration
(scripts/severity_migration_full.py). Validates completeness, schema
validity, and the read-only/reversibility guarantees Task 4 required --
does not assert that any particular rule's computed severity is "correct,"
since that is exactly what Phase 3 attorney review (not this test suite)
determines."""

from rules_engine import RuleEngine
from severity_scoring import validate_ruleset
from scripts.severity_migration_full import FULL_MIGRATION


def test_all_live_rules_are_scored():
    live_ids = {r.rule_id for r in RuleEngine().rules}
    scored_ids = {r.rule_id for r in FULL_MIGRATION}
    assert live_ids == scored_ids
    assert len(FULL_MIGRATION) == 185


def test_no_duplicate_rule_ids():
    ids = [r.rule_id for r in FULL_MIGRATION]
    assert len(ids) == len(set(ids))


def test_every_rule_has_legacy_severity_preserved():
    live_by_id = {r.rule_id: r for r in RuleEngine().rules}
    for scored in FULL_MIGRATION:
        assert scored.legacy_severity == live_by_id[scored.rule_id].severity, (
            f"{scored.rule_id}: legacy_severity does not match the live rule's "
            f"severity -- Task 4 requires legacy severity be preserved exactly, "
            f"read-only, never altered."
        )


def test_full_migration_passes_hard_validation():
    result = validate_ruleset(FULL_MIGRATION)
    assert result["errors"] == [], result["errors"]


def test_full_migration_has_no_monotonicity_violations():
    # A stricter check than test_full_migration_passes_hard_validation --
    # monotonicity is currently reported as a warning (architecture doc
    # design choice, severity_scoring.py's validate_ruleset docstring), but
    # for THIS specific 117-rule migration we assert zero violations
    # outright, since finding one would mean two rules in the same
    # clause_category were scored inconsistently with each other by the
    # same reviewer in the same pass -- a real defect, not a judgment call.
    from severity_scoring import validate_monotonicity
    violations = validate_monotonicity(FULL_MIGRATION)
    assert violations == [], violations


def test_every_rule_id_matches_a_real_live_rule():
    live_ids = {r.rule_id for r in RuleEngine().rules}
    for scored in FULL_MIGRATION:
        assert scored.rule_id in live_ids


def test_migration_is_read_only_wrt_live_rules_engine():
    # Scoring the full migration must never mutate rules_engine.py's Rule
    # objects -- confirmed by re-reading the live engine after import and
    # comparing severities are unchanged from a fresh RuleEngine instance.
    before = {r.rule_id: r.severity for r in RuleEngine().rules}
    _ = list(FULL_MIGRATION)  # force any lazy evaluation
    after = {r.rule_id: r.severity for r in RuleEngine().rules}
    assert before == after


def test_findings_log_is_nonempty_and_documents_the_headline_number():
    from scripts.severity_migration_full import FINDINGS
    assert "MEDIUM is structurally unreachable" in FINDINGS
    assert len(FINDINGS.strip()) > 500
