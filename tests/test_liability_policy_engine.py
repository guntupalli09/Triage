"""
Adversarial test suite for liability_policy_engine.py.

The point of this suite is not "does the regex match" — it's "when the
clause is more complex than a single number, does the engine refuse to
guess." A simplistic extractor that collapses a sophisticated liability
structure into one multiplier produces a deterministic but wrong decision,
which is worse than admitted uncertainty because the product presents the
answer as authoritative. So most of these tests assert on REQUIRES_REVIEW
and unresolved_facts, not just on the happy-path states.
"""

from dataclasses import dataclass
from typing import List, Optional

import liability_policy_engine as lpe


@dataclass
class FakePolicy:
    preferred_multiplier: Optional[float] = 1.0
    acceptable_max_multiplier: Optional[float] = 2.0
    negotiate_max_multiplier: Optional[float] = 3.0
    prohibit_unlimited: bool = True
    required_exceptions_json: Optional[List[str]] = None
    fallback_text: Optional[str] = "Approved fallback: liability capped at 1x annual fees."
    escalation_approval_authority: Optional[str] = "Legal Director"
    contract_side: str = "mutual"
    require_consequential_damages_exclusion: bool = False
    required_consequential_carveouts_json: Optional[List[str]] = None


def evaluate(text: str, **policy_kwargs) -> lpe.PolicyDecision:
    policy = FakePolicy(**policy_kwargs)
    facts = lpe.extract_liability_facts(text)
    return lpe.evaluate_liability_policy(facts, policy, source="Test Playbook v1")


class TestNoClause:
    def test_no_limitation_of_liability_section_is_not_applicable(self):
        d = evaluate("This Agreement shall be governed by the laws of Delaware.")
        assert d.state == lpe.NOT_APPLICABLE
        assert d.start_index is None


class TestCleanMultiplierCase:
    def test_within_preferred_position_accepts(self):
        text = (
            "12. Limitation of Liability. Except as set forth below, in no event shall either "
            "party's aggregate liability exceed 1 times the total annual fees paid in the twelve "
            "(12) months preceding the claim."
        )
        d = evaluate(text)
        assert d.state == lpe.ACCEPT
        assert d.unresolved_facts == []

    def test_between_acceptable_and_negotiate_is_negotiate(self):
        text = (
            "12. Limitation of Liability. In no event shall either party's aggregate liability "
            "exceed 2.5 times the total fees paid in the twelve (12) months preceding the claim."
        )
        d = evaluate(text)
        assert d.state == lpe.NEGOTIATE

    def test_beyond_negotiate_max_escalates(self):
        text = (
            "12. Limitation of Liability. In no event shall either party's aggregate liability "
            "exceed 5 times the total fees paid in the twelve (12) months preceding the claim."
        )
        d = evaluate(text)
        assert d.state == lpe.ESCALATE
        assert d.escalate_to == "Legal Director"


class TestUnlimited:
    def test_unlimited_liability_is_prohibited_when_policy_prohibits_it(self):
        text = "12. Limitation of Liability. Supplier shall have unlimited liability for any breach of this Agreement."
        d = evaluate(text)
        assert d.state == lpe.PROHIBITED
        assert d.fallback_text

    def test_unlimited_liability_escalates_when_policy_permits_with_approval(self):
        text = "12. Limitation of Liability. Supplier shall have unlimited liability for any breach of this Agreement."
        d = evaluate(text, prohibit_unlimited=False)
        assert d.state == lpe.ESCALATE


class TestNoCapStated:
    def test_clause_exists_but_states_no_number_must_redline(self):
        text = (
            "12. Limitation of Liability. Each party's liability under this Agreement shall be "
            "governed by the terms set forth in this Section."
        )
        d = evaluate(text)
        assert d.state == lpe.MUST_REDLINE
        assert d.fallback_text


class TestFixedDollarCap:
    def test_fixed_amount_escalates_for_manual_comparison_not_guessed(self):
        text = (
            "12. Limitation of Liability. In no event shall Supplier's maximum aggregate liability "
            "exceed $500,000 for any claim arising under this Agreement."
        )
        d = evaluate(text)
        assert d.state == lpe.ESCALATE
        assert "500,000" in d.extracted_summary
        assert "manually" in d.required_action.lower()


