"""Step 4A.5 dedicated benchmark: bystander corporate-entity discrimination.

Locked BEFORE being used to further modify policy_engine_core's
bystander-boilerplate / relational-content mechanisms (already partly
implemented earlier in Step 4A.5's Priority 4 pass). Measures
resolve_role_side's ability to distinguish role-SEMANTIC evidence (text
that actually defines/recharacterizes a policy-relevant party's
transactional direction) from a BYSTANDER entity mention (notice
address, affiliate, subcontractor, payment processor, insurer,
licensor, "customer's customer", service provider, acquisition
language, signature-page/corporate-form boilerplate) that must NOT
redefine the operative role.

Each case is (case_id, role, document_text, expected_side_or_None,
is_positive, note). is_positive=True means the document text contains
GENUINE role-defining evidence and resolve_role_side must return a
non-None side matching expected_side_or_None (or, for a genuine
CONFLICT case, expected_side_or_None is None and a conflict reason is
required). is_positive=False means the text is bystander-only noise and
resolve_role_side must return the GENERIC mapping (no escalation).
"""

# side_for_role's generic mapping: Vendor/Supplier/Provider/Licensor/
# Contractor/Landlord/Franchisor/Reseller-type names => sell_side;
# Customer/Client/Buyer/Licensee/Tenant/Franchisee-type names => buy_side.

