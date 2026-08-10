"""
Regression tests for termination_policy_engine.py — the third clause
adapter over policy_engine_core. Focused on the semantic-topology
decisions unique to termination (multiple independently-true rights per
document, notice/cure adequacy, mutual-right verification, survival
completeness, termination fee) rather than re-testing what
policy_engine_core.py already covers via the first two adapters.
"""
from dataclasses import dataclass
from typing import List, Optional

import termination_policy_engine as te
import policy_engine_core as core


@dataclass
class FakePolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = "Legal Director"
    fallback_text: Optional[str] = "Approved fallback termination language."
    require_mutual_convenience_termination: bool = True
    min_notice_days_against_us: Optional[int] = 60
    min_cure_days_against_us: Optional[int] = 30
    prohibit_immediate_termination_for_cause: bool = False
    required_survival_topics_json: Optional[List[str]] = None
    prohibit_uncapped_termination_fee: bool = True
    fee_preferred_multiplier: Optional[float] = 1.0
    fee_acceptable_max_multiplier: Optional[float] = 2.0
    fee_negotiate_max_multiplier: Optional[float] = 3.0


def evaluate(text: str, **policy_kwargs) -> core.PolicyDecision:
    policy = FakePolicy(**policy_kwargs)
    facts = te.extract_termination_facts(text)
    return te.evaluate_termination_policy(facts, policy, source="Test Playbook v1")


class TestNoClause:
    def test_no_termination_language_is_not_applicable(self):
        d = evaluate("9. Governing Law. This Agreement is governed by Delaware law.")
        assert d.state == core.NOT_APPLICABLE

    def test_negated_mention_is_not_applicable(self):
        d = evaluate("9. Governing Law. No termination right is granted under this Agreement.")
        assert d.state == core.NOT_APPLICABLE