class TestMultipleConflictingCaps:
    def test_two_different_general_caps_requires_review_not_a_guess(self):
        # Deliberately adversarial: two different numeric caps with no
        # category association distinguishing them — a naive "first match
        # wins" extractor would silently pick 1x and call it ACCEPT, which
        # would be a confidently wrong answer.
        text = (
            "12. Limitation of Liability. In no event shall either party's liability exceed 1 times "
            "the annual fees paid. Notwithstanding the foregoing, aggregate liability under this "
            "Agreement shall in no case exceed 4 times the annual fees paid."
        )
        d = evaluate(text)
        assert d.state == lpe.REQUIRES_REVIEW
        assert any("general liability cap" in f for f in d.unresolved_facts)

    def test_unlimited_and_numeric_cap_together_requires_review(self):
        text = (
            "12. Limitation of Liability. Liability shall not be limited for breaches of this "
            "Agreement. In no event shall aggregate liability exceed 2 times the annual fees paid."
        )
        d = evaluate(text)
        assert d.state == lpe.REQUIRES_REVIEW


class TestCategorySuperCap:
    def test_data_breach_super_cap_is_captured_distinctly_from_general_cap(self):
        text = (
            "12. Limitation of Liability. Except as set forth below, in no event shall either "
            "party's aggregate liability exceed 1 times the total annual fees paid. Notwithstanding "
            "the foregoing, in the event of a data breach, liability shall not exceed 2 times the "
            "total annual fees paid."
        )
        d = evaluate(text)
        # General cap (1x) should still resolve cleanly — the data-breach
        # mention has its own super-cap value and must not be treated as a
        # second conflicting general cap.
        assert d.state == lpe.ACCEPT
        db = next(t for t in d.category_treatments if t["category"] == "data_breach")
        assert db["treatment"] == "super_cap"
        assert "2x" in db["cap_summary"]

    def test_ip_infringement_carved_out_uncapped_satisfies_required_exception(self):
        text = (
            "12. Limitation of Liability. In no event shall either party's aggregate liability "
            "exceed 1 times the total annual fees paid, except that the foregoing limitation shall "
            "not apply to claims arising from intellectual property infringement."
        )
        d = evaluate(text, required_exceptions_json=["ip_infringement"])
        assert d.state == lpe.ACCEPT
        ip = next(t for t in d.category_treatments if t["category"] == "ip_infringement")
        assert ip["treatment"] == "uncapped"

    def test_missing_required_exception_downgrades_to_negotiate(self):
        text = (
            "12. Limitation of Liability. In no event shall either party's aggregate liability "
            "exceed 1 times the total annual fees paid."
        )
        d = evaluate(text, required_exceptions_json=["fraud"])
        assert d.state == lpe.NEGOTIATE
        assert "fraud" in d.required_action

    def test_ambiguous_category_carveout_requires_review_instead_of_assuming_missing(self):
        # "notwithstanding" signals a carve-out is being attempted, but no
        # exclusion phrase or distinct cap value is present nearby — the
        # engine must not silently treat this as "no fraud exception."
        text = (
            "12. Limitation of Liability. In no event shall either party's aggregate liability "
            "exceed 1 times the total annual fees paid, notwithstanding fraud by either party under "
            "applicable law and subject to the foregoing."
        )
        d = evaluate(text, required_exceptions_json=["fraud"])
        assert d.state == lpe.REQUIRES_REVIEW
        assert any("fraud" in f for f in d.unresolved_facts)


class TestCommonExceptPhrasing:
    def test_except_for_breaches_of_x_satisfies_required_exception(self):
        # "except for breaches of X" is the single most common real-world
        # way carve-outs are drafted — must be recognized, not just the
        # more formal "shall not apply to" / "excluded from" phrasing.
        text = (
            "12. Limitation of Liability. In no event shall either party's aggregate liability "
            "exceed 2 times the total fees paid in the twelve (12) months preceding the claim, "
            "except for breaches of fraud."
        )
        d = evaluate(text, required_exceptions_json=["fraud"])
        assert d.state == lpe.ACCEPT_WITH_NOTE
        fraud = next(t for t in d.category_treatments if t["category"] == "fraud")
        assert fraud["treatment"] == "uncapped"


class TestIndemnificationCarveOut:
    def test_indemnification_excluded_from_cap_is_captured(self):
        text = (
            "12. Limitation of Liability. In no event shall either party's aggregate liability "
            "exceed 1 times the total annual fees paid. The foregoing limitation shall not apply to "
            "a party's indemnification obligations under this Agreement."
        )
        d = evaluate(text)
        indem = next(t for t in d.category_treatments if t["category"] == "indemnification")
        assert indem["treatment"] == "uncapped"

    def test_category_not_mentioned_is_confidently_not_addressed(self):
        text = (
            "12. Limitation of Liability. In no event shall either party's aggregate liability "
            "exceed 1 times the total annual fees paid."
        )
        d = evaluate(text)
        indem = next(t for t in d.category_treatments if t["category"] == "indemnification")
        assert indem["treatment"] == "not_addressed"
        assert indem["established"] is True


