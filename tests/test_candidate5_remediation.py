"""
Candidate 5 remediation — targeted tests for the general failure class
behind Candidate 4's UNRESOLVED_DEFINITION_TO_CLEAN=17 (all 17 occurrences
traced to one shared pattern: a capitalized term used with an explicit
"as defined in this Agreement"/"as defined herein" self-reference that
is never actually defined anywhere in the document).

Each section pairs a generalized regression test reproducing the exact
burned-corpus failure shape with a materially different, freshly-authored
variant — these fresh variants are remediation tests, not the next
independent corpus.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import policy_engine_core as pec
import insurance_policy_engine as ipe
import ip_ownership_policy_engine as ipo
import warranties_policy_engine as we


# ---------------------------------------------------------------------------
# Shared primitive
# ---------------------------------------------------------------------------

def test_self_referential_definition_unresolved_fires_when_term_never_defined():
    note = pec.self_referential_definition_unresolved(
        "Provider shall maintain the Required Coverage, as defined in this Agreement, throughout the term."
    )
    assert note is not None
    assert "Required Coverage" in note


def test_self_referential_definition_resolved_when_definition_clause_exists():
    note = pec.self_referential_definition_unresolved(
        '"Required Coverage" means Commercial General Liability insurance with a limit of $1,000,000. '
        "Provider shall maintain the Required Coverage, as defined in this Agreement, throughout the term."
    )
    assert note is None


def test_self_referential_definition_resolved_with_parenthetical_definition_style():
    note = pec.self_referential_definition_unresolved(
        'Provider shall deliver the Milestone Deliverables (the "Deliverables") on schedule. '
        "Acceptance of the Deliverables, as defined in this Agreement, triggers payment."
    )
    assert note is None


def test_self_referential_definition_does_not_fire_on_plain_agreement_reference():
    """Negative control: 'as defined in this Agreement' referring back to
    'this Agreement' itself (not a separate defined term) must not
    falsely fire."""
    note = pec.self_referential_definition_unresolved(
        "The parties' respective obligations, as defined in this Agreement, remain in full force."
    )
    assert note is None


# ---------------------------------------------------------------------------
# Insurance
# ---------------------------------------------------------------------------

def test_insurance_undefined_required_coverage_never_clean():
    """Burned-corpus shape (iv-insurance-0277 family)."""
    facts = ipe.extract_insurance_facts(
        "13. Insurance. Provider shall maintain the Required Coverage, as defined in this Agreement, throughout the term."
    )
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"
    policy = _minimal_insurance_policy()
    decision = ipe.evaluate_insurance_policy(facts, policy, source="test")
    assert decision.state == "REQUIRES_REVIEW"


def test_insurance_undefined_required_coverage_fresh_variant():
    facts = ipe.extract_insurance_facts(
        "Section 9 (Insurance). Vendor agrees to maintain the Applicable Coverage Package, as defined "
        "herein, for the full duration of this engagement."
    )
    assert facts is not None
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"


def _minimal_insurance_policy(**overrides):
    import benchmarks.run_insurance_benchmark as rib
    return rib._build_policy(overrides)


# ---------------------------------------------------------------------------
# IP ownership
# ---------------------------------------------------------------------------

def test_ip_ownership_undefined_custom_work_product_never_clean():
    """Burned-corpus shape (iv-ip_ownership-0223 family)."""
    facts = ipo.extract_ip_facts(
        "11. Ownership. Recipient owns all Custom Work Product, as defined in this Agreement, created under this engagement."
    )
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"


def test_ip_ownership_undefined_term_fresh_variant():
    facts = ipo.extract_ip_facts(
        "Section 6 (Intellectual Property). All right, title, and interest in the Project Materials, "
        "as defined above, shall vest exclusively in Client upon final acceptance."
    )
    assert facts is not None
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"


# ---------------------------------------------------------------------------
# Warranties
# ---------------------------------------------------------------------------

def test_warranties_undefined_deliverables_never_clean():
    """Burned-corpus shape (iv-warranties-0493 family)."""
    facts = we.extract_warranties_facts(
        "8. Warranties. Provider warrants that the Deliverables, as defined in this Agreement, will "
        "materially conform to the agreed specifications."
    )
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"


def test_warranties_undefined_term_fresh_variant():
    facts = we.extract_warranties_facts(
        "Clause 12 (Warranty). Contractor warrants that the Contracted Services, as defined below, "
        "will be performed in a professional and workmanlike manner."
    )
    assert facts is not None
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"
