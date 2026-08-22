"""Step 4B Phase 4 — 210+ case DEVELOPMENT interaction benchmark, ~30 cases
per rule (7 rules x 30 = 210). DEVELOPMENT evidence -- may be iterated
against. Not a final frozen corpus. Independent of, and does not replace
or rewrite, benchmarks/interaction_corpus.py (the existing 54-case
regression control).

Methodology: primarily fixture-based (constructed PolicyDecision objects,
bypassing extraction -- isolates interaction-predicate correctness from
any single adapter's own extraction quirks, per the design doc's own
recommended benchmark methodology), with a smaller end-to-end subset
(full contract text -> real adapters -> interaction engine) to prove the
wiring, not the logic, is correct -- see the END_TO_END_CASES section.

Ground truth predeclares, per case: participating policies, material
facts, fact establishment state, whether the interaction should fire,
expected interaction result, and notes distinguishing "no interaction
exists" from "interaction cannot be safely determined."
"""
from typing import Any, Dict, List, Optional

from policy_engine_core import PolicyDecision

CASES: List[Dict[str, Any]] = []
END_TO_END_CASES: List[Dict[str, Any]] = []


def pd(clause_type: str, state: str, category_treatments=None, interaction_facts=None,
       controlling_provision: Optional[Dict] = None, reconciliation: Optional[str] = None) -> PolicyDecision:
    return PolicyDecision(
        rule_id="TEST", clause_type=clause_type, state=state,
        contract_language="", extracted_summary="", policy_limit_summary="",
        required_action="", explanation="", negotiation_ladder=[],
        category_treatments=category_treatments or [], unresolved_facts=[],
        start_index=0, end_index=10,
        controlling_provision=controlling_provision if controlling_provision is not None else
        ({"label": f"{clause_type} clause", "excerpt": "...evidence...", "start_index": "0", "end_index": "10"} if state not in ("NOT_APPLICABLE",) else None),
        interaction_facts=interaction_facts or {},
        reconciliation=reconciliation,
    )


def ct(category, treatment, established=True):
    return {"category": category, "treatment": treatment, "cap_summary": "", "raw_excerpt": "", "established": established}


def case(cid: str, interaction_id: str, family: str, decisions: Dict[str, PolicyDecision],
         expected_state: str, notes: str = "") -> Dict[str, Any]:
    return {"id": cid, "interaction_id": interaction_id, "family": family,
            "decisions": decisions, "expected_state": expected_state, "notes": notes}


LIABILITY_CATEGORIES = ("ip_infringement", "data_breach", "confidentiality", "gross_negligence", "willful_misconduct")

# ===========================================================================
# Rule 1 — IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY (~30 cases)
# ===========================================================================
R1 = "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"
_R1 = []
# Family 1: both policies acceptable (no fire)
_R1 += [
    ("both-acceptable-1", pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "within_general_cap")]),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]), "NOT_TRIGGERED"),
    ("both-acceptable-2", pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "not_addressed")]),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "excluded")]), "NOT_TRIGGERED"),
]
# Family 2/3/4: Policy A violation only / Policy B violation only / both
_R1 += [
    ("liability-violation-only", pd("limitation_of_liability", "PROHIBITED", [ct("ip_infringement", "within_general_cap")]),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "not_addressed")]), "NOT_TRIGGERED"),
    ("indemnification-violation-only", pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "within_general_cap")]),
     pd("indemnification", "PROHIBITED", [ct("ip_infringement", "covered")]), "NOT_TRIGGERED"),
    ("both-violations-independent", pd("limitation_of_liability", "PROHIBITED", [ct("ip_infringement", "within_general_cap")]),
     pd("indemnification", "PROHIBITED", [ct("ip_infringement", "covered")]), "NOT_TRIGGERED"),
]
# Family 5: individually acceptable but problematic together (the flagship case)
_R1 += [
    ("problematic-together-1", pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]), "ESCALATE"),
    ("problematic-together-2", pd("limitation_of_liability", "ACCEPT_WITH_NOTE", [ct("ip_infringement", "super_cap")]),
     pd("indemnification", "ACCEPT_WITH_NOTE", [ct("ip_infringement", "covered")]), "ESCALATE"),
    ("problematic-together-negotiate-states", pd("limitation_of_liability", "NEGOTIATE", [ct("ip_infringement", "uncapped")]),
     pd("indemnification", "NEGOTIATE", [ct("ip_infringement", "covered")]), "ESCALATE"),
]
# Family 6/7: one established + one unresolved/conflicting
_R1 += [
    ("one-unresolved-liability", pd("limitation_of_liability", "REQUIRES_REVIEW"),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]), "INSUFFICIENT_FACTS"),
    ("one-unresolved-indemnification", pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
     pd("indemnification", "REQUIRES_REVIEW"), "INSUFFICIENT_FACTS"),
    ("one-error-liability", pd("limitation_of_liability", "EVALUATION_ERROR"),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]), "INSUFFICIENT_FACTS"),
]
# Family 8: one NOT_APPLICABLE
_R1 += [
    ("liability-not-applicable", pd("limitation_of_liability", "NOT_APPLICABLE"),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]), "INSUFFICIENT_FACTS"),
    ("indemnification-not-applicable", pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
     pd("indemnification", "NOT_APPLICABLE"), "INSUFFICIENT_FACTS"),
]
# Family 12/13: multiple provisions (reconciliation field populated)
_R1 += [
    ("multiple-provisions-amendment-resolved", pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")], reconciliation="amendment_resolved"),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]), "ESCALATE"),
    ("multiple-provisions-unreconciled", pd("limitation_of_liability", "REQUIRES_REVIEW", reconciliation="unreconciled"),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]), "INSUFFICIENT_FACTS"),
]
# Family 14: amendments
_R1 += [
    ("amendment-resolved-clean", pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "within_general_cap")], reconciliation="amendment_resolved"),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]), "NOT_TRIGGERED"),
]
# Family 20 (compound, other categories co-present)
_R1 += [
    ("compound-multiple-categories-present", pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped"), ct("data_breach", "within_general_cap")]),
     pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered"), ct("data_breach", "covered")]), "ESCALATE"),
]
for i, (fam, lia, ind, exp) in enumerate(_R1):
    CASES.append(case(f"dev-r1-{i:02d}", R1, fam, {"limitation_of_liability": lia, "indemnification": ind}, exp))
# top up to ~30 with parametrized variety across the remaining 4 categories
# (ip_infringement is rule 1's own category; use it consistently but vary
# the surrounding NON-matching category noise + state combinations)
_extra_states = ["ACCEPT", "ACCEPT_WITH_NOTE", "NEGOTIATE", "MUST_REDLINE", "ESCALATE"]
for i, extra_cat in enumerate(("data_breach", "confidentiality", "gross_negligence", "willful_misconduct")):
    for j, treat in enumerate(("uncapped", "within_general_cap")):
        lia = pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped"), ct(extra_cat, treat)])
        ind = pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered"), ct(extra_cat, "covered" if treat == "uncapped" else "not_addressed")])
        CASES.append(case(f"dev-r1-extra-{i}-{j}", R1, "compound-noise-category", {"limitation_of_liability": lia, "indemnification": ind}, "ESCALATE",
                           "extra co-present category must not suppress or alter the ip_infringement fire"))

# ===========================================================================
# Rule 2 — IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH (~30 cases)
# ===========================================================================
R2 = "IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH"
_NON_IP = ("data_breach", "confidentiality", "gross_negligence", "willful_misconduct")
for i, cat in enumerate(_NON_IP):
    CASES.append(case(f"dev-r2-single-{i}", R2, "single-category-fires",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(cat, "uncapped")]),
                        "indemnification": pd("indemnification", "ACCEPT", [ct(cat, "covered")])},
                       "ESCALATE"))
    CASES.append(case(f"dev-r2-single-supercap-{i}", R2, "single-category-fires-supercap",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(cat, "super_cap")]),
                        "indemnification": pd("indemnification", "ACCEPT", [ct(cat, "covered")])},
                       "ESCALATE"))
    CASES.append(case(f"dev-r2-single-noFire-{i}", R2, "single-category-benign",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(cat, "within_general_cap")]),
                        "indemnification": pd("indemnification", "ACCEPT", [ct(cat, "covered")])},
                       "NOT_TRIGGERED"))
