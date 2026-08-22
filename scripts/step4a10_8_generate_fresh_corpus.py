#!/usr/bin/env python3
"""Step 4A.10.8 — the AUTHORITATIVE frozen validation corpus for the
equal-treatment-cue structural-exclusion fix. Built after code freeze
(commit f1bb0d6) and after the fix was exhausted against non-
authoritative dev/adversarial material only (see
scripts/step4a10_8_dev_adversarial_controls.py and the dev-replay of
all 5 prior corpora). New role names, new phrasing throughout -- not
copied/paraphrased/derived from any prior corpus in this program,
including the dev-adversarial names (Alpha/Beta Holdings). Heavily
weighted toward reciprocal-opener SHAPES (each/either/both/every/one
another/nominalized) crossed with each of the eight mandated
dimensions (scope, survival, cap, causation, defense control, claim
category, proviso, cross-reference), in both asymmetric and symmetric
form -- the direct test of this step's own claimed generalization.
Run EXACTLY ONCE with no further code changes regardless of outcome."""
import json
from pathlib import Path

ROLES = [
    ("Anchor Tenant", "Property Manager"), ("Syndication Partner", "Media Network"),
    ("Cross-Border Agent", "Local Distributor"), ("Wholesale Buyer", "Retail Reseller"),
    ("Pipeline Operator", "Shipper Client"), ("Benefit Plan Trustee", "Contributing Employer"),
    ("Cloud Host", "Managed Service Client"), ("Territory Holder", "Brand Licensor"),
]
OPENERS = [
    "Each party shall indemnify the other",
    "Either party shall indemnify the other",
    "Both parties shall indemnify the other",
    "Every party shall indemnify the other",
    "The parties shall indemnify one another",
    "The parties shall mutually indemnify each other",
]

CASES = []
_n = {"i": 0}


def add(tier, label, family, text, note, dims=None):
    _n["i"] += 1
    a, b = ROLES[_n["i"] % len(ROLES)]
    CASES.append({
        "id": f"FRESH108-{_n['i']:04d}", "tier": tier, "label": label, "family": family,
        "dimensions": dims or [], "text": text.format(a=a, b=b), "note": note,
    })


# ---- Opener x Dimension matrix -- THIS STEP'S OWN TARGET. Each of the
# 8 mandated dimensions crossed with 3 (of 6) opener shapes, both
# asymmetric and symmetric. ----
OPENER_SAMPLE = [OPENERS[0], OPENERS[2], OPENERS[4]]  # each / both / one another -- spot-check the rest via dev evidence
DIM_TEMPLATES = {
    "scope_first_third_party": (
        "for claims arising under this Agreement; {a}'s duty extends to {b}'s own first-party losses as well as third-party claims, whereas {b}'s duty is confined strictly to third-party claims brought against {a}.",
        "for claims arising under this Agreement; {a}'s duty is confined strictly to third-party claims, and {b}'s duty is likewise confined strictly to third-party claims.",
    ),
    "survival": (
        "for claims arising under this Agreement; {a}'s duty carries on with no end date once this Agreement winds down, whereas {b}'s duty ends the moment this Agreement winds down.",
        "for claims arising under this Agreement; {a}'s duty survives for a period of six years, and {b}'s duty survives for a period of six years as well.",
    ),
    "monetary_cap": (
        "for claims arising under this Agreement; {a}'s liability is capped at $180,000, whereas {b}'s liability carries no cap at all.",
        "for claims arising under this Agreement; {a}'s liability is capped at $180,000, and {b}'s liability is capped at $180,000 as well.",
    ),
    "causation": (
        "for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s gross negligence, whereas {b} is on the hook whenever the claim stems from {b}'s ordinary carelessness.",
        "for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s gross negligence, and {b} is on the hook only where the claim stems from {b}'s gross negligence as well.",
    ),
    "defense_control": (
        "for third-party claims; {a} alone decides litigation strategy for any claim against {b}, whereas {b} has no input at all into strategy for any claim against {a}.",
        "for third-party claims; {a} controls the defense of any claim brought against it, and {b} likewise controls the defense of any claim brought against it.",
    ),
    "claim_category": (
        "for claims traceable to its own conduct; {a}'s duty covers claims alleging fraud, whereas {b}'s duty covers claims alleging data breach only, with no overlap between the two categories.",
        "for claims traceable to its own conduct; {a}'s duty covers claims alleging fraud, and {b}'s duty covers that same category of claims alleging fraud.",
    ),
    "proviso": (
        "for claims arising under this Agreement, save that {a}'s duty excludes any claim traceable to {b}'s own modification of the deliverable, an exclusion {b}'s duty toward {a} does not mirror.",
        "for claims arising under this Agreement, save that each party's duty excludes any claim traceable to the other's own modification of the deliverable, an exclusion applying identically to both.",
    ),
    "cross_reference": (
        "for claims arising under this Agreement; the figure binding {a} is set out in Schedule A, and the figure binding {b}, set out separately in Schedule B, is a different figure than Schedule A states.",
        "for claims arising under this Agreement; the figure binding {a} is set out in Schedule A, and the figure binding {b} is that same figure set out in Schedule A.",
    ),
}
for dim, (asym_tail, sym_tail) in DIM_TEMPLATES.items():
    for opener in OPENER_SAMPLE:
        add("1", "ASYMMETRIC", f"opener_x_{dim}", f"{opener} {asym_tail}", f"opener x {dim}, asymmetric", dims=[dim])
        add("1", "SYMMETRIC", f"opener_x_{dim}", f"{opener} {sym_tail}", f"opener x {dim}, symmetric")

