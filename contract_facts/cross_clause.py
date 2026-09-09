"""Cross-clause relationships — distinct from monetary cross-references.

The forensic audit found that §6.3 language ("limitations apply to Section 5
indemnification") was mis-typed as MonetaryTreatment.kind=cross_reference,
which aborted indemnification evaluation. That semantic belongs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from contract_facts.evidence import EvidenceSpan
from contract_facts.presence import Presence


class CrossClauseKind(str, Enum):
    """Typed relationships between clause families."""

    # Liability limitations expressly apply to indemnification claims/obligations.
    LIABILITY_APPLIES_TO_INDEMNIFICATION = "liability_applies_to_indemnification"
    # Indemnification expressly carved out of / excluded from liability cap.
    INDEMNIFICATION_CARVED_OUT_OF_LIABILITY = "indemnification_carved_out_of_liability"
    # A category (e.g. confidentiality) is stated to ride inside the general cap.
    CATEGORY_WITHIN_LIABILITY_CAP = "category_within_liability_cap"
    # A category is stated uncapped / outside the general cap.
    CATEGORY_OUTSIDE_LIABILITY_CAP = "category_outside_liability_cap"
    # Generic structural cross-reference between named sections (non-monetary).
    SECTION_CROSS_REFERENCE = "section_cross_reference"
    # Catch-all for recognized but not yet enumerated relationships.
    OTHER = "other"


class ClauseFamily(str, Enum):
    LIMITATION_OF_LIABILITY = "limitation_of_liability"
    INDEMNIFICATION = "indemnification"
    CONFIDENTIALITY = "confidentiality"
    DATA_SECURITY = "data_security"
    INSURANCE = "insurance"
    IP_OWNERSHIP = "ip_ownership"
    PAYMENT_TERMS = "payment_terms"
    TERMINATION = "termination"
    WARRANTIES = "warranties"
    SLA = "sla"
    ASSIGNMENT = "assignment"
    GOVERNING_LAW = "governing_law"
    OTHER = "other"


@dataclass(frozen=True)
class CrossClauseRelationship:
    """One typed relationship between clause families or named sections.

    This is NOT a monetary delegation. MonetaryTreatmentFact.CROSS_REFERENCE
    remains the representation for 'cap is as set forth in Schedule B'.
    """

    relationship_id: str
    kind: CrossClauseKind
    source_family: ClauseFamily
    target_family: ClauseFamily
    presence: Presence
    source_section_label: Optional[str] = None
    target_section_label: Optional[str] = None
    category: Optional[str] = None  # when kind is category-scoped
    evidence: Optional[EvidenceSpan] = None
    unresolved_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.presence is Presence.UNKNOWN and not self.unresolved_reason:
            raise ValueError("UNKNOWN CrossClauseRelationship requires unresolved_reason")
        if self.presence is Presence.ABSENT:
            raise ValueError(
                "CrossClauseRelationship should be omitted when ABSENT; "
                "do not store negative relationships as ABSENT rows"
            )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "kind": self.kind.value,
            "source_family": self.source_family.value,
            "target_family": self.target_family.value,
            "presence": self.presence.value,
            "source_section_label": self.source_section_label,
            "target_section_label": self.target_section_label,
            "category": self.category,
            "evidence": self.evidence.as_dict() if self.evidence else None,
            "unresolved_reason": self.unresolved_reason,
        }


@dataclass(frozen=True)
class CrossClauseGraph:
    """Document-level set of cross-clause relationships."""

    relationships: Tuple[CrossClauseRelationship, ...] = ()

    def of_kind(self, kind: CrossClauseKind) -> Tuple[CrossClauseRelationship, ...]:
        return tuple(r for r in self.relationships if r.kind is kind)

    def liability_applies_to_indemnification(self) -> Optional[CrossClauseRelationship]:
        matches = self.of_kind(CrossClauseKind.LIABILITY_APPLIES_TO_INDEMNIFICATION)
        return matches[0] if matches else None

    def as_dict(self) -> Dict[str, Any]:
        return {"relationships": [r.as_dict() for r in self.relationships]}
