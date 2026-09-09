from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from policy_grammar.cap_expression import CapExpression
from policy_grammar.roles import NormalizedRole


class CarveOutCategory(str, Enum):
    CONFIDENTIALITY = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    INDEMNIFICATION = "indemnification"
    FRAUD = "fraud"
    GROSS_NEGLIGENCE = "gross_negligence"
    WILLFUL_MISCONDUCT = "willful_misconduct"
    PRIVACY = "privacy"
    DATA_SECURITY = "data_security"
    DATA_PROTECTION = "data_protection"
    BODILY_INJURY = "bodily_injury"
    OTHER = "other"


class CarveOutTreatment(str, Enum):
    OUTSIDE_GENERAL_CAP = "OUTSIDE_GENERAL_CAP"
    SUPER_CAP = "SUPER_CAP"
    SEPARATE_FIXED_CAP = "SEPARATE_FIXED_CAP"


@dataclass(frozen=True)
class CarveOutSpec:
    category: CarveOutCategory
    treatment: CarveOutTreatment
    applicable_party: Optional[NormalizedRole] = None
    custom_label: Optional[str] = None
    expression: Optional[CapExpression] = None