# multi-category merges (family 20 compound)
CASES.append(case("dev-r2-multi-2cat", R2, "compound-two-categories",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped"), ct("confidentiality", "uncapped")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered"), ct("confidentiality", "covered")])},
                   "ESCALATE"))
CASES.append(case("dev-r2-multi-4cat", R2, "compound-all-four-categories",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(c, "uncapped") for c in _NON_IP]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct(c, "covered") for c in _NON_IP])},
                   "ESCALATE"))
# unresolved/error/not_applicable participants
CASES.append(case("dev-r2-review", R2, "one-unresolved",
                   {"limitation_of_liability": pd("limitation_of_liability", "REQUIRES_REVIEW"),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r2-na", R2, "not-applicable",
                   {"limitation_of_liability": pd("limitation_of_liability", "NOT_APPLICABLE"),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r2-error", R2, "evaluation-error",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
                    "indemnification": pd("indemnification", "EVALUATION_ERROR")},
                   "INSUFFICIENT_FACTS"))
# amendment/reconciliation
CASES.append(case("dev-r2-amendment", R2, "amendment-resolved",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")], reconciliation="amendment_resolved"),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "ESCALATE"))
CASES.append(case("dev-r2-unreconciled", R2, "unreconciled-blocks",
                   {"limitation_of_liability": pd("limitation_of_liability", "REQUIRES_REVIEW", reconciliation="unreconciled"),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "INSUFFICIENT_FACTS"))
# both violation states independently (should not affect category match logic)
CASES.append(case("dev-r2-both-negotiate", R2, "both-negotiate-states",
                   {"limitation_of_liability": pd("limitation_of_liability", "NEGOTIATE", [ct("gross_negligence", "uncapped")]),
                    "indemnification": pd("indemnification", "NEGOTIATE", [ct("gross_negligence", "covered")])},
                   "ESCALATE"))
CASES.append(case("dev-r2-both-mustredline", R2, "both-must-redline",
                   {"limitation_of_liability": pd("limitation_of_liability", "MUST_REDLINE", [ct("willful_misconduct", "super_cap")]),
                    "indemnification": pd("indemnification", "MUST_REDLINE", [ct("willful_misconduct", "covered")])},
                   "ESCALATE"))
# missing participant families
CASES.append(case("dev-r2-missing", R2, "missing-participant",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")])},
                   "INSUFFICIENT_FACTS"))
# both acceptable, no shared risk
CASES.append(case("dev-r2-both-clean", R2, "both-acceptable",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(c, "within_general_cap") for c in _NON_IP]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct(c, "not_addressed") for c in _NON_IP])},
                   "NOT_TRIGGERED"))

