"""Tests for insurance_policy_engine.py's fact-admission integration.
Mirrors tests/test_ip_ownership_fact_admission.py's structure.
INSURANCE_SEMANTIC_DISCOVERY_ENABLED defaults to False; each test flips it
on for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import insurance_policy_engine as ine


def setup_function(_):
    ine.INSURANCE_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    ine.INSURANCE_SEMANTIC_DISCOVERY_ENABLED = False


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
    require_cgl = False
    require_professional_liability = False
    require_cyber_liability = False
    require_workers_comp = False
    require_employers_liability = False
    require_auto_liability = False
    cgl_minimum_per_occurrence = None
    professional_liability_minimum_limit = None
    cyber_liability_minimum_limit = None
    employers_liability_minimum_limit = None
    auto_liability_minimum_limit = None
    require_additional_insured = False
    require_waiver_of_subrogation = False
    require_primary_non_contributory = False
    require_certificate_of_insurance = False
    max_notice_of_cancellation_days = None
    require_subcontractor_coverage = False


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    ine.INSURANCE_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = ine.extract_insurance_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = ine.extract_insurance_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review_never_accept(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = ine.extract_insurance_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = ine.evaluate_insurance_policy(facts, FakePolicy())
    assert decision.state == ine.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = ine.extract_insurance_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_window(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = ine.extract_insurance_facts(doc)
    assert facts is None


def test_verified_semantic_candidate_seeds_a_window(monkeypatch):
    """Uses phrasing deliberately outside _ANCHOR_RE's vocabulary
    (no 'insurance'/'liability'/'coverage' words) so the deterministic
    anchor genuinely finds nothing and the semantic path is exercised."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. Vendor shall maintain a risk-transfer policy with a reputable underwriter "
        "covering third-party bodily injury claims arising from its operations."
    )
    quote = (
        "Vendor shall maintain a risk-transfer policy with a reputable underwriter covering "
        "third-party bodily injury claims arising from its operations."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative insurance-maintenance obligation.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ine.extract_insurance_facts(doc)
    assert facts is not None
    assert facts.clause_found is True


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. Parties commonly carry risk-transfer policies with reputable underwriters, "
        "although this Agreement does not itself impose such a requirement."
    )
    quote = "Parties commonly carry risk-transfer policies with reputable underwriters"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive statement about common practice, not operative language of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ine.extract_insurance_facts(doc)
    assert facts is None
