"""
Regression tests for clause-isolated fallback/provenance during AI import.

Ensures Limitation of Liability fallback/redline language never attaches to
Indemnification (or other) PolicyPosition rows when importing a multi-clause
playbook in one run.
"""
from __future__ import annotations

import json
import os
import re
import uuid

os.environ.setdefault("DEV_MODE", "true")

import pytest

import playbook_ai_extraction as pai
from database import SessionLocal, init_db
from models import Playbook, PlaybookSourceDocument, PolicyPosition, User

# Commercial Contract Review Playbook — representative multi-clause fixture.
COMMERCIAL_PLAYBOOK_TEXT = (
    "Commercial Contract Review Playbook — customer-side SaaS guidance.\n\n"
    "2. Limitation of Liability\n"
    "Preferred Position\n"
    "Vendor liability should be capped at the greater of:\n"
    "fees paid or payable under the agreement during the 12 months preceding the event giving rise to the claim, or\n"
    "$1,000,000.\n"
    "Acceptable Fallback\n"
    "A general liability cap equal to 12 months of fees may be accepted without escalation for agreements "
    "with annual contract value below $250,000.\n"
    "For contracts above $250,000 in annual value, a cap below 12 months of fees requires partner approval.\n"
    "Exclusions From the General Cap\n"
    "breach of confidentiality; infringement or misappropriation of intellectual property rights; "
    "vendor indemnification obligations; fraud; gross negligence or willful misconduct; "
    "violations of applicable data-protection laws caused by the vendor.\n"
    "For confidentiality and data-security claims, a super-cap of at least 2× the general liability cap is acceptable.\n"
    "Hard Stop\n"
    "Do not accept a liability cap of less than six months of fees.\n\n"
    "3. Indemnification\n"
    "Preferred Position\n"
    "Vendor shall indemnify, defend, and hold harmless Customer against third-party claims arising from "
    "Vendor's negligence, IP infringement, and data breaches caused by Vendor.\n"
    "Our exposure to the counterparty must remain third-party claims only and capped at 1x annual fees.\n"
    "Never accept uncapped vendor indemnity exposure.\n\n"
    "4. Termination\n"
    "Either party may terminate for convenience with 60 days written notice.\n"
    "Termination for cause requires a 30-day cure period.\n\n"
    "5. Confidentiality\n"
    "Mutual confidentiality obligations must survive for at least 5 years.\n"
    "Standard exclusions (public knowledge, independently developed) are required.\n\n"
    "6. Payment Terms\n"
    "Counterparty must pay Net 30 from receipt of invoice.\n"
    "Undisputed amounts remain payable during any dispute.\n\n"
    "7. Data Protection\n"
    "Vendor must maintain appropriate technical and organizational security measures.\n"
    "Vendor-caused security incidents require prompt notification.\n"
)

_LIABILITY_BLEED_PHRASES = (
    "12 months",
    "$250,000",
    "general liability cap",
    "Exclusions From the General Cap",
)

_CLAUSE_TYPE_RE = re.compile(r"Clause type:\s*(\S+)")


class CommercialPlaybookClient:
    """Simulated LLM returning minimal established fields per clause type."""

    model_name = "test-model"

    def complete(self, system_prompt, user_prompt):
        match = _CLAUSE_TYPE_RE.search(user_prompt)
        clause_type = match.group(1) if match else ""
        candidates = []
        if clause_type == "limitation_of_liability":
            candidates = [
                {"field_name": "acceptable_max_multiplier", "value": 12.0,
                 "quote": "A general liability cap equal to 12 months of fees may be accepted without escalation for agreements with annual contract value below $250,000.",
                 "basis": "EXTRACTED"},
                {"field_name": "prohibit_unlimited", "value": True,
                 "quote": "Do not accept a liability cap of less than six months of fees.", "basis": "EXTRACTED"},
            ]
        elif clause_type == "indemnification":
            candidates = [
                {"field_name": "prohibit_uncapped_exposure", "value": True,
                 "quote": "Never accept uncapped vendor indemnity exposure.", "basis": "EXTRACTED"},
                {"field_name": "require_exposure_third_party_only", "value": True,
                 "quote": "Our exposure to the counterparty must remain third-party claims only", "basis": "EXTRACTED"},
            ]
        elif clause_type == "termination":
            candidates = [
                {"field_name": "min_notice_days_against_us", "value": 60,
                 "quote": "terminate for convenience with 60 days written notice", "basis": "EXTRACTED"},
            ]
        elif clause_type == "confidentiality":
            candidates = [
                {"field_name": "min_protection_duration_years", "value": 5,
                 "quote": "Mutual confidentiality obligations must survive for at least 5 years", "basis": "EXTRACTED"},
            ]
        elif clause_type == "payment_terms":
            candidates = [
                {"field_name": "preferred_net_days", "value": 30,
                 "quote": "Counterparty must pay Net 30 from receipt of invoice", "basis": "EXTRACTED"},
            ]
        elif clause_type == "data_security":
            candidates = [
                {"field_name": "require_security_measures", "value": True,
                 "quote": "Vendor must maintain appropriate technical and organizational security measures", "basis": "EXTRACTED"},
            ]
        return pai.LLMCallResult(
            raw_text=json.dumps({"candidates": candidates}),
            input_tokens=10, output_tokens=5, latency_ms=1.0,
        )


