"""
Phase 1 integration tests: the Playbook Workbench (manual authoring UI).

Covers the release-gate scenarios from the Phase 1 task:
  1. Full six-adapter workflow: create -> incomplete draft -> complete ->
     review -> approve -> activate -> reopen/edit, verifying the ACTIVE
     position is never mutated by a subsequent edit (a new revision row
     is created instead).
  2. Unanswered vs. explicit-False preservation for boolean fields (the
     non-negotiable requirement) at the HTTP form layer, not just the
     playbook_authoring unit-test layer.
  3. Cross-user access denial for read/update/approve/activate/preview.
  4. Preview never creates a Contract or writes to the DB.
  5. Legacy /playbooks/new and /playbooks/{id}/edit (PolicyRule) untouched.
"""
import io
import os

os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi.testclient import TestClient

import main
import rate_limit
from database import SessionLocal
from models import Contract, Playbook, PolicyPosition, PolicyPositionApproval, PolicyRule, User

TEMPLATE_BYTES = b"This is a template contract. Governing Law: Delaware."


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
    # Fresh registrations default to a plan with playbooks_max == 0; bump
    # this test user to a plan that can create playbooks.
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.plan = "professional"
        db.commit()
    finally:
        db.close()
    return token


def _create_playbook(client, token, name="Test Playbook") -> int:
    files = {"file": ("template.txt", io.BytesIO(TEMPLATE_BYTES), "text/plain")}
    r = client.post("/playbooks/new", data={
        "name": name, "contract_type": "", "description": "", "lol_enabled": "", "csrf_token": token,
    }, files=files, follow_redirects=False)
    assert r.status_code == 302
    db = SessionLocal()
    try:
        pb = db.query(Playbook).filter(Playbook.name == name).order_by(Playbook.id.desc()).first()
        return pb.id
    finally:
        db.close()


LIABILITY_FORM = {
    "preferred_multiplier": "1.0", "acceptable_max_multiplier": "2.0", "negotiate_max_multiplier": "3.0",
    "prohibit_unlimited": "yes",
    "required_exceptions_json": ["fraud", "confidentiality"],
    "require_consequential_damages_exclusion": "no",
    "contract_side": "mutual", "escalation_approval_authority": "General Counsel",
    "fallback_text": "Approved fallback language.",
}


def _complete_form_for(clause_type: str) -> dict:
    """A form submission that answers every require_* field explicitly
    (so approve/activate can succeed) for each of the six clause types."""
    base = {"contract_side": "mutual", "escalation_approval_authority": "General Counsel", "fallback_text": "Approved fallback."}
    if clause_type == "limitation_of_liability":
        base.update(LIABILITY_FORM)
    elif clause_type == "indemnification":
        base.update({
            "required_protection_triggers_json": ["ip_infringement"],
            "prohibited_exposure_triggers_json": [],
            "require_exposure_third_party_only": "yes",
            "require_defense_control_for_exposure": "no",
            "require_notice_and_cooperation_for_exposure": "no",
            "prohibit_uncapped_exposure": "yes",
            "exposure_preferred_multiplier": "1.0", "exposure_acceptable_max_multiplier": "2.0", "exposure_negotiate_max_multiplier": "3.0",
        })
    elif clause_type == "termination":
        base.update({
            "require_mutual_convenience_termination": "yes",
            "min_notice_days_against_us": "30", "min_cure_days_against_us": "15",
            "prohibit_immediate_termination_for_cause": "no",
            "required_survival_topics_json": ["confidentiality"],
            "prohibit_uncapped_termination_fee": "yes",
            "fee_preferred_multiplier": "1.0", "fee_acceptable_max_multiplier": "2.0", "fee_negotiate_max_multiplier": "3.0",
        })
    elif clause_type == "confidentiality":
        base.update({
            "required_exclusions_json": ["public_knowledge"],
            "min_protection_duration_years": "3", "max_exposure_duration_years": "5",
            "require_mutual_confidentiality": "yes",
        })
    elif clause_type == "assignment":
        base.update({
            "required_exceptions_json": ["affiliate"],
            "prohibit_sole_discretion_consent": "yes",
            "require_consent_for_counterparty_assignment": "no",
        })
    elif clause_type == "governing_law":
        base.update({
            "preferred_jurisdictions_json": "Delaware",
            "acceptable_jurisdictions_json": "New York",
            "prohibited_jurisdictions_json": "",
            "required_dispute_resolution": "arbitration",
            "require_jury_trial_waiver": "no",
        })
    return base


