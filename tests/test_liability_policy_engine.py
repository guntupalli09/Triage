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
import policy_engine_core as core


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


# ---------------------------------------------------------------------------
# Final hardening pass — cross-reference resolution, typed cap basis,
# per-claim/aggregate completion, anchor whitespace tolerance
# ---------------------------------------------------------------------------

class TestCrossReferenceResolution:
    def test_unresolvable_reference_requires_review_not_must_redline(self):
        text = (
            "12. Limitation of Liability. The limitation of liability applicable to this "
            "Agreement shall be as set forth in Schedule C (Liability Terms)."
        )
        d = evaluate(text)
        assert d.state == lpe.REQUIRES_REVIEW
        assert "Schedule C" in d.explanation

    def test_resolvable_reference_resolves_deterministically(self):
        text = (
            "12. Limitation of Liability. The limitation of liability applicable to this "
            "Agreement shall be as set forth in Schedule C. " + ("Filler text. " * 50)
            + "Schedule C (Liability Terms). Aggregate liability under this Schedule shall not "
            "exceed 1 times the total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == lpe.ACCEPT

    def test_multiple_conflicting_candidates_require_review_not_a_guess(self):
        text = (
            "12. Limitation of Liability. The limitation of liability applicable to this "
            "Agreement shall be as set forth in Schedule C. "
            "Schedule C (Draft, superseded). Liability shall not exceed 5 times the total "
            "annual fees paid. "
            "Schedule C (Final). Liability shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == lpe.REQUIRES_REVIEW

    def test_generic_incorporation_by_reference_with_no_named_target_requires_review(self):
        text = (
            "12. Limitation of Liability. Liability caps for each Order Form are set forth in "
            "the applicable Order Form and incorporated herein by reference."
        )
        d = evaluate(text)
        assert d.state == lpe.REQUIRES_REVIEW


class TestTypedCapBasis:
    def test_purchase_price_basis_is_not_compared_as_if_it_were_fees(self):
        text = (
            "12. Limitation of Liability. Buyer's liability under this Agreement is limited to "
            "1 times the purchase price."
        )
        facts = lpe.extract_liability_facts(text)
        cap, reason = facts.controlling_provision.general_cap_expression.effective_cap()
        assert cap.basis == lpe.BASIS_PURCHASE_PRICE
        d = evaluate(text)
        # 1x would ACCEPT under DEFAULT_POLICY if treated as fees — it must not be.
        assert d.state == lpe.REQUIRES_REVIEW
        assert "purchase price" in d.explanation.lower() or "Purchase Price" in d.explanation

    def test_contract_value_basis_is_preserved_verbatim_and_not_compared(self):
        text = (
            "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the "
            "total contract value."
        )
        d = evaluate(text)
        assert d.state == lpe.REQUIRES_REVIEW

    def test_fees_basis_still_evaluates_normally(self):
        text = (
            "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the "
            "total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == lpe.ACCEPT


class TestPerClaimAndAggregateCompletion:
    def test_differing_fixed_amount_scopes_require_review(self):
        text = (
            "12. Limitation of Liability. Each claim is subject to a cap of $100,000, subject "
            "to an aggregate cap across all claims of $500,000 in any twelve-month period."
        )
        facts = lpe.extract_liability_facts(text)
        expr = facts.controlling_provision.general_cap_expression
        assert expr.structure == "per_claim_and_aggregate"
        d = evaluate(text)
        assert d.state == lpe.REQUIRES_REVIEW


class TestAnchorWhitespaceTolerance:
    def test_repeated_whitespace_in_heading_is_tolerated(self):
        text = (
            "12.  Limitation   of   Liability.    In no event  shall  liability   exceed  2x  "
            "the  fees    paid     annually."
        )
        d = evaluate(text)
        assert d.state != lpe.NOT_APPLICABLE

    def test_unrelated_liability_language_still_does_not_match(self):
        # Guard against the whitespace tolerance broadening the anchor too
        # far — plain "liability" mentions elsewhere must not be mistaken
        # for a Limitation of Liability clause.
        text = "9. Indemnification. Each party's liability for indemnified claims shall be as set forth herein."
        d = evaluate(text)
        assert d.state == lpe.NOT_APPLICABLE


class TestRolePositionRegexCaseSensitivity:
    """_ROLE_POSITION_RE is compiled with re.I over a pattern whose role-name
    capture group is [A-Z][A-Za-z]{2,20} — Python's IGNORECASE applies to
    character classes, not just literals, so [A-Z] under re.I matches
    lowercase too. This lets common lowercase words immediately preceding
    "aggregate/maximum liability shall not exceed..." get captured as if
    they were party role names. Regression cases here demonstrate the
    actual, currently-observable effect on real corpus text (not a
    hypothetical) before any fix is applied — see benchmarks/liability_
    benchmark_report.md for the specific case whose golden output changes
    once this is fixed, and why the new output is the correct one."""

    def test_maximum_aggregate_liability_idiom_is_not_captured_as_a_role(self):
        # fixed-02's exact phrasing: "maximum" sits directly before
        # "aggregate liability shall not exceed" and gets captured as a
        # spurious role today. It's legal boilerplate, not a party name.
        text = (
            "12. Limitation of Liability. Supplier's maximum aggregate liability shall not "
            "exceed $1,000,000.00 under this Agreement."
        )
        facts = lpe.extract_liability_facts(text)
        roles = {k for p in facts.provisions for k in p.party_positions}
        assert "maximum" not in roles

    def test_per_occurrence_and_annual_are_not_captured_as_party_roles(self):
        # perclaim-04's exact phrasing: "per-occurrence liability is capped
        # at..." and "...annual liability is capped at..." spuriously
        # produce TWO fake "party" positions with different values, which
        # today incorrectly triggers directional/asymmetric-position logic
        # for a clause that has nothing to do with two different parties —
        # it's a per-claim-vs-aggregate structure. The bogus reason
        # ("contract defines asymmetric liability positions by party...")
        # pollutes unresolved_facts even though it doesn't (here) flip the
        # final state.
        text = (
            "12. Limitation of Liability. Liability shall not exceed 1.5 times the total annual "
            "fees paid. Notwithstanding the foregoing, per-occurrence liability is capped at 1 "
            "times the total annual fees paid, and annual liability is capped at 2 times the "
            "total annual fees paid."
        )
        facts = lpe.extract_liability_facts(text)
        roles = {k for p in facts.provisions for k in p.party_positions}
        assert not ({"occurrence", "annual"} & roles)

    def test_bogus_directional_reason_does_not_appear_for_a_non_party_structure(self):
        text = (
            "12. Limitation of Liability. Each claim is subject to a cap of $100,000, subject "
            "to an aggregate cap across all claims of $500,000 in any twelve-month period."
        )
        d = evaluate(text)
        assert not any("asymmetric liability positions" in f for f in d.unresolved_facts)


# ---------------------------------------------------------------------------
# Step 4A permanent regressions — TriageCounsel counsel-audit Steps 2/2B
# demonstrated three mechanically distinct ways a confidently-wrong
# structured fact could reach a clean deterministic decision with zero
# unresolved_facts. Each test below preserves the EXACT adversarial text
# that reproduced the failure and asserts the specific wrong behavior that
# must never come back, not just "the test passes."
# ---------------------------------------------------------------------------

class TestStep4ARoleReversal:
    """LOL-C-01 (Step 2). Document redefines 'Licensor'/'Licensee' opposite
    to their conventional buy/sell mapping. Before Step 4A: side_for_role()
    used only the literal word, silently picked 'Licensee' (5x) as our
    cap under contract_side=buy_side, and returned a clean ESCALATE with
    unresolved_facts == [] — even though the document's own definitions
    make Licensor (1x) the actual buy-side party."""

    def test_defined_term_reversal_no_longer_silently_escalates(self):
        text = (
            "1. Definitions. In this Agreement, 'Licensor' refers to Gamma LLC, the party "
            "purchasing and receiving a license to use the Platform, and 'Licensee' refers to "
            "Delta Inc., the party that develops and operates the Platform and grants the "
            "license.\n\n"
            "11. Limitation of Liability. Licensor's aggregate liability under this Agreement "
            "shall not exceed 1 times the annual fees paid in the preceding twelve (12) months. "
            "Licensee's aggregate liability under this Agreement shall not exceed 5 times the "
            "annual fees paid in the preceding twelve (12) months."
        )
        d = evaluate(text, contract_side="buy_side")
        # PREVIOUS WRONG BEHAVIOR being prevented: state == ESCALATE with
        # unresolved_facts == [] and our_position == {"role": "Licensee", ...}
        # (i.e. confidently treating the document-contradicted literal
        # mapping as authoritative). That combination must never recur.
        assert not (d.state == lpe.ESCALATE and d.unresolved_facts == []), (
            "role-reversal must not silently reach a clean ESCALATE — "
            f"got state={d.state} unresolved_facts={d.unresolved_facts}"
        )
        # Acceptable outcomes per Step 4A #6: either genuinely resolve the
        # side correctly (our cap becomes 1x, from Licensor) OR escalate.
        if d.state == lpe.REQUIRES_REVIEW:
            assert d.unresolved_facts, "REQUIRES_REVIEW must carry a reason"
        else:
            assert d.our_position is not None
            assert d.our_position["role"] == "Licensor", (
                "if resolved automatically, the CORRECT party-side reading (Licensor = "
                "the actual purchaser per the document's own definition) must be used, "
                f"got our_position={d.our_position}"
            )


class TestStep4ACrossReferenceConceptVerification:
    """LOL-B-01 (Step 2B). Liability clause delegates to 'Schedule C', which
    contains only an SLA service-credit cap ($10,000), not a liability
    concept. Before Step 4A: _resolve_cross_reference adopted the $10,000
    service-credit figure as the authoritative liability cap with a clean
    ESCALATE and unresolved_facts == []."""

    def test_unrelated_schedule_content_is_not_established_as_liability_cap(self):
        text = (
            "9. Limitation of Liability. Except as expressly provided herein, Provider's "
            "aggregate liability arising under this Agreement shall be as set forth in "
            "Schedule C.\n\n"
            + ("Lorem ipsum filler text separating sections. " * 20) +
            "\n\nSchedule C: Support Service Levels. Provider shall use commercially "
            "reasonable efforts to respond to Severity 1 support tickets within two (2) "
            "hours. If Provider fails to meet this response time in a given month, Provider "
            "shall issue Customer a service credit, and Provider's obligation to issue "
            "service credits under this Schedule C shall not exceed $10,000 per incident."
        )
        d = evaluate(text)
        # PREVIOUS WRONG BEHAVIOR being prevented: extracted_summary/general
        # cap silently becoming "$10,000.00 fixed" with a clean ESCALATE.
        assert "10,000" not in d.extracted_summary, (
            "an unrelated SLA service-credit figure must never be adopted as the "
            f"liability cap — extracted_summary={d.extracted_summary!r}"
        )
        assert d.state == lpe.REQUIRES_REVIEW, (
            f"a cross-reference with no liability concept nearby must escalate, got {d.state}"
        )
        assert d.unresolved_facts

    def test_genuine_liability_cross_reference_still_resolves_automatically(self):
        # Positive control: Schedule C DOES state a liability concept, so
        # this must continue to resolve automatically (not become an
        # escalation machine that punishes every cross-reference).
        text = (
            "9. Limitation of Liability. Except as expressly provided herein, Provider's "
            "aggregate liability arising under this Agreement shall be as set forth in "
            "Schedule C.\n\n"
            + ("Lorem ipsum filler text separating sections. " * 10) +
            "\n\nSchedule C: Liability. Provider's maximum aggregate liability to Customer "
            "arising under this Agreement shall not exceed $2,000,000."
        )
        d = evaluate(text)
        assert d.state != lpe.REQUIRES_REVIEW, (
            f"a genuine, concept-anchored cross-reference must not be sent to review, got "
            f"state={d.state} unresolved_facts={d.unresolved_facts}"
        )
        assert "2,000,000" in d.extracted_summary


class TestStep4ACarveOutBoundary:
    """LOL-D-01 (Step 2B). A realistic exception list naming five carve-out
    categories in one run-on sentence before the general cap. Before Step
    4A: the fixed 100-char exclusion-coverage window only covered the
    first category or two; later categories in the SAME sentence then
    misclassified the general '1x fees' cap as their own category-specific
    super_cap, which removed it from the general-cap pool entirely,
    producing a clean MUST_REDLINE ("no enforceable numeric general cap")
    with unresolved_facts == [] even though the cap plainly is stated."""

    def test_long_exception_list_does_not_swallow_the_general_cap(self):
        text = (
            "10. Limitation of Liability. Except for claims arising from a party's fraud, "
            "willful misconduct, breach of its confidentiality obligations under Section 7, "
            "gross negligence in the performance of its duties hereunder, or infringement of "
            "the other party's intellectual property rights, in no event shall either party's "
            "aggregate liability under this Agreement exceed 1 times the total annual fees "
            "paid in the twelve (12) months preceding the claim."
        )
        d = evaluate(text, required_exceptions_json=["confidentiality"])
        # PREVIOUS WRONG BEHAVIOR being prevented: MUST_REDLINE with
        # unresolved_facts == [] and an empty/missing general cap despite
        # a plainly-stated "1 times ... fees" cap in the source text.
        assert not (d.state == lpe.MUST_REDLINE and d.unresolved_facts == []), (
            "a long same-sentence exception list must not silently delete the general "
            f"cap — got state={d.state} unresolved_facts={d.unresolved_facts} "
            f"extracted_summary={d.extracted_summary!r}"
        )
        # Acceptable outcomes: correctly resolve to 1x fees (ACCEPT under
        # the default 1.0/2.0/3.0 policy), or escalate with a reason.
        if d.state == lpe.REQUIRES_REVIEW:
            assert d.unresolved_facts
        else:
            assert d.state == lpe.ACCEPT
            assert "1x" in d.extracted_summary or "1 " in d.extracted_summary

    def test_carve_out_boundary_scales_with_two_categories(self):
        text = (
            "10. Limitation of Liability. Except for claims arising from a party's fraud or "
            "gross negligence, in no event shall either party's aggregate liability under "
            "this Agreement exceed 1 times the total annual fees paid in the twelve (12) "
            "months preceding the claim."
        )
        d = evaluate(text)
        assert d.state == lpe.ACCEPT
        assert d.unresolved_facts == []

    def test_carve_out_boundary_scales_with_six_categories(self):
        text = (
            "10. Limitation of Liability. Except for claims arising from a party's fraud, "
            "willful misconduct, breach of its confidentiality obligations under Section 7, "
            "gross negligence in the performance of its duties hereunder, infringement of "
            "the other party's intellectual property rights, or indemnification obligations "
            "under Section 15, in no event shall either party's aggregate liability under "
            "this Agreement exceed 1 times the total annual fees paid in the twelve (12) "
            "months preceding the claim."
        )
        d = evaluate(text, required_exceptions_json=["confidentiality", "fraud"])
        assert not (d.state == lpe.MUST_REDLINE and d.unresolved_facts == [])

    def test_carve_out_boundary_with_semicolon_separated_list(self):
        text = (
            "10. Limitation of Liability. Except for claims arising from fraud; willful "
            "misconduct; breach of confidentiality obligations; gross negligence; or "
            "infringement of intellectual property rights, in no event shall either party's "
            "aggregate liability under this Agreement exceed 1 times the total annual fees "
            "paid in the twelve (12) months preceding the claim."
        )
        d = evaluate(text)
        assert not (d.state == lpe.MUST_REDLINE and d.unresolved_facts == [])


class TestStep4ACandidateOwnership:
    """Defense-in-depth: candidate-ownership verification must catch a
    span claimed by multiple incompatible categories INDEPENDENTLY of the
    boundary fix — i.e. this test must not merely re-exercise the same
    fix as TestStep4ACarveOutBoundary. Constructed so the exclusion
    signal's coverage boundary correctly credits every category as
    excluded (short list, well within any reasonable window), while a
    SEPARATE, later same-sentence super-cap phrase forces two categories
    to both independently claim the same numeric span as their own
    category-specific cap."""

    def test_span_claimed_by_multiple_categories_is_flagged_not_silently_dropped(self):
        text = (
            "10. Limitation of Liability. Liability for claims of fraud and liability for "
            "claims of gross negligence shall each not exceed 1 times the total annual fees "
            "paid in the twelve (12) months preceding the claim."
        )
        d = evaluate(text)
        # Both "fraud" and "gross_negligence" keywords each have the SAME
        # "1 times ... fees" cap forward of them in the same sentence, so
        # both categories claim the identical span as their own super_cap.
        # Previously: the general-cap pool silently lost that span with no
        # ownership check, producing MUST_REDLINE / unresolved_facts == [].
        assert not (d.state == lpe.MUST_REDLINE and d.unresolved_facts == []), (
            f"a span claimed by multiple categories must not silently vanish from the "
            f"general-cap pool — got state={d.state} unresolved_facts={d.unresolved_facts}"
        )


class TestStep4A1RoleDefinitionDiscovery:
    """PA-2, made consequential (Step 4A.1). Step 4A's resolve_role_side
    only recognized 'means'/'shall mean'/'refers to'/'shall refer to' as
    definitional predicates. A definition using 'shall be construed to
    mean' was silently invisible to it — in Step 4A's own adversarial
    case this didn't change the final decision because the clause was
    non-directional (a single named role, no asymmetric comparison). This
    test constructs a DIRECTIONAL clause (two named roles being compared)
    so the same discovery gap, if it still existed, would produce a wrong
    clean policy state rather than merely an untested code path."""

    def test_shall_be_construed_to_mean_reversal_is_directionally_consequential(self):
        text = (
            "1. Definitions. 'Vendor' shall be construed to mean Gamma LLC, the party "
            "purchasing and receiving the Services from Customer, and 'Customer' shall be "
            "construed to mean Delta Inc., the party that develops and provides the "
            "Services.\n\n"
            "9. Limitation of Liability. Vendor's aggregate liability under this Agreement "
            "shall not exceed 1 times the annual fees paid in the preceding twelve (12) "
            "months. Customer's aggregate liability under this Agreement shall not exceed "
            "5 times the annual fees paid in the preceding twelve (12) months."
        )
        d = evaluate(text, contract_side="buy_side")
        # PREVIOUS WRONG BEHAVIOR (if the discovery gap still existed):
        # 'shall be construed to mean' invisible to resolve_role_side ->
        # generic side_for_role("Vendor")=sell_side, side_for_role("Customer")
        # =buy_side trusted -> "our" cap (buy_side) wrongly read as
        # Customer's 5x, when the document's own definition makes Vendor
        # (1x) the actual purchaser/buy-side party.
        assert not (d.state == lpe.ESCALATE and d.unresolved_facts == []), (
            "an unrecognized definitional predicate must not let a document-contradicted "
            f"generic role mapping reach a clean decision — got state={d.state} "
            f"unresolved_facts={d.unresolved_facts}"
        )
        if d.state == lpe.REQUIRES_REVIEW:
            assert d.unresolved_facts
        else:
            assert d.our_position is not None and d.our_position["role"] == "Vendor", (
                f"if resolved automatically, the document-correct reading (Vendor = the "
                f"actual purchaser) must be used, got our_position={d.our_position}"
            )

    def test_is_defined_as_predicate_is_discovered(self):
        text = "'Licensee' is defined as Acme Corp, a Delaware corporation providing hosting services."
        side, reason = core.resolve_role_side("Licensee", text)
        assert reason is not None, "an 'is defined as' definition with sell-side language must conflict with Licensee's generic buy-side classification"

    def test_has_the_meaning_predicate_is_discovered(self):
        text = "'Customer' has the meaning set forth herein, being the entity that provides raw materials to Vendor."
        side, reason = core.resolve_role_side("Customer", text)
        assert reason is not None, "a 'has the meaning' definition with sell-side language must conflict with Customer's generic buy-side classification"

    def test_ordinary_definition_with_unrecognized_predicate_syntax_does_not_false_conflict(self):
        # A definition using a recognized predicate but carrying NO
        # directional evidence at all must not manufacture a conflict —
        # UNKNOWN falls back to the generic mapping, per design.
        text = "'Vendor' shall be construed to mean Acme Corp, a Delaware corporation."
        side, reason = core.resolve_role_side("Vendor", text)
        assert reason is None
        assert side == "sell_side"


class TestStep4A1LiabilityConceptOwnership:
    """XR-4 (Step 4A.1). A genuine liability cap phrased with an
    intervening relative clause ('liability arising under this
    Agreement ... exceed ...') was previously rejected by Step 4A's
    narrow _ANCHOR_RE/_SECONDARY_ANCHOR_RE-based concept check, causing
    an unnecessary escalation on language that plainly states a cap."""

    def test_liability_arising_under_this_agreement_resolves_automatically(self):
        text = (
            "9. Limitation of Liability. Provider's aggregate liability arising under this "
            "Agreement shall be as set forth in Exhibit A.\n\n"
            + ("Filler text between sections. " * 25) +
            "\n\nExhibit A: Risk Allocation. Notwithstanding anything to the contrary, in no "
            "event shall either party's liability arising under this Agreement exceed 2 "
            "times the total annual fees paid in the preceding twelve (12) months."
        )
        d = evaluate(text)
        assert d.state != lpe.REQUIRES_REVIEW, (
            f"a genuine liability cap phrased with an intervening relative clause must "
            f"resolve automatically, got state={d.state} unresolved_facts={d.unresolved_facts}"
        )
        assert "2x" in d.extracted_summary or "2 " in d.extracted_summary

    def test_service_credit_near_liability_word_is_still_rejected(self):
        # Regression guard on the disqualifying-concept check: a sentence
        # that happens to mention "liability" but is actually about
        # service credits must still be rejected — restructuring the
        # concept check must not have widened it into a permissive
        # matcher that accepts anything containing the word "liability".
        text = (
            "9. Limitation of Liability. Provider's aggregate liability shall be as set "
            "forth in Schedule C.\n\n"
            + ("Filler text between sections. " * 25) +
            "\n\nSchedule C: Support Service Levels. Without limiting Provider's liability "
            "generally, Provider's service credit obligation for missed response times "
            "shall not exceed $10,000 per incident."
        )
        d = evaluate(text)
        assert "10,000" not in d.extracted_summary
        assert d.state == lpe.REQUIRES_REVIEW
