"""Bridge legacy indemnification extraction → canonical contract facts.

Phase 3: directional obligations, shared §5.3 procedure attachment,
contextual role bindings, and §6.3 liability linkage as CrossClauseGraph
(not MonetaryKind.CROSS_REFERENCE).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from contract_facts.cross_clause import (
    ClauseFamily,
    CrossClauseGraph,
    CrossClauseKind,
    CrossClauseRelationship,
)
from contract_facts.evidence import EvidenceSpan
from contract_facts.fact import EstablishedFact
from contract_facts.indemnification import (
    ClaimScope,
    ContractIndemnificationFacts,
    IndemnityObligationFacts,
    MonetaryKind,
    MonetaryTreatmentFact,
    TriggerCoverage,
    TriggerTreatmentFact,
)
from contract_facts.presence import Presence
from contract_facts.procedure import DefenseControl, DefenseControlHolder, SharedProcedure
from contract_facts.roles import (
    ContextualRoleKind,
    DocumentParty,
    DocumentRoleModel,
    RoleBinding,
)


_SCOPE_MAP = {
    "third_party_only": ClaimScope.THIRD_PARTY_ONLY,
    "includes_first_party": ClaimScope.INCLUDES_FIRST_PARTY,
    "not_addressed": ClaimScope.NOT_ADDRESSED,
    "unresolved": ClaimScope.UNKNOWN,
}

_TRIGGER_COVERAGE_MAP = {
    "covered": TriggerCoverage.COVERED,
    "excluded": TriggerCoverage.EXCLUDED,
    "not_addressed": TriggerCoverage.NOT_ADDRESSED,
    "unresolved": TriggerCoverage.UNKNOWN,
}

_DEFENSE_HOLDER_MAP = {
    "indemnifying_party": DefenseControlHolder.INDEMNIFYING_PARTY,
    "indemnified_party": DefenseControlHolder.INDEMNIFIED_PARTY,
    "shared": DefenseControlHolder.SHARED,
}


def _evidence(excerpt: str = "", start: Optional[int] = None, end: Optional[int] = None,
              section_label: Optional[str] = None) -> Optional[EvidenceSpan]:
    if not excerpt and start is None:
        return None
    return EvidenceSpan(
        excerpt=excerpt or "",
        start_index=start,
        end_index=end,
        section_label=section_label,
    )


def _monetary_from_legacy(m: Any) -> EstablishedFact[MonetaryTreatmentFact]:
    kind_raw = getattr(m, "kind", "not_stated") or "not_stated"
    evidence = _evidence(getattr(m, "raw_excerpt", "") or "")
    if kind_raw == "not_stated":
        return EstablishedFact.present(MonetaryTreatmentFact(kind=MonetaryKind.NOT_STATED), evidence)
    if kind_raw == "unlimited":
        return EstablishedFact.present(MonetaryTreatmentFact(kind=MonetaryKind.UNLIMITED, evidence=evidence), evidence)
    if kind_raw == "multiplier":
        return EstablishedFact.present(
            MonetaryTreatmentFact(
                kind=MonetaryKind.MULTIPLIER,
                multiplier=getattr(m, "multiplier", None),
                evidence=evidence,
            ),
            evidence,
        )
    if kind_raw == "fixed":
        return EstablishedFact.present(
            MonetaryTreatmentFact(
                kind=MonetaryKind.FIXED,
                fixed_amount=getattr(m, "fixed_amount", None),
                evidence=evidence,
            ),
            evidence,
        )
    if kind_raw == "duration_fees":
        return EstablishedFact.present(
            MonetaryTreatmentFact(
                kind=MonetaryKind.FEE_PERIOD,
                fee_period_months=getattr(m, "duration_months", None),
                evidence=evidence,
            ),
            evidence,
        )
    if kind_raw == "cross_reference":
        label = getattr(m, "cross_reference_label", None) or "cross-referenced provision"
        return EstablishedFact.present(
            MonetaryTreatmentFact(
                kind=MonetaryKind.CROSS_REFERENCE,
                cross_reference_label=label,
                evidence=evidence,
            ),
            evidence,
        )
    return EstablishedFact.unknown(
        f"monetary treatment kind {kind_raw!r} requires lawyer review",
        evidence,
    )


def _triggers_from_legacy(trigger_treatments: Dict[str, Any]) -> Tuple[TriggerTreatmentFact, ...]:
    out: List[TriggerTreatmentFact] = []
    for trig, tt in (trigger_treatments or {}).items():
        coverage = _TRIGGER_COVERAGE_MAP.get(tt.treatment, TriggerCoverage.UNKNOWN)
        reason = None
        if coverage is TriggerCoverage.UNKNOWN:
            reason = "ambiguous carve-out language"
        out.append(
            TriggerTreatmentFact(
                trigger=trig,
                coverage=coverage,
                evidence=_evidence(getattr(tt, "raw_excerpt", "") or ""),
                unresolved_reason=reason,
            )
        )
    return tuple(out)


def _role_bindings_for_obligation(ob: Any) -> Tuple[RoleBinding, ...]:
    evidence = _evidence(ob.raw_excerpt, ob.start_index, ob.end_index, ob.section_label)
    bindings: List[RoleBinding] = []
    if ob.indemnifying_role:
        bindings.append(
            RoleBinding.bound(ContextualRoleKind.INDEMNIFYING_PARTY, ob.indemnifying_role, evidence)
        )
    else:
        bindings.append(
            RoleBinding.unknown(ContextualRoleKind.INDEMNIFYING_PARTY, "indemnifying role not captured", evidence)
        )
    if ob.indemnified_role:
        bindings.append(
            RoleBinding.bound(ContextualRoleKind.INDEMNIFIED_PARTY, ob.indemnified_role, evidence)
        )
    else:
        bindings.append(
            RoleBinding.unknown(ContextualRoleKind.INDEMNIFIED_PARTY, "indemnified role not captured", evidence)
        )
    return tuple(bindings)


def _procedure_from_legacy(proc: Any) -> SharedProcedure:
    evidence = _evidence(proc.raw_excerpt, proc.start_index, proc.end_index, proc.section_label)
    holder = _DEFENSE_HOLDER_MAP.get(proc.defense_control)
    if holder is not None:
        defense: EstablishedFact[DefenseControl] = EstablishedFact.present(
            DefenseControl(holder=holder), evidence,
        )
    elif proc.defense_control in ("not_addressed", None):
        defense = EstablishedFact.absent(evidence)
    else:
        defense = EstablishedFact.unknown(
            f"defense control {proc.defense_control!r} could not be normalized",
            evidence,
        )

    def _bool_fact(value: Optional[bool], missing_reason: str) -> EstablishedFact[bool]:
        if value is True:
            return EstablishedFact.present(True, evidence)
        if value is False:
            return EstablishedFact.present(False, evidence)
        return EstablishedFact.unknown(missing_reason, evidence)

    return SharedProcedure(
        procedure_id=proc.procedure_id,
        defense_control=defense,
        prompt_notice_required=_bool_fact(proc.notice_required, "prompt notice not evaluated"),
        cooperation_required=_bool_fact(proc.cooperation_required, "cooperation not evaluated"),
        evidence=evidence,
        section_label=proc.section_label,
    )


def _document_roles_from_obligations(obligations: List[Any]) -> DocumentRoleModel:
    names: Dict[str, DocumentParty] = {}
    for ob in obligations:
        for role in (ob.indemnifying_role, ob.indemnified_role):
            if not role:
                continue
            key = role.lower()
            if key not in names:
                names[key] = DocumentParty(name=role)
    mutuality: EstablishedFact[str]
    if len(obligations) >= 2:
        mutuality = EstablishedFact.present("directional_reciprocal")
    elif obligations and getattr(obligations[0], "is_mutual_reciprocal", False):
        mutuality = EstablishedFact.present("mutual_reciprocal")
    else:
        mutuality = EstablishedFact.unknown("mutuality not evaluated")
    return DocumentRoleModel(parties=tuple(names.values()), mutuality=mutuality)


def _cross_clause_from_legacy(facts: Any) -> CrossClauseGraph:
    relationships: List[CrossClauseRelationship] = []
    for i, link in enumerate(getattr(facts, "liability_applies_links", None) or []):
        relationships.append(
            CrossClauseRelationship(
                relationship_id=f"xlink-liab-indem-{i}",
                kind=CrossClauseKind.LIABILITY_APPLIES_TO_INDEMNIFICATION,
                source_family=ClauseFamily.LIMITATION_OF_LIABILITY,
                target_family=ClauseFamily.INDEMNIFICATION,
                presence=Presence.PRESENT,
                source_section_label=link.source_section_label,
                target_section_label=link.target_section_label,
                evidence=_evidence(link.raw_excerpt, link.start_index, link.end_index),
            )
        )
    return CrossClauseGraph(relationships=tuple(relationships))


def canonical_indemnification_from_legacy(facts: Any) -> ContractIndemnificationFacts:
    """Build ContractIndemnificationFacts from indemnification_policy_engine output."""
    if facts is None or not getattr(facts, "clause_found", False):
        return ContractIndemnificationFacts(
            clause_presence=Presence.ABSENT,
            absence_state="CONFIRMED_ABSENT",
        )

    obligations_legacy = list(getattr(facts, "obligations", None) or [])
    if not obligations_legacy:
        return ContractIndemnificationFacts(
            clause_presence=Presence.PRESENT,
            obligations=(),
            procedures=(),
            absence_state=getattr(facts, "absence_state", "PRESENT_BUT_UNRESOLVED"),
            unresolved_reason=getattr(facts, "semantic_discovery_error", None)
            or "indemnification referenced but no directional obligation parsed",
        )

    procedures = tuple(
        _procedure_from_legacy(p) for p in (getattr(facts, "shared_procedures", None) or [])
    )
    proc_ids = {p.procedure_id for p in procedures}

    canon_obligations: List[IndemnityObligationFacts] = []
    for i, ob in enumerate(obligations_legacy):
        scope_raw = getattr(ob, "scope", "not_addressed")
        scope_enum = _SCOPE_MAP.get(scope_raw, ClaimScope.UNKNOWN)
        if scope_enum is ClaimScope.UNKNOWN:
            claim_scope: EstablishedFact[ClaimScope] = EstablishedFact.unknown(
                "claim scope ambiguous",
                _evidence(ob.raw_excerpt, ob.start_index, ob.end_index),
            )
        else:
            claim_scope = EstablishedFact.present(
                scope_enum,
                _evidence(ob.raw_excerpt, ob.start_index, ob.end_index),
            )

        procedure_id = getattr(ob, "procedure_id", None)
        if procedure_id is not None and procedure_id not in proc_ids:
            procedure_id = None

        canon_obligations.append(
            IndemnityObligationFacts(
                obligation_id=f"ind-{ob.section_label or i}",
                indemnifying_party=ob.indemnifying_role,
                indemnified_party=ob.indemnified_role,
                triggers=_triggers_from_legacy(ob.trigger_treatments),
                claim_scope=claim_scope,
                monetary=_monetary_from_legacy(ob.monetary),
                procedure_id=procedure_id,
                role_bindings=_role_bindings_for_obligation(ob),
                evidence=_evidence(ob.raw_excerpt, ob.start_index, ob.end_index, ob.section_label),
                section_label=ob.section_label,
            )
        )

    return ContractIndemnificationFacts(
        clause_presence=Presence.PRESENT,
        obligations=tuple(canon_obligations),
        procedures=procedures,
        absence_state=getattr(facts, "absence_state", "PRESENT_AND_VERIFIED"),
    )


def assemble_indemnification_family(facts: Any) -> Dict[str, Any]:
    """Return canonical indemnity + roles + cross-clause graph for one extraction."""
    indem = canonical_indemnification_from_legacy(facts)
    roles = _document_roles_from_obligations(list(getattr(facts, "obligations", None) or []))
    cross = _cross_clause_from_legacy(facts)
    return {
        "indemnification": indem,
        "roles": roles,
        "cross_clause": cross,
    }
