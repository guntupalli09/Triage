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


def test_decision_sensitivity_ai_identified_condition_forces_review(monkeypatch):
    """Paired decision-sensitivity test (final trust architecture Phase 8):
    DOCUMENT A (no modifier) reaches a resolved condition state; DOCUMENT B
    (same base obligation + a material condition phrased outside
    policy_engine_core's regex vocabulary) must not silently reach the
    same clean state -- it must force REQUIRES_REVIEW-equivalent
    unresolved-condition handling."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    cap_text = "Customer shall settle each statement of account within thirty days of its issuance"
    condition_text = "in the event Customer's designated payment method lapses, this timeline shall not apply"

    # Document A: base obligation only, no modifier.
    doc_a = f"9. Miscellaneous. {cap_text}."
    fake_a = _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))

    def fake_urlopen_a(*args, **kwargs):
        fake_urlopen_a.n += 1
        if fake_urlopen_a.n == 1:
            return fake_a
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative payment obligation, no conditions found.",
        }))
    fake_urlopen_a.n = 0

    with patch("urllib.request.urlopen", side_effect=fake_urlopen_a):
        facts_a = pte.extract_payment_facts(doc_a)
    assert facts_a is not None
    assert facts_a.condition.status == "UNCONDITIONAL"

    # Document B: same base obligation, PLUS a material condition phrased
    # using "in the event ... lapses" -- outside _LEADING_CONDITION_RE /
    # _TRAILING_PROVISO_RE's vocabulary (confirmed by the test's own
    # premise assertion below, exactly like the liability precedent).
    from policy_engine_core import detect_condition_in_span
    doc_b = f"9. Miscellaneous. {cap_text}, {condition_text}."
    deterministic_check = detect_condition_in_span(
        doc_b, doc_b.index(cap_text), doc_b.index(cap_text) + len(cap_text) + len(condition_text) + 2,
    )
    assert deterministic_check.status == "UNCONDITIONAL", "test premise violated: deterministic detector already sees this condition"

    def fake_urlopen_b(*args, **kwargs):
        fake_urlopen_b.n += 1
        if fake_urlopen_b.n == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": condition_text, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative payment obligation, but conditioned on the payment method remaining valid.",
        }))
    fake_urlopen_b.n = 0

    with patch("urllib.request.urlopen", side_effect=fake_urlopen_b):
        facts_b = pte.extract_payment_facts(doc_b)
    assert facts_b is not None
    assert facts_b.condition.status == "ESTABLISHED"
    assert facts_b.condition.evidence_span == condition_text

    # A and B must NOT resolve to the same "no unresolved condition" shape.
    assert facts_a.condition.status != facts_b.condition.status


def test_ai_identified_definition_dependency_survives_into_the_decision(monkeypatch):
    """Adapter-completion pass: the payment obligation depends on a
    defined term ("Statement Date"); the resolved definition must force
    review, never disappear because the base obligation reads clean."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        '1. Definitions. "Statement Date" means the date Vendor issues a statement of account. '
        "9. Miscellaneous. Customer shall settle each statement of account within thirty days "
        "of the Statement Date."
    )
    quote = "Customer shall settle each statement of account within thirty days of the Statement Date."

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "definition_term": "Statement Date",
            "reasoning": "Operative payment-timing obligation, scoped by a defined term.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = pte.extract_payment_facts(doc)
    assert facts is not None
    assert facts.condition is not None
    assert facts.condition.status == "ESTABLISHED"
    assert "Statement Date" in facts.condition.evidence_span

    class FullFakePolicy:
        contract_side = "vendor"
        escalation_approval_authority = None
        fallback_text = None
        acceptable_max_net_days = None
        maximum_late_interest_rate_percent = None
        maximum_price_increase_percent = None
        minimum_dispute_notice_days = None
        minimum_price_increase_notice_days = None
        prohibit_disputed_amount_withholding = False
        prohibit_set_off = False
        prohibit_unilateral_price_increase = False
        require_counterparty_is_payor = False
        require_expense_preapproval = False
        require_refund_entitlement = False
        require_tax_responsibility_counterparty = False
        require_undisputed_amounts_still_payable = False
        required_currency = None
        required_payment_trigger = None

    decision = pte.evaluate_payment_policy(facts, FullFakePolicy())
    assert decision.state == pte.REQUIRES_REVIEW


def test_ai_identified_unresolvable_cross_reference_forces_review_not_absent(monkeypatch):
    """The candidate payment obligation points to a Schedule never
    actually attached. No engagement anchor exists at all, so the
    candidate never becomes a structured obligation -- but this must
    force REQUIRES_REVIEW (DEPENDENCY_UNRESOLVED), never fall back to
    CONFIRMED_ABSENT."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "Customer shall settle each statement of account per the rates set forth in Schedule D."
    quote = doc

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None,
            "cross_reference_text": "Schedule D",
            "reasoning": "Operative payment-timing obligation, priced per an attached schedule.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = pte.extract_payment_facts(doc)
    assert facts is not None
    assert facts.absence_state == "DEPENDENCY_UNRESOLVED"

    decision = pte.evaluate_payment_policy(facts, FakePolicy())
    assert decision.state == pte.REQUIRES_REVIEW


def test_competing_readings_never_reach_the_adapter_as_authoritative(monkeypatch):
    """Adapter-level competing-reading proof (Part 5): two materially
    different, independently-grounded readings of the payment timing
    must never be resolved by picking one -- the document must not
    silently collapse to CONFIRMED_ABSENT even though a real candidate
    was discovered."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Customer's settlement obligation is addressed in this section; one reading requires "
        "settlement within thirty days of the statement date, another treats the timing as "
        "negotiable on a case-by-case basis."
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
                "proposition": "Settlement is due within thirty days.",
                "evidence_quote": "one reading requires settlement within thirty days of the statement date",
            },
            "competing_reading_b": {
                "proposition": "Settlement timing is negotiable.",
                "evidence_quote": "another treats the timing as negotiable on a case-by-case basis",
            },
            "reasoning": "Two materially different readings of the same sentence.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = pte.extract_payment_facts(doc)
    assert facts is not None
    assert facts.absence_state == "DEPENDENCY_UNRESOLVED"

    decision = pte.evaluate_payment_policy(facts, FakePolicy())
    assert decision.state == pte.REQUIRES_REVIEW
