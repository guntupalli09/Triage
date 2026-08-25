"""Tests for the shared fact-admission / semantic-verification framework
(fact_admission.py). Mirrors the mocking pattern already used in
tests/test_step4a9_2_real_provider_adversarial.py for the indemnification
adapter's real-provider integration. No live API calls — every test here
is mocked or purely deterministic, so it runs without OPENAI_API_KEY.

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
        "choices": [{"message": {"role": "assistant", "content": content_text}}],
        "usage": {"prompt_tokens": input_tokens, "completion_tokens": output_tokens},
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
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(fa.ProviderUnavailable):
        fa.discover_candidate_spans("some document text", "liability", "a limitation of liability provision")


def test_discovery_hallucinated_quote_discarded(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": [{"quote": "this text is not in the document"}]}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.discover_candidate_spans("The Vendor performs services.", "liability", "a liability cap")
    assert result == []


def test_discovery_verbatim_quote_grounds_offsets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
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
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response("this is not json at all {{{")
    with patch("urllib.request.urlopen", return_value=fake):
        with pytest.raises(fa.ProviderUnavailable):
            fa.discover_candidate_spans("Some document.", "liability", "a liability cap")


def test_discovery_network_error_raises(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        with pytest.raises(fa.ProviderUnavailable):
            fa.discover_candidate_spans("Some document.", "liability", "a liability cap")


def test_discovery_empty_candidates_list_is_not_an_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"candidates": []}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.discover_candidate_spans("Some document.", "liability", "a liability cap")
    assert result == []


# ---------------------------------------------------------------------------
# Verification (stage 2) — every provider failure fails closed
# ---------------------------------------------------------------------------

def test_verify_missing_api_key_is_verification_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = fa.verify_candidate_proposition("some document text", "This agreement caps liability at 1x fees.")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_network_error_is_verification_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_malformed_json_is_verification_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response("not json {{{")
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_empty_response_is_verification_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_invalid_enum_status_is_verification_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"status": "TOTALLY_MADE_UP_STATUS", "evidence_quote": "x"}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_established_without_evidence_quote_is_contradictory(monkeypatch):
    """A verifier claiming ESTABLISHED but citing no evidence is
    contradictory output, not a trustworthy ESTABLISHED verdict."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({"status": "ESTABLISHED", "evidence_quote": None, "reasoning": "..."}))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.VERIFICATION_ERROR


