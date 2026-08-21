#!/usr/bin/env python3
"""Step 4A.10.9 — EXPLICITLY NON-AUTHORITATIVE development/adversarial
controls for Role-Name Boundary & Tokenization Generalization. Never to
be treated as a frozen validation corpus. Attacks the specific
constructions the user named: hyphenated multi-word roles, designator
letters/numbers, dotted abbreviations, multi-word roles generally, and
ordinary surrounding nouns/corporate-name shapes that must NOT become
roles."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import indemnification_policy_engine as ie

# (text, expect_flagged, note)
POSITIVE_ROLE_SHAPES = [
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Cross-Border Agent's liability is capped at $120,000, whereas Local Distributor's liability carries no cap at all.",
        True, "hyphenated multi-word role, genuine asymmetry",
    ),
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Cross-Border Agent's liability is capped at $120,000, and Local Distributor's liability is capped at $120,000 as well.",
        False, "hyphenated multi-word role, genuine symmetry",
    ),
    (
        "Each party shall indemnify the other for third-party claims; Sub-Processor controls the defense of any claim brought against it, and Sub-Controller likewise controls the defense of any claim brought against it.",
        False, "hyphenated single-word-pair role, symmetric",
    ),
    (
        "Each party shall indemnify the other for third-party claims; Sub-Processor controls the defense of any claim brought against it, while Sub-Controller has no input at all into the defense of a claim against it.",
        True, "hyphenated single-word-pair role, asymmetric",
    ),
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Tier-1 Supplier's duty survives for a period of five years, and Tier-2 Supplier's duty survives for a period of five years as well.",
        False, "hyphen + digit designator role, symmetric",
    ),
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Tier-1 Supplier's duty carries on with no end date once this Agreement winds down, whereas Tier-2 Supplier's duty ends the moment this Agreement winds down.",
        True, "hyphen + digit designator role, asymmetric",
    ),
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Class B Purchaser's liability is capped at $75,000, and Class A Purchaser's liability is capped at $75,000 as well.",
        False, "space + letter designator role, symmetric",
    ),
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Class B Purchaser's liability is capped at $75,000, whereas Class A Purchaser's liability carries no cap at all.",
        True, "space + letter designator role, asymmetric",
    ),
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Non-U.S. Distributor's liability is capped at $300,000, and Domestic Distributor's liability is capped at $300,000 as well.",
        False, "hyphen + dotted-abbreviation role, symmetric",
    ),
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Non-U.S. Distributor's duty follows claims arising anywhere on the globe, whereas Domestic Distributor's liability carries no cap at all.",
        True, "hyphen + dotted-abbreviation role, asymmetric (different dimensions but a real asymmetry)",
    ),
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Master Services Vendor's liability is capped at $250,000, and Regional Support Partner's liability is capped at $250,000 as well.",
        False, "ordinary 3-word role names (no punctuation), symmetric -- must still work",
    ),
]

# Ordinary prose / document-structure references that must NEVER become
# roles, even though the widened continuation-token set (bare letters,
# digits, dotted abbreviations) now matches them at the regex level --
# the first-word stoplist filter must reject them.
OVER_CAPTURE_GUARDS = [
    "Each party shall indemnify the other for claims arising under this Agreement; the cap for Schedule A is $50,000 and the cap for Schedule B is $50,000 as well.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the limitations set forth in Section 2 and Section 3.",
    "Each party shall indemnify the other for claims arising under this Agreement; the terms in Exhibit A govern, and the terms in Exhibit B govern as well.",
    "Each party shall indemnify the other for claims arising under this Agreement; the ceiling in Annex 1 applies to one direction and the ceiling in Annex 2 applies to the other.",
    # ordinary corporate-name shapes with internal punctuation that
    # should either be treated as a single coherent role (not split) or
    # simply not create a false asymmetry when genuinely symmetric
    "Each party shall indemnify the other for claims arising under this Agreement; Smith & Co.'s liability is capped at $90,000, and Jones & Co.'s liability is capped at $90,000 as well.",
]


def main():
    ie.HYBRID_DISCOVERY_ENABLED = False
    passed = 0
    total = 0
    failed = []
    for text, expect_flagged, note in POSITIVE_ROLE_SHAPES:
        total += 1
        reasons = ie._detect_reciprocal_asymmetry(text)
        flagged = bool(reasons)
        if flagged == expect_flagged:
            passed += 1
        else:
            failed.append((note, text, expect_flagged, flagged, reasons))
    for text in OVER_CAPTURE_GUARDS:
        total += 1
        reasons = ie._detect_reciprocal_asymmetry(text)
        flagged = bool(reasons)
        if not flagged:
            passed += 1
        else:
            failed.append(("over-capture guard", text, False, flagged, reasons))
    print(f"PASS: {passed}/{total}")
    for note, text, expect, got, reasons in failed:
        print(f"\nFAIL [{note}]")
        print(f"  expected_flagged={expect} got_flagged={got}")
        print(f"  text: {text}")
        print(f"  reasons: {reasons}")


if __name__ == "__main__":
    main()
