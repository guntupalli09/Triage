"""
Regression tests for party-direction classification on "one-way" rules.

Rules like H_ATTFEE_01 ("One-way attorneys' fees"), H_CONSEQUENTIAL_01
("One-sided consequential damages waiver"), H_TERM_CONVENIENCE_01
("One-sided termination for convenience"), H_ASYMMETRIC_LIABILITY_01, and
H_INDEM_ONEWAY_01 used to fire HIGH severity on any matching clause
regardless of whether the clause was actually one-sided — a fully mutual
"either party may terminate for convenience" clause was labeled the same as
a unilateral one.

The engine now classifies party direction (obligor/beneficiary/applies_to/
mutuality_status) for these rules and downgrades severity when the clause
text itself establishes mutuality, instead of asserting one-way treatment
it can't prove.
"""

import pytest
from rules_engine import RuleEngine, Severity, ONE_WAY_RULE_IDS, _classify_party_direction


@pytest.fixture
def engine():
    return RuleEngine()


class TestClassifyPartyDirection:
    def test_either_party_is_mutual(self):
        result = _classify_party_direction("Either party may terminate this Agreement for convenience.")
        assert result["mutuality_status"] == "mutual"
        assert result["obligor"] == "both_parties"
        assert result["beneficiary"] == "both_parties"

    def test_both_parties_is_mutual(self):
        result = _classify_party_direction("Both parties agree that liability shall be capped.")
        assert result["mutuality_status"] == "mutual"

    def test_prevailing_party_idiom_is_mutual(self):
        result = _classify_party_direction(
            "The prevailing party shall recover attorneys' fees from the non-prevailing party."
        )
        assert result["mutuality_status"] == "mutual"

    def test_single_provider_role_is_provider_only(self):
        result = _classify_party_direction("Vendor may terminate this Agreement for convenience at any time.")
        assert result["mutuality_status"] == "provider-only"
        assert result["obligor"] == "provider"

    def test_single_customer_role_is_customer_only(self):
        result = _classify_party_direction("Customer may terminate this Agreement for convenience at any time.")
        assert result["mutuality_status"] == "customer-only"
        assert result["obligor"] == "customer"

    def test_both_roles_named_is_ambiguous_not_mutual(self):
        # Both named individually, no explicit mutual language -> can't safely
        # assert either mutuality or one-way direction from regex alone.
        result = _classify_party_direction("The Vendor shall indemnify the Customer for any claims.")
        assert result["mutuality_status"] == "ambiguous"

    def test_no_role_language_is_ambiguous(self):
        result = _classify_party_direction("This obligation shall survive termination of the Agreement.")
        assert result["mutuality_status"] == "ambiguous"
        assert result["obligor"] == "unknown"


class TestOneWayRuleDowngradeOnMutualLanguage:
    def test_mutual_prevailing_party_attorneys_fees_is_not_high(self, engine):
        text = (
            "In any dispute arising under this Agreement, the prevailing party "
            "shall be entitled to recover its reasonable attorneys' fees and "
            "costs from the non-prevailing party."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_ATTFEE_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.MEDIUM
        assert findings[0].party_direction["mutuality_status"] == "mutual"

    def test_mutual_consequential_damages_waiver_is_not_high(self, engine):
        text = (
            "In no event shall either party be liable to the other party for "
            "any consequential, indirect, or punitive damages arising under "
            "this Agreement."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_CONSEQUENTIAL_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.MEDIUM
        assert findings[0].party_direction["mutuality_status"] == "mutual"

    def test_mutual_termination_for_convenience_is_not_high(self, engine):
        text = (
            "Either party may terminate this Agreement for convenience at any "
            "time upon 30 days written notice to the other party."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_TERM_CONVENIENCE_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.MEDIUM
        assert findings[0].party_direction["mutuality_status"] == "mutual"

    def test_one_way_termination_for_convenience_stays_high(self, engine):
        text = (
            "Provider may terminate this Agreement for convenience at any time "
            "upon 30 days written notice, in its sole discretion."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_TERM_CONVENIENCE_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH
        assert findings[0].party_direction["mutuality_status"] == "provider-only"

    def test_rationale_notes_mutuality_when_downgraded(self, engine):
        text = (
            "Either party may terminate this Agreement for convenience at any "
            "time upon 30 days written notice to the other party."
        )
        result = engine.analyze(text)
        finding = [f for f in result["findings"] if f.rule_id == "H_TERM_CONVENIENCE_01"][0]
        assert "mutual" in finding.rationale.lower()

    def test_suppression_log_records_mutuality_downgrade(self, engine):
        text = (
            "Either party may terminate this Agreement for convenience at any "
            "time upon 30 days written notice to the other party."
        )
        result = engine.analyze(text)
        reasons = " ".join(result.get("suppression_log", {}).values()).lower()
        assert "mutual" in reasons


class TestNonOneWayRulesUnaffected:
    def test_rules_outside_one_way_set_have_no_party_direction(self, engine):
        text = "The parties agree to maintain confidentiality of all proprietary information disclosed hereunder."
        result = engine.analyze(text)
        for f in result["findings"]:
            if f.rule_id not in ONE_WAY_RULE_IDS:
                assert f.party_direction is None
