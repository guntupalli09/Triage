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
        "choices": [{"message": {"role": "assistant", "content": content_text}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
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
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    facts = tpe.extract_termination_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    facts = tpe.extract_termination_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    facts = tpe.extract_termination_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = tpe.evaluate_termination_policy(facts, FakePolicy())
    assert decision.state == tpe.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = tpe.extract_termination_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_right(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = tpe.extract_termination_facts(doc)
    assert facts is None


def test_admitted_candidate_still_requires_deterministic_structuring(monkeypatch):
    """A semantically-admitted candidate (unusual phrasing, no word
    'terminate') that the deterministic NAMED/MUTUAL right regexes still
    can't parse must land as REQUIRES_REVIEW, never a fabricated right."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
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
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
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


def test_ai_identified_condition_survives_into_the_decision(monkeypatch):
    """Final trust architecture Phase 6/8: like confidentiality, this
    adapter's deterministic right regexes have no vocabulary for "walk
    away from" phrasing, so the qualified case also lands on rights=[] --
    what must differ, and is asserted here, is that the condition text
    survives into the final decision rather than disappearing."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    condition_text = "in the event Customer's designated signatory changes, this right shall not apply"
    doc = f"Customer may walk away from this Agreement at any time upon 30 days' written notice, {condition_text}."
    quote = f"Customer may walk away from this Agreement at any time upon 30 days' written notice, {condition_text}"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": condition_text, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative right to end the agreement for convenience, conditioned on signatory continuity.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = tpe.extract_termination_facts(doc)
    assert facts is not None
    assert facts.ai_identified_condition == condition_text

    decision = tpe.evaluate_termination_policy(facts, FakePolicy())
    assert decision.state == tpe.REQUIRES_REVIEW
    assert condition_text in "; ".join(decision.unresolved_facts)


def test_ai_identified_definition_dependency_survives_into_the_decision(monkeypatch):
    """Adapter-completion pass: the AI-sourced candidate's termination
    right depends on a defined term ("Cause"); the shared framework
    deterministically resolves the definition, and it must survive into
    the final decision (forcing review), never disappear because the
    right otherwise reads clean."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        '1. Definitions. "Cause" means a material, uncured breach of this Agreement. '
        "2. Miscellaneous. Customer may walk away from this Agreement upon the occurrence of Cause."
    )
    quote = "Customer may walk away from this Agreement upon the occurrence of Cause."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "definition_term": "Cause",
            "reasoning": "Operative termination right, scoped by a defined term.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = tpe.extract_termination_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None
    assert "Cause" in facts.ai_identified_definition_or_reference

    decision = tpe.evaluate_termination_policy(facts, FakePolicy())
    assert decision.state == tpe.REQUIRES_REVIEW


def test_ai_identified_unresolvable_definition_never_disappears(monkeypatch):
    """The document never actually defines "Cause" -- the candidate is
    correctly NOT_ADMITTED, but the failure must not vanish into
    CONFIRMED_ABSENT."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "Customer may walk away from this Agreement upon the occurrence of Cause."
    quote = doc

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "definition_term": "Cause",
            "reasoning": "...",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = tpe.extract_termination_facts(doc)
    assert facts is not None
    assert facts.absence_state != "RECOGNITION_UNCERTAIN"
    assert facts.ai_identified_definition_or_reference is not None
    decision = tpe.evaluate_termination_policy(facts, FakePolicy())
    assert decision.state == tpe.REQUIRES_REVIEW


def test_ai_identified_cross_reference_resolved_forces_review(monkeypatch):
    """Adapter-level cross-reference proof (Part 4): the right to walk
    away is scoped by a cross-referenced section; resolved
    deterministically, must force review, never disappear because the
    right otherwise reads clean."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        "2. Miscellaneous. Customer may walk away from this Agreement at any time upon 30 days' "
        "written notice, subject to Section 8.2.\n\n"
        "Section 8.2 Notice Procedures. Notice must be delivered via certified mail and is not "
        "effective until actually received by the other party."
    )
    quote = (
        "Customer may walk away from this Agreement at any time upon 30 days' written notice, "
        "subject to Section 8.2."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None,
            "cross_reference_text": "Section 8.2",
            "reasoning": "Operative right to end the agreement, scoped by a cross-referenced section.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = tpe.extract_termination_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None
    assert "Notice Procedures" in facts.ai_identified_definition_or_reference

    decision = tpe.evaluate_termination_policy(facts, FakePolicy())
    assert decision.state == tpe.REQUIRES_REVIEW


def test_competing_readings_never_reach_the_adapter_as_authoritative(monkeypatch):
    """Adapter-level competing-reading proof (Part 5): two materially
    different, independently-grounded readings must never be resolved by
    picking one -- the document must not silently collapse to
    CONFIRMED_ABSENT even though a real candidate was discovered."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Customer's rights are addressed in this section; one reading permits Customer to walk away "
        "at any time, another treats the right as available only after a material breach."
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
                "proposition": "Customer may walk away at any time.",
                "evidence_quote": "one reading permits Customer to walk away at any time",
            },
            "competing_reading_b": {
                "proposition": "Customer may walk away only after a material breach.",
                "evidence_quote": "another treats the right as available only after a material breach",
            },
            "reasoning": "Two materially different readings of the same sentence.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = tpe.extract_termination_facts(doc)
    assert facts is not None
    assert facts.rights == []
    assert facts.ai_identified_definition_or_reference is not None

    decision = tpe.evaluate_termination_policy(facts, FakePolicy())
    assert decision.state == tpe.REQUIRES_REVIEW
