from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

import policy_engine_core as pec
from liability_policy_v2 import LiabilityPolicyV2
from policy_grammar.bands import BandOutcome, PolicyBandKind
from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import FeeRelativeCap, UnlimitedCap
from policy_grammar.comparison import CompareResult, ComparisonOutcome, compare_cap_expressions, resolve_cap_expression_to_money
from policy_grammar.conditions import evaluate_condition, evaluate_condition_group
from policy_grammar.evaluation_context import EvaluationContext
from policy_grammar.fee_relative import FeeBasis, FeeScope
from policy_grammar.serialization import cap_expression_from_dict

_WORD_NUM = pec.WORD_NUMBERS
_WORD_ALT = "|".join(sorted(_WORD_NUM.keys(), key=len, reverse=True))

_DURATION_FEES_RE = re.compile(
    rf"\b(\d+(?:\.\d+)?|{_WORD_ALT})\s*(?:\(\d+\))?\s*[-\s']*(years?|months?)'?\s*"
    r"(?:of\s+)?(?:worth\s+of\s+)?fees?\b",
    re.I,
)
_TRAILING_MONTHS_FEES_RE = re.compile(
    rf"(?:fees?\s+(?:paid|payable).{{0,100}}?(\d+(?:\.\d+)?|{_WORD_ALT}|twelve|six)\s*(?:\(\d+\))?\s*months?|"
    rf"(?:twelve|12|\d+)\s*(?:\(\d+\))?\s*months?\s+(?:preceding|prior|before).{{0,40}}?fees?)",
    re.I,
)


def _parse_num_token(token: str) -> Optional[float]:
    if not token:
        return None
    try:
        return float(token)
    except ValueError:
        return _WORD_NUM.get(token.lower())


def _fee_period_months_from_text(text: str) -> Optional[float]:
    m = _DURATION_FEES_RE.search(text)
    if m:
        n = _parse_num_token(m.group(1))
        if n is not None:
            unit = m.group(2).lower().rstrip("s")
            return n * 12 if unit == "year" else n
    m2 = _TRAILING_MONTHS_FEES_RE.search(text)
    if m2:
        token = m2.group(1) if m2.lastindex else None
        if token:
            n = _parse_num_token(token)
            if n is not None:
                return n
        if re.search(r"\b(?:twelve|12)\b", text, re.I):
            return 12.0
    return None


def _infer_fee_basis(text: str) -> FeeBasis:
    lowered = text.lower()
    if re.search(r"fees?\s+paid\s+or\s+payable", lowered):
        return FeeBasis.FEES_PAID_OR_PAYABLE
    if re.search(r"fees?\s+payable", lowered):
        return FeeBasis.FEES_PAYABLE
    if re.search(r"fees?\s+paid", lowered):
        return FeeBasis.FEES_PAID
    return FeeBasis.CONTRACT_FEES


def _infer_fee_scope(text: str) -> FeeScope:
    lowered = text.lower()
    if "order form" in lowered:
        return FeeScope.ORDER_FORM
    if "agreement" in lowered or "under this" in lowered:
        return FeeScope.AGREEMENT
    return FeeScope.AGREEMENT


def _fee_period_cap_from_text(text: str) -> Optional[FeeRelativeCap]:
    months = _fee_period_months_from_text(text)
    if months is None:
        return None
    return FeeRelativeCap(
        months=months,
        basis=_infer_fee_basis(text),
        scope=_infer_fee_scope(text),
    )


@dataclass
class ContractCapFacts:
    """Normalized contract-side cap for v2 evaluation."""
    expression: CapExpression
    fee_period_months: Optional[float] = None
    is_unlimited: bool = False