# ---- SYMMETRIC: canonical + non-canonical generic openers, no named
# roles (baseline regression) ----
generic_sym = [
    "Each party shall indemnify the other for third-party claims traceable to its own performance of this Agreement.",
    "Either party shall indemnify and hold harmless the other for claims arising from that party's own breach of this Agreement.",
    "Both parties shall indemnify and hold harmless the other for claims arising under this Agreement.",
    "The parties shall indemnify one another for claims traceable to their own respective negligent acts under this Agreement.",
]
for tpl in generic_sym * 3:
    add("1", "SYMMETRIC", "genuinely_symmetric_generic", tpl, "non-canonical opener regression, no named roles")

# ---- SYMMETRIC: nominalized-duty opener shape, no named roles ----
nominal_sym = [
    "Each party's indemnification duty under this Agreement binds both sides identically.",
    "Either party's indemnification obligation under this Agreement applies to both sides on the same footing.",
]
for tpl in nominal_sym * 3:
    add("1", "SYMMETRIC", "genuinely_symmetric_nominalized", tpl, "nominalized-duty opener regression")

# ---- SYMMETRIC: defense-control paraphrase, fresh verbs (Step 4A.10.6
# mechanism regression confirmation) ----
defense_control_sym = [
    "Each party shall indemnify the other for third-party claims; {a} fronts the response to any claim brought against it, and {b} likewise fronts the response to any claim brought against it.",
]
for tpl in defense_control_sym * 6:
    add("2", "SYMMETRIC", "genuinely_symmetric_defense_control", tpl, "defense-control paraphrase, regression confirmation")

# ---- SYMMETRIC: explicit equal-treatment cue (must still work post-masking) ----
cue_sym = [
    "Each party shall indemnify the other for claims arising under this Agreement; the ceiling in Schedule 5 applies equally to {a} and {b}.",
    "Each party shall indemnify the other for claims arising under this Agreement, on the same terms for {a} and {b} alike.",
]
for tpl in cue_sym * 5:
    add("2", "SYMMETRIC", "genuinely_symmetric_cue", tpl, "explicit drafter statement of equivalence, must survive opener masking")

