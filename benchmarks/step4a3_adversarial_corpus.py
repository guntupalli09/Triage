"""
Step 4A.3 — 40 NEW adversarial cases built AFTER the Step 4A.3 production
changes, to probe the hardened mechanisms with contract language not
copied or paraphrased from the Step 4A.2 held-out corpus. This is
explicitly NOT a replacement for a future frozen held-out corpus (that is
Step 4A.4's job) — it is a first-pass adversarial sanity check run once,
same-session, against the code that was just changed.

10 cases each: role-definition/fallback, Payment recognition, liability
candidate-ownership, indemnification asymmetry.

Each case: (id, adapter, text, kwargs, expect) where expect is one of
"escalate" (REQUIRES_REVIEW expected/acceptable), "clean:<value-substring>"
(a specific clean value expected in extracted_summary), or
"engage" (payment_terms recognition only: clause_found must be True).
"""

# --- Group A: role-definition / fallback (10) ---
ROLE_CASES = [
    ("ADV-ROLE-01", "liability",
     "1. Definitions. 'Distributor' shall be construed to mean the entity acquiring inventory from Manufacturer for resale to end customers.\n\n9. Limitation of Liability. Distributor's aggregate liability shall not exceed 2 times the annual fees paid.",
     {"contract_side": "buy_side"}, "clean:2x annual fees"),
    ("ADV-ROLE-02", "liability",
     "1. Definitions. 'Operator' means the party that maintains and hosts the Platform on behalf of Sponsor, who consumes the Platform's output.\n\n9. Limitation of Liability. Operator's aggregate liability shall not exceed 1 times the annual fees paid.",
     {"contract_side": "buy_side"}, "escalate"),
    # Bare "is" predicate with a "for purposes hereof/as used herein"
    # preamble: narrow discovery doesn't recognize a bare "is" as a
    # definitional predicate at all, so the broad-signal detector (built
    # for exactly this class of unrecognized-but-real definition) fires
    # and escalates — a safe, by-design outcome, not a missed resolution.
    ("ADV-ROLE-03", "indemnification",
     "1. Definitions. As used herein, Franchisee is the party that operates the licensed outlet and pays royalties to Franchisor.\n\n8. Indemnification. Franchisor shall indemnify, defend, and hold harmless Franchisee from and against third-party claims arising from Franchisor's gross negligence, up to a cap of 1 times the fees paid.",
     {"contract_side": "buy_side"}, "escalate"),
    ("ADV-ROLE-04", "indemnification",
     "1. Definitions. 'Underwriter' means the entity that assumes the risk transferred by Cedent under this reinsurance treaty.\n\n8. Indemnification. Underwriter shall indemnify, defend, and hold harmless Cedent from and against third-party claims arising from Underwriter's gross negligence, up to a cap of 2 times the fees paid.",
     {"contract_side": "buy_side"}, "escalate"),
    # "References to X are references to" is deliberately NOT in the
    # narrow interpretable predicate list (Family 1's explicit design
    # constraint) — it always escalates via the broad-signal detector
    # regardless of whether the trailing text happens to agree with the
    # generic mapping, since the system cannot know that without
    # interpreting language it doesn't confidently recognize.
    ("ADV-ROLE-05", "payment_terms",
     "1. Definitions. References to 'Franchisee' are references to the party that pays ongoing royalties to Franchisor in exchange for use of the licensed brand.\n\n7. Taxes. Franchisee shall be responsible for all sales and use taxes arising from this Agreement.",
     {"contract_side": "buy_side", "require_tax_responsibility_counterparty": True}, "escalate"),
    ("ADV-ROLE-06", "payment_terms",
     "1. Definitions. 'Cedent' has the meaning given to 'Reinsured' in the Recitals. 'Reinsured' means the entity that purchases reinsurance protection from Underwriter.\n\n7. Taxes. Cedent shall be responsible for all sales and use taxes arising from this Agreement.",
     {"contract_side": "buy_side", "require_tax_responsibility_counterparty": True}, "escalate"),
    # Sponsor is not in the generic BUY/SELL_SIDE_ROLES vocabulary at all
    # (generic_side=None) — "commissions...from" is Sponsor's own direct
    # conduct (no possessive/passive bystander issue), so the document's
    # own directional evidence is safely used with nothing to conflict
    # against, resolving cleanly.
    ("ADV-ROLE-07", "liability",
     "1. Definitions. 'Sponsor' means the entity that commissions the research study from Investigator and funds its conduct.\n\n9. Limitation of Liability. Sponsor's aggregate liability shall not exceed 3 times the annual fees paid.",
     {"contract_side": "sell_side"}, "clean:3x annual fees"),
    # "conducts"/"reports findings to" are not in the recognized buy/sell
    # verb vocabulary at all — genuinely unrecognized relational content
    # naming another party (Sponsor), so this safely escalates rather
    # than silently falling back.
    ("ADV-ROLE-08", "liability",
     "1. Definitions. 'Investigator' means the entity that conducts the research study and reports findings to Sponsor upon completion of each milestone.\n\n9. Limitation of Liability. Investigator's aggregate liability shall not exceed 1 times the annual fees paid.",
     {"contract_side": "sell_side"}, "escalate"),
    # Tenant resolves cleanly to buy_side (the new "leasing...from" verb
    # family), but Landlord is an unmapped generic role with no document
    # definition of its own (side=None, no conflict) — the evaluator
    # currently requires BOTH obligation sides to be non-None before
    # classifying exposure/protection, so this escalates rather than
    # using Tenant's confidently-known side alone. Safe, but a documented
    # residual generalization opportunity outside the four failure
    # families' scope (see final report Section K).
    ("ADV-ROLE-09", "indemnification",
     "1. Definitions. 'Tenant' means the entity leasing the premises from Landlord and remitting monthly rent in exchange for occupancy rights.\n\n8. Indemnification. Landlord shall indemnify, defend, and hold harmless Tenant from and against third-party claims arising from Landlord's gross negligence, up to a cap of 2 times the fees paid.",
     {"contract_side": "buy_side"}, "escalate"),
    ("ADV-ROLE-10", "indemnification",
     "1. Definitions. 'Landlord' means the entity that retains Tenant's leasehold improvements upon expiration of the lease term.\n\n8. Indemnification. Landlord shall indemnify, defend, and hold harmless Tenant from and against third-party claims arising from Landlord's gross negligence, up to a cap of 1 times the fees paid.",
     {"contract_side": "buy_side"}, "escalate"),
]

