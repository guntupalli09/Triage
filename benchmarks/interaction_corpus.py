"""
Interaction Engine V1 — independent adversarial corpus.

Per docs/architecture/interaction_engine_v1_design.md S10.1: cases are
built primarily at the DECISION level (PolicyDecision fixtures constructed
directly, never run through an extractor) so interaction-predicate
correctness is proven independent of any adapter's own extraction quirks.
A smaller end-to-end subset (real contract text -> real adapters ->
interaction engine) proves the wiring, not the logic, is correct — that
subset is a separate corpus, benchmarks/interaction_e2e_corpus.py.

This corpus is NOT a reuse of any adapter's own benchmark cases (task
requirement) — every case here was hand-built for this benchmark,
targeting interaction predicates specifically.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from policy_engine_core import PolicyDecision


def mk_decision(
    clause_type: str, state: str, category_treatments: Optional[List[Dict]] = None,
    interaction_facts: Optional[Dict] = None, escalate_to: Optional[str] = None,
    section_label: str = "X",
) -> PolicyDecision:
    return PolicyDecision(
        rule_id=f"POLICY_{clause_type.upper()}", clause_type=clause_type, state=state,
        contract_language=f"[{clause_type} contract language]", extracted_summary="s", policy_limit_summary="p",
        required_action="a", explanation="e", negotiation_ladder=[],
        category_treatments=category_treatments or [], unresolved_facts=[],
        start_index=0, end_index=10, escalate_to=escalate_to,
        controlling_provision={
            "label": f"Section {section_label} — {clause_type.replace('_', ' ').title()}",
            "excerpt": f"[{clause_type} excerpt]", "start_index": 0, "end_index": 10,
        },
        interaction_facts=interaction_facts or {},
    )


def ct(category: str, treatment: str, established: bool = True) -> Dict:
    return {"category": category, "treatment": treatment, "cap_summary": None, "raw_excerpt": "x", "established": established}


@dataclass
class InteractionCase:
    case_id: str
    tags: List[str]
    decisions: Dict[str, PolicyDecision]
    expected: Dict[str, str]  # interaction_id -> expected state, only for ids this case cares to assert
    notes: str = ""


CASES: List[InteractionCase] = []


def case(case_id, tags, decisions, expected, notes=""):
    CASES.append(InteractionCase(case_id, tags, decisions, expected, notes))


IX1 = "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"
IX2 = "IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH"
IX3 = "IX_INDEMNITY_WITHIN_GENERAL_CAP"
IX4 = "IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY"
IX5 = "IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE"
IX6 = "IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING"
IX7 = "IX_SLA_PAYMENT_CREDIT_DEPENDENCY"

# ===========================================================================
# Rule 1 — IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY
# ===========================================================================

case("ix1-true-positive-uncapped", ["ix1", "true_positive"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "NEGOTIATE", [ct("ip_infringement", "uncapped")], escalate_to="GC"),
      "indemnification": mk_decision("indemnification", "NEGOTIATE", [ct("ip_infringement", "covered")])},
     {IX1: "ESCALATE"})

case("ix1-true-positive-super-cap", ["ix1", "true_positive"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "super_cap")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX1: "ESCALATE"})

case("ix1-clear-negative-within-cap", ["ix1", "clear_negative"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "within_general_cap")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX1: "NOT_TRIGGERED"})

case("ix1-clear-negative-excluded", ["ix1", "clear_negative"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "excluded")])},
     {IX1: "NOT_TRIGGERED"})

case("ix1-missing-participant-indemnification", ["ix1", "missing_participant"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")])},
     {IX1: "INSUFFICIENT_FACTS"})

case("ix1-missing-participant-liability", ["ix1", "missing_participant"],
     {"indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX1: "INSUFFICIENT_FACTS"})

case("ix1-upstream-requires-review-liability", ["ix1", "upstream_requires_review"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "REQUIRES_REVIEW", []),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX1: "INSUFFICIENT_FACTS"})

case("ix1-upstream-requires-review-indemnification", ["ix1", "upstream_requires_review"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
      "indemnification": mk_decision("indemnification", "REQUIRES_REVIEW", [])},
     {IX1: "INSUFFICIENT_FACTS"})

case("ix1-upstream-not-applicable", ["ix1", "upstream_not_applicable"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "NOT_APPLICABLE", []),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX1: "INSUFFICIENT_FACTS"},
     notes="No liability clause at all -- must abstain, never assume 'no cap' means uncapped.")

case("ix1-superficially-similar-different-category", ["ix1", "superficially_similar"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX1: "NOT_TRIGGERED"},
     notes="Liability is uncapped for a DIFFERENT category (data_breach) -- must not cross-contaminate.")

case("ix1-superficially-similar-not-addressed", ["ix1", "superficially_similar"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "not_addressed")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX1: "NOT_TRIGGERED"})

# ===========================================================================
# Rule 2 — IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH
# ===========================================================================

case("ix2-true-positive-single-category", ["ix2", "true_positive"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
     {IX2: "ESCALATE"})

case("ix2-true-positive-multiple-categories", ["ix2", "true_positive"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [
         ct("data_breach", "uncapped"), ct("confidentiality", "super_cap"), ct("gross_negligence", "not_addressed"),
     ]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [
          ct("data_breach", "covered"), ct("confidentiality", "covered"),
      ])},
     {IX2: "ESCALATE"},
     notes="Two of three shared categories match -- must fire once, listing both.")

case("ix2-clear-negative", ["ix2", "clear_negative"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("willful_misconduct", "within_general_cap")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("willful_misconduct", "covered")])},
     {IX2: "NOT_TRIGGERED"})

case("ix2-missing-participant", ["ix2", "missing_participant"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")])},
     {IX2: "INSUFFICIENT_FACTS"})

case("ix2-upstream-requires-review", ["ix2", "upstream_requires_review"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "REQUIRES_REVIEW", []),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
     {IX2: "INSUFFICIENT_FACTS"})

case("ix2-superficially-similar-ip-only", ["ix2", "superficially_similar"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX2: "NOT_TRIGGERED"},
     notes="IP infringement alone belongs to rule 1, not rule 2 -- rule 2 must not double-fire on it.")

case("ix2-non-shared-category-fraud", ["ix2", "superficially_similar"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("fraud", "uncapped")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [])},
     {IX2: "NOT_TRIGGERED"},
     notes="'fraud' is a Liability-only category (not in Indemnification's trigger vocabulary) -- must never fire on it.")

# ===========================================================================
# Rule 3 — IX_INDEMNITY_WITHIN_GENERAL_CAP (informational DEPENDENCY)
# ===========================================================================

case("ix3-true-positive-within-cap", ["ix3", "true_positive"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
     {IX3: "ACCEPT_WITH_NOTE"})

case("ix3-true-positive-not-addressed", ["ix3", "true_positive"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("confidentiality", "not_addressed")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("confidentiality", "covered")])},
     {IX3: "ACCEPT_WITH_NOTE"})

case("ix3-clear-negative-uncapped-instead", ["ix3", "clear_negative"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
     {IX3: "NOT_TRIGGERED"},
     notes="Uncapped routes to rule 2 (CONFLICT), not rule 3 (DEPENDENCY) -- must not double-fire both.")

case("ix3-clear-negative-not-covered", ["ix3", "clear_negative"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("data_breach", "excluded")])},
     {IX3: "NOT_TRIGGERED"})

case("ix3-never-actionable", ["ix3", "accept_with_note_never_actionable"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
     {IX3: "ACCEPT_WITH_NOTE"},
     notes="ACCEPT_WITH_NOTE must never be classified actionable by the harness's own gate check.")

# ===========================================================================
# Rule 4 — IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY
# ===========================================================================

case("ix4-true-positive-liability-side-unresolved", ["ix4", "true_positive", "ambiguous_upstream"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "unresolved")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "not_addressed")])},
     {IX4: "REQUIRES_REVIEW"},
     notes="Per-category ambiguity on an otherwise-RESOLVED decision -- must fire even though decision.state is ACCEPT.")

case("ix4-true-positive-indemnification-side-unresolved", ["ix4", "true_positive", "ambiguous_upstream"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("data_breach", "unresolved")])},
     {IX4: "REQUIRES_REVIEW"})

case("ix4-clear-negative", ["ix4", "clear_negative"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX4: "NOT_TRIGGERED"})

# ===========================================================================
# Rule 5 — IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE
# ===========================================================================

case("ix5-true-positive", ["ix5", "true_positive"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
      "insurance": mk_decision("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
     {IX5: "ESCALATE"})

case("ix5-true-positive-super-cap", ["ix5", "true_positive"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "super_cap")]),
      "insurance": mk_decision("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
     {IX5: "ESCALATE"})

case("ix5-clear-negative-coverage-established", ["ix5", "clear_negative"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
      "insurance": mk_decision("insurance", "ACCEPT", [ct("cyber_liability", "established", established=True)])},
     {IX5: "NOT_TRIGGERED"})

case("ix5-clear-negative-within-cap", ["ix5", "clear_negative"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
      "insurance": mk_decision("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
     {IX5: "NOT_TRIGGERED"})

case("ix5-missing-participant-insurance", ["ix5", "missing_participant"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")])},
     {IX5: "INSUFFICIENT_FACTS"})

case("ix5-upstream-requires-review", ["ix5", "upstream_requires_review"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "REQUIRES_REVIEW", []),
      "insurance": mk_decision("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
     {IX5: "INSUFFICIENT_FACTS"})

case("ix5-superficially-similar-ip-category-no-mapping", ["ix5", "superficially_similar"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
      "insurance": mk_decision("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
     {IX5: "NOT_TRIGGERED"},
     notes="ip_infringement has no real insurance-product mapping (design doc S3.2) -- must never fire off it.")

case("ix5-superficially-similar-other-coverage-established", ["ix5", "superficially_similar"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
      "insurance": mk_decision("insurance", "ACCEPT", [ct("cgl", "established", established=True), ct("cyber_liability", "not_addressed", established=False)])},
     {IX5: "ESCALATE"},
     notes="CGL being established is irrelevant -- only cyber_liability's own established flag matters for data_breach.")

# ===========================================================================
# Rule 6 — IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING
# ===========================================================================

case("ix6-true-positive", ["ix6", "true_positive"],
     {"termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "immediate")]),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True, "service_credit_present": None})},
     {IX6: "ESCALATE"})

case("ix6-clear-negative-notice-and-cure", ["ix6", "clear_negative"],
     {"termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "notice_and_cure")]),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True, "service_credit_present": None})},
     {IX6: "NOT_TRIGGERED"})

case("ix6-clear-negative-withholding-false", ["ix6", "clear_negative"],
     {"termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "immediate")]),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": False, "service_credit_present": None})},
     {IX6: "NOT_TRIGGERED"})

case("ix6-clear-negative-withholding-unaddressed", ["ix6", "clear_negative"],
     {"termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "immediate")]),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": None})},
     {IX6: "NOT_TRIGGERED"},
     notes="None (never addressed) must never be treated as True -- absence is not affirmation.")

case("ix6-missing-participant-payment-terms", ["ix6", "missing_participant"],
     {"termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "immediate")])},
     {IX6: "INSUFFICIENT_FACTS"})

case("ix6-upstream-requires-review", ["ix6", "upstream_requires_review"],
     {"termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "immediate")]),
      "payment_terms": mk_decision("payment_terms", "REQUIRES_REVIEW", interaction_facts={})},
     {IX6: "INSUFFICIENT_FACTS"})

case("ix6-superficially-similar-material-breach-only", ["ix6", "superficially_similar"],
     {"termination": mk_decision("termination", "ACCEPT", [ct("material_breach", "immediate")]),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True, "service_credit_present": None})},
     {IX6: "NOT_TRIGGERED"},
     notes="An immediate material_breach right is not a non_payment right -- must not conflate trigger types.")

# ===========================================================================
# Rule 7 — IX_SLA_PAYMENT_CREDIT_DEPENDENCY
# ===========================================================================

case("ix7-true-positive", ["ix7", "true_positive"],
     {"sla": mk_decision("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": True})},
     {IX7: "REQUIRES_REVIEW"})

case("ix7-clear-negative-sla-only", ["ix7", "clear_negative"],
     {"sla": mk_decision("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": None})},
     {IX7: "NOT_TRIGGERED"})

case("ix7-clear-negative-payment-only", ["ix7", "clear_negative"],
     {"sla": mk_decision("sla", "ACCEPT", interaction_facts={"service_credit_present": False}),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": True})},
     {IX7: "NOT_TRIGGERED"})

case("ix7-clear-negative-neither", ["ix7", "clear_negative"],
     {"sla": mk_decision("sla", "ACCEPT", interaction_facts={"service_credit_present": None}),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": None})},
     {IX7: "NOT_TRIGGERED"})

case("ix7-missing-participant-sla", ["ix7", "missing_participant"],
     {"payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": True})},
     {IX7: "INSUFFICIENT_FACTS"})

case("ix7-upstream-not-applicable-sla", ["ix7", "upstream_not_applicable"],
     {"sla": mk_decision("sla", "NOT_APPLICABLE", interaction_facts={"service_credit_present": None}),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": True})},
     {IX7: "INSUFFICIENT_FACTS"},
     notes="No SLA clause exists at all -- must abstain, never assume no-SLA means no credit dependency.")

# ===========================================================================
# Cross-cutting: multiple simultaneous interactions in one review
# ===========================================================================

case("multi-two-independent-interactions-fire-together", ["multi_interaction"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped"), ct("data_breach", "uncapped")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered"), ct("data_breach", "covered")]),
      "insurance": mk_decision("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
      "termination": mk_decision("termination", "ACCEPT", [ct("non_payment", "immediate")]),
      "payment_terms": mk_decision("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True, "service_credit_present": None})},
     {IX1: "ESCALATE", IX2: "ESCALATE", IX5: "ESCALATE", IX6: "ESCALATE"},
     notes="Four independent rules fire in one review from overlapping but distinct participant sets -- each must reach its own correct state.")

case("multi-conflict-and-dependency-together", ["multi_interaction"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped"), ct("confidentiality", "within_general_cap")]),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered"), ct("confidentiality", "covered")])},
     {IX1: "ESCALATE", IX3: "ACCEPT_WITH_NOTE"},
     notes="A CONFLICT (ip_infringement) and a DEPENDENCY (confidentiality) fire simultaneously from the same two clause types -- kind must stay distinguishable per-rule.")

# ===========================================================================
# Cross-cutting: conflicting provisions (adapter-level reconciliation
# already unresolved) must propagate as abstention, never be guessed past.
# ===========================================================================

case("reconciliation-unreconciled-liability", ["conflicting_provisions"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "REQUIRES_REVIEW", []),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX1: "INSUFFICIENT_FACTS"},
     notes="Liability's own multi-provision reconciliation failed (REQUIRES_REVIEW) -- interaction layer must inherit the abstention, never pick one of the conflicting provisions itself.")

# ===========================================================================
# Cross-cutting: deterministic ordering — every rule always present, in
# LAUNCH_CATALOG's fixed order, regardless of which fired.
# ===========================================================================

# ===========================================================================
# Cross-cutting: amendments — the participating decision already reflects
# the adapter's own amendment resolution (reconciliation="amendment_
# resolved"); the interaction layer must read the resolved value, never
# re-derive or second-guess which provision controls.
# ===========================================================================

def _amended_liability_decision(treatment: str) -> PolicyDecision:
    d = mk_decision("limitation_of_liability", "ACCEPT", [ct("ip_infringement", treatment)])
    d.reconciliation = "amendment_resolved"
    return d


case("amendment-resolved-liability-uncapped", ["amendment"],
     {"limitation_of_liability": _amended_liability_decision("uncapped"),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX1: "ESCALATE"},
     notes="Liability's decision already reflects the amended (not the superseded) cap language -- interaction fires off the resolved value only.")

case("amendment-resolved-liability-within-cap", ["amendment"],
     {"limitation_of_liability": _amended_liability_decision("within_general_cap"),
      "indemnification": mk_decision("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
     {IX1: "NOT_TRIGGERED", IX3: "ACCEPT_WITH_NOTE"},
     notes="Same amendment machinery, opposite resolved value -- proves the interaction reads whatever the resolution actually settled on, not a fixed assumption.")

# ===========================================================================
# Cross-cutting: cross-references — a participating decision delegated to
# an unresolved Schedule/Exhibit surfaces as REQUIRES_REVIEW at the adapter
# level (see e.g. insurance_policy_engine.py's schedule_cross_reference /
# sla_policy_engine.py's schedule_cross_reference handling) -- the
# interaction layer must inherit that abstention via the same gate as any
# other REQUIRES_REVIEW participant, never treat "delegated to an exhibit"
# as equivalent to "not addressed."
# ===========================================================================

case("cross-reference-unresolved-insurance-schedule", ["cross_reference"],
     {"limitation_of_liability": mk_decision("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
      "insurance": mk_decision("insurance", "REQUIRES_REVIEW", [])},
     {IX5: "INSUFFICIENT_FACTS"},
     notes="Insurance clause delegates coverage terms to an unresolved Schedule -- must abstain, never treat as 'no coverage established' (which would be a false, overconfident CONFLICT).")

case("ordering-empty-decisions-all-seven-present-in-order", ["deterministic_ordering"],
     {},
     {IX1: "INSUFFICIENT_FACTS", IX2: "INSUFFICIENT_FACTS", IX3: "INSUFFICIENT_FACTS", IX4: "INSUFFICIENT_FACTS",
      IX5: "INSUFFICIENT_FACTS", IX6: "INSUFFICIENT_FACTS", IX7: "INSUFFICIENT_FACTS"},
     notes="No decisions at all -- every one of the seven rules must still be recorded as INSUFFICIENT_FACTS, never silently omitted.")
