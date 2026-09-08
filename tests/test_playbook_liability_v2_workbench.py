"""Workbench v2 LoL editor — load, edit, roundtrip, governance."""

import io
import os
import uuid

os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi.testclient import TestClient

import main
import playbook_liability_v2_authoring as lv2
from database import SessionLocal, init_db
from liability_policy_v2 import liability_policy_v2_to_dict
from models import Playbook, PolicyPosition, User
from tests.fixtures.liability_policy_v2_golden import FIRM_A, FIRM_B, FIRM_C, FIRM_D, firm_a_policy


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _register(client, email=None):
    email = email or f"v2wb-{uuid.uuid4().hex}@example.com"
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    client.post("/register", data={
        "email": email, "password": "Str0ngP@ssw0rd!", "confirm_password": "Str0ngP@ssw0rd!",
        "name": "Firm", "company": "", "csrf_token": token, "accept_terms": "on",
    })
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None, "registration failed"
        user.plan = "professional"
        db.commit()
        return token, user.id
    finally:
        db.close()


def _playbook(user_id, name="V2 WB"):
    db = SessionLocal()
    try:
        pb = Playbook(user_id=user_id, name=name, template_text="x")
        db.add(pb)
        db.flush()
        pid = pb.id
        db.commit()
        return pid
    finally:
        db.close()


def _v2_position(playbook_id, rules, status="DRAFT"):
    db = SessionLocal()
    try:
        pos = PolicyPosition(
            playbook_id=playbook_id,
            clause_type="limitation_of_liability",
            status=status,
            policy_schema_version=2,
            rules_v2_json=rules,
            contract_side="buy_side",
        )
        db.add(pos)
        db.commit()
        return pos.id
    finally:
        db.close()


class TestV2ViewModel:
    @pytest.mark.parametrize("rules,label", [
        (FIRM_A, "A"), (FIRM_B, "B"), (FIRM_C, "C"), (FIRM_D, "D"),
    ])
    def test_golden_firms_render_view(self, rules, label):
        db = SessionLocal()
        try:
            user = User(email=f"firm{label}-{uuid.uuid4().hex}@example.com", password_hash="x")
            db.add(user)
            db.flush()
            pb = Playbook(user_id=user.id, name=f"Firm {label}", template_text="x")
            db.add(pb)
            db.flush()
            pos = PolicyPosition(
                playbook_id=pb.id, clause_type="limitation_of_liability",
                status="DRAFT", policy_schema_version=2, rules_v2_json=rules,
            )
            view = lv2.v2_edit_view(pos)
            assert view["preferred"]["operator"] in ("SIMPLE", "GREATER_OF", "LESSER_OF")
            assert "rules_v2_json" not in str(view)
        finally:
            db.rollback()
            db.close()


class TestV2WorkbenchHTTP:
    def test_v2_editor_loads_without_raw_json(self, client):
        token, uid = _register(client)
        pb_id = _playbook(uid, "Load Test")
        _v2_position(pb_id, FIRM_A)
        r = client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/edit")
        assert r.status_code == 200
        assert "Structured liability policy (v2)" in r.text
        assert "rules_v2_json" not in r.text
        assert "General cap" in r.text or "preferred" in r.text.lower()
        assert "Hard stop" in r.text
        assert "Super-cap" in r.text

    def test_v1_editor_unchanged(self, client):
        token, uid = _register(client)
        pb_id = _playbook(uid, "V1 Test")
        db = SessionLocal()
        try:
            pos = PolicyPosition(
                playbook_id=pb_id, clause_type="limitation_of_liability",
                status="DRAFT", policy_schema_version=1,
                config_json={"preferred_multiplier": 1.0, "prohibit_unlimited": True,
                             "required_exceptions_json": [], "require_consequential_damages_exclusion": False,
                             "required_consequential_carveouts_json": []},
            )
            db.add(pos)
            db.commit()
        finally:
            db.close()
        r = client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/edit")
        assert r.status_code == 200
        assert "preferred_multiplier" in r.text
        assert "Structured liability policy (v2)" not in r.text

    def test_v2_save_and_reload(self, client):
        token, uid = _register(client)
        pb_id = _playbook(uid, "Save Test")
        _v2_position(pb_id, FIRM_A)
        client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/edit")
        save = client.post(
            f"/playbooks/{pb_id}/positions/limitation_of_liability/save",
            data={
                "csrf_token": token, "authoring_form": "1", "v2_editor": "1",
                "contract_side": "buy_side",
                "v2_orientation": "buy_side",
                "v2_preferred_operator": "GREATER_OF",
                "v2_preferred_op1_type": "fee_period", "v2_preferred_op1_months": "12",
                "v2_preferred_op1_basis": "FEES_PAID_OR_PAYABLE", "v2_preferred_op1_scope": "AGREEMENT",
                "v2_preferred_op2_type": "fixed_amount", "v2_preferred_op2_amount": "1000000", "v2_preferred_op2_currency": "USD",
                "v2_fallback_enabled": "yes",
                "v2_fallback_operator": "SIMPLE", "v2_fallback_op1_type": "fee_period",
                "v2_fallback_op1_months": "12", "v2_fallback_op1_basis": "CONTRACT_FEES", "v2_fallback_op1_scope": "AGREEMENT",
                "v2_fallback_acv_lt": "250000",
                "v2_hard_stop_enabled": "yes", "v2_hard_stop_op1_months": "6",
                "v2_hard_stop_op1_basis": "CONTRACT_FEES", "v2_hard_stop_op1_scope": "AGREEMENT",
                "v2_super_cap_enabled": "yes", "v2_super_cap_multiplier": "2",
                "v2_super_cap_category": "confidentiality",
                "v2_escalation_enabled": "yes", "v2_escalation_acv_gte": "250000",
                "v2_escalation_cap_lt_months": "12", "v2_escalation_approver": "supervising_partner",
                "v2_prohibit_unlimited": "yes",
            },
            follow_redirects=False,
        )
        assert save.status_code == 302
        db = SessionLocal()
        try:
            pos = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id,
                PolicyPosition.clause_type == "limitation_of_liability",
            ).order_by(PolicyPosition.id.desc()).first()
            assert pos.policy_schema_version == 2
            assert pos.rules_v2_json["bands"][0]["kind"] == "PREFERRED"
            assert pos.status == "DRAFT"
        finally:
            db.close()

    def test_active_edit_forks_draft(self, client):
        token, uid = _register(client)
        pb_id = _playbook(uid, "Fork Test")
        db = SessionLocal()
        try:
            active = PolicyPosition(
                playbook_id=pb_id, clause_type="limitation_of_liability",
                status="ACTIVE", policy_schema_version=2, rules_v2_json=FIRM_A,
            )
            db.add(active)
            db.commit()
            active_id = active.id
        finally:
            db.close()
        r = client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/edit")
        assert r.status_code == 200
        assert "new revision" in r.text.lower() or "Active" in r.text
        db = SessionLocal()
        try:
            rows = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id,
                PolicyPosition.clause_type == "limitation_of_liability",
            ).all()
            assert len(rows) >= 2
            assert any(p.status == "ACTIVE" and p.id == active_id for p in rows)
            assert any(p.status == "DRAFT" for p in rows)
        finally:
            db.close()
