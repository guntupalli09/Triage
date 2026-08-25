#!/usr/bin/env python3
"""CANDIDATE 1 BURNED-CORPUS REPLAY (Candidate 2 remediation mission).

Re-runs the SAME frozen, hashed 74-case corpus
(artifacts/final_frozen_validation/corpus/cases.py, imported unmodified --
never copied or edited) against Candidate 2's current code. This is
REGRESSION-ONLY evidence that the 6 previously-confirmed defects no longer
reproduce; it is explicitly NOT independent validation (the corpus was
authored with the frozen candidate's exact failures in mind and is burned
for that purpose per the mission brief). Passing this replay does NOT
authorize shipping -- only a NEW, previously-unseen corpus can.

Writes candidate2_raw_results.jsonl alongside this script (never touches
the original artifacts/final_frozen_validation/raw_results.jsonl, which
remains the immutable Mission A record).
"""
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                                 "final_frozen_validation", "corpus")))

from cases import CASES  # noqa: E402  -- the SAME frozen, hashed corpus file; not copied or modified

import policy_engine_core as core  # noqa: E402
import liability_policy_engine as lpe  # noqa: E402
import indemnification_policy_engine as ie  # noqa: E402
import confidentiality_policy_engine as cpe  # noqa: E402
import payment_terms_policy_engine as pte  # noqa: E402
import ip_ownership_policy_engine as ipoe  # noqa: E402
import insurance_policy_engine as ine  # noqa: E402
import data_security_policy_engine as dse  # noqa: E402
import governing_law_policy_engine as gpe  # noqa: E402
import termination_policy_engine as tpe  # noqa: E402
import warranties_policy_engine as we  # noqa: E402
import sla_policy_engine as sle  # noqa: E402
import assignment_policy_engine as ape  # noqa: E402

CLEAN_STATES = {core.ACCEPT, core.ACCEPT_WITH_NOTE}
NOT_CLEAN_STATES = {core.NEGOTIATE, core.MUST_REDLINE, core.PROHIBITED}


def _bucket_for_state(state: str) -> str:
    if state in CLEAN_STATES:
        return "CLEAN"
    if state in NOT_CLEAN_STATES:
        return "NOT_CLEAN"
    if state == core.REQUIRES_REVIEW:
        return "REQUIRES_REVIEW"
    if state == core.NOT_APPLICABLE:
        return "NOT_APPLICABLE"
    return f"OTHER:{state}"


@dataclass
class _LiabilityPolicy:
    preferred_multiplier: float = 1.0
    acceptable_max_multiplier: float = 1.0
    negotiate_max_multiplier: float = 2.0
    prohibit_unlimited: bool = True
    required_exceptions_json: list = field(default_factory=list)
    fallback_text: Optional[str] = None
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    require_consequential_damages_exclusion: bool = False
    required_consequential_carveouts_json: list = field(default_factory=list)


@dataclass
class _IndemnificationPolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = "Legal Director"
    fallback_text: Optional[str] = "Approved fallback indemnification language."
    required_protection_triggers_json: Optional[list] = None
    prohibited_exposure_triggers_json: Optional[list] = None
    require_exposure_third_party_only: bool = False
    require_defense_control_for_exposure: bool = False
    require_notice_and_cooperation_for_exposure: bool = False
    prohibit_uncapped_exposure: bool = True
    exposure_preferred_multiplier: Optional[float] = 1.0
    exposure_acceptable_max_multiplier: Optional[float] = 2.0
    exposure_negotiate_max_multiplier: Optional[float] = 3.0


@dataclass
class _ConfidentialityPolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    fallback_text: Optional[str] = None
    required_exclusions_json: list = field(default_factory=list)
    min_protection_duration_years: Optional[int] = None
    max_exposure_duration_years: Optional[int] = None
    require_mutual_confidentiality: bool = False


@dataclass
class _PaymentTermsPolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    fallback_text: Optional[str] = None
    preferred_net_days: Optional[int] = None
    acceptable_max_net_days: Optional[int] = 45
    negotiate_max_net_days: Optional[int] = 60
    require_disputed_amounts_withholdable: bool = False
    require_setoff_rights: bool = False
    prohibit_setoff_rights: bool = False
    require_we_are_not_tax_responsible: bool = False
    max_late_fee_percent: Optional[float] = None
    require_price_increase_notice_days: Optional[int] = None
    max_price_increase_percent: Optional[float] = None
    acceptable_max_multiplier: Optional[float] = None
    maximum_late_interest_rate_percent: Optional[float] = None
    maximum_price_increase_percent: Optional[float] = None
    minimum_dispute_notice_days: Optional[int] = None
    minimum_price_increase_notice_days: Optional[int] = None
    prohibit_disputed_amount_withholding: bool = False
    prohibit_set_off: bool = False
    prohibit_unilateral_price_increase: bool = False
    require_counterparty_is_payor: bool = False
    require_expense_preapproval: bool = False
    require_refund_entitlement: bool = False
    require_tax_responsibility_counterparty: bool = False
    require_undisputed_amounts_still_payable: bool = False
    required_currency: Optional[str] = None
    required_payment_trigger: Optional[str] = None


