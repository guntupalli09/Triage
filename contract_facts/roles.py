"""Contract-side role model — document parties and contextual role bindings.

Contextual roles (indemnifying party / indemnified party) must be bindable
to concrete document parties per obligation, not treated as free-floating
pronouns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from contract_facts.evidence import EvidenceSpan
from contract_facts.fact import EstablishedFact
from contract_facts.presence import Presence
from policy_grammar.roles import NormalizedRole, TransactionOrientation


class ContextualRoleKind(str, Enum):
    """Roles that only make sense relative to a specific obligation."""

    INDEMNIFYING_PARTY = "indemnifying_party"
    INDEMNIFIED_PARTY = "indemnified_party"
    OBLIGOR = "obligor"
    BENEFICIARY = "beneficiary"
    RECEIVING_PARTY = "receiving_party"
    DISCLOSING_PARTY = "disclosing_party"


@dataclass(frozen=True)
class DocumentParty:
    """A named party as defined in the contract."""

    name: str
    aliases: tuple[str, ...] = ()
    normalized_role: Optional[NormalizedRole] = None
    orientation: Optional[TransactionOrientation] = None
    evidence: Optional[EvidenceSpan] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "aliases": list(self.aliases),
            "normalized_role": self.normalized_role.value if self.normalized_role else None,
            "orientation": self.orientation.value if self.orientation else None,
            "evidence": self.evidence.as_dict() if self.evidence else None,
        }


@dataclass(frozen=True)
class RoleBinding:
    """Binds a contextual role to a concrete document party for one scope.

    Example: for Customer→Provider indemnity, indemnifying_party → Customer.
    UNKNOWN binding means the pronoun/role could not be resolved — never
    silently treat that as "not required" or "counterparty controls."
    """

    kind: ContextualRoleKind
    party_name: Optional[str]
    presence: Presence
    evidence: Optional[EvidenceSpan] = None
    unresolved_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.presence is Presence.PRESENT and not self.party_name:
            raise ValueError("PRESENT RoleBinding requires party_name")
        if self.presence is Presence.UNKNOWN and not self.unresolved_reason:
            raise ValueError("UNKNOWN RoleBinding requires unresolved_reason")

    @classmethod
    def bound(
        cls, kind: ContextualRoleKind, party_name: str, evidence: Optional[EvidenceSpan] = None,
    ) -> "RoleBinding":
        return cls(kind=kind, party_name=party_name, presence=Presence.PRESENT, evidence=evidence)

    @classmethod
    def unknown(
        cls, kind: ContextualRoleKind, reason: str, evidence: Optional[EvidenceSpan] = None,
    ) -> "RoleBinding":
        return cls(
            kind=kind, party_name=None, presence=Presence.UNKNOWN,
            evidence=evidence, unresolved_reason=reason,
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "party_name": self.party_name,
            "presence": self.presence.value,
            "evidence": self.evidence.as_dict() if self.evidence else None,
            "unresolved_reason": self.unresolved_reason,
        }


@dataclass(frozen=True)
class DocumentRoleModel:
    """Document-level party roster plus any global mutuality signal."""

    parties: tuple[DocumentParty, ...] = ()
    reviewing_orientation: Optional[TransactionOrientation] = None
    mutuality: EstablishedFact[str] = field(
        default_factory=lambda: EstablishedFact.unknown("mutuality not evaluated"),
    )

    def party_by_name(self, name: str) -> Optional[DocumentParty]:
        key = name.lower()
        for party in self.parties:
            if party.name.lower() == key:
                return party
            if any(a.lower() == key for a in party.aliases):
                return party
        return None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "parties": [p.as_dict() for p in self.parties],
            "reviewing_orientation": (
                self.reviewing_orientation.value if self.reviewing_orientation else None
            ),
            "mutuality": self.mutuality.as_dict(),
        }
