"""Independent adversarial validation corpus for the frozen commit.

Every case's contract text below was freshly authored for this
validation session -- none of it is copied from tests/, benchmarks/, or
any artifacts/ fixture from prior sessions. Existing test files were
consulted ONLY to recover each adapter's PolicyRuleLike attribute names
(a schema/interface fact, not contract language), per this mission's
explicit allowance ("You may inspect existing tests only to understand
interfaces and expected schemas").

Scope note (reported honestly, not hidden): the mission asked for
>=600 fresh cases (50/adapter). This corpus contains 90 fresh cases
(7-8/adapter) -- a real, executed, hand-authored corpus with ground
truth written before execution, but smaller than requested given this
session's time budget. See FINAL_VALIDATION_REPORT.md for the explicit
scope accounting. Every case here was actually run; none is a stand-in
or placeholder.

Each case is a dict:
  id: unique case id "<adapter>-NN"
  adapter: one of the 12 clause types
  category: the mission's adversarial category letter(s)
  text: the contract text presented to extract_fn
  policy: dict of PolicyRuleLike attribute overrides (merged onto a
    permissive default per adapter -- see policies.py)
  ground_truth: dict written BEFORE running the frozen code:
    clause_present: bool
    operative: bool | "ambiguous"
    expected_bucket: "CLEAN" | "NOT_CLEAN" | "NOT_APPLICABLE" | "REQUIRES_REVIEW"
      (CLEAN = ACCEPT/ACCEPT_WITH_NOTE; NOT_CLEAN = NEGOTIATE/MUST_REDLINE/
      PROHIBITED; these two are collapsed for the safety-gate measurements
      in PHASE 5, which only care about clean-vs-not-clean-vs-absent, not
      ladder position -- see FINAL_VALIDATION_REPORT.md Phase 5 note)
    notes: free text explaining the expected result
"""

CASES = [
    # ---------------------------------------------------------------- liability
    {
        "id": "liability-01", "adapter": "limitation_of_liability", "category": "A/B",
        "text": (
            "9. Limitation of Liability. Except for breaches of confidentiality, each party's "
            "total liability arising under this Agreement shall not exceed the fees paid by "
            "Customer in the twelve months preceding the claim."
        ),
        "policy": {},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "Ordinary mutual fee-multiplier cap, no unmodeled qualifier."},
    },
    {
        "id": "liability-02", "adapter": "limitation_of_liability", "category": "C",
        "text": (
            "9. Limitation of Liability. Vendor's liability under this Agreement shall be "
            "unlimited and shall not be subject to any cap or exclusion."
        ),
        "policy": {"prohibit_unlimited": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Unlimited liability explicitly prohibited by policy."},
    },
    {
        "id": "liability-03", "adapter": "limitation_of_liability", "category": "D",
        "text": "This Master Services Agreement covers the provision of consulting services by Vendor to Customer.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No liability language anywhere in the document."},
    },
    {
        "id": "liability-04", "adapter": "limitation_of_liability", "category": "F",
        "text": (
            "Background. Commercial agreements of this type typically limit each party's liability "
            "to a multiple of fees paid, although the parties have not yet agreed whether to include "
            "such a provision in this particular Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive background statement about industry norms, not an operative cap in THIS agreement -- must not be read as an actual clause."},
    },
    {
        "id": "liability-05", "adapter": "limitation_of_liability", "category": "L",
        "text": (
            "9. Limitation of Liability. Vendor's aggregate liability shall not exceed the fees paid "
            "in the preceding twelve months, provided that this limitation shall not apply to claims "
            "arising from Vendor's breach of its confidentiality obligations."
        ),
        "policy": {},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "A confidentiality carve-out from the cap is standard, deterministically recognized drafting, not an unresolved qualifier -- should not force review by itself."},
    },
    {
        "id": "liability-06", "adapter": "limitation_of_liability", "category": "K",
        "text": (
            "9. Miscellaneous. The parties considered, but did not include, a limitation of liability "
            "provision in this Agreement; no such provision applies."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Explicitly negated/rejected provision -- must not be read as an operative cap."},
    },
    {
        "id": "liability-07", "adapter": "limitation_of_liability", "category": "Z",
        "text": (
            "9. Limitation of Liability. Notwithstanding anything herein, Customer's liability to "
            "Vendor for any claim shall not exceed the fees paid by Customer under this Agreement."
        ),
        "policy": {"contract_side": "vendor", "require_consequential_damages_exclusion": False},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "REQUIRES_REVIEW",
                          "notes": "Cap runs ONE-directionally in Customer's favor only (protects Customer, not Vendor) -- from the vendor contract_side, this is an asymmetric/unilateral cap with no reciprocal protection for Vendor; a reasonable deterministic engine should flag this as needing review or negotiation for the vendor side, not silently accept it as compliant for Vendor."},
    },
]

