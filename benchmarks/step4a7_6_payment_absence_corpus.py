"""Step 4A.7.6 — payment_terms absence corpus, built to fill the gap the
Step 4A.6 corpus left (liability and indemnification each got a dedicated
absence family; payment_terms never did). Feeds the Step 4A.7.6 absence
audit alongside the existing liability/indemnification absence families.

Schema matches step4a6_corpus_*_absence.py: dict(id, adapter, tier, family,
text, kwargs, label, concept, expected_result, reason).
"""

CASES = []


def _add(id_, tier, text, kwargs, label, concept, expected_result, reason):
    CASES.append(dict(id=id_, adapter="payment_terms", tier=tier, family="absence",
                       text=text, kwargs=kwargs, label=label, concept=concept,
                       expected_result=expected_result, reason=reason))


# Genuinely absent — no payment terms clause anywhere in the document.
_add("A7-PA-01", 1,
     "1. Services. Brightwater Aquatic Landscaping shall design and install pond features as "
     "described in Exhibit A.\n\n2. Term. This Agreement continues for one year.\n\n"
     "3. Termination. Either party may terminate on 30 days' written notice.",
     {}, "AUTOMATABLE", "genuinely ABSENT payment terms clause", "NOT_APPLICABLE",
     "No payment/invoicing language anywhere in the document — correct outcome is confident "
     "absence, not fabrication.")
_add("A7-PA-02", 1,
     "1. Services. Kestrel Drone Survey Co. shall provide aerial survey services as described in "
     "Exhibit A.\n\n2. Confidentiality. Each party shall protect the other's confidential "
     "information.\n\n3. Governing Law. This Agreement is governed by Delaware law.",
     {}, "AUTOMATABLE", "genuinely ABSENT payment terms clause", "NOT_APPLICABLE",
     "No payment/invoicing language anywhere in the document.")
_add("A7-PA-03", 1,
     "1. Services. Marrow Bone Broth Co-Packers shall co-pack broth products for Client as "
     "described in Exhibit A.\n\n2. Quality Standards. All batches shall meet the specifications "
     "in Exhibit B.",
     {}, "AUTOMATABLE", "genuinely ABSENT payment terms clause", "NOT_APPLICABLE",
     "No payment/invoicing language anywhere in the document.")

# Present but phrased unusually — tests whether the extractor RECOGNIZES the
# clause exists (even if it can't fully resolve every field), as opposed to
# silently treating it as absent (a false CONFIRMED-ABSENT / NOT-RECOGNIZED
# defect).
_add("A7-PA-04", 2,
     "6. Compensation. In consideration for the services rendered, Client shall remit "
     "consideration to Vendor on a schedule to be mutually agreed, it being understood that no "
     "such schedule has yet been finalized as of the Effective Date.",
     {}, "SHOULD_REVIEW", "payment clause present under an unusual heading ('Compensation'), "
     "terms explicitly deferred", "REQUIRES_REVIEW",
     "The clause exists and is recognizable, but leaves the actual schedule undetermined — must "
     "be RECOGNIZED-BUT-UNRESOLVED, not treated as if no payment clause exists at all.")
_add("A7-PA-05", 2,
     "6. Fees and Charges. Client's obligation to remunerate Vendor for services rendered shall "
     "be as set forth in the fee table maintained in the Vendor portal (not included in this "
     "excerpt).",
     {}, "SHOULD_REVIEW", "payment clause present, delegates entirely to an external, "
     "unincluded fee table", "REQUIRES_REVIEW",
     "A payment obligation clearly exists ('Fees and Charges' + 'shall be as set forth'), but "
     "its content is entirely external — must be recognized as present-but-unresolved, not "
     "absent.")
_add("A7-PA-06", 3,
     "6. Remittance. Amounts owed by Client to Vendor hereunder shall become due per the terms "
     "the parties are currently negotiating in good faith, no agreement having yet been reached "
     "on the applicable period.",
     {}, "SHOULD_REVIEW", "payment obligation acknowledged, due-date genuinely unresolved",
     "REQUIRES_REVIEW",
     "The clause plainly states a payment obligation exists between named parties, but the due "
     "period is explicitly still under negotiation.")

# Recognized and largely resolvable, but a SPECIFIC policy-tracked sub-fact
# is missing — must be flagged as expected-but-missing, not silently treated
# as satisfied.
_add("A7-PA-07", 2,
     "6. Payment Terms. Client shall pay Vendor within 30 days of invoice date.",
     {"maximum_late_interest_rate_percent": 1.5}, "SHOULD_REVIEW",
     "ordinary due-date clause; policy tracks a maximum late-interest rate but the document "
     "states no late-fee/interest provision at all", "NEGOTIATE",
     "Policy configures a maximum late-payment interest rate as a tracked fact, but this "
     "document is silent on late fees entirely — the ABSENCE of that specific sub-provision is "
     "itself the material fact, and must not be silently treated as 'no violation, so clean'.")
_add("A7-PA-08", 2,
     "6. Payment Terms. Client shall pay Vendor within 30 days of invoice date, in U.S. Dollars.",
     {"require_tax_responsibility_counterparty": True}, "SHOULD_REVIEW",
     "ordinary due-date clause; policy requires the counterparty to bear tax responsibility but "
     "the document says nothing about taxes at all", "NEGOTIATE",
     "Policy requires an explicit tax-responsibility allocation; this document simply never "
     "raises the topic — that absence is itself the material fact needing disclosure.")

# Not-applicable in the structural sense — a genuine payment reference exists
# but for an entirely different, non-vendor-invoice payment flow (e.g., a
# security deposit), and must not be conflated with the operative invoicing
# terms the policy actually tracks.
_add("A7-PA-09", 2,
     "4. Security Deposit. Client shall pay Vendor a refundable security deposit of $5,000 upon "
     "execution of this Agreement, to be returned within 30 days of termination, less any "
     "amounts owed for damages.\n\n7. Confidentiality. Each party shall protect the other's "
     "confidential information.",
     {}, "AUTOMATABLE", "a payment reference exists (security deposit) but it is not the "
     "operative invoicing/payment-terms clause the policy tracks", "NOT_APPLICABLE",
     "A dollar amount and 'pay' language are present, but this is a security deposit, not the "
     "recurring payment-terms provision the policy evaluates — must not be misread as satisfying "
     "the payment-terms check.")

_FAMILY_MINIMUMS = {"absence": 9}


def _validate():
    assert len(CASES) >= 9, f"total {len(CASES)} < 9"
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids)), "duplicate case id"


_validate()
