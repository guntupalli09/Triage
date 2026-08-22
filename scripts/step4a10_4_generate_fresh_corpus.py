#!/usr/bin/env python3
"""Step 4A.10.4 — genuinely fresh independent validation corpus, built
AFTER code freeze (9df3906). New role names, new differentiation
phrasing throughout for the 12 dimension families -- NOT copied,
paraphrased, or derived from any prior corpus in this program (Step
4A.10, 4A.10.1, 4A.10.2 dev/independent, 4A.10.3 dev/fresh). Unlike
4A.10.3's corpus, this one deliberately weights toward MORE genuinely-
symmetric drafting, including naturally-varied per-role restatements (not
just generic "each party" boilerplate), because the target for this step
is not merely FS=0 -- it is FS=0 while preserving high correct-symmetry
automation."""
import json
from pathlib import Path

ROLES = [
    ("Freight Forwarder", "Shipper"), ("Servicer", "Noteholder"),
    ("Fund Manager", "Limited Partner"), ("Sublicensor", "Sublicensee"),
    ("Prime Contractor", "Subcontractor"), ("Trustee", "Beneficiary"),
    ("Clearing Member", "Exchange"), ("Aggregator", "Originator"),
]

CASES = []
_n = {"i": 0}


def add(tier, label, family, text, note, dims=None):
    _n["i"] += 1
    a, b = ROLES[_n["i"] % len(ROLES)]
    CASES.append({
        "id": f"FRESH104-{_n['i']:04d}", "tier": tier, "label": label, "family": family,
        "dimensions": dims or [], "text": text.format(a=a, b=b), "note": note,
    })


# ---- SYMMETRIC: generic boilerplate (no named roles at all) ----
generic_sym = [
    "Each party shall indemnify the other for third-party claims traceable to its own performance under this Agreement.",
    "Either party shall indemnify and hold harmless the other against claims arising from that party's own breach of this Agreement.",
    "The parties shall mutually indemnify each other for claims traceable to their own respective conduct under this Agreement, with no distinction in treatment between them.",
]
for tpl in generic_sym * 5:
    add("1", "SYMMETRIC", "genuinely_symmetric_generic", tpl, "no named roles -- discovery block never activates")

# ---- SYMMETRIC: named roles, naturally varied restatement (stresses
# established_equal_fn + structural equivalence together) ----
varied_sym = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s indemnification duty carries a five-year tail after this Agreement ends, and {b} likewise remains on the hook for five years after this Agreement ends.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} must give the other prompt written notice of any claim within thirty days, and {b} is bound to the same thirty-day notice requirement.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s exposure is capped at twelve months' fees, while {b}'s exposure likewise does not exceed twelve months' fees.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} controls the defense of any claim brought against it, and {b} retains that same control over any claim brought against it.",
]
for tpl in varied_sym * 6:
    add("2", "SYMMETRIC", "genuinely_symmetric_varied", tpl, "named roles, real established-equal value in varied wording")

# ---- SYMMETRIC: explicit equal-treatment cue ----
cue_sym = [
    "Each party shall indemnify the other for claims arising under this Agreement; the exposure cap set out in Schedule 2 applies equally to {a} and {b}.",
    "Each party shall indemnify the other for claims arising under this Agreement, on the same terms for both {a} and {b}.",
    "Each party's indemnification duty under this Agreement governs {a} and {b} identically.",
]
for tpl in cue_sym * 4:
    add("2", "SYMMETRIC", "genuinely_symmetric_cue", tpl, "explicit drafter statement of equivalence")

