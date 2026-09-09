"""Regression tests for v2 LoL review-page summaries."""

import os
import uuid

os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi.testclient import TestClient

import main
import playbook_authoring as pa
import playbook_liability_v2_review as lv2_review
from database import SessionLocal, init_db
from models import Playbook, PolicyPosition, User
from tests.fixtures.liability_policy_v2_golden import FIRM_A, FIRM_B, FIRM_C, FIRM_D


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _register(client, email=None):
    email = email or f"v2rev-{uuid.uuid4().hex}@example.com"
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    client.post("/register", data={
        "email": email, "password": "Str0ngP@ssw0rd!", "confirm_password": "Str0ngP@ssw0rd!",
        "name": "Firm", "company": "", "csrf_token": token, "accept_terms": "on",
    })
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.plan = "professional"
        db.commit()
        return token, user.id
    finally:
        db.close()


def _playbook(user_id, name="V2 Review"):
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


def _v2_position(playbook_id, rules, *, fallback_text="Standard fallback language.", status="DRAFT"):
    db = SessionLocal()
    try:
        pos = PolicyPosition(
            playbook_id=playbook_id,
            clause_type="limitation_of_liability",
            status=status,
            policy_schema_version=2,
            rules_v2_json=rules,
            contract_side="buy_side",
            fallback_text=fallback_text,
        )
        db.add(pos)
        db.commit()
        return pos.id
    finally:
        db.close()


class TestV2ReviewSummaryHelper:
    @pytest.mark.parametrize("rules,label,needles", [
        (FIRM_A, "A", ["Greater of", "12 months", "$1,000,000", "ACV < $250,000", "Below 6 months", "2× General Cap", "Supervising Partner"]),
        (FIRM_B, "B", ["2× annual fees", "Below 1× annual fees", "3× General Cap"]),
        (FIRM_C, "C", ["$5,000,000", "intellectual property"]),
        (FIRM_D, "D", ["Lesser of", "$10,000,000", "3× annual fees", "ACV < $1,000,000", "General Counsel"]),
    ])
    def test_golden_firm_summaries(self, rules, label, needles):
        pos = PolicyPosition(
            clause_type="limitation_of_liability",
            policy_schema_version=2,
            rules_v2_json=rules,
        )
        text = "\n".join(lv2_review.v2_lol_review_summary(pos))
        for needle in needles:
            assert needle in text, f"Firm {label} missing {needle!r} in:\n{text}"

    def test_firm_a_does_not_use_v1_not_yet_decided_wording(self):
        pos = PolicyPosition(
            clause_type="limitation_of_liability",
            policy_schema_version=2,
            rules_v2_json=FIRM_A,
        )
        text = "\n".join(pa.summarize_position(pos))
        assert "Preferred cap → Not yet decided" not in text
        assert "Accept without escalation up to → Not yet decided" not in text
        assert "Maximum negotiable before escalation → Not yet decided" not in text
        assert "preferred_multiplier" not in text


class TestV2ReviewPageHTTP:
    def test_firm_a_submit_for_review_shows_v2_summary(self, client):
        token, uid = _register(client)
        pb_id = _playbook(uid, "Firm A Review")
        _v2_position(pb_id, FIRM_A)

        submit = client.post(
            f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert submit.status_code == 302

        r = client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/review")
        assert r.status_code == 200
        text = r.text
        assert "Greater of" in text
        assert "12 months" in text
        assert "$1,000,000" in text
        assert "ACV &lt; $250,000" in text or "ACV < $250,000" in text
        assert "Below 6 months" in text
        assert "2× General Cap" in text
        assert "Supervising Partner" in text
        assert "Preferred cap → Not yet decided" not in text
        assert "Accept without escalation up to" not in text
        assert "rules_v2_json" not in text

    @pytest.mark.parametrize("rules,needle", [
        (FIRM_B, "2× annual fees"),
        (FIRM_C, "$5,000,000"),
        (FIRM_D, "Lesser of"),
    ])
    def test_golden_firms_review_page(self, client, rules, needle):
        token, uid = _register(client)
        pb_id = _playbook(uid, f"Review {needle[:8]}")
        _v2_position(pb_id, rules)
        client.post(
            f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review",
            data={"csrf_token": token},
        )
        r = client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/review")
        assert r.status_code == 200
        assert needle in r.text
