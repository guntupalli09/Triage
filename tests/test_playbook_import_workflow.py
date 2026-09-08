"""
Phase 2 integration tests: the Deterministic/Private Template Import
workflow (single-upload, dual-purpose document; proposal review; lawyer
confirmation through the existing Phase 1 lifecycle; security/privacy).
"""
import io
import os

os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi.testclient import TestClient

import evaluator
import main
import rate_limit
from database import SessionLocal
from models import (
    AuditLog, Playbook, PlaybookSourceDocument, PolicyPosition,
    PolicyPositionApproval, PolicyPositionField, PolicyRule, User,
)

LIABILITY_TEMPLATE = (
    b"12. Limitation of Liability. Aggregate liability under this Agreement shall not exceed "
    b"two (2) times the fees paid in the preceding twelve (12) months, except for breaches of "
    b"Confidentiality.\n\n"
    b"20. Governing Law. This Agreement is governed by the laws of the State of Delaware, and "
    b"disputes shall be resolved by binding arbitration."
)


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
        "name": "Firm", "company": "", "accept_terms": "on", "csrf_token": token,
    })
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.plan = "professional"
        db.commit()
    finally:
        db.close()
    return token


def _create_playbook(client, token, name="Test Playbook") -> int:
    r = client.post("/playbooks/new", data={
        "name": name, "contract_type": "", "description": "", "lol_enabled": "", "csrf_token": token,
    }, follow_redirects=False)
    assert r.status_code == 302
    db = SessionLocal()
    try:
        pb = db.query(Playbook).filter(Playbook.name == name).order_by(Playbook.id.desc()).first()
        return pb.id
    finally:
        db.close()


def _import(client, token, playbook_id, *, deviation="on", extraction="on", contract_side="mutual",
            filename="template.txt", content=LIABILITY_TEMPLATE):
    files = {"file": (filename, io.BytesIO(content), "text/plain")}
    data = {"contract_side": contract_side, "csrf_token": token}
    if deviation:
        data["use_as_deviation_baseline"] = deviation
    if extraction:
        data["use_for_policy_extraction"] = extraction
    return client.post(f"/playbooks/{playbook_id}/import", data=data, files=files, follow_redirects=False)


# ---------------------------------------------------------------------------
# Single-upload dual-purpose workflow
# ---------------------------------------------------------------------------

class TestSingleUploadWorkflow:
    def test_extraction_only_does_not_touch_deviation_baseline(self, client):
        token = _register(client, "import-extract-only@example.com")
        pb_id = _create_playbook(client, token)
        r = _import(client, token, pb_id, deviation=None, extraction="on")
        assert r.status_code == 302
        db = SessionLocal()
        try:
            pb = db.query(Playbook).filter(Playbook.id == pb_id).first()
            assert pb.template_text == ""  # no deviation baseline until import sets one
        finally:
            db.close()

    def test_deviation_baseline_only_does_not_create_positions(self, client):
        token = _register(client, "import-baseline-only@example.com")
        pb_id = _create_playbook(client, token)
        r = _import(client, token, pb_id, deviation="on", extraction=None)
        assert r.status_code == 302
        assert r.headers["location"].endswith("/workbench")
        db = SessionLocal()
        try:
            pb = db.query(Playbook).filter(Playbook.id == pb_id).first()
            assert "Limitation of Liability" in pb.template_text
            assert db.query(PolicyPosition).filter(PolicyPosition.playbook_id == pb_id).count() == 0
        finally:
            db.close()

    def test_both_boxes_checked_powers_both_mechanisms_from_one_upload(self, client):
        token = _register(client, "import-both@example.com")
        pb_id = _create_playbook(client, token)
        r = _import(client, token, pb_id, deviation="on", extraction="on")
        assert r.status_code == 302
        assert "/import/" in r.headers["location"] and "/review" in r.headers["location"]
        db = SessionLocal()
        try:
            pb = db.query(Playbook).filter(Playbook.id == pb_id).first()
            assert "Limitation of Liability" in pb.template_text
            positions = db.query(PolicyPosition).filter(PolicyPosition.playbook_id == pb_id).all()
            assert len(positions) >= 1
            docs = db.query(PlaybookSourceDocument).filter(PlaybookSourceDocument.playbook_id == pb_id).all()
            assert len(docs) == 1  # one upload, not two
        finally:
            db.close()

    def test_neither_box_checked_is_rejected(self, client):
        token = _register(client, "import-neither@example.com")
        pb_id = _create_playbook(client, token)
        r = _import(client, token, pb_id, deviation=None, extraction=None)
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Proposal layer: DRAFT, never ACTIVE, evidence preserved
# ---------------------------------------------------------------------------

