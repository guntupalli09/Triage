"""Tests for indemnification_policy_engine.py's SECOND, additive safety
channel (gap-closure pass): AI contextual analysis run over each
already-structured obligation's own window, reconciled against what this
module's own deterministic condition/exception detectors already found.

INDEMNIFICATION_RECONCILIATION_ENABLED defaults to False in production
(same rollout discipline as every other adapter's *_SEMANTIC_DISCOVERY_
ENABLED flag) -- every test here flips it on for its own duration only,
so tests/test_indemnification_policy_engine.py's default-off regression
suite is completely unaffected.

This module's OWN deterministic discovery/verification (HYBRID_DISCOVERY_
ENABLED / SEMANTIC_PROVIDER, _verify_role_capture, the structural
risk-transfer patterns) is left entirely untouched by these tests --
they exercise only the new reconciliation channel layered on top.
"""
import json
from unittest.mock import MagicMock, patch

import indemnification_policy_engine as ie
import policy_engine_core as core
from policy_engine_core import detect_condition_in_span as _core_detect_condition_in_span


class FakePolicy:
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


def setup_function(_):
    ie.INDEMNIFICATION_RECONCILIATION_ENABLED = True


def teardown_function(_):
    ie.INDEMNIFICATION_RECONCILIATION_ENABLED = False


def _fake_response(content_text: str):
    body = json.dumps({
        "content": [{"type": "text", "text": content_text}],
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = False
    return cm


_BASE_CLAUSE = (
    "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
    "against any third-party claims arising from Vendor's gross negligence. Vendor's indemnification "
    "obligations shall not exceed 1 times the total annual fees paid."
)

_UNUSUAL_CONDITION = (
    "in the event Vendor's cyber-insurance policy lapses during the term, this indemnification "
    "obligation shall not apply"
)


def test_premise_deterministic_detector_misses_the_unusual_condition():
    """Part 2's required premise check: confirm BEFORE testing the
    reconciliation channel that the existing deterministic condition
    detector genuinely does not recognize this phrasing -- otherwise the
    test downstream wouldn't be exercising the gap this pass closes."""
    doc = f"{_BASE_CLAUSE} {_UNUSUAL_CONDITION}."
    idx = doc.index("Vendor shall indemnify")
    end = doc.index("annual fees paid.") + len("annual fees paid.")
    condition = _core_detect_condition_in_span(doc, idx, end)
    assert condition.status == "UNCONDITIONAL", (
        "premise violated: the deterministic detector already recognizes this phrasing -- "
        "the forbidden-outcome test below needs different wording to exercise a genuine gap"
    )


def test_disabled_by_default_is_byte_identical(monkeypatch):
    """With the flag off (the default), behavior is unchanged: no
    reconciliation call, existing deterministic decision stands."""
    ie.INDEMNIFICATION_RECONCILIATION_ENABLED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    doc = f"{_BASE_CLAUSE} {_UNUSUAL_CONDITION}."
    facts = ie.extract_indemnification_facts(doc)
    decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")
    assert decision.state == core.ACCEPT
    assert all(ob.ai_identified_unreconciled_context is None for ob in facts.obligations)


def test_forbidden_outcome_ai_finds_modifier_deterministic_extraction_lacks_it(monkeypatch):
    """THE mission-critical case for this pass: a material condition
    phrased outside the deterministic vocabulary (confirmed missed by
    the premise test above) must survive via the reconciliation channel
    and force REQUIRES_REVIEW -- never silently reach the same clean
    ACCEPT the base clause alone would produce."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = f"{_BASE_CLAUSE} {_UNUSUAL_CONDITION}."

    # Build the verify-stage response directly (one call per obligation --
    # the reconciliation channel never runs a separate discovery call, it
    # verifies a pre-built candidate against the obligation's own window).
    verify_json = json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": doc[doc.index("Vendor shall indemnify"):doc.index("annual fees paid.") + len("annual fees paid.")],
        "condition_quote": _UNUSUAL_CONDITION,
        "exception_quote": None, "cross_reference_text": None, "definition_term": None,
        "reasoning": "Operative indemnification obligation, conditioned on insurance continuity.",
    })
    with patch("urllib.request.urlopen", return_value=_fake_response(verify_json)):
        facts = ie.extract_indemnification_facts(doc)
        decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")

    assert facts is not None
    assert any(ob.ai_identified_unreconciled_context is not None for ob in facts.obligations)
    matched = [ob for ob in facts.obligations if ob.ai_identified_unreconciled_context is not None][0]
    assert _UNUSUAL_CONDITION in matched.ai_identified_unreconciled_context
    assert decision.state == core.REQUIRES_REVIEW
    assert any(_UNUSUAL_CONDITION in f for f in decision.unresolved_facts)


def test_control_ordinary_clause_ai_and_deterministic_agree(monkeypatch):
    """The corresponding control (Part 2): an ordinary, unqualified
    indemnification clause where the AI reports no condition/exception/
    definition/cross-reference dependency beyond what deterministic
    extraction already established -- the existing deterministic
    decision continues normally, unaffected by the reconciliation
    channel."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = _BASE_CLAUSE
    verify_json = json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": doc[doc.index("Vendor shall indemnify"):] if "Vendor shall indemnify" in doc else doc,
        "condition_quote": None, "exception_quote": None, "cross_reference_text": None, "definition_term": None,
        "reasoning": "Operative indemnification obligation, no conditions found.",
    })
    with patch("urllib.request.urlopen", return_value=_fake_response(verify_json)):
        facts = ie.extract_indemnification_facts(doc)
        decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")

    assert facts is not None
    assert all(ob.ai_identified_unreconciled_context is None for ob in facts.obligations)
    assert decision.state == core.ACCEPT


