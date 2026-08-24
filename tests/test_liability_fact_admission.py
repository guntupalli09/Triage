"""Tests for liability_policy_engine.py's fact-admission integration —
the reference adapter for generalizing indemnification's proven
semantic-discovery + absence-state pattern via the shared fact_admission.py
framework (see artifacts/fact_admission_architecture/PRE_IMPLEMENTATION_MAP.md).

Mirrors tests/test_step4a9_2_real_provider_adversarial.py's mocking
pattern. LIABILITY_SEMANTIC_DISCOVERY_ENABLED defaults to False in
production/CI (see liability_policy_engine.py) — every test here flips it
on for the duration of the test only, so the default-off regression suite
in tests/test_liability_policy_engine.py is unaffected.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

import liability_policy_engine as lpe
import policy_engine_core as pec


def setup_function(_):
    lpe.LIABILITY_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    lpe.LIABILITY_SEMANTIC_DISCOVERY_ENABLED = False


def _fake_response(content_text: str):
    body = json.dumps({
        "content": [{"type": "text", "text": content_text}],
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = False
    return cm


def test_semantic_discovery_disabled_by_default_is_confirmed_absent(monkeypatch):
    """With the flag off (the default), behavior is byte-identical to
    before this integration existed: no API key required, no network call
    made, plain regex-only NOT_APPLICABLE."""
    lpe.LIABILITY_SEMANTIC_DISCOVERY_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = lpe.extract_liability_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_provider_unavailable_is_recognition_uncertain_not_confirmed_absent(monkeypatch):
    """Core Step 5/16 invariant: a provider outage must never silently
    become 'confirmed absent'."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    facts = lpe.extract_liability_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is not None
    assert facts.clause_found is True
    assert facts.provisions == []
    assert facts.absence_state == "RECOGNITION_UNCERTAIN"
    assert facts.semantic_discovery_error is not None


def test_recognition_uncertain_routes_to_requires_review_not_not_applicable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class FakePolicy:
        preferred_multiplier = 1.0
        acceptable_max_multiplier = 1.0
        negotiate_max_multiplier = 2.0
        prohibit_unlimited = True
        required_exceptions_json = []
        fallback_text = None
        contract_side = "vendor"
        escalation_approval_authority = None

    facts = lpe.extract_liability_facts("This Agreement shall be governed by the laws of Delaware.")
    decision = lpe.evaluate_liability_policy(facts, FakePolicy())
    assert decision.state == lpe.REQUIRES_REVIEW
    assert "not the same as confirming" in decision.explanation


def test_confirmed_absent_when_discovery_runs_and_finds_nothing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = lpe.extract_liability_facts("This Agreement shall be governed by the laws of Delaware.")
    assert facts is None


