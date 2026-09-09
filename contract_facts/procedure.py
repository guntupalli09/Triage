"""Shared procedure facts — defense, notice, cooperation, settlement.

Procedure subsections (e.g. §5.3) must be attachable to multiple directional
obligations without re-parsing, and without collapsing into a single global
boolean for the whole indemnification family.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from contract_facts.evidence import EvidenceSpan
from contract_facts.fact import EstablishedFact
from contract_facts.presence import Presence
from contract_facts.roles import ContextualRoleKind, RoleBinding


class DefenseControlHolder(str, Enum):
    INDEMNIFYING_PARTY = "indemnifying_party"
    INDEMNIFIED_PARTY = "indemnified_party"
    NAMED_PARTY = "named_party"
    SHARED = "shared"


@dataclass(frozen=True)
class DefenseControl:
    """Who controls defense/settlement for a claim under an indemnity."""

    holder: DefenseControlHolder
    named_party: Optional[str] = None
    settlement_consent_required: EstablishedFact[bool] = field(
        default_factory=lambda: EstablishedFact.unknown("settlement consent not evaluated"),
    )

    def __post_init__(self) -> None:
        if self.holder is DefenseControlHolder.NAMED_PARTY and not self.named_party:
            raise ValueError("NAMED_PARTY DefenseControl requires named_party")

    def binds_to_indemnifying_party(self, indemnifying_party_name: Optional[str]) -> Presence:
        """Whether this control satisfies 'indemnifying party controls defense'.

        Returns Presence rather than bool so UNKNOWN stays explicit when the
        holder is NAMED_PARTY but role binding is unresolved.
        """
        if self.holder is DefenseControlHolder.INDEMNIFYING_PARTY:
            return Presence.PRESENT
        if self.holder is DefenseControlHolder.SHARED:
            return Presence.PRESENT
        if self.holder is DefenseControlHolder.INDEMNIFIED_PARTY:
            return Presence.ABSENT
        if self.holder is DefenseControlHolder.NAMED_PARTY:
            if not indemnifying_party_name or not self.named_party:
                return Presence.UNKNOWN
            if self.named_party.lower() == indemnifying_party_name.lower():
                return Presence.PRESENT
            return Presence.ABSENT
        return Presence.UNKNOWN

    def as_dict(self) -> Dict[str, Any]:
        return {
            "holder": self.holder.value,
            "named_party": self.named_party,
            "settlement_consent_required": self.settlement_consent_required.as_dict(),
        }


@dataclass(frozen=True)
class SharedProcedure:
    """Procedure language that applies to one or more obligations.

    A single SharedProcedure instance may be referenced by multiple
    IndemnityObligationFacts (e.g. §5.3 applying to both §5.1 and §5.2).
    """

    procedure_id: str
    defense_control: EstablishedFact[DefenseControl] = field(
        default_factory=lambda: EstablishedFact.unknown("defense control not evaluated"),
    )
    prompt_notice_required: EstablishedFact[bool] = field(
        default_factory=lambda: EstablishedFact.unknown("prompt notice not evaluated"),
    )
    cooperation_required: EstablishedFact[bool] = field(
        default_factory=lambda: EstablishedFact.unknown("cooperation not evaluated"),
    )
    role_bindings: Tuple[RoleBinding, ...] = ()
    evidence: Optional[EvidenceSpan] = None
    section_label: Optional[str] = None

    def binding_for(self, kind: ContextualRoleKind) -> Optional[RoleBinding]:
        for binding in self.role_bindings:
            if binding.kind is kind:
                return binding
        return None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "procedure_id": self.procedure_id,
            "defense_control": self.defense_control.as_dict(
                value_to_dict=lambda v: v.as_dict(),
            ),
            "prompt_notice_required": self.prompt_notice_required.as_dict(),
            "cooperation_required": self.cooperation_required.as_dict(),
            "role_bindings": [b.as_dict() for b in self.role_bindings],
            "evidence": self.evidence.as_dict() if self.evidence else None,
            "section_label": self.section_label,
        }
