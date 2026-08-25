"""Targeted adversarial tests for the general failure classes fixed by
the Candidate 3 final pre-freeze blocker remediation mission (Blockers
1-4; Blocker 5 is a template/route wiring fix covered by direct
document_aggregation/review_workflow testing, not adapter-level
fact-admission behavior).

These tests exercise the SHARED fact_admission.py mechanism plus its
wiring in liability (the fully-verified template adapter), a
representative sample of the 6 other adapters that received the same
fix, and indemnification (the architecturally distinct adapter).  They
are deliberately NOT phrased against the burned corpus's named case IDs
or copied fixture text -- each test targets the general failure SHAPE
(verification-error propagation, materiality-aware suppression) using
freshly-worded documents, per the mission's explicit "general failure
class, not named corpus fixtures" requirement.
"""
import json
from unittest.mock import MagicMock, patch

import fact_admission as fa
import liability_policy_engine as lpe
import data_security_policy_engine as dpe
import insurance_policy_engine as ipe
import indemnification_policy_engine as ie
import policy_engine_core as core


def _fake_response(content_text: str):
    body = json.dumps({
        "choices": [{"message": {"role": "assistant", "content": content_text}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = False
    return cm


# ---------------------------------------------------------------------------
# Part 1 -- fact_admission.py's complete verification-state audit (Blocker 1)
# ---------------------------------------------------------------------------

def test_verification_state_vocabulary_is_fully_enumerated():
    """The module's own _UNSAFE_VERIFICATION_STATES set is the ground
    truth for 'every state besides ESTABLISHED' -- this test fails loudly
    if a new state is ever added to the vocabulary without also updating
    fact_admission._classify_unresolved_dependency_note (the assertion
    inside that function already guards this at runtime; this test
    guards it at collection time too)."""
    assert fa._VERIFICATION_STATES == {
        fa.ESTABLISHED, fa.NOT_ESTABLISHED, fa.AMBIGUOUS, fa.INSUFFICIENT_CONTEXT,
        fa.CONFLICTING, fa.DEPENDENCY_UNRESOLVED, fa.VERIFICATION_ERROR,
    }
    assert fa._UNSAFE_VERIFICATION_STATES == fa._VERIFICATION_STATES - {fa.ESTABLISHED}


def test_every_unsafe_state_produces_a_note_when_evidence_looks_operative():
    """For every one of the 6 unsafe verification states, a NOT_ADMITTED
    candidate whose evidence span contains a named-party obligation
    construction must produce a non-None note from
    first_unresolved_dependency_note -- this is the direct, general fix
    for Blocker 1 (previously NOT_ESTABLISHED/AMBIGUOUS/INSUFFICIENT_
    CONTEXT/CONFLICTING were the only 4 states checked)."""
    for status in fa._UNSAFE_VERIFICATION_STATES:
        candidate = fa.CandidateMaterialFact(
            clause_type="limitation_of_liability", fact_type="clause_presence",
            evidence_span="Vendor will notify Customer of any material breach within a reasonable time.",
            start_offset=0, end_offset=10,
        )
        candidate.semantic_verification_result = fa.VerificationResult(
            status=status, reasoning="test", provider_error="simulated failure" if status == fa.VERIFICATION_ERROR else None,
        )
        candidate.admission_status = fa.NOT_ADMITTED
        note = fa.first_unresolved_dependency_note([candidate])
        assert note is not None, f"status {status} produced no escalation note"


def test_verification_error_note_is_unconditional_within_the_shared_function():
    """VERIFICATION_ERROR must escalate regardless of evidence-span
    wording -- unlike the content-judgment states, there is no
    corroboration signal to check, because verification never examined
    the text at all."""
    candidate = fa.CandidateMaterialFact(
        clause_type="data_security", fact_type="clause_presence",
        evidence_span="Companies generally handle these matters as appropriate.",  # generic, non-operative-looking
        start_offset=0, end_offset=10,
    )
    candidate.semantic_verification_result = fa.VerificationResult(
        status=fa.VERIFICATION_ERROR, reasoning="", provider_error="timeout",
    )
    candidate.admission_status = fa.NOT_ADMITTED
    note = fa.first_unresolved_dependency_note([candidate])
    assert note is not None
    assert "infrastructure failure" in note


# ---------------------------------------------------------------------------
# Part 2 -- Adversarial pattern A/B: verification error + deterministic
# miss/hit, across a representative sample of adapters (Blocker 1 wiring)
# ---------------------------------------------------------------------------

def setup_function(_):
    lpe.LIABILITY_SEMANTIC_DISCOVERY_ENABLED = True
    dpe.DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = True
    ipe.INSURANCE_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_function(_):
    lpe.LIABILITY_SEMANTIC_DISCOVERY_ENABLED = False
    dpe.DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = False
    ipe.INSURANCE_SEMANTIC_DISCOVERY_ENABLED = False


def _discover_then_error(quote: str):
    """Mocks discovery succeeding (one candidate proposed) then the
    per-candidate verify call failing with a malformed response --
    VERIFICATION_ERROR, not a discovery-call error."""
    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response("this is not valid JSON at all")

    return fake_urlopen


def test_A_verification_error_with_deterministic_miss_liability(monkeypatch):
    """Pattern A: deterministic regex MISS + AI candidate materially
    relevant + verification ERROR. Expected: NOT ACCEPT, NOT
    NOT_APPLICABLE."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "Vendor will make Customer whole for direct losses arising from Vendor's own errors."
    quote = doc
    with patch("urllib.request.urlopen", side_effect=_discover_then_error(quote)):
        facts = lpe.extract_liability_facts(doc)
    assert facts is not None
    assert facts.absence_state != "CONFIRMED_ABSENT" or facts.provisions
    decision = lpe.evaluate_liability_policy(facts, _FakeLiabilityPolicy())
    assert decision.state not in (core.ACCEPT, core.ACCEPT_WITH_NOTE, core.NOT_APPLICABLE)


def test_A_verification_error_with_deterministic_miss_data_security(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "Should Vendor discover unauthorized access to personal data, Vendor will tell Customer promptly."
    with patch("urllib.request.urlopen", side_effect=_discover_then_error(doc)):
        facts = dpe.extract_data_security_facts(doc)
    assert facts is not None
    decision = dpe.evaluate_data_security_policy(facts, _FakeDataSecurityPolicy())
    assert decision.state not in (core.ACCEPT, core.NOT_APPLICABLE)


def test_B_verification_error_with_deterministic_hit_and_full_establishment_stays_clean(monkeypatch):
    """Pattern B: deterministic regex HIT (a real, fully-established cap
    AND category treatment), AI reconciliation candidate's verification
    ERRORs. The error concerns the SAME already-fully-resolved
    proposition, so it may be safely suppressed -- this is the positive
    control proving Blocker 2's materiality gate doesn't just escalate
    everything (which would defeat the point of an additive AI channel)."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        "15. Cap on Liability. Vendor's aggregate liability shall not exceed one times the fees paid "
        "in the prior twelve months, except that this cap shall not apply to claims arising from "
        "Vendor's gross negligence or willful misconduct."
    )
    quote = "Vendor's aggregate liability shall not exceed one times the fees paid in the prior twelve months"
    with patch("urllib.request.urlopen", side_effect=_discover_then_error(quote)):
        facts = lpe.extract_liability_facts(doc)
    assert facts is not None
    assert facts.ai_identified_unresolved_dependency is None, (
        "a redundant, uncertain AI signal about an already fully-established provision must not surface"
    )
    decision = lpe.evaluate_liability_policy(facts, _FakeLiabilityPolicy())
    assert decision.state in (core.ACCEPT, core.ACCEPT_WITH_NOTE)


# ---------------------------------------------------------------------------
# Part 3 -- Pattern C/D: material vs. irrelevant AI uncertainty (Blocker 2)
# ---------------------------------------------------------------------------

def test_C_material_unresolved_definition_dependency_not_suppressed_by_unrelated_established_cap(monkeypatch):
    """This is the exact defect found and fixed mid-mission: liability's
    original materiality gate suppressed ALL of
    first_unresolved_dependency_note's output uniformly, including a
    definition-dependency note that has NOTHING to do with the
    established cap. A defined term the deterministic detectors cannot
    read is always material regardless of what else was found."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    # Deliberately never defines "Catastrophic Failure" anywhere in the
    # document -- resolve_definition must fail to RESOLVE it, so the
    # candidate is correctly NOT_ADMITTED via the definition-dependency
    # mechanism (not the generic uncertain-verification catch-all).
    doc = (
        "15. Cap on Liability. Vendor's aggregate liability shall not exceed one times the fees paid in "
        "the prior twelve months, except that this cap shall not apply to a Catastrophic Failure."
    )
    call_count = {"n": 0}

    def fake_urlopen(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _fake_response(json.dumps({"candidates": [
                {"quote": "this cap shall not apply to a Catastrophic Failure"}
            ]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED",
            "evidence_quote": "this cap shall not apply to a Catastrophic Failure",
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "definition_term": "Catastrophic Failure",
            "reasoning": "The exception depends on a defined term this module's deterministic detectors cannot read.",
        }))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        facts = lpe.extract_liability_facts(doc)
    assert facts is not None
    # The cap and gross-negligence-style carve-out machinery isn't what's
    # being tested here -- what matters is that the definition dependency
    # is NEVER discarded merely because a cap value parses cleanly.
    decision = lpe.evaluate_liability_policy(facts, _FakeLiabilityPolicy())
    assert decision.state == core.REQUIRES_REVIEW, (
        "an unresolved, material definition dependency must force review even when the general "
        "cap itself was independently, deterministically established"
    )


def test_D_irrelevant_uncertain_signal_suppressed_when_fact_fully_established(monkeypatch):
    """Positive control mirroring test_B above: confirms the suppression
    machinery still functions for its intended purpose (not merely
    disabled outright by the Blocker 2 fix)."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        "15. Cap on Liability. Vendor's aggregate liability shall not exceed two times the fees paid "
        "in the prior twelve months, except that this cap shall not apply to claims arising from fraud."
    )
    quote = "Vendor's aggregate liability shall not exceed two times the fees paid in the prior twelve months"
    with patch("urllib.request.urlopen", side_effect=_discover_then_error(quote)):
        facts = lpe.extract_liability_facts(doc)
    assert facts is not None
    assert facts.ai_identified_unresolved_dependency is None


def test_nothing_established_at_all_still_escalates_generic_note(monkeypatch):
    """Negative-control complement: when NOTHING is deterministically
    established, the generic uncertain-verification note must surface
    (proves the gate isn't accidentally inverted or always-suppressing)."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = "15. Liability. This Section addresses liability matters generally, and Vendor will bear responsibility as described."
    quote = "This Section addresses liability matters generally, and Vendor will bear responsibility as described."
    with patch("urllib.request.urlopen", side_effect=_discover_then_error(quote)):
        facts = lpe.extract_liability_facts(doc)
    assert facts is not None
    # No deterministic anchor matched at all here, so this candidate's
    # note is preserved via the DEPENDENCY_UNRESOLVED absence-state path
    # rather than the anchor-exists gate -- either way, the decision must
    # never be silently clean.
    decision = lpe.evaluate_liability_policy(facts, _FakeLiabilityPolicy())
    assert decision.state == core.REQUIRES_REVIEW


class _FakeLiabilityPolicy:
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


class _FakeDataSecurityPolicy:
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


# ---------------------------------------------------------------------------
# Part 4 -- Indemnification reconciliation (Blocker 3): the general
# failure class, mirrored against the limitation_of_liability-006 shape
# with freshly-worded indemnification text.
# ---------------------------------------------------------------------------

def setup_module(_):
    ie.INDEMNIFICATION_RECONCILIATION_ENABLED = True


def teardown_module(_):
    ie.INDEMNIFICATION_RECONCILIATION_ENABLED = False


class _FakeIndemnPolicy:
    contract_side = "sell_side"
    escalation_approval_authority = "Legal Director"
    fallback_text = "Approved fallback indemnification language."
    required_protection_triggers_json = None
    prohibited_exposure_triggers_json = None
    require_exposure_third_party_only = False
    require_defense_control_for_exposure = False
    require_notice_and_cooperation_for_exposure = False
    prohibit_uncapped_exposure = True
    exposure_preferred_multiplier = 1.0
    exposure_acceptable_max_multiplier = 2.0
    exposure_negotiate_max_multiplier = 3.0


def test_indemnification_analogue_of_liability_006_stays_clean(monkeypatch):
    """The indemnification equivalent of limitation_of_liability-006:
    monetary AND scope are both genuinely, deterministically established
    for this obligation; a reconciliation-channel verification ERROR on
    the SAME window must not flip it to REQUIRES_REVIEW."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
        "against any third-party claims arising from Vendor's breach. Vendor's indemnification "
        "obligations shall not exceed 2 times the total annual fees paid."
    )
    with patch("urllib.request.urlopen", return_value=_fake_response("not valid json at all")):
        facts = ie.extract_indemnification_facts(doc)
        decision = ie.evaluate_indemnification_policy(facts, _FakeIndemnPolicy(), source="Test")
    assert facts is not None
    assert all(ob.ai_identified_unreconciled_context is None for ob in facts.obligations)
    assert decision.state != core.REQUIRES_REVIEW


def test_indemnification_material_gap_plus_provider_error_forces_review(monkeypatch):
    """The general failure class this mission exists to fix: an
    obligation whose monetary/scope are NOT deterministically established
    (a genuine gap, unlike the test above), reconciled against a
    verification-channel provider error -- must not silently stay
    clean."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
    doc = (
        "12. Indemnification. Vendor shall indemnify Customer from and against claims as described "
        "in this section."
    )
    with patch("urllib.request.urlopen", return_value=_fake_response("not valid json at all")):
        facts = ie.extract_indemnification_facts(doc)
        decision = ie.evaluate_indemnification_policy(facts, _FakeIndemnPolicy(), source="Test")
    assert facts is not None
    if facts.obligations:
        matched = [ob for ob in facts.obligations if ob.ai_identified_unreconciled_context is not None]
        assert matched, "a provider error on a materially-incomplete obligation must not be silently dropped"
    assert decision.state != core.ACCEPT
    assert decision.state != core.NOT_APPLICABLE
