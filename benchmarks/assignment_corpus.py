"""
Labeled adversarial corpus for the Assignment policy engine benchmark
(see benchmarks/run_assignment_benchmark.py). Batch A, adapter 2 of 3.

Labels here were written from the policy semantics and drafting pattern
alone. DEFAULT_POLICY represents a sell-side vendor's playbook.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "sell_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: mutual consent requirement, affiliate/M&A exceptions.",
    "required_exceptions_json": [],
    "prohibit_sole_discretion_consent": True,
    "require_consent_for_counterparty_assignment": False,
}


def case(
    id: str,
    tags: List[str],
    text: str,
    expected_state: str,
    expected_exceptions: Any = "SKIP",
    policy_overrides: Optional[Dict[str, Any]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "expected_state": expected_state,
        "expected_exceptions": expected_exceptions,
        "policy_overrides": policy_overrides or {},
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

CASES += [
    case("clean-01", ["clean_mutual"],
         "16. Assignment. Neither party may assign this Agreement without the prior written "
         "consent of the other party, not to be unreasonably withheld, except that either "
         "party may assign this Agreement to an affiliate or in connection with a merger, "
         "acquisition, or change of control.",
         "ACCEPT",
         {"affiliate": True, "change_of_control": True, "merger_acquisition": True}),
    case("clean-02", ["unilateral"],
         "16. Assignment. Vendor may not assign this Agreement without the prior written "
         "consent of Customer, not to be unreasonably withheld.",
         "ACCEPT"),
    case("clean-03", ["unrestricted"],
         "16. Assignment. Either party may assign this Agreement without prior consent.",
         "ACCEPT", notes="Default policy does not require consent to be required."),
]

CASES += [
    case("consent-01", ["consent_standard"],
         "16. Assignment. Vendor may not assign this Agreement without the prior written "
         "consent of Customer, which consent may be withheld in its sole discretion.",
         "NEGOTIATE", notes="Sole-discretion consent standard prohibited by default policy."),
    case("consent-02", ["consent_standard"],
         "16. Assignment. Vendor may not assign this Agreement without the prior written "
         "consent of Customer, which consent may be withheld in its sole discretion.",
         "ACCEPT", policy_overrides={"prohibit_sole_discretion_consent": False}),
]

CASES += [
    case("exceptions-01", ["exceptions"],
         "16. Assignment. Vendor may not assign this Agreement without the prior written "
         "consent of Customer, except that Vendor may assign this Agreement to an affiliate "
         "or in connection with a merger or acquisition.",
         "ACCEPT",
         {"affiliate": True, "merger_acquisition": True},
         policy_overrides={"required_exceptions_json": ["affiliate", "merger_acquisition"]}),
    case("exceptions-02", ["exceptions"],
         "16. Assignment. Vendor may not assign this Agreement without the prior written "
         "consent of Customer.",
         "NEGOTIATE",
         policy_overrides={"required_exceptions_json": ["affiliate", "merger_acquisition"]},
         notes="Required standing exceptions entirely absent from our own restriction."),
]

CASES += [
    case("unilateral-01", ["unilateral", "buy_side"],
         "16. Assignment. Customer may not assign this Agreement without the prior written "
         "consent of Vendor.",
         "ACCEPT", policy_overrides={"contract_side": "buy_side"},
         notes="We are Customer; this is our own restriction, clean otherwise."),
    case("unilateral-02", ["unilateral", "mutuality_gap"],
         "16. Assignment. Vendor may not assign this Agreement without the prior written "
         "consent of Customer.",
         "NEGOTIATE", policy_overrides={"require_consent_for_counterparty_assignment": True},
         notes="Only Vendor (us) is restricted; Customer faces no reciprocal restriction, "
               "and the policy requires mutuality here."),
]

CASES += [
    case("symmetry-01", ["reciprocal_symmetry"],
         "16. Assignment. Neither party may assign this Agreement without the prior written "
         "consent of the other party, not to be unreasonably withheld.",
         "ACCEPT", notes="Genuinely mutual, no per-party attribution — baseline."),
    case("symmetry-02", ["reciprocal_symmetry", "adversarial"],
         "16. Assignment. Neither party may assign this Agreement without the prior written "
         "consent of the other party; provided, that Vendor's assignment rights under this "
         "Section require consent not to be unreasonably withheld, and Customer's assignment "
         "rights under this Section require consent in its sole discretion.",
         "REQUIRES_REVIEW",
         notes="Opens with 'neither party' (claiming symmetry) but a differentiated proviso "
               "states different consent standards per named party."),
    case("symmetry-03", ["reciprocal_symmetry"],
         "16. Assignment. Neither party may assign this Agreement without the prior written "
         "consent of the other party; Vendor's assignment rights under this Section require "
         "consent not to be unreasonably withheld, and Customer's assignment rights under "
         "this Section require consent not to be unreasonably withheld.",
         "ACCEPT", notes="Both named parties' terms genuinely agree — must not be flagged."),
]

CASES += [
    case("undefined-01", ["undefined_parties"],
         "16. Assignment. Acme may not assign this Agreement without the prior written "
         "consent of Globex.",
         "REQUIRES_REVIEW", notes="Neither 'Acme' nor 'Globex' is a recognized role word."),
    case("mutual-policy-01", ["mutual_policy"],
         "16. Assignment. Vendor may not assign this Agreement without the prior written "
         "consent of Customer.",
         "REQUIRES_REVIEW", policy_overrides={"contract_side": "mutual"},
         notes="Recognized roles, but policy is configured mutual while the contract is "
               "directional."),
]

CASES += [
    case("malformed-01", ["malformed"],
         "16. Assinment. Vendr may nt assgn ths Agreemnt wthout the prir consnt of Custmer.",
         "NOT_APPLICABLE",
         notes="Checked directly: no 'assign' substring appears anywhere in this text "
               "('Assinment' drops the 'g', 'assgn' drops the 'i') — the anchor itself never "
               "fires, so this is honestly NOT_APPLICABLE (no clause found), the same "
               "anchor-breaking-typo precedent used in the other three corpora's malformed-01 "
               "cases, not REQUIRES_REVIEW (which is for an anchor that fires but nothing "
               "parseable follows)."),
    case("malformed-02", ["malformed"],
         "16.  Assignment.    Neither   party   may   assign   this   Agreement   without   "
         "the   prior   written   consent   of   the   other   party,   not   to   be   "
         "unreasonably   withheld.",
         "ACCEPT", notes="Excess whitespace only, words spelled correctly."),
    case("malformed-03", ["malformed"],
         "16. Assignment. [***] may not assign this Agreement without the prior written "
         "consent of [***].",
         "REQUIRES_REVIEW", notes="Redacted party names — must not fabricate roles."),
]

CASES += [
    case("absent-01", ["absent"],
         "9. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware.",
         "NOT_APPLICABLE"),
    case("absent-02", ["absent"],
         "9. Governing Law. This Agreement is governed by Delaware law. No assignment of "
         "this Agreement is permitted under any circumstances.",
         "NOT_APPLICABLE"),
]
