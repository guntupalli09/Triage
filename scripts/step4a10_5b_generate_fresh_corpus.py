#!/usr/bin/env python3
"""Step 4A.10.5 (relock, "5b") — the AUTHORITATIVE validation corpus for
this step. Built after the process-violation disclosure at commit
7d62915 and the code freeze that follows it. New role names, new
phrasing throughout -- not copied/paraphrased/derived from any prior
corpus in this program, including the burned 202-case Step 4A.10.5
corpus whose results are no longer independent validation evidence (see
artifacts/step4a10_5/process_violation_note.md). This corpus will be
run EXACTLY ONCE with no further code changes regardless of outcome."""
import json
from pathlib import Path

ROLES = [
    ("Paying Agent", "Bondholder"), ("Managing Member", "Non-Managing Member"),
    ("Consignee", "Consignor Bank"), ("Reseller", "Platform Operator"),
    ("Franchise Broker", "Prospective Franchisee"), ("Loan Servicer", "Loan Originator"),
    ("Ground Lessee", "Ground Lessor"), ("Ceding Broker", "Fronting Insurer"),
]

CASES = []
_n = {"i": 0}


def add(tier, label, family, text, note, dims=None):
    _n["i"] += 1
    a, b = ROLES[_n["i"] % len(ROLES)]
    CASES.append({
        "id": f"FRESH105B-{_n['i']:04d}", "tier": tier, "label": label, "family": family,
        "dimensions": dims or [], "text": text.format(a=a, b=b), "note": note,
    })


# ---- SYMMETRIC: generic boilerplate (no named roles) ----
generic_sym = [
    "Each party shall indemnify the other for third-party claims traceable to that party's own conduct in performing this Agreement.",
    "Each party shall indemnify the other for claims arising out of that party's own breach of this Agreement.",
    "The parties shall indemnify one another reciprocally for claims traceable to their own respective acts, with no distinction in how either is treated.",
]
for tpl in generic_sym * 5:
    add("1", "SYMMETRIC", "genuinely_symmetric_generic", tpl, "no named roles -- discovery block never activates")

# ---- SYMMETRIC: named roles, heavy paraphrase, matching values ----
paraphrase_sym = [
    # survival paraphrase (varied determiners/verbs, some with "past
    # termination"/"answerable" phrasing already generalized, some using
    # yet different fresh wording to test whether the fix holds beyond
    # its own exact trigger phrases)
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty runs on for six years once this Agreement ends, and {b} stays on the hook for that same six-year run once this Agreement ends.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} remains answerable for two years past termination, while {b} is equally answerable for two years past termination.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty does not lapse until three years after this Agreement terminates, and {b}'s duty does not lapse until that same three years after this Agreement terminates.",
    # monetary paraphrase
    "Each party shall indemnify the other for claims arising under this Agreement; {a} is on the hook for no more than seven months' worth of fees, and {b}'s exposure likewise tops out at seven months' worth of fees.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s payout ceiling sits at $750,000, and {b} faces that same $750,000 ceiling.",
    # defense-control paraphrase (fresh verb choices beyond "takes
    # charge of"/"directs the handling of")
    "Each party shall indemnify the other for third-party claims; {a} runs point on defending and resolving any claim brought against it, and {b} likewise runs point on defending and resolving any claim brought against it.",
    "Each party shall indemnify the other for third-party claims; {a} steers the response to any claim filed against it, while {b} steers the response to any claim filed against it in just the same way.",
    # notice-period paraphrase
    "Each party shall indemnify the other for claims arising under this Agreement; {a} must flag the other in writing within twenty days of learning of a claim, and {b} is under that same twenty-day written-notice duty.",
]
for tpl in paraphrase_sym * 5:
    add("2", "SYMMETRIC", "genuinely_symmetric_paraphrase", tpl, "named roles, real matching value stated with heavy paraphrase")

# ---- SYMMETRIC: explicit equal-treatment cue, varied determiners ----
cue_sym = [
    "Each party shall indemnify the other for claims arising under this Agreement; the ceiling in Schedule 6 applies equally to {a} and {b}.",
    "Each party shall indemnify the other for claims arising under this Agreement, on the same terms for {a} and {b} alike.",
    "Each party's indemnification duty under this Agreement binds {a} and {b} identically.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} owes a duty to cooperate with the defense, and {b} owes that same duty to cooperate with the defense.",
]
for tpl in cue_sym * 4:
    add("2", "SYMMETRIC", "genuinely_symmetric_cue", tpl, "explicit drafter statement of equivalence, varied determiners")

