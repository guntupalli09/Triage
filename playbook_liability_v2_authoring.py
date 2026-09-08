"""Lawyer-facing v2 LoL workbench — form ↔ rules_v2_json (never expose raw JSON)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from liability_policy_v2 import (
    LIABILITY_POLICY_SCHEMA_VERSION,
    LiabilityPolicyV2,
    liability_policy_v2_from_dict,
    liability_policy_v2_to_dict,
)
from policy_grammar.bands import BandOutcome, PolicyBandKind
from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import (
    AnnualFeeMultipleCap,
    CapOperand,
    FeeRelativeCap,
    FixedAmountCap,
    ReferenceCap,
    ReferenceTarget,
)
from policy_grammar.carve_outs import CarveOutCategory, CarveOutSpec, CarveOutTreatment
from policy_grammar.conditions import ConditionField, ConditionGroup, ConditionOperator, PolicyCondition
from policy_grammar.escalation import ApproverRole, EscalationRule, EscalationSeverity
from policy_grammar.fee_relative import FeeBasis, FeeScope
from policy_grammar.money import MoneyAmount
from policy_grammar.roles import NormalizedRole, TransactionOrientation


class LiabilityV2FormError(ValueError):
    pass


FEE_BASES = [b.value for b in FeeBasis if b != FeeBasis.UNRESOLVED]
FEE_SCOPES = [s.value for s in FeeScope if s != FeeScope.UNRESOLVED]
CARVEOUT_CATEGORIES = [c.value for c in CarveOutCategory]
CARVEOUT_TREATMENTS = [t.value for t in CarveOutTreatment]
ORIENTATIONS = [o.value for o in TransactionOrientation]
CAP_OPERATORS = ["SIMPLE", "GREATER_OF", "LESSER_OF"]
OPERAND_TYPES = ["fee_period", "annual_fee_multiple", "fixed_amount"]


def is_lol_v2_position(position) -> bool:
    return (
        position is not None
        and position.clause_type == "limitation_of_liability"
        and (getattr(position, "policy_schema_version", 1) or 1) == 2
    )


def _operand_to_view(op: CapOperand) -> Dict[str, Any]:
    if isinstance(op, FeeRelativeCap):
        return {
            "type": "fee_period",
            "months": op.months,
            "basis": op.basis.value,
            "scope": op.scope.value,
        }
    if isinstance(op, AnnualFeeMultipleCap):
        return {"type": "annual_fee_multiple", "multiple": op.multiple}
    if isinstance(op, FixedAmountCap):
        return {
            "type": "fixed_amount",
            "amount": str(op.money.amount),
            "currency": op.money.currency,
        }
    return {"type": "unknown"}


def _expression_to_view(expr: CapExpression) -> Dict[str, Any]:
    ops = [_operand_to_view(o) for o in expr.operands]
    view: Dict[str, Any] = {"operator": expr.operator.value, "operands": ops}
    if expr.operator == CapOperator.SIMPLE and ops:
        view["operand"] = ops[0]
    elif len(ops) >= 2:
        view["operand_a"] = ops[0]
        view["operand_b"] = ops[1]
    return view


def _band_by_kind(policy: LiabilityPolicyV2, kind: PolicyBandKind):
    return next((b for b in policy.bands if b.kind == kind), None)


def v2_edit_view(position) -> Dict[str, Any]:
    """Structured view model for the v2 workbench template."""
    rules = position.rules_v2_json or {}
    try:
        policy = liability_policy_v2_from_dict(rules) if rules else LiabilityPolicyV2()
    except Exception:
        policy = LiabilityPolicyV2()

    preferred = _band_by_kind(policy, PolicyBandKind.PREFERRED)
    fallback = _band_by_kind(policy, PolicyBandKind.ACCEPTABLE_FALLBACK)
    hard_stop = _band_by_kind(policy, PolicyBandKind.MINIMUM_ACCEPTABLE)

    fb_acv_lt = None
    if fallback and fallback.conditions:
        for c in fallback.conditions:
            if c.field == ConditionField.ANNUAL_CONTRACT_VALUE and c.operator == ConditionOperator.LT:
                if isinstance(c.value, MoneyAmount):
                    fb_acv_lt = str(c.value.amount)

    esc = policy.escalation_rules[0] if policy.escalation_rules else None
    esc_acv_gte = None
    esc_cap_lt_months = None
    if esc:
        for item in esc.when.conditions:
            if isinstance(item, PolicyCondition):
                if item.field == ConditionField.ANNUAL_CONTRACT_VALUE and item.operator == ConditionOperator.GTE:
                    if isinstance(item.value, MoneyAmount):
                        esc_acv_gte = str(item.value.amount)
                if item.field == ConditionField.FEE_PERIOD_MONTHS:
                    esc_cap_lt_months = item.value

    sc = policy.super_caps[0] if policy.super_caps else None
    sc_mult = None
    sc_categories: List[str] = []
    if sc:
        sc_categories = [a.value for a in sc.applies_to]
        op = sc.expression.operands[0]
        if isinstance(op, ReferenceCap):
            sc_mult = op.multiplier

    return {
        "orientation": policy.orientation.value,
        "prohibit_unlimited": policy.prohibit_unlimited,
        "preferred": _expression_to_view(preferred.expression) if preferred else {
            "operator": "SIMPLE", "operand": {"type": "fee_period", "months": 12, "basis": "CONTRACT_FEES", "scope": "AGREEMENT"},
        },
        "fallback_enabled": fallback is not None,
        "fallback": _expression_to_view(fallback.expression) if fallback else {
            "operator": "SIMPLE", "operand": {"type": "fee_period", "months": 12, "basis": "CONTRACT_FEES", "scope": "AGREEMENT"},
        },
        "fallback_acv_lt": fb_acv_lt or "250000",
        "hard_stop_enabled": hard_stop is not None,
        "hard_stop": _expression_to_view(hard_stop.expression) if hard_stop else {
            "operator": "SIMPLE", "operand": {"type": "fee_period", "months": 6, "basis": "CONTRACT_FEES", "scope": "AGREEMENT"},
        },
        "super_cap_enabled": sc is not None,
        "super_cap_multiplier": sc_mult or 2.0,
        "super_cap_categories": sc_categories or ["confidentiality", "data_security"],
        "escalation_enabled": esc is not None,
        "escalation_acv_gte": esc_acv_gte or "250000",
        "escalation_cap_lt_months": esc_cap_lt_months or 12,
        "escalation_approver": esc.approver.value if esc else "supervising_partner",
        "carve_outs": [
            {
                "category": c.category.value,
                "treatment": c.treatment.value,
                "applicable_party": c.applicable_party.value if c.applicable_party else "",
            }
            for c in policy.carve_outs
        ],
        "fee_bases": FEE_BASES,
        "fee_scopes": FEE_SCOPES,
        "carveout_categories": CARVEOUT_CATEGORIES,
        "carveout_treatments": CARVEOUT_TREATMENTS,
        "orientations": ORIENTATIONS,
        "cap_operators": CAP_OPERATORS,
        "operand_types": OPERAND_TYPES,
    }


def _get(form, key: str, default: str = "") -> str:
    val = form.get(key)
    if val is None:
        return default
    return str(val).strip()


def _parse_operand(form, prefix: str) -> Dict[str, Any]:
    op_type = _get(form, f"{prefix}_type", "fee_period")
    if op_type == "fee_period":
        months = float(_get(form, f"{prefix}_months", "12") or "12")
        return {
            "type": "fee_period",
            "months": months,
            "basis": _get(form, f"{prefix}_basis", "CONTRACT_FEES"),
            "scope": _get(form, f"{prefix}_scope", "AGREEMENT"),
        }
    if op_type == "annual_fee_multiple":
        return {"type": "annual_fee_multiple", "multiple": float(_get(form, f"{prefix}_multiple", "1") or "1")}
    if op_type == "fixed_amount":
        return {
            "type": "fixed_amount",
            "money": {
                "amount": _get(form, f"{prefix}_amount", "0").replace(",", ""),
                "currency": _get(form, f"{prefix}_currency", "USD") or "USD",
            },
        }
    raise LiabilityV2FormError(f"Unknown operand type: {op_type}")


def _build_expression(form, prefix: str) -> Dict[str, Any]:
    operator = _get(form, f"{prefix}_operator", "SIMPLE").upper()
    if operator == "SIMPLE":
        return {"operator": "SIMPLE", "operands": [_parse_operand(form, f"{prefix}_op1")]}
    return {
        "operator": operator,
        "operands": [
            _parse_operand(form, f"{prefix}_op1"),
            _parse_operand(form, f"{prefix}_op2"),
        ],
    }


def parse_v2_form(form) -> Dict[str, Any]:
    """Parse lawyer-facing form fields into rules_v2_json dict."""
    bands: List[Dict[str, Any]] = []

    bands.append({"kind": "PREFERRED", "expression": _build_expression(form, "v2_preferred"), "conditions": []})

    if _get(form, "v2_fallback_enabled", "yes") in ("yes", "true", "1", "on"):
        fb: Dict[str, Any] = {
            "kind": "ACCEPTABLE_FALLBACK",
            "expression": _build_expression(form, "v2_fallback"),
            "conditions": [],
        }
        acv_lt = _get(form, "v2_fallback_acv_lt")
        if acv_lt:
            fb["conditions"] = [{
                "field": "annual_contract_value",
                "operator": "LT",
                "value": {"amount": acv_lt.replace(",", ""), "currency": "USD"},
            }]
        bands.append(fb)

    if _get(form, "v2_hard_stop_enabled", "yes") in ("yes", "true", "1", "on"):
        bands.append({
            "kind": "MINIMUM_ACCEPTABLE",
            "expression": _build_expression(form, "v2_hard_stop"),
            "outcome_if_breached": "HARD_STOP",
        })

    carve_outs: List[Dict[str, Any]] = []
    selected = form.getlist("v2_carveout_category") if hasattr(form, "getlist") else []
    if not selected and form.get("v2_carveout_category"):
        selected = [form.get("v2_carveout_category")]
    for cat in selected:
        treatment = _get(form, f"v2_carveout_treatment_{cat}", "OUTSIDE_GENERAL_CAP")
        party = _get(form, f"v2_carveout_party_{cat}")
        entry: Dict[str, Any] = {"category": cat, "treatment": treatment}
        if party:
            entry["applicable_party"] = party
        carve_outs.append(entry)

    super_caps: List[Dict[str, Any]] = []
    if _get(form, "v2_super_cap_enabled", "yes") in ("yes", "true", "1", "on"):
        cats = form.getlist("v2_super_cap_category") if hasattr(form, "getlist") else []
        if not cats:
            cats = ["confidentiality", "data_security"]
        mult = float(_get(form, "v2_super_cap_multiplier", "2") or "2")
        super_caps.append({
            "applies_to": cats,
            "expression": {
                "operator": "SIMPLE",
                "operands": [{"type": "reference", "ref": "GENERAL_CAP", "multiplier": mult}],
            },
        })

    escalation_rules: List[Dict[str, Any]] = []
    if _get(form, "v2_escalation_enabled", "yes") in ("yes", "true", "1", "on"):
        acv_gte = _get(form, "v2_escalation_acv_gte", "250000")
        cap_months = float(_get(form, "v2_escalation_cap_lt_months", "12") or "12")
        escalation_rules.append({
            "when": {
                "operator": "AND",
                "conditions": [
                    {
                        "field": "annual_contract_value",
                        "operator": "GTE",
                        "value": {"amount": acv_gte.replace(",", ""), "currency": "USD"},
                    },
                    {
                        "field": "liability_cap",
                        "operator": "LT",
                        "value": {
                            "operator": "SIMPLE",
                            "operands": [{"type": "fee_period", "months": cap_months, "basis": "CONTRACT_FEES", "scope": "AGREEMENT"}],
                        },
                    },
                ],
            },
            "approver": _get(form, "v2_escalation_approver", "supervising_partner"),
            "severity": "REQUIRED",
        })

    orientation = _get(form, "v2_orientation", "buy_side")
    prohibit = _get(form, "v2_prohibit_unlimited", "yes") in ("yes", "true", "1", "on")

    rules = {
        "schema_version": LIABILITY_POLICY_SCHEMA_VERSION,
        "orientation": orientation,
        "bands": bands,
        "carve_outs": carve_outs,
        "super_caps": super_caps,
        "escalation_rules": escalation_rules,
        "prohibit_unlimited": prohibit,
        "consequential_damages": {"require_exclusion": False, "required_carveouts": []},
    }

    policy = liability_policy_v2_from_dict(rules)
    errors = policy.validate()
    if errors:
        raise LiabilityV2FormError("; ".join(f"{e.path}: {e.message}" for e in errors))
    return liability_policy_v2_to_dict(policy)


def apply_liability_v2_update(
    db, position, form, user, *, contract_side: str,
    escalation_approval_authority: Optional[str], fallback_text: Optional[str],
) -> None:
    """Persist v2 rules from form — never writes v1 multiplier fields."""
    import playbook_authoring as pa
    from datetime import datetime

    if position.status == "ACTIVE":
        raise pa.PolicyEnforcementGuardError("Refusing to edit ACTIVE position in place")

    rules = parse_v2_form(form)
    position.policy_schema_version = 2
    position.rules_v2_json = rules
    position.contract_side = contract_side
    position.escalation_approval_authority = escalation_approval_authority
    position.fallback_text = fallback_text
    if position.status in ("NEEDS_REVIEW", "APPROVED"):
        position.status = "DRAFT"

    # Map orientation to contract_side when lawyer picks orientation explicitly
    orientation = rules.get("orientation", "mutual")
    if orientation == "buy_side":
        position.contract_side = "buy_side"
    elif orientation == "sell_side":
        position.contract_side = "sell_side"

    now = datetime.utcnow()
    row = next((f for f in position.fields if f.field_name == "policy_v2_rules" and f.superseded_by_field_id is None), None)
    if row is None:
        from models import PolicyPositionField
        row = PolicyPositionField(policy_position_id=position.id, field_name="policy_v2_rules")
        db.add(row)
    row.value_json = {"schema_version": 2}
    row.source = "MANUAL"
    row.status = "ESTABLISHED"
    row.confirmed_by_user_id = user.id if user else None
    row.confirmed_at = now
