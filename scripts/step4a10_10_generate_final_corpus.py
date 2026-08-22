#!/usr/bin/env python3
"""Step 4A.10.10 — the FINAL, comprehensive frozen validation corpus for
the pre-ship stabilization pass. Built after code freeze (commit
a9a8615) and after full regression + dev-replay of all 7 prior corpora
confirmed clean (see artifacts/step4a10_10/design.md). Deliberately
broad-spectrum rather than another narrow family drill: samples the
standard 12 dimension families, defense-control paraphrase, reciprocal-
opener variety, every role-name construction class this program has
tackled (including the exact abbreviation-first-token shape that failed
in Step 4A.10.9), the equal-treatment cue, the new cardinality
fail-closed guard, over-capture guards, compound, and ambiguous cases.
New role vocabulary throughout -- not copied/paraphrased/derived from
any prior corpus in this program. Run EXACTLY ONCE with no further code
changes regardless of outcome."""
import json
from pathlib import Path

STANDARD_ROLES = [
    ("Bond Trustee", "Bond Issuer"), ("Anchor Investor", "Co-Investor"),
    ("Import Agent", "Export Agent"), ("Field Technician", "Dispatch Center"),
    ("Tier-4 Contractor", "Tier-5 Contractor"), ("Class M Shareholder", "Class N Shareholder"),
    ("Hargrove & Sons", "Whitfield & Co"), ("U.S. Reseller", "Non-U.S. Reseller"),
]

CASES = []
_n = {"i": 0}


def add(tier, label, family, text, note, dims=None):
    _n["i"] += 1
    CASES.append({
        "id": f"FRESH1010-{_n['i']:04d}", "tier": tier, "label": label, "family": family,
        "dimensions": dims or [], "text": text, "note": note,
    })


# ---- Standard 12 dimension families, fresh phrasing (core safety
# regression -- must all remain CA) ----
dim_families = {
    "causation_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s reckless disregard, whereas {b} is on the hook whenever the claim stems from {b}'s plain inattention.",
    "claim_category": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is confined to claims alleging false advertising, whereas {b}'s duty reaches claims of any description whatsoever.",
    "defense_control": "Each party shall indemnify the other for third-party claims; {a} alone decides litigation and settlement strategy for any claim against {b}, whereas {b} has no input at all into strategy for any claim against {a}.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability tops out at $270,000, whereas {b} faces liability with no ceiling of any kind.",
    "proviso_exception": "Each party shall indemnify the other for claims arising under this Agreement, save that {a}'s duty excludes any claim traceable to {b}'s own unauthorized use of the deliverable, an exclusion {b}'s duty toward {a} does not mirror.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty does not attach unless {b} first exhausts the escalation steps in Section 9, a precondition {b}'s duty toward {a} does not carry.",
    "first_third_party": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty reaches {b}'s own internal losses in addition to outside claims, whereas {b}'s duty reaches only outside claims brought against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} owes this duty even absent any fault on {a}'s part, whereas {b} owes it only once {b}'s own fault is shown.",
    "scope_geographic": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty follows claims arising anywhere on the globe, whereas {b}'s duty is confined to claims arising within Sweden.",
    "cross_reference_schedule": "Each party shall indemnify the other for claims arising under this Agreement; the figure binding {a} is set out in Rider X, and the figure binding {b}, set out separately in Rider Y, is a different figure than Rider X states.",
    "temporal_survival": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty carries on with no end date once this Agreement winds down, whereas {b}'s duty ends the moment this Agreement winds down.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is capped at $410,000, reaches only false-advertising claims, and applies strictly, whereas {b}'s duty carries no cap, reaches claims of any kind, and applies only where {b} is at fault.",
}
for dim, tpl in dim_families.items():
    for i, (a, b) in enumerate(STANDARD_ROLES):
        tier = "1" if i < 5 else ("2" if i == 5 else "3")
        add(tier, "ASYMMETRIC", dim, tpl.format(a=a, b=b), f"asymmetric: {dim}", dims=[dim])

# ---- Compound ----
compound_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a} keeps its own standalone insurance covering this exposure, while {b}'s duty is additionally capped at $55,000, a limit {a}'s duty does not carry.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the ceiling in Section 12; that ceiling excludes claims caused by {a}'s reckless disregard but excludes no category of claim caused by {b}.",
    "Each party shall indemnify the other for third-party claims; {a}'s duty to front defense costs as incurred runs alongside its main duty, but {b} carries no separate cost-fronting duty, only the main duty.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} relinquishes any right of contribution against {b}, but {b} retains its full right of contribution against {a}.",
]
for i, tpl in enumerate(compound_templates * 3):
    a, b = STANDARD_ROLES[i % len(STANDARD_ROLES)]
    add("3", "ASYMMETRIC", "compound", tpl.format(a=a, b=b), "compound multi-provision asymmetry", dims=["compound"])
    if len([c for c in CASES if c["family"] == "compound"]) >= 12:
        break

# ---- Defense-control paraphrase, fresh verbs (regression) ----
defense_control_sym = [
    "Each party shall indemnify the other for third-party claims; {a} anchors the response to any claim brought against it, and {b} likewise anchors the response to any claim brought against it.",
]
for i, tpl in enumerate(defense_control_sym * 6):
    a, b = STANDARD_ROLES[i % len(STANDARD_ROLES)]
    add("2", "SYMMETRIC", "genuinely_symmetric_defense_control", tpl.format(a=a, b=b), "defense-control paraphrase, fresh verb regression")