@dataclass
class _IPOwnershipPolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    fallback_text: Optional[str] = None
    require_we_retain_background_ip: bool = False
    require_we_own_work_product: bool = False
    require_customer_own_work_product: bool = False
    prohibit_work_product_includes_background_ip: bool = False
    require_exclusive_license: bool = False
    require_license_exclusive: bool = False
    require_royalty_free: bool = False
    prohibit_royalty_bearing_license: bool = False
    require_perpetual_license: bool = False
    require_irrevocable_license: bool = False
    prohibit_revocable_license: bool = False
    require_sublicensable: bool = False
    require_transferable: bool = False
    require_worldwide_territory: bool = False
    prohibit_derivative_works: bool = False
    prohibit_joint_ownership: bool = False
    require_license_for_embedded_background_ip: bool = False
    require_purpose_limited_license: bool = False
    require_feedback_assigned: bool = False
    require_residual_knowledge_rights: bool = False
    require_open_source_disclosure: bool = False
    require_infringement_remedy_reference: bool = False
    require_post_termination_survival: bool = False


@dataclass
class _InsurancePolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    fallback_text: Optional[str] = None
    require_cgl: bool = False
    require_professional_liability: bool = False
    require_cyber_liability: bool = False
    require_workers_comp: bool = False
    require_employers_liability: bool = False
    require_auto_liability: bool = False
    cgl_minimum_per_occurrence: Optional[float] = None
    professional_liability_minimum_limit: Optional[float] = None
    cyber_liability_minimum_limit: Optional[float] = None
    employers_liability_minimum_limit: Optional[float] = None
    auto_liability_minimum_limit: Optional[float] = None
    require_additional_insured: bool = False
    require_waiver_of_subrogation: bool = False
    require_primary_non_contributory: bool = False
    require_certificate_of_insurance: bool = False
    max_notice_of_cancellation_days: Optional[int] = None
    require_subcontractor_coverage: bool = False
    cgl_minimum_aggregate: Optional[float] = None
    minimum_cancellation_notice_days: Optional[int] = None
    require_claims_made_tail: bool = False
    require_counterparty_obligated: bool = False
    require_evidence_before_commencement: bool = False
    require_minimum_insurer_rating: bool = False
    require_notice_of_cancellation: bool = False
    require_policy_maintenance_through_term: bool = False


@dataclass
class _DataSecurityPolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    fallback_text: Optional[str] = None
    require_processor_role: bool = False
    prohibit_unrestricted_subprocessors: bool = False
    require_subprocessor_notice_or_consent: str = "not_required"
    max_breach_notification_hours: Optional[int] = None
    require_scc_or_adequacy_for_transfers: bool = False
    prohibit_data_transfer: bool = False
    require_deletion_or_return: bool = False
    max_retention_days: Optional[int] = None
    require_audit_rights: bool = False
    require_named_security_certification: bool = False
    require_cooperation_obligation: bool = False
    acceptable_max_breach_notification_hours: Optional[int] = None
    negotiate_max_breach_notification_hours: Optional[int] = None
    preferred_breach_notification_hours: Optional[int] = None
    require_confidentiality_of_personal_data: bool = False
    require_data_residency: bool = False
    require_fixed_breach_notification_period: bool = False
    require_international_transfer_safeguard: bool = False
    required_data_residency_regions_json: list = field(default_factory=list)

    def __post_init__(self):
        # Harness back-compat alias: some corpus cases' policy overrides use
        # "max_breach_notification_hours", which is not a field the real
        # Protocol's evaluate_data_security_policy reads (it reads
        # acceptable_max_breach_notification_hours) -- map it so those
        # cases' policy intent (a fixed max notification window) is
        # actually enforced, instead of silently no-op'ing. Same class of
        # harness authoring gap as the pre-existing
        # min_notice_days_for_convenience alias on _TerminationPolicy above.
        if self.max_breach_notification_hours is not None and self.acceptable_max_breach_notification_hours is None:
            self.acceptable_max_breach_notification_hours = self.max_breach_notification_hours
        if self.max_breach_notification_hours is not None and self.require_fixed_breach_notification_period is False:
            self.require_fixed_breach_notification_period = True


