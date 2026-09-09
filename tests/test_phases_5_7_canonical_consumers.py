"""Phases 5–7 + controlled SaaS golden (architecture §8) as CI assertions.

Phase 5: inspectors/extractors consume shared vocabulary + canonical facts.
Phase 6: redlines/summaries respect resolved mutuality / not_stated monetary.
Phase 7: supplemental generics do not drive risk/review counts when Active
policy owns Liability/Indemnification. UNKNOWN stays UNKNOWN.
"""
from __future__ import annotations

from clause_quality import analyze_indemnification_clause, analyze_liability_clause
from contract_facts.document_assembly import assemble_document_facts
from contract_facts.finding_authority import (
    AUTHORITY_STANDALONE,
    AUTHORITY_SUPPLEMENTAL,
    annotate_findings_authority,
    apply_authority_separation,
    actionable_findings,
)
from contract_facts.liability import MutualityStatus
from contract_facts.presence import Presence
from redline_templates import render_redline
from review_workflow import compute_progress
import indemnification_policy_engine as ipe


# Architecture §8 controlled SaaS fixture (mutual LoL + reciprocal indem + §6.3).
CONTROLLED_SAAS = """
MASTER SERVICES AGREEMENT

This Agreement is entered into by and between Provider and Customer.

1. FEES. Customer shall pay annual fees of Six Hundred Thousand Dollars ($600,000).
Invoices are payable within thirty (30) days after receipt.

5. INDEMNIFICATION
5.1 Provider Indemnity. Provider shall indemnify, defend, and hold harmless Customer from and against any third-party claims arising out of or relating to infringement of any patent, copyright, or trademark by the Services.
5.2 Customer Indemnity. Customer shall indemnify, defend, and hold harmless Provider from and against any third-party claims arising out of Customer Materials, Customer's negligence, or Customer's violation of applicable law.
5.3 Indemnification Procedure. The indemnifying party will control the defense of any claim subject to this Section 5. The indemnified party shall give prompt written notice of any claim and shall cooperate fully with the indemnifying party.

6. LIMITATION OF LIABILITY
6.1 Cap. EACH PARTY'S AGGREGATE LIABILITY UNDER THIS AGREEMENT WILL NOT EXCEED THE FEES PAID OR PAYABLE DURING THE SIX (6) MONTH PERIOD PRECEDING THE CLAIM.
6.2 Consequential Damages. NEITHER PARTY WILL BE LIABLE FOR ANY CONSEQUENTIAL, INDIRECT, SPECIAL, INCIDENTAL, OR PUNITIVE DAMAGES.
6.3 Applicability. The limitations of liability set forth in this Section 6 shall apply to claims arising under Section 5 (Indemnification).
"""


class TestControlledSaasGoldenSection8:
    """CI assertions for architecture §8 golden outcomes (not screenshots)."""

    def test_liability_fee_period_cap_and_mutuality(self):
        doc = assemble_document_facts(CONTROLLED_SAAS)
        assert doc.liability is not None
        assert doc.liability.clause_presence is Presence.PRESENT
        controlling = doc.liability.controlling
        assert controlling is not None
        assert controlling.general_cap.presence is Presence.PRESENT
        assert controlling.general_cap.value is not None
        # Fee-period months stay symbolic.
        from policy_grammar.cap_operands import FeeRelativeCap
        ops = controlling.general_cap.value.operands
        assert any(isinstance(o, FeeRelativeCap) and o.months == 6 for o in ops)
        assert controlling.mutuality.presence is Presence.PRESENT
        assert controlling.mutuality.value is MutualityStatus.MUTUAL

    def test_consequential_excluded(self):
        doc = assemble_document_facts(CONTROLLED_SAAS)
        cons = doc.liability.controlling.consequential_damages_excluded
        assert cons.presence is Presence.PRESENT
        assert cons.value is True

    def test_indemnification_family_and_cross_clause(self):
        doc = assemble_document_facts(CONTROLLED_SAAS)
        assert doc.indemnification is not None
        assert len(doc.indemnification.obligations) >= 2
        assert doc.indemnification.procedures
        link = doc.cross_clause.liability_applies_to_indemnification()
        assert link is not None
        assert link.presence is Presence.PRESENT

    def test_inspectors_consume_canonical_facts(self):
        doc = assemble_document_facts(CONTROLLED_SAAS)
        lol = analyze_liability_clause(CONTROLLED_SAAS, document_facts=doc)
        indem = analyze_indemnification_clause(CONTROLLED_SAAS, document_facts=doc)
        assert lol.applicable and indem.applicable
        by_key = {e.key: e for e in lol.elements}
        assert by_key["cap_present"].present is True
        assert by_key["mutual_application"].present is True
        assert by_key["consequential_damages_excluded"].present is True
        indem_by = {e.key: e for e in indem.elements}
        assert indem_by["ip_indemnity"].present is True
        assert indem_by["mutual_or_reciprocal"].present is True
        assert indem_by["defense_obligation"].present is True


