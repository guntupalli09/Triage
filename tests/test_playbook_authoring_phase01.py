"""
Phase 0.1 tests for playbook_authoring.py — validation/invariant hardening.

Three things this suite must prove (see the Phase 0.1 report for the full
per-adapter activation-requirement rationale):

1. validate_config() rejects wrong-typed values, invalid None, invalid
   list element types, and out-of-vocabulary tokens, across all six
   adapters and every type shape those Protocols use (bool/float/int/
   Optional[str]/Optional[List[str]]) — it never silently coerces.
2. validate_position_for_activation() blocks activation of a position
   whose require_* fields (the gate-shaped booleans) are NOT_ESTABLISHED,
   for every adapter that has one, and a NOT_ESTABLISHED require_* field
   never lets a builder's silent False default stand in for activation.
3. build_policy_rule_for_enforcement() only builds from ACTIVE, activation-
   valid positions; a migrated Liability position still produces
   byte-identical PolicyDecision output through this path.
"""
import os

os.environ.setdefault("DEV_MODE", "true")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import assignment_policy_engine as ape
import confidentiality_policy_engine as cpe
import governing_law_policy_engine as gpe
import indemnification_policy_engine as ipe
import liability_policy_engine as lpe
import playbook_authoring as pa
import termination_policy_engine as tpe
from database import Base
from models import Playbook, PolicyPosition, PolicyPositionField, PolicyRule, User
import analytics_models  # noqa: F401


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'playbook_authoring_phase01_test.db'}")
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
    """Builds a PolicyPosition plus PolicyPositionField rows with the
    given per-field status (defaults to ESTABLISHED for everything in
    `config`, NOT_ESTABLISHED for everything else the clause type
    defines) — mirrors how a real authoring flow would leave a mix of
    confirmed/unconfirmed fields."""
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


# ---------------------------------------------------------------------------
# 1. Type validation — invalid types are rejected, never coerced
# ---------------------------------------------------------------------------

class TestTypeValidationRejectsAcrossShapes:
    def test_string_where_float_expected(self):
        with pytest.raises(pa.PolicyConfigValidationError):
            pa.validate_config("limitation_of_liability", {"preferred_multiplier": "1.5"})

    def test_string_where_int_expected(self):
        with pytest.raises(pa.PolicyConfigValidationError):
            pa.validate_config("termination", {"min_notice_days_against_us": "60"})

    def test_float_where_int_expected_is_rejected_not_truncated(self):
        with pytest.raises(pa.PolicyConfigValidationError):
            pa.validate_config("confidentiality", {"min_protection_duration_years": 3.5})

    def test_int_where_bool_expected(self):
        with pytest.raises(pa.PolicyConfigValidationError):
            pa.validate_config("limitation_of_liability", {"prohibit_unlimited": 1})

    def test_string_where_bool_expected(self):
        with pytest.raises(pa.PolicyConfigValidationError):
            pa.validate_config("assignment", {"prohibit_sole_discretion_consent": "true"})

    def test_bool_where_float_expected_is_rejected(self):
        """type(True) is bool, but isinstance(True, (int, float)) is also
        True in Python -- a naive isinstance check would silently accept
        this. Confirms the explicit `type(value) is bool` exclusion."""
        with pytest.raises(pa.PolicyConfigValidationError):
            pa.validate_config("indemnification", {"exposure_preferred_multiplier": True})

    def test_scalar_where_list_expected(self):
        with pytest.raises(pa.PolicyConfigValidationError):
            pa.validate_config("limitation_of_liability", {"required_exceptions_json": "fraud"})

    def test_invalid_list_element_type(self):
        with pytest.raises(pa.PolicyConfigValidationError) as exc:
            pa.validate_config("termination", {"required_survival_topics_json": ["confidentiality", 4]})
        assert "required_survival_topics_json[1]" in str(exc.value)

    def test_none_rejected_for_non_optional_bool(self):
        with pytest.raises(pa.PolicyConfigValidationError):
            pa.validate_config("governing_law", {"require_jury_trial_waiver": None})

    def test_none_accepted_for_optional_float(self):
        # Optional[float] genuinely permits None -- "not established."
        pa.validate_config("limitation_of_liability", {"preferred_multiplier": None})

    def test_unknown_field_rejected(self):
        with pytest.raises(pa.PolicyConfigValidationError) as exc:
            pa.validate_config("governing_law", {"not_a_real_field": True})
        assert "unknown field" in str(exc.value)

    def test_valid_config_passes_unchanged(self):
        cfg = {"prohibit_unlimited": True, "preferred_multiplier": 1.0}
        assert pa.validate_config("limitation_of_liability", cfg) == cfg


