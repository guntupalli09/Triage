"""
Pytest configuration and shared fixtures for Triage Counsel tests.
"""

import pytest
from rules_engine import RuleEngine


@pytest.fixture(scope="module")
def rule_engine():
    """Shared rule engine instance for all tests."""
    return RuleEngine()
