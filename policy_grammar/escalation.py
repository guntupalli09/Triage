from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from policy_grammar.conditions import ConditionGroup


class ApproverRole(str, Enum):
    SUPERVISING_PARTNER = "supervising_partner"
    PRACTICE_GROUP_LEADER = "practice_group_leader"
    GENERAL_COUNSEL = "general_counsel"
    LEGAL_OPS = "legal_ops"
    CLIENT_LEGAL_CONTACT = "client_legal_contact"
    CFO = "cfo"
    CUSTOM = "custom"


class EscalationSeverity(str, Enum):
    ADVISORY = "ADVISORY"
    REQUIRED = "REQUIRED"


@dataclass(frozen=True)
class EscalationRule:
    when: ConditionGroup
    approver: ApproverRole
    custom_approver_label: Optional[str] = None
    severity: EscalationSeverity = EscalationSeverity.REQUIRED
    reason_template: Optional[str] = None
