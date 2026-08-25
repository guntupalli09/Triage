"""Zero-silent-loss mission: fresh, dev-only adversarial tests proving the
two general mechanisms fixed generalize beyond the burned-corpus phrasing
that exposed them.

Mechanism A -- an established-but-policy-unrequired material modifier
(carve-out/condition/exception) must surface in the decision, not
disappear into a bare ACCEPT.

Mechanism B -- a cross-section/cross-clause reference (a carve-out, an
additional requirement, a direct contradiction, or a self-declared
unreconciled ambiguity) elsewhere in the document must be checked, not
just the local anchor window.

None of the case texts below reuse the exact burned-corpus sentences from
artifacts/candidate3_real_ai_adversarial/corpus/cases.py.
"""
import sys
sys.path.insert(0, "artifacts/candidate2_remediation/corpus_replay")
import liability_policy_engine as lle  # noqa: E402
import insurance_policy_engine as ine  # noqa: E402
import warranties_policy_engine as we  # noqa: E402
import ip_ownership_policy_engine as ipe  # noqa: E402
import confidentiality_policy_engine as ce  # noqa: E402
import sla_policy_engine as slae  # noqa: E402
import payment_terms_policy_engine as pte  # noqa: E402
import assignment_policy_engine as ape  # noqa: E402
from replay_candidate2 import (  # noqa: E402
    _LiabilityPolicy, _InsurancePolicy, _WarrantiesPolicy, _IPOwnershipPolicy,
    _ConfidentialityPolicy, _SLAPolicy, _PaymentTermsPolicy, _AssignmentPolicy,
)


# ---------------------------------------------------------------------
# Mechanism A -- established-but-unrequired modifier surfaces, doesn't
# silently disappear into a bare ACCEPT.
# ---------------------------------------------------------------------

class TestMechanismA_MaterialModifierSurfaces:
    def test_liability_uncapped_fraud_carveout_not_required_by_policy_still_notes(self):
        text = ("12. Liability. Aggregate liability shall not exceed one times annual fees, "
                "except that this limitation does not apply to damages arising from a party's fraud.")
        facts = lle.extract_liability_facts(text)
        pol = _LiabilityPolicy(contract_side="sell_side")
        dec = lle.evaluate_liability_policy(facts, pol)
        assert dec.state == "ACCEPT_WITH_NOTE"

    def test_insurance_condition_not_gated_behind_specific_field(self):
        text = ("10. Insurance. Vendor shall carry Professional Liability insurance of $1,000,000, "
                "provided that such coverage remains commercially obtainable at standard market rates.")
        facts = ine.extract_insurance_facts(text)
        pol = _InsurancePolicy(contract_side="sell_side")
        dec = ine.evaluate_insurance_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_insurance_except_where_exception_detected(self):
        text = ("10. Insurance. Vendor shall maintain Workers' Compensation insurance as required by law, "
                "except where Vendor operates with zero employees and no such requirement applies.")
        facts = ine.extract_insurance_facts(text)
        pol = _InsurancePolicy(contract_side="sell_side")
        dec = ine.evaluate_insurance_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_warranties_condition_not_gated_behind_specific_field(self):
        text = ("13. Warranties. Contractor warrants the deliverables will match the design "
                "documents, provided that Client has not modified the design documents post-signing.")
        facts = we.extract_warranties_facts(text)
        pol = _WarrantiesPolicy(contract_side="sell_side")
        dec = we.evaluate_warranties_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_ip_ownership_same_sentence_condition_scoped_correctly(self):
        text = "12. Intellectual Property. Deliverables shall be owned by Client, provided that Client has remitted full payment."
        facts = ipe.extract_ip_facts(text)
        pol = _IPOwnershipPolicy(contract_side="sell_side")
        dec = ipe.evaluate_ip_policy(facts, pol)
        assert dec.state != "ACCEPT"
        assert facts.deterministic_condition_established is True

    def test_ip_ownership_except_for_exception_scoped_correctly(self):
        text = ("12. Intellectual Property. Deliverables shall be owned by Client, except for Contractor's "
                "internal frameworks used to build them, which Contractor keeps.")
        facts = ipe.extract_ip_facts(text)
        pol = _IPOwnershipPolicy(contract_side="sell_side")
        dec = ipe.evaluate_ip_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_ip_ownership_assign_or_fallback_idiom_not_falsely_flagged(self):
        # Regression control: the "to the extent X does not qualify..."
        # assign-or-fallback idiom (elsewhere in the SAME window as a
        # clean ownership statement) must NOT be treated as a condition
        # on that unrelated statement -- this is exactly the false
        # positive class that was found and reverted before landing the
        # sentence-scoped fix.
        text = ("14. IP. Client shall own all Deliverables. To the extent any component does not "
                "qualify as a work made for hire, Contractor hereby assigns all right, title, and "
                "interest therein to Client.")
        facts = ipe.extract_ip_facts(text)
        pol = _IPOwnershipPolicy(contract_side="sell_side")
        dec = ipe.evaluate_ip_policy(facts, pol)
        assert dec.state == "ACCEPT"