# ---- Reciprocal-opener variety (regression) ----
opener_sym = [
    "Each party shall indemnify the other for third-party claims traceable to that party's own dealings under this Agreement.",
    "Either party shall indemnify and hold harmless the other against claims traceable to a breach of this Agreement by that party.",
    "Both parties shall indemnify and hold harmless the other against third-party claims traceable to this Agreement's performance.",
    "The parties shall indemnify one another for claims traceable to each party's own respective misconduct under this Agreement.",
    "Every party shall indemnify and hold harmless the other for claims traceable to how it carried out this Agreement.",
    "Both parties' indemnification obligation under this Agreement applies to each of them on an identical footing.",
]
for tpl in opener_sym * 2:
    add("1", "SYMMETRIC", "genuinely_symmetric_opener", tpl, "reciprocal-opener variety regression, no named roles")

# ---- Role-construction shapes x dimensions (this step's own target,
# including the EXACT abbreviation-first-token shape that failed) ----
CONSTRUCTION_ROLES = [
    ("U.S. Reseller", "Non-U.S. Reseller"),   # abbreviation-first -- the exact failed shape
    ("Tier-4 Contractor", "Tier-5 Contractor"),  # hyphen + digit designator
    ("Class M Shareholder", "Class N Shareholder"),  # space + letter designator
    ("Hargrove & Sons", "Whitfield & Co"),     # ampersand-joined
]
role_dim_templates = {
    "monetary_cap": (
        "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability is capped at $195,000, whereas {b}'s liability carries no cap at all.",
        "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability is capped at $195,000, and {b}'s liability is capped at $195,000 as well.",
    ),
    "survival": (
        "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty carries on with no end date once this Agreement winds down, whereas {b}'s duty ends the moment this Agreement winds down.",
        "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty survives for a period of four years, and {b}'s duty survives for a period of four years as well.",
    ),
}
for a, b in CONSTRUCTION_ROLES:
    for dim, (asym_tpl, sym_tpl) in role_dim_templates.items():
        add("1", "ASYMMETRIC", f"role_shape_x_{dim}", asym_tpl.format(a=a, b=b), f"{a}/{b} x {dim}, asymmetric", dims=[dim])
        add("1", "SYMMETRIC", f"role_shape_x_{dim}", sym_tpl.format(a=a, b=b), f"{a}/{b} x {dim}, symmetric")

# ---- Cardinality fail-closed guard stress: role shapes the tokenizer
# STILL doesn't handle (must route to review, never silently pass) ----
cardinality_stress = [
    "Each party shall indemnify the other for claims arising under this Agreement; O'Malley Holdings's liability is capped at $80,000, whereas O'Malley Holdings's liability carries no cap at all.",
    "Each party shall indemnify the other for claims arising under this Agreement; D'Angelo Trading's duty survives for a period of two years, and D'Angelo Trading's duty survives for a period of two years as well.",
]
for tpl in cardinality_stress * 2:
    add("2", "AMBIGUOUS", "cardinality_guard_stress", tpl, "role shape the tokenizer cannot distinguish -- must route to review, not silently pass")

# ---- Over-capture guards ----
over_capture = [
    "Each party shall indemnify the other for claims arising under this Agreement; the cap for Schedule A is $40,000 and the cap for Schedule B is $40,000 as well.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the limitations set forth in Section 6 and Section 7.",
    "Each party shall indemnify the other for claims arising under this Agreement; the terms in Exhibit E govern one direction, and the terms in Exhibit F govern the other.",
]
for tpl in over_capture * 2:
    add("1", "SYMMETRIC", "over_capture_guard", tpl, "document-structure reference must not become a role")

# ---- Equal-treatment cue (regression) ----
cue_sym = [
    "Each party shall indemnify the other for claims arising under this Agreement; the ceiling in Schedule 8 applies equally to Bond Trustee and Bond Issuer.",
    "Each party shall indemnify the other for claims arising under this Agreement, on the same terms for Anchor Investor and Co-Investor alike.",
]
for tpl in cue_sym * 3:
    add("2", "SYMMETRIC", "genuinely_symmetric_cue", tpl, "explicit drafter statement of equivalence")

# ---- AMBIGUOUS ----
ambiguous_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; whether {a}'s ceiling matches {b}'s ceiling is left for a side letter the parties have not yet signed.",
    "Either party shall indemnify the other for claims arising under this Agreement, on terms the parties expect to hammer out in a subsequent side letter.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is subject to conditions to be set out in an exhibit not yet attached to this Agreement.",
]
for i, tpl in enumerate(ambiguous_templates * 4):
    a, b = STANDARD_ROLES[i % len(STANDARD_ROLES)]
    add("2", "AMBIGUOUS", "ambiguous", tpl.format(a=a, b=b), "genuinely unresolved, should route to review")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS" and c["family"] == "ambiguous"]) >= 12:
        break

for c in CASES:
    c["expected_material_dimensions"] = c["dimensions"] if c["label"] == "ASYMMETRIC" else []
    c["severity_if_false_symmetry"] = "S4" if c["label"] == "ASYMMETRIC" else "N/A"

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_10_final_validation_corpus.json"
OUT.write_text(json.dumps(CASES, indent=2))
from collections import Counter
print(f"Total: {len(CASES)}")
print(Counter(c["label"] for c in CASES))
print("families:", Counter(c["family"] for c in CASES))
print("tiers:", Counter(c["tier"] for c in CASES))
