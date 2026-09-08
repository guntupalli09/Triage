from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from policy_grammar.bands import BandOutcome, PolicyBand, PolicyBandKind
from policy_grammar.cap_expression import CapExpression
from policy_grammar.carve_outs import CarveOutCategory, CarveOutSpec, CarveOutTreatment
from policy_grammar.conditions import ConditionField, ConditionGroup, ConditionOperator, PolicyCondition
from policy_grammar.escalation import ApproverRole, EscalationRule, EscalationSeverity
from policy_grammar.money import MoneyAmount
from policy_grammar.roles import NormalizedRole, TransactionOrientation
from policy_grammar.serialization import cap_expression_from_dict, cap_expression_to_dict, money_from_dict, money_to_dict
from policy_grammar.super_cap import SuperCapSpec
from policy_grammar.cap_operands import ReferenceCap
from policy_grammar.validation import ValidationError, validate_cap_expression


LIABILITY_POLICY_SCHEMA_VERSION = 2


@dataclass
class ConsequentialDamagesPolicy:
    require_exclusion: bool = False
    required_carveouts: List[str] = field(default_factory=list)


@dataclass
class LiabilityPolicyV2:
    schema_version: int = LIABILITY_POLICY_SCHEMA_VERSION
    orientation: TransactionOrientation = TransactionOrientation.MUTUAL
    bands: List[PolicyBand] = field(default_factory=list)
    carve_outs: List[CarveOutSpec] = field(default_factory=list)
    super_caps: List[SuperCapSpec] = field(default_factory=list)
    escalation_rules: List[EscalationRule] = field(default_factory=list)
    prohibit_unlimited: bool = True
    consequential_damages: ConsequentialDamagesPolicy = field(default_factory=ConsequentialDamagesPolicy)
    fallback_language: Optional[str] = None

    def validate(self) -> List[ValidationError]:
        errors: List[ValidationError] = []
        if self.schema_version != LIABILITY_POLICY_SCHEMA_VERSION:
            errors.append(ValidationError("schema_version", f"expected {LIABILITY_POLICY_SCHEMA_VERSION}"))
        for i, band in enumerate(self.bands):
            errors.extend(validate_cap_expression(band.expression, f"bands[{i}].expression"))
            for j, cond in enumerate(band.conditions):
                from policy_grammar.conditions import validate_condition
                for msg in validate_condition(cond):
                    errors.append(ValidationError(f"bands[{i}].conditions[{j}]", msg))
        for i, sc in enumerate(self.super_caps):
            errors.extend(validate_cap_expression(sc.expression, f"super_caps[{i}].expression"))
            refs = [op for op in sc.expression.operands if isinstance(op, ReferenceCap)]
            if sc.expression.operator.value == "SIMPLE" and len(refs) != 1:
                errors.append(ValidationError(f"super_caps[{i}]", "super-cap requires exactly one ReferenceCap operand"))
            for ref in refs:
                if ref.multiplier <= 0:
                    errors.append(ValidationError(f"super_caps[{i}]", "super-cap multiplier must be positive"))
        from liability_policy_v2_consistency import validate_policy_consistency
        errors.extend(validate_policy_consistency(self))
        return errors


def _condition_to_dict(c: PolicyCondition) -> Dict[str, Any]:
    val: Any
    if isinstance(c.value, MoneyAmount):
        val = money_to_dict(c.value)
    elif isinstance(c.value, CapExpression):
        val = cap_expression_to_dict(c.value)
    elif isinstance(c.value, NormalizedRole):
        val = c.value.value
    else:
        val = c.value
    return {"field": c.field.value, "operator": c.operator.value, "value": val}


def _condition_from_dict(d: Dict[str, Any]) -> PolicyCondition:
    field = ConditionField(d["field"])
    op = ConditionOperator(d["operator"])
    raw = d["value"]
    if field in (ConditionField.ANNUAL_CONTRACT_VALUE, ConditionField.CONTRACT_VALUE):
        value = money_from_dict(raw)
    elif field == ConditionField.LIABILITY_CAP:
        value = cap_expression_from_dict(raw)
    elif field == ConditionField.COUNTERPARTY_ROLE:
        value = NormalizedRole(raw) if isinstance(raw, str) else raw
    elif field == ConditionField.FEE_PERIOD_MONTHS:
        value = float(raw)
    else:
        value = raw
    return PolicyCondition(field=field, operator=op, value=value)


