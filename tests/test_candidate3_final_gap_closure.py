"""Candidate 3 final gap-closure mission: fresh, dev-only adversarial
tests for Root Causes A (operative-context adjudication), B (dependency
completeness / cross-reference & definition detection), and C (clean-
state stability for ip_ownership's passive-voice ownership regex +
category-attribution heuristic).

Every case text here is freshly written for this mission -- none reuse
the exact burned-corpus phrasing from
artifacts/candidate3_real_ai_adversarial/corpus/cases.py. They exercise
the same STRUCTURAL FAILURE CLASSES the burned corpus exposed, not the
literal sentences, per Section 3 of the final gap-closure mission.
"""
import policy_engine_core as pec
import ip_ownership_policy_engine as ipe
import insurance_policy_engine as ine
import data_security_policy_engine as dse
import sla_policy_engine as slae
import sys
sys.path.insert(0, "artifacts/candidate2_remediation/corpus_replay")
from replay_candidate2 import _IPOwnershipPolicy, _InsurancePolicy, _DataSecurityPolicy, _SLAPolicy  # noqa: E402


# ---------------------------------------------------------------------
# Root Cause A -- operative-context adjudication
# ---------------------------------------------------------------------

class TestOperativeContextClassification:
    def _classify(self, text, needle):
        idx = text.find(needle)
        assert idx != -1, f"fixture bug: {needle!r} not found in {text!r}"
        return pec.classify_operative_context(text, idx, idx + len(needle))

    def test_generic_subject_industry_commentary_is_non_operative(self):
        # Fresh LEE2-class descriptive case (generic subject "consulting
        # agreements", not "this Agreement" / a named party).
        text = ("Background. Consulting agreements in this sector commonly cap "
                "indemnification exposure at two times the total contract value.")
        state = self._classify(text, "two times the total contract value")
        assert state == pec.NON_OPERATIVE_CONFIRMED

    def test_hypothetical_conditional_illustration_is_non_operative(self):
        # Fresh LEE3-class hypothetical case, no quote marks at all.
        text = ("For example, if a licensor were to grant a perpetual license, a "
                "one-time fee of $50,000 would be typical for a deal of this size.")
        state = self._classify(text, "$50,000")
        assert state == pec.NON_OPERATIVE_CONFIRMED

    def test_direct_negation_of_the_matched_obligation_is_non_operative(self):
        # Fresh NEGATED-class case: the match itself is inside a clause
        # that negates the very duty being described.
        text = ("12. Termination Assistance. Vendor shall have no obligation to "
                "provide transition assistance following expiration of this Agreement.")
        state = self._classify(text, "transition assistance")
        assert state == pec.NON_OPERATIVE_CONFIRMED

    def test_attached_for_reference_only_not_incorporated_is_non_operative(self):
        # Fresh LEE5-class quoted-external-template case.
        text = ("Customer's standard security policy (attached for reference only, "
                "not incorporated) requires annual penetration testing.")
        state = self._classify(text, "annual penetration testing")
        assert state == pec.NON_OPERATIVE_CONFIRMED

    def test_industry_lead_in_with_real_party_obligation_stays_operative(self):
        # Anti-over-suppression control: a genuinely operative clause that
        # merely opens with an industry-norm lead-in before naming a real
        # party obligation must NOT be suppressed.
        text = ("Consistent with standard market practice, Vendor shall carry "
                "$2,000,000 in Cyber Liability insurance throughout the Term.")
        state = self._classify(text, "$2,000,000")
        assert state == pec.OPERATIVE_CONFIRMED

    def test_industry_norm_plus_real_obligation_is_conflicting_not_silently_resolved(self):
        # A genuinely ambiguous combination (both signals fire on the
        # same match) must surface as CONFLICTING_CONTEXT, not be folded
        # silently into either confirmed state.
        text = ("It is common practice for a vendor to carry Cyber Liability "
                "insurance, and Vendor shall maintain $1,000,000 in coverage "
                "under this policy.")
        state = self._classify(text, "$1,000,000")
        assert state == pec.CONFLICTING_CONTEXT

    def test_plain_operative_clause_unaffected(self):
        # Regression control: a plain, unambiguous operative clause with
        # none of the new signals must remain OPERATIVE_CONFIRMED.
        text = "9. Insurance. Vendor shall maintain Commercial General Liability insurance of $1,000,000 per occurrence."
        state = self._classify(text, "$1,000,000")
        assert state == pec.OPERATIVE_CONFIRMED


# ---------------------------------------------------------------------
# Root Cause B -- dependency completeness / reference detection
# ---------------------------------------------------------------------

