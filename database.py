"""
Database setup using SQLAlchemy with SQLite.
Easily swappable to PostgreSQL by changing the URL.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_default_db_dir = Path("/tmp") if os.getenv("VERCEL") else Path(__file__).parent / "data"
_default_db_dir.mkdir(parents=True, exist_ok=True)
DB_PATH = _default_db_dir / "triage.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
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
