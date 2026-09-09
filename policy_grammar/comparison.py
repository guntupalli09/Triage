from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import List, Optional, Union

from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import (
    AnnualFeeMultipleCap,
    CapOperand,
    FeeRelativeCap,
    FixedAmountCap,
    ReferenceCap,
    ReferenceTarget,
    UnlimitedCap,
)
from policy_grammar.evaluation_context import EvaluationContext
from policy_grammar.fee_relative import fee_bases_compatible, fee_scopes_compatible
from policy_grammar.money import MoneyAmount


class ComparisonOutcome(Enum):
    COMPARED = auto()
    UNRESOLVED = auto()
    INCOMPARABLE = auto()


@dataclass(frozen=True)
class CompareResult:
    outcome: ComparisonOutcome
    relation: Optional[str] = None  # LT | EQ | GT when COMPARED
    reason: Optional[str] = None


@dataclass(frozen=True)
class ResolveResult:
    outcome: ComparisonOutcome
    money: Optional[MoneyAmount] = None
    reason: Optional[str] = None


def _relation_from_numeric(left: float, right: float) -> str:
    if left < right:
        return "LT"
    if left > right:
        return "GT"
    return "EQ"


def compare_fee_relative(a: FeeRelativeCap, b: FeeRelativeCap) -> CompareResult:
    if not fee_bases_compatible(a.basis, b.basis):
        return CompareResult(ComparisonOutcome.INCOMPARABLE, reason="fee bases are not compatible for symbolic comparison")
    if not fee_scopes_compatible(a.scope, b.scope):
        return CompareResult(ComparisonOutcome.INCOMPARABLE, reason="fee scopes differ")
    return CompareResult(ComparisonOutcome.COMPARED, relation=_relation_from_numeric(a.months, b.months))


def compare_operands(
    left: CapOperand,
    right: CapOperand,
    ctx: EvaluationContext,
    *,
    resolved_general_cap: Optional[MoneyAmount] = None,
) -> CompareResult:
    """Symbolic comparison first; monetary/reference resolution only when needed."""
    if isinstance(left, UnlimitedCap) or isinstance(right, UnlimitedCap):
        if isinstance(left, UnlimitedCap) and isinstance(right, UnlimitedCap):
            return CompareResult(ComparisonOutcome.COMPARED, relation="EQ")
        return CompareResult(ComparisonOutcome.INCOMPARABLE, reason="unlimited cap compared to finite cap")

    if isinstance(left, FeeRelativeCap) and isinstance(right, FeeRelativeCap):
        return compare_fee_relative(left, right)

    if isinstance(left, AnnualFeeMultipleCap) and isinstance(right, AnnualFeeMultipleCap):
        return CompareResult(
            ComparisonOutcome.COMPARED,
            relation=_relation_from_numeric(left.multiple, right.multiple),
        )

    if isinstance(left, FixedAmountCap) and isinstance(right, FixedAmountCap):
        if left.money.currency != right.money.currency:
            return CompareResult(ComparisonOutcome.INCOMPARABLE, reason="currency mismatch")
        return CompareResult(
            ComparisonOutcome.COMPARED,
            relation=_relation_from_numeric(float(left.money.amount), float(right.money.amount)),
        )

    if isinstance(left, ReferenceCap) or isinstance(right, ReferenceCap):
        left_res = resolve_operand_to_money(left, ctx, resolved_general_cap=resolved_general_cap)
        right_res = resolve_operand_to_money(right, ctx, resolved_general_cap=resolved_general_cap)
        if left_res.outcome != ComparisonOutcome.COMPARED or right_res.outcome != ComparisonOutcome.COMPARED:
            reason = left_res.reason or right_res.reason or "reference cap could not be resolved"
            return CompareResult(ComparisonOutcome.UNRESOLVED, reason=reason)
        assert left_res.money and right_res.money
        if left_res.money.currency != right_res.money.currency:
            return CompareResult(ComparisonOutcome.INCOMPARABLE, reason="currency mismatch after resolution")
        return CompareResult(
            ComparisonOutcome.COMPARED,
            relation=_relation_from_numeric(float(left_res.money.amount), float(right_res.money.amount)),
        )

    # Heterogeneous operands — resolve to money if possible
    left_res = resolve_operand_to_money(left, ctx, resolved_general_cap=resolved_general_cap)
    right_res = resolve_operand_to_money(right, ctx, resolved_general_cap=resolved_general_cap)
    if left_res.outcome != ComparisonOutcome.COMPARED or right_res.outcome != ComparisonOutcome.COMPARED:
        reason = left_res.reason or right_res.reason or "heterogeneous caps require monetary resolution but context is insufficient"
        return CompareResult(ComparisonOutcome.UNRESOLVED, reason=reason)
    assert left_res.money and right_res.money
    if left_res.money.currency != right_res.money.currency:
        return CompareResult(ComparisonOutcome.INCOMPARABLE, reason="currency mismatch after resolution")
    return CompareResult(
        ComparisonOutcome.COMPARED,
        relation=_relation_from_numeric(float(left_res.money.amount), float(right_res.money.amount)),
    )


