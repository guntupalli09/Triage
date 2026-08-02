"""Tests for review_workflow.py — the merged findings+redlines decision
record, kept independent of the FastAPI app so the logic is verifiable
without spinning up routes."""

import pytest

from review_workflow import (
    DecisionValidationError,
    build_audit_trail_text,
    build_cover_memo_text,
    compute_progress,
    finding_key,
    validate_decision,
)


def _finding(rule_id, title="Some finding", severity="high", has_redline=True, rationale="why it matters"):
    return {
        "rule_id": rule_id,
        "title": title,
        "severity": severity,
        "rationale": rationale,
        "exact_snippet": "matched text",
        "redline": {"issue": "x"} if has_redline else None,
    }


class TestFindingKey:
    def test_combines_rule_id_and_index(self):
        assert finding_key(0, "H_LOL_01") == "H_LOL_01#0"
        assert finding_key(2, "H_LOL_01") == "H_LOL_01#2"

    def test_same_rule_different_index_gives_different_keys(self):
        # this is the whole point — the same rule firing three times in one
        # document (real contracts do this) must produce three distinct keys
        assert finding_key(0, "H_ATTFEE_01") != finding_key(1, "H_ATTFEE_01")
        assert finding_key(1, "H_ATTFEE_01") != finding_key(2, "H_ATTFEE_01")


class TestValidateDecision:
    def test_accept_requires_a_redline(self):
        with pytest.raises(DecisionValidationError):
            validate_decision("R1#0", "accepted", has_redline=False, reason=None, edited_text=None)

    def test_accept_is_valid_with_a_redline(self):
        validate_decision("R1#0", "accepted", has_redline=True, reason=None, edited_text=None)

    def test_flagged_requires_no_redline(self):
        with pytest.raises(DecisionValidationError):
            validate_decision("R1#0", "flagged", has_redline=True, reason=None, edited_text=None)

    def test_flagged_is_valid_without_a_redline(self):
        validate_decision("R1#0", "flagged", has_redline=False, reason=None, edited_text=None)

    def test_rejected_requires_a_reason(self):
        with pytest.raises(DecisionValidationError):
            validate_decision("R1#0", "rejected", has_redline=True, reason="", edited_text=None)
        with pytest.raises(DecisionValidationError):
            validate_decision("R1#0", "rejected", has_redline=True, reason="   ", edited_text=None)

    def test_rejected_with_a_reason_is_valid(self):
        validate_decision("R1#0", "rejected", has_redline=True, reason="not applicable to this deal", edited_text=None)

    def test_edited_requires_edited_text(self):
        with pytest.raises(DecisionValidationError):
            validate_decision("R1#0", "edited", has_redline=True, reason=None, edited_text="")

    def test_edited_with_text_is_valid(self):
        validate_decision("R1#0", "edited", has_redline=True, reason=None, edited_text="new clause text")

    def test_unknown_action_is_rejected(self):
        with pytest.raises(DecisionValidationError):
            validate_decision("R1#0", "made_up_action", has_redline=True, reason=None, edited_text=None)

    def test_empty_key_is_rejected(self):
        with pytest.raises(DecisionValidationError):
            validate_decision("", "accepted", has_redline=True, reason=None, edited_text=None)