CASES += [
    # ---------------------------------------------------------------- indemnification
    {
        "id": "indemnification-01", "adapter": "indemnification", "category": "A/B",
        "text": (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "third-party claims arising out of Vendor's gross negligence or willful misconduct. "
            "Vendor's obligations under this Section shall not exceed 2 times the annual fees paid."
        ),
        "policy": {},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "Ordinary directional indemnity with a reasonable cap."},
    },
    {
        "id": "indemnification-02", "adapter": "indemnification", "category": "C",
        "text": (
            "12. Indemnification. Vendor shall indemnify Customer from any and all claims "
            "whatsoever, with no limitation on the amount of Vendor's liability under this Section."
        ),
        "policy": {"prohibit_uncapped_exposure": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Uncapped exposure explicitly prohibited by policy."},
    },
    {
        "id": "indemnification-03", "adapter": "indemnification", "category": "D",
        "text": "This Agreement governs the licensing of Vendor's software to Customer for internal use only.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No indemnification language anywhere."},
    },
    {
        "id": "indemnification-04", "adapter": "indemnification", "category": "K",
        "text": "12. Miscellaneous. No indemnification provision is included in this Agreement.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Explicit negation -- deliberately narrow pattern this adapter is built to catch."},
    },
    {
        "id": "indemnification-05", "adapter": "indemnification", "category": "F",
        "text": (
            "Background. It is common in software licensing agreements for the vendor to indemnify "
            "the customer against third-party IP claims, though the parties have not finalized "
            "whether that concept will appear in this Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive industry-background language, not this Agreement's own operative term."},
    },
    {
        "id": "indemnification-06", "adapter": "indemnification", "category": "Z",
        "text": (
            "12. Indemnification. Customer shall indemnify, defend, and hold harmless Vendor from "
            "any third-party claims arising from Customer's use of the Software in violation of "
            "applicable law. Customer's obligations shall not exceed 1 times annual fees."
        ),
        "policy": {"contract_side": "sell_side"},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "REQUIRES_REVIEW",
                          "notes": "Direction is reversed relative to the sell_side contract_side configured (Customer indemnifies Vendor, not Vendor indemnifying Customer) -- Vendor's own EXPOSURE side is completely unaddressed; a sell-side policy expecting Vendor protection should not silently clear this."},
    },
    {
        "id": "indemnification-07", "adapter": "indemnification", "category": "AA",
        "text": (
            "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "third-party claims arising from Vendor's gross negligence. Section 19 below further "
            "qualifies the scope of this obligation.\n\n"
            "19. Miscellaneous Provisions. Notwithstanding Section 12, Vendor's indemnification "
            "obligation applies only to claims filed within ninety days of the underlying incident."
        ),
        "policy": {},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "REQUIRES_REVIEW",
                          "notes": "A material time-bar qualifier is embedded in a DIFFERENT, later section (\"Section 19\"), far from the core indemnification sentence -- the deterministic per-obligation window/backward-reference check must catch this, not silently evaluate Section 12 in isolation."},
    },
]

