"""
Lawyer Confidence Index.

Product roadmap Feature 7 (see the product memo, Rev. 2): a bare "87%
confidence" invites skepticism from a legal reader; a checklist — "rule
matched exactly, no ambiguity detected, evidence span is bounded, not
flagged in the contradiction pass" — earns trust because it's checkable.

Purely a presentation-layer restructuring of data rules_engine.py already
computes per finding (finding_type, party_direction, evidence_quality,
confidence, confidence_reason — see rules_engine._score_confidence) plus
the document-level contradiction_log. No new detection, and the
underlying confidence classification in _score_confidence is untouched —
this module only reformats its output into an explicit, itemized
breakdown instead of a bare label.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ConfidenceChecklistItem:
    label: str
    met: bool


@dataclass(frozen=True)
class ConfidenceBreakdown:
    confidence: str  # "high" | "medium" | "low" — unchanged, passed through
    checklist: List[ConfidenceChecklistItem]
    reason: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "confidence": self.confidence,
            "checklist": [{"label": i.label, "met": i.met} for i in self.checklist],
            "reason": self.reason,
        }


def _get(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def build_confidence_breakdown(
    finding: Any, contradiction_log: Optional[Dict[str, str]] = None,
) -> ConfidenceBreakdown:
    """`finding` is anything exposing the same attributes/keys as
    rules_engine.Finding (or its dict serialization): finding_type,
    confidence, confidence_reason, evidence_quality, party_direction,
    rule_id, start_index. `contradiction_log` is the dict rules_engine.py's
    analyze() already returns, keyed "{rule_id}_{start_index}"."""
    contradiction_log = contradiction_log or {}

    finding_type = _get(finding, "finding_type", "adverse_language_detected")
    party_direction = _get(finding, "party_direction")
    evidence_quality = _get(finding, "evidence_quality", "bounded")
    confidence = _get(finding, "confidence", "high")
    reason = _get(finding, "confidence_reason", "")
    rule_id = _get(finding, "rule_id", "")
    start_index = _get(finding, "start_index")

    checklist: List[ConfidenceChecklistItem] = [
        ConfidenceChecklistItem(
            label="Direct textual match (not inferred from absence)",
            met=finding_type == "adverse_language_detected",
        ),
    ]

    # Only meaningful for findings the engine actually classified
    # directionally — a non-directional finding has no ambiguity dimension
    # to report either way, so it's omitted rather than shown as a
    # trivially-"met" item.
    if party_direction:
        checklist.append(ConfidenceChecklistItem(
            label="Party direction is unambiguous",
            met=party_direction.get("mutuality_status") != "ambiguous",
        ))

    checklist.append(ConfidenceChecklistItem(
        label="Evidence span is bounded and reviewable",
        met=evidence_quality == "bounded",
    ))

    contradiction_key = f"{rule_id}_{start_index}"
    checklist.append(ConfidenceChecklistItem(
        label="Not flagged in the contradiction-reconciliation pass",
        met=contradiction_key not in contradiction_log,
    ))

    return ConfidenceBreakdown(confidence=confidence, checklist=checklist, reason=reason)
