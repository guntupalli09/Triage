from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from policy_grammar.money import MoneyAmount


class AcvSource(str, Enum):
    """Provenance for EvaluationContext.annual_contract_value.

    Precedence (highest first):
      1. REVIEWER_DEAL_VALUE — reviewer-supplied deal_value at review time
      2. CONTRACT_ANNUAL_FEES — annual fees established from contract text
      3. UNSPECIFIED — no ACV available

    Trailing-period fees are never used as ACV (see fee_amount_for_basis).
    """

    REVIEWER_DEAL_VALUE = "reviewer_deal_value"
    CONTRACT_ANNUAL_FEES = "contract_annual_fees"
    UNSPECIFIED = "unspecified"


def _deal_value_as_money(deal_value: Any) -> Optional[MoneyAmount]:
    """Convert reviewer-supplied deal_value to MoneyAmount when safely numeric."""
    if not isinstance(deal_value, (int, float)) or isinstance(deal_value, bool):
        return None
    if isinstance(deal_value, float) and deal_value != deal_value:  # NaN
        return None
    return MoneyAmount.from_number(str(deal_value))


def resolve_annual_contract_value(
    *,
    reviewer_deal_value: Any = None,
    contract_annual_fees: Optional[MoneyAmount] = None,
) -> tuple[Optional[MoneyAmount], AcvSource]:
    """Resolve ACV with explicit provenance. Never equates trailing fees to ACV."""
    reviewer = _deal_value_as_money(reviewer_deal_value)
    if reviewer is not None:
        return reviewer, AcvSource.REVIEWER_DEAL_VALUE
    if contract_annual_fees is not None:
        return contract_annual_fees, AcvSource.CONTRACT_ANNUAL_FEES
    return None, AcvSource.UNSPECIFIED


def evaluation_context_from_review_context(
    context: Optional[Dict[str, Any]],
    *,
    contract_annual_fees: Optional[MoneyAmount] = None,
) -> "EvaluationContext":
    """Build EvaluationContext from apply_policies_for_review's context dict.

    Optional contract_annual_fees comes from ContractCommercialFacts when
    established; reviewer deal_value still takes precedence when present.
    """
    ctx = context or {}
    # Allow callers to pass pre-parsed contract fees via context as well.
    if contract_annual_fees is None and ctx.get("contract_annual_fees") is not None:
        raw = ctx["contract_annual_fees"]
        if isinstance(raw, MoneyAmount):
            contract_annual_fees = raw
        elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
            contract_annual_fees = MoneyAmount.from_number(str(raw))

    acv, source = resolve_annual_contract_value(
        reviewer_deal_value=ctx.get("deal_value"),
        contract_annual_fees=contract_annual_fees,
    )
    return EvaluationContext(
        annual_contract_value=acv,
        contract_value=acv,
        annual_fees=contract_annual_fees,
        acv_source=source,
        counterparty_role=ctx.get("customer_type"),
        contract_type=ctx.get("business_unit"),
    )


@dataclass(frozen=True)
class EvaluationContext:
    """Deal/contract facts supplied at review time — never stored in policy.

    Trailing-period fees are distinct from annual_contract_value. Do not
    silently equate them during monetary resolution.

    acv_source records which input populated annual_contract_value so
    escalation / band conditions can be audited for provenance.
    """

    annual_contract_value: Optional[MoneyAmount] = None
    contract_value: Optional[MoneyAmount] = None
    annual_fees: Optional[MoneyAmount] = None
    trailing_period_fees: Optional[MoneyAmount] = None
    trailing_period_months: Optional[float] = None
    counterparty_role: Optional[str] = None
    governing_law: Optional[str] = None
    contract_type: Optional[str] = None
    acv_source: AcvSource = AcvSource.UNSPECIFIED

    def fee_amount_for_basis(self, basis: str) -> Optional[MoneyAmount]:
        """Map explicit fee basis to the correct context field."""
        if basis in ("FEES_PAID", "FEES_PAID_OR_PAYABLE", "CONTRACT_FEES"):
            return self.trailing_period_fees or self.annual_fees
        if basis == "FEES_PAYABLE":
            return self.annual_fees
        return None
