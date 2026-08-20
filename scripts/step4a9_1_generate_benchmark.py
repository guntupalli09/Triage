#!/usr/bin/env python3
"""Step 4A.9.1 Phases 5/6 — fresh >=200-case indemnification recognition
benchmark, built BEFORE the hybrid A/B test (Phase 12) is run, from the
legal concept itself (a party absorbing/covering a counterparty's claims,
losses, or exposure arising from a stated cause) — NOT by reading
production regex source, and NOT reusing text from Step 4A.8, the Step
4A.9 recognition benchmark, or the Step 4A.9 fresh 103-case battery.

Label taxonomy (recognition-level, not full policy-decision-level):
  POSITIVE — document genuinely states a directional indemnification/
    risk-transfer obligation.
  NEGATIVE — document does not (hard negatives: adjacent-but-different
    concepts, or explicit negation).

`family` further splits POSITIVE into:
  canonical            — "shall indemnify, defend, and hold harmless"
  regex_synonym        — phrasing the Step 4A.9 regex widening already
                          recognizes (reimburse, assume liability, stand in
                          X's place, answer for, protect/satisfy, bear
                          responsibility reordered)
  semantic_vocab       — phrasing inside this POC's hand-authored semantic
                          trigger vocabulary (make good to, recompense,
                          shoulder cost, etc.) but OUTSIDE the regex sets
  novel_unseen         — phrasing outside BOTH vocabularies: a genuine,
                          un-gamed generalization stress test
"""
import json
from pathlib import Path

ROLES = [
    ("Contractor", "Owner"), ("Vendor", "Client"), ("Licensee", "Licensor"),
    ("Manufacturer", "Distributor"), ("Tenant", "Landlord"), ("Consultant", "Company"),
    ("Supplier", "Purchaser"), ("Franchisee", "Franchisor"), ("Operator", "Host"),
    ("Developer", "Investor"), ("Broker", "Principal"), ("Carrier", "Shipper"),
    ("Subcontractor", "GeneralContractor"), ("Servicer", "Bank"), ("Reseller", "Manufacturer2"),
]

CASES = []
_n = {"i": 0}


def add(family, label, text, note):
    _n["i"] += 1
    CASES.append({
        "id": f"S491-{_n['i']:03d}",
        "family": family,
        "label": label,
        "text": text,
        "note": note,
    })


# ---- POSITIVE: canonical (20) ----
for i, (a, b) in enumerate(ROLES + ROLES[:5]):
    add("canonical", "POSITIVE",
        f"{a} shall indemnify, defend, and hold harmless {b} from and against any and all third-party "
        f"claims, losses, and damages arising out of {a}'s performance under this Agreement.",
        "canonical triad phrasing")

# ---- POSITIVE: regex_synonym (30) — already-widened structured patterns ----
synonym_templates = [
    "{a} shall reimburse {b} in full for any losses {b} incurs arising from {a}'s breach of this Agreement.",
    "{a} shall assume all liability for claims brought against {b} arising out of {a}'s negligent acts.",
    "{a} shall stand in {b}'s place with respect to any claim arising from the delivered goods.",
    "{a} shall answer for any claim asserted against {b} in connection with {a}'s services.",
    "{a} shall protect {b} from and shall satisfy any claims arising out of {a}'s work under this Agreement.",
    "On {b}'s behalf, {a} shall bear responsibility for any losses arising from the equipment defects.",
]
for i, tpl in enumerate(synonym_templates):
    for j, (a, b) in enumerate(ROLES[:5]):
        add("regex_synonym", "POSITIVE", tpl.format(a=a, b=b), "regex-widened synonym obligation pattern")

# ---- POSITIVE: semantic_vocab (40) — inside this POC's semantic layer only ----
semantic_templates = [
    "Should a third party bring a claim against {b}, {a} shall make good to {b} for any resulting loss.",
    "{a} shall recompense {b} in full for any damages {b} sustains because of {a}'s failure to perform.",
    "{a} shall be answerable to {b} for any claim arising out of the installation, and {a} shall settle on {b}'s behalf.",
    "{a} agrees to shoulder the cost of any claim brought against {b} relating to the products supplied.",
    "{a} shall absorb any loss {b} incurs as a result of a third-party claim tied to {a}'s performance.",
    "{a} shall be on the hook for any judgment entered against {b} arising from {a}'s conduct under this Agreement.",
    "{a} shall stand behind {b} against any claim relating to defects in the delivered materials.",
    "{a} undertakes to make {b} whole for any loss arising from a claim connected to {a}'s services.",
    "{a} shall cover the cost of any claim asserted against {b} in connection with the work performed.",
    "{a} shall take on the liability for any third-party claim arising from {a}'s use of the facility.",
]
for tpl in semantic_templates:
    for a, b in ROLES[:4]:
        add("semantic_vocab", "POSITIVE", tpl.format(a=a, b=b), "in simulated-semantic vocabulary, outside regex")

