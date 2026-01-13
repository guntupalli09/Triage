"""
Pytest configuration and shared fixtures for Triage AI tests.
"""

import pytest
from rules_engine import RuleEngine


@pytest.fixture(scope="module")
def rule_engine():
    """Shared rule engine instance for all tests."""
    return RuleEngine()