def test_hallucinated_semantic_candidate_never_becomes_a_provision(monkeypatch):
    """The discovery-stage exact-substring check must discard a fabricated
    quote before it can ever reach verification/admission."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "This Agreement shall be governed by the laws of Delaware."
    fake = _fake_response(json.dumps({"candidates": [{"quote": "This text is not in the document at all."}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        facts = lpe.extract_liability_facts(doc)
    assert facts is None


def test_verified_semantic_candidate_becomes_a_provision(monkeypatch):
    """A semantically-discovered candidate that a real verifier claims
    ESTABLISHED, and whose evidence quote grounds, is admitted and treated
    as a real anchor — feeding the same deterministic _extract_provision
    structuring any regex-found anchor would go through."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. Neither party shall be liable for any amount in excess of "
        "the total fees paid by Customer in the twelve months preceding the claim."
    )
    quote = (
        "Neither party shall be liable for any amount in excess of the total fees paid "
        "by Customer in the twelve months preceding the claim."
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "reasoning": "Operative mutual liability cap, no conditions found.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = lpe.extract_liability_facts(doc)
    assert facts is not None
    assert facts.clause_found is True
    assert len(facts.provisions) == 1


def test_verifier_not_established_never_becomes_a_provision(monkeypatch):
    """The known-failure-class regression, applied to liability: a
    plausible-looking candidate span that the adversarial verifier
    classifies as descriptive/non-operative must not become a provision."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Background. Industry practice often limits vendor liability to fees paid, "
        "although this Agreement does not itself adopt that approach."
    )
    quote = "Industry practice often limits vendor liability to fees paid"

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "NOT_ESTABLISHED", "evidence_quote": None,
            "reasoning": "Descriptive background statement about industry practice, not operative language of this agreement.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = lpe.extract_liability_facts(doc)
    assert facts is None


def test_ai_identified_condition_survives_to_forced_review_the_mission_critical_case(monkeypatch):
    """THE critical adversarial case (final trust architecture, Phase 6):
    the base obligation looks clean (an ordinary, fully-comparable fee-
    multiplier cap), but a material condition — phrased using "in the
    event ... lapses" rather than any of policy_engine_core's regex
    vocabulary (if/when/unless/provided that/except/so long as/etc, see
    _LEADING_CONDITION_RE / _TRAILING_PROVISO_RE) — changes what the
    clause actually establishes. The deterministic condition detector
    genuinely cannot see this phrasing; only the AI verifier's own
    contextual read notices it. Proves the complete chain end to end:

      1. AI/context layer notices the material modifier (mocked verifier
         response includes condition_quote)
      2. Candidate schema preserves it (VerificationResult.condition_quote)
      3. Deterministic grounding verifies it (ground_qualifiers, exact
         substring match against the untouched source text)
      4. Admitted fact preserves it (CandidateMaterialFact.condition)
      5. Adapter receives it (Provision.condition, via the position-
         matched wiring in extract_liability_facts)
      6. Policy result reflects it (REQUIRES_REVIEW, never a clean ACCEPT)

    The forbidden outcome this test rules out: AI identifies the
    condition -> condition disappears -> simplified (unconditioned) fact
    becomes ESTABLISHED -> deterministic adapter issues a clean ACCEPT."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    condition_text = (
        "in the event Vendor's SOC 2 certification lapses during the term, this limitation shall not apply"
    )
    cap_text = (
        "Neither party shall be liable for any amount in excess of the total fees paid by Customer in the "
        "twelve months preceding the claim"
    )
    doc = f"9. Miscellaneous. {cap_text}, {condition_text}."

    # Confirm, as part of this test's own premise, that the deterministic
    # condition detector genuinely does not see this phrasing on its own —
    # otherwise this test would not actually be exercising the AI path.
    from policy_engine_core import detect_condition_in_span
    deterministic_check = detect_condition_in_span(doc, doc.index(cap_text), doc.index(cap_text) + len(cap_text) + len(condition_text) + 2)
    assert deterministic_check.status == "UNCONDITIONAL", (
        "test premise violated: the deterministic detector already sees this condition, "
        "so it no longer exercises the AI-only path this test is for"
    )

    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": cap_text}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": cap_text,
            "condition_quote": condition_text, "exception_quote": None, "cross_reference_text": None,
            "reasoning": "Operative cap, but conditioned on continued SOC 2 certification.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = lpe.extract_liability_facts(doc)

    # Steps 1-5: the condition survived from AI verification through
    # grounding to the adapter's own Provision object.
    assert facts is not None
    assert len(facts.provisions) == 1
    provision = facts.provisions[0]
    assert provision.condition is not None
    assert provision.condition.status == "ESTABLISHED"
    assert provision.condition.evidence_span == condition_text

    # Step 6: the policy decision reflects it -- REQUIRES_REVIEW, never a
    # clean ACCEPT, even though the base cap is a perfectly ordinary,
    # fully-comparable fee-multiplier that would otherwise resolve cleanly.
    class FakePolicy:
        preferred_multiplier = 1.0
        acceptable_max_multiplier = 1.0
        negotiate_max_multiplier = 2.0
        prohibit_unlimited = True
        required_exceptions_json = []
        fallback_text = None
        contract_side = "vendor"
        escalation_approval_authority = None
        require_consequential_damages_exclusion = False
        required_consequential_carveouts_json = []

    decision = lpe.evaluate_liability_policy(facts, FakePolicy())
    assert decision.state == lpe.REQUIRES_REVIEW
    assert condition_text in "; ".join(decision.unresolved_facts)


def test_admitted_fact_produces_deterministic_replay_decision(monkeypatch):
    """Step 18 (deterministic replay): once a semantic candidate is
    admitted and structured into a Provision, repeated evaluation of the
    SAME facts against the SAME policy must produce a byte-identical
    PolicyDecision — the authority boundary (AI decides admission, never
    the decision) is deterministic even though the AI call itself is not
    required to be. This test fixes the facts (no further provider calls
    needed) and checks policy_engine_core's own determinism primitive
    over repeated evaluate_liability_policy() calls."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "9. Miscellaneous. Neither party shall be liable for any amount in excess of "
        "the total fees paid by Customer in the twelve months preceding the claim."
    )
    quote = (
        "Neither party shall be liable for any amount in excess of the total fees paid "
        "by Customer in the twelve months preceding the claim."
    )
    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({"status": "ESTABLISHED", "evidence_quote": quote, "reasoning": "Operative mutual liability cap."}))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = lpe.extract_liability_facts(doc)
    assert facts is not None

    class FakePolicy:
        preferred_multiplier = 1.0
        acceptable_max_multiplier = 1.0
        negotiate_max_multiplier = 2.0
        prohibit_unlimited = True
        required_exceptions_json = []
        fallback_text = None
        contract_side = "vendor"
        escalation_approval_authority = None
        require_consequential_damages_exclusion = False
        required_consequential_carveouts_json = []

    hashes = {pec.decision_hash(lpe.evaluate_liability_policy(facts, FakePolicy())) for _ in range(5)}
    assert len(hashes) == 1
