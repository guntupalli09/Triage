#!/usr/bin/env python3
"""Step 4A.10.9 — the AUTHORITATIVE frozen validation corpus for role-
name boundary & tokenization generalization. Built after code freeze
(commit 4d9a15e) and after the fix was exhausted against non-
authoritative dev/adversarial material only (see
scripts/step4a10_9_dev_adversarial_controls.py and the dev-replay of
all 6 prior corpora). New role names and phrasing throughout -- not
copied/paraphrased/derived from any prior corpus in this program,
including the dev-adversarial names. Heavily weighted toward the exact
construction CLASSES the user named (hyphenated multi-word, hyphen +
digit designator, space + letter designator, dotted abbreviation,
ampersand-joined) crossed with tracked dimensions, in both asymmetric
and symmetric form, plus over-capture guards (document-structure
references that must never become roles). Run EXACTLY ONCE with no
further code changes regardless of outcome."""
import json
from pathlib import Path

# Role-name construction classes, each a (role_a, role_b) pair using a
# DIFFERENT unseen punctuation/designator shape than any prior corpus.
ROLE_CONSTRUCTIONS = [
    ("Post-Closing Buyer", "Pre-Closing Seller"),      # hyphenated multi-word
    ("Co-Manufacturer", "Brand Owner"),                 # hyphenated single-word pair
    ("Tier-2 Vendor", "Tier-3 Vendor"),                 # hyphen + digit designator
    ("Series C Investor", "Series D Investor"),         # space + letter designator
    ("U.K. Distributor", "U.S. Distributor"),           # dotted abbreviation
    ("Smith & Daughters", "Cole & Associates"),         # ampersand-joined
    ("Sub-Licensee", "Master Licensee"),                # hyphenated single-word pair (2nd)
    ("Class X Shareholder", "Class Y Shareholder"),     # space + letter designator (2nd)
]
# Ordinary multi-word roles with no special punctuation, for regression.
PLAIN_ROLES = [
    ("Regional Fulfillment Partner", "Central Logistics Hub"),
    ("National Accounts Manager", "Field Sales Representative"),
]

CASES = []
_n = {"i": 0}


def add(tier, label, family, text, note, dims=None):
    _n["i"] += 1
    CASES.append({
        "id": f"FRESH109-{_n['i']:04d}", "tier": tier, "label": label, "family": family,
        "dimensions": dims or [], "text": text, "note": note,
    })


# ---- Role-construction x dimension matrix -- THIS STEP'S OWN TARGET.
# Each construction class crossed with tracked dimensions (survival,
# monetary, defense control), both symmetric and asymmetric. ----
DIM_TEMPLATES = {
    "survival": (
        "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty carries on with no end date once this Agreement winds down, whereas {b}'s duty ends the moment this Agreement winds down.",
        "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty survives for a period of five years, and {b}'s duty survives for a period of five years as well.",
    ),
    "monetary_cap": (
        "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability is capped at $220,000, whereas {b}'s liability carries no cap at all.",
        "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability is capped at $220,000, and {b}'s liability is capped at $220,000 as well.",
    ),
    "defense_control": (
        "Each party shall indemnify the other for third-party claims; {a} alone decides litigation strategy for any claim against {b}, whereas {b} has no input at all into strategy for any claim against {a}.",
        "Each party shall indemnify the other for third-party claims; {a} controls the defense of any claim brought against it, and {b} likewise controls the defense of any claim brought against it.",
    ),
    "causation": (
        "Each party shall indemnify the other for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s gross negligence, whereas {b} is on the hook whenever the claim stems from {b}'s ordinary carelessness.",
        "Each party shall indemnify the other for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s gross negligence, and {b} is on the hook only where the claim stems from {b}'s gross negligence as well.",
    ),
}
for a, b in ROLE_CONSTRUCTIONS:
    for dim, (asym_tpl, sym_tpl) in DIM_TEMPLATES.items():
        add("1", "ASYMMETRIC", f"role_construction_x_{dim}", asym_tpl.format(a=a, b=b), f"{a}/{b} x {dim}, asymmetric", dims=[dim])
        add("1", "SYMMETRIC", f"role_construction_x_{dim}", sym_tpl.format(a=a, b=b), f"{a}/{b} x {dim}, symmetric")

# ---- Plain multi-word roles, no special punctuation (regression) ----
for a, b in PLAIN_ROLES:
    add("2", "SYMMETRIC", "plain_multiword_regression",
        f"Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability is capped at $150,000, and {b}'s liability is capped at $150,000 as well.",
        "ordinary multi-word role, symmetric regression")
    add("2", "ASYMMETRIC", "plain_multiword_regression",
        f"Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability is capped at $150,000, whereas {b}'s liability carries no cap at all.",
        "ordinary multi-word role, asymmetric regression", dims=["monetary_cap"])

# ---- Over-capture guards: document-structure references, must never
# become roles ----
over_capture = [
    "Each party shall indemnify the other for claims arising under this Agreement; the cap for Schedule A is $60,000 and the cap for Schedule B is $60,000 as well.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the limitations set forth in Section 4 and Section 5.",
    "Each party shall indemnify the other for claims arising under this Agreement; the terms in Exhibit C govern one direction, and the terms in Exhibit D govern the other.",
    "Each party shall indemnify the other for claims arising under this Agreement; the ceiling in Annex 3 applies to one direction and the ceiling in Annex 4 applies to the other.",
]
for tpl in over_capture * 2:
    add("1", "SYMMETRIC", "over_capture_guard", tpl, "document-structure reference must not become a role")