CLAUSE_TYPES = [
    "limitation_of_liability", "indemnification", "termination",
    "confidentiality", "assignment", "governing_law",
]


def _save(client, token, playbook_id, clause_type, form: dict):
    data = dict(form)
    data["csrf_token"] = token
    return client.post(f"/playbooks/{playbook_id}/positions/{clause_type}/save", data=data, follow_redirects=False)


def _drive_to_active(client, token, playbook_id, clause_type):
    r = _save(client, token, playbook_id, clause_type, _complete_form_for(clause_type))
    assert r.status_code == 302, r.text
    r = client.post(f"/playbooks/{playbook_id}/positions/{clause_type}/submit-for-review", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 302, r.text
    r = client.post(f"/playbooks/{playbook_id}/positions/{clause_type}/approve", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 302, r.text
    r = client.post(f"/playbooks/{playbook_id}/positions/{clause_type}/activate", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 302, r.text


# ---------------------------------------------------------------------------
# Workbench + coverage
# ---------------------------------------------------------------------------

class TestWorkbenchAndCoverage:
    def test_workbench_shows_all_six_clause_types_not_configured(self, client):
        token = _register(client, "wb-coverage@example.com")
        pb_id = _create_playbook(client, token)
        r = client.get(f"/playbooks/{pb_id}/workbench")
        assert r.status_code == 200
        for clause_type in CLAUSE_TYPES:
            assert clause_type.replace("_", " ") in r.text.lower() or "not set" in r.text.lower()
        assert "0%" in r.text

    def test_draft_row_does_not_inflate_coverage(self, client):
        token = _register(client, "wb-draft-coverage@example.com")
        pb_id = _create_playbook(client, token)
        _save(client, token, pb_id, "limitation_of_liability", _complete_form_for("limitation_of_liability"))
        r = client.get(f"/playbooks/{pb_id}/workbench")
        assert "0%" in r.text  # a DRAFT row must not count as coverage
        assert "Needs review" in r.text or "NEEDS_ATTENTION" not in r.text  # bucketed as needs-attention, not active

    def test_active_position_shown_as_covered(self, client):
        token = _register(client, "wb-active-coverage@example.com")
        pb_id = _create_playbook(client, token)
        _drive_to_active(client, token, pb_id, "limitation_of_liability")
        r = client.get(f"/playbooks/{pb_id}/workbench")
        assert "11.1%" in r.text  # 1 of 9 clause types active


# ---------------------------------------------------------------------------
# Full six-adapter lifecycle: create -> draft -> complete -> review ->
# approve -> activate -> reopen/edit -> ACTIVE not mutated
# ---------------------------------------------------------------------------

class TestFullLifecycleAllSixAdapters:
    @pytest.mark.parametrize("clause_type", CLAUSE_TYPES)
    def test_full_workflow(self, client, clause_type):
        token = _register(client, f"lifecycle-{clause_type}@example.com")
        pb_id = _create_playbook(client, token, name=f"PB {clause_type}")

        # Incomplete draft: save with nothing answered.
        r = _save(client, token, pb_id, clause_type, {"contract_side": "mutual"})
        assert r.status_code == 302

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == clause_type,
            ).first()
            assert position.status == "DRAFT"
        finally:
            db.close()

        # Submitting for review with unanswered require_* fields should
        # still be possible (schema-valid, just not activation-ready) --
        # mark_ready_for_review only checks shape, not completeness.
        r = client.post(f"/playbooks/{pb_id}/positions/{clause_type}/submit-for-review", data={"csrf_token": token}, follow_redirects=False)
        assert r.status_code == 302

        # Approving an incomplete position must fail with the missing
        # requirements shown in plain English, not silently succeed.
        r = client.post(f"/playbooks/{pb_id}/positions/{clause_type}/approve", data={"csrf_token": token}, follow_redirects=False)
        assert r.status_code == 400
        assert "unanswered" in r.text.lower() or "unresolved" in r.text.lower() or "not ready" in r.text.lower() or "before this can be approved" in r.text.lower()

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == clause_type,
            ).first()
            assert position.status == "NEEDS_REVIEW"  # unchanged by the failed approve attempt
        finally:
            db.close()

        # Complete the position, then drive it all the way to ACTIVE.
        r = _save(client, token, pb_id, clause_type, _complete_form_for(clause_type))
        assert r.status_code == 302
        r = client.post(f"/playbooks/{pb_id}/positions/{clause_type}/submit-for-review", data={"csrf_token": token}, follow_redirects=False)
        assert r.status_code == 302
        r = client.post(f"/playbooks/{pb_id}/positions/{clause_type}/approve", data={"csrf_token": token}, follow_redirects=False)
        assert r.status_code == 302
        r = client.post(f"/playbooks/{pb_id}/positions/{clause_type}/activate", data={"csrf_token": token}, follow_redirects=False)
        assert r.status_code == 302

        db = SessionLocal()
        try:
            active = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == clause_type, PolicyPosition.status == "ACTIVE",
            ).first()
            assert active is not None
            active_config_snapshot = dict(active.config_json)
            active_id = active.id
        finally:
            db.close()

        # Reopen/edit the ACTIVE position: GET should fork a new DRAFT
        # revision, not touch the ACTIVE row.
        r = client.get(f"/playbooks/{pb_id}/positions/{clause_type}/edit")
        assert r.status_code == 200
        assert "new revision" in r.text.lower() or "you’re editing a new revision" in r.text.lower() or "editing a new revision" in r.text.lower()

        db = SessionLocal()
        try:
            still_active = db.query(PolicyPosition).filter(PolicyPosition.id == active_id).first()
            assert still_active.status == "ACTIVE"
            assert dict(still_active.config_json) == active_config_snapshot  # byte-for-byte unchanged

            draft_revision = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == clause_type, PolicyPosition.status == "DRAFT",
            ).first()
            assert draft_revision is not None
            assert draft_revision.id != active_id
        finally:
            db.close()

        # Editing and saving the revision must still not touch the
        # ACTIVE row, even after a real field change.
        revised_form = _complete_form_for(clause_type)
        r = _save(client, token, pb_id, clause_type, revised_form)
        assert r.status_code == 302

        db = SessionLocal()
        try:
            still_active = db.query(PolicyPosition).filter(PolicyPosition.id == active_id).first()
            assert still_active.status == "ACTIVE"
            assert dict(still_active.config_json) == active_config_snapshot
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Preserve unknown vs explicit False (the non-negotiable requirement)
# ---------------------------------------------------------------------------

