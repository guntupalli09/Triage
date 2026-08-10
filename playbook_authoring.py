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
3. (Phase 0.1) Real Protocol-derived type validation for config_json
   (validate_config), plus a strict separation between "this object is
   shaped correctly" (authoring-time, DRAFT/NEEDS_REVIEW-safe) and "this
   object is safe to enforce" (validate_position_for_activation,
   build_policy_rule_for_enforcement) — see the two docstrings below for
   why these are different questions with different failure modes.

No route, template, or evaluate_*_policy() call site is changed by this
module. PolicyRule remains the thing main.py actually reads until Phase
4's cutover; PolicyPosition is independently testable plumbing until then.
"""

from __future__ import annotations

import typing
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Union

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


# ---------------------------------------------------------------------------
# Bounded vocabularies — Phase 0.1
#
# A Protocol's Optional[List[str]] or Optional[str] annotation only tells
# us "a list of strings" or "a string"; several of these fields are
# actually closed enumerations the engine defines elsewhere (a module-level
# constant list, or — for required_dispute_resolution — literal string
# comparisons in the evaluate function). Pulling the real vocabulary from
# each engine's own constant means this can't drift from what the engine
# actually recognizes, same principle as CLAUSE_TYPE_CONFIG_FIELDS above.
#
# governing_law's *_jurisdictions_json fields are deliberately absent here:
# jurisdictions are free-text ("Delaware", "England and Wales", ...) with
# no fixed vocabulary anywhere in governing_law_policy_engine — the engine
# matches them case-insensitively against arbitrary lawyer/contract text,
# not against an enum. Optional[List[str]] is genuinely all the type
# safety available for these three fields; see the Phase 0.1 report for
# this named as a "too weak to validate a token against" case.
# ---------------------------------------------------------------------------

_BOUNDED_VOCABULARIES: Dict[str, Dict[str, tuple]] = {
    "limitation_of_liability": {
        "required_exceptions_json": tuple(liability_policy_engine.EXCEPTION_TYPES),
        "required_consequential_carveouts_json": tuple(liability_policy_engine.CATEGORIES),
    },
    "indemnification": {
        "required_protection_triggers_json": tuple(indemnification_policy_engine.TRIGGERS),
        "prohibited_exposure_triggers_json": tuple(indemnification_policy_engine.TRIGGERS),
    },
    "termination": {
        "required_survival_topics_json": tuple(termination_policy_engine.SURVIVAL_TOPICS),
    },
    "confidentiality": {
        "required_exclusions_json": tuple(confidentiality_policy_engine.EXCLUSION_TOPICS),
    },
    "assignment": {
        "required_exceptions_json": tuple(assignment_policy_engine.EXCEPTION_TOPICS),
    },
    "governing_law": {
        # Not a Protocol-declared enum -- inferred from the only two
        # literal values governing_law_policy_engine's evaluate function
        # ever compares required_dispute_resolution against.
        "required_dispute_resolution": ("litigation", "arbitration"),
    },
}


class PolicyConfigValidationError(ValueError):
    """Raised by validate_config with every violation found, not just the
    first — a lawyer-facing (eventually) form should be able to report all
    problems in one pass rather than one round-trip per error."""

    def __init__(self, clause_type: str, errors: List[str]):
        self.clause_type = clause_type
        self.errors = errors
        super().__init__(
            f"Invalid config_json for clause_type={clause_type!r}: " + "; ".join(errors)
        )


def _is_optional(hint: Any) -> bool:
    return typing.get_origin(hint) is Union and type(None) in typing.get_args(hint)


def _non_none_arm(hint: Any) -> Any:
    """The single non-None member of an Optional[...] union. Every config
    field's Optional union in these six Protocols wraps exactly one other
    type (Optional[float], Optional[List[str]], ...) — never a real
    multi-type Union — so this is a safe simplification, not a general
    Union unwrapper."""
    args = [a for a in typing.get_args(hint) if a is not type(None)]
    return args[0]


def _validate_scalar(field_name: str, value: Any, expected: type, type_label: str) -> Optional[str]:
    if expected is bool:
        if type(value) is not bool:
            return f"{field_name}: expected bool, got {type(value).__name__}"
        return None
    if expected is float:
        # int is an acceptable literal for a float field (2 for "2x fees"
        # is not a type error); bool is explicitly excluded even though
        # Python's numeric tower makes isinstance(True, int) True.
        if type(value) is bool or not isinstance(value, (int, float)):
            return f"{field_name}: expected {type_label}, got {type(value).__name__}"
        return None
    if expected is int:
        if type(value) is bool or not isinstance(value, int):
            return f"{field_name}: expected {type_label}, got {type(value).__name__}"
        return None
    if expected is str:
        if not isinstance(value, str):
            return f"{field_name}: expected {type_label}, got {type(value).__name__}"
        return None
    return f"{field_name}: no validator for type {expected!r}"


def _validate_field(clause_type: str, field_name: str, value: Any, hint: Any) -> List[str]:
    errors: List[str] = []
    optional = _is_optional(hint)
    inner = _non_none_arm(hint) if optional else hint

    if value is None:
        if not optional:
            errors.append(f"{field_name}: None is not allowed (Protocol type is {hint!r}, not Optional)")
        return errors

    origin = typing.get_origin(inner)
    vocab = _BOUNDED_VOCABULARIES.get(clause_type, {}).get(field_name)

    if origin in (list,):
        if not isinstance(value, list):
            errors.append(f"{field_name}: expected list, got {type(value).__name__}")
            return errors
        (elem_type,) = typing.get_args(inner) or (str,)
        for i, elem in enumerate(value):
            elem_error = _validate_scalar(f"{field_name}[{i}]", elem, elem_type, elem_type.__name__)
            if elem_error:
                errors.append(elem_error)
            elif vocab is not None and elem not in vocab:
                errors.append(f"{field_name}[{i}]: {elem!r} is not a recognized value (expected one of {vocab})")
        return errors

    scalar_error = _validate_scalar(field_name, value, inner, getattr(inner, "__name__", str(inner)))
    if scalar_error:
        errors.append(scalar_error)
    elif vocab is not None and value not in vocab:
        errors.append(f"{field_name}: {value!r} is not a recognized value (expected one of {vocab})")
    return errors


def validate_config(clause_type: str, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Structural validation for a clause type's config_json: every
    supplied value is checked against the corresponding
    typing.get_type_hints() type from that clause engine's own
    *PolicyRuleLike Protocol. Rejects (never coerces) wrong-typed values,
    unknown fields, None where the Protocol doesn't allow it, and — for
    the fields whose "string" is really a closed vocabulary the engine
    defines elsewhere — tokens outside that vocabulary.

    This validates *shape*, not *completeness*: a config missing a
    require_* field entirely is still structurally valid here (the
    builder will default it) — whether that's safe to *enforce* is a
    separate question, answered by validate_position_for_activation
    below, not this function. A NEEDS_REVIEW/DRAFT position with gaps
    must still be constructible and previewable; only activation is meant
    to be the hard gate."""
    if clause_type not in _ENGINE_PROTOCOLS:
        raise ValueError(f"Unknown clause_type: {clause_type!r}")
    config = config or {}

    allowed = set(CLAUSE_TYPE_CONFIG_FIELDS[clause_type])
    unknown = set(config) - allowed
    errors = [f"unknown field: {name!r}" for name in sorted(unknown)]

    hints = typing.get_type_hints(_ENGINE_PROTOCOLS[clause_type])
    for field_name, value in config.items():
        if field_name in unknown:
            continue
        errors.extend(_validate_field(clause_type, field_name, value, hints[field_name]))

    if errors:
        raise PolicyConfigValidationError(clause_type, errors)
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
# Activation-readiness — Phase 0.1
#
# validate_config (above) proves a config_json is well-typed. It does not
# — and must not, since a DRAFT/NEEDS_REVIEW position is allowed to be
# incomplete for authoring/preview purposes — prove the position is safe
# to *enforce*. That is a different, narrower question, answered here.
#
# Every boolean field across all six *PolicyRuleLike Protocols falls into
# exactly one of two shapes, confirmed by reading each evaluate_*_policy()
# function directly (not inferred from naming alone, though the naming
# turns out to track the distinction exactly):
#
#   "prohibit_*" fields choose the SEVERITY between two states that are
#   BOTH already non-accepting. E.g. liability_policy_engine.py:1064 —
#   `state = PROHIBITED if policy.prohibit_unlimited else ESCALATE` — an
#   unlimited cap is flagged either way; prohibit_unlimited only decides
#   whether it's a hard block or a human-escalated one. A False default
#   here (from an unestablished field) cannot cause a silent ACCEPT.
#
#   "require_*" fields GATE whether an entire risk dimension is checked
#   at all, always as `if policy.require_X: ...`. E.g.
#   indemnification_policy_engine.py:755 —
#   `if policy.require_defense_control_for_exposure: ...` — when False,
#   that check never runs, and contract language that would otherwise
#   fail it produces no finding whatsoever. A False default here, coming
#   from a field nobody ever actually set, is indistinguishable inside
#   the engine from a lawyer's deliberate "we don't require this" — but
#   it did not originate as a decision, and activating a position in that
#   state silently converts "unanswered" into "answered no."
#
# This distinction was verified line-by-line for every boolean field in
# all six Protocols (see the Phase 0.1 report). It holds without
# exception, so activation-readiness is derived mechanically from it
# rather than hand-listed per adapter: every require_* boolean must be
# ESTABLISHED before activation; every prohibit_* boolean, every numeric
# ladder field (an all-None ladder already falls through to ESCALATE —
# policy_engine_core.classify_by_threshold — which is fail-safe, not
# fail-permissive), and every checklist/list field (empty means "nothing
# specifically required," a legitimate default, not a skipped check) may
# remain NOT_ESTABLISHED at activation.
# ---------------------------------------------------------------------------

