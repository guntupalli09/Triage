"""Authoritative contract-side Indemnification facts.

Directional obligations keep provider-side protection and customer-side
exposure separate. Shared procedure is referenced by id, not re-parsed per
obligation. Monetary cross-references stay distinct from cross-clause
relationships (see contract_facts.cross_clause).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from contract_facts.evidence import EvidenceSpan
from contract_facts.fact import EstablishedFact
from contract_facts.presence import Presence
from contract_facts.procedure import SharedProcedure
from contract_facts.roles import RoleBinding


class TriggerCoverage(str, Enum):
    COVERED = "covered"
    EXCLUDED = "excluded"
    NOT_ADDRESSED = "not_addressed"
    UNKNOWN = "unknown"


class ClaimScope(str, Enum):
    THIRD_PARTY_ONLY = "third_party_only"
    INCLUDES_FIRST_PARTY = "includes_first_party"
    NOT_ADDRESSED = "not_addressed"
    UNKNOWN = "unknown"


class MonetaryKind(str, Enum):
    """Monetary treatment of an indemnity obligation.

    CROSS_REFERENCE means the obligation delegates its *monetary* terms to
    another provision (e.g. 'subject to the cap in Section 6'). That is
    NOT the same as a CrossClauseRelationship asserting that liability
    limitations apply to indemnification claims — see cross_clause.py.
    """

    MULTIPLIER = "multiplier"
    FIXED = "fixed"
    UNLIMITED = "unlimited"
    FEE_PERIOD = "fee_period"
    CROSS_REFERENCE = "cross_reference"
    NOT_STATED = "not_stated"
    UNKNOWN = "unknown"


# Closed trigger vocabulary aligned with indemnification_policy_engine.TRIGGERS.
INDEMNITY_TRIGGERS: Tuple[str, ...] = (
    "ip_infringement",
    "data_breach",
    "confidentiality",
    "gross_negligence",
    "willful_misconduct",
    "fraud",
    "law_violations",
    "bodily_injury_property_damage",
    "vendor_security_incidents",
    "customer_materials",
    "unlawful_use",
    "negligence",
)


@dataclass(frozen=True)
class TriggerTreatmentFact:
    trigger: str
    coverage: TriggerCoverage
    evidence: Optional[EvidenceSpan] = None
    unresolved_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.coverage is TriggerCoverage.UNKNOWN and not self.unresolved_reason:
            raise ValueError("UNKNOWN TriggerTreatmentFact requires unresolved_reason")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "trigger": self.trigger,
            "coverage": self.coverage.value,
            "evidence": self.evidence.as_dict() if self.evidence else None,
            "unresolved_reason": self.unresolved_reason,
        }


@dataclass(frozen=True)
class MonetaryTreatmentFact:
    kind: MonetaryKind
    multiplier: Optional[float] = None
    fixed_amount: Optional[float] = None
    fee_period_months: Optional[float] = None
    cross_reference_label: Optional[str] = None
    evidence: Optional[EvidenceSpan] = None
    unresolved_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.kind is MonetaryKind.UNKNOWN and not self.unresolved_reason:
            raise ValueError("UNKNOWN MonetaryTreatmentFact requires unresolved_reason")
        if self.kind is MonetaryKind.CROSS_REFERENCE and not self.cross_reference_label:
            raise ValueError("CROSS_REFERENCE MonetaryTreatmentFact requires cross_reference_label")
        if self.kind is MonetaryKind.FEE_PERIOD and self.fee_period_months is None:
            raise ValueError("FEE_PERIOD MonetaryTreatmentFact requires fee_period_months")

    def summary(self) -> str:
        if self.kind is MonetaryKind.UNLIMITED:
            return "Uncapped"
        if self.kind is MonetaryKind.MULTIPLIER:
            return f"{self.multiplier:g}x annual fees"
        if self.kind is MonetaryKind.FIXED:
            return f"${self.fixed_amount:,.2f} fixed"
        if self.kind is MonetaryKind.FEE_PERIOD:
            return f"{self.fee_period_months:g} months' fees"
        if self.kind is MonetaryKind.CROSS_REFERENCE:
            return f"per {self.cross_reference_label}"
        if self.kind is MonetaryKind.NOT_STATED:
            return "not stated"
        return "unknown"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "multiplier": self.multiplier,
            "fixed_amount": self.fixed_amount,
            "fee_period_months": self.fee_period_months,
            "cross_reference_label": self.cross_reference_label,
            "summary": self.summary(),
            "evidence": self.evidence.as_dict() if self.evidence else None,
            "unresolved_reason": self.unresolved_reason,
        }


@dataclass(frozen=True)
class IndemnityObligationFacts:
    """One directional indemnity promise."""

    obligation_id: str
    indemnifying_party: str
    indemnified_party: str
    triggers: Tuple[TriggerTreatmentFact, ...]
    claim_scope: EstablishedFact[ClaimScope] = field(
        default_factory=lambda: EstablishedFact.unknown("claim scope not evaluated"),
    )
    monetary: EstablishedFact[MonetaryTreatmentFact] = field(
        default_factory=lambda: EstablishedFact.unknown("monetary treatment not evaluated"),
    )
    procedure_id: Optional[str] = None
    role_bindings: Tuple[RoleBinding, ...] = ()
    evidence: Optional[EvidenceSpan] = None
    section_label: Optional[str] = None

    def trigger_coverage(self, trigger: str) -> TriggerCoverage:
        for t in self.triggers:
            if t.trigger == trigger:
                return t.coverage
        return TriggerCoverage.NOT_ADDRESSED

    def covered_triggers(self) -> List[str]:
        return [t.trigger for t in self.triggers if t.coverage is TriggerCoverage.COVERED]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "indemnifying_party": self.indemnifying_party,
            "indemnified_party": self.indemnified_party,
            "triggers": [t.as_dict() for t in self.triggers],
            "claim_scope": self.claim_scope.as_dict(value_to_dict=lambda v: v.value),
            "monetary": self.monetary.as_dict(value_to_dict=lambda v: v.as_dict()),
            "procedure_id": self.procedure_id,
            "role_bindings": [b.as_dict() for b in self.role_bindings],
            "evidence": self.evidence.as_dict() if self.evidence else None,
            "section_label": self.section_label,
            "covered_triggers": self.covered_triggers(),
        }


@dataclass(frozen=True)
class ContractIndemnificationFacts:
    """Document-level indemnification: obligations + shared procedures."""

    clause_presence: Presence
    obligations: Tuple[IndemnityObligationFacts, ...] = ()
    procedures: Tuple[SharedProcedure, ...] = ()
    absence_state: str = "CONFIRMED_ABSENT"
    unresolved_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.clause_presence is Presence.PRESENT and not self.obligations:
            # PRESENT with empty obligations is allowed only as
            # PRESENT_BUT_UNRESOLVED — callers must set absence_state and
            # unresolved_reason accordingly.
            if self.absence_state not in ("PRESENT_BUT_UNRESOLVED", "RECOGNITION_UNCERTAIN"):
                raise ValueError(
                    "PRESENT ContractIndemnificationFacts with no obligations requires "
                    "absence_state PRESENT_BUT_UNRESOLVED or RECOGNITION_UNCERTAIN"
                )
        proc_ids = {p.procedure_id for p in self.procedures}
        for obl in self.obligations:
            if obl.procedure_id is not None and obl.procedure_id not in proc_ids:
                raise ValueError(
                    f"obligation {obl.obligation_id} references unknown procedure_id "
                    f"{obl.procedure_id!r}"
                )

    def procedure_for(self, procedure_id: str) -> Optional[SharedProcedure]:
        for p in self.procedures:
            if p.procedure_id == procedure_id:
                return p
        return None

    def obligations_where_indemnifying(self, party_name: str) -> List[IndemnityObligationFacts]:
        key = party_name.lower()
        return [o for o in self.obligations if o.indemnifying_party.lower() == key]

    def obligations_where_indemnified(self, party_name: str) -> List[IndemnityObligationFacts]:
        key = party_name.lower()
        return [o for o in self.obligations if o.indemnified_party.lower() == key]

    def category_treatments_for_interactions(
        self, *, from_exposure_of: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Exposure-side trigger coverages in interaction_rules list shape.

        If from_exposure_of is set, only obligations where that party is the
        indemnifying party are included (directional). If None, all covered
        triggers across obligations are unioned — callers should prefer the
        directional form.
        """
        selected = self.obligations
        if from_exposure_of is not None:
            selected = tuple(self.obligations_where_indemnifying(from_exposure_of))
        out: Dict[str, Dict[str, Any]] = {}
        for obl in selected:
            for t in obl.triggers:
                if t.coverage is TriggerCoverage.COVERED:
                    out[t.trigger] = {
                        "category": t.trigger,
                        "treatment": "covered",
                        "established": True,
                        "raw_excerpt": t.evidence.excerpt if t.evidence else "",
                    }
        return list(out.values())

    def as_dict(self) -> Dict[str, Any]:
        return {
            "clause_presence": self.clause_presence.value,
            "obligations": [o.as_dict() for o in self.obligations],
            "procedures": [p.as_dict() for p in self.procedures],
            "absence_state": self.absence_state,
            "unresolved_reason": self.unresolved_reason,
        }
