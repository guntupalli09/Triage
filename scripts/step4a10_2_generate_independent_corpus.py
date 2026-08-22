#!/usr/bin/env python3
"""Step 4A.10.2 Phase 13-17 — independent frozen false-symmetry
validation corpus. Built AFTER code freeze (58761f7), from legal/
commercial concepts, NOT copied/paraphrased/derived from the 132-case
development benchmark or the 26-case dev controls. New vocabulary and
document framings throughout."""
import json
from pathlib import Path

ROLES = [
    ("Franchisee", "Franchisor"), ("Colocation Provider", "Enterprise Customer"),
    ("Managed Service Provider", "Client"), ("Underwriter", "Cedent"),
    ("Import Broker", "Principal"), ("Data Processor", "Data Controller"),
    ("Subcontractor", "General Contractor"), ("Reseller", "Original Manufacturer"),
]

CASES = []
_n = {"i": 0}


def add(tier, label, family, text, note, dims=None):
    _n["i"] += 1
    a, b = ROLES[_n["i"] % len(ROLES)]
    CASES.append({
        "id": f"S4A102-{_n['i']:04d}", "tier": tier, "label": label, "family": family,
        "dimensions": dims or [], "text": text.format(a=a, b=b), "note": note,
    })


# ======================================================================
# 60 GENUINELY SYMMETRIC (ordinary + varied)
# ======================================================================
sym_ordinary = [
    "Each party shall indemnify and hold harmless the other party from any third-party claim arising out of the indemnifying party's breach of this Agreement, on identical terms applicable to both parties.",
    "{a} and {b} shall each indemnify the other for losses arising from their own respective negligence, subject to the same aggregate cap of twelve months' fees applicable to both.",
    "Each party's indemnification obligation to the other is limited to direct third-party claims, excludes consequential damages for both parties equally, and survives termination for two years on both sides.",
    "The parties mutually agree to indemnify one another for claims arising from a breach of confidentiality, with identical notice and defense-cooperation obligations running in both directions.",
    "Each of {a} and {b} shall bear the cost of defending any claim traceable to its own acts, with neither party bearing any greater share of exposure than the other under this Section.",
]
for i, tpl in enumerate(sym_ordinary * 8):
    add("1", "SYMMETRIC", "genuinely_symmetric", tpl, "ordinary-drafting genuine symmetry")
    if len([c for c in CASES if c["label"] == "SYMMETRIC" and c["tier"] == "1"]) >= 40:
        break

sym_varied = [
    "As between {a} and {b}, each shall indemnify the other for third-party claims of the type described in Section 4, and, for the avoidance of doubt, the survival period, monetary cap, and defense-control terms set out in Section 4 apply identically regardless of which party is indemnifying.",
    "Each party's indemnification obligation under this Section 9 mirrors the other's in every respect: same claim categories, same causation standard (negligence), same $2,000,000 cap, and same one-year survival period.",
]
for i, tpl in enumerate(sym_varied * 10):
    add("2", "SYMMETRIC", "genuinely_symmetric", tpl, "varied-drafting genuine symmetry")
    if len([c for c in CASES if c["label"] == "SYMMETRIC" and c["tier"] == "2"]) >= 20:
        break

# ======================================================================
# 100 MATERIALLY ASYMMETRIC — 12 dimension families, >=8 each
# ======================================================================
dim_families = {
    "causation_standard": "Each party shall indemnify the other for claims traceable to its own acts; {a} is answerable only for claims traceable to {a}'s gross negligence or willful misconduct, whereas {b} is answerable for claims traceable to {b}'s ordinary carelessness.",
    "claim_category": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty runs only to claims alleging trademark infringement, whereas {b}'s duty runs to claims of any nature whatsoever.",
    "defense_control": "Each party shall indemnify the other for third-party claims; {a} retains the exclusive right to control and settle any claim against {b}, whereas {b} has no corresponding right to control or settle any claim against {a}.",
    "monetary_treatment": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s exposure is capped at the amount of fees paid over the prior six months, whereas {b}'s exposure carries no cap of any kind.",
    "proviso_exception": "Each party shall indemnify the other for claims arising under this Agreement, save that {a}'s duty excludes any claim traceable to a modification {b} makes without {a}'s consent, an exclusion with no counterpart limiting {b}'s duty to {a}.",
    "conditional_applicability": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty arises only once {b} has exhausted the dispute-resolution steps in Section 14, a precondition with no counterpart applicable to {b}'s duty to {a}.",
    "first_third_party": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty extends to {b}'s own direct losses as well as third-party claims, whereas {b}'s duty is confined strictly to third-party claims asserted against {a}.",
    "negligence_fault_standard": "Each party shall indemnify the other for claims traceable to its own acts; {a} answers for such claims strictly, without regard to fault, whereas {b} answers only where {b}'s own fault is affirmatively shown.",
    "scope_geographic": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty applies to claims wherever they arise, whereas {b}'s duty is confined to claims arising within North America.",
    "cross_reference_schedule": "Each party shall indemnify the other for claims arising under this Agreement; the ceiling applicable to {a} is fixed by Schedule 7, and the ceiling applicable to {b}, set by the separate terms of Schedule 9, differs from Schedule 7.",
    "temporal_survival": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty continues without end after this Agreement concludes, whereas {b}'s duty lapses the moment this Agreement concludes.",
    "compound_multi_dimension": "Each party shall indemnify the other for claims arising under this Agreement; {a}'s duty is capped at $250,000, covers only data-security claims, and rests on a strict-liability standard, whereas {b}'s duty is uncapped, covers claims of any nature, and rests on a gross-negligence standard.",
}
for dim, tpl in dim_families.items():
    for i, (a, b) in enumerate(ROLES):
        # Ordinary single-provision "each party...provided that X while Y"
        # asymmetric provisos are themselves plausible ordinary commercial
        # drafting (Tier 1) -- only the later compound/multi-provision
        # cases are genuinely more complex (Tier 2/3).
        tier = "1" if i < 6 else ("2" if i == 6 else "3")
        add(tier, "ASYMMETRIC", dim, tpl.format(a=a, b=b), f"asymmetric: {dim}", dims=[dim])