def _activation_required_fields(clause_type: str) -> List[str]:
    hints = typing.get_type_hints(_ENGINE_PROTOCOLS[clause_type])
    return [
        name for name in CLAUSE_TYPE_CONFIG_FIELDS[clause_type]
        if hints[name] is bool and name.startswith("require_")
    ]


ACTIVATION_REQUIRED_FIELDS: Dict[str, List[str]] = {
    clause_type: _activation_required_fields(clause_type) for clause_type in _ENGINE_PROTOCOLS
}


class PolicyActivationError(ValueError):
    """Raised when a PolicyPosition is not safe to activate — distinct
    from PolicyConfigValidationError (shape) and from
    PolicyEnforcementGuardError (which path built the object)."""

    def __init__(self, clause_type: str, missing_fields: List[str]):
        self.clause_type = clause_type
        self.missing_fields = missing_fields
        super().__init__(
            f"PolicyPosition for clause_type={clause_type!r} is not ready to "
            f"activate: required field(s) not established: {', '.join(missing_fields)}"
        )


def _current_field_statuses(position: PolicyPosition) -> Dict[str, str]:
    """One status per field_name, taking only the current (not
    superseded) row for each — design doc §4.3: an edit to a confirmed
    field writes a new row and sets superseded_by_field_id on the old
    one, so "not superseded" is what "current" means. position.fields may
    be empty (nothing authored yet at all); that's handled the same as
    any other missing field, not specially."""
    return {f.field_name: f.status for f in position.fields if f.superseded_by_field_id is None}


