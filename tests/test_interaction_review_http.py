"""
HTTP-level integration for Interaction Engine V1's review-page wiring:
real upload -> real cutover-mode evaluation -> QUEUE JSON embedded in the
served review page includes the interaction bucket, an edit on a
participating clause's finding marks the dependent interaction stale via
the real /review/decision route, GET /review reflects it, and /review/
interaction/dismiss-stale clears it -- exercising main.py's actual route
handlers, not just the pure functions already covered in
test_interaction_enforcement.py.
"""
import io
import json
import re
from datetime import datetime

import os

os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi.testclient import TestClient

import main
import playbook_authoring as pa
import rate_limit
from database import SessionLocal
from models import Playbook, PolicyPosition, PolicyPositionField, User


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    rate_limit._memory_counters.clear()
    yield
    rate_limit._memory_counters.clear()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _register(client, email) -> str:
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    client.post("/register", data={
        "email": email, "password": "Str0ngP@ssw0rd!", "confirm_password": "Str0ngP@ssw0rd!",
        "name": "Firm", "company": "", "csrf_token": token,
    })
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.plan = "professional"
        db.commit()
        uid = user.id
    finally:
        db.close()
    return token, uid


def _create_playbook_direct(db, user_id, name="IX HTTP Test PB") -> Playbook:
    playbook = Playbook(user_id=user_id, name=name, template_text="x")
    db.add(playbook)
    db.flush()
    return playbook


def _make_active_position(db, playbook, clause_type, contract_side, config_overrides=None) -> PolicyPosition:
    from tests.test_phase4_policy_enforcement import _MINIMAL_CONFIG
    config = dict(_MINIMAL_CONFIG[clause_type])
    config.update(config_overrides or {})
    position = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status="DRAFT", contract_side=contract_side,
        escalation_approval_authority="General Counsel",
        fallback_text="Approved fallback text.", config_json=config, source_type="MANUAL",
    )
    db.add(position)
    db.flush()
    for field_name in pa.ACTIVATION_REQUIRED_FIELDS.get(clause_type, []):
        db.add(PolicyPositionField(
            policy_position_id=position.id, field_name=field_name,
            value_json=config.get(field_name), source="MANUAL", status="ESTABLISHED",
        ))
    db.flush()
    pa.validate_position_for_activation(position)
    position.status = "ACTIVE"
    position.activated_at = datetime.utcnow()
    db.flush()
    return position


IP_TEXT = (
    "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total annual fees "
    "paid; the foregoing limitation shall not apply to claims arising from intellectual property "
    "infringement. "
    "9.1 Indemnification. Supplier shall indemnify, defend, and hold harmless Customer from and against "
    "any third-party claims arising from actual or alleged infringement of intellectual property rights "
    "by the Services."
)


def _extract_queue_json(html: str) -> dict:
    m = re.search(r"const QUEUE = (\{.*?\});", html)
    assert m, "QUEUE JSON not found in rendered page"
    return json.loads(m.group(1))


def _extract_findings_json(html: str) -> list:
    m = re.search(r"const FINDINGS = (\[.*?\]);", html, re.DOTALL)
    assert m, "FINDINGS JSON not found in rendered page"
    return json.loads(m.group(1))


def _upload(client, token, pb_id, text=IP_TEXT):
    files = {"file": ("t.txt", io.BytesIO(text.encode()), "text/plain")}
    r = client.post("/upload", data={"playbook_id": str(pb_id), "csrf_token": token},
                     files=files, follow_redirects=False)
    assert r.status_code == 303
    return r.headers["location"].split("/contract/")[1].split("/")[0]


@pytest.fixture()
def flagship_scenario(monkeypatch, client, request):
    monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
    email = f"ix-http-{abs(hash(request.node.name))}@example.com"
    token, uid = _register(client, email)
    db = SessionLocal()
    try:
        playbook = _create_playbook_direct(db, uid)
        # preferred/acceptable set below the contract's stated 1x multiplier
        # so Liability's OWN decision lands on NEGOTIATE (an actionable
        # state that produces a real policy_decision finding to edit/reject
        # in the HTTP invalidation tests below) -- an ACCEPT decision
        # produces no finding at all, so there would be nothing to click.
        _make_active_position(db, playbook, "limitation_of_liability", "mutual", {
            "preferred_multiplier": 0.3, "acceptable_max_multiplier": 0.5, "negotiate_max_multiplier": 5.0,
            "prohibit_unlimited": False,
        })
        _make_active_position(db, playbook, "indemnification", "sell_side")
        db.commit()
        pb_id = playbook.id
    finally:
        db.close()
    contract_id = _upload(client, token, pb_id)
    return token, contract_id


