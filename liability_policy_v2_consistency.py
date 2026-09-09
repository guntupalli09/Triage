"""Structural consistency checks beyond per-field schema validation."""

from __future__ import annotations

from typing import List, Set

from liability_policy_v2 import LiabilityPolicyV2
from policy_grammar.bands import PolicyBandKind
from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import FeeRelativeCap, ReferenceCap
from policy_grammar.carve_outs import CarveOutSpec, CarveOutTreatment
from policy_grammar.comparison import ComparisonOutcome, compare_cap_expressions
from policy_grammar.evaluation_context import EvaluationContext
from policy_grammar.validation import ValidationError


def _collect_operands(expr: CapExpression):
    for op in expr.operands:
        yield op
    return


def _reference_caps_in(expr: CapExpression) -> List[ReferenceCap]:
    return [op for op in expr.operands if isinstance(op, ReferenceCap)]


def validate_policy_consistency(policy: LiabilityPolicyV2) -> List[ValidationError]:
    """Detect internally contradictory v2 rules — activation must fail."""
    errors: List[ValidationError] = []

    preferred = next((b for b in policy.bands if b.kind == PolicyBandKind.PREFERRED), None)
    minimums = [b for b in policy.bands if b.kind == PolicyBandKind.MINIMUM_ACCEPTABLE]

    # ReferenceCap belongs only in super_caps, never general bands
    for i, band in enumerate(policy.bands):
        for j, ref in enumerate(_reference_caps_in(band.expression)):
            errors.append(ValidationError(
                f"bands[{i}].expression",
                f"ReferenceCap ({ref.ref.value}) is only valid in super_caps, not policy bands",
            ))

    # Minimum vs preferred contradiction (symbolic when possible)
    if preferred:
        for i, mn in enumerate(minimums):
            cmp = compare_cap_expressions(
                mn.expression, preferred.expression, EvaluationContext(),
            )
            if cmp.outcome.name == "COMPARED" and cmp.relation == "GT":
                errors.append(ValidationError(
                    f"bands minimum[{i}]",
                    "minimum acceptable cap exceeds preferred cap — contradictory policy",
                ))

    # Carve-out category conflicts
    by_category: dict = {}
    for i, co in enumerate(policy.carve_outs):
        prev = by_category.get(co.category)
        if prev is not None and prev.treatment != co.treatment:
            errors.append(ValidationError(
                f"carve_outs[{i}]",
                f"category {co.category.value} has conflicting treatments "
                f"({prev.treatment.value} vs {co.treatment.value})",
            ))
        by_category[co.category] = co

    # Super-cap categories must not duplicate carve-out SUPER_CAP treatment without hierarchy
    super_categories: Set = set()
    for i, sc in enumerate(policy.super_caps):
        for cat in sc.applies_to:
            if cat in super_categories:
                errors.append(ValidationError(
                    f"super_caps[{i}]",
                    f"category {cat.value} appears in multiple super-cap specs",
                ))
            super_categories.add(cat)
            co = by_category.get(cat)
            if co and co.treatment == CarveOutTreatment.OUTSIDE_GENERAL_CAP:
                # Outside general cap + super cap is valid hierarchy — no error
                pass

    # Escalation + fallback overlap is allowed; contradictions at same ACV tier checked via bands above

    return errors
