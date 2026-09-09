"""
Regression tests for AI import provenance FK persistence.

Reproduces production failure: source_document.id assigned after flush,
transaction rolled back, field rows still reference the stale id.
"""
from __future__ import annotations

import io
import json
import os
import re
import uuid

os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

import main
import playbook_ai_extraction as pai
import rate_limit
from database import SessionLocal, engine, init_db
from models import (
    Playbook,
    PlaybookSourceDocument,
    PolicyPosition,
    PolicyPositionField,
    User,
)

PLAYBOOK_TEXT = (
    b"Limitation of Liability. Our preferred liability cap is 1x fees paid in the prior 12 months. "
    b"Indemnification. Each party shall indemnify the other for third-party claims. "
    b"Termination. Either party may terminate with 30 days written notice."
)


_CLAUSE_TYPE_RE = re.compile(r"Clause type:\s*(\S+)")


class MultiClauseClient:
    model_name = "test-model"

    def complete(self, system_prompt, user_prompt):
        match = _CLAUSE_TYPE_RE.search(user_prompt)
        clause_type = match.group(1) if match else ""
        if clause_type == "indemnification":
            candidates = [
                {"field_name": "prohibit_uncapped_exposure", "value": True,
                 "quote": "Each party shall indemnify the other", "basis": "EXTRACTED"},
            ]
        elif clause_type == "termination":
            candidates = [
                {"field_name": "min_notice_days_against_us", "value": 30,
                 "quote": "terminate with 30 days written notice", "basis": "EXTRACTED"},
            ]
        else:
            candidates = [
                {"field_name": "preferred_multiplier", "value": 1.0,
                 "quote": "preferred liability cap is 1x fees paid in the prior 12 months", "basis": "EXTRACTED"},
            ]
        return pai.LLMCallResult(
            raw_text=json.dumps({"candidates": candidates}),
            input_tokens=10, output_tokens=5, latency_ms=1.0,
        )


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    rate_limit._memory_counters.clear()
    yield
    rate_limit._memory_counters.clear()


@pytest.fixture(autouse=True)
def _ai_import_enabled(monkeypatch):
    monkeypatch.setenv("AI_ASSISTED_IMPORT_ENABLED", "true")


@pytest.fixture(autouse=True)
def _fake_llm_client(monkeypatch):
    monkeypatch.setattr(pai, "OpenAIExtractionClient", MultiClauseClient)


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture(autouse=True)
def _sqlite_foreign_keys():
    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield


def _register(client: TestClient) -> str:
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    email = f"prov-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/register",
        data={
            "email": email,
            "password": "Str0ngP@ssw0rd!",
            "confirm_password": "Str0ngP@ssw0rd!",
            "name": "Firm",
            "company": "",
            "accept_terms": "on",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.plan = "professional"
        db.commit()
    finally:
        db.close()
    return client.cookies.get("csrf_token")


def _create_playbook(client: TestClient, token: str) -> int:
    r = client.post(
        "/playbooks/new",
        data={
            "name": f"Provenance Test {uuid.uuid4().hex[:6]}",
            "contract_type": "",
            "description": "",
            "lol_enabled": "",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    db = SessionLocal()
    try:
        pb = db.query(Playbook).order_by(Playbook.id.desc()).first()
        return pb.id
    finally:
        db.close()


def _ai_import(client, token, playbook_id, *, content=PLAYBOOK_TEXT):
    files = {"file": ("playbook.txt", io.BytesIO(content), "text/plain")}
    return client.post(
        f"/playbooks/{playbook_id}/ai-import",
        data={"csrf_token": token, "consent": "on"},
        files=files,
        follow_redirects=False,
    )


class TestAIImportProvenancePersistence:
    def test_multi_clause_import_commits_source_document_and_provenance(self, client):
        token = _register(client)
        pb_id = _create_playbook(client, token)
        r = _ai_import(client, token, pb_id)
        assert r.status_code == 302
        assert "/workbench" in r.headers["location"]
        assert "imported=" in r.headers["location"]

        db = SessionLocal()
        try:
            docs = db.query(PlaybookSourceDocument).filter(PlaybookSourceDocument.playbook_id == pb_id).all()
            assert len(docs) == 1
            doc = docs[0]
            positions = db.query(PolicyPosition).filter(PolicyPosition.playbook_id == pb_id).all()
            assert len(positions) >= 2
            fields = (
                db.query(PolicyPositionField)
                .join(PolicyPosition)
                .filter(PolicyPosition.playbook_id == pb_id)
                .all()
            )
            assert fields
            provenance_ids = {f.evidence_document_id for f in fields if f.evidence_document_id is not None}
            assert provenance_ids == {doc.id}
            lol = next(p for p in positions if p.clause_type == "limitation_of_liability")
            if lol.policy_schema_version == 2:
                assert lol.rules_v2_json
        finally:
            db.close()

    def test_import_survives_stale_source_document_id_after_rollback(self, client, monkeypatch):
        """Production repro: flush assigns id, rollback clears row, import must recover."""
        token = _register(client)
        pb_id = _create_playbook(client, token)

        original_ensure = pai.pip.ensure_source_document_persisted
        call_count = {"n": 0}

        def _ensure_with_simulated_rollback(db, source_document):
            call_count["n"] += 1
            if call_count["n"] == 1:
                db.add(source_document)
                db.flush()
                stale_id = source_document.id
                db.rollback()
                assert source_document.id == stale_id
                assert db.get(PlaybookSourceDocument, stale_id) is None
            return original_ensure(db, source_document)

        monkeypatch.setattr(pai.pip, "ensure_source_document_persisted", _ensure_with_simulated_rollback)

        r = _ai_import(client, token, pb_id)
        assert r.status_code == 302, r.text[:500]

        db = SessionLocal()
        try:
            doc = db.query(PlaybookSourceDocument).filter(PlaybookSourceDocument.playbook_id == pb_id).one()
            fields = (
                db.query(PolicyPositionField)
                .join(PolicyPosition)
                .filter(PolicyPosition.playbook_id == pb_id)
                .filter(PolicyPositionField.evidence_document_id.isnot(None))
                .all()
            )
            assert fields
            assert all(f.evidence_document_id == doc.id for f in fields)
        finally:
            db.close()

    def test_failed_import_rolls_back_all_partial_state(self, client, monkeypatch):
        token = _register(client)
        pb_id = _create_playbook(client, token)

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated mid-import failure")

        monkeypatch.setattr(pai, "import_ai_playbook", _boom)

        r = _ai_import(client, token, pb_id)
        assert r.status_code == 400

        db = SessionLocal()
        try:
            assert db.query(PlaybookSourceDocument).filter(PlaybookSourceDocument.playbook_id == pb_id).count() == 0
            assert db.query(PolicyPosition).filter(PolicyPosition.playbook_id == pb_id).count() == 0
            assert (
                db.query(PolicyPositionField)
                .join(PolicyPosition)
                .filter(PolicyPosition.playbook_id == pb_id)
                .count()
                == 0
            )
        finally:
            db.close()
