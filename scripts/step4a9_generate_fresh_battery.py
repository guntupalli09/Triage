#!/usr/bin/env python3
"""Step 4A.9 Phase 13 — fresh development adversarial battery. Development/
adversarial evidence, NOT the final independent frozen validation (that is
Step 4A.10). Tests the Step 4A.9 mechanisms (recognition, monetary parity,
self-flagged/conditional/chained-delegation generalization) against
genuinely new domains/phrasing not used in Step 4A.8 or the Step 4A.9
recognition benchmark."""
import json
from pathlib import Path

CASES = []
_seen = set()


def add(id_, adapter, families, text, kwargs, expected_result, note=""):
    assert id_ not in _seen, id_
    _seen.add(id_)
    CASES.append(dict(id=id_, adapter=adapter, families=families, text=text,
                       kwargs=kwargs, expected_result=expected_result, note=note))


# ============================================================================
# Indemnification (>= 60) — fresh recognition verbs, monetary word-numbers,
# and mechanism generalization, entirely new domains
# ============================================================================
I_DOMAINS = [
    "Amberfield Custom Trellis Repair", "Briarcross Custom Anvil Sharpening",
    "Cragmont Custom Bellows Repair", "Duskvale Custom Loom Threading",
    "Elmshadow Custom Kiln Firing", "Fallowdale Custom Millstone Dressing",
    "Grimwald Custom Forge Bellows", "Hollowmere Custom Spinning Wheel Repair",
    "Ironbark Custom Weathercock Casting", "Junipercrag Custom Bee Skep Weaving",
    "Kettlebrook Custom Sundial Engraving", "Larchgate Custom Archery Range Design",
    "Mossvale Custom Falconry Mews Repair", "Nightfen Custom Wetland Boardwalk Build",
    "Oxfen Custom Beehive Carpentry", "Pinebrook Custom Mine Shaft Inspection",
    "Quillmoor Custom Parchment Repair", "Ravenshollow Custom Bagpipe Tuning",
    "Silvercrag Custom Termite Treatment", "Thornvale Custom Arbor Trellis Repair",
]
VERBS = [
    "shall be liable for, and shall make good to {b}", "shall accept liability for, and shall recompense {b} in full for",
    "shall shoulder the burden of, and reimburse {b} for", "undertakes to indemnify {b} against, and to defend {b} from",
    "shall be answerable to {b} for, and shall settle on {b}'s behalf",
]
for i, entity in enumerate(I_DOMAINS):
    verb = VERBS[i % len(VERBS)].format(b="Client")
    mult = ["one (1)", "two (2)", "three (3)"][i % 3]
    add(f"S49-DEV-I-{i+1:02d}", "indemnification", ["D"],
        f"8. Risk Allocation. {entity} {verb} any claim arising from {entity}'s negligence, up to a "
        f"cap of {mult} times the annual fees paid.",
        {"contract_side": "sell_side"}, "REQUIRES_REVIEW" if i % 4 == 0 else "ACCEPT_OR_REVIEW",
        note="fresh verb, generalization test of the recognition widening")

# Monetary word-number generalization, fresh basis nouns
for i in range(10):
    entity = I_DOMAINS[i]
    mult_word = ["four (4)", "five (5)", "six (6)", "seven (7)", "eight (8)",
                 "nine (9)", "ten (10)", "two (2)", "three (3)", "one (1)"][i]
    add(f"S49-DEV-I-MULT-{i+1:02d}", "indemnification", ["D"],
        f"8. Indemnification. {entity} shall indemnify, defend, and hold harmless Client from claims "
        f"arising from {entity}'s negligence, up to a cap of {mult_word} times the annual servicing "
        f"charges paid.",
        {"contract_side": "sell_side"}, "ACCEPT_OR_NEGOTIATE",
        note=f"word-number multiplier generalization test: {mult_word}")

# Self-flagged/conditional/chained-delegation generalization, fresh phrasing
add("S49-DEV-I-COND-01", "indemnification", ["F"],
    "8. Indemnification. Fenwright Custom Cooperage shall indemnify, defend, and hold harmless Winery "
    "from claims arising from Fenwright's negligence, up to a cap of two (2) times the fees paid, "
    "unless Winery has designated an alternate cap under the Preferred Client Program, a designation "
    "not yet finalized as of this excerpt.",
    {"contract_side": "sell_side"}, "REQUIRES_REVIEW", note="conditional-applicability, fresh 'finalized' verb")
