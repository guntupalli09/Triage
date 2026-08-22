"""Step 4A.7 Phase 3 — dedicated reciprocal-semantic benchmark.

Built to validate the S4 remediation in indemnification_policy_engine.py:
(1) causation-standard comparison added to _snapshot_indemnity_attribution/
_compare_indemnity_attribution, (2) trigger_treatments/notice/cooperation
added to the named-pair same_pair equality check, (3) the general
except/provided-that named-role detector (_find_exception_clause_named_roles)
reused by both the reciprocal-opener and named-pair paths.

Required categories (per Step 4A.7 Phase 3): >=20 true symmetric, >=20
trigger-differentiated, >=20 causation-differentiated, >=15 category-
differentiated, >=15 exception-differentiated, >=10 compound differences.
>=100 cases total. Hard requirement: unsafe_false_symmetry == 0.

Schema: dict(id, family, text, kwargs, expect_symmetric: bool, note).
expect_symmetric=True means the correct outcome is ACCEPT/ACCEPT_WITH_NOTE
(the two directions really are equivalent and safe to treat as one).
expect_symmetric=False means REQUIRES_REVIEW is correct (the two directions
are NOT verified-equivalent and must not be silently treated as one).
"""

CASES = []


def _add(id_, family, text, expect_symmetric, note, kwargs=None):
    CASES.append(dict(id=id_, family=family, text=text, kwargs=kwargs or {},
                       expect_symmetric=expect_symmetric, note=note))


# ---------------------------------------------------------------------------
# TRUE SYMMETRIC (>=20) — must resolve automatically (ACCEPT/ACCEPT_WITH_NOTE)
# ---------------------------------------------------------------------------
_SYM_DOMAINS = [
    ("Pacific Rim Freight Brokers", "Shipper Client", "fees"),
    ("Alpine Ridge Ski Equipment Rentals", "Renter", "rental fees"),
    ("Coastal Charter Fishing Co.", "Passenger", "charter fees"),
    ("Blue Harbor Yacht Brokerage", "Buyer", "brokerage fees"),
    ("Northgate Data Recovery Services", "Client", "service fees"),
    ("Redstone Event Catering Group", "Host", "catering fees"),
    ("Silverline Payroll Processing LLC", "Employer Client", "processing fees"),
    ("Timber Creek Logging Cooperative", "Mill Buyer", "delivery fees"),
    ("Harbor View Property Inspections", "Homebuyer", "inspection fees"),
    ("Golden Valley Seed Distributors", "Farm Purchaser", "distribution fees"),
    ("Crestline Auto Auction House", "Dealer Bidder", "auction fees"),
    ("Ironwood Fitness Equipment Leasing", "Gym Owner", "leasing fees"),
    ("Bayshore Marine Salvage Corp", "Insurer", "salvage fees"),
    ("Meridian Legal Document Services", "Filer", "filing fees"),
    ("Whitestone Pest Control Partners", "Homeowner", "service fees"),
    ("Cascadia Kayak Tour Operators", "Guest", "tour fees"),
    ("Lonepine Custom Furniture Makers", "Purchaser", "commission fees"),
    ("Emberlight Candle Manufacturing Co.", "Retailer", "wholesale fees"),
    ("Driftwood Surf School Partners", "Student", "lesson fees"),
    ("Copperfield Bookkeeping Associates", "Small Business Client", "bookkeeping fees"),
    ("Northlake Snowplow Services", "Municipality", "plow fees"),
    ("Amberfield Vineyard Management", "Grower", "management fees"),
]
for i, (p1, p2, basis) in enumerate(_SYM_DOMAINS, start=1):
    _add(f"S4B-SYM-{i:02d}", "true_symmetric",
         f"8. Indemnification. {p1} shall indemnify, defend, and hold harmless {p2}, "
         f"and {p2} shall indemnify, defend, and hold harmless {p1}, in each case from "
         f"third-party claims arising from the indemnifying party's own negligence, "
         f"up to a cap of 1 times the annual {basis} paid.",
         True, "Plain reciprocal, no per-party differentiation anywhere.")

