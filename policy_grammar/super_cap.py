from __future__ import annotations

from dataclasses import dataclass
from typing import List

from policy_grammar.cap_expression import CapExpression
from policy_grammar.carve_outs import CarveOutCategory


@dataclass(frozen=True)
class SuperCapSpec:
    applies_to: List[CarveOutCategory]
    expression: CapExpression