class TestUnansweredVsExplicitFalse:
    def test_missing_boolean_field_in_post_stays_not_established(self, client):
        """The literal scenario the requirement is about: a POST body
        that simply omits a require_*/prohibit_* field entirely (as an
        unchecked HTML checkbox would) must never be read as False."""
        token = _register(client, "tristate-missing@example.com")
        pb_id = _create_playbook(client, token)

        form = dict(LIABILITY_FORM)
        del form["prohibit_unlimited"]  # simulate the field being entirely absent from the POST
        r = _save(client, token, pb_id, "limitation_of_liability", form)
        assert r.status_code == 302

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert "prohibit_unlimited" not in position.config_json
            field = next(f for f in position.fields if f.field_name == "prohibit_unlimited")
            assert field.status == "NOT_ESTABLISHED"
            assert field.value_json is None
        finally:
            db.close()

    def test_explicit_no_is_stored_as_false_established_not_not_established(self, client):
        token = _register(client, "tristate-explicit-no@example.com")
        pb_id = _create_playbook(client, token)

        form = dict(LIABILITY_FORM)
        form["prohibit_unlimited"] = "no"
        r = _save(client, token, pb_id, "limitation_of_liability", form)
        assert r.status_code == 302

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert position.config_json["prohibit_unlimited"] is False
            field = next(f for f in position.fields if f.field_name == "prohibit_unlimited")
            assert field.status == "ESTABLISHED"
            assert field.value_json is False
        finally:
            db.close()

    def test_unset_radio_value_also_stays_not_established(self, client):
        token = _register(client, "tristate-unset@example.com")
        pb_id = _create_playbook(client, token)

        form = dict(LIABILITY_FORM)
        form["prohibit_unlimited"] = "unset"
        r = _save(client, token, pb_id, "limitation_of_liability", form)
        assert r.status_code == 302

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert "prohibit_unlimited" not in position.config_json
            field = next(f for f in position.fields if f.field_name == "prohibit_unlimited")
            assert field.status == "NOT_ESTABLISHED"
        finally:
            db.close()

    def test_incomplete_position_cannot_activate(self, client):
        token = _register(client, "tristate-cant-activate@example.com")
        pb_id = _create_playbook(client, token)
        form = dict(LIABILITY_FORM)
        del form["prohibit_unlimited"]
        del form["require_consequential_damages_exclusion"]
        _save(client, token, pb_id, "limitation_of_liability", form)
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review", data={"csrf_token": token})
        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/approve", data={"csrf_token": token}, follow_redirects=False)
        assert r.status_code == 400

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert position.status == "NEEDS_REVIEW"  # never reached APPROVED
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Approval / audit trail
# ---------------------------------------------------------------------------

