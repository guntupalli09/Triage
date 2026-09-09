"""Human-readable v2 LoL review summaries — built from rules_v2_json, never v1 fields."""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from liability_policy_v2 import LiabilityPolicyV2, liability_policy_v2_from_dict
from policy_grammar.bands import PolicyBand, PolicyBandKind
from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import (
    AnnualFeeMultipleCap,
    CapOperand,
    FeeRelativeCap,
    FixedAmountCap,
    ReferenceCap,
    ReferenceTarget,
)
from policy_grammar.carve_outs import CarveOutSpec, CarveOutTreatment
from policy_grammar.conditions import ConditionField, ConditionGroup, ConditionOperator, PolicyCondition
from policy_grammar.escalation import ApproverRole, EscalationRule
from policy_grammar.fee_relative import FeeBasis
from policy_grammar.money import MoneyAmount

_NOT_YET = "Not yet decided"

_BASIS_LABELS = {
    FeeBasis.FEES_PAID_OR_PAYABLE: "fees paid or payable under the agreement",
    FeeBasis.CONTRACT_FEES: "fees under the agreement",
    FeeBasis.FEES_PAID: "fees paid under the agreement",
    FeeBasis.FEES_PAYABLE: "fees payable under the agreement",
}

_TREATMENT_LABELS = {
    CarveOutTreatment.OUTSIDE_GENERAL_CAP: "outside general cap",
    CarveOutTreatment.SUPER_CAP: "super-cap",
    CarveOutTreatment.SEPARATE_FIXED_CAP: "separate fixed cap",
}

_APPROVER_LABELS = {
    ApproverRole.SUPERVISING_PARTNER: "Supervising Partner",
    ApproverRole.PRACTICE_GROUP_LEADER: "Practice Group Leader",
    ApproverRole.GENERAL_COUNSEL: "General Counsel",
    ApproverRole.LEGAL_OPS: "Legal Ops",
    ApproverRole.CLIENT_LEGAL_CONTACT: "Client Legal Contact",
    ApproverRole.CFO: "CFO",
    ApproverRole.CUSTOM: "Custom approver",
}


def _band_by_kind(policy: LiabilityPolicyV2, kind: PolicyBandKind) -> Optional[PolicyBand]:
    return next((b for b in policy.bands if b.kind == kind), None)


def _fmt_money(money: MoneyAmount) -> str:
    try:
        amount = Decimal(str(money.amount))
    except Exception:
        return f"${money.amount} {money.currency}"
    if amount == amount.to_integral_value():
        return f"${amount:,} {money.currency}"
    return f"${amount:,.2f} {money.currency}"


def _fmt_operand(op: CapOperand) -> str:
    if isinstance(op, FeeRelativeCap):
        months = op.months
        months_str = f"{months:g}" if float(months).is_integer() else f"{months:g}"
        basis = _BASIS_LABELS.get(op.basis, op.basis.value.replace("_", " ").lower())
        return f"{months_str} months {basis}"
    if isinstance(op, AnnualFeeMultipleCap):
        mult = op.multiple
        mult_str = f"{mult:g}" if float(mult).is_integer() else f"{mult:g}"
        return f"{mult_str}× annual fees"
    if isinstance(op, FixedAmountCap):
        return _fmt_money(op.money)
    if isinstance(op, ReferenceCap):
        ref_label = "General Cap" if op.ref == ReferenceTarget.GENERAL_CAP else op.ref.value.replace("_", " ")
        mult = op.multiplier
        mult_str = f"{mult:g}" if float(mult).is_integer() else f"{mult:g}"
        return f"{mult_str}× {ref_label}"
    return _NOT_YET


def _fmt_expression(expr: CapExpression) -> str:
    parts = [_fmt_operand(op) for op in expr.operands]
    if not parts:
        return _NOT_YET
    if expr.operator == CapOperator.SIMPLE:
        return parts[0]
    joiner = " OR "
    if expr.operator == CapOperator.GREATER_OF:
        return f"Greater of {joiner.join(parts)}"
    if expr.operator == CapOperator.LESSER_OF:
        return f"Lesser of {joiner.join(parts)}"
    return _NOT_YET


def _fmt_condition_clause(condition: PolicyCondition) -> Optional[str]:
    if condition.field == ConditionField.ANNUAL_CONTRACT_VALUE and isinstance(condition.value, MoneyAmount):
        amt = _fmt_money(condition.value)
        if condition.operator == ConditionOperator.LT:
            return f"ACV < {amt}"
        if condition.operator == ConditionOperator.LTE:
            return f"ACV ≤ {amt}"
        if condition.operator == ConditionOperator.GT:
            return f"ACV > {amt}"
        if condition.operator == ConditionOperator.GTE:
            return f"ACV ≥ {amt}"
    if condition.field == ConditionField.LIABILITY_CAP and isinstance(condition.value, CapExpression):
        cap_text = _fmt_expression(condition.value)
        if condition.operator == ConditionOperator.LT:
            return f"liability cap < {cap_text}"
        if condition.operator == ConditionOperator.LTE:
            return f"liability cap ≤ {cap_text}"
    return None


def _fmt_conditions(conditions: List[PolicyCondition]) -> str:
    parts = [c for c in (_fmt_condition_clause(cond) for cond in conditions) if c]
    if not parts:
        return ""
    return " when " + " AND ".join(parts)


