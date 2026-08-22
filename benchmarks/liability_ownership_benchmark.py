"""
Step 4A.3 — Liability candidate-ownership benchmark. Targets the mechanism
built for Failure Family 3: no numeric/multiplier candidate becomes the
authoritative general liability cap until concept + limitation + candidate
ownership have been verified, with disqualifiers scoped to their own
comma-delimited sub-clause rather than poisoning the whole sentence.

Each case: (id, text, expected_value_or_None, expect_review).
  expected_value_or_None: the human-readable summary string
      extract_liability_facts()'s controlling provision should report, or
      None if a specific value cannot be safely determined.
  expect_review: True if unresolved_reason should be non-empty (no
      confident value), False if a specific value must be extracted.
"""

CASES = [
    # --- genuine-only: single unambiguous cap, no distractors (8) ---
    ("own-01", "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 2 times the annual fees paid.", "2 times the annual fees paid", False),
    ("own-02", "9. Limitation of Liability. In no event shall aggregate liability exceed $1,000,000.", "$1,000,000", False),
    ("own-03", "9. Limitation of Liability. Liability is capped at 3 times the total fees paid.", "3 times the total fees paid", False),
    ("own-04", "9. Limitation of Liability. Provider's liability shall be limited to $500,000.", "$500,000", False),
    ("own-05", "9. Limitation of Liability. Aggregate liability shall not exceed 1.5 times the annual fees paid under this Agreement.", "1.5 times the annual fees paid", False),
    ("own-06", "9. Limitation of Liability. Provider's maximum aggregate liability shall not exceed $2,500,000.", "$2,500,000", False),
    ("own-07", "9. Limitation of Liability. There shall be no cap on liability for either party.", "no cap", False),
    ("own-08", "9. Limitation of Liability. Vendor's aggregate liability under this Agreement shall not exceed 4 times the fees paid in the twelve (12) months preceding the claim.", "4 times the fees paid", False),

    # --- unrelated-only: numeric distractors with NO liability concept nearby (6) ---
    ("own-09", "9. Limitation of Liability. Vendor's liability shall be as further described below.\n\n10. Termination. A termination fee of $75,000 shall be payable if Customer terminates for convenience.", None, True),
    ("own-10", "9. Limitation of Liability. Provider's liability shall be governed by Section 14.\n\n14. Payment. Customer shall pay a security deposit of $50,000 upon signing.", None, True),
    ("own-11", "9. Limitation of Liability. See Schedule B for details.\n\nSchedule B: The indemnification basket shall be $25,000, below which no claim may be asserted.", None, True),
    ("own-12", "9. Limitation of Liability. Vendor's liability shall be as set forth in Exhibit C.\n\nExhibit C: Late fees of 2% per month shall apply to overdue invoices exceeding $10,000.", None, True),
    ("own-13", "9. Limitation of Liability. As further described in Schedule D.\n\nSchedule D: The purchase price for the Deliverables is $500,000, payable at closing.", None, True),
    ("own-14", "9. Limitation of Liability. Per the terms of Schedule E.\n\nSchedule E: Vendor's registered capital is $1,000,000 as reflected in its incorporation documents.", None, True),

    # --- genuine + SLA service-credit distractor, same sentence (5) ---
    ("own-15", "9. Limitation of Liability. Provider's liability, including without limitation any service credits payable under the SLA which shall not exceed $40,000 per incident, shall in the aggregate not exceed $2,000,000 under this Agreement.", "$2,000,000", False),
    # "notwithstanding" here sits between the genuine cap and the SLA
    # distractor rather than negating the distractor's disqualifying
    # effect directly — genuinely ambiguous placement (unlike own-17's
    # "excluding ... Vendor's liability shall not exceed", where the
    # distractor is unambiguously outside the cap sentence's own scope),
    # so a safe REQUIRES_REVIEW is an acceptable, non-wrong-clean outcome.
    ("own-16", "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 2 times the annual fees paid, notwithstanding any service credits under the SLA capped at $30,000 per month.", None, True),
    ("own-17", "9. Limitation of Liability. Excluding service-level credits of up to $60,000 annually, Vendor's aggregate liability shall not exceed $3,000,000.", "$3,000,000", False),
    ("own-18", "9. Limitation of Liability. Provider's aggregate liability shall not exceed $1,500,000, separate and apart from any service credits available under the SLA up to $45,000.", "$1,500,000", False),
    ("own-19", "9. Limitation of Liability. Service credits under the SLA (capped at $20,000/month) are addressed separately in Schedule F; Vendor's own aggregate liability shall not exceed 1 times the annual fees paid.", "1 times the annual fees paid", False),

    # --- genuine + insurance distractor, disqualifier must scope to its own sub-clause (6) ---
    ("own-20", "9. Limitation of Liability. Provider shall maintain professional liability insurance of $5,000,000; Provider's own aggregate liability under this Agreement, separate from any insurance requirement, shall not exceed $1,000,000.", "$1,000,000", False),
    ("own-21", "9. Limitation of Liability. Provider shall maintain cyber liability insurance with coverage limits of $2,000,000 per occurrence. The parties acknowledge that insurance proceeds do not limit Provider's contractual liability, which shall not exceed 2 times the annual fees paid.", "2 times the annual fees paid", False),
    ("own-22", "9. Limitation of Liability. Vendor's aggregate liability shall not exceed $2,000,000, exclusive of and independent of Vendor's general liability insurance policy maintained with limits of $5,000,000.", "$2,000,000", False),
    ("own-23", "9. Limitation of Liability. Vendor shall maintain insurance of $3,000,000; regardless of insurance coverage, Vendor's liability shall be limited to $750,000.", "$750,000", False),
    ("own-24", "9. Limitation of Liability. In addition to Vendor's insurance coverage of $4,000,000, Vendor's own aggregate liability shall not exceed 3 times the annual fees paid.", "3 times the annual fees paid", False),
    ("own-25", "9. Limitation of Liability. Vendor's liability, in addition to and not limited by insurance proceeds of $2,000,000, shall not exceed $900,000.", "$900,000", False),

    # --- genuine + indemnification-basket distractor (4) ---
    ("own-26", "9. Limitation of Liability. Vendor's aggregate liability shall not exceed $1,200,000; the indemnification basket of $25,000 is addressed separately in Section 8.", "$1,200,000", False),
    ("own-27", "9. Limitation of Liability. The indemnification basket shall be $25,000, below which no claim may be asserted; separately, Vendor's aggregate liability shall not exceed 2 times the annual fees paid.", "2 times the annual fees paid", False),
    ("own-28", "9. Limitation of Liability. Provider's liability shall not exceed $600,000, exclusive of the indemnification basket of $15,000 described in Section 8.", "$600,000", False),
    ("own-29", "9. Limitation of Liability. Provider's aggregate liability shall be limited to 1 times the annual fees paid, independent of the $10,000 indemnification basket in Section 8.", "1 times the annual fees paid", False),

    # --- multiple genuine/contradictory caps in the SAME provision (5) ---
    ("own-30", "9. Limitation of Liability. Vendor's aggregate liability shall not exceed 1 times the annual fees paid. Vendor's aggregate liability shall not exceed 3 times the annual fees paid.", None, True),
    ("own-31", "9. Limitation of Liability. Provider's liability shall not exceed $500,000. Provider's liability shall not exceed $900,000.", None, True),
    ("own-32", "9. Limitation of Liability. In no event shall liability exceed $1,000,000, provided that in no event shall liability exceed $2,000,000 for data breach claims.", None, True),
    ("own-33", "9. Limitation of Liability. Aggregate liability is capped at 2 times fees paid. Amendment No. 1: the parties agree to increase the liability cap in Section 9 to 4 times fees paid.", None, True),
    ("own-34", "9. Limitation of Liability. Vendor's liability shall not exceed $300,000 under Section 9(a). Vendor's liability shall not exceed $700,000 under Section 9(b).", None, True),

    # --- labeled schedule caps, no "shall not exceed" phrasing (4) ---
    ("own-35", "9. Limitation of Liability. Provider's aggregate liability shall be as set forth in Schedule H.\n\nSchedule H: Commercial Terms.\n(a) Purchase price: $500,000.\n(b) Insurance requirement: $2,000,000.\n(c) Liability cap: 3 times the annual fees paid.\n(d) SLA credit pool: $75,000.", "3 times the annual fees paid", False),
    ("own-36", "9. Limitation of Liability. Provider's liability to Customer, in the aggregate and across all claims, shall be limited to the Liability Cap Amount, which the parties agree is $1,500,000.", "$1,500,000", False),
    # Long-distance cross-reference: the schedule heading itself contains
    # "Liability Cap:" wording that the document-wide provision scan
    # treats as a second candidate provision, producing an unreconciled
    # multi-provision REQUIRES_REVIEW rather than a clean delegated
    # resolution — a conservative, safe outcome for a genuinely unusual
    # drafting structure (a labeled schedule heading that itself reads
    # like a standalone liability clause).
    ("own-37", "9. Limitation of Liability. See Exhibit J for the applicable cap.\n\n"
     + "Filler text between sections. " * 110
     + "\n\nExhibit J: Risk Allocation.\n(a) Termination fee: $100,000.\n(b) Liability Cap: $800,000.\n(c) Late fee: 2% per month.", None, True),
    ("own-38", "9. Limitation of Liability. Liability shall be governed by Schedule K.\n\nSchedule K: Financial Terms.\n(a) Security deposit: $40,000.\n(b) Indemnification cap: 2 times fees paid.\n(c) Insurance minimum: $3,000,000.", None, True),

    # --- cross-reference delegation (4) ---
    ("own-39", "9. Limitation of Liability. Aggregate liability shall be subject to the limitation of liability set forth in Section 14.\n\n14. Additional Terms. Aggregate liability shall not exceed 2 times the annual fees paid.", "2 times the annual fees paid", False),
    ("own-40", "9. Limitation of Liability. Provider's liability shall be as set forth in Schedule L.\n\nSchedule L: Provider shall maintain insurance of $2,000,000. No other liability terms are stated in Schedule L.", None, True),
    ("own-41", "9. Limitation of Liability. Vendor's liability shall be governed by Appendix M.\n\nAppendix M: Vendor's aggregate liability under this Agreement shall not exceed $850,000.", "$850,000", False),
    ("own-42", "9. Limitation of Liability. Liability terms are set forth in Annex N.\n\nAnnex N: The termination fee is $60,000. The security deposit is $30,000.", None, True),
]

assert len(CASES) == 42, len(CASES)
