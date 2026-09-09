"""Phase 4: structured ContractDocumentFacts drive Interaction Engine Rule 3.

Proves vendor indemnity inside the general cap (§6.3 / family-level) without
relying only on lossy PolicyDecision.category_treatments, and that hydration
fills empty LoL treatments from canonical facts.
"""
from __future__ import annotations

import indemnification_policy_engine as ipe
import interaction_engine_core as ixc
import interaction_enforcement as ixe
import interaction_rules as ixr
import liability_policy_engine as lpe
from contract_facts.document_assembly import (
    assemble_document_facts,
    assemble_document_facts_from_legacy,
)
from contract_facts.interaction_hydration import hydrate_decisions_from_document_facts
from contract_facts.presence import Presence
from policy_engine_core import PolicyDecision
from policy_enforcement import ClauseEvaluationOutcome
from tests.test_interaction_engine_core import ct, mk_decision


CONTROLLED_FAMILY = """
5. INDEMNIFICATION
5.1 Provider Indemnity. Provider shall indemnify, defend, and hold harmless Customer from and against any third-party claims arising out of or relating to infringement of any patent, copyright, or trademark by the Services.
5.2 Customer Indemnity. Customer shall indemnify, defend, and hold harmless Provider from and against any third-party claims arising out of Customer Materials, Customer's negligence, or Customer's violation of applicable law.
5.3 Indemnification Procedure. The indemnifying party will control the defense of any claim subject to this Section 5. The indemnified party shall give prompt written notice of any claim and shall cooperate fully with the indemnifying party.
6. LIMITATION OF LIABILITY
6.1 Cap. EACH PARTY'S AGGREGATE LIABILITY UNDER THIS AGREEMENT WILL NOT EXCEED THE FEES PAID OR PAYABLE DURING THE SIX (6) MONTH PERIOD.
6.3 Applicability. The limitations of liability set forth in this Section 6 shall apply to claims arising under Section 5 (Indemnification).
"""


class TestDocumentAssembly:
    def test_assembles_cross_clause_from_legacy_extracts(self):
        doc = assemble_document_facts_from_legacy(
            liability_facts=lpe.extract_liability_facts(CONTROLLED_FAMILY),
            indemnification_facts=ipe.extract_indemnification_facts(CONTROLLED_FAMILY),
        )
        assert doc.liability is not None
        assert doc.indemnification is not None
        link = doc.cross_clause.liability_applies_to_indemnification()
        assert link is not None
        assert link.presence is Presence.PRESENT

    def test_assemble_from_text_matches_legacy_path(self):
        from_text = assemble_document_facts(CONTROLLED_FAMILY)
        assert from_text.cross_clause.liability_applies_to_indemnification() is not None


class TestInteractionHydration:
    def test_hydrates_empty_lol_treatments_with_indemnification_within_cap(self):
        doc = assemble_document_facts(CONTROLLED_FAMILY)
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", []),
            "indemnification": mk_decision("indemnification", "ACCEPT", []),
        }
        hydrate_decisions_from_document_facts(decisions, doc)
        lol = {t["category"]: t for t in decisions["limitation_of_liability"].category_treatments}
        assert lol["indemnification"]["treatment"] == "within_general_cap"
        assert lol["indemnification"]["established"] is True
        indem = {t["category"]: t for t in decisions["indemnification"].category_treatments}
        assert indem["ip_infringement"]["treatment"] == "covered"


class TestRule3FamilyLevelVendorIndemnityInsideCap:
    def test_fires_from_document_facts_without_shared_cat_join(self):
        """Empty treatments + §6.3 graph: Rule 3 must fire after hydration."""
        doc = assemble_document_facts(CONTROLLED_FAMILY)
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", []),
            "indemnification": mk_decision("indemnification", "ACCEPT", []),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG, document_facts=doc)
        r = next(d for d in results if d.interaction_id == "IX_INDEMNITY_WITHIN_GENERAL_CAP")
        assert r.state == "ACCEPT_WITH_NOTE"
        assert r.kind == "DEPENDENCY"
        assert "ip infringement" in r.matched_facts["categories"]
        assert r.matched_facts["source"] == "family_within_general_cap"

    def test_fires_from_hydrated_indemnification_category_alone(self):
        decisions = {
            "limitation_of_liability": mk_decision(
                "limitation_of_liability", "ACCEPT",
                [ct("indemnification", "within_general_cap")],
            ),
            "indemnification": mk_decision(
                "indemnification", "ACCEPT", [ct("ip_infringement", "covered")],
            ),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_INDEMNITY_WITHIN_GENERAL_CAP")
        assert r.state == "ACCEPT_WITH_NOTE"
        assert "ip infringement" in r.matched_facts["categories"]

    def test_explicit_uncapped_carve_out_not_added_by_family_path(self):
        decisions = {
            "limitation_of_liability": mk_decision(
                "limitation_of_liability", "ACCEPT",
                [ct("ip_infringement", "uncapped"), ct("indemnification", "within_general_cap")],
            ),
            "indemnification": mk_decision(
                "indemnification", "ACCEPT", [ct("ip_infringement", "covered")],
            ),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r3 = next(d for d in results if d.interaction_id == "IX_INDEMNITY_WITHIN_GENERAL_CAP")
        # Family path must not claim IP rides inside the cap when LoL carves it uncapped.
        assert r3.state == "NOT_TRIGGERED"
        r1 = next(d for d in results if d.interaction_id == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        assert r1.state == "ESCALATE"

    def test_without_document_facts_empty_treatments_do_not_fire(self):
        decisions = {
            "limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", []),
            "indemnification": mk_decision("indemnification", "ACCEPT", []),
        }
        results = ixc.evaluate(decisions, ixr.LAUNCH_CATALOG)
        r = next(d for d in results if d.interaction_id == "IX_INDEMNITY_WITHIN_GENERAL_CAP")
        assert r.state == "NOT_TRIGGERED"


class TestEnforcementWiring:
    def test_document_facts_from_outcomes_uses_legacy_extracts(self):
        liability = lpe.extract_liability_facts(CONTROLLED_FAMILY)
        indemnity = ipe.extract_indemnification_facts(CONTROLLED_FAMILY)
        outcomes = [
            ClauseEvaluationOutcome(
                clause_type="limitation_of_liability",
                decision=mk_decision("limitation_of_liability", "ACCEPT", []),
                revision_metadata={},
                legacy_facts=liability,
            ),
            ClauseEvaluationOutcome(
                clause_type="indemnification",
                decision=mk_decision("indemnification", "ACCEPT", []),
                revision_metadata={},
                legacy_facts=indemnity,
            ),
        ]
        doc = ixe.document_facts_from_outcomes(outcomes)
        assert doc is not None
        assert doc.cross_clause.liability_applies_to_indemnification() is not None

        findings: list = []
        result = ixe.apply_interaction_rules(outcomes, findings)
        r3 = result["IX_INDEMNITY_WITHIN_GENERAL_CAP"]
        assert r3["state"] == "ACCEPT_WITH_NOTE"
        # ACCEPT_WITH_NOTE is not actionable — no interaction finding injected.
        assert not any(f.get("interaction_id") == "IX_INDEMNITY_WITHIN_GENERAL_CAP" for f in findings)
