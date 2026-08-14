"""
Phase 0 tests for playbook_authoring.py — pure plumbing, no routes/UI.

Two things this suite must prove (docs/architecture/playbook_authoring_ux_
design.md Phase 0 scope):

1. Each build_*_policy_rule() function converts a PolicyPosition into an
   object exposing exactly its engine's *PolicyRuleLike Protocol fields,
   with correct defaulting/validation.
2. migrate_legacy_policy_rule() converts an existing PolicyRule row into a
   PolicyPosition whose builder output is byte-identical, field for field,
   to what the original PolicyRule row itself would have provided to
   evaluate_liability_policy() — i.e. the migration is a genuinely
   behavior-preserving representation change, not a reinterpretation.
"""
import os

os.environ.setdefault("DEV_MODE", "true")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import liability_policy_engine as lpe
import playbook_authoring as pa
from database import Base
from models import Playbook, PolicyPosition, PolicyPositionField, PolicyRule, User
import analytics_models  # noqa: F401 -- registers analytics tables on the shared Base


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'playbook_authoring_test.db'}")
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


# ---------------------------------------------------------------------------
# Schema derivation
# ---------------------------------------------------------------------------

class TestConfigFieldSchema:
    def test_all_twelve_clause_types_present(self):
        assert set(pa.CLAUSE_TYPES) == {
            "limitation_of_liability", "indemnification", "termination",
            "confidentiality", "assignment", "governing_law", "data_security",
            "ip_ownership", "insurance", "payment_terms", "warranties", "sla",
        }

    def test_shared_fields_excluded_from_config_schema(self):
        for clause_type, fields in pa.CLAUSE_TYPE_CONFIG_FIELDS.items():
            assert "contract_side" not in fields
            assert "escalation_approval_authority" not in fields
            assert "fallback_text" not in fields

    def test_liability_config_fields_match_protocol(self):
        assert set(pa.CLAUSE_TYPE_CONFIG_FIELDS["limitation_of_liability"]) == {
            "preferred_multiplier", "acceptable_max_multiplier", "negotiate_max_multiplier",
            "prohibit_unlimited", "required_exceptions_json",
            "require_consequential_damages_exclusion", "required_consequential_carveouts_json",
        }

    def test_governing_law_config_fields_match_protocol(self):
        assert set(pa.CLAUSE_TYPE_CONFIG_FIELDS["governing_law"]) == {
            "preferred_jurisdictions_json", "acceptable_jurisdictions_json",
            "prohibited_jurisdictions_json", "required_dispute_resolution",
            "require_jury_trial_waiver",
        }

    def test_validate_config_rejects_unknown_field(self):
        with pytest.raises(ValueError):
            pa.validate_config("governing_law", {"not_a_real_field": True})

    def test_validate_config_accepts_none(self):
        assert pa.validate_config("governing_law", None) == {}


# ---------------------------------------------------------------------------
# Builders — defaulting and validation
# ---------------------------------------------------------------------------

class TestBuilders:
    def test_build_liability_policy_rule_defaults_missing_fields(self, db_session, playbook):
        position = PolicyPosition(
            playbook_id=playbook.id, clause_type="limitation_of_liability",
            contract_side="mutual", config_json={},
        )
        rule = pa.build_liability_policy_rule(position)
        # bool -> False, everything else -> None, per _default_for's
        # documented "least-restrictive, never a guess" rule.
        assert rule.prohibit_unlimited is False
        assert rule.require_consequential_damages_exclusion is False
        assert rule.preferred_multiplier is None
        assert rule.required_exceptions_json is None
        assert rule.contract_side == "mutual"

    def test_build_liability_policy_rule_uses_established_config(self, db_session, playbook):
        position = PolicyPosition(
            playbook_id=playbook.id, clause_type="limitation_of_liability",
            contract_side="sell_side", escalation_approval_authority="Legal Director",
            fallback_text="Approved fallback.",
            config_json={
                "preferred_multiplier": 1.0, "acceptable_max_multiplier": 2.0,
                "negotiate_max_multiplier": 3.0, "prohibit_unlimited": True,
                "required_exceptions_json": ["fraud"],
                "require_consequential_damages_exclusion": False,
                "required_consequential_carveouts_json": None,
            },
        )
        rule = pa.build_liability_policy_rule(position)
        assert rule.preferred_multiplier == 1.0
        assert rule.acceptable_max_multiplier == 2.0
        assert rule.negotiate_max_multiplier == 3.0
        assert rule.prohibit_unlimited is True
        assert rule.required_exceptions_json == ["fraud"]
        assert rule.escalation_approval_authority == "Legal Director"
        assert rule.fallback_text == "Approved fallback."

    def test_build_rejects_mismatched_clause_type(self, db_session, playbook):
        position = PolicyPosition(playbook_id=playbook.id, clause_type="assignment", config_json={})
        with pytest.raises(ValueError):
            pa.build_liability_policy_rule(position)

    @pytest.mark.parametrize("clause_type,builder", list(pa.BUILDERS.items()))
    def test_every_builder_produces_all_protocol_fields(self, db_session, playbook, clause_type, builder):
        position = PolicyPosition(playbook_id=playbook.id, clause_type=clause_type, config_json={})
        rule = builder(position)
        protocol_cls = pa._ENGINE_PROTOCOLS[clause_type]
        for field_name in pa._config_field_names(clause_type):
            assert hasattr(rule, field_name), f"{clause_type}: missing {field_name}"
        for shared in ("contract_side", "escalation_approval_authority", "fallback_text"):
            assert hasattr(rule, shared)


# ---------------------------------------------------------------------------
# Legacy migration — byte-identical builder output vs. the original PolicyRule
# ---------------------------------------------------------------------------