# ===========================================================================
# Rule 3 — IX_INDEMNITY_WITHIN_GENERAL_CAP (~28 cases)
# Informational DEPENDENCY: liability treatment in {within_general_cap,
# not_addressed} AND indemnification treatment == covered, across ALL 5
# shared categories (including ip_infringement, unlike rules 1/2/4).
# ===========================================================================
R3 = "IX_INDEMNITY_WITHIN_GENERAL_CAP"
for i, cat in enumerate(LIABILITY_CATEGORIES):
    CASES.append(case(f"dev-r3-within-{i}", R3, "dependency-fires-within-cap",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(cat, "within_general_cap")]),
                        "indemnification": pd("indemnification", "ACCEPT", [ct(cat, "covered")])},
                       "ACCEPT_WITH_NOTE"))
    CASES.append(case(f"dev-r3-notaddressed-{i}", R3, "dependency-fires-not-addressed",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(cat, "not_addressed")]),
                        "indemnification": pd("indemnification", "ACCEPT", [ct(cat, "covered")])},
                       "ACCEPT_WITH_NOTE"))
    CASES.append(case(f"dev-r3-nofire-uncapped-{i}", R3, "no-fire-uncapped-not-within-cap",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(cat, "uncapped")]),
                        "indemnification": pd("indemnification", "ACCEPT", [ct(cat, "covered")])},
                       "NOT_TRIGGERED", "uncapped is out of this rule's scope, not merely benign"))
    CASES.append(case(f"dev-r3-nofire-notcovered-{i}", R3, "no-fire-indemnity-excluded",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(cat, "within_general_cap")]),
                        "indemnification": pd("indemnification", "ACCEPT", [ct(cat, "excluded")])},
                       "NOT_TRIGGERED"))
CASES.append(case("dev-r3-multi-category", R3, "compound-multiple-categories",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(c, "within_general_cap") for c in LIABILITY_CATEGORIES]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct(c, "covered") for c in LIABILITY_CATEGORIES])},
                   "ACCEPT_WITH_NOTE"))
CASES.append(case("dev-r3-mixed-scope", R3, "compound-only-some-categories-in-scope",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "within_general_cap"), ct("data_breach", "uncapped")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered"), ct("data_breach", "covered")])},
                   "ACCEPT_WITH_NOTE", "this case is evaluated against Rule 3 only; ip_infringement (within_general_cap+covered) matches Rule 3's condition even though the co-present data_breach (uncapped+covered) would separately fire Rule 2's ESCALATE if evaluated against that rule -- rules are evaluated independently, not merged"))
CASES.append(case("dev-r3-review", R3, "one-unresolved",
                   {"limitation_of_liability": pd("limitation_of_liability", "REQUIRES_REVIEW"),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("confidentiality", "covered")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r3-na", R3, "not-applicable",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("confidentiality", "within_general_cap")]),
                    "indemnification": pd("indemnification", "NOT_APPLICABLE")},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r3-missing", R3, "missing-participant",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("confidentiality", "within_general_cap")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r3-amendment", R3, "amendment-resolved",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("gross_negligence", "within_general_cap")], reconciliation="amendment_resolved"),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("gross_negligence", "covered")])},
                   "ACCEPT_WITH_NOTE"))
CASES.append(case("dev-r3-clean-no-overlap", R3, "both-acceptable",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("willful_misconduct", "uncapped")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("willful_misconduct", "excluded")])},
                   "NOT_TRIGGERED"))

# ===========================================================================
# Rule 4 — IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY (~26 cases)
# category_treatments[cat].treatment == "unresolved" on either side, across
# all 5 shared categories, even when the decision-level state is resolved
# (this is the mechanism distinct from generic decision-level gating).
# ===========================================================================
R4 = "IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY"
for i, cat in enumerate(LIABILITY_CATEGORIES):
    CASES.append(case(f"dev-r4-liability-unresolved-{i}", R4, "conflicting-definitions-liability-side",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(cat, "unresolved")]),
                        "indemnification": pd("indemnification", "ACCEPT", [ct(cat, "covered")])},
                       "REQUIRES_REVIEW"))
    CASES.append(case(f"dev-r4-indemnity-unresolved-{i}", R4, "conflicting-definitions-indemnity-side",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(cat, "within_general_cap")]),
                        "indemnification": pd("indemnification", "ACCEPT", [ct(cat, "unresolved")])},
                       "REQUIRES_REVIEW"))
    CASES.append(case(f"dev-r4-nofire-resolved-{i}", R4, "no-fire-both-resolved",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(cat, "within_general_cap")]),
                        "indemnification": pd("indemnification", "ACCEPT", [ct(cat, "covered")])},
                       "NOT_TRIGGERED"))
CASES.append(case("dev-r4-both-unresolved-same-cat", R4, "conflicting-definitions-both-sides",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "unresolved")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "unresolved")])},
                   "REQUIRES_REVIEW"))
CASES.append(case("dev-r4-multi-category-ambiguous", R4, "compound-multiple-ambiguous-categories",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "unresolved"), ct("confidentiality", "unresolved")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered"), ct("confidentiality", "covered")])},
                   "REQUIRES_REVIEW"))
CASES.append(case("dev-r4-decision-level-review-not-category", R4, "decision-review-but-no-category-ambiguity",
                   {"limitation_of_liability": pd("limitation_of_liability", "REQUIRES_REVIEW"),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "INSUFFICIENT_FACTS", "whole-decision REQUIRES_REVIEW is gated generically before Rule 4's own predicate ever runs"))
CASES.append(case("dev-r4-na", R4, "not-applicable",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "unresolved")]),
                    "indemnification": pd("indemnification", "NOT_APPLICABLE")},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r4-missing", R4, "missing-participant",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "unresolved")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r4-amendment", R4, "amendment-resolved",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("confidentiality", "unresolved")], reconciliation="amendment_resolved"),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("confidentiality", "covered")])},
                   "REQUIRES_REVIEW"))
