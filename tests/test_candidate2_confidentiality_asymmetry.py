"""Regression family for Candidate 2 defect #1 (confidentiality false
safe: asymmetric directional obligations bypass asymmetry detection).
Proves the underlying structural rule, not the one failed sentence --
multiple phrasings, a negative control, a paraphrase, and a
multi-paragraph form.
"""
import confidentiality_policy_engine as cpe


class FakePolicy:
    contract_side = "sell_side"
    escalation_approval_authority = None
    fallback_text = None
    required_exclusions_json = []
    min_protection_duration_years = None
    max_exposure_duration_years = None
    require_mutual_confidentiality = True


def _evaluate(text):
    facts = cpe.extract_confidentiality_facts(text)
    return facts, cpe.evaluate_confidentiality_policy(facts, FakePolicy())


def test_positive_control_symmetric_terms_stay_clean():
    """Negative control (for THIS defect family): genuinely symmetric
    directional obligations must NOT be flagged -- proves the fix isn't
    over-triggering on every two-sentence confidentiality clause."""
    text = (
        "Vendor shall protect Customer's Confidential Information for five years using reasonable care. "
        "Customer shall protect Vendor's Confidential Information for five years using reasonable care."
    )
    facts, decision = _evaluate(text)
    assert decision.state == cpe.ACCEPT


def test_asymmetric_duration_forces_non_clean():
    text = (
        "Vendor shall protect Customer's Confidential Information for five years using reasonable care. "
        "Customer shall protect Vendor's Confidential Information indefinitely using the highest degree of "
        "care available in the industry."
    )
    facts, decision = _evaluate(text)
    assert decision.state != cpe.ACCEPT


def test_paraphrase_different_wording_still_caught():
    """The same asymmetry, phrased with entirely different vocabulary
    from the original failing case -- proves the fix targets the
    STRUCTURAL comparison, not the specific words "indefinitely"/"five
    years"."""
    text = (
        "Vendor agrees to hold in confidence Customer's Confidential Information for a period of three years, "
        "exercising the same degree of care it uses to protect its own confidential materials. "
        "Customer agrees to hold in confidence Vendor's Confidential Information in perpetuity, exercising the "
        "same degree of care it uses to protect its own confidential materials."
    )
    facts, decision = _evaluate(text)
    assert decision.state != cpe.ACCEPT


def test_multi_paragraph_form_still_caught():
    """The two directional obligations separated by an intervening,
    unrelated paragraph -- proves the fix isn't merely a same-sentence
    or adjacent-sentence heuristic."""
    text = (
        "8. Confidentiality. Vendor shall protect Customer's Confidential Information for five years using "
        "reasonable care.\n\n"
        "8.1 Marking. Information need not be marked confidential to be protected under this Section.\n\n"
        "8.2 Reciprocal Obligation. Customer shall protect Vendor's Confidential Information indefinitely "
        "using the highest degree of care available in the industry."
    )
    facts, decision = _evaluate(text)
    assert decision.state != cpe.ACCEPT


def test_care_standard_asymmetry_alone_also_caught():
    """Asymmetry on standard-of-care alone (matching durations) is a
    distinct dimension from duration asymmetry -- must independently
    trigger the same comparison."""
    text = (
        "Vendor shall protect Customer's Confidential Information for five years using reasonable care. "
        "Customer shall protect Vendor's Confidential Information for five years using the same degree of "
        "care it uses to protect its own confidential information."
    )
    facts, decision = _evaluate(text)
    # Both use "reasonable_care" vs "same_as_own" -- materially different
    # standards even with matching duration.
    assert decision.state != cpe.ACCEPT


def test_window_bleed_no_longer_masks_a_second_obligations_own_terms():
    """Direct proof of the masking sub-defect: the FIRST obligation's own
    duration must reflect ONLY its own sentence, not swallow the SECOND
    obligation's "indefinitely" via an overly wide classification
    window."""
    text = (
        "Vendor shall protect Customer's Confidential Information for five years using reasonable care. "
        "Customer shall protect Vendor's Confidential Information indefinitely using the highest degree of "
        "care available in the industry."
    )
    facts = cpe.extract_confidentiality_facts(text)
    exposure, protection, _ = cpe._resolve_obligations_for_side(facts.obligations, "sell_side")
    assert exposure.duration_perpetual is False
    assert protection.duration_perpetual is True