# --- Group B: Payment Terms recognition (10) ---
PAYMENT_CASES = [
    ("ADV-PAY-01", "Customer shall be responsible for franchise royalty payments calculated as a percentage of gross sales, remitted monthly.", "engage"),
    ("ADV-PAY-02", "The reinsurance premium shall be paid in quarterly installments in arrears.", "engage"),
    ("ADV-PAY-03", "Tenant shall pay base rent and additional rent as set forth in Exhibit A, due on the first day of each month.", "engage"),
    ("ADV-PAY-04", "Licensee shall remit royalties within 45 days of the end of each calendar quarter.", "engage"),
    ("ADV-PAY-05", "Any amount not paid when due shall accrue interest at the lesser of 1% per month or the maximum rate permitted by law.", "engage"),
    # "deduct" without the word "set-off"/"offset" is a genuine recognition
    # gap outside the vocabulary hardened in this pass — documented as a
    # remaining weakness (final report Section K), not silently expected
    # to pass.
    ("ADV-PAY-06", "Customer may deduct from any payment due to Vendor an amount equal to any credits owed under the service level agreement.", "no_engage_known_gap"),
    ("ADV-PAY-07", "All fees are quoted exclusive of GST, which shall be added to each invoice at the applicable statutory rate.", "engage"),
    ("ADV-PAY-08", "Sponsor shall reimburse Investigator for pre-approved travel and per-diem expenses incurred in connection with the study.", "engage"),
    # "adjust the royalty rate" (domain vocabulary outside "increase the
    # fees/price") is a genuine recognition gap — documented as a
    # remaining weakness, not silently expected to pass.
    ("ADV-PAY-09", "Franchisor may adjust the royalty rate no more than once per calendar year upon 90 days' written notice to Franchisee.", "no_engage_known_gap"),
    ("ADV-PAY-10", "The parties dispute an invoiced amount; pending resolution, Customer shall continue to remit all amounts not subject to the dispute.", "engage"),
]