# ---------------------------------------------------------------------------
# TRIGGER-DIFFERENTIATED (>=20) — must NOT resolve automatically
# ---------------------------------------------------------------------------
_TRIG_DOMAINS = [
    ("Solaris Rooftop Installers", "Homeowner", "data-breach incidents"),
    ("Vertex Cybersecurity Consulting", "Client", "IP infringement claims"),
    ("Meadowlark Dairy Cooperative", "Distributor", "fraud"),
    ("Ashgrove Pharmaceutical Labs", "Wholesaler", "willful misconduct"),
    ("Riverside Boat Charter Group", "Passenger", "data-breach incidents"),
    ("Nightingale Home Health Services", "Patient Family", "confidentiality breaches"),
    ("Corestone Mining Equipment Corp", "Operator", "IP infringement claims"),
    ("Falcon Ridge Drone Mapping", "Landowner", "fraud"),
    ("Willow Creek Organic Farms", "Retailer", "data-breach incidents"),
    ("Ember Glass Manufacturing", "Buyer", "willful misconduct"),
    ("Tidewater Aquaculture Partners", "Distributor", "confidentiality breaches"),
    ("Northstar Actuarial Consulting", "Client", "IP infringement claims"),
    ("Granite Peak Demolition Co.", "Property Owner", "fraud"),
    ("Bluebell Childcare Franchising", "Franchisee", "data-breach incidents"),
    ("Coppertop Roofing Solutions", "Homeowner", "willful misconduct"),
    ("Sagebrush Environmental Testing", "Client", "confidentiality breaches"),
    ("Lakeshore Marina Fuel Services", "Boat Owner", "fraud"),
    ("Ridgeline Telecom Installers", "Client", "IP infringement claims"),
    ("Sunburst Solar Financing Group", "Homeowner", "data-breach incidents"),
    ("Ferncrest Landscaping Design", "Property Manager", "willful misconduct"),
]
for i, (p1, p2, extra_trigger) in enumerate(_TRIG_DOMAINS, start=1):
    _add(f"S4B-TRIG-{i:02d}", "trigger_differentiated",
         f"8. Indemnification. {p1} shall indemnify, defend, and hold harmless {p2}, "
         f"and {p2} shall indemnify, defend, and hold harmless {p1}, in each case from "
         f"third-party claims arising from the indemnifying party's own negligence, "
         f"up to a cap of 1 times the annual fees paid, except that claims involving "
         f"{extra_trigger} attributable to {p1} shall survive for five (5) years beyond "
         f"the otherwise-applicable survival period.",
         False, "One named party carries an additional, differentiated trigger-category exposure.")

# ---------------------------------------------------------------------------
# CAUSATION-DIFFERENTIATED (>=20) — must NOT resolve automatically
# ---------------------------------------------------------------------------
_CAUSE_DOMAINS = [
    ("Ashford Veterinary Diagnostics", "Referring Clinic"),
    ("Brightwater Aquarium Supply Co.", "Retailer"),
    ("Cinderpath Adventure Guides", "Participant"),
    ("Driftmoor Sailing School", "Student"),
    ("Elmsworth Craft Distillery", "Distributor"),
    ("Fallowfield Grain Cooperative", "Buyer"),
    ("Graystone Structural Engineers", "Developer"),
    ("Hollowbrook Wildlife Rehab", "Volunteer Organization"),
    ("Ironvale Precision Machining", "OEM Customer"),
    ("Juniper Ridge Wine Cellars", "Retail Partner"),
    ("Kestrel Aerial Survey Corp", "Landowner"),
    ("Larkspur Botanical Gardens", "Vendor"),
    ("Millbrook Cheese Creamery", "Distributor"),
    ("Norwood Custom Cabinetry", "Homeowner"),
    ("Oakhaven Senior Living Group", "Resident Family"),
    ("Pinecrest Trail Outfitters", "Guest"),
    ("Quarryview Stoneworks", "Contractor"),
    ("Ridgemont Tutoring Services", "Parent"),
    ("Saltmarsh Oyster Farms", "Distributor"),
    ("Thistledown Wool Mill", "Retailer"),
]
for i, (p1, p2) in enumerate(_CAUSE_DOMAINS, start=1):
    _add(f"S4B-CAUSE-{i:02d}", "causation_differentiated",
         f"8. Indemnification. {p1} shall indemnify, defend, and hold harmless {p2}, "
         f"and {p2} shall indemnify, defend, and hold harmless {p1}, in each case from "
         f"third-party claims arising from the indemnifying party's own gross negligence, "
         f"up to a cap of 1 times the annual fees paid, and {p1}'s indemnification "
         f"obligation is subject to a causation standard of 'sole and proximate cause,' "
         f"whereas {p2}'s indemnification obligation is subject to a broader 'contributing "
         f"cause' standard.",
         False, "Explicitly named, differing causation standards per direction.")

