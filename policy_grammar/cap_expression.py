from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from policy_grammar.cap_operands import CapOperand


class CapOperator(str, Enum):
    SIMPLE = "SIMPLE"
    GREATER_OF = "GREATER_OF"
    LESSER_OF = "LESSER_OF"


@dataclass(frozen=True)
class CapExpression:
    operator: CapOperator
    operands: List[CapOperand]

    def __post_init__(self) -> None:
        min_ops = 1 if self.operator == CapOperator.SIMPLE else 2
        if len(self.operands) < min_ops:
            raise ValueError(f"{self.operator.value} requires at least {min_ops} operand(s)")