# --- Group C: Liability candidate-ownership (10) ---
LIABILITY_OWNERSHIP_CASES = [
    # "per-subject payment cap" is a novel disqualifier phrase not in the
    # recognized disqualifying-concept vocabulary (service credit/SLA/
    # insurance/etc.) — REQUIRES_REVIEW is the safe, conservative outcome
    # for a distractor phrasing outside that vocabulary's current
    # coverage, documented as a remaining weakness rather than chased
    # into an ever-expanding disqualifier list.
    ("ADV-LOL-01", "9. Limitation of Liability. Investigator's aggregate liability, including without limitation any per-subject payment cap of $5,000 described in the Budget, shall not exceed $2,000,000 in the aggregate under this Agreement.", "escalate"),
    ("ADV-LOL-02", "9. Limitation of Liability. Franchisor shall maintain product liability insurance of $10,000,000; separate from and not a limitation on the foregoing, Franchisor's aggregate liability to Franchisee shall not exceed 2 times the annual royalties paid.", "clean:2 times the annual royalties paid"),
    ("ADV-LOL-03", "9. Limitation of Liability. Landlord's liability shall be as set forth in Exhibit R.\n\nExhibit R: Risk Terms.\n(a) Security deposit: $20,000.\n(b) Liability cap: 1 times the annual rent paid.\n(c) Late fee reserve: $8,000.", "clean:1 times the annual rent paid"),
    ("ADV-LOL-04", "9. Limitation of Liability. Underwriter's aggregate liability shall not exceed $3,000,000; the reinsurance retention of $250,000 is addressed separately in Section 6.", "clean:$3,000,000"),
    ("ADV-LOL-05", "9. Limitation of Liability. Sponsor's liability shall be governed by Schedule S.\n\nSchedule S: Sponsor shall maintain clinical trial insurance of $8,000,000. No other liability terms are stated in Schedule S.", "escalate"),
    ("ADV-LOL-06", "9. Limitation of Liability. Tenant's aggregate liability shall not exceed 1 times the annual base rent paid. Tenant's aggregate liability shall not exceed 3 times the annual base rent paid.", "escalate"),
    ("ADV-LOL-07", "9. Limitation of Liability. Franchisee's liability, in the aggregate and across all claims, shall be limited to the Royalty Cap Amount, which the parties agree is $600,000.", "clean:$600,000"),
    ("ADV-LOL-08", "9. Limitation of Liability. In no event shall Cedent's aggregate liability under this treaty exceed $4,500,000, exclusive of and in addition to amounts recoverable under Cedent's retrocession coverage of $9,000,000.", "clean:$4,500,000"),
    ("ADV-LOL-09", "9. Limitation of Liability. Reinsured's liability shall be as set forth in Annex T.\n\nAnnex T: Loss Allocation.\n(a) Deductible: $50,000.\n(b) Ceding commission: $100,000.\n(c) Liability Cap: 2 times the annual premium paid.\n(d) Claims reserve: $200,000.", "clean:2 times the annual premium paid"),
    ("ADV-LOL-10", "9. Limitation of Liability. Manufacturer's aggregate liability shall not exceed $1,800,000, independent of the $30,000 warranty reserve described in Section 11.", "clean:$1,800,000"),
]

# --- Group D: Indemnification reciprocal asymmetry (10) ---
INDEMNIFICATION_ASYMMETRY_CASES = [
    ("ADV-INDEM-01", "8. Indemnification. Each party shall indemnify, defend, and hold harmless the other party from and against third-party claims arising from the indemnifying party's gross negligence, up to a cap of 1 times the fees paid.", False),
    ("ADV-INDEM-02", "8. Indemnification. The parties shall mutually indemnify each other from and against third-party claims arising from breach of confidentiality, up to a cap of 2 times the fees paid.", False),
    ("ADV-INDEM-03", "8. Indemnification. Each party shall indemnify the other party from third-party claims arising from gross negligence, up to a cap of 1 times the fees paid, except that Franchisor's cap for claims arising from the licensed brand shall be 4 times the fees paid.", True),
    ("ADV-INDEM-04", "8. Indemnification. The parties shall mutually indemnify each other from third-party claims, up to a cap of 2 times the fees paid, provided that Underwriter's cap for claims arising from the treaty shall be 6 times the fees paid.", True),
    ("ADV-INDEM-05", "8. Indemnification. Each party shall indemnify the other from third-party claims arising from willful misconduct. Landlord's indemnification obligations under this Section shall not exceed 1 times the annual rent paid. Tenant's indemnification obligations under this Section shall not exceed 5 times the annual rent paid.", True),
    ("ADV-INDEM-06", "8. Indemnification. The parties shall mutually indemnify each other from third-party claims, provided that Sponsor's obligations under this Section shall not exceed 2 times the fees paid and Investigator's obligations under this Section shall not exceed 2 times the fees paid.", False),
    ("ADV-INDEM-07", "8. Indemnification. Each party shall indemnify the other party from third-party claims arising from gross negligence, except that Reinsured's indemnification obligations under this Section shall also include claims arising from data breach.", True),
    ("ADV-INDEM-08", "8. Indemnification. Franchisor shall indemnify, defend, and hold harmless Franchisee from and against third-party claims arising from Franchisor's gross negligence, up to a cap of 3 times the fees paid.", None),
    ("ADV-INDEM-09", "8. Indemnification. Each party shall indemnify, defend, and hold harmless the other party and its affiliates from and against third-party claims, up to a cap of 1 times the fees paid, subject to a notice and cooperation requirement.", False),
    ("ADV-INDEM-10", "8. Indemnification. The parties shall mutually indemnify each other from third-party claims arising from breach of this Agreement, on terms to be further specified by the parties from time to time for each Order Form.", None),
]

assert len(ROLE_CASES) == 10
assert len(PAYMENT_CASES) == 10
assert len(LIABILITY_OWNERSHIP_CASES) == 10
assert len(INDEMNIFICATION_ASYMMETRY_CASES) == 10
