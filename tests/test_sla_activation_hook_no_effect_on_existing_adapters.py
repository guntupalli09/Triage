"""
Regression tests proving the adapter-owned activation-validator hook
(playbook_authoring._ADAPTER_ACTIVATION_VALIDATORS, added for SLA per
docs/architecture/sla_adapter_design.md S3.3) has ZERO effect on the
eleven pre-existing adapters' activation behavior.

The hook is a purely additive extension point: validate_position_for_
activation() only consults _ADAPTER_ACTIVATION_VALIDATORS.get(clause_type)
after already running the unchanged mechanical ACTIVATION_REQUIRED_FIELDS
check, and only clause types that register a validator there get any
additional check appended. This file proves both halves of that claim:
(1) no clause type other than "sla" has a validator registered at all,
so the extra_validator branch can never execute for them; and (2) for a
representative activation scenario per pre-existing adapter, the outcome
(raises vs. does not raise, and which fields are reported missing) is
identical to what test_playbook_authoring_phase01.py already independently
established before this hook existed.
"""
import os

os.environ.setdefault("DEV_MODE", "true")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import playbook_authoring as pa
from database import Base
from models import Playbook, PolicyPosition, PolicyPositionField, User
import analytics_models  # noqa: F401


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sla_activation_hook_test.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def playbook(db_session):
    user = User(email="lawyer@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    pb = Playbook(user_id=user.id, name="Test Playbook", template_text="irrelevant for this suite")
    db_session.add(pb)
    db_session.flush()
    return pb


def _add_position(db_session, playbook, clause_type, *, status="ACTIVE", config=None, field_statuses=None):
    config = config or {}
    field_statuses = field_statuses or {}
    position = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status=status,
        contract_side="mutual", config_json=config, source_type="MANUAL",
    )
    db_session.add(position)
    db_session.flush()

    for field_name in pa.CLAUSE_TYPE_CONFIG_FIELDS[clause_type]:
        explicit_status = field_statuses.get(field_name)
        if explicit_status is not None:
            field_status = explicit_status
        elif field_name in config:
            field_status = "ESTABLISHED"
        else:
            field_status = "NOT_ESTABLISHED"
        db_session.add(PolicyPositionField(
            policy_position_id=position.id, field_name=field_name,
            value_json=config.get(field_name), source="MANUAL", status=field_status,
        ))
    db_session.flush()
    return position


_PRE_EXISTING_CLAUSE_TYPES = tuple(ct for ct in pa.CLAUSE_TYPES if ct != "sla")


def test_only_sla_has_an_activation_validator_registered():
    """The extension point itself: every pre-existing clause type must
    have no entry at all in _ADAPTER_ACTIVATION_VALIDATORS, so
    validate_position_for_activation's `if extra_validator:` branch can
    never execute for them -- this is the structural guarantee the rest
    of this file's behavioral tests corroborate."""
    for clause_type in _PRE_EXISTING_CLAUSE_TYPES:
        assert pa._ADAPTER_ACTIVATION_VALIDATORS.get(clause_type) is None, (
            f"{clause_type!r} unexpectedly has an activation validator registered"
        )
    assert "sla" in pa._ADAPTER_ACTIVATION_VALIDATORS


@pytest.mark.parametrize("clause_type,require_field", [
    ("limitation_of_liability", "require_consequential_damages_exclusion"),
    ("termination", "require_mutual_convenience_termination"),
    ("confidentiality", "require_mutual_confidentiality"),
    ("assignment", "require_consent_for_counterparty_assignment"),
    ("governing_law", "require_jury_trial_waiver"),
    ("data_security", "require_processor_role"),
    ("ip_ownership", "require_we_retain_background_ip"),
    ("insurance", "require_cgl"),
    ("payment_terms", "require_counterparty_is_payor"),
    ("warranties", "require_mutual_warranties"),
])
def test_blocks_activation_when_require_field_not_established_unchanged(db_session, playbook, clause_type, require_field):
    """Same scenario, same outcome as test_playbook_authoring_phase01.py's
    pre-hook version of this test: a missing require_* field still blocks
    activation with exactly that field name reported, for adapters that
    never register an activation validator."""
    position = _add_position(db_session, playbook, clause_type, status="NEEDS_REVIEW", config={})
    with pytest.raises(pa.PolicyActivationError) as exc:
        pa.validate_position_for_activation(position)
    assert require_field in exc.value.missing_fields


def test_indemnification_blocks_on_any_missing_require_field_unchanged(db_session, playbook):
    position = _add_position(
        db_session, playbook, "indemnification", status="NEEDS_REVIEW",
        config={"require_exposure_third_party_only": True},
        field_statuses={"require_exposure_third_party_only": "ESTABLISHED"},
    )
    with pytest.raises(pa.PolicyActivationError) as exc:
        pa.validate_position_for_activation(position)
    assert "require_defense_control_for_exposure" in exc.value.missing_fields
    assert "require_notice_and_cooperation_for_exposure" in exc.value.missing_fields
    assert "require_exposure_third_party_only" not in exc.value.missing_fields


