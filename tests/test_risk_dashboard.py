"""
Tests for the Three-Score Risk Dashboard (Legal Risk / Business Risk /
Negotiation Difficulty) — see risk_dashboard.py.

Unit tests exercise compute_risk_dashboard() directly against synthetic
findings (fast, precise control over severity/rule_id combinations).
Integration tests exercise RuleEngine.analyze() end-to-end to confirm the
dashboard is wired in as an additive layer, same pattern as
tests/test_workflow_decision.py for signature_readiness.
"""

from dataclasses import dataclass

from risk_dashboard import compute_risk_dashboard
from rules_engine import Severity


@dataclass
class FakeFinding:
    """Minimal stand-in for rules_engine.Finding — compute_risk_dashboard()
    only touches rule_id/severity/title, so a full Finding isn't needed for
    unit-level control over inputs."""
    rule_id: str
    severity: Severity
    title: str = "Fake finding"


class TestBucketClassification:
    def test_finding_with_no_matching_keywords_scores_zero_everywhere(self):
        findings = [FakeFinding(rule_id="H_PUBLICITY_01", severity=Severity.HIGH)]
        dashboard = compute_risk_dashboard(findings)
        assert dashboard.legal_risk.score == 0
        assert dashboard.business_risk.score == 0
        assert dashboard.negotiation_difficulty.score == 0

    def test_liability_finding_counts_toward_business_risk_only(self):
        findings = [FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH)]
        dashboard = compute_risk_dashboard(findings)
        assert dashboard.business_risk.score == 12  # HIGH weight
        assert dashboard.legal_risk.score == 0
        assert dashboard.negotiation_difficulty.score == 0

    def test_arbitration_finding_counts_toward_legal_risk_only(self):
        findings = [FakeFinding(rule_id="H_ARBITRATION_01", severity=Severity.HIGH)]
        dashboard = compute_risk_dashboard(findings)
        assert dashboard.legal_risk.score == 12
        assert dashboard.business_risk.score == 0

    def test_unilateral_finding_counts_toward_negotiation_difficulty_only(self):
        findings = [FakeFinding(rule_id="H_UNILATERAL_MOD_01", severity=Severity.HIGH)]
        dashboard = compute_risk_dashboard(findings)
        assert dashboard.negotiation_difficulty.score == 12
        assert dashboard.legal_risk.score == 0
        assert dashboard.business_risk.score == 0

    def test_a_finding_can_match_more_than_one_bucket(self):
        # ASYMMETRIC appears in both BUSINESS_RISK_KEYWORDS (via LIAB
        # substring match on ASYMMETRIC_LIABILITY) and
        # NEGOTIATION_DIFFICULTY_KEYWORDS (ASYMMETRIC directly).
        findings = [FakeFinding(rule_id="H_ASYMMETRIC_LIABILITY_01", severity=Severity.HIGH)]
        dashboard = compute_risk_dashboard(findings)
        assert dashboard.business_risk.score == 12
        assert dashboard.negotiation_difficulty.score == 12


class TestSeverityWeighting:
    def test_critical_weighs_more_than_high(self):
        crit = compute_risk_dashboard([FakeFinding(rule_id="H_LOL_01", severity=Severity.CRITICAL)])
        high = compute_risk_dashboard([FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH)])
        assert crit.business_risk.score > high.business_risk.score

    def test_scores_accumulate_across_multiple_findings_in_same_bucket(self):
        findings = [
            FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH),
            FakeFinding(rule_id="H_INDEM_01", severity=Severity.HIGH),
        ]
        dashboard = compute_risk_dashboard(findings)
        assert dashboard.business_risk.score == 24  # 12 + 12

    def test_score_is_capped_at_100(self):
        findings = [FakeFinding(rule_id=f"H_LOL_{i:02d}", severity=Severity.CRITICAL) for i in range(10)]
        dashboard = compute_risk_dashboard(findings)
        assert dashboard.business_risk.score == 100


class TestEmptyInput:
    def test_no_findings_produces_all_zero_scores(self):
        dashboard = compute_risk_dashboard([])
        assert dashboard.legal_risk.score == 0
        assert dashboard.business_risk.score == 0
        assert dashboard.negotiation_difficulty.score == 0
        assert dashboard.legal_risk.top_contributors == []


class TestTopContributors:
    def test_top_contributors_are_sorted_most_severe_first(self):
        findings = [
            FakeFinding(rule_id="H_LOL_01", severity=Severity.MEDIUM, title="Medium liability"),
            FakeFinding(rule_id="H_LOL_02", severity=Severity.CRITICAL, title="Critical liability"),
        ]
        dashboard = compute_risk_dashboard(findings)
        top = dashboard.business_risk.top_contributors
        assert top[0]["rule_id"] == "H_LOL_02"
        assert top[0]["severity"] == "critical"

    def test_top_contributors_capped_at_five(self):
        findings = [FakeFinding(rule_id=f"H_LOL_{i:02d}", severity=Severity.LOW) for i in range(8)]
        dashboard = compute_risk_dashboard(findings)
        assert len(dashboard.business_risk.top_contributors) == 5
        assert dashboard.business_risk.matched_finding_count == 8


class TestAsDict:
    def test_as_dict_has_expected_keys(self):
        dashboard = compute_risk_dashboard([FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH)])
        d = dashboard.as_dict()
        assert set(d.keys()) == {
            "legal_risk_score", "business_risk_score", "negotiation_difficulty_score",
            "legal_risk_contributors", "business_risk_contributors",
            "negotiation_difficulty_contributors", "methodology_note",
        }
        assert d["business_risk_score"] == 12


class TestEndToEndIntegration:
    """The dashboard must be wired into RuleEngine.analyze() as an additive
    layer, same pattern as signature_readiness — never replacing
    overall_risk or rule_counts. `engine` comes from tests/conftest.py."""

    def test_analyze_result_includes_risk_dashboard(self, rule_engine):
        text = (
            "The Contractor shall indemnify the Client for all claims. "
            "In no event shall Vendor's liability be limited under this Agreement, without limit."
        )
        result = rule_engine.analyze(text)
        assert "risk_dashboard" in result
        dashboard = result["risk_dashboard"]
        for key in ("legal_risk_score", "business_risk_score", "negotiation_difficulty_score"):
            assert key in dashboard
            assert isinstance(dashboard[key], int)
            assert 0 <= dashboard[key] <= 100

    def test_overall_risk_is_unchanged_by_the_dashboard(self, rule_engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        result = rule_engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert "risk_dashboard" in result

    def test_document_with_no_findings_has_all_zero_scores(self, rule_engine):
        result = rule_engine.analyze("")
        dashboard = result["risk_dashboard"]
        assert dashboard["legal_risk_score"] == 0
        assert dashboard["business_risk_score"] == 0
        assert dashboard["negotiation_difficulty_score"] == 0
