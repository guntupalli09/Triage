"""Unit tests for playbook/policy_engine.py — the deterministic 6-status
classification truth table."""
from types import SimpleNamespace

from playbook.policy_engine import (
    classify, COMPLIANT, PARTIALLY_COMPLIANT, NEGOTIABLE, PROHIBITED, ESCALATE, NOT_APPLICABLE,
)


def _finding(severity="medium", finding_type="adverse_language_detected"):
    return SimpleNamespace(severity=severity, finding_type=finding_type)


def _rule(status, severity=None, approval_required=False, escalation_owner=None):
    return SimpleNamespace(
        title="Test Rule", status=status, severity=severity, approval_required=approval_required,
        escalation_owner=escalation_owner, preferred_position="preferred", fallback_position="fallback",
        legal_reason=None, business_reason=None,
    )


def test_no_policy_rule_is_not_applicable():
    result = classify(_finding(), None)
    assert result.status == NOT_APPLICABLE


def test_unable_to_determine_always_escalates_when_policy_exists():
    rule = _rule("acceptable")
    result = classify(_finding(finding_type="unable_to_determine"), rule)
    assert result.status == ESCALATE
    assert result.escalation_required is True


def test_unable_to_determine_with_no_policy_is_not_applicable():
    # No policy authored at all — nothing to escalate against.
    result = classify(_finding(finding_type="unable_to_determine"), None)
    assert result.status == NOT_APPLICABLE


def test_prohibited_status_yields_prohibited():
    rule = _rule("prohibited")
    result = classify(_finding(severity="critical"), rule)
    assert result.status == PROHIBITED


def test_prohibited_with_approval_required_floors_at_escalate():
    rule = _rule("prohibited", approval_required=True, escalation_owner="Managing Partner")
    result = classify(_finding(), rule)
    assert result.status == ESCALATE
    assert result.escalation_required is True
    assert result.escalation_owner == "Managing Partner"


def test_negotiate_status_yields_negotiable():
    rule = _rule("negotiate")
    result = classify(_finding(), rule)
    assert result.status == NEGOTIABLE
    assert result.fallback_position == "fallback"


def test_negotiate_with_approval_required_escalates():
    rule = _rule("negotiate", approval_required=True)
    result = classify(_finding(), rule)
    assert result.status == ESCALATE


def test_acceptable_within_tolerance_is_compliant():
    rule = _rule("acceptable", severity="high")
    result = classify(_finding(severity="medium"), rule)
    assert result.status == COMPLIANT


def test_acceptable_exceeding_tolerance_is_partially_compliant():
    rule = _rule("acceptable", severity="low")
    result = classify(_finding(severity="critical"), rule)
    assert result.status == PARTIALLY_COMPLIANT


def test_acceptable_with_approval_required_escalates():
    rule = _rule("acceptable", approval_required=True)
    result = classify(_finding(), rule)
    assert result.status == ESCALATE


def test_expected_protection_not_found_with_prohibited_policy_is_prohibited():
    rule = _rule("prohibited")
    result = classify(_finding(finding_type="expected_protection_not_found"), rule)
    assert result.status == PROHIBITED
