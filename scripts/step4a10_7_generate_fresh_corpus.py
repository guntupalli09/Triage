#!/usr/bin/env python3
"""Step 4A.10.7 — the AUTHORITATIVE frozen validation corpus for the
reciprocal-opener discovery generalization. Built after code freeze
(commit ddeb93f) and after the discovery fix was exhausted against
non-authoritative dev-replay of all 4 prior corpora (see
artifacts/step4a10_7/design.md). New role names, new phrasing
throughout -- not copied/paraphrased/derived from any prior corpus in
this program. Symmetric cases deliberately weighted toward the
NON-CANONICAL reciprocal-opener phrasings this step specifically
targets (either/both/every quantifiers, "one another," the nominalized
"duty ... binds/applies to/governs" shape), since that is the direct
test of this step's claimed generalization. The symmetry comparator
itself is untouched from Step 4A.10.6, so its own dimension families
are included largely as regression confirmation, not as this step's
primary target. Run EXACTLY ONCE with no further code changes
regardless of outcome."""
import json
from pathlib import Path

ROLES = [
    ("Sponsor Bank", "Program Manager"), ("Content Licensor", "Distribution Partner"),
    ("Terminal Operator", "Cargo Owner"), ("Staffing Agency", "Host Employer"),
    ("Equipment Lessor", "Equipment Lessee"), ("Origination Partner", "Servicing Partner"),
    ("Ticketing Platform", "Event Promoter"), ("Cold Storage Operator", "Shipping Client"),
]

CASES = []
_n = {"i": 0}


def add(tier, label, family, text, note, dims=None):
    _n["i"] += 1
    a, b = ROLES[_n["i"] % len(ROLES)]
    CASES.append({
        "id": f"FRESH107-{_n['i']:04d}", "tier": tier, "label": label, "family": family,
        "dimensions": dims or [], "text": text.format(a=a, b=b), "note": note,
    })


# ---- SYMMETRIC: non-canonical reciprocal-opener phrasing -- THIS
# STEP'S OWN TARGET, no named roles (opener recognition is the thing
# under test, not role attribution) ----
opener_sym = [
    "Either party shall indemnify and hold harmless the other for third-party claims traceable to that party's own conduct under this Agreement.",
    "Both parties shall indemnify the other for claims arising from that party's own breach of this Agreement.",
    "Every party shall indemnify and hold harmless the other for claims traceable to its own performance under this Agreement.",
    "The parties shall indemnify one another for third-party claims traceable to their own respective negligent acts under this Agreement.",
    "Either party's indemnification obligation under this Agreement binds both sides identically.",
    "Both parties' indemnification duty under this Agreement governs each of them identically.",
    "Each party's indemnification obligation under this Agreement applies to both sides on the same footing.",
]
for tpl in opener_sym * 4:
    add("1", "SYMMETRIC", "genuinely_symmetric_opener", tpl, "non-canonical reciprocal opener, this step's own target")

# ---- SYMMETRIC: canonical "each party" boilerplate (regression
# confirmation -- must still work) ----
generic_sym = [
    "Each party shall indemnify the other for third-party claims traceable to its own actions or omissions taken under this Agreement.",
]
for tpl in generic_sym * 8:
    add("1", "SYMMETRIC", "genuinely_symmetric_generic", tpl, "canonical opener, regression confirmation")

# ---- SYMMETRIC: defense-control paraphrase, fresh verbs (regression
# confirmation for the Step 4A.10.6 mechanism, not this step's target)
defense_control_sym = [
    "Each party shall indemnify the other for third-party claims; {a} steers negotiations on any claim brought against it, and {b} likewise steers negotiations on any claim brought against it.",
    "Each party shall indemnify the other for third-party claims; {a} governs the handling of any claim against it, while {b} governs the handling of any claim against it in just the same way.",
]
for tpl in defense_control_sym * 5:
    add("2", "SYMMETRIC", "genuinely_symmetric_defense_control", tpl, "defense-control paraphrase, regression confirmation")

# ---- SYMMETRIC: explicit equal-treatment cue ----
cue_sym = [
    "Each party shall indemnify the other for claims arising under this Agreement; the ceiling in Schedule 7 applies equally to {a} and {b}.",
    "Each party shall indemnify the other for claims arising under this Agreement, on the same terms for {a} and {b} alike.",
]
for tpl in cue_sym * 5:
    add("2", "SYMMETRIC", "genuinely_symmetric_cue", tpl, "explicit drafter statement of equivalence")

