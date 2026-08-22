"""Step 4B Phase 3 — adversarial authority micro-benchmark (~10 cases per
rule, 7 rules). Constructs PolicyDecision fixtures directly (same
methodology as the Phase 3 truth-table script) and attacks: missing
participant, unresolved participant, category-level ambiguity, wrong
direction, wrong owner, false applicability, insufficient evidence,
duplicated participant, one safe + one unsafe input, uncertainty
laundering. DEVELOPMENT evidence — may be iterated against.
"""
from typing import Any, Dict, List, Optional

from policy_engine_core import PolicyDecision

CASES: List[Dict[str, Any]] = []


def pd(clause_type: str, state: str, category_treatments=None, interaction_facts=None,
       controlling_provision: Optional[Dict] = None) -> PolicyDecision:
    return PolicyDecision(
        rule_id="TEST", clause_type=clause_type, state=state,
        contract_language="", extracted_summary="", policy_limit_summary="",
        required_action="", explanation="", negotiation_ladder=[],
        category_treatments=category_treatments or [], unresolved_facts=[],
        start_index=0, end_index=10,
        controlling_provision=controlling_provision if controlling_provision is not None else
        ({"label": f"{clause_type} clause", "excerpt": "...evidence...", "start_index": "0", "end_index": "10"} if state not in ("NOT_APPLICABLE",) else None),
        interaction_facts=interaction_facts or {},
    )


def ct(category, treatment, established=True):
    return {"category": category, "treatment": treatment, "cap_summary": "", "raw_excerpt": "", "established": established}


def case(cid: str, interaction_id: str, attack: str, decisions: Dict[str, PolicyDecision],
         expected_state: str, notes: str = "") -> Dict[str, Any]:
    return {"id": cid, "interaction_id": interaction_id, "attack": attack,
            "decisions": decisions, "expected_state": expected_state, "notes": notes}


# ===========================================================================
# Rule 1 — IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY
# ===========================================================================
R1 = "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"
CASES += [
    case("mb-r1-01", R1, "missing_participant", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r1-02", R1, "unresolved_participant", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "indemnification": pd("indemnification", "REQUIRES_REVIEW"),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r1-03", R1, "conflicting_participant", {
        "limitation_of_liability": pd("limitation_of_liability", "EVALUATION_ERROR"),
        "indemnification": pd("indemnification", "ESCALATE", [ct("ip_infringement", "covered")]),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r1-04", R1, "false_applicability", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
    }, "NOT_TRIGGERED", "within_general_cap is NOT uncapped/super_cap -- must not falsely fire"),
    case("mb-r1-05", R1, "insufficient_evidence_bare_category", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", []),
        "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
    }, "NOT_TRIGGERED", "liability has no ip_infringement category entry at all -- must not fire on absence-as-uncapped"),
    case("mb-r1-06", R1, "duplicated_participant_category", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped"), ct("ip_infringement", "within_general_cap")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("ip_infringement", "covered")]),
    }, "NOT_TRIGGERED", "GTD: corrected ground truth -- dict-building (_by_category) keeps the LAST duplicate entry (within_general_cap), which is not uncapped/super_cap, so the rule correctly does NOT fire. Original expected value (ESCALATE) was a corpus-authoring error contradicting this case's own notes; verified directly via _by_category before correcting. Safe-direction mismatch (NOT_TRIGGERED, not a false fire), not a production defect."),
    case("mb-r1-07", R1, "one_safe_one_unsafe_a", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "indemnification": pd("indemnification", "NOT_APPLICABLE"),
    }, "INSUFFICIENT_FACTS", "liability side is 'unsafe' (uncapped) but indemnification absent -- must not fire on the unsafe side alone"),
    case("mb-r1-08", R1, "one_safe_one_unsafe_b", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "within_general_cap")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("ip_infringement", "covered")]),
    }, "NOT_TRIGGERED", "indemnification side resolved+covered but liability side benign -- correctly does not fire"),
    case("mb-r1-09", R1, "uncertainty_laundering_wrong_category_present", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("confidentiality", "unresolved")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
    }, "NOT_TRIGGERED", "an unresolved OTHER category must not be laundered into firing this ip_infringement-specific rule"),
    case("mb-r1-10", R1, "wrong_owner_wrong_clause_type_key", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("ip_infringement", "covered")]),
        "insurance": pd("insurance", "ESCALATE", [ct("ip_infringement", "uncapped")]),  # bystander, not a rule-1 participant
    }, "ESCALATE", "a third, non-participating decision (insurance) present in the dict must not affect rule 1's own two-participant evaluation"),
]

