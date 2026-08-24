"""Tests for governing_law_policy_engine.py's fact-admission integration.
Mirrors tests/test_confidentiality_fact_admission.py's structure.
GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED defaults to False; each test
flips it on for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import governing_law_policy_engine as gpe


def setup_function(_):
    gpe.GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    gpe.GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED = False


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
    preferred_jurisdictions_json = []
    acceptable_jurisdictions_json = []
    prohibited_jurisdictions_json = []
    required_dispute_resolution = None
    require_jury_trial_waiver = False


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    gpe.GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = gpe.extract_governing_law_facts("This Agreement covers the sale of widgets.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = gpe.extract_governing_law_facts("This Agreement covers the sale of widgets.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = gpe.extract_governing_law_facts("This Agreement covers the sale of widgets.")
    decision = gpe.evaluate_governing_law_policy(facts, FakePolicy())
    assert decision.state == gpe.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = gpe.extract_governing_law_facts("This Agreement covers the sale of widgets.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_jurisdiction(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement covers the sale of widgets."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = gpe.extract_governing_law_facts(doc)
    assert facts is None


def test_admitted_candidate_still_requires_deterministic_structuring(monkeypatch):
    """A semantically-admitted candidate (unusual phrasing, no
    'governing law'/'governed by' words) that _JURISDICTION_RE still
    can't parse must land as REQUIRES_REVIEW, never a fabricated
    jurisdiction."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "The parties agree that Delaware's substantive rules shall control interpretation of this Agreement."
    quote = "The parties agree that Delaware's substantive rules shall control interpretation of this Agreement."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative choice-of-law language.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = gpe.extract_governing_law_facts(doc)
    assert facts is not None
    assert facts.clause_found is True
    # _JURISDICTION_RE's vocabulary doesn't recognize "X's substantive
    # rules shall control" phrasing, so this correctly stays unresolved.
    assert facts.jurisdiction is None


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. Agreements of this type commonly designate Delaware's substantive rules "
        "as controlling, although this Agreement does not itself state such a term."
    )
    quote = "Agreements of this type commonly designate Delaware's substantive rules as controlling"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive statement about common drafting, not operative language of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = gpe.extract_governing_law_facts(doc)
    assert facts is None


def test_decision_sensitivity_ai_identified_condition_forces_review_even_with_jurisdiction_found():
    """Final trust architecture Phase 8: this adapter's own _JURISDICTION_RE
    always implies _ANCHOR_RE matched too (both require "governed by"),
    so extract_governing_law_facts's semantic-only path can never itself
    produce a jurisdiction-found-plus-AI-qualifier combination in
    practice -- but evaluate_governing_law_policy must still handle it
    correctly if it ever occurs (e.g. a future adapter change that lets
    semantic discovery run alongside a successful deterministic parse).
    Tested directly at the Facts level, the same established pattern
    other adapters' RECOGNITION_UNCERTAIN tests already use."""
    condition_text = "in the event of a change of control of either party, this choice of law shall not apply"

    facts_clean = gpe.GoverningLawFacts(
        clause_found=True, jurisdiction="Delaware", raw_excerpt="governed by the laws of Delaware.",
        start_index=0, end_index=30,
    )
    facts_conditioned = gpe.GoverningLawFacts(
        clause_found=True, jurisdiction="Delaware", raw_excerpt="governed by the laws of Delaware.",
        start_index=0, end_index=30, ai_identified_condition=condition_text,
    )

    decision_clean = gpe.evaluate_governing_law_policy(facts_clean, FakePolicy())
    decision_conditioned = gpe.evaluate_governing_law_policy(facts_conditioned, FakePolicy())

    assert decision_clean.state != gpe.REQUIRES_REVIEW
    assert decision_conditioned.state == gpe.REQUIRES_REVIEW
    assert condition_text in "; ".join(decision_conditioned.unresolved_facts)