def liability_policy_v2_to_dict(policy: LiabilityPolicyV2) -> Dict[str, Any]:
    return {
        "schema_version": policy.schema_version,
        "orientation": policy.orientation.value,
        "bands": [
            {
                "kind": b.kind.value,
                "expression": cap_expression_to_dict(b.expression),
                "conditions": [_condition_to_dict(c) for c in b.conditions],
                "outcome_if_breached": b.outcome_if_breached.value if b.outcome_if_breached else None,
            }
            for b in policy.bands
        ],
        "carve_outs": [
            {
                "category": c.category.value,
                "treatment": c.treatment.value,
                "applicable_party": c.applicable_party.value if c.applicable_party else None,
                "custom_label": c.custom_label,
                "expression": cap_expression_to_dict(c.expression) if c.expression else None,
            }
            for c in policy.carve_outs
        ],
        "super_caps": [
            {
                "applies_to": [a.value for a in sc.applies_to],
                "expression": cap_expression_to_dict(sc.expression),
            }
            for sc in policy.super_caps
        ],
        "escalation_rules": [
            {
                "when": _group_to_dict(e.when),
                "approver": e.approver.value,
                "custom_approver_label": e.custom_approver_label,
                "severity": e.severity.value,
                "reason_template": e.reason_template,
            }
            for e in policy.escalation_rules
        ],
        "prohibit_unlimited": policy.prohibit_unlimited,
        "consequential_damages": {
            "require_exclusion": policy.consequential_damages.require_exclusion,
            "required_carveouts": list(policy.consequential_damages.required_carveouts),
        },
        "fallback_language": policy.fallback_language,
    }


def _group_to_dict(g: ConditionGroup) -> Dict[str, Any]:
    items = []
    for item in g.conditions:
        if isinstance(item, ConditionGroup):
            items.append(_group_to_dict(item))
        else:
            items.append(_condition_to_dict(item))
    return {"operator": g.operator, "conditions": items}


def _group_from_dict(d: Dict[str, Any]) -> ConditionGroup:
    conditions = []
    for item in d["conditions"]:
        if "field" in item:
            conditions.append(_condition_from_dict(item))
        else:
            conditions.append(_group_from_dict(item))
    return ConditionGroup(operator=d["operator"], conditions=conditions)


def liability_policy_v2_from_dict(d: Dict[str, Any]) -> LiabilityPolicyV2:
    bands = []
    for b in d.get("bands", []):
        bands.append(PolicyBand(
            kind=PolicyBandKind(b["kind"]),
            expression=cap_expression_from_dict(b["expression"]),
            conditions=[_condition_from_dict(c) for c in b.get("conditions", [])],
            outcome_if_breached=BandOutcome(b["outcome_if_breached"]) if b.get("outcome_if_breached") else None,
        ))
    carve_outs = []
    for c in d.get("carve_outs", []):
        carve_outs.append(CarveOutSpec(
            category=CarveOutCategory(c["category"]),
            treatment=CarveOutTreatment(c["treatment"]),
            applicable_party=NormalizedRole(c["applicable_party"]) if c.get("applicable_party") else None,
            custom_label=c.get("custom_label"),
            expression=cap_expression_from_dict(c["expression"]) if c.get("expression") else None,
        ))
    super_caps = []
    for sc in d.get("super_caps", []):
        super_caps.append(SuperCapSpec(
            applies_to=[CarveOutCategory(a) for a in sc["applies_to"]],
            expression=cap_expression_from_dict(sc["expression"]),
        ))
    escalation = []
    for e in d.get("escalation_rules", []):
        escalation.append(EscalationRule(
            when=_group_from_dict(e["when"]),
            approver=ApproverRole(e["approver"]),
            custom_approver_label=e.get("custom_approver_label"),
            severity=EscalationSeverity(e.get("severity", EscalationSeverity.REQUIRED.value)),
            reason_template=e.get("reason_template"),
        ))
    cd = d.get("consequential_damages", {})
    return LiabilityPolicyV2(
        schema_version=int(d.get("schema_version", LIABILITY_POLICY_SCHEMA_VERSION)),
        orientation=TransactionOrientation(d.get("orientation", TransactionOrientation.MUTUAL.value)),
        bands=bands,
        carve_outs=carve_outs,
        super_caps=super_caps,
        escalation_rules=escalation,
        prohibit_unlimited=bool(d.get("prohibit_unlimited", True)),
        consequential_damages=ConsequentialDamagesPolicy(
            require_exclusion=bool(cd.get("require_exclusion", False)),
            required_carveouts=list(cd.get("required_carveouts", [])),
        ),
        fallback_language=d.get("fallback_language"),
    )