CASES.append(case("dev-r4-clean", R4, "both-acceptable",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct(c, "within_general_cap") for c in LIABILITY_CATEGORIES]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct(c, "covered") for c in LIABILITY_CATEGORIES])},
                   "NOT_TRIGGERED"))

# ===========================================================================
# Rule 5 — IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE (~26 cases)
# data_breach only; liability treatment uncapped/super_cap AND insurance's
# cyber_liability category_treatments entry has established=False.
# ===========================================================================
R5 = "IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE"
_R5 = [
    ("fires-uncapped", pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
     pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]), "ESCALATE"),
    ("fires-supercap", pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "super_cap")]),
     pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]), "ESCALATE"),
    ("nofire-insurance-established", pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
     pd("insurance", "ACCEPT", [ct("cyber_liability", "required", established=True)]), "NOT_TRIGGERED"),
    ("nofire-liability-within-cap", pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
     pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]), "NOT_TRIGGERED"),
    ("nofire-other-category-only", pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
     pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]), "NOT_TRIGGERED",
     "ip_infringement has no insurance mapping by design -- must not generalize"),
    ("nofire-no-data-breach-treatment", pd("limitation_of_liability", "ACCEPT", [ct("confidentiality", "uncapped")]),
     pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]), "NOT_TRIGGERED"),
    ("one-unresolved-liability", pd("limitation_of_liability", "REQUIRES_REVIEW"),
     pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]), "INSUFFICIENT_FACTS"),
    ("one-unresolved-insurance", pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
     pd("insurance", "REQUIRES_REVIEW"), "INSUFFICIENT_FACTS"),
    ("insurance-not-applicable", pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
     pd("insurance", "NOT_APPLICABLE"), "INSUFFICIENT_FACTS"),
    ("liability-not-applicable", pd("limitation_of_liability", "NOT_APPLICABLE"),
     pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]), "INSUFFICIENT_FACTS"),
    ("evaluation-error", pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
     pd("insurance", "EVALUATION_ERROR"), "INSUFFICIENT_FACTS"),
    ("amendment-resolved", pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")], reconciliation="amendment_resolved"),
     pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]), "ESCALATE"),
    ("both-negotiate-states", pd("limitation_of_liability", "NEGOTIATE", [ct("data_breach", "uncapped")]),
     pd("insurance", "NEGOTIATE", [ct("cyber_liability", "not_addressed", established=False)]), "ESCALATE"),
]
for i, row in enumerate(_R5):
    fam, lia, ins, exp = row[0], row[1], row[2], row[3]
    notes = row[4] if len(row) > 4 else ""
    CASES.append(case(f"dev-r5-{i:02d}", R5, fam, {"limitation_of_liability": lia, "insurance": ins}, exp, notes))
CASES.append(case("dev-r5-missing", R5, "missing-participant",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r5-compound-with-r1", R5, "compound-interaction",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped"), ct("ip_infringement", "uncapped")]),
                    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
                   "ESCALATE", "co-present ip_infringement uncapped fires Rule 1 separately (indemnification not a Rule 5 participant); Rule 5 fires independently on data_breach/insurance"))
for i, treat in enumerate(("within_general_cap", "not_addressed")):
    CASES.append(case(f"dev-r5-established-variants-{i}", R5, "no-fire-established-variant",
                       {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", treat)]),
                        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "required", established=True)])},
                       "NOT_TRIGGERED"))

# ===========================================================================
# Rule 6 — IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING (~30 cases)
# Directional rule -- termination.non_payment == "immediate" (counterparty
# right only, by upstream adapter construction) AND
# payment_terms.interaction_facts["disputed_amounts_withholdable"] is True.
# ===========================================================================
R6 = "IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING"
_R6 = [
    ("fires-clean", pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
     pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}), "ESCALATE"),
    ("nofire-cure-period", pd("termination", "ACCEPT", [ct("non_payment", "cure_period")]),
     pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}), "NOT_TRIGGERED"),
    ("nofire-not-withholdable", pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
     pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": False}), "NOT_TRIGGERED"),
    ("nofire-withholdable-unestablished", pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
     pd("payment_terms", "ACCEPT", interaction_facts={}), "NOT_TRIGGERED",
     "unestablished (absent key, None) must not be treated as True"),
    ("nofire-no-nonpayment-category", pd("termination", "ACCEPT", [ct("convenience", "immediate")]),
     pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}), "NOT_TRIGGERED"),
    ("role-reversal-our-right-not-theirs", pd("termination", "ACCEPT", []),
     pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}), "NOT_TRIGGERED",
     "no non_payment category_treatments entry at all -- our-side-only rights are never surfaced into category_treatments per adapter's their_rights construction, so this represents the role-reversed scenario correctly resolving to no-fire"),
    ("one-unresolved-termination", pd("termination", "REQUIRES_REVIEW"),
     pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}), "INSUFFICIENT_FACTS"),
    ("one-unresolved-payment", pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
     pd("payment_terms", "REQUIRES_REVIEW"), "INSUFFICIENT_FACTS"),
    ("termination-not-applicable", pd("termination", "NOT_APPLICABLE"),
     pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}), "INSUFFICIENT_FACTS"),
    ("payment-not-applicable", pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
     pd("payment_terms", "NOT_APPLICABLE"), "INSUFFICIENT_FACTS"),
    ("evaluation-error", pd("termination", "EVALUATION_ERROR"),
     pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}), "INSUFFICIENT_FACTS"),
    ("amendment-resolved", pd("termination", "ACCEPT", [ct("non_payment", "immediate")], reconciliation="amendment_resolved"),
     pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}), "ESCALATE"),
    ("both-negotiate-states", pd("termination", "NEGOTIATE", [ct("non_payment", "immediate")]),
     pd("payment_terms", "NEGOTIATE", interaction_facts={"disputed_amounts_withholdable": True}), "ESCALATE"),
    ("conditional-notice-then-immediate", pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
     pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}), "ESCALATE",
     "conditional-applicability family: immediate right conditioned elsewhere in the clause on a threshold, but adapter has already resolved category_treatments to immediate -- interaction layer trusts the upstream resolved fact"),
]
for i, row in enumerate(_R6):
    fam, term, pay, exp = row[0], row[1], row[2], row[3]
    notes = row[4] if len(row) > 4 else ""
    CASES.append(case(f"dev-r6-{i:02d}", R6, fam, {"termination": term, "payment_terms": pay}, exp, notes))
