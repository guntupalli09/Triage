"""Phase 3: Indemnification clause-family assembly."""

import indemnification_policy_engine as ipe
from contract_facts.cross_clause import CrossClauseKind
from contract_facts.indemnification_bridge import (
    assemble_indemnification_family,
    canonical_indemnification_from_legacy,
)
from contract_facts.presence import Presence
from contract_facts.procedure import DefenseControlHolder
from contract_facts.roles import ContextualRoleKind


CONTROLLED_INDEMNITY_FAMILY = """
5. INDEMNIFICATION
5.1 Provider Indemnity. Provider shall indemnify, defend, and hold harmless Customer from and against any third-party claims arising out of or relating to infringement of any patent, copyright, or trademark by the Services.
5.2 Customer Indemnity. Customer shall indemnify, defend, and hold harmless Provider from and against any third-party claims arising out of Customer Materials, Customer's negligence, or Customer's violation of applicable law.
5.3 Indemnification Procedure. The indemnifying party will control the defense of any claim subject to this Section 5. The indemnified party shall give prompt written notice of any claim and shall cooperate fully with the indemnifying party.
6. LIMITATION OF LIABILITY
6.1 Cap. EACH PARTY'S AGGREGATE LIABILITY UNDER THIS AGREEMENT WILL NOT EXCEED THE FEES PAID OR PAYABLE DURING THE SIX (6) MONTH PERIOD.
6.3 Applicability. The limitations of liability set forth in this Section 6 shall apply to claims arising under Section 5 (Indemnification).
"""


class TestDirectionalObligations:
    def test_provider_and_customer_directions_are_separate(self):
        facts = ipe.extract_indemnification_facts(CONTROLLED_INDEMNITY_FAMILY)
        assert facts is not None
        assert len(facts.obligations) == 2
        pairs = {
            (o.indemnifying_role.lower(), o.indemnified_role.lower())
            for o in facts.obligations
        }
        assert ("provider", "customer") in pairs
        assert ("customer", "provider") in pairs

    def test_triggers_do_not_bleed_across_subsections(self):
        facts = ipe.extract_indemnification_facts(CONTROLLED_INDEMNITY_FAMILY)
        by_dir = {
            (o.indemnifying_role.lower(), o.indemnified_role.lower()): o
            for o in facts.obligations
        }
        provider = by_dir[("provider", "customer")]
        customer = by_dir[("customer", "provider")]
        assert provider.trigger_treatments["ip_infringement"].treatment == "covered"
        assert provider.trigger_treatments["customer_materials"].treatment == "not_addressed"
        assert customer.trigger_treatments["customer_materials"].treatment == "covered"
        assert customer.trigger_treatments["ip_infringement"].treatment == "not_addressed"

    def test_patent_copyright_trademark_counts_as_ip_infringement(self):
        facts = ipe.extract_indemnification_facts(CONTROLLED_INDEMNITY_FAMILY)
        provider = next(o for o in facts.obligations if o.indemnifying_role.lower() == "provider")
        assert provider.trigger_treatments["ip_infringement"].treatment == "covered"


class TestSharedProcedureAttachment:
    def test_section_5_3_attaches_to_both_obligations(self):
        facts = ipe.extract_indemnification_facts(CONTROLLED_INDEMNITY_FAMILY)
        assert len(facts.shared_procedures) == 1
        proc = facts.shared_procedures[0]
        assert proc.procedure_id == "proc-5.3"
        assert proc.defense_control == "indemnifying_party"
        assert proc.notice_required is True
        assert proc.cooperation_required is True
        for o in facts.obligations:
            assert o.procedure_id == "proc-5.3"
            assert o.defense_control == "indemnifying_party"
            assert o.notice_required is True
            assert o.cooperation_required is True

    def test_will_control_defense_recognized(self):
        window = "The indemnifying party will control the defense of any claim."
        assert ipe._classify_defense_control(window) == "indemnifying_party"


class TestLiabilityLinkageSeparateFromMonetary:
    def test_subject_to_this_section_is_not_monetary_cross_reference(self):
        facts = ipe.extract_indemnification_facts(CONTROLLED_INDEMNITY_FAMILY)
        for o in facts.obligations:
            assert o.monetary.kind == "not_stated"

    def test_section_6_3_emitted_as_liability_applies_link(self):
        facts = ipe.extract_indemnification_facts(CONTROLLED_INDEMNITY_FAMILY)
        assert len(facts.liability_applies_links) == 1
        link = facts.liability_applies_links[0]
        assert link.target_section_label == "5"
        assert "apply" in link.raw_excerpt.lower()

    def test_true_monetary_cross_reference_still_requires_review(self):
        from tests.test_indemnification_policy_engine import evaluate
        import policy_engine_core as core

        d = evaluate(
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
            "indemnification obligations shall be subject to the limitation of liability set forth "
            "in Section 14."
        )
        assert d.state == core.REQUIRES_REVIEW


class TestCanonicalBridge:
    def test_assemble_family_builds_roles_procedure_and_cross_clause(self):
        facts = ipe.extract_indemnification_facts(CONTROLLED_INDEMNITY_FAMILY)
        assembled = assemble_indemnification_family(facts)
        indem = assembled["indemnification"]
        roles = assembled["roles"]
        cross = assembled["cross_clause"]

        assert indem.clause_presence is Presence.PRESENT
        assert len(indem.obligations) == 2
        assert len(indem.procedures) == 1
        proc = indem.procedure_for("proc-5.3")
        assert proc is not None
        assert proc.defense_control.is_known
        assert proc.defense_control.value.holder is DefenseControlHolder.INDEMNIFYING_PARTY

        provider = next(o for o in indem.obligations if o.indemnifying_party.lower() == "provider")
        assert provider.procedure_id == "proc-5.3"
        assert provider.trigger_coverage("ip_infringement").name == "COVERED"
        bindings = {b.kind: b.party_name for b in provider.role_bindings}
        assert bindings[ContextualRoleKind.INDEMNIFYING_PARTY] == "Provider"
        assert bindings[ContextualRoleKind.INDEMNIFIED_PARTY] == "Customer"

        assert roles.party_by_name("Provider") is not None
        assert roles.party_by_name("Customer") is not None

        link = cross.liability_applies_to_indemnification()
        assert link is not None
        assert link.kind is CrossClauseKind.LIABILITY_APPLIES_TO_INDEMNIFICATION
        assert link.target_section_label == "5"

        # Monetary on obligations is NOT_STATED — linkage lives only on cross_clause.
        for o in indem.obligations:
            assert o.monetary.is_known
            assert o.monetary.value.kind.value == "not_stated"

    def test_canonical_from_legacy_preserves_procedure_id(self):
        facts = ipe.extract_indemnification_facts(CONTROLLED_INDEMNITY_FAMILY)
        canon = canonical_indemnification_from_legacy(facts)
        assert all(o.procedure_id == "proc-5.3" for o in canon.obligations)