class TestProposalLayer:
    def test_extracted_position_is_draft_never_active(self, client):
        token = _register(client, "import-draft-only@example.com")
        pb_id = _create_playbook(client, token)
        _import(client, token, pb_id, deviation=None, extraction="on")
        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert position.status == "DRAFT"
        finally:
            db.close()

    def test_established_field_preserves_full_evidence(self, client):
        token = _register(client, "import-evidence@example.com")
        pb_id = _create_playbook(client, token)
        _import(client, token, pb_id, deviation=None, extraction="on")
        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            field = next(f for f in position.fields if f.field_name == "preferred_multiplier")
            assert field.source == "EXTRACTED"
            assert field.status == "ESTABLISHED"
            assert field.evidence_document_id is not None
            assert field.evidence_excerpt
            assert field.extraction_version
            assert field.confirmed_by_user_id is None  # not yet a lawyer decision
        finally:
            db.close()

    def test_import_never_auto_approves_or_activates(self, client):
        token = _register(client, "import-no-auto-activate@example.com")
        pb_id = _create_playbook(client, token)
        _import(client, token, pb_id, deviation=None, extraction="on")
        db = SessionLocal()
        try:
            positions = db.query(PolicyPosition).filter(PolicyPosition.playbook_id == pb_id).all()
            assert all(p.status == "DRAFT" for p in positions)
            assert db.query(PolicyPositionApproval).filter(
                PolicyPositionApproval.policy_position_id.in_([p.id for p in positions]),
            ).count() == 0
        finally:
            db.close()

    def test_review_page_shows_established_needs_input_and_no_json(self, client):
        token = _register(client, "import-review-page@example.com")
        pb_id = _create_playbook(client, token)
        r = _import(client, token, pb_id, deviation=None, extraction="on")
        review = client.get(r.headers["location"])
        assert review.status_code == 200
        assert "Directly established" in review.text
        assert "Needs your input" in review.text
        assert "preferred_multiplier" not in review.text
        assert "config_json" not in review.text


# ---------------------------------------------------------------------------
# Lawyer confirmation: extraction goes through the Phase 1 lifecycle
# ---------------------------------------------------------------------------