class TestComputeProgress:
    def test_empty_findings_is_not_complete(self):
        progress = compute_progress([], {})
        assert progress.total == 0
        assert progress.is_complete is False  # nothing to review isn't "reviewed"

    def test_no_decisions_yet(self):
        findings = [_finding("R1"), _finding("R2")]
        progress = compute_progress(findings, {})
        assert progress.resolved == 0
        assert progress.is_complete is False
        assert progress.first_unresolved_key == "R1#0"

    def test_partial_progress(self):
        findings = [_finding("R1"), _finding("R2"), _finding("R3")]
        decisions = {"R1#0": {"action": "accepted"}}
        progress = compute_progress(findings, decisions)
        assert progress.resolved == 1
        assert progress.accepted == 1
        assert progress.is_complete is False
        assert progress.first_unresolved_key == "R2#1"

    def test_fully_resolved(self):
        findings = [_finding("R1"), _finding("R2")]
        decisions = {"R1#0": {"action": "accepted"}, "R2#1": {"action": "rejected", "reason": "no"}}
        progress = compute_progress(findings, decisions)
        assert progress.is_complete is True
        assert progress.first_unresolved_key is None

    def test_comment_only_does_not_count_as_resolved(self):
        # a comment is a note, not a decision — see module docstring
        findings = [_finding("R1")]
        decisions = {"R1#0": {"comment": "ask Jane about this"}}
        progress = compute_progress(findings, decisions)
        assert progress.resolved == 0
        assert progress.is_complete is False

    def test_counts_every_action_type(self):
        findings = [_finding(f"R{i}") for i in range(5)]
        decisions = {
            "R0#0": {"action": "accepted"}, "R1#1": {"action": "edited"}, "R2#2": {"action": "rejected", "reason": "x"},
            "R3#3": {"action": "flagged"}, "R4#4": {"action": "dismissed"},
        }
        progress = compute_progress(findings, decisions)
        assert progress.as_dict() == {
            "total": 5, "resolved": 5, "accepted": 1, "edited": 1, "rejected": 1,
            "flagged": 1, "dismissed": 1, "is_complete": True, "first_unresolved_key": None,
        }

    def test_same_rule_id_firing_twice_is_tracked_independently(self):
        # the bug this whole keying scheme exists to prevent: two findings
        # sharing a rule_id must be resolvable independently of each other
        findings = [
            _finding("H_ATTFEE_01", title="One-way attorneys' fees"),
            _finding("H_ATTFEE_01", title="Mutual attorneys' fees"),
            _finding("H_ATTFEE_01", title="One-way attorneys' fees (again)"),
        ]
        decisions = {finding_key(1, "H_ATTFEE_01"): {"action": "rejected", "reason": "already mutual"}}
        progress = compute_progress(findings, decisions)
        assert progress.resolved == 1
        assert progress.rejected == 1
        assert progress.is_complete is False
        # the other two occurrences of the SAME rule_id must still be unresolved
        assert progress.first_unresolved_key == finding_key(0, "H_ATTFEE_01")


class TestCoverMemo:
    def test_all_accepted_says_nothing_to_flag(self):
        findings = [_finding("R1")]
        decisions = {"R1#0": {"action": "accepted"}}
        memo = build_cover_memo_text("test.docx", findings, decisions)
        assert "nothing requires further attention" in memo

    def test_rejected_includes_the_stated_reason(self):
        findings = [_finding("R1", title="Unlimited Liability")]
        decisions = {"R1#0": {"action": "rejected", "reason": "deal size too small to matter"}}
        memo = build_cover_memo_text("test.docx", findings, decisions)
        assert "Unlimited Liability" in memo
        assert "deal size too small to matter" in memo

    def test_flagged_finding_included_with_rationale(self):
        findings = [_finding("R1", title="Narrow indemnity scope", has_redline=False, rationale="leaves data breach uncovered")]
        decisions = {"R1#0": {"action": "flagged"}}
        memo = build_cover_memo_text("test.docx", findings, decisions)
        assert "Narrow indemnity scope" in memo
        assert "leaves data breach uncovered" in memo

    def test_duplicate_rule_id_findings_are_reported_separately(self):
        findings = [
            _finding("H_ATTFEE_01", title="One-way attorneys' fees"),
            _finding("H_ATTFEE_01", title="Mutual attorneys' fees"),
        ]
        decisions = {
            finding_key(0, "H_ATTFEE_01"): {"action": "accepted"},
            finding_key(1, "H_ATTFEE_01"): {"action": "rejected", "reason": "already mutual"},
        }
        memo = build_cover_memo_text("test.docx", findings, decisions)
        assert "1 accepted, 1 rejected" in memo
        assert "already mutual" in memo


class TestAuditTrail:
    def test_includes_every_finding_even_unresolved(self):
        findings = [_finding("R1"), _finding("R2")]
        decisions = {"R1#0": {"action": "accepted", "decided_at": "2026-08-02T00:00:00"}}
        trail = build_audit_trail_text("test.docx", "7.2.0", findings, decisions)
        assert "R1" in trail and "accepted" in trail
        assert "R2" in trail and "UNRESOLVED" in trail

    def test_includes_engine_version(self):
        trail = build_audit_trail_text("test.docx", "7.2.0", [], {})
        assert "7.2.0" in trail

    def test_duplicate_rule_id_occurrences_both_appear_with_correct_decisions(self):
        findings = [
            _finding("H_ATTFEE_01", title="One-way attorneys' fees"),
            _finding("H_ATTFEE_01", title="Mutual attorneys' fees"),
        ]
        decisions = {finding_key(1, "H_ATTFEE_01"): {"action": "rejected", "reason": "already mutual"}}
        trail = build_audit_trail_text("test.docx", "7.2.0", findings, decisions)
        assert trail.count("H_ATTFEE_01") == 2
        assert "UNRESOLVED" in trail  # the first occurrence, untouched
        assert "rejected" in trail  # the second occurrence, decided