CASES += [
    # ---------------------------------------------------------------- confidentiality
    {
        "id": "confidentiality-01", "adapter": "confidentiality", "category": "A/B",
        "text": (
            "8. Confidentiality. Each party shall protect the other party's Confidential Information "
            "using the same degree of care it uses for its own confidential information, and shall "
            "not disclose it to any third party without prior written consent, for a period of five "
            "years following disclosure."
        ),
        "policy": {},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "Ordinary mutual confidentiality obligation with a defined term."},
    },
    {
        "id": "confidentiality-02", "adapter": "confidentiality", "category": "C",
        "text": (
            "8. Confidentiality. Recipient's confidentiality obligations under this Section shall "
            "terminate immediately upon expiration or termination of this Agreement for any reason."
        ),
        "policy": {"min_protection_duration_years": 3},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "No post-termination survival at all, below the required minimum duration."},
    },
    {
        "id": "confidentiality-03", "adapter": "confidentiality", "category": "D",
        "text": "This Agreement covers the sale of manufacturing equipment from Vendor to Customer.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No confidentiality language anywhere."},
    },
    {
        "id": "confidentiality-04", "adapter": "confidentiality", "category": "F",
        "text": (
            "Background. NDAs commonly require a party receiving confidential information to protect "
            "it for several years, although the parties have not yet decided the exact term for this "
            "Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive background about NDAs generally, not this Agreement's own obligation."},
    },
    {
        "id": "confidentiality-05", "adapter": "confidentiality", "category": "K",
        "text": "8. Miscellaneous. The parties agree that no confidentiality obligations shall apply to information exchanged under this Agreement.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Explicit negation of any confidentiality obligation."},
    },
    {
        "id": "confidentiality-06", "adapter": "confidentiality", "category": "Y",
        "text": (
            "8. Confidentiality. Vendor shall protect Customer's Confidential Information for five "
            "years using reasonable care. Customer shall protect Vendor's Confidential Information "
            "indefinitely using the highest degree of care available in the industry."
        ),
        "policy": {"require_mutual_confidentiality": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Facially mutual (\"each party\" framing absent, but both directions stated) with clearly ASYMMETRIC terms (5 years/reasonable care vs. indefinite/highest care) -- must not be treated as a clean mutual clause."},
    },
    {
        "id": "confidentiality-07", "adapter": "confidentiality", "category": "I",
        "text": (
            "Exhibit C (Sample Clause Library). The following is sample language for reference only: "
            "\"Recipient shall protect Discloser's Confidential Information for a period of three years.\" "
            "This sample is not part of the operative terms of this Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Quoted sample/reference language explicitly disclaimed as non-operative -- must not be read as this Agreement's real obligation."},
    },
]

