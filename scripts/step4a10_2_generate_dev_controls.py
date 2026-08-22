#!/usr/bin/env python3
"""Step 4A.10.2 Phase 7 — dedicated positive/negative/ambiguous controls
for the 2 root-cause families (survival/temporal, schedule cross-
reference), locked BEFORE implementation."""
import json
from pathlib import Path

ROLES = [
    ("Vendor", "Client"), ("Contractor", "Owner"), ("Licensee", "Licensor"),
    ("Manufacturer", "Retailer"), ("Broker", "Principal"),
]

CASES = []
_n = {"i": 0}


def add(family, label, text, note):
    _n["i"] += 1
    a, b = ROLES[_n["i"] % len(ROLES)]
    CASES.append({"id": f"DEVCTL-{_n['i']:03d}", "family": family, "label": label,
                   "text": text.format(a=a, b=b), "note": note})


# ===================== SURVIVAL / TEMPORAL FAMILY =====================
survival_asym = [
    "Each party shall indemnify the other for claims arising from this Agreement; provided that {a}'s indemnification obligation survives termination of this Agreement indefinitely, while {b}'s obligation terminates upon expiration of this Agreement.",
    "Each party shall indemnify the other for claims arising from this Agreement; provided that {a}'s obligation survives in perpetuity, whereas {b}'s obligation does not survive termination at all.",
    "Each party shall indemnify the other for claims arising from this Agreement; provided that {a}'s indemnification obligation survives for a period of ten (10) years following termination, while {b}'s obligation survives for a period of two (2) years following termination.",
    "Each party shall indemnify the other for claims arising from this Agreement; {a}'s obligation continues indefinitely after this Agreement ends, but {b}'s obligation ceases immediately upon termination.",
    "Each party's indemnification obligation is ordinarily coextensive with the term of this Agreement; however, {a}'s obligation survives termination indefinitely, and {b}'s does not survive termination at all.",
]
survival_sym = [
    "Each party shall indemnify the other for claims arising from this Agreement; each party's indemnification obligation survives termination of this Agreement for a period of four (4) years, on identical terms.",
    "Each party shall indemnify the other for claims arising from this Agreement; {a}'s indemnification obligation survives termination for a period of three (3) years, and {b}'s obligation survives termination for a period of three (3) years as well.",
    "Each party shall indemnify the other for claims arising from this Agreement; both parties' indemnification obligations survive termination of this Agreement indefinitely.",
    "Each party shall indemnify the other for claims arising from this Agreement; neither party's obligation survives termination of this Agreement.",
    "Each party shall indemnify the other for claims arising from this Agreement, with no stated survival term for either party.",
]
survival_ambiguous = [
    "Each party shall indemnify the other for claims arising from this Agreement; the parties have not yet agreed whether {a}'s obligation will survive termination.",
    "Each party shall indemnify the other for claims arising from this Agreement; survival terms remain subject to future negotiation between {a} and {b}.",
    "Each party shall indemnify the other for claims arising from this Agreement; the survival period, if any, shall be as set forth in an amendment not yet executed.",
]
for t in survival_asym:
    add("survival_temporal", "ASYMMETRIC", t, "survival/temporal asymmetry")
for t in survival_sym:
    add("survival_temporal", "SYMMETRIC", t, "survival/temporal genuinely symmetric")
for t in survival_ambiguous:
    add("survival_temporal", "AMBIGUOUS", t, "survival/temporal unresolved")

# ===================== SCHEDULE CROSS-REFERENCE FAMILY =====================
schedule_asym = [
    "Each party shall indemnify the other for claims arising from this Agreement, subject to the limitations set forth in Schedule 3 for {a} and the different limitations set forth in Schedule 5 for {b}.",
    "Each party shall indemnify the other for claims arising from this Agreement; the exposure cap applicable to {a} is set forth in Exhibit B, while the exposure cap applicable to {b} is set forth in Exhibit C.",
    "Each party's indemnification obligation is subject to the terms of the applicable schedule: Schedule 1 for {a}, Schedule 2 for {b}.",
    "Each party shall indemnify the other for claims arising from this Agreement, as further limited by Appendix A for {a} and Appendix D for {b}.",
    "Each party shall indemnify the other for claims arising from this Agreement; see Annex I for {a}'s specific terms and Annex II for {b}'s specific terms.",
]
schedule_sym = [
    "Each party shall indemnify the other for claims arising from this Agreement, subject to the same limitations set forth in Schedule 3, which applies equally to {a} and {b}.",
    "Each party's indemnification obligation is subject to the terms of Schedule 1, which governs both {a} and {b} identically.",
    "Each party shall indemnify the other for claims arising from this Agreement; the exposure cap applicable to both {a} and {b} is set forth in Exhibit B.",
    "Each party shall indemnify the other for claims arising from this Agreement, with no schedule or exhibit referenced for either party.",
    "Each party shall indemnify the other for claims arising from this Agreement, subject to Schedule 3 for {a} and Schedule 3 for {b} alike.",
]
schedule_ambiguous = [
    "Each party shall indemnify the other for claims arising from this Agreement, subject to the limitations set forth in a schedule to be attached at a later date.",
    "Each party shall indemnify the other for claims arising from this Agreement, subject to Schedule 3, which has not yet been finalized by the parties.",
    "Each party shall indemnify the other for claims arising from this Agreement, subject to the limitations set forth in the applicable schedule (schedule reference to be confirmed).",
]
for t in schedule_asym:
    add("schedule_cross_reference", "ASYMMETRIC", t, "schedule cross-reference asymmetry")
for t in schedule_sym:
    add("schedule_cross_reference", "SYMMETRIC", t, "schedule cross-reference genuinely symmetric")
for t in schedule_ambiguous:
    add("schedule_cross_reference", "AMBIGUOUS", t, "schedule cross-reference unresolved")

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_2_dev_controls.json"
OUT.write_text(json.dumps(CASES, indent=2))
from collections import Counter
print(f"Total: {len(CASES)}")
print(Counter(c["family"] for c in CASES))
print(Counter(c["label"] for c in CASES))
