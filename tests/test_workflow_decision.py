"""
Regression tests for the workflow decision layer (signature_readiness).

overall_risk/severity is a blunt "did anything HIGH fire" signal: a
publicity/press-release clause and uncapped liability + uncapped
indemnification both produce overall_risk="high", which makes prioritization
noisy for a business workflow. signature_readiness is a separate, additive
layer that classifies findings as policy-blocking, legal-review-blocking, or
non-blocking, and derives a single recommendation from that — not from raw
severity counts.
"""

import pytest
from rules_engine import (
    RuleEngine,
    Severity,
    SignatureReadiness,
    BLOCKING_RULE_IDS,
    POLICY_BLOCK_RULE_IDS,
)


@pytest.fixture
def engine():
    return RuleEngine()


class TestOverallRiskIsUnchanged:
    """The workflow layer must be additive, not a replacement for severity."""

    def test_publicity_only_contract_is_still_overall_risk_high(self, engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent, and may "
            "use the other party's name and logo in public announcements."
        )
        result = engine.analyze(text)
        assert result["overall_risk"] == "high"


class TestSeverityDoesNotDetermineBlockingAlone:
    def test_publicity_only_contract_does_not_require_legal_review(self, engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent, and may "
            "use the other party's name and logo in public announcements."
        )
        result = engine.analyze(text)
        assert result["overall_risk"] == "high"
        # Same overall_risk as the severe case below, but a nuisance clause
        # should route to commercial review, not legal review.
        assert result["signature_readiness"] == SignatureReadiness.COMMERCIAL_REVIEW_RECOMMENDED.value
        assert result["blocking_findings"] == []
        assert "H_PUBLICITY_01" in result["non_blocking_findings"]

    def test_uncapped_liability_and_indemnification_requires_legal_review(self, engine):
        text = (
            "The Contractor shall indemnify the Client for all claims, "
            "notwithstanding any limitation of liability. In no event shall "
            "Vendor's liability be limited under this Agreement, without "
            "limitation as to indirect or consequential damages."
        )
        result = engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert result["signature_readiness"] == SignatureReadiness.LEGAL_REVIEW_REQUIRED.value
        assert "H_INDEM_01" in result["blocking_findings"]
        assert "H_LOL_01" in result["blocking_findings"]

    def test_these_two_high_risk_contracts_get_different_signature_readiness(self, engine):
        publicity_text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        severe_text = (
            "The Contractor shall indemnify the Client for all claims, "
            "notwithstanding any limitation of liability. In no event shall "
            "Vendor's liability be limited under this Agreement, without "
            "limitation as to indirect or consequential damages."
        )
        publicity_result = engine.analyze(publicity_text)
        severe_result = engine.analyze(severe_text)

        # Both are overall_risk="high" -- the exact false-equivalence this
        # layer exists to break.
        assert publicity_result["overall_risk"] == severe_result["overall_risk"] == "high"
        assert publicity_result["signature_readiness"] != severe_result["signature_readiness"]


class TestPolicyBlockedTier:
    def test_ai_training_on_customer_data_is_policy_blocked(self, engine):
        text = (
            "Provider may use Customer's submitted data and input data to "
            "train its machine learning and artificial intelligence models "
            "for product improvement purposes."
        )
        result = engine.analyze(text)
        assert result["signature_readiness"] == SignatureReadiness.BLOCKED_BY_POLICY.value
        assert "H_AI_TRAINING_01" in result["policy_blocked_findings"]
        # Policy blocks are a superset of blocking_findings.
        assert "H_AI_TRAINING_01" in result["blocking_findings"]

    def test_policy_block_outranks_ordinary_legal_review(self, engine):
        text = (
            "Provider may use Customer's input data to train its machine "
            "learning models. The Contractor shall indemnify the Client for "
            "all claims, notwithstanding any limitation of liability."
        )
        result = engine.analyze(text)
        assert result["signature_readiness"] == SignatureReadiness.BLOCKED_BY_POLICY.value


class TestReadyToSend:
    def test_contract_with_no_findings_is_ready_to_send(self, engine):
        text = (
            "This Agreement is between Acme Corp and Beta Inc for the "
            "purchase of office chairs. The total price is $5,000, due upon "
            "delivery."
        )
        result = engine.analyze(text)
        assert result["findings"] == []
        assert result["signature_readiness"] == SignatureReadiness.READY_TO_SEND.value
        assert result["blocking_findings"] == []
        assert result["non_blocking_findings"] == []


class TestDowngradedFindingsDoNotBlock:
    """A finding whose severity was downgraded by suppression (e.g. mutual
    language, or 'to the extent required by law') has had its risk
    contained and must not force legal_review_required on its own."""

    def test_indemnity_limited_by_law_does_not_block(self, engine):
        text = (
            "The party shall indemnify the other party without limit, to "
            "the extent required by law, for all claims arising under this "
            "Agreement."
        )
        result = engine.analyze(text)
        indem = [f for f in result["findings"] if f.rule_id == "H_INDEM_01"]
        assert len(indem) == 1
        assert indem[0].severity == Severity.MEDIUM
        assert "H_INDEM_01" not in result["blocking_findings"]

    def test_mutual_liability_cap_does_not_block(self, engine):
        text = (
            "Both parties agree that liability shall not exceed the total "
            "fees paid in the twelve months preceding the claim."
        )
        result = engine.analyze(text)
        asym = [f for f in result["findings"] if f.rule_id == "H_ASYMMETRIC_LIABILITY_01"]
        if asym:  # only assert if the rule actually fired on this phrasing
            assert asym[0].severity != Severity.HIGH
            assert "H_ASYMMETRIC_LIABILITY_01" not in result["blocking_findings"]


class TestFindingListsAreDeduplicatedAndDisjointFromEachOther:
    def test_no_rule_id_appears_in_both_blocking_and_non_blocking(self, engine):
        text = (
            "The Contractor shall indemnify the Client for all claims, "
            "notwithstanding any limitation of liability. The parties agree "
            "that either party may issue a press release regarding this "
            "Agreement without prior written consent."
        )
        result = engine.analyze(text)
        assert set(result["blocking_findings"]).isdisjoint(set(result["non_blocking_findings"]))

    def test_blocking_findings_has_no_duplicates(self, engine):
        text = (
            "The Contractor shall indemnify the Client for all claims, "
            "notwithstanding any limitation of liability. "
            "Contractor shall indemnify Client for any and all further "
            "claims, notwithstanding any limitation of liability whatsoever."
        )
        result = engine.analyze(text)
        assert len(result["blocking_findings"]) == len(set(result["blocking_findings"]))


class TestRuleClassificationConstants:
    def test_policy_block_is_subset_of_blocking(self):
        assert POLICY_BLOCK_RULE_IDS.issubset(BLOCKING_RULE_IDS)

    def test_known_blocking_and_non_blocking_examples_from_the_spec(self):
        # These are literally the example rule_ids from the workflow-layer spec.
        assert "H_INDEM_01" in BLOCKING_RULE_IDS
        assert "H_LOL_01" in BLOCKING_RULE_IDS
        assert "H_PUBLICITY_01" not in BLOCKING_RULE_IDS
