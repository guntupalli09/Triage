"""End-to-end: v2 LoL policy activation, cutover enforcement, and v1 unchanged."""

import os
import uuid

os.environ.setdefault("DEV_MODE", "true")

import pytest

import playbook_authoring as pa
import policy_enforcement as pe
from database import SessionLocal, init_db
from models import Playbook, PolicyPosition, PolicyPositionField, User
from tests.fixtures.liability_policy_v2_golden import FIRM_A, firm_a_policy


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema():
    init_db()


def _user(db) -> User:
    user = User(email=f"v2-{uuid.uuid4().hex}@test.com", password_hash="x", name="Test")
    db.add(user)
    db.flush()
    return user


def _playbook(db, user_id) -> Playbook:
    pb = Playbook(user_id=user_id, name="V2 Enforcement Playbook", template_text="x")
    db.add(pb)
    db.flush()
    return pb


CONTRACT_5X_ANNUAL = (
    "12. Limitation of Liability. In no event shall either party's aggregate liability under this "
    "Agreement exceed 5 times the total annual fees paid in the twelve (12) months preceding the claim."
)

CONTRACT_12MO_FEES = (
    "12. Limitation of Liability. Provider's aggregate liability shall not exceed fees paid or payable "
    "during the twelve (12) months preceding the claim."
)

CONTRACT_3MO_FEES = (
    "12. Limitation of Liability. Vendor liability shall not exceed three (3) months of fees paid."
)


class TestV2Activation:
    def test_v2_position_passes_activation_without_v1_config_fields(self):
        db = SessionLocal()
        try:
            user = _user(db)
            pb = _playbook(db, user.id)
            position = PolicyPosition(
                playbook_id=pb.id,
                clause_type="limitation_of_liability",
                status="APPROVED",
                config_json={},
                policy_schema_version=2,
                rules_v2_json=FIRM_A,
            )
            db.add(position)
            db.flush()
            pa.validate_position_for_activation(position)
        finally:
            db.rollback()
            db.close()

    def test_v2_position_rejects_invalid_rules(self):
        db = SessionLocal()
        try:
            user = _user(db)
            pb = _playbook(db, user.id)
            position = PolicyPosition(
                playbook_id=pb.id,
                clause_type="limitation_of_liability",
                status="APPROVED",
                config_json={},
                policy_schema_version=2,
                rules_v2_json={"schema_version": 2, "bands": []},
            )
            db.add(position)
            db.flush()
            with pytest.raises(pa.PolicyActivationError) as exc:
                pa.validate_position_for_activation(position)
            assert "PREFERRED" in str(exc.value)
        finally:
            db.rollback()
            db.close()


class TestV2CutoverEnforcement:
    def test_firm_a_fallback_accepts_12_month_contract_low_acv(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            user = _user(db)
            pb = _playbook(db, user.id)
            position = PolicyPosition(
                playbook_id=pb.id,
                clause_type="limitation_of_liability",
                status="ACTIVE",
                config_json={"preferred_multiplier": 1.0},
                policy_schema_version=2,
                rules_v2_json=FIRM_A,
            )
            db.add(position)
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(
                db, pb, CONTRACT_12MO_FEES, findings, context={"deal_value": 100000},
            )
            decision = result["policy_decisions"]["limitation_of_liability"]
            assert decision["state"] == "ACCEPT_WITH_NOTE"
            assert result["policy_revision_metadata"]["limitation_of_liability"]["config_hash"]
        finally:
            db.rollback()
            db.close()

    def test_firm_a_hard_stops_3_month_contract(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            user = _user(db)
            pb = _playbook(db, user.id)
            position = PolicyPosition(
                playbook_id=pb.id,
                clause_type="limitation_of_liability",
                status="ACTIVE",
                config_json={},
                policy_schema_version=2,
                rules_v2_json=FIRM_A,
            )
            db.add(position)
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(
                db, pb, CONTRACT_3MO_FEES, findings, context={"deal_value": 500000},
            )
            decision = result["policy_decisions"]["limitation_of_liability"]
            assert decision["state"] == "PROHIBITED"
            assert len(findings) == 1
            assert findings[0]["policy_state"] == "PROHIBITED"
        finally:
            db.rollback()
            db.close()

    def test_v1_position_still_uses_v1_evaluator(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            user = _user(db)
            pb = _playbook(db, user.id)
            config = {
                "preferred_multiplier": 1.0,
                "acceptable_max_multiplier": 2.0,
                "negotiate_max_multiplier": 5.0,
                "prohibit_unlimited": True,
                "required_exceptions_json": [],
                "require_consequential_damages_exclusion": False,
                "required_consequential_carveouts_json": [],
            }
            position = PolicyPosition(
                playbook_id=pb.id,
                clause_type="limitation_of_liability",
                status="ACTIVE",
                config_json=config,
                policy_schema_version=1,
            )
            db.add(position)
            db.flush()
            db.add(PolicyPositionField(
                policy_position_id=position.id,
                field_name="require_consequential_damages_exclusion",
                value_json=False,
                source="MANUAL",
                status="ESTABLISHED",
            ))
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(db, pb, CONTRACT_5X_ANNUAL, findings)
            decision = result["policy_decisions"]["limitation_of_liability"]
            assert decision["state"] == "NEGOTIATE"
        finally:
            db.rollback()
            db.close()

    def test_config_hash_includes_v2_rules(self):
        db = SessionLocal()
        try:
            user = _user(db)
            pb = _playbook(db, user.id)
            position = PolicyPosition(
                playbook_id=pb.id,
                clause_type="limitation_of_liability",
                status="ACTIVE",
                policy_schema_version=2,
                rules_v2_json=FIRM_A,
            )
            h1 = pe.config_hash_for_position(position)
            position.rules_v2_json = dict(FIRM_A)
            position.rules_v2_json["prohibit_unlimited"] = False
            h2 = pe.config_hash_for_position(position)
            assert h1 != h2
        finally:
            db.rollback()
            db.close()
