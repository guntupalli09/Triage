"""
Pytest configuration and shared fixtures for Triage Counsel tests.
"""

import pytest
from rules_engine import RuleEngine


@pytest.fixture(scope="module")
def rule_engine():
    """Shared rule engine instance for all tests."""
    return RuleEngine()


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database for policy-engine tests
    (tests/test_playbook_*.py) — a fresh schema per test, entirely separate
    from the app's real database.py engine, so these tests never touch
    on-disk state."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database import Base
    import models  # noqa: F401 — registers User/Contract/Playbook
    import analytics_models  # noqa: F401
    import playbook.db_models  # noqa: F401 — registers policy engine models

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
