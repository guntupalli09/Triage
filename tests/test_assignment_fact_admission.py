"""Tests for assignment_policy_engine.py's fact-admission integration.
Mirrors tests/test_governing_law_fact_admission.py's structure.
ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED defaults to False; each test flips
it on for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import assignment_policy_engine as ape


def setup_function(_):
    ape.ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    ape.ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED = False


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
    require_consent_for_counterparty_assignment = False
    allow_affiliate_assignment_without_consent = True
    allow_change_of_control_without_consent = False


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    ape.ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = ape.extract_assignment_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = ape.extract_assignment_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = ape.extract_assignment_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = ape.evaluate_assignment_policy(facts, FakePolicy())
    assert decision.state == ape.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = ape.extract_assignment_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_restriction(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = ape.extract_assignment_facts(doc)
    assert facts is None


def test_admitted_candidate_still_requires_deterministic_structuring(monkeypatch):
    """A semantically-admitted candidate (unusual phrasing, no word
    'assign') that the deterministic NAMED/MUTUAL restriction regexes
    still can't parse must land as REQUIRES_REVIEW, never a fabricated
    restriction."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "Vendor may not hand this Agreement off to a third party without Customer's prior written approval."
    quote = "Vendor may not hand this Agreement off to a third party without Customer's prior written approval."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative consent-required transfer restriction.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ape.extract_assignment_facts(doc)
    assert facts is not None
    assert facts.clause_found is True
    # The deterministic NAMED_RESTRICTION_RE vocabulary doesn't recognize
    # "hand ... off to" phrasing, so this correctly stays unresolved.
    assert facts.restrictions == []
    assert facts.unrestricted_assignment is False


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. Vendors commonly require consent before handing an agreement off to a "
        "third party, although this Agreement does not itself state such a term."
    )
    quote = "Vendors commonly require consent before handing an agreement off to a third party"

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
        facts = ape.extract_assignment_facts(doc)
    assert facts is None


def test_ai_identified_condition_survives_into_the_decision(monkeypatch):
    """Final trust architecture Phase 6/8: NAMED_RESTRICTION_RE/
    MUTUAL_RESTRICTION_RE have no vocabulary for "hand ... off to"
    phrasing, so restrictions stay empty in both the qualified and
    unqualified case -- what must differ is that the condition text
    survives into the final decision."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    condition_text = "in the event Vendor's ownership changes, this restriction shall not apply"
    doc = f"Vendor may not hand this Agreement off to a third party without Customer's prior written approval, {condition_text}."
    quote = f"Vendor may not hand this Agreement off to a third party without Customer's prior written approval, {condition_text}"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": condition_text, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative consent-required transfer restriction, conditioned on ownership continuity.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ape.extract_assignment_facts(doc)
    assert facts is not None
    assert facts.ai_identified_condition == condition_text

    decision = ape.evaluate_assignment_policy(facts, FakePolicy())
    assert decision.state == ape.REQUIRES_REVIEW
    assert condition_text in "; ".join(decision.unresolved_facts)


def test_ai_identified_definition_dependency_survives_into_the_decision(monkeypatch):
    """Adapter-completion pass: the restriction depends on a defined
    term ("Change of Control"); the resolved definition must survive
    into the decision, forcing review, never disappear because the
    restriction otherwise reads clean (or unstructured)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        '1. Definitions. "Change of Control" means the acquisition of more than fifty percent '
        "of Vendor's voting equity. 2. Miscellaneous. Vendor may not hand this Agreement off to "
        "a third party following a Change of Control without Customer's prior written approval."
    )
    quote = (
        "Vendor may not hand this Agreement off to a third party following a Change of Control "
        "without Customer's prior written approval."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "definition_term": "Change of Control",
            "reasoning": "Operative consent-required transfer restriction, scoped by a defined term.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ape.extract_assignment_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None
    assert "Change of Control" in facts.ai_identified_definition_or_reference

    decision = ape.evaluate_assignment_policy(facts, FakePolicy())
    assert decision.state == ape.REQUIRES_REVIEW
    assert "Change of Control" in "; ".join(decision.unresolved_facts)


def test_ai_identified_cross_reference_resolved_forces_review(monkeypatch):
    """Adapter-level cross-reference proof (Part 4): the restriction is
    scoped by a cross-referenced section; resolved deterministically,
    must force review, never disappear because the restriction otherwise
    reads clean (or unstructured)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "2. Miscellaneous. Vendor may not hand this Agreement off to a third party without "
        "Customer's prior written approval, subject to Section 8.3.\n\n"
        "Section 8.3 Permitted Transferees. Notice must be delivered to Customer at least 30 days "
        "before any transfer contemplated by this section takes effect."
    )
    quote = (
        "Vendor may not hand this Agreement off to a third party without Customer's prior written "
        "approval, subject to Section 8.3."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None,
            "cross_reference_text": "Section 8.3",
            "reasoning": "Operative consent-required transfer restriction, scoped by a cross-referenced section.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ape.extract_assignment_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None
    assert "Permitted Transferees" in facts.ai_identified_definition_or_reference

    decision = ape.evaluate_assignment_policy(facts, FakePolicy())
    assert decision.state == ape.REQUIRES_REVIEW


def test_competing_readings_never_reach_the_adapter_as_authoritative(monkeypatch):
    """Adapter-level competing-reading proof (Part 5)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "The parties' transfer rights are addressed in this section; one reading requires prior "
        "written approval for any transfer, another treats transfers as freely permitted."
    )
    quote = doc

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "AMBIGUOUS", "evidence_quote": None,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "competing_reading_a": {
                "proposition": "Transfers require prior written approval.",
                "evidence_quote": "one reading requires prior written approval for any transfer",
            },
            "competing_reading_b": {
                "proposition": "Transfers are freely permitted.",
                "evidence_quote": "another treats transfers as freely permitted",
            },
            "reasoning": "Two materially different readings of the same sentence.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ape.extract_assignment_facts(doc)
    assert facts is not None
    assert facts.restrictions == []
    assert facts.unrestricted_assignment is False
    assert facts.ai_identified_definition_or_reference is not None

    decision = ape.evaluate_assignment_policy(facts, FakePolicy())
    assert decision.state == ape.REQUIRES_REVIEW