class TestMultipleIndependentRights:
    def test_convenience_cause_and_insolvency_rights_coexist(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice. Either party may terminate this Agreement for cause "
            "if the other party materially breaches this Agreement and fails to cure such "
            "breach within 30 days after written notice. Either party may terminate this "
            "Agreement immediately upon the other party's insolvency or bankruptcy."
        )
        facts = te.extract_termination_facts(text)
        assert {r.trigger_type for r in facts.rights} == {"convenience", "material_breach", "insolvency"}

    def test_rights_are_not_reconciled_into_one_controlling_provision(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice. Either party may terminate this Agreement for cause "
            "if the other party materially breaches this Agreement and fails to cure such "
            "breach within 30 days after written notice."
        )
        facts = te.extract_termination_facts(text)
        assert len(facts.rights) == 2

    def test_insolvency_trigger_is_conventionally_immediate_not_flagged_as_missing_cure(self):
        text = (
            "15. Termination. Either party may terminate this Agreement immediately upon the "
            "other party's insolvency or bankruptcy."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT


class TestDirectionalRightResolution:
    def test_returns_decision_object_from_shared_core(self):
        text = (
            "15. Termination. Vendor may terminate this Agreement for convenience upon 90 "
            "days prior written notice."
        )
        d = evaluate(text)
        assert isinstance(d, core.PolicyDecision)

    def test_unrecognized_party_names_never_silently_pick_a_side(self):
        text = (
            "15. Termination. Acme may terminate this Agreement for convenience upon 90 days "
            "prior written notice."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_mutual_policy_facing_directional_right_requires_review(self):
        text = (
            "15. Termination. Vendor may terminate this Agreement for convenience upon 90 "
            "days prior written notice."
        )
        d = evaluate(text, contract_side="mutual")
        assert d.state == core.REQUIRES_REVIEW

    def test_our_own_right_alone_is_not_a_risk(self):
        # We (Vendor) hold a convenience right; nothing is stated about
        # Customer holding one against us — nothing to bound.
        text = (
            "15. Termination. Vendor may terminate this Agreement for convenience upon 30 "
            "days prior written notice."
        )
        d = evaluate(text, require_mutual_convenience_termination=False)
        assert d.state == core.ACCEPT


class TestNoticeAdequacy:
    def test_adequate_notice_accepts(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice."
        )
        d = evaluate(text, min_notice_days_against_us=60)
        assert d.state == core.ACCEPT

    def test_inadequate_notice_negotiates(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "10 days prior written notice."
        )
        d = evaluate(text, min_notice_days_against_us=60)
        assert d.state == core.NEGOTIATE

    def test_missing_notice_period_must_redline(self):
        text = "15. Termination. Either party may terminate this Agreement for convenience."
        d = evaluate(text)
        assert d.state == core.MUST_REDLINE


class TestCureAdequacy:
    def test_adequate_cure_accepts(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for cause if the "
            "other party materially breaches this Agreement and fails to cure such breach "
            "within 30 days after written notice."
        )
        d = evaluate(text, min_cure_days_against_us=30)
        assert d.state == core.ACCEPT

    def test_inadequate_cure_negotiates(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for cause if the "
            "other party materially breaches this Agreement and fails to cure such breach "
            "within 5 days after written notice."
        )
        d = evaluate(text, min_cure_days_against_us=30)
        assert d.state == core.NEGOTIATE

    def test_missing_cure_period_must_redline(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for cause if the "
            "other party materially breaches this Agreement."
        )
        d = evaluate(text)
        assert d.state == core.MUST_REDLINE

    def test_immediate_termination_for_cause_escalates(self):
        text = (
            "15. Termination. Either party may terminate this Agreement immediately upon a "
            "material breach of this Agreement by the other party, without opportunity to cure."
        )
        d = evaluate(text, prohibit_immediate_termination_for_cause=False)
        assert d.state == core.ESCALATE

    def test_immediate_termination_for_cause_prohibited_when_policy_requires(self):
        text = (
            "15. Termination. Either party may terminate this Agreement immediately upon a "
            "material breach of this Agreement by the other party, without opportunity to cure."
        )
        d = evaluate(text, prohibit_immediate_termination_for_cause=True)
        assert d.state == core.PROHIBITED


class TestMutuality:
    def test_counterparty_only_convenience_right_negotiates_when_mutuality_required(self):
        text = (
            "15. Termination. Customer may terminate this Agreement for convenience upon 90 "
            "days prior written notice."
        )
        d = evaluate(text, require_mutual_convenience_termination=True)
        assert d.state == core.NEGOTIATE

    def test_mutual_convenience_right_accepts(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice."
        )
        d = evaluate(text, require_mutual_convenience_termination=True)
        assert d.state == core.ACCEPT


class TestSurvivalCompleteness:
    def test_required_survival_topics_present_accepts(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice. The following provisions shall survive termination "
            "of this Agreement: Confidentiality, Limitation of Liability, and accrued but "
            "unpaid payment obligations."
        )
        d = evaluate(text, required_survival_topics_json=["confidentiality", "limitation_of_liability"])
        assert d.state == core.ACCEPT

    def test_missing_survival_topic_negotiates(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice. The following provisions shall survive termination "
            "of this Agreement: Confidentiality."
        )
        d = evaluate(text, required_survival_topics_json=["confidentiality", "limitation_of_liability"])
        assert d.state == core.NEGOTIATE

    def test_no_survival_clause_at_all_negotiates_when_required(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice."
        )
        d = evaluate(text, required_survival_topics_json=["confidentiality"])
        assert d.state == core.NEGOTIATE

    def test_no_survival_requirement_configured_is_unaffected_by_absence(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice."
        )
        d = evaluate(text, required_survival_topics_json=[])
        assert d.state == core.ACCEPT


class TestTerminationFee:
    def test_no_fee_mentioned_is_not_penalized(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT

    def test_uncapped_fee_prohibited_by_default(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice. Vendor shall pay a termination fee that shall not "
            "be subject to any cap."
        )
        d = evaluate(text)
        assert d.state == core.PROHIBITED

    def test_fixed_dollar_fee_escalates(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice. Customer shall pay a termination fee of $500,000."
        )
        d = evaluate(text)
        assert d.state == core.ESCALATE

    def test_multiplier_fee_within_preferred_accepts(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice. Customer shall pay a termination fee equal to 1 "
            "times the total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT

    def test_multiplier_fee_beyond_negotiate_escalates(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice. Customer shall pay a termination fee equal to 5 "
            "times the total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == core.ESCALATE


class TestReciprocalRightSymmetryVerification:
    """The same third directional shape found in Indemnification's
    reciprocal clauses: an "either party" opener claims symmetric
    treatment, but a differentiated proviso can state different terms per
    named party. Mirrors TestReciprocalSymmetryVerification in
    tests/test_indemnification_policy_engine.py."""

    def test_genuinely_mutual_right_with_no_attribution_accepts(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience upon "
            "90 days prior written notice."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT

    def test_differentiated_notice_periods_requires_review(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience; "
            "provided, that Vendor's right to terminate under this Section requires 90 days "
            "prior written notice, and Customer's right to terminate under this Section "
            "requires 10 days prior written notice."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_differentiated_cure_periods_requires_review(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for cause upon a "
            "material breach by the other party; provided, that Vendor's right to terminate "
            "under this Section requires a 30 days cure period, and Customer's right to "
            "terminate under this Section requires a 5 days cure period."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_agreeing_per_party_attribution_still_accepts(self):
        text = (
            "15. Termination. Either party may terminate this Agreement for convenience; "
            "Vendor's right to terminate under this Section requires 90 days prior written "
            "notice, and Customer's right to terminate under this Section requires 90 days "
            "prior written notice."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT
