"""Hydrate PolicyDecision.category_treatments from canonical document facts.

Phase 4: LoL v2 decisions historically left category_treatments empty
(_base_decision). Interaction predicates that join on those treatments
then silently NOT_TRIGGERED. Hydration restores structured carve-out /
trigger coverage without re-parsing inside the Interaction Engine.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from contract_facts.document import ContractDocumentFacts
from contract_facts.presence import Presence
from policy_engine_core import PolicyDecision


def _merge_treatments(existing: List[dict], incoming: List[dict]) -> List[dict]:
    by_cat = {t["category"]: dict(t) for t in existing if t.get("category")}
    for t in incoming:
        cat = t.get("category")
        if not cat:
            continue
        if cat not in by_cat:
            by_cat[cat] = dict(t)
            continue
        cur = by_cat[cat]
        if not cur.get("established") and t.get("established"):
            by_cat[cat] = dict(t)
        elif cur.get("treatment") in (None, "", "not_addressed") and t.get("treatment") not in (None, ""):
            by_cat[cat] = dict(t)
    return list(by_cat.values())


def _indemnification_within_cap_from_facts(document_facts: ContractDocumentFacts) -> Optional[dict]:
    """Synthesize liability category 'indemnification' = within_general_cap.

    Prefers an established carve-out on the liability provision; otherwise
    uses §6.3-style CrossClauseGraph.LIABILITY_APPLIES_TO_INDEMNIFICATION.
    """
    liability = document_facts.liability
    if liability is not None and liability.controlling is not None:
        treatment = liability.controlling.treatment_for("indemnification")
        if treatment.treatment.value in ("within_general_cap", "uncapped", "super_cap"):
            return {
                "category": "indemnification",
                "treatment": treatment.treatment.value,
                "established": True,
                "raw_excerpt": treatment.evidence.excerpt if treatment.evidence else "",
            }

    link = document_facts.cross_clause.liability_applies_to_indemnification()
    if link is not None and link.presence is Presence.PRESENT:
        return {
            "category": "indemnification",
            "treatment": "within_general_cap",
            "established": True,
            "raw_excerpt": link.evidence.excerpt if link.evidence else "",
            "source": "cross_clause.liability_applies_to_indemnification",
        }
    return None


def hydrate_decisions_from_document_facts(
    decisions: Dict[str, PolicyDecision],
    document_facts: Optional[ContractDocumentFacts],
) -> Dict[str, PolicyDecision]:
    """Fill / merge category_treatments from structured facts. Mutates in place."""
    if document_facts is None:
        return decisions

    lol = decisions.get("limitation_of_liability")
    if lol is not None:
        incoming: List[dict] = []
        if document_facts.liability is not None:
            incoming.extend(document_facts.liability.category_treatments_for_interactions())
        synth = _indemnification_within_cap_from_facts(document_facts)
        if synth is not None:
            incoming = _merge_treatments(incoming, [synth])
        if incoming:
            lol.category_treatments = _merge_treatments(list(lol.category_treatments or []), incoming)

    indem = decisions.get("indemnification")
    if indem is not None and document_facts.indemnification is not None:
        incoming = document_facts.indemnification.category_treatments_for_interactions()
        if incoming:
            indem.category_treatments = _merge_treatments(list(indem.category_treatments or []), incoming)

    return decisions