class TestGarbledLanguage:
    def test_unparseable_clause_degrades_to_must_redline_not_a_wrong_number(self):
        text = (
            "12. Limitation of Liability. The provisions hereof relating to liability, as further "
            "elaborated in Schedule C and subject to the parties' mutual agreement from time to "
            "time, shall govern."
        )
        d = evaluate(text)
        assert d.state in (lpe.MUST_REDLINE, lpe.REQUIRES_REVIEW)
        assert d.state != lpe.ACCEPT


class TestEvidenceIsTraceable:
    def test_explanation_quotes_the_actual_contract_language(self):
        text = (
            "12. Limitation of Liability. In no event shall either party's aggregate liability "
            "exceed 2 times the total fees paid in the twelve (12) months preceding the claim."
        )
        d = evaluate(text)
        assert "2" in d.explanation
        assert d.source == "Test Playbook v1"
        assert d.rule_id == "POLICY_LOL_CAP"

    def test_render_evidence_report_includes_controlling_provision_and_result(self):
        text = (
            "12. Limitation of Liability. In no event shall either party's aggregate liability "
            "exceed 5 times the total annual fees paid."
        )
        d = evaluate(text)
        report = d.render_evidence_report()
        assert "Section 12" in report
        assert "ESCALATE" in report
        assert "5x annual fees" in report


# ---------------------------------------------------------------------------
# Priority 1 — document-wide provision discovery (no fixed-window blindness)
# ---------------------------------------------------------------------------

class TestDocumentWideProvisionDiscovery:
    def test_amendment_beyond_old_3000_char_window_is_found_and_controls(self):
        # This is the exact failure the benchmark's window_boundary cases
        # were built to catch: a superseding cap placed well past the old
        # fixed extraction window must still be found and must control,
        # not be silently ignored in favor of the stale original.
        filler = " Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 60
        text = (
            "12. Limitation of Liability. In no event shall aggregate liability exceed 1 times "
            "the total annual fees paid." + filler + " First Amendment to Agreement: Section 12 "
            "(Limitation of Liability) is hereby amended and restated to provide that aggregate "
            "liability shall not exceed 6 times the total annual fees paid, superseding the "
            "original Section 12 in its entirety."
        )
        assert len(text) > 3000  # confirms this genuinely exceeds the old fixed window
        d = evaluate(text)
        assert d.state == lpe.ESCALATE  # 6x > negotiate_max(3) — the amendment's value, not the stale 1x
        assert "6" in d.explanation
        assert d.reconciliation == "amendment_resolved"

    def test_two_unreconciled_provisions_require_review_not_first_pick(self):
        # Anchors close enough together to fall in one extraction window
        # are deduped into a single provision (see _ANCHOR_DEDUP_GAP) and
        # the conflict is caught by the intra-provision ambiguity check
        # instead — either path is correct as long as the two different
        # values (1x vs. 5x) never resolve to a silent ACCEPT.
        filler = " Various other terms of this Agreement are set forth below and are not material " * 15
        text = (
            "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
            "annual fees paid." + filler + " Exhibit F. Limitation of Liability (Professional "
            "Services). Liability under this Exhibit shall not exceed 5 times the fees paid for "
            "Professional Services."
        )
        d = evaluate(text)
        assert d.state == lpe.REQUIRES_REVIEW
        assert d.reconciliation == "unreconciled"
        assert d.state not in (lpe.ACCEPT, lpe.ACCEPT_WITH_NOTE)

    def test_consistent_duplicate_mentions_resolve_cleanly(self):
        text = (
            "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
            "annual fees paid. Exhibit A confirms that the Limitation of Liability cap set forth "
            "in Section 12 (1 times the total annual fees paid) applies to all Order Forms."
        )
        d = evaluate(text)
        assert d.state == lpe.ACCEPT
        assert d.reconciliation in ("consistent_duplicate", "single")


# ---------------------------------------------------------------------------
# Priority 2 — typed compound cap structures
# ---------------------------------------------------------------------------