# ======================================================================
# 30 COMPOUND CASES
# ======================================================================
compound_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; {a} separately maintains cyber-liability insurance covering the same risk, while {b}'s indemnification duty is additionally capped at $100,000 -- a limitation {a}'s duty does not share.",
    "Each party shall indemnify the other for claims arising under this Agreement, subject to the liability cap in Section 11; that cap, however, exempts claims caused by {a}'s gross negligence but does not exempt any category of claim caused by {b}.",
    "Each party shall indemnify the other for third-party claims; {a}'s duty to reimburse ordinary defense costs runs alongside its indemnification duty, whereas {b} has no separate reimbursement duty at all, only the indemnification duty itself.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a} waives any right of contribution against {b}, while {b} retains a full right of contribution against {a}.",
    "Each party shall indemnify the other for claims arising under this Agreement, and {a} shall additionally reimburse {b} for the cost of any tax assessed on amounts paid under this Section, a reimbursement duty with no counterpart running from {b} to {a}.",
    "Each party shall indemnify the other for claims arising from this Agreement's multiple risk-transfer provisions: Section 6 addresses IP claims, Section 7 addresses data claims. Section 6 applies identically to both parties, but Section 7 caps only {b}'s exposure, leaving {a}'s Section 7 exposure uncapped.",
]
for i, tpl in enumerate(compound_templates * 5):
    add("3", "ASYMMETRIC", "compound", tpl, "compound multi-provision asymmetry", dims=["compound"])
    if len([c for c in CASES if c["family"] == "compound"]) >= 30:
        break

# ======================================================================
# 40 SHOULD_REVIEW / AMBIGUOUS
# ======================================================================
ambiguous_templates = [
    "Each party shall indemnify the other for claims arising under this Agreement; the parties acknowledge that whether {a}'s duty is subject to the same cap as {b}'s remains an open question pending a forthcoming amendment.",
    "Each party shall indemnify the other for claims arising under this Agreement, on terms to be finalized in a schedule the parties have not yet prepared.",
    "Each party shall indemnify the other for claims arising under this Agreement; {a}'s obligation is subject to conditions described elsewhere in this Agreement that have not yet been drafted.",
    "Each party shall indemnify the other for claims arising under this Agreement, provided that the parties have not yet reached agreement on which claim categories are covered.",
    "Each party shall indemnify the other for claims arising under this Agreement; the causation standard applicable to each party's duty remains a matter the parties intend to address in a future amendment.",
]
for i, tpl in enumerate(ambiguous_templates * 8):
    add("2", "AMBIGUOUS", "ambiguous", tpl, "genuinely unresolved, should route to review")
    if len([c for c in CASES if c["label"] == "AMBIGUOUS"]) >= 40:
        break

# ======================================================================
# PHASE 17 — ground truth, assigned before execution
# ======================================================================
for c in CASES:
    c["obligated_party_a"] = "first-named role in template"
    c["protected_party_b"] = "second-named role in template"
    c["expected_material_dimensions"] = c["dimensions"] if c["label"] == "ASYMMETRIC" else []
    c["expected_safe_outcome"] = {
        "SYMMETRIC": "CS (clean, correctly symmetric)",
        "ASYMMETRIC": "CA (flagged asymmetric) or CR (routed to review) -- never a clean unflagged symmetric result",
        "AMBIGUOUS": "CR (routed to review)",
    }[c["label"]]
    c["severity_if_false_symmetry"] = "S4" if c["label"] == "ASYMMETRIC" else "N/A"

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a10_2_independent_corpus.json"
OUT.write_text(json.dumps(CASES, indent=2))
from collections import Counter
print(f"Total: {len(CASES)}")
print(Counter(c["label"] for c in CASES))
print("ordinary(tier1)+varied(tier2)/adversarial(tier3):", Counter(c["tier"] for c in CASES))
print("dimension family counts (asymmetric only):")
fam_counts = Counter()
for c in CASES:
    if c["label"] == "ASYMMETRIC":
        for d in c["dimensions"]:
            fam_counts[d] += 1
print(dict(fam_counts))