def test_material_definition_dependency_resolved_forces_review(monkeypatch):
    """The obligation depends on a defined term ("Losses"); resolved
    deterministically, must still force review since this adapter has no
    code path that reads what the resolved definition text says."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        '1. Definitions. "Losses" means direct damages excluding lost profits. '
        f"{_BASE_CLAUSE}"
    )
    verify_json = json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": _BASE_CLAUSE[_BASE_CLAUSE.index("Vendor shall indemnify"):],
        "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
        "definition_term": "Losses",
        "reasoning": "Operative indemnification obligation, scoped by a defined term.",
    })
    with patch("urllib.request.urlopen", return_value=_fake_response(verify_json)):
        facts = ie.extract_indemnification_facts(doc)
        decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")

    assert facts is not None
    matched = [ob for ob in facts.obligations if ob.ai_identified_unreconciled_context is not None]
    assert matched, "expected the resolved definition dependency to be preserved on at least one obligation"
    assert "Losses" in matched[0].ai_identified_unreconciled_context
    assert decision.state == core.REQUIRES_REVIEW


def test_material_definition_dependency_unresolved_forces_review_not_silent(monkeypatch):
    """The AI claims a dependency on a defined term this document never
    actually defines -- the candidate is correctly NOT_ADMITTED, but the
    failure must not vanish; it must still force review."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = _BASE_CLAUSE
    verify_json = json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": doc[doc.index("Vendor shall indemnify"):] if "Vendor shall indemnify" in doc else doc,
        "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
        "definition_term": "Losses",
        "reasoning": "...",
    })
    with patch("urllib.request.urlopen", return_value=_fake_response(verify_json)):
        facts = ie.extract_indemnification_facts(doc)
        decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")

    assert facts is not None
    matched = [ob for ob in facts.obligations if ob.ai_identified_unreconciled_context is not None]
    assert matched
    assert "Losses" in matched[0].ai_identified_unreconciled_context
    assert decision.state == core.REQUIRES_REVIEW


