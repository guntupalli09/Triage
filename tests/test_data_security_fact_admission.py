"""Tests for data_security_policy_engine.py's fact-admission integration.
Mirrors tests/test_liability_fact_admission.py's structure and mocking
pattern. DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED defaults to False; each
test flips it on for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import data_security_policy_engine as dse


def setup_function(_):
    dse.DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    dse.DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = False


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
    require_processor_role = False
    prohibit_unrestricted_subprocessors = False
    require_subprocessor_notice_or_consent = "not_required"
    max_breach_notification_hours = None
    require_scc_or_adequacy_for_transfers = False
    prohibit_data_transfer = False
    require_deletion_or_return = False
    max_retention_days = None
    require_audit_rights = False
    require_named_security_certification = False
    require_cooperation_obligation = False
    acceptable_max_breach_notification_hours = None
    negotiate_max_breach_notification_hours = None
    preferred_breach_notification_hours = None
    require_confidentiality_of_personal_data = False
    require_data_residency = False
    require_fixed_breach_notification_period = False
    require_international_transfer_safeguard = False
    required_data_residency_regions_json = []


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    dse.DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = dse.extract_data_security_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = dse.extract_data_security_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review_never_accept(monkeypatch):
    """Critical for this adapter specifically: an all-None facts object
    with clause_found=True could otherwise resolve to ACCEPT under a
    permissive playbook (no dimension required) -- the explicit
    absence_state check must intercept before that dimension logic runs."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = dse.extract_data_security_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = dse.evaluate_data_security_policy(facts, FakePolicy())
    assert decision.state == dse.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = dse.extract_data_security_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_window(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = dse.extract_data_security_facts(doc)
    assert facts is None


def test_verified_semantic_candidate_seeds_a_window_and_is_classified(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. Vendor shall notify Customer within 48 hours of becoming aware of any "
        "data breach affecting Customer's data."
    )
    quote = "Vendor shall notify Customer within 48 hours of becoming aware of any data breach affecting Customer's data."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative breach-notification obligation.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = dse.extract_data_security_facts(doc)
    assert facts is not None
    assert facts.clause_found is True
    assert facts.breach_notification_hours == 48


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. Companies generally notify customers of data breaches within a reasonable time, "
        "although this Agreement does not itself impose such a requirement."
    )
    quote = "Companies generally notify customers of data breaches within a reasonable time"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive statement about general industry practice, not operative language of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = dse.extract_data_security_facts(doc)
    assert facts is None


def test_decision_sensitivity_ai_identified_condition_forces_review(monkeypatch):
    """Paired decision-sensitivity test: document A resolves the breach-
    notification obligation cleanly; document B adds a material condition
    outside the deterministic vocabulary and must not reach the same
    clean outcome."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    cap_text = (
        "Vendor shall notify Customer within 48 hours of becoming aware of any data breach "
        "affecting Customer's data"
    )
    condition_text = "in the event Vendor's incident-response vendor changes, this timeline shall not apply"

    doc_a = f"9. Miscellaneous. {cap_text}."

    def fake_urlopen_a(*args, **kwargs):
        fake_urlopen_a.n += 1
        if fake_urlopen_a.n == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative breach-notification obligation, no conditions found.",
        }))
    fake_urlopen_a.n = 0

    with patch("urllib.request.urlopen", side_effect=fake_urlopen_a):
        facts_a = dse.extract_data_security_facts(doc_a)
    assert facts_a is not None
    assert facts_a.ai_identified_condition is None
    decision_a = dse.evaluate_data_security_policy(facts_a, FakePolicy())
    assert decision_a.state != dse.REQUIRES_REVIEW

    doc_b = f"9. Miscellaneous. {cap_text}, {condition_text}."

    def fake_urlopen_b(*args, **kwargs):
        fake_urlopen_b.n += 1
        if fake_urlopen_b.n == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": condition_text, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative breach-notification obligation, conditioned on vendor continuity.",
        }))
    fake_urlopen_b.n = 0

    with patch("urllib.request.urlopen", side_effect=fake_urlopen_b):
        facts_b = dse.extract_data_security_facts(doc_b)
    assert facts_b is not None
    assert facts_b.ai_identified_condition == condition_text
    decision_b = dse.evaluate_data_security_policy(facts_b, FakePolicy())
    assert decision_b.state == dse.REQUIRES_REVIEW
    assert condition_text in "; ".join(decision_b.unresolved_facts)


def test_ai_identified_definition_dependency_survives_into_the_decision(monkeypatch):
    """Adapter-completion pass: the notification obligation depends on a
    defined term ("Reportable Event"); the resolved definition must
    force review, never disappear because the base obligation reads
    clean."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        '1. Definitions. "Reportable Event" means unauthorized access to Customer\'s data. '
        "9. Miscellaneous. Vendor shall notify Customer within 48 hours of becoming aware of "
        "any Reportable Event affecting Customer's data."
    )
    quote = (
        "Vendor shall notify Customer within 48 hours of becoming aware of any Reportable "
        "Event affecting Customer's data."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "definition_term": "Reportable Event",
            "reasoning": "Operative breach-notification obligation, scoped by a defined term.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = dse.extract_data_security_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None
    assert "Reportable Event" in facts.ai_identified_definition_or_reference

    decision = dse.evaluate_data_security_policy(facts, FakePolicy())
    assert decision.state == dse.REQUIRES_REVIEW
    assert "Reportable Event" in "; ".join(decision.unresolved_facts)


def test_ai_identified_cross_reference_resolved_forces_review(monkeypatch):
    """Adapter-level cross-reference proof (Part 4)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. Vendor shall notify Customer within 48 hours of becoming aware of any "
        "Reportable Event affecting Customer's data, subject to Section 9.4.\n\n"
        "Section 9.4 Notification Procedures. Notice shall be delivered to the security contact "
        "designated in the order form and confirmed by phone within one business day."
    )
    quote = (
        "Vendor shall notify Customer within 48 hours of becoming aware of any Reportable Event "
        "affecting Customer's data, subject to Section 9.4."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None,
            "cross_reference_text": "Section 9.4",
            "reasoning": "Operative breach-notification obligation, scoped by a cross-referenced section.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = dse.extract_data_security_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None
    assert "Notification Procedures" in facts.ai_identified_definition_or_reference

    decision = dse.evaluate_data_security_policy(facts, FakePolicy())
    assert decision.state == dse.REQUIRES_REVIEW


def test_competing_readings_never_reach_the_adapter_as_authoritative(monkeypatch):
    """Adapter-level competing-reading proof (Part 5)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Vendor's notification obligation is addressed in this section; one reading requires notice "
        "within 48 hours, another treats notice timing as discretionary."
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
                "proposition": "Notice is required within 48 hours.",
                "evidence_quote": "one reading requires notice within 48 hours",
            },
            "competing_reading_b": {
                "proposition": "Notice timing is discretionary.",
                "evidence_quote": "another treats notice timing as discretionary",
            },
            "reasoning": "Two materially different readings of the same sentence.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = dse.extract_data_security_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None

    decision = dse.evaluate_data_security_policy(facts, FakePolicy())
    assert decision.state == dse.REQUIRES_REVIEW
