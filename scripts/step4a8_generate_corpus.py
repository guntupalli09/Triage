#!/usr/bin/env python3
"""Step 4A.8 corpus generator. Produces the independent held-out corpus
BEFORE any execution against production code — every case's ground truth
is decided here, by the author, from the template's own known legal
structure, never inferred from system output (Phase 1/Rule #4).

Domains/entities used here are deliberately NOT drawn from any prior
TriageCounsel corpus (Step 4A.2/4A.4/4A.6/4A.7.x) — verified by hand
against the domain list used in those corpora before writing this file.
"""
import json
import random
from pathlib import Path

random.seed(48810)  # fixed seed so the corpus is reproducible if regenerated before locking

OUT = Path(__file__).resolve().parent.parent / "benchmarks"

CASES = []
_ids_seen = set()


def add(id_, adapter, tier, families, text, kwargs, expected_facts, expected_result,
        review, presence, rationale, severity_if_wrong, note=""):
    assert id_ not in _ids_seen, f"duplicate id {id_}"
    _ids_seen.add(id_)
    CASES.append(dict(
        id=id_, adapter=adapter, tier=tier, families=families, text=text, kwargs=kwargs,
        expected_facts=expected_facts, expected_result=expected_result,
        review=review,  # "AUTOMATIC" | "SHOULD_REVIEW"
        presence=presence,  # dict or None
        rationale=rationale, severity_if_wrong=severity_if_wrong, note=note,
    ))

# ============================================================================
# LIABILITY — target >= 80 cases (Families A, B, C, F, G, H, I)
# Fresh domains: commercial laundry, industrial welding, elevator maintenance,
# pest control, medical billing, court reporting, forklift leasing, vending,
# janitorial staffing, well drilling, fire suppression, crane rental,
# scaffold erection, EV charging install, 3D printing services, mobile
# notary, self-storage management, upholstery restoration, appliance
# repair, staffing agency, freight forwarding, cold storage warehousing,
# uniform rental, alarm monitoring, golf course maintenance, marina slip
# rental, hunting guide services, ATM servicing, coin laundry route.
# ============================================================================

L_DOMAINS = [
    ("Meridian Commercial Laundry Services", "Client", "laundry-processing", "sell_side"),
    ("Ironforge Industrial Welding Corp", "Fabricator's Customer", "welding-inspection", "sell_side"),
    ("Ascendia Elevator Maintenance Group", "Building Owner", "elevator-service", "sell_side"),
    ("Bramwell Pest Control Franchising LLC", "Franchisee", "pest-treatment", "buy_side"),
    ("Northcastle Medical Billing Outsourcing", "Physician Group", "claims-processing", "sell_side"),
    ("Verity Court Reporting Services", "Law Firm Client", "transcription", "sell_side"),
    ("Highline Forklift Leasing Co", "Warehouse Operator", "equipment-lease", "sell_side"),
    ("Palisade Vending Route Partners", "Site Host", "vending-commission", "buy_side"),
    ("Cobalt Janitorial Staffing Solutions", "Facility Manager", "janitorial-service", "sell_side"),
    ("Deepwell Drilling & Water Systems", "Landowner", "well-drilling", "sell_side"),
    ("Redoubt Fire Suppression Systems Inc", "Property Manager", "inspection", "sell_side"),
    ("Talus Crane Rental Corporation", "General Contractor", "crane-rental", "sell_side"),
    ("Steadfast Scaffold Erection Services", "Construction Manager", "scaffold-rental", "sell_side"),
    ("Voltframe EV Charging Installation LLC", "Property Developer", "installation", "sell_side"),
    ("Latticework 3D Printing Services", "Client", "print-production", "sell_side"),
    ("Signet Mobile Notary Network", "Title Company", "notary-service", "sell_side"),
    ("Harborline Self-Storage Management Co", "Facility Owner", "management-fee", "sell_side"),
    ("Quillfeather Upholstery Restoration Studio", "Customer", "restoration", "sell_side"),
    ("Brassbound Appliance Repair Guild", "Homeowner Association", "repair-service", "sell_side"),
    ("Ninefold Staffing Agency Partners", "Host Employer", "placement-fee", "sell_side"),
    ("Cargobrook Freight Forwarding LLC", "Shipper", "forwarding-fee", "sell_side"),
    ("Glacierpoint Cold Storage Warehousing", "Distributor", "storage-fee", "sell_side"),
    ("Ledgerstone Uniform Rental Services", "Restaurant Group", "rental-fee", "sell_side"),
    ("Wardenclyffe Alarm Monitoring Corp", "Subscriber", "monitoring-fee", "sell_side"),
    ("Fairgreen Golf Course Maintenance Co", "Country Club", "maintenance-fee", "sell_side"),
    ("Anchorwatch Marina Slip Rental LLC", "Boat Owner", "slip-fee", "sell_side"),
    ("Timberline Hunting Guide Services", "Client", "guide-fee", "sell_side"),
    ("Coinvault ATM Servicing Network", "Retail Host", "servicing-fee", "sell_side"),
    ("Suddspring Coin-Operated Laundry Route", "Property Owner", "route-commission", "buy_side"),
    ("Brightlatch Access Control Installation", "Property Manager", "installation-fee", "sell_side"),
]

# Family A — role attribution, ordinary + adversarial vocabulary
ROLE_PAIRS_ORDINARY = [
    ("Buyer", "Seller", "buy_side"), ("Customer", "Provider", "buy_side"),
    ("Client", "Consultant", "buy_side"), ("Licensee", "Licensor", "buy_side"),
    ("Distributor", "Supplier", "buy_side"), ("Purchaser", "Vendor", "buy_side"),
    ("Recipient", "Contractor", "buy_side"), ("Company", "Provider", "sell_side"),
]
ROLE_PAIRS_UNMAPPED = [
    ("Grantee", "Grantor"), ("Obligee", "Obligor"), ("Chargee", "Chargor"),
    ("Cessionary", "Cedent"), ("Transferee", "Transferor"),
]

tier1_count = 0
for i, (entity, counterparty, basis, side) in enumerate(L_DOMAINS):
    mult = [1, 1, 2, 2, 3][i % 5]
    add(
        f"S48-L-T1-{i+1:02d}", "liability", 1, ["B"],
        f"9. Limitation of Liability. {entity}'s aggregate liability to {counterparty} arising out of or "
        f"relating to this Agreement shall not exceed {mult} times the total {basis} fees paid by "
        f"{counterparty} in the twelve (12) months preceding the claim.",
        {"contract_side": side},
        {"cap_multiplier": mult, "cap_basis": f"{basis} fees"},
        "ACCEPT" if mult == 1 else ("ACCEPT_WITH_NOTE" if mult == 2 else "NEGOTIATE"),
        "AUTOMATIC", None,
        "Ordinary single-sentence multiplier cap, unambiguous basis, standard commercial phrasing.",
        "S2",
    )
    tier1_count += 1

# Tier 1 — Family A ordinary role-pair variety (fixed dollar caps this time)
for i, (buy, sell, side) in enumerate(ROLE_PAIRS_ORDINARY):
    amt = [50000, 100000, 250000, 500000, 750000, 1000000, 150000, 300000][i % 8]
    add(
        f"S48-L-T1-RA-{i+1:02d}", "liability", 1, ["A", "B"],
        f"Limitation of Liability. {sell}'s total liability to {buy} under this Agreement shall in no "
        f"event exceed ${amt:,}.",
        {"contract_side": side},
        {"cap_fixed_amount": amt},
        "ESCALATE",
        "AUTOMATIC", None,
        f"Ordinary generic-vocabulary role pair ({sell}/{buy}), unambiguous fixed-dollar cap; fixed-dollar "
        f"caps require manual comparison against policy's own dollar ceiling, hence ESCALATE not ACCEPT.",
        "S2",
    )
    tier1_count += 1

print("tier1 running count:", tier1_count)

# ----------------------------------------------------------------------------
# Liability Tier 2 — structurally difficult (long sentences, parentheticals,
# multi-word roles, single-level cross-references, passive voice, defined
# terms, nested provisos that DO resolve cleanly)
# ----------------------------------------------------------------------------

L_T2 = []

L_T2.append(dict(
    id="S48-L-T2-01", tier=2, families=["B"],
    text=(
        "9. Limitation of Liability. Notwithstanding anything to the contrary contained elsewhere in this "
        "Agreement (including, without limitation, Section 14 hereof), and except as otherwise expressly "
        "provided in Section 9.3, the aggregate liability of Cormorant Bay Ship Chandlery Supply Corp, "
        "whether arising in contract, tort (including negligence), strict liability, or otherwise, to "
        "Fleet Operator shall not, under any circumstances, exceed an amount equal to two (2) times the "
        "aggregate supply fees actually paid by Fleet Operator during the twelve (12) month period "
        "immediately preceding the event giving rise to such liability."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 2, "cap_basis": "supply fees"},
    expected_result="ACCEPT_WITH_NOTE", review="AUTOMATIC", presence=None,
    rationale="Long, heavily-qualified sentence with multiple parenthetical carve-out references, but the "
              "governing multiplier (2x) and basis (supply fees) are stated once, unambiguously, at the end.",
    severity_if_wrong="S2",
))

L_T2.append(dict(
    id="S48-L-T2-02", tier=2, families=["A", "B"],
    text=(
        "9. Limitation of Liability. The aggregate liability of Northgate Regional Ambulance Billing "
        "Consortium, LLC (a Delaware limited liability company, together with its wholly-owned "
        "subsidiaries, \"Consortium\"), to County Emergency Services Authority, arising under or in "
        "connection with this Agreement, shall not exceed one (1) times the annual billing-processing "
        "fees paid by County Emergency Services Authority to Consortium hereunder."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1, "cap_basis": "billing-processing fees"},
    expected_result="ACCEPT", review="AUTOMATIC", presence=None,
    rationale="Elaborate but harmless entity-description parenthetical (defined-term alias, subsidiary "
              "language) must not be misread as conflicting directional evidence — same shape validated "
              "in Step 4A.7.2's benchmark, tested here on fresh domain/entities.",
    severity_if_wrong="S3",
))

L_T2.append(dict(
    id="S48-L-T2-03", tier=2, families=["B", "H"],
    text=(
        "9. Limitation of Liability. Aggregate liability shall not exceed the Cap Amount. The \"Cap "
        "Amount\" means one (1) times the annual inspection fees paid, as further itemized for reference "
        "purposes in the fee schedule attached as Schedule 1."
    ),
    kwargs={"contract_side": "buy_side"},
    expected_facts={"cap_multiplier": 1, "cap_basis": "annual inspection fees"},
    expected_result="ACCEPT", review="AUTOMATIC", presence=None,
    rationale="Single, consistent definition with a harmless 'for reference purposes' cross-reference to "
              "a schedule — must resolve automatically, not be mistaken for a conflicting-definition or "
              "chained-delegation shape (no second value, no 'not included' disclosure).",
    severity_if_wrong="S3",
))

L_T2.append(dict(
    id="S48-L-T2-04", tier=2, families=["B"],
    text=(
        "9. Limitation of Liability. Except for claims arising from a party's breach of its "
        "confidentiality obligations under Section 11 (which shall be governed exclusively by Section "
        "11.6), and subject in all respects to Section 9.4 below, the liability of Praxisfield Clinical "
        "Trial Logistics Inc., in the aggregate, to Sponsor shall be limited to, and shall not exceed, "
        "three (3) times the logistics-coordination fees paid to Praxisfield Clinical Trial Logistics "
        "Inc. by Sponsor under this Agreement."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 3, "cap_basis": "logistics-coordination fees"},
    expected_result="NEGOTIATE", review="AUTOMATIC", presence=None,
    rationale="Multiple carve-out/cross-reference distractors surrounding a single, clean, extractable "
              "multiplier — the confidentiality carve-out is a bystander clause, not itself a competing "
              "cap value.",
    severity_if_wrong="S2",
))

