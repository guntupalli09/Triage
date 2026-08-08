"""
Pytest configuration and shared fixtures for Triage Counsel tests.
"""

import atexit
import os
import shutil
import tempfile

# Give the whole test session its own throwaway SQLite file, set BEFORE
# anything imports `database` (whose module-level `engine = create_engine(...)`
# reads DATABASE_URL once, at import time — setting this any later, e.g. in
# a fixture, would be too late for every TestClient-based test that does
# `import main` at module scope).
#
# Without this, every TestClient-based test (test_contract_deletion.py,
# test_demo_routes.py, test_share_link_hardening.py, ...) reads and writes
# the real development database at data/triage.db. Each of those files uses
# fixed, hardcoded email addresses for its fixtures, so the first run
# against a fresh dev DB passes — but registration silently fails with
# "an account with this email already exists" on every subsequent run,
# which then cascades into unrelated-looking failures (redirects landing on
# a login/error page instead of a contract id, uploads 404ing, etc.) that
# have nothing to do with whatever the second run was actually meant to
# test. `setdefault` so an explicit DATABASE_URL from the environment (e.g.
# a CI job pointing at a real Postgres test instance) still wins.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="triagecounsel-pytest-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(_TEST_DB_DIR, 'test.db')}")
os.environ.setdefault("DEV_MODE", "true")
atexit.register(shutil.rmtree, _TEST_DB_DIR, ignore_errors=True)

import pytest
from rules_engine import RuleEngine


@pytest.fixture(scope="module")
def rule_engine():
    """Shared rule engine instance for all tests."""
    return RuleEngine()
