"""Step 4A.7.2 — dedicated benchmark for the A6-L-52 role-attribution fix
(liability_policy_engine.py's _unmapped_cap_role_pair_reason /
CapExpression.unmapped_role_pair_reason).

Proves the fix (a) closes the genuine gap (neither named role in a
"[Role1]'s liability to [Role2]" cap sentence maps to buy/sell vocabulary,
AND the policy's contract_side is specifically buy_side/sell_side, not
mutual) without (b) corrupting ordinary role mappings — including cases
that were found, during validation, to regress before the fix was narrowed
(A6-L-59-style elaborate-but-harmless entity descriptions).

Schema: dict(id, family, text, kwargs, expect_review: bool, note).
"""

CASES = []


def _add(id_, family, text, kwargs, expect_review, note):
    CASES.append(dict(id=id_, family=family, text=text, kwargs=kwargs,
                       expect_review=expect_review, note=note))


# ---------------------------------------------------------------------------
# TRUE POSITIVES — neither role maps, contract_side is directional: MUST review
# ---------------------------------------------------------------------------
_add("RA-TP-01", "true_positive",
     "1. Definitions. 'Grantee' means the entity to whom, and 'Grantor' means the entity by whom, "
     "the mineral rights described in Exhibit A are conveyed under this instrument.\n\n"
     "9. Limitation of Liability. Grantee's aggregate liability to Grantor shall not exceed 1 times "
     "the annual royalty payments made.",
     {"contract_side": "buy_side"}, True,
     "A6-L-52 itself — neither Grantee nor Grantor maps to buy/sell vocabulary.")
_add("RA-TP-02", "true_positive",
     "1. Definitions. 'Assignor' means the party transferring rights, and 'Assignee' means the "
     "party receiving them under this deed.\n\n"
     "9. Limitation of Liability. Assignor's aggregate liability to Assignee shall not exceed 2 times "
     "the annual assignment fees paid.",
     {"contract_side": "sell_side"}, True,
     "'Assignor'/'Assignee' are not in the buy/sell generic vocabulary.")
_add("RA-TP-03", "true_positive",
     "1. Definitions. 'Settlor' means the party establishing the trust, and 'Beneficiary' means the "
     "party for whose benefit the trust is established under this instrument.\n\n"
     "9. Limitation of Liability. Settlor's aggregate liability to Beneficiary shall not exceed 1 "
     "times the annual trustee fees paid.",
     {"contract_side": "buy_side"}, True,
     "Trust vocabulary ('Settlor'/'Beneficiary') has no buy/sell mapping.")
_add("RA-TP-04", "true_positive",
     "1. Definitions. 'Pledgor' means the party granting a security interest, and 'Pledgee' means "
     "the party receiving it under this security agreement.\n\n"
     "9. Limitation of Liability. Pledgor's aggregate liability to Pledgee shall not exceed 2 times "
     "the annual custody fees paid.",
     {"contract_side": "sell_side"}, True,
     "Secured-lending vocabulary ('Pledgor'/'Pledgee') has no buy/sell mapping.")

# ---------------------------------------------------------------------------
# NEGATIVE CONTROLS — mutual contract_side: must NOT escalate even though
# neither role maps to buy/sell vocabulary (direction doesn't matter here)
# ---------------------------------------------------------------------------
_add("RA-NEG-MUTUAL-01", "negative_mutual",
     "1. Definitions. 'Processor' means Continental Payment Processing Solutions, Inc. ('CPPS'), "
     "together with any successor entity resulting from a merger, acquisition, or corporate "
     "reorganization, including without limitation the entity's recent acquisition by Meridian "
     "Financial Technologies Group, provided that CPPS continues to process transactions on behalf "
     "of Merchant as its primary function.\n\n"
     "9. Limitation of Liability. Processor's aggregate liability to Merchant shall not exceed 2 "
     "times the annual processing fees paid.",
     {}, False,
     "A6-L-54 shape — contract_side defaults to mutual; role identity doesn't matter here.")
_add("RA-NEG-MUTUAL-02", "negative_mutual",
     "1. Definitions. 'Operator' means the party operating the facility. 'Facility Operator' and "
     "'Operator' are used interchangeably throughout this Agreement and refer to the same entity, "
     "Redstone Industrial Park Management LLC, which leases warehouse space to Tenant.\n\n"
     "9. Limitation of Liability. Facility Operator's aggregate liability to Tenant shall not exceed "
     "1 times the annual lease fees paid.",
     {}, False,
     "A6-L-55 shape — mutual contract_side, elaborate-but-harmless alias definition.")
_add("RA-NEG-MUTUAL-03", "negative_mutual",
     "9. Limitation of Liability. Assignor's aggregate liability to Assignee shall not exceed 1 "
     "times the annual assignment fees paid.",
     {}, False,
     "Same unmapped-vocabulary pair as RA-TP-02, but mutual contract_side — must not escalate.")

