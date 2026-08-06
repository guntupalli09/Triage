"""
Decision Engine — the orchestrator that turns a raw Finding list (from the
untouched rules_engine.py) into structured policy verdicts.

evaluate() ties Inheritance Resolver + Topic Binding + Policy Engine
together: resolve the firm's effective policy for this matter/contract
type, classify each finding against it, and persist one PolicyEvaluation
header plus one PolicyDecision row per finding occurrence. Every finding is
always recorded — even one with no matching policy becomes a NOT_APPLICABLE
PolicyDecision, never a silently dropped row.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from playbook.db_models import PolicyEvaluation, PolicyDecision
from playbook.inheritance import InheritanceResolver
from playbook.topic_binding import bind
from playbook.policy_engine import classify
from review_workflow import finding_key as _finding_key, _rule_id_of


class DecisionEngine:
    @staticmethod
    def evaluate(
        db: Session, contract_id: int, findings: Sequence,
        firm_id: int, rule_engine_version: str,
        matter_id: Optional[int] = None, contract_type_id: Optional[int] = None,
    ) -> PolicyEvaluation:
        effective = InheritanceResolver.resolve(db, firm_id, matter_id, contract_type_id)

        evaluation = PolicyEvaluation(
            contract_id=contract_id, matter_id=matter_id, contract_type_id=contract_type_id,
            rule_engine_version=rule_engine_version,
            resolved_policy_set_ids_json=effective.policy_set_ids,
        )
        db.add(evaluation)
        db.flush()

        for index, finding in enumerate(findings):
            rule_id = _rule_id_of(finding)
            policy_rule = bind(finding, effective.topics)
            result = classify(finding, policy_rule)

            db.add(PolicyDecision(
                evaluation_id=evaluation.id,
                finding_key=_finding_key(index, rule_id),
                rule_id=rule_id,
                policy_rule_id=policy_rule.id if policy_rule else None,
                policy_status=result.status,
                reason=result.reason,
                preferred_position=result.preferred_position,
                fallback_position=result.fallback_position,
                escalation_required=result.escalation_required,
                escalation_owner=result.escalation_owner,
                matched_policy_set_id=policy_rule.policy_set_id if policy_rule else None,
                matched_policy_rule_version=(
                    f"{policy_rule.policy_set.version_major}.{policy_rule.policy_set.version_minor}"
                    if policy_rule else None
                ),
            ))

        db.flush()
        return evaluation