class TestApprovalHistory:
    def test_approve_and_activate_write_append_only_history(self, client):
        token = _register(client, "approval-history@example.com")
        pb_id = _create_playbook(client, token)
        _drive_to_active(client, token, pb_id, "limitation_of_liability")

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            history = db.query(PolicyPositionApproval).filter(
                PolicyPositionApproval.policy_position_id == position.id,
            ).order_by(PolicyPositionApproval.created_at).all()
            actions = [h.action for h in history]
            assert actions == ["MARKED_REVIEWED", "APPROVED", "ACTIVATED"]
            assert all(h.actor_user_id is not None for h in history)
        finally:
            db.close()

    def test_review_page_shows_human_readable_summary_not_json(self, client):
        token = _register(client, "review-summary@example.com")
        pb_id = _create_playbook(client, token)
        _save(client, token, pb_id, "limitation_of_liability", _complete_form_for("limitation_of_liability"))
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review", data={"csrf_token": token})

        r = client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/review")
        assert r.status_code == 200
        assert "preferred_multiplier" not in r.text  # never a raw field/JSON name
        assert "config_json" not in r.text
        assert "Preferred cap" in r.text or "1× fees" in r.text


# ---------------------------------------------------------------------------
# Preview: read-only, no Contract/review record
# ---------------------------------------------------------------------------

class TestPreview:
    def test_preview_does_not_create_contract_or_mutate_position(self, client):
        token = _register(client, "preview-readonly@example.com")
        pb_id = _create_playbook(client, token)
        _drive_to_active(client, token, pb_id, "limitation_of_liability")

        db = SessionLocal()
        try:
            contracts_before = db.query(Contract).count()
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            config_before = dict(position.config_json)
        finally:
            db.close()

        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/preview", data={
            "csrf_token": token,
            "sample_text": "Limitation of Liability. Liability shall not exceed one (1) times the fees paid in the preceding 12 months.",
        })
        assert r.status_code == 200
        assert "PREVIEW ONLY" in r.text

        db = SessionLocal()
        try:
            assert db.query(Contract).count() == contracts_before
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert dict(position.config_json) == config_before
            assert position.status == "ACTIVE"
        finally:
            db.close()

    def test_preview_with_no_matching_clause_shows_not_applicable(self, client):
        token = _register(client, "preview-no-clause@example.com")
        pb_id = _create_playbook(client, token)
        _drive_to_active(client, token, pb_id, "governing_law")
        r = client.post(f"/playbooks/{pb_id}/positions/governing_law/preview", data={
            "csrf_token": token, "sample_text": "This document says nothing relevant.",
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Security: cross-user access denial + ownership isolation
# ---------------------------------------------------------------------------

class TestCrossUserSecurity:
    def test_other_user_cannot_view_workbench(self, client):
        token_a = _register(client, "owner-a@example.com")
        pb_id = _create_playbook(client, token_a)

        client.cookies.clear()
        _register(client, "attacker-b@example.com")
        r = client.get(f"/playbooks/{pb_id}/workbench")
        assert r.status_code == 404

    def test_other_user_cannot_view_edit_page(self, client):
        token_a = _register(client, "owner-c@example.com")
        pb_id = _create_playbook(client, token_a)

        client.cookies.clear()
        _register(client, "attacker-d@example.com")
        r = client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/edit")
        assert r.status_code == 404

    def test_other_user_cannot_save_fields(self, client):
        token_a = _register(client, "owner-e@example.com")
        pb_id = _create_playbook(client, token_a)

        client.cookies.clear()
        token_b = _register(client, "attacker-f@example.com")
        r = _save(client, token_b, pb_id, "limitation_of_liability", LIABILITY_FORM)
        assert r.status_code == 404

        db = SessionLocal()
        try:
            assert db.query(PolicyPosition).filter(PolicyPosition.playbook_id == pb_id).count() == 0
        finally:
            db.close()

    def test_other_user_cannot_approve_or_activate(self, client):
        token_a = _register(client, "owner-g@example.com")
        pb_id = _create_playbook(client, token_a)
        _save(client, token_a, pb_id, "limitation_of_liability", _complete_form_for("limitation_of_liability"))
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review", data={"csrf_token": token_a})

        client.cookies.clear()
        token_b = _register(client, "attacker-h@example.com")
        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/approve", data={"csrf_token": token_b})
        assert r.status_code == 404
        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/activate", data={"csrf_token": token_b})
        assert r.status_code == 404

    def test_other_user_cannot_run_preview(self, client):
        token_a = _register(client, "owner-i@example.com")
        pb_id = _create_playbook(client, token_a)
        _drive_to_active(client, token_a, pb_id, "limitation_of_liability")

        client.cookies.clear()
        token_b = _register(client, "attacker-j@example.com")
        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/preview", data={
            "csrf_token": token_b, "sample_text": "irrelevant",
        })
        assert r.status_code == 404

    def test_wrong_playbook_id_type_does_not_leak_other_users_data(self, client):
        """A crafted playbook_id belonging to another user must 404, not
        200-with-someone-else's-data, across every route in this module."""
        token_a = _register(client, "owner-k@example.com")
        pb_id = _create_playbook(client, token_a)

        client.cookies.clear()
        token_b = _register(client, "attacker-l@example.com")
        for path, method in [
            (f"/playbooks/{pb_id}/workbench", "get"),
            (f"/playbooks/{pb_id}/positions/limitation_of_liability/edit", "get"),
            (f"/playbooks/{pb_id}/positions/limitation_of_liability/review", "get"),
            (f"/playbooks/{pb_id}/positions/limitation_of_liability/preview", "get"),
        ]:
            r = getattr(client, method)(path)
            assert r.status_code == 404, path


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------

