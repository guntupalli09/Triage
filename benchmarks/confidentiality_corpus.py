"""
Labeled adversarial corpus for the Confidentiality policy engine
benchmark (see benchmarks/run_confidentiality_benchmark.py). Batch A,
adapter 1 of 3.

Labels here were written from the policy semantics and drafting pattern
alone, never by running the implementation and copying its output.
DEFAULT_POLICY represents a sell-side vendor's playbook.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "sell_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: mutual confidentiality, 5-year duration, standard exclusions.",
    "required_exclusions_json": [],
    "min_protection_duration_years": 3,
    "max_exposure_duration_years": None,
    "require_mutual_confidentiality": True,
}


def case(
    id: str,
    tags: List[str],
    text: str,
    expected_state: str,
    expected_exclusions: Any = "SKIP",
    policy_overrides: Optional[Dict[str, Any]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "expected_state": expected_state,
        "expected_exclusions": expected_exclusions,
        "policy_overrides": policy_overrides or {},
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

CASES += [
    case("clean-01", ["clean_mutual"],
         "10. Confidentiality. Each party shall protect the confidentiality of the other "
         "party's Confidential Information using reasonable care, for a period of 5 years "
         "after the termination of this Agreement. Confidential Information does not include "
         "information that is publicly known, independently developed by the receiving "
         "party, rightfully received from a third party, or required by law to be disclosed.",
         "ACCEPT",
         {"public_knowledge": True, "independently_developed": True, "third_party_rightful": True, "required_by_law": True}),
    case("clean-02", ["clean_mutual", "perpetual"],
         "10. Confidentiality. Each party shall protect the confidentiality of the other "
         "party's Confidential Information using reasonable care, in perpetuity.",
         "ACCEPT"),
    case("unilateral-01", ["unilateral"],
         "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
         "Confidential Information using reasonable care, for 5 years.",
         "NEGOTIATE", notes="No reciprocal protection stated; mutuality required by default policy."),
    case("unilateral-02", ["unilateral"],
         "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
         "Confidential Information using reasonable care, for 5 years.",
         "ACCEPT", policy_overrides={"require_mutual_confidentiality": False}),
    case("unilateral-03", ["unilateral", "buy_side"],
         "10. Confidentiality. Customer shall protect the confidentiality of Vendor's "
         "Confidential Information using reasonable care, for 5 years.",
         "NEGOTIATE",
         policy_overrides={"contract_side": "buy_side"},
         notes="We are Customer; our exposure is protecting Vendor's info, no reciprocal "
               "protection stated for us."),
]

CASES += [
    case("duration-01", ["duration"],
         "10. Confidentiality. Customer shall protect the confidentiality of Vendor's "
         "Confidential Information using reasonable care, for 5 years.",
         "ACCEPT", policy_overrides={"require_mutual_confidentiality": False}),
    case("duration-02", ["duration"],
         "10. Confidentiality. Customer shall protect the confidentiality of Vendor's "
         "Confidential Information using reasonable care, for 1 year.",
         "NEGOTIATE", policy_overrides={"require_mutual_confidentiality": False}),
    case("duration-03", ["duration"],
         "10. Confidentiality. Customer shall protect the confidentiality of Vendor's "
         "Confidential Information using reasonable care.",
         "MUST_REDLINE", policy_overrides={"require_mutual_confidentiality": False},
         notes="No duration stated at all."),
    case("duration-04", ["duration", "perpetual"],
         "10. Confidentiality. Customer shall protect the confidentiality of Vendor's "
         "Confidential Information using reasonable care, in perpetuity.",
         "ACCEPT", policy_overrides={"require_mutual_confidentiality": False, "min_protection_duration_years": 10},
         notes="Perpetual protection satisfies any stated minimum."),
    case("duration-05", ["duration", "exposure_max"],
         "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
         "Confidential Information using reasonable care, in perpetuity.",
         "ESCALATE",
         policy_overrides={"require_mutual_confidentiality": False, "min_protection_duration_years": None,
                            "max_exposure_duration_years": 10},
         notes="Our own exposure is perpetual, exceeding a configured maximum — escalate."),
]

CASES += [
    case("exclusions-01", ["exclusions"],
         "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
         "Confidential Information using reasonable care, for 5 years. Confidential "
         "Information does not include information that is publicly known or required by "
         "law to be disclosed.",
         "ACCEPT",
         {"public_knowledge": True, "required_by_law": True},
         policy_overrides={"require_mutual_confidentiality": False, "min_protection_duration_years": None,
                            "required_exclusions_json": ["public_knowledge", "required_by_law"]}),
    case("exclusions-02", ["exclusions"],
         "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
         "Confidential Information using reasonable care, for 5 years.",
         "NEGOTIATE",
         policy_overrides={"require_mutual_confidentiality": False, "min_protection_duration_years": None,
                            "required_exclusions_json": ["public_knowledge", "required_by_law"]},
         notes="Required exclusions entirely absent from our own exposure obligation."),
]

CASES += [
    case("symmetry-01", ["reciprocal_symmetry"],
         "10. Confidentiality. Each party shall protect the confidentiality of the other "
         "party's Confidential Information using reasonable care, for a period of 5 years.",
         "ACCEPT", notes="Genuinely mutual, no per-party attribution — baseline."),
    case("symmetry-02", ["reciprocal_symmetry", "adversarial"],
         "10. Confidentiality. Each party shall protect the confidentiality of the other "
         "party's Confidential Information using reasonable care; provided, that Vendor's "
         "confidentiality obligations under this Section last for 5 years, and Customer's "
         "confidentiality obligations under this Section last for 1 year.",
         "REQUIRES_REVIEW",
         notes="Opens with 'each party' (claiming symmetry) but a differentiated proviso "
               "states different durations per named party — same third-shape verification "
               "concern as Indemnification's and Termination's reciprocal clauses."),
    case("symmetry-03", ["reciprocal_symmetry"],
         "10. Confidentiality. Each party shall protect the confidentiality of the other "
         "party's Confidential Information using reasonable care; Vendor's confidentiality "
         "obligations under this Section last for 5 years, and Customer's confidentiality "
         "obligations under this Section last for 5 years.",
         "ACCEPT", notes="Both named parties' terms genuinely agree — must not be flagged."),
]

CASES += [
    case("undefined-01", ["undefined_parties"],
         "10. Confidentiality. Acme shall protect the confidentiality of Globex's "
         "Confidential Information using reasonable care, for 5 years.",
         "REQUIRES_REVIEW", notes="Neither 'Acme' nor 'Globex' is a recognized role word."),
    case("mutual-policy-01", ["mutual_policy"],
         "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
         "Confidential Information using reasonable care, for 5 years.",
         "REQUIRES_REVIEW", policy_overrides={"contract_side": "mutual"},
         notes="Recognized roles, but policy is configured mutual while the contract is "
               "directional."),
]

CASES += [
    case("malformed-01", ["malformed"],
         "10. Confidntiality. Vendr shal protct th confidentality of Customr's Confidential "
         "Informaton using reasnable care.",
         "REQUIRES_REVIEW",
         notes="The heading typo ('Confidntiality') and 'confidentality' both miss the "
               "'confidential' substring the anchor requires, but 'Confidential Informaton' "
               "later in the same sentence is spelled correctly, so the anchor still fires. "
               "The operative verb phrase ('Vendr shal protct') is too corrupted to match the "
               "obligation pattern regardless — REQUIRES_REVIEW, not a guess."),
    case("malformed-02", ["malformed"],
         "10.  Confidentiality.    Each   party   shall   protect   the   confidentiality   "
         "of   the   other   party's   Confidential   Information   using   reasonable   "
         "care,   for   a   period   of   5   years.",
         "ACCEPT", notes="Excess whitespace only, words spelled correctly."),
    case("malformed-03", ["malformed"],
         "10. Confidentiality. [***] shall protect the confidentiality of [***]'s "
         "Confidential Information using reasonable care, for 5 years.",
         "REQUIRES_REVIEW", notes="Redacted party names — must not fabricate roles."),
]

CASES += [
    case("absent-01", ["absent"],
         "9. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware.",
         "NOT_APPLICABLE"),
    case("absent-02", ["absent"],
         "9. Governing Law. This Agreement is governed by Delaware law. No confidentiality "
         "obligation is created under this Agreement.",
         "NOT_APPLICABLE"),
]

CASES += [
    case("scope-01", ["marking_scope"],
         "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
         "Confidential Information, whether or not marked confidential, using reasonable "
         "care, for 5 years.",
         "ACCEPT", policy_overrides={"require_mutual_confidentiality": False},
         notes="Broad-scope (unmarked-included) definition — verifies extraction doesn't "
               "break; not independently scored by policy in this pass."),
    case("care-01", ["standard_of_care"],
         "10. Confidentiality. Vendor shall protect the confidentiality of Customer's "
         "Confidential Information using the same degree of care it uses to protect its own "
         "confidential information, for 5 years.",
         "ACCEPT", policy_overrides={"require_mutual_confidentiality": False},
         notes="'Same as own' standard of care — a common, acceptable alternative to "
               "'reasonable care'; verifies extraction recognizes it."),
]
