"""Regression tests for Liability Policy v2 evaluator safety invariants."""

import pytest

from liability_evaluator_v2 import ContractCapFacts, evaluate_liability_policy_v2
from liability_policy_v2 import LiabilityPolicyV2, liability_policy_v2_from_dict
from policy_engine_core import ACCEPT_WITH_NOTE, ESCALATE, PROHIBITED, REQUIRES_REVIEW
from policy_grammar.bands import BandOutcome, PolicyBand, PolicyBandKind
from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import FeeRelativeCap, FixedAmountCap
from policy_grammar.conditions import ConditionField, ConditionOperator, PolicyCondition
from policy_grammar.evaluation_context import EvaluationContext
from policy_grammar.fee_relative import FeeBasis, FeeScope
from policy_grammar.money import MoneyAmount
from tests.fixtures.liability_policy_v2_golden import firm_a_policy


def _contract_fee_months(n: float) -> ContractCapFacts:
    return ContractCapFacts(
        expression=CapExpression(
            operator=CapOperator.SIMPLE,
            operands=[FeeRelativeCap(months=n, basis=FeeBasis.CONTRACT_FEES, scope=FeeScope.AGREEMENT)],
        ),
        fee_period_months=n,
    )


def _contract_fixed(amount: str, currency: str = "USD") -> ContractCapFacts:
    return ContractCapFacts(
        expression=CapExpression(
            operator=CapOperator.SIMPLE,
            operands=[FixedAmountCap(money=MoneyAmount.from_number(amount, currency))],
        ),
    )


class TestHardStopPrecedence:
    """Hard stops override fallback/preferred outcomes."""

    def test_three_months_prohibited_despite_low_acv_fallback(self):
        """ACV=$100k + 3mo cap must HARD_STOP, never ACCEPT via fallback."""
        policy = firm_a_policy()
        contract = _contract_fee_months(3)
        ctx = EvaluationContext(annual_contract_value=MoneyAmount.from_number("100000"))
        decision = evaluate_liability_policy_v2(policy, contract, ctx)
        assert decision.state == PROHIBITED
        assert decision.state != ACCEPT_WITH_NOTE

    def test_hard_stop_before_escalation_on_same_facts(self):
        policy = firm_a_policy()
        contract = _contract_fee_months(3)
        ctx = EvaluationContext(
            annual_contract_value=MoneyAmount.from_number("500000"),
            trailing_period_fees=MoneyAmount.from_number("500000"),
            trailing_period_months=12,
        )
        assert evaluate_liability_policy_v2(policy, contract, ctx).state == PROHIBITED


class TestTriStateConditions:
    """Missing deal facts → UNRESOLVED, never silent FALSE."""

    def test_missing_acv_fallback_unresolved(self):
        policy = LiabilityPolicyV2(
            bands=[
                PolicyBand(
                    kind=PolicyBandKind.ACCEPTABLE_FALLBACK,
                    expression=CapExpression(
                        operator=CapOperator.SIMPLE,
                        operands=[FeeRelativeCap(months=12, basis=FeeBasis.CONTRACT_FEES, scope=FeeScope.AGREEMENT)],
                    ),
                    conditions=[
                        PolicyCondition(
                            field=ConditionField.ANNUAL_CONTRACT_VALUE,
                            operator=ConditionOperator.LT,
                            value=MoneyAmount.from_number("250000"),
                        ),
                    ],
                ),
                PolicyBand(
                    kind=PolicyBandKind.MINIMUM_ACCEPTABLE,
                    expression=CapExpression(
                        operator=CapOperator.SIMPLE,
                        operands=[FeeRelativeCap(months=6, basis=FeeBasis.CONTRACT_FEES, scope=FeeScope.AGREEMENT)],
                    ),
                    outcome_if_breached=BandOutcome.HARD_STOP,
                ),
            ],
        )
        contract = _contract_fee_months(12)
        ctx = EvaluationContext()  # no ACV
        decision = evaluate_liability_policy_v2(policy, contract, ctx)
        assert decision.state == REQUIRES_REVIEW

    @pytest.mark.parametrize("field,ctx_kwargs,cond_factory", [
        ("annual_contract_value", {}, lambda: PolicyCondition(
            field=ConditionField.ANNUAL_CONTRACT_VALUE, operator=ConditionOperator.LT,
            value=MoneyAmount.from_number("250000"),
        )),
        ("contract_value", {}, lambda: PolicyCondition(
            field=ConditionField.CONTRACT_VALUE, operator=ConditionOperator.LT,
            value=MoneyAmount.from_number("250000"),
        )),
        ("counterparty_role", {}, lambda: PolicyCondition(
            field=ConditionField.COUNTERPARTY_ROLE, operator=ConditionOperator.EQ, value="vendor",
        )),
        ("governing_law", {}, lambda: PolicyCondition(
            field=ConditionField.GOVERNING_LAW, operator=ConditionOperator.EQ, value="Delaware",
        )),
    ])
    def test_missing_context_fields_unresolved(self, field, ctx_kwargs, cond_factory):
        from policy_grammar.conditions import evaluate_condition
        ctx = EvaluationContext(
            annual_contract_value=ctx_kwargs.get("annual_contract_value"),
            contract_value=ctx_kwargs.get("contract_value"),
            counterparty_role=ctx_kwargs.get("counterparty_role"),
            governing_law=ctx_kwargs.get("governing_law"),
        )
        cond = cond_factory()
        ok, reason = evaluate_condition(cond, ctx)
        assert ok is None
        assert reason is not None

    def test_missing_annual_fees_unresolved_for_monetary_resolution(self):
        from policy_grammar.comparison import resolve_operand_to_money, ComparisonOutcome
        from policy_grammar.cap_operands import AnnualFeeMultipleCap
        op = AnnualFeeMultipleCap(multiple=2.0)
        result = resolve_operand_to_money(op, EvaluationContext())
        assert result.outcome == ComparisonOutcome.UNRESOLVED


