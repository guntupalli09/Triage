"""
Regression tests for assignment_policy_engine.py — Batch A adapter 2 of
3. Focused on the semantic-topology decisions unique to assignment
(consent standard, exception completeness, mutual symmetry verification)
rather than re-testing what policy_engine_core.py already covers.
"""
from dataclasses import dataclass
from typing import List, Optional

import assignment_policy_engine as ae
import policy_engine_core as core


@dataclass
class FakePolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = "Legal Director"
    fallback_text: Optional[str] = "Approved fallback assignment language."
    required_exceptions_json: Optional[List[str]] = None
    prohibit_sole_discretion_consent: bool = True
    require_consent_for_counterparty_assignment: bool = True


def evaluate(text: str, **policy_kwargs) -> core.PolicyDecision:
    policy = FakePolicy(**policy_kwargs)
    facts = ae.extract_assignment_facts(text)
    return ae.evaluate_assignment_policy(facts, policy, source="Test Playbook v1")


class TestNoClause:
    def test_no_assignment_language_is_not_applicable(self):
        d = evaluate("9. Governing Law. This Agreement is governed by Delaware law.")
        assert d.state == core.NOT_APPLICABLE

    def test_negated_mention_is_not_applicable(self):
        d = evaluate("9. Governing Law. No assignment of this Agreement is permitted under any circumstances.")
        assert d.state == core.NOT_APPLICABLE


class TestMutualRestriction:
    def test_clean_mutual_restriction_accepts(self):
        text = (
            "16. Assignment. Neither party may assign this Agreement without the prior "
            "written consent of the other party, not to be unreasonably withheld, except "
            "that either party may assign this Agreement to an affiliate or in connection "
            "with a merger, acquisition, or change of control."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT

    def test_reciprocal_resolves_the_same_regardless_of_side(self):
        text = (
            "16. Assignment. Neither party may assign this Agreement without the prior "
            "written consent of the other party, not to be unreasonably withheld, except "
            "that either party may assign this Agreement to an affiliate."
        )
        d_sell = evaluate(text, contract_side="sell_side", required_exceptions_json=["affiliate"])
        d_buy = evaluate(text, contract_side="buy_side", required_exceptions_json=["affiliate"])
        assert d_sell.state == d_buy.state == core.ACCEPT


class TestDirectionalResolution:
    def test_unrecognized_party_names_never_silently_pick_a_side(self):
        text = (
            "16. Assignment. Acme may not assign this Agreement without the prior written "
            "consent of Globex."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_mutual_policy_facing_directional_restriction_requires_review(self):
        text = (
            "16. Assignment. Vendor may not assign this Agreement without the prior written "
            "consent of Customer."
        )
        d = evaluate(text, contract_side="mutual")
        assert d.state == core.REQUIRES_REVIEW


class TestConsentStandard:
    def test_sole_discretion_consent_negotiates_when_prohibited(self):
        text = (
            "16. Assignment. Vendor may not assign this Agreement without the prior written "
            "consent of Customer, which consent may be withheld in its sole discretion."
        )
        d = evaluate(text, prohibit_sole_discretion_consent=True, require_consent_for_counterparty_assignment=False)
        assert d.state == core.NEGOTIATE

    def test_reasonable_consent_standard_accepts(self):
        text = (
            "16. Assignment. Vendor may not assign this Agreement without the prior written "
            "consent of Customer, not to be unreasonably withheld."
        )
        d = evaluate(text, require_consent_for_counterparty_assignment=False)
        assert d.state == core.ACCEPT


class TestExceptionCompleteness:
    def test_required_exception_present_accepts(self):
        text = (
            "16. Assignment. Vendor may not assign this Agreement without the prior written "
            "consent of Customer, except that Vendor may assign this Agreement to an "
            "affiliate or in connection with a merger or acquisition."
        )
        d = evaluate(text, required_exceptions_json=["affiliate", "merger_acquisition"],
                     require_consent_for_counterparty_assignment=False)
        assert d.state == core.ACCEPT

    def test_missing_required_exception_negotiates(self):
        text = (
            "16. Assignment. Vendor may not assign this Agreement without the prior written "
            "consent of Customer."
        )
        d = evaluate(text, required_exceptions_json=["affiliate", "merger_acquisition"],
                     require_consent_for_counterparty_assignment=False)
        assert d.state == core.NEGOTIATE


class TestMutualityRequirement:
    def test_unilateral_restriction_with_no_reciprocal_negotiates(self):
        text = (
            "16. Assignment. Vendor may not assign this Agreement without the prior written "
            "consent of Customer."
        )
        d = evaluate(text, require_consent_for_counterparty_assignment=True)
        assert d.state == core.NEGOTIATE

    def test_unrestricted_assignment_negotiates_when_consent_required(self):
        text = (
            "16. Assignment. Either party may assign this Agreement without prior consent."
        )
        d = evaluate(text, require_consent_for_counterparty_assignment=True)
        assert d.state == core.NEGOTIATE

    def test_unrestricted_assignment_accepted_when_not_required(self):
        text = (
            "16. Assignment. Either party may assign this Agreement without prior consent."
        )
        d = evaluate(text, require_consent_for_counterparty_assignment=False)
        assert d.state == core.ACCEPT


class TestMutualSymmetryVerification:
    def test_genuinely_mutual_with_no_attribution_accepts(self):
        text = (
            "16. Assignment. Neither party may assign this Agreement without the prior "
            "written consent of the other party, not to be unreasonably withheld."
        )
        d = evaluate(text, require_consent_for_counterparty_assignment=False)
        assert d.state == core.ACCEPT

    def test_differentiated_consent_standard_requires_review(self):
        text = (
            "16. Assignment. Neither party may assign this Agreement without the prior "
            "written consent of the other party; provided, that Vendor's assignment rights "
            "under this Section require consent not to be unreasonably withheld, and "
            "Customer's assignment rights under this Section require consent in its sole "
            "discretion."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_agreeing_per_party_attribution_still_accepts(self):
        text = (
            "16. Assignment. Neither party may assign this Agreement without the prior "
            "written consent of the other party; Vendor's assignment rights under this "
            "Section require consent not to be unreasonably withheld, and Customer's "
            "assignment rights under this Section require consent not to be unreasonably "
            "withheld."
        )
        d = evaluate(text, require_consent_for_counterparty_assignment=False)
        assert d.state == core.ACCEPT
