from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from policy_grammar.money import MoneyAmount


def _deal_value_as_money(deal_value: Any) -> Optional[MoneyAmount]:
    """Convert reviewer-supplied deal_value to MoneyAmount when safely numeric."""
    if not isinstance(deal_value, (int, float)) or isinstance(deal_value, bool):
        return None
    if isinstance(deal_value, float) and deal_value != deal_value:  # NaN
        return None
    return MoneyAmount.from_number(str(deal_value))


def evaluation_context_from_review_context(context: Optional[Dict[str, Any]]) -> "EvaluationContext":
    """Build EvaluationContext from apply_policies_for_review's context dict."""
    if not context:
        return EvaluationContext()
    acv = _deal_value_as_money(context.get("deal_value"))
    return EvaluationContext(
        annual_contract_value=acv,
        contract_value=acv,
        counterparty_role=context.get("customer_type"),
        contract_type=context.get("business_unit"),
    )


@dataclass(frozen=True)
class EvaluationContext:
    """Deal/contract facts supplied at review time — never stored in policy.

    Trailing-period fees are distinct from annual_contract_value. Do not
    silently equate them during monetary resolution."""
    annual_contract_value: Optional[MoneyAmount] = None
    contract_value: Optional[MoneyAmount] = None
    annual_fees: Optional[MoneyAmount] = None
    trailing_period_fees: Optional[MoneyAmount] = None
    trailing_period_months: Optional[float] = None
    counterparty_role: Optional[str] = None
    governing_law: Optional[str] = None
    contract_type: Optional[str] = None

    def fee_amount_for_basis(self, basis: str) -> Optional[MoneyAmount]:
        """Map explicit fee basis to the correct context field."""
        if basis in ("FEES_PAID", "FEES_PAID_OR_PAYABLE", "CONTRACT_FEES"):
            return self.trailing_period_fees or self.annual_fees
        if basis == "FEES_PAYABLE":
            return self.annual_fees
        return None