def _fmt_hard_stop(band: PolicyBand) -> str:
    expr = band.expression
    if expr.operator != CapOperator.SIMPLE or len(expr.operands) != 1:
        return _fmt_expression(expr)
    op = expr.operands[0]
    if isinstance(op, FeeRelativeCap):
        months_str = f"{op.months:g}" if float(op.months).is_integer() else f"{op.months:g}"
        basis = _BASIS_LABELS.get(op.basis, op.basis.value.replace("_", " ").lower())
        return f"Below {months_str} months {basis} is prohibited"
    if isinstance(op, AnnualFeeMultipleCap):
        mult_str = f"{op.multiple:g}" if float(op.multiple).is_integer() else f"{op.multiple:g}"
        return f"Below {mult_str}× annual fees is prohibited"
    if isinstance(op, FixedAmountCap):
        return f"Below {_fmt_money(op.money)} is prohibited"
    return _fmt_expression(expr)


def _fmt_carve_outs(carve_outs: List[CarveOutSpec]) -> str:
    if not carve_outs:
        return _NOT_YET
    grouped: dict[tuple[str, str], List[str]] = {}
    for spec in carve_outs:
        treatment = _TREATMENT_LABELS.get(spec.treatment, spec.treatment.value.replace("_", " "))
        party = f" ({spec.applicable_party.value})" if spec.applicable_party else ""
        key = (treatment, party)
        grouped.setdefault(key, []).append(spec.category.value.replace("_", " "))
    parts = []
    for (treatment, party), categories in grouped.items():
        cats = ", ".join(categories)
        parts.append(f"{cats} → {treatment}{party}")
    return "; ".join(parts)


def _fmt_escalation_group(group: ConditionGroup) -> str:
    clauses: List[str] = []
    for item in group.conditions:
        if isinstance(item, PolicyCondition):
            clause = _fmt_condition_clause(item)
            if clause:
                clauses.append(clause)
        elif isinstance(item, ConditionGroup):
            nested = _fmt_escalation_group(item)
            if nested:
                clauses.append(nested)
    return " AND ".join(clauses)


def _fmt_escalation(rule: EscalationRule) -> str:
    approver = _APPROVER_LABELS.get(rule.approver, rule.approver.value.replace("_", " ").title())
    when = _fmt_escalation_group(rule.when)
    if when:
        return f"{approver} when {when}"
    return approver


def v2_lol_review_summary(position) -> List[str]:
    """Lawyer-facing review lines for policy_schema_version == 2 LoL positions."""
    rules = position.rules_v2_json or {}
    try:
        policy = liability_policy_v2_from_dict(rules)
    except Exception:
        return [
            f"Preferred cap → {_NOT_YET}",
            f"Acceptable fallback → {_NOT_YET}",
            f"Hard stop → {_NOT_YET}",
            f"Super-cap → {_NOT_YET}",
            f"Required carve-outs / treatment → {_NOT_YET}",
            f"Unlimited liability → {_NOT_YET}",
            f"Escalation → {_NOT_YET}",
        ]

    lines: List[str] = []

    preferred = _band_by_kind(policy, PolicyBandKind.PREFERRED)
    if preferred:
        lines.append(f"Preferred cap → {_fmt_expression(preferred.expression)}")
    else:
        lines.append(f"Preferred cap → {_NOT_YET}")

    fallback = _band_by_kind(policy, PolicyBandKind.ACCEPTABLE_FALLBACK)
    if fallback:
        text = _fmt_expression(fallback.expression) + _fmt_conditions(fallback.conditions)
        lines.append(f"Acceptable fallback → {text}")
    else:
        lines.append(f"Acceptable fallback → {_NOT_YET}")

    hard_stop = _band_by_kind(policy, PolicyBandKind.MINIMUM_ACCEPTABLE)
    if hard_stop:
        lines.append(f"Hard stop → {_fmt_hard_stop(hard_stop)}")
    else:
        lines.append(f"Hard stop → {_NOT_YET}")

    if policy.super_caps:
        sc_lines = []
        for sc in policy.super_caps:
            if sc.expression.operator == CapOperator.SIMPLE and sc.expression.operands:
                cap_text = _fmt_operand(sc.expression.operands[0])
                cats = " and ".join(c.value.replace("_", " ") for c in sc.applies_to)
                sc_lines.append(f"{cap_text} for {cats}")
            else:
                sc_lines.append(_fmt_expression(sc.expression))
        lines.append(f"Super-cap → {'; '.join(sc_lines)}")
    else:
        lines.append(f"Super-cap → {_NOT_YET}")

    lines.append(f"Required carve-outs / treatment → {_fmt_carve_outs(policy.carve_outs)}")

    if policy.prohibit_unlimited:
        lines.append("Unlimited liability → Prohibited")
    else:
        lines.append("Unlimited liability → Allowed only with escalation")

    if policy.consequential_damages.require_exclusion:
        carveouts = ", ".join(c.replace("_", " ") for c in policy.consequential_damages.required_carveouts)
        if carveouts:
            lines.append(f"Consequential damages exclusion → Required (carve-outs: {carveouts})")
        else:
            lines.append("Consequential damages exclusion → Required")

    if policy.escalation_rules:
        esc_lines = [_fmt_escalation(rule) for rule in policy.escalation_rules]
        lines.append(f"Escalation → {'; '.join(esc_lines)}")
    else:
        lines.append(f"Escalation → {_NOT_YET}")

    return lines
