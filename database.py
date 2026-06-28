"""
Database setup using SQLAlchemy.
Supports PostgreSQL (production) and SQLite (development).
"""
from __future__ import annotations

import os
import logging
from pathlib import Path

from sqlalchemy import create_engine, event
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


def init_db():
    import models  # noqa: F401 — registers all models
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized: {'PostgreSQL' if not _is_sqlite else 'SQLite'}")
