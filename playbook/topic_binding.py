"""
The Finding <-> PolicyRule matching key.

rules_engine.py's rule_id convention is {SEVERITY}_{TOPIC}_{SEQ}, e.g.
"H_INDEM_01", "H_ASYMMETRIC_LIABILITY_01". main.py already derives a
human-readable category from this same token (`_get_rule_category`,
main.py) for the rule-category dashboard. derive_policy_topic here performs
the identical prefix extraction (kept in sync deliberately — see its
docstring) but returns the raw token, not the display name, since it's
used as a machine matching key rather than UI text.

This is what makes a PolicyRule bind to a topic instead of one document's
rule_id set: a firm authors a PolicyRule once against policy_topic="INDEM"
and it automatically covers every current and future engine rule whose
rule_id middle token is INDEM (H_INDEM_01, H_INDEM_ONEWAY_01,
H_INDEM_SCOPE_NARROW_01, ...) without enumerating rule_ids. A PolicyRule
can still target one exact rule_id via bound_rule_ids_json when topic-level
binding is too coarse; explicit binds always win over topic binds.
"""
from __future__ import annotations

from typing import Dict, Optional

from playbook.db_models import PolicyRule


def derive_policy_topic(rule_id: str) -> str:
    """Extract the topic token from a rules_engine.py rule_id.

    Mirrors main.py's _get_rule_category prefix extraction exactly (same
    split/rsplit logic) so the two stay aligned automatically as new rules
    are added to the ruleset — this function does not maintain its own
    separate rule_id parsing convention.
    """
    if not rule_id:
        return ""
    return rule_id.split("_", 1)[1].rsplit("_", 1)[0] if "_" in rule_id else rule_id


def bind(finding, effective_topics: Dict[str, PolicyRule]) -> Optional[PolicyRule]:
    """Resolve the PolicyRule that governs one Finding, given the firm's
    EffectivePolicySet (see playbook/inheritance.py) as a flat
    {policy_topic: PolicyRule} map with each PolicyRule's explicit
    bound_rule_ids_json already available on the object.

    Resolution order:
      1. Any PolicyRule in scope with an explicit bound_rule_ids_json entry
         matching this exact rule_id wins outright (precision beats topic).
      2. Otherwise, the PolicyRule bound to this Finding's derived topic.
      3. None if neither matches — the caller (policy_engine.classify) turns
         that into a NOT_APPLICABLE decision, never a dropped finding.
    """
    rule_id = finding.rule_id if hasattr(finding, "rule_id") else finding.get("rule_id")
    if not rule_id:
        return None

    for policy_rule in effective_topics.values():
        bound_ids = policy_rule.bound_rule_ids_json or []
        if rule_id in bound_ids:
            return policy_rule

    topic = derive_policy_topic(rule_id)
    return effective_topics.get(topic)
