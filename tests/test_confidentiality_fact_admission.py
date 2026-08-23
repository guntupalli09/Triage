"""Tests for confidentiality_policy_engine.py's fact-admission integration.
Mirrors tests/test_liability_fact_admission.py's structure and mocking
pattern. CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED defaults to False; each
test flips it on for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import confidentiality_policy_engine as cpe


def setup_function(_):
    cpe.CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    cpe.CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED = False


def _fake_response(content_text: str):
    body = json.dumps({
        "content": [{"type": "text", "text": content_text}],
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = False
    return cm


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    cpe.CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = cpe.extract_confidentiality_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = cpe.extract_confidentiality_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FakePolicy:
        contract_side = "vendor"
        escalation_approval_authority = None
        fallback_text = None
        required_exclusions_json = []
        min_protection_duration_years = None
        max_exposure_duration_years = None
        require_mutual_confidentiality = False

    facts = cpe.extract_confidentiality_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = cpe.evaluate_confidentiality_policy(facts, FakePolicy())
    assert decision.state == cpe.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = cpe.extract_confidentiality_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_an_obligation(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = cpe.extract_confidentiality_facts(doc)
    assert facts is None


def test_admitted_candidate_still_requires_deterministic_structuring(monkeypatch):
    """A semantically-admitted candidate (unusual phrasing, no word
    'confidential') that the deterministic NAMED/MUTUAL obligation
    regexes still can't parse must land as REQUIRES_REVIEW, never a
    fabricated obligation -- the AI never structures protecting/protected
    roles itself."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "Vendor shall treat Customer's proprietary information as strictly private and shall not disclose it."
    quote = "Vendor shall treat Customer's proprietary information as strictly private and shall not disclose it."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative non-disclosure obligation.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = cpe.extract_confidentiality_facts(doc)
    assert facts is not None
    assert facts.clause_found is True
    # The deterministic NAMED_OBLIGATION_RE vocabulary doesn't recognize
    # "treat ... as strictly private" phrasing, so this correctly stays
    # unresolved rather than being fabricated by the semantic layer.
    assert facts.obligations == []


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    """The known-failure-class regression, applied to confidentiality:
    industry-standard/background language must not become an obligation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. As is standard in the industry, vendors often agree to protect "
        "client proprietary information, although this Agreement does not itself state such a term."
    )
    quote = "vendors often agree to protect client proprietary information"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive statement about industry norms, not an operative obligation of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = cpe.extract_confidentiality_facts(doc)
    assert facts is None
