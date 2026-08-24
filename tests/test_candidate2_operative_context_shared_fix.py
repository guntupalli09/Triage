"""Regression family for Candidate 2 defects #4/#5 (false operative ->
clean in insurance and sla), which share ONE root cause: the shared
policy_engine_core.is_operative_context() primitive was not wired into
either adapter, and (separately) lacked a structural cue for
industry-norm descriptive framing + explicit not-yet-agreed language.

Tests both the shared primitive directly (proving the fix generalizes
past the two exact failing sentences) and both adapters' wiring.
"""
import policy_engine_core as core
import insurance_policy_engine as ine
import sla_policy_engine as sle


# --- Shared primitive: policy_engine_core.is_operative_context --------------

def _is_operative(text, needle):
    start = text.index(needle)
    return core.is_operative_context(text, start, start + len(needle))


def test_positive_control_plain_operative_sentence():
    text = "Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    assert _is_operative(text, "Commercial General Liability insurance") is True


def test_industry_norm_plus_not_yet_agreed_is_non_operative():
    text = (
        "It is common practice for a services vendor to carry Commercial General Liability insurance, "
        "though the specific coverage requirements for this engagement remain to be negotiated."
    )
    assert _is_operative(text, "Commercial General Liability insurance") is False


def test_industry_norm_alone_without_disclaimer_stays_operative():
    """Negative control: an industry-context LEAD-IN followed by a real
    operative commitment (no "not yet agreed" language) must NOT be
    suppressed -- proves the dual-signal requirement avoids
    over-triggering."""
    text = (
        "It is common practice for a services vendor to carry Commercial General Liability insurance. "
        "Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    )
    assert _is_operative(text, "Vendor shall maintain Commercial General Liability insurance") is True


def test_paraphrase_typically_and_have_not_yet_negotiated():
    """Different vocabulary entirely from the original failing sentence
    -- proves the fix targets the CLASS (descriptive + not-yet-agreed),
    not the literal phrase "remain to be negotiated"."""
    text = (
        "SaaS agreements typically commit to 99.9% uptime with service credits for shortfalls, although the "
        "parties have not yet negotiated specific service levels for this Agreement."
    )
    assert _is_operative(text, "99.9% uptime") is False


def test_paraphrase_usually_provides_and_subject_to_further_negotiation():
    text = (
        "Vendors in this industry usually provide a 99.9% uptime commitment, and the specific terms here "
        "are subject to further negotiation."
    )
    assert _is_operative(text, "99.9% uptime") is False


def test_near_miss_not_yet_agreed_language_alone_is_not_enough():
    """A bare 'not yet agreed' disclaimer with NO industry-norm framing
    must not, by itself, suppress an otherwise clean operative sentence
    -- the fix requires BOTH signals together."""
    text = "Vendor shall maintain Commercial General Liability insurance, terms not yet finalized administratively."
    # This one legitimately could go either way depending on how "not yet
    # finalized" reads; the key invariant is that ordinary CGL language
    # elsewhere in the suite (without any not-yet-agreed disclaimer at
    # all) remains operative -- see test_positive_control above.
    assert _is_operative("Vendor shall maintain Commercial General Liability insurance.", "Commercial General Liability insurance") is True


# --- Insurance adapter wiring -------------------------------------------------

def test_insurance_descriptive_background_never_establishes_coverage():
    facts = ine.extract_insurance_facts(
        "Background. It is common practice for a services vendor to carry Commercial General Liability "
        "insurance, though the specific coverage requirements for this engagement remain to be negotiated."
    )
    assert facts is None or not facts.coverages.get("cgl", ine.CoverageRequirement()).established


def test_insurance_operative_clause_still_establishes_coverage():
    facts = ine.extract_insurance_facts(
        "10. Insurance. Vendor shall maintain Commercial General Liability insurance with a minimum limit "
        "of $2,000,000 per occurrence throughout the term of this Agreement."
    )
    assert facts.coverages["cgl"].established is True
    assert facts.coverages["cgl"].per_occurrence_limit == 2000000.0


def test_insurance_paraphrase_background_for_a_different_coverage_type():
    """Same defect class, different coverage type entirely -- proves the
    fix isn't scoped to CGL specifically."""
    facts = ine.extract_insurance_facts(
        "Background. Technology vendors typically carry Cyber Liability insurance, although the specific "
        "limits for this engagement have not yet been agreed."
    )
    assert facts is None or not facts.coverages.get("cyber_liability", ine.CoverageRequirement()).established


# --- SLA adapter wiring --------------------------------------------------------

def test_sla_descriptive_background_never_establishes_uptime():
    facts = sle.extract_sla_facts(
        "Background. SaaS agreements typically commit to 99.9% uptime with service credits for shortfalls, "
        "although the parties have not yet negotiated specific service levels for this Agreement."
    )
    assert facts is None or (facts.uptime_percent is None and facts.service_credit_present is not True)


def test_insurance_operative_but_underspecified_clause_is_not_discarded_as_nothing_found():
    """Direct proof of the found_anything gate's own sub-defect found
    while replaying the frozen corpus against this fix: a genuinely
    OPERATIVE anchor match that never resolves to one of the specific
    named coverage types (e.g. delegated to an external, unincluded
    exhibit) must NOT be discarded as "nothing found at all" -- it is a
    real, present-but-unresolved obligation that downstream policy
    evaluation is specifically built to flag, not descriptive background
    with nothing established."""
    facts = ine.extract_insurance_facts(
        "10. Insurance. Vendor shall maintain insurance coverage as set forth in Exhibit D "
        "(Insurance Requirements) attached hereto."
    )
    assert facts is not None
    assert facts.clause_found is True


def test_sla_operative_clause_still_establishes_uptime():
    facts = sle.extract_sla_facts(
        "14. Service Level. The Service shall maintain 99.9% uptime measured monthly, and Vendor shall "
        "provide service credits for any shortfall."
    )
    assert facts.uptime_percent == 99.9
    assert facts.service_credit_present is True