def test_verify_established_with_evidence_quote_succeeds(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
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
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({
        "status": "NOT_ESTABLISHED", "evidence_quote": None,
        "reasoning": "This is a recital describing industry practice, not an operative obligation of this agreement.",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.NOT_ESTABLISHED


@pytest.mark.parametrize("status", ["AMBIGUOUS", "INSUFFICIENT_CONTEXT", "CONFLICTING", "DEPENDENCY_UNRESOLVED"])
def test_verify_every_non_established_status_passes_through(monkeypatch, status):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
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
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
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
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
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
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    candidate = fa.CandidateMaterialFact(clause_type="liability", fact_type="cap_provision")
    result = fa.verify_and_ground(candidate, "doc text", "proposition text")
    assert result.admission_status == fa.NOT_ADMITTED
    assert result.semantic_verification_result.status == fa.VERIFICATION_ERROR


# ---------------------------------------------------------------------------
# Qualifier grounding (final trust architecture, Phase 1-4): a material
# condition/exception/cross-reference the verifier claims to have found
# must be preserved onto the admitted fact, or block admission outright if
# it cannot be grounded -- never silently dropped so a simplified fact can
# still reach a clean ESTABLISHED.
# ---------------------------------------------------------------------------

def test_verification_result_carries_qualifier_fields_by_default_none():
    vr = fa.VerificationResult(status=fa.ESTABLISHED, evidence_quote="x")
    assert vr.condition_quote is None
    assert vr.exception_quote is None
    assert vr.cross_reference_text is None


def test_verify_candidate_proposition_parses_qualifier_quotes(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    fake = _fake_response(json.dumps({
        "status": "ESTABLISHED", "evidence_quote": "Vendor shall indemnify Customer.",
        "condition_quote": "provided Customer gives prompt written notice",
        "exception_quote": "except to the extent caused by Customer's negligence",
        "cross_reference_text": None,
        "reasoning": "Operative, conditioned, with an exception.",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_candidate_proposition("doc text", "proposition text")
    assert result.status == fa.ESTABLISHED
    assert result.condition_quote == "provided Customer gives prompt written notice"
    assert result.exception_quote == "except to the extent caused by Customer's negligence"
    assert result.cross_reference_text is None


def test_ground_qualifiers_grounds_each_present_field():
    doc = "Vendor shall indemnify Customer, provided Customer gives prompt written notice, except for Customer's own negligence."
    vr = fa.VerificationResult(
        status=fa.ESTABLISHED, evidence_quote="Vendor shall indemnify Customer",
        condition_quote="provided Customer gives prompt written notice",
        exception_quote="except for Customer's own negligence",
    )
    results = fa.ground_qualifiers(doc, vr)
    assert set(results.keys()) == {"condition_quote", "exception_quote"}
    assert results["condition_quote"].passed
    assert results["exception_quote"].passed


def test_ground_qualifiers_fails_on_fabricated_condition():
    doc = "Vendor shall indemnify Customer for third-party IP claims."
    vr = fa.VerificationResult(
        status=fa.ESTABLISHED, evidence_quote="Vendor shall indemnify Customer",
        condition_quote="this exact condition text is not in the document",
    )
    results = fa.ground_qualifiers(doc, vr)
    assert not results["condition_quote"].passed


def test_admission_blocked_when_claimed_condition_fails_grounding():
    """The hard gate: a material condition the verifier claims to have
    found, but which cannot be grounded, must block admission outright --
    never silently dropped so the base obligation still reaches ADMITTED."""
    candidate = fa.CandidateMaterialFact(clause_type="indemnification", fact_type="obligation")
    candidate.semantic_verification_result = fa.VerificationResult(
        status=fa.ESTABLISHED, evidence_quote="grounded evidence",
        condition_quote="a condition that will fail to ground",
    )
    candidate.deterministic_grounding_result = fa.GroundingResult(passed=True)
    qualifier_grounding = {"condition_quote": fa.GroundingResult(passed=False, reasons=["not found"])}
    result = fa.evaluate_admission(candidate, qualifier_grounding=qualifier_grounding)
    assert result.admission_status == fa.NOT_ADMITTED
    assert "condition_quote" in result.non_admission_reason
    # Never dropped: the base fact must not be ADMITTED merely because
    # the ungrounded qualifier was excluded.
    assert candidate.condition is None


def test_admission_preserves_grounded_condition_and_exception_onto_candidate():
    candidate = fa.CandidateMaterialFact(clause_type="indemnification", fact_type="obligation")
    candidate.semantic_verification_result = fa.VerificationResult(
        status=fa.ESTABLISHED, evidence_quote="grounded evidence",
        condition_quote="prompt written notice", exception_quote="Customer's own negligence",
    )
    candidate.deterministic_grounding_result = fa.GroundingResult(passed=True)
    qualifier_grounding = {
        "condition_quote": fa.GroundingResult(passed=True),
        "exception_quote": fa.GroundingResult(passed=True),
    }
    result = fa.evaluate_admission(candidate, qualifier_grounding=qualifier_grounding)
    assert result.admission_status == fa.ADMITTED
    assert result.condition == "prompt written notice"
    assert result.exception == "Customer's own negligence"


def test_admission_with_no_qualifiers_claimed_is_unaffected():
    """A candidate where the verifier found no qualifiers at all (the
    common case) is unaffected by the new gate -- backward compatible."""
    candidate = fa.CandidateMaterialFact(clause_type="liability", fact_type="cap_provision")
    candidate.semantic_verification_result = fa.VerificationResult(status=fa.ESTABLISHED, evidence_quote="x")
    candidate.deterministic_grounding_result = fa.GroundingResult(passed=True)
    result = fa.evaluate_admission(candidate)
    assert result.admission_status == fa.ADMITTED
    assert result.condition is None
    assert result.exception is None
    assert result.cross_reference is None


def test_verify_and_ground_end_to_end_preserves_grounded_condition(monkeypatch):
    """Full pipeline: the mission's own worked example (indemnification
    with a notice condition and a negligence exception) -- both survive
    from AI verification through grounding to the admitted fact."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        "Vendor shall indemnify Customer against third-party intellectual-property claims, "
        "provided Customer gives prompt written notice, except to the extent caused by "
        "Customer's negligence."
    )
    fake = _fake_response(json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": "Vendor shall indemnify Customer against third-party intellectual-property claims",
        "condition_quote": "provided Customer gives prompt written notice",
        "exception_quote": "except to the extent caused by Customer's negligence",
        "cross_reference_text": None,
        "reasoning": "Operative indemnification, conditioned on notice, subject to a negligence exception.",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        candidate = fa.CandidateMaterialFact(clause_type="indemnification", fact_type="obligation")
        result = fa.verify_and_ground(
            candidate, doc,
            "Vendor is obligated to indemnify Customer against third-party IP claims.",
        )
    assert result.admission_status == fa.ADMITTED
    assert result.condition == "provided Customer gives prompt written notice"
    assert result.exception == "except to the extent caused by Customer's negligence"
    assert result.cross_reference is None


def test_verify_and_ground_end_to_end_blocks_on_fabricated_exception(monkeypatch):
    """If the verifier hallucinates an exception that isn't actually in
    the document, the whole candidate is blocked, not just the exception
    field -- proving the hard gate operates through the full pipeline,
    not only the unit-level evaluate_admission call."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "Vendor shall indemnify Customer against third-party intellectual-property claims."
    fake = _fake_response(json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": "Vendor shall indemnify Customer against third-party intellectual-property claims",
        "condition_quote": None,
        "exception_quote": "except to the extent caused by Customer's own gross negligence or willful misconduct",
        "cross_reference_text": None,
        "reasoning": "...",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        candidate = fa.CandidateMaterialFact(clause_type="indemnification", fact_type="obligation")
        result = fa.verify_and_ground(candidate, doc, "Vendor is obligated to indemnify Customer.")
    assert result.admission_status == fa.NOT_ADMITTED
    assert candidate.exception is None


# ---------------------------------------------------------------------------
# Final trust architecture: definition resolution, cross-reference target
# resolution, competing-reading data preservation, and the zero-silent-loss
# invariant that ties them together.
# ---------------------------------------------------------------------------

def test_resolve_definition_found_single_clause():
    doc = (
        '1. Definitions. "Confidential Information" means any non-public information '
        "disclosed by either party. 2. Obligations. Recipient shall protect Confidential Information."
    )
    result = fa.resolve_definition(doc, "Confidential Information")
    assert result.status == "RESOLVED"
    assert result.term == "Confidential Information"
    assert result.definition_evidence.startswith('"Confidential Information" means')
    assert doc[result.definition_start:result.definition_end].strip() == result.definition_evidence


def test_resolve_definition_not_found():
    doc = "Recipient shall protect Confidential Information disclosed by Discloser."
    result = fa.resolve_definition(doc, "Confidential Information")
    assert result.status == "NOT_FOUND"
    assert result.definition_evidence is None


def test_resolve_definition_conflicting_when_two_differing_clauses_exist():
    doc = (
        '"Losses" means direct damages only. Elsewhere: "Losses" means direct and indirect damages.'
    )
    result = fa.resolve_definition(doc, "Losses")
    assert result.status == "CONFLICTING"


def test_resolve_definition_no_term_provided():
    result = fa.resolve_definition("some document text", None)
    assert result.status == "NOT_FOUND"


def test_resolve_cross_reference_target_section_resolved():
    doc = (
        "1. Liability. Vendor's liability is capped as set forth in Section 9.3.\n\n"
        "Section 9.3 Liability Cap. Vendor's total liability shall not exceed the fees "
        "paid in the preceding twelve months.\n\n"
        "Section 10 Miscellaneous. This is the next section."
    )
    result = fa.resolve_cross_reference_target(doc, "as set forth in Section 9.3")
    assert result.status == "RESOLVED"
    assert result.label.endswith("9.3")
    assert "Liability Cap" in result.target_evidence
    assert "Section 10" not in result.target_evidence


def test_resolve_cross_reference_target_section_not_found():
    doc = "1. Liability. Vendor's liability is capped as set forth in Section 9.3."
    result = fa.resolve_cross_reference_target(doc, "as set forth in Section 9.3")
    assert result.status == "NOT_FOUND"


def test_resolve_cross_reference_target_missing_attachment():
    doc = "Deliverables are described in Schedule A attached hereto."
    result = fa.resolve_cross_reference_target(doc, "Schedule A")
    assert result.status == "MISSING_ATTACHMENT"


def test_resolve_cross_reference_target_conflicting_multiple_headings():
    doc = (
        "Section 9.3 First Heading. Text one.\n\n"
        "Section 9.3 Duplicate Heading. Text two."
    )
    result = fa.resolve_cross_reference_target(doc, "Section 9.3")
    assert result.status == "CONFLICTING"


def test_resolve_cross_reference_target_unrecognized_label():
    result = fa.resolve_cross_reference_target("some document", "the other agreement")
    assert result.status == "NOT_FOUND"


def test_ground_competing_readings_preserves_both_grounded_readings():
    doc = "The Fee is due on delivery. Alternatively, the Fee is due on acceptance."
    verification = fa.VerificationResult(
        status=fa.AMBIGUOUS,
        competing_reading_a={"proposition": "Fee due on delivery.", "evidence_quote": "The Fee is due on delivery."},
        competing_reading_b={"proposition": "Fee due on acceptance.", "evidence_quote": "the Fee is due on acceptance."},
    )
    readings = fa.ground_competing_readings(doc, verification)
    assert len(readings) == 2
    assert all(r.grounded for r in readings)
    assert {r.reading_id for r in readings} == {"A", "B"}


def test_ground_competing_readings_marks_ungrounded_reading_but_keeps_it_as_data():
    doc = "The Fee is due on delivery."
    verification = fa.VerificationResult(
        status=fa.AMBIGUOUS,
        competing_reading_a={"proposition": "Fee due on delivery.", "evidence_quote": "The Fee is due on delivery."},
        competing_reading_b={"proposition": "Fee due on acceptance.", "evidence_quote": "text not in the document"},
    )
    readings = fa.ground_competing_readings(doc, verification)
    assert len(readings) == 2
    grounded = {r.reading_id: r.grounded for r in readings}
    assert grounded["A"] is True
    assert grounded["B"] is False


def test_evaluate_admission_blocks_on_unresolved_definition_dependency():
    candidate = fa.CandidateMaterialFact(clause_type="confidentiality", fact_type="obligation")
    candidate.semantic_verification_result = fa.VerificationResult(status=fa.ESTABLISHED, evidence_quote="x")
    candidate.deterministic_grounding_result = fa.GroundingResult(passed=True)
    candidate.definition_resolution = fa.DefinitionResolution(status="NOT_FOUND", term="Confidential Information")
    result = fa.evaluate_admission(candidate)
    assert result.admission_status == fa.NOT_ADMITTED
    assert "Confidential Information" in result.non_admission_reason


def test_evaluate_admission_blocks_on_unresolved_cross_reference():
    candidate = fa.CandidateMaterialFact(clause_type="liability", fact_type="cap_provision")
    candidate.semantic_verification_result = fa.VerificationResult(status=fa.ESTABLISHED, evidence_quote="x")
    candidate.deterministic_grounding_result = fa.GroundingResult(passed=True)
    candidate.cross_reference_resolution = fa.CrossReferenceResolution(status="MISSING_ATTACHMENT", label="Schedule A")
    result = fa.evaluate_admission(candidate)
    assert result.admission_status == fa.NOT_ADMITTED
    assert "Schedule A" in result.non_admission_reason


def test_evaluate_admission_admits_when_definition_and_cross_reference_both_resolve():
    candidate = fa.CandidateMaterialFact(clause_type="confidentiality", fact_type="obligation")
    candidate.semantic_verification_result = fa.VerificationResult(status=fa.ESTABLISHED, evidence_quote="x")
    candidate.deterministic_grounding_result = fa.GroundingResult(passed=True)
    candidate.definition_resolution = fa.DefinitionResolution(
        status="RESOLVED", term="Confidential Information", definition_evidence='"Confidential Information" means X.',
    )
    candidate.cross_reference_resolution = fa.CrossReferenceResolution(
        status="RESOLVED", label="Section 9.3", target_evidence="Section 9.3 Liability Cap. ...",
    )
    result = fa.evaluate_admission(candidate)
    assert result.admission_status == fa.ADMITTED
    assert result.definition_resolution.status == "RESOLVED"
    assert result.cross_reference_resolution.status == "RESOLVED"


def test_evaluate_admission_blocks_on_two_grounded_competing_readings():
    """Defense-in-depth for Step C: even if verification.status were
    ESTABLISHED, two independently-grounded competing readings must never
    be resolved by silently picking one."""
    candidate = fa.CandidateMaterialFact(clause_type="payment_terms", fact_type="due_date")
    candidate.semantic_verification_result = fa.VerificationResult(status=fa.ESTABLISHED, evidence_quote="x")
    candidate.deterministic_grounding_result = fa.GroundingResult(passed=True)
    candidate.competing_readings = [
        fa.CompetingReading(reading_id="A", proposition="Reading A", evidence_quote="x", grounded=True),
        fa.CompetingReading(reading_id="B", proposition="Reading B", evidence_quote="y", grounded=True),
    ]
    result = fa.evaluate_admission(candidate)
    assert result.admission_status == fa.NOT_ADMITTED
    assert "competing readings" in result.non_admission_reason


def test_evaluate_admission_admits_when_only_one_reading_grounded():
    """A single grounded reading (the other having failed grounding, or
    never having been proposed) is not a 'competing readings' situation --
    it's just one verified proposition, and must not be blocked by this
    gate."""
    candidate = fa.CandidateMaterialFact(clause_type="payment_terms", fact_type="due_date")
    candidate.semantic_verification_result = fa.VerificationResult(status=fa.ESTABLISHED, evidence_quote="x")
    candidate.deterministic_grounding_result = fa.GroundingResult(passed=True)
    candidate.competing_readings = [
        fa.CompetingReading(reading_id="A", proposition="Reading A", evidence_quote="x", grounded=True),
        fa.CompetingReading(reading_id="B", proposition="Reading B", evidence_quote="not in doc", grounded=False),
    ]
    result = fa.evaluate_admission(candidate)
    assert result.admission_status == fa.ADMITTED


def test_verify_and_ground_end_to_end_resolves_definition_dependency(monkeypatch):
    """Full pipeline proof for Step A: AI notices the dependency (via
    definition_term) -> deterministic resolve_definition locates the
    actual clause -> the resolution (not the AI's claim) lands on the
    admitted fact."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        '1. Definitions. "Confidential Information" means any non-public technical or '
        "business information disclosed by either party. "
        "2. Obligations. Recipient shall not disclose Confidential Information to any third party."
    )
    fake = _fake_response(json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": "Recipient shall not disclose Confidential Information to any third party",
        "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
        "definition_term": "Confidential Information",
        "reasoning": "Operative non-disclosure obligation, scoped by the defined term.",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        candidate = fa.CandidateMaterialFact(clause_type="confidentiality", fact_type="obligation")
        result = fa.verify_and_ground(
            candidate, doc,
            "Recipient is obligated not to disclose Confidential Information.",
        )
    assert result.admission_status == fa.ADMITTED
    assert result.definition_resolution is not None
    assert result.definition_resolution.status == "RESOLVED"
    assert result.definition_resolution.definition_evidence.startswith('"Confidential Information" means')


def test_verify_and_ground_end_to_end_blocks_on_unresolvable_definition(monkeypatch):
    """The AI claims a proposition depends on a defined term that this
    document never actually defines -- must block admission rather than
    silently evaluate the obligation as though the dependency didn't
    exist."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "Recipient shall not disclose Confidential Information to any third party."
    fake = _fake_response(json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": "Recipient shall not disclose Confidential Information to any third party",
        "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
        "definition_term": "Confidential Information",
        "reasoning": "...",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        candidate = fa.CandidateMaterialFact(clause_type="confidentiality", fact_type="obligation")
        result = fa.verify_and_ground(
            candidate, doc,
            "Recipient is obligated not to disclose Confidential Information.",
        )
    assert result.admission_status == fa.NOT_ADMITTED
    assert result.definition_resolution.status == "NOT_FOUND"


def test_verify_and_ground_end_to_end_resolves_cross_reference_target(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        "1. Liability. Vendor's total liability is limited as set forth in Section 9.3.\n\n"
        "Section 9.3 Liability Cap. Vendor's total liability shall not exceed fees paid in "
        "the preceding twelve months."
    )
    fake = _fake_response(json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": "Vendor's total liability is limited as set forth in Section 9.3",
        "condition_quote": None, "exception_quote": None,
        "cross_reference_text": "as set forth in Section 9.3",
        "reasoning": "Operative liability limitation, capped per the referenced section.",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        candidate = fa.CandidateMaterialFact(clause_type="liability", fact_type="cap_provision")
        result = fa.verify_and_ground(
            candidate, doc,
            "Vendor's liability is limited per a cross-referenced section.",
        )
    assert result.admission_status == fa.ADMITTED
    assert result.cross_reference_resolution.status == "RESOLVED"
    assert "Liability Cap" in result.cross_reference_resolution.target_evidence


def test_verify_and_ground_end_to_end_blocks_on_missing_attachment(monkeypatch):
    """Cross-reference points to a schedule/exhibit that was never
    actually attached -- must route to review with the explicit
    MISSING_ATTACHMENT state, never silently drop the reference and
    evaluate only the local sentence."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "Deliverables shall conform to the specifications in Schedule A."
    fake = _fake_response(json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": "Deliverables shall conform to the specifications in Schedule A",
        "condition_quote": None, "exception_quote": None,
        "cross_reference_text": "the specifications in Schedule A",
        "reasoning": "Operative conformance obligation, scoped by attached schedule.",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        candidate = fa.CandidateMaterialFact(clause_type="ip_ownership", fact_type="deliverable_spec")
        result = fa.verify_and_ground(
            candidate, doc,
            "Deliverables must conform to a referenced schedule.",
        )
    assert result.admission_status == fa.NOT_ADMITTED
    assert result.cross_reference_resolution.status == "MISSING_ATTACHMENT"


def test_verify_and_ground_end_to_end_preserves_competing_readings_as_data(monkeypatch):
    """Step C end-to-end: verifier reports AMBIGUOUS with two competing
    readings -- admission is blocked (existing safety property) AND both
    readings are preserved as grounded data on the candidate, not
    discarded (the previously-missing half of Step 6)."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "The Fee is due on delivery. In some readings, the Fee is due on final acceptance."
    fake = _fake_response(json.dumps({
        "status": "AMBIGUOUS",
        "evidence_quote": None, "condition_quote": None, "exception_quote": None,
        "cross_reference_text": None, "definition_term": None,
        "competing_reading_a": {"proposition": "Fee due on delivery.", "evidence_quote": "The Fee is due on delivery."},
        "competing_reading_b": {"proposition": "Fee due on final acceptance.", "evidence_quote": "the Fee is due on final acceptance."},
        "reasoning": "Two materially different readings of when the Fee is due.",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        candidate = fa.CandidateMaterialFact(clause_type="payment_terms", fact_type="due_date")
        result = fa.verify_and_ground(candidate, doc, "The Fee's due date is established.")
    assert result.admission_status == fa.NOT_ADMITTED
    assert len(result.competing_readings) == 2
    assert all(r.grounded for r in result.competing_readings)


def test_zero_silent_loss_invariant_definition_dependency_never_disappears(monkeypatch):
    """Direct test of the zero-silent-loss invariant (Step H) for the
    definition dimension: exactly one of (survives to admitted fact) or
    (admission blocked) happens -- there is no third state where the
    definition dependency vanishes and the base proposition is still
    ADMITTED."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "Recipient shall not disclose Confidential Information to any third party."
    fake = _fake_response(json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": "Recipient shall not disclose Confidential Information to any third party",
        "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
        "definition_term": "Confidential Information",
        "reasoning": "...",
    }))
    with patch("urllib.request.urlopen", return_value=fake):
        candidate = fa.CandidateMaterialFact(clause_type="confidentiality", fact_type="obligation")
        result = fa.verify_and_ground(
            candidate, doc, "Recipient is obligated not to disclose Confidential Information.",
        )
    survived = result.admission_status == fa.ADMITTED and result.definition_resolution is not None and result.definition_resolution.status == "RESOLVED"
    blocked = result.admission_status == fa.NOT_ADMITTED
    assert survived or blocked
    assert not (result.admission_status == fa.ADMITTED and result.definition_resolution is None)
