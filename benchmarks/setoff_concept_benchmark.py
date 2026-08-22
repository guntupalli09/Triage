"""
Step 4A.5 — Priority 1 (SM-CRITICAL fix). Set-off/mutual-debt-netting
concept recognition benchmark, built and locked BEFORE the corresponding
production change per the task's explicit instruction.

The supported concept: one party may deduct, net, reduce, retain, credit,
or otherwise satisfy an amount it owes using an amount the OTHER party
owes it — a mutual-debt-netting right, however phrased. This is the exact
legal concept behind "set-off"/"offset", generalized to cover drafting
that expresses the same right without either literal word (the Step 4A.4
SM-CRITICAL case, A4-K-07: "shall be entitled to withhold from any amount
otherwise due to Venue Owner an amount equal to any sums Venue Owner owes
Event Producer").

Each case: (id, text, is_setoff_concept, note).
"""

CASES = [
    # ================= POSITIVES (42) =================
    ("SO-01", "Customer shall have the right to set off any amounts owed to Vendor against amounts Vendor owes Customer.", True, "canonical set-off wording"),
    ("SO-02", "Neither party shall have any right of set-off against amounts payable hereunder.", True, "canonical prohibition wording"),
    ("SO-03", "Customer may offset any amounts owed to Vendor against amounts Vendor owes Customer.", True, "offset synonym"),
    ("SO-04", "Payments shall be made without any right of deduction, counterclaim, or offset.", True, "prohibition bundle including offset"),
    ("SO-05", "Event Producer shall be entitled to withhold from any amount otherwise due to Venue Owner an amount equal to any sums Venue Owner owes Event Producer under a separate services agreement between them.", True, "the SM-CRITICAL case — withhold framed as mutual-debt netting"),
    ("SO-06", "Buyer may deduct from any payment due to Seller an amount equal to any sums Seller owes Buyer under this or any other agreement.", True, "deduct framed as mutual-debt netting"),
    ("SO-07", "Landlord shall have the right to apply any security deposit held hereunder against amounts owed by Tenant, and Tenant shall have no right to apply rent owed against amounts Landlord owes Tenant under any other agreement.", True, "apply/net framed reciprocally (Tenant's own right prohibited)"),
    ("SO-08", "Contractor may reduce any payment otherwise due to Subcontractor by the amount of any sums Subcontractor owes Contractor for defective work.", True, "reduce framed as mutual-debt netting"),
    ("SO-09", "Distributor shall be entitled to net any amount it owes Manufacturer against any amount Manufacturer owes Distributor.", True, "net (verb) framed as mutual-debt netting"),
    ("SO-10", "Franchisor may retain from royalties otherwise payable to Franchisee an amount equal to any sums Franchisee owes Franchisor for unpaid marketing fund contributions.", True, "retain framed as mutual-debt netting"),
    ("SO-11", "Carrier may recoup from freight charges otherwise due to Shipper any amount Shipper owes Carrier for demurrage.", True, "recoup framed as mutual-debt netting"),
    ("SO-12", "Vendor shall debit against amounts payable to Customer any sums Customer owes Vendor for equipment damage.", True, "debit framed as mutual-debt netting"),
    ("SO-13", "Customer's payment obligations may be satisfied by crediting against them any amount Vendor owes Customer for service credits accrued under the SLA.", True, "credit-against framed as mutual-debt netting (SLA credits used as netting basis, not the credit itself)"),
    ("SO-14", "Underwriter may deduct from ceding commissions otherwise due to Reinsured any amounts Reinsured owes Underwriter for unpaid premium.", True, "deduct framed as mutual-debt netting, reinsurance domain"),
    ("SO-15", "Grower may withhold from amounts otherwise payable to Processor an amount equal to sums Processor owes Grower for delivery shortfalls.", True, "withhold framed as mutual-debt netting, agriculture domain"),
    ("SO-16", "Neither party shall exercise any right to deduct, withhold, or otherwise reduce a payment due to the other party by reference to any amount owed by that other party, whether arising under this Agreement or otherwise.", True, "broad prohibition, no literal set-off/offset word, general mutual-debt language"),
    ("SO-17", "The parties agree that all amounts owed by either party to the other under this Agreement and any other agreement between them may be netted and only the net balance shall be payable.", True, "explicit mutual netting-to-net-balance structure"),
    ("SO-18", "Customer shall have no right to reduce, hold back, or apply against any invoice any amount that Vendor may owe Customer under a separate agreement.", True, "prohibition, reduce/hold back/apply-against phrasing"),
    ("SO-19", "Licensee may apply unpaid royalties owed by Licensor as a credit against amounts Licensee owes Licensor for services rendered.", True, "apply-as-credit framed as mutual-debt netting"),
    ("SO-20", "Buyer shall be entitled to withhold payment of the purchase price to the extent of any amount Seller owes Buyer for breach of warranty on prior deliveries.", True, "withhold framed as mutual-debt netting tied to warranty claims"),
    ("SO-21", "Any amount that Consultant owes Client may, at Client's election, be deducted from fees otherwise payable to Consultant.", True, "deduct framed as mutual-debt netting, reverse sentence order"),
    ("SO-22", "Supplier agrees that Buyer may satisfy amounts Supplier owes Buyer by reducing the next invoice payment due to Supplier by a corresponding amount.", True, "reduce-next-invoice framed as mutual-debt netting"),
    ("SO-23", "Neither party may reduce or delay payment of amounts due to the other on the basis that the other party owes it money under this or any related agreement.", True, "explicit prohibition of using counterparty's debt to justify non-payment"),
    ("SO-24", "Charter Operator shall have the right to deduct demurrage amounts owed by Charterer from hire otherwise payable to Charterer.", True, "deduct framed as mutual-debt netting, maritime domain"),
    ("SO-25", "Import Broker may offset duties advanced on Importer of Record's behalf against fees otherwise owed to Importer of Record.", True, "offset (explicit word) framed as mutual-debt netting"),
    ("SO-26", "Host Facility shall have no right to withhold or reduce amounts payable to Tenant Operator on the ground that Tenant Operator owes Host Facility money under any other arrangement.", True, "prohibition of using counterparty debt to justify withholding"),
    ("SO-27", "Payor may credit against any invoice the amount of any refund, rebate, or other sum that Payor determines Payee owes Payor arising from a prior overpayment by Payor.", True, "credit-against framed as mutual-debt netting even though triggered by an overpayment"),
    ("SO-28", "The Company may satisfy its payment obligations to the Consultant, in whole or in part, by setting off amounts the Consultant owes the Company for advances previously made.", True, "setting off (gerund form) framed as mutual-debt netting"),
    ("SO-29", "Vendor's invoices shall be reduced by any amount Vendor owes Customer for liquidated damages assessed under Section 9.", True, "reduce framed as mutual-debt netting tied to liquidated damages"),
    ("SO-30", "Reseller may apply amounts Manufacturer owes Reseller for defective units as a credit against Reseller's payment obligations to Manufacturer.", True, "apply-as-credit framed as mutual-debt netting"),
    ("SO-31", "Notwithstanding anything herein, Customer shall not be entitled to reduce any payment to Vendor by any amount Customer claims Vendor owes Customer, whether disputed or not.", True, "explicit prohibition, claims-based mutual debt"),
    ("SO-32", "Servicer may deduct servicing fees it is owed from collections otherwise remittable to Investor.", True, "deduct/owed-by-Servicer-itself framed against amounts due to Investor (mutual-debt structure, fees owed to the deducting party)"),
    ("SO-33", "Toll Manufacturer may retain a portion of amounts otherwise payable to Brand Owner equal to the cost of materials Brand Owner failed to supply as required.", True, "retain framed as mutual-debt netting (cost owed by Brand Owner used as offset)"),
    ("SO-34", "Underwriting Agent shall not withhold or reduce commission payments to Insurer on account of amounts Underwriting Agent claims are owed to it by Insurer, absent Insurer's written agreement.", True, "prohibition absent consent — mutual-debt netting concept"),
    ("SO-35", "Home Health Agency may not reduce payments due to Patient Referral Source by any amount Home Health Agency believes Patient Referral Source owes it.", True, "prohibition, mutual-debt netting concept"),
    ("SO-36", "Energy Purchaser may deduct from settlement payments otherwise due to Generator any amount Generator owes Energy Purchaser for imbalance charges.", True, "deduct framed as mutual-debt netting, energy domain"),
    ("SO-37", "Telecom Reseller shall have the right to net amounts owed to Carrier Wholesaler against amounts Carrier Wholesaler owes Telecom Reseller for service outages.", True, "net framed as mutual-debt netting, telecom domain"),
    ("SO-38", "Franchisee shall not withhold royalty payments on the basis that Franchisor owes Franchisee money under a separate marketing agreement.", True, "prohibition, mutual-debt netting concept"),
    ("SO-39", "Underwriter may reduce the ceding commission by any amount Reinsured owes Underwriter for retrospective premium adjustments.", True, "reduce framed as mutual-debt netting"),
    ("SO-40", "Payments due from either party to the other under this Agreement shall be subject to a right of set-off in favor of the paying party for any liquidated sum then due and owing from the other party.", True, "formal set-off clause, explicit word present"),
    ("SO-41", "Grower shall not be entitled to deduct from the purchase price any amount Grower alleges Processor owes Grower under a prior harvest.", True, "prohibition, mutual-debt netting concept"),
    ("SO-42", "Consignee may apply amounts Carrier owes Consignee for cargo damage as a credit against freight charges otherwise payable to Carrier.", True, "apply-as-credit framed as mutual-debt netting, logistics domain"),

    # ================= NEGATIVE CONTROLS (30) =================
    ("NEG-SO-01", "Vendor shall be responsible for any withholding taxes imposed on payments under this Agreement.", False, "tax withholding — unidirectional statutory deduction, no counterparty debt"),
    ("NEG-SO-02", "Payments shall be made without deduction for withholding taxes except as required by law.", False, "tax withholding, no mutual debt reference"),
    ("NEG-SO-03", "Customer shall receive a service credit of $5,000 for the SLA breach described in Section 6, to be applied to the next invoice.", False, "ordinary service credit — a known fixed adjustment, not a mutual-debt netting right"),
    ("NEG-SO-04", "Vendor shall issue a refund to Customer within 30 days of a valid return.", False, "ordinary refund — no counterparty-debt reference at all"),
    ("NEG-SO-05", "Any billing error shall be corrected on the next invoice following notice from the affected party.", False, "billing correction — no debt-netting concept"),
    ("NEG-SO-06", "Customer shall be entitled to a rebate of 2% of annual purchases, payable within 60 days of year-end.", False, "volume rebate — a scheduled payment, not netting against a debt"),
    ("NEG-SO-07", "Vendor may offer promotional credits to Customer at Vendor's sole discretion, which shall be applied against future purchases.", False, "promotional credit — no debt-netting concept"),
    ("NEG-SO-08", "Customer shall deduct applicable sales tax from the amount remitted to Vendor as required by the taxing jurisdiction.", False, "tax deduction — unidirectional statutory obligation, not mutual debt"),
    ("NEG-SO-09", "In the event of a dispute, the parties shall attempt in good faith to resolve the disputed amount within 30 days.", False, "ordinary dispute-resolution language, no deduction/netting mechanism at all"),
    ("NEG-SO-10", "Vendor shall be liable for damages arising from its breach of this Agreement, subject to the limitation of liability in Section 9.", False, "ordinary damages clause, not a payment-netting mechanism"),
    ("NEG-SO-11", "The financial statements shall present amounts due to and from affiliates on a net basis in accordance with GAAP.", False, "accounting net presentation — a reporting convention, not a contractual payment right"),
    ("NEG-SO-12", "Customer shall pay all invoices within Net 30 days of the invoice date.", False, "ordinary payment-timing clause"),
    ("NEG-SO-13", "Vendor shall reduce the price of the Deliverables by 10% for the second and subsequent orders placed in the same calendar year.", False, "volume-based price reduction — a pricing term, not netting against a debt"),
    ("NEG-SO-14", "Customer shall be entitled to withhold payment of the disputed portion of an invoice pending resolution of a good-faith dispute as to that portion.", False, "disputed-amount withholding — a distinct, already-supported concept (withholding one's OWN disputed obligation, not netting against the counterparty's debt)"),
    ("NEG-SO-15", "Any overpayment by Customer shall be refunded by Vendor within 15 days of Vendor's determination that an overpayment occurred.", False, "overpayment refund — a distinct, one-directional correction, no netting language"),
    ("NEG-SO-16", "Vendor shall correct any pricing error identified by Customer within 10 business days by issuing a corrected invoice.", False, "pricing-error correction — no debt-netting concept"),
    ("NEG-SO-17", "Customer's account shall be credited with any unused prepaid balance upon termination of this Agreement.", False, "prepaid-balance credit — no counterparty-debt reference"),
    ("NEG-SO-18", "Reinsured shall pay the annual premium in advance, subject to adjustment at year-end based on actual exposure.", False, "premium adjustment — a scheduled true-up, not mutual-debt netting"),
    ("NEG-SO-19", "Vendor shall reduce the invoiced amount to reflect any early-payment discount elected by Customer.", False, "early-payment discount — a pricing mechanic, not debt-netting"),
    ("NEG-SO-20", "Vendor is responsible for value-added tax, which shall be withheld and remitted by Customer to the taxing authority as required by law.", False, "withholding-tax remittance mechanic — unidirectional statutory obligation"),
    ("NEG-SO-21", "Grower's payment shall be net of the agreed handling fee described in Exhibit C.", False, "'net of' a scheduled fee — a pricing calculation, not mutual-debt netting"),
    ("NEG-SO-22", "Customer shall be given a credit memo for any goods returned as defective within the warranty period.", False, "credit memo for returns — an ordinary commercial adjustment, no counterparty-debt reference"),
    ("NEG-SO-23", "The parties acknowledge that amounts owed under the prior agreement have been paid in full and no further sums are due between them.", False, "a factual recital that prior debts are settled — not a netting mechanism"),
    ("NEG-SO-24", "Carrier shall deduct the applicable fuel surcharge from the base freight rate as published in Carrier's tariff.", False, "fuel-surcharge deduction — a pricing mechanic, not mutual-debt netting"),
    ("NEG-SO-25", "Vendor shall withhold delivery of the Deliverables until Customer has paid all amounts then due under this Agreement.", False, "withholding PERFORMANCE (not payment) pending payment — a distinct concept (a security/leverage right over delivery, not a payment-netting right)"),
    ("NEG-SO-26", "Insurer shall deduct the policy deductible from any claim payment made to the insured.", False, "insurance deductible — a policy-term reduction, not mutual-debt netting"),
    ("NEG-SO-27", "Underwriting Agent shall retain its commission from premiums collected before remitting the balance to Insurer, as compensation for underwriting services rendered.", False, "retaining one's OWN earned commission from funds collected on another's behalf — a compensation mechanic, not netting against a debt owed BY the other party"),
    ("NEG-SO-28", "Any amount improperly invoiced shall be corrected by Vendor issuing a credit note within 5 business days.", False, "credit note for invoicing error — no counterparty-debt reference"),
    ("NEG-SO-29", "Distributor shall receive a marketing development allowance equal to 3% of net purchases, credited quarterly.", False, "marketing allowance — a scheduled credit, not debt-netting"),
    ("NEG-SO-30", "Customer shall pay a late fee of 1.5% per month on any overdue amount, which late fee is not subject to reduction or waiver except by Vendor's written consent.", False, "late-fee clause — an interest/penalty mechanic, not a debt-netting right"),
]

assert len(CASES) == 72, len(CASES)
assert sum(1 for c in CASES if c[2]) == 42
assert sum(1 for c in CASES if not c[2]) == 30