# ---- ASYMMETRIC — 12 dimension families, fresh phrasing ----
dim_families = {
    "causation_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s deliberate misconduct, whereas {b} is on the hook whenever the claim stems from {b}'s ordinary inattention.",
    "claim_category": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is confined to claims alleging a securities-law violation, whereas {b}'s duty reaches claims of any description whatsoever.",
    "defense_control": "Each party shall indemnify the other for third-party claims; {a} alone sets litigation and settlement strategy for any claim against {b}, whereas {b} has no input at all into strategy for any claim against {a}.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability tops out at five months' worth of fees, whereas {b} faces liability with no ceiling of any kind.",
    "proviso_exception": "Each party shall indemnify the other for claims arising under this Agreement, save that {a}'s duty excludes any claim traceable to {b}'s own unauthorized alteration of the deliverable, an exclusion {b}'s duty toward {a} does not mirror.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty does not attach unless {b} first exhausts the notice-and-cure procedure in Section 7, a precondition {b}'s duty toward {a} does not carry.",
    "first_third_party": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty reaches {b}'s own internal losses in addition to outside claims, whereas {b}'s duty reaches only outside claims brought against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} owes this duty even absent any fault on {a}'s part, whereas {b} owes it only once {b}'s own fault is shown.",
    "scope_geographic": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty follows claims arising anywhere in the world, whereas {b}'s duty is confined to claims arising within Canada.",
    "cross_reference_schedule": "Each party shall indemnify the other for claims arising under this Agreement; the figure binding {a} is set out in Rider A, and the figure binding {b}, set out separately in Rider B, is a different figure than Rider A states.",
    "temporal_survival": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty carries on with no end date once this Agreement winds down, whereas {b}'s duty ends the moment this Agreement winds down.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is capped at $200,000, reaches only regulatory-penalty claims, and applies strictly, whereas {b}'s duty carries no cap, reaches claims of any kind, and applies only where {b} is at fault.",
}
for dim, tpl in dim_families.items():
    for i, (a, b) in enumerate(ROLES):
        tier = "1" if i < 5 else ("2" if i == 5 else "3")
        add(tier, "ASYMMETRIC", dim, tpl.format(a=a, b=b), f"asymmetric: {dim}", dims=[dim])

# ---- COMPOUND, ~20 ----
compound_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a} keeps its own standalone insurance covering this exposure, while {b}'s duty is additionally capped at $85,000, a limit {a}'s duty does not carry.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the ceiling in Section 6; that ceiling excludes claims caused by {a}'s deliberate misconduct but excludes no category of claim caused by {b}.",
    "Each party shall indemnify the other for third-party claims; {a}'s duty to front defense costs as incurred runs alongside its main duty, but {b} carries no separate cost-fronting duty, only the main duty.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} relinquishes any right of contribution against {b}, but {b} retains its full right of contribution against {a}.",
]
for i, tpl in enumerate(compound_templates * 5):
    add("3", "ASYMMETRIC", "compound", tpl, "compound multi-provision asymmetry", dims=["compound"])
    if len([c for c in CASES if c["family"] == "compound"]) >= 20:
        break

# ---- AMBIGUOUS, ~20 ----
ambiguous_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; whether {a}'s ceiling matches {b}'s ceiling is left for a side letter the parties have not yet signed.",
    "Each party shall indemnify the other for claims arising under this Agreement, on terms the parties still intend to work out in a future side letter.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is subject to conditions to be set out in an exhibit not yet attached to this Agreement.",
]
for i, tpl in enumerate(ambiguous_templates * 7):
    add("2", "AMBIGUOUS", "ambiguous", tpl, "genuinely unresolved, should route to review")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS"]) >= 20:
        break

for c in CASES:
    c["expected_material_dimensions"] = c["dimensions"] if c["label"] == "ASYMMETRIC" else []
    c["severity_if_false_symmetry"] = "S4" if c["label"] == "ASYMMETRIC" else "N/A"

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_5b_fresh_independent_corpus.json"
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