# ===========================================================================
# Rule 2 — IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH
# ===========================================================================
R2 = "IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH"
CASES += [
    case("mb-r2-01", R2, "missing_participant", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r2-02", R2, "unresolved_participant", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "indemnification": pd("indemnification", "EVALUATION_ERROR"),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r2-03", R2, "false_applicability_ip_excluded", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("ip_infringement", "covered")]),
    }, "NOT_TRIGGERED", "ip_infringement is deliberately excluded from rule 2 (rule 1's job) -- must not double-fire"),
    case("mb-r2-04", R2, "insufficient_evidence_no_categories", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", []),
        "indemnification": pd("indemnification", "ACCEPT", []),
    }, "NOT_TRIGGERED"),
    case("mb-r2-05", R2, "duplicated_participant_categories", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped"), ct("confidentiality", "uncapped"), ct("gross_negligence", "uncapped")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("data_breach", "covered"), ct("confidentiality", "covered"), ct("gross_negligence", "covered")]),
    }, "ESCALATE", "3 matching categories must merge into ONE finding, not 3 separate fires"),
    case("mb-r2-06", R2, "one_safe_one_unsafe", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("willful_misconduct", "uncapped")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("willful_misconduct", "not_addressed")]),
    }, "NOT_TRIGGERED", "indemnification does not COVER this category -- must not fire on liability's exposure alone"),
    case("mb-r2-07", R2, "uncertainty_laundering_partial_categories", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped"), ct("confidentiality", "unresolved")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("data_breach", "covered"), ct("confidentiality", "covered")]),
    }, "ESCALATE", "data_breach genuinely matches (fires correctly); confidentiality's unresolved status must not be silently folded into the same finding as if resolved"),
    case("mb-r2-08", R2, "wrong_direction_na", {
        "limitation_of_liability": pd("limitation_of_liability", "NOT_APPLICABLE"),
        "indemnification": pd("indemnification", "ESCALATE", [ct("data_breach", "covered")]),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r2-09", R2, "false_applicability_super_cap_still_fires", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("gross_negligence", "super_cap")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("gross_negligence", "covered")]),
    }, "ESCALATE", "super_cap is a genuine trigger condition, not a false positive -- must fire"),
    case("mb-r2-10", R2, "bystander_third_decision", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("data_breach", "covered")]),
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
    }, "ESCALATE", "unrelated termination decision present must not affect this rule's own evaluation"),
]

# ===========================================================================
# Rule 3 — IX_INDEMNITY_WITHIN_GENERAL_CAP (DEPENDENCY)
# ===========================================================================
R3 = "IX_INDEMNITY_WITHIN_GENERAL_CAP"
CASES += [
    case("mb-r3-01", R3, "missing_participant", {
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r3-02", R3, "unresolved_participant", {
        "limitation_of_liability": pd("limitation_of_liability", "REQUIRES_REVIEW"),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r3-03", R3, "false_applicability_uncapped_excluded", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("data_breach", "covered")]),
    }, "NOT_TRIGGERED", "uncapped must route to rules 1/2, never double-report as a benign dependency too"),
    case("mb-r3-04", R3, "insufficient_evidence_no_category", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", []),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    }, "NOT_TRIGGERED"),
    case("mb-r3-05", R3, "one_safe_one_unsafe", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "excluded")]),
    }, "NOT_TRIGGERED", "indemnification EXCLUDES the category -- no exposure to be inside the cap, must not fire"),
    case("mb-r3-06", R3, "duplicated_categories_merge", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "not_addressed"), ct("confidentiality", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered"), ct("confidentiality", "covered")]),
    }, "ACCEPT_WITH_NOTE", "both categories qualify -- must merge into one finding"),
    case("mb-r3-07", R3, "ceiling_never_exceeds_accept_with_note", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "not_addressed")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
    }, "ACCEPT_WITH_NOTE", "rule's ceiling_state is ACCEPT_WITH_NOTE -- can never escalate past it even under attack framing"),
    case("mb-r3-08", R3, "wrong_participant_key", {
        "insurance": pd("insurance", "ACCEPT", [ct("data_breach", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    }, "INSUFFICIENT_FACTS", "wrong clause_type key (insurance) supplied instead of limitation_of_liability -- must gate, not misread"),
    case("mb-r3-09", R3, "bystander_third_decision", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "not_addressed")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
    }, "ACCEPT_WITH_NOTE", "unrelated sla decision must not affect this rule"),
]

