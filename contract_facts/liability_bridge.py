"""Bridge legacy liability extraction → canonical ContractLiabilityFacts → LoL v2.

Phase 2: fee-period CapValues from liability_policy_engine become first-class
FeeRelativeCap operands. Consumers must not re-parse truncated excerpts once
a component is established.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from contract_facts.evidence import EvidenceSpan
from contract_facts.fact import EstablishedFact
from contract_facts.liability import (
    CategoryTreatmentFact,
    CategoryTreatmentKind,
    ContractLiabilityFacts,
    LiabilityProvisionFacts,
    MutualityStatus,
)
from contract_facts.presence import Presence
from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import (
    AnnualFeeMultipleCap,
    FeeRelativeCap,
    FixedAmountCap,
    UnlimitedCap,
)
from policy_grammar.fee_relative import FeeBasis, FeeScope
from policy_grammar.money import MoneyAmount


def _infer_fee_basis(text: str) -> FeeBasis:
    import re

    lowered = (text or "").lower()
    if re.search(r"paid\s+or\s+payable", lowered):
        return FeeBasis.FEES_PAID_OR_PAYABLE
    if re.search(r"fees?\s+payable", lowered):
        return FeeBasis.FEES_PAYABLE
    if re.search(r"fees?\s+paid", lowered):
        return FeeBasis.FEES_PAID
    return FeeBasis.CONTRACT_FEES


def _infer_fee_scope(text: str) -> FeeScope:
    lowered = (text or "").lower()
    if "order form" in lowered:
        return FeeScope.ORDER_FORM
    return FeeScope.AGREEMENT


def legacy_cap_value_to_operand(comp: Any) -> Optional[Any]:
    """Map liability_policy_engine.CapValue → policy_grammar CapOperand."""
    kind = getattr(comp, "kind", None)
    excerpt = getattr(comp, "raw_excerpt", "") or ""
    if kind == "unlimited":
        return UnlimitedCap()
    if kind == "fee_multiplier":
        return AnnualFeeMultipleCap(multiple=float(comp.multiplier))
    if kind == "fixed_amount":
        return FixedAmountCap(money=MoneyAmount.from_number(str(comp.fixed_amount)))
    if kind == "fee_period":
        months = getattr(comp, "months", None)
        if months is None:
            return None
        return FeeRelativeCap(
            months=float(months),
            basis=_infer_fee_basis(excerpt),
            scope=_infer_fee_scope(excerpt),
        )
    return None


def legacy_cap_expression_to_policy(expr: Any) -> Optional[CapExpression]:
    """Map legacy CapExpression components to policy_grammar CapExpression."""
    if expr is None or getattr(expr, "structure", None) == "unresolved":
        return None
    operands = []
    for comp in getattr(expr, "components", []) or []:
        op = legacy_cap_value_to_operand(comp)
        if op is None:
            return None
        operands.append(op)
    if not operands:
        return None
    structure = expr.structure
    if structure == "simple":
        return CapExpression(operator=CapOperator.SIMPLE, operands=operands[:1])
    if structure == "greater_of":
        return CapExpression(operator=CapOperator.GREATER_OF, operands=operands)
    if structure == "lesser_of":
        return CapExpression(operator=CapOperator.LESSER_OF, operands=operands)
    # per_claim_and_aggregate and other structures: take first comparable operand
    return CapExpression(operator=CapOperator.SIMPLE, operands=operands[:1])


def _treatment_kind(raw: str) -> CategoryTreatmentKind:
    mapping = {
        "uncapped": CategoryTreatmentKind.UNCAPPED,
        "super_cap": CategoryTreatmentKind.SUPER_CAP,
        "within_general_cap": CategoryTreatmentKind.WITHIN_GENERAL_CAP,
        "not_addressed": CategoryTreatmentKind.NOT_ADDRESSED,
        "unresolved": CategoryTreatmentKind.UNKNOWN,
    }
    return mapping.get(raw, CategoryTreatmentKind.UNKNOWN)


def _mutuality_from_provision(provision: Any) -> EstablishedFact[MutualityStatus]:
    positions = getattr(provision, "party_positions", None) or {}
    if len(positions) >= 2:
        return EstablishedFact.present(MutualityStatus.ONE_SIDED)
    # Heuristic: "either party" / mutual phrasing in excerpt → mutual when single pool
    excerpt = (getattr(provision, "raw_excerpt", "") or "").lower()
    window_hint = excerpt
    if "either party" in window_hint or "each party" in window_hint:
        return EstablishedFact.present(MutualityStatus.MUTUAL)
    return EstablishedFact.unknown("mutuality not fully established from legacy extraction")


def canonical_liability_from_legacy(facts: Any) -> ContractLiabilityFacts:
    """Build ContractLiabilityFacts from liability_policy_engine.LiabilityFacts."""
    if facts is None or not getattr(facts, "clause_found", False):
        presence = Presence.UNKNOWN if facts is not None and getattr(facts, "absence_state", "") == "RECOGNITION_UNCERTAIN" else Presence.ABSENT
        return ContractLiabilityFacts(
            clause_presence=presence,
            absence_state=getattr(facts, "absence_state", "CONFIRMED_ABSENT") if facts else "CONFIRMED_ABSENT",
            unresolved_reason=getattr(facts, "semantic_discovery_error", None) if facts else None,
        )

    provisions: List[LiabilityProvisionFacts] = []
    for prov in facts.provisions:
        evidence = EvidenceSpan(
            excerpt=prov.raw_excerpt or "",
            start_index=prov.start_index,
            end_index=prov.end_index,
            section_label=prov.section_label,
        )
        policy_expr = legacy_cap_expression_to_policy(prov.general_cap_expression)
        if policy_expr is not None:
            general_cap: EstablishedFact[CapExpression] = EstablishedFact.present(
                policy_expr, evidence,
            )
        elif getattr(prov.general_cap_expression, "structure", None) == "unresolved":
            general_cap = EstablishedFact.unknown(
                prov.general_cap_expression.unresolved_reason or "cap unresolved",
                evidence,
            )
        else:
            general_cap = EstablishedFact.unknown(
                "no comparable general cap components extracted",
                evidence,
            )

        treatments = []
        for cat, t in (prov.category_treatments or {}).items():
            kind = _treatment_kind(t.treatment)
            cat_cap = None
            if t.cap is not None:
                operand = legacy_cap_value_to_operand(t.cap)
                if operand is not None:
                    cat_cap = CapExpression(operator=CapOperator.SIMPLE, operands=[operand])
            if kind is CategoryTreatmentKind.SUPER_CAP and cat_cap is None:
                kind = CategoryTreatmentKind.UNKNOWN
            treatments.append(
                CategoryTreatmentFact(
                    category=cat,
                    treatment=kind,
                    category_cap=cat_cap,
                    evidence=EvidenceSpan(excerpt=t.raw_excerpt or "") if t.raw_excerpt else None,
                    unresolved_reason=(
                        "ambiguous carve-out language" if kind is CategoryTreatmentKind.UNKNOWN else None
                    ),
                )
            )

        consequential: EstablishedFact[bool]
        if not prov.consequential_damages_established:
            consequential = EstablishedFact.unknown("consequential damages language ambiguous", evidence)
        elif prov.consequential_damages_excluded is True:
            consequential = EstablishedFact.present(True, evidence)
        elif prov.consequential_damages_excluded is False:
            consequential = EstablishedFact.present(False, evidence)
        else:
            consequential = EstablishedFact.absent(evidence)

        provisions.append(
            LiabilityProvisionFacts(
                provision_id=f"prov-{prov.index}",
                general_cap=general_cap,
                mutuality=_mutuality_from_provision(prov),
                consequential_damages_excluded=consequential,
                category_treatments=tuple(treatments),
                evidence=evidence,
                section_label=prov.section_label,
                is_amendment=bool(prov.is_amendment),
            )
        )

    controlling_id = None
    controlling = getattr(facts, "controlling_provision", None)
    if controlling is not None:
        controlling_id = f"prov-{controlling.index}"

    return ContractLiabilityFacts(
        clause_presence=Presence.PRESENT,
        provisions=tuple(provisions),
        controlling_provision_id=controlling_id,
        reconciliation=facts.reconciliation or "none",
        reconciliation_explanation=getattr(facts, "reconciliation_explanation", None),
        absence_state=getattr(facts, "absence_state", "CONFIRMED_ABSENT"),
    )


def contract_cap_from_canonical(liability: ContractLiabilityFacts):
    """Build liability_evaluator_v2.ContractCapFacts from canonical liability facts."""
    from liability_evaluator_v2 import ContractCapFacts

    if liability.clause_presence is not Presence.PRESENT:
        return None
    controlling = liability.controlling
    if controlling is None:
        return None
    if not controlling.general_cap.is_known or controlling.general_cap.value is None:
        return None
    expr = controlling.general_cap.value
    fee_months = controlling.fee_period_months()
    unlimited = any(isinstance(o, UnlimitedCap) for o in expr.operands)
    return ContractCapFacts(
        expression=expr,
        fee_period_months=fee_months,
        is_unlimited=unlimited,
    )


def category_treatments_for_decision(liability: ContractLiabilityFacts) -> List[Dict[str, Any]]:
    """Interaction/decision list shape from canonical facts."""
    return liability.category_treatments_for_interactions()
