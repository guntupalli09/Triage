"""
Database setup using SQLAlchemy.
Supports PostgreSQL (production) and SQLite (development).
"""
from __future__ import annotations

import os
import time
import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

logger = logging.getLogger(__name__)

_default_db_dir = Path("/tmp") if os.getenv("VERCEL") else Path(__file__).parent / "data"
_default_db_dir.mkdir(parents=True, exist_ok=True)
DB_PATH = _default_db_dir / "triage.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

_is_sqlite = "sqlite" in DATABASE_URL

_connect_args = {"check_same_thread": False} if _is_sqlite else {}

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


class Base(DeclarativeBase):
    pass


def get_db():
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


def init_db():
    import models  # noqa: F401 — registers all models
    Base.metadata.create_all(bind=engine)
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
