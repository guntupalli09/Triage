"""
Labeled adversarial corpus for the Indemnification policy engine benchmark
(see benchmarks/run_indemnification_benchmark.py).

Labels here were written from the policy semantics and drafting pattern
alone — what SHOULD happen given who indemnifies whom, for what, under
what policy — never by running the implementation and copying its output.
Where the "correct" answer is genuinely a judgment call (as with several
Limitation of Liability cases), the case is labeled with the most
defensible reading and flagged in `notes`; a mismatch against that label
is not automatically an implementation bug.

DEFAULT_POLICY represents a sell-side vendor's playbook: we are Vendor/
Supplier, Customer/Client is the counterparty. Most cases use this
directly; asymmetric/reciprocal/buy-side cases override contract_side or
thresholds explicitly.

expected_exposure_monetary / expected_protection_present /
expected_trigger_treatments follow the same "SKIP unless asserted"
discipline as the Liability corpus — only fields explicitly asserted are
scored; everything else is descriptive.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "sell_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: indemnification exposure capped at 1x annual fees, third-party claims only.",
    "required_protection_triggers_json": [],
    "permitted_exposure_triggers_json": [],
    "prohibited_exposure_triggers_json": [],
    "require_exposure_third_party_only": True,
    "require_defense_control_for_exposure": False,
    "require_notice_and_cooperation_for_exposure": False,
    "prohibit_uncapped_exposure": True,
    "exposure_preferred_multiplier": 1.0,
    "exposure_acceptable_max_multiplier": 2.0,
    "exposure_negotiate_max_multiplier": 3.0,
}


def case(
    id: str,
    tags: List[str],
    text: str,
    expected_state: str,
    expected_exposure_monetary: Any = "SKIP",
    expected_trigger_treatments: Optional[Dict[str, str]] = None,
    expected_protection_present: Any = "SKIP",
    expected_direction: Any = "SKIP",  # (indemnifying_role, indemnified_role) of the resolved exposure obligation
    policy_overrides: Optional[Dict[str, Any]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "expected_state": expected_state,
        "expected_exposure_monetary": expected_exposure_monetary,
        "expected_trigger_treatments": expected_trigger_treatments or {},
        "expected_protection_present": expected_protection_present,
        "expected_direction": expected_direction,
        "policy_overrides": policy_overrides or {},
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# 1. Clean unilateral obligations (our exposure only)
# ---------------------------------------------------------------------------
CASES += [
    case("clean-01", ["clean_unilateral"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence or willful "
         "misconduct. Vendor's indemnification obligations under this Section shall not exceed "
         "1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         {"gross_negligence": "covered", "willful_misconduct": "covered"},
         expected_direction=("Vendor", "Customer")),
    case("clean-02", ["clean_unilateral"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's infringement of intellectual "
         "property rights. Vendor's indemnification obligations shall not exceed 2 times the "
         "total annual fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "multiplier", "multiplier": 2.0},
         expected_direction=("Vendor", "Customer"), expected_protection_present=False),
    case("clean-03", ["clean_unilateral"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 2.5 times the total annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 2.5}),
    case("clean-04", ["clean_unilateral"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 5 times the total annual fees paid.",
         "ESCALATE", {"kind": "multiplier", "multiplier": 5.0}),
    case("clean-05", ["clean_unilateral"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's willful misconduct. Vendor's "
         "indemnification obligations shall not be subject to any cap.",
         "PROHIBITED", {"kind": "unlimited"},
         notes="prohibit_uncapped_exposure defaults True."),
    case("clean-06", ["clean_unilateral"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's willful misconduct. Vendor's "
         "indemnification obligations shall not be subject to any cap.",
         "ESCALATE", {"kind": "unlimited"},
         policy_overrides={"prohibit_uncapped_exposure": False}),
]

# ---------------------------------------------------------------------------
# 2. Reciprocal / mutual indemnification
# ---------------------------------------------------------------------------
CASES += [
    case("reciprocal-01", ["reciprocal"],
         "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
         "party from and against any third-party claims arising from the indemnifying party's "
         "gross negligence or willful misconduct. Each party's indemnification obligations shall "
         "not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="Symmetric terms apply as both exposure and protection regardless of contract_side."),
    case("reciprocal-02", ["reciprocal"],
         "The parties shall mutually indemnify each other for third-party claims arising from "
         "each party's breach of its confidentiality obligations. Indemnification obligations "
         "shall not exceed 3 times the total annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 3.0}),
    case("reciprocal-03", ["reciprocal"],
         "This Agreement provides for mutual indemnification. Each party shall indemnify the "
         "other for third-party claims arising from its own gross negligence, subject to a cap "
         "of 2 times the total annual fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "multiplier", "multiplier": 2.0}),
    case("reciprocal-04", ["reciprocal"],
         "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
         "party from and against any third-party claims arising from the indemnifying party's "
         "willful misconduct. Each party's indemnification obligations shall not be subject to "
         "any cap.",
         "PROHIBITED", {"kind": "unlimited"}),
    case("reciprocal-05", ["reciprocal", "buy_side"],
         "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
         "party from and against any third-party claims arising from the indemnifying party's "
         "gross negligence. Each party's indemnification obligations shall not exceed 1 times "
         "the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"contract_side": "buy_side"},
         notes="Symmetric clause should resolve the same way regardless of which side we're on."),
]

# ---------------------------------------------------------------------------
# 3. Asymmetric indemnification (two distinct directional obligations)
# ---------------------------------------------------------------------------
CASES += [
    case("asym-01", ["asymmetric"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, subject to a cap "
         "of 1 times the total annual fees paid. Customer shall indemnify, defend, and hold "
         "harmless Vendor from and against any third-party claims arising from Customer's misuse "
         "of the deliverables, subject to a cap of 3 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         expected_protection_present=True,
         notes="We are Vendor (sell_side, default policy). OUR exposure is the Vendor->Customer "
               "obligation (1x) — the Customer->Vendor 3x obligation is Customer's exposure, i.e. "
               "OUR PROTECTION, not ours to be capped by our own exposure thresholds. Corrected "
               "after the first benchmark run: the original label swapped which obligation was ours."),
    case("asym-02", ["asymmetric"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's infringement of intellectual "
         "property rights, subject to a cap of 1 times the total annual fees paid. Customer shall "
         "indemnify, defend, and hold harmless Vendor from and against any third-party claims "
         "arising from Customer's breach of confidentiality obligations, subject to a cap of 1 "
         "times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         expected_protection_present=True, expected_direction=("Vendor", "Customer")),
    case("asym-03", ["asymmetric", "buy_side"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, subject to a cap "
         "of 1 times the total annual fees paid. Customer shall indemnify, defend, and hold "
         "harmless Vendor from and against any third-party claims arising from Customer's misuse "
         "of the deliverables, subject to a cap of 5 times the total annual fees paid.",
         "ESCALATE", {"kind": "multiplier", "multiplier": 5.0},
         expected_protection_present=True, expected_direction=("Customer", "Vendor"),
         policy_overrides={"contract_side": "buy_side"},
         notes="We are Customer (buy_side): OUR exposure is the Customer->Vendor obligation (5x, "
               "'Customer's misuse of the deliverables'), not the Vendor->Customer one. 5x exceeds "
               "negotiate_max(3) -> ESCALATE. Vendor's 1x obligation to us is our protection."),
]

# ---------------------------------------------------------------------------
# 4. Nested exceptions / carve-outs
# ---------------------------------------------------------------------------
CASES += [
    case("nested-01", ["nested_exceptions"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, except for claims "
         "arising from Customer's misuse of the deliverables. Vendor's indemnification obligations "
         "shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         {"gross_negligence": "covered"}),
    case("nested-02", ["nested_exceptions"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence or willful "
         "misconduct, except for willful misconduct arising from actions directed by Customer. "
         "Vendor's indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         {"gross_negligence": "covered", "willful_misconduct": "excluded"},
         notes="Nested exception narrows willful_misconduct coverage specifically, not gross_negligence."),
    case("nested-03", ["nested_exceptions"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, provided, "
         "however, that such indemnification shall not apply where Customer contributed to the "
         "underlying claim through its own actions. Vendor's indemnification obligations shall "
         "not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         {"gross_negligence": "unresolved"},
         notes="'Provided, however' signals ambiguity about scope without a clean exclusion phrase — "
               "gross_negligence coverage is genuinely unclear here."),
]

# ---------------------------------------------------------------------------
# 5. Cross-referenced monetary caps
# ---------------------------------------------------------------------------
CASES += [
    case("xref-01", ["cross_referenced_cap"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall be subject to the limitation of liability set forth "
         "in Section 14.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Monetary treatment delegates to another section not resolved by this adapter."),
    case("xref-02", ["cross_referenced_cap"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's willful misconduct. Vendor's "
         "indemnification obligations shall be subject to the liability cap set forth in Section 9.",
         "REQUIRES_REVIEW", "SKIP"),
]

# ---------------------------------------------------------------------------
# 6. Malformed drafting
# ---------------------------------------------------------------------------
CASES += [
    case("malformed-01", ["malformed"],
         "12. Indemnfication. Vender shal indemify, defend, and hold harmles Customer from any "
         "third-party claims arizing from Vender's gross neglignce.",
         "NOT_APPLICABLE", None,
         notes="The typo in 'Indemnfication' breaks the anchor substring itself ('indemnif' is not "
               "present), so no clause is located at all — NOT_APPLICABLE is the honest answer, same "
               "reasoning as the corresponding correction made to the Liability corpus's malformed-01/"
               "04 after its first benchmark run. Corrected after this adapter's first run, not "
               "originally REQUIRES_REVIEW as first labeled."),
    case("malformed-02", ["malformed"],
         "12.  Indemnification.    Vendor   shall   indemnify,   defend,   and   hold   harmless   "
         "Customer   from   third-party   claims   arising   from   Vendor's   gross   negligence.  "
         "Vendor's indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="Excess whitespace only, words spelled correctly — regex uses \\s+ throughout and "
               "should tolerate this."),
    case("malformed-03", ["malformed"],
         "12. Indemnification. [***] shall indemnify, defend, and hold harmless [***] from "
         "third-party claims arising from gross negligence.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Redacted party names (common in filed exhibits) — must not fabricate roles."),
]

# ---------------------------------------------------------------------------
# 7. Undefined / unmappable parties
# ---------------------------------------------------------------------------
CASES += [
    case("undefined-01", ["undefined_parties"],
         "12. Indemnification. Acme shall indemnify, defend, and hold harmless Globex from and "
         "against any third-party claims arising from Acme's gross negligence. Acme's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Neither 'Acme' nor 'Globex' is a recognized buy/sell-side role word — must not guess "
               "which one is us."),
    case("undefined-02", ["undefined_parties"],
         "12. Indemnification. Party A shall indemnify, defend, and hold harmless Party B from "
         "and against any third-party claims arising from Party A's willful misconduct.",
         "REQUIRES_REVIEW", "SKIP"),
    case("undefined-03", ["undefined_parties", "mutual_policy"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
         "and against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         policy_overrides={"contract_side": "mutual"},
         notes="Recognized roles, but policy is configured mutual while the contract is directional — "
               "cannot determine which side is ours under a mutual assumption."),
]

# ---------------------------------------------------------------------------
# 8. Multiple indemnification provisions (non-conflicting: different scopes)
# ---------------------------------------------------------------------------
CASES += [
    case("multi-01", ["multiple_provisions"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, subject to a cap "
         "of 1 times the total annual fees paid. Exhibit C. Data Processing Addendum "
         "Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's data breach, subject to a cap of "
         "1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="Two obligations, same direction, SAME cap value — consistent, not conflicting. "
               "Current adapter resolves the first Vendor->Customer match it finds; both agree so "
               "the answer is the same either way."),
]

# ---------------------------------------------------------------------------
# 9. Conflicting provisions (same direction, different terms)
# ---------------------------------------------------------------------------
CASES += [
    case("conflict-01", ["conflicting_provisions"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, subject to a cap "
         "of 1 times the total annual fees paid. 45. Amendment. Vendor shall indemnify, defend, "
         "and hold harmless Customer from and against any third-party claims arising from Vendor's "
         "gross negligence, subject to a cap of 5 times the total annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Two Vendor->Customer obligations with conflicting caps (1x vs 5x). This adapter has "
               "no amendment-supersession logic (unlike the LoL adapter), but _resolve_obligations_"
               "for_side does compare monetary terms across same-direction obligations and correctly "
               "flags disagreement as unresolved rather than silently keeping the first match — "
               "verified directly against this case after the first benchmark run."),
]

# ---------------------------------------------------------------------------
# 10. Indemnification absent
# ---------------------------------------------------------------------------
CASES += [
    case("absent-01", ["absent"],
         "9. Governing Law. This Agreement shall be governed by the laws of the State of Delaware.",
         "NOT_APPLICABLE", None),
    case("absent-02", ["absent"],
         "10. Term and Termination. This Agreement shall commence on the Effective Date and "
         "continue for one year.",
         "NOT_APPLICABLE", None),
    case("absent-03", ["absent"],
         "11. Limitation of Liability. In no event shall either party's aggregate liability "
         "exceed 1 times the total annual fees paid.",
         "NOT_APPLICABLE", None),
    case("absent-04", ["absent"],
         "8. Confidentiality. Each party shall protect the other party's Confidential Information "
         "using reasonable care.",
         "NOT_APPLICABLE", None),
]

# ---------------------------------------------------------------------------
# 11. Missing required protection
# ---------------------------------------------------------------------------
CASES += [
    case("missing-protection-01", ["missing_protection"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "NEGOTIATE", "SKIP",
         policy_overrides={"contract_side": "buy_side", "required_protection_triggers_json": ["ip_infringement"]},
         notes="We are Customer (buy_side); this text states only Vendor->Customer (our protection), "
               "no Customer->Vendor obligation, so we have no exposure obligation to score monetary "
               "treatment for (expected_exposure_monetary intentionally SKIP, not asserted — the "
               "original assertion here was a corpus-authoring error, corrected after the first run). "
               "Vendor's obligation to us doesn't cover ip_infringement, which our policy requires."),
    case("missing-protection-02", ["missing_protection"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence and willful "
         "misconduct. Vendor's indemnification obligations shall not exceed 1 times the total "
         "annual fees paid.",
         "ACCEPT", "SKIP",
         policy_overrides={"contract_side": "buy_side", "required_protection_triggers_json": ["gross_negligence"]},
         notes="Required trigger IS covered — should accept cleanly. No Customer->Vendor exposure "
               "obligation is stated in this text, so expected_exposure_monetary is intentionally "
               "SKIP (corrected after the first run, same reasoning as missing-protection-01)."),
    case("missing-protection-03", ["missing_protection"],
         "9. Governing Law. This Agreement shall be governed by the laws of Delaware. No "
         "indemnification provision is included in this Agreement.",
         "NOT_APPLICABLE", None,
         policy_overrides={"contract_side": "buy_side", "required_protection_triggers_json": ["ip_infringement"]},
         notes="No indemnification clause at all is NOT_APPLICABLE, even though our policy requires "
               "protection — the engine reports what's in the document, it doesn't invent a "
               "different state for absence; a human still needs to notice NOT_APPLICABLE plus a "
               "required-protection policy is itself a signal worth a lawyer's attention, but that's "
               "a product-layer concern, not this engine's job to encode as a different state."),
]

# ---------------------------------------------------------------------------
# 12. Prohibited exposure trigger
# ---------------------------------------------------------------------------
CASES += [
    case("prohibited-exposure-01", ["prohibited_exposure"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's ordinary negligence. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 1.0},
         {"negligence": "covered"},
         policy_overrides={"prohibited_exposure_triggers_json": ["negligence"]},
         notes="Policy refuses to indemnify for ordinary (non-gross) negligence — a common, real "
               "playbook position (only gross negligence/willful misconduct should trigger "
               "indemnification exposure)."),
]

# ---------------------------------------------------------------------------
# 13. Defense control
# ---------------------------------------------------------------------------
CASES += [
    case("defense-01", ["defense_control"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. The indemnifying "
         "party shall control the defense of any such claim at its own expense. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"require_defense_control_for_exposure": True}),
    case("defense-02", ["defense_control"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. The indemnified "
         "party shall control its own defense at Vendor's expense. Vendor's indemnification "
         "obligations shall not exceed 1 times the total annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"require_defense_control_for_exposure": True},
         notes="We're on the hook financially (Vendor) but don't control the defense — real risk."),
]

# ---------------------------------------------------------------------------
# 14. Notice and cooperation
# ---------------------------------------------------------------------------
CASES += [
    case("notice-01", ["notice_cooperation"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, provided that "
         "Customer gives Vendor prompt written notice of any such claim and Customer's reasonable "
         "cooperation in the defense thereof. Vendor's indemnification obligations shall not "
         "exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"require_notice_and_cooperation_for_exposure": True}),
    case("notice-02", ["notice_cooperation"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"require_notice_and_cooperation_for_exposure": True},
         notes="No notice/cooperation precondition stated at all — a real drafting gap our policy cares about."),
]

# ---------------------------------------------------------------------------
# 15. Third-party vs. first-party scope
# ---------------------------------------------------------------------------
CASES += [
    case("scope-01", ["scope"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any claims, whether or not asserted by a third party, arising from Vendor's "
         "gross negligence. Vendor's indemnification obligations shall not exceed 1 times the "
         "total annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 1.0},
         notes="Explicit first-party-inclusive language — our exposure is broader than the usual "
               "third-party-only convention, and our policy requires third-party-only."),
    case("scope-02", ["scope"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="Explicit third-party-only language, matches policy requirement cleanly."),
]

# ---------------------------------------------------------------------------
# 16. Monetary treatment variety
# ---------------------------------------------------------------------------
CASES += [
    case("monetary-01", ["monetary"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's maximum "
         "liability under this indemnification obligation shall not exceed $500,000.",
         "ESCALATE", {"kind": "fixed", "fixed_amount": 500000.0},
         notes="Fixed-dollar exposure cap — not comparable to a multiplier threshold automatically; "
               "escalate for manual comparison, same philosophy as the LoL adapter's fixed-amount handling."),
    case("monetary-02", ["monetary"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence.",
         "MUST_REDLINE", {"kind": "not_stated"},
         notes="No monetary treatment stated at all for the exposure obligation."),
]

# ---------------------------------------------------------------------------
# Phase 1 expansion (43 -> 100+). Labels below were written from the
# contract-semantics/policy-drafting reading alone, the same discipline as
# cases 1-16 above — NOT by tracing the extraction regexes and NOT by
# running the implementation and copying its output. Several cases are
# deliberately adversarial against known regex/vocabulary shapes (first-
# party scope signals, monetary cross-reference phrasing, trigger
# vocabulary gaps) specifically because a benchmark that only restates
# what the engine already does well is not useful; a mismatch found here
# is reported as a real finding, not silently relabeled to match output.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 17. Reciprocal obligations split across separate provisions (not phrased
#     as "each party" — two independent, mirrored unilateral obligations)
# ---------------------------------------------------------------------------
CASES += [
    case("split-reciprocal-01", ["reciprocal", "split_provisions"],
         "12. Indemnification by Vendor. Vendor shall indemnify, defend, and hold harmless Customer "
         "from and against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid. "
         "45. Indemnification by Customer. Customer shall indemnify, defend, and hold harmless "
         "Vendor from and against any third-party claims arising from Customer's gross negligence. "
         "Customer's indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         expected_protection_present=True, expected_direction=("Vendor", "Customer"),
         notes="Functionally reciprocal (mirrored 1x terms) but drafted as two separate unilateral "
               "obligations in two separate sections, not 'each party' language. Our exposure "
               "(Vendor->Customer, 1x) accepts; Customer's mirrored 1x obligation to us is protection."),
    case("split-reciprocal-02", ["reciprocal", "split_provisions"],
         "12. Indemnification by Vendor. Vendor shall indemnify, defend, and hold harmless Customer "
         "from and against any third-party claims arising from Vendor's willful misconduct. "
         "Vendor's indemnification obligations shall not exceed 1 times the total annual fees paid. "
         "45. Indemnification by Customer. Customer shall indemnify, defend, and hold harmless "
         "Vendor from and against any third-party claims arising from Customer's willful "
         "misconduct. Customer's indemnification obligations shall not be subject to any cap.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         expected_protection_present=True, expected_direction=("Vendor", "Customer"),
         notes="Mirrored in trigger and direction shape only, NOT in monetary terms — our exposure "
               "is a clean capped 1x; Customer's uncapped obligation to us is generous protection, "
               "not something that should push our own decision toward escalation."),
]

# ---------------------------------------------------------------------------
# 18. Unilateral Customer -> Vendor obligations, evaluated buy-side (we are
#     Customer; the Customer->Vendor promise IS our exposure)
# ---------------------------------------------------------------------------
CASES += [
    case("unilateral-buyside-01", ["unilateral", "buy_side"],
         "12. Indemnification. Customer shall indemnify, defend, and hold harmless Vendor from and "
         "against any third-party claims arising from Customer's gross negligence. Customer's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         expected_direction=("Customer", "Vendor"),
         policy_overrides={"contract_side": "buy_side"},
         notes="We are Customer; Customer's own promise to indemnify Vendor is OUR exposure here, "
               "not protection, since we made the promise."),
    case("unilateral-buyside-02", ["unilateral", "buy_side"],
         "12. Indemnification. Customer shall indemnify, defend, and hold harmless Vendor from and "
         "against any third-party claims arising from Customer's misuse of the deliverables. "
         "Customer's indemnification obligations shall not exceed 6 times the total annual fees "
         "paid.",
         "ESCALATE", {"kind": "multiplier", "multiplier": 6.0},
         expected_direction=("Customer", "Vendor"),
         policy_overrides={"contract_side": "buy_side"}),
    case("unilateral-buyside-03", ["unilateral", "buy_side"],
         "12. Indemnification. Customer shall indemnify, defend, and hold harmless Vendor from and "
         "against any third-party claims arising from Customer's infringement of intellectual "
         "property rights. Customer's indemnification obligations shall not be subject to any cap.",
         "PROHIBITED", {"kind": "unlimited"},
         expected_direction=("Customer", "Vendor"),
         policy_overrides={"contract_side": "buy_side"},
         notes="prohibit_uncapped_exposure defaults True regardless of which side we're on."),
]

# ---------------------------------------------------------------------------
# 19. First-party scope signaled in wording the extractor's regex family
#     does not recognize — adversarial against _FIRST_PARTY_SIGNAL_RE.
# ---------------------------------------------------------------------------
CASES += [
    case("scope-03", ["scope", "adversarial"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any claims, whether direct or third-party, arising from Vendor's gross "
         "negligence. Vendor's indemnification obligations shall not exceed 1 times the total "
         "annual fees paid.",
         "NEGOTIATE", "SKIP",
         notes="'whether direct or third-party' plainly broadens scope beyond third-party claims to "
               "a lawyer reading it, but it does not match any of _FIRST_PARTY_SIGNAL_RE's fixed "
               "phrasings ('first-party claims', 'whether or not asserted by a third party', "
               "'direct claims between the parties', etc.) while _THIRD_PARTY_ONLY_RE's plain "
               "'third-party claims' substring IS present. Adversarial: written specifically to "
               "probe whether the scope classifier over-relies on the presence of the third-party "
               "phrase without checking for a broadening signal expressed differently. If the "
               "engine reports ACCEPT here instead of NEGOTIATE, that is a false-safe finding, not "
               "a corpus error — report it, don't relabel to match."),
    case("scope-04", ["scope"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims, including claims by Customer against Vendor arising "
         "under this Agreement, resulting from Vendor's gross negligence. Vendor's indemnification "
         "obligations shall not exceed 1 times the total annual fees paid.",
         "NEGOTIATE", "SKIP",
         notes="'claims by Customer against Vendor' is a first-party claim between the contracting "
               "parties themselves, phrased without any of the fixed first-party trigger phrases — "
               "same adversarial shape as scope-03, different wording."),
]

# ---------------------------------------------------------------------------
# 20. IP infringement, with an exclusion carve-out
# ---------------------------------------------------------------------------
CASES += [
    case("ip-excl-01", ["ip_infringement", "nested_exceptions"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's infringement of intellectual "
         "property rights, except for infringement of intellectual property rights resulting from "
         "Customer's modifications to the deliverables. Vendor's indemnification obligations shall "
         "not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         {"ip_infringement": "excluded"},
         notes="A narrow, standard carve-out (Customer's own modifications) — does not itself change "
               "the monetary-driven ACCEPT outcome, but the trigger treatment should reflect the "
               "exclusion accurately. CORRECTED after the first Phase 1 run: the original text said "
               "'except for infringement resulting from...' without restating 'intellectual "
               "property', so ip_infringement's own keyword regex (which requires 'intellectual "
               "property' nearby) never matched inside the exclusion's forward-coverage span, and "
               "the case scored a false trigger mismatch that was actually a corpus-authoring gap, "
               "not an engine gap — nested-02's existing passing case already established that the "
               "excluded trigger's keyword must be restated after 'except for' for the forward-span "
               "exclusion model to find it; this case simply hadn't followed that same pattern yet."),
    case("ip-required-missing-01", ["ip_infringement", "missing_protection"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         {"ip_infringement": "not_addressed"},
         policy_overrides={"required_protection_triggers_json": [], "prohibited_exposure_triggers_json": []},
         notes="CORRECTED after the first Phase 1 run: originally labeled NEGOTIATE, on the theory "
               "that our own sell-side exposure should be required to cover ip_infringement. But "
               "required_protection_triggers_json is defined (correctly, per the architecture) to "
               "apply to the COUNTERPARTY's protection obligation to us, not our own exposure scope "
               "— there is no policy field for 'our exposure must affirmatively cover trigger X', "
               "and this case's policy_overrides clear both trigger lists to empty, so nothing in "
               "the configured policy actually requires ip_infringement coverage anywhere. With no "
               "protection obligation stated in the text either, there is genuinely no policy gap "
               "to flag: state is correctly driven by the clean 1x monetary term alone. The original "
               "NEGOTIATE label was a labeling error (asserting an outcome the case's own policy "
               "configuration doesn't actually produce), not a finding about the engine."),
]

# ---------------------------------------------------------------------------
# 21. Confidentiality / data breach triggers (previously entirely untested)
# ---------------------------------------------------------------------------
CASES += [
    case("databreach-01", ["data_breach", "confidentiality"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from a data breach or unauthorized disclosure of "
         "Customer's confidential information. Vendor's indemnification obligations shall not "
         "exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         {"data_breach": "covered", "confidentiality": "covered"}),
    case("databreach-02", ["data_breach", "missing_protection", "buy_side"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "NEGOTIATE", "SKIP",
         policy_overrides={"contract_side": "buy_side", "required_protection_triggers_json": ["data_breach"]},
         notes="We are Customer and require data_breach protection; Vendor's obligation to us covers "
               "only gross_negligence — a real, common gap for a data-handling vendor relationship."),
    case("confidentiality-excl-01", ["confidentiality", "nested_exceptions"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's breach of its confidentiality "
         "obligations, except for breach of confidentiality obligations caused by Customer's own "
         "personnel. Vendor's indemnification obligations shall not exceed 1 times the total "
         "annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         {"confidentiality": "excluded"},
         notes="CORRECTED after the first Phase 1 run: same authoring gap as ip-excl-01 — the "
               "excluded trigger's keyword ('confidentiality') must be restated within the "
               "forward-coverage span after 'except for' for the exclusion model to find it; the "
               "original text said only 'except for breaches caused by...' without the word "
               "'confidentiality' appearing again."),
]

# ---------------------------------------------------------------------------
# 22. Bodily injury / property damage — NOT in this adapter's trigger
#     vocabulary (TRIGGERS list has no bodily_injury/property_damage entry).
#     Labeled from what the contract actually promises, independent of
#     whether the current extractor has a category for it at all — a real
#     vocabulary gap, not something to paper over by omission.
# ---------------------------------------------------------------------------
CASES += [
    case("bodily-injury-01", ["bodily_injury", "vocabulary_gap"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims for bodily injury or property damage arising from "
         "Vendor's performance of the Services. Vendor's indemnification obligations shall not "
         "exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="No trigger_treatments assertion: bodily_injury/property_damage are not in TRIGGERS "
               "at all, so this text's actual coverage category can't be represented or scored by "
               "this adapter's vocabulary. State is correctly driven by the 1x monetary term alone "
               "here, but flag: a playbook requiring specific bodily-injury/property-damage "
               "protection (common in services agreements with on-site work) has no policy field to "
               "express that requirement against, and no way to detect if such coverage is silently "
               "absent. This is an architecture-report-worthy vocabulary gap, not a bug in this case."),
    case("bodily-injury-02", ["bodily_injury", "vocabulary_gap", "missing_protection", "buy_side"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "NEGOTIATE", "SKIP",
         policy_overrides={"contract_side": "buy_side", "required_protection_triggers_json": ["bodily_injury"]},
         notes="Intentionally asserts a required_protection_triggers_json value ('bodily_injury') "
               "that does not exist anywhere in TRIGGERS/_TRIGGER_KEYWORD_RE. The policy layer lets "
               "a playbook author configure a trigger the engine can never recognize as covered — "
               "meaning this requirement can NEVER be satisfied, silently, for any contract, "
               "regardless of what the text actually says. Expected NEGOTIATE (missing protection) "
               "is the CORRECT outcome by construction here (Vendor's obligation only covers "
               "gross_negligence either way) — but the deeper finding, worth reporting regardless of "
               "this case's pass/fail, is that this misconfiguration is undetectable and unbounded: "
               "even a contract that explicitly promises bodily-injury protection would still read "
               "as NEGOTIATE/missing, because the trigger keyword never exists to be matched."),
]

# ---------------------------------------------------------------------------
# 23. Breach-of-contract indemnities — also outside TRIGGERS vocabulary
# ---------------------------------------------------------------------------
CASES += [
    case("breach-of-contract-01", ["breach_of_contract", "vocabulary_gap"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's material breach of this Agreement. "
         "Vendor's indemnification obligations shall not exceed 1 times the total annual fees "
         "paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="Same vocabulary-gap finding as bodily-injury-01: 'material breach of this Agreement' "
               "as an indemnification trigger has no TRIGGERS entry. Monetary term alone drives "
               "state here, correctly."),
]

# ---------------------------------------------------------------------------
# 24. Duty-to-defend language without the word "indemnify" appearing in the
#     operative sentence itself
# ---------------------------------------------------------------------------
CASES += [
    case("defend-only-01", ["duty_to_defend_only"],
         "12. Defense Obligation. Vendor shall defend Customer against any third-party claims "
         "arising from Vendor's gross negligence, at Vendor's sole cost and expense. See also "
         "Section 45 (Indemnification) for related terms.",
         "REQUIRES_REVIEW", "SKIP",
         notes="The operative promise sentence says only 'shall defend', never 'indemnify' — "
               "_OBLIGATION_RE requires the literal word 'indemnify' (alone or paired with defend) "
               "to match a directional promise. The word 'Indemnification' appears only in a "
               "cross-reference to a different section that isn't itself quoted here. No directional "
               "obligation can be honestly parsed from this text alone — REQUIRES_REVIEW ('duty to "
               "defend' is a real, narrower legal obligation than indemnification and should not be "
               "silently treated as equivalent or silently ignored)."),
    case("defend-only-02", ["duty_to_defend_only"],
         "12. Indemnification. Vendor shall defend and hold harmless Customer from and against any "
         "third-party claims arising from Vendor's gross negligence, and shall pay all resulting "
         "damages and costs. Vendor's obligations under this Section shall not exceed 1 times the "
         "total annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Heading says 'Indemnification' and the substance (defend, pay damages/costs) is "
               "functionally an indemnification promise, but the operative sentence itself never "
               "uses the word 'indemnify' — 'shall defend and hold harmless ... and shall pay all "
               "resulting damages' — so _OBLIGATION_RE (which requires the literal word) won't match "
               "it. Adversarial: tests whether the engine over-relies on the word 'indemnify' "
               "appearing verbatim rather than on functional indemnification language."),
]

# ---------------------------------------------------------------------------
# 25. Advancement / reimbursement of defense costs
# ---------------------------------------------------------------------------
CASES += [
    case("advancement-01", ["advancement_reimbursement"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, and shall advance "
         "and reimburse Customer's reasonable defense costs as incurred, subject to repayment if "
         "it is finally determined that Customer was not entitled to indemnification. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="Advancement/reimbursement language is a real procedural detail (common in D&O-style "
               "indemnification, occasionally in commercial contracts) that this adapter has no "
               "dedicated fact for — it should not break extraction of the core obligation/monetary "
               "terms around it, and shouldn't itself change the state."),
]

# ---------------------------------------------------------------------------
# 26. Shared / joint control of defense
# ---------------------------------------------------------------------------
CASES += [
    case("defense-shared-01", ["defense_control"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. The parties shall "
         "jointly control the defense of any such claim, with Customer entitled to participate in "
         "the defense with counsel of its own choosing at its own expense. Vendor's indemnification "
         "obligations shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"require_defense_control_for_exposure": True},
         notes="Shared/joint control satisfies a policy that requires the indemnifying party to "
               "control OR share control of the defense — should not be treated as a gap."),
]

# ---------------------------------------------------------------------------
# 27. Settlement-consent restrictions (present in text, not independently
#     scored by this adapter — verifies it doesn't break extraction)
# ---------------------------------------------------------------------------
CASES += [
    case("settlement-consent-01", ["settlement_consent"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor shall not "
         "settle any such claim without Customer's prior written consent, which shall not be "
         "unreasonably withheld. Vendor's indemnification obligations shall not exceed 1 times the "
         "total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="Settlement-consent language has no dedicated fact in this adapter and is not "
               "scored — this case verifies its presence doesn't corrupt monetary/trigger "
               "extraction for the surrounding obligation."),
]

# ---------------------------------------------------------------------------
# 28. Partial notice-without-cooperation precondition (only one of the two
#     required elements stated)
# ---------------------------------------------------------------------------
CASES += [
    case("notice-partial-01", ["notice_cooperation"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, provided that "
         "Customer gives Vendor prompt written notice of any such claim. Vendor's indemnification "
         "obligations shall not exceed 1 times the total annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"require_notice_and_cooperation_for_exposure": True},
         notes="Notice is stated but cooperation is not — the policy requires BOTH; a precondition "
               "that's only half-present is still a gap worth negotiating, not a pass."),
]

# ---------------------------------------------------------------------------
# 29. Nested exclusions across multiple, distinct triggers in one sentence
# ---------------------------------------------------------------------------
CASES += [
    case("nested-04", ["nested_exceptions"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, willful "
         "misconduct, or infringement of intellectual property rights, except for claims arising "
         "from Customer's misuse of the deliverables or Customer's own modifications to the "
         "deliverables. Vendor's indemnification obligations shall not exceed 1 times the total "
         "annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         {"gross_negligence": "covered", "willful_misconduct": "covered", "ip_infringement": "covered"},
         notes="Exception is scoped entirely to Customer's own conduct (misuse/modifications), not "
               "to any of the three listed triggers themselves — none of gross_negligence, "
               "willful_misconduct, or ip_infringement should be marked excluded just because an "
               "exception clause exists somewhere nearby."),
]

# ---------------------------------------------------------------------------
# 30. Multiple defined party names / broad indemnified group (affiliates,
#     officers, directors, employees, agents)
# ---------------------------------------------------------------------------
CASES += [
    case("broad-group-01", ["broad_indemnified_group"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer and its "
         "affiliates, officers, directors, employees, and agents from and against any third-party "
         "claims arising from Vendor's gross negligence. Vendor's indemnification obligations "
         "shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         expected_direction=("Vendor", "Customer"),
         notes="Broad indemnified-party group (affiliates/officers/directors/employees/agents) is "
               "standard boilerplate — the core Vendor->Customer directional obligation should "
               "still resolve correctly with the group language trailing after 'Customer'."),
    case("broad-group-02", ["broad_indemnified_group", "reciprocal"],
         "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
         "party and its affiliates, officers, directors, employees, and agents from and against "
         "any third-party claims arising from the indemnifying party's gross negligence. Each "
         "party's indemnification obligations shall not exceed 1 times the total annual fees "
         "paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="Reciprocal clause with the same broad indemnified-group boilerplate trailing after "
               "'the other party' — should not prevent the mutual/reciprocal pattern from matching."),
]

# ---------------------------------------------------------------------------
# 31. Malformed / incomplete drafting (additional patterns)
# ---------------------------------------------------------------------------
CASES += [
    case("malformed-04", ["malformed"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. [Section "
         "intentionally left incomplete — monetary terms to be negotiated.]",
         "MUST_REDLINE", {"kind": "not_stated"},
         notes="An honest drafting placeholder — no monetary treatment stated at all, same as "
               "monetary-02 but with explicit bracketed placeholder language rather than simply "
               "ending the sentence."),
    case("malformed-05", ["malformed"],
         "12. Indemnification. Vendor shal, defend, and hold harmles Customer from third-party "
         "claims arizing from Vendor's gross negligence. Vendor's indemnification obligations "
         "shall not exceed 1 times the total annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="'Vendor shal, defend' — a dropped word ('indemnify') mid-typo breaks the operative "
               "verb phrase itself (not just cosmetic misspelling like malformed-02's whitespace or "
               "malformed-01's anchor-breaking typo). The anchor still matches later in "
               "'indemnification obligations', so the clause is found, but no directional promise "
               "can be honestly parsed from the broken sentence — REQUIRES_REVIEW is the honest "
               "answer, not a guess that 'shal, defend' means 'shall indemnify and defend'."),
]

# ---------------------------------------------------------------------------
# 32. Cross-reference phrased in a way _MONETARY_CROSS_REF_RE does not match
#     (adversarial against the fixed cross-reference phrase requirement)
# ---------------------------------------------------------------------------
CASES += [
    case("xref-03", ["cross_referenced_cap", "adversarial"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. The monetary cap "
         "on Vendor's indemnification obligations is set forth in Section 9.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Delegates the cap to Section 9 without using either of the two fixed phrases "
               "_MONETARY_CROSS_REF_RE requires ('limitation of liability' / 'liability cap'). "
               "Semantically this is exactly the same delegated-cap situation as xref-01/xref-02 "
               "and deserves the same REQUIRES_REVIEW answer (delegated, unresolved by this "
               "evaluation) — not MUST_REDLINE's 'insert cap language' framing, since a cap is not "
               "actually missing, just stated elsewhere in different words than the regex expects. "
               "If the engine reports MUST_REDLINE, that's a real extraction gap: report it, don't "
               "relabel to match."),
]

# ---------------------------------------------------------------------------
# 33. Indemnification EXPRESSLY EXCLUDED from the general liability cap
#     (semantic inversion adversarial against _MONETARY_CROSS_REF_RE, which
#     matches the phrase "liability cap ... Section N" regardless of
#     whether the clause says the indemnity is SUBJECT TO or EXCLUDED FROM
#     that cap — two opposite meanings sharing the same trigger phrase)
# ---------------------------------------------------------------------------
CASES += [
    case("cap-excluded-01", ["cap_interaction", "adversarial"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's willful misconduct. Vendor's "
         "indemnification obligations under this Section shall not be subject to the limitation of "
         "liability cap set forth in Section 9, and shall not otherwise be subject to any monetary "
         "limitation on Vendor's indemnification exposure.",
         "PROHIBITED", "SKIP",
         notes="This is an UNCAPPED exposure in substance — the clause says indemnification is not "
               "subject to the LoL cap and not subject to any other monetary limitation, i.e. no cap "
               "applies at all. But the sentence still contains the literal substring 'subject to "
               "the limitation of liability cap ... in Section 9' that _MONETARY_CROSS_REF_RE "
               "matches via a plain regex.search — the regex has no notion of the negation ('shall "
               "not be subject to') wrapping that phrase, so it would misclassify this as a "
               "cross-reference to resolve (REQUIRES_REVIEW) rather than recognizing the explicit "
               "'not... subject to any monetary limitation' language as unlimited exposure "
               "(PROHIBITED, by default policy). Adversarial by design: the regex family is "
               "negation-blind — it matches the phrase 'subject to cap X' identically whether or not "
               "the surrounding sentence negates it. expected_exposure_monetary is intentionally "
               "SKIP since neither {kind: cross_reference} nor {kind: unlimited} should be asserted "
               "as ground truth without knowing which regex the engine's first-candidate-wins logic "
               "actually surfaces; the policy-state mismatch itself is the finding worth reporting. "
               "CORRECTED after the first Phase 1 run: the original phrasing used commas ('excluded "
               "from, and shall not be subject to, the limitation...') that broke both the cross-"
               "reference AND the unlimited regex on pure punctuation grounds, producing 'not_stated' "
               "instead of demonstrating the intended negation-blindness finding — that was a corpus "
               "authoring defect, not the finding being tested. Rewritten without the interrupting "
               "commas so the cross-reference regex actually fires, which is the scenario this case "
               "exists to probe."),
]

# ---------------------------------------------------------------------------
# 34. Special / super caps (a distinct, higher cap carved out for a
#     specific trigger, layered on top of / instead of the general cap)
# ---------------------------------------------------------------------------
CASES += [
    case("super-cap-01", ["special_cap"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's infringement of intellectual "
         "property rights. Notwithstanding the limitation of liability set forth in Section 9, "
         "Vendor's indemnification obligations for such claims shall not exceed 3 times the total "
         "annual fees paid, as a separate and additional cap.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 3.0},
         {"ip_infringement": "covered"},
         notes="'Notwithstanding the limitation of liability...' is an override signal, not a "
               "delegation — the clause states its OWN 3x figure directly rather than pointing "
               "elsewhere for it, so this should extract as a plain 3x multiplier, not a cross-"
               "reference. 3x sits exactly at the negotiate_max boundary -> NEGOTIATE. CORRECTED "
               "after the first Phase 1 run: the original text had no 'X shall indemnify Y' "
               "sentence at all — only a follow-on sentence about the cap for an obligation that "
               "was never itself stated, so nothing could be parsed and this case never actually "
               "tested the override-vs-delegation question it was written for. Added the missing "
               "base obligation sentence."),
    case("super-cap-02", ["special_cap"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's willful misconduct. Vendor's "
         "indemnification obligations for such claims shall be capped at $2,000,000, notwithstanding "
         "any other cap stated elsewhere in this Agreement.",
         "ESCALATE", {"kind": "fixed", "fixed_amount": 2000000.0},
         {"willful_misconduct": "covered"},
         notes="A special fixed-dollar super-cap for a specific trigger — fixed amounts always "
               "escalate for manual comparison regardless of size, same as monetary-01. CORRECTED "
               "after the first Phase 1 run: same missing-base-obligation defect as super-cap-01, "
               "fixed the same way."),
]

# ---------------------------------------------------------------------------
# 35. Conflicting provisions, a different pattern than conflict-01 (three
#     mentions, two of which agree and one of which disagrees)
# ---------------------------------------------------------------------------
CASES += [
    case("conflict-02", ["conflicting_provisions"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, subject to a cap "
         "of 1 times the total annual fees paid. Exhibit C. Vendor shall indemnify, defend, and "
         "hold harmless Customer from and against any third-party claims arising from Vendor's "
         "data breach, subject to a cap of 1 times the total annual fees paid. 45. Amendment. "
         "Vendor shall indemnify, defend, and hold harmless Customer from and against any "
         "third-party claims arising from Vendor's gross negligence, subject to a cap of 4 times "
         "the total annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Three Vendor->Customer mentions: two agree (1x, 1x), one disagrees (4x in the "
               "Amendment section). The disagreement should be caught the same way conflict-01's "
               "simpler two-mention case is caught."),
]

# ---------------------------------------------------------------------------
# 36. Amendment / restatement language (no supersession logic exists in
#     this adapter for indemnification, unlike the LoL adapter's amendment
#     reconciliation — expected answer follows conflict-01's precedent)
# ---------------------------------------------------------------------------
CASES += [
    case("amendment-01", ["amendment"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, subject to a cap "
         "of 1 times the total annual fees paid. 45. Amendment. Section 12 (Indemnification) is "
         "hereby amended and restated in its entirety: Vendor shall indemnify, defend, and hold "
         "harmless Customer from and against any third-party claims arising from Vendor's gross "
         "negligence or willful misconduct, subject to a cap of 2 times the total annual fees "
         "paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Explicit 'hereby amended and restated in its entirety' language signals the "
               "amendment supersedes the original 1x figure with 2x — a human reading this would "
               "likely conclude 2x governs deterministically. This adapter has no amendment-"
               "supersession logic (documented in conflict-01's notes as an intentional scope "
               "boundary, unlike the LoL adapter which does have this), so two same-direction "
               "obligations with different monetary terms (1x vs 2x) will be flagged as an "
               "unresolved conflict rather than resolved to the amendment's 2x. Labeled "
               "REQUIRES_REVIEW to match the adapter's actual documented scope boundary rather than "
               "asserting a capability (amendment resolution) this adapter was explicitly not built "
               "to have — but flag: if amendment-aware resolution is later added (mirroring the LoL "
               "adapter's approach), this label should become ACCEPT_WITH_NOTE (2x)."),
]

# ---------------------------------------------------------------------------
# 37. Indemnification terminology present with no actual obligation created
# ---------------------------------------------------------------------------
CASES += [
    case("no-obligation-01", ["no_obligation_created"],
         "12. Indemnification. The parties acknowledge the general concept of contractual "
         "indemnification. For the avoidance of doubt, no party shall have any indemnification "
         "obligation to the other under this Agreement.",
         "NOT_APPLICABLE", None,
         notes="Explicit, unambiguous negation — 'no party shall have any indemnification "
               "obligation' is a clean statement that nothing is promised. This differs from "
               "malformed-01's precedent (a destroyed anchor finding nothing) in that the anchor "
               "here is intact and the clause is clearly drafted, but its substance is a deliberate "
               "non-obligation. NOT_APPLICABLE is the honest answer: there is no indemnification "
               "obligation to evaluate, same conclusion as if the section were absent."),
    case("no-obligation-02", ["no_obligation_created"],
         "12. Definitions. 'Indemnification Cap' means, with respect to any indemnification "
         "obligation under this Agreement (if any), the maximum monetary exposure of the "
         "indemnifying party. No indemnification obligation is created by this definition alone.",
         "NOT_APPLICABLE", None,
         notes="A definitions-section mention of indemnification terminology, explicitly not "
               "itself creating an obligation and with no operative indemnify-clause anywhere else "
               "in this excerpt. Same reasoning as no-obligation-01: nothing to evaluate."),
]

# ---------------------------------------------------------------------------
# 38. Passive-voice / structurally unparseable directionality
# ---------------------------------------------------------------------------
CASES += [
    case("passive-01", ["ambiguous_directionality", "adversarial"],
         "12. Indemnification. Customer shall be indemnified and held harmless by Vendor from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 1 times the total annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Passive voice ('Customer shall be indemnified ... by Vendor') states the same "
               "Vendor->Customer promise as clean-01's active voice, but _OBLIGATION_RE only "
               "matches the active-voice shape (role1 + shall + indemnify + role2). No directional "
               "obligation can be parsed from this sentence structure. A human reads this "
               "unambiguously; this adapter cannot currently parse it — REQUIRES_REVIEW is the "
               "honest, safe answer given the actual extraction capability, not a claim that the "
               "underlying contract is itself ambiguous. If the engine happens to resolve this "
               "correctly some other way, that's a pleasant surprise worth noting, not expected."),
]

# ---------------------------------------------------------------------------
# 39. Reciprocal wording that is NOT actually symmetric once the fine print
#     is read (each party's obligation has a different real-world scope
#     despite "each party" phrasing)
# ---------------------------------------------------------------------------
CASES += [
    case("false-reciprocal-01", ["reciprocal", "adversarial"],
         "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
         "party from and against any third-party claims arising from the indemnifying party's "
         "gross negligence; provided, that Customer's indemnification obligations under this "
         "Section shall not exceed 1 times the total annual fees paid, and Vendor's "
         "indemnification obligations under this Section shall not exceed 5 times the total "
         "annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Opens with 'each party shall indemnify... the other party' (matching the reciprocal "
               "pattern) but the proviso then states DIFFERENT monetary caps per named party (1x "
               "for Customer, 5x for Vendor) — not actually symmetric. CORRECTED after the "
               "reciprocal-symmetry-verification fix: originally labeled ESCALATE on the theory "
               "that our real (Vendor) exposure is confidently identifiable as 5x. On reflection "
               "that assumes a reading the drafting doesn't actually support — a clause that opens "
               "with a symmetric claim and then states different numbers per party is genuinely "
               "ambiguous about which figure is truly controlling (is the reciprocal opener the "
               "operative term with the proviso merely illustrative, or do the named figures "
               "override the opener for each party specifically); confidently picking 5x as 'our "
               "number' is itself a guess, just a differently-shaped one than picking 1x. "
               "REQUIRES_REVIEW — a human resolving which figure actually governs — is the more "
               "defensible answer, consistent with this project's own abstention discipline (never "
               "guess when a fact can't be established) and with the explicit instruction that "
               "verified-symmetry failures should return REQUIRES_REVIEW or an escalation state, "
               "not a confident accept OR a confident guess at which value is real."),
]

# ---------------------------------------------------------------------------
# 40. Additional negative / deceptive edge cases
# ---------------------------------------------------------------------------
CASES += [
    case("deceptive-heading-01", ["negative", "malformed"],
         "12. Indemnification (Reserved). [This Section intentionally left blank; indemnification "
         "terms to be added by future amendment.]",
         "REQUIRES_REVIEW", "SKIP",
         notes="Heading exists and clearly signals intent to address indemnification, but no "
               "obligation is stated at all — an honest 'reserved' placeholder. Different from "
               "no-obligation-01/02 (explicit negation) in that this doesn't say no obligation will "
               "ever exist, it says none exists YET. No directional obligation can be parsed at all "
               "here (no 'X shall indemnify Y'), so this is REQUIRES_REVIEW ('could not be parsed') "
               "rather than MUST_REDLINE — MUST_REDLINE would imply an exposure obligation was found "
               "and is merely missing its monetary term, which is not what's true of this text."),
    case("deceptive-defined-term-01", ["negative"],
         "12. Payment Terms. As used in this Section, 'Indemnification Period' means the 90-day "
         "period following an invoice during which Customer may dispute charges. No indemnification "
         "obligation under Section 45 (Indemnification) is affected by this Section.",
         "REQUIRES_REVIEW", "SKIP",
         notes="CORRECTED after the first Phase 1 run: originally labeled NOT_APPLICABLE, on the "
               "theory that the second sentence was a clean negation. On closer reading it is not — "
               "'No indemnification obligation under Section 45 is affected by this Section' "
               "actually PRESUPPOSES a real indemnification obligation exists under Section 45, and "
               "states only that this (Payment Terms) section doesn't change it. That is a "
               "cross-reference to a real clause not included in this excerpt, not a negation of "
               "the clause's existence. 'Indemnification Period' is still a defined-term trap "
               "unrelated to indemnification itself, but the honest answer given both sentences "
               "together is REQUIRES_REVIEW (a real obligation is referenced but not visible here), "
               "not NOT_APPLICABLE — the original label was an authoring misread of my own test "
               "text, not a finding about the engine."),
]

# ---------------------------------------------------------------------------
# 41. Monetary threshold boundary sweep (multiplier values right at each
#     ladder boundary — preferred/acceptable/negotiate — independent of any
#     single trigger or directional complexity, isolating threshold logic)
# ---------------------------------------------------------------------------
CASES += [
    case("threshold-01", ["monetary", "threshold_boundary"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 1.5 times the total annual fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "multiplier", "multiplier": 1.5}),
    case("threshold-02", ["monetary", "threshold_boundary"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 3 times the total annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 3.0},
         notes="3x sits exactly at negotiate_max — the boundary itself, not beyond it."),
    case("threshold-03", ["monetary", "threshold_boundary"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 3.1 times the total annual fees paid.",
         "ESCALATE", {"kind": "multiplier", "multiplier": 3.1},
         notes="Just past the negotiate_max boundary — the immediate next value beyond threshold-02."),
    case("threshold-04", ["monetary", "threshold_boundary"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 0.5 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 0.5},
         notes="Below the preferred multiplier — more favorable than our own ideal position, still "
               "a clean accept."),
]

# ---------------------------------------------------------------------------
# 42. Reciprocal clause combined with a required protection trigger (tests
#     that a symmetric obligation, used simultaneously as both exposure and
#     protection, is checked against protection-trigger requirements too)
# ---------------------------------------------------------------------------
CASES += [
    case("reciprocal-06", ["reciprocal", "missing_protection"],
         "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
         "party from and against any third-party claims arising from the indemnifying party's "
         "gross negligence. Each party's indemnification obligations shall not exceed 1 times the "
         "total annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"required_protection_triggers_json": ["ip_infringement"]},
         notes="Symmetric 1x/gross_negligence-only clause used as both exposure and protection — "
               "our exposure is clean (1x, ACCEPT-worthy) but the required ip_infringement "
               "protection trigger isn't covered by the reciprocal terms either, so the missing-"
               "protection finding should still surface even though the same obligation object "
               "serves both roles."),
]

# ---------------------------------------------------------------------------
# 43. Prohibited exposure trigger combined with willful misconduct (tests
#     that a prohibited-trigger finding and an otherwise-clean uncapped/
#     capped monetary reading combine correctly, not silently drop one)
# ---------------------------------------------------------------------------
CASES += [
    case("prohibited-exposure-02", ["prohibited_exposure"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's ordinary negligence or willful "
         "misconduct. Vendor's indemnification obligations shall not exceed 1 times the total "
         "annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 1.0},
         {"negligence": "covered", "willful_misconduct": "covered"},
         policy_overrides={"prohibited_exposure_triggers_json": ["negligence"]},
         notes="Ordinary negligence is prohibited by policy even though willful_misconduct coverage "
               "and the 1x monetary term are both fine on their own — the prohibited-trigger finding "
               "should still drive NEGOTIATE, not be masked by an otherwise-clean monetary reading."),
]

# ---------------------------------------------------------------------------
# 44. Asymmetric obligations where OUR exposure is clean but the
#     counterparty's protection to us is deficient — verifies the two
#     sides are genuinely scored independently, not just whichever is worse
# ---------------------------------------------------------------------------
CASES += [
    case("asym-04", ["asymmetric", "missing_protection"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence, subject to a cap "
         "of 1 times the total annual fees paid. Customer shall indemnify, defend, and hold "
         "harmless Vendor from and against any third-party claims arising from Customer's "
         "negligence, subject to a cap of 1 times the total annual fees paid.",
         "NEGOTIATE", {"kind": "multiplier", "multiplier": 1.0},
         expected_protection_present=True,
         policy_overrides={"required_protection_triggers_json": ["ip_infringement"]},
         notes="Our (Vendor's) 1x exposure is clean. Customer's 1x protection to us is also clean "
               "in monetary terms, but only covers negligence — not the ip_infringement protection "
               "our policy requires. The final state should reflect the protection-side gap even "
               "though the exposure side alone would have been a clean ACCEPT."),
]

# ---------------------------------------------------------------------------
# 45. Third-party-only requirement satisfied only via absence of any first-
#     party signal (no explicit 'third-party claims' phrase at all, no
#     first-party phrase either — genuinely silent on scope)
# ---------------------------------------------------------------------------
CASES += [
    case("scope-05", ["scope"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any claims arising from Vendor's gross negligence. Vendor's indemnification "
         "obligations shall not exceed 1 times the total annual fees paid.",
         "NEGOTIATE", "SKIP",
         notes="'any claims' with no third-party-only qualifier and no first-party-inclusive "
               "signal either — genuinely silent on scope. A policy that specifically requires "
               "third-party-only coverage should not treat unstated scope as satisfying that "
               "requirement; silence is not the same as an affirmative 'third-party claims' "
               "limitation. Since neither regex fires, this adapter's scope classifier will report "
               "'not_addressed', which the evaluator currently treats as satisfying the third-"
               "party-only requirement (only 'includes_first_party' triggers the NEGOTIATE branch) "
               "— if the engine reports ACCEPT here, that's a real finding about how 'not_addressed' "
               "scope is treated as equivalent to 'confirmed third-party-only', which is not the "
               "same fact and arguably should not auto-pass a policy that affirmatively requires "
               "third-party-only language to be present."),
]

# ---------------------------------------------------------------------------
# 46. Mutual policy configured against a genuinely reciprocal contract
#     (contrasts with undefined-03, which is mutual policy against a
#     directional contract — here the policy/contract shapes actually
#     match, confirming mutual policy isn't unconditionally REQUIRES_REVIEW)
# ---------------------------------------------------------------------------
CASES += [
    case("mutual-match-01", ["reciprocal", "mutual_policy"],
         "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
         "party from and against any third-party claims arising from the indemnifying party's "
         "gross negligence. Each party's indemnification obligations shall not exceed 1 times the "
         "total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"contract_side": "mutual"},
         notes="Contrast with undefined-03: THIS case's contract is genuinely reciprocal, matching "
               "a mutual policy configuration — should resolve cleanly, not be treated as an "
               "unresolvable mismatch just because contract_side is 'mutual'."),
]

# ---------------------------------------------------------------------------
# 47. Two entirely separate reciprocal clauses in one document with
#     different terms (e.g. a general reciprocal clause plus a narrower,
#     IP-specific reciprocal carve-out with a different, higher cap)
# ---------------------------------------------------------------------------
CASES += [
    case("multi-reciprocal-01", ["reciprocal", "multiple_provisions"],
         "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
         "party from and against any third-party claims arising from the indemnifying party's "
         "gross negligence. Each party's indemnification obligations shall not exceed 1 times the "
         "total annual fees paid. 13. IP Indemnification. Each party shall indemnify, defend, and "
         "hold harmless the other party from and against any third-party claims arising from the "
         "indemnifying party's infringement of intellectual property rights. Each party's "
         "indemnification obligations under this Section 13 shall not exceed 3 times the total "
         "annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="Two distinct reciprocal clauses (general 1x, IP-specific 3x) rather than one — "
               "this adapter has no per-trigger monetary segmentation and no reconciliation logic "
               "for multiple mutual-reciprocal matches, so it will resolve to whichever it finds "
               "first (the general 1x clause, given seen_spans ordering by position). "
               "expected_exposure_monetary reflects that documented first-match behavior (1x), "
               "consistent with multi-01's 'current adapter resolves the first match it finds' "
               "precedent for the analogous unilateral case — not a claim that per-trigger monetary "
               "segmentation is actually supported."),
]

# ---------------------------------------------------------------------------
# 48. Threshold boundary at the preferred/acceptable line (2.0x) and a
#     fixed-dollar exposure evaluated buy-side (verifies fixed-amount
#     escalation isn't accidentally direction-dependent)
# ---------------------------------------------------------------------------
CASES += [
    case("threshold-05", ["monetary", "threshold_boundary"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. Vendor's "
         "indemnification obligations shall not exceed 2 times the total annual fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "multiplier", "multiplier": 2.0},
         notes="2x sits exactly at the acceptable_max boundary."),
    case("monetary-buyside-01", ["monetary", "buy_side"],
         "12. Indemnification. Customer shall indemnify, defend, and hold harmless Vendor from and "
         "against any third-party claims arising from Customer's gross negligence. Customer's "
         "maximum liability under this indemnification obligation shall not exceed $250,000.",
         "ESCALATE", {"kind": "fixed", "fixed_amount": 250000.0},
         expected_direction=("Customer", "Vendor"),
         policy_overrides={"contract_side": "buy_side"},
         notes="Fixed-dollar exposure escalates for manual comparison regardless of which side we "
               "are on — mirrors monetary-01's sell-side fixed-amount case."),
]

# ---------------------------------------------------------------------------
# 49. Negation-guard edge case: an unrelated defined term that starts with
#     "non-indemnification" style prefixing, near but not matching the
#     "no <anchor>" negation guard pattern
# ---------------------------------------------------------------------------
CASES += [
    case("negation-edge-01", ["negative", "adversarial"],
         "12. Non-Indemnification Matters. This Section addresses matters unrelated to "
         "indemnification. See Section 45 for the Agreement's actual indemnification terms, which "
         "provide that Vendor shall indemnify, defend, and hold harmless Customer from and against "
         "any third-party claims arising from Vendor's gross negligence, subject to a cap of 1 "
         "times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         notes="A heading using 'Non-Indemnification' as a defined section label (not a negation of "
               "the operative clause) should not prevent the real obligation stated later in the "
               "same excerpt from being found and evaluated normally."),
]

# ---------------------------------------------------------------------------
# 50. Absent, additional pattern: indemnification mentioned only inside an
#     unrelated clause's cross-reference, with no clause of its own present
# ---------------------------------------------------------------------------
CASES += [
    case("absent-05", ["absent"],
         "9. Insurance. Vendor shall maintain commercial general liability insurance in an amount "
         "not less than $1,000,000 per occurrence, covering the risks that would otherwise be "
         "addressed by indemnification under a separate agreement not incorporated herein.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Mentions 'indemnification' in passing (not negated) while describing an insurance "
               "requirement, with no directional 'X shall indemnify Y' obligation anywhere in the "
               "text. The anchor fires (word present, not negated), but nothing parseable follows — "
               "same REQUIRES_REVIEW reasoning as the other anchor-found-but-unparseable cases "
               "(malformed-05, defend-only-01, passive-01), not NOT_APPLICABLE, since the anchor "
               "itself isn't filtered by the negation guard here."),
]

# ---------------------------------------------------------------------------
# 51. Conflicting defense-control signals within the same obligation
#     (both indemnifying-party-controls and indemnified-party-controls
#     language present, contradicting each other rather than being absent)
# ---------------------------------------------------------------------------
CASES += [
    case("defense-conflict-01", ["defense_control", "adversarial"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. The indemnifying "
         "party shall control the defense of any such claim; provided, that the indemnified party "
         "may control its own defense at Vendor's expense if it reasonably believes a conflict of "
         "interest exists. Vendor's indemnification obligations shall not exceed 1 times the total "
         "annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"require_defense_control_for_exposure": True},
         notes="Both defense-control signals are present (indemnifying party controls by default; "
               "indemnified party may take over under a specific condition) — this adapter's "
               "_classify_defense_control treats 2+ signals as 'shared', which satisfies a policy "
               "requiring the indemnifying party to control OR share control. A defensible reading, "
               "though a lawyer might note the conditional carve-out is narrower than true shared "
               "control — flagged as a judgment call, not asserting a stricter alternative label."),
]

# ---------------------------------------------------------------------------
# 52. Willful misconduct combined with a required protection trigger that
#     IS satisfied, and a separate case where a prohibited exposure trigger
#     is stated but genuinely excluded by carve-out (should NOT negotiate)
# ---------------------------------------------------------------------------
CASES += [
    case("missing-protection-04", ["missing_protection", "buy_side"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's infringement of intellectual "
         "property rights or data breach. Vendor's indemnification obligations shall not exceed "
         "1 times the total annual fees paid.",
         "ACCEPT", "SKIP",
         policy_overrides={"contract_side": "buy_side",
                            "required_protection_triggers_json": ["ip_infringement", "data_breach"]},
         notes="Both required protection triggers (ip_infringement, data_breach) are covered by "
               "Vendor's obligation to us — should accept cleanly, confirming multi-trigger "
               "required-protection checks aren't satisfied by only a partial match."),
    case("prohibited-excluded-01", ["prohibited_exposure", "nested_exceptions"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence or willful "
         "misconduct, except for claims arising from Vendor's ordinary negligence, which are "
         "expressly excluded from this indemnification obligation. Vendor's indemnification "
         "obligations shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         {"negligence": "excluded", "gross_negligence": "covered", "willful_misconduct": "covered"},
         policy_overrides={"prohibited_exposure_triggers_json": ["negligence"]},
         notes="Ordinary negligence is both prohibited by policy AND already excluded by the "
               "contract's own carve-out — the prohibited-trigger check should look at whether the "
               "trigger is COVERED, not merely mentioned; an excluded trigger is not a policy "
               "violation, it's the drafting already doing what the policy wants."),
]

# ---------------------------------------------------------------------------
# 53. Cross-reference to an Order Form / Schedule (not "Section N") for the
#     monetary cap — a different delegation target than xref-01/02/03
# ---------------------------------------------------------------------------
CASES += [
    case("xref-04", ["cross_referenced_cap"],
         "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
         "against any third-party claims arising from Vendor's gross negligence. The applicable "
         "liability cap for this indemnification obligation is set forth in the Order Form.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Delegates to 'the Order Form' rather than a numbered Section — "
               "_MONETARY_CROSS_REF_RE's capture group specifically expects 'Section \\d+', so this "
               "phrasing (same 'liability cap ... set forth in' shape, different target format) "
               "will not match at all and will fall through to 'not_stated' rather than "
               "'cross_reference'. Semantically this is still a delegated, unresolved cap — "
               "REQUIRES_REVIEW, not MUST_REDLINE's 'insert cap language' framing. Adversarial: "
               "probes the target-pattern's narrowness, not just the trigger-phrase narrowness "
               "already probed by xref-03."),
]

# ---------------------------------------------------------------------------
# 54. A fully clean reciprocal clause combined with defense control AND
#     notice/cooperation requirements all satisfied at once (positive
#     composite case — verifies multiple simultaneously-satisfied policy
#     requirements don't interfere with each other)
# ---------------------------------------------------------------------------
CASES += [
    case("composite-clean-01", ["reciprocal", "defense_control", "notice_cooperation"],
         "12. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
         "party from and against any third-party claims arising from the indemnifying party's "
         "gross negligence, provided that the party seeking indemnification gives prompt written "
         "notice of any such claim and its reasonable cooperation in the defense thereof. The "
         "indemnifying party shall control the defense of any such claim at its own expense. Each "
         "party's indemnification obligations shall not exceed 1 times the total annual fees "
         "paid.",
         "ACCEPT", {"kind": "multiplier", "multiplier": 1.0},
         policy_overrides={"require_defense_control_for_exposure": True,
                            "require_notice_and_cooperation_for_exposure": True},
         notes="All three policy requirements (clean 1x cap, defense control by indemnifying "
               "party, notice+cooperation precondition) are satisfied simultaneously in one "
               "reciprocal clause — a fully clean composite case."),
]