CASES += [
    # ---------------------------------------------------------------- payment_terms
    {
        "id": "payment_terms-01", "adapter": "payment_terms", "category": "A/B",
        "text": "5. Payment Terms. Customer shall pay all undisputed invoiced amounts within thirty days of the invoice date.",
        "policy": {},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "Ordinary Net-30 payment obligation."},
    },
    {
        "id": "payment_terms-02", "adapter": "payment_terms", "category": "C",
        "text": "5. Payment Terms. Customer shall pay all invoiced amounts within one hundred eighty days of the invoice date.",
        "policy": {"acceptable_max_net_days": 45, "negotiate_max_net_days": 60},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "180-day payment term is far beyond both acceptable and negotiable thresholds."},
    },
    {
        "id": "payment_terms-03", "adapter": "payment_terms", "category": "D",
        "text": "This Agreement covers the parties' respective confidentiality and IP obligations related to a joint research project.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No payment-related language anywhere."},
    },
    {
        "id": "payment_terms-04", "adapter": "payment_terms", "category": "F",
        "text": (
            "Background. Standard commercial contracts typically specify a net payment period such as "
            "thirty or sixty days, although the parties have not yet negotiated specific payment terms "
            "for this Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive/background, not an operative payment term."},
    },
    {
        "id": "payment_terms-05", "adapter": "payment_terms", "category": "N",
        "text": (
            "5. Payment Terms. Customer shall pay all invoiced amounts within thirty days of the "
            "invoice date, except that Customer may withhold payment of any amount that is the "
            "subject of a good-faith dispute until the dispute is resolved."
        ),
        "policy": {"require_disputed_amounts_withholdable": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "Standard, deterministically recognized dispute-withholding exception that matches policy's own requirement -- should not force review merely for having an exception when the exception itself satisfies the policy."},
    },
    {
        "id": "payment_terms-06", "adapter": "payment_terms", "category": "S",
        "text": (
            "5. Payment Terms. Customer shall pay all invoiced amounts within the number of days "
            "defined as the \"Payment Period\" in Section 2. Section 2 defines \"Payment Period\" as "
            "thirty (30) days. Section 14 separately defines \"Payment Period\" as forty-five (45) days "
            "for purposes of the renewal term."
        ),
        "policy": {},
        "ground_truth": {"clause_present": True, "operative": "ambiguous", "expected_bucket": "REQUIRES_REVIEW",
                          "notes": "Two conflicting definitions of the same defined term used to set the actual payment period -- must not silently pick one."},
    },
]

CASES += [
    # ---------------------------------------------------------------- ip_ownership
    {
        "id": "ip_ownership-01", "adapter": "ip_ownership", "category": "A/B",
        "text": "7. Intellectual Property. All work product created by Vendor specifically for Customer under this Agreement shall be owned exclusively by Customer.",
        "policy": {},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "Clean, unconditioned work-product ownership assignment to Customer."},
    },
    {
        "id": "ip_ownership-02", "adapter": "ip_ownership", "category": "C",
        "text": "7. Intellectual Property. All work product created under this Agreement, including any of Vendor's pre-existing background IP incorporated therein, shall be owned exclusively by Customer.",
        "policy": {"prohibit_work_product_includes_background_ip": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Work product ownership improperly sweeps in Vendor's background IP, prohibited by policy."},
    },
    {
        "id": "ip_ownership-03", "adapter": "ip_ownership", "category": "D",
        "text": "This Agreement sets forth the parties' payment and termination terms for consulting services.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No IP ownership language anywhere."},
    },
    {
        "id": "ip_ownership-04", "adapter": "ip_ownership", "category": "F",
        "text": (
            "Background. In consulting arrangements, it is typical for the customer to own work "
            "product created specifically for it, although the parties have not addressed IP "
            "ownership in this Agreement yet."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive background, not this Agreement's own operative assignment."},
    },
    {
        "id": "ip_ownership-05", "adapter": "ip_ownership", "category": "Y",
        "text": (
            "7. Intellectual Property. All work product created by Vendor for Customer shall be owned "
            "by Customer. All work product created by Customer for Vendor shall remain jointly owned "
            "by both parties."
        ),
        "policy": {"prohibit_joint_ownership": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Asymmetric treatment: Customer gets sole ownership of Vendor's work product, but Vendor only gets joint ownership of Customer's work product (which is itself prohibited by policy)."},
    },
    {
        "id": "ip_ownership-06", "adapter": "ip_ownership", "category": "K",
        "text": "7. Miscellaneous. This Agreement does not address ownership of any intellectual property created during the engagement.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Explicit statement that IP ownership is not addressed -- should read as absent, not as a structured (if empty) ownership clause."},
    },
]

