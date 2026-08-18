"""Step 4A.5 dedicated benchmark: multi-word role-NAME BOUNDARY accuracy.

Locked BEFORE being used to further modify the multi-word role-name
mechanism (policy_engine_core.trim_role_name / _MULTIWORD_ROLE_NAME_FRAGMENT,
already implemented earlier in Step 4A.5). Measures whether the exact
boundary of a captured role name is correct — not merely whether SOME
role is captured.

Each case is (case_id, role_definition_or_obligation_sentence, expected_role,
is_positive, note). Positive cases (>=30) are multi-word role names that
must be captured in FULL (not truncated to the last word, not over-captured
into a trailing connector/stopword). Negative/boundary cases (>=20) test
that a NEARBY unrelated entity (an affiliate, a subcontractor, a notice
address, a corporate suffix, a different named party in the same sentence)
does NOT get pulled into the captured role name.
"""

CASES = [
    # --- Positive: multi-word role names, exact boundary required ---
    ("RB-01", "Charter Operator", "hold_harmless", True, "two-word role name, direct object"),
    ("RB-02", "Home Health Agency", "hold_harmless", True, "three-word role name"),
    ("RB-03", "Patient Referral Source", "hold_harmless", True, "three-word role name, second slot"),
    ("RB-04", "Telecom Reseller", "hold_harmless", True, "two-word role name"),
    ("RB-05", "Toll Manufacturer", "hold_harmless", True, "two-word role name"),
    ("RB-06", "Brand Owner", "hold_harmless", True, "two-word role name"),
    ("RB-07", "Import Broker", "hold_harmless", True, "two-word role name"),
    ("RB-08", "Importer of Record", "hold_harmless", True, "three-word role name including preposition-like connector"),
    ("RB-09", "Underwriting Agent", "hold_harmless", True, "two-word role name"),
    ("RB-10", "Host Facility", "hold_harmless", True, "two-word role name"),
    ("RB-11", "Tenant Operator", "hold_harmless", True, "two-word role name"),
    ("RB-12", "Energy Purchaser", "hold_harmless", True, "two-word role name"),
    ("RB-13", "Charter Party", "hold_harmless", True, "two-word role name (distinct from Charter Operator)"),
    ("RB-14", "Ceding Reinsurer", "hold_harmless", True, "two-word role name"),
    ("RB-15", "Fronting Insurer", "hold_harmless", True, "two-word role name"),
    ("RB-16", "Consignee Party", "hold_harmless", True, "two-word role name"),
    ("RB-17", "Grower Cooperative", "hold_harmless", True, "two-word role name"),
    ("RB-18", "Processor Group", "hold_harmless", True, "two-word role name"),
    ("RB-19", "Staffing Agency", "hold_harmless", True, "two-word role name"),
    ("RB-20", "Warehouse Operator", "hold_harmless", True, "two-word role name"),
    ("RB-21", "Fleet Manager", "hold_harmless", True, "two-word role name"),
    ("RB-22", "Terminal Operator", "hold_harmless", True, "two-word role name"),
    ("RB-23", "Origination Agent", "hold_harmless", True, "two-word role name"),
    ("RB-24", "Servicing Agent", "hold_harmless", True, "two-word role name"),
    ("RB-25", "Underwriting Manager", "hold_harmless", True, "two-word role name"),
    ("RB-26", "Loss Adjuster", "hold_harmless", True, "two-word role name"),
    ("RB-27", "Claims Administrator", "hold_harmless", True, "two-word role name"),
    ("RB-28", "Network Operator", "hold_harmless", True, "two-word role name"),
    ("RB-29", "Franchise Development Manager", "hold_harmless", True, "three-word role name"),
    ("RB-30", "Regional Distribution Partner", "hold_harmless", True, "three-word role name"),
    ("RB-31", "Cargo Handling Agent", "hold_harmless", True, "three-word role name"),
    ("RB-32", "Vessel Charter Broker", "hold_harmless", True, "three-word role name"),
    ("RB-33", "Equipment Leasing Company", "hold_harmless", True, "three-word role name"),

    # --- Negative/boundary: nearby unrelated entity must NOT be captured.
    # The bystander entity is placed in a PARENTHETICAL aside immediately
    # after the role name (the realistic drafting shape _OBLIGATION_RE's
    # optional "(?:\s*\([^)]{0,40}\))?" is designed for) rather than as a
    # bare trailing clause directly adjacent to the verb — a bystander
    # entity sitting immediately before "shall indemnify" with no
    # punctuation boundary at all would confuse any subject-identification
    # approach, human or automated, and is not the boundary case this
    # benchmark is targeting.
    ("NEG-RB-01", "Charter Operator (together with Charter Support Services Inc)", "Charter Operator", False, "affiliate name in parenthetical must not be folded in"),
    ("NEG-RB-02", "Toll Manufacturer (subcontractor: Regional Fabrication Partners)", "Toll Manufacturer", False, "subcontractor entity in parenthetical must not be folded in"),
    ("NEG-RB-03", "Host Facility (notices c/o Corporate Compliance Group)", "Host Facility", False, "notice-address entity in parenthetical must not be folded in"),
    ("NEG-RB-04", "Underwriting Agent (a subsidiary of Meridian Holdings Corp)", "Underwriting Agent", False, "parent-company name in parenthetical must not be folded in"),
    ("NEG-RB-05", "Import Broker (represented by Pacific Customs Services)", "Import Broker", False, "designated representative name in parenthetical must not be folded in"),
    ("NEG-RB-06", "Brand Owner (successor to Prior Brand Holdings LLC)", "Brand Owner", False, "predecessor entity in parenthetical must not be folded in"),
    ("NEG-RB-07", "CHARTER OPERATOR (FORMERLY KNOWN AS COASTAL CHARTER HOLDINGS)", "CHARTER OPERATOR", False, "ALL-CAPS: parenthetical former-name entity must not be folded in"),
    ("NEG-RB-08", "TOLL MANUFACTURER (A DELAWARE CORPORATION)", "TOLL MANUFACTURER", False, "ALL-CAPS: corporate-form parenthetical must not be folded in"),
    ("NEG-RB-09", "HOST FACILITY (AN AFFILIATE OF SUMMIT PROPERTIES)", "HOST FACILITY", False, "ALL-CAPS: affiliate parenthetical must not be folded in"),
    ("NEG-RB-10", "Patient Referral Source (c/o Regional Medical Partners)", "Patient Referral Source", False, "care-of parenthetical must not extend capture"),
    ("NEG-RB-11", "Energy Purchaser (acting as Grid Balancing Authority)", "Energy Purchaser", False, "capacity-clause entity in parenthetical must not be folded in"),
    ("NEG-RB-12", "Ceding Reinsurer (broker: Global Reinsurance Brokers Ltd)", "Ceding Reinsurer", False, "care-of address entity in parenthetical must not be folded in"),
    ("NEG-RB-13", "Servicing Agent (formerly National Loan Servicing Co)", "Servicing Agent", False, "former-name entity in parenthetical must not be folded in"),
    ("NEG-RB-14", "Terminal Operator (parent: Atlantic Ports Holdings)", "Terminal Operator", False, "parent-company entity in parenthetical must not be folded in"),
    ("NEG-RB-15", "Fleet Manager (payments via Southeast Logistics Payments LLC)", "Fleet Manager", False, "payment-agent entity in parenthetical must not be folded in"),
    ("NEG-RB-16", "Warehouse Operator (copy: General Counsel Legal Department)", "Warehouse Operator", False, "copy-recipient department name in parenthetical must not be folded in"),
    ("NEG-RB-17", "Network Operator (d/b/a Continental Fiber Networks)", "Network Operator", False, "d/b/a trade name in parenthetical must not be folded in"),
    ("NEG-RB-18", "Claims Administrator (successor: Claims Processing Firm)", "Claims Administrator", False, "successor-firm entity in parenthetical must not be folded in"),
    ("NEG-RB-19", "Origination Agent (affiliate: Third Party Loan Purchasers)", "Origination Agent", False, "affiliate clause in parenthetical must not be folded in"),
    ("NEG-RB-20", "Loss Adjuster (retained by Consolidated Claims Bureau)", "Loss Adjuster", False, "retaining-party entity in parenthetical must not be folded in"),
]