class TestLegacyMigration:
    def _make_policy_rule(self, db_session, playbook, **overrides):
        defaults = dict(
            playbook_id=playbook.id, clause_type="limitation_of_liability",
            contract_side="sell_side", preferred_multiplier=1.0,
            acceptable_max_multiplier=2.0, negotiate_max_multiplier=3.0,
            prohibit_unlimited=True, required_exceptions_json=["fraud", "confidentiality"],
            fallback_text="Approved fallback: liability capped at 1x annual fees.",
            escalation_approval_authority="Legal Director",
            require_consequential_damages_exclusion=True,
            required_consequential_carveouts_json=["gross_negligence"],
        )
        defaults.update(overrides)
        rule = PolicyRule(**defaults)
        db_session.add(rule)
        db_session.flush()
        return rule

    def test_migration_writes_active_position(self, db_session, playbook):
        rule = self._make_policy_rule(db_session, playbook)
        position = pa.migrate_legacy_policy_rule(db_session, rule)
        db_session.commit()

        assert position.status == "ACTIVE"
        assert position.source_type == "MANUAL"
        assert position.clause_type == "limitation_of_liability"
        assert position.playbook_id == playbook.id
        assert position.activated_at == rule.updated_at

    def test_migration_writes_one_field_row_per_field_all_manual(self, db_session, playbook):
        rule = self._make_policy_rule(db_session, playbook)
        position = pa.migrate_legacy_policy_rule(db_session, rule)
        db_session.commit()

        fields = db_session.query(PolicyPositionField).filter(
            PolicyPositionField.policy_position_id == position.id,
        ).all()
        field_names = {f.field_name for f in fields}
        assert field_names == {
            "preferred_multiplier", "acceptable_max_multiplier", "negotiate_max_multiplier",
            "prohibit_unlimited", "required_exceptions_json",
            "require_consequential_damages_exclusion", "required_consequential_carveouts_json",
            "contract_side", "escalation_approval_authority", "fallback_text",
        }
        assert all(f.source == "MANUAL" for f in fields)
        assert all(f.confirmed_at == rule.updated_at for f in fields)
        assert all(f.confirmed_by_user_id is None for f in fields)

    def test_migration_is_idempotent(self, db_session, playbook):
        rule = self._make_policy_rule(db_session, playbook)
        first = pa.migrate_legacy_policy_rule(db_session, rule)
        db_session.commit()
        second = pa.migrate_legacy_policy_rule(db_session, rule)
        db_session.commit()
        assert first.id == second.id
        assert db_session.query(PolicyPosition).filter(
            PolicyPosition.playbook_id == playbook.id, PolicyPosition.clause_type == rule.clause_type,
        ).count() == 1

    def test_migrated_builder_output_matches_original_policy_rule_fields(self, db_session, playbook):
        """The core behavior-preservation claim: every field
        evaluate_liability_policy() reads from a PolicyRuleLike must carry
        the same value whether it came from the original PolicyRule row
        directly, or from build_liability_policy_rule(migrated position)."""
        rule = self._make_policy_rule(db_session, playbook)
        position = pa.migrate_legacy_policy_rule(db_session, rule)
        db_session.commit()

        built = pa.build_liability_policy_rule(position)

        protocol_fields = list(pa._config_field_names("limitation_of_liability")) + [
            "contract_side", "escalation_approval_authority", "fallback_text",
        ]
        for field_name in protocol_fields:
            assert getattr(built, field_name) == getattr(rule, field_name), field_name

    def test_migrated_position_decision_matches_pre_migration_decision(self, db_session, playbook):
        """End-to-end: run evaluate_liability_policy() against the raw
        PolicyRule row, then against build_liability_policy_rule() of the
        migrated PolicyPosition, over the same contract text. Both must
        produce the same decision_state and controlling values -- this is
        the golden-snapshot-style check for the migration path itself."""
        text = (
            "12. Limitation of Liability. Except for breaches of "
            "Confidentiality, either party's total liability under this "
            "Agreement shall not exceed one (1) times the fees paid in the "
            "preceding twelve (12) months."
        )
        rule = self._make_policy_rule(
            db_session, playbook,
            preferred_multiplier=1.0, acceptable_max_multiplier=1.0, negotiate_max_multiplier=2.0,
            required_exceptions_json=["confidentiality"],
            require_consequential_damages_exclusion=False, required_consequential_carveouts_json=None,
        )
        facts = lpe.extract_liability_facts(text)
        before = lpe.evaluate_liability_policy(facts, rule, source="Same Source")

        position = pa.migrate_legacy_policy_rule(db_session, rule)
        db_session.commit()
        built = pa.build_liability_policy_rule(position)
        facts_after = lpe.extract_liability_facts(text)  # re-extract: facts must not be mutated by evaluate()
        after = lpe.evaluate_liability_policy(facts_after, built, source="Same Source")

        assert before.state == after.state
        assert before.as_dict() == after.as_dict()

    def test_migration_rejects_non_liability_clause_type(self, db_session, playbook):
        rule = self._make_policy_rule(db_session, playbook, clause_type="indemnification")
        with pytest.raises(ValueError):
            pa.migrate_legacy_policy_rule(db_session, rule)


class TestMigrateAll:
    def test_migrate_all_processes_every_rule(self, db_session, playbook):
        rule = PolicyRule(
            playbook_id=playbook.id, clause_type="limitation_of_liability",
            contract_side="mutual", prohibit_unlimited=True,
        )
        db_session.add(rule)
        db_session.commit()

        positions = pa.migrate_all_legacy_policy_rules(db_session)
        assert len(positions) == 1
        assert positions[0].status == "ACTIVE"
