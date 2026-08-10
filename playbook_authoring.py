"""
Playbook Authoring — Phase 0: data-model builders and legacy migration.

Sits above the six policy engines and above models.py, never inside
either — see docs/architecture/playbook_authoring_ux_design.md for the
full design. This module owns exactly two things at this phase:

1. Six "policy rule builder" functions (build_*_policy_rule), each
   converting a PolicyPosition row into the exact object its engine's
   evaluate_*_policy() function expects. This is the production
   promotion of the FakePolicy dataclass pattern already used by every
   tests/test_*_policy_engine.py fixture (design doc §4.1) — the object
   returned is a plain SimpleNamespace satisfying that engine's
   *PolicyRuleLike Protocol structurally, not a new dataclass per clause
   type, since the conversion logic itself (shared columns + config_json,
   validated/defaulted per Protocol) is clause-agnostic.
2. A one-time migration path for existing (Liability-only) PolicyRule
   rows into PolicyPosition + PolicyPositionField rows (design doc §8.3).

No route, template, or evaluate_*_policy() call site is changed by this
module. PolicyRule remains the thing main.py actually reads until Phase
4's cutover; PolicyPosition is independently testable plumbing until then.
"""

from __future__ import annotations

import typing
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import assignment_policy_engine
import confidentiality_policy_engine
import governing_law_policy_engine
import indemnification_policy_engine
import liability_policy_engine
import termination_policy_engine
from models import PolicyPosition, PolicyPositionField, PolicyRule

# Fields every engine's *PolicyRuleLike Protocol has in common — real
# columns on PolicyPosition, never part of config_json (design doc §4.1).
_SHARED_FIELDS = ("contract_side", "escalation_approval_authority", "fallback_text")

# clause_type -> that engine's own Protocol, used as the single source of
# truth for what belongs in config_json. Never maintained as a separate
# schema — see _config_field_names below.
_ENGINE_PROTOCOLS: Dict[str, type] = {
    "limitation_of_liability": liability_policy_engine.PolicyRuleLike,
    "indemnification": indemnification_policy_engine.IndemnificationPolicyRuleLike,
    "termination": termination_policy_engine.TerminationPolicyRuleLike,
    "confidentiality": confidentiality_policy_engine.ConfidentialityPolicyRuleLike,
    "assignment": assignment_policy_engine.AssignmentPolicyRuleLike,
    "governing_law": governing_law_policy_engine.GoverningLawPolicyRuleLike,
}

CLAUSE_TYPES = tuple(_ENGINE_PROTOCOLS)


def _config_field_names(clause_type: str) -> List[str]:
    """Clause-specific field names for a clause type's config_json,
    derived directly from that engine's own *PolicyRuleLike Protocol
    (typing.get_type_hints resolves the string annotations left by each
    engine's `from __future__ import annotations`) so this schema can
    never drift from what the engine actually accepts."""
    protocol_cls = _ENGINE_PROTOCOLS[clause_type]
    hints = typing.get_type_hints(protocol_cls)
    return [name for name in hints if name not in _SHARED_FIELDS]


CLAUSE_TYPE_CONFIG_FIELDS: Dict[str, List[str]] = {
    clause_type: _config_field_names(clause_type) for clause_type in _ENGINE_PROTOCOLS
}


def _default_for(protocol_cls: type, field_name: str) -> Any:
    """A field with no established value defaults to the least-restrictive
    interpretation, never a guess: boolean toggles default False ("not
    required"), everything else (Optional[str]/[float]/[int]/[List[str]])
    defaults to None ("not established"). This intentionally does not
    reproduce PolicyRule's own column defaults (e.g. prohibit_unlimited=
    True) — those were choices baked into the old Liability-only form;
    the migration path (migrate_legacy_policy_rule below) copies the
    PolicyRule row's actual stored values instead of relying on this
    default, so existing behavior is unaffected."""
    hints = typing.get_type_hints(protocol_cls)
    return False if hints[field_name] is bool else None