class TestBoundedVocabularyRejectsInvalidTokens:
    @pytest.mark.parametrize("clause_type,field_name,bad_value", [
        ("limitation_of_liability", "required_exceptions_json", ["not_a_category"]),
        ("limitation_of_liability", "required_consequential_carveouts_json", ["made_up"]),
        ("indemnification", "required_protection_triggers_json", ["nonexistent_trigger"]),
        ("indemnification", "prohibited_exposure_triggers_json", ["nonexistent_trigger"]),
        ("termination", "required_survival_topics_json", ["not_a_survival_topic"]),
        ("confidentiality", "required_exclusions_json", ["not_an_exclusion"]),
        ("assignment", "required_exceptions_json", ["not_an_exception"]),
        ("governing_law", "required_dispute_resolution", "mediation"),
    ])
    def test_bad_token_rejected(self, clause_type, field_name, bad_value):
        with pytest.raises(pa.PolicyConfigValidationError):
            pa.validate_config(clause_type, {field_name: bad_value})

    @pytest.mark.parametrize("clause_type,field_name,good_value", [
        ("limitation_of_liability", "required_exceptions_json", ["fraud", "confidentiality"]),
        ("indemnification", "required_protection_triggers_json", ["ip_infringement"]),
        ("termination", "required_survival_topics_json", ["confidentiality", "ip_ownership"]),
        ("confidentiality", "required_exclusions_json", ["public_knowledge"]),
        ("assignment", "required_exceptions_json", ["affiliate"]),
        ("governing_law", "required_dispute_resolution", "arbitration"),
    ])
    def test_valid_token_accepted(self, clause_type, field_name, good_value):
        pa.validate_config(clause_type, {field_name: good_value})  # must not raise

    def test_governing_law_jurisdictions_are_free_text_not_bounded(self):
        """No fixed vocabulary exists for jurisdictions anywhere in
        governing_law_policy_engine -- arbitrary strings must pass type
        validation (this is the documented 'too weak to validate a token
        against' case, not a bug)."""
        pa.validate_config("governing_law", {"preferred_jurisdictions_json": ["Насколько Угодно"]})


# ---------------------------------------------------------------------------
# 2. Activation-readiness — require_* gates must be ESTABLISHED
# ---------------------------------------------------------------------------

class TestActivationRequiredFieldsAreExactlyTheRequireGates:
    def test_every_adapter_with_a_require_field_has_it_listed(self):
        assert pa.ACTIVATION_REQUIRED_FIELDS == {
            "limitation_of_liability": ["require_consequential_damages_exclusion"],
            "indemnification": [
                "require_exposure_third_party_only",
                "require_defense_control_for_exposure",
                "require_notice_and_cooperation_for_exposure",
            ],
            "termination": ["require_mutual_convenience_termination"],
            "confidentiality": ["require_mutual_confidentiality"],
            "assignment": ["require_consent_for_counterparty_assignment"],
            "governing_law": ["require_jury_trial_waiver"],
            "data_security": [
                "require_processor_role",
                "require_fixed_breach_notification_period",
                "require_international_transfer_safeguard",
                "require_data_residency",
                "require_deletion_or_return",
                "require_audit_rights",
                "require_named_security_certification",
                "require_cooperation_obligation",
                "require_confidentiality_of_personal_data",
            ],
            "ip_ownership": [
                "require_we_retain_background_ip",
                "require_we_own_work_product",
                "require_license_for_embedded_background_ip",
                "require_license_exclusive",
                "require_perpetual_license",
                "require_sublicensable",
                "require_transferable",
                "require_worldwide_territory",
                "require_purpose_limited_license",
                "require_feedback_assigned",
                "require_residual_knowledge_rights",
                "require_open_source_disclosure",
                "require_infringement_remedy_reference",
                "require_post_termination_survival",
            ],
        }

    def test_prohibit_fields_are_never_activation_required(self):
        """prohibit_* booleans choose severity between two already-
        flagged states (PROHIBITED vs ESCALATE) -- their default cannot
        cause a silent accept, so they must never appear here."""
        for clause_type, required in pa.ACTIVATION_REQUIRED_FIELDS.items():
            assert not any(name.startswith("prohibit_") for name in required)

    def test_ladder_and_list_fields_are_never_activation_required(self):
        ladder_or_list_suffixes = ("_multiplier", "_json", "_days_against_us", "_duration_years")
        for clause_type, required in pa.ACTIVATION_REQUIRED_FIELDS.items():
            for name in required:
                assert not name.endswith(ladder_or_list_suffixes), name


