#!/usr/bin/env python3
"""
Interaction Engine V1 — product demonstration fixture.

A realistic, synthetic commercial SaaS MSA run through the REAL production
pipeline (policy_enforcement.apply_policies_for_review, cutover mode —
the exact function main.py calls, no shortcuts) against a playbook with
all twelve clause types ACTIVE. Deliberately NOT an artificially
catastrophic contract where everything fires: the drafting choices below
were made to be plausible, ordinary MSA language, then run through the
unmodified engine to see what it actually finds. Per the task instruction,
this fixture was assembled AFTER the independent benchmark (benchmarks/
interaction_corpus.py / run_interaction_benchmark.py) already existed and
passed its gates — nothing about the engine was tuned to make this
specific fixture look a particular way.

Run: python3 benchmarks/interaction_demo_fixture.py
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
os.environ.setdefault("DEV_MODE", "true")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import interaction_enforcement as ixe
import playbook_authoring as pa
import policy_enforcement as pe
from database import Base
from models import Playbook, PolicyPosition, PolicyPositionField, User
import analytics_models  # noqa: F401


# ---------------------------------------------------------------------------
# The contract — a synthetic SaaS Master Services Agreement, one section
# per clause type this system evaluates.
# ---------------------------------------------------------------------------

MSA_TEXT = "\n\n".join([
    "MASTER SERVICES AGREEMENT",

    "8. Limitation of Liability. Except for the exclusion below, each party's aggregate liability "
    "under this Agreement shall not exceed 1 times the total annual fees paid in the preceding twelve "
    "months; the foregoing limitation shall not apply to claims arising from intellectual property "
    "infringement.",

    "9. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against "
    "any third-party claims arising from actual or alleged infringement of intellectual property "
    "rights by the Services.",

    "10. Termination. Either party may terminate this Agreement for convenience upon 60 days' prior "
    "written notice. Customer may terminate this Agreement immediately upon Vendor's failure to pay "
    "any amount when due. Either party may terminate immediately upon the other party's insolvency.",

    "11. Payment Terms. Customer shall pay Vendor all undisputed amounts within Net 45 days of "
    "receipt of a valid invoice. Customer may withhold payment of disputed amounts pending resolution "
    "in good faith. Vendor shall provide a service credit equal to a percentage of monthly fees as "
    "the sole remedy for any failure described in Exhibit A.",

    "12. Service Levels. Vendor commits to 99.9% uptime, measured monthly, excluding scheduled "
    "maintenance. Severity 1 issues shall have a response time of 1 hour and a restoration time of 4 "
    "hours. Vendor shall provide a service credit of 5% of monthly fees for each hour of unavailability "
    "beyond the committed uptime, subject to a claim submission deadline of 30 days.",

    "13. Insurance. Vendor shall maintain, at its own expense, Commercial General Liability insurance "
    "with limits of not less than $1,000,000 per occurrence and $2,000,000 in the aggregate, and "
    "Cyber Liability insurance with limits of not less than $2,000,000 per claim. Customer shall be "
    "named as an additional insured, and Vendor shall provide a certificate of insurance evidencing "
    "such coverage.",

    "14. Confidentiality. Each party shall protect the confidentiality of the other party's "
    "Confidential Information using reasonable care, for a period of 5 years after the termination of "
    "this Agreement. Confidential Information does not include information that is publicly known, "
    "independently developed by the receiving party, rightfully received from a third party, or "
    "required by law to be disclosed.",

    "15. Assignment. Either party may assign this Agreement to an affiliate or in connection with a "
    "merger, acquisition, or change of control.",

    "16. Governing Law. This Agreement shall be governed by the laws of the State of Delaware. Any "
    "dispute arising under this Agreement shall be resolved by binding arbitration under the rules of "
    "the American Arbitration Association.",

    "17. Data Protection. Vendor acts as a processor of Customer personal data. Vendor shall notify "
    "Customer of a personal data breach without undue delay and in any event within 48 hours. Vendor "
    "shall not engage a subprocessor without Customer's prior written consent, and personal data "
    "shall not be transferred outside the region without Standard Contractual Clauses.",

    "18. Intellectual Property. Vendor shall retain all right, title and interest in and to its "
    "pre-existing intellectual property. Customer shall own all right, title and interest in and to "
    "the Work Product created under this Agreement. Vendor hereby grants to Customer a non-exclusive, "
    "worldwide, royalty-free, perpetual and irrevocable license to use any Vendor background "
    "intellectual property embodied in the Deliverables.",

    "19. Warranties. Vendor represents and warrants that it has the authority to enter into this "
    "Agreement, that the Services will be performed in a professional and workmanlike manner in "
    "compliance with applicable law, and that the Services are free of malware.",
])


# ---------------------------------------------------------------------------
# The playbook — moderate, realistic buy-side thresholds, not adversarially
# tuned to force interactions. Every position built via the same builder
# functions playbook_authoring.py already uses in production authoring.
# ---------------------------------------------------------------------------

POSITIONS = {
    "limitation_of_liability": ("mutual", {
        "preferred_multiplier": 1.0, "acceptable_max_multiplier": 1.5, "negotiate_max_multiplier": 3.0,
        "prohibit_unlimited": True, "required_exceptions_json": [],
        "require_consequential_damages_exclusion": False, "required_consequential_carveouts_json": [],
    }),
    # This demo playbook represents Vendor's own legal team reviewing their
    # standard outbound MSA -- sell_side here (matching payment_terms and
    # sla below) is what makes Vendor's own IP-indemnification EXPOSURE
    # (not the protection Vendor extends to Customer) the fact this
    # adapter surfaces, which is what the flagship interaction (rule 1)
    # actually reasons about: OUR exposure vs. OUR liability cap treatment
    # of the same category. A buy-side Customer playbook reviewing the
    # identical clause would correctly see no exposure here at all (they
    # are the protected party, not the indemnifying party) -- that
    # asymmetry is itself a correct, deliberate property of the
    # directional resolution shared across every adapter, not a fixture
    # workaround.
    "indemnification": ("sell_side", {
        "required_protection_triggers_json": ["ip_infringement"], "prohibited_exposure_triggers_json": [],
        "require_exposure_third_party_only": False, "require_defense_control_for_exposure": False,
        "require_notice_and_cooperation_for_exposure": False, "prohibit_uncapped_exposure": False,
        "exposure_preferred_multiplier": 1.0, "exposure_acceptable_max_multiplier": 2.0, "exposure_negotiate_max_multiplier": 5.0,
    }),
    "termination": ("buy_side", {
        "require_mutual_convenience_termination": False, "min_notice_days_against_us": 30,
        "min_cure_days_against_us": 15, "prohibit_immediate_termination_for_cause": False,
        "required_survival_topics_json": [], "prohibit_uncapped_termination_fee": False,
        "fee_preferred_multiplier": None, "fee_acceptable_max_multiplier": None, "fee_negotiate_max_multiplier": None,
    }),
    "payment_terms": ("sell_side", {
        "require_counterparty_is_payor": False, "preferred_net_days": 30.0, "acceptable_max_net_days": 30.0,
        "required_payment_trigger": None, "require_undisputed_amounts_still_payable": True,
        "prohibit_disputed_amount_withholding": False, "minimum_dispute_notice_days": None,
        "prohibit_set_off": False, "maximum_late_interest_rate_percent": None,
        "prohibit_unilateral_price_increase": False, "maximum_price_increase_percent": None,
        "minimum_price_increase_notice_days": None, "require_expense_preapproval": False,
        "require_tax_responsibility_counterparty": False, "required_currency": None,
        "require_refund_entitlement": False,
    }),
    "sla": ("sell_side", {
        "require_uptime_commitment": True, "preferred_uptime_percent": 99.9, "minimum_acceptable_uptime_percent": 99.5,
        "permitted_maintenance_exclusions_json": ["scheduled_maintenance"],
        "require_severity_tiers": True,
        "p1_max_response_hours": 1.0, "p1_response_basis": "calendar",
        "p1_max_restoration_hours": 4.0, "p1_restoration_basis": "calendar",
        "p2_max_response_hours": None, "p2_response_basis": None, "p2_max_restoration_hours": None, "p2_restoration_basis": None,
        "p3_max_response_hours": None, "p3_response_basis": None, "p3_max_restoration_hours": None, "p3_restoration_basis": None,
        "p4_max_response_hours": None, "p4_response_basis": None, "p4_max_restoration_hours": None, "p4_restoration_basis": None,
        "required_support_hours": None, "require_service_credits": True,
        "minimum_credit_percent_of_fees": 5.0, "minimum_credit_cap_percent_of_fees": None,
        "require_chronic_failure_remedy": False, "require_termination_right_for_chronic_failure": False,
        "prohibit_service_credits_as_exclusive_remedy": False, "minimum_claim_submission_days": 15.0,
    }),
    "insurance": ("buy_side", {
        "require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0, "cgl_minimum_aggregate": 2_000_000.0,
        "require_professional_liability": False, "professional_liability_minimum_limit": None,
        "require_cyber_liability": True, "cyber_liability_minimum_limit": 2_000_000.0,
        "require_workers_comp": False, "require_employers_liability": False, "employers_liability_minimum_limit": None,
        "require_auto_liability": False, "auto_liability_minimum_limit": None,
        "require_counterparty_obligated": True, "require_additional_insured": True,
        "require_waiver_of_subrogation": False, "require_primary_non_contributory": False,
        "require_certificate_of_insurance": True, "require_minimum_insurer_rating": False,
        "require_notice_of_cancellation": False, "minimum_cancellation_notice_days": None,
        "require_policy_maintenance_through_term": False, "require_claims_made_tail": False,
        "require_subcontractor_coverage": False, "require_evidence_before_commencement": False,
    }),
    "confidentiality": ("mutual", {
        "required_exclusions_json": ["public_knowledge", "independently_developed", "third_party_rightful", "required_by_law"],
        "min_protection_duration_years": 3, "max_exposure_duration_years": None,
        "require_mutual_confidentiality": True,
    }),
    "assignment": ("mutual", {
        "required_exceptions_json": ["affiliate", "change_of_control", "merger_acquisition"],
        "prohibit_sole_discretion_consent": False, "require_consent_for_counterparty_assignment": False,
    }),
    "governing_law": ("buy_side", {
        "preferred_jurisdictions_json": ["Delaware"], "acceptable_jurisdictions_json": ["Delaware", "New York"],
        "prohibited_jurisdictions_json": [], "required_dispute_resolution": None,
        "require_jury_trial_waiver": False,
    }),
    "data_security": ("buy_side", {
        "require_processor_role": True, "prohibit_unrestricted_subprocessors": True,
        "require_subprocessor_notice_or_consent": "consent",
        "preferred_breach_notification_hours": 48, "acceptable_max_breach_notification_hours": 72,
        "negotiate_max_breach_notification_hours": 96, "require_fixed_breach_notification_period": True,
        "require_international_transfer_safeguard": True, "require_data_residency": False,
        "required_data_residency_regions_json": [], "require_deletion_or_return": False, "max_retention_days": None,
        "require_audit_rights": False, "require_named_security_certification": False,
        "require_cooperation_obligation": False, "require_confidentiality_of_personal_data": False,
    }),
    "ip_ownership": ("buy_side", {
        "require_we_retain_background_ip": False, "require_we_own_work_product": True,
        "prohibit_joint_ownership": False, "require_license_for_embedded_background_ip": True,
        "require_license_exclusive": False, "prohibit_royalty_bearing_license": True,
        "require_perpetual_license": True, "prohibit_revocable_license": True,
        "require_sublicensable": False, "require_transferable": False, "require_worldwide_territory": True,
        "require_purpose_limited_license": False, "prohibit_derivative_works": False,
        "require_feedback_assigned": False, "require_residual_knowledge_rights": False,
        "require_open_source_disclosure": False, "require_infringement_remedy_reference": False,
        "require_post_termination_survival": False,
    }),
    "warranties": ("buy_side", {
        "required_warranty_categories_json": ["authority", "compliance_with_law", "professional_workmanlike", "malware_free"],
        "prohibited_warranty_categories_json": [], "require_mutual_warranties": False,
        "minimum_warranty_duration_days": None, "prohibit_as_is_disclaimer": False,
        "prohibit_exclusive_remedy": False, "required_remedy_type": None,
        "require_non_infringement_warranty": False, "require_compliance_with_law_warranty": True,
        "require_professional_standard": True, "require_malware_free_warranty": True,
        "require_title_warranty": False, "require_warranty_survival": False,
    }),
}


def build_demo_playbook(db):
    user = User(email="demo@example.com", password_hash="x")
    db.add(user)
    db.flush()
    playbook = Playbook(user_id=user.id, name="Demo SaaS MSA Playbook", template_text="n/a")
    db.add(playbook)
    db.flush()

    for clause_type, (contract_side, config) in POSITIONS.items():
        position = PolicyPosition(
            playbook_id=playbook.id, clause_type=clause_type, status="DRAFT",
            contract_side=contract_side, escalation_approval_authority="General Counsel",
            fallback_text="Approved fallback language.", config_json=config, source_type="MANUAL",
        )
        db.add(position)
        db.flush()
        # Every configured field is marked ESTABLISHED, not only the
        # mechanically-required ones -- SLA's adapter-owned activation
        # hook (playbook_authoring._sla_activation_validator) additionally
        # checks that a configured p{n}_max_*_hours has its matching
        # p{n}_*_basis field ESTABLISHED too, which this demo fixture
        # genuinely configures (a real severity-tier ceiling with a real
        # basis), so it needs a real field row, not just the require_*
        # booleans every other clause type gets away with.
        for field_name in pa.CLAUSE_TYPE_CONFIG_FIELDS[clause_type]:
            db.add(PolicyPositionField(
                policy_position_id=position.id, field_name=field_name,
                value_json=config.get(field_name), source="MANUAL", status="ESTABLISHED",
            ))
        db.flush()
        pa.validate_position_for_activation(position)
        position.status = "ACTIVE"
        position.activated_at = datetime.utcnow()
        db.flush()
    db.commit()
    return playbook


def _print_section(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main():
    os.environ["POLICY_ENFORCEMENT_MODE"] = "cutover"
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    playbook = build_demo_playbook(db)

    findings = []
    result = pe.apply_policies_for_review(db, playbook, MSA_TEXT, findings)
    policy_decisions = result["policy_decisions"]
    interaction_decisions = result["interaction_decisions"]

    _print_section("1. Individual policy evaluation — 12 clause areas")
    buckets = {"passed": [], "negotiate": [], "requires_review": [], "other": []}
    for clause_type in pa.CLAUSE_TYPES:
        decision = policy_decisions.get(clause_type)
        state = decision["state"] if decision else "NOT_EVALUATED"
        label = pa.CLAUSE_TYPE_LABELS[clause_type]
        if state in ("ACCEPT", "ACCEPT_WITH_NOTE"):
            buckets["passed"].append((label, state))
        elif state == "NEGOTIATE":
            buckets["negotiate"].append((label, state))
        elif state == "REQUIRES_REVIEW":
            buckets["requires_review"].append((label, state))
        else:
            buckets["other"].append((label, state))
        print(f"  {label:32s} {state}")

    _print_section("2. Review summary")
    print(f"  {len(buckets['passed'])} policy checks passed: {', '.join(l for l, s in buckets['passed'])}")
    print(f"  {len(buckets['negotiate'])} need negotiation: {', '.join(l for l, s in buckets['negotiate']) or '(none)'}")
    print(f"  {len(buckets['requires_review'])} require judgment (REQUIRES_REVIEW): {', '.join(l for l, s in buckets['requires_review']) or '(none)'}")
    if buckets["other"]:
        print(f"  {len(buckets['other'])} other: {', '.join(f'{l} ({s})' for l, s in buckets['other'])}")

    actionable_interactions = {
        iid: d for iid, d in interaction_decisions.items()
        if d["state"] in ("ESCALATE", "NEGOTIATE", "REQUIRES_REVIEW")
    }
    print(f"  {len(actionable_interactions)} cross-policy interactions require attention")

    _print_section("3. Cross-policy interactions requiring attention")
    if not actionable_interactions:
        print("  None fired.")
    for iid, d in actionable_interactions.items():
        print(f"\n  [{d['kind']}] {d['label']} — {d['state']}")
        print(f"    Participating clauses: {', '.join(pa.CLAUSE_TYPE_LABELS[c] for c in d['participating_clause_types'])}")
        for ct in d["participating_clause_types"]:
            prov = d["participating_provisions"].get(ct)
            if prov:
                print(f"    {prov['label']}: {prov['excerpt'][:110]}")
        print(f"    Why this matters: {d['explanation']}")
        print(f"    Required action: {d['required_action']}")

    not_triggered = [iid for iid, d in interaction_decisions.items() if d["state"] == "NOT_TRIGGERED"]
    insufficient = [iid for iid, d in interaction_decisions.items() if d["state"] == "INSUFFICIENT_FACTS"]
    print(f"\n  ({len(not_triggered)} of the 7 launch rules evaluated cleanly and did not fire; "
          f"{len(insufficient)} could not be evaluated due to insufficient facts)")

    # -----------------------------------------------------------------
    # 4. Redline invalidation demonstration
    # -----------------------------------------------------------------
    _print_section("4. Redline invalidation demonstration")
    if not actionable_interactions:
        print("  No actionable interaction to demonstrate invalidation against.")
        return

    first_iid, first_decision = next(iter(actionable_interactions.items()))
    edited_clause = first_decision["participating_clause_types"][0]
    edited_label = pa.CLAUSE_TYPE_LABELS[edited_clause]
    print(f"  Simulating a lawyer editing the {edited_label} finding (participates in '{first_iid}')...")

    class _FakeContract:
        def __init__(self, interaction_decisions_json, interaction_staleness_json=None):
            self.interaction_decisions_json = interaction_decisions_json
            self.interaction_staleness_json = interaction_staleness_json

    contract = _FakeContract(interaction_decisions_json=interaction_decisions)
    marked = ixe.mark_dependent_interactions_stale(contract, edited_clause, edited_label)

    print(f"\n  Interactions flagged NEEDS_RECONFIRMATION: {marked}")
    for iid in interaction_decisions:
        if iid in marked:
            reason = contract.interaction_staleness_json[iid]["stale_reason"]
            print(f"    [STALE] {interaction_decisions[iid]['label']} — {reason}")
    untouched_actionable = [iid for iid in actionable_interactions if iid not in marked]
    print(f"\n  Untouched actionable interactions (correctly NOT flagged): {untouched_actionable or '(none other fired)'}")
    print("  -> Only the interaction depending on the edited clause changed. Every other")
    print("     interaction's evidence remains exactly as originally evaluated.")


if __name__ == "__main__":
    main()
