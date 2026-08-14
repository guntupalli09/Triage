"""
Labeled adversarial corpus for the Warranties policy engine benchmark
(see benchmarks/run_warranties_benchmark.py). Adapter #11 — first adapter
added after the ten-adapter scalability review
(docs/architecture/ten_adapter_scalability_review.md).

Labels here were written from the policy semantics and the drafting
pattern alone, reasoning directly from warranties_policy_engine.py's
evaluate_warranties_policy logic, never by running the implementation and
copying whatever it happened to output. Where a label was corrected after
a benchmark run, the correction and its reasoning are recorded in the
case's `notes` field, per the discipline established with payment_terms.

DEFAULT_POLICY requires NOTHING by default (every require_*/prohibit_*
field is False, every list/threshold is None) — the corrected convention
established with insurance_corpus.py and carried through payment_terms.
Each case here explicitly turns on only the dimension(s) it means to test
via policy_overrides.

contract_side is "buy_side" by default across this corpus (we are
"Customer"; "Vendor" resolves to sell_side via policy_engine_core's
BUY_SIDE_ROLES/SELL_SIDE_ROLES) -- individual cases override this where
directionality itself is what's being tested.

Several cases are deliberate NEGATIVE CONTROLS: "warrant"/"warranty"/
"guarantee"/"represents" tokens appearing in a context that is not a
legal warranties clause at all (a dispute-notice provision mentioning
"warranty claims", a purchase-price recital using "represents", an SLA
section that "guarantees" a response time, a "search warrant", a
"money-back guarantee" marketing phrase, a parent/financial guarantee)
-- these must resolve NOT_APPLICABLE, never REQUIRES_REVIEW, per the
module docstring's explicit negative-control discipline.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "buy_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: mutual authority warranty; Vendor warrants compliance with "
                      "law, professional/workmanlike performance, non-infringement, and malware-free "
                      "deliverables for 180 days; no AS IS disclaimer of express warranties; repair/"
                      "replace/reperform as sole remedy.",
    "required_warranty_categories_json": None,
    "prohibited_warranty_categories_json": None,
    "require_mutual_warranties": False,
    "minimum_warranty_duration_days": None,
    "prohibit_as_is_disclaimer": False,
    "prohibit_exclusive_remedy": False,
    "required_remedy_type": None,
    "require_non_infringement_warranty": False,
    "require_compliance_with_law_warranty": False,
    "require_professional_standard": False,
    "require_malware_free_warranty": False,
    "require_title_warranty": False,
    "require_warranty_survival": False,
}


def case(
    id: str,
    tags: List[str],
    text: str,
    expected_state: str,
    policy_overrides: Optional[Dict[str, Any]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "expected_state": expected_state,
        "policy_overrides": policy_overrides or {},
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Fully-compliant baseline.
# ---------------------------------------------------------------------------
FULLY_COMPLIANT_TEXT = (
    "9. Warranties. Vendor represents and warrants that it has the full corporate power and "
    "authority to enter into this Agreement. Vendor further represents and warrants that it shall "
    "comply with all applicable laws in performing the Services, that the Services will be "
    "performed in a professional and workmanlike manner, and that the Deliverables do not infringe "
    "any third-party intellectual property rights. Vendor further represents and warrants that the "
    "Deliverables are free from any viruses, malware, or malicious code. This warranty shall be "
    "valid for a period of 180 days from delivery and shall survive termination of this Agreement. "
    "Customer's sole and exclusive remedy for breach of the foregoing warranties shall be repair or "
    "replacement of the nonconforming Deliverables."
)
FULLY_COMPLIANT_POLICY = {
    "require_non_infringement_warranty": True,
    "require_compliance_with_law_warranty": True,
    "require_professional_standard": True,
    "require_malware_free_warranty": True,
    "minimum_warranty_duration_days": 90.0,
    "require_warranty_survival": True,
    "required_remedy_type": "repair_replace_reperform",
}
CASES.append(case(
    "clean-01", ["baseline", "fully_compliant"], FULLY_COMPLIANT_TEXT, "ACCEPT",
    policy_overrides=FULLY_COMPLIANT_POLICY,
    notes="Every configured requirement is satisfied: non-infringement/compliance/professional-"
          "standard/malware-free all established for Vendor (sell_side, i.e. counterparty), "
          "180-day duration clears the 90-day minimum, survival present, exclusive remedy is "
          "repair/replace which matches required_remedy_type.",
))

# ---------------------------------------------------------------------------
# Per-category individual warranties.
# ---------------------------------------------------------------------------
CASES.append(case(
    "category-authority-01", ["category", "authority"],
    "Vendor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "ACCEPT", policy_overrides={},
    notes="No policy dimension turned on; authority established for Vendor (sell_side) but nothing requires it.",
))
CASES.append(case(
    "category-compliance-law-01", ["category", "compliance_with_law"],
    "Vendor represents and warrants that it shall comply with all applicable laws in the performance of the Services.",
    "ACCEPT", policy_overrides={"require_compliance_with_law_warranty": True},
    notes="Compliance-with-law warranty established for Vendor (counterparty) -- satisfies the requirement.",
))
CASES.append(case(
    "category-compliance-law-missing-01", ["category", "compliance_with_law", "gap"],
    "Vendor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "NEGOTIATE", policy_overrides={"require_compliance_with_law_warranty": True},
    notes="Only authority is warranted; compliance-with-law was never established, so the required dimension is unmet.",
))
CASES.append(case(
    "category-professional-01", ["category", "professional_workmanlike"],
    "Vendor represents and warrants that the Services will be performed in a professional and workmanlike manner.",
    "ACCEPT", policy_overrides={"require_professional_standard": True},
    notes="Professional/workmanlike standard established for Vendor.",
))
CASES.append(case(
    "category-conformity-01", ["category", "conformity_to_documentation"],
    "Vendor represents and warrants that the Software conforms in all material respects to the Documentation.",
    "ACCEPT", policy_overrides={},
    notes="No policy field targets conformity_to_documentation directly; category_treatments records it, state is ACCEPT with no configured requirement.",
))
CASES.append(case(
    "category-non-infringement-01", ["category", "non_infringement"],
    "Vendor represents and warrants that the Deliverables do not infringe any third-party intellectual property rights.",
    "ACCEPT", policy_overrides={"require_non_infringement_warranty": True},
    notes="Non-infringement established for Vendor -- satisfies the requirement.",
))
CASES.append(case(
    "category-non-infringement-missing-01", ["category", "non_infringement", "gap"],
    "Vendor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "NEGOTIATE", policy_overrides={"require_non_infringement_warranty": True},
    notes="Non-infringement never established; required dimension unmet.",
))
CASES.append(case(
    "category-malware-01", ["category", "malware_free"],
    "Vendor represents and warrants that the Software is free from any viruses, malware, or malicious code.",
    "ACCEPT", policy_overrides={"require_malware_free_warranty": True},
    notes="Malware-free warranty established for Vendor.",
))
CASES.append(case(
    "category-security-01", ["category", "security"],
    "Vendor represents and warrants that it maintains commercially reasonable administrative, technical, and physical security measures.",
    "ACCEPT", policy_overrides={},
    notes="Security warranty category established; no dedicated policy field for it, so ACCEPT with category_treatments recording the fact.",
))
CASES.append(case(
    "category-performance-01", ["category", "performance"],
    "Vendor represents and warrants that the Software will perform substantially in accordance with the Documentation.",
    "ACCEPT", policy_overrides={},
    notes="Performance warranty established; no dedicated policy field.",
))
CASES.append(case(
    "category-title-01", ["category", "title"],
    "Vendor represents and warrants that it has good and valid title to the goods sold hereunder.",
    "ACCEPT", policy_overrides={"require_title_warranty": True},
    notes="Title warranty established for Vendor -- satisfies the requirement.",
))
CASES.append(case(
    "category-title-missing-01", ["category", "title", "gap"],
    "Vendor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "NEGOTIATE", policy_overrides={"require_title_warranty": True},
    notes="Title warranty never established; required dimension unmet.",
))
CASES.append(case(
    "category-third-party-rights-01", ["category", "third_party_rights"],
    "Vendor represents and warrants that the Services will not violate the rights of any third party.",
    "ACCEPT", policy_overrides={},
    notes="Third-party-rights warranty established; no dedicated policy field.",
))

# ---------------------------------------------------------------------------
# Mutual warranties.
# ---------------------------------------------------------------------------
CASES.append(case(
    "mutual-clean-01", ["mutual", "authority"],
    "Each party represents and warrants that it has the full power and authority to enter into this Agreement.",
    "ACCEPT", policy_overrides={"require_mutual_warranties": True},
    notes="Mutual opener present, no asymmetry detectable (no per-party subclauses at all) -- satisfies require_mutual_warranties.",
))
CASES.append(case(
    "mutual-missing-01", ["mutual", "gap"],
    "Vendor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "NEGOTIATE", policy_overrides={"require_mutual_warranties": True},
    notes="Only a unilateral Vendor warranty -- no mutual opener -- fails require_mutual_warranties.",
))
CASES.append(case(
    "mutual-asymmetric-duration-01", ["mutual", "asymmetry", "duration"],
    "Each party represents and warrants that it has the full power and authority to enter into this "
    "Agreement. Vendor's warranty obligations under this Section shall be limited to a period of 30 "
    "days, whereas Customer's warranty obligations under this Section shall continue for a period "
    "of 365 days.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Mutual opener contradicted by asymmetric per-party duration subclauses -- symmetry cannot "
          "be confirmed, routes to REQUIRES_REVIEW (also independently trips duration_conflict since "
          "30 and 365 are both accumulated document-wide).",
))
CASES.append(case(
    "mutual-asymmetric-categories-01", ["mutual", "asymmetry", "categories"],
    "Each party represents and warrants that it has the full power and authority to enter into this "
    "Agreement. Vendor's warranty obligations under this Section shall include that the Deliverables "
    "do not infringe any third-party intellectual property rights, whereas Customer's warranty "
    "obligations under this Section shall include that it has the full power and authority to enter "
    "into this Agreement.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Mutual opener contradicted by asymmetric per-party category subclauses (Vendor's sub-clause "
          "adds non-infringement, Customer's doesn't) -- symmetry cannot be confirmed.",
))

# ---------------------------------------------------------------------------
# Unilateral vendor warranties (bundled categories).
# ---------------------------------------------------------------------------
CASES.append(case(
    "unilateral-bundle-01", ["unilateral", "bundle"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement, that it shall comply with all applicable laws, and that the Services will be "
    "performed in a professional and workmanlike manner.",
    "ACCEPT", policy_overrides={"require_compliance_with_law_warranty": True, "require_professional_standard": True},
    notes="Compliance-with-law and professional-standard both established for Vendor in one bundled statement.",
))

# ---------------------------------------------------------------------------
# Customer warranties present.
# ---------------------------------------------------------------------------
CASES.append(case(
    "customer-warranty-01", ["directionality", "customer_warrants"],
    "Customer represents and warrants that it has the full power and authority to enter into this Agreement.",
    "ACCEPT", policy_overrides={},
    notes="Authority is warranted BY Customer (buy_side, i.e. us) here -- resolved_categories['authority'] == 'buy_side', no policy dimension requires anything of it.",
))
CASES.append(case(
    "customer-warranty-prohibited-01", ["directionality", "customer_warrants", "prohibited"],
    "Customer represents and warrants that the specifications provided to Vendor do not infringe any "
    "third-party intellectual property rights.",
    "ESCALATE", policy_overrides={"prohibited_warranty_categories_json": ["non_infringement"]},
    notes="non_infringement is warranted BY us (buy_side == contract_side) -- _our_side(side) is True, "
          "which is exactly what prohibited_warranty_categories_json is meant to catch (we should "
          "never be the one giving this warranty).",
))

# ---------------------------------------------------------------------------
# Required / prohibited category dimensions.
# ---------------------------------------------------------------------------
CASES.append(case(
    "required-category-satisfied-01", ["required_categories"],
    "Vendor represents and warrants that the Deliverables do not infringe any third-party "
    "intellectual property rights and that it shall comply with all applicable laws.",
    "ACCEPT", policy_overrides={"required_warranty_categories_json": ["non_infringement", "compliance_with_law"]},
    notes="Both required categories established for Vendor (counterparty) -- satisfies the requirement.",
))
CASES.append(case(
    "required-category-partial-01", ["required_categories", "gap"],
    "Vendor represents and warrants that the Deliverables do not infringe any third-party intellectual property rights.",
    "NEGOTIATE", policy_overrides={"required_warranty_categories_json": ["non_infringement", "compliance_with_law"]},
    notes="Only non_infringement established; compliance_with_law required but missing -- NEGOTIATE.",
))
CASES.append(case(
    "prohibited-category-not-triggered-01", ["prohibited_categories"],
    "Vendor represents and warrants that the Software will perform substantially in accordance with the Documentation.",
    "ACCEPT", policy_overrides={"prohibited_warranty_categories_json": ["performance"]},
    notes="prohibited_warranty_categories_json only fires when WE (contract_side) are the warranting "
          "side. Here performance is warranted BY Vendor (sell_side), not by us (buy_side), so "
          "_our_side(side) is False and the prohibition never triggers -- ACCEPT. See "
          "customer-warranty-prohibited-01 for the genuine-violation counterpart of this same "
          "policy dimension, where WE are the warranting side.",
))

# ---------------------------------------------------------------------------
# Disclaimer language.
# ---------------------------------------------------------------------------
AS_IS_TEXT = (
    "EXCEPT AS EXPRESSLY SET FORTH IN THIS SECTION, THE SOFTWARE IS PROVIDED ON AN \"AS IS\" BASIS "
    "AND VENDOR MAKES NO OTHER WARRANTIES, WHETHER EXPRESS OR IMPLIED. CUSTOMER'S SOLE AND EXCLUSIVE "
    "REMEDY FOR BREACH OF WARRANTY SHALL BE REPAIR OR REPLACEMENT OF THE DEFECTIVE SOFTWARE."
)
CASES.append(case(
    "as-is-prohibited-01", ["disclaimer", "as_is", "prohibited"],
    AS_IS_TEXT, "ESCALATE", policy_overrides={"prohibit_as_is_disclaimer": True},
    notes="AS IS disclaimer present, policy prohibits it -- ESCALATE.",
))
CASES.append(case(
    "as-is-allowed-01", ["disclaimer", "as_is"],
    AS_IS_TEXT, "ACCEPT", policy_overrides={},
    notes="AS IS disclaimer present but no policy dimension prohibits it -- ACCEPT (exclusive remedy "
          "and repair/replace are also present but not restricted by this policy).",
))
CASES.append(case(
    "disclaimer-carveout-01", ["disclaimer", "carveout"],
    "Except for the express warranties set forth in this Section, Vendor disclaims all other "
    "warranties, whether express or implied. Vendor represents and warrants that it has the full "
    "power and authority to enter into this Agreement.",
    "ACCEPT", policy_overrides={},
    notes="Disclaimer with a carve-out for expressly-stated warranties; authority is one of the "
          "express warranties. No policy dimension violated.",
))

# ---------------------------------------------------------------------------
# Remedy language.
# ---------------------------------------------------------------------------
CASES.append(case(
    "exclusive-remedy-prohibited-01", ["remedy", "exclusive", "prohibited"],
    "Customer's sole and exclusive remedy for breach of the foregoing warranty shall be repair or "
    "replacement of the nonconforming Deliverables.",
    "ESCALATE", policy_overrides={"prohibit_exclusive_remedy": True},
    notes="Exclusive-remedy language present, policy prohibits it -- ESCALATE.",
))
CASES.append(case(
    "exclusive-remedy-allowed-01", ["remedy", "exclusive"],
    "Customer's sole and exclusive remedy for breach of the foregoing warranty shall be repair or "
    "replacement of the nonconforming Deliverables.",
    "ACCEPT", policy_overrides={},
    notes="Exclusive-remedy language present but not prohibited by policy -- ACCEPT.",
))
CASES.append(case(
    "repair-replace-required-satisfied-01", ["remedy", "repair_replace"],
    "Vendor represents and warrants that the Deliverables will conform to the Documentation. Vendor "
    "shall, at its option, repair or replace any nonconforming Deliverables.",
    "ACCEPT", policy_overrides={"required_remedy_type": "repair_replace_reperform"},
    notes="Repair/replace remedy language present -- satisfies required_remedy_type. (Also carries a "
          "warranty statement so the clause anchor genuinely fires -- a bare remedy sentence with no "
          "warranty language at all would not, by design, be treated as a warranties clause.)",
))
CASES.append(case(
    "repair-replace-required-missing-01", ["remedy", "repair_replace", "gap"],
    "Vendor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "NEGOTIATE", policy_overrides={"required_remedy_type": "repair_replace_reperform"},
    notes="No repair/replace/reperform language found -- required remedy type unmet.",
))
CASES.append(case(
    "refund-credit-01", ["remedy", "refund_credit"],
    "In the event of a breach of the foregoing warranty, Vendor shall issue Customer a refund of the amounts paid for the nonconforming Services.",
    "ACCEPT", policy_overrides={"required_remedy_type": "refund_credit"},
    notes="Refund remedy language present -- satisfies required_remedy_type.",
))
CASES.append(case(
    "refund-credit-missing-01", ["remedy", "refund_credit", "gap"],
    "Vendor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "NEGOTIATE", policy_overrides={"required_remedy_type": "refund_credit"},
    notes="No refund/credit language found -- required remedy type unmet.",
))

# ---------------------------------------------------------------------------
# Duration.
# ---------------------------------------------------------------------------
CASES.append(case(
    "duration-30-days-01", ["duration"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. This warranty shall be valid for a period of 30 days from delivery.",
    "NEGOTIATE", policy_overrides={"minimum_warranty_duration_days": 90.0},
    notes="30-day duration is below the 90-day policy minimum -- NEGOTIATE.",
))
CASES.append(case(
    "duration-90-days-01", ["duration"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. This warranty shall be valid for a period of 90 days from delivery.",
    "ACCEPT", policy_overrides={"minimum_warranty_duration_days": 90.0},
    notes="90-day duration meets the 90-day policy minimum exactly -- ACCEPT.",
))
CASES.append(case(
    "duration-180-days-01", ["duration"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. This warranty shall be valid for a period of 180 days from delivery.",
    "ACCEPT", policy_overrides={"minimum_warranty_duration_days": 90.0},
    notes="180-day duration exceeds the 90-day minimum -- ACCEPT.",
))
CASES.append(case(
    "duration-months-01", ["duration", "months"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. This warranty shall be valid for a period of 6 months from delivery.",
    "ACCEPT", policy_overrides={"minimum_warranty_duration_days": 90.0},
    notes="6 months normalizes to 180 days (6*30), which exceeds the 90-day minimum -- ACCEPT.",
))
CASES.append(case(
    "duration-years-01", ["duration", "years"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. This warranty shall be valid for a period of 1 year from delivery.",
    "ACCEPT", policy_overrides={"minimum_warranty_duration_days": 90.0},
    notes="1 year normalizes to 365 days, which exceeds the 90-day minimum -- ACCEPT.",
))
CASES.append(case(
    "duration-missing-01", ["duration", "gap"],
    "Vendor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "NEGOTIATE", policy_overrides={"minimum_warranty_duration_days": 90.0},
    notes="No duration stated at all and policy configures a minimum -- NEGOTIATE (silence is a gap, "
          "not automatically satisfying an unconfigured ceiling -- same precedent as data_security's "
          "breach-notification-hours handling and payment_terms's late-fee handling).",
))

# ---------------------------------------------------------------------------
# Perpetual / no-duration ambiguity.
# ---------------------------------------------------------------------------
CASES.append(case(
    "perpetual-clean-01", ["duration", "perpetual"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. This warranty shall be perpetual.",
    "ACCEPT", policy_overrides={"minimum_warranty_duration_days": 90.0},
    notes="Perpetual warranty stated cleanly (no conflicting numeric duration) -- satisfies any "
          "minimum-duration policy since duration_perpetual is set and the minimum-duration check "
          "only fires when BOTH duration_days is None AND duration_perpetual is falsy.",
))
CASES.append(case(
    "perpetual-numeric-conflict-01", ["duration", "perpetual", "conflict"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. This warranty shall be perpetual. Notwithstanding the foregoing, this warranty "
    "shall be valid for a period of 90 days from delivery.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Both perpetual and a numeric 90-day duration are stated for the same warranty -- "
          "genuinely ambiguous, routes to REQUIRES_REVIEW via duration_conflict.",
))

# ---------------------------------------------------------------------------
# SOW / Schedule cross-reference.
# ---------------------------------------------------------------------------
CASES.append(case(
    "sow-crossref-nothing-else-01", ["cross_reference", "sow"],
    "Vendor's warranties are as set forth in the applicable Statement of Work. Vendor warrants that it will comply with such terms.",
    "ESCALATE", policy_overrides={},
    notes="Material warranty terms are delegated to an SOW that cannot be resolved from the contract "
          "text alone, and no categories were independently established in this text -- ESCALATE per "
          "the schedule_cross_reference-with-nothing-else-established gate.",
))
CASES.append(case(
    "sow-crossref-supplementing-01", ["cross_reference", "sow"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. Additional warranties applicable to specific Deliverables are as set forth in the "
    "applicable Statement of Work.",
    "ACCEPT", policy_overrides={},
    notes="A category (authority) IS independently established in the visible text; the SOW "
          "cross-reference only supplements it, so the cross-reference gate does not fire (it only "
          "fires when nothing else was established).",
))

# ---------------------------------------------------------------------------
# Amendments.
# ---------------------------------------------------------------------------
CASES.append(case(
    "amendment-consistent-01", ["amendment"],
    "Vendor represents and warrants that this warranty shall be valid for a period of 90 days from "
    "delivery. This Agreement is hereby amended to restate that the warranty period referenced above "
    "shall be valid for a period of 90 days from delivery.",
    "ACCEPT", policy_overrides={"minimum_warranty_duration_days": 90.0},
    notes="Amendment restates the identical 90-day duration -- both mentions accumulate to the same "
          "single value, no conflict is detected (this adapter has no dedicated amendment-resolution "
          "logic, unlike liability_policy_engine -- a consistent restatement is safe by construction).",
))
CASES.append(case(
    "amendment-changes-duration-01", ["amendment", "conflict"],
    "Vendor represents and warrants that this warranty shall be valid for a period of 90 days from "
    "delivery. This Agreement is hereby amended to restate that the warranty period referenced above "
    "shall instead be valid for a period of 365 days from delivery.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Amendment changes the duration to a different value; this adapter has no amendment-aware "
          "'last mention wins' resolution (unlike liability), so the generic accumulate-then-resolve "
          "conflict machinery correctly and safely routes this to REQUIRES_REVIEW rather than "
          "guessing which duration governs.",
))

# ---------------------------------------------------------------------------
# Conflicting warranties (category established AND negated).
# ---------------------------------------------------------------------------
CASES.append(case(
    "conflict-non-infringement-01", ["conflict", "negation"],
    "Vendor represents and warrants that the Deliverables do not infringe any third-party "
    "intellectual property rights. Notwithstanding the foregoing, Vendor makes no warranty of "
    "non-infringement with respect to Open Source components incorporated into the Deliverables.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="non_infringement is both affirmatively warranted and expressly negated elsewhere in the "
          "same document -- genuine conflict, cannot determine which governs -- REQUIRES_REVIEW.",
))
CASES.append(case(
    "conflict-compliance-law-01", ["conflict", "negation"],
    "Vendor represents and warrants that it shall comply with all applicable laws. Vendor makes no "
    "warranty of compliance with laws applicable to Customer's specific use case.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="compliance_with_law both affirmed and negated -- REQUIRES_REVIEW.",
))

# ---------------------------------------------------------------------------
# Explicit negations (standalone, no affirmative counterpart -- not a conflict).
# ---------------------------------------------------------------------------
CASES.append(case(
    "negation-standalone-01", ["negation"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. Vendor makes no warranty of non-infringement with respect to any Open Source "
    "components incorporated into the Deliverables.",
    "NEGOTIATE", policy_overrides={"require_non_infringement_warranty": True},
    notes="non_infringement is negated (and never affirmed elsewhere, so no conflict -- just a "
          "negated, never-established category) -- required_non_infringement_warranty is unmet, "
          "NEGOTIATE, not REQUIRES_REVIEW (no conflict exists, just a clean gap).",
))
CASES.append(case(
    "negation-standalone-no-policy-01", ["negation"],
    "Vendor makes no warranty of title with respect to the goods sold hereunder.",
    "ACCEPT", policy_overrides={},
    notes="Title is negated but no policy dimension requires it -- ACCEPT (negation alone, with no "
          "policy requirement and no conflicting affirmation, is not itself a violation).",
))

# ---------------------------------------------------------------------------
# No warranty clause.
# ---------------------------------------------------------------------------
CASES.append(case(
    "no-clause-01", ["not_applicable"],
    "This Agreement contains no representations or warranties of any kind regarding the subject matter hereof, other than as expressly negotiated by the parties in a separate writing.",
    "NOT_APPLICABLE", policy_overrides={"require_non_infringement_warranty": True},
    notes="'warranties' matches _ANCHOR_RE (the anchor is a bare 'warrant' root), but no concrete "
          "category/disclaimer/remedy/mutual-opener signal is ever found in this negation-only "
          "recital -- found_anything stays False and extract_warranties_facts returns None -- "
          "NOT_APPLICABLE.",
))
CASES.append(case(
    "no-clause-stray-mention-01", ["not_applicable", "negative_control"],
    "Any warranty claims must be submitted in writing within 10 days of discovery pursuant to Section 4.2.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="A stray 'warranty' mention inside what is actually a claims-notice provision -- no "
          "category/disclaimer/remedy/mutual-opener signal found -- NOT_APPLICABLE, not a low-signal "
          "REQUIRES_REVIEW.",
))

# ---------------------------------------------------------------------------
# Malformed drafting.
# ---------------------------------------------------------------------------
CASES.append(case(
    "malformed-01", ["malformed"],
    "Warranties. warrants that warrants and represents that the the Agreement shall shall be be "
    "warranted for warranty purposes under this this Section 9 hereof notwithstanding.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="Garbled/repeated-word drafting with the 'warrant' anchor firing repeatedly but no "
          "coherent named-party statement, mutual opener, category, disclaimer, or remedy language "
          "ever parseable -- NOT_APPLICABLE.",
))
CASES.append(case(
    "malformed-02", ["malformed"],
    "9. [DRAFTING NOTE: INSERT WARRANTY LANGUAGE HERE -- TBD PER DEAL TEAM]",
    "NOT_APPLICABLE", policy_overrides={},
    notes="Placeholder/bracketed drafting-note text, not real warranty language -- no structured "
          "signal parseable -- NOT_APPLICABLE.",
))
CASES.append(case(
    "malformed-03", ["malformed", "run_on"],
    "Vendor warrants and represents and further warrants and additionally represents and warrants "
    "that Vendor warrants that Vendor has authority and Vendor warrants that Vendor has authority "
    "to enter into this Agreement and this Agreement only and no other agreement whatsoever.",
    "ACCEPT", policy_overrides={},
    notes="Run-on, repetitive drafting, but the authority category IS genuinely, repeatedly "
          "established for Vendor with no conflict -- ACCEPT (repetition of the same fact is not a "
          "conflict; only materially DIFFERENT repeated statements are).",
))

# ---------------------------------------------------------------------------
# Ambiguous pronouns / multiple parties.
# ---------------------------------------------------------------------------
CASES.append(case(
    "ambiguous-pronoun-01", ["ambiguous_pronoun"],
    "It represents and warrants that it has the full power and authority to enter into this Agreement.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="'It' is not a capitalized proper-noun party name -- _WARRANTING_PARTY_RE's (?-i:[A-Z]...) "
          "capture never matches lowercase 'it', so no warranting-party statement is extracted at "
          "all here, and no mutual opener either -- found_anything stays False -- NOT_APPLICABLE. "
          "This text has no concrete extractable warranty at all, matching the same 'clause anchor "
          "present but nothing structured found' safety rule as no-clause-stray-mention-01.",
))
CASES.append(case(
    "multiple-parties-01", ["multiple_parties", "unresolved"],
    "Guarantor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="'Guarantor' is a genuine capitalized party name captured by _WARRANTING_PARTY_RE, but it "
          "is not a recognized buy_side/sell_side role token (not in BUY_SIDE_ROLES or "
          "SELL_SIDE_ROLES) -- side_for_role returns None -- the category cannot be attributed to a "
          "side -- REQUIRES_REVIEW.",
))

# ---------------------------------------------------------------------------
# Negative controls: warrant/warranty/guarantee/represent in unrelated contexts.
# ---------------------------------------------------------------------------
CASES.append(case(
    "negative-control-dispute-notice-01", ["negative_control"],
    "Any warranty claims must be submitted in writing within 10 days of discovery pursuant to Section 4.2.",
    "NOT_APPLICABLE", policy_overrides={"require_non_infringement_warranty": True},
    notes="Duplicate of no-clause-stray-mention-01 with a policy dimension turned on, to prove the "
          "negative control holds even when a require_* field is active -- still NOT_APPLICABLE.",
))
CASES.append(case(
    "negative-control-represents-fair-value-01", ["negative_control"],
    "The Purchase Price represents fair market value of the acquired assets as of the Closing Date.",
    "NOT_APPLICABLE", policy_overrides={"require_compliance_with_law_warranty": True},
    notes="'represents' used in its ordinary-English sense (fair value), not as part of a "
          "representations-and-warranties statement -- _ANCHOR_RE never fires at all (it only "
          "anchors on 'warrant'-root tokens, never bare 'represents') -- NOT_APPLICABLE.",
))
CASES.append(case(
    "negative-control-sla-guarantee-01", ["negative_control"],
    "We guarantee a response within 24 hours for all Severity 1 incidents reported through the support portal.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="'guarantee' used in an SLA/support-commitment sense -- _ANCHOR_RE never anchors on "
          "'guarantee' at all (only 'warrant'-root tokens) -- NOT_APPLICABLE.",
))
CASES.append(case(
    "negative-control-search-warrant-01", ["negative_control"],
    "In the event that a law enforcement agency presents a valid search warrant, Vendor shall notify Customer within 24 hours to the extent permitted by law.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="'warrant' used in its search-warrant sense -- the anchor fires (bare 'warrant' root "
          "matches), but no category/disclaimer/remedy/mutual-opener signal is ever found in this "
          "text -- NOT_APPLICABLE.",
))
CASES.append(case(
    "negative-control-money-back-guarantee-01", ["negative_control"],
    "Customer is entitled to a 30-day money-back guarantee, refundable upon written request to Vendor's billing department.",
    "NOT_APPLICABLE", policy_overrides={"required_remedy_type": "refund_credit"},
    notes="'guarantee' in a marketing/refund-policy sense with no warranty structure at all -- "
          "_ANCHOR_RE never anchors on 'guarantee' -- NOT_APPLICABLE even though refund language is "
          "present, because the clause was never recognized as a warranties clause in the first place.",
))
CASES.append(case(
    "negative-control-parent-guarantee-01", ["negative_control"],
    "Parent hereby unconditionally guarantees the full and timely payment of all amounts owed by Subsidiary under this Agreement.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="A financial/payment guaranty (a different legal concept from a product/service warranty) "
          "-- 'guarantee' never anchors this adapter -- NOT_APPLICABLE (this text belongs to a "
          "parent-guaranty clause, not warranties, and correctly is never claimed by this adapter).",
))

# ---------------------------------------------------------------------------
# Warranty survival.
# ---------------------------------------------------------------------------
CASES.append(case(
    "survival-present-01", ["survival"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. This warranty shall survive the termination or expiration of this Agreement.",
    "ACCEPT", policy_overrides={"require_warranty_survival": True},
    notes="Survival language present -- satisfies the requirement.",
))
CASES.append(case(
    "survival-missing-01", ["survival", "gap"],
    "Vendor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "NEGOTIATE", policy_overrides={"require_warranty_survival": True},
    notes="No survival language found -- required dimension unmet.",
))

# ---------------------------------------------------------------------------
# Additional per-category coverage.
# ---------------------------------------------------------------------------
CASES.append(case(
    "category-authority-required-01", ["category", "authority", "required"],
    "Vendor represents and warrants that the Services will be performed in a professional and workmanlike manner.",
    "NEGOTIATE", policy_overrides={"required_warranty_categories_json": ["authority"]},
    notes="Authority never established (only professional_workmanlike is); required_warranty_categories_json includes authority -- NEGOTIATE.",
))
CASES.append(case(
    "category-conformity-required-01", ["category", "conformity_to_documentation", "required"],
    "Vendor represents and warrants that the Software conforms in all material respects to the Documentation.",
    "ACCEPT", policy_overrides={"required_warranty_categories_json": ["conformity_to_documentation"]},
    notes="Conformity established for Vendor -- satisfies the required-categories check.",
))
CASES.append(case(
    "category-security-required-01", ["category", "security", "required"],
    "Vendor represents and warrants that it maintains commercially reasonable technical and physical security safeguards.",
    "ACCEPT", policy_overrides={"required_warranty_categories_json": ["security"]},
    notes="Security established for Vendor -- satisfies the required-categories check.",
))
CASES.append(case(
    "category-performance-required-missing-01", ["category", "performance", "required", "gap"],
    "Vendor represents and warrants that it has the full power and authority to enter into this Agreement.",
    "NEGOTIATE", policy_overrides={"required_warranty_categories_json": ["performance"]},
    notes="Performance never established -- required-categories check fails.",
))

# ---------------------------------------------------------------------------
# Multiple, non-conflicting warranty provisions in one document.
# ---------------------------------------------------------------------------
CASES.append(case(
    "multi-provision-01", ["multi_provision"],
    "9.1 Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. 9.2 Vendor further represents and warrants that it shall comply with all applicable "
    "laws. 9.3 Vendor further represents and warrants that the Deliverables do not infringe any "
    "third-party intellectual property rights.",
    "ACCEPT", policy_overrides={
        "require_compliance_with_law_warranty": True, "require_non_infringement_warranty": True,
    },
    notes="Three separately-numbered subsections, each establishing a distinct category for the "
          "same party with no conflict -- all requirements satisfied, ACCEPT.",
))
CASES.append(case(
    "multi-provision-consistency-01", ["multi_provision", "consistency"],
    "9.1 Vendor represents and warrants that this warranty shall be valid for a period of 180 days "
    "from delivery. 9.4 For the avoidance of doubt, the warranty period described in Section 9.1 is "
    "180 days from the date of delivery of the applicable Deliverable.",
    "ACCEPT", policy_overrides={"minimum_warranty_duration_days": 90.0},
    notes="Two mentions of the identical 180-day duration (a clarifying restatement, not a change) -- "
          "both accumulate to the same single value, no conflict, satisfies the 90-day minimum.",
))

# ---------------------------------------------------------------------------
# Additional directionality cases.
# ---------------------------------------------------------------------------
CASES.append(case(
    "directionality-sell-side-contract-01", ["directionality"],
    "Customer represents and warrants that the specifications provided to Vendor do not infringe any third-party intellectual property rights.",
    "ACCEPT", policy_overrides={"contract_side": "sell_side", "require_non_infringement_warranty": True},
    notes="Here WE are Vendor (sell_side). non_infringement is warranted BY Customer (buy_side), "
          "which differs from our contract_side (sell_side), so _their_side(resolved) is True -- "
          "satisfies require_non_infringement_warranty regardless of which side of the deal we sit "
          "on -- ACCEPT. Proves the directional resolution isn't hardcoded to assume Vendor/seller "
          "is always our side.",
))

# ---------------------------------------------------------------------------
# Additional conflict / negation combinations.
# ---------------------------------------------------------------------------
CASES.append(case(
    "conflict-malware-01", ["conflict", "negation"],
    "Vendor represents and warrants that the Software is free from any viruses, malware, or "
    "malicious code. Notwithstanding the foregoing, Vendor makes no warranty of viruses, malware, "
    "or malicious code with respect to third-party components bundled with the Software.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="malware_free both affirmed and negated -- genuine conflict -- REQUIRES_REVIEW.",
))
CASES.append(case(
    "negation-title-standalone-01", ["negation"],
    "Vendor represents and warrants that it has the full power and authority to enter into this "
    "Agreement. Vendor makes no warranty of title with respect to any third-party components "
    "incorporated into the Deliverables.",
    "NEGOTIATE", policy_overrides={"require_title_warranty": True},
    notes="Title is negated (and never affirmed elsewhere -- no conflict, just a clean negated gap) "
          "-- require_title_warranty is unmet -- NEGOTIATE.",
))

# ---------------------------------------------------------------------------
# Additional malformed / ambiguous drafting.
# ---------------------------------------------------------------------------
CASES.append(case(
    "malformed-04", ["malformed", "ambiguous"],
    "Section 9 [RESERVED].",
    "NOT_APPLICABLE", policy_overrides={},
    notes="A reserved/blank section with no 'warrant' anchor at all -- clause not found -- NOT_APPLICABLE.",
))
CASES.append(case(
    "ambiguous-pronoun-02", ["ambiguous_pronoun"],
    "The undersigned represents and warrants that the undersigned has the full power and authority to enter into this Agreement.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="'The undersigned' is not a capitalized single-token proper-noun party name matching "
          "_WARRANTING_PARTY_RE's [A-Z][A-Za-z]{2,30} capture (the article 'The' would be captured "
          "instead, and 'the' is in _GENERIC_ROLE_WORDS so it is skipped) -- no warranting-party "
          "statement is extracted and no mutual opener either -- found_anything stays False -- "
          "NOT_APPLICABLE, the same safety rule as ambiguous-pronoun-01.",
))

# ---------------------------------------------------------------------------
# Additional negative controls.
# ---------------------------------------------------------------------------
CASES.append(case(
    "negative-control-warranty-deed-01", ["negative_control"],
    "The property is conveyed by warranty deed, free and clear of all liens and encumbrances, as more particularly described in Exhibit A.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="'warranty deed' is a real-property conveyancing term of art, not a representations-and-"
          "warranties clause -- the anchor fires on 'warranty' but no category/disclaimer/remedy/"
          "mutual-opener signal is ever found -- NOT_APPLICABLE.",
))
CASES.append(case(
    "negative-control-warrant-officer-01", ["negative_control"],
    "References in this Agreement to a duly authorized officer shall include any warrant officer "
    "or equivalent rank designated by either party's government contracting authority.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="'warrant officer' is a military rank, entirely unrelated to a warranties clause -- anchor "
          "fires, nothing structured found -- NOT_APPLICABLE.",
))
CASES.append(case(
    "negative-control-represents-percentage-01", ["negative_control"],
    "The Annual Fee represents approximately 15% of Customer's total technology spend for the "
    "relevant fiscal year, as disclosed in the RFP response.",
    "NOT_APPLICABLE", policy_overrides={"require_compliance_with_law_warranty": True},
    notes="'represents' in its ordinary-English sense again, different wording from the earlier "
          "fair-value negative control -- _ANCHOR_RE never fires on bare 'represents' -- NOT_APPLICABLE.",
))

# ---------------------------------------------------------------------------
# Additional coverage to round out the corpus.
# ---------------------------------------------------------------------------
CASES.append(case(
    "prohibited-category-mutual-01", ["prohibited_categories", "mutual"],
    "Each party represents and warrants that it has the full power and authority to enter into this Agreement.",
    "ESCALATE", policy_overrides={"prohibited_warranty_categories_json": ["authority"]},
    notes="A mutual warranty is, by definition, also given BY us -- _our_side treats 'mutual' as "
          "True -- a prohibited category given mutually still counts as us giving it -- ESCALATE.",
))
CASES.append(case(
    "required-category-mutual-01", ["required_categories", "mutual"],
    "Each party represents and warrants that it has the full power and authority to enter into this Agreement.",
    "ACCEPT", policy_overrides={"required_warranty_categories_json": ["authority"]},
    notes="A mutual warranty is, by definition, also given BY the counterparty -- _their_side treats "
          "'mutual' as True -- satisfies a required-from-counterparty category -- ACCEPT.",
))
CASES.append(case(
    "duration-conflicting-numeric-01", ["duration", "conflict"],
    "Vendor represents and warrants that this warranty shall be valid for a period of 90 days from "
    "delivery. Vendor further represents and warrants that this warranty shall be valid for a "
    "period of 12 months from delivery.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="90 days and 12 months (normalized to 360 days) are different values -- genuine duration "
          "conflict -- REQUIRES_REVIEW.",
))
CASES.append(case(
    "remedy-both-types-01", ["remedy", "combined"],
    "Vendor represents and warrants that the Deliverables will conform to the Documentation. Vendor "
    "shall, at its option, either repair or replace any nonconforming Deliverables, or issue "
    "Customer a refund of the fees paid for the nonconforming Deliverables.",
    "ACCEPT", policy_overrides={"required_remedy_type": "repair_replace_reperform"},
    notes="Both repair/replace AND refund/credit language are present -- required_remedy_type only "
          "checks that its own specified type is present, which it is -- ACCEPT. (Carries a warranty "
          "statement so the clause anchor genuinely fires.)",
))
CASES.append(case(
    "compliance-and-professional-combined-01", ["category", "combined"],
    "Vendor represents and warrants that the Services shall be performed in compliance with all "
    "applicable laws and in a professional and workmanlike manner consistent with industry standards.",
    "ACCEPT", policy_overrides={"require_compliance_with_law_warranty": True, "require_professional_standard": True},
    notes="Both categories established in one combined sentence for Vendor -- both requirements satisfied.",
))

