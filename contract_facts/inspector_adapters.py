"""Refine clause-quality inspectors from canonical ContractDocumentFacts (Phase 5).

Inspectors remain useful when facts are absent. When facts *are* present,
override only dimensions the canonical layer has established as PRESENT or
ABSENT. UNKNOWN never becomes False — fail-closed / no false-safe confidence.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, List, Optional

from clause_quality import (
    ClauseElement,
    IndemnificationQualityReport,
    LiabilityQualityReport,
)
from contract_facts.document import ContractDocumentFacts
from contract_facts.indemnification import TriggerCoverage
from contract_facts.liability import MutualityStatus
from contract_facts.presence import Presence


def _replace_element(elements: List[ClauseElement], key: str, *, present: bool, detail: str) -> List[ClauseElement]:
    out: List[ClauseElement] = []
    for e in elements:
        if e.key == key:
            out.append(replace(e, present=present, detail=detail, reasoning_chain=None if present else e.reasoning_chain))
        else:
            out.append(e)
    return out


def refine_liability_quality(
    report: LiabilityQualityReport,
    document_facts: Optional[ContractDocumentFacts],
) -> LiabilityQualityReport:
    """Overlay liability inspector elements from canonical liability facts."""
    if not report.applicable or document_facts is None or document_facts.liability is None:
        return report
    liability = document_facts.liability
    if liability.clause_presence is not Presence.PRESENT:
        return report

    controlling = liability.controlling
    if controlling is None:
        return report

    elements = list(report.elements)

    # Cap present
    cap = controlling.general_cap
    if cap.presence is Presence.PRESENT:
        elements = _replace_element(
            elements, "cap_present", present=True,
            detail="A liability cap is established in canonical contract facts.",
        )
    elif cap.presence is Presence.ABSENT:
        elements = _replace_element(
            elements, "cap_present", present=False,
            detail="Canonical facts establish no general liability cap.",
        )
    # UNKNOWN → leave regex result untouched

    mut = controlling.mutuality
    if mut.presence is Presence.PRESENT and mut.value is MutualityStatus.MUTUAL:
        elements = _replace_element(
            elements, "mutual_application", present=True,
            detail="Canonical facts establish mutual liability application.",
        )
    elif mut.presence is Presence.PRESENT and mut.value is MutualityStatus.ONE_SIDED:
        elements = _replace_element(
            elements, "mutual_application", present=False,
            detail="Canonical facts establish one-sided liability application.",
        )

    cons = controlling.consequential_damages_excluded
    if cons.presence is Presence.PRESENT and cons.value is True:
        elements = _replace_element(
            elements, "consequential_damages_excluded", present=True,
            detail="Canonical facts establish consequential damages are excluded.",
        )
    elif cons.presence is Presence.PRESENT and cons.value is False:
        elements = _replace_element(
            elements, "consequential_damages_excluded", present=False,
            detail="Canonical facts establish consequential damages are not excluded.",
        )
    elif cons.presence is Presence.ABSENT:
        elements = _replace_element(
            elements, "consequential_damages_excluded", present=False,
            detail="Canonical facts establish consequential-damages exclusion is absent.",
        )

    score = sum(e.weight for e in elements if e.present)
    return LiabilityQualityReport(applicable=True, score=score, elements=elements)


def refine_indemnification_quality(
    report: IndemnificationQualityReport,
    document_facts: Optional[ContractDocumentFacts],
) -> IndemnificationQualityReport:
    """Overlay indemnification inspector elements from canonical indemnity facts."""
    if not report.applicable or document_facts is None or document_facts.indemnification is None:
        return report
    indem = document_facts.indemnification
    if indem.clause_presence is not Presence.PRESENT:
        return report

    elements = list(report.elements)

    # Mutual / reciprocal: ≥2 directional obligations with opposite directions
    if len(indem.obligations) >= 2:
        pairs = {
            (o.indemnifying_party.lower(), o.indemnified_party.lower())
            for o in indem.obligations
        }
        reciprocal = any((b, a) in pairs for a, b in pairs)
        if reciprocal:
            elements = _replace_element(
                elements, "mutual_or_reciprocal", present=True,
                detail="Canonical facts establish reciprocal directional indemnities.",
            )

    # IP indemnity from trigger coverage
    ip_covered = any(
        t.coverage is TriggerCoverage.COVERED and t.trigger == "ip_infringement"
        for o in indem.obligations
        for t in o.triggers
    )
    if ip_covered:
        elements = _replace_element(
            elements, "ip_indemnity", present=True,
            detail="Canonical facts establish IP infringement indemnity coverage "
                   "(including patent/copyright/trademark enumerations).",
        )

    # Procedure: defense / notice / coop from shared procedures
    if indem.procedures:
        proc = indem.procedures[0]
        defense = proc.defense_control
        if defense.presence is Presence.PRESENT and defense.value is not None:
            bind = defense.value.binds_to_indemnifying_party(None)
            if bind is Presence.PRESENT or defense.value.holder.value in (
                "indemnifying_party", "shared",
            ):
                elements = _replace_element(
                    elements, "defense_obligation", present=True,
                    detail="Canonical shared procedure establishes defense control.",
                )
        notice = proc.prompt_notice_required
        if notice.presence is Presence.PRESENT and notice.value is True:
            elements = _replace_element(
                elements, "notification_requirement", present=True,
                detail="Canonical shared procedure establishes notice requirement.",
            )
        coop = proc.cooperation_required
        if coop.presence is Presence.PRESENT and coop.value is True:
            elements = _replace_element(
                elements, "limitations_or_procedure", present=True,
                detail="Canonical shared procedure establishes defense/cooperation procedure.",
            )

    score = sum(e.weight for e in elements if e.present)
    return IndemnificationQualityReport(applicable=True, score=score, elements=elements)


def refine_clause_quality_bundle(
    clause_quality: dict,
    document_facts: Optional[ContractDocumentFacts],
) -> dict:
    """Apply refinements to an already-built clause_quality as_dict bundle.

    Used when callers only have dicts; prefer refine_* on typed reports
    inside RuleEngine.analyze.
    """
    if document_facts is None or not clause_quality:
        return clause_quality
    # Reconstruct minimal typed reports is awkward from dicts; callers
    # should refine before as_dict(). This helper is a no-op reserved for
    # future dict-level overlays.
    return clause_quality
