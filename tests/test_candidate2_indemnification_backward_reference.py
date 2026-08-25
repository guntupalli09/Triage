"""Regression family for Candidate 2 defect #6 (indemnification material
context silently lost): a single, unopposed backward-reference qualifier
on an obligation's own Section (most commonly a leading "Notwithstanding
Section N, ..." construct) was invisible to the pre-Candidate-2 detector,
which only ever fired when TWO conflicting backward-references existed.

Tests both the shared primitive (policy_engine_core.
detect_backward_referenced_qualifier) directly and the indemnification
adapter's wiring of it, proving the fix generalizes past the exact
"Section 19 notwithstanding Section 12" fixture that originally exposed
it.
"""
from dataclasses import dataclass
from typing import List, Optional

import indemnification_policy_engine as ie
import policy_engine_core as core


@dataclass
class FakePolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = "Legal Director"
    fallback_text: Optional[str] = "Approved fallback indemnification language."
    required_protection_triggers_json: Optional[List[str]] = None
    prohibited_exposure_triggers_json: Optional[List[str]] = None
    require_exposure_third_party_only: bool = False
    require_defense_control_for_exposure: bool = False
    require_notice_and_cooperation_for_exposure: bool = False
    prohibit_uncapped_exposure: bool = True
    exposure_preferred_multiplier: Optional[float] = 1.0
    exposure_acceptable_max_multiplier: Optional[float] = 2.0
    exposure_negotiate_max_multiplier: Optional[float] = 3.0


def evaluate(text: str, **policy_kwargs) -> core.PolicyDecision:
    policy = FakePolicy(**policy_kwargs)
    facts = ie.extract_indemnification_facts(text)
    return ie.evaluate_indemnification_policy(facts, policy, source="Test Playbook v1")


# --- Shared primitive: policy_engine_core.detect_backward_referenced_qualifier

def test_shared_primitive_single_notwithstanding_reference_is_established():
    text = (
        "12. Indemnification. Vendor shall indemnify Customer for third-party claims. "
        "19. Limitation. Notwithstanding Section 12, Vendor's indemnification obligation "
        "shall apply only to claims filed within ninety days of the underlying incident."
    )
    ev = core.detect_backward_referenced_qualifier(text, "Section", "12")
    assert ev is not None
    assert ev.status == "ESTABLISHED"
    assert ev.condition_type == "backward_reference"


def test_shared_primitive_no_reference_returns_none():
    text = "12. Indemnification. Vendor shall indemnify Customer for third-party claims."
    assert core.detect_backward_referenced_qualifier(text, "Section", "12") is None


def test_shared_primitive_two_conflicting_references_still_conflicting():
    text = (
        "12. Indemnification. Vendor shall indemnify Customer for third-party claims. "
        "19. Notwithstanding Section 12, the indemnification obligation shall apply only "
        "to claims arising after January 1, 2027. "
        "20. The indemnification obligation under Section 12 shall not apply until the "
        "underlying claim is finally adjudicated."
    )
    ev = core.detect_backward_referenced_qualifier(text, "Section", "12")
    assert ev is not None
    assert ev.status == "CONFLICTING"


# --- Adapter wiring: indemnification_policy_engine ----------------------------

class TestBackwardReferenceQualifierWiring:
    def test_positive_control_no_qualifier_still_accepts(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer "
            "from and against any third-party claims arising from Vendor's gross negligence. "
            "Vendor's indemnification obligations shall not exceed 1 times the total annual "
            "fees paid."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT

    def test_single_notwithstanding_qualifier_forces_review_not_silently_clean(self):
        """The exact defect class: a single, unopposed backward-reference
        qualifier on the obligation's own section must surface as a real,
        unresolved fact rather than disappearing because there was no
        second conflicting reference to compare it against."""
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer "
            "from and against any third-party claims arising from Vendor's gross negligence. "
            "Vendor's indemnification obligations shall not exceed 1 times the total annual "
            "fees paid.\n\n"
            "19. Limitation on Remedies. Notwithstanding Section 12, Vendor's indemnification "
            "obligation shall apply only to claims filed within ninety days of the underlying "
            "incident."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_paraphrase_anything_to_the_contrary_contained_in_section(self):
        """Different vocabulary for the same backward-reference concept --
        proves the fix targets the STRUCTURAL cross-reference pattern, not
        the literal word 'Notwithstanding'."""
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer "
            "from and against any third-party claims arising from Vendor's gross negligence. "
            "Vendor's indemnification obligations shall not exceed 1 times the total annual "
            "fees paid.\n\n"
            "19. Limitation on Remedies. Notwithstanding anything to the contrary contained in "
            "Section 12, Vendor's indemnification obligation is limited to claims filed within "
            "ninety days of the underlying incident."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_multi_section_form_forward_reference_wording_still_caught(self):
        """The original 'backward condition on section' surface form
        (qualifying clause opens with the section reference, THEN the
        'shall apply only' language) must still work alongside the new
        leading-notwithstanding form."""
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer "
            "from and against any third-party claims arising from Vendor's gross negligence. "
            "Vendor's indemnification obligations shall not exceed 1 times the total annual "
            "fees paid.\n\n"
            "19. The indemnification obligation under Section 12 shall apply only to claims "
            "filed within ninety days of the underlying incident."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_near_miss_qualifier_on_a_different_section_not_misattributed(self):
        """Negative control: a 'Notwithstanding Section 7, ...' qualifier
        that references an UNRELATED section must not be misattributed to
        this obligation's Section 12."""
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer "
            "from and against any third-party claims arising from Vendor's gross negligence. "
            "Vendor's indemnification obligations shall not exceed 1 times the total annual "
            "fees paid.\n\n"
            "19. Notwithstanding Section 7, the payment terms described therein shall not "
            "apply to disputed invoices."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT

    def test_ambiguous_form_qualifier_referencing_wrong_kind_not_misattributed(self):
        """Negative control: a backward reference to 'Article 12' (a
        different division KIND from 'Section') must not be conflated
        with a Section-12 qualifier."""
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer "
            "from and against any third-party claims arising from Vendor's gross negligence. "
            "Vendor's indemnification obligations shall not exceed 1 times the total annual "
            "fees paid.\n\n"
            "19. Notwithstanding Article 12, unrelated confidentiality obligations survive "
            "termination."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT
