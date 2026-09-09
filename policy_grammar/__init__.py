"""Generic typed policy grammar — shared across clause adapters.

Separates policy concepts (what TriageCounsel understands) from firm-specific
values (what lawyers configure). See docs/architecture/liability_policy_v2_design.md.
"""
from policy_grammar.cap_expression import CapExpression, CapOperator
from policy_grammar.cap_operands import (
    AnnualFeeMultipleCap,
    CapOperand,
    FeeRelativeCap,
    FixedAmountCap,
    ReferenceCap,
    ReferenceTarget,
    UnlimitedCap,
)
from policy_grammar.comparison import (
    CompareResult,
    ComparisonOutcome,
    compare_cap_expressions,
    compare_operands,
    resolve_cap_expression_to_money,
)
from policy_grammar.conditions import (
    ConditionField,
    ConditionGroup,
    ConditionOperator,
    PolicyCondition,
    evaluate_condition,
    evaluate_condition_group,
    validate_condition,
)
from policy_grammar.evaluation_context import EvaluationContext
from policy_grammar.fee_relative import FeeBasis, FeeScope
from policy_grammar.money import MoneyAmount
from policy_grammar.roles import NormalizedRole, TransactionOrientation
from policy_grammar.serialization import (
    cap_expression_from_dict,
    cap_expression_to_dict,
    cap_operand_from_dict,
    cap_operand_to_dict,
    money_from_dict,
    money_to_dict,
)
from policy_grammar.validation import ValidationError, validate_cap_expression, validate_cap_operand

__all__ = [
    "AnnualFeeMultipleCap",
    "CapExpression",
    "CapOperand",
    "CapOperator",
    "CompareResult",
    "ComparisonOutcome",
    "ConditionField",
    "ConditionGroup",
    "ConditionOperator",
    "EvaluationContext",
    "FeeBasis",
    "FeeRelativeCap",
    "FeeScope",
    "FixedAmountCap",
    "MoneyAmount",
    "NormalizedRole",
    "PolicyCondition",
    "ReferenceCap",
    "ReferenceTarget",
    "TransactionOrientation",
    "UnlimitedCap",
    "ValidationError",
    "cap_expression_from_dict",
    "cap_expression_to_dict",
    "cap_operand_from_dict",
    "cap_operand_to_dict",
    "compare_cap_expressions",
    "compare_operands",
    "evaluate_condition",
    "evaluate_condition_group",
    "money_from_dict",
    "money_to_dict",
    "resolve_cap_expression_to_money",
    "validate_cap_expression",
    "validate_cap_operand",
    "validate_condition",
]
