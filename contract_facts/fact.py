"""EstablishedFact — value + presence + evidence, never bare Optionals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

from contract_facts.evidence import EvidenceSpan
from contract_facts.presence import Presence

T = TypeVar("T")


@dataclass(frozen=True)
class EstablishedFact(Generic[T]):
    """A single contract-side fact with explicit presence and provenance.

    Invariants:
    - If presence is PRESENT, value must be non-None (unless value_type
      itself permits a meaningful None, which these schemas avoid).
    - If presence is ABSENT or UNKNOWN, value must be None.
    - Evidence may be attached in any presence state (e.g. UNKNOWN with an
      excerpt that could not be normalized).
    """

    presence: Presence
    value: Optional[T] = None
    evidence: Optional[EvidenceSpan] = None
    unresolved_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.presence is Presence.PRESENT and self.value is None:
            raise ValueError("EstablishedFact with presence=PRESENT requires a value")
        if self.presence is not Presence.PRESENT and self.value is not None:
            raise ValueError(
                f"EstablishedFact with presence={self.presence.value} must not carry a value"
            )
        if self.presence is Presence.UNKNOWN and not self.unresolved_reason:
            raise ValueError("EstablishedFact with presence=UNKNOWN requires unresolved_reason")

    @classmethod
    def present(cls, value: T, evidence: Optional[EvidenceSpan] = None) -> "EstablishedFact[T]":
        return cls(presence=Presence.PRESENT, value=value, evidence=evidence)

    @classmethod
    def absent(cls, evidence: Optional[EvidenceSpan] = None) -> "EstablishedFact[T]":
        return cls(presence=Presence.ABSENT, value=None, evidence=evidence)

    @classmethod
    def unknown(
        cls, reason: str, evidence: Optional[EvidenceSpan] = None,
    ) -> "EstablishedFact[T]":
        return cls(
            presence=Presence.UNKNOWN,
            value=None,
            evidence=evidence,
            unresolved_reason=reason,
        )

    @property
    def is_known(self) -> bool:
        return self.presence is Presence.PRESENT

    def as_dict(self, value_to_dict: Optional[Callable[[T], Any]] = None) -> Dict[str, Any]:
        if self.value is None:
            serialized_value = None
        elif value_to_dict is not None:
            serialized_value = value_to_dict(self.value)
        else:
            serialized_value = self.value
        return {
            "presence": self.presence.value,
            "value": serialized_value,
            "evidence": self.evidence.as_dict() if self.evidence else None,
            "unresolved_reason": self.unresolved_reason,
        }