add("S49-DEV-I-SELF-01", "indemnification", ["G"],
    "8. Indemnification. Ashgrove Custom Livestock Fence Repair shall indemnify, defend, and hold "
    "harmless Client from claims arising from Ashgrove's negligence, the parties conceding that the "
    "precise monetary limit remains an open question pending further negotiation.",
    {"contract_side": "sell_side"}, "REQUIRES_REVIEW", note="self-flagged, fresh 'remains an open question' phrasing")
add("S49-DEV-I-CHAIN-01", "indemnification", ["I"],
    "8. Indemnification. Vendor shall indemnify, defend, and hold harmless Client from claims described "
    "in the Risk Matrix, which Risk Matrix in turn points to the underwriting guidelines maintained by "
    "Vendor's insurer (not included in this excerpt).",
    {"contract_side": "buy_side"}, "REQUIRES_REVIEW", note="chained delegation, fresh 'points to' verb (NOT in the widened verb list - true generalization test)")

# Hard negatives (recognition must NOT over-fire)
I_NEG_DOMAINS = [
    "Umberfen Custom Well House Repair", "Vinegate Custom Grape Press Repair",
    "Wickmoor Custom Stile Repair", "Xanderfen Custom Cattle Chute Repair",
    "Yewmarsh Custom Pond Liner Repair", "Zestfen Custom Weathervane Balancing",
]
NEG_TEXTS = [
    "9. Scope. {e} shall be liable for completing all work described in Exhibit A on the agreed schedule.",
    "10. Payment. {e} shall make good on any invoice discrepancy within 10 business days.",
    "11. Warranty. {e} shall recompense Client for any parts replaced under warranty within the first year.",
    "12. Insurance. {e} shall maintain workers' compensation insurance as required by law.",
    "13. Termination. Either party may terminate this Agreement for convenience upon 60 days' notice.",
    "14. Force Majeure. {e} shall not be liable for delays caused by events beyond its reasonable control.",
]
for i, entity in enumerate(I_NEG_DOMAINS):
    add(f"S49-DEV-I-NEG-{i+1:02d}", "indemnification", ["D"],
        NEG_TEXTS[i].format(e=entity), {}, "NOT_APPLICABLE",
        note="hard negative — ordinary clause using a risk-transfer-adjacent verb, no claim/loss context")

# Reciprocal asymmetry generalization
R_DOMAINS = [
    ("Coalridge Custom Smokehouse Repair", "Distributor"), ("Driftwood Custom Kayak Repair", "Outfitter"),
    ("Emberlight Custom Candle Repair", "Retailer"), ("Frostpine Custom Sled Repair", "Lot Operator"),
]
for i, (a, b) in enumerate(R_DOMAINS):
    add(f"S49-DEV-I-RECIP-{i+1:02d}", "indemnification", ["E"],
        f"8. Indemnification. {a} shall indemnify, defend, and hold harmless {b}, and {b} shall "
        f"indemnify, defend, and hold harmless {a}, in each case from claims arising from the "
        f"indemnifying party's own negligence, up to a cap of two (2) times the fees paid, and "
        f"{a}'s obligation is subject to a materially narrower 'gross negligence only' standard, "
        f"whereas {b}'s obligation covers ordinary negligence as well.",
        {"contract_side": "sell_side"}, "REQUIRES_REVIEW",
        note="causation-standard-style asymmetry via a fresh 'gross negligence only' vs 'ordinary negligence' contrast")

extra_needed = 60 - len([c for c in CASES if c['adapter']=='indemnification'])
EXTRA_DOMAINS = [
    "Gravelback Custom Sawmill Repair", "Hollowfen Custom Grist Mill Repair", "Inglewood Custom Sheep Dip Repair",
    "Junipervale Custom Cattle Guard Repair", "Kettlemoor Custom Windbreak Repair", "Larkhollow Custom Hedge Repair",
    "Mosswick Custom Rain Garden Repair", "Nightfen Custom Bat House Repair", "Oxendale Custom Owl Box Repair",
    "Pinemarsh Custom Bee Skep Repair", "Quillmoor Custom Falcon Perch Repair", "Ravenscar Custom Crow Nest Repair",
    "Silverdale Custom Lamp Repair", "Thornwick Custom Buoy Repair", "Underwood Custom Dock Repair",
    "Vinehollow Custom Gate Repair",
]
for i in range(max(0, extra_needed)):
    entity = EXTRA_DOMAINS[i % len(EXTRA_DOMAINS)]
    add(f"S49-DEV-I-FILL-{i+1:02d}", "indemnification", ["D"],
        f"8. Indemnification. {entity} shall indemnify, defend, and hold harmless Client from claims "
        f"arising from {entity}'s negligence, up to a cap of one (1) times the annual fees paid.",
        {"contract_side": "sell_side"}, "ACCEPT", note="ordinary control")

