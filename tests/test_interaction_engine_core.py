"""
Interaction Engine V1 — pure-function unit tests for interaction_engine_core.py
and interaction_rules.py. Builds PolicyDecision fixtures directly (never
going through an extractor) to isolate predicate-level correctness from any
adapter's own extraction behavior, per docs/architecture/
interaction_engine_v1_design.md S10.1.
"""
import pytest

import interaction_engine_core as ixc
import interaction_rules as ixr
from policy_engine_core import PolicyDecision


def mk_decision(clause_type, state, category_treatments=None, interaction_facts=None,
                 escalate_to=None, controlling_provision=None):
    return PolicyDecision(
        rule_id="X", clause_type=clause_type, state=state,
        contract_language="lang", extracted_summary="s", policy_limit_summary="p",
        required_action="a", explanation="e", negotiation_ladder=[],
        category_treatments=category_treatments or [], unresolved_facts=[],
        start_index=0, end_index=10, escalate_to=escalate_to,
        controlling_provision=controlling_provision or {
            "label": f"Section X — {clause_type}", "excerpt": "lang", "start_index": 0, "end_index": 10,
        },
        interaction_facts=interaction_facts or {},
    )


def ct(category, treatment, established=True):
    return {"category": category, "treatment": treatment, "cap_summary": None, "raw_excerpt": "x", "established": established}


# ---------------------------------------------------------------------------
# Rule 1: IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY
# ---------------------------------------------------------------------------