@dataclass
class _GoverningLawPolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    fallback_text: Optional[str] = None
    preferred_jurisdictions_json: list = field(default_factory=list)
    acceptable_jurisdictions_json: list = field(default_factory=list)
    prohibited_jurisdictions_json: list = field(default_factory=list)
    required_dispute_resolution: Optional[str] = None
    require_jury_trial_waiver: bool = False


@dataclass
class _TerminationPolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    fallback_text: Optional[str] = None
    require_mutual_convenience_termination: bool = False
    min_notice_days_against_us: Optional[int] = None
    min_cure_days_against_us: Optional[int] = None
    prohibit_immediate_termination_for_cause: bool = False
    required_survival_topics_json: Optional[list] = None
    prohibit_uncapped_termination_fee: bool = False
    fee_preferred_multiplier: Optional[float] = None
    fee_acceptable_max_multiplier: Optional[float] = None
    fee_negotiate_max_multiplier: Optional[float] = None
    # Back-compat aliases kept only so case overrides using the more
    # readable names still apply -- __post_init__ maps them onto the
    # real attribute names above.
    min_notice_days_for_convenience: Optional[int] = None
    require_mutual_termination_for_convenience: Optional[bool] = None

    def __post_init__(self):
        if self.min_notice_days_for_convenience is not None:
            self.min_notice_days_against_us = self.min_notice_days_for_convenience
        if self.require_mutual_termination_for_convenience is not None:
            self.require_mutual_convenience_termination = self.require_mutual_termination_for_convenience


@dataclass
class _WarrantiesPolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    fallback_text: Optional[str] = None
    require_categories_json: list = field(default_factory=list)
    max_disclaimer_scope: Optional[str] = None
    min_duration_days: Optional[int] = None
    require_exclusive_remedy: bool = False
    prohibit_as_is_disclaimer: bool = False
    minimum_warranty_duration_days: Optional[int] = None
    prohibit_exclusive_remedy: bool = False
    prohibited_warranty_categories_json: list = field(default_factory=list)
    require_compliance_with_law_warranty: bool = False
    require_malware_free_warranty: bool = False
    require_mutual_warranties: bool = False
    require_non_infringement_warranty: bool = False
    require_professional_standard: bool = False
    require_title_warranty: bool = False
    require_warranty_survival: bool = False
    required_remedy_type: Optional[str] = None
    required_warranty_categories_json: list = field(default_factory=list)


@dataclass
class _SLAPolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    fallback_text: Optional[str] = None
    min_uptime_percent: Optional[float] = None
    require_service_credits: bool = False
    max_credit_cap_percent: Optional[float] = None
    require_exclusive_remedy: bool = False
    minimum_acceptable_uptime_percent: Optional[float] = None
    minimum_claim_submission_days: Optional[int] = None
    minimum_credit_cap_percent_of_fees: Optional[float] = None
    minimum_credit_percent_of_fees: Optional[float] = None
    permitted_maintenance_exclusions_json: list = field(default_factory=list)
    prohibit_service_credits_as_exclusive_remedy: bool = False
    require_chronic_failure_remedy: bool = False
    require_severity_tiers: bool = False
    require_termination_right_for_chronic_failure: bool = False
    require_uptime_commitment: bool = False
    required_support_hours: Optional[str] = None
    p1_max_response_hours: Optional[float] = None
    p1_response_basis: Optional[str] = None
    p1_max_restoration_hours: Optional[float] = None
    p1_restoration_basis: Optional[str] = None
    p2_max_response_hours: Optional[float] = None
    p2_response_basis: Optional[str] = None
    p2_max_restoration_hours: Optional[float] = None
    p2_restoration_basis: Optional[str] = None
    p3_max_response_hours: Optional[float] = None
    p3_response_basis: Optional[str] = None
    p3_max_restoration_hours: Optional[float] = None
    p3_restoration_basis: Optional[str] = None
    p4_max_response_hours: Optional[float] = None
    p4_response_basis: Optional[str] = None
    p4_max_restoration_hours: Optional[float] = None
    p4_restoration_basis: Optional[str] = None


@dataclass
class _AssignmentPolicy:
    contract_side: str = "sell_side"
    escalation_approval_authority: Optional[str] = None
    fallback_text: Optional[str] = None
    require_consent_for_counterparty_assignment: bool = False
    prohibit_sole_discretion_consent: bool = False
    required_exceptions_json: list = field(default_factory=list)


