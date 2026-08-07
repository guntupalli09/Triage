"""
Tests for encryption.EncryptedJSON (P2b — extends AES-256-GCM encryption
at rest to the JSON analysis columns that can embed verbatim contract
excerpts: findings_json, llm_result_json, deviations_json,
review_decisions_json, structure_report_json, clause_quality_json,
metadata_json, risk_balance_json, payment_terms_json,
blocking_findings_json, policy_blocked_findings_json, risk_dashboard_json,
Playbook.template_findings_json).
"""
import base64
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DEV_MODE", "true")

import encryption
from database import Base
from models import Contract, Playbook, User
import analytics_models  # noqa: F401


def _key(byte: bytes = b"k") -> str:
    return base64.b64encode(byte * 32).decode("ascii")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_KEYS", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY_CURRENT", raising=False)


# --- Unit: encryption.EncryptedJSON's underlying encrypt/decrypt of JSON text ---

def test_json_value_roundtrips_through_encrypt_decrypt(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{_key()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    import json
    payload = {"rule_id": "r1", "matched_excerpt": "Confidential terms apply", "severity": "high"}
    ciphertext = encryption.encrypt(json.dumps(payload))
    assert ciphertext.startswith("enc:v1:")
    assert json.loads(encryption.decrypt(ciphertext)) == payload


# --- DB-level integration ---

@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{base64.b64encode(b'a' * 32).decode()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")
    engine = create_engine(f"sqlite:///{tmp_path / 'encjson_test.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session, engine
    finally:
        session.close()


def _make_user(session) -> User:
    user = User(email="firm@example.com", password_hash="x")
    session.add(user)
    session.commit()
    return user


def _raw_column(engine, table: str, column: str, row_id: int):
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT {column} FROM {table} WHERE id = :id"), {"id": row_id}).scalar()


def test_findings_json_encrypted_on_disk_and_transparent_on_read(db_session):
    session, engine = db_session
    user = _make_user(session)
    findings = [{"rule_id": "r1", "matched_excerpt": "Acme Corp shall indemnify Beta LLC", "severity": "high"}]
    contract = Contract(user_id=user.id, filename="nda.pdf", contract_text="text", findings_json=findings)
    session.add(contract)
    session.commit()

    raw = _raw_column(engine, "contracts", "findings_json", contract.id)
    assert raw.startswith("enc:v1:")
    assert "Acme Corp" not in raw

    session.expire_all()
    reloaded = session.query(Contract).filter(Contract.id == contract.id).first()
    assert reloaded.findings_json == findings


def test_multiple_encrypted_json_columns_all_encrypted(db_session):
    session, engine = db_session
    user = _make_user(session)
    contract = Contract(
        user_id=user.id, filename="nda.pdf", contract_text="text",
        llm_result_json={"summary_bullets": ["Acme Corp retains broad indemnification rights"]},
        metadata_json={"party_a": "Acme Corp", "party_b": "Beta LLC"},
        review_decisions_json={"r1#0": {"action": "edited", "edited_text": "Acme shall not be liable"}},
    )
    session.add(contract)
    session.commit()

    for col in ("llm_result_json", "metadata_json", "review_decisions_json"):
        raw = _raw_column(engine, "contracts", col, contract.id)
        assert raw.startswith("enc:v1:")
        assert "Acme" not in raw

    session.expire_all()
    reloaded = session.query(Contract).filter(Contract.id == contract.id).first()
    assert reloaded.metadata_json == {"party_a": "Acme Corp", "party_b": "Beta LLC"}
    assert reloaded.review_decisions_json["r1#0"]["edited_text"] == "Acme shall not be liable"


def test_rule_counts_json_stays_plain_json_not_encrypted(db_session):
    """rule_counts_json is just severity counts, no contract text — it
    deliberately stays a plain JSON column, not EncryptedJSON."""
    session, engine = db_session
    user = _make_user(session)
    contract = Contract(
        user_id=user.id, filename="nda.pdf", contract_text="text",
        rule_counts_json={"high": 2, "medium": 1, "low": 0},
    )
    session.add(contract)
    session.commit()

    raw = _raw_column(engine, "contracts", "rule_counts_json", contract.id)
    assert not raw.startswith("enc:v1:")
    assert "high" in raw  # plain JSON text


def test_null_json_value_stored_as_null(db_session):
    session, engine = db_session
    user = _make_user(session)
    contract = Contract(user_id=user.id, filename="nda.pdf", contract_text="text", findings_json=None)
    session.add(contract)
    session.commit()

    raw = _raw_column(engine, "contracts", "findings_json", contract.id)
    assert raw is None

    session.expire_all()
    reloaded = session.query(Contract).filter(Contract.id == contract.id).first()
    assert reloaded.findings_json is None


def test_legacy_plaintext_json_reads_correctly(db_session):
    """Simulates a row written before EncryptedJSON existed: raw JSON text
    in the column, no envelope prefix."""
    session, engine = db_session
    user = _make_user(session)
    contract = Contract(user_id=user.id, filename="nda.pdf", contract_text="text", findings_json={"placeholder": True})
    session.add(contract)
    session.commit()
    contract_id = contract.id

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE contracts SET findings_json = :v WHERE id = :id"),
            {"v": '{"rule_id": "legacy_rule", "matched_excerpt": "legacy plaintext excerpt"}', "id": contract_id},
        )

    session.expire_all()
    reloaded = session.query(Contract).filter(Contract.id == contract_id).first()
    assert reloaded.findings_json == {"rule_id": "legacy_rule", "matched_excerpt": "legacy plaintext excerpt"}


def test_malformed_encrypted_json_envelope_fails_closed(db_session):
    session, engine = db_session
    user = _make_user(session)
    contract = Contract(user_id=user.id, filename="nda.pdf", contract_text="text", findings_json={"a": 1})
    session.add(contract)
    session.commit()
    contract_id = contract.id

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE contracts SET findings_json = :v WHERE id = :id"),
            {"v": "enc:v1:corrupted:garbage:notreal", "id": contract_id},
        )

    session.expire_all()
    # SQLAlchemy applies the column result-processor while materializing
    # the row itself (not lazily on attribute access), so the query call
    # is where this raises.
    with pytest.raises(encryption.DecryptionError):
        session.query(Contract).filter(Contract.id == contract_id).first()


def test_playbook_template_findings_json_encrypted(db_session):
    session, engine = db_session
    user = _make_user(session)
    playbook = Playbook(
        user_id=user.id, name="Standard NDA", template_text="template",
        template_findings_json=[{"rule_id": "r1", "matched_excerpt": "Confidential info of Acme Corp"}],
    )
    session.add(playbook)
    session.commit()

    raw = _raw_column(engine, "playbooks", "template_findings_json", playbook.id)
    assert raw.startswith("enc:v1:")

    session.expire_all()
    reloaded = session.query(Playbook).filter(Playbook.id == playbook.id).first()
    assert reloaded.template_findings_json[0]["rule_id"] == "r1"


def test_key_rotation_works_for_json_columns_too(db_session, monkeypatch):
    session, engine = db_session
    user = _make_user(session)
    contract = Contract(user_id=user.id, filename="nda.pdf", contract_text="text", findings_json={"a": "rotate-me"})
    session.add(contract)
    session.commit()
    contract_id = contract.id

    monkeypatch.setenv(
        "ENCRYPTION_KEYS",
        f"k1:{base64.b64encode(b'a' * 32).decode()},k2:{base64.b64encode(b'b' * 32).decode()}",
    )
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k2")

    session.expire_all()
    reloaded = session.query(Contract).filter(Contract.id == contract_id).first()
    assert reloaded.findings_json == {"a": "rotate-me"}
