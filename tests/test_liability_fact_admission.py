"""Tests for liability_policy_engine.py's fact-admission integration —
the reference adapter for generalizing indemnification's proven
semantic-discovery + absence-state pattern via the shared fact_admission.py
framework (see artifacts/fact_admission_architecture/PRE_IMPLEMENTATION_MAP.md).

Mirrors tests/test_step4a9_2_real_provider_adversarial.py's mocking
pattern. LIABILITY_SEMANTIC_DISCOVERY_ENABLED defaults to False in
production/CI (see liability_policy_engine.py) — every test here flips it
on for the duration of the test only, so the default-off regression suite
in tests/test_liability_policy_engine.py is unaffected.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

import liability_policy_engine as lpe


def setup_function(_):
    lpe.LIABILITY_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    lpe.LIABILITY_SEMANTIC_DISCOVERY_ENABLED = False


def _fake_response(content_text: str):
    body = json.dumps({
        "content": [{"type": "text", "text": content_text}],
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = False
    return cm


def test_semantic_discovery_disabled_by_default_is_confirmed_absent(monkeypatch):
    """With the flag off (the default), behavior is byte-identical to
    before this integration existed: no API key required, no network call
    made, plain regex-only NOT_APPLICABLE."""
    lpe.LIABILITY_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = lpe.extract_liability_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain_not_confirmed_absent(monkeypatch):
    """Core Step 5/16 invariant: a provider outage must never silently
    become 'confirmed absent'."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = lpe.extract_liability_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.clause_found is True
    assert facts.provisions == []
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review_not_not_applicable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FakePolicy:
        preferred_multiplier = 1.0
        acceptable_max_multiplier = 1.0
        negotiate_max_multiplier = 2.0
        prohibit_unlimited = True
        required_exceptions_json = []
        fallback_text = None
        contract_side = "vendor"
        escalation_approval_authority = None

    facts = lpe.extract_liability_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = lpe.evaluate_liability_policy(facts, FakePolicy())
    assert decision.state == lpe.REQUIRES_REVIEW
    assert "not the same as confirming" in decision.explanation


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = lpe.extract_liability_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_semantic_candidate_never_becomes_a_provision(monkeypatch):
    """The discovery-stage exact-substring check must discard a fabricated
    quote before it can ever reach verification/admission."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = lpe.extract_liability_facts(doc)
    assert facts is None


def test_verified_semantic_candidate_becomes_a_provision(monkeypatch):
    """A semantically-discovered candidate that a real verifier claims
    ESTABLISHED, and whose evidence quote grounds, is admitted and treated
    as a real anchor — feeding the same deterministic _extract_provision
    structuring any regex-found anchor would go through."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. Neither party shall be liable for any amount in excess of "
        "the total fees paid by Customer in the twelve months preceding the claim."
    )
    quote = (
        "Neither party shall be liable for any amount in excess of the total fees paid "
        "by Customer in the twelve months preceding the claim."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative mutual liability cap, no conditions found.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = lpe.extract_liability_facts(doc)
    assert facts is not None
    assert facts.clause_found is True
    assert len(facts.provisions) == 1


def test_verifier_not_established_never_becomes_a_provision(monkeypatch):
    """The known-failure-class regression, applied to liability: a
    plausible-looking candidate span that the adversarial verifier
    classifies as descriptive/non-operative must not become a provision."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. Industry practice often limits vendor liability to fees paid, "
        "although this Agreement does not itself adopt that approach."
    )
    quote = "Industry practice often limits vendor liability to fees paid"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive background statement about industry practice, not operative language of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = lpe.extract_liability_facts(doc)
    assert facts is None