def test_material_cross_reference_resolved_forces_review(monkeypatch):
    """The obligation's cap is cross-referenced to another section;
    resolved deterministically, must still force review."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        f"{_BASE_CLAUSE} The cap amount is further addressed in Section 14.2.\n\n"
        "Section 14.2 Supplemental Terms. Notwithstanding the foregoing, the cap escalates to 3 "
        "times fees for claims arising from a data breach."
    )
    verify_json = json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": doc[doc.index("Vendor shall indemnify"):doc.index("Section 14.2.") + len("Section 14.2.")],
        "condition_quote": None, "exception_quote": None,
        "cross_reference_text": "Section 14.2",
        "reasoning": "Operative indemnification obligation, further addressed by a cross-referenced section.",
    })
    with patch("urllib.request.urlopen", return_value=_fake_response(verify_json)):
        facts = ie.extract_indemnification_facts(doc)
        decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")

    assert facts is not None
    matched = [ob for ob in facts.obligations if ob.ai_identified_unreconciled_context is not None]
    assert matched
    assert "14.2" in matched[0].ai_identified_unreconciled_context
    assert decision.state == core.REQUIRES_REVIEW


def test_missing_cross_reference_target_forces_review(monkeypatch):
    """The obligation cross-references a Schedule never actually
    attached -- must force review with the dependency preserved, not
    silently ignored."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = f"{_BASE_CLAUSE} Exclusions are set forth in Schedule F."
    verify_json = json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": doc[doc.index("Vendor shall indemnify"):] if "Vendor shall indemnify" in doc else doc,
        "condition_quote": None, "exception_quote": None,
        "cross_reference_text": "Schedule F",
        "reasoning": "Operative indemnification obligation, subject to schedule-based exclusions.",
    })
    with patch("urllib.request.urlopen", return_value=_fake_response(verify_json)):
        facts = ie.extract_indemnification_facts(doc)
        decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")

    assert facts is not None
    matched = [ob for ob in facts.obligations if ob.ai_identified_unreconciled_context is not None]
    assert matched
    assert "Schedule F" in matched[0].ai_identified_unreconciled_context
    assert decision.state == core.REQUIRES_REVIEW


def test_two_grounded_competing_readings_never_pick_one(monkeypatch):
    """Two materially different, independently-grounded readings of the
    same obligation must never be resolved by picking one -- both
    preserved as data, decision forced to review."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = (
        "12. Indemnification. Vendor's obligation is addressed in this section; one reading treats "
        "it as a full indemnity, another treats it as a mere best-efforts cooperation duty."
    )
    verify_json = json.dumps({
        "status": "AMBIGUOUS", "evidence_quote": None,
        "condition_quote": None, "exception_quote": None, "cross_reference_text": None, "definition_term": None,
        "competing_reading_a": {
            "proposition": "Vendor owes a full indemnity.",
            "evidence_quote": "one reading treats it as a full indemnity",
        },
        "competing_reading_b": {
            "proposition": "Vendor owes only a best-efforts cooperation duty.",
            "evidence_quote": "another treats it as a mere best-efforts cooperation duty",
        },
        "reasoning": "Two materially different readings of the same sentence.",
    })
    # This document has no regex-recognizable obligation at all via the
    # deterministic OBLIGATION_RE (no "shall indemnify"), so the risk-
    # transfer signal / structural patterns won't structure an obligation
    # either -- exercise the reconciliation channel directly on a
    # synthetic obligation instead, since PRESENT_BUT_UNRESOLVED/
    # CONFIRMED_ABSENT documents never reach the per-obligation loop this
    # channel hooks into.
    obligation = ie.IndemnityObligation(
        indemnifying_role="Vendor", indemnifying_side="sell_side",
        indemnified_role="Customer", indemnified_side="buy_side",
        trigger_treatments={}, scope="third_party_only", defense_control="not_addressed",
        notice_required=None, cooperation_required=None,
        monetary=ie.MonetaryTreatment(kind="uncapped"),
        raw_excerpt=doc, start_index=0, end_index=len(doc), section_label=None,
    )
    with patch("urllib.request.urlopen", return_value=_fake_response(verify_json)):
        ie._reconcile_obligation_with_contextual_analysis(doc, obligation)

    assert obligation.ai_identified_unreconciled_context is not None
    assert "full indemnity" in obligation.ai_identified_unreconciled_context
    assert "best-efforts cooperation duty" in obligation.ai_identified_unreconciled_context


def test_provider_timeout_never_silently_confirms_clean(monkeypatch):
    """A provider failure during reconciliation must never produce a
    grounded qualifier out of nothing -- the reconciliation channel is
    additive, so a failure here simply means it contributes no signal
    (the existing deterministic decision, unaffected, still stands) --
    it must never itself manufacture a false-clean confirmation."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    doc = _BASE_CLAUSE
    facts = ie.extract_indemnification_facts(doc)
    decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")
    assert facts is not None
    assert all(ob.ai_identified_unreconciled_context is None for ob in facts.obligations)
    # Deterministic-only decision proceeds exactly as it would with the
    # channel entirely off -- no false confirmation, no false escalation.
    assert decision.state == core.ACCEPT


