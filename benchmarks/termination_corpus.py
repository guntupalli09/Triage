"""
Labeled adversarial corpus for the Termination policy engine benchmark
(see benchmarks/run_termination_benchmark.py). Third clause adapter —
authorized specifically to stress the architecture along a reasoning
shape neither Liability (comparative value) nor Indemnification (directed
obligation graph) exercises: a catalog of independently-true contingent
rights (convenience / cause / insolvency / non-payment), each with its
own trigger, conditions (notice/cure), and consequence.

Labels here were written from the policy semantics and drafting pattern
alone — what SHOULD happen given who holds what right, under what
trigger, with what conditions — never by running the implementation and
copying its output. Where the "correct" answer is genuinely a judgment
call, the case is labeled with the most defensible reading and flagged
in `notes`.

DEFAULT_POLICY represents a sell-side vendor's playbook: we are Vendor/
Supplier, Customer/Client is the counterparty.

expected_fee / expected_survival_topics / expected_rights follow the same
"SKIP unless asserted" discipline as the Liability and Indemnification
corpora — only fields explicitly asserted are scored.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "sell_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: mutual 60-day convenience termination, 30-day cure period.",
    "require_mutual_convenience_termination": True,
    "min_notice_days_against_us": 60,
    "min_cure_days_against_us": 30,
    "prohibit_immediate_termination_for_cause": False,
    "required_survival_topics_json": [],
    "prohibit_uncapped_termination_fee": True,
    "fee_preferred_multiplier": 1.0,
    "fee_acceptable_max_multiplier": 2.0,
    "fee_negotiate_max_multiplier": 3.0,
}


def case(
    id: str,
    tags: List[str],
    text: str,
    expected_state: str,
    expected_fee: Any = "SKIP",
    expected_trigger_types: Any = "SKIP",  # set of trigger_type strings expected among facts.rights
    expected_survival_present: Any = "SKIP",  # dict of topic -> bool, subset checked
    policy_overrides: Optional[Dict[str, Any]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "expected_state": expected_state,
        "expected_fee": expected_fee,
        "expected_trigger_types": expected_trigger_types,
        "expected_survival_present": expected_survival_present,
        "policy_overrides": policy_overrides or {},
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# 1. Clean mutual rights (convenience / cause / insolvency)
# ---------------------------------------------------------------------------
CASES += [
    case("clean-01", ["clean_mutual", "convenience"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice.",
         "ACCEPT", expected_trigger_types={"convenience"}),
    case("clean-02", ["clean_mutual", "cause"],
         "15. Termination. Either party may terminate this Agreement for cause if the other "
         "party materially breaches this Agreement and fails to cure such breach within 30 "
         "days after written notice.",
         "ACCEPT", expected_trigger_types={"material_breach"}),
    case("clean-03", ["clean_mutual", "insolvency"],
         "15. Termination. Either party may terminate this Agreement immediately upon the "
         "other party's insolvency, bankruptcy, or assignment for the benefit of creditors.",
         "ACCEPT", expected_trigger_types={"insolvency"},
         notes="Immediate termination on insolvency is a conventional, expected allocation — "
               "not itself a problem, no cure period required."),
    case("clean-04", ["clean_mutual", "multiple_rights"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice. Either party may terminate this Agreement for cause if "
         "the other party materially breaches this Agreement and fails to cure such breach "
         "within 30 days after written notice. Either party may terminate this Agreement "
         "immediately upon the other party's insolvency or bankruptcy.",
         "ACCEPT", expected_trigger_types={"convenience", "material_breach", "insolvency"},
         notes="Three independently-true rights, not reconciled into one controlling provision."),
]

# ---------------------------------------------------------------------------
# 2. Notice period adequacy (convenience termination against us)
# ---------------------------------------------------------------------------
CASES += [
    case("notice-01", ["notice_adequacy"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice.",
         "ACCEPT"),
    case("notice-02", ["notice_adequacy"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 60 "
         "days prior written notice.",
         "ACCEPT", notes="Exactly at the policy minimum — boundary inclusive."),
    case("notice-03", ["notice_adequacy"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 15 "
         "days prior written notice.",
         "NEGOTIATE"),
    case("notice-04", ["notice_adequacy"],
         "15. Termination. Either party may terminate this Agreement for convenience.",
         "MUST_REDLINE", notes="No notice period stated at all for the convenience right."),
    case("notice-05", ["notice_adequacy", "buy_side"],
         "15. Termination. Vendor may terminate this Agreement for convenience upon 10 days "
         "prior written notice.",
         "NEGOTIATE",
         policy_overrides={"contract_side": "buy_side", "require_mutual_convenience_termination": False},
         notes="We are Customer; Vendor's convenience right against us has inadequate notice."),
]

# ---------------------------------------------------------------------------
# 3. Cure period adequacy (for-cause termination against us)
# ---------------------------------------------------------------------------
CASES += [
    case("cure-01", ["cure_adequacy"],
         "15. Termination. Either party may terminate this Agreement for cause if the other "
         "party materially breaches this Agreement and fails to cure such breach within 30 "
         "days after written notice.",
         "ACCEPT"),
    case("cure-02", ["cure_adequacy"],
         "15. Termination. Either party may terminate this Agreement for cause if the other "
         "party materially breaches this Agreement and fails to cure such breach within 5 "
         "days after written notice.",
         "NEGOTIATE"),
    case("cure-03", ["cure_adequacy"],
         "15. Termination. Either party may terminate this Agreement for cause if the other "
         "party materially breaches this Agreement.",
         "MUST_REDLINE", notes="No cure period stated at all for the for-cause right."),
    case("cure-04", ["cure_adequacy", "immediate"],
         "15. Termination. Either party may terminate this Agreement immediately upon a "
         "material breach of this Agreement by the other party, without opportunity to cure.",
         "ESCALATE", policy_overrides={"prohibit_immediate_termination_for_cause": False},
         notes="Immediate termination for a curable breach (not insolvency) is a real risk — "
               "escalate for manual review under a permissive policy."),
    case("cure-05", ["cure_adequacy", "immediate"],
         "15. Termination. Either party may terminate this Agreement immediately upon a "
         "material breach of this Agreement by the other party, without opportunity to cure.",
         "PROHIBITED", policy_overrides={"prohibit_immediate_termination_for_cause": True}),
]

# ---------------------------------------------------------------------------
# 4. Unilateral vs. mutual rights
# ---------------------------------------------------------------------------
CASES += [
    case("unilateral-01", ["unilateral", "buy_side"],
         "15. Termination. Customer may terminate this Agreement for convenience upon 90 days "
         "prior written notice.",
         "NEGOTIATE",
         notes="Counterparty (Customer) holds a convenience right; we (Vendor, sell_side "
               "default) do not — mutuality required by default policy."),
    case("unilateral-02", ["unilateral"],
         "15. Termination. Vendor may terminate this Agreement for convenience upon 30 days "
         "prior written notice.",
         "ACCEPT", policy_overrides={"require_mutual_convenience_termination": False},
         notes="We (Vendor) hold a convenience right; nothing is stated about Customer holding "
               "one against us, so there's no notice/cure risk to bound, and mutuality isn't "
               "required by this override."),
    case("unilateral-03", ["unilateral", "undefined_parties"],
         "15. Termination. Acme may terminate this Agreement for convenience upon 90 days "
         "prior written notice.",
         "REQUIRES_REVIEW",
         notes="'Acme' is not a recognized buy/sell-side role word — must not guess which side "
               "holds this right."),
    case("unilateral-04", ["unilateral", "mutual_policy"],
         "15. Termination. Vendor may terminate this Agreement for convenience upon 90 days "
         "prior written notice.",
         "REQUIRES_REVIEW", policy_overrides={"contract_side": "mutual"},
         notes="Recognized role, but policy is configured mutual while the contract is "
               "directional — cannot determine which side is ours."),
]

# ---------------------------------------------------------------------------
# 5. Reciprocal-right symmetry verification (the third directional shape)
# ---------------------------------------------------------------------------
CASES += [
    case("symmetry-01", ["reciprocal_symmetry"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice.",
         "ACCEPT", notes="Genuinely mutual, no per-party attribution — baseline."),
    case("symmetry-02", ["reciprocal_symmetry", "adversarial"],
         "15. Termination. Either party may terminate this Agreement for convenience; "
         "provided, that Vendor's right to terminate under this Section requires 90 days "
         "prior written notice, and Customer's right to terminate under this Section "
         "requires 10 days prior written notice.",
         "REQUIRES_REVIEW",
         notes="Opens with 'either party' (claiming symmetry) but a differentiated proviso "
               "states different notice periods per named party — the symmetry claim cannot "
               "be verified, so which figure is truly ours/theirs cannot be determined from "
               "this drafting alone."),
    case("symmetry-03", ["reciprocal_symmetry", "adversarial"],
         "15. Termination. Either party may terminate this Agreement for cause upon a "
         "material breach by the other party; provided, that Vendor's right to terminate "
         "under this Section requires a 30 days cure period, and Customer's right to "
         "terminate under this Section requires a 5 days cure period.",
         "REQUIRES_REVIEW",
         notes="Same shape as symmetry-02 but on the cure-period axis."),
    case("symmetry-04", ["reciprocal_symmetry"],
         "15. Termination. Either party may terminate this Agreement for convenience; "
         "Vendor's right to terminate under this Section requires 90 days prior written "
         "notice, and Customer's right to terminate under this Section requires 90 days "
         "prior written notice.",
         "ACCEPT",
         notes="Both named parties' terms genuinely agree — must NOT be flagged as asymmetric."),
]

# ---------------------------------------------------------------------------
# 6. Survival clause completeness
# ---------------------------------------------------------------------------
CASES += [
    case("survival-01", ["survival"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice. The following provisions shall survive termination of "
         "this Agreement: Confidentiality, Limitation of Liability, and accrued but unpaid "
         "payment obligations.",
         "ACCEPT", expected_survival_present={"confidentiality": True, "limitation_of_liability": True},
         policy_overrides={"required_survival_topics_json": ["confidentiality", "limitation_of_liability"]}),
    case("survival-02", ["survival"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice. The following provisions shall survive termination of "
         "this Agreement: Confidentiality.",
         "NEGOTIATE", expected_survival_present={"confidentiality": True, "limitation_of_liability": False},
         policy_overrides={"required_survival_topics_json": ["confidentiality", "limitation_of_liability"]},
         notes="Limitation of Liability is required by this case's policy override but not "
               "listed as surviving."),
    case("survival-03", ["survival"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice.",
         "NEGOTIATE",
         policy_overrides={"required_survival_topics_json": ["confidentiality", "limitation_of_liability"]},
         notes="No survival clause at all, though this case's policy override requires two topics."),
    case("survival-04", ["survival"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice.",
         "ACCEPT",
         notes="No survival requirement configured (default policy) — absence is not itself "
               "penalized."),
]

# ---------------------------------------------------------------------------
# 7. Termination fee
# ---------------------------------------------------------------------------
CASES += [
    case("fee-01", ["fee"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice.",
         "ACCEPT", expected_fee={"kind": "not_mentioned"},
         notes="No termination fee mentioned at all — the common case, never itself penalized."),
    case("fee-02", ["fee"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice. Customer shall pay a termination fee equal to 1 times "
         "the total annual fees paid.",
         "ACCEPT", expected_fee={"kind": "multiplier", "multiplier": 1.0}),
    case("fee-03", ["fee"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice. Customer shall pay a termination fee equal to 5 times "
         "the total annual fees paid.",
         "ESCALATE", expected_fee={"kind": "multiplier", "multiplier": 5.0}),
    case("fee-04", ["fee"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice. Customer shall pay a termination fee of $500,000.",
         "ESCALATE", expected_fee={"kind": "fixed", "fixed_amount": 500000.0}),
    case("fee-05", ["fee"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice. Vendor shall pay a termination fee that shall not be "
         "subject to any cap.",
         "PROHIBITED", expected_fee={"kind": "unlimited"}),
    case("fee-06", ["fee"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice. Customer shall pay a termination fee.",
         "MUST_REDLINE", expected_fee={"kind": "not_stated"},
         notes="A termination fee is referenced but no amount at all is stated."),
]

# ---------------------------------------------------------------------------
# 8. Malformed / incomplete drafting
# ---------------------------------------------------------------------------
CASES += [
    case("malformed-01", ["malformed"],
         "15. Terminaton. Eithr party may terminat this Agreemnt for convenence upon 90 days "
         "notce.",
         "REQUIRES_REVIEW",
         notes="CORRECTED after the first benchmark run, per this case's own original caveat: "
               "the typo in 'Terminaton' still contains the 'terminat' substring the anchor "
               "matches, so the anchor itself is NOT broken (unlike, e.g., the LoL/"
               "Indemnification corpora's malformed-01 cases, where the typo removes the exact "
               "substring the anchor requires). With the anchor intact but 'terminat this "
               "Agreemnt' too corrupted to match the operative right pattern, this is "
               "structurally identical to malformed-04 (anchor found, nothing parseable) — "
               "REQUIRES_REVIEW is correct, not NOT_APPLICABLE, which should be reserved for "
               "an anchor that fails to match (or is explicitly negated) at all."),
    case("malformed-02", ["malformed"],
         "15.  Termination.    Either   party   may   terminate   this   Agreement   for   "
         "convenience   upon   90   days   prior   written   notice.",
         "ACCEPT", notes="Excess whitespace only, words spelled correctly."),
    case("malformed-03", ["malformed"],
         "15. Termination. [***] may terminate this Agreement for convenience upon 90 days "
         "prior written notice.",
         "REQUIRES_REVIEW", notes="Redacted party name — must not fabricate a role."),
    case("malformed-04", ["malformed"],
         "15. Termination. [Section intentionally left incomplete — termination terms to be "
         "negotiated.]",
         "REQUIRES_REVIEW",
         notes="Anchor word present ('Termination', 'terminated' isn't even required — "
               "'termination' itself matches terminat\\w*), but no parseable right — honest "
               "answer is REQUIRES_REVIEW, not a guess."),
]

# ---------------------------------------------------------------------------
# 9. Absent termination clause
# ---------------------------------------------------------------------------
CASES += [
    case("absent-01", ["absent"],
         "9. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware.",
         "NOT_APPLICABLE"),
    case("absent-02", ["absent"],
         "8. Confidentiality. Each party shall protect the other party's Confidential "
         "Information using reasonable care.",
         "NOT_APPLICABLE"),
    case("absent-03", ["absent"],
         "9. Governing Law. This Agreement is governed by Delaware law. No termination right "
         "is granted under this Agreement.",
         "NOT_APPLICABLE",
         notes="Explicit negation immediately preceding the anchor — filtered by the "
               "negation guard, same as the Indemnification adapter's equivalent case."),
]

# ---------------------------------------------------------------------------
# 10. Post-termination transition assistance (present, not independently
#     scored by this adapter — verifies it doesn't break extraction)
# ---------------------------------------------------------------------------
CASES += [
    case("transition-01", ["transition_assistance"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 90 "
         "days prior written notice. Upon termination, Vendor shall provide reasonable "
         "transition assistance to Customer for up to 90 days at Customer's request.",
         "ACCEPT",
         notes="Transition-assistance language has no dedicated policy check in this adapter "
               "and is not scored — this case verifies its presence doesn't corrupt "
               "notice/cure extraction for the surrounding right."),
]