CASES.append(case("dev-r6-missing", R6, "missing-participant",
                   {"termination": pd("termination", "ACCEPT", [ct("non_payment", "immediate")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r6-duplicate-category", R6, "duplicate-evidence-non_payment",
                   {"termination": pd("termination", "ACCEPT", [ct("non_payment", "immediate"), ct("non_payment", "cure_period")]),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                   "NOT_TRIGGERED", "duplicated category key -- last dict entry wins per _by_category's dict comprehension, so cure_period (not immediate) governs; documented, not a defect -- verified against the real _by_category mechanism before predeclaring, per the mb-r1-06 lesson"))
for i, cat in enumerate(("late_fee", "notice_period")):
    CASES.append(case(f"dev-r6-noise-category-{i}", R6, "compound-noise-category",
                       {"termination": pd("termination", "ACCEPT", [ct("non_payment", "immediate"), ct(cat, "established")]),
                        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                       "ESCALATE", "unrelated co-present termination category must not suppress the fire"))
CASES.append(case("dev-r6-compound-with-r1", R6, "compound-interaction",
                   {"termination": pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                   "ESCALATE"))
CASES.append(case("dev-r6-non-operative-recital", R6, "non-operative-text",
                   {"termination": pd("termination", "ACCEPT", [ct("non_payment", "immediate")],
                                      controlling_provision={"label": "Recitals reference only", "excerpt": "WHEREAS the parties may terminate...", "start_index": "0", "end_index": "10"}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                   "ESCALATE", "operative-vs-non-operative classification is an upstream Step 4A adapter responsibility; interaction layer trusts the already-resolved category_treatments regardless of the evidence excerpt's own textual framing"))

# ===========================================================================
# Rule 7 — IX_SLA_PAYMENT_CREDIT_DEPENDENCY (~26 cases)
# Both sla.interaction_facts["service_credit_present"] and
# payment_terms.interaction_facts["service_credit_present"] must be True.
# ===========================================================================
R7 = "IX_SLA_PAYMENT_CREDIT_DEPENDENCY"
_R7 = [
    ("fires-both-present", pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
     pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}), "REQUIRES_REVIEW"),
    ("nofire-sla-only", pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
     pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": False}), "NOT_TRIGGERED"),
    ("nofire-payment-only", pd("sla", "ACCEPT", interaction_facts={"service_credit_present": False}),
     pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}), "NOT_TRIGGERED"),
    ("nofire-neither", pd("sla", "ACCEPT", interaction_facts={"service_credit_present": False}),
     pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": False}), "NOT_TRIGGERED"),
    ("nofire-sla-unestablished-key-absent", pd("sla", "ACCEPT", interaction_facts={}),
     pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}), "NOT_TRIGGERED",
     "unestablished (absent key) must not be treated as True"),
    ("one-unresolved-sla", pd("sla", "REQUIRES_REVIEW"),
     pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}), "INSUFFICIENT_FACTS"),
    ("one-unresolved-payment", pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
     pd("payment_terms", "REQUIRES_REVIEW"), "INSUFFICIENT_FACTS"),
    ("sla-not-applicable", pd("sla", "NOT_APPLICABLE"),
     pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}), "INSUFFICIENT_FACTS"),
    ("payment-not-applicable", pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
     pd("payment_terms", "NOT_APPLICABLE"), "INSUFFICIENT_FACTS"),
    ("evaluation-error", pd("sla", "EVALUATION_ERROR"),
     pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}), "INSUFFICIENT_FACTS"),
    ("amendment-resolved", pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}, reconciliation="amendment_resolved"),
     pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}), "REQUIRES_REVIEW"),
    ("both-negotiate-states", pd("sla", "NEGOTIATE", interaction_facts={"service_credit_present": True}),
     pd("payment_terms", "NEGOTIATE", interaction_facts={"service_credit_present": True}), "REQUIRES_REVIEW"),
]
for i, row in enumerate(_R7):
    fam, sla, pay, exp = row[0], row[1], row[2], row[3]
    notes = row[4] if len(row) > 4 else ""
    CASES.append(case(f"dev-r7-{i:02d}", R7, fam, {"sla": sla, "payment_terms": pay}, exp, notes))
