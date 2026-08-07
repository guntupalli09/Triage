"""
Tests for backfill_encryption.py: idempotency, dry-run, mixed rows, and
error/progress reporting.
"""
import base64
import os
import sys

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DEV_MODE", "true")

import backfill_encryption
import encryption
from database import Base
from models import Contract, Playbook, User
import analytics_models  # noqa: F401


@pytest.fixture()
def engine_and_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEYS", f"k1:{base64.b64encode(b'a' * 32).decode()}")
    monkeypatch.setenv("ENCRYPTION_KEY_CURRENT", "k1")

    db_path = tmp_path / "backfill_test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)

    # backfill_encryption.py uses database.engine directly; point it at this
    # throwaway DB for the duration of the test.
    monkeypatch.setattr(backfill_encryption, "engine", engine)

    yield engine


def _seed_legacy_rows(engine, n=3):
    Session = sessionmaker(bind=engine)
    session = Session()
    user = User(email="firm@example.com", password_hash="x")
    session.add(user)
    session.commit()

    ids = []
    for i in range(n):
        c = Contract(user_id=user.id, filename=f"c{i}.txt", contract_text="placeholder")
        session.add(c)
        session.commit()
        ids.append(c.id)
    session.close()

    # Overwrite with true raw plaintext (bypassing the ORM's auto-encrypt),
    # simulating rows written before encryption existed.
    with engine.begin() as conn:
        for i, row_id in enumerate(ids):
            conn.execute(
                text("UPDATE contracts SET contract_text = :v WHERE id = :id"),
                {"v": f"legacy plaintext contract #{i}", "id": row_id},
            )
    return ids


def _raw_values(engine, table="contracts", column="contract_text"):
    with engine.connect() as conn:
        return dict(conn.execute(text(f"SELECT id, {column} FROM {table}")).fetchall())


def test_backfill_encrypts_legacy_plaintext_rows(engine_and_key):
    engine = engine_and_key
    _seed_legacy_rows(engine, n=3)

    stats = backfill_encryption._backfill_table("contracts", "contract_text", dry_run=False, batch_size=10)
    assert stats == {"total": 3, "encrypted": 3, "already_encrypted": 0, "empty": 0, "errors": 0}

    values = _raw_values(engine)
    assert all(v.startswith("enc:v1:") for v in values.values())
    # And the content is recoverable.
    decrypted = {encryption.decrypt(v) for v in values.values()}
    assert decrypted == {"legacy plaintext contract #0", "legacy plaintext contract #1", "legacy plaintext contract #2"}


def test_backfill_is_idempotent(engine_and_key):
    engine = engine_and_key
    _seed_legacy_rows(engine, n=3)

    first = backfill_encryption._backfill_table("contracts", "contract_text", dry_run=False, batch_size=10)
    assert first["encrypted"] == 3

    values_after_first = _raw_values(engine)

    second = backfill_encryption._backfill_table("contracts", "contract_text", dry_run=False, batch_size=10)
    assert second == {"total": 3, "encrypted": 0, "already_encrypted": 3, "empty": 0, "errors": 0}

    values_after_second = _raw_values(engine)
    # Re-running must not re-encrypt (different ciphertext/nonce) already-encrypted rows.
    assert values_after_first == values_after_second


def test_backfill_dry_run_writes_nothing(engine_and_key):
    engine = engine_and_key
    _seed_legacy_rows(engine, n=3)
    before = _raw_values(engine)

    stats = backfill_encryption._backfill_table("contracts", "contract_text", dry_run=True, batch_size=10)
    assert stats["encrypted"] == 3  # reports what WOULD be encrypted

    after = _raw_values(engine)
    assert before == after  # but nothing was actually written


def test_backfill_skips_empty_and_null_values(engine_and_key):
    engine = engine_and_key
    Session = sessionmaker(bind=engine)
    session = Session()
    user = User(email="firm@example.com", password_hash="x")
    session.add(user)
    session.commit()
    c = Contract(user_id=user.id, filename="empty.txt", contract_text="placeholder")
    session.add(c)
    session.commit()
    row_id = c.id
    session.close()

    with engine.begin() as conn:
        conn.execute(text("UPDATE contracts SET contract_text = :v WHERE id = :id"), {"v": "", "id": row_id})

    stats = backfill_encryption._backfill_table("contracts", "contract_text", dry_run=False, batch_size=10)
    assert stats["empty"] == 1
    assert stats["encrypted"] == 0