def validate_position_for_activation(position: PolicyPosition) -> None:
    """The enforcement-readiness gate. A position may sit in DRAFT or
    NEEDS_REVIEW indefinitely with gaps — that's expected, that's what
    those states are for. This function is what stands between "looks
    complete enough to preview" and "safe to let evaluate_*_policy() run
    against real contracts under this position's authority." Raises
    PolicyActivationError listing every required field that is not
    ESTABLISHED; callers (the future activation route, main.py's eventual
    call site) should surface position.clause_type +
    error.missing_fields directly rather than a generic failure."""
    required = ACTIVATION_REQUIRED_FIELDS.get(position.clause_type, [])
    if not required:
        return
    statuses = _current_field_statuses(position)
    missing = [name for name in required if statuses.get(name) != "ESTABLISHED"]
    if missing:
        raise PolicyActivationError(position.clause_type, missing)


class PolicyEnforcementGuardError(ValueError):
    """Raised by build_policy_rule_for_enforcement when called on
    anything but an ACTIVE, activation-valid PolicyPosition. This is a
    distinct exception (not PolicyActivationError) so a caller can tell
    "this position was never even allowed to activate" (a data problem)
    apart from "code tried to enforce a non-ACTIVE position" (a call-site
    bug) — the latter should never happen if the activation route itself
    used validate_position_for_activation correctly."""


def build_policy_rule_for_enforcement(position: PolicyPosition) -> SimpleNamespace:
    """The ONLY builder call this codebase's contract-review path may use
    once Phase 4 cuts it over from PolicyRule to PolicyPosition. Refuses
    anything but status == "ACTIVE", and re-validates activation-readiness
    even though it should already hold for any genuinely ACTIVE row —
    status is a stored flag, not a proof, and this function does not
    trust it unchecked. Deliberately named and shaped differently from
    the six build_<clause>_policy_rule functions (which remain the
    authoring-preview path — a lawyer looking at a DRAFT/NEEDS_REVIEW
    clause card should be able to see how it would currently evaluate,
    gaps and all) so the two call sites cannot be confused for one
    another at a glance or by autocomplete."""
    if position.status != "ACTIVE":
        raise PolicyEnforcementGuardError(
            f"Refusing to build an enforcement policy rule from a PolicyPosition "
            f"(clause_type={position.clause_type!r}) with status={position.status!r}; "
            f"must be ACTIVE. Use BUILDERS[clause_type](position) directly for an "
            f"authoring preview of an incomplete position."
        )
    validate_position_for_activation(position)
    return BUILDERS[position.clause_type](position)


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
