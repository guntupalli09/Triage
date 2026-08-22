#!/usr/bin/env python3
"""Step 4A.10.5 — genuinely fresh, paraphrase-heavy independent
validation corpus, built AFTER code freeze (ea36114). New role names,
new differentiation AND new paraphrase phrasing throughout -- not
copied/paraphrased/derived from any prior corpus in this program (Step
4A.10 through 4A.10.4, dev or independent). Deliberately weighted with
MORE genuinely-symmetric cases using varied paraphrase across survival/
monetary/defense-control/notice terms specifically, since that is the
risk surface Step 4A.10.5 targets (Step 4A.10.4's FA=18/51 finding)."""
import json
from pathlib import Path

ROLES = [
    ("Custodian", "Depositary"), ("Master Franchisor", "Area Developer"),
    ("General Partner", "Investor"), ("Colocation Provider", "Tenant Operator"),
    ("Data Processor", "Data Controller"), ("Referral Partner", "Merchant"),
    ("Correspondent Bank", "Respondent Bank"), ("Ground Handler", "Carrier"),
]

CASES = []
_n = {"i": 0}


def add(tier, label, family, text, note, dims=None):
    _n["i"] += 1
    a, b = ROLES[_n["i"] % len(ROLES)]
    CASES.append({
        "id": f"FRESH105-{_n['i']:04d}", "tier": tier, "label": label, "family": family,
        "dimensions": dims or [], "text": text.format(a=a, b=b), "note": note,
    })


# ---- SYMMETRIC: generic boilerplate (no named roles) ----
generic_sym = [
    "Each party shall indemnify the other for third-party claims traceable to that party's own performance of this Agreement.",
    "Each party shall indemnify the other for claims arising from that party's own negligent acts or omissions under this Agreement.",
    "The parties shall indemnify each other on a reciprocal basis for claims traceable to their own respective conduct, with no difference in treatment between them.",
]
for tpl in generic_sym * 5:
    add("1", "SYMMETRIC", "genuinely_symmetric_generic", tpl, "no named roles -- discovery block never activates")

# ---- SYMMETRIC: named roles, heavy paraphrase, matching values
# (this is Step 4A.10.5's own target risk surface) ----
paraphrase_sym = [
    # survival paraphrase
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty stays in force for a full three years once this Agreement winds down, and {b} is on the hook for that identical three-year stretch after this Agreement winds down.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} remains answerable for four years past termination, while {b} is equally answerable for four years past termination.",
    # monetary paraphrase
    "Each party shall indemnify the other for claims arising under this Agreement; {a} is on the hook for no more than nine months' worth of fees, and {b}'s exposure likewise tops out at nine months' worth of fees.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s payout ceiling sits at $500,000, and {b} faces that same $500,000 ceiling.",
    # defense-control paraphrase
    "Each party shall indemnify the other for third-party claims; {a} takes charge of defending and settling any claim brought against it, and {b} likewise takes charge of defending and settling any claim brought against it.",
    "Each party shall indemnify the other for third-party claims; {a} directs the handling of any claim asserted against it, while {b} directs the handling of any claim asserted against it in just the same way.",
    # notice-period paraphrase (no dedicated dimension field -- tests
    # whether the structural check tolerates ordinary connector variation
    # even with NOTHING established, as long as no continuation/cue signal differentiates)
    "Each party shall indemnify the other for claims arising under this Agreement; {a} must alert the other in writing within fifteen days of learning of a claim, and {b} is under that same fifteen-day written-notice obligation.",
]
for tpl in paraphrase_sym * 5:
    add("2", "SYMMETRIC", "genuinely_symmetric_paraphrase", tpl, "named roles, real matching value stated with heavy paraphrase")

# ---- SYMMETRIC: explicit equal-treatment cue, varied determiners ----
cue_sym = [
    "Each party shall indemnify the other for claims arising under this Agreement; the ceiling in Schedule 4 applies equally to {a} and {b}.",
    "Each party shall indemnify the other for claims arising under this Agreement, on the same terms for {a} and {b} alike.",
    "Each party's indemnification duty under this Agreement binds {a} and {b} identically.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} bears a duty to cooperate with the defense, and {b} bears that same duty to cooperate with the defense.",
]
for tpl in cue_sym * 4:
    add("2", "SYMMETRIC", "genuinely_symmetric_cue", tpl, "explicit drafter statement of equivalence, varied determiners")

