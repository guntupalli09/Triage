"""Tests for policy grammar symbolic comparison and monetary resolution."""

import pytest

from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import (
    AnnualFeeMultipleCap,
    FeeRelativeCap,
    FixedAmountCap,
    ReferenceCap,
    ReferenceTarget,
)
from policy_grammar.comparison import (
    ComparisonOutcome,
    compare_cap_expressions,
    compare_operands,
    resolve_cap_expression_to_money,
)
from policy_grammar.evaluation_context import EvaluationContext
from policy_grammar.fee_relative import FeeBasis, FeeScope
from policy_grammar.money import MoneyAmount


def _fee_months(n: float, basis=FeeBasis.CONTRACT_FEES) -> CapExpression:
    return CapExpression(
        operator=CapOperator.SIMPLE,
        operands=[FeeRelativeCap(months=n, basis=basis, scope=FeeScope.AGREEMENT)],
    )


def _fixed(amount: str) -> CapExpression:
    return CapExpression(
        operator=CapOperator.SIMPLE,
        operands=[FixedAmountCap(money=MoneyAmount.from_number(amount))],
    )


def _greater_of_fee_and_fixed(months: float, amount: str) -> CapExpression:
    return CapExpression(
        operator=CapOperator.GREATER_OF,
        operands=[
            FeeRelativeCap(months=months, basis=FeeBasis.FEES_PAID_OR_PAYABLE, scope=FeeScope.AGREEMENT),
            FixedAmountCap(money=MoneyAmount.from_number(amount)),
        ],
    )


class TestSymbolicComparison:
    def test_twelve_months_equals_twelve_months_without_money(self):
        left = _fee_months(12)
        right = _fee_months(12)
        ctx = EvaluationContext()
        result = compare_cap_expressions(left, right, ctx)
        assert result.outcome == ComparisonOutcome.COMPARED
        assert result.relation == "EQ"

    def test_three_months_less_than_six_month_minimum(self):
        left = _fee_months(3)
        right = _fee_months(6)
        result = compare_cap_expressions(left, right, EvaluationContext())
        assert result.outcome == ComparisonOutcome.COMPARED
        assert result.relation == "LT"

    def test_six_month_boundary_equal(self):
        result = compare_cap_expressions(_fee_months(6), _fee_months(6), EvaluationContext())
        assert result.relation == "EQ"

    def test_twenty_four_months_greater_than_twelve(self):
        result = compare_cap_expressions(_fee_months(24), _fee_months(12), EvaluationContext())
        assert result.relation == "GT"

    def test_one_year_preserved_as_twelve_months(self):
        left = CapExpression(
            operator=CapOperator.SIMPLE,
            operands=[FeeRelativeCap(months=12, basis=FeeBasis.CONTRACT_FEES, scope=FeeScope.AGREEMENT)],
        )
        right = CapExpression(
            operator=CapOperator.SIMPLE,
            operands=[FeeRelativeCap(months=12, basis=FeeBasis.CONTRACT_FEES, scope=FeeScope.AGREEMENT)],
        )
        assert compare_cap_expressions(left, right, EvaluationContext()).relation == "EQ"

    def test_two_x_annual_fees_symbolic(self):
        left = CapExpression(operator=CapOperator.SIMPLE, operands=[AnnualFeeMultipleCap(2.0)])
        right = CapExpression(operator=CapOperator.SIMPLE, operands=[AnnualFeeMultipleCap(2.0)])
        assert compare_cap_expressions(left, right, EvaluationContext()).relation == "EQ"

    def test_twelve_months_not_twelve_x_annual(self):
        fee = _fee_months(12)
        mult = CapExpression(operator=CapOperator.SIMPLE, operands=[AnnualFeeMultipleCap(12.0)])
        # Different operand kinds — needs money or incomparable
        result = compare_operands(fee.operands[0], mult.operands[0], EvaluationContext())
        assert result.outcome in (ComparisonOutcome.UNRESOLVED, ComparisonOutcome.INCOMPARABLE)


class TestMonetaryResolution:
    def test_greater_of_resolves_with_trailing_fees(self):
        expr = _greater_of_fee_and_fixed(12, "1000000")
        ctx = EvaluationContext(
            trailing_period_fees=MoneyAmount.from_number("600000"),
            trailing_period_months=12,
        )
        result = resolve_cap_expression_to_money(expr, ctx)
        assert result.outcome == ComparisonOutcome.COMPARED
        assert result.money.amount == MoneyAmount.from_number("1000000").amount

    def test_greater_of_resolves_to_trailing_when_higher(self):
        expr = _greater_of_fee_and_fixed(12, "1000000")
        ctx = EvaluationContext(
            trailing_period_fees=MoneyAmount.from_number("2000000"),
            trailing_period_months=12,
        )
        result = resolve_cap_expression_to_money(expr, ctx)
        assert result.outcome == ComparisonOutcome.COMPARED
        assert result.money.amount == MoneyAmount.from_number("2000000").amount

    def test_unresolved_without_fee_context(self):
        expr = _greater_of_fee_and_fixed(12, "1000000")
        result = resolve_cap_expression_to_money(expr, EvaluationContext())
        assert result.outcome == ComparisonOutcome.UNRESOLVED

    def test_reference_cap_never_annual_fee_multiple(self):
        ref = ReferenceCap(ref=ReferenceTarget.GENERAL_CAP, multiplier=2.0)
        assert ref.operand_type == "reference"
        general = MoneyAmount.from_number("1000000")
        from policy_grammar.comparison import resolve_operand_to_money
        resolved = resolve_operand_to_money(ref, EvaluationContext(), resolved_general_cap=general)
        assert resolved.money.amount == MoneyAmount.from_number("2000000").amount


class TestConditionValidation:
    def test_rejects_governing_law_money_comparison(self):
        from policy_grammar.conditions import ConditionField, ConditionOperator, PolicyCondition, validate_condition
        cond = PolicyCondition(
            field=ConditionField.GOVERNING_LAW,
            operator=ConditionOperator.LT,
            value="Delaware",
        )
        errors = validate_condition(cond)
        assert errors

    def test_liability_cap_condition_accepts_cap_expression(self):
        from policy_grammar.conditions import ConditionField, ConditionOperator, PolicyCondition, validate_condition
        cond = PolicyCondition(
            field=ConditionField.LIABILITY_CAP,
            operator=ConditionOperator.LT,
            value=_fee_months(12),
        )
        assert not validate_condition(cond)


class TestDeterminism:
    def test_identical_inputs_identical_output(self):
        left = _fee_months(12)
        right = _fee_months(6)
        ctx = EvaluationContext()
        results = [compare_cap_expressions(left, right, ctx) for _ in range(10)]
        assert len({(r.outcome, r.relation) for r in results}) == 1