# ---------------------------------------------------------------------------
# NEGATIVE CONTROLS — ordinary generic vocabulary, directional contract_side:
# must resolve automatically even though the definition includes elaborate,
# harmless entity-description boilerplate
# ---------------------------------------------------------------------------
_add("RA-NEG-GENERIC-01", "negative_generic_vocabulary",
     "1. Definitions. 'Supplier' means Heartland Grain Milling Cooperative, an agricultural "
     "cooperative organized under the laws of the State of Iowa and doing business as 'Heartland "
     "Mills.'\n\n"
     "9. Limitation of Liability. Supplier's aggregate liability to Buyer shall not exceed 2 times "
     "the annual milling fees paid.",
     {"contract_side": "sell_side"}, False,
     "A6-L-59 shape — 'Supplier' and 'Buyer' both have clean generic buy/sell mappings; the "
     "cooperative/d.b.a. boilerplate must not be misread as conflicting directional evidence.")
_add("RA-NEG-GENERIC-02", "negative_generic_vocabulary",
     "1. Definitions. 'Vendor' means Northgate Cloud Storage Solutions, Inc., a Delaware "
     "corporation, together with its wholly-owned subsidiaries and any successor by merger or "
     "acquisition.\n\n"
     "9. Limitation of Liability. Vendor's aggregate liability to Client shall not exceed 1 times "
     "the annual subscription fees paid.",
     {"contract_side": "buy_side"}, False,
     "Ordinary Vendor/Client pair with elaborate-but-harmless corporate-family boilerplate.")
_add("RA-NEG-GENERIC-03", "negative_generic_vocabulary",
     "9. Limitation of Liability. Licensor's aggregate liability to Licensee shall not exceed 2 "
     "times the annual licensing fees paid.",
     {"contract_side": "sell_side"}, False,
     "Ordinary Licensor/Licensee pair, no definitions section at all.")
_add("RA-NEG-GENERIC-04", "negative_generic_vocabulary",
     "9. Limitation of Liability. Contractor's aggregate liability to Owner shall not exceed 1 "
     "times the annual contract fees paid.",
     {"contract_side": "sell_side"}, False,
     "Ordinary Contractor/Owner pair.")
_add("RA-NEG-GENERIC-05", "negative_generic_vocabulary",
     "9. Limitation of Liability. Provider's aggregate liability to Customer shall not exceed 2 "
     "times the annual service fees paid.",
     {"contract_side": "buy_side"}, False,
     "Ordinary Provider/Customer pair, both in the generic buy/sell vocabulary.")
# Franchisor/Franchisee is NOT currently in the shared buy/sell vocabulary
# (policy_engine_core.BUY_SIDE_ROLES/SELL_SIDE_ROLES) despite being a
# common, ordinary business relationship — discovered while building this
# benchmark. Recorded as a true positive under the CURRENT vocabulary
# (disclosed as a vocabulary-coverage gap, not fixed here, since widening
# the shared cross-adapter vocabulary is a larger-blast-radius change than
# this benchmark's scope) rather than silently treated as the negative
# control it was first assumed to be.
_add("RA-TP-05", "true_positive",
     "9. Limitation of Liability. Franchisor's aggregate liability to Franchisee shall not exceed 2 "
     "times the annual franchise fees paid.",
     {"contract_side": "buy_side"}, True,
     "'Franchisor'/'Franchisee' are NOT in the current shared buy/sell vocabulary — a disclosed "
     "vocabulary-coverage gap (common relationship, not covered), not this fix's own defect.")

# ---------------------------------------------------------------------------
# NEGATIVE CONTROLS — no role-pair sentence shape at all
# ---------------------------------------------------------------------------
_add("RA-NEG-NOPAIR-01", "negative_no_pair_shape",
     "9. Limitation of Liability. Aggregate liability shall not exceed 1 times the annual fees paid.",
     {"contract_side": "buy_side"}, False,
     "No named role pair in the cap sentence at all — the role-pair regex must not match.")
_add("RA-NEG-NOPAIR-02", "negative_no_pair_shape",
     "9. Limitation of Liability. Grantee's aggregate liability shall not exceed 1 times the annual "
     "fees paid.",
     {"contract_side": "buy_side"}, False,
     "Only one named role, no 'liability to [Role2]' structure — must not match.")

_FAMILY_MINIMUMS = {"true_positive": 3, "negative_mutual": 3, "negative_generic_vocabulary": 4, "negative_no_pair_shape": 2}


def _validate():
    from collections import Counter
    counts = Counter(c["family"] for c in CASES)
    for fam, minimum in _FAMILY_MINIMUMS.items():
        assert counts[fam] >= minimum, f"{fam}: {counts[fam]} < {minimum}"
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))


_validate()