# ---- ASYMMETRIC — 12 dimension families, fresh phrasing (regression
# confirmation: the comparator is untouched, these must all still pass)
dim_families = {
    "causation_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s deliberate wrongdoing, whereas {b} is on the hook whenever the claim stems from {b}'s ordinary lapse.",
    "claim_category": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is confined to claims alleging a data-protection violation, whereas {b}'s duty reaches claims of any description whatsoever.",
    "defense_control": "Each party shall indemnify the other for third-party claims; {a} alone commands litigation and settlement strategy for any claim against {b}, whereas {b} has no input at all into strategy for any claim against {a}.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability tops out at three months' worth of fees, whereas {b} faces liability with no ceiling of any kind.",
    "proviso_exception": "Each party shall indemnify the other for claims arising under this Agreement, save that {a}'s duty excludes any claim traceable to {b}'s own unauthorized use of the deliverable, an exclusion {b}'s duty toward {a} does not mirror.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty does not attach unless {b} first exhausts the notice procedure in Section 5, a precondition {b}'s duty toward {a} does not carry.",
    "first_third_party": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty reaches {b}'s own internal losses in addition to outside claims, whereas {b}'s duty reaches only outside claims brought against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} owes this duty even absent any fault on {a}'s part, whereas {b} owes it only once {b}'s own fault is shown.",
    "scope_geographic": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty follows claims arising anywhere on the globe, whereas {b}'s duty is confined to claims arising within Japan.",
    "cross_reference_schedule": "Each party shall indemnify the other for claims arising under this Agreement; the figure binding {a} is set out in Schedule X, and the figure binding {b}, set out separately in Schedule Y, is a different figure than Schedule X states.",
    "temporal_survival": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty carries on with no end date once this Agreement winds down, whereas {b}'s duty ends the moment this Agreement winds down.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is capped at $450,000, reaches only privacy-related claims, and applies strictly, whereas {b}'s duty carries no cap, reaches claims of any kind, and applies only where {b} is at fault.",
}
for dim, tpl in dim_families.items():
    for i, (a, b) in enumerate(ROLES):
        tier = "1" if i < 5 else ("2" if i == 5 else "3")
        add(tier, "ASYMMETRIC", dim, tpl.format(a=a, b=b), f"asymmetric: {dim}", dims=[dim])

# ---- ASYMMETRIC using a non-canonical opener (Either/Both) to confirm
# the discovery generalization doesn't accidentally suppress a real
# asymmetry once discovered ----
opener_asym = [
    "Either party shall indemnify the other for claims arising under this Agreement; {a}'s liability is capped at $150,000, whereas {b}'s liability carries no cap at all.",
    "Both parties shall indemnify the other for claims arising under this Agreement; {a}'s duty covers claims worldwide, whereas {b}'s duty is confined to domestic claims only.",
]
for i, tpl in enumerate(opener_asym * 4):
    a, b = ROLES[i % len(ROLES)]
    add("2", "ASYMMETRIC", "opener_asymmetric", tpl.format(a=a, b=b), "non-canonical opener with real asymmetry -- must still escalate", dims=["monetary_treatment"])
    if len([c for c in CASES if c["family"] == "opener_asymmetric"]) >= 8:
        break

# ---- COMPOUND, ~20 ----
compound_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a} keeps its own standalone insurance covering this exposure, while {b}'s duty is additionally capped at $70,000, a limit {a}'s duty does not carry.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the ceiling in Section 4; that ceiling excludes claims caused by {a}'s deliberate wrongdoing but excludes no category of claim caused by {b}.",
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
    "Either party shall indemnify the other for claims arising under this Agreement, on terms the parties still intend to work out in a future amendment.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is subject to conditions to be set out in an exhibit not yet attached to this Agreement.",
]
for i, tpl in enumerate(ambiguous_templates * 7):
    add("2", "AMBIGUOUS", "ambiguous", tpl, "genuinely unresolved, should route to review")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS"]) >= 20:
        break

for c in CASES:
    c["expected_material_dimensions"] = c["dimensions"] if c["label"] == "ASYMMETRIC" else []
    c["severity_if_false_symmetry"] = "S4" if c["label"] == "ASYMMETRIC" else "N/A"

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_7_fresh_independent_corpus.json"
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
