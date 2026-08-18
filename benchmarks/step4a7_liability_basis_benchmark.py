"""Step 4A.7 Phase 7 — dedicated liability multiplier-cap basis benchmark.

Built to validate the basis-word-modifier fix in liability_policy_engine.py
(_BASIS_MODIFIER_FRAGMENT) and the parallel fix in
indemnification_policy_engine.py's _MONETARY_MULTIPLIER_RE. Measures basis
recognition, basis ownership/association, multiplier recognition, and
false-positive rate SEPARATELY, per the governing instructions.

Schema: dict(id, family, text, expect_recognized: bool,
expect_multiplier: Optional[float], note).
family in {"ordinary_basis", "negative_control", "false_association"}.
"""

CASES = []


def _add(id_, family, text, expect_recognized, expect_multiplier, note):
    CASES.append(dict(id=id_, family=family, text=text,
                       expect_recognized=expect_recognized,
                       expect_multiplier=expect_multiplier, note=note))


# ---------------------------------------------------------------------------
# ORDINARY QUALIFIED BASES (must recognize) — covers every basis family
# named in the governing instructions plus realistic domain variety.
# ---------------------------------------------------------------------------
_ORDINARY = [
    ("Northwind Data Analytics Corp", "aggregate liability", "2 times the annual fees paid"),
    ("Sunrise Meal Kit Delivery", "aggregate liability", "1 times the annual subscription fees paid"),
    ("Coastal IT Support Group", "aggregate liability", "2 times the annual service fees paid"),
    ("Redwood Craft Brewery Distribution", "aggregate liability", "1 times the annual distribution fees paid"),
    ("Alpine Software Licensing Corp", "aggregate liability", "3 times the annual licensing fees paid"),
    ("Bluepeak Facilities Maintenance", "aggregate liability", "2 times the annual maintenance charges paid"),
    ("Skyline Cloud Platform Services", "aggregate liability", "1 times the annual platform charges paid"),
    ("Harborview Marina Boat Storage", "aggregate liability", "1 times the annual rent paid"),
    ("Cascade Wine and Spirits Distribution", "aggregate liability", "2 times the annual royalties paid"),
    ("Meridian Insurance Brokerage Group", "aggregate liability", "1 times the annual premiums paid"),
    ("Fernwood Landscape Design Partners", "aggregate liability", "1 times the fees paid in the preceding twelve months"),
    ("Ironclad Security Consulting Corp", "aggregate liability", "2 times the charges paid during the prior twelve months"),
    ("Timberline Coworking Space Group", "aggregate liability", "1 times the amounts paid or payable"),
    ("Northgate Behavioral Health Partners", "aggregate liability", "1 times the recurring charges paid"),
    ("Solaris Rooftop Installation Services", "aggregate liability", "1 times the annual installation fees paid"),
    ("Vantage Wine and Spirits Distribution", "aggregate liability", "2 times the annual franchise royalty fees paid"),
    ("Pinehollow Veterinary Group Practice", "aggregate liability", "3 times the annual service fees paid"),
    ("Summit Physical Therapy Network", "aggregate liability", "5 times the annual referral fees paid"),
    ("EverGreen Landscaping Services Corp", "aggregate liability", "2 times the annual maintenance fees paid"),
    ("Continental Data Center Colocation", "aggregate liability", "1 times the annual colocation fees paid"),
    ("Falconridge Wine and Spirits Group", "aggregate liability", "2 times the annual distribution fees paid"),
    ("Northeast Beverage Partners Distribution", "aggregate liability", "1 times the annual beverage fees paid"),
    ("Optique Vision Franchise Partners", "aggregate liability", "2 times the annual franchise fees paid"),
    ("Cypress Wellness Spa Franchising", "aggregate liability", "1 times the annual spa membership fees paid"),
    ("Willowbrook Pool Maintenance Services", "aggregate liability", "1 times the annual pool service fees paid"),
    ("Zenith 3D-Printing Manufacturing Corp", "aggregate liability", "2 times the annual manufacturing fees paid"),
    ("Harborlight Art Gallery Consignment", "aggregate liability", "2 times the annual consignment fees paid"),
    ("Bayview Marina Boat Storage Group", "aggregate liability", "1 times the annual storage fees paid"),
    ("Quicksilver Courier Services Corp", "aggregate liability", "1 times the annual courier fees paid"),
    ("Meadowbrook Dental Practice Management", "aggregate liability", "1 times the annual management fees paid"),
]
for i, (party, cap_phrase, basis) in enumerate(_ORDINARY, start=1):
    mult = float(basis.split()[0])
    _add(f"LB-ORD-{i:02d}", "ordinary_basis",
         f"9. Limitation of Liability. {party}'s {cap_phrase} shall not exceed {basis}.",
         True, mult, "Ordinary qualified-basis multiplier cap; must recognize both value and basis.")

