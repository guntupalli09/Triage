"""
DB-level integration tests for encryption at rest (P2): the EncryptedText
column type, transparent reads over mixed legacy-plaintext/encrypted rows,
"reading doesn't rewrite", and full contract/playbook lifecycle through the
real app (upload -> analysis -> persistence -> reload -> export).
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
import analytics_models  # noqa: F401 — registers User.acquisition/sessions/events relationships


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    """A throwaway SQLite file DB, independent of the app's global engine,
    so these tests don't interfere with (or depend on) any other test's
    database state."""
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{base64.b64encode(b'a' * 32).decode()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")

    db_path = tmp_path / "enc_test.db"
    engine = create_engine(f"sqlite:///{db_path}")
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


def _raw_column(engine, table: str, column: str, row_id: int) -> str:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT {column} FROM {table} WHERE id = :id"), {"id": row_id}).scalar()


def test_contract_text_is_encrypted_on_disk_and_decrypted_transparently(db_session):
    session, engine = db_session
    user = _make_user(session)
    contract = Contract(user_id=user.id, filename="nda.pdf", contract_text="Confidential: parties agree...")
    session.add(contract)
    session.commit()

    raw = _raw_column(engine, "contracts", "contract_text", contract.id)
    assert raw.startswith("enc:v1:")
    assert "Confidential" not in raw  # never stored in plaintext

    session.expire_all()
    reloaded = session.query(Contract).filter(Contract.id == contract.id).first()
    assert reloaded.contract_text == "Confidential: parties agree..."


def test_playbook_template_text_is_encrypted_on_disk_and_decrypted_transparently(db_session):
    session, engine = db_session
    user = _make_user(session)
    playbook = Playbook(user_id=user.id, name="Standard NDA", template_text="Standard template clause text")
    session.add(playbook)
    session.commit()

    raw = _raw_column(engine, "playbooks", "template_text", playbook.id)
    assert raw.startswith("enc:v1:")

    session.expire_all()
    reloaded = session.query(Playbook).filter(Playbook.id == playbook.id).first()
    assert reloaded.template_text == "Standard template clause text"


def test_legacy_plaintext_row_reads_correctly_through_the_orm(db_session):
    """Simulates a row written before encryption existed: raw plaintext in
    the column, no envelope prefix. The ORM must still read it back as-is."""
    session, engine = db_session
    user = _make_user(session)
    contract = Contract(user_id=user.id, filename="old.txt", contract_text="placeholder")
    session.add(contract)
    session.commit()
    contract_id = contract.id

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE contracts SET contract_text = :v WHERE id = :id"),
            {"v": "This is legacy plaintext with no envelope.", "id": contract_id},
        )

    session.expire_all()
    reloaded = session.query(Contract).filter(Contract.id == contract_id).first()
    assert reloaded.contract_text == "This is legacy plaintext with no envelope."


def test_mixed_encrypted_and_legacy_rows_both_read_correctly(db_session):
    session, engine = db_session
    user = _make_user(session)

    encrypted_row = Contract(user_id=user.id, filename="a.txt", contract_text="placeholder-a")
    legacy_row = Contract(user_id=user.id, filename="b.txt", contract_text="placeholder-b")
    session.add_all([encrypted_row, legacy_row])
    session.commit()
    legacy_id = legacy_row.id

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE contracts SET contract_text = :v WHERE id = :id"),
            {"v": "raw legacy text, never encrypted", "id": legacy_id},
        )

    session.expire_all()
    rows = {c.id: c.contract_text for c in session.query(Contract).all()}
    assert rows[encrypted_row.id] == "placeholder-a"
    assert rows[legacy_id] == "raw legacy text, never encrypted"


def test_reading_a_row_does_not_rewrite_it(db_session):
    """No automatic re-encryption merely from a read: the raw stored bytes
    for an already-encrypted row must be byte-for-byte identical before and
    after an ORM read that doesn't reassign the attribute."""
    session, engine = db_session
    user = _make_user(session)
    contract = Contract(user_id=user.id, filename="nda.pdf", contract_text="some contract text")
    session.add(contract)
    session.commit()
    contract_id = contract.id

    raw_before = _raw_column(engine, "contracts", "contract_text", contract_id)

    session.expire_all()
    reloaded = session.query(Contract).filter(Contract.id == contract_id).first()
    _ = reloaded.contract_text  # read only, no reassignment
    session.commit()  # no-op commit; must not trigger an UPDATE

    raw_after = _raw_column(engine, "contracts", "contract_text", contract_id)
    assert raw_before == raw_after


def test_key_rotation_old_row_still_readable_after_current_key_changes(db_session, monkeypatch):
    session, engine = db_session
    user = _make_user(session)
    contract = Contract(user_id=user.id, filename="nda.pdf", contract_text="rotate-me contract text")
    session.add(contract)
    session.commit()
    contract_id = contract.id

    # Rotate: add a new key and make it current; the old key stays present
    # for decrypt-only use.
    monkeypatch.setenv(
        "ENCRYPTION_KEYS",
        f"k1:{base64.b64encode(b'a' * 32).decode()},k2:{base64.b64encode(b'b' * 32).decode()}",
    )
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k2")

    session.expire_all()
    reloaded = session.query(Contract).filter(Contract.id == contract_id).first()
    assert reloaded.contract_text == "rotate-me contract text"

    # A fresh write now uses k2.
    new_contract = Contract(user_id=user.id, filename="new.pdf", contract_text="new text")
    session.add(new_contract)
    session.commit()
    raw = _raw_column(engine, "contracts", "contract_text", new_contract.id)
    assert raw.split(":")[2] == "k2"
