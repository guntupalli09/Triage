"""
Step 4A.3 — Payment Terms recognition benchmark. Built and labeled BEFORE
any change to payment_terms_policy_engine.py's recognition logic (git
history / PRE run in the Step 4A.3 report is the evidence of this
ordering). Measures whether the adapter ENGAGES at all (clause_found)
on a labeled positive (a genuine, supported payment-policy concept) or
correctly does NOT engage on a labeled negative control.

Each case: (id, text, is_supported_positive, concept).
"""

CASES = [
    # --- payment timing (5) ---
    ("PT-01", "Customer shall pay all invoices within Net 30 days of the invoice date.", True, "payment_timing"),
    ("PT-02", "Payment shall be due within 45 days of receipt of the invoice.", True, "payment_timing"),
    ("PT-03", "Customer shall remit payment within 60 days after acceptance of the deliverables.", True, "payment_timing"),
    ("PT-04", "Invoices are payable within thirty (30) days from the invoice date.", True, "payment_timing"),
    ("PT-05", "Payment terms are Net 15 from the date of invoice.", True, "payment_timing"),

    # --- invoice / payment obligation (5) ---
    ("PT-06", "Vendor shall invoice Customer monthly in arrears for Services rendered.", True, "invoice_obligation"),
    ("PT-07", "Invoices shall be submitted electronically to the address specified in Exhibit A.", True, "invoice_obligation"),
    ("PT-08", "An incomplete or incorrect invoice shall toll the payment period until corrected.", True, "invoice_obligation"),
    ("PT-09", "Customer shall pay Vendor the fees set forth in the applicable Order Form.", True, "invoice_obligation"),
    ("PT-10", "All amounts invoiced hereunder are due and payable in full.", True, "invoice_obligation"),

    # --- taxes (5) ---
    ("PT-11", "Vendor shall be responsible for all sales and use taxes arising from this Agreement.", True, "taxes"),
    ("PT-12", "Customer shall be responsible for all applicable taxes imposed on the transactions contemplated hereby.", True, "taxes"),
    ("PT-13", "Each party shall be responsible for taxes based on its own net income.", True, "taxes"),
    ("PT-14", "All fees are exclusive of sales, use, and value-added taxes, which Customer shall bear.", True, "taxes"),
    ("PT-15", "Vendor shall be responsible for any and all federal, state, and local taxes.", True, "taxes"),

    # --- withholding (3) ---
    ("PT-16", "Vendor shall be responsible for any withholding taxes imposed on payments under this Agreement.", True, "withholding"),
    ("PT-17", "Customer may withhold and remit withholding tax as required by applicable law.", True, "withholding"),
    ("PT-18", "Payments shall be made without deduction for withholding taxes except as required by law.", True, "withholding"),

    # --- currency (4) ---
    ("PT-19", "All amounts payable under this Agreement shall be paid in United States Dollars.", True, "currency"),
    ("PT-20", "Customer shall pay Vendor in United States Dollars within Net 45 days of delivery.", True, "currency"),
    ("PT-21", "Payment shall be made in Euros to the bank account designated by Vendor.", True, "currency"),
    ("PT-22", "Invoices shall be denominated and payable in USD.", True, "currency"),

    # --- disputed amounts (5) ---
    ("PT-23", "Customer shall have the right to dispute any invoiced amount in good faith.", True, "disputed_amounts"),
    ("PT-24", "Any dispute must be raised within 15 days of the invoice date.", True, "disputed_amounts"),
    ("PT-25", "Customer may withhold payment of the disputed portion pending resolution.", True, "disputed_amounts"),
    ("PT-26", "Customer shall not withhold payment of any amount solely because another amount is disputed.", True, "disputed_amounts"),
    ("PT-27", "Disputes regarding invoiced amounts shall be resolved in accordance with Section 12.", True, "disputed_amounts"),

    # --- undisputed-payment obligation (3) ---
    ("PT-28", "Undisputed amounts shall remain payable during the pendency of any dispute.", True, "undisputed_payable"),
    ("PT-29", "Customer shall continue to pay all undisputed amounts notwithstanding a good-faith dispute as to other amounts.", True, "undisputed_payable"),
    ("PT-30", "Notwithstanding any dispute, Customer shall timely pay all undisputed portions of each invoice.", True, "undisputed_payable"),

    # --- set-off/offset (5) ---
    ("PT-31", "Customer shall have the right to set off any amounts owed against amounts due to Vendor.", True, "set_off"),
    ("PT-32", "Neither party shall have any right of set-off against amounts payable hereunder.", True, "set_off"),
    ("PT-33", "Customer shall have the right to offset any amounts owed to Vendor against amounts Vendor owes Customer.", True, "set_off"),
    ("PT-34", "Payments shall be made without any right of deduction, counterclaim, or offset.", True, "set_off"),
    ("PT-35", "Vendor may not unilaterally deduct amounts from payments due without Customer's prior written consent.", True, "set_off"),

    # --- late fees / interest (4) ---
    ("PT-36", "Overdue amounts shall accrue interest at 1.5% per month until paid in full.", True, "late_fee"),
    ("PT-37", "A late fee of 2% per month shall apply to any overdue invoice.", True, "late_fee"),
    ("PT-38", "Interest on overdue amounts shall not exceed the maximum rate permitted by applicable law.", True, "late_fee"),
    ("PT-39", "A grace period of 10 days shall apply before any late fee accrues.", True, "late_fee"),

    # --- reimbursement (3) ---
    ("PT-40", "Customer shall reimburse Vendor for all reasonable travel expenses pre-approved in writing.", True, "reimbursement"),
    ("PT-41", "Vendor's expenses shall be reimbursed upon submission of receipts and documentation.", True, "reimbursement"),
    ("PT-42", "Customer shall reimburse Vendor for out-of-pocket expenses incurred in performing the Services.", True, "reimbursement"),

    # --- price increase (3, existing supported concept) ---
    ("PT-43", "Vendor may increase the fees upon 60 days prior written notice, not to exceed 5% annually.", True, "price_increase"),
    ("PT-44", "Vendor shall not unilaterally increase prices except as permitted under this Section.", True, "price_increase"),
    ("PT-45", "Fees are fixed for the initial term and shall not be increased.", True, "price_increase"),

    # ======================= NEGATIVE CONTROLS (20) =======================
    # Money/tax/payment-adjacent words that must NOT engage payment-terms policy.
    ("NEG-01", "Provider shall maintain professional liability insurance with a limit of $5,000,000.", False, "distractor_insurance"),
    ("NEG-02", "In no event shall Provider's aggregate liability exceed 2 times the annual fees paid.", False, "distractor_liability_cap"),
    ("NEG-03", "The purchase price for the Deliverables is $500,000, payable at closing under the Asset Purchase Agreement.", False, "distractor_ma_purchase_price"),
    ("NEG-04", "Vendor shall indemnify Customer for damages up to $1,000,000 arising from third-party claims.", False, "distractor_indemnification"),
    ("NEG-05", "Customer shall maintain the confidentiality of Vendor's pricing information for five years.", False, "distractor_confidentiality"),
    ("NEG-06", "This Agreement is governed by the tax laws and regulations of the State of Delaware for choice-of-law purposes only.", False, "distractor_governing_law"),
    ("NEG-07", "The parties acknowledge that Vendor's total company revenue exceeded $10,000,000 in the prior fiscal year.", False, "distractor_representation"),
    ("NEG-08", "Customer represents that it has the corporate authority and financial resources to perform its obligations.", False, "distractor_representation"),
    ("NEG-09", "Vendor's insurance policy shall have a deductible of no more than $25,000 per claim.", False, "distractor_insurance"),
    ("NEG-10", "The security deposit held in escrow shall not exceed $50,000.", False, "distractor_security_deposit"),
    ("NEG-11", "This is a business valued at approximately $2,000,000 based on the parties' good-faith estimate.", False, "distractor_valuation"),
    ("NEG-12", "Damages for breach of the confidentiality provisions are difficult to quantify and may exceed $100,000.", False, "distractor_damages"),
    ("NEG-13", "Vendor shall maintain cyber liability insurance with coverage limits of $2,000,000.", False, "distractor_insurance"),
    ("NEG-14", "The indemnification basket shall be $25,000, below which no claim may be asserted.", False, "distractor_indemnification"),
    ("NEG-15", "A termination fee of $75,000 shall be payable if Customer terminates for convenience.", False, "distractor_termination_fee"),
    ("NEG-16", "The parties dispute the proper interpretation of Section 4 but agree to negotiate in good faith.", False, "distractor_generic_dispute"),
    ("NEG-17", "Vendor warrants that the Software is free of material defects for a period of 90 days.", False, "distractor_warranty"),
    ("NEG-18", "This Agreement may be assigned only with the prior written consent of the other party.", False, "distractor_assignment"),
    ("NEG-19", "The parties shall equally share the arbitration costs and each bear their own attorneys' fees.", False, "distractor_dispute_resolution"),
    ("NEG-20", "Vendor's registered office is located at 123 Main Street, and its tax identification number is on file with Customer.", False, "distractor_boilerplate_tax_id"),
]

assert len(CASES) == 65, len(CASES)
assert sum(1 for c in CASES if c[2]) == 45
assert sum(1 for c in CASES if not c[2]) == 20