def contract_cap_from_legacy(facts) -> Optional[ContractCapFacts]:
    """Bridge from liability_policy_engine.LiabilityFacts via canonical facts.

    Fee-period CapValues extracted in the full provision window map to
    FeeRelativeCap symbolically. Truncated-excerpt re-parse is only a
    last-resort fallback when components are empty (legacy path); new
    extraction should never need it for fee-period language.
    """
    from contract_facts.liability_bridge import (
        canonical_liability_from_legacy,
        contract_cap_from_canonical,
        legacy_cap_expression_to_policy,
    )

    if facts is None or not getattr(facts, "clause_found", False):
        return None
    canonical = canonical_liability_from_legacy(facts)
    from_canonical = contract_cap_from_canonical(canonical)
    if from_canonical is not None:
        return from_canonical

    provision = getattr(facts, "controlling_provision", None)
    if provision is None:
        return None
    cap_expr = provision.general_cap_expression
    if cap_expr.structure == "unresolved":
        return None

    # Prefer structured components (including fee_period) over excerpt re-parse.
    policy_expr = legacy_cap_expression_to_policy(cap_expr)
    if policy_expr is not None:
        fee_months = None
        unlimited = False
        for op in policy_expr.operands:
            if isinstance(op, FeeRelativeCap):
                fee_months = op.months
            if isinstance(op, UnlimitedCap):
                unlimited = True
        return ContractCapFacts(
            expression=policy_expr,
            fee_period_months=fee_months,
            is_unlimited=unlimited,
        )

    # Deprecated fallback: re-parse provision excerpt when no components
    # were classified. Prefer fixing extraction over relying on this path.
    excerpt = (provision.raw_excerpt or cap_expr.raw_excerpt or "").strip()
    if not excerpt:
        return None
    fee_cap = _fee_period_cap_from_text(excerpt)
    if fee_cap is None:
        return None
    expr = CapExpression(operator=CapOperator.SIMPLE, operands=[fee_cap])
    return ContractCapFacts(expression=expr, fee_period_months=fee_cap.months, is_unlimited=False)


def evaluate_liability_policy_v2(
    policy: LiabilityPolicyV2,
    contract_cap: ContractCapFacts,
    ctx: EvaluationContext,
    *,
    source: str = "policy_v2",
) -> pec.PolicyDecision:
    """Deterministic v2 evaluator — no LLM."""
    validation_errors = policy.validate()
    if validation_errors:
        return _review_decision(
            source,
            f"policy schema invalid: {'; '.join(e.message for e in validation_errors)}",
            contract_cap,
        )

    if contract_cap.is_unlimited:
        if policy.prohibit_unlimited:
            return _prohibited_decision(source, "contract cap is unlimited", contract_cap, policy)
        return _escalate_decision(source, "contract cap is unlimited", contract_cap, policy)

    preferred = _band(policy, PolicyBandKind.PREFERRED)
    general_cap_money = None
    if preferred:
        resolved = resolve_cap_expression_to_money(preferred.expression, ctx)
        if resolved.outcome == ComparisonOutcome.COMPARED:
            general_cap_money = resolved.money

    # Step 3 — Hard stops (see docs/architecture/liability_policy_v2_precedence.md)
    for band in policy.bands:
        if band.kind != PolicyBandKind.MINIMUM_ACCEPTABLE:
            continue
        cond = _band_conditions_eval(band, ctx, contract_cap)
        if cond is False:
            continue
        if cond is None:
            return _review_decision(
                source, "hard-stop band conditions could not be evaluated — missing deal context", contract_cap, policy,
            )
        cmp = compare_cap_expressions(
            contract_cap.expression, band.expression, ctx,
            resolved_general_cap=general_cap_money,
        )
        if cmp.outcome == ComparisonOutcome.UNRESOLVED:
            return _review_decision(source, cmp.reason or "cannot compare against minimum band", contract_cap, policy)
        if cmp.outcome == ComparisonOutcome.COMPARED and cmp.relation == "LT":
            if band.outcome_if_breached == BandOutcome.HARD_STOP:
                return _prohibited_decision(
                    source, "contract cap below policy minimum acceptable threshold", contract_cap, policy,
                )

    # Step 4 — Escalation rules
    for rule in policy.escalation_rules:
        ok, reason = evaluate_condition_group(
            rule.when, ctx,
            contract_cap=contract_cap.expression,
            contract_fee_period_months=contract_cap.fee_period_months,
        )
        if ok is None:
            return _review_decision(source, reason or "escalation rule context insufficient", contract_cap, policy)
        if ok:
            approver = rule.custom_approver_label or rule.approver.value.replace("_", " ").title()
            return _escalate_decision(
                source, rule.reason_template or "escalation rule triggered", contract_cap, policy,
                escalate_to=approver,
            )

    # Step 5 — Preferred band
    pref_cond = _band_conditions_eval(preferred, ctx, contract_cap) if preferred else False
    if preferred and pref_cond is None:
        return _review_decision(
            source, "preferred band conditions could not be evaluated — missing deal context", contract_cap, policy,
        )
    if preferred and pref_cond is True:
        cmp = compare_cap_expressions(
            contract_cap.expression, preferred.expression, ctx,
            resolved_general_cap=general_cap_money,
        )
        if cmp.outcome == ComparisonOutcome.COMPARED:
            if cmp.relation in ("EQ", "GT"):
                return _accept_decision(source, "contract cap meets or exceeds preferred position", contract_cap, policy)
            fb_state = _evaluate_fallbacks(policy, contract_cap, ctx, general_cap_money)
            if fb_state:
                return fb_state
        elif cmp.outcome == ComparisonOutcome.UNRESOLVED:
            fb_state = _evaluate_fallbacks(policy, contract_cap, ctx, general_cap_money)
            if fb_state:
                return fb_state
            return _review_decision(source, cmp.reason or "cannot compare against preferred band", contract_cap, policy)

    # Step 6 — Fallback bands (when preferred absent or conditions not met)
    fb_state = _evaluate_fallbacks(policy, contract_cap, ctx, general_cap_money)
    if fb_state:
        return fb_state

    return _escalate_decision(source, "contract cap does not meet policy bands", contract_cap, policy)