# Word-number variant (a handful, tests _MULTIPLIER_WORD_RE specifically)
_WORD_NUM = [
    ("Ashford Veterinary Diagnostics Group", "two", 2.0, "annual diagnostic fees"),
    ("Brightwater Aquarium Supply Company", "three", 3.0, "annual supply fees"),
    ("Cinderpath Adventure Guide Services", "one", 1.0, "annual guide fees"),
    ("Driftmoor Sailing School Partners", "four", 4.0, "annual instruction fees"),
    ("Elmsworth Craft Distillery Group", "two", 2.0, "annual distillery fees"),
]
for i, (party, word, mult, basis) in enumerate(_WORD_NUM, start=1):
    _add(f"LB-WORD-{i:02d}", "ordinary_basis",
         f"9. Limitation of Liability. {party}'s aggregate liability shall not exceed {word} times the {basis} paid.",
         True, mult, "Word-form multiplier with a qualified basis.")

# ---------------------------------------------------------------------------
# NEGATIVE CONTROLS (must NOT associate as the general liability cap) —
# multipliers attached to a DIFFERENT, non-cap concept nearby.
# ---------------------------------------------------------------------------
_NEGATIVE = [
    ("Northshore Facilities Management Corp",
     "9. Limitation of Liability. Service credits payable under the SLA in Exhibit B shall not exceed "
     "2 times the monthly service fees for the affected period. Northshore Facilities Management Corp's "
     "aggregate liability to Client shall not exceed $500,000.",
     "SLA service-credit multiplier is a DIFFERENT concept from the general liability cap stated separately as a fixed dollar amount."),
    ("Ridgeline Telecom Installation Partners",
     "9. Limitation of Liability. Ridgeline Telecom Installation Partners maintains commercial general "
     "liability insurance with limits of not less than 3 times its annual premium obligation under the "
     "policy. Ridgeline Telecom Installation Partners' aggregate liability to Client for any claim shall "
     "not exceed $1,000,000.",
     "Insurance-premium multiplier is a distractor; the real cap is the separately-stated fixed amount."),
    ("Sagebrush Environmental Testing Corp",
     "9. Limitation of Liability. In the event of early termination, Sagebrush Environmental Testing "
     "Corp shall pay a termination fee equal to 2 times the average monthly fees. Sagebrush Environmental "
     "Testing Corp's aggregate liability to Client for any claim arising under this Agreement shall not "
     "exceed $750,000.",
     "Termination-fee multiplier is unrelated to the general liability cap."),
    ("Lakeshore Marina Fuel Services Group",
     "9. Limitation of Liability. Lakeshore Marina Fuel Services Group's indemnification obligation "
     "under Section 8 shall not exceed 2 times the annual fuel-delivery fees paid. Separately, Lakeshore "
     "Marina Fuel Services Group's aggregate liability under this Section 9 shall not exceed $300,000.",
     "The multiplier belongs to the INDEMNIFICATION cap (Section 8), not the liability cap (Section 9) — cross-clause ownership must not blur."),
]
for i, (party, text, note) in enumerate(_NEGATIVE, start=1):
    _add(f"LB-NEG-{i:02d}", "negative_control", text, True, None,
         note + " (expect_multiplier=None: the GENERAL cap for the liability adapter is the separately-stated fixed amount, not the distractor multiplier.)")

