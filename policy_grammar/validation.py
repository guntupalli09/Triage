from __future__ import annotations

from dataclasses import dataclass
from typing import List

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


@dataclass
class ValidationError:
    path: str
    message: str


def validate_cap_operand(op: CapOperand, path: str = "operand") -> List[ValidationError]:
    errors: List[ValidationError] = []
    if isinstance(op, FeeRelativeCap):
        if op.months <= 0:
            errors.append(ValidationError(path, "fee_period months must be positive"))
    elif isinstance(op, AnnualFeeMultipleCap):
        if op.multiple < 0:
            errors.append(ValidationError(path, "annual_fee_multiple must be non-negative"))
    elif isinstance(op, ReferenceCap):
        if op.multiplier <= 0:
            errors.append(ValidationError(path, "reference multiplier must be positive"))
        if op.ref != ReferenceTarget.GENERAL_CAP:
            errors.append(ValidationError(path, f"unsupported reference target {op.ref.value}"))
    elif isinstance(op, FixedAmountCap):
        try:
            _ = op.money.amount
        except ValueError as e:
            errors.append(ValidationError(path, str(e)))
    return errors


def validate_cap_expression(expr: CapExpression, path: str = "expression") -> List[ValidationError]:
    errors: List[ValidationError] = []
    if expr.operator == CapOperator.SIMPLE and len(expr.operands) != 1:
        errors.append(ValidationError(path, "SIMPLE expression requires exactly one operand"))
    if expr.operator in (CapOperator.GREATER_OF, CapOperator.LESSER_OF) and len(expr.operands) < 2:
        errors.append(ValidationError(path, f"{expr.operator.value} requires at least two operands"))
    for i, op in enumerate(expr.operands):
        errors.extend(validate_cap_operand(op, f"{path}.operands[{i}]"))
    return errors