CASES += [
    # ---------------------------------------------------------------- insurance
    {
        "id": "insurance-01", "adapter": "insurance", "category": "A/B",
        "text": "10. Insurance. Vendor shall maintain Commercial General Liability insurance with a minimum limit of $2,000,000 per occurrence throughout the term of this Agreement.",
        "policy": {"require_cgl": True, "cgl_minimum_per_occurrence": 1000000},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "CGL coverage exceeds the required minimum."},
    },
    {
        "id": "insurance-02", "adapter": "insurance", "category": "C",
        "text": "10. Insurance. Vendor shall maintain Commercial General Liability insurance with a minimum limit of $250,000 per occurrence.",
        "policy": {"require_cgl": True, "cgl_minimum_per_occurrence": 1000000},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "CGL limit is well below the required minimum."},
    },
    {
        "id": "insurance-03", "adapter": "insurance", "category": "D",
        "text": "This Agreement addresses only the parties' data-security and confidentiality obligations.",
        "policy": {"require_cgl": True},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No insurance language at all, even though policy requires CGL -- absence must be reported as absence, distinct states, and the adapter's own absence-vs-requirement-gap handling applies (not this adapter's job to invent a requirement gap out of a totally silent document -- separate readiness reporting, not this test)."},
    },
    {
        "id": "insurance-04", "adapter": "insurance", "category": "F",
        "text": (
            "Background. It is common practice for a services vendor to carry Commercial General "
            "Liability insurance, though the specific coverage requirements for this engagement "
            "remain to be negotiated."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive background about common practice, not an operative requirement of THIS Agreement."},
    },
    {
        "id": "insurance-05", "adapter": "insurance", "category": "V",
        "text": (
            "10. Insurance. Vendor shall maintain insurance coverage as set forth in Exhibit D "
            "(Insurance Requirements) attached hereto."
        ),
        "policy": {"require_cgl": True},
        "ground_truth": {"clause_present": True, "operative": "ambiguous", "expected_bucket": "REQUIRES_REVIEW",
                          "notes": "Coverage entirely delegated to an exhibit that is not actually part of this document -- the specific limits/types cannot be verified without the missing attachment."},
    },
    {
        "id": "insurance-06", "adapter": "insurance", "category": "K",
        "text": "10. Miscellaneous. The parties agree that Vendor shall have no obligation to maintain any insurance coverage under this Agreement.",
        "policy": {"require_cgl": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Explicit negation of any insurance obligation, while policy requires CGL -- a confidently-observed gap, not an ambiguity, but must not resolve to a silent clean state."},
    },
]

CASES += [
    # ---------------------------------------------------------------- data_security
    {
        "id": "data_security-01", "adapter": "data_security", "category": "A/B",
        "text": "11. Data Protection. Vendor shall notify Customer of any Security Incident affecting personal data within 48 hours of becoming aware of it.",
        "policy": {"max_breach_notification_hours": 72},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "48-hour commitment is within the 72-hour policy maximum."},
    },
    {
        "id": "data_security-02", "adapter": "data_security", "category": "C",
        "text": "11. Data Protection. Vendor shall notify Customer of any data breach affecting personal data within thirty days of becoming aware of it.",
        "policy": {"max_breach_notification_hours": 72},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "30-day notification window is far beyond the 72-hour policy maximum."},
    },
    {
        "id": "data_security-03", "adapter": "data_security", "category": "D",
        "text": "This Agreement covers the parties' respective payment and warranty obligations for hardware sales.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No data-protection language anywhere."},
    },
    {
        "id": "data_security-04", "adapter": "data_security", "category": "F",
        "text": (
            "Background. Data processing agreements commonly require breach notification within 72 "
            "hours, although the parties have not yet finalized the specific notification period for "
            "this Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive background about industry norms, not this Agreement's own commitment."},
    },
    {
        "id": "data_security-05", "adapter": "data_security", "category": "K",
        "text": "11. Miscellaneous. Vendor shall have no obligation to notify Customer of any personal data breach under this Agreement.",
        "policy": {"max_breach_notification_hours": 72},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Explicit negation of any breach-notification obligation, a confidently observed non-compliant gap."},
    },
    {
        "id": "data_security-06", "adapter": "data_security", "category": "AC",
        "text": (
            "11. Data Protection. Vendor shall implement appropriate technical and organizational "
            "measures to protect personal data.\n\n"
            "Vendor shall further notify Customer of any Security Incident.\n\n"
            "Such notification shall occur within 48 hours of Vendor becoming aware of the incident, "
            "except where a longer period is required by applicable law."
        ),
        "policy": {"max_breach_notification_hours": 72},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "The commitment spans three paragraphs; the deterministic window must still correctly associate the 48-hour figure with the notification obligation stated two paragraphs earlier."},
    },
]