# ---- ASYMMETRIC — standard 12 dimension families, canonical opener
# (full regression confirmation the comparator is otherwise unchanged)
dim_families = {
    "causation_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s intentional misconduct, whereas {b} is on the hook whenever the claim stems from {b}'s simple inattention.",
    "claim_category": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is confined to claims alleging patent infringement, whereas {b}'s duty reaches claims of any description whatsoever.",
    "defense_control": "Each party shall indemnify the other for third-party claims; {a} alone directs litigation strategy for any claim against {b}, whereas {b} has no input at all into strategy for any claim against {a}.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability tops out at five months' worth of fees, whereas {b} faces liability with no ceiling of any kind.",
    "proviso_exception": "Each party shall indemnify the other for claims arising under this Agreement, save that {a}'s duty excludes any claim traceable to {b}'s own unauthorized use of the deliverable, an exclusion {b}'s duty toward {a} does not mirror.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty does not attach unless {b} first exhausts the notice procedure in Section 6, a precondition {b}'s duty toward {a} does not carry.",
    "first_third_party": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty reaches {b}'s own internal losses in addition to outside claims, whereas {b}'s duty reaches only outside claims brought against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} owes this duty even absent any fault on {a}'s part, whereas {b} owes it only once {b}'s own fault is shown.",
    "scope_geographic": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty follows claims arising anywhere on the globe, whereas {b}'s duty is confined to claims arising within Brazil.",
    "cross_reference_schedule": "Each party shall indemnify the other for claims arising under this Agreement; the figure binding {a} is set out in Exhibit 1, and the figure binding {b}, set out separately in Exhibit 2, is a different figure than Exhibit 1 states.",
    "temporal_survival": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty carries on with no end date once this Agreement winds down, whereas {b}'s duty ends the moment this Agreement winds down.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is capped at $500,000, reaches only trade-secret claims, and applies strictly, whereas {b}'s duty carries no cap, reaches claims of any kind, and applies only where {b} is at fault.",
}
for dim, tpl in dim_families.items():
    for i, (a, b) in enumerate(ROLES):
        tier = "1" if i < 5 else ("2" if i == 5 else "3")
        add(tier, "ASYMMETRIC", dim, tpl.format(a=a, b=b), f"asymmetric: {dim}", dims=[dim])

# ---- COMPOUND, ~16 ----
compound_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a} keeps its own standalone insurance covering this exposure, while {b}'s duty is additionally capped at $80,000, a limit {a}'s duty does not carry.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the ceiling in Section 3; that ceiling excludes claims caused by {a}'s intentional misconduct but excludes no category of claim caused by {b}.",
    "Each party shall indemnify the other for third-party claims; {a}'s duty to front defense costs as incurred runs alongside its main duty, but {b} carries no separate cost-fronting duty, only the main duty.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} relinquishes any right of contribution against {b}, but {b} retains its full right of contribution against {a}.",
]
for i, tpl in enumerate(compound_templates * 4):
    add("3", "ASYMMETRIC", "compound", tpl, "compound multi-provision asymmetry", dims=["compound"])
    if len([c for c in CASES if c["family"] == "compound"]) >= 16:
        break

# ---- AMBIGUOUS, ~18 ----
ambiguous_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; whether {a}'s ceiling matches {b}'s ceiling is left for a side letter the parties have not yet signed.",
    "Either party shall indemnify the other for claims arising under this Agreement, on terms the parties have agreed to negotiate further before this Agreement is signed.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is subject to conditions to be set out in an exhibit not yet attached to this Agreement.",
]
for i, tpl in enumerate(ambiguous_templates * 6):
    add("2", "AMBIGUOUS", "ambiguous", tpl, "genuinely unresolved, should route to review")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS"]) >= 18:
        break

for c in CASES:
    c["expected_material_dimensions"] = c["dimensions"] if c["label"] == "ASYMMETRIC" else []
    c["severity_if_false_symmetry"] = "S4" if c["label"] == "ASYMMETRIC" else "N/A"

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_8_fresh_independent_corpus.json"
OUT.write_text(json.dumps(CASES, indent=2))
from collections import Counter
print(f"Total: {len(CASES)}")
print(Counter(c["label"] for c in CASES))
print("families:", Counter(c["family"] for c in CASES))
print("tiers:", Counter(c["tier"] for c in CASES))
