"""Tests for warranties_policy_engine.py's fact-admission integration.
Mirrors tests/test_termination_fact_admission.py's structure.
WARRANTIES_SEMANTIC_DISCOVERY_ENABLED defaults to False; each test flips
it on for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import warranties_policy_engine as we


def setup_function(_):
    we.WARRANTIES_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    we.WARRANTIES_SEMANTIC_DISCOVERY_ENABLED = False


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
    require_categories_json = []
    max_disclaimer_scope = None
    min_duration_days = None
    require_exclusive_remedy = False
    prohibit_as_is_disclaimer = False


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    we.WARRANTIES_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = we.extract_warranties_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = we.extract_warranties_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review_not_not_applicable(monkeypatch):
    """Critical for this adapter specifically: its own deliberate design
    treats "anchor fired but nothing structured" as NOT_APPLICABLE, not
    REQUIRES_REVIEW (negative-control discipline) -- the RECOGNITION_
    UNCERTAIN case must NOT be confused with that path and must still
    escalate."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = we.extract_warranties_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = we.evaluate_warranties_policy(facts, FakePolicy())
    assert decision.state == we.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = we.extract_warranties_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_window(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = we.extract_warranties_facts(doc)
    assert facts is None


def test_verified_semantic_candidate_seeds_a_window(monkeypatch):
    """Uses phrasing with no 'warrant'-root word at all so the
    deterministic anchor genuinely finds nothing and the semantic path is
    exercised."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. Vendor represents that the Software conforms to the Documentation "
        "for a period of ninety days."
    )
    quote = "Vendor represents that the Software conforms to the Documentation for a period of ninety days."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative performance representation functioning as a warranty.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = we.extract_warranties_facts(doc)
    assert facts is not None
    assert facts.clause_found is True


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. Vendors in this industry typically represent that software will perform "
        "in accordance with documentation, although this Agreement does not itself state such a term."
    )
    quote = "Vendors in this industry typically represent that software will perform in accordance with documentation"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive statement about industry norms, not operative language of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = we.extract_warranties_facts(doc)
    assert facts is None