# ---- ASYMMETRIC — 12 dimension families, fresh phrasing ----
dim_families = {
    "causation_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s intentional misconduct, whereas {b} is on the hook whenever the claim stems from {b}'s mere carelessness.",
    "claim_category": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is confined to claims alleging trade-secret misappropriation, whereas {b}'s duty reaches claims of any description whatsoever.",
    "defense_control": "Each party shall indemnify the other for third-party claims; {a} alone decides litigation and settlement strategy for any claim against {b}, whereas {b} has no voice at all in strategy for any claim against {a}.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability tops out at four months' worth of fees, whereas {b} faces liability with no ceiling of any kind.",
    "proviso_exception": "Each party shall indemnify the other for claims arising under this Agreement, save that {a}'s duty excludes any claim traceable to {b}'s own unauthorized use of the deliverable, an exclusion {b}'s duty toward {a} does not mirror.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty does not attach unless {b} first complies with the escalation procedure in Section 9, a precondition {b}'s duty toward {a} does not carry.",
    "first_third_party": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty reaches {b}'s own direct losses in addition to outside claims, whereas {b}'s duty reaches only outside claims brought against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} owes this duty even absent any fault on {a}'s part, whereas {b} owes it only once {b}'s own fault is established.",
    "scope_geographic": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty follows claims arising anywhere on the globe, whereas {b}'s duty is confined to claims arising within the United Kingdom.",
    "cross_reference_schedule": "Each party shall indemnify the other for claims arising under this Agreement; the figure binding {a} is set out in Annex C, and the figure binding {b}, set out separately in Annex D, is a different figure than Annex C states.",
    "temporal_survival": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty carries on with no end date once this Agreement winds down, whereas {b}'s duty ends the moment this Agreement winds down.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is capped at $300,000, reaches only IP-infringement claims, and applies strictly, whereas {b}'s duty carries no cap, reaches claims of any kind, and applies only where {b} is at fault.",
}
for dim, tpl in dim_families.items():
    for i, (a, b) in enumerate(ROLES):
        tier = "1" if i < 5 else ("2" if i == 5 else "3")
        add(tier, "ASYMMETRIC", dim, tpl.format(a=a, b=b), f"asymmetric: {dim}", dims=[dim])

# ---- COMPOUND, ~20 ----
compound_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a} keeps its own standalone cyber-risk policy covering this exposure, while {b}'s duty is additionally capped at $90,000, a limit {a}'s duty does not carry.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the ceiling in Section 8; that ceiling excludes claims caused by {a}'s intentional misconduct but excludes no category of claim caused by {b}.",
    "Each party shall indemnify the other for third-party claims; {a}'s duty to front defense costs as incurred runs alongside its main duty, but {b} carries no separate cost-fronting duty, only the main duty.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} relinquishes any right of contribution against {b}, but {b} retains its full right of contribution against {a}.",
]
for i, tpl in enumerate(compound_templates * 5):
    add("3", "ASYMMETRIC", "compound", tpl, "compound multi-provision asymmetry", dims=["compound"])
    if len([c for c in CASES if c["family"] == "compound"]) >= 20:
        break

# ---- AMBIGUOUS, ~20 ----
ambiguous_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; whether {a}'s ceiling matches {b}'s ceiling is left for a side agreement the parties have not yet signed.",
    "Each party shall indemnify the other for claims arising under this Agreement, on terms the parties expect to finalize in a later amendment.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is subject to conditions to be set out in an exhibit not yet attached to this Agreement.",
]
for i, tpl in enumerate(ambiguous_templates * 7):
    add("2", "AMBIGUOUS", "ambiguous", tpl, "genuinely unresolved, should route to review")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS"]) >= 20:
        break

for c in CASES:
    c["expected_material_dimensions"] = c["dimensions"] if c["label"] == "ASYMMETRIC" else []
    c["severity_if_false_symmetry"] = "S4" if c["label"] == "ASYMMETRIC" else "N/A"

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_5_fresh_independent_corpus.json"
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