# ---------------------------------------------------------------------------
# CATEGORY-DIFFERENTIATED (>=15) — must NOT resolve automatically
# ---------------------------------------------------------------------------
_CAT_DOMAINS = [
    ("Alderwood Furniture Exporters", "Import Distributor", "defective veneer products"),
    ("Bellcrest Optics Manufacturing", "Retail Chain", "defective lens coatings"),
    ("Cobalt Battery Recyclers", "Municipal Client", "improper disposal claims"),
    ("Duskwood Timber Exporters", "Overseas Buyer", "defective lumber grading"),
    ("Everline Elevator Maintenance", "Building Owner", "malfunction claims"),
    ("Frostbyte Cold Storage Corp", "Food Distributor", "spoilage claims"),
    ("Gearworks Industrial Robotics", "Factory Client", "defective actuator claims"),
    ("Hearthstone Fireplace Installers", "Homeowner", "improper venting claims"),
    ("Ivywall Greenhouse Systems", "Grower Client", "structural collapse claims"),
    ("Jetstream HVAC Manufacturing", "Contractor Buyer", "refrigerant leak claims"),
    ("Kelpwood Marine Coatings", "Boatyard Client", "coating-failure claims"),
    ("Lumenwave Lighting Fixtures", "Commercial Buyer", "electrical-fault claims"),
    ("Moonstone Ceramic Tile Works", "Contractor", "defective-glaze claims"),
    ("Nettlebrook Irrigation Systems", "Farm Client", "leak-damage claims"),
    ("Oreline Metal Fabrication", "Construction Buyer", "weld-failure claims"),
]
for i, (p1, p2, category) in enumerate(_CAT_DOMAINS, start=1):
    _add(f"S4B-CAT-{i:02d}", "category_differentiated",
         f"8. Indemnification. Each party shall indemnify the other party from "
         f"third-party claims arising from its own negligence, up to a cap of 1 times "
         f"the fees paid, except that {p1} (but not {p2}) shall be solely responsible "
         f"for defending claims arising from {category}.",
         False, "Named-party-only defense responsibility scoped to one claim category.")

# ---------------------------------------------------------------------------
# EXCEPTION-DIFFERENTIATED (>=15) — must NOT resolve automatically
# ---------------------------------------------------------------------------
_EXC_DOMAINS = [
    ("Palewood Custom Millwork", "Products manufactured by Palewood Custom Millwork specifically"),
    ("Quicksilver Print Solutions", "materials sourced by Quicksilver Print Solutions specifically"),
    ("Rustwater Plumbing Supply", "fixtures installed by Rustwater Plumbing Supply specifically"),
    ("Stonebridge Fence Contractors", "posts set by Stonebridge Fence Contractors specifically"),
    ("Tallowmark Candle Wholesale", "wax batches produced by Tallowmark Candle Wholesale specifically"),
    ("Underhill Excavation Corp", "trenches dug by Underhill Excavation Corp specifically"),
    ("Vantagepoint Drone Delivery", "packages routed by Vantagepoint Drone Delivery specifically"),
    ("Westfold Grain Elevator Co.", "grain stored by Westfold Grain Elevator Co. specifically"),
    ("Yewbranch Orchard Partners", "fruit harvested by Yewbranch Orchard Partners specifically"),
    ("Zephyrwing Paragliding School", "equipment maintained by Zephyrwing Paragliding School specifically"),
    ("Ashcombe Brewing Supply", "kegs filled by Ashcombe Brewing Supply specifically"),
    ("Briarcliff Roofing Materials", "shingles batched by Briarcliff Roofing Materials specifically"),
    ("Coldharbor Ice Cream Co.", "mix produced by Coldharbor Ice Cream Co. specifically"),
    ("Duncannon Woodfired Ovens", "units assembled by Duncannon Woodfired Ovens specifically"),
    ("Elderglen Apiary Supply", "hives sold by Elderglen Apiary Supply specifically"),
]
for i, (p1, cond) in enumerate(_EXC_DOMAINS, start=1):
    _add(f"S4B-EXC-{i:02d}", "exception_differentiated",
         f"8. Indemnification. Each party shall indemnify the other party from "
         f"third-party claims arising from its own negligence, up to a cap of 1 times "
         f"the fees paid, PROVIDED THAT if the claim arises from a defect in "
         f"{cond} (as opposed to products/materials from any other party), the cap for "
         f"that specific claim shall instead be 3 times the fees paid.",
         False, "Conditional monetary escalation tied to one specific named party.")

