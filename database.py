"""
Database setup using SQLAlchemy.
Supports PostgreSQL (production) and SQLite (development).
"""
from __future__ import annotations

import os
import time
import logging
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

logger = logging.getLogger(__name__)

_default_db_dir = Path("/tmp") if os.getenv("VERCEL") else Path(__file__).parent / "data"
_default_db_dir.mkdir(parents=True, exist_ok=True)
DB_PATH = _default_db_dir / "triage.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

_is_sqlite = "sqlite" in DATABASE_URL

# timeout=30 matches pool_timeout below: without it, sqlite3's own default
# 5-second busy-wait raises "database is locked" well before a request
# would otherwise have queued successfully for a pool connection, turning
# an ordinary write-contention wait into a hard failure under concurrent
# writers.
_connect_args = {"check_same_thread": False, "timeout": 30} if _is_sqlite else {}

_engine_kwargs = {}
if not _is_sqlite:
    _engine_kwargs.update(
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
    )

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, connection_record):
        """WAL mode lets readers proceed without blocking on a writer (and
        vice versa) instead of SQLite's default rollback-journal mode,
        where every writer takes an exclusive file lock that blocks every
        other connection — reader or writer — for the transaction's
        duration. Under concurrent traffic (multiple requests each opening
        their own pooled connection) that default serializes far more work
        than necessary and, combined with a short busy-timeout, was
        observed compounding into cascading connection-pool timeouts under
        bursty concurrent load. WAL is standard, safe, and strictly better
        for this access pattern; it has no effect on PostgreSQL, which
        already handles concurrent writers via MVCC."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency (`Depends(get_db)`): FastAPI drives this generator
    itself and guarantees `.close()` runs via its own exit-stack handling
    once the request finishes, regardless of whether the route raised.
    Never call this directly with `next(get_db())` — nothing then owns
    advancing the generator past its `yield`, so `db.close()` never runs
    deterministically; cleanup would depend on the generator eventually
    being garbage-collected, which is not guaranteed to happen promptly
    under load and is exactly how a connection-pool exhaustion bug was
    found and fixed in this codebase (see git history / triagebench_live's
    README for the full incident writeup)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session():
    """Explicit context-manager form of get_db(), for the few call sites
    that are NOT invoked through FastAPI's dependency-injection graph and
    so cannot use `Depends(get_db)` — namely `@app.exception_handler`
    callbacks, which Starlette calls directly as `handler(request, exc)`
    with no DI resolution at all. Guarantees the same deterministic
    `db.close()` on the `with` block's exit, success or exception."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(max_retries: int = 30, delay: float = 2.0):
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"Database connection verified (attempt {attempt})")
            return
        except Exception as e:
            logger.warning(f"Database not ready (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise RuntimeError(f"Database not available after {max_retries} attempts") from e
            time.sleep(delay)


def wait_for_redis(max_retries: int = 15, delay: float = 2.0):
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.info("No REDIS_URL configured, skipping Redis wait")
        return
    import redis as _redis
    for attempt in range(1, max_retries + 1):
        try:
            r = _redis.from_url(redis_url, decode_responses=True, socket_timeout=5)
            r.ping()
            r.close()
            logger.info(f"Redis connection verified (attempt {attempt})")
            return
        except Exception as e:
            logger.warning(f"Redis not ready (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise RuntimeError(f"Redis not available after {max_retries} attempts") from e
            time.sleep(delay)


def _run_migrations():
    """In-place migrations for existing tables — create_all only creates missing
    tables, it never alters columns on tables that already exist."""
    from sqlalchemy import inspect

    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"]: c for c in insp.get_columns("users")}

    with engine.begin() as conn:
        if "google_sub" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN google_sub VARCHAR(255)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS users_google_sub_idx ON users (google_sub)"))
            logger.info("Migration applied: users.google_sub column + unique index")
        if "reset_token_hash" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_hash VARCHAR(64)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS users_reset_token_hash_idx ON users (reset_token_hash)"))
            logger.info("Migration applied: users.reset_token_hash column + index")
        if "reset_token_expires_at" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires_at TIMESTAMP"))
            logger.info("Migration applied: users.reset_token_expires_at column")
        # SQLite can't drop NOT NULL without a table rebuild; fresh SQLite DBs
        # already get the nullable column from the model definition.
        if not _is_sqlite and "password_hash" in cols and not cols["password_hash"]["nullable"]:
            conn.execute(text("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL"))
            logger.info("Migration applied: users.password_hash now nullable")
        if "mfa_secret" not in cols:
            # TEXT, not VARCHAR — EncryptedText columns store an
            # "enc:v1:..." envelope, longer than the raw base32 secret.
            conn.execute(text("ALTER TABLE users ADD COLUMN mfa_secret TEXT"))
            logger.info("Migration applied: users.mfa_secret column")
        if "mfa_enabled" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN NOT NULL DEFAULT false"))
            logger.info("Migration applied: users.mfa_enabled column")
        if "mfa_enrolled_at" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN mfa_enrolled_at TIMESTAMP"))
            logger.info("Migration applied: users.mfa_enrolled_at column")
        if "mfa_recovery_codes_json" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN mfa_recovery_codes_json JSON"))
            logger.info("Migration applied: users.mfa_recovery_codes_json column")

        # Columns storing EncryptedJSON (encryption.py) — TEXT-backed, not
        # JSON/JSONB, because an encrypted blob is not valid JSON. Used both
        # for ADD COLUMN on old databases missing these entirely, and for
        # the JSON->TEXT column-type migration below on databases that
        # already have them as JSON/JSONB (PostgreSQL only — SQLite's JSON
        # type is already TEXT-backed under the hood, so no ALTER is needed
        # there even though the Python-side type changed).
        encrypted_json_col_type = "TEXT"
        contract_encrypted_json_columns = [
            "findings_json", "llm_result_json", "payment_terms_json",
            "blocking_findings_json", "policy_blocked_findings_json",
            "risk_dashboard_json", "structure_report_json", "clause_quality_json",
            "metadata_json", "risk_balance_json", "deviations_json", "review_decisions_json",
            "policy_decisions_json",
        ]

        if "contracts" in insp.get_table_names():
            contract_cols_info = {c["name"]: c for c in insp.get_columns("contracts")}
            contract_cols = set(contract_cols_info)
            if "signature_readiness" not in contract_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN signature_readiness VARCHAR(40)"))
                logger.info("Migration applied: contracts.signature_readiness column")
            if "payment_terms_json" not in contract_cols:
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN payment_terms_json {encrypted_json_col_type}"))
                logger.info("Migration applied: contracts.payment_terms_json column")
            if "blocking_findings_json" not in contract_cols:
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN blocking_findings_json {encrypted_json_col_type}"))
                logger.info("Migration applied: contracts.blocking_findings_json column")
            if "policy_blocked_findings_json" not in contract_cols:
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN policy_blocked_findings_json {encrypted_json_col_type}"))
                logger.info("Migration applied: contracts.policy_blocked_findings_json column")
            if "legal_risk_score" not in contract_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN legal_risk_score INTEGER"))
                logger.info("Migration applied: contracts.legal_risk_score column")
            if "business_risk_score" not in contract_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN business_risk_score INTEGER"))
                logger.info("Migration applied: contracts.business_risk_score column")
            if "negotiation_difficulty_score" not in contract_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN negotiation_difficulty_score INTEGER"))
                logger.info("Migration applied: contracts.negotiation_difficulty_score column")
            if "risk_dashboard_json" not in contract_cols:
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN risk_dashboard_json {encrypted_json_col_type}"))
                logger.info("Migration applied: contracts.risk_dashboard_json column")
            if "structure_report_json" not in contract_cols:
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN structure_report_json {encrypted_json_col_type}"))
                logger.info("Migration applied: contracts.structure_report_json column")
            if "clause_quality_json" not in contract_cols:
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN clause_quality_json {encrypted_json_col_type}"))
                logger.info("Migration applied: contracts.clause_quality_json column")
            if "risk_balance_json" not in contract_cols:
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN risk_balance_json {encrypted_json_col_type}"))
                logger.info("Migration applied: contracts.risk_balance_json column")
            if "metadata_json" not in contract_cols:
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN metadata_json {encrypted_json_col_type}"))
                logger.info("Migration applied: contracts.metadata_json column")
            if "review_decisions_json" not in contract_cols:
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN review_decisions_json {encrypted_json_col_type}"))
                logger.info("Migration applied: contracts.review_decisions_json column")
            if "policy_decisions_json" not in contract_cols:
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN policy_decisions_json {encrypted_json_col_type}"))
                logger.info("Migration applied: contracts.policy_decisions_json column")
            if "review_finalized_at" not in contract_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN review_finalized_at TIMESTAMP"))
                logger.info("Migration applied: contracts.review_finalized_at column")
            if "share_expires_at" not in contract_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN share_expires_at TIMESTAMP"))
                logger.info("Migration applied: contracts.share_expires_at column")
            if "share_revoked_at" not in contract_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN share_revoked_at TIMESTAMP"))
                logger.info("Migration applied: contracts.share_revoked_at column")
            if "share_max_views" not in contract_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN share_max_views INTEGER"))
                logger.info("Migration applied: contracts.share_max_views column")
            if "share_view_count" not in contract_cols:
                # DEFAULT 0 so existing rows (all pre-hardening, so all
                # legitimately "0 views recorded so far") satisfy the
                # model's nullable=False without a separate backfill pass.
                conn.execute(text("ALTER TABLE contracts ADD COLUMN share_view_count INTEGER NOT NULL DEFAULT 0"))
                logger.info("Migration applied: contracts.share_view_count column")

            # JSON/JSONB -> TEXT for columns that already existed before
            # EncryptedJSON was introduced. Existing values are valid JSON
            # text either way, so `col::text` is a safe, lossless cast —
            # this does NOT encrypt existing data (that's backfill_encryption.py's
            # job); it only changes the column's storage type so encrypted
            # writes (which are TEXT, not valid JSON) can be stored at all.
            if not _is_sqlite:
                for col_name in contract_encrypted_json_columns:
                    info = contract_cols_info.get(col_name)
                    if info is not None and "JSON" in str(info["type"]).upper():
                        conn.execute(text(
                            f"ALTER TABLE contracts ALTER COLUMN {col_name} TYPE TEXT USING {col_name}::text"
                        ))
                        logger.info(f"Migration applied: contracts.{col_name} JSON/JSONB -> TEXT (for encryption)")

        if "playbooks" in insp.get_table_names():
            playbook_cols_info = {c["name"]: c for c in insp.get_columns("playbooks")}
            if not _is_sqlite:
                info = playbook_cols_info.get("template_findings_json")
                if info is not None and "JSON" in str(info["type"]).upper():
                    conn.execute(text(
                        "ALTER TABLE playbooks ALTER COLUMN template_findings_json TYPE TEXT "
                        "USING template_findings_json::text"
                    ))
                    logger.info("Migration applied: playbooks.template_findings_json JSON/JSONB -> TEXT (for encryption)")


def init_db():
    import models  # noqa: F401 — registers all models
    import analytics_models  # noqa: F401 — registers acquisition/session/event models
    Base.metadata.create_all(bind=engine)
    try:
        _run_migrations()
    except Exception:
        logger.exception("Schema migration failed — Google sign-in may not work until resolved")
    logger.info(f"Database initialized: {'PostgreSQL' if not _is_sqlite else 'SQLite'}")


def check_db_health() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_redis_health() -> bool:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return True
    try:
        import redis as _redis
        r = _redis.from_url(redis_url, decode_responses=True, socket_timeout=3)
        r.ping()
        r.close()
        return True
    except Exception:
        return False