@pytest.fixture(autouse=True)
def _ai_import_enabled(monkeypatch):
    monkeypatch.setenv("AI_ASSISTED_IMPORT_ENABLED", "true")


@pytest.fixture()
def db_session():
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def playbook(db_session):
    user = User(
        email=f"isolation-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
    )
    db_session.add(user)
    db_session.flush()
    pb = Playbook(user_id=user.id, name="Commercial Contract Review Playbook", template_text="")
    db_session.add(pb)
    db_session.commit()
    return pb


def _import_commercial_playbook(db, playbook, user):
    doc = PlaybookSourceDocument(
        playbook_id=playbook.id,
        uploaded_by_user_id=user.id,
        document_type="playbook_guideline",
        original_filename="commercial-playbook.txt",
        extracted_text=COMMERCIAL_PLAYBOOK_TEXT,
        use_for_policy_extraction=True,
    )
    db.add(doc)
    db.flush()
    return pai.import_ai_playbook(
        db, playbook, doc, user, consent=True, client=CommercialPlaybookClient(),
    )


class TestClauseScopedFallbackInference:
    def test_padded_indemnification_window_excludes_lol_fallback(self):
        """Root-cause repro: LoL Acceptable Fallback sits inside padded indem window."""
        sections = pai.discover_relevant_sections(COMMERCIAL_PLAYBOOK_TEXT)
        indem_sections = sections["indemnification"]
        assert indem_sections, "fixture must discover an indemnification section"
        raw_texts = [s.text for s in indem_sections if s.text]
        combined_raw = "\n".join(raw_texts)
        assert "Acceptable Fallback" in combined_raw
        assert "general liability cap" in combined_raw

        scoped = pai._clause_scoped_section_texts(raw_texts, "indemnification")
        scoped_combined = "\n".join(scoped)
        assert "Acceptable Fallback" not in scoped_combined
        assert "general liability cap" not in scoped_combined

        fallback, _ = pai._infer_fallback_text(raw_texts, "indemnification")
        assert fallback is None

    def test_lol_fallback_still_found_for_liability_clause(self):
        sections = pai.discover_relevant_sections(COMMERCIAL_PLAYBOOK_TEXT)
        lol_texts = [s.text for s in sections["limitation_of_liability"] if s.text]
        fallback, evidence = pai._infer_fallback_text(lol_texts, "limitation_of_liability")
        assert fallback is not None
        assert evidence is not None
        assert "12 months" in fallback
        assert "$250,000" in fallback or "250,000" in fallback
        assert "general liability cap" in fallback.lower()


class TestCrossClauseFallbackPersistence:
    def test_import_all_clauses_isolates_fallback_text(self, db_session, playbook):
        user = db_session.query(User).filter(User.id == playbook.user_id).one()
        results, _report = _import_commercial_playbook(db_session, playbook, user)
        db_session.commit()

        lol: PolicyPosition = results["limitation_of_liability"]
        indem: PolicyPosition = results["indemnification"]

        assert lol.fallback_text
        assert "12 months" in lol.fallback_text
        assert "$250,000" in lol.fallback_text or "250,000" in lol.fallback_text

        assert not indem.fallback_text, (
            f"Indemnification must not inherit LoL fallback; got: {indem.fallback_text!r}"
        )
        for phrase in _LIABILITY_BLEED_PHRASES:
            assert phrase not in (indem.fallback_text or "")

        for clause_type in ("termination", "confidentiality", "payment_terms", "data_security"):
            pos = results.get(clause_type)
            if pos is None:
                continue
            fb = pos.fallback_text or ""
            for phrase in _LIABILITY_BLEED_PHRASES:
                assert phrase not in fb, f"{clause_type} leaked LoL fallback: {fb!r}"

    def test_clause_a_fallback_cannot_persist_on_clause_b(self, db_session, playbook):
        """Generic isolation: LoL fallback metadata cannot attach to Indemnification."""
        user = db_session.query(User).filter(User.id == playbook.user_id).one()
        sections = pai.discover_relevant_sections(COMMERCIAL_PLAYBOOK_TEXT)
        lol_texts = [s.text for s in sections["limitation_of_liability"] if s.text]
        lol_fallback, lol_evidence = pai._infer_fallback_text(lol_texts, "limitation_of_liability")
        assert lol_fallback

        position, _ = __import__("playbook_authoring").get_or_build_editable_position(
            db_session, playbook, "indemnification",
        )
        indem_sections = [s.text for s in sections["indemnification"] if s.text]
        doc = PlaybookSourceDocument(
            playbook_id=playbook.id,
            uploaded_by_user_id=user.id,
            document_type="playbook_guideline",
            original_filename="x.txt",
            extracted_text=COMMERCIAL_PLAYBOOK_TEXT,
            use_for_policy_extraction=True,
        )
        db_session.add(doc)
        db_session.flush()

        # Even if a caller mistakenly passes LoL fallback in metadata, persistence
        # re-derives fallback only from the indemnification section span.
        pai._apply_position_metadata(
            db_session, position,
            {"fallback_text": lol_fallback, "fallback_evidence_excerpt": lol_evidence},
            doc, user,
            clause_type="indemnification", section_texts=indem_sections,
        )
        db_session.commit()
        assert not position.fallback_text