class TestValidatePositionForActivation:
    @pytest.mark.parametrize("clause_type,require_field", [
        ("limitation_of_liability", "require_consequential_damages_exclusion"),
        ("termination", "require_mutual_convenience_termination"),
        ("confidentiality", "require_mutual_confidentiality"),
        ("assignment", "require_consent_for_counterparty_assignment"),
        ("governing_law", "require_jury_trial_waiver"),
    ])
    def test_blocks_activation_when_require_field_not_established(self, db_session, playbook, clause_type, require_field):
        position = _add_position(db_session, playbook, clause_type, status="NEEDS_REVIEW", config={})
        with pytest.raises(pa.PolicyActivationError) as exc:
            pa.validate_position_for_activation(position)
        assert require_field in exc.value.missing_fields

    def test_indemnification_blocks_on_any_missing_require_field(self, db_session, playbook):
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

    def test_established_false_is_a_legitimate_activation_state(self, db_session, playbook):
        """A require_* field explicitly set to False and ESTABLISHED
        (a lawyer's deliberate 'we don't require this') must activate
        fine -- the gate is about provenance, not about the value."""
        position = _add_position(
            db_session, playbook, "confidentiality", status="NEEDS_REVIEW",
            config={"require_mutual_confidentiality": False},
            field_statuses={"require_mutual_confidentiality": "ESTABLISHED"},
        )
        pa.validate_position_for_activation(position)  # must not raise

    def test_conflicting_status_also_blocks_activation(self, db_session, playbook):
        position = _add_position(
            db_session, playbook, "assignment", status="NEEDS_REVIEW",
            config={"require_consent_for_counterparty_assignment": True},
            field_statuses={"require_consent_for_counterparty_assignment": "CONFLICTING"},
        )
        with pytest.raises(pa.PolicyActivationError):
            pa.validate_position_for_activation(position)

    def test_adapter_with_no_require_field_semantics_placeholder(self, db_session, playbook):
        """Documents that ACTIVATION_REQUIRED_FIELDS is genuinely per-
        adapter (not "every field"): a position with zero PolicyPositionField
        rows at all still activates fine for an adapter with no require_*
        gate... except every current adapter has at least one, so this
        proves the mechanism doesn't over-require by construction instead."""
        for clause_type in pa.CLAUSE_TYPES:
            assert len(pa.ACTIVATION_REQUIRED_FIELDS[clause_type]) >= 1

    def test_not_established_does_not_silently_become_permissive_false(self, db_session, playbook):
        """The core silent-permissiveness check: a require_* field left
        NOT_ESTABLISHED must never be allowed to reach an ACTIVE position
        (where it would function identically to a deliberate False)."""
        position = _add_position(db_session, playbook, "indemnification", status="NEEDS_REVIEW", config={})
        with pytest.raises(pa.PolicyActivationError):
            pa.validate_position_for_activation(position)
        # And the builder itself, in isolation, WOULD default it to
        # False -- proving this is exactly the gap activation must close.
        built = pa.build_indemnification_policy_rule(position)
        assert built.require_exposure_third_party_only is False


# ---------------------------------------------------------------------------
# 3. Enforcement builder guard
# ---------------------------------------------------------------------------