class TestReviewPageIncludesInteractions:
    def test_queue_json_has_interaction_bucket_populated(self, flagship_scenario, client):
        token, contract_id = flagship_scenario
        r = client.get(f"/contract/{contract_id}/review")
        assert r.status_code == 200
        queue = _extract_queue_json(r.text)
        assert queue["summary"]["interactions_needing_attention"] == 1
        assert len(queue["interaction_exception_indices"]) == 1

        findings = _extract_findings_json(r.text)
        idx = queue["interaction_exception_indices"][0]
        assert findings[idx]["finding_type"] == "interaction_decision"
        assert findings[idx]["interaction_id"] == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"
        assert findings[idx]["policy_state"] == "ESCALATE"
        assert findings[idx].get("stale") in (False, None)

    def test_cross_policy_interactions_section_rendered(self, flagship_scenario, client):
        # The queue-section-head/row markup lives inside a JS template
        # literal in the served page's <script> block (client-side
        # rendering, same as every other queue row) -- this asserts the
        # static source the runtime JS depends on is present, mirroring
        # test_review_exception_queue.py's own "static markup regression
        # guard" convention for parts with no JS test runner.
        token, contract_id = flagship_scenario
        r = client.get(f"/contract/{contract_id}/review")
        assert "Cross-Policy Interactions" in r.text
        assert "interactionQueueRowHTML" in r.text
        assert "interaction_exception_indices" in r.text


class TestInvalidationHTTPFlow:
    def test_editing_liability_finding_marks_interaction_stale(self, flagship_scenario, client):
        token, contract_id = flagship_scenario
        r = client.get(f"/contract/{contract_id}/review")
        findings = _extract_findings_json(r.text)
        liability_idx = next(i for i, f in enumerate(findings) if f.get("clause_type") == "limitation_of_liability")

        edit_resp = client.post(f"/contract/{contract_id}/review/decision", data={
            "finding_index": liability_idx, "action": "edited",
            "edited_text": "Revised cap language.", "csrf_token": token,
        })
        assert edit_resp.status_code == 200

        r2 = client.get(f"/contract/{contract_id}/review")
        findings2 = _extract_findings_json(r2.text)
        interaction_finding = next(f for f in findings2 if f.get("finding_type") == "interaction_decision")
        assert interaction_finding["stale"] is True
        assert "Limitation of Liability" in interaction_finding["stale_reason"]

    def test_dismiss_stale_clears_flag(self, flagship_scenario, client):
        token, contract_id = flagship_scenario
        r = client.get(f"/contract/{contract_id}/review")
        findings = _extract_findings_json(r.text)
        liability_idx = next(i for i, f in enumerate(findings) if f.get("clause_type") == "limitation_of_liability")
        client.post(f"/contract/{contract_id}/review/decision", data={
            "finding_index": liability_idx, "action": "edited",
            "edited_text": "Revised cap language.", "csrf_token": token,
        })

        dismiss_resp = client.post(f"/contract/{contract_id}/review/interaction/dismiss-stale", data={
            "interaction_id": "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY", "csrf_token": token,
        })
        assert dismiss_resp.status_code == 200
        assert dismiss_resp.json()["cleared"] is True

        r2 = client.get(f"/contract/{contract_id}/review")
        findings2 = _extract_findings_json(r2.text)
        interaction_finding = next(f for f in findings2 if f.get("finding_type") == "interaction_decision")
        assert interaction_finding.get("stale") in (False, None)

    def test_accepting_liability_finding_does_not_mark_stale(self, flagship_scenario, client):
        """Only edited/rejected represent a changed effective treatment --
        accepting the deterministic recommendation as-is must never flag
        dependent interactions (design doc S5.2: only an actual EDIT to
        the provision is a genuine invalidation trigger)."""
        token, contract_id = flagship_scenario
        r = client.get(f"/contract/{contract_id}/review")
        findings = _extract_findings_json(r.text)
        liability_idx = next(i for i, f in enumerate(findings) if f.get("clause_type") == "limitation_of_liability")

        client.post(f"/contract/{contract_id}/review/decision", data={
            "finding_index": liability_idx, "action": "accepted", "csrf_token": token,
        })

        r2 = client.get(f"/contract/{contract_id}/review")
        findings2 = _extract_findings_json(r2.text)
        interaction_finding = next(f for f in findings2 if f.get("finding_type") == "interaction_decision")
        assert interaction_finding.get("stale") in (False, None)

    def test_edited_reason_is_forwarded_to_the_stale_reason_via_the_real_clause_label(self, flagship_scenario, client):
        # Confirms main.py forwards the ACTUAL edited clause_type (not a
        # hardcoded string) into mark_dependent_interactions_stale by
        # checking the human-readable clause label appears verbatim in
        # the stored reason -- the case where an HTTP request for a
        # DIFFERENT, non-participating clause_type is a safe no-op is
        # already covered directly against the pure function in
        # test_interaction_enforcement.py::TestMarkDependentInteractionsStale
        # (participating_clause_types is the sole filter there; nothing
        # about the HTTP layer changes that logic, only how clause_type
        # reaches it).
        token, contract_id = flagship_scenario
        r = client.get(f"/contract/{contract_id}/review")
        findings = _extract_findings_json(r.text)
        liability_idx = next(i for i, f in enumerate(findings) if f.get("clause_type") == "limitation_of_liability")

        resp = client.post(f"/contract/{contract_id}/review/decision", data={
            "finding_index": liability_idx, "action": "rejected",
            "reason": "Renegotiating the cap.", "csrf_token": token,
        })
        assert resp.status_code == 200, resp.text

        r2 = client.get(f"/contract/{contract_id}/review")
        findings2 = _extract_findings_json(r2.text)
        interaction_finding = next(f for f in findings2 if f.get("finding_type") == "interaction_decision")
        assert interaction_finding["stale"] is True
        assert interaction_finding["stale_reason"] == (
            "This interaction depends on Limitation of Liability, which has changed since the interaction was evaluated."
        )
