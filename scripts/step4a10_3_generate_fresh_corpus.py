#!/usr/bin/env python3
"""Step 4A.10.3 — genuinely fresh independent false-symmetry validation
corpus, built AFTER code freeze (22eac3d). New role names, new document
framings, new attribution verbs throughout -- NOT copied/paraphrased/
derived from any prior corpus in this program (Step 4A.10, 4A.10.1,
4A.10.2 dev or independent, or 4A.10.3 dev controls)."""
import json
from pathlib import Path

ROLES = [
    ("Charterer", "Shipowner"), ("Escrow Agent", "Depositor"),
    ("Third-Party Administrator", "Plan Sponsor"), ("Ceding Company", "Reinsurer"),
    ("Warehouse Operator", "Consignor"), ("Toll Manufacturer", "Brand Owner"),
    ("Syndicate Lead", "Participant Lender"), ("Booking Agent", "Performer"),
]

CASES = []
_n = {"i": 0}


def add(tier, label, family, text, note, dims=None):
    _n["i"] += 1
    a, b = ROLES[_n["i"] % len(ROLES)]
    CASES.append({
        "id": f"FRESH103-{_n['i']:04d}", "tier": tier, "label": label, "family": family,
        "dimensions": dims or [], "text": text.format(a=a, b=b), "note": note,
    })


# ---- SYMMETRIC (ordinary + varied), ~40 ----
sym_templates = [
    "Each party shall indemnify the other for any third-party claim traceable to its own performance under this Agreement, on identical terms for both parties.",
    "{a} and {b} shall each stand behind the other against claims arising from their own respective acts, subject to the same aggregate ceiling of eighteen months' fees for both.",
    "Each party shall indemnify the other for claims arising under this Agreement; that indemnification obligation is confined to direct third-party claims, carries the same two-year tail for both parties, and is triggered only by the acting party's own fault.",
    "Each party shall indemnify the other for claims traceable to a breach of confidentiality by that party, with the same notice period and the same defense-cooperation duty running in both directions.",
    "As between {a} and {b}, each shall indemnify the other for any claim traceable to its own conduct, and neither carries a greater share of that burden than the other under this Section.",
]
for i, tpl in enumerate(sym_templates * 8):
    add("1", "SYMMETRIC", "genuinely_symmetric", tpl, "ordinary-drafting genuine symmetry")
    if len([c for c in CASES if c["label"] == "SYMMETRIC" and c["tier"] == "1"]) >= 26:
        break
sym_varied = [
    "As between {a} and {b}, each shall answer for third-party claims of the type described in Section 5, and for the avoidance of doubt the tail period, the ceiling, and the defense-control terms in Section 5 apply identically regardless of which party is answering.",
]
for i, tpl in enumerate(sym_varied * 14):
    add("2", "SYMMETRIC", "genuinely_symmetric", tpl, "varied-drafting genuine symmetry")
    if len([c for c in CASES if c["label"] == "SYMMETRIC" and c["tier"] == "2"]) >= 14:
        break

# ---- ASYMMETRIC — 12 dimension families, new verbs/nouns throughout ----
dim_families = {
    "causation_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} carries this burden only for claims traceable to {a}'s gross negligence or willful misconduct, but {b} carries it for claims traceable to {b}'s plain carelessness.",
    "claim_category": "Each party shall indemnify the other for claims arising under this Agreement; {a} is chargeable only for claims alleging patent infringement, while {b} is chargeable for claims of every description.",
    "defense_control": "Each party shall indemnify the other for third-party claims; {a} keeps sole command over the defense and settlement of any claim against {b}, but {b} holds no corresponding command over any claim against {a}.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s exposure tops out at nine months' fees, but {b} carries no ceiling on its exposure whatsoever.",
    "proviso_exception": "Each party shall indemnify the other for claims arising under this Agreement, save that {a}'s duty leaves out any claim traceable to a change {b} makes without {a}'s sign-off, a carve-out with nothing matching it on {b}'s side toward {a}.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty kicks in only once {b} has first pursued the escalation steps in Section 12, a precondition with no mirror image applicable to {b}'s duty toward {a}.",
    "first_third_party": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty stretches to {b}'s own direct losses as well as outside claims, but {b}'s duty is confined strictly to outside claims brought against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims traceable to its own conduct; {a} carries this duty strictly, without regard to fault, but {b} carries it only where {b}'s own fault is shown.",
    "scope_geographic": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty reaches claims arising anywhere on earth, but {b}'s duty is confined to claims arising within the European Union.",
    "cross_reference_schedule": "Each party shall indemnify the other for claims arising under this Agreement; the ceiling that binds {a} is fixed by Annex 4, and the ceiling that binds {b}, set out separately in Annex 6, is not the same as Annex 4.",
    "temporal_survival": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty carries on without end after this Agreement winds up, but {b}'s duty stops the moment this Agreement winds up.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty tops out at $400,000, reaches only data-security claims, and rests on a strict standard, but {b}'s duty has no ceiling, reaches claims of any kind, and rests on a gross-negligence standard.",
}
for dim, tpl in dim_families.items():
    for i, (a, b) in enumerate(ROLES):
        tier = "1" if i < 5 else ("2" if i == 5 else "3")
        add(tier, "ASYMMETRIC", dim, tpl.format(a=a, b=b), f"asymmetric: {dim}", dims=[dim])

# ---- COMPOUND, ~20 ----
compound_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a} separately carries its own cyber cover for the same risk, while {b}'s duty additionally tops out at $75,000, a ceiling {a}'s duty does not share.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the ceiling in Section 9; that ceiling exempts claims caused by {a}'s gross negligence but exempts no category of claim caused by {b}.",
    "Each party shall indemnify the other for third-party claims; {a}'s duty to cover ordinary defense costs runs alongside its main duty, but {b} carries no separate cost-covering duty at all, only the main duty itself.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} gives up any right of contribution against {b}, but {b} keeps a full right of contribution against {a}.",
]
for i, tpl in enumerate(compound_templates * 5):
    add("3", "ASYMMETRIC", "compound", tpl, "compound multi-provision asymmetry", dims=["compound"])
    if len([c for c in CASES if c["family"] == "compound"]) >= 20:
        break

# ---- AMBIGUOUS, ~26 ----
ambiguous_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; the parties note that whether {a}'s duty carries the same ceiling as {b}'s remains open pending a future amendment.",
    "Each party shall indemnify the other for claims arising under this Agreement, on terms to be spelled out in an annex the parties have not yet drawn up.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is subject to conditions described elsewhere in this Agreement that have not yet been written.",
]
for i, tpl in enumerate(ambiguous_templates * 9):
    add("2", "AMBIGUOUS", "ambiguous", tpl, "genuinely unresolved, should route to review")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS"]) >= 26:
        break

for c in CASES:
    c["expected_material_dimensions"] = c["dimensions"] if c["label"] == "ASYMMETRIC" else []
    c["severity_if_false_symmetry"] = "S4" if c["label"] == "ASYMMETRIC" else "N/A"

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_3_fresh_independent_corpus.json"
OUT.write_text(json.dumps(CASES, indent=2))
from collections import Counter
print(f"Total: {len(CASES)}")
print(Counter(c["label"] for c in CASES))
print("tiers:", Counter(c["tier"] for c in CASES))
fam_counts = Counter()
for c in CASES:
    if c["label"] == "ASYMMETRIC":
        for d in c["dimensions"]:
            fam_counts[d] += 1
print(dict(fam_counts))