L_T2.append(dict(
    id="S48-L-T2-05", tier=2, families=["B"],
    text=(
        "9. Limitation of Liability. It is agreed by and between the parties that, in no event and under "
        "no theory of liability whatsoever, shall the total aggregate liability incurred by Wrenholt "
        "Specialty Chemical Blending Co. to Formulator, whether such liability arises from breach of "
        "contract, breach of warranty, indemnification, tort, or any other legal or equitable theory, "
        "exceed a sum equal to two (2) times the total blending fees actually invoiced to and paid by "
        "Formulator during the immediately preceding twelve (12) calendar months."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 2, "cap_basis": "blending fees"},
    expected_result="ACCEPT_WITH_NOTE", review="AUTOMATIC", presence=None,
    rationale="Extremely verbose passive-voice legalese wrapper around a single unambiguous value; tests "
              "whether basis extraction survives heavy syntactic padding.",
    severity_if_wrong="S2",
))

L_T2.append(dict(
    id="S48-L-T2-06", tier=2, families=["B"],
    text=(
        "9. Limitation of Liability. Subject to Section 9.2 (Exceptions), the liability of Kettlewell "
        "Precision Instrument Calibration Labs for any and all claims arising out of a single occurrence "
        "or a series of related occurrences shall not, in the aggregate, exceed one (1) times the annual "
        "calibration-service fees paid by Client; provided, further, that this limitation shall apply "
        "regardless of the form of action."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1, "cap_basis": "calibration-service fees"},
    expected_result="ACCEPT", review="AUTOMATIC", presence=None,
    rationale="Nested proviso ('provided, further, that...') is a bystander clarifying clause about the "
              "cap's SCOPE (form of action), not a competing value — must not trigger ambiguity escalation.",
    severity_if_wrong="S2",
))

L_T2.append(dict(
    id="S48-L-T2-07", tier=2, families=["B"],
    text=(
        "9. Limitation of Liability. Aggregate liability shall not exceed either (a) two (2) times the "
        "annual maintenance fees paid, or (b) fifty thousand dollars ($50,000), whichever amount is "
        "greater, as determined by comparing the two figures at the time a claim is finally adjudicated."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"structure": "greater_of", "component_a_multiplier": 2, "component_b_fixed": 50000},
    expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
    rationale="Greater-of structure mixing a multiplier and a fixed dollar amount without a known annual "
              "fee figure — cannot be resolved deterministically without the actual dollar value.",
    severity_if_wrong="S3",
))

L_T2.append(dict(
    id="S48-L-T2-08", tier=2, families=["B", "H"],
    text=(
        "9. Limitation of Liability. Aggregate liability shall not exceed the amount set forth in Table 1 "
        "below.\n\nTable 1 — Liability Cap\n| Contract Year | Multiplier |\n| Year 1 | 1x annual fees |\n"
        "| Year 2 | 1x annual fees |\n| Year 3+ | 1x annual fees |"
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1, "cap_basis": "annual fees"},
    expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
    rationale="Table-formatted cap value — every row states the SAME 1x value, but table-cell extraction "
              "is a structurally unfamiliar format the extractor was never validated against; ground truth "
              "is that a human reviewer should confirm table-based structured data was read correctly "
              "before automation, even though the value itself happens to be unambiguous.",
    severity_if_wrong="S1",
))

L_T2.append(dict(
    id="S48-L-T2-09", tier=2, families=["A", "B"],
    text=(
        "9. Limitation of Liability. Silverquill Regulatory Affairs Consulting Group's (\"Consultant\") "
        "aggregate liability to Pharma Sponsor Client (\"Sponsor\"); provided that, for purposes of this "
        "Section only, Consultant and its Affiliates shall be treated as a single entity; shall not exceed "
        "one (1) times the annual consulting fees paid by Sponsor."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1, "cap_basis": "annual consulting fees"},
    expected_result="ACCEPT", review="AUTOMATIC", presence=None,
    rationale="Semicolon-delimited proviso interposed directly between subject and predicate — tests "
              "whether the extractor's multiplier-to-subject binding survives an interposed clause using "
              "semicolons rather than the more common comma/parenthetical shape.",
    severity_if_wrong="S2",
))

L_T2.append(dict(
    id="S48-L-T2-10", tier=2, families=["B"],
    text=(
        "9. Limitation of Liability. Total liability of Fenwright Marine Salvage & Towing Operations "
        "shall be capped, in the aggregate and without exception, at an amount equal to one and one-half "
        "(1.5) times the annual towing-service fees paid by Vessel Owner under this Agreement."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1.5, "cap_basis": "towing-service fees"},
    expected_result="ACCEPT", review="AUTOMATIC", presence=None,
    rationale="Fractional multiplier spelled out in words with the numeral in parentheses ('one and "
              "one-half (1.5)') — tests numeral-in-parenthetical extraction robustness.",
    severity_if_wrong="S2",
))

for c in L_T2:
    add(c["id"], "liability", c["tier"], c["families"], c["text"], c["kwargs"],
        c["expected_facts"], c["expected_result"], c["review"], c["presence"],
        c["rationale"], c["severity_if_wrong"])

print("after L_T2:", len(CASES))

# ----------------------------------------------------------------------------
# Liability Tier 3 — adversarial (Families A-unmapped, C, F, G, H, I, N-compound)
# ----------------------------------------------------------------------------

L_T3 = []

# Family A adversarial — unmapped role vocabulary, directional
for i, (r1, r2) in enumerate(ROLE_PAIRS_UNMAPPED):
    L_T3.append(dict(
        id=f"S48-L-T3-RA-{i+1:02d}", tier=3, families=["A"],
        text=(
            f"1. Definitions. '{r1}' means the party receiving the benefit conferred hereunder, and "
            f"'{r2}' means the party conferring such benefit.\n\n9. Limitation of Liability. "
            f"{r2}'s aggregate liability to {r1} shall not exceed two (2) times the annual service fees paid."
        ),
        kwargs={"contract_side": "sell_side"},
        expected_facts={"cap_multiplier": 2, "role_attribution": "unresolved"},
        expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
        rationale=f"'{r1}'/'{r2}' are unusual, legally legitimate role vocabulary not in any generic "
                  f"buy/sell mapping — direct generalization test of the A6-L-52/Step-4A.7.2 role-"
                  f"attribution fix on fresh vocabulary.",
        severity_if_wrong="S3",
    ))

# Family C — ownership/contamination distractors
L_T3.append(dict(
    id="S48-L-T3-C-01", tier=3, families=["C"],
    text=(
        "9. Limitation of Liability. Aggregate liability of Thornquist Aerial Drone Inspection Services "
        "shall not exceed one (1) times the annual inspection fees paid. Separately, under the "
        "Equipment Insurance Rider attached as Exhibit C, Thornquist maintains commercial general "
        "liability coverage with a per-occurrence limit of $2,000,000, which is unrelated to the "
        "contractual cap stated in this Section."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1, "cap_basis": "annual inspection fees"},
    expected_result="ACCEPT", review="AUTOMATIC", presence=None,
    rationale="Insurance-limit distractor ($2,000,000) explicitly disclaimed as unrelated — must not be "
              "adopted as the liability cap.",
    severity_if_wrong="S4",
))
L_T3.append(dict(
    id="S48-L-T3-C-02", tier=3, families=["C"],
    text=(
        "9. Limitation of Liability. Client acknowledges a minimum annual purchase commitment of "
        "$120,000. Vendor's aggregate liability under this Agreement shall not exceed one (1) times "
        "the annual license fees paid by Client."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1, "cap_basis": "annual license fees"},
    expected_result="ACCEPT", review="AUTOMATIC", presence=None,
    rationale="Minimum-purchase-commitment dollar figure ($120,000) sits in the same provision but is a "
              "commercial minimum, not a liability cap value — must not be adopted as a fixed-dollar cap.",
    severity_if_wrong="S4",
))
L_T3.append(dict(
    id="S48-L-T3-C-03", tier=3, families=["C"],
    text=(
        "9. Limitation of Liability. Vendor shall pay liquidated damages of $10,000 per day for each day "
        "of delay beyond the agreed delivery date, subject to a liquidated-damages cap of $150,000. "
        "Separately, Vendor's aggregate liability under this Agreement (exclusive of the liquidated "
        "damages addressed above) shall not exceed two (2) times the annual purchase-order value."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 2, "cap_basis": "annual purchase-order value"},
    expected_result="ACCEPT_WITH_NOTE", review="AUTOMATIC", presence=None,
    rationale="Liquidated-damages dollar figures ($10,000/day, $150,000 cap) are a DIFFERENT, explicitly "
              "carved-out remedy — must not be adopted as the general liability cap, which is the "
              "separately-stated 2x multiplier.",
    severity_if_wrong="S4",
))