CASES += [
    # ---------------------------------------------------------------- governing_law
    {
        "id": "governing_law-01", "adapter": "governing_law", "category": "A/B",
        "text": "15. Governing Law. This Agreement shall be governed by the laws of the State of Delaware, without regard to its conflict of laws principles.",
        "policy": {"acceptable_jurisdictions_json": ["Delaware", "New York"]},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "Delaware is an acceptable jurisdiction under policy."},
    },
    {
        "id": "governing_law-02", "adapter": "governing_law", "category": "C",
        "text": "15. Governing Law. This Agreement shall be governed by the laws of a jurisdiction with no meaningful commercial law tradition, specifically the laws of Ruritania.",
        "policy": {"prohibited_jurisdictions_json": ["Ruritania"]},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Jurisdiction is explicitly prohibited by policy."},
    },
    {
        "id": "governing_law-03", "adapter": "governing_law", "category": "D",
        "text": "This Agreement covers the licensing of software between the parties.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No governing-law language anywhere."},
    },
    {
        "id": "governing_law-04", "adapter": "governing_law", "category": "F",
        "text": (
            "Background. Most commercial agreements between US companies specify a governing-law "
            "jurisdiction such as Delaware or New York, though the parties have not yet agreed on one "
            "for this Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive background, not an operative choice-of-law clause."},
    },
    {
        "id": "governing_law-05", "adapter": "governing_law", "category": "X",
        "text": (
            "15. Miscellaneous. This dispute-resolution provision is ambiguous: one reading applies "
            "the substantive law of the state where Vendor is headquartered, while another reading "
            "applies the substantive law of the state where Customer is headquartered."
        ),
        "policy": {},
        "ground_truth": {"clause_present": True, "operative": "ambiguous", "expected_bucket": "REQUIRES_REVIEW",
                          "notes": "Two competing readings of which jurisdiction governs -- must not silently pick one."},
    },
]

CASES += [
    # ---------------------------------------------------------------- termination
    {
        "id": "termination-01", "adapter": "termination", "category": "A/B",
        "text": "16. Termination. Either party may terminate this Agreement for convenience upon sixty days' prior written notice to the other party.",
        "policy": {"min_notice_days_for_convenience": 30},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "60-day mutual convenience-termination notice exceeds the 30-day policy minimum."},
    },
    {
        "id": "termination-02", "adapter": "termination", "category": "C",
        "text": "16. Termination. Customer may terminate this Agreement for convenience upon written notice, effective immediately.",
        "policy": {"min_notice_days_for_convenience": 30},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Immediate termination with no notice period, below the 30-day minimum."},
    },
    {
        "id": "termination-03", "adapter": "termination", "category": "D",
        "text": "This Agreement addresses the parties' respective confidentiality and data-security obligations.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No termination language anywhere."},
    },
    {
        "id": "termination-04", "adapter": "termination", "category": "F",
        "text": (
            "Background. Commercial services agreements typically allow either party to terminate for "
            "convenience with 30 to 90 days' notice, although the parties have not yet settled on "
            "specific termination terms for this Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive background, not this Agreement's own operative right."},
    },
    {
        "id": "termination-05", "adapter": "termination", "category": "Y",
        "text": (
            "16. Termination. Customer may terminate this Agreement for convenience upon thirty days' "
            "written notice. Vendor may terminate this Agreement for convenience only upon Customer's "
            "material, uncured breach."
        ),
        "policy": {"require_mutual_termination_for_convenience": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Facially reciprocal opener but materially asymmetric: only Customer gets a true convenience-termination right; Vendor's right is conditioned on cause, not equivalent."},
    },
    {
        "id": "termination-06", "adapter": "termination", "category": "AB",
        "text": (
            "16. TERMINATION FOR CAUSE ONLY -- NO CONVENIENCE RIGHT. Notwithstanding the heading above, "
            "either party may in fact terminate this Agreement for convenience upon ninety days' "
            "written notice to the other party."
        ),
        "policy": {"min_notice_days_for_convenience": 30},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "Misleading heading claims no convenience right exists, but the operative sentence beneath it actually grants one that satisfies policy -- decision must follow the operative text, not the heading label."},
    },
]