# ===========================================================================
# Rule 4 — IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY
# ===========================================================================
R4 = "IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY"
CASES += [
    case("mb-r4-01", R4, "missing_participant", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "unresolved")]),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r4-02", R4, "whole_decision_requires_review_gates_first", {
        "limitation_of_liability": pd("limitation_of_liability", "REQUIRES_REVIEW"),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    }, "INSUFFICIENT_FACTS", "decision-level REQUIRES_REVIEW gates before rule 4's own category-level check ever runs"),
    case("mb-r4-03", R4, "false_applicability_no_ambiguity", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    }, "NOT_TRIGGERED"),
    case("mb-r4-04", R4, "insufficient_evidence_no_categories", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", []),
        "indemnification": pd("indemnification", "ACCEPT", []),
    }, "NOT_TRIGGERED"),
    case("mb-r4-05", R4, "conflicting_both_categories_unresolved", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("confidentiality", "unresolved")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("confidentiality", "unresolved")]),
    }, "REQUIRES_REVIEW", "both sides ambiguous on the SAME category -- must resolve to review, listed once"),
    case("mb-r4-06", R4, "one_safe_one_unsafe_indemnification_side", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("gross_negligence", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("gross_negligence", "unresolved")]),
    }, "REQUIRES_REVIEW", "liability side is clean but indemnification's own category is ambiguous -- must still surface"),
    case("mb-r4-07", R4, "uncertainty_laundering_multiple_categories_one_ambiguous", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap"), ct("willful_misconduct", "unresolved")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered"), ct("willful_misconduct", "not_addressed")]),
    }, "REQUIRES_REVIEW", "data_breach is clean but willful_misconduct is ambiguous -- the ambiguous category must not be laundered away by the clean one"),
    case("mb-r4-08", R4, "duplicated_category_entries", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "unresolved"), ct("data_breach", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    }, "NOT_TRIGGERED", "documents actual last-wins dict behavior on duplicate categories -- last entry (within_general_cap) overwrites the ambiguous one"),
    case("mb-r4-09", R4, "bystander_third_decision", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("confidentiality", "unresolved")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("confidentiality", "not_addressed")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "unresolved")]),
    }, "REQUIRES_REVIEW", "unrelated insurance ambiguity must not affect this rule's own two-participant scope"),
]

# ===========================================================================
# Rule 5 — IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE
# ===========================================================================
R5 = "IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE"
CASES += [
    case("mb-r5-01", R5, "missing_participant", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r5-02", R5, "unresolved_participant", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "insurance": pd("insurance", "REQUIRES_REVIEW"),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r5-03", R5, "false_applicability_established_insurance", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "within_general_cap", established=True)]),
    }, "NOT_TRIGGERED", "insurance IS established -- must not fire"),
    case("mb-r5-04", R5, "wrong_owner_wrong_category_mapping", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("confidentiality", "uncapped")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
    }, "NOT_TRIGGERED", "confidentiality is not data_breach -- this rule is scoped to data_breach only, must not generalize"),
    case("mb-r5-05", R5, "insufficient_evidence_no_insurance_coverage_entry", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "insurance": pd("insurance", "ACCEPT", []),
    }, "NOT_TRIGGERED", "no cyber_liability category entry present at all -- must not assume not-established"),
    case("mb-r5-06", R5, "duplicated_insurance_entries", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False), ct("cyber_liability", "within_general_cap", established=True)]),
    }, "NOT_TRIGGERED", "documents last-wins on duplicate insurance entries -- established=True wins"),
    case("mb-r5-07", R5, "one_safe_one_unsafe", {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
    }, "NOT_TRIGGERED", "liability side is benign (within_general_cap) -- missing insurance alone is not the trigger"),
    case("mb-r5-08", R5, "insurance_not_applicable", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "insurance": pd("insurance", "NOT_APPLICABLE"),
    }, "INSUFFICIENT_FACTS", "no insurance clause at all is NOT the same as 'established=False' -- must gate as insufficient facts, never silently treated as evidence of the conflict"),
    case("mb-r5-09", R5, "bystander_third_decision", {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("data_breach", "covered")]),
    }, "ESCALATE", "unrelated indemnification decision present must not change rule 5's own two-participant evaluation"),
]