def _band(policy: LiabilityPolicyV2, kind: PolicyBandKind):
    for b in policy.bands:
        if b.kind == kind:
            return b
    return None


def _band_conditions_eval(band, ctx, contract_cap) -> Optional[bool]:
    """Tri-state band condition evaluation: True, False, or None (UNRESOLVED)."""
    if not band.conditions:
        return True
    unresolved = False
    for cond in band.conditions:
        ok, _ = evaluate_condition(
            cond, ctx,
            contract_cap=contract_cap.expression,
            contract_fee_period_months=contract_cap.fee_period_months,
        )
        if ok is None:
            unresolved = True
        elif not ok:
            return False
    if unresolved:
        return None
    return True


def _band_conditions_match(band, ctx, contract_cap) -> bool:
    result = _band_conditions_eval(band, ctx, contract_cap)
    return result is True


def _evaluate_fallbacks(policy, contract_cap, ctx, general_cap_money):
    for band in policy.bands:
        if band.kind != PolicyBandKind.ACCEPTABLE_FALLBACK:
            continue
        cond = _band_conditions_eval(band, ctx, contract_cap)
        if cond is False:
            continue
        if cond is None:
            return _review_decision(
                "policy_v2",
                "fallback band conditions could not be evaluated — missing deal context",
                contract_cap, policy,
            )
        cmp = compare_cap_expressions(
            contract_cap.expression, band.expression, ctx,
            resolved_general_cap=general_cap_money,
        )
        if cmp.outcome == ComparisonOutcome.UNRESOLVED:
            return _review_decision("policy_v2", cmp.reason or "fallback comparison unresolved", contract_cap, policy)
        if cmp.outcome == ComparisonOutcome.COMPARED and cmp.relation in ("EQ", "LT"):
            return _accept_with_note_decision(
                None, "contract cap within acceptable fallback", contract_cap, policy,
            )
    return None


def _base_decision(state, rule_id, explanation, required_action, source, policy=None, escalate_to=None):
    return pec.PolicyDecision(
        rule_id=rule_id,
        clause_type="limitation_of_liability",
        state=state,
        contract_language="",
        extracted_summary=explanation,
        policy_limit_summary="v2 structured policy",
        required_action=required_action,
        explanation=explanation,
        negotiation_ladder=[],
        category_treatments=[],
        unresolved_facts=[],
        start_index=None,
        end_index=None,
        escalate_to=escalate_to,
        fallback_text=policy.fallback_language if policy else None,
        source=source or "policy_v2",
    )


def _accept_decision(source, explanation, contract_cap, policy):
    return _base_decision(pec.ACCEPT, "LOL-V2-ACCEPT", explanation, "No action required", source, policy)


def _accept_with_note_decision(source, explanation, contract_cap, policy):
    return _base_decision(pec.ACCEPT_WITH_NOTE, "LOL-V2-ACCEPT-NOTE", explanation, "Accept with note", source or "policy_v2", policy)


def _escalate_decision(source, explanation, contract_cap, policy, escalate_to=None):
    return _base_decision(
        pec.ESCALATE, "LOL-V2-ESCALATE", explanation,
        f"Escalate to {escalate_to or 'legal'}", source, policy, escalate_to=escalate_to,
    )


def _prohibited_decision(source, explanation, contract_cap, policy):
    return _base_decision(pec.PROHIBITED, "LOL-V2-PROHIBITED", explanation, "Do not accept", source, policy)


def _review_decision(source, explanation, contract_cap, policy=None):
    return _base_decision(
        pec.REQUIRES_REVIEW, "LOL-V2-REVIEW", explanation, "Manual review required", source or "policy_v2", policy,
    )
