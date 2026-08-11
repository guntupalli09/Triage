"""
Labeled adversarial corpus for the Governing Law policy engine benchmark
(see benchmarks/run_governing_law_benchmark.py). Batch A, adapter 3 of 3
— the structurally simplest and most different shape: a categorical
jurisdiction lookup with no directionality.

Labels here were written from the policy semantics and drafting pattern
alone.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "sell_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: Delaware governing law, binding arbitration.",
    "preferred_jurisdictions_json": ["Delaware"],
    "acceptable_jurisdictions_json": ["New York", "California"],
    "prohibited_jurisdictions_json": ["Russia"],
    "required_dispute_resolution": None,
    "require_jury_trial_waiver": False,
}


def case(
    id: str,
    tags: List[str],
    text: str,
    expected_state: str,
    expected_jurisdiction: Any = "SKIP",
    expected_dispute_resolution: Any = "SKIP",
    policy_overrides: Optional[Dict[str, Any]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "expected_state": expected_state,
        "expected_jurisdiction": expected_jurisdiction,
        "expected_dispute_resolution": expected_dispute_resolution,
        "policy_overrides": policy_overrides or {},
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

CASES += [
    case("preferred-01", ["jurisdiction"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware.",
         "ACCEPT", "Delaware"),
    case("acceptable-01", ["jurisdiction"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of New York.",
         "ACCEPT_WITH_NOTE", "New York"),
    case("acceptable-02", ["jurisdiction"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of California.",
         "ACCEPT_WITH_NOTE", "California"),
    case("prohibited-01", ["jurisdiction"],
         "20. Governing Law. This Agreement shall be governed by the laws of Russia.",
         "PROHIBITED", "Russia"),
    case("unlisted-01", ["jurisdiction"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of Texas.",
         "NEGOTIATE", "Texas"),
    case("unlisted-02", ["jurisdiction"],
         "20. Governing Law. This Agreement shall be governed by the laws of England and Wales.",
         "NEGOTIATE", "England and Wales"),
]

CASES += [
    case("dispute-01", ["dispute_resolution"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware. Any dispute arising under this Agreement shall be resolved by binding "
         "arbitration.",
         "ACCEPT", "Delaware", "arbitration",
         policy_overrides={"required_dispute_resolution": "arbitration"}),
    case("dispute-02", ["dispute_resolution"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware. The parties submit to the exclusive jurisdiction of the state and "
         "federal courts located in Wilmington, Delaware.",
         "NEGOTIATE", "Delaware", "litigation",
         policy_overrides={"required_dispute_resolution": "arbitration"},
         notes="Litigation stated where policy requires arbitration."),
    case("dispute-03", ["dispute_resolution"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware.",
         "MUST_REDLINE", "Delaware", "not_stated",
         policy_overrides={"required_dispute_resolution": "arbitration"},
         notes="No dispute resolution mechanism stated at all."),
    case("dispute-04", ["dispute_resolution"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware. The parties shall first attempt to resolve any dispute through "
         "mediation, and if unresolved after 30 days, through binding arbitration.",
         "ACCEPT", "Delaware", "mediation_then_arbitration",
         policy_overrides={"required_dispute_resolution": "arbitration"},
         notes="Mediation-then-arbitration satisfies an arbitration requirement."),
    case("dispute-05", ["dispute_resolution"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware. The parties submit to the exclusive jurisdiction of the state and "
         "federal courts located in Wilmington, Delaware.",
         "ACCEPT", "Delaware", "litigation",
         policy_overrides={"required_dispute_resolution": "litigation"},
         notes="Litigation required and litigation stated — clean match."),
]

CASES += [
    case("jury-01", ["jury_waiver"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware. Each party hereby waives its right to a trial by jury.",
         "ACCEPT", "Delaware",
         policy_overrides={"require_jury_trial_waiver": True}),
    case("jury-02", ["jury_waiver"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware.",
         "NEGOTIATE", "Delaware",
         policy_overrides={"require_jury_trial_waiver": True},
         notes="No jury waiver stated, required by policy."),
    case("jury-03", ["jury_waiver", "dispute_resolution"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware. Any dispute shall be resolved by binding arbitration.",
         "ACCEPT", "Delaware", "arbitration",
         policy_overrides={"require_jury_trial_waiver": True},
         notes="Arbitration makes a jury waiver moot — no jury trial exists to waive."),
]

CASES += [
    case("no-directionality-01", ["no_directionality", "buy_side"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware.",
         "ACCEPT", "Delaware",
         policy_overrides={"contract_side": "buy_side"},
         notes="Governing law applies uniformly — the same clause resolves identically "
               "regardless of which side we're on."),
    case("no-directionality-02", ["no_directionality", "mutual"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware.",
         "ACCEPT", "Delaware",
         policy_overrides={"contract_side": "mutual"},
         notes="Unlike every directional adapter, a 'mutual' contract_side is never itself an "
               "unresolved fact here — there is no directionality to be ambiguous about."),
]

CASES += [
    case("malformed-01", ["malformed"],
         "20. Governing Law. This Agreement is governed by applicable law.",
         "REQUIRES_REVIEW",
         notes="Anchor fires ('governed by'), but no specific jurisdiction is named — "
               "honest abstention, not a guess."),
    case("malformed-02", ["malformed"],
         "20.  Governing   Law.    This   Agreement   shall   be   governed   by   the   "
         "laws   of   the   State   of   Delaware.",
         "ACCEPT", "Delaware", notes="Excess whitespace only, words spelled correctly."),
    case("malformed-03", ["malformed"],
         "20. Governing Law. This Agreement shall be governed by the laws of [***].",
         "REQUIRES_REVIEW", notes="Redacted jurisdiction — must not fabricate a value."),
]

CASES += [
    case("absent-01", ["absent"],
         "8. Confidentiality. Each party shall protect the other party's Confidential Information.",
         "NOT_APPLICABLE"),
    case("absent-02", ["absent"],
         "8. Confidentiality. Each party shall protect the other party's Confidential "
         "Information. No governing law is specified in this Agreement.",
         "NOT_APPLICABLE"),
]

CASES += [
    case("venue-differs-01", ["venue"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware. The parties submit to the exclusive jurisdiction of the state and "
         "federal courts located in New York, New York.",
         "ACCEPT", "Delaware",
         notes="Governing law and venue can differ (Delaware law, New York venue) — a real, "
               "common drafting pattern; this adapter only scores jurisdiction/dispute-"
               "resolution/jury-waiver in this pass, venue extraction is verified separately "
               "not to break jurisdiction parsing."),
]
