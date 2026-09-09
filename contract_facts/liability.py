"""Authoritative contract-side Limitation of Liability facts.

Uses policy_grammar CapExpression / CapOperand so fee-period caps are
first-class on the contract side — the same axis policy v2 evaluates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from contract_facts.evidence import EvidenceSpan
from contract_facts.fact import EstablishedFact
from contract_facts.presence import Presence
from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import CapOperand, FeeRelativeCap
from policy_grammar.serialization import cap_expression_from_dict, cap_expression_to_dict


class CategoryTreatmentKind(str, Enum):
    UNCAPPED = "uncapped"
    SUPER_CAP = "super_cap"
    WITHIN_GENERAL_CAP = "within_general_cap"
    NOT_ADDRESSED = "not_addressed"
    UNKNOWN = "unknown"


class MutualityStatus(str, Enum):
    MUTUAL = "mutual"
    ONE_SIDED = "one_sided"
    UNKNOWN = "unknown"


# Categories shared with interaction_rules / liability carve-out vocabulary.
LIABILITY_CATEGORIES: Tuple[str, ...] = (
    "ip_infringement",
    "data_breach",
    "confidentiality",
    "indemnification",
    "fraud",
    "gross_negligence",
    "willful_misconduct",
)


@dataclass(frozen=True)
class CategoryTreatmentFact:
    category: str
    treatment: CategoryTreatmentKind
    category_cap: Optional[CapExpression] = None
    evidence: Optional[EvidenceSpan] = None
    unresolved_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.treatment is CategoryTreatmentKind.UNKNOWN and not self.unresolved_reason:
            raise ValueError("UNKNOWN CategoryTreatmentFact requires unresolved_reason")
        if self.treatment is CategoryTreatmentKind.SUPER_CAP and self.category_cap is None:
            raise ValueError("SUPER_CAP CategoryTreatmentFact requires category_cap")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "treatment": self.treatment.value,
            "category_cap": cap_expression_to_dict(self.category_cap) if self.category_cap else None,
            "evidence": self.evidence.as_dict() if self.evidence else None,
            "unresolved_reason": self.unresolved_reason,
        }


@dataclass(frozen=True)
class LiabilityProvisionFacts:
    """One LoL provision (a document may have several before reconciliation)."""

    provision_id: str
    general_cap: EstablishedFact[CapExpression]
    mutuality: EstablishedFact[MutualityStatus] = field(
        default_factory=lambda: EstablishedFact.unknown("mutuality not evaluated"),
    )
    consequential_damages_excluded: EstablishedFact[bool] = field(
        default_factory=lambda: EstablishedFact.unknown("consequential damages not evaluated"),
    )
    category_treatments: Tuple[CategoryTreatmentFact, ...] = ()
    evidence: Optional[EvidenceSpan] = None
    section_label: Optional[str] = None
    is_amendment: bool = False

    def fee_period_months(self) -> Optional[float]:
        """Symbolic fee-period months when the general cap is a simple FeeRelativeCap."""
        if not self.general_cap.is_known or self.general_cap.value is None:
            return None
        expr = self.general_cap.value
        if expr.operator is not CapOperator.SIMPLE or len(expr.operands) != 1:
            return None
        operand = expr.operands[0]
        if isinstance(operand, FeeRelativeCap):
            return float(operand.months)
        return None

    def treatment_for(self, category: str) -> CategoryTreatmentFact:
        for t in self.category_treatments:
            if t.category == category:
                return t
        return CategoryTreatmentFact(
            category=category,
            treatment=CategoryTreatmentKind.NOT_ADDRESSED,
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provision_id": self.provision_id,
            "general_cap": self.general_cap.as_dict(
                value_to_dict=cap_expression_to_dict,
            ),
            "mutuality": self.mutuality.as_dict(
                value_to_dict=lambda v: v.value,
            ),
            "consequential_damages_excluded": self.consequential_damages_excluded.as_dict(),
            "category_treatments": [t.as_dict() for t in self.category_treatments],
            "evidence": self.evidence.as_dict() if self.evidence else None,
            "section_label": self.section_label,
            "is_amendment": self.is_amendment,
            "fee_period_months": self.fee_period_months(),
        }


@dataclass(frozen=True)
class ContractLiabilityFacts:
    """Document-level LoL facts after provision discovery / reconciliation."""

    clause_presence: Presence
    provisions: Tuple[LiabilityProvisionFacts, ...] = ()
    controlling_provision_id: Optional[str] = None
    reconciliation: str = "none"  # none | single | reconciled | unreconciled
    reconciliation_explanation: Optional[str] = None
    absence_state: str = "CONFIRMED_ABSENT"
    unresolved_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.clause_presence is Presence.PRESENT and not self.provisions:
            raise ValueError("PRESENT ContractLiabilityFacts requires at least one provision")
        if self.controlling_provision_id:
            ids = {p.provision_id for p in self.provisions}
            if self.controlling_provision_id not in ids:
                raise ValueError("controlling_provision_id must refer to a known provision")

    @property
    def controlling(self) -> Optional[LiabilityProvisionFacts]:
        if not self.controlling_provision_id:
            return None
        for p in self.provisions:
            if p.provision_id == self.controlling_provision_id:
                return p
        return None

    def category_treatments_for_interactions(self) -> List[Dict[str, Any]]:
        """Shape expected by interaction_rules._by_category (list of dicts)."""
        controlling = self.controlling
        if controlling is None:
            return []
        return [
            {
                "category": t.category,
                "treatment": t.treatment.value,
                "established": t.treatment is not CategoryTreatmentKind.UNKNOWN,
                "raw_excerpt": t.evidence.excerpt if t.evidence else "",
            }
            for t in controlling.category_treatments
        ]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "clause_presence": self.clause_presence.value,
            "provisions": [p.as_dict() for p in self.provisions],
            "controlling_provision_id": self.controlling_provision_id,
            "reconciliation": self.reconciliation,
            "reconciliation_explanation": self.reconciliation_explanation,
            "absence_state": self.absence_state,
            "unresolved_reason": self.unresolved_reason,
            "category_treatments_for_interactions": self.category_treatments_for_interactions(),
        }


def simple_fee_period_cap(
    months: float,
    *,
    basis=None,
    scope=None,
) -> CapExpression:
    """Convenience constructor for the common 'N months fees paid/payable' form."""
    from policy_grammar.fee_relative import FeeBasis, FeeScope

    return CapExpression(
        operator=CapOperator.SIMPLE,
        operands=[
            FeeRelativeCap(
                months=months,
                basis=basis or FeeBasis.FEES_PAID_OR_PAYABLE,
                scope=scope or FeeScope.AGREEMENT,
            )
        ],
    )