# ===========================================================================
# Rule 6 — IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING (directional)
# ===========================================================================
R6 = "IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING"
CASES += [
    case("mb-r6-01", R6, "missing_participant", {
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r6-02", R6, "unresolved_participant", {
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
        "payment_terms": pd("payment_terms", "REQUIRES_REVIEW"),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r6-03", R6, "false_applicability_notice_and_cure", {
        "termination": pd("termination", "ACCEPT", [ct("non_payment", "notice_and_cure")]),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}),
    }, "NOT_TRIGGERED", "termination right has notice/cure -- immediate is required to fire"),
    case("mb-r6-04", R6, "wrong_direction_our_own_right_never_in_category_treatments",
         {
             # This case documents that termination_policy_engine.py's own
             # category_treatments is ALREADY scoped to counterparty rights
             # only (their_rights) -- our own non-payment right, if any,
             # never appears here at all. This case constructs a decision
             # AS IF our own right leaked in, to confirm the interaction
             # rule itself has no additional directional check of its own
             # (it trusts the adapter's own scoping) -- documenting the
             # boundary, not finding a defect (the adapter-level scoping
             # was verified separately in phase3_authority_verification.md
             # Finding J).
             "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
             "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}),
         }, "ESCALATE", "fires correctly when the adapter has already scoped this to a counterparty-held right (verified upstream, not re-checked by this rule)"),
    case("mb-r6-05", R6, "insufficient_evidence_withholdable_none", {
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={}),
    }, "NOT_TRIGGERED", "withholdable fact never established -- must not assume True"),
    case("mb-r6-06", R6, "insufficient_evidence_withholdable_explicit_false", {
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": False}),
    }, "NOT_TRIGGERED"),
    case("mb-r6-07", R6, "one_safe_one_unsafe", {
        "termination": pd("termination", "ACCEPT", [ct("non_payment", "notice_and_cure")]),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}),
    }, "NOT_TRIGGERED", "payment side is 'unsafe' (withholdable=True) but termination side is benign -- must not fire on one side alone"),
    case("mb-r6-08", R6, "missing_category_entry", {
        "termination": pd("termination", "ACCEPT", []),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}),
    }, "NOT_TRIGGERED", "no non_payment category entry at all -- must not assume immediate"),
    case("mb-r6-09", R6, "bystander_third_decision", {
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}),
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
    }, "ESCALATE", "unrelated sla decision must not change this rule's own evaluation"),
]

# ===========================================================================
# Rule 7 — IX_SLA_PAYMENT_CREDIT_DEPENDENCY
# ===========================================================================
R7 = "IX_SLA_PAYMENT_CREDIT_DEPENDENCY"
CASES += [
    case("mb-r7-01", R7, "missing_participant", {
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r7-02", R7, "unresolved_participant", {
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
        "payment_terms": pd("payment_terms", "REQUIRES_REVIEW"),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r7-03", R7, "false_applicability_one_false", {
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": False}),
    }, "NOT_TRIGGERED"),
    case("mb-r7-04", R7, "insufficient_evidence_both_unestablished", {
        "sla": pd("sla", "ACCEPT", interaction_facts={}),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={}),
    }, "NOT_TRIGGERED"),
    case("mb-r7-05", R7, "one_safe_one_unsafe", {
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": None}),
    }, "NOT_TRIGGERED", "payment side unestablished (None) despite sla True -- must not fire"),
    case("mb-r7-06", R7, "sla_not_applicable", {
        "sla": pd("sla", "NOT_APPLICABLE"),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r7-07", R7, "payment_evaluation_error", {
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
        "payment_terms": pd("payment_terms", "EVALUATION_ERROR"),
    }, "INSUFFICIENT_FACTS"),
    case("mb-r7-08", R7, "ceiling_never_exceeds_requires_review", {
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}),
    }, "REQUIRES_REVIEW", "rule's ceiling_state is REQUIRES_REVIEW -- can never escalate past it"),
    case("mb-r7-09", R7, "bystander_third_decision", {
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}),
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
    }, "REQUIRES_REVIEW", "unrelated termination decision must not affect this rule"),
]

# ---------------------------------------------------------------------------
# Additional cases to reach the >=70-case minimum, one more per rule 3-7,
# each targeting "wrong participant key" (a decisions dict keyed by the
# WRONG clause_type string entirely) -- a structural attack not yet
# covered for these 5 rules.
# ---------------------------------------------------------------------------
CASES += [
    case("mb-r3-10", R3, "wrong_participant_key_swap", {
        "termination": pd("termination", "ACCEPT", [ct("data_breach", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    }, "INSUFFICIENT_FACTS", "limitation_of_liability key entirely absent (termination substituted) -- must gate, not misread termination's category_treatments as liability's"),
    case("mb-r4-10", R4, "wrong_participant_key_swap", {
        "insurance": pd("insurance", "ACCEPT", [ct("data_breach", "unresolved")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "not_addressed")]),
    }, "INSUFFICIENT_FACTS", "limitation_of_liability key absent -- must gate"),
    case("mb-r5-10", R5, "wrong_participant_key_swap", {
        "termination": pd("termination", "ESCALATE", [ct("data_breach", "uncapped")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
    }, "INSUFFICIENT_FACTS", "limitation_of_liability key absent (termination substituted) -- must gate"),
    case("mb-r6-10", R6, "wrong_participant_key_swap", {
        "sla": pd("sla", "ESCALATE", [ct("non_payment", "immediate")]),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}),
    }, "INSUFFICIENT_FACTS", "termination key absent (sla substituted) -- must gate"),
    case("mb-r7-10", R7, "wrong_participant_key_swap", {
        "insurance": pd("insurance", "ACCEPT", interaction_facts={"service_credit_present": True}),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}),
    }, "INSUFFICIENT_FACTS", "sla key absent (insurance substituted) -- must gate"),
]