def test_malformed_ai_output_never_silently_confirms_clean(monkeypatch):
    """A malformed/unparseable provider response must fail closed
    (VERIFICATION_ERROR under the hood), never silently confirm a clean
    reading."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = _BASE_CLAUSE
    with patch("urllib.request.urlopen", return_value=_fake_response("not valid json at all")):
        facts = ie.extract_indemnification_facts(doc)
        decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")
    assert facts is not None
    assert all(ob.ai_identified_unreconciled_context is None for ob in facts.obligations)
    assert decision.state == core.ACCEPT


def test_unverifiable_evidence_never_becomes_authoritative(monkeypatch):
    """The AI claims a condition but cites a quote that isn't actually in
    the document -- must fail closed (grounding failure), never
    contribute a fabricated condition to the reconciliation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = _BASE_CLAUSE
    verify_json = json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": doc[doc.index("Vendor shall indemnify"):] if "Vendor shall indemnify" in doc else doc,
        "condition_quote": "this text does not appear anywhere in the actual document",
        "exception_quote": None, "cross_reference_text": None, "definition_term": None,
        "reasoning": "...",
    })
    with patch("urllib.request.urlopen", return_value=_fake_response(verify_json)):
        facts = ie.extract_indemnification_facts(doc)
        decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")
    assert facts is not None
    assert all(ob.ai_identified_unreconciled_context is None for ob in facts.obligations)
    assert decision.state == core.ACCEPT


def test_genuine_clause_absence_unaffected_by_reconciliation_channel(monkeypatch):
    """A document with no indemnification language at all is unaffected
    by this channel (it never runs -- there are no obligations to
    reconcile)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    doc = "9. Governing Law. This Agreement is governed by Delaware law."
    facts = ie.extract_indemnification_facts(doc)
    decision = ie.evaluate_indemnification_policy(facts, FakePolicy(), source="Test")
    assert facts is None
    assert decision.state == core.NOT_APPLICABLE


def test_data_survival_at_every_boundary(monkeypatch):
    """End-to-end data-survival assertion (not just final-state): the AI
    result, the candidate, the grounding result, and the canonical
    obligation field must all be inspectable and consistent at every
    boundary, not just the final decision."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-mock-test")
    doc = f"{_BASE_CLAUSE} {_UNUSUAL_CONDITION}."
    verify_json = json.dumps({
        "status": "ESTABLISHED",
        "evidence_quote": doc[doc.index("Vendor shall indemnify"):doc.index("annual fees paid.") + len("annual fees paid.")],
        "condition_quote": _UNUSUAL_CONDITION,
        "exception_quote": None, "cross_reference_text": None, "definition_term": None,
        "reasoning": "Operative indemnification obligation, conditioned on insurance continuity.",
    })
    obligation = ie.IndemnityObligation(
        indemnifying_role="Vendor", indemnifying_side="sell_side",
        indemnified_role="Customer", indemnified_side="buy_side",
        trigger_treatments={}, scope="third_party_only", defense_control="not_addressed",
        notice_required=None, cooperation_required=None,
        monetary=ie.MonetaryTreatment(kind="uncapped"),
        raw_excerpt=doc, start_index=0, end_index=len(doc), section_label=None,
    )
    import fact_admission as fa
    candidate_holder = {}
    real_verify_and_ground = fa.verify_and_ground

    def spy_verify_and_ground(candidate, *args, **kwargs):
        result = real_verify_and_ground(candidate, *args, **kwargs)
        candidate_holder["candidate"] = result
        return result

    with patch("urllib.request.urlopen", return_value=_fake_response(verify_json)), \
         patch.object(fa, "verify_and_ground", side_effect=spy_verify_and_ground):
        ie._reconcile_obligation_with_contextual_analysis(doc, obligation)

    candidate = candidate_holder["candidate"]
    # AI response -> VerificationResult
    assert candidate.semantic_verification_result.condition_quote == _UNUSUAL_CONDITION
    # -> deterministic grounding result
    assert candidate.deterministic_grounding_result.passed is True
    # -> admitted canonical candidate
    assert candidate.admission_status == fa.ADMITTED
    assert candidate.condition == _UNUSUAL_CONDITION
    # -> reconciled onto the obligation (adapter input)
    assert obligation.ai_identified_unreconciled_context is not None
    assert _UNUSUAL_CONDITION in obligation.ai_identified_unreconciled_context
