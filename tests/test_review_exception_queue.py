"""
Integration tests for the contract-review exception queue (P0
remediation of docs/architecture/contract_review_exception_ux.md).

review_queue.py's own ordering/passed-correctness logic is covered
exhaustively at the unit level in tests/test_review_queue.py (pure
functions, no DB). This file covers the parts a pure-function test
cannot: real Playbook/PolicyPosition/Contract rows flowing through
main.py's review_contract route into the QUEUE JSON embedded in the
served page, plus static-markup regression guards for the UI mechanics
that only run as client-side JS (defaults-collapsed passed section,
row-level escalation badge, exception relabeling, evidence drawer,
ordinary-rule-finding accessibility) — there is no JS test runner in
this repository, so those are verified by asserting the exact template
source/markers the runtime JS depends on are present in the served
response, alongside the review_queue.py unit tests that prove the data
feeding them is correct.
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
from models import Contract, Playbook, PolicyPosition, PolicyPositionField, PolicyRule, User


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
    finally:
        db.close()
    return token


def _create_playbook_direct(db, user_id, name="Queue Test PB") -> Playbook:
    playbook = Playbook(user_id=user_id, name=name, template_text="x")
    db.add(playbook)
    db.flush()
    return playbook


_MINIMAL_CONFIG = {
    "limitation_of_liability": {
        "preferred_multiplier": 1.0, "acceptable_max_multiplier": 2.0, "negotiate_max_multiplier": 3.0,
        "prohibit_unlimited": True, "required_exceptions_json": [],
        "require_consequential_damages_exclusion": False, "required_consequential_carveouts_json": [],
    },
    "governing_law": {
        "preferred_jurisdictions_json": ["Delaware"], "acceptable_jurisdictions_json": ["Delaware"],
        "prohibited_jurisdictions_json": [], "require_jury_trial_waiver": False,
    },
}
_ACTIVATION_REQUIRED = {
    "limitation_of_liability": ["require_consequential_damages_exclusion"],
    "governing_law": ["require_jury_trial_waiver"],
}


def _make_active_position(db, playbook, clause_type, config_overrides=None, escalation_approval_authority="General Counsel") -> PolicyPosition:
    config = dict(_MINIMAL_CONFIG[clause_type])
    config.update(config_overrides or {})
    position = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status="DRAFT", contract_side="mutual",
        escalation_approval_authority=escalation_approval_authority,
        fallback_text="Approved fallback text.", config_json=config, source_type="MANUAL",
    )
    db.add(position)
    db.flush()
    for field_name in _ACTIVATION_REQUIRED[clause_type]:
        db.add(PolicyPositionField(
            policy_position_id=position.id, field_name=field_name,
            value_json=config.get(field_name, False), source="MANUAL", status="ESTABLISHED",
        ))
    db.flush()
    pa.validate_position_for_activation(position)
    position.status = "ACTIVE"
    position.activated_at = datetime.utcnow()
    db.flush()
    return position


CONTRACT_TEXT = (
    "12. Limitation of Liability. Each party shall have unlimited liability for any and all claims "
    "arising under this Agreement. "
    "13. Governing Law. This Agreement shall be governed by the laws of the State of New York."
)


def _extract_queue_json(html: str) -> dict:
    m = re.search(r"const QUEUE = (\{.*?\});", html)
    assert m, "QUEUE JSON not found in rendered page"
    return json.loads(m.group(1))


def _upload_with_playbook(client, token, pb_id, text=CONTRACT_TEXT):
    files = {"file": ("t.txt", io.BytesIO(text.encode()), "text/plain")}
    r = client.post("/upload", data={"playbook_id": str(pb_id), "csrf_token": token},
                     files=files, follow_redirects=False)
    assert r.status_code == 303
    return r.headers["location"].split("/contract/")[1].split("/")[0]


# ---------------------------------------------------------------------------
# End-to-end: real playbook -> real evaluation -> QUEUE embedded correctly
# ---------------------------------------------------------------------------

class TestEndToEndQueueWiring:
    def test_prohibited_and_acceptable_clause_classified_correctly_end_to_end(self, client, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        token = _register(client, "queue-e2e-a@example.com")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "queue-e2e-a@example.com").first()
            playbook = _create_playbook_direct(db, user.id)
            _make_active_position(db, playbook, "limitation_of_liability")
            _make_active_position(db, playbook, "governing_law", {"preferred_jurisdictions_json": ["New York"], "acceptable_jurisdictions_json": ["New York"]})
            db.commit()
            pb_id = playbook.id
        finally:
            db.close()

        contract_id = _upload_with_playbook(client, token, pb_id)
        page = client.get(f"/contract/{contract_id}/review")
        assert page.status_code == 200
        queue = _extract_queue_json(page.text)

        # Unlimited liability against prohibit_unlimited=True -> PROHIBITED.
        assert queue["summary"]["top_tier"] >= 1
        # New York matches the (adjusted) governing-law policy -> ACCEPT,
        # must show up as passed, never as a finding.
        assert queue["summary"]["passed"] >= 1
        passed_clause_types = {c["clause_type"] for c in queue["passed_checks"]}
        assert "governing_law" in passed_clause_types

    def test_evaluation_error_clause_never_counted_as_passed_end_to_end(self, client, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        token = _register(client, "queue-e2e-error@example.com")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "queue-e2e-error@example.com").first()
            playbook = _create_playbook_direct(db, user.id)
            _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()
            pb_id = playbook.id
        finally:
            db.close()

        def _boom(text):
            raise RuntimeError("simulated extractor crash")

        original_funcs = pa._ENGINE_FUNCS["limitation_of_liability"]
        monkeypatch.setitem(pa._ENGINE_FUNCS, "limitation_of_liability", (_boom, original_funcs[1]))

        contract_id = _upload_with_playbook(client, token, pb_id)
        page = client.get(f"/contract/{contract_id}/review")
        queue = _extract_queue_json(page.text)
        assert queue["summary"]["evaluation_error"] == 1
        assert queue["summary"]["passed"] == 0
        assert "limitation_of_liability" not in {c["clause_type"] for c in queue["passed_checks"]}

    def test_only_evaluated_clause_appears_never_manufactured_as_passed(self, client, monkeypatch):
        """Only limitation_of_liability has an ACTIVE position — the other
        five clause types must never appear as 'passed' since they were
        never evaluated at all."""
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        token = _register(client, "queue-e2e-partial@example.com")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "queue-e2e-partial@example.com").first()
            playbook = _create_playbook_direct(db, user.id)
            _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 5.0, "acceptable_max_multiplier": 8.0, "prohibit_unlimited": False})
            db.commit()
            pb_id = playbook.id
        finally:
            db.close()

        contract_id = _upload_with_playbook(client, token, pb_id,
            text="12. Limitation of Liability. In no event shall liability exceed 5 times fees paid.")
        page = client.get(f"/contract/{contract_id}/review")
        queue = _extract_queue_json(page.text)
        passed_clause_types = {c["clause_type"] for c in queue["passed_checks"]}
        assert passed_clause_types <= {"limitation_of_liability"}
        assert "governing_law" not in passed_clause_types
        assert "indemnification" not in passed_clause_types

    def test_ordinary_rule_findings_remain_accessible_alongside_policy_findings(self, client, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        token = _register(client, "queue-e2e-other@example.com")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "queue-e2e-other@example.com").first()
            playbook = _create_playbook_direct(db, user.id)
            _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()
            pb_id = playbook.id
        finally:
            db.close()

        contract_id = _upload_with_playbook(client, token, pb_id)
        page = client.get(f"/contract/{contract_id}/review")
        queue = _extract_queue_json(page.text)
        # other_finding_indices must be present in the structure (may be
        # empty for this short fixture text, but the key/shape must exist
        # and every FINDINGS entry must be reachable via one list or the
        # other — no finding silently dropped).
        assert "other_finding_indices" in queue
        m = re.search(r"const FINDINGS = (\[.*?\]);", page.text)
        findings = json.loads(m.group(1))
        all_idxs = set(queue["policy_exception_indices"]) | set(queue["other_finding_indices"])
        assert all_idxs == set(range(len(findings)))

    def test_escalation_authority_reaches_the_page(self, client, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        token = _register(client, "queue-e2e-escalate@example.com")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "queue-e2e-escalate@example.com").first()
            playbook = _create_playbook_direct(db, user.id)
            _make_active_position(db, playbook, "limitation_of_liability", escalation_approval_authority="Chief Legal Officer")
            db.commit()
            pb_id = playbook.id
        finally:
            db.close()

        contract_id = _upload_with_playbook(client, token, pb_id)
        page = client.get(f"/contract/{contract_id}/review")
        m = re.search(r"const FINDINGS = (\[.*?\]);", page.text)
        findings = json.loads(m.group(1))
        policy_findings = [f for f in findings if f["finding_type"] == "policy_decision"]
        assert policy_findings
        assert policy_findings[0]["escalate_to"] == "Chief Legal Officer"
        # And the row-rendering markup that surfaces it at row level (not
        # just inside the popover) is present in the shipped JS.
        assert "row-escalate-badge" in page.text

    def test_previously_overridden_finding_carries_original_recommendation_for_row_display(self, client, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        token = _register(client, "queue-e2e-override@example.com")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "queue-e2e-override@example.com").first()
            playbook = _create_playbook_direct(db, user.id)
            _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()
            pb_id = playbook.id
        finally:
            db.close()

        contract_id = _upload_with_playbook(client, token, pb_id)
        page = client.get(f"/contract/{contract_id}/review")
        m = re.search(r"const FINDINGS = (\[.*?\]);", page.text)
        findings = json.loads(m.group(1))
        policy_idx = next(i for i, f in enumerate(findings) if f["finding_type"] == "policy_decision")

        resp = client.post(f"/contract/{contract_id}/review/decision", data={
            "finding_index": policy_idx, "action": "rejected",
            "reason": "Strategic exception approved.", "csrf_token": token,
        })
        assert resp.status_code == 200
        entry = resp.json()["entry"]
        assert entry["policy_original_recommendation"] == "PROHIBITED"

        reloaded = client.get(f"/contract/{contract_id}/review")
        m2 = re.search(r"let DECISIONS = (\{.*?\});", reloaded.text)
        decisions = json.loads(m2.group(1))
        stored_key = [k for k in decisions if k.startswith(findings[policy_idx]["rule_id"])][0]
        assert decisions[stored_key]["policy_original_recommendation"] == "PROHIBITED"
        # Row-level rendering logic (rowStatusBadgeHTML) that surfaces this
        # without opening the finding is present in the shipped JS.
        assert "Exception granted" in reloaded.text


# ---------------------------------------------------------------------------
# Static UI-mechanics regression guards (no JS runtime in this repo — see
# module docstring for why these assert on served source rather than
# actual rendered DOM state)
# ---------------------------------------------------------------------------

class TestStaticUIMechanics:
    def test_passed_section_defaults_collapsed_in_source(self, client):
        page = client.get("/register")  # any page to get a valid client; content check is on review.html source
        with open("templates/review.html") as fh:
            src = fh.read()
        # The passed-list container must never be constructed with the
        # "open" class already applied — only user interaction (the click
        # handler toggling .open) reveals it.
        assert 'class="passed-list" id="passed-list">' in src
        assert 'class="passed-list open"' not in src

    def test_exception_relabeling_present_for_governance_states(self):
        with open("templates/review.html") as fh:
            src = fh.read()
        assert "Request exception" in src
        assert "POLICY_GOVERNANCE_STATES" in src

    def test_evidence_report_drawer_present(self):
        with open("templates/review.html") as fh:
            src = fh.read()
        assert "pop-evidence-report" in src
        assert "f.evidence_report" in src

    def test_no_confidence_score_introduced_for_policy_findings(self):
        with open("templates/review.html") as fh:
            src = fh.read()
        # The existing (Phase 3-era) guarantee — policy findings carry a
        # null confidence_breakdown and the UI must not paper over that
        # with an invented percentage.
        assert "cb ? esc(cb.confidence)" in src

    def test_review_queue_summary_and_playbook_exceptions_labels_present(self):
        with open("templates/review.html") as fh:
            src = fh.read()
        assert "Playbook Exceptions" in src
        assert "policy check" in src  # "N policy check(s) passed"


# ---------------------------------------------------------------------------
# Preserve existing behavior: Verify, redline, cross-user access
# ---------------------------------------------------------------------------

class TestExistingBehaviorPreserved:
    def test_verify_still_works_for_policy_findings_after_queue_changes(self, client, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        token = _register(client, "queue-verify-still-works@example.com")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "queue-verify-still-works@example.com").first()
            playbook = _create_playbook_direct(db, user.id)
            _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()
            pb_id = playbook.id
        finally:
            db.close()

        contract_id = _upload_with_playbook(client, token, pb_id)
        page = client.get(f"/contract/{contract_id}/review")
        m = re.search(r"const FINDINGS = (\[.*?\]);", page.text)
        findings = json.loads(m.group(1))
        policy_idx = next(i for i, f in enumerate(findings) if f["finding_type"] == "policy_decision")

        resp = client.post(f"/contract/{contract_id}/review/verify", data={"finding_index": policy_idx, "csrf_token": token})
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy_verification"] is True
        assert data["verified"] is True

    def test_redline_accept_workflow_still_works(self, client, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        token = _register(client, "queue-redline-still-works@example.com")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == "queue-redline-still-works@example.com").first()
            playbook = _create_playbook_direct(db, user.id)
            _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()
            pb_id = playbook.id
        finally:
            db.close()

        contract_id = _upload_with_playbook(client, token, pb_id)
        page = client.get(f"/contract/{contract_id}/review")
        m = re.search(r"const FINDINGS = (\[.*?\]);", page.text)
        findings = json.loads(m.group(1))
        policy_idx = next(i for i, f in enumerate(findings) if f["finding_type"] == "policy_decision")
        assert findings[policy_idx]["redline"]

        resp = client.post(f"/contract/{contract_id}/review/decision", data={
            "finding_index": policy_idx, "action": "accepted", "csrf_token": token,
        })
        assert resp.status_code == 200
        assert resp.json()["entry"]["action"] == "accepted"

    def test_cross_user_cannot_read_others_review_queue(self, client):
        token_a = _register(client, "queue-owner-a@example.com")
        # Upload without a playbook_id to avoid cross-user playbook
        # plumbing entirely — this test is specifically about the review
        # route's ownership check, not playbook ownership.
        files = {"file": ("t.txt", io.BytesIO(CONTRACT_TEXT.encode()), "text/plain")}
        r = client.post("/upload", data={"csrf_token": token_a}, files=files, follow_redirects=False)
        assert r.status_code == 303
        contract_id = r.headers["location"].split("/contract/")[1].split("/")[0]

        client.cookies.clear()
        token_b = _register(client, "queue-attacker-b@example.com")
        resp = client.get(f"/contract/{contract_id}/review")
        assert resp.status_code == 404
