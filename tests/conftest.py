"""
Pytest configuration and shared fixtures for Triage Counsel tests.
"""

import os

# Must be set before anything imports main.py / auth.py / security_config.py:
# those modules validate production secrets and Redis reachability at
# import/startup time, and the test suite runs without real production
# secrets configured.
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("IP_API_FALLBACK_ENABLED", "false")

import pytest
from rules_engine import RuleEngine


@pytest.fixture(scope="module")
def rule_engine():
    """Shared rule engine instance for all tests."""
    return RuleEngine()