# ---------------------------------------------------------------------------
# COMPOUND DIFFERENCES (>=10) — must NOT resolve automatically
# ---------------------------------------------------------------------------
_COMPOUND = [
    ("Ashmere Legal Staffing Group", "Client Firm",
     "up to a cap of 1 times the fees paid, and Ashmere Legal Staffing Group's "
     "indemnification obligation is subject to a causation standard of 'direct cause,' "
     "whereas Client Firm's indemnification obligation is subject to a broader "
     "'contributing cause' standard, except that Client Firm (but not Ashmere Legal "
     "Staffing Group) shall additionally require sixty (60) days' prior written notice "
     "before any claim may be asserted against it"),
    ("Brindlewood Tax Advisory Partners", "Corporate Client",
     "up to a cap of 1 times the fees paid, except that claims involving data-breach "
     "incidents attributable to Brindlewood Tax Advisory Partners shall survive for "
     "five (5) years instead, PROVIDED THAT the cap for any such data-breach claim "
     "shall instead be 2 times the fees paid"),
    ("Cloudspire IT Managed Services", "Enterprise Client",
     "up to a cap of 1 times the fees paid, and Cloudspire IT Managed Services shall "
     "control the defense of any claim, except that Enterprise Client (but not "
     "Cloudspire IT Managed Services) shall be solely responsible for defending claims "
     "arising from third-party API integration failures"),
    ("Driftglass Solar Panel Recyclers", "Municipal Partner",
     "up to a cap of 1 times the fees paid, PROVIDED THAT if the claim arises from a "
     "defect in materials processed by Driftglass Solar Panel Recyclers specifically, "
     "the cap for that specific claim shall instead be 4 times the fees paid, and such "
     "claims shall survive for six (6) years instead of the otherwise-applicable period"),
    ("Emberlynn Data Center Cooling", "Colocation Tenant",
     "up to a cap of 1 times the fees paid, except that claims involving willful "
     "misconduct attributable to Emberlynn Data Center Cooling shall not be subject to "
     "any cap at all, whereas Colocation Tenant's indemnification obligation is subject "
     "to a 'contributing cause' standard"),
    ("Fenwick Structural Glass Corp", "General Contractor",
     "up to a cap of 1 times the fees paid, and Fenwick Structural Glass Corp's "
     "indemnification obligation is subject to a causation standard of 'sole and "
     "proximate cause,' except that General Contractor (but not Fenwick Structural "
     "Glass Corp) shall additionally require thirty (30) days' prior written notice"),
    ("Greymantle Custom Upholstery", "Furniture Retailer",
     "up to a cap of 1 times the fees paid, PROVIDED THAT if the claim arises from a "
     "defect in fabric sourced by Greymantle Custom Upholstery specifically, the cap "
     "for that specific claim shall instead be 2 times the fees paid, and Furniture "
     "Retailer's indemnification obligation is subject to a broader 'contributing "
     "cause' standard"),
    ("Hollowmere Wetland Consulting", "Development Client",
     "up to a cap of 1 times the fees paid, except that claims involving fraud "
     "attributable to Hollowmere Wetland Consulting shall survive for seven (7) years "
     "instead, and Development Client shall control the defense of any such claim"),
    ("Inkwell Custom Printing Press", "Publishing Client",
     "up to a cap of 1 times the fees paid, and Inkwell Custom Printing Press "
     "(but not Publishing Client) shall be solely responsible for defending claims "
     "arising from defective binding materials, except that such claims shall survive "
     "for five (5) years instead"),
    ("Jarrowfield Precision Optics", "Instrument Manufacturer",
     "up to a cap of 1 times the fees paid, PROVIDED THAT if the claim arises from a "
     "defect in lenses ground by Jarrowfield Precision Optics specifically, the cap "
     "shall instead be 5 times the fees paid, except that claims involving IP "
     "infringement attributable to Instrument Manufacturer shall not be subject to any "
     "cap at all"),
]
for i, (p1, p2, tail) in enumerate(_COMPOUND, start=1):
    _add(f"S4B-COMP-{i:02d}", "compound_differences",
         f"8. Indemnification. {p1} shall indemnify, defend, and hold harmless {p2}, "
         f"and {p2} shall indemnify, defend, and hold harmless {p1}, in each case from "
         f"third-party claims arising from the indemnifying party's own negligence, "
         f"{tail}.",
         False, "Two or more simultaneous differentiation dimensions in one clause.")