ADAPTERS = {
    "limitation_of_liability": (lpe.extract_liability_facts, lpe.evaluate_liability_policy, _LiabilityPolicy),
    "indemnification": (ie.extract_indemnification_facts, ie.evaluate_indemnification_policy, _IndemnificationPolicy),
    "confidentiality": (cpe.extract_confidentiality_facts, cpe.evaluate_confidentiality_policy, _ConfidentialityPolicy),
    "payment_terms": (pte.extract_payment_facts, pte.evaluate_payment_policy, _PaymentTermsPolicy),
    "ip_ownership": (ipoe.extract_ip_facts, ipoe.evaluate_ip_policy, _IPOwnershipPolicy),
    "insurance": (ine.extract_insurance_facts, ine.evaluate_insurance_policy, _InsurancePolicy),
    "data_security": (dse.extract_data_security_facts, dse.evaluate_data_security_policy, _DataSecurityPolicy),
    "governing_law": (gpe.extract_governing_law_facts, gpe.evaluate_governing_law_policy, _GoverningLawPolicy),
    "termination": (tpe.extract_termination_facts, tpe.evaluate_termination_policy, _TerminationPolicy),
    "warranties": (we.extract_warranties_facts, we.evaluate_warranties_policy, _WarrantiesPolicy),
    "sla": (sle.extract_sla_facts, sle.evaluate_sla_policy, _SLAPolicy),
    "assignment": (ape.extract_assignment_facts, ape.evaluate_assignment_policy, _AssignmentPolicy),
}


def run_case(case):
    adapter = case["adapter"]
    extract_fn, evaluate_fn, policy_cls = ADAPTERS[adapter]
    policy = policy_cls(**case.get("policy", {}))
    text = case["text"]

    # Ensure the semantic/AI path is OFF for every adapter (production
    # default at FROZEN_COMMIT -- see FREEZE_MANIFEST.md) so this run
    # exercises only the deterministic backbone. No ANTHROPIC_API_KEY is
    # present in this environment regardless.
    facts = extract_fn(text)
    decision = evaluate_fn(facts, policy)

    # Determinism check: re-run evaluate_fn (not extract_fn/provider) on
    # the SAME admitted facts object multiple times -- this is the
    # deterministic-authority-boundary determinism the mission asks for,
    # not a repeat probabilistic discovery call.
    hashes = set()
    for _ in range(5):
        d = evaluate_fn(facts, policy)
        hashes.add(core.decision_hash(d) if hasattr(core, "decision_hash") else (d.state, tuple(d.unresolved_facts)))
    deterministic = len(hashes) == 1

    return {
        "case_id": case["id"],
        "adapter": adapter,
        "category": case["category"],
        "input_text": text,
        "ground_truth": case["ground_truth"],
        "facts_repr": repr(facts),
        "decision_state": decision.state,
        "decision_bucket": _bucket_for_state(decision.state),
        "decision_explanation": decision.explanation,
        "decision_unresolved_facts": list(decision.unresolved_facts),
        "deterministic_repeat_evaluation": deterministic,
    }


def main():
    results = []
    for case in CASES:
        try:
            results.append(run_case(case))
        except Exception as exc:  # noqa: BLE001 -- record, don't crash the run
            results.append({
                "case_id": case["id"], "adapter": case["adapter"], "category": case["category"],
                "input_text": case["text"], "ground_truth": case["ground_truth"],
                "error": f"{type(exc).__name__}: {exc}",
                "decision_state": None, "decision_bucket": "RUNNER_ERROR",
                "decision_explanation": None, "decision_unresolved_facts": [],
                "deterministic_repeat_evaluation": None,
            })

    out_path = os.path.join(os.path.dirname(__file__), "candidate2_raw_results.jsonl")
    with open(out_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    corpus_json = json.dumps(CASES, sort_keys=True).encode("utf-8")
    corpus_hash = hashlib.sha256(corpus_json).hexdigest()
    print(f"CORPUS_SHA256={corpus_hash}")
    print(f"TOTAL_CASES={len(CASES)}")
    print(f"RESULTS_WRITTEN={out_path}")

    fails = [r for r in results if r["decision_bucket"] == "RUNNER_ERROR"]
    if fails:
        print(f"RUNNER ERRORS: {len(fails)}")
        for r in fails:
            print(f"  {r['case_id']}: {r['error']}")


if __name__ == "__main__":
    main()
