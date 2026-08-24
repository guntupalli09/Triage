"""Tests for sla_policy_engine.py's fact-admission integration. Mirrors
tests/test_warranties_fact_admission.py's structure.
SLA_SEMANTIC_DISCOVERY_ENABLED defaults to False; each test flips it on
for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import sla_policy_engine as sle


def setup_function(_):
    sle.SLA_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    sle.SLA_SEMANTIC_DISCOVERY_ENABLED = False


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
    min_uptime_percent = None
    require_service_credits = False
    max_credit_cap_percent = None
    require_exclusive_remedy = False
    minimum_acceptable_uptime_percent = None
    minimum_claim_submission_days = None
    minimum_credit_cap_percent_of_fees = None
    minimum_credit_percent_of_fees = None
    permitted_maintenance_exclusions_json = []
    prohibit_service_credits_as_exclusive_remedy = False
    require_chronic_failure_remedy = False
    require_severity_tiers = False
    require_termination_right_for_chronic_failure = False
    require_uptime_commitment = False
    required_support_hours = None
    p1_max_response_hours = None
    p1_response_basis = None
    p1_max_restoration_hours = None
    p1_restoration_basis = None
    p2_max_response_hours = None
    p2_response_basis = None
    p2_max_restoration_hours = None
    p2_restoration_basis = None
    p3_max_response_hours = None
    p3_response_basis = None
    p3_max_restoration_hours = None
    p3_restoration_basis = None
    p4_max_response_hours = None
    p4_response_basis = None
    p4_max_restoration_hours = None
    p4_restoration_basis = None


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    sle.SLA_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = sle.extract_sla_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = sle.extract_sla_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review_not_not_applicable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = sle.extract_sla_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = sle.evaluate_sla_policy(facts, FakePolicy())
    assert decision.state == sle.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = sle.extract_sla_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_window(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = sle.extract_sla_facts(doc)
    assert facts is None


def test_verified_semantic_candidate_seeds_a_window(monkeypatch):
    """Uses phrasing with no 'uptime'/'SLA'/'availability' word so the
    deterministic anchor genuinely finds nothing and the semantic path is
    exercised."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. The system shall be operational and reachable 99.9% of the time "
        "each calendar month, measured over rolling 24-hour periods."
    )
    quote = (
        "The system shall be operational and reachable 99.9% of the time each calendar month, "
        "measured over rolling 24-hour periods."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative availability commitment.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = sle.extract_sla_facts(doc)
    assert facts is not None
    assert facts.clause_found is True


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. This type of agreement typically guarantees the system will be "
        "operational and reachable 99.9% of the time, although this Agreement does not "
        "itself impose such a requirement."
    )
    quote = "this type of agreement typically guarantees the system will be operational and reachable 99.9% of the time"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive statement about typical drafting, not operative language of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = sle.extract_sla_facts(doc)
    assert facts is None


def test_decision_sensitivity_ai_identified_condition_forces_review(monkeypatch):
    """Paired decision-sensitivity test: document A (clean availability
    commitment that deterministically structures a measurement period)
    resolves; document B (same commitment + a condition outside the
    deterministic vocabulary) forces REQUIRES_REVIEW."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    cap_text = (
        "The system shall be operational and reachable 99.9% of the time each calendar month, "
        "measured over rolling 24-hour periods"
    )
    condition_text = "in the event a third-party network outage occurs, this commitment shall not apply"

    doc_a = f"{cap_text}."

    def fake_urlopen_a(*args, **kwargs):
        fake_urlopen_a.n += 1
        if fake_urlopen_a.n == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative availability commitment, no conditions found.",
        }))
    fake_urlopen_a.n = 0

    with patch("urllib.request.urlopen", side_effect=fake_urlopen_a):
        facts_a = sle.extract_sla_facts(doc_a)
    assert facts_a is not None
    assert facts_a.ai_identified_condition is None
    decision_a = sle.evaluate_sla_policy(facts_a, FakePolicy())
    assert decision_a.state != sle.REQUIRES_REVIEW

    doc_b = f"{cap_text}, {condition_text}."

    def fake_urlopen_b(*args, **kwargs):
        fake_urlopen_b.n += 1
        if fake_urlopen_b.n == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": condition_text, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative availability commitment, conditioned on network continuity.",
        }))
    fake_urlopen_b.n = 0

    with patch("urllib.request.urlopen", side_effect=fake_urlopen_b):
        facts_b = sle.extract_sla_facts(doc_b)
    assert facts_b is not None
    assert facts_b.ai_identified_condition == condition_text
    decision_b = sle.evaluate_sla_policy(facts_b, FakePolicy())
    assert decision_b.state == sle.REQUIRES_REVIEW
    assert condition_text in "; ".join(decision_b.unresolved_facts)


def test_ai_identified_definition_dependency_survives_into_the_decision(monkeypatch):
    """Adapter-completion pass: the availability commitment depends on a
    defined term ("Scheduled Maintenance"); the resolved definition must
    force review, never disappear because the commitment otherwise reads
    clean."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    cap_text = (
        "The system shall be operational and reachable 99.9% of the time each calendar month, "
        "excluding Scheduled Maintenance, measured over rolling 24-hour periods"
    )
    doc = (
        '9. Miscellaneous. "Scheduled Maintenance" means planned downtime communicated at least '
        f"48 hours in advance. {cap_text}."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "definition_term": "Scheduled Maintenance",
            "reasoning": "Operative availability commitment, scoped by a defined term.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = sle.extract_sla_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None
    assert "Scheduled Maintenance" in facts.ai_identified_definition_or_reference

    decision = sle.evaluate_sla_policy(facts, FakePolicy())
    assert decision.state == sle.REQUIRES_REVIEW
    assert "Scheduled Maintenance" in "; ".join(decision.unresolved_facts)
