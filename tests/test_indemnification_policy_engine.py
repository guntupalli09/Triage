"""
Regression tests for indemnification_policy_engine.py — the second clause
adapter over policy_engine_core. Focused on the semantic-topology decisions
that are unique to indemnification (directed role pairs, reciprocal vs.
unilateral structure, exposure vs. protection resolution) rather than
re-testing what policy_engine_core.py already covers via the Liability
adapter's suite.
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


class TestNoClause:
    def test_no_indemnification_language_is_not_applicable(self):
        d = evaluate("9. Governing Law. This Agreement is governed by Delaware law.")
        assert d.state == core.NOT_APPLICABLE

    def test_negated_mention_is_not_applicable_not_a_false_clause(self):
        d = evaluate("9. Governing Law. No indemnification provision is included in this Agreement.")
        assert d.state == core.NOT_APPLICABLE


class TestDirectionalTopology:
    def test_returns_decision_object_from_shared_core(self):
        d = evaluate(
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall not exceed 1 times the total annual fees paid."
        )
        assert isinstance(d, core.PolicyDecision)
        assert d.state == core.ACCEPT

    def test_direction_is_not_collapsed_customer_indemnifies_vendor_differs(self):
        # Same trigger/monetary language, opposite direction — under a
        # sell-side policy this is the COUNTERPARTY's obligation to us
        # (protection), not our exposure, and must not evaluate the same
        # as if we made the promise.
        text = (
            "12. Indemnification. Customer shall indemnify, defend, and hold harmless Vendor from "
            "and against any third-party claims arising from Customer's gross negligence. "
            "Customer's indemnification obligations shall not exceed 10 times the total annual "
            "fees paid."
        )
        d = evaluate(text, contract_side="sell_side")
        # Customer's 10x obligation is protection FOR us (Vendor), not our
        # exposure — a wildly generous number offered TO us must not itself
        # trigger an ESCALATE as if it were our own liability.
        assert d.state in (core.ACCEPT, core.NOT_APPLICABLE) or d.our_position is None

    def test_mutual_policy_facing_directional_contract_requires_review(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text, contract_side="mutual")
        assert d.state == core.REQUIRES_REVIEW

    def test_unrecognized_party_names_never_silently_pick_a_side(self):
        text = (
            "12. Indemnification. Acme shall indemnify, defend, and hold harmless Globex from and "
            "against any third-party claims arising from Acme's gross negligence. Acme's "
            "indemnification obligations shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW
        assert d.state not in (core.ACCEPT, core.ACCEPT_WITH_NOTE)


class TestReciprocalVsUnilateral:
    def test_reciprocal_clause_applies_symmetric_terms_to_both_directions(self):
        text = (
            "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
            "party from and against any third-party claims arising from the indemnifying party's "
            "gross negligence. Each party's indemnification obligations shall not exceed 1 times "
            "the total annual fees paid."
        )
        d = evaluate(text, contract_side="sell_side")
        assert d.state == core.ACCEPT

    def test_reciprocal_resolves_the_same_regardless_of_configured_side(self):
        text = (
            "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
            "party from and against any third-party claims arising from the indemnifying party's "
            "gross negligence. Each party's indemnification obligations shall not exceed 1 times "
            "the total annual fees paid."
        )
        d_sell = evaluate(text, contract_side="sell_side")
        d_buy = evaluate(text, contract_side="buy_side")
        assert d_sell.state == d_buy.state == core.ACCEPT

    def test_two_directional_obligations_are_not_conflated_with_reciprocal(self):
        # Two DISTINCT named obligations (not "each party") with different
        # terms is asymmetric, not reciprocal — must not be treated as a
        # single symmetric promise.
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence, subject to "
            "a cap of 1 times the total annual fees paid. Customer shall indemnify, defend, and "
            "hold harmless Vendor from and against any third-party claims arising from Customer's "
            "misuse of the deliverables, subject to a cap of 8 times the total annual fees paid."
        )
        d = evaluate(text, contract_side="sell_side")
        # Our (Vendor's) exposure is the 1x obligation, not the counterparty's 8x.
        assert d.state == core.ACCEPT


class TestMonetaryTreatment:
    def test_uncapped_exposure_prohibited_by_default(self):
        d = evaluate(
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's willful misconduct. Vendor's "
            "indemnification obligations shall not be subject to any cap."
        )
        assert d.state == core.PROHIBITED

    def test_fixed_dollar_exposure_escalates_not_guessed(self):
        d = evaluate(
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
            "maximum liability under this indemnification obligation shall not exceed $500,000."
        )
        assert d.state == core.ESCALATE

    def test_no_monetary_treatment_stated_must_redline(self):
        d = evaluate(
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence."
        )
        assert d.state == core.MUST_REDLINE

    def test_cross_referenced_cap_requires_review_not_resolved_silently(self):
        d = evaluate(
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall be subject to the limitation of liability set forth "
            "in Section 14."
        )
        assert d.state == core.REQUIRES_REVIEW

    def test_conflicting_same_direction_caps_require_review(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence, subject "
            "to a cap of 1 times the total annual fees paid. 45. Amendment. Vendor shall "
            "indemnify, defend, and hold harmless Customer from and against any third-party "
            "claims arising from Vendor's gross negligence, subject to a cap of 5 times the "
            "total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == core.REQUIRES_REVIEW

    def test_duplicate_mentions_with_agreeing_caps_do_not_falsely_conflict(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence, subject "
            "to a cap of 1 times the total annual fees paid. Exhibit C. Vendor shall indemnify, "
            "defend, and hold harmless Customer from and against any third-party claims arising "
            "from Vendor's data breach, subject to a cap of 1 times the total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT


class TestTriggerCoverageAndScope:
    def test_missing_required_protection_trigger_negotiates(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text, contract_side="buy_side", required_protection_triggers_json=["ip_infringement"])
        assert d.state == core.NEGOTIATE

    def test_prohibited_exposure_trigger_negotiates(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's ordinary negligence. "
            "Vendor's indemnification obligations shall not exceed 1 times the total annual fees "
            "paid."
        )
        d = evaluate(text, prohibited_exposure_triggers_json=["negligence"])
        assert d.state == core.NEGOTIATE

    def test_first_party_scope_negotiates_when_third_party_only_required(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any claims, whether or not asserted by a third party, arising from "
            "Vendor's gross negligence. Vendor's indemnification obligations shall not exceed "
            "1 times the total annual fees paid."
        )
        d = evaluate(text, require_exposure_third_party_only=True)
        assert d.state == core.NEGOTIATE

    def test_nested_nearby_exception_does_not_bleed_across_triggers(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence or willful "
            "misconduct, except for willful misconduct arising from actions directed by Customer. "
            "Vendor's indemnification obligations shall not exceed 1 times the total annual fees "
            "paid."
        )
        facts = ie.extract_indemnification_facts(text)
        exposure, _, _ = ie._resolve_obligations_for_side(facts.obligations, "sell_side")
        assert exposure.trigger_treatments["willful_misconduct"].treatment == "excluded"
        assert exposure.trigger_treatments["gross_negligence"].treatment == "covered"


class TestDefenseAndNotice:
    def test_missing_defense_control_negotiates_when_required(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. The "
            "indemnified party shall control its own defense at Vendor's expense. Vendor's "
            "indemnification obligations shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text, require_defense_control_for_exposure=True)
        assert d.state == core.NEGOTIATE

    def test_missing_notice_and_cooperation_negotiates_when_required(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text, require_notice_and_cooperation_for_exposure=True)
        assert d.state == core.NEGOTIATE


class TestThirdPartyOnlyScopeSilence:
    """Phase 1 corpus expansion (scope-05) found that a required-third-
    party-only policy was silently satisfied by scope that was never
    affirmatively stated at all — 'exposure.scope == "not_addressed"' was
    treated the same as a confirmed 'third_party_only' reading. Since the
    benchmark corpus's DEFAULT_POLICY sets require_exposure_third_party_only
    True, this affected any exposure text that never used the phrase
    'third-party claims' at all, not just texts using broadening language.
    """

    def test_unstated_scope_negotiates_when_third_party_only_is_required(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any claims arising from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text, require_exposure_third_party_only=True)
        assert d.state == core.NEGOTIATE

    def test_explicit_third_party_only_still_accepts(self):
        # Regression guard: the fix must not turn every clean case into a
        # false NEGOTIATE — an affirmatively-stated third-party-only scope
        # must still accept.
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT


class TestFirstPartySignalPhrasing:
    def test_whether_direct_or_third_party_idiom_is_recognized_as_broadening(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any claims, whether direct or third-party, arising from Vendor's gross "
            "negligence. Vendor's indemnification obligations shall not exceed 1 times the total "
            "annual fees paid."
        )
        d = evaluate(text, require_exposure_third_party_only=True)
        assert d.state == core.NEGOTIATE

    def test_claims_by_one_named_party_against_another_is_recognized_as_broadening(self):
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims, including claims by Customer against Vendor "
            "arising under this Agreement, resulting from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text, require_exposure_third_party_only=True)
        assert d.state == core.NEGOTIATE


class TestExplicitNegationDetection:
    """Phase 1 corpus expansion (no-obligation-01/02) found that a clause
    which explicitly and unambiguously states no indemnification
    obligation exists ('no party shall have any indemnification
    obligation...') still returned REQUIRES_REVIEW rather than
    NOT_APPLICABLE, because the anchor-negation guard only looks ~15
    characters immediately before an anchor match, not at an explicit
    negation stated elsewhere in the same document. A human reading these
    two sentences together has no ambiguity; this closes that gap without
    touching the local negation guard's existing (narrower, still correct)
    behavior for cases where the anchor itself is directly negated.
    """

    def test_unambiguous_document_wide_negation_is_not_applicable(self):
        text = (
            "12. Indemnification. The parties acknowledge the general concept of contractual "
            "indemnification. For the avoidance of doubt, no party shall have any indemnification "
            "obligation to the other under this Agreement."
        )
        d = evaluate(text)
        assert d.state == core.NOT_APPLICABLE

    def test_regular_clause_is_unaffected(self):
        # Regression guard: a normal, real obligation must not be swept up
        # by the new negation check.
        text = (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall not exceed 1 times the total annual fees paid."
        )
        d = evaluate(text)
        assert d.state == core.ACCEPT


class TestEvidenceProvenance:
    def test_evidence_report_uses_indemnification_specific_labels(self):
        d = evaluate(
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall not exceed 5 times the total annual fees paid."
        )
        report = d.render_evidence_report()
        assert "Indemnification treatment" in report
        assert "Section 12" in report
        assert d.state == core.ESCALATE
