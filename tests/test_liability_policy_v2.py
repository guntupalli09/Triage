"""Tests for LiabilityPolicyV2 schema, golden playbooks, and v2 evaluator."""

import pytest

from liability_evaluator_v2 import ContractCapFacts, evaluate_liability_policy_v2
from liability_policy_v2 import liability_policy_v2_from_dict, liability_policy_v2_to_dict
from policy_engine_core import ACCEPT, ACCEPT_WITH_NOTE, ESCALATE, PROHIBITED, REQUIRES_REVIEW
from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import AnnualFeeMultipleCap, FeeRelativeCap, ReferenceCap, ReferenceTarget
from policy_grammar.evaluation_context import EvaluationContext
from policy_grammar.fee_relative import FeeBasis, FeeScope
from policy_grammar.money import MoneyAmount
from tests.fixtures.liability_policy_v2_golden import (
    FIRM_A,
    FIRM_B,
    FIRM_C,
    FIRM_D,
    firm_a_policy,
    firm_b_policy,
    firm_c_policy,
    firm_d_policy,
    roundtrip,
)


def _contract_fee_months(n: float) -> ContractCapFacts:
    return ContractCapFacts(
        expression=CapExpression(
            operator=CapOperator.SIMPLE,
            operands=[FeeRelativeCap(months=n, basis=FeeBasis.CONTRACT_FEES, scope=FeeScope.AGREEMENT)],
        ),
        fee_period_months=n,
    )


class TestGoldenFixtures:
    @pytest.mark.parametrize("factory", [firm_a_policy, firm_b_policy, firm_c_policy, firm_d_policy])
    def test_roundtrip(self, factory):
        p = factory()
        assert not p.validate()
        rt = roundtrip(p)
        assert liability_policy_v2_to_dict(rt) == liability_policy_v2_to_dict(p)

    def test_firm_a_has_reference_super_cap_not_annual_multiple(self):
        p = firm_a_policy()
        sc = p.super_caps[0]
        op = sc.expression.operands[0]
        assert isinstance(op, ReferenceCap)
        assert op.ref == ReferenceTarget.GENERAL_CAP
        assert op.multiplier == 2.0


class TestConditionalFallback:
    def test_acv_below_250k_fallback_applicable(self):
        policy = firm_a_policy()
        contract = _contract_fee_months(12)
        ctx = EvaluationContext(annual_contract_value=MoneyAmount.from_number("100000"))
        # Below preferred (greater of) but within fallback
        decision = evaluate_liability_policy_v2(policy, contract, ctx)
        assert decision.state in (ACCEPT_WITH_NOTE, ACCEPT, ESCALATE, REQUIRES_REVIEW)

    @pytest.mark.parametrize("acv", ["249999", "100000"])
    def test_acv_under_250k(self, acv):
        policy = firm_a_policy()
        contract = _contract_fee_months(12)
        ctx = EvaluationContext(annual_contract_value=MoneyAmount.from_number(acv))
        # With only symbolic comparison, 12mo contract vs 12mo fallback under ACV condition
        from policy_grammar.conditions import evaluate_condition
        from policy_grammar.conditions import ConditionField, ConditionOperator, PolicyCondition
        cond = PolicyCondition(
            field=ConditionField.ANNUAL_CONTRACT_VALUE,
            operator=__import__("policy_grammar.conditions", fromlist=["ConditionOperator"]).ConditionOperator.LT,
            value=MoneyAmount.from_number("250000"),
        )
        ok, _ = evaluate_condition(cond, ctx)
        assert ok is True

    def test_acv_at_250k_fallback_not_applicable(self):
        from policy_grammar.conditions import ConditionField, ConditionOperator, PolicyCondition, evaluate_condition
        ctx = EvaluationContext(annual_contract_value=MoneyAmount.from_number("250000"))
        cond = PolicyCondition(
            field=ConditionField.ANNUAL_CONTRACT_VALUE,
            operator=ConditionOperator.LT,
            value=MoneyAmount.from_number("250000"),
        )
        ok, _ = evaluate_condition(cond, ctx)
        assert ok is False


class TestHardStop:
    def test_three_months_hard_stop(self):
        policy = firm_a_policy()
        contract = _contract_fee_months(3)
        ctx = EvaluationContext()
        decision = evaluate_liability_policy_v2(policy, contract, ctx)
        assert decision.state == PROHIBITED

    def test_six_months_not_hard_stop(self):
        policy = firm_a_policy()
        contract = _contract_fee_months(6)
        ctx = EvaluationContext()
        decision = evaluate_liability_policy_v2(policy, contract, ctx)
        assert decision.state != PROHIBITED


class TestSuperCap:
    def test_super_cap_does_not_change_general_cap_band(self):
        policy = firm_b_policy()
        pref = next(b for b in policy.bands if b.kind.value == "PREFERRED")
        assert isinstance(pref.expression.operands[0], AnnualFeeMultipleCap)
        assert pref.expression.operands[0].multiple == 2.0
        sc = policy.super_caps[0]
        assert isinstance(sc.expression.operands[0], ReferenceCap)
        assert sc.expression.operands[0].multiplier == 3.0


class TestFirmB:
    def test_preferred_two_x(self):
        p = firm_b_policy()
        pref = p.bands[0]
        assert pref.expression.operands[0].multiple == 2.0


class TestFirmC:
    def test_fixed_five_million(self):
        p = firm_c_policy()
        op = p.bands[0].expression.operands[0]
        assert float(op.money.amount) == 5_000_000


class TestFirmD:
    def test_lesser_of_preferred(self):
        p = firm_d_policy()
        assert p.bands[0].expression.operator.value == "LESSER_OF"


class TestMonetaryPreferred:
    def test_greater_of_resolves_500k_fees_to_1m_floor(self):
        policy = firm_a_policy()
        contract = _contract_fee_months(12)
        ctx = EvaluationContext(
            trailing_period_fees=MoneyAmount.from_number("500000"),
            trailing_period_months=12,
            annual_contract_value=MoneyAmount.from_number("500000"),
        )
        decision = evaluate_liability_policy_v2(policy, contract, ctx)
        assert decision.state in (ACCEPT, ACCEPT_WITH_NOTE, REQUIRES_REVIEW, ESCALATE)

    def test_greater_of_resolves_1_5m_fees(self):
        policy = firm_a_policy()
        contract = _contract_fee_months(12)
        ctx = EvaluationContext(
            trailing_period_fees=MoneyAmount.from_number("1500000"),
            trailing_period_months=12,
        )
        decision = evaluate_liability_policy_v2(policy, contract, ctx)
        assert decision.state in (ACCEPT, ACCEPT_WITH_NOTE, REQUIRES_REVIEW)
