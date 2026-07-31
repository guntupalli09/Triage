"""
Tests for the Risk Allocation & Clause Balance Score — see risk_balance.py.

Unit tests exercise compute_risk_balance() directly against synthetic
findings carrying a `perspective` attribute (mirroring what
rules_engine.py's _build_perspective actually attaches). Integration tests
exercise RuleEngine.analyze() end-to-end.
"""

from dataclasses import dataclass
from typing import Optional

from risk_balance import compute_risk_balance
from rules_engine import Severity


@dataclass
class FakeFinding:
    rule_id: str
    severity: Severity
    perspective: Optional[dict] = None
    title: str = "Fake finding"


def favorable(rule_id="H_TEST_01", severity=Severity.HIGH):
    return FakeFinding(rule_id=rule_id, severity=severity, perspective={"favorability": "favorable"})


def unfavorable(rule_id="H_TEST_01", severity=Severity.HIGH):
    return FakeFinding(rule_id=rule_id, severity=severity, perspective={"favorability": "unfavorable"})


def neutral(rule_id="H_TEST_01", severity=Severity.HIGH):
    return FakeFinding(rule_id=rule_id, severity=severity, perspective={"favorability": "neutral"})


def unclear(rule_id="H_TEST_01", severity=Severity.HIGH):
    return FakeFinding(rule_id=rule_id, severity=severity, perspective={"favorability": "unclear"})


def no_perspective(rule_id="H_TEST_01", severity=Severity.HIGH):
    return FakeFinding(rule_id=rule_id, severity=severity, perspective=None)


class TestNotApplicable:
    def test_no_findings_is_not_applicable(self):
        report = compute_risk_balance([])
        assert report.applicable is False
        assert report.balance_score is None

    def test_findings_with_no_perspective_are_not_applicable(self):
        report = compute_risk_balance([no_perspective(), no_perspective()])
        assert report.applicable is False

    def test_only_neutral_and_unclear_findings_are_not_applicable(self):
        # Neutral/unclear findings exist but there's nothing DIRECTIONAL to
        # score a balance from.
        report = compute_risk_balance([neutral(), unclear()])
        assert report.applicable is False
        assert report.neutral_count == 1
        assert report.unclear_count == 1


class TestBalanceScore:
    def test_entirely_unfavorable_scores_100(self):
        report = compute_risk_balance([unfavorable(), unfavorable()])
        assert report.applicable is True
        assert report.balance_score == 100

    def test_entirely_favorable_scores_0(self):
        report = compute_risk_balance([favorable(), favorable()])
        assert report.applicable is True
        assert report.balance_score == 0

    def test_evenly_split_scores_50(self):
        report = compute_risk_balance([favorable(), unfavorable()])
        assert report.balance_score == 50

    def test_neutral_and_unclear_do_not_affect_the_ratio(self):
        # 1 favorable, 3 unfavorable among directional findings -> 75,
        # regardless of how many neutral/unclear findings also exist.
        report = compute_risk_balance([
            favorable(), unfavorable(), unfavorable(), unfavorable(),
            neutral(), neutral(), unclear(),
        ])
        assert report.balance_score == 75
        assert report.neutral_count == 2
        assert report.unclear_count == 1


class TestTopContributors:
    def test_top_contributors_are_unfavorable_only(self):
        report = compute_risk_balance([
            favorable(rule_id="H_FAVORABLE_01"),
            unfavorable(rule_id="H_UNFAVORABLE_01", severity=Severity.CRITICAL),
        ])
        assert len(report.top_unfavorable_contributors) == 1
        assert report.top_unfavorable_contributors[0]["rule_id"] == "H_UNFAVORABLE_01"

    def test_top_contributors_sorted_most_severe_first(self):
        report = compute_risk_balance([
            unfavorable(rule_id="H_MED_01", severity=Severity.MEDIUM),
            unfavorable(rule_id="H_CRIT_01", severity=Severity.CRITICAL),
        ])
        assert report.top_unfavorable_contributors[0]["rule_id"] == "H_CRIT_01"

    def test_top_contributors_capped_at_five(self):
        findings = [unfavorable(rule_id=f"H_TEST_{i:02d}") for i in range(8)]
        report = compute_risk_balance(findings)
        assert len(report.top_unfavorable_contributors) == 5
        assert report.unfavorable_count == 8


class TestAsDict:
    def test_as_dict_has_expected_keys(self):
        report = compute_risk_balance([unfavorable()])
        d = report.as_dict()
        assert set(d.keys()) == {
            "applicable", "balance_score", "favorable_count", "unfavorable_count",
            "neutral_count", "unclear_count", "top_unfavorable_contributors", "methodology_note",
        }


class TestEndToEndIntegration:
    def test_analyze_result_includes_risk_balance(self, rule_engine):
        text = (
            "The Company may terminate this Agreement for convenience upon 30 days notice. "
            "Client shall indemnify Company for all claims arising from this Agreement."
        )
        result = rule_engine.analyze(text)
        assert "risk_balance" in result
        rb = result["risk_balance"]
        assert isinstance(rb["applicable"], bool)

    def test_overall_risk_is_unchanged_by_risk_balance(self, rule_engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        result = rule_engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert "risk_balance" in result

    def test_document_with_no_directional_findings_is_not_applicable_end_to_end(self, rule_engine):
        result = rule_engine.analyze("")
        assert result["risk_balance"]["applicable"] is False
