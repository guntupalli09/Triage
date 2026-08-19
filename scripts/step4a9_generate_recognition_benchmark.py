#!/usr/bin/env python3
"""Step 4A.9 — indemnification recognition benchmark, built and locked
BEFORE any production code is modified (Phase 4). Ground truth assigned by
the author from each template's own known structure. Domains are fresh
relative to Step 4A.8 and all earlier corpora."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "benchmarks"
CASES = []
_seen = set()


def add(id_, label, text, kwargs=None, discover_expected=True, structure_expected=None,
        actor=None, beneficiary=None, direction=None, note=""):
    assert id_ not in _seen, id_
    _seen.add(id_)
    CASES.append(dict(
        id=id_, label=label,  # "positive" | "negative"
        text=text, kwargs=kwargs or {},
        discover_expected=discover_expected,  # should broad discovery fire?
        structure_expected=structure_expected,  # "ESTABLISHED" | "UNRESOLVED" | None
        actor=actor, beneficiary=beneficiary, direction=direction, note=note,
    ))


# ============================================================================
# POSITIVES — >= 100. Genuinely varied risk-transfer expressions.
# Domains fresh vs. Step 4A.8 (no repeated entity names/domains).
# ============================================================================

POS_DOMAINS = [
    "Ferrowatch Industrial Boiler Inspection", "Lockstone Vault Installation Services",
    "Nightloom Custom Lighting Design", "Oakspire Timber Framing Guild",
    "Pikeview Alpine Rescue Training", "Quenchfield Fire Hydrant Servicing",
    "Ridgemark Land Surveying Corp", "Sableridge Custom Taxidermy Studio",
    "Tarnhollow Custom Blacksmithing", "Umberlight Solar Array Cleaning",
    "Vesperwood Custom Organ Building", "Wraithmoor Pest Fumigation Services",
    "Xandergate Custom Metal Casting", "Yewfield Custom Barn Restoration",
    "Zenithcrest Custom Antenna Installation", "Ashfall Custom Ceramic Tiling",
    "Briarcliff Custom Stonemasonry", "Cragwater Custom Diving Instruction",
    "Duskmere Custom Puppet Theater", "Emberfall Custom Glassblowing Studio",
    "Frostgate Custom Ice Carving", "Gravenhurst Custom Tattoo Studio",
    "Hallowbrook Custom Beekeeping Removal", "Ironspan Custom Bridge Inspection",
    "Junipergate Custom Aromatherapy Blending", "Kettlespire Custom Distillery Servicing",
    "Larkmoor Custom Falconry Training", "Millgate Custom Weaving Instruction",
    "Nettlewood Custom Herbalism Consulting", "Oxfordale Custom Cheese Aging",
]
VERB_TEMPLATES = [
    ("shall indemnify, defend, and hold harmless {b} from", "canonical"),
    ("shall indemnify and hold {b} harmless from", "canonical-variant"),
    ("shall be responsible for, and shall reimburse {b} in full for", "reimbursement"),
    ("shall assume all liability for, and undertakes to make {b} whole in respect of", "loss-bearing"),
    ("shall stand in {b}'s place in defending against, and shall bear the cost of resolving", "duty-to-defend"),
    ("shall protect {b} from, and satisfy on {b}'s behalf, any claim arising from", "protection"),
    ("agrees to answer for, and to save {b} harmless from", "answer-for"),
    ("shall bear full responsibility for defending and satisfying, on {b}'s behalf,", "bear-responsibility-reordered"),
    ("shall bear full responsibility for defending and satisfying any claim on {b}'s behalf, arising from", "bear-responsibility-canonical-order"),
    ("undertakes to make {b} whole for, and to assume the defense of", "make-whole-canonical"),
]
for i, entity in enumerate(POS_DOMAINS):
    verb, concept = VERB_TEMPLATES[i % len(VERB_TEMPLATES)]
    verb_f = verb.format(b="Client")
    add(
        f"S49-REC-POS-{i+1:03d}", "positive",
        f"8. Risk Allocation. {entity} {verb_f} any third-party claim arising from {entity}'s "
        f"negligence in performing services under this Agreement.",
        {"contract_side": "sell_side"}, True, "ESTABLISHED",
        actor=entity, beneficiary="Client", direction="exposure",
        note=f"verb family: {concept}",
    )

# Passive voice variants
PASSIVE_DOMAINS = [
    "Palewick Custom Cartography Studio", "Quillhaven Custom Bookplate Engraving",
    "Rimefrost Custom Snowshoe Making", "Silverbrook Custom Violin Repair",
    "Thistlemoor Custom Wreath Weaving", "Underspire Custom Well Capping",
]
for i, entity in enumerate(PASSIVE_DOMAINS):
    add(
        f"S49-REC-POS-PASS-{i+1:02d}", "positive",
        f"8. Risk Allocation. Any third-party claim arising from {entity}'s negligence shall be "
        f"defended and satisfied by {entity} on Client's behalf, with all resulting losses to be "
        f"reimbursed to Client in full.",
        {"contract_side": "sell_side"}, True, "ESTABLISHED",
        actor=entity, beneficiary="Client", direction="exposure",
        note="passive-voice risk-transfer statement",
    )

# Reciprocal / bilateral
RECIP_DOMAINS = [
    ("Vantagepoint Custom Kite Design", "Retailer"), ("Wickerlight Custom Basket Import", "Distributor"),
    ("Xenonfrost Custom Neon Repair", "Client"), ("Yarrowdale Custom Herb Drying", "Cooperative"),
    ("Zephyrmoor Custom Windvane Casting", "Architect"),
]
for i, (a, b) in enumerate(RECIP_DOMAINS):
    add(
        f"S49-REC-POS-RECIP-{i+1:02d}", "positive",
        f"8. Risk Allocation. {a} shall bear responsibility for, and reimburse {b} in full for, any "
        f"claim arising from {a}'s own negligence, and {b} shall likewise bear responsibility for, "
        f"and reimburse {a} in full for, any claim arising from {b}'s own negligence.",
        {"contract_side": "sell_side"}, True, "ESTABLISHED",
        actor=a, beneficiary=b, direction="reciprocal",
        note="reciprocal risk-transfer using the fresh reimbursement idiom on both sides",
    )

# IP / bodily injury / regulatory / data / tax / employment specific triggers
TRIGGER_DOMAINS = [
    ("Ashworth Custom Circuit Board Fab", "third-party patent infringement claims"),
    ("Briardown Custom Playground Install", "bodily injury or property damage claims"),
    ("Cloverpeak Custom Food Truck Fabrication", "regulatory fines arising from health-code violations"),
    ("Driftglass Custom Data Migration Services", "claims arising from unauthorized disclosure of personal data"),
    ("Emberton Custom Payroll Bureau", "claims arising from misclassification of workers"),
    ("Falconbridge Custom Tax Advisory", "penalties assessed due to advisory errors"),
]
for i, (entity, trig) in enumerate(TRIGGER_DOMAINS):
    add(
        f"S49-REC-POS-TRIG-{i+1:02d}", "positive",
        f"8. Risk Allocation. {entity} shall assume all liability for, and shall make Client whole in "
        f"respect of, any {trig} attributable to {entity}'s performance under this Agreement.",
        {"contract_side": "sell_side"}, True, "ESTABLISHED",
        actor=entity, beneficiary="Client", direction="exposure",
        note=f"specific trigger category: {trig}",
    )

# Multi-word roles, definitions, provisos, long sentences, first-party structures
add("S49-REC-POS-LONG-01", "positive",
    "8. Risk Allocation. Notwithstanding anything to the contrary elsewhere in this Agreement, and "
    "subject only to the express carve-outs in Section 8.5, Northgate Regional Environmental "
    "Consulting Group, LLC shall, at its own cost and expense, assume all liability for and shall make "
    "Client Municipal Water Authority whole in respect of any and all third-party claims, of whatever "
    "kind or nature, arising out of or in any way related to Northgate Regional Environmental "
    "Consulting Group, LLC's negligent performance of the services described in Exhibit A.",
    {"contract_side": "sell_side"}, True, "ESTABLISHED",
    actor="Northgate Regional Environmental Consulting Group, LLC", beneficiary="Client Municipal Water Authority",
    direction="exposure", note="long, heavily-qualified sentence, multi-word entity name")
add("S49-REC-POS-DEF-01", "positive",
    "1. Definitions. 'Fabricator' means Coldwater Custom HVAC Ductwork Fabrication, and 'Owner' means "
    "the party engaging Fabricator's services.\n\n8. Risk Allocation. Fabricator shall bear full "
    "responsibility for defending and satisfying, on Owner's behalf, any claim arising from "
    "Fabricator's negligence.",
    {"contract_side": "sell_side"}, True, "ESTABLISHED",
    actor="Fabricator", beneficiary="Owner", direction="exposure",
    note="defined-term role names, reordered bear-responsibility idiom")
add("S49-REC-POS-FIRST-01", "positive",
    "8. Risk Allocation. Ashgrove Custom Aquarium Livestock Import shall protect Client from, and "
    "satisfy on Client's behalf, any claim, whether asserted by a third party or brought directly "
    "between the parties, arising from Ashgrove's negligence.",
    {"contract_side": "sell_side"}, True, "ESTABLISHED",
    actor="Ashgrove Custom Aquarium Livestock Import", beneficiary="Client", direction="exposure",
    note="first-party (direct-claim) risk-transfer structure")

print(f"Positives so far: {len(CASES)}")
PYEOF_MARK = None

# More positives: unilateral, procedural, multi-party, amendments, schedules
MORE_DOMAINS = [
    "Grovemantle Custom Vineyard Trellising", "Hollowspire Custom Church Bell Repair",
    "Ironvale Custom Anvil Forging", "Jasperfield Custom Gemstone Cutting",
    "Kettlebridge Custom Rain Gutter Fab", "Larkspire Custom Weathercock Casting",
    "Moonvale Custom Herbal Tincture Blending", "Nettlefen Custom Reed Basket Weaving",
    "Oxhollow Custom Cider Press Building", "Pemberly Custom Sundial Engraving",
    "Quiverfield Custom Archery Range Design", "Ravensdale Custom Falconry Mews Construction",
    "Silverfen Custom Wetland Boardwalk Build", "Thornspire Custom Beehive Carpentry",
    "Underfell Custom Mine Shaft Inspection", "Vellumoor Custom Parchment Making",
    "Whistlecrag Custom Bagpipe Repair", "Xylophage Custom Termite Treatment",
    "Yewshade Custom Arbor Trellis Design", "Zestwood Custom Citrus Grove Consulting",
]
for i, entity in enumerate(MORE_DOMAINS):
    verb, concept = VERB_TEMPLATES[(i + 3) % len(VERB_TEMPLATES)]
    verb_f = verb.format(b="Owner")
    tier2 = i % 2 == 0
    text = (
        f"8. Risk Allocation. {entity} {verb_f} any claim arising from {entity}'s negligence."
    )
    if tier2:
        text = (
            f"8. Risk Allocation. Subject to Section 8.6 and without limiting any other remedy Owner "
            f"may have, {entity} {verb_f} any claim, of whatever kind, arising from {entity}'s "
            f"negligent acts or omissions in connection with this Agreement."
        )
    add(
        f"S49-REC-POS-MORE-{i+1:02d}", "positive", text, {"contract_side": "sell_side"}, True, "ESTABLISHED",
        actor=entity, beneficiary="Owner", direction="exposure", note=f"verb family: {concept}",
    )

# Unilateral (buy_side beneficiary) and procedural cooperation-heavy variants
UNI_DOMAINS = [
    "Ashcombe Custom Millpond Restoration", "Briarhollow Custom Grist Mill Repair",
]
for i, entity in enumerate(UNI_DOMAINS):
    add(f"S49-REC-POS-UNI-{i+1:02d}", "positive",
        f"8. Risk Allocation. {entity} shall answer for, and save Client harmless from, any claim "
        f"arising from {entity}'s negligence, and shall cooperate fully with Client in the defense of "
        f"any such claim upon prompt written notice.",
        {"contract_side": "sell_side"}, True, "ESTABLISHED",
        actor=entity, beneficiary="Client", direction="exposure", note="procedural cooperation layered on risk-transfer")

# Multi-party
add("S49-REC-POS-MULTI-01", "positive",
    "8. Risk Allocation. Coldharbor Consortium Members (defined collectively in Exhibit A) shall each "
    "assume all liability for, and shall make the Sponsoring Municipality whole in respect of, any "
    "claim arising from that Member's own negligence in performing services under this Agreement.",
    {"contract_side": "sell_side"}, True, "ESTABLISHED",
    actor="Coldharbor Consortium Members", beneficiary="Sponsoring Municipality", direction="exposure",
    note="multi-party (consortium) risk-transfer")

# Amendment/schedule referenced
add("S49-REC-POS-AMEND-01", "positive",
    "8. Risk Allocation. Fenwright Custom Cooperage Services shall bear full responsibility for "
    "defending and satisfying any claim on Winery's behalf, arising from Fenwright's negligence.\n\n"
    "Amendment No. 1. Section 8 is amended to add: 'This obligation extends to claims arising from "
    "subcontractors Fenwright engages.'",
    {"contract_side": "sell_side"}, True, "ESTABLISHED",
    actor="Fenwright Custom Cooperage Services", beneficiary="Winery", direction="exposure",
    note="canonical idiom plus a valid amendment expanding scope")

print(f"Total after more positives: {len(CASES)}")

# Final positive push (>= 100)
FINAL_POS_DOMAINS = [
    "Alderwick Custom Millrace Repair", "Barrowfen Custom Reed Thatching",
    "Cindergrove Custom Kiln Building", "Duskholt Custom Watchtower Restoration",
    "Elmscar Custom Drystone Walling", "Fallowmere Custom Hedgerow Laying",
    "Grimsby Custom Weathercock Repair", "Hearthstone Custom Bake Oven Building",
    "Ivorygate Custom Piano Case Restoration", "Junebrook Custom Springhouse Repair",
    "Kestrelfen Custom Dovecote Building", "Larchwood Custom Timber Bridge Repair",
    "Marrowfield Custom Threshing Floor Repair", "Nightshade Custom Herb Garden Design",
    "Oxbridge Custom Punt Boat Building", "Pinewick Custom Sawmill Servicing",
    "Quillfen Custom Feather Duster Making", "Rosemere Custom Rose Arbor Building",
    "Stonebrook Custom Millwheel Repair", "Thatchgate Custom Roof Thatching",
    "Underbrook Custom Ford Crossing Repair", "Vinehollow Custom Grape Press Building",
    "Windmere Custom Windmill Sail Repair", "Yewbridge Custom Footbridge Repair",
    "Zestholm Custom Orchard Ladder Building", "Ashcroft Custom Well Pump Repair",
]
for i, entity in enumerate(FINAL_POS_DOMAINS):
    verb, concept = VERB_TEMPLATES[(i + 7) % len(VERB_TEMPLATES)]
    verb_f = verb.format(b="Landowner")
    add(
        f"S49-REC-POS-FINAL-{i+1:02d}", "positive",
        f"8. Risk Allocation. {entity} {verb_f} any claim arising from {entity}'s negligence in "
        f"connection with the work described in Exhibit A.",
        {"contract_side": "sell_side"}, True, "ESTABLISHED",
        actor=entity, beneficiary="Landowner", direction="exposure", note=f"verb family: {concept}",
    )

print(f"FINAL positive count: {len([c for c in CASES if c['label']=='positive'])}")

# ============================================================================
# NEGATIVES — >= 80. Hard negatives: insurance, LoL, warranties, damages,
# payment obligations, refunds/credits, ordinary breach remedies, defense-
# without-indemnity, non-risk-transfer responsibility statements, release
# concepts distinct from indemnity, procedural cooperation alone.
# ============================================================================

NEG_INSURANCE = [
    "Alderfen Custom Rope Access Services", "Briskwater Custom Tunnel Lighting",
    "Cragmoor Custom Avalanche Barrier Install",
]
for i, entity in enumerate(NEG_INSURANCE):
    add(f"S49-REC-NEG-INS-{i+1:02d}", "negative",
        f"12. Insurance. {entity} shall maintain commercial general liability insurance with limits of "
        f"not less than $2,000,000 per occurrence, and shall provide Client with a certificate of "
        f"insurance evidencing such coverage upon request.",
        {}, False, None, note="insurance requirement, no risk-transfer obligation stated")

NEG_LOL = [
    "Duskwell Custom Elevator Cab Refinishing", "Emberline Custom Cold Room Install",
]
for i, entity in enumerate(NEG_LOL):
    add(f"S49-REC-NEG-LOL-{i+1:02d}", "negative",
        f"9. Limitation of Liability. {entity}'s aggregate liability to Client shall not exceed one (1) "
        f"times the annual fees paid.",
        {}, False, None, note="ordinary liability cap, not a risk-transfer/indemnity obligation")

NEG_WARRANTY = [
    "Frostgate Custom Skylight Sealing", "Graveltide Custom Retaining Wall Build",
]
for i, entity in enumerate(NEG_WARRANTY):
    add(f"S49-REC-NEG-WARR-{i+1:02d}", "negative",
        f"7. Warranty. {entity} warrants that all work will be free from defects in materials and "
        f"workmanship for a period of two years, and shall repair or replace any defective work at no "
        f"additional cost.",
        {}, False, None, note="warranty repair-or-replace remedy, not indemnity")

NEG_DAMAGES = [
    "Hollowfield Custom Grain Bin Repair", "Ironwood Custom Sluice Gate Building",
]
for i, entity in enumerate(NEG_DAMAGES):
    add(f"S49-REC-NEG-DMG-{i+1:02d}", "negative",
        f"10. Liquidated Damages. {entity} shall pay liquidated damages of $500 per day for each day of "
        f"delay beyond the agreed completion date, subject to a cap of $15,000.",
        {}, False, None, note="liquidated damages, not risk-transfer")

NEG_PAYMENT = [
    "Junipergrove Custom Root Cellar Digging", "Kettlebrook Custom Sluiceway Repair",
]
for i, entity in enumerate(NEG_PAYMENT):
    add(f"S49-REC-NEG-PAY-{i+1:02d}", "negative",
        f"6. Payment. Client shall pay {entity} within 30 days of invoice, and shall bear responsibility "
        f"for remitting payment on the schedule set forth in Exhibit B.",
        {}, False, None, note="'bear responsibility for remitting payment' is a payment obligation, not risk transfer")

NEG_REFUND = [
    "Larchmont Custom Weathervane Polishing", "Millhaven Custom Grist Stone Dressing",
]
for i, entity in enumerate(NEG_REFUND):
    add(f"S49-REC-NEG-REF-{i+1:02d}", "negative",
        f"11. Refunds. {entity} shall reimburse Client for any prepaid amounts attributable to services "
        f"not rendered, within 15 days of Client's written request.",
        {}, False, None, note="'reimburse' used for an ordinary refund of unrendered fees, not a third-party claim")

NEG_BREACH = [
    "Nettlefield Custom Cistern Lining", "Oxwood Custom Barn Door Track Repair",
]
for i, entity in enumerate(NEG_BREACH):
    add(f"S49-REC-NEG-BR-{i+1:02d}", "negative",
        f"13. Remedies. In the event of a material breach by {entity}, Client may terminate this "
        f"Agreement upon 30 days' written notice and pursue any remedy available at law or in equity.",
        {}, False, None, note="ordinary breach/termination remedy, no risk-transfer language")

NEG_DEFENSE_ONLY = [
    "Pemberton Custom Chimney Cap Fabrication", "Quarrystone Custom Foundation Underpinning",
]
for i, entity in enumerate(NEG_DEFENSE_ONLY):
    add(f"S49-REC-NEG-DEF-{i+1:02d}", "negative",
        f"14. Litigation Cooperation. {entity} shall reasonably cooperate with Client and provide "
        f"requested documents and witnesses in connection with any litigation involving Client, at "
        f"Client's expense.",
        {}, False, None, note="procedural litigation cooperation without any assumption of liability")

NEG_RESPONSIBILITY = [
    "Ravensfield Custom Silo Ladder Install", "Sablewood Custom Grain Auger Repair",
]
for i, entity in enumerate(NEG_RESPONSIBILITY):
    add(f"S49-REC-NEG-RESP-{i+1:02d}", "negative",
        f"5. Scope of Work. {entity} shall be responsible for supplying all materials, tools, and labor "
        f"necessary to complete the work described in Exhibit A on schedule.",
        {}, False, None, note="'shall be responsible for' describing ordinary performance scope, not a third-party claim obligation")

NEG_RELEASE = [
    "Thornfield Custom Livestock Fence Repair", "Underbrook Custom Spring Box Building",
]
for i, entity in enumerate(NEG_RELEASE):
    add(f"S49-REC-NEG-REL-{i+1:02d}", "negative",
        f"15. Release. Client releases {entity} from any claim arising from Client's own use of the "
        f"completed work after final acceptance.",
        {}, False, None, note="a release running FROM Client TO the vendor — the inverse direction of indemnity, not itself an indemnity obligation")

NEG_HOLD_NONINDEM = [
    "Vinemoor Custom Trellis Repair", "Wickford Custom Hay Loft Repair",
]
for i, entity in enumerate(NEG_HOLD_NONINDEM):
    add(f"S49-REC-NEG-HOLD-{i+1:02d}", "negative",
        f"16. Confidentiality. {entity} shall hold Client's confidential information in strict "
        f"confidence and shall not disclose it to any third party without prior written consent.",
        {}, False, None, note="'hold...in confidence' — a confidentiality obligation, not 'hold harmless'")

# More negatives to reach 80: general boilerplate distractors
NEG_MISC_DOMAINS = [
    "Xanderfield Custom Pump House Repair", "Yewgate Custom Aqueduct Repair",
    "Zestbrook Custom Millpond Dredging", "Ashenvale Custom Barn Roof Repair",
    "Briarfen Custom Corn Crib Repair", "Cindervale Custom Smokehouse Repair",
    "Duskfield Custom Well House Repair", "Elmgate Custom Root Cellar Sealing",
]
NEG_MISC_CLAUSES = [
    ("17. Force Majeure.", "Neither party shall be liable for delay caused by events beyond its "
     "reasonable control, including acts of God, labor disputes, or governmental action."),
    ("18. Assignment.", "Neither party may assign this Agreement without the prior written consent of "
     "the other party, which consent shall not be unreasonably withheld."),
    ("19. Governing Law.", "This Agreement shall be governed by the laws of the State of Delaware, "
     "without regard to conflict-of-law principles."),
    ("20. Notices.", "All notices shall be sent by certified mail to the addresses set forth on the "
     "signature page of this Agreement."),
    ("21. Entire Agreement.", "This Agreement constitutes the entire agreement between the parties and "
     "supersedes all prior negotiations, representations, or agreements."),
    ("22. Severability.", "If any provision of this Agreement is held invalid, the remaining "
     "provisions shall continue in full force and effect."),
    ("23. Independent Contractor.", "The relationship of the parties is that of independent "
     "contractors, and nothing herein shall be construed to create a partnership or joint venture."),
    ("24. Non-Solicitation.", "Neither party shall solicit the other's employees for a period of one "
     "year following termination of this Agreement."),
]
for i, entity in enumerate(NEG_MISC_DOMAINS):
    heading, clause = NEG_MISC_CLAUSES[i % len(NEG_MISC_CLAUSES)]
    add(f"S49-REC-NEG-MISC-{i+1:02d}", "negative",
        f"{heading} {clause}", {}, False, None,
        note="ordinary boilerplate clause unrelated to risk transfer, entity name unused in clause body")

print(f"FINAL negative count: {len([c for c in CASES if c['label']=='negative'])}")
print(f"GRAND TOTAL: {len(CASES)}")

# Additional negatives to reach >= 80
NEG_MISC2_DOMAINS = [
    "Foxglenn Custom Mill Sluice Repair", "Graniteford Custom Weir Repair",
    "Hollowmere Custom Culvert Repair", "Inglewood Custom Sheep Dip Repair",
    "Junipervale Custom Cattle Guard Repair", "Kettlemoor Custom Windbreak Planting",
    "Larkhollow Custom Hedge Maze Design", "Mosswick Custom Rain Garden Design",
    "Nightfen Custom Bat House Building", "Oxendale Custom Owl Box Building",
    "Pinemarsh Custom Bee Skep Weaving", "Quillmoor Custom Falcon Perch Building",
    "Ravenscar Custom Crow's Nest Repair", "Silverdale Custom Lighthouse Lamp Repair",
    "Thornwick Custom Buoy Painting", "Underwood Custom Dock Piling Repair",
    "Vinehollow Custom Arbor Gate Repair", "Wickmoor Custom Stile Repair",
    "Xanderfen Custom Cattle Chute Repair", "Yewmarsh Custom Pond Liner Repair",
    "Zestfen Custom Weathervane Balancing", "Ashmoor Custom Silo Vent Repair",
    "Briarfield Custom Grain Chute Repair", "Cindermoor Custom Forge Bellows Repair",
    "Duskfen Custom Tanning Vat Repair", "Elmfield Custom Loom Repair",
    "Fallowbrook Custom Spinning Wheel Repair", "Grimwood Custom Cider Barrel Repair",
    "Hazelmoor Custom Cheese Press Repair", "Inklewood Custom Quill Pen Making",
]
for i, entity in enumerate(NEG_MISC2_DOMAINS):
    heading, clause = NEG_MISC_CLAUSES[i % len(NEG_MISC_CLAUSES)]
    add(f"S49-REC-NEG-MISC2-{i+1:02d}", "negative",
        f"{heading} {clause}", {}, False, None,
        note="ordinary boilerplate clause unrelated to risk transfer")

print(f"FINAL negative count: {len([c for c in CASES if c['label']=='negative'])}")
print(f"GRAND TOTAL: {len(CASES)}")

# Final negative push (>= 80)
NEG_FINAL_DOMAINS = [
    "Junebrook Custom Loom Shuttle Repair", "Kettlefen Custom Wool Carder Repair",
    "Larchmoor Custom Fulling Mill Repair", "Millwick Custom Dye Vat Repair",
    "Nettlemoor Custom Spindle Repair", "Oxfen Custom Weaver's Reed Repair",
    "Pinehollow Custom Fleece Sorting Table Build", "Quillfen Custom Ink Well Casting",
    "Ravensmoor Custom Parchment Stretcher Repair", "Silverfen Custom Bookbinding Press Repair",
    "Thornbrook Custom Gilding Wheel Repair", "Underfen Custom Vellum Scraper Repair",
]
for i, entity in enumerate(NEG_FINAL_DOMAINS):
    heading, clause = NEG_MISC_CLAUSES[(i + 4) % len(NEG_MISC_CLAUSES)]
    add(f"S49-REC-NEG-FINAL-{i+1:02d}", "negative",
        f"{heading} {clause}", {}, False, None,
        note="ordinary boilerplate clause unrelated to risk transfer")

# A few more "close paraphrase but still not risk-transfer" hard negatives
add("S49-REC-NEG-CLOSE-01", "negative",
    "8. Service Standards. Vendor shall be responsible for maintaining service levels described in "
    "Exhibit C and shall remediate any deficiency identified during the quarterly review.",
    {}, False, None, note="'responsible for' + 'remediate' describing SLA performance, not risk transfer")
add("S49-REC-NEG-CLOSE-02", "negative",
    "8. Quality Assurance. Vendor shall assume responsibility for final inspection of all units prior "
    "to shipment and shall bear the cost of any rework required to meet specification.",
    {}, False, None, note="'assume responsibility' + 'bear the cost' describing internal QA rework, no third party involved")
add("S49-REC-NEG-CLOSE-03", "negative",
    "8. Support Obligations. Vendor shall protect the integrity of Client's production environment and "
    "shall satisfy all service-level commitments described in the Support Addendum.",
    {}, False, None, note="'protect' + 'satisfy' describing operational commitments, not a claim/loss context")

print(f"FINAL negative count: {len([c for c in CASES if c['label']=='negative'])}")
print(f"GRAND TOTAL: {len(CASES)}")

add("S49-REC-NEG-CLOSE-04", "negative",
    "8. Escrow. The parties shall deposit disputed funds into escrow pending resolution, and the "
    "escrow agent shall hold such funds harmless from claims by either party pending release.",
    {}, False, None, note="'hold...harmless' used in an escrow-mechanics sense, not third-party indemnity")
add("S49-REC-NEG-CLOSE-05", "negative",
    "8. Data Backup. Vendor shall reimburse Client's IT department for reasonable costs incurred in "
    "restoring data from backup following a scheduled maintenance window, up to $500 per incident.",
    {}, False, None, note="'reimburse' for a routine operational cost, not a third-party claim")
add("S49-REC-NEG-CLOSE-06", "negative",
    "8. Facility Access. Contractor's personnel shall be responsible for badge check-in and shall "
    "answer for any lost access credentials by paying a $50 replacement fee.",
    {}, False, None, note="'responsible for' + 'answer for' describing a badge-replacement fee, not risk transfer")
add("S49-REC-NEG-CLOSE-07", "negative",
    "8. Equipment Return. Lessee shall bear the cost of any damage to leased equipment beyond normal "
    "wear and tear upon return, as assessed by Lessor's inspection.",
    {}, False, None, note="'bear the cost' for equipment condition on return, a lease mechanic not risk transfer")

print(f"FINAL negative count: {len([c for c in CASES if c['label']=='negative'])}")
print(f"GRAND TOTAL: {len(CASES)}")
with open('benchmarks/step4a9_recognition_benchmark.json', 'w') as f:
    import json
    json.dump(CASES, f, indent=2)
print("written")