# Family F — conditional applicability
L_T3.append(dict(
    id="S48-L-T3-F-01", tier=3, families=["F"],
    text=(
        "9. Limitation of Liability. Ashworth Data Migration Specialists' aggregate liability to Client "
        "shall not exceed one (1) times the annual migration fees paid, unless Client has elected the "
        "Premium Migration Package under the applicable Order Form, in which case the cap shall instead "
        "be three (3) times such fees; the parties have not yet executed an Order Form specifying which "
        "package applies."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": "conditional (1x or 3x, election not made)"},
    expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
    rationale="Cap value depends on a future election that has not yet been made — the base value cannot "
              "be silently treated as the governing figure.",
    severity_if_wrong="S3",
))
L_T3.append(dict(
    id="S48-L-T3-F-02", tier=3, families=["F"],
    text=(
        "9. Limitation of Liability. Bellcastle Structural Engineering Associates' aggregate liability "
        "shall not exceed one (1) times the annual design fees paid, PROVIDED THAT this limitation applies "
        "only for so long as Bellcastle maintains professional liability insurance in the amount required "
        "by Section 12, a condition Bellcastle represents but which has not yet been independently "
        "confirmed as of the date of this excerpt."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": "conditional, precondition unverified"},
    expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
    rationale="Direct generalization test of the conditional-unverified-precondition mechanism "
              "(Step 4A.7.4) on fresh domain/phrasing.",
    severity_if_wrong="S3",
))

# Family G — self-flagged/unresolved scope
L_T3.append(dict(
    id="S48-L-T3-G-01", tier=3, families=["G"],
    text=(
        "9. Limitation of Liability. Aggregate liability shall not exceed one (1) times the annual fees "
        "paid, it being expressly noted that the parties have not yet agreed whether 'annual fees' as "
        "used in this Section includes amounts paid under separately-executed statements of work."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1, "basis_ambiguity": "self-flagged, unresolved"},
    expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
    rationale="Fresh phrasing of the self-flagged basis-value-ambiguity family — the document itself "
              "states the scope of 'fees' is unresolved.",
    severity_if_wrong="S3",
))
L_T3.append(dict(
    id="S48-L-T3-G-02", tier=3, families=["G"],
    text=(
        "9. Limitation of Liability. Vantablack Optical Coatings LLC's liability to Client shall be "
        "limited as the parties shall mutually agree in a forthcoming amendment; no such amendment has "
        "been executed as of the date of this excerpt, and in its absence no numeric cap is currently "
        "stated."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": None, "clause_status": "no cap currently stated, deferred"},
    expected_result="MUST_REDLINE", review="SHOULD_REVIEW", presence=None,
    rationale="No enforceable numeric cap is stated at all; the clause openly defers to a future, "
              "unexecuted amendment — company policy requires a stated cap.",
    severity_if_wrong="S2",
))

# Family H — definitions
L_T3.append(dict(
    id="S48-L-T3-H-01", tier=3, families=["H"],
    text=(
        "9. Limitation of Liability. Aggregate liability shall not exceed the Liability Ceiling. The "
        "'Liability Ceiling' is defined in Section 9.1 as one (1) times the annual fees paid, and is "
        "separately defined in Section 22.4 (Data Breach Addendum) as three (3) times the annual fees "
        "paid."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": "conflicting (1x vs 3x)"},
    expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
    rationale="Same self-defined-term-given-two-values shape the Step 4A.5/4A.7.1 fix targets, fresh "
              "domain/section numbers.",
    severity_if_wrong="S3",
))
L_T3.append(dict(
    id="S48-L-T3-H-02", tier=3, families=["H"],
    text=(
        "9. Limitation of Liability. Aggregate liability shall not exceed the Ceiling Value. 'Ceiling "
        "Value' means $75,000, as also confirmed for consistency in Section 30 (Miscellaneous)."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_fixed_amount": 75000},
    expected_result="ESCALATE", review="AUTOMATIC", presence=None,
    rationale="Near-miss negative control: single consistent definition with a harmless cross-reference "
              "explicitly confirming (not conflicting with) the same value — must resolve automatically, "
              "not be mistaken for a conflicting-definition shape.",
    severity_if_wrong="S3",
))

# Family I — chained delegation
L_T3.append(dict(
    id="S48-L-T3-I-01", tier=3, families=["I"],
    text=(
        "9. Limitation of Liability. Aggregate liability shall not exceed one (1) times the annual fees "
        "paid, calculated per the methodology set forth in Attachment D, which Attachment D in turn "
        "defers to the then-current pricing methodology maintained on Vendor's customer portal (not "
        "included in this excerpt)."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1, "basis": "chained delegation to external, unincluded source"},
    expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
    rationale="Two-level chained delegation ending in an external, unincluded document — fresh phrasing "
              "('Attachment D' + 'customer portal') generalization test.",
    severity_if_wrong="S4",
))
L_T3.append(dict(
    id="S48-L-T3-I-02", tier=3, families=["I"],
    text=(
        "9. Limitation of Liability. Aggregate liability shall not exceed one (1) times the annual fees "
        "paid, as calculated under Exhibit F.",
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1, "basis": "single-level reference only, no chain"},
    expected_result="ACCEPT", review="AUTOMATIC", presence=None,
    rationale="Near-miss negative control: only ONE level of cross-reference (no second 'which Exhibit F "
              "itself references...' hop) — must resolve automatically.",
    severity_if_wrong="S3",
))

# Family N — compound (liability), 2-3 mechanisms each
L_T3.append(dict(
    id="S48-L-T3-N-01", tier=3, families=["A", "I", "N"],
    text=(
        "1. Definitions. 'Obligee' means the party to whom performance is owed, and 'Obligor' means the "
        "party owing such performance.\n\n9. Limitation of Liability. Obligor's aggregate liability to "
        "Obligee shall not exceed the amount set forth in Section 4, which Section 4 itself references "
        "the rate schedule maintained by Obligor's finance department (not included in this excerpt)."
    ),
    kwargs={"contract_side": "buy_side"},
    expected_facts={"role_attribution": "unresolved", "basis": "also chained-delegated, unresolved"},
    expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
    rationale="Compound: unmapped role-attribution vocabulary stacked with chained delegation — either "
              "mechanism alone would force review; tests both fire without conflicting.",
    severity_if_wrong="S4",
))
L_T3.append(dict(
    id="S48-L-T3-N-02", tier=3, families=["F", "H", "N"],
    text=(
        "9. Limitation of Liability. Aggregate liability shall not exceed the Coverage Amount. 'Coverage "
        "Amount' means, for purposes of the standard-claims process described in Section 9.1, one (1) "
        "times the annual fees paid, and means, for purposes of the expedited-claims process described in "
        "Section 9.5, two (2) times the annual fees paid, PROVIDED THAT which process applies has not yet "
        "been determined as of this excerpt."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": "conflicting AND conditionally selected, unresolved"},
    expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
    rationale="Compound: conflicting defined term stacked with conditional-applicability (which process "
              "applies is itself unresolved) — a THREE-mechanism-adjacent stack.",
    severity_if_wrong="S3",
))
L_T3.append(dict(
    id="S48-L-T3-N-03", tier=3, families=["C", "G", "N"],
    text=(
        "9. Limitation of Liability. Aggregate liability shall not exceed one (1) times the annual fees "
        "paid, it being unresolved whether this figure includes the separately-itemized $25,000 annual "
        "platform-access fee described in Schedule B, which itemization is provided for billing "
        "transparency only and does not itself constitute a distinct liability cap."
    ),
    kwargs={"contract_side": "sell_side"},
    expected_facts={"cap_multiplier": 1, "basis_ambiguity": "self-flagged, distractor dollar figure present"},
    expected_result="REQUIRES_REVIEW", review="SHOULD_REVIEW", presence=None,
    rationale="Compound: an ownership/contamination distractor dollar figure ($25,000) combined with a "
              "genuine self-flagged basis-scope ambiguity — the $25,000 must NOT be adopted as the cap, "
              "but the clause should still escalate because of the explicit self-flagged ambiguity about "
              "the 1x basis itself.",
    severity_if_wrong="S3",
))

for c in L_T3:
    add(c["id"], "liability", c["tier"], c["families"], c["text"], c["kwargs"],
        c["expected_facts"], c["expected_result"], c["review"], c["presence"],
        c["rationale"], c["severity_if_wrong"])

print("after L_T3:", len(CASES))

# ----------------------------------------------------------------------------
# Liability Tier 2 — additional (push liability total past 75)
# ----------------------------------------------------------------------------
L_T2B = []
L_T2B_DOMAINS = [
    ("Quarryline Industrial Sandblasting Co", "Shipyard Client", "sandblasting fees"),
    ("Falconcrest Rooftop Solar Maintenance", "Building Owner", "annual maintenance fees"),
    ("Ridgemont Commercial Window Washing", "Property Manager", "window-washing fees"),
    ("Sablewood Custom Cabinetry Studio", "Homeowner", "cabinetry fees"),
    ("Copperline Metal Recycling Services", "Municipal Client", "processing fees"),
    ("Thornfield Livestock Transport Co", "Rancher", "transport fees"),
    ("Glasswing Aquarium Design & Build", "Facility Owner", "design fees"),
    ("Redberry Orchard Equipment Repair", "Grower", "repair fees"),
    ("Millbrook Textile Dyeing Works", "Apparel Brand", "dyeing fees"),
    ("Stonegate Playground Equipment Install", "School District", "installation fees"),
]
for i, (entity, cp, basis) in enumerate(L_T2B_DOMAINS):
    mult = [1, 2, 1, 3, 2][i % 5]
    L_T2B.append(dict(
        id=f"S48-L-T2B-{i+1:02d}", tier=2, families=["B"],
        text=(
            f"9. Limitation of Liability. Subject to the exceptions in Section 9.2, and without limiting "
            f"any other right or remedy the {cp} may have at law or in equity, the total aggregate "
            f"liability of {entity} arising out of this Agreement, whether in contract or tort, shall not "
            f"exceed {mult} times the {basis} paid by the {cp} during the preceding contract year."
        ),
        kwargs={"contract_side": "sell_side"},
        expected_facts={"cap_multiplier": mult, "cap_basis": basis},
        expected_result="ACCEPT" if mult == 1 else ("ACCEPT_WITH_NOTE" if mult == 2 else "NEGOTIATE"),
        review="AUTOMATIC", presence=None,
        rationale="Moderate-length sentence with an 'other rights/remedies' savings-clause distractor "
                  "preceding the cap — must not be misread as part of the cap value.",
        severity_if_wrong="S2",
    ))

for c in L_T2B:
    add(c["id"], "liability", c["tier"], c["families"], c["text"], c["kwargs"],
        c["expected_facts"], c["expected_result"], c["review"], c["presence"],
        c["rationale"], c["severity_if_wrong"])

print("after L_T2B:", len(CASES))

# ============================================================================
# INDEMNIFICATION — target >= 80 cases (Families A, D, E(>=30), F, G, H, I, N)
# ============================================================================

I_DOMAINS = [
    ("Palewood Custom Furniture Makers", "Retail Buyer", "sell_side"),
    ("Kestrelrun Skydiving Adventures", "Jumper", "sell_side"),
    ("Vantagepoint Home Inspection Services", "Homebuyer", "sell_side"),
    ("Ferrowine Cellar Climate Systems", "Vineyard Owner", "sell_side"),
    ("Hollowmere Escape Room Ventures", "Guest", "sell_side"),
    ("Brackenfield Axe-Throwing Lounge", "Patron", "sell_side"),
    ("Coppertide Boat Detailing Services", "Boat Owner", "sell_side"),
    ("Wrenfield Pet Grooming Franchise Group", "Franchisee", "buy_side"),
    ("Ashgate Commercial Kitchen Equipment Repair", "Restaurant Group", "sell_side"),
    ("Larkfeather Piano Tuning Guild", "Concert Hall", "sell_side"),
    ("Thistledown Mold Remediation Corp", "Property Owner", "sell_side"),
    ("Grimshaw Chimney Sweep Services", "Homeowner", "sell_side"),
    ("Ravenglass Fence Installation Co", "Property Owner", "sell_side"),
    ("Nightspire Karaoke Equipment Rental", "Event Host", "sell_side"),
    ("Duskwillow Bounce House Rentals", "Party Planner", "sell_side"),
]

# Family D — indemnification recognition with genuinely fresh drafting
D_SYNONYM_TEMPLATES = [
    ("shall be responsible for, and shall reimburse {ctp} in full for, any losses arising from",
     "reimbursement"),
    ("shall assume all liability for, and undertakes to make {ctp} whole in respect of,",
     "loss-bearing"),
    ("shall stand in {ctp}'s place in defending against, and shall bear the cost of resolving,",
     "duty to defend"),
    ("shall protect {ctp} from, and satisfy on {ctp}'s behalf, any third-party claim arising from",
     "third-party claims"),
]
for i, (entity, ctp, side) in enumerate(I_DOMAINS):
    template, concept = D_SYNONYM_TEMPLATES[i % len(D_SYNONYM_TEMPLATES)]
    clause = template.format(ctp=ctp)
    add(
        f"S48-I-T1-D-{i+1:02d}", "indemnification", 1, ["D"],
        f"8. Risk Allocation. {entity} {clause} {entity}'s negligent acts or omissions in performing "
        f"services under this Agreement, up to a cap of one (1) times the annual fees paid.",
        {"contract_side": side},
        {"exposure_role": entity, "monetary_multiplier": 1, "concept": concept},
        "ACCEPT", "AUTOMATIC", None,
        f"Genuinely fresh indemnification-idiom phrasing ({concept}) not drawn from any prior corpus's "
        f"synonym family — tests whether recognition generalizes beyond the closed synonym list.",
        "S3" if side == "sell_side" else "S2",
    )

print("after I_D:", len(CASES))

# ============================================================================
# INDEMNIFICATION — Family E, reciprocal semantics, >= 30 cases
# ============================================================================

E_DOMAIN_PAIRS = [
    ("Amberline Custom Framing Studio", "Gallery"), ("Brookstone Artisan Cheese Cave", "Distributor"),
    ("Cindergate Blacksmith Forge Co", "Retailer"), ("Driftwood Kayak Outfitters", "Guide Service"),
    ("Emberlight Candle Manufacturing", "Wholesaler"), ("Frostpine Christmas Tree Farm", "Lot Operator"),
    ("Glimmerstone Jewelry Repair Guild", "Retail Partner"), ("Hollowbrook Beekeeping Supply Co", "Apiary"),
    ("Ironvale Blacksmithing School", "Student Cooperative"), ("Juniper Ridge Distillery Consulting", "Client Distillery"),
    ("Kettlecove Fish Smoking House", "Market"), ("Larkspur Herbal Tea Blending Co", "Cafe Chain"),
    ("Mossgate Terrarium Design Studio", "Retail Partner"), ("Nettlecrest Mushroom Farm", "Restaurant Group"),
    ("Oakenfold Barrel Cooperage", "Winery"), ("Pinewhistle Sled Dog Adventures", "Tour Operator"),
    ("Quailridge Poultry Processing", "Distributor"), ("Rimewood Ice Sculpture Studio", "Event Planner"),
    ("Saltmarsh Oyster Farming Co", "Restaurant Group"), ("Thistlebrook Weaving Cooperative", "Retail Partner"),
]

# 20 named-pair reciprocal, various asymmetry mechanisms
E_MECHS = [
    ("monetary", "up to a cap of one (1) times the fees paid", "up to a cap of three (3) times the fees paid"),
    ("scope", "for third-party claims only", "for both third-party and first-party claims"),
    ("defense_control", "with {a} controlling the defense", "with {b} controlling the defense"),
    ("trigger", "arising from data breach only", "arising from any breach of this Agreement"),
]
for i, (a, b) in enumerate(E_DOMAIN_PAIRS):
    mech, term_a, term_b = E_MECHS[i % len(E_MECHS)]
    term_a_f = term_a.format(a=a, b=b) if "{a}" in term_a else term_a
    term_b_f = term_b.format(a=a, b=b) if "{b}" in term_b else term_b
    add(
        f"S48-I-E-{i+1:02d}", "indemnification", (2 if i % 3 else 3), ["E"],
        (
            f"8. Indemnification. {a} shall indemnify, defend, and hold harmless {b}, and {b} shall "
            f"indemnify, defend, and hold harmless {a}, in each case from third-party claims arising from "
            f"the indemnifying party's own negligence, PROVIDED THAT {a}'s obligation is {term_a_f}, "
            f"whereas {b}'s obligation is {term_b_f}."
        ),
        {"contract_side": "sell_side"},
        {"asymmetry_mechanism": mech, "roles": [a, b]},
        "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
        f"Genuine per-party differentiation ({mech}) stated for a named pair opening with symmetric "
        f"phrasing — the reciprocal opener's symmetry claim cannot be trusted.",
        "S3",
    )

# 10 genuine-symmetry negative controls (must NOT escalate)
E_SYM_DOMAINS = [
    "Woodbine Antique Clock Restoration", "Copperlantern Stained Glass Studio",
    "Fernhollow Botanical Illustration Co", "Grayling Fly-Fishing Outfitters",
    "Hazelmoor Wool Spinning Mill", "Inkwell Custom Bookbinding Studio",
    "Juneberry Preserves & Jam Co", "Kelpshore Seaweed Harvesting Co-op",
    "Lanternfish Night-Diving Charters", "Marrowbone Broth Co-Packers",
]
for i, entity in enumerate(E_SYM_DOMAINS):
    add(
        f"S48-I-E-SYM-{i+1:02d}", "indemnification", 2, ["E"],
        (
            f"8. Indemnification. {entity} shall indemnify, defend, and hold harmless Client, and Client "
            f"shall indemnify, defend, and hold harmless {entity}, in each case from third-party claims "
            f"arising from the indemnifying party's own negligence or willful misconduct, up to a cap of "
            f"one (1) times the annual fees paid, with each indemnifying party controlling the defense of "
            f"claims for which it is responsible."
        ),
        {"contract_side": "sell_side"},
        {"symmetric": True},
        "ACCEPT", "AUTOMATIC", None,
        "Genuinely symmetric reciprocal indemnity — identical terms stated for both directions, no "
        "differentiation anywhere in the clause. Must resolve automatically.",
        "S2",
    )

print("after I_E:", len(CASES))

# ============================================================================
# INDEMNIFICATION — Families F, G, H, I, N (push total past 80)
# ============================================================================

# Family F — conditional applicability
add(
    "S48-I-F-01", "indemnification", 3, ["F"],
    (
        "8. Indemnification. Whistledown Aerial Photography Corp shall indemnify, defend, and hold "
        "harmless Client from third-party claims arising from Whistledown's negligence, up to a cap of "
        "one (1) times the annual fees paid, PROVIDED THAT if the claim arises from a photography flight "
        "conducted outside standard daylight operating hours, the cap for that specific claim shall "
        "instead be four (4) times the annual fees paid."
    ),
    {"contract_side": "sell_side"},
    {"exposure_monetary": "conditionally escalates 1x -> 4x for a specific claim scenario"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Bifurcated cap tied to a specific claim scenario — silently adopting the 1x base understates the "
    "true worst-case exposure (4x) this clause permits.",
    "S3",
)
add(
    "S48-I-F-02", "indemnification", 3, ["F"],
    (
        "8. Indemnification. Coldharbor Ice Cream Manufacturing shall indemnify, defend, and hold "
        "harmless Distributor from third-party claims, up to a cap of two (2) times the annual fees "
        "paid, applicable only if Distributor has designated Coldharbor as its 'primary supplier' under "
        "the Master Supply Agreement, a designation not yet made as of this excerpt."
    ),
    {"contract_side": "sell_side"},
    {"exposure_monetary": "conditioned on undesignated status"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "The cap's applicability is conditioned on a designation the document itself says has not yet been "
    "made — direct generalization of the conditional-unverified-precondition mechanism to indemnification.",
    "S3",
)

# Family G — self-flagged/unresolved scope
add(
    "S48-I-G-01", "indemnification", 3, ["G"],
    (
        "8. Indemnification. Marrowlight Custom Neon Signage Co shall indemnify, defend, and hold "
        "harmless Client from claims arising under this Agreement, the parties acknowledging that "
        "whether claims arising from installation (as opposed to fabrication) are included within this "
        "obligation remains a matter not yet finally resolved between them."
    ),
    {"contract_side": "sell_side"},
    {"scope": "self-flagged, unresolved (installation vs fabrication)"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Direct generalization of the Step 4A.7.4 indemnification self-flagged-unresolved-scope fix to a "
    "fresh domain and a fresh scope question.",
    "S3",
)
add(
    "S48-I-G-02", "indemnification", 3, ["G"],
    (
        "8. Indemnification. Ferngully Landscape Irrigation Design shall indemnify, defend, and hold "
        "harmless Client from third-party claims, the amount of such indemnification not yet having been "
        "determined pending completion of the parties' ongoing rate negotiation."
    ),
    {"contract_side": "sell_side"},
    {"monetary": "self-flagged, undetermined"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "The monetary treatment of the indemnification obligation is explicitly flagged as not yet "
    "determined — must not be silently treated as uncapped or absent.",
    "S3",
)

# Family H — conflicting definitions
add(
    "S48-I-H-01", "indemnification", 3, ["H"],
    (
        "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Client from claims "
        "arising under this Agreement, up to a cap of the Indemnity Limit. 'Indemnity Limit' means, for "
        "purposes of Section 8.2, one (1) times the fees paid, and means, for purposes of Section 8.9 "
        "(Cybersecurity Incidents), six (6) times the fees paid."
    ),
    {"contract_side": "buy_side"},
    {"protection_monetary": "conflicting (1x vs 6x)"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Category-scoped conflicting-defined-term shape, fresh domain and multiplier values (6x delta).",
    "S3",
)
add(
    "S48-I-H-02", "indemnification", 3, ["H"],
    (
        "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Client from claims "
        "arising under this Agreement, up to a cap of the Indemnity Limit. 'Indemnity Limit' means one "
        "(1) times the fees paid, as further confirmed for the parties' convenience in the signature "
        "block preamble."
    ),
    {"contract_side": "buy_side"},
    {"protection_monetary": 1},
    "ACCEPT", "AUTOMATIC", None,
    "Near-miss negative control: single consistent definition with an explicit 'for convenience' "
    "harmless restatement — must resolve automatically.",
    "S3",
)

# Family I — chained delegation
add(
    "S48-I-I-01", "indemnification", 3, ["I"],
    (
        "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Client from claims "
        "described in the Risk Allocation Matrix, which Risk Allocation Matrix itself incorporates by "
        "reference the claims-handling protocol maintained by Vendor's insurer (not included in this "
        "excerpt)."
    ),
    {"contract_side": "buy_side"},
    {"protection_monetary": "chained delegation, unresolved"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Fresh-phrasing generalization test of the indemnification chained-delegation detector added in "
    "Step 4A.7.3.",
    "S4",
)

# Family N — compound (indemnification), 2-3 mechanisms
add(
    "S48-I-N-01", "indemnification", 3, ["E", "H", "N"],
    (
        "8. Indemnification. Each party shall indemnify the other party from third-party claims arising "
        "from its own negligence, up to a cap of the Shared Ceiling. 'Shared Ceiling' means, for purposes "
        "of ordinary claims, one (1) times the fees paid, and means, for purposes of claims arising from "
        "willful misconduct, five (5) times the fees paid, PROVIDED THAT Halcyon Rooftop Beekeeping "
        "Cooperative's obligation for willful-misconduct claims specifically is further subject to a "
        "heightened 'clear and convincing evidence' causation standard not applicable to the counterparty."
    ),
    {"contract_side": "sell_side"},
    {"asymmetry": "causation standard + conflicting defined term, both unresolved"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Three-mechanism compound: conflicting defined term (1x/5x) + causation-standard asymmetry, stacked "
    "on a reciprocal opener.",
    "S3",
)
add(
    "S48-I-N-02", "indemnification", 3, ["F", "I", "N"],
    (
        "8. Indemnification. Winterbourne Custom Millwork Corp shall indemnify, defend, and hold "
        "harmless Client from claims described in Schedule K, which Schedule K itself cross-references "
        "the then-current claims protocol maintained by Winterbourne's parent company (not included in "
        "this excerpt), PROVIDED THAT this obligation applies only if Client has opted into the Extended "
        "Warranty Program, an election not yet made as of this excerpt."
    ),
    {"contract_side": "sell_side"},
    {"exposure": "chained delegation AND conditional applicability, both unresolved"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: chained delegation to an external, unincluded protocol stacked with conditional "
    "applicability tied to an unmade election.",
    "S4",
)

print("after I_extra:", len(CASES))

# ============================================================================
# INDEMNIFICATION — additional Tier 1/2 ordinary cases (push total past 80)
# ============================================================================
I_MORE_DOMAINS = [
    ("Alderbrook Custom Signage Fabricators", "Retail Client", "sell_side"),
    ("Brightloom Textile Screen Printing", "Apparel Brand", "sell_side"),
    ("Coalcrest Industrial Boiler Servicing", "Manufacturing Plant", "sell_side"),
    ("Duskrose Event Floral Design Studio", "Wedding Planner", "sell_side"),
    ("Emberglass Custom Stained Glass Co", "Church Building Committee", "sell_side"),
    ("Fallowfield Organic Seed Cleaning", "Cooperative Farm", "sell_side"),
    ("Graniteshore Monument Engraving Co", "Cemetery Association", "sell_side"),
    ("Heatherglen Wool Felting Studio", "Craft Retailer", "sell_side"),
    ("Ironclad Portable Toilet Rentals", "Event Organizer", "sell_side"),
    ("Jasperfield Custom Leatherworking", "Boutique Retailer", "sell_side"),
    ("Kelvinbrook HVAC Duct Cleaning", "Office Building Manager", "sell_side"),
    ("Lanterngate Escape Vehicle Rentals", "Film Production Co", "sell_side"),
    ("Moorfield Composting Services", "Municipal Waste Authority", "sell_side"),
    ("Nightshade Greenhouse Construction", "Commercial Grower", "sell_side"),
    ("Oxbow River Rafting Outfitters", "Tour Booking Agency", "sell_side"),
    ("Pemberton Custom Trophy Engraving", "Sports League", "sell_side"),
    ("Quicksilver Mobile Auto Detailing", "Fleet Manager", "sell_side"),
    ("Ravensworth Antique Clock Repair", "Estate Sale Company", "sell_side"),
    ("Silverpine Yurt & Glamping Rentals", "Resort Operator", "sell_side"),
    ("Tanglewood Beekeeping Consulting", "Agricultural Cooperative", "sell_side"),
    ("Underhill Root Cellar Construction", "Homeowner", "sell_side"),
    ("Vellumcraft Custom Bookbinding Studio", "Library Foundation", "sell_side"),
    ("Whetstone Knife Sharpening Services", "Restaurant Group", "sell_side"),
    ("Xylobrook Custom Wood Flooring", "Property Developer", "sell_side"),
    ("Yarrowfield Herbal Apiary Products", "Retail Cooperative", "sell_side"),
]
for i, (entity, ctp, side) in enumerate(I_MORE_DOMAINS):
    mult = [1, 1, 2, 1, 2, 3][i % 6]
    tier = 1 if i % 3 != 0 else 2
    text = (
        f"8. Indemnification. {entity} shall indemnify, defend, and hold harmless {ctp} from and "
        f"against any and all third-party claims, damages, and expenses arising out of {entity}'s "
        f"negligence or willful misconduct in performing services under this Agreement, up to a cap of "
        f"{mult} times the annual fees paid by {ctp}."
    )
    if tier == 2:
        text = (
            f"8. Indemnification. Subject to Section 8.4 (Limitations) and without limiting any other "
            f"remedy available to {ctp} at law or in equity, {entity} shall indemnify, defend, and hold "
            f"harmless {ctp}, its officers, directors, and employees, from and against any and all "
            f"third-party claims, damages, and reasonable expenses (including attorneys' fees) arising "
            f"out of {entity}'s negligence or willful misconduct in performing services under this "
            f"Agreement, up to a cap of {mult} times the annual fees paid by {ctp} hereunder."
        )
    add(
        f"S48-I-T{tier}-{i+1:02d}", "indemnification", tier, ["D"],
        text, {"contract_side": side},
        {"exposure_role": entity, "monetary_multiplier": mult},
        "ACCEPT" if mult == 1 else ("ACCEPT_WITH_NOTE" if mult == 2 else "NEGOTIATE"),
        "AUTOMATIC", None,
        "Ordinary clean indemnification obligation, standard 'shall indemnify, defend, and hold harmless' "
        "phrasing, unambiguous cap and role pair" + (
            " with a broad-beneficiary clause and savings-clause distractor." if tier == 2 else "."
        ),
        "S2",
    )

print("after I_more:", len(CASES))

# ============================================================================
# PAYMENT TERMS — target >= 80 cases (Families A, F, G, H, I, J, K, L, M, N)
# ============================================================================

P_DOMAINS = [
    "Featherstone Commercial Embroidery Co", "Grousemoor Industrial Degreasing Services",
    "Hartwell Custom Trophy Manufacturing", "Inglenook Fireplace Installation Corp",
    "Juniper Hollow Beekeeping Supply", "Kettlebrook Artisan Soap Manufacturing",
    "Larchmont Custom Awning Fabricators", "Millwright Grain Elevator Servicing",
    "Norwood Playground Surfacing Co", "Oatfield Grain Storage Solutions",
    "Pinegate Custom Furniture Refinishing", "Quarrystone Monument Fabrication",
    "Riverbend Irrigation Pump Servicing", "Shalefield Water Well Testing Labs",
    "Thistlegate Custom Drapery Workroom", "Underbrook Tree Cabling Services",
    "Vinemont Trellis Construction Co", "Whitfield Custom Millwork Supply",
    "Yewbrook Landscape Boulder Delivery", "Zephyrfield Kite Festival Rentals",
]
for i, entity in enumerate(P_DOMAINS):
    net = [30, 45, 15, 60, 30][i % 5]
    tier = 1
    add(
        f"S48-P-T1-{i+1:02d}", "payment_terms", tier, ["A"],
        f"6. Payment Terms. Client shall pay {entity} all invoiced amounts within {net} days of the "
        f"invoice date.",
        {},
        {"net_days": net}, "ACCEPT", "AUTOMATIC", None,
        "Ordinary, unambiguous net-days payment clause.",
        "S2",
    )
    add(
        f"S48-P-T1B-{i+1:02d}", "payment_terms", tier, ["A"],
        f"6. Payment Terms. {entity} shall submit invoices monthly, and Client shall remit payment "
        f"within {net} days of receipt of each invoice; amounts subject to a good-faith dispute may be "
        f"withheld pending resolution, but all undisputed amounts remain payable on the original schedule.",
        {},
        {"net_days": net, "dispute_right": True}, "ACCEPT", "AUTOMATIC", None,
        "Ordinary dispute-carve-out clause paired with a standard net-days term — common commercial "
        "drafting, should resolve cleanly.",
        "S2",
    )

print("after P_T1:", len(CASES))

# ----------------------------------------------------------------------------
# Payment Terms — Tier 2/3, Families F, G, H, I, J, K, L, M, N
# ----------------------------------------------------------------------------

# Family F — conditional applicability
add(
    "S48-P-F-01", "payment_terms", 3, ["F"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice, PROVIDED THAT for orders "
    "placed through the Preferred Partner Portal specifically, payment shall instead be due within 15 "
    "days, it not yet having been determined whether Client qualifies for Preferred Partner status.",
    {}, {"net_days": "conditional (30 or 15), qualification unresolved"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Direct generalization of the conditional-payment-period mechanism (Step 4A.7.4) — fresh domain.",
    "S3",
)
add(
    "S48-P-F-02", "payment_terms", 3, ["F"],
    "6. Payment Terms. Client shall pay Vendor within 45 days of invoice, unless Vendor has elected "
    "quarterly consolidated billing under Section 6.7, in which case payment is due within 60 days; "
    "Vendor has not yet made this election as of the date of this excerpt.",
    {}, {"net_days": "conditional (45 or 60), election unresolved"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Payment period depends on an unmade billing-method election.",
    "S2",
)

# Family G — self-flagged unresolved
add(
    "S48-P-G-01", "payment_terms", 3, ["G"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice for the base subscription fee; "
    "the parties have not yet agreed whether usage-based overage charges are included within this "
    "payment obligation or will be addressed under a separate future amendment.",
    {}, {"scope": "self-flagged, unresolved (overage charges)"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "The BASE fee timing is clear, but whether overage charges are included is explicitly flagged as "
    "unresolved — a genuine scope ambiguity affecting the total amount owed.",
    "S3",
)
add(
    "S48-P-G-02", "payment_terms", 3, ["G"],
    "6. Payment Terms. Payment terms shall be as the parties mutually determine in good faith; the "
    "parties acknowledge that no such determination has yet been reached as of the Effective Date, and "
    "in the interim no invoice shall issue.",
    {}, {"net_days": None, "clause_status": "entirely deferred"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Entire payment structure deferred to a future, unreached determination.",
    "S3",
)

# Family H — conflicting/ambiguous definitions
add(
    "S48-P-H-01", "payment_terms", 3, ["H"],
    "6. Payment Terms. Payment is due Net 45. 'Net 45' means, for purposes of the domestic-shipment "
    "pricing described in Section 6.3, forty-five calendar days from invoice date, and means, for "
    "purposes of the international-shipment pricing described in Section 6.11, forty-five business days "
    "from invoice date.",
    {}, {"net_days": "conflicting definition (calendar vs business days)"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Category-scoped conflicting-defined-term shape applied to Net-45 rather than Net-30, fresh domain "
    "categories (domestic vs international shipment).",
    "S3",
)
add(
    "S48-P-H-02", "payment_terms", 3, ["H"],
    "6. Payment Terms. Payment is due Net 30. 'Net 30' means thirty calendar days from invoice date, "
    "consistent with the definition of the same term used throughout this Agreement, including in "
    "Section 14.",
    {}, {"net_days": 30}, "ACCEPT", "AUTOMATIC", None,
    "Near-miss negative control: explicit 'consistent with...throughout' cross-reference confirming, not "
    "conflicting with, the single stated definition.",
    "S3",
)

# Family I — chained delegation
add(
    "S48-P-I-01", "payment_terms", 3, ["I"],
    "6. Payment Terms. Client shall pay the amount set forth in the Order Form, which Order Form itself "
    "incorporates by reference the then-current price list maintained on Vendor's partner portal (not "
    "included in this excerpt).",
    {}, {"amount": "chained delegation, unresolved"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Fresh-phrasing generalization test of the payment_terms chained-delegation detector.",
    "S4",
)
add(
    "S48-P-I-02", "payment_terms", 2, ["I"],
    "6. Payment Terms. Client shall pay the amount set forth in the attached Order Form.",
    {}, {"amount": "single-level reference, no chain"},
    "ACCEPT", "AUTOMATIC", None,
    "Near-miss negative control: single-level reference to an attached (not external/excluded) Order "
    "Form — must resolve automatically, no policy gap signaled.",
    "S3",
)

# Family J — set-off / netting
add(
    "S48-P-J-01", "payment_terms", 3, ["J"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice. Rather than each party "
    "remitting payment separately, the parties agree that at each quarter's close, only the resulting "
    "balance after offsetting Vendor's amounts due to Client under the separate co-marketing agreement "
    "shall be transferred between them.",
    {"prohibit_set_off": True}, {"setoff": "genuine cross-agreement netting"},
    "MUST_REDLINE", "AUTOMATIC", None,
    "Genuine mutual-debt netting across a SEPARATE agreement using fresh 'resulting balance after "
    "offsetting' phrasing not in any prior corpus.",
    "S4",
)
add(
    "S48-P-J-02", "payment_terms", 3, ["J"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice. Vendor may issue a service "
    "credit to Client's account for any confirmed SLA breach, to be applied against Client's next "
    "invoice.",
    {"prohibit_set_off": True}, {"setoff": "hard negative — SLA service credit, not debt netting"},
    "ACCEPT", "AUTOMATIC", None,
    "Ordinary SLA service-credit mechanic — a routine accounting adjustment, not mutual debt netting; "
    "must NOT trigger the set-off detector.",
    "S3",
)
add(
    "S48-P-J-03", "payment_terms", 3, ["J"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice. Vendor shall be entitled to "
    "deduct from any amount otherwise payable to Client the value of any nonconforming units Client has "
    "returned under the Warranty Policy, as measured by the returned units' invoiced price.",
    {"prohibit_set_off": True}, {"setoff": "hard negative — warranty-return deduction"},
    "ACCEPT", "AUTOMATIC", None,
    "Warranty-return deduction tied to Client's own returned goods, not an independent debt — must NOT "
    "trigger the set-off detector.",
    "S3",
)

# Family K — payment recognition / absence
add(
    "S48-P-K-01", "payment_terms", 2, ["K"],
    "6. Fee Schedule. In exchange for the services rendered, Client is obligated to remit compensation "
    "to Vendor totaling $4,000 per month, due on the first business day of each month.",
    {}, {"amount": 4000, "period": "monthly"}, "ACCEPT", "AUTOMATIC", None,
    "Payment clause under an atypical heading ('Fee Schedule') with 'obligated to remit compensation' "
    "phrasing rather than 'shall pay' — tests recognition generalization.",
    "S3",
)
add(
    "S48-P-K-02", "payment_terms", 2, ["K"],
    "4. Damage Deposit. Client shall pay Vendor a refundable damage deposit of $2,500 upon execution of "
    "this Agreement, to be returned within 14 days of the equipment's return in good condition.",
    {}, {"presence": "deposit only, not operative payment terms"},
    "NOT_APPLICABLE", "AUTOMATIC", {"expected_classification": "NOT_APPLICABLE"},
    "A damage-deposit clause is not the operative recurring payment-terms provision — must not be "
    "misread as satisfying the payment-terms check.",
    "S4",
)
add(
    "S48-P-K-03", "payment_terms", 1, ["L"],
    "1. Services. Hearthside Custom Fireplace Mantels shall design and install custom mantels as "
    "described in Exhibit A.\n\n2. Warranty. All work is warranted for two years.",
    {}, {"presence": "genuinely absent"},
    "NOT_APPLICABLE", "AUTOMATIC", {"expected_classification": "CONFIRMED_ABSENT"},
    "No payment/invoicing language anywhere in the document — correct outcome is confident absence.",
    "S1",
)

# Family M — amendments/supersession
add(
    "S48-P-M-01", "payment_terms", 3, ["M"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice.\n\nAmendment No. 1. Section 6 "
    "is hereby amended and restated in its entirety to read: 'Client shall pay Vendor within 45 days of "
    "invoice.'",
    {}, {"net_days": 45, "amendment": "valid full restatement"},
    "ACCEPT_WITH_NOTE", "AUTOMATIC", None,
    "Valid amendment restates Section 6 in full — the governing term is the amended 45-day period, not "
    "the original 30-day period.",
    "S3",
)
add(
    "S48-P-M-02", "payment_terms", 3, ["M"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice.\n\nAmendment No. 1. The parties "
    "agree to add the following sentence to Section 6: 'Late payments accrue interest at 1.5% per "
    "month.' All other terms of Section 6 remain in full force and effect.",
    {}, {"net_days": 30, "late_fee_rate": 1.5, "amendment": "valid partial addition"},
    "ACCEPT", "AUTOMATIC", None,
    "Valid partial amendment adds a late-fee term while leaving the original 30-day period intact — both "
    "the original and added terms should be read together, not treated as conflicting.",
    "S2",
)

for c in list(CASES):
    pass  # no-op; ensures list mutation visibility for print below

print("after P_families:", len(CASES))

# ============================================================================
# FAMILY N — COMPOUND, additional cases across all 3 adapters (push total
# Family N to >= 30, with >= 10 cases combining 3+ mechanisms)
# ============================================================================

# --- Liability compound (5 more, several 3-mechanism) ---
add("S48-L-N-04", "liability", 3, ["A", "F", "N"],
    "1. Definitions. 'Transferee' means the party to whom rights are conveyed, and 'Transferor' means "
    "the conveying party.\n\n9. Limitation of Liability. Transferor's aggregate liability to Transferee "
    "shall not exceed two (2) times the annual fees paid, PROVIDED THAT this multiplier applies only if "
    "Transferor has maintained the insurance required by Section 12, a fact not yet confirmed as of this "
    "excerpt.",
    {"contract_side": "sell_side"}, {"role_attribution": "unresolved", "cap_conditional": "unverified"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: unmapped role vocabulary + conditional-unverified-precondition, either alone sufficient "
    "to force review.", "S4")
add("S48-L-N-05", "liability", 3, ["C", "H", "I", "N"],
    "9. Limitation of Liability. Aggregate liability shall not exceed the Cap Value, which is $15,000 "
    "less than the separately-stated $80,000 Performance Bond amount described in Section 11 (a distinct, "
    "unrelated instrument). 'Cap Value' means, for purposes of Section 9.1, one (1) times the annual "
    "fees paid, and means, for purposes of Section 9.6, which Section 9.6 itself cross-references the "
    "vendor's internal rate table (not included), a chained-delegated amount.",
    {"contract_side": "sell_side"}, {"cap": "conflicting AND chained-delegated, with a bond distractor"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Four-tag compound: contamination distractor (Performance Bond) + conflicting defined term + chained "
    "delegation, all in one provision.", "S4")
add("S48-L-N-06", "liability", 3, ["B", "F", "G", "N"],
    "9. Limitation of Liability. Aggregate liability shall not exceed two (2) times the annual fees paid "
    "for claims arising after the Transition Date, PROVIDED THAT the Transition Date itself has not yet "
    "been fixed by the parties, it remaining unresolved whether the current or a prior fee schedule "
    "governs in the interim.",
    {"contract_side": "sell_side"}, {"cap": "conditional AND self-flagged unresolved basis"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Three-mechanism compound: conditional-applicability (undetermined Transition Date) stacked with "
    "self-flagged basis-scope ambiguity (which fee schedule governs).", "S3")
add("S48-L-N-07", "liability", 3, ["A", "C", "N"],
    "1. Definitions. 'Chargee' means the secured party, and 'Chargor' means the party granting the "
    "security interest.\n\n9. Limitation of Liability. Chargor's aggregate liability to Chargee shall not "
    "exceed one (1) times the annual servicing fees paid. Separately, Chargor's total secured-loan "
    "exposure under the facility is $2,400,000, which figure is unrelated to this liability cap.",
    {"contract_side": "sell_side"}, {"role_attribution": "unresolved", "distractor": "$2,400,000 unrelated"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: unmapped role vocabulary + a large unrelated-dollar-figure distractor that must not be "
    "adopted as the cap.", "S4")
add("S48-L-N-08", "liability", 3, ["F", "I", "N"],
    "9. Limitation of Liability. Aggregate liability shall not exceed the amount calculated under the "
    "Fee Protocol, which Fee Protocol itself references the then-current rate table maintained by "
    "Licensor's finance department (not included), applicable only for claims filed after Licensee's "
    "election of the Standard Support Tier, an election not yet made as of this excerpt.",
    {"contract_side": "sell_side"}, {"cap": "chained delegation AND conditional election, both unresolved"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: chained delegation to an external unincluded rate table + conditional-applicability tied "
    "to an unmade tier election.", "S4")

# --- Indemnification compound (5 more) ---
add("S48-I-N-03", "indemnification", 3, ["D", "F", "G", "N"],
    "8. Risk Allocation. Featherquill Custom Calligraphy Studio shall bear full responsibility for "
    "defending and satisfying, on Client's behalf, any third-party claim arising from Featherquill's "
    "negligence, up to a cap of one (1) times the annual fees paid, PROVIDED THAT this cap applies only "
    "if the claim is filed within the Standard Claims Window; whether a given claim falls within or "
    "outside that window remains a matter the parties have not yet finally resolved.",
    {"contract_side": "sell_side"}, {"exposure": "fresh idiom + conditional + self-flagged, unresolved"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Three-mechanism compound: novel synonym-idiom recognition + conditional-applicability + self-"
    "flagged-unresolved scope, all stacked on one obligation.", "S4")
add("S48-I-N-04", "indemnification", 3, ["A", "E", "N"],
    "8. Indemnification. Grantee shall indemnify, defend, and hold harmless Grantor, and Grantor shall "
    "indemnify, defend, and hold harmless Grantee, in each case from third-party claims arising from the "
    "indemnifying party's own negligence, up to a cap of one (1) times the fees paid, and Grantee's "
    "indemnification obligation is subject to a causation standard of 'sole proximate cause,' whereas "
    "Grantor's obligation is subject to a substantially broader 'contributing cause' standard.",
    {"contract_side": "sell_side"}, {"role_attribution": "unresolved", "causation": "asymmetric"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: unmapped role-attribution vocabulary (Grantee/Grantor) stacked with causation-standard "
    "asymmetry — direct generalization test of the adverb-tolerant causation regex on fresh vocabulary.",
    "S4")
add("S48-I-N-05", "indemnification", 3, ["E", "H", "I", "N"],
    "8. Indemnification. Each party shall indemnify the other party from third-party claims arising from "
    "its own negligence, up to a cap of the Shared Limit, which Shared Limit itself cross-references the "
    "risk table maintained by each party's respective insurer (not included in this excerpt), and 'Shared "
    "Limit' additionally means, for purposes of data-breach claims specifically, three (3) times the fees "
    "paid.",
    {"contract_side": "sell_side"}, {"cap": "chained delegation AND conflicting category-scoped term"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Four-tag compound: reciprocal opener + chained delegation + conflicting category-scoped defined "
    "term, all on the same monetary fact.", "S4")
add("S48-I-N-06", "indemnification", 3, ["D", "H", "N"],
    "8. Risk Allocation. Hollowmere Custom Terrarium Studio undertakes to make Client whole for, and to "
    "assume the defense of, any third-party claim arising from Hollowmere's negligence, up to a cap of "
    "the Loss Ceiling. 'Loss Ceiling' means, for purposes of Section 8.1, one (1) times the fees paid, "
    "and means, for purposes of Section 8.7 (Product Liability), four (4) times the fees paid.",
    {"contract_side": "sell_side"}, {"exposure": "fresh idiom + conflicting category-scoped term"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: fresh synonym-idiom recognition test stacked with a conflicting category-scoped defined "
    "term.", "S4")

# --- Payment terms compound (9, several 3-mechanism, also boosts payment count) ---
add("S48-P-N-01", "payment_terms", 3, ["F", "J", "N"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice, PROVIDED THAT for orders under "
    "the Volume Rebate Program specifically, Vendor shall net any rebate credits against Client's "
    "independently-owed balance under the separate distribution agreement, a program Client has not yet "
    "elected to join as of this excerpt.",
    {"prohibit_set_off": True}, {"setoff": "conditional AND genuine cross-agreement netting, unresolved"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: conditional-applicability (unelected program) stacked with genuine cross-agreement "
    "netting language.", "S4")
add("S48-P-N-02", "payment_terms", 3, ["H", "I", "N"],
    "6. Payment Terms. Payment is due Net 30. 'Net 30' means, for purposes of Section 6.2, thirty "
    "calendar days from invoice, and means, for purposes of Section 6.9, which Section 6.9 itself "
    "cross-references the then-current billing calendar maintained on Vendor's client portal (not "
    "included), a chained-delegated period.",
    {}, {"net_days": "conflicting AND chained-delegated"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: conflicting defined term stacked with chained delegation on the SAME fact (the governing "
    "payment period).", "S4")
add("S48-P-N-03", "payment_terms", 3, ["G", "K", "N"],
    "4. Security Retainer. Client shall pay Vendor a refundable security retainer of $3,000 upon "
    "execution. 6. Payment Terms. Ongoing service fees shall be as the parties mutually determine, no "
    "such determination having yet been made as of this excerpt.",
    {}, {"presence": "deposit distractor + genuinely unresolved operative terms"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: a deposit-vs-operative-terms distractor (Family K) alongside a genuinely self-flagged-"
    "unresolved operative payment structure (Family G) — the deposit must not be adopted as the answer, "
    "AND the genuine unresolved gap must still be flagged.", "S3")
add("S48-P-N-04", "payment_terms", 3, ["F", "H", "N"],
    "6. Payment Terms. Payment is due Net 45 for standard orders, PROVIDED THAT for orders exceeding "
    "$50,000, 'Net 45' shall instead mean forty-five business days rather than calendar days, and "
    "whether any given order exceeds this threshold before applicable discounts has not yet been "
    "determined for pending orders.",
    {}, {"net_days": "conditional AND definitionally conflicting"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: conditional-applicability (threshold determination unresolved) stacked with a conflicting "
    "calendar-vs-business-days definition.", "S3")
add("S48-P-N-05", "payment_terms", 2, ["A", "K", "N"],
    "6. Fees and Charges. Client's obligation to remunerate Underhill Custom Cabinetry Supply for goods "
    "delivered shall be Net 30 from invoice date; Client shall also pay a one-time $500 design-consult "
    "fee, which is not a security deposit and does not affect the operative Net 30 payment schedule "
    "above.",
    {}, {"net_days": 30, "distractor": "one-time design fee explicitly not a deposit"},
    "ACCEPT", "AUTOMATIC", None,
    "Compound negative control: atypical heading (Family K recognition test) plus an explicit disclaimer "
    "that a secondary fee is NOT a deposit and does not change the operative schedule — should resolve "
    "cleanly, not be conflated or escalated.", "S2")
add("S48-P-N-06", "payment_terms", 3, ["G", "I", "N"],
    "6. Payment Terms. Client shall pay the royalty rate set forth in Schedule Q, which Schedule Q "
    "itself incorporates by reference the then-current commission table maintained by Licensor's "
    "accounting department (not included in this excerpt); the parties further acknowledge that whether "
    "returns are deducted before or after this calculation remains unresolved.",
    {}, {"amount": "chained delegation AND self-flagged unresolved calculation order"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Three-mechanism compound: chained delegation to an external unincluded commission table + a "
    "self-flagged unresolved calculation-order ambiguity.", "S4")

print("after N_compound:", len(CASES))

# ============================================================================
# Additional payment_terms ordinary cases (push payment_terms >= 75)
# ============================================================================
P_MORE = [
    "Applecross Custom Pottery Studio", "Briarwood Handmade Candle Co",
    "Cloverfield Artisan Chocolate Makers", "Duskhollow Vintage Furniture Restoration",
    "Elmswood Custom Guitar Building", "Foxglove Herbal Skincare Manufacturing",
    "Greystone Custom Countertop Fabrication", "Hollyburn Christmas Wreath Making",
    "Ivywood Custom Tapestry Weaving", "Junebug Handpoured Soap Co",
    "Kingfisher Custom Birdhouse Manufacturing", "Lilypad Water Garden Design",
    "Moonstone Custom Jewelry Casting",
]
for i, entity in enumerate(P_MORE):
    net = [30, 45, 60, 15][i % 4]
    tax_side = i % 3 == 0
    text = (
        f"6. Payment Terms. Client shall pay {entity} within {net} days of invoice date, in U.S. "
        f"Dollars."
    )
    facts = {"net_days": net}
    if tax_side:
        text += (
            f" {entity} shall be solely responsible for remitting any applicable sales or use tax "
            f"arising from this Agreement."
        )
        facts["tax_responsibility"] = "counterparty"
    add(
        f"S48-P-T1M-{i+1:02d}", "payment_terms", 1, ["A"], text, {},
        facts, "ACCEPT", "AUTOMATIC", None,
        "Ordinary net-days clause" + (" with an explicit tax-responsibility statement" if tax_side else "") + ".",
        "S2",
    )

print("after P_more:", len(CASES))

# ============================================================================
# Additional Tier 2 cases across all adapters (push Tier2 >= 80) — mix of
# AUTOMATIC and SHOULD_REVIEW to also push SHOULD_REVIEW >= 70
# ============================================================================

# --- Liability Tier 2 (10 more, mix) ---
L_T2C = [
    ("Ashford Custom Pergola Builders", "Homeowner", 1, "ACCEPT"),
    ("Briardale Grain Silo Inspection Co", "Cooperative", 2, "ACCEPT_WITH_NOTE"),
    ("Cragmont Rock Climbing Wall Installers", "Gym Owner", 3, "NEGOTIATE"),
    ("Duncastle Custom Shutter Manufacturing", "Contractor", 1, "ACCEPT"),
    ("Everfrost Ice Rink Refrigeration Services", "Arena Operator", 2, "ACCEPT_WITH_NOTE"),
]
for i, (entity, cp, mult, exp) in enumerate(L_T2C):
    add(f"S48-L-T2C-{i+1:02d}", "liability", 2, ["B"],
        f"9. Limitation of Liability. Notwithstanding the generality of the foregoing, and subject "
        f"always to the parties' respective obligations under Section 4 (Insurance), the aggregate "
        f"liability of {entity} to {cp}, however arising, shall be limited to, and shall in no event "
        f"exceed, {mult} times the annual service fees actually paid by {cp} to {entity} in the "
        f"twelve-month period immediately preceding the claim giving rise to such liability.",
        {"contract_side": "sell_side"}, {"cap_multiplier": mult},
        exp, "AUTOMATIC", None,
        "Long qualifier-heavy sentence with an Insurance cross-reference distractor preceding a single "
        "clean cap value.", "S2")

L_T2D = [
    ("Fenwick Custom Aquarium Maintenance", "Restaurant Client"),
    ("Grovehaven Landscape Boulder Placement", "HOA Board"),
]
for i, (entity, cp) in enumerate(L_T2D):
    add(f"S48-L-T2D-{i+1:02d}", "liability", 2, ["H"],
        f"9. Limitation of Liability. Aggregate liability of {entity} shall not exceed the Liability "
        f"Threshold. 'Liability Threshold' means one (1) times the annual fees paid, and this same "
        f"figure is restated for the parties' administrative convenience in the cover letter accompanying "
        f"this Agreement.",
        {"contract_side": "sell_side"}, {"cap_multiplier": 1},
        "ACCEPT", "AUTOMATIC", None,
        "Restated-but-identical value near-miss control — a second mention exists but states the SAME "
        "figure with an explicit convenience framing.", "S3")

L_T2E = [
    ("Harrowgate Precision Tool Grinding", "Manufacturer"),
    ("Ironhollow Custom Weathervane Forge", "Architectural Firm"),
    ("Juniper Vale Beekeeping Equipment Supply", "Apiary Network"),
]
for i, (entity, cp) in enumerate(L_T2E):
    add(f"S48-L-T2E-{i+1:02d}", "liability", 2, ["I"],
        f"9. Limitation of Liability. Aggregate liability of {entity} shall not exceed one (1) times the "
        f"annual fees paid, calculated per the methodology in Exhibit G.",
        {"contract_side": "sell_side"}, {"cap_multiplier": 1},
        "ACCEPT", "AUTOMATIC", None,
        "Single-level cross-reference control (no second delegation hop) — must resolve automatically.",
        "S3")

# --- Indemnification Tier 2 (10 more, mix) ---
I_T2 = [
    ("Kettleworth Custom Wine Cellar Design", "Homeowner", "sell_side"),
    ("Larkfield Antique Rug Restoration", "Auction House", "sell_side"),
    ("Millgrove Custom Stone Carving Studio", "Cemetery Association", "sell_side"),
    ("Nettlebrook Beekeeping Removal Services", "Homeowner", "sell_side"),
]
for i, (entity, cp, side) in enumerate(I_T2):
    add(f"S48-I-T2X-{i+1:02d}", "indemnification", 2, ["D"],
        f"8. Indemnification. Notwithstanding any other provision of this Agreement, and without "
        f"prejudice to any other right or remedy {cp} may have, {entity} shall indemnify, defend, and "
        f"hold harmless {cp}, its affiliates, officers, and employees, from and against any and all "
        f"third-party claims arising out of {entity}'s negligence, up to a cap of one (1) times the "
        f"annual fees paid by {cp}.",
        {"contract_side": side}, {"exposure_role": entity, "monetary_multiplier": 1},
        "ACCEPT", "AUTOMATIC", None,
        "Broad-beneficiary clause (affiliates/officers/employees) and savings-clause distractor "
        "surrounding a single clean obligation and cap.", "S2")

I_T2B = [
    ("Oxrun Custom Millstone Restoration", "Historical Society"),
    ("Palegrove Custom Weathering Steel Fabrication", "Architect"),
]
for i, (entity, cp) in enumerate(I_T2B):
    add(f"S48-I-T2Y-{i+1:02d}", "indemnification", 2, ["H"],
        f"8. Indemnification. {entity} shall indemnify, defend, and hold harmless {cp} from claims "
        f"arising under this Agreement, up to a cap of the Exposure Ceiling. 'Exposure Ceiling' means one "
        f"(1) times the fees paid, consistent throughout this Agreement including as referenced in "
        f"Section 15.",
        {"contract_side": "sell_side"}, {"exposure_monetary": 1},
        "ACCEPT", "AUTOMATIC", None,
        "Single consistent definition confirmed (not conflicted) by a cross-reference — negative control.",
        "S3")

I_T2C = [
    ("Quillstone Custom Engraved Signage", "Municipal Client"),
    ("Rushmere Custom Copper Guttering", "Contractor"),
    ("Silverwood Custom Bell Casting Foundry", "Church Committee"),
    ("Talonridge Custom Falconry Equipment", "Wildlife Sanctuary"),
]
for i, (entity, cp) in enumerate(I_T2C):
    add(f"S48-I-T2Z-{i+1:02d}", "indemnification", 2, ["E"],
        f"8. Indemnification. {entity} shall indemnify, defend, and hold harmless {cp}, and {cp} shall "
        f"indemnify, defend, and hold harmless {entity}, in each case from third-party claims arising "
        f"from the indemnifying party's own negligence, up to a cap of one (1) times the fees paid, with "
        f"each party bearing its own notice and cooperation obligations equally.",
        {"contract_side": "sell_side"}, {"symmetric": True},
        "ACCEPT", "AUTOMATIC", None,
        "Genuinely symmetric reciprocal indemnity with identical procedural terms — negative control.",
        "S2")

# --- Payment terms Tier 2 (10 more, mix) ---
P_T2 = [
    "Umberglade Custom Trellis & Arbor Co", "Vinewood Custom Fence Staining",
    "Wickerbrook Custom Basket Weaving", "Xenonfield Custom Neon Art Studio",
]
for i, entity in enumerate(P_T2):
    net = [30, 45][i % 2]
    add(f"S48-P-T2X-{i+1:02d}", "payment_terms", 2, ["A"],
        f"6. Payment Terms. Subject to Section 6.5 (Disputes) and notwithstanding any other provision "
        f"hereof, Client shall remit payment to {entity} for all undisputed invoiced amounts within "
        f"{net} days of the invoice date, time being of the essence with respect to this obligation.",
        {}, {"net_days": net}, "ACCEPT", "AUTOMATIC", None,
        "Verbose legalese wrapper ('time being of the essence') around a single unambiguous net-days "
        "value.", "S2")

P_T2B = [
    "Yewgarden Custom Espalier Pruning", "Zestfield Custom Fruit Tree Grafting",
]
for i, entity in enumerate(P_T2B):
    add(f"S48-P-T2Y-{i+1:02d}", "payment_terms", 2, ["H"],
        f"6. Payment Terms. Payment is due Net 30. 'Net 30' means thirty calendar days from invoice "
        f"date, as also stated for clarity in the parties' cover email accompanying this Agreement.",
        {}, {"net_days": 30}, "ACCEPT", "AUTOMATIC", None,
        "Harmless restating cross-reference ('for clarity') confirming, not conflicting with, the single "
        "stated definition.", "S3")

P_T2C = [
    "Ashendell Custom Pond Filtration Install", "Brightmoor Custom Rain Barrel Systems",
    "Coppergate Custom Sundial Fabrication", "Duskvale Custom Weathervane Repair",
]
for i, entity in enumerate(P_T2C):
    add(f"S48-P-T2Z-{i+1:02d}", "payment_terms", 2, ["I"],
        f"6. Payment Terms. Client shall pay the amount stated in the attached fee schedule (Exhibit A "
        f"to this Agreement).",
        {}, {"amount": "single-level reference, attached (not external)"},
        "ACCEPT", "AUTOMATIC", None,
        "Single-level reference to an ATTACHED exhibit (not an external, excluded source) — negative "
        "control, must resolve automatically.", "S3")

print("after T2_boost:", len(CASES))

# ============================================================================
# Final Family-N boost (>= 30 total, >= 10 with 3+ mechanisms) and
# SHOULD_REVIEW boost (>= 70 total)
# ============================================================================
add("S48-L-N-09", "liability", 3, ["A", "C", "H", "N"],
    "1. Definitions. 'Cessionary' means the party to whom a claim is assigned, and 'Cedent' means the "
    "assigning party.\n\n9. Limitation of Liability. Cedent's aggregate liability to Cessionary shall not "
    "exceed the Ceiling. Separately, Cedent's outstanding letter-of-credit exposure is $600,000 "
    "(unrelated to this cap). 'Ceiling' means, for purposes of Section 9.1, one (1) times the fees paid, "
    "and means, for purposes of Section 9.8, two (2) times the fees paid.",
    {"contract_side": "sell_side"}, {"role": "unresolved", "cap": "conflicting", "distractor": "$600,000"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Four-mechanism compound: unmapped role vocabulary + contamination distractor + conflicting defined "
    "term.", "S4")
add("S48-L-N-10", "liability", 3, ["F", "G", "I", "N"],
    "9. Limitation of Liability. Aggregate liability shall not exceed the amount set forth in the Rate "
    "Protocol, which Rate Protocol itself references the vendor's internal pricing system (not "
    "included), applicable only if the Premium Tier has been elected, an election the parties acknowledge "
    "has not yet been made, it further remaining unresolved whether the Standard Tier's 1x fallback rate "
    "applies in the interim.",
    {"contract_side": "sell_side"}, {"cap": "chained delegation + conditional + self-flagged, all unresolved"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Three-mechanism compound: chained delegation + conditional-applicability + self-flagged-unresolved "
    "fallback, all on the same cap fact.", "S4")
add("S48-I-N-07", "indemnification", 3, ["A", "F", "H", "N"],
    "1. Definitions. 'Assignee' means the party receiving assigned rights, and 'Assignor' means the "
    "assigning party.\n\n8. Indemnification. Assignor shall indemnify, defend, and hold harmless "
    "Assignee from claims arising under this Agreement, up to a cap of the Coverage Amount, applicable "
    "only if Assignor has completed the Onboarding Certification (not yet completed as of this excerpt). "
    "'Coverage Amount' means, for purposes of Section 8.1, one (1) times fees paid, and means, for "
    "purposes of Section 8.6, three (3) times fees paid.",
    {"contract_side": "sell_side"}, {"role": "unresolved", "cap": "conditional AND conflicting"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Three-mechanism compound: unmapped role vocabulary + conditional-applicability + conflicting "
    "defined term.", "S4")
add("S48-I-N-08", "indemnification", 3, ["E", "F", "G", "N"],
    "8. Indemnification. Each party shall indemnify the other party from third-party claims arising from "
    "its own negligence, up to a cap of one (1) times the fees paid, PROVIDED THAT for claims arising "
    "from Meridian Precision Optics Inc.'s use of a subcontractor specifically, the cap for that specific "
    "claim shall instead be five (5) times the fees paid, it further remaining unresolved whether "
    "'subcontractor' as used in this proviso includes independent testing labs.",
    {"contract_side": "sell_side"}, {"cap": "conditional escalation + self-flagged scope ambiguity"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Three-mechanism compound: reciprocal opener + conditional cap escalation + self-flagged scope "
    "ambiguity about the escalation's own trigger definition.", "S4")
add("S48-P-N-07", "payment_terms", 3, ["F", "G", "J", "N"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice, PROVIDED THAT amounts "
    "independently owed to Vendor by Client under the separate reseller agreement shall be netted "
    "against this balance if the Consolidated Billing Election is made; the parties acknowledge that "
    "whether this election has been made for the current billing cycle remains unresolved.",
    {"prohibit_set_off": True},
    {"setoff": "conditional election, unresolved AND genuine cross-agreement netting language"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Three-mechanism compound: conditional-applicability + self-flagged-unresolved election status + "
    "genuine cross-agreement netting language.", "S4")
add("S48-P-N-08", "payment_terms", 3, ["H", "M", "N"],
    "6. Payment Terms. Payment is due Net 30.\n\nAmendment No. 2. Section 6 is amended to add: 'For "
    "purposes of expedited orders under Section 6.4, \"Net 30\" shall instead mean fifteen calendar "
    "days.' The parties dispute whether Amendment No. 1 (which separately purported to change Net 30 to "
    "Net 45 generally) remains in effect following execution of this Amendment No. 2.",
    {}, {"net_days": "conflicting amendments, supersession genuinely disputed"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Compound: conflicting category-scoped definition + genuinely disputed amendment supersession "
    "(explicitly stated as disputed by the parties, not merely a bystander reference).", "S3")
add("S48-P-N-09", "payment_terms", 3, ["F", "I", "K", "N"],
    "4. Onboarding Deposit. Client shall pay a $1,000 onboarding deposit upon execution. 6. Fees and "
    "Charges. Ongoing amounts owed shall be as set forth in the Master Rate Card, which Master Rate Card "
    "itself incorporates by reference the then-current index maintained by a third-party pricing service "
    "(not included), applicable only once Client's account is fully onboarded, a status not yet reached "
    "as of this excerpt.",
    {}, {"amount": "deposit distractor + chained delegation + conditional onboarding status"},
    "REQUIRES_REVIEW", "SHOULD_REVIEW", None,
    "Three-mechanism compound: deposit-vs-operative-terms distractor + chained delegation + conditional-"
    "applicability, all in one short clause.", "S4")

print("FINAL COUNT:", len(CASES))

# Final tiny Family-N top-up (>= 30 total)
add("S48-L-N-11", "liability", 3, ["B", "C", "N"],
    "9. Limitation of Liability. Aggregate liability of Windermere Custom Topiary Sculpting shall not "
    "exceed two (2) times the annual maintenance fees paid. Separately, the parties note that "
    "Windermere's general commercial liability insurance policy limit is $1,000,000, a figure unrelated "
    "to this contractual cap.",
    {"contract_side": "sell_side"}, {"cap_multiplier": 2, "distractor": "$1,000,000 insurance"},
    "ACCEPT_WITH_NOTE", "AUTOMATIC", None,
    "Compound negative control: ordinary clean cap extraction combined with an explicit insurance-limit "
    "distractor that must not be adopted.", "S4")
add("S48-I-N-09", "indemnification", 3, ["D", "E", "N"],
    "8. Risk Allocation. Ashcombe Custom Wrought-Iron Gate Works agrees to hold Client harmless from and "
    "defend Client against any third-party claim, and Client agrees to hold Ashcombe harmless from and "
    "defend Ashcombe against any third-party claim, in each case arising from the indemnifying party's "
    "own negligence, up to a cap of one (1) times the fees paid.",
    {"contract_side": "sell_side"}, {"symmetric": True},
    "ACCEPT", "AUTOMATIC", None,
    "Compound negative control: fresh synonym-idiom phrasing combined with genuine reciprocal symmetry "
    "— should resolve automatically, testing both mechanisms don't spuriously interact.", "S2")
add("S48-P-N-10", "payment_terms", 3, ["A", "J", "N"],
    "6. Payment Terms. Client shall pay Fernhollow Custom Rain Chain Fabrication within 30 days of "
    "invoice. Fernhollow shall be entitled to apply any manufacturer's rebate credit issued to Client "
    "against Client's next invoice.",
    {"prohibit_set_off": True}, {"setoff": "hard negative — rebate credit application, not debt netting"},
    "ACCEPT", "AUTOMATIC", None,
    "Compound negative control: ordinary role/net-days extraction combined with a routine rebate-credit "
    "mechanic that must not trigger the set-off detector.", "S3")

print("ABSOLUTE FINAL COUNT:", len(CASES))

# ============================================================================
# Family L — explicit absence coverage across all three adapters
# ============================================================================
add("S48-L-L-01", "liability", 1, ["L"],
    "1. Services. Thistlebrook Custom Millwork Supply shall fabricate and deliver custom cabinetry "
    "components as described in Exhibit A.\n\n2. Payment. Client shall pay $8,000 upon delivery.\n\n"
    "3. Term. This Agreement continues for eighteen months.",
    {"contract_side": "sell_side"}, {"presence": "genuinely absent"},
    "NOT_APPLICABLE", "AUTOMATIC", {"expected_classification": "CONFIRMED_ABSENT"},
    "No limitation-of-liability clause anywhere in the document — correct outcome is confident absence.",
    "S2")
add("S48-I-L-01", "indemnification", 1, ["L"],
    "1. Services. Featherline Custom Weathervane Repair shall repair the weathervane described in "
    "Exhibit A.\n\n2. Payment. Client shall pay $1,200 upon completion.\n\n3. Warranty. Work is "
    "warranted for one year.",
    {"contract_side": "sell_side"}, {"presence": "genuinely absent"},
    "NOT_APPLICABLE", "AUTOMATIC", {"expected_classification": "CONFIRMED_ABSENT"},
    "No indemnification language anywhere in the document — correct outcome is confident absence.",
    "S2")
add("S48-P-L-01", "payment_terms", 1, ["L"],
    "1. Services. Grovewick Custom Hedge Sculpting shall maintain the topiary described in Exhibit A.\n\n"
    "2. Confidentiality. Each party shall protect the other's confidential information.\n\n"
    "3. Term. This Agreement renews annually.",
    {}, {"presence": "genuinely absent"},
    "NOT_APPLICABLE", "AUTOMATIC", {"expected_classification": "CONFIRMED_ABSENT"},
    "No payment/invoicing language anywhere in the document.", "S1")
add("S48-L-L-02", "liability", 2, ["L"],
    "9. Limitation of Liability. Liability of Coldbrook Custom Ironwork Fabrication shall be governed "
    "by the terms set forth in the Master Program Agreement between the parties' respective parent "
    "companies (a separate document not attached to or incorporated into this excerpt).",
    {"contract_side": "sell_side"}, {"presence": "referenced but target missing entirely"},
    "MUST_REDLINE", "SHOULD_REVIEW", {"expected_classification": "EXPECTED_BUT_MISSING"},
    "The clause exists and is recognized, but delegates its ENTIRE substance to an external document not "
    "provided — no enforceable numeric cap is stated at all within reach of this evaluation.", "S3")

print("WITH_L:", len(CASES))

# ============================================================================
# PHASE 4 — FORMATTING MUTATIONS (>= 30), presentation-only changes to a
# subset of semantic cases above. Reported SEPARATELY from semantic evidence.
# ============================================================================

MUTATIONS = []


def add_mutation(mut_id, base_id, mutated_text, mutation_kind):
    base = next(c for c in CASES if c["id"] == base_id)
    MUTATIONS.append(dict(
        id=mut_id, base_id=base_id, adapter=base["adapter"], kwargs=base["kwargs"],
        text=mutated_text, mutation_kind=mutation_kind,
        expected_result=base["expected_result"], review=base["review"],
    ))


_MUT_SOURCES = [
    CASES[i]["id"] for i in range(0, len(CASES), max(1, len(CASES) // 32))
][:32]
_MUT_KINDS = [
    "line_breaks_mid_sentence", "tabs_for_indentation", "numbered_list_reformat",
    "bullet_reformat", "all_caps_heading", "extra_whitespace", "section_number_style_change",
    "parenthetical_layout_change", "semicolon_to_newline",
]

for i, base_id in enumerate(_MUT_SOURCES):
    base_text = next(c["text"] for c in CASES if c["id"] == base_id)
    kind = _MUT_KINDS[i % len(_MUT_KINDS)]
    if kind == "line_breaks_mid_sentence":
        mutated = base_text.replace(". ", ".\n") if ". " in base_text else base_text + "\n"
    elif kind == "tabs_for_indentation":
        mutated = "\t" + base_text.replace("\n\n", "\n\n\t")
    elif kind == "numbered_list_reformat":
        mutated = base_text.replace("9. Limitation of Liability.", "9.\n\tLimitation of Liability.") \
            .replace("8. Indemnification.", "8.\n\tIndemnification.") \
            .replace("8. Risk Allocation.", "8.\n\tRisk Allocation.") \
            .replace("6. Payment Terms.", "6.\n\tPayment Terms.")
    elif kind == "bullet_reformat":
        mutated = "- " + base_text.replace(". ", "\n- ", 1)
    elif kind == "all_caps_heading":
        mutated = base_text.replace("Limitation of Liability", "LIMITATION OF LIABILITY") \
            .replace("Indemnification", "INDEMNIFICATION").replace("Payment Terms", "PAYMENT TERMS") \
            .replace("Risk Allocation", "RISK ALLOCATION")
    elif kind == "extra_whitespace":
        mutated = "   " + base_text.replace("  ", "   ").replace(" ", "  ", 3)
    elif kind == "section_number_style_change":
        mutated = base_text.replace("9. ", "Section 9: ").replace("8. ", "Section 8: ") \
            .replace("6. ", "Section 6: ")
    elif kind == "parenthetical_layout_change":
        mutated = base_text.replace("(", "\n(").replace(")", ")\n", 1)
    else:  # semicolon_to_newline
        mutated = base_text.replace("; ", ";\n")
    if mutated == base_text:
        # fallback: guarantee a genuine presentation-only change even if the
        # targeted pattern wasn't present in this particular base text.
        mutated = base_text.replace(". ", ".  ")
        kind = kind + "+whitespace_fallback"
    add_mutation(f"S48-FMT-{i+1:02d}", base_id, mutated, kind)

print("MUTATIONS:", len(MUTATIONS))