class TestRule1IPUncappedLiabilityWithIndemnity:
    def test_fires_when_both_conditions_met(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "NEGOTIATE", [ct("ip_infringement", "uncapped")], escalate_to="Legal Director"),
            "indemnification": mk_decision("indemnification", "NEGOTIATE", [ct("ip_infringement", "covered")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        assert r.state == "ESCALATE"
        assert r.kind == "CONFLICT"
        assert r.escalate_to == "Legal Director"

    def test_super_cap_also_fires(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "super_cap")]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        assert r.state == "ESCALATE"

    def test_does_not_fire_when_within_general_cap(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "within_general_cap")]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        assert r.state == "NOT_TRIGGERED"

    def test_does_not_fire_when_indemnification_excludes_ip(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "excluded")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        assert r.state == "NOT_TRIGGERED"

    def test_missing_participant_is_insufficient_facts_not_not_triggered(self):
        decisions = {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")])}
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        assert r.state == "INSUFFICIENT_FACTS"
        assert r.missing_clause_types == ("indemnification",)

    @pytest.mark.parametrize("unsafe_state", ["REQUIRES_REVIEW", "NOT_APPLICABLE"])
    def test_unsafe_participant_state_is_insufficient_facts(self, unsafe_state):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", unsafe_state, [ct("ip_infringement", "uncapped")]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        assert r.state == "INSUFFICIENT_FACTS"


# ---------------------------------------------------------------------------
# Rule 2: shared-category mismatch (non-IP categories)
# ---------------------------------------------------------------------------

class TestRule2SharedCategoryMismatch:
    def test_fires_and_lists_every_matching_category(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [
                ct("data_breach", "uncapped"), ct("confidentiality", "super_cap"), ct("fraud", "uncapped"),
            ]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [
                ct("data_breach", "covered"), ct("confidentiality", "covered"),
            ]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH")
        assert r.state == "ESCALATE"
        assert "data breach" in r.matched_facts["categories"]
        assert "confidentiality" in r.matched_facts["categories"]
        # "fraud" is not in the shared-category vocabulary (design doc S1.2)
        # and must never appear even though it superficially matches "uncapped".
        assert "fraud" not in r.matched_facts["categories"]

    def test_ip_infringement_alone_does_not_double_fire_rule_2(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH")
        assert r.state == "NOT_TRIGGERED"


# ---------------------------------------------------------------------------
# Rule 3: indemnity rides inside general cap (DEPENDENCY, informational)
# ---------------------------------------------------------------------------

class TestRule3IndemnityWithinGeneralCap:
    def test_fires_as_dependency_not_conflict(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_INDEMNITY_WITHIN_GENERAL_CAP")
        assert r.kind == "DEPENDENCY"
        assert r.state == "ACCEPT_WITH_NOTE"
        # ACCEPT_WITH_NOTE is never actionable -- must not surface as a
        # "needs attention" finding.
        assert r.state not in ixc.ACTIONABLE_STATES
        assert r.matched_facts["source"] == "per_category"

    def test_not_addressed_also_counts_as_within_cap(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "not_addressed")]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_INDEMNITY_WITHIN_GENERAL_CAP")
        assert r.state == "ACCEPT_WITH_NOTE"


# ---------------------------------------------------------------------------
# Rule 4: per-category ambiguity (distinct from whole-decision gating)
# ---------------------------------------------------------------------------

class TestRule4CategoryAmbiguity:
    def test_fires_on_per_category_unresolved_even_when_decision_resolved(self):
        # Both decisions are themselves ACCEPT (a resolved, safe state) --
        # the ambiguity is scoped to ONE category only, which is exactly
        # the case interaction_engine_core's whole-decision gate cannot
        # catch (see interaction_rules.py's rule 4 module docstring).
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [
                ct("ip_infringement", "unresolved"), ct("data_breach", "within_general_cap"),
            ]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "not_addressed")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY")
        assert r.state == "REQUIRES_REVIEW"
        assert "ip infringement" in r.matched_facts["categories"]

    def test_does_not_fire_when_nothing_unresolved(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY")
        assert r.state == "NOT_TRIGGERED"


# ---------------------------------------------------------------------------
# Rule 5: uncapped data-breach liability, no cyber insurance
# ---------------------------------------------------------------------------

class TestRule5UncappedLiabilityNoCyberInsurance:
    def test_fires_when_uncapped_and_no_coverage(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
            "insurance": mk_decision("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE")
        assert r.state == "ESCALATE"

    def test_does_not_fire_when_coverage_established(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
            "insurance": mk_decision("insurance", "ACCEPT", [ct("cyber_liability", "established", established=True)]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE")
        assert r.state == "NOT_TRIGGERED"

    def test_ip_infringement_category_never_maps_to_insurance(self):
        # ip_infringement has no real insurance-coverage mapping (design
        # doc S3.2) -- must never accidentally fire off this category.
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
            "insurance": mk_decision("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE")
        assert r.state == "NOT_TRIGGERED"


# ---------------------------------------------------------------------------
# Rule 6: non-payment termination vs. dispute withholding
# ---------------------------------------------------------------------------

class TestRule6NonpaymentTerminationVsWithholding:
    def test_fires_when_immediate_and_withholdable(self):
        decisions = {
            "termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "immediate")]),
            "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True, "service_credit_present": None}),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING")
        assert r.state == "ESCALATE"

    def test_does_not_fire_when_notice_and_cure(self):
        decisions = {
            "termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "notice_and_cure")]),
            "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True, "service_credit_present": None}),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING")
        assert r.state == "NOT_TRIGGERED"

    def test_does_not_fire_when_withholding_not_addressed(self):
        decisions = {
            "termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "immediate")]),
            "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": None}),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING")
        assert r.state == "NOT_TRIGGERED"

    def test_does_not_fire_when_withholding_affirmatively_false(self):
        decisions = {
            "termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "immediate")]),
            "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": False, "service_credit_present": None}),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING")
        assert r.state == "NOT_TRIGGERED"

    def test_no_non_payment_right_at_all_does_not_fire(self):
        decisions = {
            "termination": mk_decision("termination", "ACCEPT", [ct("material_breach", "notice_and_cure")]),
            "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True, "service_credit_present": None}),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING")
        assert r.state == "NOT_TRIGGERED"


# ---------------------------------------------------------------------------
# Rule 7: SLA / Payment Terms credit dependency
# ---------------------------------------------------------------------------

class TestRule7SLAPaymentCreditDependency:
    def test_fires_when_both_present(self):
        decisions = {
            "sla": mk_decision("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
            "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": True}),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_SLA_PAYMENT_CREDIT_DEPENDENCY")
        assert r.state == "REQUIRES_REVIEW"
        assert r.kind == "DEPENDENCY"

    def test_does_not_fire_when_only_one_side_present(self):
        decisions = {
            "sla": mk_decision("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
            "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": None}),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_SLA_PAYMENT_CREDIT_DEPENDENCY")
        assert r.state == "NOT_TRIGGERED"


# ---------------------------------------------------------------------------
# Generic engine mechanics
# ---------------------------------------------------------------------------

class TestEngineMechanics:
    def test_every_rule_always_produces_exactly_one_decision(self):
        decisions = {}  # nothing present at all
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        assert len(results) == len(ixr.LAUNCH_CATALOG)
        assert all(r.state == "INSUFFICIENT_FACTS" for r in results)

    def test_determinism_across_repeated_calls(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
        }
        assert ixc.check_deterministic(lambda: ixc.evaluate(decisions, ixr.LAUNCH_CATALOG))

    def test_deterministic_ordering_matches_catalog_order(self):
        decisions = {}
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        assert [r.interaction_id for r in results] == list(ixr.LAUNCH_CATALOG_IDS)

    def test_predicate_exception_is_isolated_as_evaluation_error(self):
        def _boom(decisions):
            raise ValueError("boom")

        rule = ixr.LAUNCH_CATALOG[0]
        original = rule.predicate
        rule.predicate = _boom
        try:
            decisions = {
                "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
                "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
            }
            results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
            r = next(d for d in results if d.interaction_id == rule.interaction_id)
            assert r.state == "EVALUATION_ERROR"
            # every other rule still evaluates
            others = [d for d in results if d.interaction_id != rule.interaction_id]
            assert len(others) == len(ixr.LAUNCH_CATALOG) - 1
        finally:
            rule.predicate = original

    def test_rule_registration_rejects_state_above_declared_ceiling(self):
        from interaction_engine_core import InteractionFinding, InteractionRule, CONFLICT, ESCALATE, REQUIRES_REVIEW

        def _over_ceiling(decisions):
            return InteractionFinding(state=ESCALATE, explanation="e", required_action="a")

        bad_rule = InteractionRule(
            interaction_id="IX_TEST_OVER_CEILING", label="test", kind=CONFLICT,
            ceiling_state=REQUIRES_REVIEW,  # declares a LOWER ceiling than what the predicate returns
            participating_clause_types=("limitation_of_liability", "indemnification"),
            predicate=_over_ceiling,
        )
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", []),
            "indemnification": mk_decision("indemnification", "ACCEPT", []),
        }
        with pytest.raises(ValueError, match="above its declared ceiling"):
            ixc.evaluate(decisions, [bad_rule])

    def test_rule_construction_rejects_single_participant(self):
        from interaction_engine_core import InteractionRule, CONFLICT, ESCALATE
        with pytest.raises(ValueError, match="2\\+ participating_clause_types"):
            InteractionRule(
                interaction_id="X", label="x", kind=CONFLICT, ceiling_state=ESCALATE,
                participating_clause_types=("limitation_of_liability",),
                predicate=lambda d: None,
            )

    def test_launch_catalog_has_exactly_seven_rules_with_unique_ids(self):
        assert len(ixr.LAUNCH_CATALOG) == 7
        assert len(set(ixr.LAUNCH_CATALOG_IDS)) == 7

    def test_evidence_report_includes_every_participant_and_explanation(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
            "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        report = r.render_evidence_report()
        assert "Section X — limitation_of_liability" in report
        assert "Section X — indemnification" in report
        assert "Why this matters" in report
        assert "Required action" in report
