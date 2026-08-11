"""
Regression tests for confidentiality_policy_engine.py — Batch A adapter
1 of 3. Focused on the semantic-topology decisions unique to
confidentiality (duration adequacy, exclusion completeness, mutual
symmetry verification) rather than re-testing what policy_engine_core.py
already covers via the first three adapters.
"""
from dataclasses import dataclass
from typing import List, Optional

import confidentiality_policy_engine as ce
import policy_engine_core as core


@dataclass
class FakePolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = "Legal Director"
    fallback_text: Optional[str] = "Approved fallback confidentiality language."
    required_exclusions_json: Optional[List[str]] = None
    min_protection_duration_years: Optional[int] = 3
    max_exposure_duration_years: Optional[int] = None
    require_mutual_confidentiality: bool = True


def evaluate(text: str, **policy_kwargs) -> core.PolicyDecision:
    policy = FakePolicy(**policy_kwargs)
    facts = ce.extract_confidentiality_facts(text)
    return ce.evaluate_confidentiality_policy(facts, policy, source="Test Playbook v1")


class TestNoClause:
    def test_no_confidentiality_language_is_not_applicable(self):
        d = evaluate("9. Governing Law. This Agreement is governed by Delaware law.")
        assert d.state == core.NOT_APPLICABLE

    def test_negated_mention_is_not_applicable(self):
        d = evaluate("9. Governing Law. No confidentiality obligation is created under this Agreement.")
        assert d.state == core.NOT_APPLICABLE


class TestMutualObligation:
    def test_clean_mutual_obligation_accepts(self):
        text = (
            "10. Confidentiality. Each party shall protect the confidentiality of the other "
            "party's Confidential Information using reasonable care, for a period of 5 years "
            "after the termination of this Agreement. Confidential Information does not "
            "include information that is publicly known, independently developed by the "
            "receiving party, rightfully received from a third party, or required by law to "
            "be disclosed."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT

    def test_reciprocal_resolves_the_same_regardless_of_side(self):
        text = (
            "10. Confidentiality. Each party shall protect the confidentiality of the other "
            "party's Confidential Information using reasonable care, for a period of 5 years."
        )
        d_sell = evaluate(text, contract_side="sell_side")
        d_buy = evaluate(text, contract_side="buy_side")
        assert d_sell.state == d_buy.state == core.ACCEPT


class TestDirectionalResolution:
    def test_unrecognized_party_names_never_silently_pick_a_side(self):
        text = (
            "10. Confidentiality. Acme shall protect the confidentiality of Globex's "
            "Confidential Information using reasonable care, for a period of 5 years."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_mutual_policy_facing_directional_obligation_requires_review(self):
        text = (
            "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
            "Confidential Information using reasonable care, for a period of 5 years."
        )
        d = evaluate(text, contract_side="mutual")
        assert d.state == core.REQUIRES_REVIEW


class TestDurationAdequacy:
    def test_adequate_protection_duration_accepts(self):
        text = (
            "10. Confidentiality. Customer shall protect the confidentiality of Vendor's "
            "Confidential Information using reasonable care, for a period of 5 years."
        )
        d = evaluate(text, min_protection_duration_years=3)
        assert d.state == core.ACCEPT

    def test_inadequate_protection_duration_negotiates(self):
        text = (
            "10. Confidentiality. Customer shall protect the confidentiality of Vendor's "
            "Confidential Information using reasonable care, for a period of 1 year."
        )
        d = evaluate(text, min_protection_duration_years=3)
        assert d.state == core.NEGOTIATE

    def test_missing_duration_must_redline(self):
        text = (
            "10. Confidentiality. Customer shall protect the confidentiality of Vendor's "
            "Confidential Information using reasonable care."
        )
        d = evaluate(text, min_protection_duration_years=3)
        assert d.state == core.MUST_REDLINE

    def test_perpetual_protection_satisfies_any_minimum(self):
        text = (
            "10. Confidentiality. Customer shall protect the confidentiality of Vendor's "
            "Confidential Information using reasonable care, in perpetuity."
        )
        d = evaluate(text, min_protection_duration_years=10)
        assert d.state == core.ACCEPT

    def test_perpetual_exposure_escalates_when_max_configured(self):
        text = (
            "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
            "Confidential Information using reasonable care, in perpetuity."
        )
        d = evaluate(text, max_exposure_duration_years=10, min_protection_duration_years=None)
        assert d.state == core.ESCALATE


class TestExclusionCompleteness:
    def test_all_required_exclusions_present_accepts(self):
        text = (
            "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
            "Confidential Information using reasonable care, for 5 years. Confidential "
            "Information does not include information that is publicly known, independently "
            "developed by the receiving party, rightfully received from a third party, or "
            "required by law to be disclosed."
        )
        d = evaluate(text, required_exclusions_json=["public_knowledge", "required_by_law"],
                     min_protection_duration_years=None, require_mutual_confidentiality=False)
        assert d.state == core.ACCEPT

    def test_missing_required_exclusion_negotiates(self):
        text = (
            "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
            "Confidential Information using reasonable care, for 5 years."
        )
        d = evaluate(text, required_exclusions_json=["public_knowledge", "required_by_law"],
                     min_protection_duration_years=None)
        assert d.state == core.NEGOTIATE


class TestMutualityRequirement:
    def test_unilateral_exposure_with_no_reciprocal_protection_negotiates(self):
        text = (
            "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
            "Confidential Information using reasonable care, for 5 years."
        )
        d = evaluate(text, require_mutual_confidentiality=True, min_protection_duration_years=None)
        assert d.state == core.NEGOTIATE

    def test_unilateral_exposure_accepted_when_mutuality_not_required(self):
        text = (
            "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
            "Confidential Information using reasonable care, for 5 years."
        )
        d = evaluate(text, require_mutual_confidentiality=False, min_protection_duration_years=None)
        assert d.state == core.ACCEPT


class TestMutualSymmetryVerification:
    def test_genuinely_mutual_with_no_attribution_accepts(self):
        text = (
            "10. Confidentiality. Each party shall protect the confidentiality of the other "
            "party's Confidential Information using reasonable care, for a period of 5 years."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT

    def test_differentiated_duration_requires_review(self):
        text = (
            "10. Confidentiality. Each party shall protect the confidentiality of the other "
            "party's Confidential Information using reasonable care; provided, that Vendor's "
            "confidentiality obligations under this Section last for 5 years, and Customer's "
            "confidentiality obligations under this Section last for 1 year."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_agreeing_per_party_attribution_still_accepts(self):
        text = (
            "10. Confidentiality. Each party shall protect the confidentiality of the other "
            "party's Confidential Information using reasonable care; Vendor's confidentiality "
            "obligations under this Section last for 5 years, and Customer's confidentiality "
            "obligations under this Section last for 5 years."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT

    def test_differentiated_standard_of_care_requires_review(self):
        # Regression test for a window-bleed bug: without bounding a
        # role's local window at the START of the next role's own
        # attribution, "same as own" appearing in Customer's clause could
        # leak into Vendor's classification window and be picked up by
        # _classify_care's priority check (same_as_own checked before
        # reasonable, regardless of position), masking a real difference.
        text = (
            "10. Confidentiality. Each party shall protect the confidentiality of the other "
            "party's Confidential Information; provided, that Vendor's confidentiality "
            "obligations under this Section require reasonable care, and Customer's "
            "confidentiality obligations under this Section require the same degree of care "
            "Customer uses to protect its own confidential information."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW
