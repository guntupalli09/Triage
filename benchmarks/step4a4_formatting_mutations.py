"""
Step 4A.4 — formatting-mutation suite. 20 mutations of NEW Step 4A.4
semantic cases (not from Step 4A.2/4A.3). Expected policy semantics are
IDENTICAL to the base case; only surface formatting changes. Reported
separately from the 172-case semantic corpus and does not count toward it.

Each entry: (id, base_id, text, label, expected) — label/expected copied
from the base case (must match).
"""

MUT_CASES = [
    ("A4-A-01-FMT-caps", "A4-A-01",
     "1. DEFINITIONS. 'CONSIGNEE' MEANS MERIDIAN FREIGHT SOLUTIONS, INC., A DELAWARE CORPORATION WITH ITS PRINCIPAL PLACE OF BUSINESS IN COLUMBUS, OHIO, WHICH, NOTWITHSTANDING ANY OTHER PROVISION HEREOF, IS THE PARTY THAT PURCHASES LOGISTICS CAPACITY FROM CARRIER FOR THE TRANSPORT OF GOODS DESCRIBED IN EACH BILL OF LADING.\n\n9. LIMITATION OF LIABILITY. CONSIGNEE'S AGGREGATE LIABILITY SHALL NOT EXCEED 2 TIMES THE ANNUAL FEES PAID.",
     "AUTOMATABLE", "side=buy_side, value=2x annual fees"),
    ("A4-A-02-FMT-no-heading", "A4-A-02",
     "'Broadcaster' shall mean the entity that, having entered into this Agreement following extensive negotiation among the parties and their respective counsel, licenses the Programming to Affiliate for exhibition within the Territory.\n\nBroadcaster's aggregate liability shall not exceed 1 times the annual fees paid.",
     "AUTOMATABLE", "side=sell_side, value=1x annual fees"),
    ("A4-C-01-FMT-linebreaks", "A4-C-01",
     "9. Limitation\nof\nLiability.\nCarrier\nshall\nmaintain\ncargo\ninsurance\nwith\nlimits\nof\n$5,000,000;\nseparate\nfrom\nand\nindependent\nof\nsuch\ninsurance,\nCarrier's\naggregate\nliability\nunder\nthis\nAgreement\nshall\nnot\nexceed\n$1,000,000.",
     "AUTOMATABLE", "$1,000,000"),
    ("A4-C-02-FMT-compressed", "A4-C-02",
     "9. Limitation of Liability. Provider's aggregate liability shall not exceed 2 times the annual fees paid, exclusive of any service credits payable under the SLA, which shall not exceed $40,000 in any calendar quarter.".replace(". ", "."),
     "AUTOMATABLE", "2 times the annual fees paid"),
    ("A4-D-06-FMT-semicolons", "A4-D-06",
     "9. Limitation of Liability. Provider's liability per claim shall not exceed $500,000; and Provider's aggregate liability across all claims in any twelve (12) month period shall not exceed $2,000,000.",
     "AUTOMATABLE", "per-claim $500,000 / aggregate $2,000,000"),
    ("A4-C-18-FMT-numbered-list", "A4-C-18",
     "9. Limitation of Liability. Manufacturer's liability shall be as set forth in Schedule I.\n\nSchedule I: Risk Terms.\n1. Purchase order minimum: $50,000.\n2. Insurance requirement: $3,000,000.\n3. Liability cap: 2 times the annual fees paid.\n4. Freight allowance: $5,000.",
     "AUTOMATABLE", "2 times the annual fees paid"),
    ("A4-C-19-FMT-bullets", "A4-C-19",
     "9. Limitation of Liability. Operator's liability shall be governed by Exhibit K.\n\nExhibit K: Financial Terms.\n- Security deposit: $40,000.\n- Liability Cap Amount: $875,000.\n- Late payment penalty: 1.5% per month.",
     "AUTOMATABLE", "$875,000"),
    ("A4-A-01-FMT-unquoted", "A4-A-01",
     "1. Definitions. Consignee means Meridian Freight Solutions, Inc., a Delaware corporation with its principal place of business in Columbus, Ohio, which, notwithstanding any other provision hereof, is the party that purchases logistics capacity from Carrier for the transport of goods described in each Bill of Lading.\n\n9. Limitation of Liability. Consignee's aggregate liability shall not exceed 2 times the annual fees paid.",
     "AUTOMATABLE", "side=buy_side, value=2x annual fees"),
    ("A4-D-11-FMT-table-normalized", "A4-D-11",
     "9. Limitation of Liability.\n\nLiability Terms | Value\n-----------------|------\nGeneral aggregate cap | 1 times the annual fees paid\nInsurance minimum | $2,000,000\nSecurity deposit | $25,000",
     "AUTOMATABLE", "1 times the annual fees paid"),
    ("A4-B-01-FMT-whitespace", "A4-B-01",
     "1.   Definitions.    'Vendor'     means    Acme   Corporation,     a    Delaware   corporation.\n\n\n\n9.   Limitation   of   Liability.    Vendor's    aggregate    liability    shall    not    exceed    2   times   the   annual   fees   paid.",
     "AUTOMATABLE", "side=sell_side (generic), value=2x annual fees"),
    ("A4-F-05-FMT-caps", "A4-F-05",
     "6. PAYMENT TERMS. LANDLORD SHALL HAVE THE RIGHT TO APPLY ANY SECURITY DEPOSIT HELD HEREUNDER AGAINST AMOUNTS OWED BY TENANT, AND TENANT SHALL HAVE NO RIGHT TO APPLY RENT OWED AGAINST AMOUNTS LANDLORD OWES TENANT UNDER ANY OTHER AGREEMENT.",
     "AUTOMATABLE", "engage: set-off (prohibited for Tenant)"),
    ("A4-E-01-FMT-linebreaks", "A4-E-01",
     "8. Indemnification.\nEach party shall indemnify, defend, and hold harmless\nthe other party from and against any and all third-party\nclaims, damages, losses, and expenses (including reasonable\nattorneys' fees) arising out of or relating to the indemnifying\nparty's breach of its representations, warranties, or covenants\nunder this Agreement, subject to a cap equal to 2 times the fees\npaid by Customer to Vendor hereunder.",
     "AUTOMATABLE", "symmetric 2x fees, no asymmetry"),
    ("A4-J-01-FMT-semicolons", "A4-J-01",
     "8. Indemnification. Each party shall indemnify the other party from third-party claims arising from its own negligence; up to a cap of 1 times the fees paid; except that Underwriter's cap for claims arising from reinsurance recoverable disputes shall be 5 times the fees paid.",
     "SHOULD_REVIEW", None),
    ("A4-G-01-FMT-no-heading", "A4-G-01",
     "'Consignee' means the entity that both purchases logistics capacity from Carrier and, in certain circumstances described in Schedule A, resells such capacity to third-party shippers.\n\nConsignee's aggregate liability shall not exceed 2 times the annual fees paid.",
     "SHOULD_REVIEW", None),
    ("A4-H-01-FMT-compressed", "A4-H-01",
     "9. Limitation of Liability. Carrier's aggregate liability shall not exceed $1,000,000.Carrier's aggregate liability shall not exceed $2,500,000.",
     "SHOULD_REVIEW", None),
    ("A4-F-06-FMT-caps", "A4-F-06",
     "6. PAYMENT TERMS. ALL AMOUNTS PAYABLE UNDER THIS AGREEMENT SHALL BE DENOMINATED AND PAID IN JAPANESE YEN (JPY).",
     "AUTOMATABLE", "engage: currency (JPY)"),
    ("A4-K-15-FMT-whitespace", "A4-K-15",
     "Liability   Terms\n\n\nParty   responsible:    Distributor\n\nType:    aggregate   cap\n\nAmount:    2   times   the   annual   fees   paid\n\nApplies   to:    all   claims   arising   under   this   Agreement",
     "AUTOMATABLE", "2 times the annual fees paid"),
    ("A4-COMP-01-FMT-linebreaks", "A4-COMP-01",
     "9. Limitation\nof Liability. Underwriter shall\nmaintain errors-and-omissions insurance of $5,000,000;\nseparate from and independent of such insurance,\nUnderwriter's aggregate liability to Reinsured shall not\nexceed 2 times the annual premium paid.\n\n10. Insurance. Underwriter's insurance\nunder Section 9 shall be primary and non-contributory.",
     "AUTOMATABLE", "2 times the annual premium paid"),
    ("A4-D-04-FMT-numbered", "A4-D-04",
     "9. Limitation of Liability. Vendor's aggregate liability shall not exceed the greater of: (1) $500,000; or (2) 2 times the annual fees paid.",
     "AUTOMATABLE", "greater of $500,000 / 2x annual fees"),
    ("A4-I-11-FMT-caps-quoted", "A4-I-11",
     "1. DEFINITIONS. 'TELECOM RESELLER' HAS THE MEANING GIVEN TO 'WHOLESALE PURCHASER' IN SCHEDULE B. 'WHOLESALE PURCHASER' MEANS THE ENTITY THAT PURCHASES WHOLESALE MINUTES AND BANDWIDTH FROM CARRIER WHOLESALER.\n\n7. TAXES. TELECOM RESELLER SHALL BE RESPONSIBLE FOR ALL APPLICABLE TELECOMMUNICATIONS TAXES.",
     "AUTOMATABLE", "tax on us (Telecom Reseller=buy_side) — policy VIOLATED"),
]

assert len(MUT_CASES) == 20, len(MUT_CASES)
