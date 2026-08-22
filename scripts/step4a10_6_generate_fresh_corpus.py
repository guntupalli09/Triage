#!/usr/bin/env python3
"""Step 4A.10.6 — the AUTHORITATIVE frozen validation corpus for the
structural defense-control redesign. Built after code freeze (commit
6ea8c5d) and after the redesign was exhausted against explicitly
non-authoritative development/adversarial material (see
scripts/step4a10_6_dev_adversarial_controls.py and the dev-replay of
all 3 prior corpora, none of which count as authoritative evidence for
THIS step). New role names, new phrasing throughout -- not copied,
paraphrased, or derived from any prior corpus in this program,
including the dev-adversarial names. Defense-control verbs deliberately
chosen to be OUTSIDE every verb this program has used so far (takes
charge of/directs/controls/decides/manages/handles/runs point on/
steers/oversees/spearheads/calls the shots on/owns/commands), since
that is the specific generalization this step claims to have achieved.
Run EXACTLY ONCE with no further code changes regardless of outcome."""
import json
from pathlib import Path

ROLES = [
    ("Aircraft Lessor", "Aircraft Lessee"), ("Technology Licensor", "Implementation Partner"),
    ("Storage Provider", "Depositing Client"), ("Underwriting Agent", "Capacity Provider"),
    ("Outsourcing Provider", "Client Enterprise"), ("Import Broker", "Export Broker"),
    ("Facility Operator", "Facility User"), ("Benefits Administrator", "Plan Participant"),
]

CASES = []
_n = {"i": 0}


def add(tier, label, family, text, note, dims=None):
    _n["i"] += 1
    a, b = ROLES[_n["i"] % len(ROLES)]
    CASES.append({
        "id": f"FRESH106-{_n['i']:04d}", "tier": tier, "label": label, "family": family,
        "dimensions": dims or [], "text": text.format(a=a, b=b), "note": note,
    })


# ---- SYMMETRIC: generic boilerplate (no named roles) ----
generic_sym = [
    "Each party shall indemnify the other for third-party claims traceable to that party's own performance under this Agreement.",
    "Each party shall indemnify the other for claims arising from that party's own wrongful acts under this Agreement.",
    "The parties shall indemnify one another reciprocally for claims traceable to their own respective conduct, applying no distinction in how either is treated.",
]
for tpl in generic_sym * 5:
    add("1", "SYMMETRIC", "genuinely_symmetric_generic", tpl, "no named roles -- discovery block never activates")

# ---- SYMMETRIC: defense-control paraphrase using verbs NEVER used
# anywhere else in this program -- the direct test of this step's own
# claimed generalization ----
defense_control_sym = [
    "Each party shall indemnify the other for third-party claims; {a} helms the defense of any claim brought against it, and {b} likewise helms the defense of any claim brought against it.",
    "Each party shall indemnify the other for third-party claims; {a} quarterbacks the litigation response to any claim against it, while {b} quarterbacks the litigation response to any claim against it in just the same way.",
    "Each party shall indemnify the other for third-party claims; {a} presides over settlement of any claim brought against it, and {b} presides over that same settlement process for any claim brought against it.",
    "Each party shall indemnify the other for third-party claims; {a} shepherds the resolution of any claim against it, while {b} shepherds the resolution of any claim against it as well.",
    "Each party shall indemnify the other for third-party claims; {a} holds the reins on any claim's defense against it, and {b} holds the reins on any claim's defense against it too.",
]
for tpl in defense_control_sym * 6:
    add("2", "SYMMETRIC", "genuinely_symmetric_defense_control", tpl, "defense-control paraphrase, fresh verbs never used elsewhere in this program")

# ---- SYMMETRIC: survival/monetary paraphrase (already-generalized
# dimensions -- confirm they still hold on unseen vocabulary too) ----
other_paraphrase_sym = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty stretches on for five years after this Agreement lapses, and {b} stays bound for that same five years after this Agreement lapses.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} is capped at eight months' worth of fees, and {b}'s exposure likewise does not go past eight months' worth of fees.",
]
for tpl in other_paraphrase_sym * 5:
    add("2", "SYMMETRIC", "genuinely_symmetric_other_paraphrase", tpl, "survival/monetary paraphrase, confirming prior generalization holds on fresh vocabulary")

# ---- SYMMETRIC: explicit equal-treatment cue, varied determiners ----
cue_sym = [
    "Each party shall indemnify the other for claims arising under this Agreement; the ceiling in Schedule 9 applies equally to {a} and {b}.",
    "Each party shall indemnify the other for claims arising under this Agreement, on the same terms for {a} and {b} alike.",
    "Each party's indemnification duty under this Agreement binds {a} and {b} identically.",
]
for tpl in cue_sym * 5:
    add("2", "SYMMETRIC", "genuinely_symmetric_cue", tpl, "explicit drafter statement of equivalence")

