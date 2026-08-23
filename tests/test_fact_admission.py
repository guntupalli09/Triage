"""Tests for the shared fact-admission / semantic-verification framework
(fact_admission.py). Mirrors the mocking pattern already used in
tests/test_step4a9_2_real_provider_adversarial.py for the indemnification
adapter's real-provider integration. No live API calls — every test here
is mocked or purely deterministic, so it runs without ANTHROPIC_API_KEY.

Covers:
  - the authority-boundary guard (no policy field can ever land on
    CandidateMaterialFact)
  - discovery: hallucinated/non-verbatim quotes discarded, malformed
    response / missing key / network failure all fail closed
  - verification: every provider-failure mode (Step 16) resolves to
    VERIFICATION_ERROR, never NOT_ESTABLISHED
  - grounding: exact-substring requirement, no silent pass on a paraphrase
  - admission gate: only ESTABLISHED + grounding-pass + no unresolved
    dependency/conflict reaches ADMITTED; every other combination is
    NOT_ADMITTED (the asymmetric clean-safety rule, Step 6)
"""
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

import fact_admission as fa


def _fake_response(content_text: str, input_tokens=10, output_tokens=10):
    body = json.dumps({
        "content": [{"type": "text", "text": content_text}],
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = False
    return cm


# ---------------------------------------------------------------------------
# Authority boundary
# ---------------------------------------------------------------------------

def test_authority_boundary_intact():
    fa.assert_authority_boundary_intact()


def test_verification_result_rejects_unknown_status():
    with pytest.raises(ValueError):
        fa.VerificationResult(status="ACCEPT")


# ---------------------------------------------------------------------------
# Discovery (stage 1)
# ---------------------------------------------------------------------------

def test_discovery_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(fa.ProviderUnavailable):
        fa.discover_candidate_spans("some document text", "liability", "a limitation of liability provision")


def test_discovery_hallucinated_quote_discarded(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": [{"quote": "this text is not in the document"}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.discover_candidate_spans("The Vendor performs services.", "liability", "a liability cap")
    assert result == []


def test_discovery_verbatim_quote_grounds_offsets(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "Section 1. Vendor's liability shall not exceed fees paid in the prior 12 months."
    quote = "Vendor's liability shall not exceed fees paid in the prior 12 months."
    fake = _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.discover_candidate_spans(doc, "liability", "a liability cap")
    assert len(result) == 1
    cand = result[0]
    assert cand.start_offset == doc.find(quote)
    assert cand.end_offset == cand.start_offset + len(quote)
    assert cand.evidence_span == quote
    assert cand.clause_type == "liability"


def test_discovery_malformed_json_raises(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response("this is not json at all {{{")
    with patch("urllib.request.urlopen", return_value=fake):
        with pytest.raises(fa.ProviderUnavailable):
            fa.discover_candidate_spans("Some document.", "liability", "a liability cap")


def test_discovery_network_error_raises(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        with pytest.raises(fa.ProviderUnavailable):
            fa.discover_candidate_spans("Some document.", "liability", "a liability cap")


def test_discovery_empty_candidates_list_is_not_an_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.discover_candidate_spans("Some document.", "liability", "a liability cap")
    assert result == []


# ---------------------------------------------------------------------------
# Verification (stage 2) — every provider failure fails closed
# ---------------------------------------------------------------------------

def test_verify_missing_api_key_is_verification_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = fa.verify_candidate_proposition("some document text", "This agreement caps liability at 1x fees.")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_network_error_is_verification_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_malformed_json_is_verification_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response("not json {{{")
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_empty_response_is_verification_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_invalid_enum_status_is_verification_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"status": "TOTALLY_MADE_UP_STATUS", "evidence_quote": "x"}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_established_without_evidence_quote_is_contradictory(monkeypatch):
    """A verifier claiming ESTABLISHED but citing no evidence is
    contradictory output, not a trustworthy ESTABLISHED verdict."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"status": "ESTABLISHED", "evidence_quote": None, "reasoning": "..."}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_established_with_evidence_quote_succeeds(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({
        "status": "ESTABLISHED", "evidence_quote": "Vendor's liability is capped at 1x fees.",
        "reasoning": "Operative capping language, no conditions found.",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.ESTABLISHED
    assert result.evidence_quote == "Vendor's liability is capped at 1x fees."


def test_verify_not_established_descriptive_language(monkeypatch):
    """The core known-failure-class regression: descriptive/background
    obligation-shaped language must be classified NOT_ESTABLISHED, not
    ESTABLISHED, by the adversarial verifier."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({
        "status": "NOT_ESTABLISHED", "evidence_quote": None,
        "reasoning": "This is a recital describing industry practice, not an operative obligation of this agreement.",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.NOT_ESTABLISHED


@pytest.mark.parametrize("status", ["AMBIGUOUS", "INSUFFICIENT_CONTEXT", "CONFLICTING", "DEPENDENCY_UNRESOLVED"])
def test_verify_every_non_established_status_passes_through(monkeypatch, status):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"status": status, "evidence_quote": None, "reasoning": "..."}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == status


# ---------------------------------------------------------------------------
# Grounding (stage 3)
# ---------------------------------------------------------------------------

def test_grounding_passes_on_exact_substring():
    doc = "The Vendor's liability shall not exceed one times the fees paid."
    result = fa.ground_evidence_quote(doc, "liability shall not exceed one times the fees paid")
    assert result.passed


def test_grounding_fails_on_paraphrase():
    doc = "The Vendor's liability shall not exceed one times the fees paid."
    result = fa.ground_evidence_quote(doc, "liability is capped at 1x fees")
    assert not result.passed


def test_grounding_fails_on_none_quote():
    result = fa.ground_evidence_quote("some document", None)
    assert not result.passed


def test_grounding_fails_on_empty_quote():
    result = fa.ground_evidence_quote("some document", "   ")
    assert not result.passed


# ---------------------------------------------------------------------------
# Admission gate (stage 4) — the asymmetric clean-safety rule
# ---------------------------------------------------------------------------

def _candidate(verification_status, grounding_passed=True, evidence_quote="x"):
    c = fa.CandidateMaterialFact(clause_type="liability", fact_type="cap_provision")
    c.semantic_verification_result = fa.VerificationResult(status=verification_status, evidence_quote=evidence_quote)
    c.deterministic_grounding_result = fa.GroundingResult(passed=grounding_passed, reasons=[] if grounding_passed else ["not found"])
    return c


def test_admission_established_and_grounded_is_admitted():
    c = _candidate(fa.ESTABLISHED, grounding_passed=True)
    result = fa.evaluate_admission(c)
    assert result.admission_status == fa.ADMITTED
    assert result.non_admission_reason is None


@pytest.mark.parametrize("status", [
    fa.NOT_ESTABLISHED, fa.AMBIGUOUS, fa.INSUFFICIENT_CONTEXT,
    fa.CONFLICTING, fa.DEPENDENCY_UNRESOLVED, fa.VERIFICATION_ERROR,
])
def test_admission_never_admits_unsafe_verification_status(status):
    c = _candidate(status, grounding_passed=True)
    result = fa.evaluate_admission(c)
    assert result.admission_status == fa.NOT_ADMITTED
    assert result.non_admission_reason


def test_admission_established_but_grounding_failed_is_not_admitted():
    c = _candidate(fa.ESTABLISHED, grounding_passed=False)
    result = fa.evaluate_admission(c)
    assert result.admission_status == fa.NOT_ADMITTED
    assert "grounding" in result.non_admission_reason


def test_admission_unresolved_dependency_blocks_admission_even_if_established():
    c = _candidate(fa.ESTABLISHED, grounding_passed=True)
    result = fa.evaluate_admission(c, has_unresolved_dependency=True)
    assert result.admission_status == fa.NOT_ADMITTED


def test_admission_unresolved_conflict_blocks_admission_even_if_established():
    c = _candidate(fa.ESTABLISHED, grounding_passed=True)
    result = fa.evaluate_admission(c, has_unresolved_conflict=True)
    assert result.admission_status == fa.NOT_ADMITTED


def test_admission_no_verification_result_is_not_admitted():
    c = fa.CandidateMaterialFact(clause_type="liability", fact_type="cap_provision")
    result = fa.evaluate_admission(c)
    assert result.admission_status == fa.NOT_ADMITTED


def test_admission_defensive_unknown_status_is_not_admitted():
    """Guards evaluate_admission itself against a hypothetical future
    verification status added to the vocabulary without updating this
    function's safety review — must default to NOT_ADMITTED, never admit
    by omission."""
    c = fa.CandidateMaterialFact(clause_type="liability", fact_type="cap_provision")
    vr = fa.VerificationResult.__new__(fa.VerificationResult)
    vr.status = "SOME_FUTURE_STATUS"
    vr.reasoning = ""
    vr.evidence_quote = "x"
    vr.provider_error = None
    c.semantic_verification_result = vr
    c.deterministic_grounding_result = fa.GroundingResult(passed=True)
    result = fa.evaluate_admission(c)
    assert result.admission_status == fa.NOT_ADMITTED


# ---------------------------------------------------------------------------
# End-to-end composition (verify_and_ground)
# ---------------------------------------------------------------------------

def test_verify_and_ground_end_to_end_admitted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "Vendor's total liability under this Agreement shall not exceed the fees paid in the prior 12 months."
    quote = "Vendor's total liability under this Agreement shall not exceed the fees paid in the prior 12 months."
    fake = _fake_response(json.dumps({"status": "ESTABLISHED", "evidence_quote": quote, "reasoning": "Operative cap."}))
    with patch("urllib.request.urlopen", return_value=fake):
        candidate = fa.CandidateMaterialFact(clause_type="liability", fact_type="cap_provision", evidence_span=quote)
        result = fa.verify_and_ground(candidate, doc, "This agreement caps Vendor's liability.")
    assert result.admission_status == fa.ADMITTED


def test_verify_and_ground_end_to_end_fabricated_evidence_not_admitted(monkeypatch):
    """The verifier claims ESTABLISHED and cites a quote that does not
    actually appear in the document — grounding must catch this
    independent of what the verifier claimed."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = "Vendor's total liability under this Agreement shall not exceed the fees paid."
    fake = _fake_response(json.dumps({
        "status": "ESTABLISHED", "evidence_quote": "This sentence was never in the document.",
        "reasoning": "...",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        candidate = fa.CandidateMaterialFact(clause_type="liability", fact_type="cap_provision")
        result = fa.verify_and_ground(candidate, doc, "This agreement caps Vendor's liability.")
    assert result.admission_status == fa.NOT_ADMITTED
    assert "grounding" in result.non_admission_reason


def test_verify_and_ground_provider_failure_never_admits(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    candidate = fa.CandidateMaterialFact(clause_type="liability", fact_type="cap_provision")
    result = fa.verify_and_ground(candidate, "doc text", "proposition text")
    assert result.admission_status == fa.NOT_ADMITTED
    assert result.semantic_verification_result.status == fa.VERIFICATION_ERROR