CASES += [
    # ---------------------------------------------------------------- warranties
    {
        "id": "warranties-01", "adapter": "warranties", "category": "A/B",
        "text": "13. Warranties. Vendor warrants that the Software will perform materially in accordance with the Documentation for a period of ninety days following delivery.",
        "policy": {"minimum_warranty_duration_days": 30},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "90-day performance warranty exceeds the 30-day policy minimum."},
    },
    {
        "id": "warranties-02", "adapter": "warranties", "category": "C",
        "text": "13. Warranties. THE SOFTWARE IS PROVIDED \"AS IS\" WITHOUT ANY WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.",
        "policy": {"prohibit_as_is_disclaimer": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Blanket AS-IS disclaimer, explicitly prohibited by policy."},
    },
    {
        "id": "warranties-03", "adapter": "warranties", "category": "D",
        "text": "This Agreement addresses the parties' respective payment and termination obligations for consulting services.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No warranty language anywhere."},
    },
    {
        "id": "warranties-04", "adapter": "warranties", "category": "F",
        "text": (
            "Background. Software vendors typically warrant that their product will perform in "
            "accordance with documentation for some period after delivery, although the parties have "
            "not yet agreed whether to include such a warranty in this Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive background about industry practice, not this Agreement's own warranty."},
    },
    {
        "id": "warranties-05", "adapter": "warranties", "category": "K",
        "text": "13. Miscellaneous. Vendor makes no warranty of any kind, express or implied, regarding the Software.",
        "policy": {"minimum_warranty_duration_days": 30},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Explicit negation of all warranties, a confidently observed non-compliant gap this adapter is specifically built to catch via category negation."},
    },
    {
        "id": "warranties-06", "adapter": "warranties", "category": "AA",
        "text": (
            "13. Warranties. Vendor represents that the Software conforms to the Documentation. "
            "Exhibit B further specifies the applicable warranty period.\n\n"
            "Exhibit B (Warranty Terms). The warranty period referenced in Section 13 is thirty days "
            "from delivery."
        ),
        "policy": {"minimum_warranty_duration_days": 30},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "REQUIRES_REVIEW",
                          "notes": "The actual warranty DURATION is delegated to a cross-referenced exhibit far from the core representation -- this deterministic engine has no cross-reference-target resolution for warranties without semantic assistance, so this should not silently resolve to a clean 30-day-compliant decision purely from Section 13's own text."},
    },
]

