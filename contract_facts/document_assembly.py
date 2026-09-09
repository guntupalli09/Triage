"""Assemble ContractDocumentFacts from legacy adapter extracts (Phase 4).

Interaction rules consume these structured facts instead of relying only on
lossy PolicyDecision.category_treatments. Assembly never invents facts —
it bridges what liability / indemnification / commercial extractors already
established.
"""
from __future__ import annotations

from typing import Any, Optional

from contract_facts.commercial import ContractCommercialFacts
from contract_facts.document import ContractDocumentFacts
from contract_facts.indemnification_bridge import assemble_indemnification_family
from contract_facts.liability_bridge import canonical_liability_from_legacy


def assemble_document_facts_from_legacy(
    *,
    liability_facts: Any = None,
    indemnification_facts: Any = None,
    commercial_facts: Optional[ContractCommercialFacts] = None,
) -> ContractDocumentFacts:
    """Build document facts from already-computed adapter extracts."""
    liability = None
    if liability_facts is not None:
        liability = canonical_liability_from_legacy(liability_facts)

    indemnification = None
    roles = None
    cross_clause = None
    if indemnification_facts is not None and getattr(indemnification_facts, "clause_found", False):
        family = assemble_indemnification_family(indemnification_facts)
        indemnification = family["indemnification"]
        roles = family["roles"]
        cross_clause = family["cross_clause"]

    kwargs: dict = {"liability": liability, "indemnification": indemnification}
    if commercial_facts is not None:
        kwargs["commercial"] = commercial_facts
    if roles is not None:
        kwargs["roles"] = roles
    if cross_clause is not None:
        kwargs["cross_clause"] = cross_clause
    return ContractDocumentFacts(**kwargs)


def assemble_document_facts(contract_text: str) -> ContractDocumentFacts:
    """Extract liability + indemnification + commercial once and assemble.

    Used by the cutover interaction path when outcomes do not already carry
    structured extracts. Prefer assemble_document_facts_from_legacy when
    extracts are already available from evaluate_active_policies.
    """
    import indemnification_policy_engine as ipe
    import liability_policy_engine as lpe
    from contract_facts.commercial_extract import extract_commercial_facts

    return assemble_document_facts_from_legacy(
        liability_facts=lpe.extract_liability_facts(contract_text),
        indemnification_facts=ipe.extract_indemnification_facts(contract_text),
        commercial_facts=extract_commercial_facts(contract_text),
    )
