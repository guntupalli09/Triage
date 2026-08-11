"""
Regression tests for governing_law_policy_engine.py — Batch A adapter 3
of 3. The structurally simplest and most different shape of the four
adapters built so far: a categorical jurisdiction lookup with no
directionality at all, not a directed obligation/right/restriction graph.
"""
from dataclasses import dataclass
from typing import List, Optional

import governing_law_policy_engine as ge
import policy_engine_core as core


@dataclass
class FakePolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = "Legal Director"
    fallback_text: Optional[str] = "Approved fallback: Delaware governing law, binding arbitration."
    preferred_jurisdictions_json: Optional[List[str]] = None
    acceptable_jurisdictions_json: Optional[List[str]] = None
    prohibited_jurisdictions_json: Optional[List[str]] = None
    required_dispute_resolution: Optional[str] = None
    require_jury_trial_waiver: bool = False


def evaluate(text: str, **policy_kwargs) -> core.PolicyDecision:
    policy = FakePolicy(**policy_kwargs)
    facts = ge.extract_governing_law_facts(text)
    return ge.evaluate_governing_law_policy(facts, policy, source="Test Playbook v1")


class TestNoClause:
    def test_no_governing_law_language_is_not_applicable(self):
        d = evaluate("8. Confidentiality. Each party shall protect the other's information.")
        assert d.state == core.NOT_APPLICABLE


class TestJurisdictionClassification:
    def test_preferred_jurisdiction_accepts(self):
        text = "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware."
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"])
        assert d.state == core.ACCEPT

    def test_acceptable_jurisdiction_accepts_with_note(self):
        text = "20. Governing Law. This Agreement shall be governed by the laws of the State of New York."
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"], acceptable_jurisdictions_json=["New York"])
        assert d.state == core.ACCEPT_WITH_NOTE

    def test_prohibited_jurisdiction_prohibited(self):
        text = "20. Governing Law. This Agreement shall be governed by the laws of the State of California."
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"], prohibited_jurisdictions_json=["California"])
        assert d.state == core.PROHIBITED

    def test_unlisted_jurisdiction_negotiates(self):
        text = "20. Governing Law. This Agreement shall be governed by the laws of the State of Texas."
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"], prohibited_jurisdictions_json=["California"])
        assert d.state == core.NEGOTIATE

    def test_no_jurisdiction_configured_still_deterministic(self):
        # No preferred/acceptable/prohibited lists at all — an unlisted
        # jurisdiction with an empty policy is NEGOTIATE, not a crash.
        text = "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware."
        d = evaluate(text)
        assert d.state == core.NEGOTIATE


class TestNoDirectionality:
    def test_result_is_identical_regardless_of_contract_side(self):
        text = "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware."
        d_sell = evaluate(text, contract_side="sell_side", preferred_jurisdictions_json=["Delaware"])
        d_buy = evaluate(text, contract_side="buy_side", preferred_jurisdictions_json=["Delaware"])
        assert d_sell.state == d_buy.state == core.ACCEPT


class TestDisputeResolution:
    def test_required_arbitration_present_accepts(self):
        text = (
            "20. Governing Law. This Agreement shall be governed by the laws of the State of "
            "Delaware. Any dispute arising under this Agreement shall be resolved by binding "
            "arbitration."
        )
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"], required_dispute_resolution="arbitration")
        assert d.state == core.ACCEPT

    def test_required_arbitration_missing_negotiates(self):
        text = (
            "20. Governing Law. This Agreement shall be governed by the laws of the State of "
            "Delaware. The parties submit to the exclusive jurisdiction of the state and "
            "federal courts located in Wilmington, Delaware."
        )
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"], required_dispute_resolution="arbitration")
        assert d.state == core.NEGOTIATE

    def test_dispute_resolution_not_stated_must_redline_when_required(self):
        text = "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware."
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"], required_dispute_resolution="arbitration")
        assert d.state == core.MUST_REDLINE

    def test_mediation_then_arbitration_satisfies_arbitration_requirement(self):
        text = (
            "20. Governing Law. This Agreement shall be governed by the laws of the State of "
            "Delaware. The parties shall first attempt to resolve any dispute through "
            "mediation, and if unresolved after 30 days, through binding arbitration."
        )
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"], required_dispute_resolution="arbitration")
        assert d.state == core.ACCEPT


class TestJuryTrialWaiver:
    def test_waiver_present_accepts_when_required(self):
        text = (
            "20. Governing Law. This Agreement shall be governed by the laws of the State of "
            "Delaware. Each party hereby waives its right to a trial by jury."
        )
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"], require_jury_trial_waiver=True)
        assert d.state == core.ACCEPT

    def test_missing_waiver_negotiates_when_required(self):
        text = "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware."
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"], require_jury_trial_waiver=True)
        assert d.state == core.NEGOTIATE

    def test_arbitration_makes_jury_waiver_moot(self):
        text = (
            "20. Governing Law. This Agreement shall be governed by the laws of the State of "
            "Delaware. Any dispute shall be resolved by binding arbitration."
        )
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"], require_jury_trial_waiver=True)
        assert d.state == core.ACCEPT


class TestMalformedAndAmbiguous:
    def test_anchor_present_but_jurisdiction_unparseable_requires_review(self):
        text = "20. Governing Law. This Agreement is governed by applicable law."
        d = evaluate(text, preferred_jurisdictions_json=["Delaware"])
        assert d.state == core.REQUIRES_REVIEW
