"""Document-level canonical contract facts aggregate.

This is the authoritative contract-side representation that policy adapters,
interaction rules, inspectors, and (eventually) generic rules should consume.
Phase 1 defines the schema only — no extractor migration, no 189-rule rewrite.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from contract_facts.commercial import ContractCommercialFacts
from contract_facts.cross_clause import CrossClauseGraph
from contract_facts.indemnification import ContractIndemnificationFacts
from contract_facts.liability import ContractLiabilityFacts
from contract_facts.presence import Presence
from contract_facts.roles import DocumentRoleModel


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ContractDocumentFacts:
    """Canonical structured facts for one contract review.

    Authority rules (Phase 1):
    - This object is the contract-side source of truth once populated.
    - PolicyPosition / LiabilityPolicyV2 remain the policy-side source of truth.
    - Generic RuleEngine findings are NOT authoritative for facts represented
      here; they may only surface issues outside these families until migrated.
    - Presence.UNKNOWN must propagate to REQUIRES_REVIEW at evaluation time —
      never coerce to False / ABSENT / ACCEPT.
    """

    schema_version: int = SCHEMA_VERSION
    roles: DocumentRoleModel = field(default_factory=DocumentRoleModel)
    commercial: ContractCommercialFacts = field(default_factory=ContractCommercialFacts)
    liability: Optional[ContractLiabilityFacts] = None
    indemnification: Optional[ContractIndemnificationFacts] = None
    cross_clause: CrossClauseGraph = field(default_factory=CrossClauseGraph)

    def liability_or_unknown(self) -> ContractLiabilityFacts:
        if self.liability is not None:
            return self.liability
        return ContractLiabilityFacts(
            clause_presence=Presence.UNKNOWN,
            absence_state="RECOGNITION_UNCERTAIN",
            unresolved_reason="liability facts not populated",
        )

    def indemnification_or_unknown(self) -> ContractIndemnificationFacts:
        if self.indemnification is not None:
            return self.indemnification
        return ContractIndemnificationFacts(
            clause_presence=Presence.UNKNOWN,
            absence_state="RECOGNITION_UNCERTAIN",
            unresolved_reason="indemnification facts not populated",
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "roles": self.roles.as_dict(),
            "commercial": self.commercial.as_dict(),
            "liability": self.liability.as_dict() if self.liability else None,
            "indemnification": self.indemnification.as_dict() if self.indemnification else None,
            "cross_clause": self.cross_clause.as_dict(),
        }