def resolve_operand_to_money(
    operand: CapOperand,
    ctx: EvaluationContext,
    *,
    resolved_general_cap: Optional[MoneyAmount] = None,
) -> ResolveResult:
    if isinstance(operand, UnlimitedCap):
        return ResolveResult(ComparisonOutcome.INCOMPARABLE, reason="unlimited cap has no finite money value")

    if isinstance(operand, FixedAmountCap):
        return ResolveResult(ComparisonOutcome.COMPARED, money=operand.money)

    if isinstance(operand, FeeRelativeCap):
        fee_money = ctx.fee_amount_for_basis(operand.basis.value)
        if fee_money is None:
            return ResolveResult(
                ComparisonOutcome.UNRESOLVED,
                reason=f"fee amount for basis {operand.basis.value} not available — trailing_period_fees and annual_fees both absent",
            )
        if operand.months == 12 and ctx.trailing_period_months and ctx.trailing_period_months != 12:
            # Explicit trailing period in context — scale if months differ from 12
            scale = Decimal(str(operand.months / ctx.trailing_period_months))
            amount = fee_money.amount * scale
        elif operand.months != 12 and ctx.trailing_period_months == operand.months:
            amount = fee_money.amount
        elif operand.months == 12 and ctx.trailing_period_fees is not None:
            amount = fee_money.amount
        elif ctx.annual_fees is not None and operand.months == 12:
            amount = ctx.annual_fees.amount
        elif ctx.trailing_period_fees is not None:
            # Scale trailing fees to requested months when period length known
            if ctx.trailing_period_months:
                scale = Decimal(str(operand.months / ctx.trailing_period_months))
                amount = ctx.trailing_period_fees.amount * scale
            else:
                return ResolveResult(
                    ComparisonOutcome.UNRESOLVED,
                    reason=f"cannot scale fee amount to {operand.months} months without trailing_period_months in context",
                )
        else:
            return ResolveResult(
                ComparisonOutcome.UNRESOLVED,
                reason=f"cannot resolve {operand.months} months of fees without fee context",
            )
        return ResolveResult(ComparisonOutcome.COMPARED, money=MoneyAmount(amount=amount, currency=fee_money.currency))

    if isinstance(operand, AnnualFeeMultipleCap):
        if ctx.annual_fees is None:
            return ResolveResult(ComparisonOutcome.UNRESOLVED, reason="annual_fees not available for annual_fee_multiple resolution")
        amount = ctx.annual_fees.amount * Decimal(str(operand.multiple))
        return ResolveResult(ComparisonOutcome.COMPARED, money=MoneyAmount(amount=amount, currency=ctx.annual_fees.currency))

    if isinstance(operand, ReferenceCap):
        if operand.ref == ReferenceTarget.GENERAL_CAP:
            if resolved_general_cap is None:
                return ResolveResult(ComparisonOutcome.UNRESOLVED, reason="GENERAL_CAP reference requires resolved general cap")
            amount = resolved_general_cap.amount * Decimal(str(operand.multiplier))
            return ResolveResult(
                ComparisonOutcome.COMPARED,
                money=MoneyAmount(amount=amount, currency=resolved_general_cap.currency),
            )
        return ResolveResult(ComparisonOutcome.UNRESOLVED, reason=f"unknown reference target {operand.ref.value}")

    return ResolveResult(ComparisonOutcome.INCOMPARABLE, reason="unknown operand type")


def resolve_cap_expression_to_money(
    expr: CapExpression,
    ctx: EvaluationContext,
    *,
    resolved_general_cap: Optional[MoneyAmount] = None,
) -> ResolveResult:
    if expr.operator == CapOperator.SIMPLE:
        return resolve_operand_to_money(expr.operands[0], ctx, resolved_general_cap=resolved_general_cap)

    resolved: List[MoneyAmount] = []
    for op in expr.operands:
        r = resolve_operand_to_money(op, ctx, resolved_general_cap=resolved_general_cap)
        if r.outcome != ComparisonOutcome.COMPARED or r.money is None:
            return ResolveResult(ComparisonOutcome.UNRESOLVED, reason=r.reason)
        resolved.append(r.money)

    currencies = {m.currency for m in resolved}
    if len(currencies) > 1:
        return ResolveResult(ComparisonOutcome.INCOMPARABLE, reason="compound cap mixes currencies")

    amounts = [m.amount for m in resolved]
    if expr.operator == CapOperator.GREATER_OF:
        return ResolveResult(ComparisonOutcome.COMPARED, money=MoneyAmount(amount=max(amounts), currency=resolved[0].currency))
    if expr.operator == CapOperator.LESSER_OF:
        return ResolveResult(ComparisonOutcome.COMPARED, money=MoneyAmount(amount=min(amounts), currency=resolved[0].currency))
    return ResolveResult(ComparisonOutcome.INCOMPARABLE, reason=f"unknown operator {expr.operator.value}")


def compare_cap_expressions(
    left: CapExpression,
    right: CapExpression,
    ctx: EvaluationContext,
    *,
    resolved_general_cap: Optional[MoneyAmount] = None,
) -> CompareResult:
    """Compare two cap expressions — symbolic path when possible."""
    if (
        left.operator == CapOperator.SIMPLE
        and right.operator == CapOperator.SIMPLE
        and len(left.operands) == 1
        and len(right.operands) == 1
    ):
        return compare_operands(
            left.operands[0], right.operands[0], ctx, resolved_general_cap=resolved_general_cap,
        )

    left_res = resolve_cap_expression_to_money(left, ctx, resolved_general_cap=resolved_general_cap)
    right_res = resolve_cap_expression_to_money(right, ctx, resolved_general_cap=resolved_general_cap)
    if left_res.outcome != ComparisonOutcome.COMPARED or right_res.outcome != ComparisonOutcome.COMPARED:
        return CompareResult(
            ComparisonOutcome.UNRESOLVED,
            reason=left_res.reason or right_res.reason or "compound cap comparison requires monetary resolution",
        )
    assert left_res.money and right_res.money
    if left_res.money.currency != right_res.money.currency:
        return CompareResult(ComparisonOutcome.INCOMPARABLE, reason="currency mismatch")
    return CompareResult(
        ComparisonOutcome.COMPARED,
        relation=_relation_from_numeric(float(left_res.money.amount), float(right_res.money.amount)),
    )
