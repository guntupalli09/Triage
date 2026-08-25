"""Candidate 3 remediation regression family: the new PRESENT_BUT_UNRESOLVED
absence-state, added to insurance, payment_terms, ip_ownership,
data_security, warranties, and sla (see
artifacts/candidate3_remediation/CANONICAL_PRIMARY_FACT_SCHEMA.md).

For each of these 6 adapters, proves:
  1. POSITIVE CONTROL: an ordinary, deterministically-structurable clause
     is unaffected (still reaches its normal decision, real AI enabled).
  2. THE FIX: a colloquial clause with zero deterministic-anchor overlap,
     which real AI discovers/verifies/admits but whose specific value the
     adapter's own narrow regex cannot structure, now reaches
     REQUIRES_REVIEW -- never a silent ACCEPT (Root Cause 1's exact
     mechanism) and never NOT_APPLICABLE (would misreport "nothing here
     at all" despite a verified finding).
  3. DECISION SENSITIVITY: the SAME clause, phrased so the deterministic
     regex DOES match, reaches a decision other than REQUIRES_REVIEW --
     proving the fix is scoped to the admitted-but-unstructured case, not
     a blanket "always review" regression.

All fixtures use mocked provider responses (unittest.mock), following
this codebase's existing fact-admission test convention -- see
artifacts/candidate3_remediation/REAL_PROVIDER_REPEATABILITY.md for the
separate REAL-provider verification of the same mechanism.
"""
import json
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional
from unittest.mock import MagicMock, patch

import insurance_policy_engine as ine
import payment_terms_policy_engine as pte
import ip_ownership_policy_engine as ipoe
import data_security_policy_engine as dse
import warranties_policy_engine as we
import sla_policy_engine as sle

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_REPO_ROOT, "artifacts", "candidate2_remediation", "corpus_replay"))
import replay_candidate2 as _rc2  # noqa: E402  -- reuse its already-complete FakePolicy fixtures

# Each adapter's own <ADAPTER>_SEMANTIC_DISCOVERY_ENABLED module constant is
# resolved once at import time from FACT_ADMISSION_MODE/its own env var --
# setting the env var from inside a test does not retroactively flip an
# already-imported module's constant. Following this codebase's existing
# fact-admission test convention (see test_insurance_fact_admission.py),
# flip each module's flag directly for this file's duration only.


def setup_module(_):
    ine.INSURANCE_SEMANTIC_DISCOVERY_ENABLED = True
    pte.PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED = True
    ipoe.IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED = True
    dse.DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = True
    we.WARRANTIES_SEMANTIC_DISCOVERY_ENABLED = True
    sle.SLA_SEMANTIC_DISCOVERY_ENABLED = True


def teardown_module(_):
    ine.INSURANCE_SEMANTIC_DISCOVERY_ENABLED = False
    pte.PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED = False
    ipoe.IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED = False
    dse.DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = False
    we.WARRANTIES_SEMANTIC_DISCOVERY_ENABLED = False
    sle.SLA_SEMANTIC_DISCOVERY_ENABLED = False


