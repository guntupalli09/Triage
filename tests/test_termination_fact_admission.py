"""Tests for termination_policy_engine.py's fact-admission integration.
Mirrors tests/test_confidentiality_fact_admission.py's structure.
TERMINATION_SEMANTIC_DISCOVERY_ENABLED defaults to False; each test flips
it on for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import termination_policy_engine as tpe


def setup_function(_):
    tpe.TERMINATION_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    tpe.TERMINATION_SEMANTIC_DISCOVERY_ENABLED = False


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
    require_mutual_termination_for_convenience = False
    min_notice_days_for_convenience = None
    min_cure_period_days = None
    max_termination_fee_multiplier = None
    require_survival_of_confidentiality = False
    require_survival_of_payment_obligations = False
    fee_preferred_multiplier = None
    prohibit_uncapped_termination_fee = False


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    tpe.TERMINATION_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = tpe.extract_termination_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = tpe.extract_termination_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = tpe.extract_termination_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = tpe.evaluate_termination_policy(facts, FakePolicy())
    assert decision.state == tpe.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = tpe.extract_termination_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_right(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = tpe.extract_termination_facts(doc)
    assert facts is None


def test_admitted_candidate_still_requires_deterministic_structuring(monkeypatch):
    """A semantically-admitted candidate (unusual phrasing, no word
    'terminate') that the deterministic NAMED/MUTUAL right regexes still
    can't parse must land as REQUIRES_REVIEW, never a fabricated right."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "Customer may walk away from this Agreement at any time upon 30 days' written notice."
    quote = "Customer may walk away from this Agreement at any time upon 30 days' written notice."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative right to end the agreement for convenience.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = tpe.extract_termination_facts(doc)
    assert facts is not None
    assert facts.clause_found is True
    # The deterministic NAMED_RIGHT_RE vocabulary doesn't recognize "walk
    # away from" phrasing, so this correctly stays unresolved.
    assert facts.rights == []


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. Companies typically allow either party to walk away from this type of "
        "agreement on notice, although this Agreement does not itself state such a term."
    )
    quote = "Companies typically allow either party to walk away from this type of agreement on notice"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive statement about industry practice, not operative language of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = tpe.extract_termination_facts(doc)
    assert facts is None