CASES = [
    # --- Positive: genuine role-semantic evidence (must resolve, non-bystander) ---
    ("BD-01", "Vendor", "'Vendor' means the entity that sells the Deliverables to Customer.", "sell_side", True, "direct sell-side verb"),
    ("BD-02", "Customer", "'Customer' means the entity that purchases the Deliverables from Vendor.", "buy_side", True, "direct buy-side verb"),
    ("BD-03", "Landlord", "'Landlord' means the entity that leases the Premises to Tenant.", "sell_side", True, "lease-to sell-side verb"),
    ("BD-04", "Reseller", "'Reseller' means the entity that purchases goods from Manufacturer and resells them to Distributor.", None, True, "mixed buy+sell about the role's OWN core business (genuine conflict, not bystander)"),
    ("BD-05", "Franchisor", "'Franchisor' means the entity that grants a license to operate under its brand to Franchisee.", "sell_side", True, "license-grant sell-side verb"),
    ("BD-06", "Underwriter", "'Underwriter' means the entity that provides reinsurance capacity to Reinsured.", "sell_side", True, "provides-to sell-side verb"),
    ("BD-07", "Reinsured", "'Reinsured' means the entity that procures reinsurance capacity from Underwriter.", "buy_side", True, "procures-from buy-side verb"),
    ("BD-08", "Carrier", "'Carrier' means the entity that furnishes transportation services to Shipper.", "sell_side", True, "furnishes-to sell-side verb"),
    ("BD-09", "Consignee", "'Consignee' means the entity that receives services from Carrier under this Agreement.", "buy_side", True, "receives-services-from buy-side verb"),
    ("BD-10", "Grower", "'Grower' means the entity that sells the harvested crop to Processor.", "sell_side", True, "sells-to sell-side verb"),
    ("BD-11", "Processor", "'Processor' means the entity that purchases raw agricultural inputs from Grower.", "buy_side", True, "purchases-from buy-side verb"),
    ("BD-12", "Agent", "'Agent' means the entity retained to procure services on behalf of Principal from third-party providers.", "buy_side", True, "procures-on-behalf-of buy-side verb"),
    ("BD-13", "Distributor", "'Distributor' means the entity that acquires Products from Manufacturer for resale.", "buy_side", True, "acquires-from buy-side verb"),
    ("BD-14", "Licensor", "'Licensor' means the entity that grants the license described in Exhibit A to Licensee.", "sell_side", True, "grants-license sell-side verb"),
    ("BD-15", "Operator", "'Operator' means the entity that supplies staffing services to Client.", "sell_side", True, "supplies-to sell-side verb"),
    ("BD-16", "Buyer", "'Buyer' means the entity that engages Seller's manufacturing services for a fee.", "buy_side", True, "engages...services buy-side verb"),
    ("BD-17", "Broker", "'Broker' means the entity that procures specialty insurance products on behalf of Client.", "buy_side", True, "procures-on-behalf-of buy-side pattern"),
    ("BD-18", "Insurer", "'Insurer' means the entity that develops and delivers the coverage described in the Policy to Policyholder.", "sell_side", True, "develops/delivers sell-side verb"),
    ("BD-19", "Subscriber", "'Subscriber' means the entity that subscribes to the Service offered by Platform Operator.", "buy_side", True, "subscribes-to buy-side verb"),
    ("BD-20", "Manufacturer", "'Manufacturer' means the entity that manufactures and delivers Products to Purchaser.", "sell_side", True, "manufactures/delivers sell-side verb"),
    ("BD-21", "Purchaser", "'Purchaser' means the entity that orders the goods described in Schedule A from Manufacturer.", "buy_side", True, "orders-from buy-side verb"),
    ("BD-22", "Servicer", "'Servicer' means the entity that performs loan-servicing functions for Investor.", "sell_side", True, "performs-for sell-side verb"),

    # --- Negative: bystander entity mentions, must NOT redefine the role ---
    ("NEG-BD-01", "Vendor", "'Vendor' means Acme Corporation, a Delaware corporation.", "sell_side", False, "corporate-identity boilerplate only"),
    ("NEG-BD-02", "Supplier", "'Supplier' means Ridgeline Materials Group, a general partnership formed under the laws of the State of Colorado, together with its successors and permitted assigns.", "sell_side", False, "successors-and-assigns + jurisdiction boilerplate"),
    ("NEG-BD-03", "Client", "'Client' means the party identified as 'Client' on the signature page hereto, which for the avoidance of doubt is Harborview Capital Management, L.P.", "buy_side", False, "signature-page cross-reference"),
    ("NEG-BD-04", "Provider", "'Provider' means Summit Peak Consulting Group, Inc., together with its wholly owned subsidiaries and any Affiliate performing services hereunder.", "sell_side", False, "subsidiary/affiliate boilerplate"),
    ("NEG-BD-05", "Licensor", "'Licensor' means Beacon Software Holdings, Inc., a corporation incorporated in the State of Delaware and qualified to do business in California.", "sell_side", False, "incorporation + qualified-to-do-business boilerplate"),
    ("NEG-BD-06", "Buyer", "'Buyer' means Prairie Grain Cooperative, an agricultural cooperative organized under the laws of the State of Kansas, and includes its member-owners acting in their capacity as such.", "buy_side", False, "cooperative/member-owner boilerplate"),
    ("NEG-BD-07", "Vendor", "'Vendor' means the entity identified in the Order Form, notices to which shall be sent to Vendor's Legal Department at the address in Exhibit B.", "sell_side", False, "notice-address bystander clause"),
    ("NEG-BD-08", "Carrier", "'Carrier' means the entity providing transportation services, insured under a policy issued by Continental Freight Insurers for cargo-loss coverage.", "sell_side", False, "insurer bystander mention"),
    ("NEG-BD-09", "Landlord", "'Landlord' means the property owner, whose property manager, Meridian Property Services, handles day-to-day operations.", None, False, "subcontracted property-manager bystander mention"),
    ("NEG-BD-10", "Customer", "'Customer' means the entity purchasing the Service, payments for which are processed by Northgate Payment Solutions on Customer's behalf.", "buy_side", False, "payment-processor bystander mention"),
    ("NEG-BD-11", "Consignee", "'Consignee' means the entity to which Carrier delivers the goods, Carrier's own customer being a separate unrelated shipping line.", None, False, "Carrier's own unrelated third-party customer bystander mention"),
    ("NEG-BD-12", "Distributor", "'Distributor' means the entity purchasing Products from Manufacturer for resale to end-user customers.", "buy_side", False, "resale to GENERIC unnamed end-user customers is a bystander downstream fact"),
    ("NEG-BD-13", "Reseller", "'Reseller' means the entity that purchases wholesale minutes from Carrier Wholesaler and resells the same to end-user subscribers, Carrier Wholesaler having no direct relationship with such subscribers.", "buy_side", False, "downstream generic-subscriber resale is bystander; only the named-counterparty purchase governs"),
    ("NEG-BD-14", "Subscriber", "'Subscriber' means any entity that, having provided the data described in Schedule C to Platform Operator for account-verification purposes, subscribes to the premium tier of the Service offered by Platform Operator.", "buy_side", False, "administrative data-provision for verification is a bystander clause, not a sale"),
    ("NEG-BD-15", "Home Health Agency", "'Home Health Agency' means the licensed provider that renders skilled nursing services to Patient Referral Source's referred patients, and submits invoices to Patient Referral Source for services rendered.", "sell_side", False, "invoicing-administration clause is incidental to the already-established sell-side relationship"),
    ("NEG-BD-16", "Underwriter", "'Underwriter' means the entity described in the Slip, licensed by the State Insurance Commissioner and subject to solvency regulation by that Commissioner.", None, False, "regulatory-oversight bystander mention"),
    ("NEG-BD-17", "Franchisor", "'Franchisor' means the entity that licenses the System, which has entered into a separate unrelated joint venture with Continental Capital Partners for expansion financing.", "sell_side", False, "unrelated joint-venture financing bystander mention"),
    ("NEG-BD-18", "Servicer", "'Servicer' means the entity performing loan-servicing functions, which was acquired last year by Meridian Financial Holdings in an unrelated transaction.", None, False, "acquisition-history bystander mention"),
    ("NEG-BD-19", "Grower", "'Grower' means the entity that sells the harvested crop to Processor, Processor being the party that purchases raw agricultural inputs from a third-party cooperative unrelated to this Agreement.", None, False, "Processor's own unrelated third-party purchase is a bystander clause about Processor, not Grower"),
    ("NEG-BD-20", "Broker", "'Broker' means the entity that procures insurance placements for Client, whose errors-and-omissions coverage is maintained through Pinnacle Professional Liability Underwriters.", "buy_side", False, "broker's own E&O insurer bystander mention"),
    ("NEG-BD-21", "Operator", "'Operator' means the entity supplying staffing services, together with any successor Staffing Solutions Group that may assume this Agreement.", "sell_side", False, "successor-entity boilerplate"),
    ("NEG-BD-22", "Manufacturer", "'Manufacturer' means the entity manufacturing Products, whose raw-material supplier is Continental Chemical Supply Co, an unrelated third party.", "sell_side", False, "Manufacturer's own unrelated upstream supplier bystander mention"),
    ("NEG-BD-23", "Insurer", "'Insurer' means the entity providing coverage under the Policy, reinsured in part through a treaty with Atlantic Re Group.", "sell_side", False, "insurer's own reinsurance-treaty bystander mention"),
    ("NEG-BD-24", "Purchaser", "'Purchaser' means the entity ordering goods from Manufacturer, whose outside counsel is Whitfield & Associates LLP.", "buy_side", False, "outside-counsel bystander mention"),
    ("NEG-BD-25", "Client", "'Client' means the entity engaging Consultant's services, care of Client's parent company Global Ventures Holdings for notice purposes.", "buy_side", False, "care-of parent-company notice bystander mention"),
]
