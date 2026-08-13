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

import re
import typing
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Union

import assignment_policy_engine
import confidentiality_policy_engine
import data_security_policy_engine
import governing_law_policy_engine
import indemnification_policy_engine
import liability_policy_engine
import termination_policy_engine
from models import Playbook, PolicyPosition, PolicyPositionApproval, PolicyPositionField, PolicyRule

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
    "data_security": data_security_policy_engine.DataSecurityPolicyRuleLike,
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
    "data_security": {
        "require_subprocessor_notice_or_consent": ("not_required", "notice", "consent"),
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


def vocabulary_for(clause_type: str, field_name: str) -> Optional[Tuple[str, ...]]:
    """Public accessor for a field's bounded vocabulary (or None if the
    field is free text) — used by the authoring templates to render
    checklist options without reaching into _BOUNDED_VOCABULARIES
    directly."""
    return _BOUNDED_VOCABULARIES.get(clause_type, {}).get(field_name)


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


def build_data_security_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches data_security_policy_engine.DataSecurityPolicyRuleLike."""
    return _build_policy_rule(position, "data_security")


BUILDERS = {
    "limitation_of_liability": build_liability_policy_rule,
    "indemnification": build_indemnification_policy_rule,
    "termination": build_termination_policy_rule,
    "confidentiality": build_confidentiality_policy_rule,
    "assignment": build_assignment_policy_rule,
    "governing_law": build_governing_law_policy_rule,
    "data_security": build_data_security_policy_rule,
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


def current_field_statuses(position: PolicyPosition) -> Dict[str, str]:
    """Public alias of _current_field_statuses — routes/templates need
    per-field ESTABLISHED/NOT_ESTABLISHED/CONFLICTING status to render
    "Not answered" vs a real value; this is the one function that answers
    that question, reused rather than re-derived at the route layer."""
    return _current_field_statuses(position)


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


# ---------------------------------------------------------------------------
# Phase 1: manual authoring — engine function lookup (for preview)
# ---------------------------------------------------------------------------

_ENGINE_FUNCS: Dict[str, Tuple[Any, Any]] = {
    "limitation_of_liability": (liability_policy_engine.extract_liability_facts, liability_policy_engine.evaluate_liability_policy),
    "indemnification": (indemnification_policy_engine.extract_indemnification_facts, indemnification_policy_engine.evaluate_indemnification_policy),
    "termination": (termination_policy_engine.extract_termination_facts, termination_policy_engine.evaluate_termination_policy),
    "confidentiality": (confidentiality_policy_engine.extract_confidentiality_facts, confidentiality_policy_engine.evaluate_confidentiality_policy),
    "assignment": (assignment_policy_engine.extract_assignment_facts, assignment_policy_engine.evaluate_assignment_policy),
    "governing_law": (governing_law_policy_engine.extract_governing_law_facts, governing_law_policy_engine.evaluate_governing_law_policy),
    "data_security": (data_security_policy_engine.extract_data_security_facts, data_security_policy_engine.evaluate_data_security_policy),
}

CLAUSE_TYPE_LABELS: Dict[str, str] = {
    "limitation_of_liability": "Limitation of Liability",
    "indemnification": "Indemnification",
    "termination": "Termination",
    "confidentiality": "Confidentiality",
    "assignment": "Assignment",
    "governing_law": "Governing Law",
    "data_security": "Data Protection & Security",
}


# ---------------------------------------------------------------------------
# Phase 1: form-value parsing — preserves NOT_ESTABLISHED vs explicit False
#
# This is the one non-negotiable property of everything below: a boolean
# that the lawyer never answered must come out of parsing as
# (None, "NOT_ESTABLISHED"), and an explicit "No" must come out as
# (False, "ESTABLISHED"). Nothing here uses HTML checkboxes for a
# require_*/prohibit_* field (checkboxes are absent from the POST body
# entirely when unchecked, which is indistinguishable from "field wasn't
# rendered at all" — exactly the trap this must not fall into). Every
# boolean control is rendered as a three-way radio group instead (see
# templates/policy_position_fields/*.html), so "the browser sent nothing
# for this name" can only happen if the whole control was never on the
# page — never as a side effect of the lawyer's actual choice.
# ---------------------------------------------------------------------------

class PositionFormError(ValueError):
    """A value submitted from the authoring form doesn't parse — e.g. a
    non-numeric string in a number field. Distinct from
    PolicyConfigValidationError (which fires after parsing, on a
    structurally-assembled config dict) so a route can catch this closer
    to "which literal form field was the problem" for a plain-English
    error message."""


TRISTATE_YES = "yes"
TRISTATE_NO = "no"
TRISTATE_UNSET = "unset"

DISPUTE_RESOLUTION_NOT_DECIDED = ""
DISPUTE_RESOLUTION_NO_PREFERENCE = "no_preference"


def parse_tristate_bool(raw: Optional[str]) -> Tuple[Optional[bool], str]:
    """raw is one of "yes"/"no"/"unset"/None (radio group value, or
    nothing if the group somehow wasn't submitted). "unset" and "missing"
    deliberately collapse to the same (None, NOT_ESTABLISHED) result —
    the whole point is that there is no way to observe, from the parsed
    result, whether the lawyer explicitly clicked "not decided yet" or
    the request simply didn't include the field; both are "nobody made a
    decision here," full stop."""
    if raw == TRISTATE_YES:
        return True, "ESTABLISHED"
    if raw == TRISTATE_NO:
        return False, "ESTABLISHED"
    return None, "NOT_ESTABLISHED"


def parse_optional_float(raw: Optional[str]) -> Tuple[Optional[float], str]:
    raw = (raw or "").strip()
    if not raw:
        return None, "NOT_ESTABLISHED"
    try:
        return float(raw), "ESTABLISHED"
    except ValueError:
        raise PositionFormError(f"{raw!r} is not a number")


def parse_optional_int(raw: Optional[str]) -> Tuple[Optional[int], str]:
    raw = (raw or "").strip()
    if not raw:
        return None, "NOT_ESTABLISHED"
    try:
        return int(raw), "ESTABLISHED"
    except ValueError:
        raise PositionFormError(f"{raw!r} is not a whole number")


def parse_checklist(raw_values: List[str], vocabulary: Tuple[str, ...]) -> Tuple[List[str], str]:
    """Checklist fields (required_exceptions_json and similar) are always
    ESTABLISHED once the form is submitted, even if nothing is checked —
    an empty list is a legitimate, meaningful answer ("no specific
    carve-outs required"), not an unanswered question. This is safe
    specifically because none of these fields are activation-required
    (see policy_engine reasoning in validate_position_for_activation) —
    an empty checklist can never silently disable a whole risk check the
    way an un-set require_* boolean could."""
    return [v for v in raw_values if v in vocabulary], "ESTABLISHED"


def parse_jurisdiction_list(raw: Optional[str]) -> Tuple[List[str], str]:
    """Free-text jurisdictions (comma- or newline-separated) — no bounded
    vocabulary exists for these anywhere in governing_law_policy_engine
    (see the Phase 0.1 report's "too weak to validate" note), so this
    only tokenizes; validate_config's List[str] element-type check is
    everything else in play. Always ESTABLISHED once submitted, same
    reasoning as checklists."""
    items = [part.strip() for part in re.split(r"[,\n]", raw or "") if part.strip()]
    return items, "ESTABLISHED"


def parse_dispute_resolution(raw: Optional[str]) -> Tuple[Optional[str], str]:
    """Four-way choice, not three: "not decided yet" (NOT_ESTABLISHED,
    None) is distinct from the engine's own legitimate "no preference"
    value (ESTABLISHED, None) — governing_law_policy_engine.py's
    required_dispute_resolution docstring defines None as a real policy
    stance ("no preference"), not an absence. Collapsing those two would
    make it impossible for a lawyer to ever record "we truly don't care"
    as opposed to "nobody has looked at this yet.\""""
    if raw in (None, DISPUTE_RESOLUTION_NOT_DECIDED):
        return None, "NOT_ESTABLISHED"
    if raw == DISPUTE_RESOLUTION_NO_PREFERENCE:
        return None, "ESTABLISHED"
    if raw in ("arbitration", "litigation"):
        return raw, "ESTABLISHED"
    raise PositionFormError(f"unrecognized dispute resolution option: {raw!r}")


def parse_optional_text(raw: Optional[str]) -> Tuple[Optional[str], str]:
    raw = (raw or "").strip()
    return (raw or None), "ESTABLISHED"


def _parse_config_field(clause_type: str, field_name: str, form: Any) -> Tuple[Any, str]:
    """Dispatches one config_json field to the right parser above, based
    on that field's own Protocol type (and, where relevant, its bounded
    vocabulary) — the same introspection Phase 0.1's validate_config
    already does, reused here so the two can never disagree about a
    field's shape. `form` is a Starlette FormData (supports .get() and
    .getlist())."""
    hints = typing.get_type_hints(_ENGINE_PROTOCOLS[clause_type])
    hint = hints[field_name]
    optional = _is_optional(hint)
    inner = _non_none_arm(hint) if optional else hint
    origin = typing.get_origin(inner)

    if inner is bool:
        return parse_tristate_bool(form.get(field_name))
    if origin is list:
        vocab = _BOUNDED_VOCABULARIES.get(clause_type, {}).get(field_name)
        if vocab is not None:
            return parse_checklist(form.getlist(field_name), vocab)
        return parse_jurisdiction_list(form.get(field_name))
    if inner is float:
        return parse_optional_float(form.get(field_name))
    if inner is int:
        return parse_optional_int(form.get(field_name))
    if inner is str:
        if clause_type == "governing_law" and field_name == "required_dispute_resolution":
            return parse_dispute_resolution(form.get(field_name))
        return parse_optional_text(form.get(field_name))
    raise PositionFormError(f"no form parser for {clause_type}.{field_name} ({hint!r})")


def parse_clause_form(clause_type: str, form: Any) -> Dict[str, Tuple[Any, str]]:
    """Parses every config_json field for a clause type out of a
    submitted form. Returns {field_name: (value, status)}. Raises
    PositionFormError on the first malformed value (a number field that
    doesn't parse) — callers should catch this and re-render the form
    with a plain-English error rather than a 500."""
    return {
        field_name: _parse_config_field(clause_type, field_name, form)
        for field_name in CLAUSE_TYPE_CONFIG_FIELDS[clause_type]
    }


CONTRACT_SIDES = ("mutual", "buy_side", "sell_side")


def parse_contract_side(raw: Optional[str]) -> str:
    return raw if raw in CONTRACT_SIDES else "mutual"


# ---------------------------------------------------------------------------
# Phase 1: revisions — the row-family model behind "editing an ACTIVE
# position must never mutate it in place"
#
# Within one playbook_id + clause_type "family" of PolicyPosition rows:
#   - at most one row is ever ACTIVE (enforced by activate_position, which
#     archives any existing ACTIVE sibling before activating a new row)
#   - at most one row is ever the "current" editable/pending row (DRAFT,
#     NEEDS_REVIEW, or APPROVED) — a new one is only ever created by
#     get_or_build_editable_position, and only when no such row exists
#   - every other row is ARCHIVED (history, never read by the Workbench
#     or by evaluate_*_policy())
#
# _current_position always resolves to "the row the Workbench should
# show" — the pending row if one exists, else the ACTIVE row, else None.
# ---------------------------------------------------------------------------

def _current_position(db, playbook_id: int, clause_type: str) -> Optional[PolicyPosition]:
    return (
        db.query(PolicyPosition)
        .filter(
            PolicyPosition.playbook_id == playbook_id,
            PolicyPosition.clause_type == clause_type,
            PolicyPosition.status != "ARCHIVED",
        )
        .order_by(PolicyPosition.created_at.desc(), PolicyPosition.id.desc())
        .first()
    )


def get_position_for_display(db, playbook_id: int, clause_type: str) -> Optional[PolicyPosition]:
    """Read-only lookup for the Workbench card / review pages — never
    creates a row. Public alias of _current_position for callers outside
    this module."""
    return _current_position(db, playbook_id, clause_type)


def get_or_build_editable_position(db, playbook: Playbook, clause_type: str) -> Tuple[PolicyPosition, bool]:
    """Returns (position, is_new_revision) for the authoring form.

    If the current position is already editable (DRAFT/NEEDS_REVIEW/
    APPROVED), returns it directly. If the current position is ACTIVE, or
    nothing exists yet, a new DRAFT row is created — config_json and
    field rows copied from the ACTIVE row if there was one — WITHOUT
    modifying the ACTIVE row itself. This is the entire mechanism behind
    the Phase 1 release-gate requirement that editing an ACTIVE policy
    must not silently change the currently approved legal position: there
    is no code path in this module that writes to a PolicyPosition whose
    status is ACTIVE (apply_position_update asserts this defensively)."""
    current = _current_position(db, playbook.id, clause_type)
    if current is not None and current.status != "ACTIVE":
        return current, False

    new_position = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status="DRAFT",
        contract_side=current.contract_side if current else "mutual",
        escalation_approval_authority=current.escalation_approval_authority if current else None,
        fallback_text=current.fallback_text if current else None,
        config_json=dict(current.config_json or {}) if current else {},
        source_type="MANUAL",
    )
    db.add(new_position)
    db.flush()

    if current is not None:
        for old_field in current.fields:
            if old_field.superseded_by_field_id is not None:
                continue
            db.add(PolicyPositionField(
                policy_position_id=new_position.id, field_name=old_field.field_name,
                value_json=old_field.value_json, source=old_field.source, status=old_field.status,
                confirmed_by_user_id=old_field.confirmed_by_user_id, confirmed_at=old_field.confirmed_at,
                evidence_document_id=old_field.evidence_document_id, evidence_excerpt=old_field.evidence_excerpt,
                evidence_start_index=old_field.evidence_start_index, evidence_end_index=old_field.evidence_end_index,
            ))
        db.flush()

    return new_position, True


def apply_position_update(
    db, position: PolicyPosition, *, clause_field_updates: Dict[str, Tuple[Any, str]],
    contract_side: str, escalation_approval_authority: Optional[str], fallback_text: Optional[str], user,
) -> None:
    """Writes a full field-level update to a DRAFT/NEEDS_REVIEW/APPROVED
    position. Refuses an ACTIVE position outright (defense in depth —
    routes.py should never call this on one, since
    get_or_build_editable_position never returns an ACTIVE row to edit,
    but this function does not trust that unchecked).

    Editing content after NEEDS_REVIEW or APPROVED reverts status back to
    DRAFT: those states assert "a lawyer looked at this and it was
    correct," and silently keeping that assertion true after the content
    changed underneath it would be exactly the kind of silent-authority
    bug this whole design exists to prevent. The lawyer must re-submit
    for review after any edit past that checkpoint."""
    if position.status == "ACTIVE":
        raise PolicyEnforcementGuardError(
            "Refusing to edit an ACTIVE PolicyPosition in place; use "
            "get_or_build_editable_position to obtain a revision first."
        )

    # NOT_ESTABLISHED fields are omitted from config_json entirely, never
    # stored as an explicit None — this matters even for Optional fields
    # (where None would otherwise validate fine) because it keeps
    # "unanswered" represented one way everywhere: absent from config_json
    # AND status=NOT_ESTABLISHED on the field row, never divergent. It is
    # non-negotiable for non-Optional bool fields specifically: every
    # require_*/prohibit_* Protocol field is `bool`, not `Optional[bool]`
    # (Phase 0.1 confirmed this holds for all six adapters without
    # exception), so writing an explicit None for one of these into
    # config_json would fail validate_config's own type check — config_json
    # only ever holds fields whose value is actually known.
    config = dict(position.config_json or {})
    for field_name, (value, status) in clause_field_updates.items():
        if status == "NOT_ESTABLISHED":
            config.pop(field_name, None)
        else:
            config[field_name] = value
    validate_config(position.clause_type, config)

    position.config_json = config
    position.contract_side = contract_side
    position.escalation_approval_authority = escalation_approval_authority
    position.fallback_text = fallback_text
    if position.status in ("NEEDS_REVIEW", "APPROVED"):
        position.status = "DRAFT"

    now = datetime.utcnow()
    existing_fields = {f.field_name: f for f in position.fields if f.superseded_by_field_id is None}

    def _upsert_field(field_name: str, value: Any, status: str) -> None:
        row = existing_fields.get(field_name)
        if row is None:
            row = PolicyPositionField(policy_position_id=position.id, field_name=field_name)
            db.add(row)
        row.value_json = value
        row.source = "MANUAL"
        row.status = status
        row.confirmed_by_user_id = user.id if (status == "ESTABLISHED" and user) else None
        row.confirmed_at = now if status == "ESTABLISHED" else None

    for field_name, (value, status) in clause_field_updates.items():
        _upsert_field(field_name, value, status)
    _upsert_field("contract_side", contract_side, "ESTABLISHED")
    _upsert_field("escalation_approval_authority", escalation_approval_authority, "ESTABLISHED")
    _upsert_field("fallback_text", fallback_text, "ESTABLISHED")


# ---------------------------------------------------------------------------
# Phase 1: lifecycle transitions — DRAFT -> NEEDS_REVIEW -> APPROVED -> ACTIVE
# ---------------------------------------------------------------------------

class PositionLifecycleError(ValueError):
    """An invalid state transition was requested — e.g. activating a
    position that is still DRAFT. Routes should catch this and show the
    lawyer why, never 500."""


def _record_transition(db, position: PolicyPosition, user, action: str, from_status: str, to_status: str, reason: Optional[str] = None) -> None:
    db.add(PolicyPositionApproval(
        policy_position_id=position.id, actor_user_id=user.id if user else None,
        action=action, from_status=from_status, to_status=to_status, reason=reason,
    ))


def mark_ready_for_review(db, position: PolicyPosition, user) -> None:
    if position.status != "DRAFT":
        raise PositionLifecycleError(f"Cannot submit for review from status={position.status!r}; must be DRAFT")
    validate_config(position.clause_type, position.config_json)
    _record_transition(db, position, user, "MARKED_REVIEWED", "DRAFT", "NEEDS_REVIEW")
    position.status = "NEEDS_REVIEW"


def return_to_draft(db, position: PolicyPosition, user, reason: Optional[str] = None) -> None:
    if position.status not in ("NEEDS_REVIEW", "APPROVED"):
        raise PositionLifecycleError(f"Cannot return to draft from status={position.status!r}")
    _record_transition(db, position, user, "REVERTED", position.status, "DRAFT", reason)
    position.status = "DRAFT"


def approve_position(db, position: PolicyPosition, user, reason: Optional[str] = None) -> None:
    """NEEDS_REVIEW -> APPROVED. Runs the Phase 0.1 activation validator
    first — approval and activation share the same readiness bar in
    Phase 1 (both require every require_* gate to be ESTABLISHED); they
    remain two separate actions/permission points per the design doc so a
    later "second approver activates" policy can be added without
    touching this function."""
    if position.status != "NEEDS_REVIEW":
        raise PositionLifecycleError(f"Cannot approve from status={position.status!r}; must be NEEDS_REVIEW")
    validate_position_for_activation(position)
    _record_transition(db, position, user, "APPROVED", "NEEDS_REVIEW", "APPROVED", reason)
    position.status = "APPROVED"


def activate_position(db, position: PolicyPosition, user, reason: Optional[str] = None) -> None:
    """APPROVED -> ACTIVE. Archives any existing ACTIVE sibling for the
    same playbook_id/clause_type first (in the same transaction) — this
    is the enforcement of "at most one ACTIVE row per clause type" that
    the model's docstring describes; there is no DB constraint doing it."""
    if position.status != "APPROVED":
        raise PositionLifecycleError(f"Cannot activate from status={position.status!r}; must be APPROVED")
    validate_position_for_activation(position)

    sibling_active = (
        db.query(PolicyPosition)
        .filter(
            PolicyPosition.playbook_id == position.playbook_id,
            PolicyPosition.clause_type == position.clause_type,
            PolicyPosition.status == "ACTIVE",
            PolicyPosition.id != position.id,
        )
        .first()
    )
    if sibling_active is not None:
        _record_transition(
            db, sibling_active, user, "ARCHIVED", "ACTIVE", "ARCHIVED",
            reason=f"Superseded by PolicyPosition id={position.id}",
        )
        sibling_active.status = "ARCHIVED"

    _record_transition(db, position, user, "ACTIVATED", "APPROVED", "ACTIVE", reason)
    position.status = "ACTIVE"
    position.activated_at = datetime.utcnow()
    position.activated_by_user_id = user.id if user else None


# ---------------------------------------------------------------------------
# Phase 1: coverage — enforceable coverage, not database-row coverage
# ---------------------------------------------------------------------------

@dataclass
class ClauseCoverage:
    clause_type: str
    label: str
    status_bucket: str  # "ACTIVE" | "NEEDS_ATTENTION" | "NOT_CONFIGURED"
    position: Optional[PolicyPosition]


@dataclass
class CoverageSummary:
    active_count: int
    needs_attention_count: int
    not_configured_count: int
    coverage_pct: float
    high_impact_gaps: List[str]
    clauses: List[ClauseCoverage] = dataclass_field(default_factory=list)


# Fixed, documented ranking — never inferred from data. Ordered by typical
# financial/legal exposure if left unconfigured: an uncapped liability or
# indemnification exposure is direct, often-unbounded dollar risk;
# confidentiality and termination carry real but usually bounded
# operational risk; assignment and governing law are comparatively
# lower-stakes defaults most counterparties won't aggressively push on.
# This exists so "high-impact gaps" is deterministic and explainable, and
# is expected to be revisited (not silently reordered) once Batch B
# clause types exist alongside these six.
#
# data_security was added as adapter #7 (the first added after the
# original six) and ranked directly after indemnification: a data-
# protection failure carries direct, often-unbounded regulatory-fine and
# breach-notification exposure comparable to indemnification's uncapped-
# claim risk, and materially higher than confidentiality/termination's
# bounded operational risk.
CLAUSE_TYPE_IMPORTANCE: Tuple[str, ...] = (
    "limitation_of_liability", "indemnification", "data_security", "confidentiality",
    "termination", "assignment", "governing_law",
)


def compute_coverage(db, playbook) -> CoverageSummary:
    """Coverage counts ACTIVE positions only — a DRAFT or NEEDS_REVIEW row
    existing for a clause type does not count as covered (it isn't
    enforceable; evaluate_*_policy() will never read it), so it is
    bucketed as NEEDS_ATTENTION, distinct from both ACTIVE and
    NOT_CONFIGURED. This is deliberate: the coverage bar must represent
    what actually governs a contract review today, not how many rows
    exist in the database."""
    clauses: List[ClauseCoverage] = []
    for clause_type in CLAUSE_TYPES:
        position = _current_position(db, playbook.id, clause_type)
        if position is not None and position.status == "ACTIVE":
            bucket = "ACTIVE"
        elif position is not None:
            bucket = "NEEDS_ATTENTION"
        else:
            bucket = "NOT_CONFIGURED"
        clauses.append(ClauseCoverage(clause_type=clause_type, label=CLAUSE_TYPE_LABELS[clause_type], status_bucket=bucket, position=position))

    bucket_by_type = {c.clause_type: c.status_bucket for c in clauses}
    active_count = sum(1 for b in bucket_by_type.values() if b == "ACTIVE")
    needs_attention_count = sum(1 for b in bucket_by_type.values() if b == "NEEDS_ATTENTION")
    not_configured_count = sum(1 for b in bucket_by_type.values() if b == "NOT_CONFIGURED")
    coverage_pct = round(100.0 * active_count / len(CLAUSE_TYPES), 1)
    high_impact_gaps = [ct for ct in CLAUSE_TYPE_IMPORTANCE if bucket_by_type[ct] != "ACTIVE"]

    return CoverageSummary(
        active_count=active_count, needs_attention_count=needs_attention_count,
        not_configured_count=not_configured_count, coverage_pct=coverage_pct,
        high_impact_gaps=high_impact_gaps, clauses=clauses,
    )


# ---------------------------------------------------------------------------
# Phase 1: plain-English summaries — never a JSON dump
# ---------------------------------------------------------------------------

def _fmt_mult(value: Optional[float]) -> str:
    if value is None:
        return "Not yet decided"
    return f"{value:g}× fees"


def _fmt_bool(value: Optional[bool], yes: str, no: str) -> str:
    if value is None:
        return "Not yet decided"
    return yes if value else no


def _fmt_list(values: Optional[List[str]], empty: str = "None specified") -> str:
    if not values:
        return empty
    return ", ".join(v.replace("_", " ") for v in values)


def _fmt_days(value: Optional[int]) -> str:
    return "Not yet decided" if value is None else f"{value} days"


def _fmt_years(value: Optional[int]) -> str:
    if value is None:
        return "Not yet decided"
    return "Indefinite/perpetual" if value == 0 else f"{value} year(s)"


def _fmt_hours(value: Optional[float]) -> str:
    if value is None:
        return "Not yet decided"
    return f"{value:g} hours"


def _summarize_liability(cfg: Dict[str, Any]) -> List[str]:
    lines = [
        f"Unlimited liability → {_fmt_bool(cfg.get('prohibit_unlimited'), 'Prohibited', 'Allowed only with escalation')}",
        f"Preferred cap → {_fmt_mult(cfg.get('preferred_multiplier'))}",
        f"Accept without escalation up to → {_fmt_mult(cfg.get('acceptable_max_multiplier'))}",
        f"Maximum negotiable before escalation → {_fmt_mult(cfg.get('negotiate_max_multiplier'))}",
        f"Required exceptions to the cap → {_fmt_list(cfg.get('required_exceptions_json'))}",
        f"Consequential damages exclusion required → {_fmt_bool(cfg.get('require_consequential_damages_exclusion'), 'Yes', 'No')}",
    ]
    if cfg.get("require_consequential_damages_exclusion"):
        lines.append(f"Required carve-outs from that exclusion → {_fmt_list(cfg.get('required_consequential_carveouts_json'))}")
    return lines


def _summarize_indemnification(cfg: Dict[str, Any]) -> List[str]:
    return [
        f"They must indemnify us for → {_fmt_list(cfg.get('required_protection_triggers_json'))}",
        f"We will never indemnify for → {_fmt_list(cfg.get('prohibited_exposure_triggers_json'))}",
        f"Our indemnity limited to third-party claims only → {_fmt_bool(cfg.get('require_exposure_third_party_only'), 'Required', 'Not required')}",
        f"We must control our own defense → {_fmt_bool(cfg.get('require_defense_control_for_exposure'), 'Required', 'Not required')}",
        f"Prompt notice and cooperation required first → {_fmt_bool(cfg.get('require_notice_and_cooperation_for_exposure'), 'Required', 'Not required')}",
        f"Uncapped indemnity exposure → {_fmt_bool(cfg.get('prohibit_uncapped_exposure'), 'Prohibited', 'Allowed only with escalation')}",
        f"Preferred indemnity cap → {_fmt_mult(cfg.get('exposure_preferred_multiplier'))}",
        f"Accept without escalation up to → {_fmt_mult(cfg.get('exposure_acceptable_max_multiplier'))}",
        f"Maximum negotiable before escalation → {_fmt_mult(cfg.get('exposure_negotiate_max_multiplier'))}",
    ]


def _summarize_termination(cfg: Dict[str, Any]) -> List[str]:
    return [
        f"We must have the same walk-away right they do → {_fmt_bool(cfg.get('require_mutual_convenience_termination'), 'Required', 'Not required')}",
        f"Minimum notice before they can end the deal → {_fmt_days(cfg.get('min_notice_days_against_us'))}",
        f"Minimum cure period before termination for cause → {_fmt_days(cfg.get('min_cure_days_against_us'))}",
        f"Immediate termination for cause with no cure → {_fmt_bool(cfg.get('prohibit_immediate_termination_for_cause'), 'Prohibited', 'Allowed only with escalation')}",
        f"Must survive termination → {_fmt_list(cfg.get('required_survival_topics_json'))}",
        f"Uncapped termination fee → {_fmt_bool(cfg.get('prohibit_uncapped_termination_fee'), 'Prohibited', 'Allowed only with escalation')}",
        f"Preferred termination fee cap → {_fmt_mult(cfg.get('fee_preferred_multiplier'))}",
        f"Accept without escalation up to → {_fmt_mult(cfg.get('fee_acceptable_max_multiplier'))}",
        f"Maximum negotiable before escalation → {_fmt_mult(cfg.get('fee_negotiate_max_multiplier'))}",
    ]


def _summarize_confidentiality(cfg: Dict[str, Any]) -> List[str]:
    return [
        f"Standard carve-outs required → {_fmt_list(cfg.get('required_exclusions_json'))}",
        f"Minimum years they must protect our information → {_fmt_years(cfg.get('min_protection_duration_years'))}",
        f"Maximum years we'll protect theirs → {_fmt_years(cfg.get('max_exposure_duration_years'))}",
        f"Protection must run both ways → {_fmt_bool(cfg.get('require_mutual_confidentiality'), 'Required', 'Not required')}",
    ]


def _summarize_assignment(cfg: Dict[str, Any]) -> List[str]:
    return [
        f"Assignment allowed without consent for → {_fmt_list(cfg.get('required_exceptions_json'))}",
        f"\"Sole discretion\" consent language → {_fmt_bool(cfg.get('prohibit_sole_discretion_consent'), 'Prohibited', 'Allowed')}",
        f"They need our consent too, if we need theirs → {_fmt_bool(cfg.get('require_consent_for_counterparty_assignment'), 'Required', 'Not required')}",
    ]


_DISPUTE_RESOLUTION_LABELS = {
    None: "Not yet decided",
    "no_preference": "No preference (either is acceptable)",
    "arbitration": "Arbitration required",
    "litigation": "Litigation required",
}


def _summarize_governing_law(cfg: Dict[str, Any], field_statuses: Dict[str, str]) -> List[str]:
    dispute_value = cfg.get("required_dispute_resolution")
    dispute_status = field_statuses.get("required_dispute_resolution", "NOT_ESTABLISHED")
    if dispute_status == "NOT_ESTABLISHED":
        dispute_label = "Not yet decided"
    elif dispute_value is None:
        dispute_label = _DISPUTE_RESOLUTION_LABELS["no_preference"]
    else:
        dispute_label = _DISPUTE_RESOLUTION_LABELS.get(dispute_value, dispute_value)
    return [
        f"Preferred jurisdiction(s) → {_fmt_list(cfg.get('preferred_jurisdictions_json'), 'Unspecified')}",
        f"Also acceptable → {_fmt_list(cfg.get('acceptable_jurisdictions_json'), 'Unspecified')}",
        f"Never acceptable → {_fmt_list(cfg.get('prohibited_jurisdictions_json'), 'None specified')}",
        f"Dispute resolution → {dispute_label}",
        f"Jury trial waiver required → {_fmt_bool(cfg.get('require_jury_trial_waiver'), 'Required', 'Not required')}",
    ]


_SUBPROCESSOR_REQUIREMENT_LABELS = {
    None: "Not yet decided",
    "not_required": "No notice or consent required",
    "notice": "Prior notice required",
    "consent": "Prior written consent required",
}


def _summarize_data_security(cfg: Dict[str, Any]) -> List[str]:
    return [
        f"We must be identified as Processor → {_fmt_bool(cfg.get('require_processor_role'), 'Required', 'Not required')}",
        f"Unrestricted subprocessors → {_fmt_bool(cfg.get('prohibit_unrestricted_subprocessors'), 'Prohibited', 'Allowed')}",
        f"Subprocessor engagement → {_SUBPROCESSOR_REQUIREMENT_LABELS.get(cfg.get('require_subprocessor_notice_or_consent'), 'Not yet decided')}",
        f"Preferred breach notification → {_fmt_hours(cfg.get('preferred_breach_notification_hours'))}",
        f"Auto-accept up to → {_fmt_hours(cfg.get('acceptable_max_breach_notification_hours'))}",
        f"Maximum negotiable before escalation → {_fmt_hours(cfg.get('negotiate_max_breach_notification_hours'))}",
        f"Fixed breach notification period required → {_fmt_bool(cfg.get('require_fixed_breach_notification_period'), 'Required', 'Not required')}",
        f"International transfer safeguard (SCC/adequacy) required → {_fmt_bool(cfg.get('require_international_transfer_safeguard'), 'Required', 'Not required')}",
        f"Data residency required → {_fmt_bool(cfg.get('require_data_residency'), 'Required', 'Not required')}",
        f"Approved residency region(s) → {_fmt_list(cfg.get('required_data_residency_regions_json'), 'Any')}",
        f"Deletion or return of personal data on termination required → {_fmt_bool(cfg.get('require_deletion_or_return'), 'Required', 'Not required')}",
        f"Maximum retention → {_fmt_days(cfg.get('max_retention_days'))}",
        f"Audit rights required → {_fmt_bool(cfg.get('require_audit_rights'), 'Required', 'Not required')}",
        f"Named security certification required (e.g. ISO 27001, SOC 2) → {_fmt_bool(cfg.get('require_named_security_certification'), 'Required', 'Not required')}",
        f"Cooperation with data subject/regulatory requests required → {_fmt_bool(cfg.get('require_cooperation_obligation'), 'Required', 'Not required')}",
        f"Explicit confidentiality of personal data required → {_fmt_bool(cfg.get('require_confidentiality_of_personal_data'), 'Required', 'Not required')}",
    ]


_SUMMARIZERS = {
    "limitation_of_liability": lambda cfg, statuses: _summarize_liability(cfg),
    "indemnification": lambda cfg, statuses: _summarize_indemnification(cfg),
    "termination": lambda cfg, statuses: _summarize_termination(cfg),
    "confidentiality": lambda cfg, statuses: _summarize_confidentiality(cfg),
    "assignment": lambda cfg, statuses: _summarize_assignment(cfg),
    "governing_law": lambda cfg, statuses: _summarize_governing_law(cfg, statuses),
    "data_security": lambda cfg, statuses: _summarize_data_security(cfg),
}


def summarize_position(position: PolicyPosition) -> List[str]:
    """The human-readable policy summary a lawyer approves — never a
    JSON/field-name dump. Used on both the Workbench clause card (a
    trimmed version) and the pre-approval review page (in full)."""
    cfg = position.config_json or {}
    statuses = _current_field_statuses(position)
    lines = _SUMMARIZERS[position.clause_type](cfg, statuses)
    if position.escalation_approval_authority:
        lines.append(f"Escalation authority → {position.escalation_approval_authority}")
    else:
        lines.append("Escalation authority → Not set")
    lines.append(f"Fallback/redline language → {'Provided' if position.fallback_text else 'Not provided'}")
    return lines


def card_headline(position: Optional[PolicyPosition]) -> str:
    """One short line for the Workbench tile — not the full summary."""
    if position is None:
        return "Not configured"
    lines = summarize_position(position)
    return lines[0] if lines else "Configured"


# ---------------------------------------------------------------------------
# Phase 1: preview — pure function, no DB writes, no production effect
# ---------------------------------------------------------------------------

def run_preview(position: PolicyPosition, sample_text: str):
    """Runs the SAME extractor + evaluator the real engine uses (imported
    directly, never modified, never wrapped) against lawyer-pasted sample
    text and this position's current config — via the same BUILDERS
    function used everywhere else, so there is no separate "preview
    evaluator" to drift out of sync with production logic. Read-only: no
    Contract or Contract-review record is created, and nothing here
    touches PolicyRule or any table this module doesn't already own.
    Safe to call on a DRAFT/NEEDS_REVIEW/APPROVED/ACTIVE position alike —
    unlike apply_position_update, preview never writes anything, so the
    ACTIVE-guard that protects mutation doesn't apply to it."""
    extract_fn, evaluate_fn = _ENGINE_FUNCS[position.clause_type]
    rule = BUILDERS[position.clause_type](position)
    facts = extract_fn(sample_text)
    return evaluate_fn(facts, rule, source="Preview (not enforced)")


# ---------------------------------------------------------------------------
# Phase 1: plain-English field labels — single source of truth reused by
# both route-level "missing requirements" messages and the authoring
# templates' control labels, so the two can never say different things
# about what a field means.
# ---------------------------------------------------------------------------

FIELD_LABELS: Dict[str, Dict[str, str]] = {
    "limitation_of_liability": {
        "preferred_multiplier": "Preferred liability cap",
        "acceptable_max_multiplier": "Auto-accept up to",
        "negotiate_max_multiplier": "Maximum negotiable before escalation",
        "prohibit_unlimited": "Never accept unlimited liability",
        "required_exceptions_json": "Carve-outs that must stay uncapped",
        "require_consequential_damages_exclusion": "Require exclusion of consequential/indirect damages",
        "required_consequential_carveouts_json": "Required carve-outs from that exclusion",
    },
    "indemnification": {
        "required_protection_triggers_json": "They must indemnify us for",
        "prohibited_exposure_triggers_json": "We will never indemnify for",
        "require_exposure_third_party_only": "Our indemnity only covers third-party claims",
        "require_defense_control_for_exposure": "We must control our own defense",
        "require_notice_and_cooperation_for_exposure": "Require prompt notice and cooperation first",
        "prohibit_uncapped_exposure": "Never accept uncapped indemnity",
        "exposure_preferred_multiplier": "Preferred indemnity cap",
        "exposure_acceptable_max_multiplier": "Auto-accept up to",
        "exposure_negotiate_max_multiplier": "Maximum negotiable before escalation",
    },
    "termination": {
        "require_mutual_convenience_termination": "We must have the same walk-away right they do",
        "min_notice_days_against_us": "Minimum notice before they can end the deal",
        "min_cure_days_against_us": "Minimum time to fix a problem before termination for cause",
        "prohibit_immediate_termination_for_cause": "Never allow immediate termination without a chance to fix it",
        "required_survival_topics_json": "Must survive termination",
        "prohibit_uncapped_termination_fee": "Never accept an uncapped termination fee",
        "fee_preferred_multiplier": "Preferred termination fee cap",
        "fee_acceptable_max_multiplier": "Auto-accept up to",
        "fee_negotiate_max_multiplier": "Maximum negotiable before escalation",
    },
    "confidentiality": {
        "required_exclusions_json": "Standard carve-outs that must be included",
        "min_protection_duration_years": "Minimum years they must protect our information",
        "max_exposure_duration_years": "Maximum years we'll protect theirs",
        "require_mutual_confidentiality": "Protection must run both ways",
    },
    "assignment": {
        "required_exceptions_json": "Allow assignment without consent for",
        "prohibit_sole_discretion_consent": "Never accept \"sole discretion\" consent language",
        "require_consent_for_counterparty_assignment": "They need our consent too, if we need theirs",
    },
    "governing_law": {
        "preferred_jurisdictions_json": "Preferred jurisdiction(s)",
        "acceptable_jurisdictions_json": "Also acceptable",
        "prohibited_jurisdictions_json": "Never acceptable",
        "required_dispute_resolution": "Dispute resolution requirement",
        "require_jury_trial_waiver": "Require jury trial waiver",
    },
    "data_security": {
        "require_processor_role": "We must be identified as Processor",
        "prohibit_unrestricted_subprocessors": "Never accept unrestricted subprocessors",
        "require_subprocessor_notice_or_consent": "Subprocessor engagement requires",
        "preferred_breach_notification_hours": "Preferred breach notification window",
        "acceptable_max_breach_notification_hours": "Auto-accept up to",
        "negotiate_max_breach_notification_hours": "Maximum negotiable before escalation",
        "require_fixed_breach_notification_period": "Require a fixed breach notification period",
        "require_international_transfer_safeguard": "Require an international transfer safeguard (SCC/adequacy)",
        "require_data_residency": "Require a stated data-residency commitment",
        "required_data_residency_regions_json": "Approved residency region(s)",
        "require_deletion_or_return": "Require deletion or return of personal data on termination",
        "max_retention_days": "Maximum retention period",
        "require_audit_rights": "Require audit rights",
        "require_named_security_certification": "Require a named security certification (e.g. ISO 27001, SOC 2)",
        "require_cooperation_obligation": "Require cooperation with data subject/regulatory requests",
        "require_confidentiality_of_personal_data": "Require explicit confidentiality of personal data",
    },
}

SHARED_FIELD_LABELS: Dict[str, str] = {
    "contract_side": "Which side are we?",
    "escalation_approval_authority": "Who signs off if this needs escalation?",
    "fallback_text": "Fallback language to propose",
}


def missing_field_labels(clause_type: str, missing_fields: List[str]) -> List[str]:
    """Turns validate_position_for_activation's internal field names into
    the same plain-English labels the authoring form itself uses — so a
    lawyer sees "Our indemnity only covers third-party claims" as an
    unanswered question, never require_exposure_third_party_only."""
    labels = FIELD_LABELS[clause_type]
    return [labels.get(f, f) for f in missing_fields]
