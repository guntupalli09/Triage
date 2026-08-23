"""Tests for payment_terms_policy_engine.py's fact-admission integration.
Mirrors tests/test_insurance_fact_admission.py's structure.
PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED defaults to False; each test
flips it on for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import payment_terms_policy_engine as pte


def setup_function(_):
    pte.PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    pte.PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED = False


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
    preferred_net_days = None
    acceptable_max_net_days = None
    negotiate_max_net_days = None
    require_disputed_amounts_withholdable = False
    require_setoff_rights = False
    prohibit_setoff_rights = False
    require_we_are_not_tax_responsible = False
    max_late_fee_percent = None
    require_price_increase_notice_days = None
    max_price_increase_percent = None


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    pte.PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = pte.extract_payment_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = pte.extract_payment_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review_never_accept(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = pte.extract_payment_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = pte.evaluate_payment_policy(facts, FakePolicy())
    assert decision.state == pte.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = pte.extract_payment_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_window(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = pte.extract_payment_facts(doc)
    assert facts is None


def test_verified_semantic_candidate_seeds_a_window(monkeypatch):
    """Uses phrasing deliberately outside _ANCHOR_RE/_CONCEPT_ENGAGEMENT_RES's
    vocabulary (no 'pay'/'invoice'/'net X days'/tax words) so the
    deterministic engagement gate genuinely finds nothing and the semantic
    path is exercised -- this is the general, open-ended complement Step
    4A.3's finite concept list cannot by itself exhaust."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. Customer shall settle each statement of account within thirty days "
        "of its issuance."
    )
    quote = "Customer shall settle each statement of account within thirty days of its issuance."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative payment-timing obligation.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = pte.extract_payment_facts(doc)
    assert facts is not None
    assert facts.clause_found is True


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    """The known-failure-class regression, applied to payment terms:
    'as is standard in the industry'-shaped descriptive language must not
    be admitted, even when the sentence is obligation-shaped."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. As is standard in the industry, customers generally settle statements of "
        "account within thirty days, although this Agreement does not itself impose such a term."
    )
    quote = "customers generally settle statements of account within thirty days"

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
        facts = pte.extract_payment_facts(doc)
    assert facts is None
