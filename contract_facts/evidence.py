"""Evidence / provenance attached to every established contract fact."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class EvidenceSpan:
    """A grounded span in the contract text that supports a fact.

    Offsets are absolute document indices (same convention as Finding /
    PolicyDecision). excerpt is the human-readable slice; it must not be
    treated as the sole identity of the evidence — offsets are authoritative
    when both are present.
    """

    excerpt: str
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    section_label: Optional[str] = None

    def __post_init__(self) -> None:
        if self.start_index is not None and self.end_index is not None:
            if self.end_index < self.start_index:
                raise ValueError("EvidenceSpan.end_index must be >= start_index")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "excerpt": self.excerpt,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "section_label": self.section_label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceSpan":
        return cls(
            excerpt=str(data.get("excerpt") or ""),
            start_index=data.get("start_index"),
            end_index=data.get("end_index"),
            section_label=data.get("section_label"),
        )