print(f"Indemnification total: {len([c for c in CASES if c['adapter']=='indemnification'])}")

# ============================================================================
# Liability (>= 20) — fresh phrasing of the same mechanisms Step 4A.9 fixed
# ============================================================================
L_DOMAINS = [
    "Amberfield Precision Optics Servicing", "Briarhollow Grain Elevator Repair",
    "Coldharbor Marine Engine Overhaul", "Duskvale Custom Wine Vat Fabrication",
    "Elmshadow Custom Barn Crane Install", "Fallowdale Custom Silo Vent Repair",
    "Grimwald Custom Forge Ventilation", "Hollowmere Custom Distillery Piping",
]
for i, entity in enumerate(L_DOMAINS):
    mult = [1, 2, 3][i % 3]
    add(f"S49-DEV-L-{i+1:02d}", "liability", ["B"],
        f"9. Limitation of Liability. {entity}'s aggregate liability shall not exceed {['one (1)','two (2)','three (3)'][i%3]} "
        f"times the annual servicing fees paid.",
        {"contract_side": "sell_side"}, "ACCEPT_OR_NEGOTIATE", note="ordinary control")
add("S49-DEV-L-COND-01", "liability", ["F"],
    "9. Limitation of Liability. Aggregate liability shall not exceed two (2) times the annual fees "
    "paid, provided that this multiplier applies only if Client has certified compliance with the "
    "Security Addendum, certification not yet completed as of this excerpt.",
    {"contract_side": "sell_side"}, "REQUIRES_REVIEW", note="conditional-applicability, fresh 'certification...completed' phrasing")
add("S49-DEV-L-SELF-01", "liability", ["G"],
    "9. Limitation of Liability. Aggregate liability shall not exceed one (1) times the annual fees "
    "paid, it remaining an open point whether 'fees' includes onboarding charges billed separately.",
    {"contract_side": "sell_side"}, "REQUIRES_REVIEW", note="self-flagged, fresh 'remaining an open point' phrasing")
add("S49-DEV-L-CHAIN-01", "liability", ["I"],
    "9. Limitation of Liability. Aggregate liability shall not exceed one (1) times the annual fees "
    "paid, calculated per Schedule M, which Schedule M in turn points to the vendor's published rate "
    "sheet (not included in this excerpt).",
    {"contract_side": "sell_side"}, "REQUIRES_REVIEW", note="chained delegation, fresh 'points to' verb")
add("S49-DEV-L-GL-01", "liability", ["B"],
    "9. Limitation of Liability. Aggregate liability shall not exceed either (a) one (1) times the "
    "annual fees paid, or (b) $40,000, whichever total is greater, as determined when a claim is filed.",
    {"contract_side": "sell_side"}, "REQUIRES_REVIEW", note="greater-of, fresh 'whichever TOTAL is greater' interposed-noun test")
add("S49-DEV-L-DEF-01", "liability", ["H"],
    "9. Limitation of Liability. Aggregate liability shall not exceed the Cap. 'Cap' is defined in "
    "Section 9.1 as one (1) times the annual fees paid, and is likewise separately defined in Section "
    "14.3 as three (3) times the annual fees paid.",
    {"contract_side": "sell_side"}, "REQUIRES_REVIEW", note="conflicting definition, fresh 'is likewise separately defined' phrasing")

print(f"Liability total: {len([c for c in CASES if c['adapter']=='liability'])}")

# ============================================================================
# Payment terms (>= 20) — fresh phrasing of the same mechanisms
# ============================================================================
P_DOMAINS = [
    "Ashenvale Custom Barn Repair", "Briarfen Custom Corn Crib Repair", "Cindervale Custom Smokehouse Repair",
    "Duskfield Custom Well House Repair",
]
for i, entity in enumerate(P_DOMAINS):
    net = [30, 45, 15, 60][i]
    add(f"S49-DEV-P-{i+1:02d}", "payment_terms", ["A"],
        f"6. Payment Terms. Client shall pay {entity} within {net} days of invoice date.",
        {}, "ACCEPT", note="ordinary control")
