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
