"""
Database setup using SQLAlchemy.
Supports PostgreSQL (production) and SQLite (local dev fallback).
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    _default_db_dir = Path("/tmp") if os.getenv("VERCEL") else Path(__file__).parent / "data"
    _default_db_dir.mkdir(parents=True, exist_ok=True)
    DB_PATH = _default_db_dir / "triage.db"
    DATABASE_URL = f"sqlite:///{DB_PATH}"

_is_sqlite = "sqlite" in DATABASE_URL

if _is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
    )

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
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