# ---------------------------------------------------------------------------
# FALSE-ASSOCIATION STRESS (must not silently adopt an unrelated basis) —
# genuinely absent multiplier basis near liability language.
# ---------------------------------------------------------------------------
_add("LB-FA-01", "false_association",
     "9. Limitation of Liability. Meridian Actuarial Consulting Group shall have no liability whatsoever "
     "to Client for any claim arising under this Agreement, except that Client shall maintain insurance "
     "coverage of not less than 2 times its annual payroll expense.",
     True, None, "The '2 times annual payroll expense' is an INSURANCE requirement on Client, not the general liability cap basis at all.")
_add("LB-FA-02", "false_association",
     "9. Limitation of Liability. Northlake Snowplow Services' aggregate liability to Municipality shall "
     "be governed by the fee schedule set forth in Exhibit D, which separately references a service credit "
     "of up to 2 times the monthly plow fee for missed routes.",
     True, None, "Cross-referenced external cap delegation; the '2x monthly plow fee' is a service-credit distractor, not the general cap.")

# ---------------------------------------------------------------------------
# Additional ordinary-basis domain variety (bring total to 60+)
# ---------------------------------------------------------------------------
_ORDINARY_2 = [
    ("Thornfield Grain Elevator Cooperative", "1 times the annual storage fees paid"),
    ("Blackwood Custom Furniture Makers", "2 times the annual commission fees paid"),
    ("Emberlight Candle Manufacturing Group", "1 times the annual wholesale fees paid"),
    ("Driftwood Surf School Enterprises", "2 times the annual lesson fees paid"),
    ("Copperfield Bookkeeping Associates Corp", "1 times the annual bookkeeping fees paid"),
    ("Amberfield Vineyard Management Group", "3 times the annual management fees paid"),
    ("Granite Peak Demolition Contracting", "1 times the annual contracting fees paid"),
    ("Bluebell Childcare Franchising Group", "2 times the annual franchise fees paid"),
    ("Coppertop Roofing Solutions Corp", "1 times the annual roofing fees paid"),
    ("Tidewater Aquaculture Partners Group", "2 times the annual harvest fees paid"),
    ("Northstar Actuarial Consulting Group", "1 times the annual consulting fees paid"),
    ("Ferncrest Landscaping Design Studio", "2 times the annual design fees paid"),
    ("Kestrel Aerial Survey Corporation", "1 times the annual survey fees paid"),
    ("Larkspur Botanical Gardens Trust", "1 times the annual admission fees paid"),
    ("Millbrook Cheese Creamery Group", "2 times the annual creamery fees paid"),
    ("Oakhaven Senior Living Group Corp", "1 times the annual resident fees paid"),
    ("Quarryview Stoneworks Manufacturing", "3 times the annual quarry fees paid"),
    ("Saltmarsh Oyster Farms Cooperative", "1 times the annual farming fees paid"),
    ("Thistledown Wool Mill Enterprises", "2 times the annual milling fees paid"),
]
for i, (party, basis) in enumerate(_ORDINARY_2, start=1):
    mult = float(basis.split()[0])
    _add(f"LB-ORD2-{i:02d}", "ordinary_basis",
         f"9. Limitation of Liability. {party}'s aggregate liability shall not exceed {basis}.",
         True, mult, "Ordinary qualified-basis multiplier cap; must recognize both value and basis.")

_FAMILY_MINIMUMS = {"ordinary_basis": 30, "negative_control": 4, "false_association": 2}


def _validate():
    from collections import Counter
    counts = Counter(c["family"] for c in CASES)
    for fam, minimum in _FAMILY_MINIMUMS.items():
        assert counts[fam] >= minimum, f"{fam}: {counts[fam]} < {minimum}"
    assert len(CASES) >= 30, f"total {len(CASES)} too small"
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))


_validate()
