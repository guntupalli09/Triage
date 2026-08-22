#!/usr/bin/env python3
"""Step 4A.10.8 — EXPLICITLY NON-AUTHORITATIVE development/adversarial
controls for the equal-treatment-cue opener-masking fix. Never to be
treated as a frozen validation corpus. Per the user's mandate: attack
every reciprocal-opener SHAPE (each/either/both/every/one another/
nominalized-duty) paired with a downstream difference in EACH of scope,
survival, cap, causation, defense control, claim type, provisos, and
cross-references -- plus the mirror-image genuinely-symmetric case for
each opener shape, to confirm the fix doesn't overcorrect into FA."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import indemnification_policy_engine as ie

OPENERS = [
    "Each party shall indemnify the other",
    "Either party shall indemnify the other",
    "Both parties shall indemnify the other",
    "Every party shall indemnify the other",
    "The parties shall indemnify one another",
    "The parties shall mutually indemnify each other",
]

# (dimension_label, asymmetric_tail, symmetric_tail)
DIMENSIONS = [
    (
        "scope_first_third_party",
        "for claims arising under this Agreement; Alpha Holdings's duty extends to Beta Holdings's own first-party losses as well as third-party claims, whereas Beta Holdings's duty is confined strictly to third-party claims.",
        "for claims arising under this Agreement; Alpha Holdings's duty is confined strictly to third-party claims, and Beta Holdings's duty is likewise confined strictly to third-party claims.",
    ),
    (
        "survival",
        "for claims arising under this Agreement; Alpha Holdings's duty carries on with no end date once this Agreement winds down, whereas Beta Holdings's duty ends the moment this Agreement winds down.",
        "for claims arising under this Agreement; Alpha Holdings's duty survives for a period of four years, and Beta Holdings's duty survives for a period of four years as well.",
    ),
    (
        "monetary_cap",
        "for claims arising under this Agreement; Alpha Holdings's liability is capped at $200,000, whereas Beta Holdings's liability carries no cap at all.",
        "for claims arising under this Agreement; Alpha Holdings's liability is capped at $200,000, and Beta Holdings's liability is capped at $200,000 as well.",
    ),
    (
        "causation",
        "for claims traceable to its own conduct; Alpha Holdings is on the hook only where the claim stems from Alpha Holdings's gross negligence, whereas Beta Holdings is on the hook whenever the claim stems from Beta Holdings's ordinary carelessness.",
        "for claims traceable to its own conduct; Alpha Holdings is on the hook only where the claim stems from Alpha Holdings's gross negligence, and Beta Holdings is on the hook only where the claim stems from Beta Holdings's gross negligence as well.",
    ),
    (
        "defense_control",
        "for third-party claims; Alpha Holdings alone decides litigation strategy for any claim against Beta Holdings, whereas Beta Holdings has no input at all into strategy for any claim against Alpha Holdings.",
        "for third-party claims; Alpha Holdings controls the defense of any claim brought against it, and Beta Holdings likewise controls the defense of any claim brought against it.",
    ),
    (
        "claim_category",
        "for claims traceable to its own conduct; Alpha Holdings's duty covers claims alleging fraud, whereas Beta Holdings's duty covers claims alleging data breach only, with no overlap between the two categories.",
        "for claims traceable to its own conduct; Alpha Holdings's duty covers claims alleging fraud, and Beta Holdings's duty covers that same category of claims alleging fraud.",
    ),
    (
        "proviso",
        "for claims arising under this Agreement, save that Alpha Holdings's duty excludes any claim traceable to Beta Holdings's own modification of the deliverable, an exclusion Beta Holdings's duty toward Alpha Holdings does not mirror.",
        "for claims arising under this Agreement, save that each party's duty excludes any claim traceable to the other's own modification of the deliverable, an exclusion applying identically to both.",
    ),
    (
        "cross_reference",
        "for claims arising under this Agreement; the figure binding Alpha Holdings is set out in Schedule 1, and the figure binding Beta Holdings, set out separately in Schedule 2, is a different figure than Schedule 1 states.",
        "for claims arising under this Agreement; the figure binding Alpha Holdings is set out in Schedule 1, and the figure binding Beta Holdings is that same figure set out in Schedule 1.",
    ),
]


def main():
    ie.HYBRID_DISCOVERY_ENABLED = False
    total = 0
    passed = 0
    failed = []
    for opener in OPENERS:
        for dim, asym_tail, sym_tail in DIMENSIONS:
            for label, tail, expect_flagged in ((f"{dim}/asymmetric", asym_tail, True), (f"{dim}/symmetric", sym_tail, False)):
                text = f"{opener} {tail}"
                total += 1
                reasons = ie._detect_reciprocal_asymmetry(text)
                flagged = bool(reasons)
                ok = flagged == expect_flagged
                if ok:
                    passed += 1
                else:
                    failed.append((opener, label, text, expect_flagged, flagged, reasons))
    print(f"PASS: {passed}/{total}")
    for opener, label, text, expect, got, reasons in failed:
        print(f"\nFAIL opener={opener!r} [{label}]")
        print(f"  expected_flagged={expect} got_flagged={got}")
        print(f"  text: {text}")
        print(f"  reasons: {reasons}")


if __name__ == "__main__":
    main()