class TestDependencyCompletenessDetection:
    def test_directly_named_exhibit_without_the_is_detected(self):
        # Fresh case: insurance cross-reference to a directly-named
        # exhibit, no "the".
        text = "10. Insurance. Required coverage limits are as set forth in Exhibit F (Coverage Schedule)."
        facts = ine.extract_insurance_facts(text)
        pol = _InsurancePolicy(contract_side="sell_side")
        dec = ine.evaluate_insurance_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_directly_named_schedule_ip_ownership_without_the(self):
        text = "11. Intellectual Property. Allocation of derivative work rights is as set forth in Schedule K (Rights Matrix)."
        facts = ipe.extract_ip_facts(text)
        pol = _IPOwnershipPolicy(contract_side="sell_side")
        dec = ipe.evaluate_ip_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_data_processing_addendum_vocabulary_detected(self):
        # Fresh case: "Addendum" instead of "Agreement" for the DPA
        # cross-reference vocabulary gap.
        text = "12. Data Protection. Sub-processor obligations are as set forth in the Data Processing Addendum attached as Annex 2."
        facts = dse.extract_data_security_facts(text)
        pol = _DataSecurityPolicy(contract_side="sell_side")
        dec = dse.evaluate_data_security_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_external_definition_not_attached_insurance(self):
        text = ("10. Insurance. Vendor shall maintain the 'Minimum Coverage Package.' "
                "That term is defined in the Vendor Master Agreement, which is not attached here.")
        facts = ine.extract_insurance_facts(text)
        pol = _InsurancePolicy(contract_side="sell_side")
        dec = ine.evaluate_insurance_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_external_definition_not_attached_sla(self):
        text = ("14. Service Level. Vendor shall meet the 'Committed Uptime Target' as "
                "defined in the Service Schedule, which is not attached.")
        facts = slae.extract_sla_facts(text)
        pol = _SLAPolicy(contract_side="sell_side")
        dec = slae.evaluate_sla_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_external_definition_scoping_an_already_established_fact_ip_ownership(self):
        # Distinct shape: ownership itself IS established, but a named
        # term used inside that same statement is externally defined and
        # explicitly not attached -- must still surface, not be
        # swallowed by the already-established ownership fact.
        text = ("11. Intellectual Property. Customer shall own all 'Deliverable Materials.' "
                "That term is defined in the Order Form, which is not attached.")
        facts = ipe.extract_ip_facts(text)
        assert facts.definition_dependency_unresolved is True
        pol = _IPOwnershipPolicy(contract_side="sell_side")
        dec = ipe.evaluate_ip_policy(facts, pol)
        assert dec.state == "REQUIRES_REVIEW"

    def test_regression_directly_named_exhibit_with_the_still_detected(self):
        # The pre-existing "the Schedule/Exhibit" phrasing must still work.
        text = "10. Insurance. Required coverage limits are as set forth in the attached Schedule B."
        facts = ine.extract_insurance_facts(text)
        assert facts.schedule_cross_reference is True


# ---------------------------------------------------------------------
# Root Cause C -- clean-state stability (ip_ownership passive-voice /
# category-attribution interaction)
# ---------------------------------------------------------------------

class TestCleanStateStabilityOwnershipAttribution:
    def test_adverb_between_owned_and_by_is_now_deterministically_established(self):
        # The exact structural shape of the burned-corpus ip_ownership-080
        # finding (freshly worded): an adverb sits between "owned" and
        # "by", which previously made deterministic establishment
        # entirely dependent on AI success/failure across runs.
        text = ("12. Intellectual Property. All work product produced by Contractor "
                "under this engagement shall be owned exclusively by Client upon acceptance.")
        facts = ipe.extract_ip_facts(text)
        assert facts.ownership_attributions.get("work_product", {}).get("Client") is True

    def test_solely_variant_also_matches(self):
        text = "12. Intellectual Property. All custom work product written for Client shall be owned solely by Client."
        facts = ipe.extract_ip_facts(text)
        assert facts.ownership_attributions.get("work_product", {}).get("Client") is True

    def test_no_adverb_variant_still_matches(self):
        text = "12. Intellectual Property. All custom work product written for Client shall be owned by Client."
        facts = ipe.extract_ip_facts(text)
        assert facts.ownership_attributions.get("work_product", {}).get("Client") is True

    def test_subordinate_qualifier_does_not_hijack_category_attribution(self):
        # Fresh variant of the conflict-02 shape that the first attempted
        # fix regressed: a subordinate "including X" clause naming a
        # DIFFERENT category than the sentence's real subject must not
        # win the nearest-keyword search.
        text = ("12. Intellectual Property. All Work Product Deliverables, including any background "
                "technology embodied therein, shall be owned exclusively by Customer.")
        facts = ipe.extract_ip_facts(text)
        # The governing subject is "Deliverables" (work product), not the
        # subordinate "background technology" mention.
        assert facts.ownership_attributions.get("work_product", {}).get("Customer") is True
        assert "background_ip" not in facts.ownership_attributions

    def test_repeatability_five_identical_runs_same_decision(self):
        # Direct proxy for the real-provider repeatability requirement:
        # since deterministic establishment now always succeeds for this
        # phrasing, five independent extraction+evaluation runs on the
        # identical text must produce the identical decision every time,
        # with zero dependence on AI discovery outcome.
        text = ("12. Intellectual Property. All work product produced by Contractor "
                "under this engagement shall be owned exclusively by Client upon acceptance.")
        pol = _IPOwnershipPolicy(contract_side="sell_side")
        decisions = set()
        for _ in range(5):
            facts = ipe.extract_ip_facts(text)
            dec = ipe.evaluate_ip_policy(facts, pol)
            decisions.add(dec.state)
        assert len(decisions) == 1