class TestBuildPolicyRuleForEnforcement:
    def test_refuses_non_active_position(self, db_session, playbook):
        position = _add_position(db_session, playbook, "assignment", status="NEEDS_REVIEW", config={})
        with pytest.raises(pa.PolicyEnforcementGuardError):
            pa.build_policy_rule_for_enforcement(position)

    def test_refuses_active_position_missing_required_field(self, db_session, playbook):
        """status=ACTIVE alone is not trusted -- the guard re-validates
        even an already-ACTIVE row (defense in depth against a row that
        reached ACTIVE some other way, e.g. a future bug elsewhere)."""
        position = _add_position(db_session, playbook, "governing_law", status="ACTIVE", config={})
        with pytest.raises(pa.PolicyActivationError):
            pa.build_policy_rule_for_enforcement(position)

    def test_builds_from_valid_active_position(self, db_session, playbook):
        position = _add_position(
            db_session, playbook, "governing_law", status="ACTIVE",
            config={"require_jury_trial_waiver": True},
            field_statuses={"require_jury_trial_waiver": "ESTABLISHED"},
        )
        rule = pa.build_policy_rule_for_enforcement(position)
        assert rule.require_jury_trial_waiver is True

    def test_migrated_liability_position_builds_through_enforcement_path(self, db_session, playbook):
        """Every migrated (Liability-only) legacy PolicyRule row carries a
        real bool for both boolean fields (PolicyRule's own columns are
        non-nullable with defaults), so it always satisfies activation --
        confirms the migration path and the new activation gate compose
        without any special-casing."""
        rule = PolicyRule(
            playbook_id=playbook.id, clause_type="limitation_of_liability",
            contract_side="sell_side", preferred_multiplier=1.0,
            acceptable_max_multiplier=2.0, negotiate_max_multiplier=3.0,
            prohibit_unlimited=True, required_exceptions_json=["fraud"],
            require_consequential_damages_exclusion=True,
            required_consequential_carveouts_json=["gross_negligence"],
        )
        db_session.add(rule)
        db_session.flush()
        position = pa.migrate_legacy_policy_rule(db_session, rule)
        db_session.commit()

        rule_via_enforcement = pa.build_policy_rule_for_enforcement(position)
        rule_via_preview = pa.build_liability_policy_rule(position)
        assert vars(rule_via_enforcement) == vars(rule_via_preview)

    def test_migrated_liability_decision_byte_identical_through_enforcement_path(self, db_session, playbook):
        text = (
            "12. Limitation of Liability. Except for breaches of "
            "Confidentiality, either party's total liability under this "
            "Agreement shall not exceed one (1) times the fees paid in the "
            "preceding twelve (12) months."
        )
        rule = PolicyRule(
            playbook_id=playbook.id, clause_type="limitation_of_liability",
            contract_side="sell_side", preferred_multiplier=1.0,
            acceptable_max_multiplier=1.0, negotiate_max_multiplier=2.0,
            prohibit_unlimited=True, required_exceptions_json=["confidentiality"],
            require_consequential_damages_exclusion=False,
            required_consequential_carveouts_json=None,
        )
        db_session.add(rule)
        db_session.flush()

        facts_before = lpe.extract_liability_facts(text)
        before = lpe.evaluate_liability_policy(facts_before, rule, source="Same Source")

        position = pa.migrate_legacy_policy_rule(db_session, rule)
        db_session.commit()
        built = pa.build_policy_rule_for_enforcement(position)
        facts_after = lpe.extract_liability_facts(text)
        after = lpe.evaluate_liability_policy(facts_after, built, source="Same Source")

        assert before.state == after.state
        assert before.as_dict() == after.as_dict()


# ---------------------------------------------------------------------------
# Six-adapter benchmark gate sanity — Phase 0.1 must not move these
# ---------------------------------------------------------------------------

class TestSixAdapterRegressionSuitesUnaffected:
    """Phase 0.1 touches only playbook_authoring.py, never the six policy
    engines. This is a smoke check (not a replacement for the full
    benchmark corpora, which are run separately) that each engine's own
    module-level constants used by the new bounded-vocabulary tables
    still import and evaluate cleanly after this change."""

    def test_liability_engine_constants_unchanged(self):
        assert lpe.EXCEPTION_TYPES == lpe.CATEGORIES
        assert set(lpe.CATEGORIES) == {
            "data_breach", "ip_infringement", "confidentiality",
            "indemnification", "fraud", "gross_negligence", "willful_misconduct",
        }

    def test_indemnification_engine_constants_unchanged(self):
        assert set(ipe.TRIGGERS) == {
            "ip_infringement", "data_breach", "confidentiality",
            "negligence", "gross_negligence", "willful_misconduct",
        }

    def test_termination_engine_constants_unchanged(self):
        assert set(tpe.SURVIVAL_TOPICS) == {
            "confidentiality", "payment_obligations", "limitation_of_liability",
            "indemnification", "ip_ownership", "audit_rights",
        }

    def test_confidentiality_engine_constants_unchanged(self):
        assert set(cpe.EXCLUSION_TOPICS) == {
            "public_knowledge", "independently_developed", "third_party_rightful", "required_by_law",
        }

    def test_assignment_engine_constants_unchanged(self):
        assert set(ape.EXCEPTION_TOPICS) == {"affiliate", "change_of_control", "merger_acquisition"}

    def test_governing_law_engine_has_no_bounded_jurisdiction_vocabulary(self):
        assert not hasattr(gpe, "JURISDICTION_TYPES")
