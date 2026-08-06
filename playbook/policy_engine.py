"""
Policy Engine — deterministic classification of one Finding against one
(optional) PolicyRule into exactly one of six policy statuses.

This is a pure lookup table over already-known deterministic fields
(PolicyRule.status, Finding.finding_type, Finding.severity,
PolicyRule.approval_required) — no LLM, no free-text parsing beyond a
documented severity-tier comparison. Every branch is total: every
(finding, policy_rule) pair produces exactly one status, never an
exception and never a silent default to COMPLIANT.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from playbook.db_models import PolicyRule

COMPLIANT = "COMPLIANT"
PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
NEGOTIABLE = "NEGOTIABLE"
PROHIBITED = "PROHIBITED"
ESCALATE = "ESCALATE"
NOT_APPLICABLE = "NOT_APPLICABLE"

POLICY_STATUSES = (COMPLIANT, PARTIALLY_COMPLIANT, NEGOTIABLE, PROHIBITED, ESCALATE, NOT_APPLICABLE)

# Mirrors rules_engine.Severity's ordering for the acceptable/tolerance
# comparison below — kept as plain strings here (not an import of
# rules_engine.Severity) so this module has zero dependency on rule-engine
# internals beyond the Finding object's already-computed .severity string.
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

_ADVERSE_LANGUAGE = "adverse_language_detected"
_PROTECTION_NOT_FOUND = "expected_protection_not_found"
_UNABLE_TO_DETERMINE = "unable_to_determine"


@dataclass
class PolicyStatusResult:
    status: str
    reason: str
    preferred_position: Optional[str] = None
    fallback_position: Optional[str] = None
    escalation_required: bool = False
    escalation_owner: Optional[str] = None


def _finding_severity(finding) -> str:
    sev = finding.severity if hasattr(finding, "severity") else finding.get("severity")
    sev = getattr(sev, "value", sev)  # Severity enum -> str
    return (sev or "low").lower()


def _finding_type(finding) -> str:
    ft = finding.finding_type if hasattr(finding, "finding_type") else finding.get("finding_type")
    return ft or _ADVERSE_LANGUAGE


def classify(finding, policy_rule: Optional[PolicyRule]) -> PolicyStatusResult:
    if policy_rule is None:
        return PolicyStatusResult(
            status=NOT_APPLICABLE,
            reason="No firm policy has been authored for this topic — nothing to evaluate against.",
        )

    finding_type = _finding_type(finding)
    base_escalation = bool(policy_rule.approval_required)
    escalation_owner = policy_rule.escalation_owner

    # The engine could not verify this claim either way — never silently
    # treat that as compliant, regardless of what the policy says.
    if finding_type == _UNABLE_TO_DETERMINE:
        result = PolicyStatusResult(
            status=ESCALATE,
            reason="The rule engine could not determine this clause's status with confidence — requires attorney review.",
            preferred_position=policy_rule.preferred_position,
            fallback_position=policy_rule.fallback_position,
            escalation_required=True,
            escalation_owner=escalation_owner,
        )
        return result

    if policy_rule.status == "prohibited":
        reason = policy_rule.legal_reason or policy_rule.business_reason or f"'{policy_rule.title}' is prohibited by firm policy."
        result = PolicyStatusResult(
            status=PROHIBITED,
            reason=reason,
            preferred_position=policy_rule.preferred_position,
            fallback_position=policy_rule.fallback_position,
            escalation_required=base_escalation,
            escalation_owner=escalation_owner,
        )
        # approval_required floors the result at ESCALATE regardless of the
        # underlying status — an approval requirement always dominates.
        if base_escalation:
            result.status = ESCALATE
        return result

    if policy_rule.status == "negotiate":
        return PolicyStatusResult(
            status=ESCALATE if base_escalation else NEGOTIABLE,
            reason=policy_rule.business_reason or f"'{policy_rule.title}' is negotiable under firm policy; propose the fallback position.",
            preferred_position=policy_rule.preferred_position,
            fallback_position=policy_rule.fallback_position,
            escalation_required=base_escalation,
            escalation_owner=escalation_owner,
        )

    # status == "acceptable"
    tolerance_exceeded = False
    if policy_rule.severity:
        finding_rank = _SEVERITY_RANK.get(_finding_severity(finding), 0)
        policy_rank = _SEVERITY_RANK.get(str(policy_rule.severity).lower(), 0)
        tolerance_exceeded = finding_rank > policy_rank

    if base_escalation:
        return PolicyStatusResult(
            status=ESCALATE,
            reason=f"'{policy_rule.title}' requires approval before it can be marked compliant.",
            preferred_position=policy_rule.preferred_position,
            fallback_position=policy_rule.fallback_position,
            escalation_required=True,
            escalation_owner=escalation_owner,
        )

    if tolerance_exceeded:
        return PolicyStatusResult(
            status=PARTIALLY_COMPLIANT,
            reason=(
                f"'{policy_rule.title}' is acceptable under firm policy, but this occurrence's severity "
                f"exceeds the policy's tolerance ({_finding_severity(finding)} > {policy_rule.severity})."
            ),
            preferred_position=policy_rule.preferred_position,
            fallback_position=policy_rule.fallback_position,
        )

    return PolicyStatusResult(
        status=COMPLIANT,
        reason=f"Matches firm policy — '{policy_rule.title}' is within the acceptable position.",
        preferred_position=policy_rule.preferred_position,
    )
