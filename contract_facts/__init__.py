"""Canonical contract-side fact contracts for TriageCounsel.

Phase 1 of the post-audit architecture remediation. Defines authoritative
representations representations for Liability, Indemnification, roles/procedures,
commercial context, and cross-clause relationships.

This package does NOT:
- migrate the ~189 generic rules
- replace existing extract_*_facts implementations yet
- change policy evaluation outcomes by itself

Consumers added in later phases must read these types rather than
re-parsing raw text for the same facts.
"""
from contract_facts.commercial import (
    BillingFrequency,
    ContractCommercialFacts,
    PaymentDueBasis,
    PaymentDueTerms,
)
from contract_facts.cross_clause import (
    ClauseFamily,
    CrossClauseGraph,
    CrossClauseKind,
    CrossClauseRelationship,
)
from contract_facts.document import SCHEMA_VERSION, ContractDocumentFacts
from contract_facts.evidence import EvidenceSpan
from contract_facts.fact import EstablishedFact
from contract_facts.indemnification import (
    INDEMNITY_TRIGGERS,
    ClaimScope,
    ContractIndemnificationFacts,
    IndemnityObligationFacts,
    MonetaryKind,
    MonetaryTreatmentFact,
    TriggerCoverage,
    TriggerTreatmentFact,
)
from contract_facts.indemnification_bridge import (
    assemble_indemnification_family,
    canonical_indemnification_from_legacy,
)
from contract_facts.liability import (
    LIABILITY_CATEGORIES,
    CategoryTreatmentFact,
    CategoryTreatmentKind,
    ContractLiabilityFacts,
    LiabilityProvisionFacts,
    MutualityStatus,
    simple_fee_period_cap,
)
from contract_facts.liability_bridge import (
    canonical_liability_from_legacy,
    category_treatments_for_decision,
    contract_cap_from_canonical,
    legacy_cap_expression_to_policy,
    legacy_cap_value_to_operand,
)
from contract_facts.presence import Presence, presence_from_optional_bool
from contract_facts.procedure import DefenseControl, DefenseControlHolder, SharedProcedure
from contract_facts.roles import (
    ContextualRoleKind,
    DocumentParty,
    DocumentRoleModel,
    RoleBinding,
)

__all__ = [
    "SCHEMA_VERSION",
    "BillingFrequency",
    "CategoryTreatmentFact",
    "CategoryTreatmentKind",
    "ClaimScope",
    "ClauseFamily",
    "ContractCommercialFacts",
    "ContractDocumentFacts",
    "ContractIndemnificationFacts",
    "ContractLiabilityFacts",
    "ContextualRoleKind",
    "CrossClauseGraph",
    "CrossClauseKind",
    "CrossClauseRelationship",
    "DefenseControl",
    "DefenseControlHolder",
    "DocumentParty",
    "DocumentRoleModel",
    "EstablishedFact",
    "EvidenceSpan",
    "INDEMNITY_TRIGGERS",
    "IndemnityObligationFacts",
    "LIABILITY_CATEGORIES",
    "MonetaryKind",
    "MonetaryTreatmentFact",
    "MutualityStatus",
    "PaymentDueBasis",
    "PaymentDueTerms",
    "Presence",
    "RoleBinding",
    "SharedProcedure",
    "TriggerCoverage",
    "TriggerTreatmentFact",
    "LiabilityProvisionFacts",
    "presence_from_optional_bool",
    "assemble_indemnification_family",
    "canonical_indemnification_from_legacy",
    "canonical_liability_from_legacy",
    "category_treatments_for_decision",
    "contract_cap_from_canonical",
    "legacy_cap_expression_to_policy",
    "legacy_cap_value_to_operand",
    "simple_fee_period_cap",
]