class TestTypedCapExpressions:
    def test_greater_of_mixed_multiplier_and_fixed_requires_review(self):
        text = (
            "12. Limitation of Liability. Aggregate liability shall not exceed the greater of "
            "$1,000,000 or 2 times the total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == lpe.REQUIRES_REVIEW
        assert "greater of" in d.unresolved_facts[0] or "greater" in " ".join(d.unresolved_facts)

    def test_lesser_of_mixed_multiplier_and_fixed_requires_review(self):
        text = (
            "12. Limitation of Liability. Aggregate liability shall not exceed the lesser of "
            "$1,000,000 or 2 times the total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == lpe.REQUIRES_REVIEW

    def test_greater_of_two_multipliers_resolves_to_the_larger(self):
        # Same basis on both sides — this one CAN be resolved deterministically.
        text = (
            "12. Limitation of Liability. Aggregate liability shall not exceed the greater of "
            "1 times the total annual fees paid or 2 times the total annual fees paid."
        )
        facts = lpe.extract_liability_facts(text)
        cap, reason = facts.controlling_provision.general_cap_expression.effective_cap()
        assert reason is None
        assert cap.kind == "fee_multiplier"
        assert cap.multiplier == 2.0

    def test_lesser_of_two_multipliers_resolves_to_the_smaller(self):
        text = (
            "12. Limitation of Liability. Aggregate liability shall not exceed the lesser of "
            "1 times the total annual fees paid or 2 times the total annual fees paid."
        )
        facts = lpe.extract_liability_facts(text)
        cap, reason = facts.controlling_provision.general_cap_expression.effective_cap()
        assert reason is None
        assert cap.multiplier == 1.0


# ---------------------------------------------------------------------------
# Priority 3 — directional / asymmetric positions
# ---------------------------------------------------------------------------

class TestDirectionalPositions:
    def test_mutual_policy_with_asymmetric_contract_requires_review(self):
        text = (
            "12. Limitation of Liability. Customer's aggregate liability shall not exceed 1 times "
            "the fees paid. Vendor's aggregate liability shall not exceed 3 times the fees paid."
        )
        d = evaluate(text, contract_side="mutual")
        assert d.state == lpe.REQUIRES_REVIEW

    def test_sell_side_policy_evaluates_our_position_not_counterpartys(self):
        text = (
            "12. Limitation of Liability. Customer's aggregate liability shall not exceed 2 times "
            "the fees paid. Vendor's aggregate liability shall not exceed 5 times the fees paid."
        )
        # We are the Vendor (sell_side) — our exposure is 5x, which must
        # drive the decision, not Customer's 2x.
        d = evaluate(text, contract_side="sell_side")
        assert d.state == lpe.ESCALATE  # 5x > negotiate_max(3)
        assert d.our_position["role"] == "Vendor"
        assert d.counterparty_position["role"] == "Customer"

    def test_buy_side_policy_evaluates_our_position_not_counterpartys(self):
        text = (
            "12. Limitation of Liability. Customer's aggregate liability shall not exceed 1 times "
            "the fees paid. Vendor's aggregate liability shall not exceed 5 times the fees paid."
        )
        # We are the Customer (buy_side) — our exposure is 1x, must ACCEPT,
        # regardless of the Vendor's much larger 5x figure.
        d = evaluate(text, contract_side="buy_side")
        assert d.state == lpe.ACCEPT
        assert d.our_position["role"] == "Customer"

    def test_unmappable_roles_never_silently_evaluate_only_one_side(self):
        text = (
            "12. Limitation of Liability. Acme's aggregate liability shall not exceed 1 times the "
            "fees paid. Globex's aggregate liability shall not exceed 5 times the fees paid."
        )
        # Neither "Acme" nor "Globex" is a recognized buy/sell-side role
        # word — the engine must not guess which one is "us".
        d = evaluate(text, contract_side="sell_side")
        assert d.state == lpe.REQUIRES_REVIEW
        assert d.state not in (lpe.ACCEPT, lpe.ACCEPT_WITH_NOTE)


# ---------------------------------------------------------------------------
# Priority 5 — consequential damages as real, consumed policy inputs
# ---------------------------------------------------------------------------

class TestConsequentialDamagesPolicy:
    def test_required_exclusion_missing_downgrades_to_negotiate(self):
        text = (
            "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
            "annual fees paid."
        )
        d = evaluate(text, require_consequential_damages_exclusion=True)
        assert d.state == lpe.NEGOTIATE
        assert "consequential" in d.required_action.lower()

    def test_required_exclusion_present_accepts_cleanly(self):
        text = (
            "12. Limitation of Liability. Neither party shall be liable for consequential damages. "
            "Aggregate liability shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text, require_consequential_damages_exclusion=True)
        assert d.state == lpe.ACCEPT

    def test_required_carveout_missing_from_exclusion_downgrades(self):
        text = (
            "12. Limitation of Liability. Neither party shall be liable for consequential damages. "
            "Aggregate liability shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(
            text, require_consequential_damages_exclusion=True,
            required_consequential_carveouts_json=["confidentiality"],
        )
        assert d.state == lpe.NEGOTIATE

    def test_ambiguous_consequential_language_requires_review_when_required_by_policy(self):
        text = (
            "12. Limitation of Liability. Consequential damages shall be treated in accordance "
            "with applicable law. Aggregate liability shall not exceed 1 times the total annual "
            "fees paid."
        )
        d = evaluate(text, require_consequential_damages_exclusion=True)
        assert d.state == lpe.REQUIRES_REVIEW

    def test_consequential_damages_not_required_by_policy_is_inert_as_before(self):
        text = (
            "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
            "annual fees paid."
        )
        d = evaluate(text, require_consequential_damages_exclusion=False)
        assert d.state == lpe.ACCEPT
