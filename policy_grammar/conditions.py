from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional, Union

from policy_grammar.cap_expression import CapExpression
from policy_grammar.money import MoneyAmount
from policy_grammar.roles import NormalizedRole


class ConditionField(str, Enum):
    ANNUAL_CONTRACT_VALUE = "annual_contract_value"
    CONTRACT_VALUE = "contract_value"
    LIABILITY_CAP = "liability_cap"
    FEE_PERIOD_MONTHS = "fee_period_months"
    COUNTERPARTY_ROLE = "counterparty_role"
    GOVERNING_LAW = "governing_law"
    CONTRACT_TYPE = "contract_type"


class ConditionOperator(str, Enum):
    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"
    IN = "IN"
    NOT_IN = "NOT_IN"


ConditionValue = Union[MoneyAmount, CapExpression, int, float, str, NormalizedRole, List[str]]


@dataclass(frozen=True)
class PolicyCondition:
    field: ConditionField
    operator: ConditionOperator
    value: ConditionValue


@dataclass(frozen=True)
class ConditionGroup:
    operator: str  # AND | OR
    conditions: List[Union[PolicyCondition, "ConditionGroup"]]


def _compare_scalar(left: float, op: ConditionOperator, right: float) -> bool:
    if op == ConditionOperator.EQ:
        return left == right
    if op == ConditionOperator.NE:
        return left != right
    if op == ConditionOperator.LT:
        return left < right
    if op == ConditionOperator.LTE:
        return left <= right
    if op == ConditionOperator.GT:
        return left > right
    if op == ConditionOperator.GTE:
        return left >= right
    raise ValueError(f"operator {op} is not valid for numeric comparison")


def evaluate_condition(
    condition: PolicyCondition,
    ctx: "EvaluationContext",
    *,
    contract_cap: Optional[CapExpression] = None,
    contract_fee_period_months: Optional[float] = None,
) -> tuple[Optional[bool], Optional[str]]:
    """Returns (result, unresolved_reason). result=None when context insufficient."""
    from policy_grammar.comparison import compare_cap_expressions
    from policy_grammar.evaluation_context import EvaluationContext

    field = condition.field
    op = condition.operator
    val = condition.value

    if field in (ConditionField.ANNUAL_CONTRACT_VALUE, ConditionField.CONTRACT_VALUE):
        if not isinstance(val, MoneyAmount):
            return None, f"invalid value type for {field.value}"
        ctx_money = ctx.annual_contract_value if field == ConditionField.ANNUAL_CONTRACT_VALUE else ctx.contract_value
        if ctx_money is None:
            return None, f"{field.value} not available in evaluation context"
        if ctx_money.currency != val.currency:
            return None, f"currency mismatch: {ctx_money.currency} vs {val.currency}"
        return _compare_scalar(float(ctx_money.amount), op, float(val.amount)), None

    if field == ConditionField.FEE_PERIOD_MONTHS:
        if not isinstance(val, (int, float)):
            return None, "fee_period_months condition requires numeric value"
        if contract_fee_period_months is None:
            return None, "contract fee period months not established"
        return _compare_scalar(float(contract_fee_period_months), op, float(val)), None

    if field == ConditionField.LIABILITY_CAP:
        if not isinstance(val, CapExpression):
            return None, "liability_cap condition requires CapExpression value"
        if contract_cap is None:
            return None, "contract liability cap not established"
        cmp = compare_cap_expressions(contract_cap, val, ctx)
        if cmp.outcome.name == "UNRESOLVED":
            return None, cmp.reason
        if cmp.outcome.name == "INCOMPARABLE":
            return None, cmp.reason or "caps are not comparable"
        rel = cmp.relation  # LT | EQ | GT
        if rel is None:
            return None, cmp.reason
        truth = {
            ConditionOperator.LT: rel == "LT",
            ConditionOperator.LTE: rel in ("LT", "EQ"),
            ConditionOperator.GT: rel == "GT",
            ConditionOperator.GTE: rel in ("GT", "EQ"),
            ConditionOperator.EQ: rel == "EQ",
            ConditionOperator.NE: rel != "EQ",
        }.get(op)
        if truth is None:
            return None, f"operator {op.value} not supported for liability_cap comparison"
        return truth, None

    if field == ConditionField.COUNTERPARTY_ROLE:
        if not isinstance(val, (NormalizedRole, str)):
            return None, "counterparty_role condition requires role value"
        if ctx.counterparty_role is None:
            return None, "counterparty_role not available in evaluation context"
        expected = val.value if isinstance(val, NormalizedRole) else val
        actual = ctx.counterparty_role
        if op in (ConditionOperator.EQ, ConditionOperator.IN):
            members = val if isinstance(val, list) else [expected]
            return actual in members, None
        if op in (ConditionOperator.NE, ConditionOperator.NOT_IN):
            members = val if isinstance(val, list) else [expected]
            return actual not in members, None
        return None, f"operator {op.value} not valid for counterparty_role"

    if field == ConditionField.GOVERNING_LAW:
        if not isinstance(val, str):
            return None, "governing_law condition requires string value"
        if ctx.governing_law is None:
            return None, "governing_law not available in evaluation context"
        if op == ConditionOperator.EQ:
            return ctx.governing_law.lower() == val.lower(), None
        if op == ConditionOperator.NE:
            return ctx.governing_law.lower() != val.lower(), None
        if op == ConditionOperator.IN:
            return ctx.governing_law.lower() in [v.lower() for v in val], None if isinstance(val, list) else None
        return None, f"operator {op.value} not valid for governing_law"

    if field == ConditionField.CONTRACT_TYPE:
        if not isinstance(val, str):
            return None, "contract_type condition requires string value"
        if ctx.contract_type is None:
            return None, "contract_type not available in evaluation context"
        if op == ConditionOperator.EQ:
            return ctx.contract_type.lower() == val.lower(), None
        if op == ConditionOperator.NE:
            return ctx.contract_type.lower() != val.lower(), None
        return None, f"operator {op.value} not valid for contract_type"

    return None, f"unknown condition field {field.value}"


def evaluate_condition_group(
    group: ConditionGroup,
    ctx: "EvaluationContext",
    *,
    contract_cap: Optional[CapExpression] = None,
    contract_fee_period_months: Optional[float] = None,
) -> tuple[Optional[bool], Optional[str]]:
    results: List[Optional[bool]] = []
    for item in group.conditions:
        if isinstance(item, ConditionGroup):
            r, reason = evaluate_condition_group(
                item, ctx, contract_cap=contract_cap, contract_fee_period_months=contract_fee_period_months,
            )
        else:
            r, reason = evaluate_condition(
                item, ctx, contract_cap=contract_cap, contract_fee_period_months=contract_fee_period_months,
            )
        if r is None:
            return None, reason
        results.append(r)
    if group.operator == "AND":
        return all(results), None
    if group.operator == "OR":
        return any(results), None
    return None, f"unknown group operator {group.operator!r}"


def validate_condition(condition: PolicyCondition) -> List[str]:
    errors: List[str] = []
    allowed: dict[ConditionField, tuple] = {
        ConditionField.ANNUAL_CONTRACT_VALUE: (MoneyAmount,),
        ConditionField.CONTRACT_VALUE: (MoneyAmount,),
        ConditionField.LIABILITY_CAP: (CapExpression,),
        ConditionField.FEE_PERIOD_MONTHS: (int, float),
        ConditionField.COUNTERPARTY_ROLE: (NormalizedRole, str, list),
        ConditionField.GOVERNING_LAW: (str, list),
        ConditionField.CONTRACT_TYPE: (str, list),
    }
    expected = allowed.get(condition.field)
    if expected is None:
        errors.append(f"unknown condition field {condition.field.value}")
        return errors
    if not isinstance(condition.value, expected):
        errors.append(
            f"field {condition.field.value} requires value type {expected}, got {type(condition.value).__name__}"
        )
    numeric_ops = {
        ConditionOperator.LT, ConditionOperator.LTE, ConditionOperator.GT, ConditionOperator.GTE,
        ConditionOperator.EQ, ConditionOperator.NE,
    }
    set_ops = {ConditionOperator.IN, ConditionOperator.NOT_IN}
    if condition.field in (ConditionField.GOVERNING_LAW, ConditionField.CONTRACT_TYPE):
        if condition.operator not in (ConditionOperator.EQ, ConditionOperator.NE, ConditionOperator.IN, ConditionOperator.NOT_IN):
            errors.append(f"operator {condition.operator.value} not allowed for {condition.field.value}")
    if condition.field in (ConditionField.ANNUAL_CONTRACT_VALUE, ConditionField.CONTRACT_VALUE, ConditionField.FEE_PERIOD_MONTHS, ConditionField.LIABILITY_CAP):
        if condition.operator in set_ops:
            errors.append(f"operator {condition.operator.value} not allowed for {condition.field.value}")
    return errors