# ---- POSITIVE: novel_unseen (30) — outside BOTH vocabularies, real stress test ----
novel_templates = [
    "If a claim is ever filed against {b} because of something {a} did under this Agreement, "
    "{a} will make sure {b} does not end up paying for it.",
    "{a} promises that {b} will never be left holding the bag for costs tied to {a}'s mistakes on this project.",
    "In the event {b} faces a lawsuit traceable to {a}'s work, {a} will step in and foot the bill for {b}'s defense and any judgment.",
    "{a} accepts that any expense {b} incurs defending a claim arising from {a}'s conduct is {a}'s expense to carry, not {b}'s.",
    "Where a third party comes after {b} on account of {a}'s performance, {a} will square things up with {b} financially.",
    "{a} will see to it that {b} comes out whole, dollar for dollar, on any claim connected to {a}'s obligations here.",
    "{a} is on the hook to keep {b} out of pocket for any losses stemming from claims tied to this engagement.",
    "Any financial fallout {b} experiences from a claim linked to {a}'s actions under this contract falls to {a} to resolve.",
    "{a} will pick up wherever {b} is left exposed by a claim arising out of {a}'s performance of this Agreement.",
    "{a} shall not allow {b} to bear any cost of a claim that traces back to {a}'s conduct under this Agreement.",
]
for tpl in novel_templates:
    for a, b in ROLES[:3]:
        add("novel_unseen", "POSITIVE", tpl.format(a=a, b=b), "genuinely novel phrasing, outside both vocabularies")

# ---- NEGATIVE: hard negatives (80+) ----
neg_templates = [
    ("explicit_negation", "No indemnification obligation of any kind is created by this Agreement between {a} and {b}."),
    ("insurance", "{a} shall maintain commercial general liability insurance with coverage of not less than $1,000,000 per occurrence."),
    ("warranty", "{a} warrants that the goods delivered to {b} will be free from material defects for a period of twelve months."),
    ("limitation_of_liability", "In no event shall {a}'s aggregate liability to {b} under this Agreement exceed the fees paid in the preceding twelve months."),
    ("confidentiality", "{a} shall not disclose {b}'s Confidential Information to any third party without prior written consent."),
    ("force_majeure", "Neither party shall be liable for delay or failure to perform caused by events beyond its reasonable control."),
    ("termination", "Either party may terminate this Agreement upon thirty days' prior written notice to the other party."),
    ("assignment", "{a} may not assign this Agreement without the prior written consent of {b}."),
    ("ip_ownership", "All intellectual property created by {a} in the course of performing the services shall be owned exclusively by {b}."),
    ("ordinary_performance", "{a} shall perform the services in a professional and workmanlike manner consistent with industry standards."),
    ("risk_of_loss", "Risk of loss for goods in transit shall pass to {b} upon delivery to the common carrier."),
    ("payment_terms", "{b} shall pay {a} within thirty days of receipt of a correct invoice for services rendered."),
    ("non_solicitation", "During the term and for one year thereafter, {a} shall not solicit for employment any employee of {b}."),
    ("governing_law", "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware."),
    ("self_liability_only", "{a} shall be solely responsible for its own costs and expenses incurred in performing this Agreement."),
    ("notice", "All notices under this Agreement shall be delivered in writing to the addresses set forth on the signature page."),
]
for kind, tpl in neg_templates:
    for a, b in ROLES[:5]:
        add(kind, "NEGATIVE", tpl.format(a=a, b=b), f"hard negative — {kind}")

OUT = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a9_1_benchmark.json"
OUT.write_text(json.dumps(CASES, indent=2))
pos = sum(1 for c in CASES if c["label"] == "POSITIVE")
neg = sum(1 for c in CASES if c["label"] == "NEGATIVE")
print(f"Wrote {len(CASES)} cases ({pos} positive / {neg} negative) to {OUT}")
fam_counts = {}
for c in CASES:
    fam_counts[c["family"]] = fam_counts.get(c["family"], 0) + 1
print(fam_counts)
