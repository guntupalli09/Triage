from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from policy_grammar.cap_expression import CapExpression
from policy_grammar.conditions import ConditionGroup, PolicyCondition


class PolicyBandKind(str, Enum):
    PREFERRED = "PREFERRED"
    ACCEPTABLE_FALLBACK = "ACCEPTABLE_FALLBACK"
    MAXIMUM_NEGOTIABLE = "MAXIMUM_NEGOTIABLE"
    MINIMUM_ACCEPTABLE = "MINIMUM_ACCEPTABLE"


class BandOutcome(str, Enum):
    HARD_STOP = "HARD_STOP"
    ESCALATE = "ESCALATE"
    NEGOTIATE = "NEGOTIATE"


@dataclass(frozen=True)
class PolicyBand:
    kind: PolicyBandKind
    expression: CapExpression
    conditions: List[PolicyCondition] = field(default_factory=list)
    outcome_if_breached: Optional[BandOutcome] = None