add("S49-DEV-P-COND-01", "payment_terms", ["F"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice, unless Vendor has designated "
    "the order under the Rush Fulfillment Program, in which case payment is due within 10 days; that "
    "designation has not yet been finalized for pending orders.",
    {}, "REQUIRES_REVIEW", note="conditional-applicability, fresh 'finalized' verb")
add("S49-DEV-P-SELF-01", "payment_terms", ["G"],
    "6. Payment Terms. Client shall pay Vendor within 30 days of invoice for base services; the parties "
    "concede that whether expedite fees are included in this schedule remains an open question.",
    {}, "REQUIRES_REVIEW", note="self-flagged, fresh 'remains an open question' phrasing")
add("S49-DEV-P-CHAIN-01", "payment_terms", ["I"],
    "6. Payment Terms. Client shall pay the amount set forth in the Rate Sheet, which Rate Sheet in "
    "turn points to the index maintained by a third-party pricing service (not included in this "
    "excerpt).",
    {}, "REQUIRES_REVIEW", note="chained delegation, fresh 'points to' verb")
add("S49-DEV-P-SF-PORT-01", "payment_terms", ["G"],
    "6. Payment Terms. Payment terms shall be as the parties later determine, no such determination "
    "having yet been made as of the Effective Date.",
    {}, "REQUIRES_REVIEW", note="cross-adapter propagation check — the exact liability-origin phrase, now expected in payment_terms too")
P_MORE = [
    "Emberton Custom Root Cellar Repair", "Falconbridge Custom Tax Advisory Fee Schedule",
    "Grovemantle Custom Trellis Repair", "Hollowspire Custom Bell Repair",
    "Ironvale Custom Anvil Repair", "Jasperfield Custom Gemstone Cutting Fees",
    "Kettlebridge Custom Gutter Repair", "Larkspire Custom Weathercock Repair",
    "Moonvale Custom Tincture Blending Fees", "Nettlefen Custom Basket Repair",
    "Oxhollow Custom Cider Press Repair", "Pemberly Custom Sundial Repair",
    "Quiverfield Custom Range Repair", "Ravensdale Custom Mews Repair",
    "Silverfen Custom Boardwalk Repair",
]
for i, entity in enumerate(P_MORE):
    net = [30, 45, 60][i % 3]
    add(f"S49-DEV-P-MORE-{i+1:02d}", "payment_terms", ["A"],
        f"6. Payment Terms. {entity} shall be paid by Client within {net} days of invoice date.",
        {}, "ACCEPT", note="ordinary control, passive voice")

print(f"Payment total: {len([c for c in CASES if c['adapter']=='payment_terms'])}")
print(f"GRAND TOTAL: {len(CASES)}")

with open(Path(__file__).resolve().parent.parent / "benchmarks" / "step4a9_fresh_battery.json", "w") as f:
    json.dump(CASES, f, indent=2)
print("written")

# Liability top-up (>= 20)
L_MORE = [
    "Ironspan Custom Bridge Cable Inspection", "Junipergate Custom Aromatherapy Blending Fees",
    "Kettlespire Custom Distillery Piping", "Larkmoor Custom Falconry Mews Repair",
    "Millgate Custom Weaving Loom Repair", "Nettlewood Custom Herbalism Studio Repair",
    "Oxfordale Custom Cheese Cave Repair",
]
for i, entity in enumerate(L_MORE):
    mult = [1, 2, 3][i % 3]
    add(f"S49-DEV-L-MORE-{i+1:02d}", "liability", ["B"],
        f"9. Limitation of Liability. {entity}'s aggregate liability to Client shall not exceed "
        f"{['one (1)','two (2)','three (3)'][i%3]} times the annual fees paid.",
        {"contract_side": "sell_side"}, "ACCEPT_OR_NEGOTIATE", note="ordinary control")

print(f"Liability total: {len([c for c in CASES if c['adapter']=='liability'])}")
print(f"GRAND TOTAL: {len(CASES)}")
with open(Path(__file__).resolve().parent.parent / "benchmarks" / "step4a9_fresh_battery.json", "w") as f:
    json.dump(CASES, f, indent=2)
print("re-written")