def test_backfill_handles_mixed_legacy_and_already_encrypted_rows(engine_and_key):
    engine = engine_and_key
    ids = _seed_legacy_rows(engine, n=2)

    # Manually pre-encrypt one of the two rows to simulate a row that was
    # already migrated (or written post-encryption) sitting alongside a
    # still-legacy row.
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE contracts SET contract_text = :v WHERE id = :id"),
            {"v": encryption.encrypt("already encrypted contract"), "id": ids[0]},
        )

    stats = backfill_encryption._backfill_table("contracts", "contract_text", dry_run=False, batch_size=10)
    assert stats["total"] == 2
    assert stats["already_encrypted"] == 1
    assert stats["encrypted"] == 1

    values = _raw_values(engine)
    assert all(v.startswith("enc:v1:") for v in values.values())


def test_backfill_covers_playbooks_table_too(engine_and_key):
    engine = engine_and_key
    Session = sessionmaker(bind=engine)
    session = Session()
    user = User(email="firm@example.com", password_hash="x")
    session.add(user)
    session.commit()
    p = Playbook(user_id=user.id, name="Standard", template_text="placeholder")
    session.add(p)
    session.commit()
    row_id = p.id
    session.close()

    with engine.begin() as conn:
        conn.execute(text("UPDATE playbooks SET template_text = :v WHERE id = :id"), {"v": "legacy template text", "id": row_id})

    stats = backfill_encryption._backfill_table("playbooks", "template_text", dry_run=False, batch_size=10)
    assert stats["encrypted"] == 1

    raw = _raw_values(engine, table="playbooks", column="template_text")
    assert encryption.decrypt(raw[row_id]) == "legacy template text"


def test_main_returns_nonzero_exit_code_on_errors(engine_and_key, monkeypatch):
    engine = engine_and_key
    _seed_legacy_rows(engine, n=1)

    def _boom(*a, **kw):
        raise RuntimeError("simulated encryption failure")

    monkeypatch.setattr(backfill_encryption.encryption, "encrypt", _boom)
    monkeypatch.setattr(sys, "argv", ["backfill_encryption.py", "--table", "contracts"])
    exit_code = backfill_encryption.main()
    assert exit_code == 1


def test_targets_include_json_analysis_columns(engine_and_key):
    """P2b: the CLI must cover the JSON columns that can embed contract
    excerpts, not just contract_text/template_text."""
    assert "findings_json" in backfill_encryption._TARGETS["contracts"]
    assert "llm_result_json" in backfill_encryption._TARGETS["contracts"]
    assert "review_decisions_json" in backfill_encryption._TARGETS["contracts"]
    assert "template_findings_json" in backfill_encryption._TARGETS["playbooks"]
    # rule_counts_json deliberately stays plain JSON — not encrypted.
    assert "rule_counts_json" not in backfill_encryption._TARGETS["contracts"]


def test_main_encrypts_legacy_findings_json_end_to_end(engine_and_key, monkeypatch):
    engine = engine_and_key
    Session = sessionmaker(bind=engine)
    session = Session()
    user = User(email="firm@example.com", password_hash="x")
    session.add(user)
    session.commit()
    c = Contract(user_id=user.id, filename="c.txt", contract_text="placeholder")
    session.add(c)
    session.commit()
    row_id = c.id
    session.close()

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE contracts SET findings_json = :v WHERE id = :id"),
            {"v": '{"rule_id": "r1", "matched_excerpt": "legacy excerpt text"}', "id": row_id},
        )

    monkeypatch.setattr(sys, "argv", ["backfill_encryption.py", "--table", "contracts"])
    exit_code = backfill_encryption.main()
    assert exit_code == 0

    raw = _raw_values(engine, table="contracts", column="findings_json")
    assert raw[row_id].startswith("enc:v1:")
    import json
    assert json.loads(encryption.decrypt(raw[row_id])) == {"rule_id": "r1", "matched_excerpt": "legacy excerpt text"}