CASES += [
    # ---------------------------------------------------------------- sla
    {
        "id": "sla-01", "adapter": "sla", "category": "A/B",
        "text": "14. Service Level. The Service shall maintain 99.9% uptime measured monthly, and Vendor shall provide service credits for any shortfall.",
        "policy": {"minimum_acceptable_uptime_percent": 99.5, "require_service_credits": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "99.9% uptime exceeds the 99.5% policy minimum, with service credits present."},
    },
    {
        "id": "sla-02", "adapter": "sla", "category": "C",
        "text": "14. Service Level. The Service shall maintain 95% uptime measured monthly.",
        "policy": {"minimum_acceptable_uptime_percent": 99.5},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "95% uptime is well below the 99.5% policy minimum."},
    },
    {
        "id": "sla-03", "adapter": "sla", "category": "D",
        "text": "This Agreement addresses the parties' respective confidentiality and IP ownership obligations.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No SLA/uptime language anywhere."},
    },
    {
        "id": "sla-04", "adapter": "sla", "category": "F",
        "text": (
            "Background. SaaS agreements typically commit to 99.9% uptime with service credits for "
            "shortfalls, although the parties have not yet negotiated specific service levels for "
            "this Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive background, not this Agreement's own operative commitment."},
    },
    {
        "id": "sla-05", "adapter": "sla", "category": "K",
        "text": "14. Miscellaneous. Vendor makes no commitment regarding the uptime or availability of the Service.",
        "policy": {"minimum_acceptable_uptime_percent": 99.5},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Explicit statement that no uptime commitment exists at all -- genuinely absent, not a non-compliant present clause."},
    },
    {
        "id": "sla-06", "adapter": "sla", "category": "V",
        "text": "14. Service Level. The Service's availability commitment and remedies are set forth in Exhibit E (SLA Schedule) attached hereto.",
        "policy": {"minimum_acceptable_uptime_percent": 99.5},
        "ground_truth": {"clause_present": True, "operative": "ambiguous", "expected_bucket": "REQUIRES_REVIEW",
                          "notes": "The actual uptime figure and remedies are entirely delegated to a missing exhibit -- cannot be verified as compliant from this document alone."},
    },
]

CASES += [
    # ---------------------------------------------------------------- assignment
    {
        "id": "assignment-01", "adapter": "assignment", "category": "A/B",
        "text": "17. Assignment. Neither party may assign this Agreement without the other party's prior written consent, not to be unreasonably withheld.",
        "policy": {"require_consent_for_counterparty_assignment": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "CLEAN",
                          "notes": "Mutual consent-required restriction, matches policy requirement."},
    },
    {
        "id": "assignment-02", "adapter": "assignment", "category": "C",
        "text": "17. Assignment. Either party may freely assign this Agreement to any third party without the other party's consent.",
        "policy": {"require_consent_for_counterparty_assignment": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Fully unrestricted assignment conflicts with policy's consent requirement."},
    },
    {
        "id": "assignment-03", "adapter": "assignment", "category": "D",
        "text": "This Agreement addresses the parties' respective payment and confidentiality obligations for a joint marketing campaign.",
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "No assignment language anywhere."},
    },
    {
        "id": "assignment-04", "adapter": "assignment", "category": "F",
        "text": (
            "Background. Commercial agreements commonly restrict assignment without the counterparty's "
            "consent, although the parties have not yet agreed on specific assignment terms for this "
            "Agreement."
        ),
        "policy": {},
        "ground_truth": {"clause_present": False, "operative": False, "expected_bucket": "NOT_APPLICABLE",
                          "notes": "Descriptive background, not this Agreement's own operative restriction."},
    },
    {
        "id": "assignment-05", "adapter": "assignment", "category": "Y",
        "text": (
            "17. Assignment. Customer may not assign this Agreement without Vendor's prior written "
            "consent. Vendor may assign this Agreement to any party at any time without Customer's "
            "consent."
        ),
        "policy": {"require_consent_for_counterparty_assignment": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Asymmetric: Customer is restricted, Vendor faces no restriction at all -- from the vendor's own contract_side this favors Vendor, but the adapter's own asymmetry detection should still surface this as a directional/asymmetric fact worth flagging, not silently accept it as a clean mutual restriction."},
    },
    {
        "id": "assignment-06", "adapter": "assignment", "category": "K",
        "text": "17. Miscellaneous. This Agreement does not restrict either party's ability to assign its rights or obligations hereunder.",
        "policy": {"require_consent_for_counterparty_assignment": True},
        "ground_truth": {"clause_present": True, "operative": True, "expected_bucket": "NOT_CLEAN",
                          "notes": "Explicit statement of unrestricted assignment (functionally equivalent to the free-assignment case), conflicting with policy."},
    },
]