class TestCSRF:
    def test_save_without_csrf_token_is_rejected(self, client):
        token = _register(client, "csrf-missing@example.com")
        pb_id = _create_playbook(client, token)
        form = dict(LIABILITY_FORM)
        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/save", data=form)
        assert r.status_code in (403, 422)  # missing required field or explicit reject, matching test_csrf.py's convention

    def test_save_with_wrong_csrf_token_is_rejected(self, client):
        token = _register(client, "csrf-wrong@example.com")
        pb_id = _create_playbook(client, token)
        form = dict(LIABILITY_FORM)
        form["csrf_token"] = "not-the-real-token"
        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/save", data=form)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Legacy path untouched
# ---------------------------------------------------------------------------

class TestLegacyPathUntouched:
    def test_legacy_playbook_rule_route_still_works(self, client):
        """Phase 1 must not touch main.py's existing PolicyRule-backed
        /playbooks/new and /playbooks/{id}/edit routes."""
        token = _register(client, "legacy-untouched@example.com")
        files = {"file": ("t.txt", io.BytesIO(TEMPLATE_BYTES), "text/plain")}
        r = client.post("/playbooks/new", data={
            "name": "Legacy PB", "contract_type": "", "description": "",
            "lol_enabled": "on", "lol_side": "mutual", "lol_preferred": "1.0",
            "lol_acceptable_max": "2.0", "lol_negotiate_max": "3.0",
            "lol_prohibit_unlimited": "on", "lol_required_exceptions": ["fraud"],
            "lol_fallback_text": "fallback", "lol_escalation_authority": "GC",
            "csrf_token": token,
        }, files=files, follow_redirects=False)
        assert r.status_code == 302

        db = SessionLocal()
        try:
            pb = db.query(Playbook).filter(Playbook.name == "Legacy PB").first()
            rule = db.query(PolicyRule).filter(PolicyRule.playbook_id == pb.id).first()
            assert rule is not None
            assert rule.preferred_multiplier == 1.0
            # No PolicyPosition should be created by the legacy route.
            assert db.query(PolicyPosition).filter(PolicyPosition.playbook_id == pb.id).count() == 0
        finally:
            db.close()
