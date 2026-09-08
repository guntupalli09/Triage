"""Propose LiabilityPolicyV2 rules from verified playbook section text.

Used by AI-assisted import to populate rules_v2_json alongside (not
instead of) v1 field proposals until the workbench v2 editor ships.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from liability_policy_v2 import LIABILITY_POLICY_SCHEMA_VERSION, liability_policy_v2_from_dict, liability_policy_v2_to_dict
from policy_grammar.bands import BandOutcome, PolicyBandKind
from policy_grammar.fee_relative import FeeBasis, FeeScope

_WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}
_WORD_NUM_ALT = "|".join(_WORD_NUMBERS)

_EXPLICIT_FEE_MULTIPLIER_RE = re.compile(
    rf"\b(\d+(?:\.\d+)?|{_WORD_NUM_ALT})\s*(?:\(\d+\))?\s*(?:x|times|×)\s*(?:the\s+)?"
    r"(?:total\s+|aggregate\s+)?(?:annual\s+)?(?:[\w-]+\s+){{0,2}}fees?\b",
    re.I,
)
_DURATION_FEES_RE = re.compile(
    rf"\b(\d+(?:\.\d+)?|{_WORD_NUM_ALT})\s*(?:\(\d+\))?\s*[-\s']*(years?|months?)'?\s*"
    r"(?:of\s+)?(?:worth\s+of\s+)?fees?\b",
    re.I,
)
_TRAILING_MONTHS_FEES_RE = re.compile(
    rf"(?:fees?\s+(?:paid|payable).{{0,100}}?(\d+(?:\.\d+)?|{_WORD_NUM_ALT}|twelve|six)\s*(?:\(\d+\))?\s*months?|"
    rf"(?:twelve|12|\d+)\s*(?:\(\d+\))?\s*months?\s+(?:preceding|prior|before).{{0,40}}?fees?)",
    re.I,
)
_HARD_STOP_CUE_RE = re.compile(
    r"\b(?:do\s+not\s+accept|hard\s+stop|must\s+not|shall\s+not\s+accept|minimum\s+acceptable)\b",
    re.I,
)
_FALLBACK_CUE_RE = re.compile(r"\b(?:acceptable\s+fallback|fallback\s+position|may\s+be\s+accepted)\b", re.I)
_SUPER_CAP_QUOTE_RE = re.compile(r"\bsuper[-\s]?cap\b|\b2\s*(?:x|times|×)\s*(?:the\s+)?general\s+liability\s+cap\b", re.I)
_GREATER_OF_FIXED_RE = re.compile(
    r"\bgreater\s+of\b.{0,200}?\$\s*[\d,]+|\bgreater\s+of\b.{0,200}?\b\d[\d,]*\s*(?:million|m\b)",
    re.I | re.S,
)
_ACV_CONDITION_RE = re.compile(
    r"\b(?:annual contract value|ACV|contract value)\b.{0,40}\$\s*[\d,]+|\b(?:below|above|under|over)\s+\$\s*[\d,]+",
    re.I,
)
_PARTNER_ESCALATION_RE = re.compile(r"\b(?:partner|supervising\s+partner)\s+approval\b", re.I)


def _parse_num_token(token: str) -> Optional[float]:
    try:
        return float(token)
    except ValueError:
        return float(_WORD_NUMBERS[token.lower()]) if token.lower() in _WORD_NUMBERS else None


def _duration_months_in_quote(quote_text: str) -> Optional[float]:
    m = _DURATION_FEES_RE.search(quote_text)
    if m:
        n = _parse_num_token(m.group(1))
        if n is not None:
            unit = m.group(2).lower().rstrip("s")
            return n * 12 if unit == "year" else n
    m2 = _TRAILING_MONTHS_FEES_RE.search(quote_text)
    if m2:
        token = m2.group(1) if m2.lastindex else None
        if token:
            n = _parse_num_token(token)
            if n is not None:
                return n
        if re.search(r"\b(?:twelve|12)\b", quote_text, re.I):
            return 12.0
    return None


def _fee_period_operand(text: str) -> Optional[Dict[str, Any]]:
    months = _duration_months_in_quote(text)
    if months is None:
        return None
    lowered = text.lower()
    if re.search(r"fees?\s+paid\s+or\s+payable", lowered):
        basis = FeeBasis.FEES_PAID_OR_PAYABLE.value
    elif re.search(r"fees?\s+payable", lowered):
        basis = FeeBasis.FEES_PAYABLE.value
    elif re.search(r"fees?\s+paid", lowered):
        basis = FeeBasis.FEES_PAID.value
    else:
        basis = FeeBasis.CONTRACT_FEES.value
    scope = FeeScope.ORDER_FORM.value if "order form" in lowered else FeeScope.AGREEMENT.value
    return {"type": "fee_period", "months": months, "basis": basis, "scope": scope}


def _fixed_dollar_operand(text: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"\$\s*([\d,]+)", text)
    if not m:
        m = re.search(r"\b([\d,]+)\s*(?:million|m)\b", text, re.I)
        if m:
            amount = str(int(m.group(1).replace(",", "")) * 1_000_000)
            return {"type": "fixed_amount", "money": {"amount": amount, "currency": "USD"}}
        return None
    return {"type": "fixed_amount", "money": {"amount": m.group(1).replace(",", ""), "currency": "USD"}}


def _annual_multiple_operand(text: str) -> Optional[Dict[str, Any]]:
    m = _EXPLICIT_FEE_MULTIPLIER_RE.search(text)
    if not m:
        return None
    val = _parse_num_token(m.group(1))
    if val is None:
        return None
    return {"type": "annual_fee_multiple", "multiple": float(val)}


def _cap_expression_from_quote(text: str) -> Optional[Dict[str, Any]]:
    if _SUPER_CAP_QUOTE_RE.search(text):
        return None
    fee = _fee_period_operand(text)
    fixed = _fixed_dollar_operand(text)
    mult = _annual_multiple_operand(text)
    if _GREATER_OF_FIXED_RE.search(text) and fee and fixed:
        return {"operator": "GREATER_OF", "operands": [fee, fixed]}
    if fee:
        return {"operator": "SIMPLE", "operands": [fee]}
    if mult:
        return {"operator": "SIMPLE", "operands": [mult]}
    if fixed:
        return {"operator": "SIMPLE", "operands": [fixed]}
    return None


def _acv_threshold(text: str) -> Optional[str]:
    m = re.search(r"\$\s*([\d,]+)", text)
    if m:
        return m.group(1).replace(",", "")
    return None


def propose_liability_rules_v2_from_sections(section_texts: List[str]) -> Optional[Dict[str, Any]]:
    """Build rules_v2_json from liability section text when patterns are clear."""
    combined = "\n".join(section_texts)
    bands: List[Dict[str, Any]] = []
    super_caps: List[Dict[str, Any]] = []
    escalation_rules: List[Dict[str, Any]] = []

    for section in section_texts:
        for paragraph in re.split(r"\n\s*\n", section):
            para = paragraph.strip()
            if not para:
                continue
            if _SUPER_CAP_QUOTE_RE.search(para):
                m = re.search(r"(\d+(?:\.\d+)?|two|three)\s*(?:x|times|×)", para, re.I)
                mult = 2.0
                if m:
                    parsed = _parse_num_token(m.group(1))
                    if parsed is not None:
                        mult = float(parsed)
                super_caps.append({
                    "applies_to": ["confidentiality", "data_security"],
                    "expression": {
                        "operator": "SIMPLE",
                        "operands": [{"type": "reference", "ref": "GENERAL_CAP", "multiplier": mult}],
                    },
                })
                continue
            if _HARD_STOP_CUE_RE.search(para) and re.search(r"\b(?:less\s+than|below|minimum|not\s+exceed)\b", para, re.I):
                expr = _cap_expression_from_quote(para)
                if expr:
                    bands.append({
                        "kind": PolicyBandKind.MINIMUM_ACCEPTABLE.value,
                        "expression": expr,
                        "outcome_if_breached": BandOutcome.HARD_STOP.value,
                    })
                continue
            if _FALLBACK_CUE_RE.search(para):
                expr = _cap_expression_from_quote(para)
                if expr:
                    band: Dict[str, Any] = {"kind": PolicyBandKind.ACCEPTABLE_FALLBACK.value, "expression": expr}
                    if _ACV_CONDITION_RE.search(para):
                        threshold = _acv_threshold(para)
                        if threshold and re.search(r"\b(?:below|under|less\s+than)\b", para, re.I):
                            band["conditions"] = [{
                                "field": "annual_contract_value",
                                "operator": "LT",
                                "value": {"amount": threshold, "currency": "USD"},
                            }]
                    bands.append(band)
                continue
            if re.search(r"\b(?:preferred|primary|target)\b", para, re.I) or _GREATER_OF_FIXED_RE.search(para):
                expr = _cap_expression_from_quote(para)
                if expr and not any(b["kind"] == PolicyBandKind.PREFERRED.value for b in bands):
                    bands.append({"kind": PolicyBandKind.PREFERRED.value, "expression": expr})

    if not bands and combined:
        expr = _cap_expression_from_quote(combined)
        if expr:
            bands.append({"kind": PolicyBandKind.PREFERRED.value, "expression": expr})

    if not any(b["kind"] == PolicyBandKind.PREFERRED.value for b in bands):
        return None

    if _PARTNER_ESCALATION_RE.search(combined):
        threshold = _acv_threshold(combined) or "250000"
        escalation_rules.append({
            "when": {
                "operator": "AND",
                "conditions": [
                    {"field": "annual_contract_value", "operator": "GTE", "value": {"amount": threshold, "currency": "USD"}},
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
        })

    rules = {
        "schema_version": LIABILITY_POLICY_SCHEMA_VERSION,
        "orientation": "buy_side",
        "bands": bands,
        "carve_outs": [],
        "super_caps": super_caps,
        "escalation_rules": escalation_rules,
        "prohibit_unlimited": True,
        "consequential_damages": {"require_exclusion": False, "required_carveouts": []},
    }
    try:
        policy = liability_policy_v2_from_dict(rules)
        if policy.validate():
            return None
        return liability_policy_v2_to_dict(policy)
    except Exception:
        return None