# ---------------------------------------------------------------------
# Mechanism B -- cross-section reference / self-declared ambiguity /
# document-wide contradiction must block clean.
# ---------------------------------------------------------------------

class TestMechanismB_CrossSectionAndContradiction:
    def test_confidentiality_cross_section_exclusion(self):
        text = ("9. Confidentiality. Recipient shall protect Discloser's Confidential Information "
                "for three years.\n\n17. Notwithstanding Section 9, information independently "
                "developed by Recipient without reference to the Confidential Information is excluded.")
        facts = ce.extract_confidentiality_facts(text)
        pol = _ConfidentialityPolicy(contract_side="sell_side")
        dec = ce.evaluate_confidentiality_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_sla_cross_section_additional_requirement(self):
        text = ("15. Service Level. The Platform shall maintain 99.5% availability.\n\n"
                "40. Miscellaneous. For the avoidance of doubt, availability under Section 15 "
                "excludes scheduled maintenance windows announced at least 5 days in advance.")
        facts = slae.extract_sla_facts(text)
        pol = _SLAPolicy(contract_side="sell_side")
        dec = slae.evaluate_sla_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_assignment_cross_section_survival_clause(self):
        text = ("22. Assignment. No party may assign this Agreement without written approval.\n\n"
                "51. Miscellaneous. An assignment approved under Section 22 does not relieve the "
                "assignor of accrued indemnification obligations.")
        facts = ape.extract_assignment_facts(text)
        pol = _AssignmentPolicy(contract_side="sell_side")
        dec = ape.evaluate_assignment_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_payment_terms_unreconciled_ambiguity_marker(self):
        text = ("7. Payment. Invoices are payable per the Order Form. One Order Form clause states "
                "'Net 45' and another states 'due at signing,' without indicating which governs.")
        facts = pte.extract_payment_facts(text)
        pol = _PaymentTermsPolicy(contract_side="sell_side")
        dec = pte.evaluate_payment_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_liability_document_wide_negation_of_entire_cap_section(self):
        text = ("15. Liability. Aggregate liability shall not exceed two times annual fees. "
                "15.3 For the avoidance of doubt, liability hereunder is unlimited and Section 15 shall not apply.")
        facts = lle.extract_liability_facts(text)
        pol = _LiabilityPolicy(contract_side="sell_side")
        dec = lle.evaluate_liability_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_liability_legitimate_category_carveout_not_falsely_flagged(self):
        # Regression control: "shall not apply to claims arising from X"
        # (a legitimate, category-scoped carve-out already handled by
        # category_treatments) must NOT be caught by the document-wide
        # negation detector meant for whole-section nullification.
        text = ("15. Liability. Aggregate liability shall not exceed one times annual fees, except "
                "that this limitation shall not apply to claims arising from intellectual property infringement.")
        facts = lle.extract_liability_facts(text)
        pol = _LiabilityPolicy(contract_side="sell_side", required_exceptions_json=["ip_infringement"])
        dec = lle.evaluate_liability_policy(facts, pol)
        assert dec.state == "ACCEPT"

    def test_insurance_broad_negation_of_stated_limit(self):
        text = ("10. Insurance. Vendor shall carry Cyber Liability insurance of $3,000,000. "
                "10.4 For clarity, no specific coverage amounts are required beyond statutory minimums.")
        facts = ine.extract_insurance_facts(text)
        pol = _InsurancePolicy(contract_side="sell_side")
        dec = ine.evaluate_insurance_policy(facts, pol)
        assert dec.state != "ACCEPT"

    def test_assignment_freely_assign_reversal(self):
        text = ("20. Assignment. No party may assign this Agreement without written consent. "
                "20.5 For clarity, either party may freely assign this Agreement to an affiliate without consent.")
        facts = ape.extract_assignment_facts(text)
        pol = _AssignmentPolicy(contract_side="sell_side")
        dec = ape.evaluate_assignment_policy(facts, pol)
        assert dec.state != "ACCEPT"


class TestCleanStateStabilityIPOwnership:
    def test_repeatability_five_identical_runs_owner_and_exception(self):
        text = ("12. Intellectual Property. Deliverables shall be owned by Client, except for Contractor's internal "
                "frameworks used to build them, which Contractor keeps.")
        pol = _IPOwnershipPolicy(contract_side="sell_side")
        decisions = set()
        for _ in range(5):
            facts = ipe.extract_ip_facts(text)
            dec = ipe.evaluate_ip_policy(facts, pol)
            decisions.add(dec.state)
        assert len(decisions) == 1
