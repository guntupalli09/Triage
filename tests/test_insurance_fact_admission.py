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
    cgl_minimum_aggregate = None
    minimum_cancellation_notice_days = None
    require_claims_made_tail = False
    require_counterparty_obligated = False
    require_evidence_before_commencement = False
    require_minimum_insurer_rating = False
    require_notice_of_cancellation = False
    require_policy_maintenance_through_term = False


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    ine.INSURANCE_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    facts = ine.extract_insurance_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    facts = ine.extract_insurance_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review_never_accept(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    facts = ine.extract_insurance_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = ine.evaluate_insurance_policy(facts, FakePolicy())
    assert decision.state == ine.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = ine.extract_insurance_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_window(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = ine.extract_insurance_facts(doc)
    assert facts is None


def test_verified_semantic_candidate_seeds_a_window(monkeypatch):
    """Uses phrasing deliberately outside _ANCHOR_RE's vocabulary
    (no 'insurance'/'liability'/'coverage' words) so the deterministic
    anchor genuinely finds nothing and the semantic path is exercised."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
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
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
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


def test_decision_sensitivity_ai_identified_condition_forces_review(monkeypatch):
    """Paired decision-sensitivity test: document A (no modifier) reaches
    ACCEPT under a permissive playbook; document B adds a material
    condition -- it must not reach the same clean ACCEPT."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    cap_text = (
        "Vendor shall maintain a risk-transfer policy with a reputable underwriter covering "
        "third-party bodily injury claims arising from its operations."
    )
    condition_text = "in the event Vendor's underwriter downgrades its rating, this requirement shall not apply"

    def fake_urlopen_a(*args, **kwargs):
        fake_urlopen_a.n += 1
        if fake_urlopen_a.n == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative insurance-maintenance obligation, no conditions found.",
        }))
    fake_urlopen_a.n = 0

    with patch("urllib.request.urlopen", side_effect=fake_urlopen_a):
        facts_a = ine.extract_insurance_facts(cap_text)
    assert facts_a is not None
    assert facts_a.ai_identified_condition is None
    decision_a = ine.evaluate_insurance_policy(facts_a, FakePolicy())
    assert decision_a.state != ine.REQUIRES_REVIEW

    doc_b = f"{cap_text} {condition_text}."

    def fake_urlopen_b(*args, **kwargs):
        fake_urlopen_b.n += 1
        if fake_urlopen_b.n == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": condition_text, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative insurance-maintenance obligation, conditioned on rating continuity.",
        }))
    fake_urlopen_b.n = 0

    with patch("urllib.request.urlopen", side_effect=fake_urlopen_b):
        facts_b = ine.extract_insurance_facts(doc_b)
    assert facts_b is not None
    assert facts_b.ai_identified_condition == condition_text
    decision_b = ine.evaluate_insurance_policy(facts_b, FakePolicy())
    assert decision_b.state == ine.REQUIRES_REVIEW
    assert condition_text in "; ".join(decision_b.unresolved_facts)


def test_ai_identified_definition_dependency_survives_into_the_decision(monkeypatch):
    """Adapter-completion pass: the risk-transfer obligation depends on a
    defined term ("Named Underwriter"); the resolved definition must
    force review, never disappear because the base obligation reads
    clean."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        '1. Definitions. "Named Underwriter" means an underwriter carrying at minimum an A- rating. '
        "9. Miscellaneous. Vendor shall maintain a risk-transfer policy with a Named Underwriter "
        "covering third-party bodily injury claims arising from its operations."
    )
    quote = (
        "Vendor shall maintain a risk-transfer policy with a Named Underwriter covering "
        "third-party bodily injury claims arising from its operations."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "definition_term": "Named Underwriter",
            "reasoning": "Operative insurance-maintenance obligation, scoped by a defined term.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ine.extract_insurance_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None
    assert "Named Underwriter" in facts.ai_identified_definition_or_reference

    decision = ine.evaluate_insurance_policy(facts, FakePolicy())
    assert decision.state == ine.REQUIRES_REVIEW
    assert "Named Underwriter" in "; ".join(decision.unresolved_facts)


def test_ai_identified_cross_reference_resolved_forces_review(monkeypatch):
    """Adapter-level cross-reference proof (Part 4)."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. Vendor shall maintain a risk-transfer policy with a reputable underwriter "
        "covering third-party bodily injury claims arising from its operations, subject to Section 9.4.\n\n"
        "Section 9.4 Evidence of Coverage. Vendor shall furnish a certificate confirming the policy "
        "remains in force within ten days of Customer's request."
    )
    quote = (
        "Vendor shall maintain a risk-transfer policy with a reputable underwriter covering "
        "third-party bodily injury claims arising from its operations, subject to Section 9.4."
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
            "reasoning": "Operative insurance-maintenance obligation, scoped by a cross-referenced section.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ine.extract_insurance_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None
    assert "Evidence of Coverage" in facts.ai_identified_definition_or_reference

    decision = ine.evaluate_insurance_policy(facts, FakePolicy())
    assert decision.state == ine.REQUIRES_REVIEW


def test_competing_readings_never_reach_the_adapter_as_authoritative(monkeypatch):
    """Adapter-level competing-reading proof (Part 5)."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Vendor's risk-transfer obligation is addressed in this section; one reading requires "
        "coverage of third-party claims, another treats coverage as optional at Vendor's discretion."
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
                "proposition": "Coverage of third-party claims is required.",
                "evidence_quote": "one reading requires coverage of third-party claims",
            },
            "competing_reading_b": {
                "proposition": "Coverage is optional.",
                "evidence_quote": "another treats coverage as optional at Vendor's discretion",
            },
            "reasoning": "Two materially different readings of the same sentence.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ine.extract_insurance_facts(doc)
    assert facts is not None
    assert facts.ai_identified_definition_or_reference is not None

    decision = ine.evaluate_insurance_policy(facts, FakePolicy())
    assert decision.state == ine.REQUIRES_REVIEW
