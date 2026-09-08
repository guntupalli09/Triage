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
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import assignment_policy_engine
import confidentiality_policy_engine
import data_security_policy_engine
import governing_law_policy_engine
import indemnification_policy_engine
import insurance_policy_engine
import ip_ownership_policy_engine
import liability_policy_engine
import payment_terms_policy_engine
import sla_policy_engine
import termination_policy_engine
import warranties_policy_engine
from models import (
    POLICY_POSITION_SEGMENT_FIELDS, Playbook, PolicyPosition, PolicyPositionApproval,
    PolicyPositionField, PolicyRule,
)

# A segment is (business_unit, customer_type, deal_value_min, deal_value_max)
# — see models.POLICY_POSITION_SEGMENT_FIELDS. None (the default everywhere
# below) means the GLOBAL segment, i.e. all four fields None — every family
# function below is 100% behavior-preserving for existing (pre-segmentation)
# playbooks, which have only ever had GLOBAL positions.
Segment = Tuple[Optional[str], Optional[str], Optional[float], Optional[float]]
GLOBAL_SEGMENT: Segment = (None, None, None, None)

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
    "ip_ownership": ip_ownership_policy_engine.IPPolicyRuleLike,
    "insurance": insurance_policy_engine.InsurancePolicyRuleLike,
    "payment_terms": payment_terms_policy_engine.PaymentPolicyRuleLike,
    "warranties": warranties_policy_engine.WarrantiesPolicyRuleLike,
    "sla": sla_policy_engine.SLAPolicyRuleLike,
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
    "payment_terms": {
        # Not a Protocol-declared enum -- inferred from the four literal
        # values payment_terms_policy_engine's extraction/evaluate logic
        # ever compares payment_trigger / required_payment_trigger against.
        "required_payment_trigger": ("invoice", "receipt", "acceptance", "milestone"),
    },
    "warranties": {
        "required_warranty_categories_json": tuple(warranties_policy_engine.WARRANTY_CATEGORIES),
        "prohibited_warranty_categories_json": tuple(warranties_policy_engine.WARRANTY_CATEGORIES),
        # Not a Protocol-declared enum -- inferred from the two literal
        # values warranties_policy_engine's evaluate logic ever compares
        # required_remedy_type against.
        "required_remedy_type": ("repair_replace_reperform", "refund_credit"),
    },
    "sla": {
        "permitted_maintenance_exclusions_json": tuple(sla_policy_engine.MAINTENANCE_EXCLUSION_TYPES),
        # Not a Protocol-declared enum -- inferred from the two literal
        # values sla_policy_engine's evaluate logic ever compares
        # required_support_hours against.
        "required_support_hours": ("24x7", "business_hours"),
        # Not a Protocol-declared enum -- inferred from the two literal
        # basis values sla_policy_engine's _to_hours/evaluate logic ever
        # compares p{n}_response_basis/p{n}_restoration_basis against.
        "p1_response_basis": ("calendar", "business"), "p1_restoration_basis": ("calendar", "business"),
        "p2_response_basis": ("calendar", "business"), "p2_restoration_basis": ("calendar", "business"),
        "p3_response_basis": ("calendar", "business"), "p3_restoration_basis": ("calendar", "business"),
        "p4_response_basis": ("calendar", "business"), "p4_restoration_basis": ("calendar", "business"),
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


def build_ip_ownership_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches ip_ownership_policy_engine.IPPolicyRuleLike."""
    return _build_policy_rule(position, "ip_ownership")


def build_insurance_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches insurance_policy_engine.InsurancePolicyRuleLike."""
    return _build_policy_rule(position, "insurance")


def build_payment_terms_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches payment_terms_policy_engine.PaymentPolicyRuleLike."""
    return _build_policy_rule(position, "payment_terms")


def build_warranties_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches warranties_policy_engine.WarrantiesPolicyRuleLike."""
    return _build_policy_rule(position, "warranties")


def build_sla_policy_rule(position: PolicyPosition) -> SimpleNamespace:
    """Matches sla_policy_engine.SLAPolicyRuleLike."""
    return _build_policy_rule(position, "sla")


BUILDERS = {
    "limitation_of_liability": build_liability_policy_rule,
    "indemnification": build_indemnification_policy_rule,
    "termination": build_termination_policy_rule,
    "confidentiality": build_confidentiality_policy_rule,
    "assignment": build_assignment_policy_rule,
    "governing_law": build_governing_law_policy_rule,
    "data_security": build_data_security_policy_rule,
    "ip_ownership": build_ip_ownership_policy_rule,
    "insurance": build_insurance_policy_rule,
    "payment_terms": build_payment_terms_policy_rule,
    "warranties": build_warranties_policy_rule,
    "sla": build_sla_policy_rule,
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


# Adapter-owned activation-validator hook (design doc: docs/architecture/
# sla_adapter_design.md S3.3). ACTIVATION_REQUIRED_FIELDS's mechanical
# rule (bool type hint + require_ name prefix) inspects exactly one
# field's type and name — it cannot express a relationship BETWEEN
# fields. SLA is the first adapter where a require_* boolean's entire
# enforcement value depends on a companion set of other fields also being
# configured (e.g. require_severity_tiers=True with every pN_max_*_hours
# field left unconfigured is a vacuously "enforceable" position that
# never actually checks anything). Rather than expand the generic
# mechanical rule to handle this one adapter's shape, this dict is a
# purely additive extension point: it defaults to empty, so the other
# eleven adapters' activation behavior is provably unchanged (see
# tests/test_sla_activation_hook_no_effect_on_existing_adapters.py),
# and only clause types that register a validator here get any
# additional check at all.
_ADAPTER_ACTIVATION_VALIDATORS: Dict[str, Callable[["PolicyPosition", Dict[str, str]], List[str]]] = {}


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
    statuses = _current_field_statuses(position)
    missing: List[str] = []

    is_lol_v2 = (
        position.clause_type == "limitation_of_liability"
        and (getattr(position, "policy_schema_version", 1) or 1) == 2
    )
    if not is_lol_v2:
        required = ACTIVATION_REQUIRED_FIELDS.get(position.clause_type, [])
        missing = [name for name in required if statuses.get(name) != "ESTABLISHED"] if required else []

    extra_validator = _ADAPTER_ACTIVATION_VALIDATORS.get(position.clause_type)
    if extra_validator:
        missing = list(missing) + list(extra_validator(position, statuses))

    if missing:
        raise PolicyActivationError(position.clause_type, missing)


def _sla_activation_validator(position: PolicyPosition, statuses: Dict[str, str]) -> List[str]:
    """SLA-specific consistency checks the mechanical ACTIVATION_REQUIRED_
    FIELDS rule cannot express (design doc S3.2/S3.3): a require_*
    boolean whose enforcement value depends on a companion set of numeric/
    basis fields also being configured. Returns extra "missing" entries
    (human-readable, not necessarily bare field names — PolicyActivationError
    just joins and displays them) on top of whatever the mechanical rule
    already found; returns [] when nothing extra is wrong."""
    cfg = position.config_json or {}
    extra: List[str] = []

    def _is_true(field_name: str) -> bool:
        return statuses.get(field_name) == "ESTABLISHED" and cfg.get(field_name) is True

    if _is_true("require_severity_tiers"):
        severity_fields = [
            "p1_max_response_hours", "p1_max_restoration_hours",
            "p2_max_response_hours", "p2_max_restoration_hours",
            "p3_max_response_hours", "p3_max_restoration_hours",
            "p4_max_response_hours", "p4_max_restoration_hours",
        ]
        if not any(statuses.get(f) == "ESTABLISHED" for f in severity_fields):
            extra.append(
                "require_severity_tiers is enabled, but no P1-P4 response/restoration ceiling "
                "is configured — this would activate a requirement that never actually checks anything"
            )

    for level_prefix in ("p1", "p2", "p3", "p4"):
        for dimension in ("response", "restoration"):
            hours_field = f"{level_prefix}_max_{dimension}_hours"
            basis_field = f"{level_prefix}_{dimension}_basis"
            if statuses.get(hours_field) == "ESTABLISHED" and statuses.get(basis_field) != "ESTABLISHED":
                extra.append(
                    f"{hours_field} is configured, but {basis_field} is not — a response/"
                    f"restoration ceiling without a stated basis can never be safely compared "
                    f"against contract text (this adapter never assumes a basis)"
                )

    if _is_true("require_service_credits"):
        credit_params = ["minimum_credit_percent_of_fees", "minimum_credit_cap_percent_of_fees"]
        if not any(statuses.get(f) == "ESTABLISHED" for f in credit_params):
            extra.append(
                "require_service_credits is enabled, but neither minimum_credit_percent_of_fees "
                "nor minimum_credit_cap_percent_of_fees is configured — this would activate a "
                "requirement with no way to evaluate whether a stated credit is adequate"
            )

    return extra


_ADAPTER_ACTIVATION_VALIDATORS["sla"] = _sla_activation_validator


def _lol_v2_activation_validator(position: PolicyPosition, statuses: Dict[str, str]) -> List[str]:
    """v2 LoL positions validate rules_v2_json instead of v1 config_json fields."""
    if (getattr(position, "policy_schema_version", 1) or 1) != 2:
        return []
    extra: List[str] = []
    rules = position.rules_v2_json
    if not rules:
        extra.append("rules_v2_json is required for policy_schema_version=2")
        return extra
    try:
        from liability_policy_v2 import liability_policy_v2_from_dict
        from policy_grammar.bands import PolicyBandKind

        policy = liability_policy_v2_from_dict(rules)
        validation_errors = policy.validate()
        if validation_errors:
            extra.append(
                "rules_v2_json failed validation: "
                + "; ".join(f"{e.path}: {e.message}" for e in validation_errors)
            )
        has_preferred = any(b.kind == PolicyBandKind.PREFERRED for b in policy.bands)
        if not has_preferred:
            extra.append("rules_v2_json must include at least one PREFERRED band")
    except Exception as exc:  # noqa: BLE001 — surface parse errors at activation
        extra.append(f"rules_v2_json could not be parsed: {type(exc).__name__}")
    return extra


_ADAPTER_ACTIVATION_VALIDATORS["limitation_of_liability"] = _lol_v2_activation_validator


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
    "ip_ownership": (ip_ownership_policy_engine.extract_ip_facts, ip_ownership_policy_engine.evaluate_ip_policy),
    "insurance": (insurance_policy_engine.extract_insurance_facts, insurance_policy_engine.evaluate_insurance_policy),
    "payment_terms": (payment_terms_policy_engine.extract_payment_facts, payment_terms_policy_engine.evaluate_payment_policy),
    "warranties": (warranties_policy_engine.extract_warranties_facts, warranties_policy_engine.evaluate_warranties_policy),
    "sla": (sla_policy_engine.extract_sla_facts, sla_policy_engine.evaluate_sla_policy),
}

CLAUSE_TYPE_LABELS: Dict[str, str] = {
    "limitation_of_liability": "Limitation of Liability",
    "indemnification": "Indemnification",
    "termination": "Termination",
    "confidentiality": "Confidentiality",
    "assignment": "Assignment",
    "governing_law": "Governing Law",
    "data_security": "Data Protection & Security",
    "ip_ownership": "IP Ownership & Licensing",
    "insurance": "Insurance",
    "payment_terms": "Payment Terms",
    "warranties": "Warranties",
    "sla": "SLA / Service Levels",
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


def parse_clause_form_best_effort(clause_type: str, form: Any) -> Dict[str, Any]:
    """Same parse as parse_clause_form, but field-by-field and never
    raising: fields that parse cleanly are returned as a config-shaped
    dict, and the one(s) that don't are simply omitted.

    Used only to re-render an authoring form after a validation failure so
    the lawyer's other entered values survive the round trip (UX
    walkthrough P0-1: an invalid submission must not blank the form). It
    is never a persistence path — nothing calls this to write config_json.
    """
    out: Dict[str, Any] = {}
    for field_name in CLAUSE_TYPE_CONFIG_FIELDS[clause_type]:
        try:
            value, status = _parse_config_field(clause_type, field_name, form)
        except (PositionFormError, ValueError):
            continue
        if status != "NOT_ESTABLISHED":
            out[field_name] = value
    return out


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

def _segment_filter(query, segment: Optional[Segment]):
    business_unit, customer_type, deal_min, deal_max = segment or GLOBAL_SEGMENT
    return query.filter(
        PolicyPosition.segment_business_unit == business_unit,
        PolicyPosition.segment_customer_type == customer_type,
        PolicyPosition.segment_deal_value_min == deal_min,
        PolicyPosition.segment_deal_value_max == deal_max,
    )


def _current_position(db, playbook_id: int, clause_type: str, segment: Optional[Segment] = None) -> Optional[PolicyPosition]:
    query = db.query(PolicyPosition).filter(
        PolicyPosition.playbook_id == playbook_id,
        PolicyPosition.clause_type == clause_type,
        PolicyPosition.status != "ARCHIVED",
    )
    return (
        _segment_filter(query, segment)
        .order_by(PolicyPosition.created_at.desc(), PolicyPosition.id.desc())
        .first()
    )


def get_position_for_display(db, playbook_id: int, clause_type: str, segment: Optional[Segment] = None) -> Optional[PolicyPosition]:
    """Read-only lookup for the Workbench card / review pages — never
    creates a row. Public alias of _current_position for callers outside
    this module. `segment` defaults to GLOBAL, matching every call site
    that predates segment conditionality."""
    return _current_position(db, playbook_id, clause_type, segment)


def list_positions_for_clause_type(db, playbook_id: int, clause_type: str) -> List[PolicyPosition]:
    """Every non-archived position (any segment) for one clause_type —
    the Workbench's segment-management view iterates this to show the
    GLOBAL position alongside whatever segment variants exist."""
    return (
        db.query(PolicyPosition)
        .filter(
            PolicyPosition.playbook_id == playbook_id,
            PolicyPosition.clause_type == clause_type,
            PolicyPosition.status != "ARCHIVED",
        )
        .order_by(PolicyPosition.created_at.desc(), PolicyPosition.id.desc())
        .all()
    )


def get_or_build_editable_position(
    db, playbook: Playbook, clause_type: str, segment: Optional[Segment] = None,
) -> Tuple[PolicyPosition, bool]:
    """Returns (position, is_new_revision) for the authoring form.

    If the current position is already editable (DRAFT/NEEDS_REVIEW/
    APPROVED), returns it directly. If the current position is ACTIVE, or
    nothing exists yet, a new DRAFT row is created — config_json and
    field rows copied from the ACTIVE row if there was one — WITHOUT
    modifying the ACTIVE row itself. This is the entire mechanism behind
    the Phase 1 release-gate requirement that editing an ACTIVE policy
    must not silently change the currently approved legal position: there
    is no code path in this module that writes to a PolicyPosition whose
    status is ACTIVE (apply_position_update asserts this defensively).

    `segment` (default GLOBAL) scopes the family this operates on — a
    segment with nothing configured yet starts empty (contract_side=
    "mutual", no config), it does NOT clone the GLOBAL position's config;
    use create_segment_position to start a new segment from an existing
    position's content instead."""
    current = _current_position(db, playbook.id, clause_type, segment)
    if current is not None and current.status != "ACTIVE":
        return current, False

    business_unit, customer_type, deal_min, deal_max = segment or GLOBAL_SEGMENT
    new_position = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status="DRAFT",
        contract_side=current.contract_side if current else "mutual",
        escalation_approval_authority=current.escalation_approval_authority if current else None,
        fallback_text=current.fallback_text if current else None,
        config_json=dict(current.config_json or {}) if current else {},
        source_type="MANUAL",
        segment_business_unit=business_unit, segment_customer_type=customer_type,
        segment_deal_value_min=deal_min, segment_deal_value_max=deal_max,
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


class DuplicateSegmentError(ValueError):
    """Raised by create_segment_position when the target segment already
    has a non-archived row — callers should route the lawyer to
    get_or_build_editable_position for that existing family instead of
    silently creating a second, competing one."""


def create_segment_position(
    db, playbook: Playbook, clause_type: str, segment: Segment, *, clone_from: Optional[Segment] = GLOBAL_SEGMENT,
) -> PolicyPosition:
    """Starts a new segment variant for a clause_type — e.g. "Enterprise
    customers get a 3x liability cap instead of the 1x GLOBAL default."
    segment must not be GLOBAL_SEGMENT (use get_or_build_editable_position
    for that family) and must not already have a non-archived row.

    Unlike get_or_build_editable_position building a brand-new segment
    from scratch, this clones config/fallback/escalation from
    `clone_from`'s current position (GLOBAL by default) as the starting
    draft — the common case is "same position as our default, except for
    this one field," not starting from nothing. Pass clone_from=None to
    start empty instead."""
    if segment == GLOBAL_SEGMENT:
        raise ValueError("create_segment_position is for non-GLOBAL segments; use get_or_build_editable_position for GLOBAL")
    if _current_position(db, playbook.id, clause_type, segment) is not None:
        raise DuplicateSegmentError(
            f"A position already exists for playbook_id={playbook.id} clause_type={clause_type!r} segment={segment!r}"
        )

    base = _current_position(db, playbook.id, clause_type, clone_from) if clone_from is not None else None
    business_unit, customer_type, deal_min, deal_max = segment
    new_position = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status="DRAFT",
        contract_side=base.contract_side if base else "mutual",
        escalation_approval_authority=base.escalation_approval_authority if base else None,
        fallback_text=base.fallback_text if base else None,
        config_json=dict(base.config_json or {}) if base else {},
        source_type="MANUAL",
        segment_business_unit=business_unit, segment_customer_type=customer_type,
        segment_deal_value_min=deal_min, segment_deal_value_max=deal_max,
    )
    db.add(new_position)
    db.flush()

    if base is not None:
        for old_field in base.fields:
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

    return new_position


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
    """APPROVED -> ACTIVE. Archives any existing ACTIVE sibling in the SAME
    segment for this playbook_id/clause_type first (in the same
    transaction) — this is the enforcement of "at most one ACTIVE row per
    clause type per segment" that the model's docstring describes; there
    is no DB constraint doing it. Scoping the sibling lookup by segment
    (not just clause_type) is what lets a segment-specific position (e.g.
    Enterprise-customer liability) and the GLOBAL position for the same
    clause_type both be ACTIVE at once — activating one never archives
    the other. For a GLOBAL position (the only kind that existed before
    segment conditionality), this reproduces the original one-row-per-
    clause_type behavior exactly, since every pre-existing row's segment
    is GLOBAL."""
    if position.status != "APPROVED":
        raise PositionLifecycleError(f"Cannot activate from status={position.status!r}; must be APPROVED")
    validate_position_for_activation(position)

    sibling_active = (
        _segment_filter(
            db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == position.playbook_id,
                PolicyPosition.clause_type == position.clause_type,
                PolicyPosition.status == "ACTIVE",
                PolicyPosition.id != position.id,
            ),
            (
                position.segment_business_unit, position.segment_customer_type,
                position.segment_deal_value_min, position.segment_deal_value_max,
            ),
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
#
# ip_ownership was added as adapter #8 and ranked directly after
# data_security: losing ownership of foreground work product/deliverables,
# or losing the license needed to use a counterparty's background IP
# embedded in what was delivered, is a direct and often business-critical
# exposure (loss of the ability to use or resell what was built/paid for)
# — comparable in stakes to a data-protection gap, and materially higher
# than confidentiality/termination's bounded operational risk.
#
# insurance was added as adapter #9 and ranked after ip_ownership but
# still ahead of confidentiality/termination: inadequate or missing
# insurance coverage is a direct, quantifiable balance-sheet exposure if
# a claim materializes (the counterparty's insurer — or lack of one —
# stands behind exactly the same risks liability/indemnification caps
# already rank highly), materially higher-stakes than confidentiality or
# termination's bounded operational risk, though one step behind
# ip_ownership's often business-critical (not just financial) exposure.
#
# payment_terms was added as adapter #10 and ranked at the top,
# alongside limitation_of_liability: payment timing, disputed-amount
# withholding, set-off, and price-increase terms are direct cash-flow
# and balance-sheet exposure that materializes on essentially every
# invoice cycle, not just when a claim or incident occurs — the most
# immediate, recurring financial risk of any clause type modeled so
# far, ranked ahead of indemnification/data_security/ip_ownership/
# insurance (whose exposure is contingent on a claim, breach, dispute,
# or loss event actually happening).
#
# warranties was added as adapter #11 (the first added after the
# ten-adapter scalability review) and ranked after insurance but ahead
# of confidentiality/termination: a warranty gap (missing non-
# infringement, compliance-with-law, or malware-free warranties; an
# unrestricted "AS IS" disclaimer; an unfavorable exclusive-remedy
# limitation) is a direct, concrete product-quality/compliance/IP
# exposure comparable in kind to insurance's balance-sheet risk — but
# typically bounded by the remedy language itself (repair/replace/
# reperform, refund/credit) once a breach occurs, unlike liability/
# indemnification/data_security/ip_ownership's open-ended exposure, and
# not itself a recurring cash-flow risk the way payment_terms is.
#
# sla was added as adapter #12 (built per the resolved design in
# docs/architecture/sla_adapter_design.md) and ranked directly after
# warranties: an SLA gap (missing availability floor, missing/weak
# severity-tier response and restoration commitments, no service-credit
# remedy, or credits stated as the exclusive remedy) is, like warranties,
# a concrete, recurring operational exposure bounded by the contract's
# own credit-cap/remedy language once a breach occurs -- but SLA failure
# recurs on essentially every measurement period (monthly/quarterly)
# rather than only when a discrete defect or claim arises, putting it
# closer to payment_terms' recurring-cash-flow character than to
# warranties' one-time-breach character, while still being bounded
# (unlike liability/indemnification/data_security/ip_ownership's
# open-ended exposure) -- ranked just below warranties and above
# confidentiality/termination for that combination of recurrence and
# boundedness.
CLAUSE_TYPE_IMPORTANCE: Tuple[str, ...] = (
    "payment_terms", "limitation_of_liability", "indemnification", "data_security",
    "ip_ownership", "insurance", "warranties", "sla", "confidentiality", "termination",
    "assignment", "governing_law",
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


def _summarize_ip_ownership(cfg: Dict[str, Any]) -> List[str]:
    return [
        f"We retain our background/pre-existing IP → {_fmt_bool(cfg.get('require_we_retain_background_ip'), 'Required', 'Not required')}",
        f"We own work product/deliverables → {_fmt_bool(cfg.get('require_we_own_work_product'), 'Required', 'Not required')}",
        f"Joint ownership → {_fmt_bool(cfg.get('prohibit_joint_ownership'), 'Prohibited', 'Allowed')}",
        f"License to use embedded background IP required → {_fmt_bool(cfg.get('require_license_for_embedded_background_ip'), 'Required', 'Not required')}",
        f"Exclusive license required → {_fmt_bool(cfg.get('require_license_exclusive'), 'Required', 'Not required')}",
        f"Royalty-bearing license → {_fmt_bool(cfg.get('prohibit_royalty_bearing_license'), 'Prohibited', 'Allowed')}",
        f"Perpetual license required → {_fmt_bool(cfg.get('require_perpetual_license'), 'Required', 'Not required')}",
        f"Revocable license → {_fmt_bool(cfg.get('prohibit_revocable_license'), 'Prohibited', 'Allowed')}",
        f"Sublicensing required → {_fmt_bool(cfg.get('require_sublicensable'), 'Required', 'Not required')}",
        f"Transferability required → {_fmt_bool(cfg.get('require_transferable'), 'Required', 'Not required')}",
        f"Worldwide territory required → {_fmt_bool(cfg.get('require_worldwide_territory'), 'Required', 'Not required')}",
        f"Purpose-limited (field-of-use) license required → {_fmt_bool(cfg.get('require_purpose_limited_license'), 'Required', 'Not required')}",
        f"Derivative works → {_fmt_bool(cfg.get('prohibit_derivative_works'), 'Prohibited', 'Allowed')}",
        f"Feedback must be assigned outright → {_fmt_bool(cfg.get('require_feedback_assigned'), 'Required', 'Not required')}",
        f"Residual-knowledge rights required → {_fmt_bool(cfg.get('require_residual_knowledge_rights'), 'Required', 'Not required')}",
        f"Open-source disclosure required → {_fmt_bool(cfg.get('require_open_source_disclosure'), 'Required', 'Not required')}",
        f"Infringement/third-party IP reference required → {_fmt_bool(cfg.get('require_infringement_remedy_reference'), 'Required', 'Not required')}",
        f"License must survive termination → {_fmt_bool(cfg.get('require_post_termination_survival'), 'Required', 'Not required')}",
    ]


def _fmt_dollars(value: Optional[float]) -> str:
    if value is None:
        return "Not yet decided"
    return f"${value:,.0f}"


def _summarize_insurance(cfg: Dict[str, Any]) -> List[str]:
    return [
        f"Commercial General Liability required → {_fmt_bool(cfg.get('require_cgl'), 'Required', 'Not required')}",
        f"CGL minimum per-occurrence limit → {_fmt_dollars(cfg.get('cgl_minimum_per_occurrence'))}",
        f"CGL minimum aggregate limit → {_fmt_dollars(cfg.get('cgl_minimum_aggregate'))}",
        f"Professional Liability / E&O required → {_fmt_bool(cfg.get('require_professional_liability'), 'Required', 'Not required')}",
        f"Professional Liability minimum limit → {_fmt_dollars(cfg.get('professional_liability_minimum_limit'))}",
        f"Cyber Liability required → {_fmt_bool(cfg.get('require_cyber_liability'), 'Required', 'Not required')}",
        f"Cyber Liability minimum limit → {_fmt_dollars(cfg.get('cyber_liability_minimum_limit'))}",
        f"Workers' Compensation required → {_fmt_bool(cfg.get('require_workers_comp'), 'Required', 'Not required')}",
        f"Employer's Liability required → {_fmt_bool(cfg.get('require_employers_liability'), 'Required', 'Not required')}",
        f"Employer's Liability minimum limit → {_fmt_dollars(cfg.get('employers_liability_minimum_limit'))}",
        f"Automobile Liability required → {_fmt_bool(cfg.get('require_auto_liability'), 'Required', 'Not required')}",
        f"Auto Liability minimum limit → {_fmt_dollars(cfg.get('auto_liability_minimum_limit'))}",
        f"Counterparty (not us) must be the obligated party → {_fmt_bool(cfg.get('require_counterparty_obligated'), 'Required', 'Not required')}",
        f"Additional insured required → {_fmt_bool(cfg.get('require_additional_insured'), 'Required', 'Not required')}",
        f"Waiver of subrogation required → {_fmt_bool(cfg.get('require_waiver_of_subrogation'), 'Required', 'Not required')}",
        f"Primary and non-contributory required → {_fmt_bool(cfg.get('require_primary_non_contributory'), 'Required', 'Not required')}",
        f"Certificate of insurance required → {_fmt_bool(cfg.get('require_certificate_of_insurance'), 'Required', 'Not required')}",
        f"Minimum insurer rating required → {_fmt_bool(cfg.get('require_minimum_insurer_rating'), 'Required', 'Not required')}",
        f"Notice of cancellation required → {_fmt_bool(cfg.get('require_notice_of_cancellation'), 'Required', 'Not required')}",
        f"Minimum cancellation notice → {_fmt_days(cfg.get('minimum_cancellation_notice_days'))}",
        f"Coverage must be maintained through the term → {_fmt_bool(cfg.get('require_policy_maintenance_through_term'), 'Required', 'Not required')}",
        f"Claims-made tail/extended reporting required → {_fmt_bool(cfg.get('require_claims_made_tail'), 'Required', 'Not required')}",
        f"Subcontractor coverage required → {_fmt_bool(cfg.get('require_subcontractor_coverage'), 'Required', 'Not required')}",
        f"Evidence of coverage before commencement required → {_fmt_bool(cfg.get('require_evidence_before_commencement'), 'Required', 'Not required')}",
    ]


_PAYMENT_TRIGGER_LABELS = {
    None: "Not yet decided", "invoice": "Invoice date", "receipt": "Receipt of goods/services",
    "acceptance": "Acceptance of deliverables", "milestone": "Milestone completion",
}

_WARRANTY_REMEDY_LABELS = {
    None: "Not yet decided", "repair_replace_reperform": "Repair, replace, or reperform",
    "refund_credit": "Refund or credit",
}


def _summarize_payment_terms(cfg: Dict[str, Any], field_statuses: Dict[str, str]) -> List[str]:
    trigger_value = cfg.get("required_payment_trigger")
    trigger_status = field_statuses.get("required_payment_trigger", "NOT_ESTABLISHED")
    trigger_label = "Not yet decided" if trigger_status != "ESTABLISHED" else _PAYMENT_TRIGGER_LABELS.get(trigger_value, trigger_value)
    return [
        f"Counterparty (not us) must be the payor → {_fmt_bool(cfg.get('require_counterparty_is_payor'), 'Required', 'Not required')}",
        f"Preferred payment period → {_fmt_days(cfg.get('preferred_net_days'))}",
        f"Acceptable maximum payment period → {_fmt_days(cfg.get('acceptable_max_net_days'))}",
        f"Required payment trigger → {trigger_label}",
        f"Undisputed amounts must remain payable → {_fmt_bool(cfg.get('require_undisputed_amounts_still_payable'), 'Required', 'Not required')}",
        f"Withholding of disputed amounts → {_fmt_bool(cfg.get('prohibit_disputed_amount_withholding'), 'Prohibited', 'Allowed')}",
        f"Minimum dispute-notice period → {_fmt_days(cfg.get('minimum_dispute_notice_days'))}",
        f"Set-off → {_fmt_bool(cfg.get('prohibit_set_off'), 'Prohibited', 'Allowed')}",
        f"Maximum permitted late-interest rate (annualized) → {cfg.get('maximum_late_interest_rate_percent'):g}%" if cfg.get('maximum_late_interest_rate_percent') is not None else "Maximum permitted late-interest rate (annualized) → Not yet decided",
        f"Unilateral price increases → {_fmt_bool(cfg.get('prohibit_unilateral_price_increase'), 'Prohibited', 'Allowed')}",
        f"Maximum permitted price-increase → {cfg.get('maximum_price_increase_percent'):g}%" if cfg.get('maximum_price_increase_percent') is not None else "Maximum permitted price-increase → Not yet decided",
        f"Minimum price-increase notice → {_fmt_days(cfg.get('minimum_price_increase_notice_days'))}",
        f"Expense pre-approval required → {_fmt_bool(cfg.get('require_expense_preapproval'), 'Required', 'Not required')}",
        f"Counterparty (not us) must bear tax responsibility → {_fmt_bool(cfg.get('require_tax_responsibility_counterparty'), 'Required', 'Not required')}",
        f"Required payment currency → {cfg.get('required_currency') or 'Not yet decided'}",
        f"Refund entitlement required → {_fmt_bool(cfg.get('require_refund_entitlement'), 'Required', 'Not required')}",
    ]


def _summarize_warranties(cfg: Dict[str, Any], field_statuses: Dict[str, str]) -> List[str]:
    remedy_value = cfg.get("required_remedy_type")
    remedy_status = field_statuses.get("required_remedy_type", "NOT_ESTABLISHED")
    remedy_label = "Not yet decided" if remedy_status != "ESTABLISHED" else _WARRANTY_REMEDY_LABELS.get(remedy_value, remedy_value)
    return [
        f"Required warranty categories (from counterparty) → {_fmt_list(cfg.get('required_warranty_categories_json'))}",
        f"Prohibited warranty categories (we must never give) → {_fmt_list(cfg.get('prohibited_warranty_categories_json'))}",
        f"Mutual warranties required → {_fmt_bool(cfg.get('require_mutual_warranties'), 'Required', 'Not required')}",
        f"Minimum warranty duration → {_fmt_days(cfg.get('minimum_warranty_duration_days'))}",
        f"\"AS IS\" disclaimer → {_fmt_bool(cfg.get('prohibit_as_is_disclaimer'), 'Prohibited', 'Allowed')}",
        f"Exclusive remedy language → {_fmt_bool(cfg.get('prohibit_exclusive_remedy'), 'Prohibited', 'Allowed')}",
        f"Required remedy type → {remedy_label}",
        f"Non-infringement warranty required → {_fmt_bool(cfg.get('require_non_infringement_warranty'), 'Required', 'Not required')}",
        f"Compliance-with-law warranty required → {_fmt_bool(cfg.get('require_compliance_with_law_warranty'), 'Required', 'Not required')}",
        f"Professional/workmanlike standard required → {_fmt_bool(cfg.get('require_professional_standard'), 'Required', 'Not required')}",
        f"Malware/malicious-code-free warranty required → {_fmt_bool(cfg.get('require_malware_free_warranty'), 'Required', 'Not required')}",
        f"Title warranty required → {_fmt_bool(cfg.get('require_title_warranty'), 'Required', 'Not required')}",
        f"Warranty survival required → {_fmt_bool(cfg.get('require_warranty_survival'), 'Required', 'Not required')}",
    ]


_SLA_SUPPORT_HOURS_LABELS = {
    None: "Not yet decided", "24x7": "24x7", "business_hours": "Business hours only",
}
_SLA_BASIS_LABELS = {None: "Not yet decided", "calendar": "Calendar", "business": "Business"}


def _summarize_sla(cfg: Dict[str, Any], field_statuses: Dict[str, str]) -> List[str]:
    support_value = cfg.get("required_support_hours")
    support_status = field_statuses.get("required_support_hours", "NOT_ESTABLISHED")
    support_label = "Not yet decided" if support_status != "ESTABLISHED" else _SLA_SUPPORT_HOURS_LABELS.get(support_value, support_value)

    lines = [
        f"Uptime commitment required → {_fmt_bool(cfg.get('require_uptime_commitment'), 'Required', 'Not required')}",
        f"Preferred uptime → {cfg.get('preferred_uptime_percent'):g}%" if cfg.get('preferred_uptime_percent') is not None else "Preferred uptime → Not yet decided",
        f"Minimum acceptable uptime → {cfg.get('minimum_acceptable_uptime_percent'):g}%" if cfg.get('minimum_acceptable_uptime_percent') is not None else "Minimum acceptable uptime → Not yet decided",
        f"Permitted maintenance exclusions → {_fmt_list(cfg.get('permitted_maintenance_exclusions_json'))}",
        f"Severity-tiered commitments required → {_fmt_bool(cfg.get('require_severity_tiers'), 'Required', 'Not required')}",
    ]
    for n in (1, 2, 3, 4):
        rh = cfg.get(f"p{n}_max_response_hours")
        rb = cfg.get(f"p{n}_response_basis")
        sh = cfg.get(f"p{n}_max_restoration_hours")
        sb = cfg.get(f"p{n}_restoration_basis")
        lines.append(
            f"P{n} max response → " + (f"{rh:g} hours ({_SLA_BASIS_LABELS.get(rb, rb)})" if rh is not None else "Not yet decided")
        )
        lines.append(
            f"P{n} max restoration → " + (f"{sh:g} hours ({_SLA_BASIS_LABELS.get(sb, sb)})" if sh is not None else "Not yet decided")
        )
    lines += [
        f"Required support hours → {support_label}",
        f"Service credits required → {_fmt_bool(cfg.get('require_service_credits'), 'Required', 'Not required')}",
        f"Minimum credit percentage of fees → {cfg.get('minimum_credit_percent_of_fees'):g}%" if cfg.get('minimum_credit_percent_of_fees') is not None else "Minimum credit percentage of fees → Not yet decided",
        f"Minimum credit cap → {cfg.get('minimum_credit_cap_percent_of_fees'):g}%" if cfg.get('minimum_credit_cap_percent_of_fees') is not None else "Minimum credit cap → Not yet decided",
        f"Chronic-failure remedy required → {_fmt_bool(cfg.get('require_chronic_failure_remedy'), 'Required', 'Not required')}",
        f"Termination right for chronic failure required → {_fmt_bool(cfg.get('require_termination_right_for_chronic_failure'), 'Required', 'Not required')}",
        f"Service credits as exclusive remedy → {_fmt_bool(cfg.get('prohibit_service_credits_as_exclusive_remedy'), 'Prohibited', 'Allowed')}",
        f"Minimum claim-submission window → {_fmt_days(cfg.get('minimum_claim_submission_days'))}",
    ]
    return lines


_SUMMARIZERS = {
    "limitation_of_liability": lambda cfg, statuses: _summarize_liability(cfg),
    "indemnification": lambda cfg, statuses: _summarize_indemnification(cfg),
    "termination": lambda cfg, statuses: _summarize_termination(cfg),
    "confidentiality": lambda cfg, statuses: _summarize_confidentiality(cfg),
    "assignment": lambda cfg, statuses: _summarize_assignment(cfg),
    "governing_law": lambda cfg, statuses: _summarize_governing_law(cfg, statuses),
    "data_security": lambda cfg, statuses: _summarize_data_security(cfg),
    "ip_ownership": lambda cfg, statuses: _summarize_ip_ownership(cfg),
    "insurance": lambda cfg, statuses: _summarize_insurance(cfg),
    "payment_terms": lambda cfg, statuses: _summarize_payment_terms(cfg, statuses),
    "warranties": lambda cfg, statuses: _summarize_warranties(cfg, statuses),
    "sla": lambda cfg, statuses: _summarize_sla(cfg, statuses),
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
    "payment_terms": {
        "require_counterparty_is_payor": "Counterparty (not us) must be the payor",
        "preferred_net_days": "Preferred payment period",
        "acceptable_max_net_days": "Acceptable maximum payment period",
        "required_payment_trigger": "Required payment trigger",
        "require_undisputed_amounts_still_payable": "Undisputed amounts must remain payable during a dispute",
        "prohibit_disputed_amount_withholding": "Never accept withholding of disputed amounts",
        "minimum_dispute_notice_days": "Minimum dispute-notice period",
        "prohibit_set_off": "Never accept set-off rights",
        "maximum_late_interest_rate_percent": "Maximum permitted late-interest rate (annualized)",
        "prohibit_unilateral_price_increase": "Never accept unilateral price increases",
        "maximum_price_increase_percent": "Maximum permitted price-increase",
        "minimum_price_increase_notice_days": "Minimum price-increase notice period",
        "require_expense_preapproval": "Require expense pre-approval",
        "require_tax_responsibility_counterparty": "Counterparty (not us) must bear tax responsibility",
        "required_currency": "Required payment currency",
        "require_refund_entitlement": "Require a refund entitlement",
    },
    "warranties": {
        "required_warranty_categories_json": "Required warranty categories (from counterparty)",
        "prohibited_warranty_categories_json": "Prohibited warranty categories (we must never give)",
        "require_mutual_warranties": "Require mutual warranties",
        "minimum_warranty_duration_days": "Minimum warranty duration",
        "prohibit_as_is_disclaimer": "Never accept an \"AS IS\" disclaimer",
        "prohibit_exclusive_remedy": "Never accept exclusive-remedy language",
        "required_remedy_type": "Required remedy type",
        "require_non_infringement_warranty": "Require a non-infringement warranty",
        "require_compliance_with_law_warranty": "Require a compliance-with-law warranty",
        "require_professional_standard": "Require a professional/workmanlike standard warranty",
        "require_malware_free_warranty": "Require a malware/malicious-code-free warranty",
        "require_title_warranty": "Require a title warranty",
        "require_warranty_survival": "Require the warranty to survive termination",
    },
    "sla": {
        "require_uptime_commitment": "Require an uptime/availability commitment",
        "preferred_uptime_percent": "Preferred uptime",
        "minimum_acceptable_uptime_percent": "Minimum acceptable uptime",
        "permitted_maintenance_exclusions_json": "Permitted maintenance exclusions",
        "require_severity_tiers": "Require severity-tiered response/restoration commitments",
        "p1_max_response_hours": "P1 maximum response time",
        "p1_response_basis": "P1 response time basis",
        "p1_max_restoration_hours": "P1 maximum restoration time",
        "p1_restoration_basis": "P1 restoration time basis",
        "p2_max_response_hours": "P2 maximum response time",
        "p2_response_basis": "P2 response time basis",
        "p2_max_restoration_hours": "P2 maximum restoration time",
        "p2_restoration_basis": "P2 restoration time basis",
        "p3_max_response_hours": "P3 maximum response time",
        "p3_response_basis": "P3 response time basis",
        "p3_max_restoration_hours": "P3 maximum restoration time",
        "p3_restoration_basis": "P3 restoration time basis",
        "p4_max_response_hours": "P4 maximum response time",
        "p4_response_basis": "P4 response time basis",
        "p4_max_restoration_hours": "P4 maximum restoration time",
        "p4_restoration_basis": "P4 restoration time basis",
        "required_support_hours": "Required support hours",
        "require_service_credits": "Require a service-credit remedy",
        "minimum_credit_percent_of_fees": "Minimum service-credit percentage of fees",
        "minimum_credit_cap_percent_of_fees": "Minimum service-credit cap",
        "require_chronic_failure_remedy": "Require a chronic/repeated-failure remedy",
        "require_termination_right_for_chronic_failure": "Require a termination right for chronic failure",
        "prohibit_service_credits_as_exclusive_remedy": "Never accept service credits as the exclusive remedy",
        "minimum_claim_submission_days": "Minimum claim-submission window",
    },
    "insurance": {
        "require_cgl": "Commercial General Liability required",
        "cgl_minimum_per_occurrence": "CGL minimum per-occurrence limit",
        "cgl_minimum_aggregate": "CGL minimum aggregate limit",
        "require_professional_liability": "Professional Liability / E&O required",
        "professional_liability_minimum_limit": "Professional Liability minimum limit",
        "require_cyber_liability": "Cyber Liability required",
        "cyber_liability_minimum_limit": "Cyber Liability minimum limit",
        "require_workers_comp": "Workers' Compensation required",
        "require_employers_liability": "Employer's Liability required",
        "employers_liability_minimum_limit": "Employer's Liability minimum limit",
        "require_auto_liability": "Automobile Liability required",
        "auto_liability_minimum_limit": "Auto Liability minimum limit",
        "require_counterparty_obligated": "Counterparty (not us) must be the obligated party",
        "require_additional_insured": "Require additional insured status",
        "require_waiver_of_subrogation": "Require a waiver of subrogation",
        "require_primary_non_contributory": "Require primary and non-contributory language",
        "require_certificate_of_insurance": "Require a certificate of insurance",
        "require_minimum_insurer_rating": "Require a minimum insurer rating (e.g. A.M. Best)",
        "require_notice_of_cancellation": "Require advance notice of cancellation",
        "minimum_cancellation_notice_days": "Minimum cancellation notice period",
        "require_policy_maintenance_through_term": "Require coverage to be maintained through the term",
        "require_claims_made_tail": "Require claims-made tail/extended reporting coverage",
        "require_subcontractor_coverage": "Require subcontractors to carry equivalent insurance",
        "require_evidence_before_commencement": "Require evidence of coverage before commencement",
    },
    "ip_ownership": {
        "require_we_retain_background_ip": "We retain ownership of our background/pre-existing IP",
        "require_we_own_work_product": "We own work product/deliverables",
        "prohibit_joint_ownership": "Never accept joint ownership",
        "require_license_for_embedded_background_ip": "Require a license to use background IP embedded in deliverables",
        "require_license_exclusive": "Require an exclusive license",
        "prohibit_royalty_bearing_license": "Never accept a royalty-bearing license (royalty-free required)",
        "require_perpetual_license": "Require a perpetual license",
        "prohibit_revocable_license": "Never accept a revocable license (irrevocable required)",
        "require_sublicensable": "Require sublicensing rights",
        "require_transferable": "Require transferability",
        "require_worldwide_territory": "Require a worldwide territory",
        "require_purpose_limited_license": "Require a purpose-limited (field-of-use restricted) license",
        "prohibit_derivative_works": "Never accept derivative-works rights",
        "require_feedback_assigned": "Require feedback to be assigned outright",
        "require_residual_knowledge_rights": "Require residual-knowledge rights",
        "require_open_source_disclosure": "Require open-source disclosure/obligations",
        "require_infringement_remedy_reference": "Require the clause to reference infringement/third-party IP treatment",
        "require_post_termination_survival": "Require the license to survive termination",
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
