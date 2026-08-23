"""Tests for data_security_policy_engine.py's fact-admission integration.
Mirrors tests/test_liability_fact_admission.py's structure and mocking
pattern. DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED defaults to False; each
test flips it on for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import data_security_policy_engine as dse


def setup_function(_):
    dse.DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    dse.DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = False


def _fake_response(content_text: str):
    body = json.dumps({
        "content": [{"type": "text", "text": content_text}],
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = False
    return cm


class FakePolicy:
    contract_side = "vendor"
    escalation_approval_authority = None
    fallback_text = None
    require_processor_role = False
    prohibit_unrestricted_subprocessors = False
    require_subprocessor_notice_or_consent = "not_required"
    max_breach_notification_hours = None
    require_scc_or_adequacy_for_transfers = False
    prohibit_data_transfer = False
    require_deletion_or_return = False
    max_retention_days = None
    require_audit_rights = False
    require_named_security_certification = False
    require_cooperation_obligation = False


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    dse.DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = dse.extract_data_security_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = dse.extract_data_security_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review_never_accept(monkeypatch):
    """Critical for this adapter specifically: an all-None facts object
    with clause_found=True could otherwise resolve to ACCEPT under a
    permissive playbook (no dimension required) -- the explicit
    absence_state check must intercept before that dimension logic runs."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = dse.extract_data_security_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = dse.evaluate_data_security_policy(facts, FakePolicy())
    assert decision.state == dse.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = dse.extract_data_security_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_window(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = dse.extract_data_security_facts(doc)
    assert facts is None


def test_verified_semantic_candidate_seeds_a_window_and_is_classified(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. Vendor shall notify Customer within 48 hours of becoming aware of any "
        "data breach affecting Customer's data."
    )
    quote = "Vendor shall notify Customer within 48 hours of becoming aware of any data breach affecting Customer's data."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative breach-notification obligation.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = dse.extract_data_security_facts(doc)
    assert facts is not None
    assert facts.clause_found is True
    assert facts.breach_notification_hours == 48


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. Companies generally notify customers of data breaches within a reasonable time, "
        "although this Agreement does not itself impose such a requirement."
    )
    quote = "Companies generally notify customers of data breaches within a reasonable time"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive statement about general industry practice, not operative language of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = dse.extract_data_security_facts(doc)
    assert facts is None
