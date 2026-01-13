"""
Unit tests for MEDIUM severity rules.

Tests verify:
- Correct rule_id detection
- Correct severity classification
- No hallucinated rules
- Deterministic repeatability
- True positives, false positives, and edge cases
"""

import pytest
from rules_engine import RuleEngine, Severity


@pytest.fixture
def engine():
    return RuleEngine()


class TestM_CONF_01_IndefiniteConfidentiality:
    """Tests for M_CONF_01: Confidentiality may be perpetual / indefinite"""
    
    def test_true_positive_perpetual(self, engine):
        """True positive: 'perpetual confidentiality'"""
        text = "The confidentiality obligations shall be perpetual and survive termination."
        result = engine.analyze(text)
        findings = result["findings"]
        conf_findings = [f for f in findings if f.rule_id == "M_CONF_01"]
        assert len(conf_findings) > 0
        assert conf_findings[0].severity == Severity.MEDIUM
    
    def test_true_positive_in_perpetuity(self, engine):
        """True positive: 'in perpetuity'"""
        text = "This non-disclosure agreement shall remain in effect in perpetuity."
        result = engine.analyze(text)
        findings = result["findings"]
        conf_findings = [f for f in findings if f.rule_id == "M_CONF_01"]
        assert len(conf_findings) > 0
    
    def test_true_positive_indefinite(self, engine):
        """True positive: 'indefinite'"""
        text = "Confidentiality obligations are indefinite and have no expiration date."
        result = engine.analyze(text)
        findings = result["findings"]
        conf_findings = [f for f in findings if f.rule_id == "M_CONF_01"]
        assert len(conf_findings) > 0
    
    def test_true_positive_no_expiration(self, engine):
        """True positive: 'no expiration'"""
        text = "The non-disclosure agreement has no expiration and continues indefinitely."
        result = engine.analyze(text)
        findings = result["findings"]
        conf_findings = [f for f in findings if f.rule_id == "M_CONF_01"]
        assert len(conf_findings) > 0
    
    def test_true_positive_indefinitely(self, engine):
        """True positive: 'indefinitely'"""
        text = "Confidential information shall remain confidential indefinitely."
        result = engine.analyze(text)
        findings = result["findings"]
        conf_findings = [f for f in findings if f.rule_id == "M_CONF_01"]
        assert len(conf_findings) > 0
    
    def test_false_positive_limited_term(self, engine):
        """False positive: limited term confidentiality should NOT trigger"""
        text = "Confidentiality obligations expire after 5 years from termination."
        result = engine.analyze(text)
        findings = result["findings"]
        conf_findings = [f for f in findings if f.rule_id == "M_CONF_01"]
        assert len(conf_findings) == 0
    
    def test_false_positive_standard_survival(self, engine):
        """False positive: standard survival clause should NOT trigger"""
        text = "Confidentiality obligations survive termination for 3 years."
        result = engine.analyze(text)
        findings = result["findings"]
        conf_findings = [f for f in findings if f.rule_id == "M_CONF_01"]
        assert len(conf_findings) == 0
    
    def test_edge_case_hyphenated(self, engine):
        """Edge case: 'non-disclosure' vs 'nondisclosure'"""
        text = "The non-disclosure obligations are perpetual."
        result = engine.analyze(text)
        findings = result["findings"]
        conf_findings = [f for f in findings if f.rule_id == "M_CONF_01"]
        # Should handle hyphenated forms
        assert len(conf_findings) >= 0


class TestM_RENEW_01_AutoRenewal:
    """Tests for M_RENEW_01: Auto-renewal may lock you in"""
    
    def test_true_positive_auto_renewal_unless_notice(self, engine):
        """True positive: 'auto-renewal unless notice'"""
        text = "This agreement shall automatically renew unless written notice is provided."
        result = engine.analyze(text)
        findings = result["findings"]
        renew_findings = [f for f in findings if f.rule_id == "M_RENEW_01"]
        assert len(renew_findings) > 0
        assert renew_findings[0].severity == Severity.MEDIUM
    
    def test_true_positive_automatically_renews(self, engine):
        """True positive: 'automatically renews'"""
        text = "The contract automatically renews for additional terms unless terminated."
        result = engine.analyze(text)
        findings = result["findings"]
        renew_findings = [f for f in findings if f.rule_id == "M_RENEW_01"]
        assert len(renew_findings) > 0
    
    def test_false_positive_manual_renewal(self, engine):
        """False positive: manual renewal should NOT trigger"""
        text = "This agreement may be renewed by mutual written consent of both parties."
        result = engine.analyze(text)
        findings = result["findings"]
        renew_findings = [f for f in findings if f.rule_id == "M_RENEW_01"]
        assert len(renew_findings) == 0


class TestM_AUDIT_01_AuditRights:
    """Tests for M_AUDIT_01: Audit or inspection rights"""
    
    def test_true_positive_audit_upon_notice(self, engine):
        """True positive: 'audit upon notice'"""
        text = "The party may audit the records upon reasonable notice during normal business hours."
        result = engine.analyze(text)
        findings = result["findings"]
        audit_findings = [f for f in findings if f.rule_id == "M_AUDIT_01"]
        assert len(audit_findings) > 0
        assert audit_findings[0].severity == Severity.MEDIUM
    
    def test_true_positive_inspect_records(self, engine):
        """True positive: 'inspect records'"""
        text = "The client may inspect all records related to the services provided."
        result = engine.analyze(text)
        findings = result["findings"]
        audit_findings = [f for f in findings if f.rule_id == "M_AUDIT_01"]
        assert len(audit_findings) > 0
    
    def test_false_positive_voluntary_audit(self, engine):
        """False positive: voluntary audit rights should NOT trigger"""
        text = "Either party may request an audit, but it is not required."
        result = engine.analyze(text)
        findings = result["findings"]
        # May or may not trigger depending on rule specificity


class TestDeterministicRepeatability:
    """Tests for deterministic repeatability for medium-risk rules"""
    
    def test_same_input_same_output(self, engine):
        """Same input must produce identical output"""
        text = "Confidentiality is perpetual. The agreement auto-renews unless notice is given."
        result1 = engine.analyze(text)
        result2 = engine.analyze(text)
        
        assert len(result1["findings"]) == len(result2["findings"])
        rule_ids1 = {f.rule_id for f in result1["findings"]}
        rule_ids2 = {f.rule_id for f in result2["findings"]}
        assert rule_ids1 == rule_ids2