# ---------------------------------------------------------------------------
# ADVERSARIAL NEGATIVE CONTROLS (anti-false-escalation) — must resolve
# automatically despite superficially resembling a differentiation trigger
# ---------------------------------------------------------------------------
_add("S4B-NEG-01", "adversarial_negative",
     "8. Indemnification. Underwriting Manager shall indemnify, defend, and hold "
     "harmless Ceding Reinsurer, and Ceding Reinsurer shall indemnify, defend, and "
     "hold harmless Underwriting Manager, in each case from third-party claims "
     "arising from the indemnifying party's own negligence, up to a cap of 1 times "
     "the annual premium paid, except that Underwriting Manager has no direct "
     "relationship with Ceding Reinsurer's downstream capital-markets investors, a "
     "fact that does not affect either party's indemnification obligations under "
     "this Section.",
     True, "Uses the 'except that' trigger phrase but is a self-negating bystander aside — must NOT escalate (A6-I-37, preserved as a permanent regression case).")
_add("S4B-NEG-02", "adversarial_negative",
     "8. Indemnification. Redwood Craft Brewery Distribution shall indemnify, "
     "defend, and hold harmless Retail Partner, and Retail Partner shall indemnify, "
     "defend, and hold harmless Redwood Craft Brewery Distribution, in each case "
     "from third-party claims arising from the indemnifying party's own negligence, "
     "up to a cap of 1 times the fees paid, and Redwood Craft Brewery Distribution's "
     "indemnification obligations shall survive termination of this Agreement for a "
     "period of four (4) years, whereas Retail Partner's indemnification obligations "
     "shall survive termination for a period of four (4) years as well.",
     True, "Two named roles, but IDENTICAL survival values — genuinely symmetric restatement, not differentiation (A6-I-13 shape).")
_add("S4B-NEG-03", "adversarial_negative",
     "8. Indemnification. Ceding Reinsurer shall indemnify, defend, and hold "
     "harmless Fronting Insurer, and Fronting Insurer shall indemnify, defend, and "
     "hold harmless Ceding Reinsurer, in each case from third-party claims arising "
     "from the indemnifying party's own negligence, up to a cap of 1 times the "
     "annual premium paid, and each party's indemnification obligations shall "
     "additionally require thirty (30) days' prior written notice before any claim "
     "may be asserted against it.",
     True, "'each party's' — generic placeholder, not a named-role differentiation (A6-I-14 shape).")
_add("S4B-NEG-04", "adversarial_negative",
     "8. Indemnification. Underwriting Manager shall indemnify, defend, and hold "
     "harmless Ceding Reinsurer, and Ceding Reinsurer shall indemnify, defend, and "
     "hold harmless Underwriting Manager, in each case from third-party claims "
     "arising from the indemnifying party's own negligence, up to a cap of 2 times "
     "the annual premium paid, and both Underwriting Manager and Ceding Reinsurer "
     "shall each control the defense of any claim for which each is respectively "
     "the indemnifying party.",
     True, "Both named roles get the SAME symmetric grant explicitly ('each...respectively') — not differentiation (A6-I-15 shape).")
_add("S4B-NEG-05", "adversarial_negative",
     "8. Indemnification. Bayview Marina Boat Storage shall indemnify, defend, and "
     "hold harmless Boat Owner, and Boat Owner shall indemnify, defend, and hold "
     "harmless Bayview Marina Boat Storage, in each case from third-party claims "
     "arising from the indemnifying party's own gross negligence, up to a cap of 1 "
     "times the annual storage fees paid, and both parties' indemnification "
     "obligations are subject to the same thirty (30) day notice requirement "
     "described in Section 20.",
     True, "'both parties'' — generic, shared, cross-referenced term, not a per-party carve-out (A6-I-25 shape).")
_add("S4B-NEG-06", "adversarial_negative",
     "8. Indemnification. Optique Vision Franchise Partners shall indemnify, "
     "defend, and hold harmless individual Franchisee, and individual Franchisee "
     "shall indemnify, defend, and hold harmless Optique Vision Franchise "
     "Partners, in each case from third-party claims arising from the indemnifying "
     "party's own gross negligence, up to a cap of 2 times the annual franchise "
     "fees paid, and each party shall bear its own costs of defense.",
     True, "'each party' — symmetric cost allocation, not a named-role grant (A6-I-22 shape).")

_FAMILY_MINIMUMS = {
    "true_symmetric": 20, "trigger_differentiated": 20,
    "causation_differentiated": 20, "category_differentiated": 15,
    "exception_differentiated": 15, "compound_differences": 10,
}


def _validate():
    from collections import Counter
    counts = Counter(c["family"] for c in CASES)
    for fam, minimum in _FAMILY_MINIMUMS.items():
        assert counts[fam] >= minimum, f"{fam}: {counts[fam]} < required {minimum}"
    assert len(CASES) >= 100, f"total {len(CASES)} < required 100"
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids)), "duplicate case id"


_validate()