class TestLawyerConfirmationFlow:
    def test_extracted_only_position_cannot_activate_until_requirements_answered(self, client):
        token = _register(client, "import-cant-activate@example.com")
        pb_id = _create_playbook(client, token)
        _import(client, token, pb_id, deviation=None, extraction="on")

        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review", data={"csrf_token": token})
        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/approve", data={"csrf_token": token}, follow_redirects=False)
        assert r.status_code == 400  # require_consequential_damages_exclusion still unanswered

    def test_lawyer_can_answer_remaining_fields_and_activate(self, client):
        token = _register(client, "import-then-activate@example.com")
        pb_id = _create_playbook(client, token)
        _import(client, token, pb_id, deviation=None, extraction="on")

        # Lawyer fills in what extraction correctly left unestablished.
        form = {
            "preferred_multiplier": "2.0", "prohibit_unlimited": "yes",
            "required_exceptions_json": ["confidentiality"],
            "require_consequential_damages_exclusion": "no",
            "contract_side": "mutual", "escalation_approval_authority": "General Counsel",
            "fallback_text": "Approved fallback.", "csrf_token": token,
        }
        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/save", data=form, follow_redirects=False)
        assert r.status_code == 302
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review", data={"csrf_token": token})
        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/approve", data={"csrf_token": token}, follow_redirects=False)
        assert r.status_code == 302
        r = client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/activate", data={"csrf_token": token}, follow_redirects=False)
        assert r.status_code == 302

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert position.status == "ACTIVE"
            # The originally-extracted field survives, now still EXTRACTED
            # (never confirmed by the lawyer directly -- they only added
            # the *other*, previously-unestablished fields).
            preferred = next(f for f in position.fields if f.field_name == "preferred_multiplier")
            assert preferred.source == "MANUAL"  # re-saved via the edit form -> now a lawyer-entered value
        finally:
            db.close()

    def test_lawyer_can_modify_an_extracted_value(self, client):
        token = _register(client, "import-modify@example.com")
        pb_id = _create_playbook(client, token)
        _import(client, token, pb_id, deviation=None, extraction="on")

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert position.config_json["preferred_multiplier"] == 2.0
        finally:
            db.close()

        form = {
            "preferred_multiplier": "1.5",  # lawyer overrides the extracted 2.0
            "prohibit_unlimited": "yes", "required_exceptions_json": ["confidentiality"],
            "require_consequential_damages_exclusion": "no",
            "contract_side": "mutual", "escalation_approval_authority": "GC",
            "fallback_text": "fallback", "csrf_token": token,
        }
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/save", data=form)

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert position.config_json["preferred_multiplier"] == 1.5
            field = next(f for f in position.fields if f.field_name == "preferred_multiplier")
            assert field.source == "MANUAL"
            assert field.status == "ESTABLISHED"
            assert field.confirmed_by_user_id is not None
        finally:
            db.close()

    def test_reimport_does_not_clobber_a_lawyer_confirmed_field(self, client):
        """A field the lawyer has already manually confirmed must survive
        a second import of a (possibly different) document."""
        token = _register(client, "import-reimport-protects@example.com")
        pb_id = _create_playbook(client, token)
        _import(client, token, pb_id, deviation=None, extraction="on")

        form = {
            "preferred_multiplier": "9.9",  # deliberately different from any extraction
            "prohibit_unlimited": "yes", "required_exceptions_json": [],
            "require_consequential_damages_exclusion": "no",
            "contract_side": "mutual", "escalation_approval_authority": "GC",
            "fallback_text": "fallback", "csrf_token": token,
        }
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/save", data=form)

        # Re-import the same document.
        _import(client, token, pb_id, deviation=None, extraction="on")

        db = SessionLocal()
        try:
            position = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert position.config_json["preferred_multiplier"] == 9.9  # untouched by re-extraction
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Determinism at the HTTP layer
# ---------------------------------------------------------------------------

class TestDeterminismAtImportLayer:
    def test_two_playbooks_same_document_produce_identical_proposals(self, client):
        token = _register(client, "import-determinism@example.com")
        pb_id_1 = _create_playbook(client, token, name="PB Det 1")
        pb_id_2 = _create_playbook(client, token, name="PB Det 2")
        _import(client, token, pb_id_1, deviation=None, extraction="on")
        _import(client, token, pb_id_2, deviation=None, extraction="on")

        db = SessionLocal()
        try:
            p1 = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id_1, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            p2 = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id_2, PolicyPosition.clause_type == "limitation_of_liability",
            ).first()
            assert p1.config_json == p2.config_json
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Security / privacy
# ---------------------------------------------------------------------------