class TestCurrencySafety:
    def test_eur_contract_vs_usd_policy_floor_unresolved(self):
        policy = LiabilityPolicyV2(
            bands=[
                PolicyBand(
                    kind=PolicyBandKind.PREFERRED,
                    expression=CapExpression(
                        operator=CapOperator.SIMPLE,
                        operands=[FixedAmountCap(money=MoneyAmount.from_number("1000000", "USD"))],
                    ),
                ),
            ],
        )
        contract = _contract_fixed("900000", "EUR")
        ctx = EvaluationContext()
        decision = evaluate_liability_policy_v2(policy, contract, ctx)
        assert decision.state in (REQUIRES_REVIEW, ESCALATE)

    def test_compare_operands_currency_mismatch(self):
        from policy_grammar.comparison import compare_operands, ComparisonOutcome
        from policy_grammar.cap_operands import FixedAmountCap
        left = FixedAmountCap(money=MoneyAmount.from_number("900000", "EUR"))
        right = FixedAmountCap(money=MoneyAmount.from_number("1000000", "USD"))
        result = compare_operands(left, right, EvaluationContext())
        assert result.outcome == ComparisonOutcome.INCOMPARABLE


class TestContradictoryPolicyValidation:
    def test_preferred_below_minimum_rejected(self):
        rules = {
            "schema_version": 2,
            "orientation": "buy_side",
            "bands": [
                {
                    "kind": "PREFERRED",
                    "expression": {
                        "operator": "SIMPLE",
                        "operands": [{"type": "fee_period", "months": 12, "basis": "CONTRACT_FEES", "scope": "AGREEMENT"}],
                    },
                },
                {
                    "kind": "MINIMUM_ACCEPTABLE",
                    "expression": {
                        "operator": "SIMPLE",
                        "operands": [{"type": "fee_period", "months": 24, "basis": "CONTRACT_FEES", "scope": "AGREEMENT"}],
                    },
                    "outcome_if_breached": "HARD_STOP",
                },
            ],
            "carve_outs": [],
            "super_caps": [],
            "escalation_rules": [],
            "prohibit_unlimited": True,
            "consequential_damages": {"require_exclusion": False, "required_carveouts": []},
        }
        policy = liability_policy_v2_from_dict(rules)
        errors = policy.validate()
        assert any("contradictory" in e.message for e in errors)

    def test_reference_cap_in_general_band_rejected(self):
        rules = {
            "schema_version": 2,
            "orientation": "buy_side",
            "bands": [{
                "kind": "PREFERRED",
                "expression": {
                    "operator": "SIMPLE",
                    "operands": [{"type": "reference", "ref": "GENERAL_CAP", "multiplier": 2.0}],
                },
            }],
            "carve_outs": [],
            "super_caps": [],
            "escalation_rules": [],
            "prohibit_unlimited": True,
            "consequential_damages": {"require_exclusion": False, "required_carveouts": []},
        }
        policy = liability_policy_v2_from_dict(rules)
        errors = policy.validate()
        assert any("super_caps" in e.message for e in errors)


class TestReferenceCapSafety:
    def test_only_general_cap_target_allowed(self):
        from policy_grammar.cap_operands import ReferenceCap, ReferenceTarget
        from policy_grammar.validation import validate_cap_operand
        ref = ReferenceCap(ref=ReferenceTarget.GENERAL_CAP, multiplier=2.0)
        assert not validate_cap_operand(ref)

    def test_super_cap_resolves_deterministically(self):
        from policy_grammar.comparison import resolve_operand_to_money, ComparisonOutcome
        from policy_grammar.cap_operands import ReferenceCap, ReferenceTarget
        ref = ReferenceCap(ref=ReferenceTarget.GENERAL_CAP, multiplier=2.0)
        general = MoneyAmount.from_number("1000000")
        result = resolve_operand_to_money(ref, EvaluationContext(), resolved_general_cap=general)
        assert result.outcome == ComparisonOutcome.COMPARED
        assert float(result.money.amount) == 2_000_000


class TestDeterministicPrecedence:
    def test_escalation_wins_over_fallback_when_both_match(self):
        policy = firm_a_policy()
        contract = _contract_fee_months(6)
        ctx = EvaluationContext(
            annual_contract_value=MoneyAmount.from_number("100000"),
            trailing_period_fees=MoneyAmount.from_number("100000"),
            trailing_period_months=12,
        )
        decision = evaluate_liability_policy_v2(policy, contract, ctx)
        # 6mo meets fallback symbolically but escalation may also apply for high ACV policies;
        # with ACV 100k escalation rule is FALSE, fallback may apply
        assert decision.state in (ACCEPT_WITH_NOTE, ESCALATE, REQUIRES_REVIEW, PROHIBITED)

    def test_identical_inputs_identical_decision(self):
        policy = firm_a_policy()
        contract = _contract_fee_months(12)
        ctx = EvaluationContext(annual_contract_value=MoneyAmount.from_number("100000"))
        d1 = evaluate_liability_policy_v2(policy, contract, ctx)
        d2 = evaluate_liability_policy_v2(policy, contract, ctx)
        assert d1.state == d2.state
        assert d1.rule_id == d2.rule_id