@pytest.mark.parametrize("clause_type,require_field", [
    ("confidentiality", "require_mutual_confidentiality"),
    ("insurance", "require_cgl"),
    ("payment_terms", "require_counterparty_is_payor"),
    ("warranties", "require_mutual_warranties"),
])
def test_established_false_still_activates_fine_unchanged(db_session, playbook, clause_type, require_field):
    """A require_* field explicitly set to False and ESTABLISHED must
    still activate cleanly for every pre-existing adapter -- the hook
    must never turn a previously-clean activation into a blocked one.
    Sets EVERY required field for the clause type (not just the one
    named in the parametrization) since several adapters have more than
    one required field and the mechanical check independently demands
    all of them regardless of this hook."""
    config = {f: False for f in pa.ACTIVATION_REQUIRED_FIELDS[clause_type]}
    field_statuses = {f: "ESTABLISHED" for f in pa.ACTIVATION_REQUIRED_FIELDS[clause_type]}
    assert require_field in config  # sanity: the named field really is one of this clause type's required fields
    position = _add_position(
        db_session, playbook, clause_type, status="NEEDS_REVIEW",
        config=config, field_statuses=field_statuses,
    )
    pa.validate_position_for_activation(position)  # must not raise


def test_full_valid_position_still_activates_for_every_pre_existing_adapter(db_session, playbook):
    """Builds a fully-ESTABLISHED (all require_* fields set) position for
    every pre-existing clause type and confirms activation still succeeds
    with no exception -- the broadest possible proof that the hook adds
    no new failure mode for adapters that never registered one."""
    for clause_type in _PRE_EXISTING_CLAUSE_TYPES:
        config = {f: False for f in pa.ACTIVATION_REQUIRED_FIELDS[clause_type]}
        field_statuses = {f: "ESTABLISHED" for f in pa.ACTIVATION_REQUIRED_FIELDS[clause_type]}
        position = _add_position(
            db_session, playbook, clause_type, status="NEEDS_REVIEW",
            config=config, field_statuses=field_statuses,
        )
        pa.validate_position_for_activation(position)  # must not raise, for every one of these


# ---------------------------------------------------------------------------
# Positive confirmation: the SLA hook DOES fire when it should, proving the
# hook is a real, working extension point and not an inert no-op.
# ---------------------------------------------------------------------------

def test_sla_hook_blocks_severity_tiers_required_with_no_targets_configured(db_session, playbook):
    position = _add_position(
        db_session, playbook, "sla", status="NEEDS_REVIEW",
        config={"require_severity_tiers": True},
        field_statuses={"require_severity_tiers": "ESTABLISHED"},
    )
    with pytest.raises(pa.PolicyActivationError) as exc:
        pa.validate_position_for_activation(position)
    assert any("require_severity_tiers" in m for m in exc.value.missing_fields)


def test_sla_hook_blocks_response_hours_without_basis(db_session, playbook):
    position = _add_position(
        db_session, playbook, "sla", status="NEEDS_REVIEW",
        config={"p1_max_response_hours": 2.0},
        field_statuses={"p1_max_response_hours": "ESTABLISHED"},
    )
    with pytest.raises(pa.PolicyActivationError) as exc:
        pa.validate_position_for_activation(position)
    assert any("p1_max_response_hours" in m and "p1_response_basis" in m for m in exc.value.missing_fields)


def test_sla_hook_blocks_service_credits_required_without_parameters(db_session, playbook):
    position = _add_position(
        db_session, playbook, "sla", status="NEEDS_REVIEW",
        config={"require_service_credits": True},
        field_statuses={"require_service_credits": "ESTABLISHED"},
    )
    with pytest.raises(pa.PolicyActivationError) as exc:
        pa.validate_position_for_activation(position)
    assert any("require_service_credits" in m for m in exc.value.missing_fields)


def test_sla_hook_allows_fully_configured_severity_tier_position(db_session, playbook):
    """Every mechanically-required sla field (all require_* fields, per
    the ACTIVATION_REQUIRED_FIELDS auto-derivation) must be established,
    not just require_severity_tiers, or the pre-existing mechanical check
    blocks activation for reasons unrelated to this hook."""
    config = {f: False for f in pa.ACTIVATION_REQUIRED_FIELDS["sla"]}
    config.update({
        "require_severity_tiers": True,
        "p1_max_response_hours": 2.0, "p1_response_basis": "calendar",
        "p1_max_restoration_hours": 8.0, "p1_restoration_basis": "calendar",
    })
    position = _add_position(
        db_session, playbook, "sla", status="NEEDS_REVIEW",
        config=config, field_statuses={k: "ESTABLISHED" for k in config},
    )
    pa.validate_position_for_activation(position)  # must not raise