CASES.append(case("dev-r7-missing", R7, "missing-participant",
                   {"sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r7-cross-reference", R7, "cross-reference",
                   {"sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True},
                              controlling_provision={"label": "SLA clause (cross-referencing Exhibit B)", "excerpt": "...as further detailed in Exhibit B...", "start_index": "0", "end_index": "10"}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "REQUIRES_REVIEW", "cross-reference resolution is an upstream adapter responsibility; interaction layer trusts the already-resolved interaction_facts regardless of the evidence excerpt referencing an exhibit"))
CASES.append(case("dev-r7-duplicate-evidence", R7, "duplicate-evidence",
                   {"sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "REQUIRES_REVIEW"))

# ===========================================================================
# Top-up block: additional cases per rule to reach the ~30/rule /
# 210+ total target, exercising the remaining mandatory case families
# (non-operative text, conditional applicability, additional violation
# states, multiple-provisions/reconciliation, role/wrong-participant-key)
# not yet exercised for each rule above.
# ===========================================================================

# --- Rule 1 top-up (conditional applicability, non-operative text, wrong participant key) ---
CASES.append(case("dev-r1-conditional-applicability", R1, "conditional-applicability",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
                   "ESCALATE", "conditional carve-out already resolved upstream by the adapter into a flat uncapped treatment -- interaction layer trusts the resolved fact, does not re-parse the condition"))
CASES.append(case("dev-r1-non-operative-text", R1, "non-operative-text",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")],
                                                   controlling_provision={"label": "Recitals", "excerpt": "WHEREAS liability may be uncapped for IP...", "start_index": "0", "end_index": "10"}),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
                   "ESCALATE", "operative/non-operative classification is upstream adapter responsibility; interaction layer trusts the resolved category_treatments regardless of evidence excerpt framing"))
CASES.append(case("dev-r1-wrong-participant-key", R1, "wrong-participant-key",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")]),
                    "indemnity": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
                   "INSUFFICIENT_FACTS", "decisions dict keyed 'indemnity' instead of 'indemnification' -- indemnification participant effectively missing"))
for i, extra_state in enumerate(("ACCEPT_WITH_NOTE", "MUST_REDLINE")):
    CASES.append(case(f"dev-r1-topup-state-{i}", R1, "problematic-together-state-variety",
                       {"limitation_of_liability": pd("limitation_of_liability", extra_state, [ct("ip_infringement", "uncapped")]),
                        "indemnification": pd("indemnification", extra_state, [ct("ip_infringement", "covered")])},
                       "ESCALATE"))

# --- Rule 2 top-up (non-operative, conditional applicability, wrong participant) ---
CASES.append(case("dev-r2-conditional-applicability", R2, "conditional-applicability",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("confidentiality", "super_cap")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("confidentiality", "covered")])},
                   "ESCALATE"))
CASES.append(case("dev-r2-non-operative-text", R2, "non-operative-text",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("gross_negligence", "uncapped")],
                                                   controlling_provision={"label": "Definitions section", "excerpt": "\"Gross Negligence\" means...", "start_index": "0", "end_index": "10"}),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("gross_negligence", "covered")])},
                   "ESCALATE"))
CASES.append(case("dev-r2-wrong-participant-key", R2, "wrong-participant-key",
                   {"limitation": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r2-role-reversal-not-applicable", R2, "role-reversal",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("willful_misconduct", "uncapped")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "NOT_TRIGGERED", "categories must match on BOTH sides for the same category -- liability's willful_misconduct and indemnification's data_breach do not overlap"))
CASES.append(case("dev-r2-topup-mustredline-negotiate-mix", R2, "mixed-violation-states",
                   {"limitation_of_liability": pd("limitation_of_liability", "MUST_REDLINE", [ct("confidentiality", "super_cap")]),
                    "indemnification": pd("indemnification", "NEGOTIATE", [ct("confidentiality", "covered")])},
                   "ESCALATE"))

# --- Rule 3 top-up ---
CASES.append(case("dev-r3-non-operative-text", R3, "non-operative-text",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")],
                                                   controlling_provision={"label": "Preamble", "excerpt": "This Agreement is entered into...", "start_index": "0", "end_index": "10"}),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "ACCEPT_WITH_NOTE"))
CASES.append(case("dev-r3-wrong-participant-key", R3, "wrong-participant-key",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
                    "indemnify": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r3-conditional-applicability", R3, "conditional-applicability",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("gross_negligence", "not_addressed")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("gross_negligence", "covered")])},
                   "ACCEPT_WITH_NOTE"))

# --- Rule 4 top-up ---
CASES.append(case("dev-r4-non-operative-text", R4, "non-operative-text",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("willful_misconduct", "unresolved")],
                                                   controlling_provision={"label": "Table of contents reference", "excerpt": "See Section 8...", "start_index": "0", "end_index": "10"}),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("willful_misconduct", "covered")])},
                   "REQUIRES_REVIEW"))
CASES.append(case("dev-r4-wrong-participant-key", R4, "wrong-participant-key",
                   {"liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "unresolved")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r4-conditional-applicability", R4, "conditional-applicability",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "unresolved")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])},
                   "REQUIRES_REVIEW"))

# --- Rule 5 top-up ---
CASES.append(case("dev-r5-non-operative-text", R5, "non-operative-text",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")],
                                                   controlling_provision={"label": "Table of contents", "excerpt": "8. Insurance...", "start_index": "0", "end_index": "10"}),
                    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
                   "ESCALATE"))
CASES.append(case("dev-r5-wrong-participant-key", R5, "wrong-participant-key",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
                    "insurance_policy": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r5-conditional-applicability", R5, "conditional-applicability",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "super_cap")]),
                    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
                   "ESCALATE"))
CASES.append(case("dev-r5-duplicate-category", R5, "duplicate-evidence",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped"), ct("data_breach", "within_general_cap")]),
                    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
                   "NOT_TRIGGERED", "duplicated data_breach category -- last entry (within_general_cap) wins, does not satisfy uncapped/super_cap"))

