from __future__ import annotations

from typing import Any, Dict, List

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
from policy_grammar.fee_relative import FeeBasis, FeeScope
from policy_grammar.money import MoneyAmount


def money_to_dict(m: MoneyAmount) -> Dict[str, Any]:
    return {"amount": str(m.amount), "currency": m.currency}


def money_from_dict(d: Dict[str, Any]) -> MoneyAmount:
    return MoneyAmount.from_number(d["amount"], d.get("currency", "USD"))


def cap_operand_to_dict(op: CapOperand) -> Dict[str, Any]:
    if isinstance(op, FeeRelativeCap):
        return {
            "type": "fee_period",
            "months": op.months,
            "basis": op.basis.value,
            "scope": op.scope.value,
        }
    if isinstance(op, AnnualFeeMultipleCap):
        return {"type": "annual_fee_multiple", "multiple": op.multiple}
    if isinstance(op, FixedAmountCap):
        return {"type": "fixed_amount", "money": money_to_dict(op.money)}
    if isinstance(op, ReferenceCap):
        return {"type": "reference", "ref": op.ref.value, "multiplier": op.multiplier}
    if isinstance(op, UnlimitedCap):
        return {"type": "unlimited"}
    raise TypeError(f"unknown operand type {type(op)}")


def cap_operand_from_dict(d: Dict[str, Any]) -> CapOperand:
    t = d.get("type")
    if t == "fee_period":
        return FeeRelativeCap(
            months=float(d["months"]),
            basis=FeeBasis(d.get("basis", FeeBasis.CONTRACT_FEES.value)),
            scope=FeeScope(d.get("scope", FeeScope.AGREEMENT.value)),
        )
    if t == "annual_fee_multiple":
        return AnnualFeeMultipleCap(multiple=float(d["multiple"]))
    if t == "fixed_amount":
        return FixedAmountCap(money=money_from_dict(d["money"]))
    if t == "reference":
        return ReferenceCap(ref=ReferenceTarget(d["ref"]), multiplier=float(d["multiplier"]))
    if t == "unlimited":
        return UnlimitedCap()
    raise ValueError(f"unknown cap operand type {t!r}")


def cap_expression_to_dict(expr: CapExpression) -> Dict[str, Any]:
    return {
        "operator": expr.operator.value,
        "operands": [cap_operand_to_dict(o) for o in expr.operands],
    }


def cap_expression_from_dict(d: Dict[str, Any]) -> CapExpression:
    return CapExpression(
        operator=CapOperator(d["operator"]),
        operands=[cap_operand_from_dict(o) for o in d["operands"]],
    )
