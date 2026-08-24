"""Tests for ip_ownership_policy_engine.py's fact-admission integration.
Mirrors tests/test_data_security_fact_admission.py's structure.
IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED defaults to False; each test flips
it on for its own duration only.
"""
import json
from unittest.mock import MagicMock, patch

import ip_ownership_policy_engine as ipoe


def setup_function(_):
    ipoe.IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    ipoe.IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED = False


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
    require_we_retain_background_ip = False
    require_we_own_work_product = False
    require_customer_own_work_product = False
    prohibit_work_product_includes_background_ip = False
    require_exclusive_license = False
    require_license_exclusive = False
    require_royalty_free = False
    prohibit_royalty_bearing_license = False
    require_perpetual_license = False
    require_irrevocable_license = False
    prohibit_revocable_license = False
    require_sublicensable = False
    require_transferable = False
    require_worldwide_territory = False
    prohibit_derivative_works = False
    prohibit_joint_ownership = False
    require_license_for_embedded_background_ip = False
    require_purpose_limited_license = False
    require_feedback_assigned = False
    require_residual_knowledge_rights = False
    require_open_source_disclosure = False
    require_infringement_remedy_reference = False
    require_post_termination_survival = False


def test_disabled_by_default_is_confirmed_absent(monkeypatch):
    ipoe.IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = ipoe.extract_ip_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = ipoe.extract_ip_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review_never_accept(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = ipoe.extract_ip_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = ipoe.evaluate_ip_policy(facts, FakePolicy())
    assert decision.state == ipoe.REQUIRES_REVIEW


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = ipoe.extract_ip_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_candidate_never_becomes_a_window(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = ipoe.extract_ip_facts(doc)
    assert facts is None


def test_verified_semantic_candidate_seeds_a_window_and_is_classified(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. All deliverables created by Vendor under this Agreement shall be "
        "solely owned by Customer."
    )
    quote = "All deliverables created by Vendor under this Agreement shall be solely owned by Customer."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative work-product ownership assignment.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ipoe.extract_ip_facts(doc)
    assert facts is not None
    assert facts.clause_found is True
    assert "work_product" in facts.ownership_attributions


def test_verifier_not_established_descriptive_language_never_admitted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. In this type of agreement, vendors typically retain ownership of pre-existing "
        "inventions while assigning newly created deliverables, although this Agreement does not "
        "itself state such a term."
    )
    quote = "vendors typically retain ownership of pre-existing inventions while assigning newly created deliverables"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive statement about typical industry drafting, not operative language of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = ipoe.extract_ip_facts(doc)
    assert facts is None


def test_decision_sensitivity_ai_identified_condition_forces_review(monkeypatch):
    """Paired decision-sensitivity test: document A resolves ownership
    cleanly via the deterministic ownership regexes; document B adds a
    material condition phrased outside the deterministic condition
    vocabulary. A and B must not resolve to the same clean outcome."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    cap_text = "All deliverables created by Vendor under this Agreement shall be solely owned by Customer"
    condition_text = "in the event Vendor's engagement terminates early, this assignment shall not apply"

    doc_a = f"9. Miscellaneous. {cap_text}."

    def fake_urlopen_a(*args, **kwargs):
        fake_urlopen_a.n += 1
        if fake_urlopen_a.n == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative work-product ownership assignment, no conditions found.",
        }))
    fake_urlopen_a.n = 0

    with patch("urllib.request.urlopen", side_effect=fake_urlopen_a):
        facts_a = ipoe.extract_ip_facts(doc_a)
    assert facts_a is not None
    assert facts_a.ai_identified_condition is None
    decision_a = ipoe.evaluate_ip_policy(facts_a, FakePolicy())
    assert decision_a.state != ipoe.REQUIRES_REVIEW

    doc_b = f"9. Miscellaneous. {cap_text}, {condition_text}."

    def fake_urlopen_b(*args, **kwargs):
        fake_urlopen_b.n += 1
        if fake_urlopen_b.n == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": condition_text, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative work-product ownership assignment, conditioned on continued engagement.",
        }))
    fake_urlopen_b.n = 0

    with patch("urllib.request.urlopen", side_effect=fake_urlopen_b):
        facts_b = ipoe.extract_ip_facts(doc_b)
    assert facts_b is not None
    assert facts_b.ai_identified_condition == condition_text
    decision_b = ipoe.evaluate_ip_policy(facts_b, FakePolicy())
    assert decision_b.state == ipoe.REQUIRES_REVIEW
    assert condition_text in "; ".join(decision_b.unresolved_facts)
