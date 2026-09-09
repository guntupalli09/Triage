"""Authoritative commercial / deal-context facts extracted from the contract.

Distinct from reviewer-supplied EvaluationContext.deal_value: contract text
may establish ACV / fees / payment due independently. Policy evaluation may
combine both; neither silently overwrites the other.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from contract_facts.evidence import EvidenceSpan
from contract_facts.fact import EstablishedFact
from policy_grammar.money import MoneyAmount
from policy_grammar.serialization import money_from_dict, money_to_dict


class BillingFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    WEEKLY = "weekly"
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    UNKNOWN = "unknown"


class PaymentDueBasis(str, Enum):
    """What the payment-due clock runs from."""

    INVOICE_RECEIPT = "invoice_receipt"
    INVOICE_DATE = "invoice_date"
    DELIVERY = "delivery"
    ACCEPTANCE = "acceptance"
    EXECUTION = "execution"
    NET = "net"  # bare "Net 30" with no explicit anchor
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PaymentDueTerms:
    days: int
    basis: PaymentDueBasis = PaymentDueBasis.UNKNOWN

    def __post_init__(self) -> None:
        if self.days < 0:
            raise ValueError("PaymentDueTerms.days must be non-negative")

    def as_dict(self) -> Dict[str, Any]:
        return {"days": self.days, "basis": self.basis.value}


@dataclass(frozen=True)
class ContractCommercialFacts:
    """Commercial terms established from contract text."""

    annual_fees: EstablishedFact[MoneyAmount] = field(
        default_factory=lambda: EstablishedFact.unknown("annual fees not evaluated"),
    )
    currency: EstablishedFact[str] = field(
        default_factory=lambda: EstablishedFact.unknown("currency not evaluated"),
    )
    billing_frequency: EstablishedFact[BillingFrequency] = field(
        default_factory=lambda: EstablishedFact.unknown("billing frequency not evaluated"),
    )
    payment_due: EstablishedFact[PaymentDueTerms] = field(
        default_factory=lambda: EstablishedFact.unknown("payment due not evaluated"),
    )
    invoice_trigger: EstablishedFact[str] = field(
        default_factory=lambda: EstablishedFact.unknown("invoice trigger not evaluated"),
    )

    def due_days_or_none(self) -> Optional[int]:
        if self.payment_due.is_known and self.payment_due.value is not None:
            return self.payment_due.value.days
        return None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "annual_fees": self.annual_fees.as_dict(value_to_dict=money_to_dict),
            "currency": self.currency.as_dict(),
            "billing_frequency": self.billing_frequency.as_dict(
                value_to_dict=lambda v: v.value,
            ),
            "payment_due": self.payment_due.as_dict(value_to_dict=lambda v: v.as_dict()),
            "invoice_trigger": self.invoice_trigger.as_dict(),
            "due_days": self.due_days_or_none(),
        }

    def legacy_payment_terms_dict(self) -> Dict[str, Optional[object]]:
        """Shape compatible with rules_engine._extract_payment_terms output."""
        currency = self.currency.value if self.currency.is_known else None
        billing = (
            self.billing_frequency.value.value
            if self.billing_frequency.is_known and self.billing_frequency.value is not None
            else None
        )
        trigger = self.invoice_trigger.value if self.invoice_trigger.is_known else None
        return {
            "due_days": self.due_days_or_none(),
            "currency": currency,
            "billing_frequency": billing,
            "invoice_trigger": trigger,
        }