# ---- ASYMMETRIC — 12 dimension families, fresh phrasing ----
dim_families = {
    "causation_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} answers for this only where the claim traces to {a}'s reckless disregard, whereas {b} answers for this whenever the claim traces to {b}'s simple inattention.",
    "claim_category": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty runs only to claims alleging a data-privacy violation, whereas {b}'s duty runs to claims of whatever description.",
    "defense_control": "Each party shall indemnify the other for third-party claims; {a} decides unilaterally how any claim against {b} is defended and resolved, whereas {b} has no say at all in how a claim against {a} is defended.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising under this Agreement; {a} answers for no more than six months' fees, whereas {b} answers without any ceiling on the amount.",
    "proviso_exception": "Each party shall indemnify the other for claims arising under this Agreement, except that {a}'s duty leaves out any claim traceable to {b}'s own modification of the deliverable, a carve-out {b}'s duty toward {a} does not mirror.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty does not begin until {b} first exhausts the dispute-resolution steps in Section 14, a precondition {b}'s duty toward {a} is not subject to.",
    "first_third_party": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty covers {b}'s own internal losses in addition to outside claims, whereas {b}'s duty covers only outside claims brought against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} bears this duty even where {a} is not at fault, whereas {b} bears it only upon a showing that {b} was at fault.",
    "scope_geographic": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty follows claims wherever in the world they arise, whereas {b}'s duty follows only claims arising within North America.",
    "cross_reference_schedule": "Each party shall indemnify the other for claims arising under this Agreement; the limit governing {a} is the figure stated in Rider 2, and the limit governing {b}, stated separately in Rider 5, departs from the figure in Rider 2.",
    "temporal_survival": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty persists indefinitely after this Agreement terminates, whereas {b}'s duty lapses the moment this Agreement terminates.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is capped at $250,000, reaches only product-liability claims, and applies regardless of fault, whereas {b}'s duty carries no cap, reaches claims of any kind, and applies only upon a showing of fault.",
}
for dim, tpl in dim_families.items():
    for i, (a, b) in enumerate(ROLES):
        tier = "1" if i < 5 else ("2" if i == 5 else "3")
        add(tier, "ASYMMETRIC", dim, tpl.format(a=a, b=b), f"asymmetric: {dim}", dims=[dim])

# ---- COMPOUND, ~20 ----
compound_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a} maintains its own separate insurance for this same exposure, while {b}'s duty is additionally capped at $60,000, a limit {a}'s duty does not share.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the cap in Section 11; that cap excludes claims caused by {a}'s reckless disregard but excludes no category of claim caused by {b}.",
    "Each party shall indemnify the other for third-party claims; {a}'s duty to advance defense costs as they are incurred runs alongside its main duty, but {b} has no separate cost-advancing duty, only the main duty.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} waives any right of contribution against {b}, but {b} keeps its full right of contribution against {a}.",
]
for i, tpl in enumerate(compound_templates * 5):
    add("3", "ASYMMETRIC", "compound", tpl, "compound multi-provision asymmetry", dims=["compound"])
    if len([c for c in CASES if c["family"] == "compound"]) >= 20:
        break

# ---- AMBIGUOUS, ~20 ----
ambiguous_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; whether {a}'s cap matches {b}'s cap is left to a side letter the parties have not yet executed.",
    "Each party shall indemnify the other for claims arising under this Agreement, on terms the parties intend to finalize in a forthcoming amendment.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is subject to conditions to be set out in a schedule not yet attached to this Agreement.",
]
for i, tpl in enumerate(ambiguous_templates * 7):
    add("2", "AMBIGUOUS", "ambiguous", tpl, "genuinely unresolved, should route to review")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS"]) >= 20:
        break

for c in CASES:
    c["expected_material_dimensions"] = c["dimensions"] if c["label"] == "ASYMMETRIC" else []
    c["severity_if_false_symmetry"] = "S4" if c["label"] == "ASYMMETRIC" else "N/A"

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_4_fresh_independent_corpus.json"
OUT.write_text(json.dumps(CASES, indent=2))
from collections import Counter
print(f"Total: {len(CASES)}")
print(Counter(c["label"] for c in CASES))
print("families (symmetric):", Counter(c["family"] for c in CASES if c["label"] == "SYMMETRIC"))
print("tiers:", Counter(c["tier"] for c in CASES))
fam_counts = Counter()
for c in CASES:
    if c["label"] == "ASYMMETRIC":
        for d in c["dimensions"]:
            fam_counts[d] += 1
print(dict(fam_counts))