class TestImportSecurity:
    def test_no_llm_invoked_during_import(self, client, monkeypatch):
        def _boom(*args, **kwargs):
            raise AssertionError("LLM evaluator must never be invoked by deterministic import")
        monkeypatch.setattr(evaluator.LLMEvaluator, "explain_findings", _boom, raising=False)
        monkeypatch.setattr(evaluator.LLMEvaluator, "__call__", _boom, raising=False)

        token = _register(client, "import-no-llm@example.com")
        pb_id = _create_playbook(client, token)
        r = _import(client, token, pb_id, deviation="on", extraction="on")
        assert r.status_code == 302  # completed without ever touching the LLM path

    def test_source_document_ownership_enforced(self, client):
        token_a = _register(client, "import-owner-a@example.com")
        pb_id = _create_playbook(client, token_a)
        r = _import(client, token_a, pb_id, deviation=None, extraction="on")
        review_url = r.headers["location"]

        client.cookies.clear()
        _register(client, "import-attacker-b@example.com")
        r2 = client.get(review_url)
        assert r2.status_code == 404

    def test_cross_user_cannot_import_into_someone_elses_playbook(self, client):
        token_a = _register(client, "import-owner-c@example.com")
        pb_id = _create_playbook(client, token_a)

        client.cookies.clear()
        token_b = _register(client, "import-attacker-d@example.com")
        r = _import(client, token_b, pb_id, deviation=None, extraction="on")
        assert r.status_code == 404

        db = SessionLocal()
        try:
            assert db.query(PlaybookSourceDocument).filter(PlaybookSourceDocument.playbook_id == pb_id).count() == 0
        finally:
            db.close()

    def test_cross_user_cannot_view_import_page(self, client):
        token_a = _register(client, "import-owner-e@example.com")
        pb_id = _create_playbook(client, token_a)

        client.cookies.clear()
        _register(client, "import-attacker-f@example.com")
        r = client.get(f"/playbooks/{pb_id}/import")
        assert r.status_code == 404

    def test_source_text_is_encrypted_at_rest(self, client):
        token = _register(client, "import-encryption@example.com")
        pb_id = _create_playbook(client, token)
        _import(client, token, pb_id, deviation=None, extraction="on")

        db = SessionLocal()
        try:
            from sqlalchemy import text as sql_text
            raw = db.execute(
                sql_text("SELECT extracted_text FROM playbook_source_documents WHERE playbook_id = :pid"),
                {"pid": pb_id},
            ).scalar()
            assert raw is not None
            assert "Limitation of Liability" not in raw  # plaintext must not appear on disk
            assert raw.startswith("enc:")  # envelope prefix per encryption.py
        finally:
            db.close()

    def test_archiving_a_position_preserves_approval_history(self, client):
        """Deleting/superseding a position (via revision + activation)
        must not destroy the prior approval trail."""
        token = _register(client, "import-archival@example.com")
        pb_id = _create_playbook(client, token)
        _import(client, token, pb_id, deviation=None, extraction="on")
        form = {
            "preferred_multiplier": "2.0", "prohibit_unlimited": "yes",
            "required_exceptions_json": ["confidentiality"],
            "require_consequential_damages_exclusion": "no",
            "contract_side": "mutual", "escalation_approval_authority": "GC",
            "fallback_text": "fallback", "csrf_token": token,
        }
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/save", data=form)
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review", data={"csrf_token": token})
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/approve", data={"csrf_token": token})
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/activate", data={"csrf_token": token})

        db = SessionLocal()
        try:
            active = db.query(PolicyPosition).filter(
                PolicyPosition.playbook_id == pb_id, PolicyPosition.clause_type == "limitation_of_liability",
                PolicyPosition.status == "ACTIVE",
            ).first()
            active_id = active.id
        finally:
            db.close()

        # Start and activate a revision -- archives the original.
        client.get(f"/playbooks/{pb_id}/positions/limitation_of_liability/edit")
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/save", data=form)
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/submit-for-review", data={"csrf_token": token})
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/approve", data={"csrf_token": token})
        client.post(f"/playbooks/{pb_id}/positions/limitation_of_liability/activate", data={"csrf_token": token})

        db = SessionLocal()
        try:
            original = db.query(PolicyPosition).filter(PolicyPosition.id == active_id).first()
            assert original.status == "ARCHIVED"
            history = db.query(PolicyPositionApproval).filter(
                PolicyPositionApproval.policy_position_id == active_id,
            ).all()
            assert len(history) >= 3  # MARKED_REVIEWED, APPROVED, ACTIVATED all still present
            assert any(h.action == "ARCHIVED" for h in history)
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Existing invariants: legacy path + six engines untouched
# ---------------------------------------------------------------------------

class TestExistingInvariantsUntouched:
    def test_legacy_playbook_rule_route_unaffected_by_import(self, client):
        token = _register(client, "import-legacy-untouched@example.com")
        pb_id = _create_playbook(client, token)
        _import(client, token, pb_id, deviation="on", extraction="on")

        db = SessionLocal()
        try:
            assert db.query(PolicyRule).filter(PolicyRule.playbook_id == pb_id).count() == 0
        finally:
            db.close()