def _fake_response(content_text: str):
    body = json.dumps({
        "choices": [{"message": {"role": "assistant", "content": content_text}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = False
    return cm


def _admitted_mock(quote: str):
    """Returns a urlopen side_effect that discovers+admits exactly `quote`
    as ESTABLISHED with no qualifiers, mimicking a real successful
    discovery+verification round trip."""
    def fake_urlopen(*args, **kwargs):
        fake_urlopen.n = getattr(fake_urlopen, "n", 0) + 1
        if fake_urlopen.n == 1:
            return _fake_response(json.dumps({"candidates": [{"quote": quote}]}))
        return _fake_response(json.dumps({
            "status": "ESTABLISHED", "evidence_quote": quote,
            "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
            "definition_term": None, "competing_reading_a": None, "competing_reading_b": None,
            "reasoning": "Operative obligation, colloquially phrased.",
        }))
    return fake_urlopen


class TestInsurancePresentButUnresolved:
    def test_positive_control_named_coverage_still_accepts(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "9. Insurance. Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = ine.extract_insurance_facts(doc)
        decision = ine.evaluate_insurance_policy(facts, _rc2._InsurancePolicy())
        assert decision.state == ine.ACCEPT

    def test_ai_admitted_unstructured_forces_review(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = ("Vendor shall maintain a risk-transfer policy with a reputable underwriter covering "
               "third-party bodily injury claims arising from its operations.")
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = ine.extract_insurance_facts(doc)
        assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"
        decision = ine.evaluate_insurance_policy(facts, _rc2._InsurancePolicy())
        assert decision.state == ine.REQUIRES_REVIEW

    def test_decision_sensitivity_same_concept_named_type_not_review(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "Vendor shall maintain Commercial General Liability insurance covering third-party bodily injury claims."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = ine.extract_insurance_facts(doc)
        decision = ine.evaluate_insurance_policy(facts, _rc2._InsurancePolicy())
        assert decision.state != ine.REQUIRES_REVIEW


BASE_PAYMENT_POLICY_KWARGS = dict(
    contract_side="sell_side", escalation_approval_authority=None, fallback_text=None,
    preferred_net_days=None, acceptable_max_net_days=None, negotiate_max_net_days=None,
    require_disputed_amounts_withholdable=False, require_setoff_rights=False, prohibit_setoff_rights=False,
    require_we_are_not_tax_responsible=False, max_late_fee_percent=None, require_price_increase_notice_days=None,
    max_price_increase_percent=None, acceptable_max_multiplier=None, maximum_late_interest_rate_percent=None,
    maximum_price_increase_percent=None, minimum_dispute_notice_days=None, minimum_price_increase_notice_days=None,
    prohibit_disputed_amount_withholding=False, prohibit_set_off=False, prohibit_unilateral_price_increase=False,
    require_counterparty_is_payor=False, require_expense_preapproval=False, require_refund_entitlement=False,
    require_tax_responsibility_counterparty=False, require_undisputed_amounts_still_payable=False,
    required_currency=None, required_payment_trigger=None,
)


class _PaymentPolicy:
    def __init__(self, **overrides):
        kwargs = dict(BASE_PAYMENT_POLICY_KWARGS)
        kwargs.update(overrides)
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestPaymentTermsPresentButUnresolved:
    def test_positive_control_net_days_still_established(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "6. Payment Terms. Customer shall pay all invoiced amounts net 30."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = pte.extract_payment_facts(doc)
        assert facts.net_days == 30

    def test_ai_admitted_unstructured_forces_review(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "Customer will settle up on Vendor's bills within a reasonable time after getting them."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = pte.extract_payment_facts(doc)
        assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"
        decision = pte.evaluate_payment_policy(facts, _PaymentPolicy())
        assert decision.state == pte.REQUIRES_REVIEW


class TestIPOwnershipPresentButUnresolved:
    def test_positive_control_named_ownership_still_established(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "11. IP. All work product created by Vendor for Customer shall be owned by Customer."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = ipoe.extract_ip_facts(doc)
        assert facts.ownership_attributions

    def test_ai_admitted_unstructured_forces_review(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "Once Customer's checks clear, anything Vendor builds specifically for this project belongs to Customer, lock, stock, and barrel."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = ipoe.extract_ip_facts(doc)
        assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"

        class _P:
            contract_side = "sell_side"
            escalation_approval_authority = None
            fallback_text = None
            require_we_retain_background_ip = False
            require_we_own_work_product = False
            require_customer_own_work_product = False
            prohibit_work_product_includes_background_ip = False
            require_exclusive_license = False
            require_license_exclusive = False
            require_royalty_free = False
            prohibit_royalty_bearing_license = False
            require_perpetual_license = False
            require_irrevocable_license = False
            prohibit_revocable_license = False
            require_sublicensable = False
            require_transferable = False
            require_worldwide_territory = False
            prohibit_derivative_works = False
            prohibit_joint_ownership = False
            require_license_for_embedded_background_ip = False
            require_purpose_limited_license = False
            require_feedback_assigned = False
            require_residual_knowledge_rights = False
            require_open_source_disclosure = False
            require_infringement_remedy_reference = False
            require_post_termination_survival = False
        decision = ipoe.evaluate_ip_policy(facts, _P())
        assert decision.state == ipoe.REQUIRES_REVIEW
        # Repeatability proof (deterministic replay of the SAME admitted
        # facts, not a new provider call): must never vary.
        for _ in range(5):
            assert ipoe.evaluate_ip_policy(facts, _P()).state == ipoe.REQUIRES_REVIEW


BASE_DS_POLICY_KWARGS = dict(
    contract_side="sell_side", escalation_approval_authority=None, fallback_text=None,
    require_processor_role=False, prohibit_unrestricted_subprocessors=False,
    require_subprocessor_notice_or_consent="not_required",
    require_scc_or_adequacy_for_transfers=False, prohibit_data_transfer=False,
    require_deletion_or_return=False, max_retention_days=None, require_audit_rights=False,
    require_named_security_certification=False, require_cooperation_obligation=False,
    require_confidentiality_of_personal_data=False, require_data_residency=False,
    require_fixed_breach_notification_period=False, require_international_transfer_safeguard=False,
    required_data_residency_regions_json=[],
    max_breach_notification_hours=None, acceptable_max_breach_notification_hours=None,
    negotiate_max_breach_notification_hours=None, preferred_breach_notification_hours=None,
)


class _DataSecurityPolicy:
    def __init__(self, **overrides):
        kwargs = dict(BASE_DS_POLICY_KWARGS)
        kwargs.update(overrides)
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestDataSecurityPresentButUnresolved:
    def test_positive_control_breach_hours_still_established(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "11. Data Protection. Vendor shall notify Customer of any personal data breach within 48 hours."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = dse.extract_data_security_facts(doc)
        assert facts.breach_notification_hours == 48

    def test_ai_admitted_unstructured_forces_review(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "If something goes wrong with personal data, Vendor will let Customer know promptly."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = dse.extract_data_security_facts(doc)
        assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"
        decision = dse.evaluate_data_security_policy(facts, _DataSecurityPolicy())
        assert decision.state == dse.REQUIRES_REVIEW


class TestWarrantiesPresentButUnresolved:
    def test_positive_control_named_warranty_still_established(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "13. Warranties. Vendor warrants that the Services will be performed in a professional and workmanlike manner."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = we.extract_warranties_facts(doc)
        assert any(cat.established for cat in facts.categories.values())

    def test_ai_admitted_unstructured_forces_review(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "Vendor's going to do this work right, the way any solid outfit in this line of business would."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = we.extract_warranties_facts(doc)
        assert facts is not None
        assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"

        class _P:
            contract_side = "sell_side"
            escalation_approval_authority = None
            fallback_text = None
        decision = we.evaluate_warranties_policy(facts, _P())
        assert decision.state == we.REQUIRES_REVIEW


class TestSLAPresentButUnresolved:
    def test_positive_control_uptime_percent_still_established(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "14. Service Level. The Service shall maintain 99.9% uptime measured monthly."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = sle.extract_sla_facts(doc)
        assert facts.uptime_percent == 99.9

    def test_ai_admitted_unstructured_forces_review(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-mock-test")
        doc = "Vendor's going to keep this thing running practically all the time, barring something unusual."
        with patch("urllib.request.urlopen", side_effect=_admitted_mock(doc)):
            facts = sle.extract_sla_facts(doc)
        assert facts is not None
        assert facts.absence_state == "PRESENT_BUT_UNRESOLVED"

        class _P:
            contract_side = "sell_side"
            escalation_approval_authority = None
            fallback_text = None
        decision = sle.evaluate_sla_policy(facts, _P())
        assert decision.state == sle.REQUIRES_REVIEW