# ---- ASYMMETRIC — 12 dimension families, fresh phrasing (including a
# defense_control family using fresh asymmetric-shape verbs) ----
dim_families = {
    "causation_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} is on the hook only where the claim stems from {a}'s knowing misconduct, whereas {b} is on the hook whenever the claim stems from {b}'s simple oversight.",
    "claim_category": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is confined to claims alleging an environmental violation, whereas {b}'s duty reaches claims of any description whatsoever.",
    "defense_control": "Each party shall indemnify the other for third-party claims; {a} alone helms litigation and settlement strategy for any claim against {b}, whereas {b} has no input at all into strategy for any claim against {a}.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s liability tops out at six months' worth of fees, whereas {b} faces liability with no ceiling of any kind.",
    "proviso_exception": "Each party shall indemnify the other for claims arising under this Agreement, save that {a}'s duty excludes any claim traceable to {b}'s own unauthorized modification of the deliverable, an exclusion {b}'s duty toward {a} does not mirror.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty does not attach unless {b} first exhausts the escalation procedure in Section 11, a precondition {b}'s duty toward {a} does not carry.",
    "first_third_party": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty reaches {b}'s own internal losses in addition to outside claims, whereas {b}'s duty reaches only outside claims brought against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} owes this duty even absent any fault on {a}'s part, whereas {b} owes it only once {b}'s own fault is shown.",
    "scope_geographic": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty follows claims arising anywhere on the globe, whereas {b}'s duty is confined to claims arising within Australia.",
    "cross_reference_schedule": "Each party shall indemnify the other for claims arising under this Agreement; the figure binding {a} is set out in Appendix 1, and the figure binding {b}, set out separately in Appendix 2, is a different figure than Appendix 1 states.",
    "temporal_survival": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty carries on with no end date once this Agreement winds down, whereas {b}'s duty ends the moment this Agreement winds down.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is capped at $600,000, reaches only cybersecurity claims, and applies strictly, whereas {b}'s duty carries no cap, reaches claims of any kind, and applies only where {b} is at fault.",
}
for dim, tpl in dim_families.items():
    for i, (a, b) in enumerate(ROLES):
        tier = "1" if i < 5 else ("2" if i == 5 else "3")
        add(tier, "ASYMMETRIC", dim, tpl.format(a=a, b=b), f"asymmetric: {dim}", dims=[dim])

# ---- ASYMMETRIC defense-control using fresh verbs + genuine
# control-vs-no-control shape (the direct adversarial-style stress
# case, now placed IN the authoritative corpus) ----
defense_control_asym = [
    "Each party shall indemnify the other for third-party claims; {a} commands the response to any claim brought against it, while {b} has absolutely no say in the response to any claim brought against it.",
    "Each party shall indemnify the other for third-party claims; {a} captains the defense of any claim against it, whereas {b} is excluded from any role in the defense of a claim against it.",
]
for i, tpl in enumerate(defense_control_asym * 4):
    add("2", "ASYMMETRIC", "defense_control_no_control", tpl.format(a=ROLES[i % len(ROLES)][0], b=ROLES[i % len(ROLES)][1]), "genuine control-vs-no-control asymmetry, fresh verbs", dims=["defense_control"])
    if len([c for c in CASES if c["family"] == "defense_control_no_control"]) >= 8:
        break

# ---- COMPOUND, ~20 ----
compound_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a} keeps its own standalone insurance covering this exposure, while {b}'s duty is additionally capped at $95,000, a limit {a}'s duty does not carry.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the ceiling in Section 10; that ceiling excludes claims caused by {a}'s knowing misconduct but excludes no category of claim caused by {b}.",
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
    "Each party shall indemnify the other for claims arising under this Agreement, on terms the parties still intend to work out in a future amendment.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is subject to conditions to be set out in an exhibit not yet attached to this Agreement.",
]
for i, tpl in enumerate(ambiguous_templates * 7):
    add("2", "AMBIGUOUS", "ambiguous", tpl, "genuinely unresolved, should route to review")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS"]) >= 20:
        break

for c in CASES:
    c["expected_material_dimensions"] = c["dimensions"] if c["label"] == "ASYMMETRIC" else []
    c["severity_if_false_symmetry"] = "S4" if c["label"] == "ASYMMETRIC" else "N/A"

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_6_fresh_independent_corpus.json"
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
