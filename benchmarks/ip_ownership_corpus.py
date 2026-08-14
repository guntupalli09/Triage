"""
Labeled adversarial corpus for the IP Ownership / Licensing policy
engine benchmark (see benchmarks/run_ip_ownership_benchmark.py).
Adapter #8 — second adapter added after the original six.

Labels here were written from the policy semantics and the drafting
pattern alone, reasoning directly from ip_ownership_policy_engine.py's
evaluate_ip_policy logic, never by running the implementation and
copying whatever it happened to output. DEFAULT_POLICY represents a
sell-side vendor playbook with a fully-specified set of requirements
across every dimension, so most cases only need to override the one or
two dimensions under test.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "sell_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: Vendor retains background IP; Customer owns work product; "
                      "non-exclusive, worldwide, royalty-free, perpetual, irrevocable, purpose-limited "
                      "license to embedded background IP; sublicensable and transferable; feedback "
                      "assigned; residual knowledge rights retained; open-source disclosed; infringement "
                      "remedy referenced; license survives termination.",
    "require_we_retain_background_ip": True,
    "require_we_own_work_product": False,
    "prohibit_joint_ownership": True,
    "require_license_for_embedded_background_ip": True,
    "require_license_exclusive": False,
    "prohibit_royalty_bearing_license": True,
    "require_perpetual_license": True,
    "prohibit_revocable_license": True,
    "require_sublicensable": False,
    "require_transferable": False,
    "require_worldwide_territory": True,
    "require_purpose_limited_license": True,
    "prohibit_derivative_works": False,
    "require_feedback_assigned": True,
    "require_residual_knowledge_rights": True,
    "require_open_source_disclosure": True,
    "require_infringement_remedy_reference": True,
    "require_post_termination_survival": True,
}


# Every dimension below DEFAULT_POLICY's background-IP/joint-ownership pair
# turned off — used to isolate a single dimension under test from every
# other MUST_REDLINE/NEGOTIATE-capable requirement DEFAULT_POLICY also
# turns on, so a test case's text only needs to address the ONE thing it's
# actually about.
_ISOLATE = {
    "require_license_for_embedded_background_ip": False, "require_license_exclusive": False,
    "prohibit_royalty_bearing_license": False, "require_perpetual_license": False,
    "prohibit_revocable_license": False, "require_sublicensable": False, "require_transferable": False,
    "require_worldwide_territory": False, "require_purpose_limited_license": False,
    "prohibit_derivative_works": False, "require_feedback_assigned": False,
    "require_residual_knowledge_rights": False, "require_open_source_disclosure": False,
    "require_infringement_remedy_reference": False, "require_post_termination_survival": False,
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
# Fully-compliant baseline
# ---------------------------------------------------------------------------
FULLY_COMPLIANT_TEXT = (
    "14. Intellectual Property. Vendor shall retain all right, title and interest in and to its "
    "pre-existing intellectual property, including any background technology used in providing the "
    "Services. Customer shall own all right, title and interest in and to the Work Product and "
    "Deliverables created under this Agreement. To the extent any Deliverables do not qualify as a "
    "work made for hire, Vendor hereby assigns to Customer all right, title and interest therein. "
    "Vendor hereby grants to Customer a non-exclusive, worldwide, royalty-free, perpetual and "
    "irrevocable license to use, reproduce, and create derivative works of any Vendor background "
    "intellectual property embodied in the Deliverables, solely for Customer's internal business "
    "purposes. Such license is sublicensable to Customer's Affiliates and is transferable in "
    "connection with a permitted assignment of this Agreement. Customer hereby assigns to Vendor "
    "all feedback, suggestions, and ideas provided regarding the Services. The parties acknowledge "
    "that Vendor personnel may retain and use residual knowledge and skills acquired in the course "
    "of providing the Services. Vendor's use of any open-source software is disclosed in Exhibit B. "
    "Vendor shall defend Customer against any claim that the Deliverables infringe a third party's "
    "intellectual property rights. The license granted herein shall survive termination of this "
    "Agreement."
)

CASES += [
    case("clean-01", ["clean_all"], FULLY_COMPLIANT_TEXT, "ACCEPT",
         notes="Every configured dimension satisfied at the preferred tier."),
    case("clean-02", ["clean_all", "minimal_policy"],
         "14. Intellectual Property. Vendor shall retain all right, title and interest in its "
         "pre-existing intellectual property. Customer shall own all Deliverables.",
         "ACCEPT",
         policy_overrides={
             "require_license_for_embedded_background_ip": False, "prohibit_royalty_bearing_license": False,
             "require_perpetual_license": False, "prohibit_revocable_license": False,
             "require_worldwide_territory": False, "require_purpose_limited_license": False,
             "require_feedback_assigned": False, "require_residual_knowledge_rights": False,
             "require_open_source_disclosure": False, "require_infringement_remedy_reference": False,
             "require_post_termination_survival": False,
         },
         notes="With every other requirement off, bare ownership statements alone satisfy the policy."),
]

# ---------------------------------------------------------------------------
# Ownership: customer owns all deliverables; vendor retains background;
# joint ownership; work-for-hire + fallback assignment; conflicting
# provisions; buy-side framing.
# ---------------------------------------------------------------------------
CASES += [
    case("own-01", ["ownership", "customer_owns_all"],
         "14. Intellectual Property. Customer shall own all right, title and interest in and to all "
         "Deliverables produced under this Agreement, including all intellectual property rights therein.",
         "NEGOTIATE", policy_overrides=dict(_ISOLATE),
         notes="Work-product ownership stated, but background-IP requirement (still on) is "
               "unaddressed — downgrades to NEGOTIATE, not ACCEPT."),
    case("own-02", ["ownership", "vendor_retains_background"],
         "14. Intellectual Property. Vendor shall retain all right, title and interest in and to its "
         "pre-existing intellectual property.",
         "ACCEPT", policy_overrides=dict(_ISOLATE),
         notes="Background IP correctly retained by Vendor (us) satisfies the only remaining active "
               "requirement (prohibit_joint_ownership is trivially satisfied, nothing is stated as "
               "joint) -> ACCEPT."),
    case("own-03", ["ownership", "joint"],
         "14. Intellectual Property. The parties agree that they shall jointly own all Work Product "
         "created under this Agreement.",
         "MUST_REDLINE", policy_overrides=dict(_ISOLATE),
         notes="Joint ownership of work product is prohibited by default policy -> MUST_REDLINE from "
               "the joint-ownership note. (Corrected after benchmark run: original label NEGOTIATE "
               "directly contradicted this file's own reasoning in this note.)"),
    case("own-04", ["ownership", "work_for_hire_fallback"],
         "14. Intellectual Property. All Deliverables shall be deemed a \"work made for hire.\" To the "
         "extent any Deliverables do not qualify as a work made for hire under applicable law, Vendor "
         "hereby assigns to Customer all right, title and interest therein.",
         "NEGOTIATE", policy_overrides=dict(_ISOLATE),
         notes="Work-for-hire plus fallback assignment correctly attributes work product to Customer "
               "(counterparty) — since require_we_own_work_product is False by default, no note fires "
               "for that dimension; background-IP requirement (still on) is unaddressed here -> "
               "NEGOTIATE."),
    case("own-05", ["ownership", "conflicting_provisions"],
         "14. Intellectual Property. Vendor shall own all right, title and interest in and to the "
         "Deliverables. Notwithstanding the foregoing, Customer shall retain all right, title and "
         "interest in and to the Deliverables and all Work Product created under this Agreement.",
         "REQUIRES_REVIEW",
         notes="Two different parties attributed ownership of the same work_product category — "
               "genuine conflict, must abstain."),
    case("own-06", ["ownership", "buy_side_customer_wants_work_product"],
         "14. Intellectual Property. Vendor shall retain all right, title and interest in its "
         "pre-existing intellectual property. Customer shall own all right, title and interest in and "
         "to the Work Product and Deliverables created under this Agreement.",
         "ACCEPT",
         policy_overrides={**_ISOLATE, "contract_side": "buy_side", "require_we_retain_background_ip": False,
                            "require_we_own_work_product": True},
         notes="We are Customer (buy_side); work product correctly attributed to us -> no note; "
               "background-IP requirement is off; every other dimension isolated off -> ACCEPT."),
    case("own-07", ["ownership", "wrong_owner_work_product"],
         "14. Intellectual Property. Vendor shall own all right, title and interest in and to the "
         "Work Product and Deliverables created under this Agreement.",
         "MUST_REDLINE",
         policy_overrides={"contract_side": "buy_side", "require_we_retain_background_ip": False,
                            "require_we_own_work_product": True},
         notes="We are Customer (buy_side) but the clause attributes work product to Vendor — wrong "
               "owner for our policy."),
    case("own-08", ["ownership", "mutual_directional"],
         "14. Intellectual Property. Vendor shall retain all right, title and interest in its "
         "pre-existing intellectual property.",
         "REQUIRES_REVIEW",
         policy_overrides={"contract_side": "mutual"},
         notes="Directional ownership statement under a mutual-position playbook — cannot determine "
               "our ownership without knowing which named party we are."),
    case("own-09", ["ownership", "missing_background_requirement_off"],
         "14. Intellectual Property. Customer shall own all right, title and interest in and to the "
         "Work Product and Deliverables created under this Agreement.",
         "ACCEPT",
         policy_overrides={"require_we_retain_background_ip": False,
                            "require_license_for_embedded_background_ip": False,
                            "prohibit_royalty_bearing_license": False, "require_perpetual_license": False,
                            "prohibit_revocable_license": False, "require_worldwide_territory": False,
                            "require_purpose_limited_license": False, "require_feedback_assigned": False,
                            "require_residual_knowledge_rights": False, "require_open_source_disclosure": False,
                            "require_infringement_remedy_reference": False, "require_post_termination_survival": False},
         notes="With background IP and every license dimension off, a bare work-product ownership "
               "statement alone satisfies the (trivial) remaining policy."),
    case("own-10", ["ownership", "customer_materials_informational"],
         "14. Intellectual Property. Vendor shall retain all right, title and interest in its "
         "pre-existing intellectual property. Customer shall retain all right, title and interest in "
         "Customer Materials provided to Vendor under this Agreement.",
         "ACCEPT", policy_overrides=dict(_ISOLATE),
         notes="Customer-materials ownership is informational-only (no dedicated require_* gate) — "
               "extracted into category_treatments but does not independently change the state; "
               "background IP satisfied and every other dimension isolated off -> ACCEPT."),
]

# ---------------------------------------------------------------------------
# Work-product/background-IP incorporation conflict.
# ---------------------------------------------------------------------------
CASES += [
    case("conflict-01", ["conflict", "wp_includes_background"],
         "9. Intellectual Property. Vendor shall retain ownership of all its pre-existing intellectual "
         "property. All Work Product, including any pre-existing intellectual property embodied "
         "therein, shall be owned exclusively by Customer.",
         "REQUIRES_REVIEW",
         notes="Work-product assignment sweeps in pre-existing IP while a separate provision reserves "
               "background IP to Vendor — genuine drafting conflict."),
    case("conflict-02", ["conflict", "wp_includes_background_no_separate_reservation"],
         "9. Intellectual Property. All Work Product, including any pre-existing intellectual property "
         "embodied therein, shall be owned exclusively by Customer.",
         "NEGOTIATE", policy_overrides=dict(_ISOLATE),
         notes="The inclusion language alone, with no separate background-IP reservation anywhere in "
               "the clause, is not a conflict — nothing to conflict WITH. Work product attributed to "
               "Customer (counterparty); background-IP requirement (still on) unaddressed -> NEGOTIATE."),
]

# ---------------------------------------------------------------------------
# License grants: exclusive vs non-exclusive; royalty; duration;
# revocability; sublicensing; transferability; territory; purpose;
# derivative works; feedback; residuals; open source; SOW cross-refs.
# ---------------------------------------------------------------------------
_LICENSE_BASE = ("14. Intellectual Property. Vendor shall retain all right, title and interest in its "
                  "pre-existing intellectual property. {license_clause}")

CASES += [
    case("lic-01", ["license", "exclusive"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer an exclusive license to "
                               "use the Vendor background intellectual property embodied in the Deliverables."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_license_exclusive": True},
         notes="CORRECTED after benchmark run: exclusive license satisfies the exclusivity "
               "requirement; background IP satisfied; everything else isolated off -> ACCEPT "
               "(original label NEGOTIATE contradicted this case's own reasoning note)."),
    case("lic-02", ["license", "non_exclusive_but_exclusive_required"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a non-exclusive license "
                               "to use the Vendor background intellectual property embodied in the Deliverables."),
         "NEGOTIATE",
         policy_overrides={"require_license_exclusive": True, "require_license_for_embedded_background_ip": False,
                            "prohibit_royalty_bearing_license": False, "require_perpetual_license": False,
                            "prohibit_revocable_license": False, "require_worldwide_territory": False,
                            "require_purpose_limited_license": False, "require_feedback_assigned": False,
                            "require_residual_knowledge_rights": False, "require_open_source_disclosure": False,
                            "require_infringement_remedy_reference": False, "require_post_termination_survival": False},
         notes="Non-exclusive license does not satisfy an exclusivity requirement."),
    case("lic-03", ["license", "royalty_free"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a royalty-free license "
                               "to use the Vendor background intellectual property embodied in the Deliverables."),
         "NEGOTIATE", notes="Royalty-free satisfies the royalty-free requirement; other unaddressed "
                             "dims keep NEGOTIATE."),
    case("lic-04", ["license", "paid_royalty_prohibited"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a license to use the "
                               "Vendor background intellectual property embodied in the Deliverables, "
                               "subject to a royalty of 5% of Net Sales."),
         "MUST_REDLINE", notes="Royalty-bearing license, prohibited by policy (royalty-free required)."),
    case("lic-05", ["license", "perpetual"],
         _LICENSE_BASE.format(license_clause="The license granted herein is perpetual and irrevocable."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_perpetual_license": True},
         notes="Perpetual satisfies the perpetual-license requirement; background IP satisfied; "
               "everything else isolated off -> ACCEPT."),
    case("lic-06", ["license", "term_limited"],
         _LICENSE_BASE.format(license_clause="This license shall terminate upon expiration of the "
                               "Initial Term."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "require_perpetual_license": True},
         notes="Term-limited license does not satisfy a perpetual-license requirement."),
    case("lic-07", ["license", "term_years"],
         _LICENSE_BASE.format(license_clause="This license is granted for a term of 5 years."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "require_perpetual_license": True},
         notes="Fixed-term (5 years) license does not satisfy a perpetual-license requirement."),
    case("lic-08", ["license", "revocable_expressly"],
         _LICENSE_BASE.format(license_clause="This license is perpetual but revocable at Vendor's "
                               "discretion upon 30 days' written notice."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "prohibit_revocable_license": True},
         notes="Expressly revocable, prohibited by policy (irrevocable required)."),
    case("lic-09", ["license", "revocability_missing"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a license to use the "
                               "Vendor background intellectual property embodied in the Deliverables."),
         "NEGOTIATE",
         policy_overrides={"prohibit_revocable_license": True, "require_license_for_embedded_background_ip": False,
                            "prohibit_royalty_bearing_license": False, "require_perpetual_license": False,
                            "require_worldwide_territory": False, "require_purpose_limited_license": False,
                            "require_feedback_assigned": False, "require_residual_knowledge_rights": False,
                            "require_open_source_disclosure": False, "require_infringement_remedy_reference": False,
                            "require_post_termination_survival": False},
         notes="Revocability never addressed at all -- policy requiring irrevocable treats silence as "
               "a gap, same as an explicit revocable grant."),
    case("lic-10", ["license", "sublicensable"],
         _LICENSE_BASE.format(license_clause="Such license is sublicensable to Customer's Affiliates."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_sublicensable": True},
         notes="Sublicensable satisfies a sublicensing requirement; background IP satisfied; "
               "everything else isolated off -> ACCEPT."),
    case("lic-11", ["license", "non_sublicensable"],
         _LICENSE_BASE.format(license_clause="This license is non-sublicensable."),
         "NEGOTIATE",
         policy_overrides={"require_sublicensable": True, "require_license_for_embedded_background_ip": False,
                            "prohibit_royalty_bearing_license": False, "require_perpetual_license": False,
                            "prohibit_revocable_license": False, "require_worldwide_territory": False,
                            "require_purpose_limited_license": False, "require_feedback_assigned": False,
                            "require_residual_knowledge_rights": False, "require_open_source_disclosure": False,
                            "require_infringement_remedy_reference": False, "require_post_termination_survival": False},
         notes="Expressly non-sublicensable does not satisfy a sublicensing requirement."),
    case("lic-12", ["license", "transferable"],
         _LICENSE_BASE.format(license_clause="This license is transferable in connection with a "
                               "permitted assignment of this Agreement."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_transferable": True},
         notes="Transferable satisfies a transferability requirement; background IP satisfied; "
               "everything else isolated off -> ACCEPT."),
    case("lic-13", ["license", "non_transferable"],
         _LICENSE_BASE.format(license_clause="This license is non-transferable and may not be assigned."),
         "NEGOTIATE",
         policy_overrides={"require_transferable": True, "require_license_for_embedded_background_ip": False,
                            "prohibit_royalty_bearing_license": False, "require_perpetual_license": False,
                            "prohibit_revocable_license": False, "require_worldwide_territory": False,
                            "require_purpose_limited_license": False, "require_feedback_assigned": False,
                            "require_residual_knowledge_rights": False, "require_open_source_disclosure": False,
                            "require_infringement_remedy_reference": False, "require_post_termination_survival": False},
         notes="Expressly non-transferable does not satisfy a transferability requirement."),
    case("lic-14", ["license", "worldwide"],
         _LICENSE_BASE.format(license_clause="This license is granted on a worldwide basis."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_worldwide_territory": True},
         notes="Worldwide territory satisfies the territory requirement; background IP satisfied; "
               "everything else isolated off -> ACCEPT."),
    case("lic-15", ["license", "restricted_territory"],
         _LICENSE_BASE.format(license_clause="This license is limited to North America."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "require_worldwide_territory": True},
         notes="Restricted territory does not satisfy a worldwide-territory requirement."),
    case("lic-16", ["license", "purpose_limited"],
         _LICENSE_BASE.format(license_clause="This license is granted solely for Customer's internal "
                               "business purposes."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_purpose_limited_license": True},
         notes="Purpose-limited language satisfies the field-of-use requirement; background IP "
               "satisfied; everything else isolated off -> ACCEPT."),
    case("lic-17", ["license", "purpose_unlimited"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a license to use the "
                               "Vendor background intellectual property embodied in the Deliverables "
                               "for any purpose."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "require_purpose_limited_license": True},
         notes="No purpose-limiting language found — policy requires field-of-use restriction."),
    case("lic-18", ["license", "derivative_permitted"],
         _LICENSE_BASE.format(license_clause="Customer may create derivative works of the Deliverables."),
         "MUST_REDLINE",
         policy_overrides={**_ISOLATE, "prohibit_derivative_works": True},
         notes="Derivative works expressly permitted, prohibited by policy."),
    case("lic-19", ["license", "derivative_prohibited"],
         _LICENSE_BASE.format(license_clause="Customer shall not create derivative works of the "
                               "Deliverables."),
         "ACCEPT",
         policy_overrides={**_ISOLATE, "prohibit_derivative_works": True},
         notes="Derivative works expressly prohibited -- satisfies (does not violate) the "
               "prohibition; background IP satisfied; everything else isolated off -> ACCEPT."),
    case("lic-20", ["license", "feedback_assigned"],
         _LICENSE_BASE.format(license_clause="Customer hereby assigns to Vendor all feedback, "
                               "suggestions, and ideas provided regarding the Services."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_feedback_assigned": True},
         notes="Feedback assigned outright satisfies the feedback requirement; background IP "
               "satisfied; everything else isolated off -> ACCEPT."),
    case("lic-21", ["license", "feedback_licensed_only"],
         _LICENSE_BASE.format(license_clause="Customer hereby grants to Vendor a license to use any "
                               "feedback, suggestions, and ideas provided regarding the Services."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "require_feedback_assigned": True},
         notes="Feedback only licensed (not assigned) does not satisfy an assignment-required policy."),
    case("lic-22", ["license", "feedback_layered_fallback"],
         _LICENSE_BASE.format(license_clause="Customer hereby assigns to Vendor all feedback provided "
                               "regarding the Services, or, to the extent such feedback is not "
                               "assignable, hereby grants Vendor a perpetual license to use such "
                               "feedback."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_feedback_assigned": True},
         notes="Standard assign-or-fallback-license drafting — 'assigned' still resolves (not a "
               "conflict) since assignment is the stronger, controlling commitment stated first; "
               "background IP satisfied; everything else isolated off -> ACCEPT."),
    case("lic-23", ["license", "residual_knowledge"],
         _LICENSE_BASE.format(license_clause="The parties acknowledge that Vendor personnel may retain "
                               "and use residual knowledge acquired in the course of providing the "
                               "Services."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_residual_knowledge_rights": True},
         notes="Residual-knowledge rights satisfied; background IP satisfied; everything else "
               "isolated off -> ACCEPT."),
    case("lic-24", ["license", "open_source"],
         _LICENSE_BASE.format(license_clause="Vendor's use of any open-source software components is "
                               "disclosed in Exhibit C."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_open_source_disclosure": True},
         notes="Open-source disclosure satisfied; background IP satisfied; everything else isolated "
               "off -> ACCEPT."),
    case("lic-25", ["license", "infringement_reference"],
         _LICENSE_BASE.format(license_clause="Vendor shall defend Customer against any claim that the "
                               "Deliverables infringe a third party's patent or copyright."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_infringement_remedy_reference": True},
         notes="Infringement/third-party-IP treatment referenced; background IP satisfied; everything "
               "else isolated off -> ACCEPT."),
    case("lic-26", ["license", "post_termination_survival"],
         _LICENSE_BASE.format(license_clause="The license granted herein shall survive termination or "
                               "expiration of this Agreement."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_post_termination_survival": True},
         notes="Survival commitment satisfied; background IP satisfied; everything else isolated off "
               "-> ACCEPT."),
    case("lic-27", ["license", "embedded_license_missing"],
         "14. Intellectual Property. Vendor shall retain all right, title and interest in its "
         "pre-existing intellectual property. Customer shall own all right, title and interest in the "
         "Deliverables.",
         "MUST_REDLINE",
         notes="Background IP retained by Vendor but no license granted to Customer to use it as "
               "embodied in the Deliverables — required by policy."),
]

# ---------------------------------------------------------------------------
# License term/exclusivity/royalty/revocability/sublicensing/transferable/
# territory/derivative conflicts (multiple grants stating different things).
# ---------------------------------------------------------------------------
CASES += [
    case("lic-conflict-01", ["license", "conflict", "exclusivity"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a non-exclusive license "
                               "to use the Deliverables. Notwithstanding the foregoing, such license "
                               "shall be exclusive to Customer within the software industry."),
         "REQUIRES_REVIEW", notes="Both 'non-exclusive' and 'exclusive' stated for the same license — "
                                   "genuine conflict."),
    case("lic-conflict-02", ["license", "conflict", "royalty"],
         _LICENSE_BASE.format(license_clause="The license is royalty-free. Notwithstanding the "
                               "foregoing, Customer shall pay Vendor a royalty of 3% of Net Sales for "
                               "use of the licensed technology."),
         "REQUIRES_REVIEW", notes="Both royalty-free and paid-royalty language stated — genuine "
                                   "conflict."),
    case("lic-conflict-03", ["license", "conflict", "duration"],
         _LICENSE_BASE.format(license_clause="The license is perpetual. Notwithstanding the foregoing, "
                               "this license shall terminate upon expiration of the Initial Term."),
         "REQUIRES_REVIEW", notes="Both perpetual and term-limited stated — genuine conflict."),
    case("lic-conflict-04", ["license", "conflict", "revocability"],
         _LICENSE_BASE.format(license_clause="The license is irrevocable. Notwithstanding the "
                               "foregoing, Vendor may revoke this license upon 30 days' written "
                               "notice."),
         "REQUIRES_REVIEW", notes="Both irrevocable and revocable stated — genuine conflict."),
    case("lic-conflict-05", ["license", "conflict", "sublicensing"],
         _LICENSE_BASE.format(license_clause="This license is sublicensable to Customer's Affiliates. "
                               "Notwithstanding the foregoing, this license is non-sublicensable."),
         "REQUIRES_REVIEW", notes="Both sublicensable and non-sublicensable stated — genuine "
                                   "conflict."),
    case("lic-conflict-06", ["license", "conflict", "transferability"],
         _LICENSE_BASE.format(license_clause="This license is transferable in connection with a "
                               "permitted assignment. Notwithstanding the foregoing, this license is "
                               "non-transferable."),
         "REQUIRES_REVIEW", notes="Both transferable and non-transferable stated — genuine conflict."),
    case("lic-conflict-07", ["license", "conflict", "territory"],
         _LICENSE_BASE.format(license_clause="This license is granted on a worldwide basis. "
                               "Notwithstanding the foregoing, use of the licensed technology is "
                               "limited to North America."),
         "REQUIRES_REVIEW", notes="Both worldwide and a restricted territory stated — genuine "
                                   "conflict."),
    case("lic-conflict-08", ["license", "conflict", "derivative"],
         _LICENSE_BASE.format(license_clause="Customer may create derivative works of the Deliverables. "
                               "Notwithstanding the foregoing, Customer shall not create derivative "
                               "works of the Deliverables."),
         "REQUIRES_REVIEW", notes="Both derivative-works-permitted and prohibited stated — genuine "
                                   "conflict."),
]

# ---------------------------------------------------------------------------
# SOW cross-reference (delegation to an external doc).
# ---------------------------------------------------------------------------
CASES += [
    case("sow-crossref-01", ["sow_crossref", "nothing_else"],
         "14. Intellectual Property. All intellectual property ownership, license grants, "
         "exclusivity, duration, and territory with respect to Deliverables shall be as set forth in "
         "the applicable Statement of Work.",
         "REQUIRES_REVIEW",
         notes="Material IP ownership/license terms are delegated wholesale to an external SOW with "
               "no dimension independently established in-clause — cannot evaluate deterministically."),
    case("sow-crossref-02", ["sow_crossref", "supplementing"],
         FULLY_COMPLIANT_TEXT + " This Section is further supplemented by the applicable Statement of "
         "Work.",
         "ACCEPT",
         notes="An SOW cross-reference that supplements (rather than replaces) an otherwise-complete "
               "in-clause treatment does not, on its own, block evaluation."),
]

# ---------------------------------------------------------------------------
# Multiple sections / amendments (document-wide, consistent vs changed).
# ---------------------------------------------------------------------------
CASES += [
    case("multi-section-01", ["multi_section", "consistent"],
         "14. Intellectual Property. Vendor shall retain all right, title and interest in its "
         "pre-existing intellectual property. The license granted herein is perpetual.\n\n22. "
         "Amendment to IP Terms. For the avoidance of doubt, Vendor confirms its pre-existing "
         "intellectual property remains its sole property, and the license remains perpetual, "
         "consistent with Section 14.",
         "ACCEPT", policy_overrides={**_ISOLATE, "require_perpetual_license": True},
         notes="Two anchored windows restate the SAME owner and SAME duration — no conflict, values "
               "merge cleanly; background IP and perpetual duration both satisfied, everything else "
               "isolated off -> ACCEPT."),
    case("multi-section-02", ["multi_section", "amendment_changes_duration"],
         "14. Intellectual Property. Vendor shall retain all right, title and interest in its "
         "pre-existing intellectual property. The license granted herein is perpetual.\n\n22. First "
         "Amendment. Section 14 is hereby amended to provide that the license granted therein shall "
         "terminate upon expiration of the Initial Term.",
         "REQUIRES_REVIEW", policy_overrides={**_ISOLATE, "require_perpetual_license": True},
         notes="The original clause and the amendment state two DIFFERENT license durations — the "
               "extractor cannot determine which one controls without legal interpretation."),
]

# ---------------------------------------------------------------------------
# No IP clause -> NOT_APPLICABLE.
# ---------------------------------------------------------------------------
CASES += [
    case("not-applicable-01", ["not_applicable"],
         "9. Governing Law. This Agreement shall be governed by the laws of the State of Delaware, "
         "without regard to its conflicts of laws principles.",
         "NOT_APPLICABLE", notes="No IP ownership/licensing clause anchor at all."),
    case("not-applicable-02", ["not_applicable", "commercial_only"],
         "9. Fees. Customer shall pay Vendor the fees set forth in the applicable Order Form within "
         "30 days of invoice.",
         "NOT_APPLICABLE", notes="Ordinary commercial clause, no IP content."),
]

# ---------------------------------------------------------------------------
# Malformed / degenerate clauses.
# ---------------------------------------------------------------------------
CASES += [
    case("malformed-01", ["malformed", "fragment"],
         "14. Intellectual Property. Work product.",
         "NEGOTIATE", policy_overrides=dict(_ISOLATE),
         notes="Anchor matches ('work product') but the fragment establishes nothing — background-IP "
               "requirement (still on) falls through to its 'no ownership statement found' branch, "
               "which is NEGOTIATE, not REQUIRES_REVIEW."),
    case("malformed-02", ["malformed", "heading_only"],
         "14. Intellectual Property.",
         "NEGOTIATE", policy_overrides=dict(_ISOLATE),
         notes="The section heading itself ('Intellectual Property') matches the anchor, so "
               "clause_found=True even with no body — same treatment as malformed-01's bare fragment, "
               "not a fabricated NOT_APPLICABLE."),
    case("malformed-03", ["malformed", "ocr_noise"],
         "14.  Intellectual   Property .   Vendor  shall   retain  all   right ,  title   and  "
         "interest  in  its   pre-existing  intellectual  property .",
         "ACCEPT", policy_overrides=dict(_ISOLATE),
         notes="Irregular whitespace (OCR-style artifact) should not defeat the anchor or ownership "
               "regexes, which tolerate \\s+ throughout — background IP correctly retained by Vendor "
               "(us); everything else isolated off -> ACCEPT."),
]

# ---------------------------------------------------------------------------
# Ambiguous pronouns.
# ---------------------------------------------------------------------------
CASES += [
    case("ambiguous-pronoun-01", ["ambiguous_pronoun"],
         "14. Intellectual Property. Each party shall retain ownership of its own pre-existing "
         "intellectual property. Neither party shall use the other's intellectual property except as "
         "expressly licensed herein.",
         "NEGOTIATE", policy_overrides=dict(_ISOLATE),
         notes="No named-party ownership statement is extractable here at all (generic 'each "
               "party'/'its own' pronouns, no resolvable party name) — ownership_attributions stays "
               "empty, so the 'no ownership statement found' NEGOTIATE note fires rather than a false "
               "abstention."),
]

# ---------------------------------------------------------------------------
# Explicit negations.
# ---------------------------------------------------------------------------
CASES += [
    case("negation-01", ["negation", "no_derivative_works"],
         _LICENSE_BASE.format(license_clause="Customer shall not create derivative works of the "
                               "Deliverables."),
         "ACCEPT",
         policy_overrides={**_ISOLATE, "prohibit_derivative_works": False},
         notes="Prohibition not configured, so an explicit negation of derivative-works rights simply "
               "isn't checked against that dimension; background IP satisfied; everything else "
               "isolated off -> ACCEPT."),
    case("negation-02", ["negation", "no_sublicense"],
         _LICENSE_BASE.format(license_clause="This license is non-sublicensable and Customer shall not "
                               "sublicense any rights granted herein."),
         "NEGOTIATE",
         policy_overrides={"require_sublicensable": True, "require_license_for_embedded_background_ip": False,
                            "prohibit_royalty_bearing_license": False, "require_perpetual_license": False,
                            "prohibit_revocable_license": False, "require_worldwide_territory": False,
                            "require_purpose_limited_license": False, "require_feedback_assigned": False,
                            "require_residual_knowledge_rights": False, "require_open_source_disclosure": False,
                            "require_infringement_remedy_reference": False, "require_post_termination_survival": False},
         notes="Explicit double-negation of sublicensing does not satisfy a sublicensing requirement."),
]

# ---------------------------------------------------------------------------
# Exceptions / carve-outs.
# ---------------------------------------------------------------------------
CASES += [
    case("exception-01", ["exception", "purpose_carveout"],
         _LICENSE_BASE.format(license_clause="This license is granted solely for Customer's internal "
                               "business purposes, except that Customer may use the licensed technology "
                               "for customer-facing demonstrations."),
         "ACCEPT", policy_overrides={**_ISOLATE, "require_purpose_limited_license": True},
         notes="The purpose-limiting language is the dominant, clearly-stated commitment; the "
               "demonstration carve-out is a minor exception the regex does not need to specially "
               "detect for the top-level purpose-limited boolean to be satisfied. Background IP "
               "satisfied; everything else isolated off -> ACCEPT."),
    case("exception-02", ["exception", "sublicense_affiliate_carveout"],
         _LICENSE_BASE.format(license_clause="This license is non-sublicensable, except that Customer "
                               "may sublicense to its wholly-owned Affiliates."),
         "REQUIRES_REVIEW",
         policy_overrides={**_ISOLATE, "require_sublicensable": True},
         notes="CORRECTED after benchmark run: the same window matches both the non-sublicensable "
               "phrase and the 'may sublicense' carve-out — the token-set reconciliation the engine "
               "uses to catch genuine same-window conflicts (see lic-conflict-* cases) cannot, with "
               "simple regex extraction, distinguish 'flatly contradictory' from 'general rule plus "
               "narrow carve-out' within one sentence. Treating this as REQUIRES_REVIEW rather than "
               "silently picking a side is the conservative, correct behavior given that limitation — "
               "original label (NEGOTIATE) assumed a precision the extractor does not actually have "
               "for layered exception clauses."),
]

# ---------------------------------------------------------------------------
# Additional coverage: term-years extraction, buy-side full compliance,
# mutual license grants, non-exclusive accepted by default, additional
# malformed/negation/no-clause patterns not yet independently exercised.
# ---------------------------------------------------------------------------
CASES += [
    case("term-years-01", ["license", "term_years_extraction"],
         _LICENSE_BASE.format(license_clause="This license is granted for a term of 3 years."),
         "ACCEPT", policy_overrides=dict(_ISOLATE),
         notes="license_term_years should extract to 3 (informational only, no dedicated require_* "
               "gate); duration itself isn't checked since require_perpetual_license is isolated off "
               "-> background IP alone (satisfied) -> ACCEPT."),
    case("buyside-clean-01", ["clean_all", "buy_side"],
         "14. Intellectual Property. Vendor shall retain all right, title and interest in its "
         "pre-existing intellectual property. Customer shall own all right, title and interest in the "
         "Work Product and Deliverables created under this Agreement. Vendor hereby grants to Customer "
         "a non-exclusive, worldwide, royalty-free, perpetual and irrevocable license to use, "
         "reproduce, and create derivative works of any Vendor background intellectual property "
         "embodied in the Deliverables, solely for Customer's internal business purposes. Such "
         "license is sublicensable to Customer's Affiliates and is transferable in connection with a "
         "permitted assignment of this Agreement. Customer hereby assigns to Vendor all feedback "
         "provided regarding the Services. Vendor personnel may retain and use residual knowledge "
         "acquired in the course of providing the Services. Vendor's use of open-source software is "
         "disclosed in Exhibit B. Vendor shall defend Customer against any claim that the "
         "Deliverables infringe a third party's patent. The license granted herein shall survive "
         "termination of this Agreement.",
         "ACCEPT",
         policy_overrides={"contract_side": "buy_side", "require_we_retain_background_ip": False,
                            "require_we_own_work_product": True},
         notes="We are Customer (buy_side); work product correctly attributed to us; every license "
               "dimension satisfied at the preferred tier -> ACCEPT."),
    case("nonexclusive-default-01", ["license", "exclusivity_not_required"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a non-exclusive license "
                               "to use the Vendor background intellectual property embodied in the "
                               "Deliverables."),
         "ACCEPT", policy_overrides=dict(_ISOLATE),
         notes="require_license_exclusive is False by default (and isolated off here) — a "
               "non-exclusive grant is the ordinary case and must not be penalized when exclusivity "
               "was never required; background IP satisfied -> ACCEPT."),
    case("malformed-04", ["malformed", "no_party_named_ownership_phrase"],
         "14. Intellectual Property. All right, title and interest in the Deliverables shall vest "
         "upon creation.",
         "NEGOTIATE", policy_overrides=dict(_ISOLATE),
         notes="'Shall vest upon creation' names no owner at all (matches neither the active nor "
               "passive ownership regex, which both require a named party) — background-IP "
               "requirement (still on) falls through to 'no ownership statement found' -> NEGOTIATE, "
               "not a false attribution."),
    case("not-applicable-03", ["not_applicable", "confidentiality_only"],
         "9. Confidentiality. Each party shall protect the other's Confidential Information using "
         "reasonable care for a period of 5 years following termination.",
         "NOT_APPLICABLE", notes="A Confidentiality clause alone, with no IP ownership/licensing "
                                  "content, does not anchor this adapter."),
    case("negation-03", ["negation", "no_worldwide"],
         _LICENSE_BASE.format(license_clause="This license does not extend beyond the territory of "
                               "the United States."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "require_worldwide_territory": True},
         notes="An explicit territorial restriction (whatever its exact phrasing) does not establish "
               "'worldwide' -- territory stays unaddressed by the worldwide/restricted-territory "
               "regexes here (no 'limited to'/'solely within' trigger phrase), so this scores as a "
               "plain 'no stated territory' gap, same as silence."),
    case("residual-missing-01", ["license", "residual_missing"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a license to use the "
                               "Vendor background intellectual property embodied in the Deliverables."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "require_residual_knowledge_rights": True},
         notes="No residual-knowledge language present — policy requires it, so this is a gap, not a "
               "false ACCEPT."),
    case("infringement-missing-01", ["license", "infringement_missing"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a license to use the "
                               "Vendor background intellectual property embodied in the Deliverables."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "require_infringement_remedy_reference": True},
         notes="No infringement/third-party-IP reference present — policy requires it, so this is a "
               "gap."),
    case("survival-missing-01", ["license", "survival_missing"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a license to use the "
                               "Vendor background intellectual property embodied in the Deliverables."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "require_post_termination_survival": True},
         notes="No post-termination survival language present — policy requires it, so this is a "
               "gap."),
    case("open-source-missing-01", ["license", "open_source_missing"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a license to use the "
                               "Vendor background intellectual property embodied in the Deliverables."),
         "NEGOTIATE", policy_overrides={**_ISOLATE, "require_open_source_disclosure": True},
         notes="No open-source disclosure language present — policy requires it, so this is a gap."),
    case("royalty-silent-01", ["license", "royalty_silent"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer a license to use the "
                               "Vendor background intellectual property embodied in the Deliverables."),
         "ACCEPT", policy_overrides=dict(_ISOLATE),
         notes="Royalty treatment never addressed at all; prohibit_royalty_bearing_license only fires "
               "when royalty=='paid' is actually found — silence is not held against the clause for a "
               "prohibition (as opposed to a requirement), so background IP alone (isolated) -> "
               "ACCEPT."),
    case("exclusive-prohibited-not-modeled", ["license", "exclusive_stated_no_requirement"],
         _LICENSE_BASE.format(license_clause="Vendor hereby grants to Customer an exclusive license to "
                               "use the Vendor background intellectual property embodied in the "
                               "Deliverables."),
         "ACCEPT", policy_overrides=dict(_ISOLATE),
         notes="An exclusive grant is neither required nor prohibited by this adapter's Protocol (no "
               "prohibit_exclusive_license field exists) — background IP alone (isolated) -> ACCEPT."),
    case("sow-crossref-03", ["sow_crossref", "specific_dimension_only"],
         "14. Intellectual Property. Vendor shall retain all right, title and interest in its "
         "pre-existing intellectual property. Royalty rates and payment terms for the license granted "
         "hereunder shall be as set forth in the applicable Statement of Work.",
         "ACCEPT", policy_overrides=dict(_ISOLATE),
         notes="Background IP is independently established in-clause (established_dimension_count > "
               "0 via ownership_attributions) even though royalty terms are cross-referenced to an "
               "SOW — the cross-reference does not block evaluation when other material terms are "
               "already resolved in-text; with royalty isolated off, this scores ACCEPT."),
]
