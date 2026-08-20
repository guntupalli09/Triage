#!/usr/bin/env python3
"""Step 4A.10.1 Phase 6 — false-symmetry benchmark, locked before any
symmetry-logic changes. Indemnification-focused (per the task's own
observation that historical failures concentrated there); liability/
payment_terms symmetry not covered this pass -- disclosed scope
reduction, not hidden."""
import json
from pathlib import Path

ROLES = [
    ("Vendor", "Client"), ("Contractor", "Owner"), ("Licensee", "Licensor"),
    ("Servicer", "Bank"), ("Supplier", "Purchaser"), ("Distributor", "Brand Owner"),
]

CASES = []
_n = {"i": 0}


def add(family, label, text, note):
    _n["i"] += 1
    a, b = ROLES[_n["i"] % len(ROLES)]
    CASES.append({
        "id": f"SYM-{_n['i']:03d}",
        "family": family,
        "label": label,  # SYMMETRIC / ASYMMETRIC / AMBIGUOUS
        "dimension": family,
        "text": text.format(a=a, b=b),
        "note": note,
    })


# ---- 40 genuinely symmetric ----
symmetric_templates = [
    "Each party shall indemnify, defend, and hold harmless the other party from and against any claim arising out of the indemnifying party's breach of this Agreement.",
    "Each of {a} and {b} shall indemnify the other for third-party claims arising from its own negligent acts, on identical terms.",
    "{a} and {b} shall each indemnify the other party for claims arising from their respective breaches of this Agreement, subject to the same $1,000,000 cap applicable to both parties.",
    "Each party shall defend, indemnify, and hold harmless the other from claims of gross negligence or willful misconduct, with identical notice and cooperation obligations applying to both.",
    "The parties shall mutually indemnify each other for third-party claims arising from their own performance under this Agreement, on the same terms and subject to the same defense-control provisions.",
    "Each party shall indemnify the other for claims arising from a breach of confidentiality, with both parties bearing identical defense obligations and no monetary cap applicable to either.",
]
for i, tpl in enumerate(symmetric_templates * 7):
    add("genuinely_symmetric", "SYMMETRIC", tpl, "genuinely reciprocal, no material asymmetry")
    if len([c for c in CASES if c["label"] == "SYMMETRIC"]) >= 40:
        break

# ---- 60 asymmetric, 12 dimensions x 5 ----
dim_templates = {
    "causation_standard": "Each party shall indemnify the other for claims arising from its own conduct; provided that {a}'s obligation applies only to claims arising from {a}'s gross negligence or willful misconduct, while {b}'s obligation applies to claims arising from {b}'s ordinary negligence.",
    "claim_category": "Each party shall indemnify the other for claims arising from this Agreement; provided that {a}'s indemnification obligation covers only intellectual-property infringement claims, while {b}'s obligation covers all third-party claims of any kind.",
    "defense_control": "Each party shall indemnify the other for third-party claims; provided that {a} shall control the defense of any claim against {b}, while {b} has no right to control the defense of any claim against {a}.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising from this Agreement; provided that {a}'s indemnification obligation is capped at the fees paid in the prior twelve months, while {b}'s indemnification obligation is uncapped.",
    "exception_proviso": "Each party shall indemnify the other for claims arising from this Agreement, except that {a}'s obligation does not apply to claims arising from {b}'s own modification of the deliverables, a carve-out that does not apply to {b}'s obligation to {a}.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising from this Agreement; provided, however, that {a}'s obligation is conditioned on {b} first exhausting its remedies under Section 6, a condition that does not apply to {b}'s obligation to {a}.",
    "first_third_party": "Each party shall indemnify the other for claims arising from this Agreement; provided that {a}'s obligation extends to first-party losses {b} incurs directly, while {b}'s obligation covers only third-party claims asserted against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims arising from its own acts; provided that {a} is liable for indemnification regardless of fault, while {b} is liable only upon a showing of negligence.",
    "scope_difference": "Each party shall indemnify the other for claims arising from this Agreement; provided that {a}'s obligation covers claims arising anywhere in the world, while {b}'s obligation covers only claims arising within the United States.",
    "cross_reference": "Each party shall indemnify the other for claims arising from this Agreement, subject to the limitations set forth in Schedule 3 for {a} and the different limitations set forth in Schedule 5 for {b}.",
    "temporal_survival": "Each party shall indemnify the other for claims arising from this Agreement; provided that {a}'s indemnification obligation survives termination of this Agreement indefinitely, while {b}'s obligation terminates upon expiration of this Agreement.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising from this Agreement; provided that {a}'s obligation is capped at $500,000 and covers only IP claims arising from {a}'s gross negligence, while {b}'s obligation is uncapped and covers all claims arising from {b}'s ordinary negligence.",
}
for dim, tpl in dim_templates.items():
    for i, (a, b) in enumerate(ROLES):
        add(dim, "ASYMMETRIC", tpl.format(a=a, b=b), f"asymmetric dimension: {dim}")

# ---- 20 ambiguous / SHOULD_REVIEW ----
ambiguous_templates = [
    "Each party shall indemnify the other for claims arising from this Agreement; the parties acknowledge that the precise scope of the indemnification obligation for {a} remains a matter to be determined by future amendment.",
    "The parties shall mutually indemnify each other, provided that the exact allocation of defense costs between {a} and {b} has not yet been agreed and remains subject to further negotiation.",
    "Each party shall indemnify the other for claims of the type described in Schedule 9, which schedule is referenced but not attached to this Agreement.",
    "Each party shall indemnify the other for claims arising from this Agreement, except as the parties may otherwise agree in a side letter not included in this Agreement.",
    "Each of {a} and {b} shall indemnify the other, subject to terms to be mutually agreed and set forth in a future amendment to this Agreement.",
]
for i, tpl in enumerate(ambiguous_templates * 4):
    add("ambiguous", "AMBIGUOUS", tpl, "genuinely ambiguous, should route to review regardless of symmetry claim")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS"]) >= 20:
        break

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_1_symmetry_benchmark.json"
OUT.write_text(json.dumps(CASES, indent=2))
from collections import Counter
print(f"Total: {len(CASES)}")
print(Counter(c["label"] for c in CASES))
print(Counter(c["family"] for c in CASES))