class TestPhase5Vocabulary:
    def test_will_not_exceed_and_each_party_detected_by_inspector(self):
        text = (
            "LIMITATION OF LIABILITY. Each party's aggregate liability will not exceed "
            "the fees paid during the twelve month period."
        )
        report = analyze_liability_clause(text)
        by_key = {e.key: e for e in report.elements}
        assert by_key["cap_present"].present is True
        assert by_key["mutual_application"].present is True

    def test_patent_copyright_trademark_enum_counts_as_ip_indemnity(self):
        text = (
            "INDEMNIFICATION. Provider shall indemnify Customer from third-party claims "
            "arising out of infringement of any patent, copyright, or trademark."
        )
        report = analyze_indemnification_clause(text)
        ip = next(e for e in report.elements if e.key == "ip_indemnity")
        assert ip.present is True

    def test_will_control_defense_recognized_as_procedure(self):
        text = (
            "INDEMNIFICATION. Provider shall indemnify Customer against third-party claims. "
            "The indemnifying party will control the defense of any claim."
        )
        report = analyze_indemnification_clause(text)
        procedure = next(e for e in report.elements if e.key == "limitations_or_procedure")
        assert procedure.present is True

    def test_will_defend_recognized_as_defense_obligation(self):
        text = (
            "INDEMNIFICATION. Provider will defend and indemnify Customer against third-party claims."
        )
        report = analyze_indemnification_clause(text)
        defense = next(e for e in report.elements if e.key == "defense_obligation")
        assert defense.present is True


class TestPhase6RedlinesAndSummaries:
    def test_mutual_finding_does_not_get_make_mutual_redline(self):
        finding = {
            "rule_id": "H_ASYMMETRIC_LIABILITY_01",
            "severity": "high",
            "exact_snippet": "Each party's aggregate liability shall not exceed...",
            "clause_number": "6.1",
            "party_direction": {"mutuality_status": "mutual"},
        }
        assert render_redline(finding) is None

    def test_one_sided_finding_still_gets_mutuality_redline(self):
        finding = {
            "rule_id": "H_ASYMMETRIC_LIABILITY_01",
            "severity": "high",
            "exact_snippet": "Supplier's aggregate liability shall not exceed...",
            "clause_number": "6.1",
            "party_direction": {"mutuality_status": "provider-only"},
        }
        redline = render_redline(finding)
        assert redline is not None
        assert "mutual" in redline["recommended_change"].lower()

    def test_exposure_not_stated_is_not_unspecified(self):
        mt = ipe.MonetaryTreatment(kind="not_stated")
        assert mt.summary() == "not stated"
        assert "unspecified" not in mt.summary()


class TestPhase7AuthoritySeparation:
    def test_overlap_generics_become_supplemental_when_policy_active(self):
        findings = [
            {"rule_id": "H_ASYMMETRIC_LIABILITY_01", "severity": "high", "finding_type": "rule"},
            {"rule_id": "H_INDEM_ONEWAY_01", "severity": "high", "finding_type": "rule"},
            {"rule_id": "H_GOVLAW_01", "severity": "medium", "finding_type": "rule"},
            {
                "rule_id": "POLICY_LOL",
                "severity": "low",
                "finding_type": "policy_decision",
                "clause_type": "limitation_of_liability",
            },
        ]
        policy_decisions = {
            "limitation_of_liability": {"state": "ACCEPT"},
            "indemnification": {"state": "ACCEPT"},
        }
        annotated = annotate_findings_authority(findings, policy_decisions)
        by_id = {f["rule_id"]: f["authority_layer"] for f in annotated}
        assert by_id["H_ASYMMETRIC_LIABILITY_01"] == AUTHORITY_SUPPLEMENTAL
        assert by_id["H_INDEM_ONEWAY_01"] == AUTHORITY_SUPPLEMENTAL
        assert by_id["H_GOVLAW_01"] == AUTHORITY_STANDALONE
        assert by_id["POLICY_LOL"] == "authoritative"

    def test_review_progress_excludes_supplemental(self):
        findings = [
            {
                "rule_id": "H_ASYMMETRIC_LIABILITY_01",
                "severity": "high",
                "finding_type": "rule",
                "authority_layer": AUTHORITY_SUPPLEMENTAL,
                "start_index": 0,
            },
            {
                "rule_id": "H_GOVLAW_01",
                "severity": "medium",
                "finding_type": "rule",
                "authority_layer": AUTHORITY_STANDALONE,
                "start_index": 10,
            },
        ]
        progress = compute_progress(findings, {})
        assert progress.total == 1
        assert progress.first_unresolved_key is not None

    def test_apply_authority_separation_clears_supplemental_mutuality_redline(self):
        findings = [
            {
                "rule_id": "H_ASYMMETRIC_LIABILITY_01",
                "severity": "high",
                "finding_type": "rule",
                "exact_snippet": "x",
                "party_direction": {"mutuality_status": "provider-only"},
                "redline": {"recommended_change": "Make mutual"},
            },
        ]
        policy_decisions = {"limitation_of_liability": {"state": "ACCEPT"}}
        result = apply_authority_separation(findings, policy_decisions)
        assert result["findings"][0]["authority_layer"] == AUTHORITY_SUPPLEMENTAL
        assert result["findings"][0]["redline"] is None
        assert result["supplemental_count"] == 1
        assert len(actionable_findings(result["findings"])) == 0

    def test_unknown_policy_does_not_suppress_generics(self):
        findings = [
            {"rule_id": "H_LOL_01", "severity": "high", "finding_type": "rule"},
        ]
        # No Active policy decisions → standalone, full weight.
        annotated = annotate_findings_authority(findings, None)
        assert annotated[0]["authority_layer"] == AUTHORITY_STANDALONE
