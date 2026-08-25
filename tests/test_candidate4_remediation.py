"""
Candidate 4 remediation — targeted adversarial tests for the general
failure class identified in the Candidate 3 independent-validation report
(UNVERIFIED_FEEDING_CLEAN / FALSE_ABSENCE): a deterministic anchor is
genuinely operative (a real party obligation is present) but nothing could
be deterministically structured from it, and AI discovery also returned
nothing (a genuine recall miss, not a disproven claim). The pre-existing
code left `absence_state` at its default CONFIRMED_ABSENT in this case,
which downstream reaches ACCEPT/NOT_APPLICABLE — an operative, unverified
obligation silently treated as "affirmatively confirmed absent."

Each adapter section below pairs:
  1. a generalized regression test reproducing the exact burned-corpus
     failure shape (confirmed live in PHASE4_HARD_SAFETY_GATES.md), and
  2. a materially different, freshly-authored variant of the same failure
     class (per the mission's anti-memorization requirement) — these fresh
     variants are remediation tests, not the next independent corpus.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import insurance_policy_engine as ipe
import data_security_policy_engine as dse
import ip_ownership_policy_engine as ipo


# ---------------------------------------------------------------------------
# Insurance
# ---------------------------------------------------------------------------

def test_insurance_operative_anchor_unstructured_never_confirmed_absent():
    """Burned-corpus shape (iv-insurance-0274): a generic, non-named-coverage-
    type phrasing that IS operative must not collapse to CONFIRMED_ABSENT."""
    facts = ipe.extract_insurance_facts(
        "13. Insurance. Provider shall maintain liability coverage of at least $1 million, "
        "provided that such coverage shall only be required for the duration of any on-site work."
    )
    assert facts is not None
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"


def test_insurance_operative_anchor_unstructured_fresh_variant():
    """Fresh variant: a different generic ancillary-coverage phrasing never
    seen in the burned corpus or the independent corpus."""
    facts = ipe.extract_insurance_facts(
        "Section 11. Contractor shall carry appropriate insurance for the duration of this "
        "engagement, at levels the parties agree are commercially reasonable."
    )
    assert facts is not None
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"


def test_insurance_required_but_unaddressed_still_reaches_must_redline():
    """Precision check: when a policy DOES require a specific coverage type
    and it is genuinely never addressed anywhere, the more specific,
    already-correct MUST_REDLINE finding must not be downgraded to a
    generic REQUIRES_REVIEW by the PRESENT_BUT_UNRESOLVED fallback."""
    facts = ipe.extract_insurance_facts("9. Insurance. Coverage.")
    policy = _minimal_insurance_policy(require_cgl=True, cgl_minimum_per_occurrence=1_000_000.0)
    decision = ipe.evaluate_insurance_policy(facts, policy, source="test")
    assert decision.state == "MUST_REDLINE"


def test_insurance_genuinely_nothing_stays_not_applicable():
    """Negative control: a document that never mentions insurance at all
    must still resolve to NOT_APPLICABLE, not escalate."""
    facts = ipe.extract_insurance_facts(
        "This Agreement governs the licensing of software between the parties."
    )
    assert facts is None


def _minimal_insurance_policy(**overrides):
    import benchmarks.run_insurance_benchmark as rib
    return rib._build_policy(overrides)


# ---------------------------------------------------------------------------
# Data security
# ---------------------------------------------------------------------------

def test_data_security_operative_anchor_unstructured_never_confirmed_absent():
    facts = dse.extract_data_security_facts(
        "8. Data Security. Vendor shall implement appropriate technical measures "
        "with respect to personal data processed under this Agreement, as further "
        "described in the parties' internal security procedures."
    )
    assert facts is not None
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"


def test_data_security_operative_anchor_unstructured_fresh_variant():
    facts = dse.extract_data_security_facts(
        "Clause 14. Provider commits to handling personal data in accordance with "
        "applicable data protection requirements throughout the engagement."
    )
    assert facts is not None
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"


def test_data_security_descriptive_mention_does_not_confirm_absent():
    """Negative control: a purely descriptive/recital mention of the topic
    must never be silently treated as CONFIRMED_ABSENT (the old, unsafe
    default) — the shared operative-context classifier's own permissive
    default (no explicit suppression cue -> assume operative) means it
    correctly escalates to PRESENT_BUT_UNRESOLVED here too, which is the
    safe direction; it must not remain the unsafe CONFIRMED_ABSENT."""
    facts = dse.extract_data_security_facts(
        "Recitals. This Agreement is entered into in a context where data protection "
        "and privacy regulation generally continue to evolve across jurisdictions."
    )
    assert facts is not None
    assert facts.absence_state != "CONFIRMED_ABSENT"


# ---------------------------------------------------------------------------
# IP ownership
# ---------------------------------------------------------------------------

def test_ip_ownership_conditional_transfer_construction_never_false_absence():
    """Burned-corpus shape (independent corpus's ip_ownership 'conditional'
    family): a less-common ownership-transfer construction ('Title...
    shall transfer to X upon Y') must not resolve to a clean ACCEPT/
    NOT_APPLICABLE merely because it doesn't match the common 'shall be
    owned exclusively by X' phrasing AND AI discovery misses it too."""
    facts = ipo.extract_ip_facts(
        "7. Intellectual Property. Title to the deliverables shall transfer to Recipient "
        "upon final payment in full of all amounts due under this Statement of Work."
    )
    assert facts is not None
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"


def test_ip_ownership_conditional_transfer_fresh_variant():
    facts = ipo.extract_ip_facts(
        "Section 5. Ownership of the work product shall pass to Client only after "
        "Client has confirmed acceptance of all deliverables in writing."
    )
    assert facts is not None
    assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"


def test_ip_ownership_genuinely_nothing_stays_absent():
    """Negative control: a document with no IP-ownership anchor at all must
    still resolve to a clean None (NOT_APPLICABLE), not escalate."""
    facts = ipo.extract_ip_facts(
        "This Agreement sets forth the payment terms between the parties."
    )
    assert facts is None