# --- Rule 6 top-up ---
CASES.append(case("dev-r6-wrong-participant-key", R6, "wrong-participant-key",
                   {"terminations": pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r6-direction-reversal-explicit", R6, "direction-reversal",
                   {"termination": pd("termination", "ACCEPT", [ct("non_payment", "not_established")]),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                   "NOT_TRIGGERED", "non_payment present but treatment is neither 'immediate' nor absent -- distinct value must not be conflated with the trigger value"))
for i, treat in enumerate(("notice_only", "mutual")):
    CASES.append(case(f"dev-r6-topup-treatment-{i}", R6, "no-fire-other-treatment-values",
                       {"termination": pd("termination", "ACCEPT", [ct("non_payment", treat)]),
                        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                       "NOT_TRIGGERED"))

# --- Rule 7 top-up ---
CASES.append(case("dev-r7-wrong-participant-key", R7, "wrong-participant-key",
                   {"service_level_agreement": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r7-non-operative-text", R7, "non-operative-text",
                   {"sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True},
                              controlling_provision={"label": "Table of contents", "excerpt": "9. Service Level Agreement...", "start_index": "0", "end_index": "10"}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "REQUIRES_REVIEW"))
CASES.append(case("dev-r7-conditional-applicability", R7, "conditional-applicability",
                   {"sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "REQUIRES_REVIEW", "credit presence already resolved upstream regardless of any triggering condition text"))
for i, treat in enumerate(("MUST_REDLINE", "ESCALATE")):
    CASES.append(case(f"dev-r7-topup-state-{i}", R7, "violation-state-variety",
                       {"sla": pd("sla", treat, interaction_facts={"service_credit_present": True}),
                        "payment_terms": pd("payment_terms", treat, interaction_facts={"service_credit_present": True})},
                       "REQUIRES_REVIEW"))

# ===========================================================================
# Second top-up round: close the remaining gap to 210+ total / push every
# rule to >=30, using fresh combinations not yet exercised above.
# ===========================================================================

# --- Rule 2 second top-up (reach 30) ---
CASES.append(case("dev-r2-multi-3cat", R2, "compound-three-categories",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "super_cap"), ct("confidentiality", "uncapped"), ct("gross_negligence", "super_cap")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered"), ct("confidentiality", "covered"), ct("gross_negligence", "covered")])},
                   "ESCALATE"))
CASES.append(case("dev-r2-duplicate-category", R2, "duplicate-evidence",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped"), ct("data_breach", "within_general_cap")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "NOT_TRIGGERED", "duplicated data_breach category -- last entry wins (within_general_cap), not uncapped/super_cap"))

# --- Rule 4 second top-up (reach 30) ---
CASES.append(case("dev-r4-duplicate-category", R4, "duplicate-evidence",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "unresolved"), ct("data_breach", "within_general_cap")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "NOT_TRIGGERED", "duplicated data_breach category -- last entry (within_general_cap) wins, not unresolved"))
CASES.append(case("dev-r4-multiple-provisions-unreconciled", R4, "multiple-provisions",
                   {"limitation_of_liability": pd("limitation_of_liability", "REQUIRES_REVIEW", reconciliation="unreconciled"),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r4-role-reversal-mismatched-category", R4, "role-reversal",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "unresolved")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "unresolved")])},
                   "REQUIRES_REVIEW", "ambiguity check is per-category-independent: any ambiguous category on either side fires, even without cross-category overlap -- both ip_infringement and data_breach independently contribute to the ambiguous set"))

# --- Rule 5 second top-up (reach 30) ---
CASES.append(case("dev-r5-multiple-provisions-unreconciled", R5, "multiple-provisions",
                   {"limitation_of_liability": pd("limitation_of_liability", "REQUIRES_REVIEW", reconciliation="unreconciled"),
                    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r5-both-mustredline", R5, "both-must-redline",
                   {"limitation_of_liability": pd("limitation_of_liability", "MUST_REDLINE", [ct("data_breach", "super_cap")]),
                    "insurance": pd("insurance", "MUST_REDLINE", [ct("cyber_liability", "not_addressed", established=False)])},
                   "ESCALATE"))
CASES.append(case("dev-r5-role-reversal-not-cyber", R5, "role-reversal",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
                    "insurance": pd("insurance", "ACCEPT", [ct("general_liability", "required", established=True)])},
                   "NOT_TRIGGERED", "insurance established a DIFFERENT coverage type (general_liability); cyber_liability key itself is absent, so the predicate's it lookup is None"))

# --- Rule 6 second top-up (reach 30) ---
CASES.append(case("dev-r6-multiple-provisions-unreconciled", R6, "multiple-provisions",
                   {"termination": pd("termination", "REQUIRES_REVIEW", reconciliation="unreconciled"),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r6-both-mustredline", R6, "both-must-redline",
                   {"termination": pd("termination", "MUST_REDLINE", [ct("non_payment", "immediate")]),
                    "payment_terms": pd("payment_terms", "MUST_REDLINE", interaction_facts={"disputed_amounts_withholdable": True})},
                   "ESCALATE"))
CASES.append(case("dev-r6-both-error", R6, "compound-both-error",
                   {"termination": pd("termination", "EVALUATION_ERROR"),
                    "payment_terms": pd("payment_terms", "EVALUATION_ERROR")},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r6-conflicting-definitions", R6, "conflicting-definitions",
                   {"termination": pd("termination", "ACCEPT", [ct("non_payment", "unresolved")]),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                   "NOT_TRIGGERED", "'unresolved' is not the trigger value 'immediate' -- Rule 6 has no separate ambiguity-escalation mechanism like Rule 4's; an ambiguous non_payment treatment simply does not satisfy the equality check"))
CASES.append(case("dev-r6-cross-reference", R6, "cross-reference",
                   {"termination": pd("termination", "ACCEPT", [ct("non_payment", "immediate")],
                                       controlling_provision={"label": "Termination clause (cross-referencing Section 5)", "excerpt": "...subject to Section 5 payment terms...", "start_index": "0", "end_index": "10"}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                   "ESCALATE"))

# --- Rule 7 second top-up (reach 30) ---
CASES.append(case("dev-r7-multiple-provisions-unreconciled", R7, "multiple-provisions",
                   {"sla": pd("sla", "REQUIRES_REVIEW", reconciliation="unreconciled"),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r7-both-mustredline", R7, "both-must-redline",
                   {"sla": pd("sla", "MUST_REDLINE", interaction_facts={"service_credit_present": True}),
                    "payment_terms": pd("payment_terms", "MUST_REDLINE", interaction_facts={"service_credit_present": True})},
                   "REQUIRES_REVIEW"))
CASES.append(case("dev-r7-both-error", R7, "compound-both-error",
                   {"sla": pd("sla", "EVALUATION_ERROR"),
                    "payment_terms": pd("payment_terms", "EVALUATION_ERROR")},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r7-role-reversal-not-sla-credit", R7, "role-reversal",
                   {"sla": pd("sla", "ACCEPT", interaction_facts={"other_remedy_present": True}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "NOT_TRIGGERED", "sla's interaction_facts has a different key present ('other_remedy_present'); 'service_credit_present' itself is absent (None), so no fire"))

# ===========================================================================
# Third, final top-up: push every remaining under-30 rule (4, 5, 6, 7) to
# >=30 and the corpus total to 210+.
# ===========================================================================
CASES.append(case("dev-r4-amendment-unreconciled", R4, "amendments",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "unresolved")], reconciliation="superseded"),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])},
                   "REQUIRES_REVIEW"))
CASES.append(case("dev-r4-compound-with-r1", R4, "compound-interaction",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped"), ct("confidentiality", "unresolved")]),
                    "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered"), ct("confidentiality", "covered")])},
                   "REQUIRES_REVIEW", "co-present ip_infringement uncapped fires Rule 1 separately; Rule 4 independently fires on the unresolved confidentiality category"))

CASES.append(case("dev-r5-amendment-superseded", R5, "amendments",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")], reconciliation="superseded"),
                    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
                   "ESCALATE"))
CASES.append(case("dev-r5-cross-reference", R5, "cross-reference",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")],
                                                   controlling_provision={"label": "Liability clause (cross-referencing Exhibit C)", "excerpt": "...as set forth in Exhibit C...", "start_index": "0", "end_index": "10"}),
                    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])},
                   "ESCALATE"))

CASES.append(case("dev-r6-amendment-superseded", R6, "amendments",
                   {"termination": pd("termination", "ACCEPT", [ct("non_payment", "immediate")], reconciliation="superseded"),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})},
                   "ESCALATE"))