def validate_config(clause_type: str, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Reject unknown fields at write time — config_json can never
    silently accept a field the clause type's engine doesn't define."""
    if clause_type not in _ENGINE_PROTOCOLS:
        raise ValueError(f"Unknown clause_type: {clause_type!r}")
    config = config or {}
    allowed = set(CLAUSE_TYPE_CONFIG_FIELDS[clause_type])
    unknown = set(config) - allowed
    if unknown:
        raise ValueError(f"Unknown field(s) for clause_type={clause_type!r}: {sorted(unknown)}")
    return config


def _build_policy_rule(position: PolicyPosition, expected_clause_type: str) -> SimpleNamespace:
    if position.clause_type != expected_clause_type:
        raise ValueError(
            f"build_*_policy_rule for {expected_clause_type!r} called on a "
            f"PolicyPosition with clause_type={position.clause_type!r}"
        )
    protocol_cls = _ENGINE_PROTOCOLS[expected_clause_type]
    config = validate_config(expected_clause_type, position.config_json)

    values: Dict[str, Any] = {
        "contract_side": position.contract_side,
        "escalation_approval_authority": position.escalation_approval_authority,
        "fallback_text": position.fallback_text,
    }
    for field_name in CLAUSE_TYPE_CONFIG_FIELDS[expected_clause_type]:
        values[field_name] = config.get(field_name, _default_for(protocol_cls, field_name))

    return SimpleNamespace(**values)


def build_liability_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches liability_policy_engine.PolicyRuleLike."""
    return _build_policy_rule(position, "limitation_of_liability")


def build_indemnification_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches indemnification_policy_engine.IndemnificationPolicyRuleLike."""
    return _build_policy_rule(position, "indemnification")


def build_termination_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches termination_policy_engine.TerminationPolicyRuleLike."""
    return _build_policy_rule(position, "termination")


def build_confidentiality_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches confidentiality_policy_engine.ConfidentialityPolicyRuleLike."""
    return _build_policy_rule(position, "confidentiality")


def build_assignment_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches assignment_policy_engine.AssignmentPolicyRuleLike."""
    return _build_policy_rule(position, "assignment")


def build_governing_law_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches governing_law_policy_engine.GoverningLawPolicyRuleLike."""
    return _build_policy_rule(position, "governing_law")


BUILDERS = {
    "limitation_of_liability": build_liability_policy_rule,
    "indemnification": build_indemnification_policy_rule,
    "termination": build_termination_policy_rule,
    "confidentiality": build_confidentiality_policy_rule,
    "assignment": build_assignment_policy_rule,
    "governing_law": build_governing_law_policy_rule,
}


# ---------------------------------------------------------------------------
# Legacy migration — design doc §8.3
# ---------------------------------------------------------------------------

_LIABILITY_CONFIG_FIELDS = (
    "preferred_multiplier",
    "acceptable_max_multiplier",
    "negotiate_max_multiplier",
    "prohibit_unlimited",
    "required_exceptions_json",
    "require_consequential_damages_exclusion",
    "required_consequential_carveouts_json",
)


def migrate_legacy_policy_rule(db, rule: PolicyRule) -> PolicyPosition:
    """One-time backfill for a single existing PolicyRule row into a
    PolicyPosition + PolicyPositionField rows.

    status=ACTIVE immediately: these rows are, today, already governing
    live contract review, so writing anything less (DRAFT/NEEDS_REVIEW)
    would be a silent behavior change — a currently-enforced policy
    suddenly not enforced — which is exactly what this migration must
    avoid (design doc §8.3). source=MANUAL / confirmed_by=None (the
    original creating user is not recoverable from PolicyRule, which has
    no created-by column) / confirmed_at=rule.updated_at, per the same
    section.

    Idempotent: if a PolicyPosition already exists for this playbook +
    clause_type, it is returned unchanged rather than duplicated, so this
    can be safely re-run.
    """
    existing = (
        db.query(PolicyPosition)
        .filter(PolicyPosition.playbook_id == rule.playbook_id, PolicyPosition.clause_type == rule.clause_type)
        .first()
    )
    if existing:
        return existing

    if rule.clause_type != "limitation_of_liability":
        # No other clause type has ever had a PolicyRule row constructed
        # (main.py only ever builds "limitation_of_liability" — see design
        # doc §1.1) — this is a defensive guard, not an expected path.
        raise ValueError(f"No migration mapping for legacy clause_type={rule.clause_type!r}")

    config = {name: getattr(rule, name) for name in _LIABILITY_CONFIG_FIELDS}

    position = PolicyPosition(
        playbook_id=rule.playbook_id,
        clause_type=rule.clause_type,
        status="ACTIVE",
        contract_side=rule.contract_side,
        escalation_approval_authority=rule.escalation_approval_authority,
        fallback_text=rule.fallback_text,
        config_json=config,
        source_type="MANUAL",
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        activated_at=rule.updated_at,
        activated_by_user_id=None,
    )
    db.add(position)
    db.flush()  # assign position.id for the field rows below

    field_values: Dict[str, Any] = dict(config)
    field_values["contract_side"] = rule.contract_side
    field_values["escalation_approval_authority"] = rule.escalation_approval_authority
    field_values["fallback_text"] = rule.fallback_text

    for field_name, value in field_values.items():
        db.add(PolicyPositionField(
            policy_position_id=position.id,
            field_name=field_name,
            value_json=value,
            source="MANUAL",
            status="NOT_ESTABLISHED" if value is None else "ESTABLISHED",
            confirmed_by_user_id=None,
            confirmed_at=rule.updated_at,
        ))

    return position


def migrate_all_legacy_policy_rules(db) -> List[PolicyPosition]:
    """Runs migrate_legacy_policy_rule for every existing PolicyRule row
    and commits. Safe to re-run (idempotent per-row, see above)."""
    positions = [migrate_legacy_policy_rule(db, rule) for rule in db.query(PolicyRule).all()]
    db.commit()
    return positions
