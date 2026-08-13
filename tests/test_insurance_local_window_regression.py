"""
Regression tests for the insurance_policy_engine._local_window decimal-
truncation bug (Stage A.1 of the pre-#11 hardening pass).

Before the fix, _local_window scoped a coverage-type mention's dollar-
amount search using a naive `text.find(".")` sentence boundary. A decimal
dollar figure like "$2.5 million" has its own "." between two digits, so
the window was truncated immediately after "2." — losing both the
".5 million" fraction/multiplier and any qualifier (e.g. "in the
aggregate") that came later in the same sentence. The fix reuses
payment_terms_policy_engine's already-proven sentence-boundary regex
(a period NOT immediately between two digits, or a semicolon).

These tests both prove the fix (values are no longer truncated) and prove
the fix didn't over-widen the window (adjacent, unrelated coverage-type
sentences still don't bleed into each other).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import insurance_policy_engine as ine


def test_decimal_million_per_occurrence_and_aggregate_both_captured():
    text = (
        "The Contractor shall maintain Commercial General Liability insurance with limits of not "
        "less than $2.5 million per occurrence and $5,000,000 in the aggregate, covering bodily "
        "injury and property damage arising from the performance of this Agreement."
    )
    facts = ine.extract_insurance_facts(text)
    cgl = facts.coverages["cgl"]
    assert cgl.per_occurrence_limit == 2_500_000.0, (
        f"expected $2.5 million to resolve to 2,500,000, got {cgl.per_occurrence_limit} "
        f"(2.0 would indicate the pre-fix truncation-at-decimal-point bug)"
    )
    assert cgl.aggregate_limit == 5_000_000.0, (
        f"expected the aggregate figure to be reached at all, got {cgl.aggregate_limit} "
        f"(None would indicate the window was truncated before reaching it)"
    )
    assert cgl.limit_conflict is False


def test_decimal_m_suffix_per_occurrence_captured():
    text = (
        "The Contractor shall maintain Commercial General Liability insurance with limits of not "
        "less than $1.25M per occurrence."
    )
    facts = ine.extract_insurance_facts(text)
    cgl = facts.coverages["cgl"]
    assert cgl.per_occurrence_limit == 1_250_000.0, (
        f"expected $1.25M to resolve to 1,250,000, got {cgl.per_occurrence_limit}"
    )


def test_decimal_deductible_not_truncated():
    text = (
        "The Contractor shall maintain Commercial General Liability insurance with a deductible "
        "of $2.5 million per occurrence, with limits of not less than $10,000,000 in the aggregate."
    )
    facts = ine.extract_insurance_facts(text)
    assert facts.deductible_or_sir == 2_500_000.0, (
        f"decimal deductible amount should not be truncated at its own internal decimal point, "
        f"got {facts.deductible_or_sir}"
    )


def test_local_window_does_not_swallow_a_real_adjacent_sentence():
    """A genuine sentence boundary immediately after a decimal dollar
    figure must still stop the window -- the fix must not turn into
    "never stop at a period", only "don't stop at a decimal point's
    period"."""
    text = (
        "The Contractor shall maintain Commercial General Liability insurance with limits of not "
        "less than $2.5 million per occurrence. The Contractor shall also maintain Cyber Liability "
        "insurance with limits of not less than $1,000,000 per occurrence."
    )
    facts = ine.extract_insurance_facts(text)
    cgl = facts.coverages["cgl"]
    cyber = facts.coverages["cyber_liability"]
    assert cgl.per_occurrence_limit == 2_500_000.0
    assert cyber.per_occurrence_limit == 1_000_000.0
    # Neither coverage type's limit should have bled into the other's.
    assert cgl.limit_conflict is False
    assert cyber.limit_conflict is False


def test_local_window_stops_at_semicolon_boundary():
    text = (
        "The Contractor shall maintain Commercial General Liability insurance with limits of not "
        "less than $2.5 million per occurrence; the Contractor shall also maintain Automobile "
        "Liability insurance with limits of not less than $1,000,000 per occurrence."
    )
    facts = ine.extract_insurance_facts(text)
    cgl = facts.coverages["cgl"]
    auto = facts.coverages["auto_liability"]
    assert cgl.per_occurrence_limit == 2_500_000.0
    assert auto.per_occurrence_limit == 1_000_000.0


def test_local_window_helper_directly_on_decimal_boundary():
    """Direct unit check on _local_window itself: the period inside
    "2.5" must not be treated as the window's stopping point."""
    text = "Commercial General Liability with limits of $2.5 million per occurrence and $5,000,000 in the aggregate."
    start = text.index("Commercial")
    window = ine._local_window(text, start, [])
    assert "million" in window, f"window truncated before 'million': {window!r}"
    assert "aggregate" in window, f"window truncated before reaching the aggregate qualifier: {window!r}"


def test_local_window_helper_still_stops_at_real_sentence_end():
    text = "Commercial General Liability with limits of $2.5 million per occurrence. Unrelated next sentence about Cyber Liability."
    start = text.index("Commercial")
    window = ine._local_window(text, start, [])
    assert "Cyber Liability" not in window, f"window over-extended past the real sentence boundary: {window!r}"