CASES.append(case("dev-r7-amendment-superseded", R7, "amendments",
                   {"sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}, reconciliation="superseded"),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "REQUIRES_REVIEW"))
CASES.append(case("dev-r7-compound-with-r3", R7, "compound-interaction",
                   {"sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "REQUIRES_REVIEW"))
CASES.append(case("dev-r7-payment-not-established-explicit-false", R7, "no-fire-explicit-false",
                   {"sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": False})},
                   "NOT_TRIGGERED"))
CASES.append(case("dev-r7-both-negotiate-mixed-with-review", R7, "one-established-one-negotiate",
                   {"sla": pd("sla", "REQUIRES_REVIEW"),
                    "payment_terms": pd("payment_terms", "NEGOTIATE", interaction_facts={"service_credit_present": True})},
                   "INSUFFICIENT_FACTS"))

CASES.append(case("dev-r6-payment-not-established-explicit-false", R6, "no-fire-explicit-false",
                   {"termination": pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": False})},
                   "NOT_TRIGGERED"))
CASES.append(case("dev-r6-one-established-one-review", R6, "one-established-one-unresolved",
                   {"termination": pd("termination", "REQUIRES_REVIEW"),
                    "payment_terms": pd("payment_terms", "NEGOTIATE", interaction_facts={"disputed_amounts_withholdable": True})},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r6-multiple-provisions-payment", R6, "multiple-provisions",
                   {"termination": pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}, reconciliation="amendment_resolved")},
                   "ESCALATE"))

CASES.append(case("dev-r7-one-established-one-error", R7, "one-established-one-error",
                   {"sla": pd("sla", "EVALUATION_ERROR"),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r7-both-must-redline-with-review-facts", R7, "compound-noise",
                   {"sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True, "other_remedy_present": True}),
                    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})},
                   "REQUIRES_REVIEW", "extra co-present interaction_facts key on sla must not suppress the fire"))

CASES.append(case("dev-r5-both-negotiate-mixed-with-review", R5, "one-established-one-unresolved",
                   {"limitation_of_liability": pd("limitation_of_liability", "NEGOTIATE", [ct("data_breach", "uncapped")]),
                    "insurance": pd("insurance", "REQUIRES_REVIEW")},
                   "INSUFFICIENT_FACTS"))
CASES.append(case("dev-r5-compound-noise-category", R5, "compound-noise-category",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped"), ct("confidentiality", "within_general_cap")]),
                    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False), ct("general_liability", "required", established=True)])},
                   "ESCALATE", "unrelated co-present confidentiality/general_liability entries must not suppress the data_breach/cyber_liability fire"))
CASES.append(case("dev-r5-role-reversal-established-different-key", R5, "role-reversal",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
                    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "excess_required", established=True)])},
                   "NOT_TRIGGERED", "cyber_liability IS established here (just with a different treatment label) -- established flag alone controls the gate, not the treatment string"))
CASES.append(case("dev-r5-multiple-provisions-insurance-amendment", R5, "multiple-provisions",
                   {"limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
                    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)], reconciliation="amendment_resolved")},
                   "ESCALATE"))
