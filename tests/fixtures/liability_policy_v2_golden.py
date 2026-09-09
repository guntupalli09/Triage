"""Golden playbook fixtures — Firms A/B/C/D for regression, not architecture."""

from __future__ import annotations

from liability_policy_v2 import LiabilityPolicyV2, liability_policy_v2_from_dict, liability_policy_v2_to_dict

FIRM_A = {
    "schema_version": 2,
    "orientation": "buy_side",
    "bands": [
        {
            "kind": "PREFERRED",
            "expression": {
                "operator": "GREATER_OF",
                "operands": [
                    {"type": "fee_period", "months": 12, "basis": "FEES_PAID_OR_PAYABLE", "scope": "AGREEMENT"},
                    {"type": "fixed_amount", "money": {"amount": "1000000", "currency": "USD"}},
                ],
            },
            "conditions": [],
        },
        {
            "kind": "ACCEPTABLE_FALLBACK",
            "expression": {
                "operator": "SIMPLE",
                "operands": [{"type": "fee_period", "months": 12, "basis": "CONTRACT_FEES", "scope": "AGREEMENT"}],
            },
            "conditions": [
                {
                    "field": "annual_contract_value",
                    "operator": "LT",
                    "value": {"amount": "250000", "currency": "USD"},
                },
            ],
        },
        {
            "kind": "MINIMUM_ACCEPTABLE",
            "expression": {
                "operator": "SIMPLE",
                "operands": [{"type": "fee_period", "months": 6, "basis": "CONTRACT_FEES", "scope": "AGREEMENT"}],
            },
            "outcome_if_breached": "HARD_STOP",
        },
    ],
    "carve_outs": [
        {"category": "confidentiality", "treatment": "OUTSIDE_GENERAL_CAP", "applicable_party": "vendor"},
        {"category": "intellectual_property", "treatment": "OUTSIDE_GENERAL_CAP", "applicable_party": "vendor"},
        {"category": "indemnification", "treatment": "OUTSIDE_GENERAL_CAP", "applicable_party": "vendor"},
        {"category": "fraud", "treatment": "OUTSIDE_GENERAL_CAP", "applicable_party": "vendor"},
        {"category": "gross_negligence", "treatment": "OUTSIDE_GENERAL_CAP", "applicable_party": "vendor"},
        {"category": "willful_misconduct", "treatment": "OUTSIDE_GENERAL_CAP", "applicable_party": "vendor"},
        {"category": "data_protection", "treatment": "OUTSIDE_GENERAL_CAP", "applicable_party": "vendor"},
    ],
    "super_caps": [
        {
            "applies_to": ["confidentiality", "data_security"],
            "expression": {
                "operator": "SIMPLE",
                "operands": [{"type": "reference", "ref": "GENERAL_CAP", "multiplier": 2.0}],
            },
        },
    ],
    "escalation_rules": [
        {
            "when": {
                "operator": "AND",
                "conditions": [
                    {"field": "annual_contract_value", "operator": "GTE", "value": {"amount": "250000", "currency": "USD"}},
                    {
                        "field": "liability_cap",
                        "operator": "LT",
                        "value": {
                            "operator": "SIMPLE",
                            "operands": [{"type": "fee_period", "months": 12, "basis": "CONTRACT_FEES", "scope": "AGREEMENT"}],
                        },
                    },
                ],
            },
            "approver": "supervising_partner",
            "severity": "REQUIRED",
        },
    ],
    "prohibit_unlimited": True,
    "consequential_damages": {"require_exclusion": False, "required_carveouts": []},
}

FIRM_B = {
    "schema_version": 2,
    "orientation": "buy_side",
    "bands": [
        {
            "kind": "PREFERRED",
            "expression": {
                "operator": "SIMPLE",
                "operands": [{"type": "annual_fee_multiple", "multiple": 2.0}],
            },
        },
        {
            "kind": "MINIMUM_ACCEPTABLE",
            "expression": {
                "operator": "SIMPLE",
                "operands": [{"type": "annual_fee_multiple", "multiple": 1.0}],
            },
            "outcome_if_breached": "HARD_STOP",
        },
    ],
    "carve_outs": [],
    "super_caps": [
        {
            "applies_to": ["privacy"],
            "expression": {
                "operator": "SIMPLE",
                "operands": [{"type": "reference", "ref": "GENERAL_CAP", "multiplier": 3.0}],
            },
        },
    ],
    "escalation_rules": [],
    "prohibit_unlimited": True,
    "consequential_damages": {"require_exclusion": False, "required_carveouts": []},
}

FIRM_C = {
    "schema_version": 2,
    "orientation": "buy_side",
    "bands": [
        {
            "kind": "PREFERRED",
            "expression": {
                "operator": "SIMPLE",
                "operands": [{"type": "fixed_amount", "money": {"amount": "5000000", "currency": "USD"}}],
            },
        },
    ],
    "carve_outs": [
        {"category": "intellectual_property", "treatment": "OUTSIDE_GENERAL_CAP"},
    ],
    "super_caps": [],
    "escalation_rules": [],
    "prohibit_unlimited": True,
    "consequential_damages": {"require_exclusion": False, "required_carveouts": []},
}

FIRM_D = {
    "schema_version": 2,
    "orientation": "sell_side",
    "bands": [
        {
            "kind": "PREFERRED",
            "expression": {
                "operator": "LESSER_OF",
                "operands": [
                    {"type": "fixed_amount", "money": {"amount": "10000000", "currency": "USD"}},
                    {"type": "annual_fee_multiple", "multiple": 3.0},
                ],
            },
        },
        {
            "kind": "ACCEPTABLE_FALLBACK",
            "expression": {
                "operator": "SIMPLE",
                "operands": [{"type": "annual_fee_multiple", "multiple": 2.0}],
            },
            "conditions": [
                {"field": "annual_contract_value", "operator": "LT", "value": {"amount": "1000000", "currency": "USD"}},
            ],
        },
    ],
    "carve_outs": [],
    "super_caps": [],
    "escalation_rules": [
        {
            "when": {
                "operator": "AND",
                "conditions": [
                    {"field": "annual_contract_value", "operator": "GTE", "value": {"amount": "1000000", "currency": "USD"}},
                ],
            },
            "approver": "general_counsel",
            "severity": "REQUIRED",
        },
    ],
    "prohibit_unlimited": True,
    "consequential_damages": {"require_exclusion": False, "required_carveouts": []},
}


def firm_a_policy() -> LiabilityPolicyV2:
    return liability_policy_v2_from_dict(FIRM_A)


def firm_b_policy() -> LiabilityPolicyV2:
    return liability_policy_v2_from_dict(FIRM_B)


def firm_c_policy() -> LiabilityPolicyV2:
    return liability_policy_v2_from_dict(FIRM_C)


def firm_d_policy() -> LiabilityPolicyV2:
    return liability_policy_v2_from_dict(FIRM_D)


def roundtrip(policy: LiabilityPolicyV2) -> LiabilityPolicyV2:
    return liability_policy_v2_from_dict(liability_policy_v2_to_dict(policy))