# ---- SYMMETRIC: generic + non-canonical + nominalized openers, no
# named roles (Step 4A.10.7 regression confirmation) ----
generic_sym = [
    "Each party shall indemnify the other for third-party claims traceable to that party's own performance in carrying out this Agreement.",
    "Either party shall indemnify and hold harmless the other against claims traceable to that party's own wrongful conduct under this Agreement.",
    "Both parties shall indemnify and hold harmless the other against third-party claims arising under this Agreement.",
    "The parties shall indemnify one another for claims traceable to each party's own respective breach of this Agreement.",
    "Either party's indemnification obligation under this Agreement applies to both sides on an identical footing.",
]
for tpl in generic_sym * 3:
    add("1", "SYMMETRIC", "genuinely_symmetric_generic", tpl, "opener regression, no named roles")

# ---- SYMMETRIC: explicit equal-treatment cue (Step 4A.10.8 regression) ----
cue_sym = [
    "Each party shall indemnify the other for claims arising under this Agreement; the ceiling in Schedule 9 applies equally to Post-Closing Buyer and Pre-Closing Seller.",
    "Each party shall indemnify the other for claims arising under this Agreement, on the same terms for Tier-2 Vendor and Tier-3 Vendor alike.",
]
for tpl in cue_sym * 4:
    add("2", "SYMMETRIC", "genuinely_symmetric_cue", tpl, "explicit drafter statement of equivalence, must survive role-name construction shapes")

# ---- ASYMMETRIC — standard 12 dimension families, plain named roles
# (full regression confirmation the comparator/discovery is otherwise
# unchanged) ----
dim_families = {
    "causation_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s intentional misconduct, whereas {b} is on the hook whenever the claim stems from {b}'s simple inattention.",
    "claim_category": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is confined to claims alleging trademark infringement, whereas {b}'s duty reaches claims of any description whatsoever.",
    "defense_control": "Each party shall indemnify the other for third-party claims; {a} alone commands litigation strategy for any claim against {b}, whereas {b} has no input at all into strategy for any claim against {a}.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability tops out at four months' worth of fees, whereas {b} faces liability with no ceiling of any kind.",
    "proviso_exception": "Each party shall indemnify the other for claims arising under this Agreement, save that {a}'s duty excludes any claim traceable to {b}'s own unauthorized use of the deliverable, an exclusion {b}'s duty toward {a} does not mirror.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty does not attach unless {b} first exhausts the notice procedure in Section 8, a precondition {b}'s duty toward {a} does not carry.",
    "first_third_party": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty reaches {b}'s own internal losses in addition to outside claims, whereas {b}'s duty reaches only outside claims brought against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} owes this duty even absent any fault on {a}'s part, whereas {b} owes it only once {b}'s own fault is shown.",
    "scope_geographic": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty follows claims arising anywhere on the globe, whereas {b}'s duty is confined to claims arising within Mexico.",
    "cross_reference_schedule": "Each party shall indemnify the other for claims arising under this Agreement; the figure binding {a} is set out in Rider 1, and the figure binding {b}, set out separately in Rider 2, is a different figure than Rider 1 states.",
    "temporal_survival": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty carries on with no end date once this Agreement winds down, whereas {b}'s duty ends the moment this Agreement winds down.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is capped at $350,000, reaches only trade-dress claims, and applies strictly, whereas {b}'s duty carries no cap, reaches claims of any kind, and applies only where {b} is at fault.",
}
all_pairs = ROLE_CONSTRUCTIONS + PLAIN_ROLES
for dim, tpl in dim_families.items():
    for i, (a, b) in enumerate(all_pairs):
        tier = "1" if i < 5 else ("2" if i == 5 else "3")
        add(tier, "ASYMMETRIC", dim, tpl.format(a=a, b=b), f"asymmetric: {dim}", dims=[dim])

# ---- COMPOUND, ~16 ----
compound_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a} keeps its own standalone insurance covering this exposure, while {b}'s duty is additionally capped at $65,000, a limit {a}'s duty does not carry.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the ceiling in Section 7; that ceiling excludes claims caused by {a}'s intentional misconduct but excludes no category of claim caused by {b}.",
    "Each party shall indemnify the other for third-party claims; {a}'s duty to front defense costs as incurred runs alongside its main duty, but {b} carries no separate cost-fronting duty, only the main duty.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} relinquishes any right of contribution against {b}, but {b} retains its full right of contribution against {a}.",
]
for i, tpl in enumerate(compound_templates * 4):
    a, b = all_pairs[i % len(all_pairs)]
    add("3", "ASYMMETRIC", "compound", tpl.format(a=a, b=b), "compound multi-provision asymmetry", dims=["compound"])
    if len([c for c in CASES if c["family"] == "compound"]) >= 16:
        break

# ---- AMBIGUOUS, ~18 ----
ambiguous_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; whether {a}'s ceiling matches {b}'s ceiling is left for a side letter the parties have not yet signed.",
    "Either party shall indemnify the other for claims arising under this Agreement, on terms the parties have agreed to work out in a subsequent side agreement.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is subject to conditions to be set out in an exhibit not yet attached to this Agreement.",
]
for i, tpl in enumerate(ambiguous_templates * 6):
    a, b = all_pairs[i % len(all_pairs)]
    add("2", "AMBIGUOUS", "ambiguous", tpl.format(a=a, b=b), "genuinely unresolved, should route to review")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS"]) >= 18:
        break

for c in CASES:
    c["expected_material_dimensions"] = c["dimensions"] if c["label"] == "ASYMMETRIC" else []
    c["severity_if_false_symmetry"] = "S4" if c["label"] == "ASYMMETRIC" else "N/A"

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_9_fresh_independent_corpus.json"
OUT.write_text(json.dumps(CASES, indent=2))
from collections import Counter
print(f"Total: {len(CASES)}")
print(Counter(c["label"] for c in CASES))
print("families:", Counter(c["family"] for c in CASES))
print("tiers:", Counter(c["tier"] for c in CASES))
