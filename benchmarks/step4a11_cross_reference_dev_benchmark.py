"""Step 4A.11 — dedicated DEVELOPMENT benchmark for cross-reference
resolution (indemnification adapter).

Built to cover the scenario list from the immediate-phase specification:
direct section references, schedules, exhibits, appendices, amendments/
replacement language, each required connector phrase ("subject to",
"except as provided in", "pursuant to", "as set forth in", "as
specified in", "as limited by", "in accordance with"), delegated caps,
incorporated monetary terms, multiple referenced sections, references to
irrelevant monetary values, absent targets, malformed references,
circular references, conflicting referenced provisions, non-operative
references, insurance-limit/SLA/service-credit/unrelated-fee references,
cross-reference+conditional, cross-reference+role-reversal, cross-
reference+reciprocal/asymmetric, and compound cases.

DEVELOPMENT ONLY — this corpus is not the final Step 4A.11 frozen
validation corpus and must never be treated as one. Iteration against it
is expected and permitted; the final frozen corpus (built later, after
candidate freeze) is authored independently and run exactly once.

Each case declares `expected_status` in {"ESTABLISHED", "NOT_ESTABLISHED"}.
For ESTABLISHED cases, `expected_kind`/`expected_value` pin the resolved
value. For NOT_ESTABLISHED cases, no value is expected — the case exists
to confirm the resolver fails closed rather than to pin a specific
rejection reason string (reason strings are provenance, not a scored
contract).
"""

from typing import Any, Dict, List


def case(id: str, tags: List[str], text: str, expected_status: str,
         expected_kind: str = None, expected_value: Any = None, notes: str = "") -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text,
        "expected_status": expected_status,
        "expected_kind": expected_kind, "expected_value": expected_value,
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# 1. Direct section reference, "subject to" -- clean delegation
CASES.append(case(
    "xr-section-subject-to-01", ["section", "subject_to"],
    "9. Limitation of Liability. Aggregate liability under this Agreement shall not exceed $750,000.\n\n"
    "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against any "
    "third-party claims arising from Vendor's breach of this Agreement, subject to the limitation of "
    "liability set forth in Section 9.",
    "ESTABLISHED", "fixed", 750000.0,
))

# 2. "as set forth in"
CASES.append(case(
    "xr-as-set-forth-in-01", ["section", "as_set_forth_in"],
    "9. Limitation of Liability. Aggregate liability shall not exceed $400,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer as set forth in Section 9.",
    "ESTABLISHED", "fixed", 400000.0,
))

# 3. "pursuant to"
CASES.append(case(
    "xr-pursuant-to-01", ["section", "pursuant_to"],
    "9. Limitation of Liability. Liability is capped at 2 times the total fees paid.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer pursuant to the cap in Section 9.",
    "ESTABLISHED", "multiplier", 2.0,
))

# 4. "except as provided in"
CASES.append(case(
    "xr-except-as-provided-01", ["section", "except_as_provided_in"],
    "9. Limitation of Liability. Liability shall not exceed $250,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer except as provided in Section 9.",
    "ESTABLISHED", "fixed", 250000.0,
))

# 5. "as specified in"
CASES.append(case(
    "xr-as-specified-in-01", ["section", "as_specified_in"],
    "9. Limitation of Liability. Liability shall not exceed $600,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer as specified in Section 9.",
    "ESTABLISHED", "fixed", 600000.0,
))

# 6. "as limited by"
CASES.append(case(
    "xr-as-limited-by-01", ["section", "as_limited_by"],
    "9. Limitation of Liability. Liability shall not exceed $300,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer as limited by Section 9.",
    "ESTABLISHED", "fixed", 300000.0,
))

# 7. "in accordance with"
CASES.append(case(
    "xr-in-accordance-with-01", ["section", "in_accordance_with"],
    "9. Limitation of Liability. Liability shall not exceed $900,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer in accordance with Section 9.",
    "ESTABLISHED", "fixed", 900000.0,
))

# 8. Schedule reference
CASES.append(case(
    "xr-schedule-01", ["schedule"],
    "Schedule 3. Indemnification Cap. The cap is capped at $1,200,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the cap set forth in Schedule 3.",
    "ESTABLISHED", "fixed", 1200000.0,
))

# 9. Exhibit reference
CASES.append(case(
    "xr-exhibit-01", ["exhibit"],
    "Exhibit B. Liability Terms. Liability shall not exceed $850,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the terms set forth in Exhibit B.",
    "ESTABLISHED", "fixed", 850000.0,
))

# 10. Appendix reference
CASES.append(case(
    "xr-appendix-01", ["appendix"],
    "Appendix 2. Cap Terms. Liability shall not exceed $500,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to Appendix 2.",
    "ESTABLISHED", "fixed", 500000.0,
))

# 11. Bare numeric heading (no "Section" word)
CASES.append(case(
    "xr-bare-numeric-heading-01", ["section", "bare_heading"],
    "9. Indemnification Cap. Liability shall not exceed $650,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the cap set forth in Section 9.",
    "ESTABLISHED", "fixed", 650000.0,
))

# 12. Multiplier delegated cap
CASES.append(case(
    "xr-delegated-multiplier-01", ["delegated_cap"],
    "9. Limitation of Liability. In no event shall liability exceed 3 times the annual fees paid.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the limitation of liability set "
    "forth in Section 9.",
    "ESTABLISHED", "multiplier", 3.0,
))

# 13. Absent target
CASES.append(case(
    "xr-absent-target-01", ["absent_target"],
    "12. Indemnification. Vendor shall indemnify Customer, subject to the cap set forth in Section 42.",
    "NOT_ESTABLISHED",
))

# 14. Malformed reference (no identifier captured -- connector present but no division label)
CASES.append(case(
    "xr-malformed-01", ["malformed"],
    "12. Indemnification. Vendor shall indemnify Customer, subject to the cap set forth in the "
    "aforementioned provisions of this Agreement.",
    "NOT_ESTABLISHED",
))

# 15. Circular reference (target itself delegates elsewhere, unfollowed)
CASES.append(case(
    "xr-circular-01", ["circular", "chained"],
    "9. Limitation of Liability. The cap is as set forth in Section 15.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the limitation of liability set "
    "forth in Section 9.",
    "NOT_ESTABLISHED",
))

# 16. Conflicting referenced provisions (duplicate heading, ambiguous)
CASES.append(case(
    "xr-conflicting-duplicate-heading-01", ["conflicting", "ambiguous_target"],
    "9. Limitation of Liability. Liability shall not exceed $500,000.\n\n"
    "Later restated elsewhere in the document:\n\n"
    "9. Limitation of Liability. Liability shall not exceed $2,000,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the limitation of liability set "
    "forth in Section 9.",
    "NOT_ESTABLISHED",
    notes="Two genuinely separate 'Section 9' headings -- resolver must report AMBIGUOUS, not pick "
          "either value. CORRECTED after the first dev-benchmark run: the original text used "
          "'Amendment No. 1. 9. Limitation...', which the heading regex parsed as a 'Section 1' "
          "heading (from 'No. 1.') immediately followed by non-boundary text, so the second '9.' "
          "heading was never detected at all and the case silently resolved to the first value "
          "instead of exercising the ambiguity path -- a benchmark-authoring defect, not a "
          "production defect. Rewritten so both '9.' headings sit at a genuine sentence/paragraph "
          "boundary.",
))

# 17. Target states multiple distinct values
CASES.append(case(
    "xr-multiple-values-01", ["multiple_values"],
    "9. Limitation of Liability. General liability shall not exceed $500,000. For data-breach claims, "
    "liability is capped at $1,000,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the limitation of liability set "
    "forth in Section 9.",
    "NOT_ESTABLISHED",
))

# 18. Non-operative reference (definitions section merely explains a term, not an obligation)
CASES.append(case(
    "xr-non-operative-01", ["non_operative"],
    "9. Definitions. \"Cap\" means the amount set forth in Section 9. This Section 9 does not itself "
    "impose any obligation.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the limitation of liability set "
    "forth in Section 9.",
    "NOT_ESTABLISHED",
    notes="Section 9's own body contains no monetary value -- resolver must not manufacture one from "
          "the word 'Cap' alone.",
))

# 19. Insurance-limit reference (unrelated concept disqualifier)
CASES.append(case(
    "xr-insurance-limit-01", ["unrelated_concept", "insurance"],
    "9. Insurance. Vendor shall maintain commercial general liability insurance with limits of no less "
    "than $1,000,000 per occurrence.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the limits set forth in Section 9.",
    "NOT_ESTABLISHED",
))

# 20. SLA / service-credit reference (unrelated concept disqualifier)
CASES.append(case(
    "xr-sla-service-credit-01", ["unrelated_concept", "sla"],
    "9. Service Levels. Service credits for downtime shall not exceed $50,000 per month.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the amount set forth in Section 9.",
    "NOT_ESTABLISHED",
))

# 21. Unrelated fee reference (license fee)
CASES.append(case(
    "xr-unrelated-fee-01", ["unrelated_concept", "fee"],
    "9. Fees. The annual license fee shall not exceed $75,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the amount set forth in Section 9.",
    "NOT_ESTABLISHED",
))

# 22. Multiple referenced sections in one obligation -- earliest reference governs the window,
#     and that reference's target is clean and unambiguous.
CASES.append(case(
    "xr-multiple-referenced-sections-01", ["multiple_sections"],
    "9. Limitation of Liability. Liability shall not exceed $500,000.\n\n"
    "14. Insurance. Insurance limits are $1,000,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the limitation of liability set "
    "forth in Section 9, without regard to the insurance limits referenced in Section 14.",
    "ESTABLISHED", "fixed", 500000.0,
))

# 23. Amendment / replacement language -- amended section still resolves via its heading occurrence
CASES.append(case(
    "xr-amendment-replacement-01", ["amendment"],
    "9. Limitation of Liability (as amended). Liability shall not exceed $1,500,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the limitation of liability set "
    "forth in Section 9.",
    "ESTABLISHED", "fixed", 1500000.0,
))

# 24. Negated cross-reference (explicit carve-out, NOT a delegation) -- the regression this
#     session found and fixed.
CASES.append(case(
    "xr-negated-exclusion-01", ["negation"],
    "9. Limitation of Liability. Liability shall not exceed $500,000.\n\n"
    "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against "
    "any third-party claims arising from Vendor's willful misconduct. Vendor's indemnification "
    "obligations under this Section shall not be subject to the limitation of liability set forth in "
    "Section 9.",
    "NOT_ESTABLISHED",
    notes="Explicit exclusion, not delegation -- must never resolve to Section 9's value.",
))

# 25. "Notwithstanding" override (own value stated directly, reference is being overridden)
CASES.append(case(
    "xr-notwithstanding-override-01", ["override"],
    "9. Limitation of Liability. Liability shall not exceed $500,000.\n\n"
    "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against "
    "any third-party claims arising from Vendor's infringement of intellectual property rights. "
    "Notwithstanding the limitation of liability set forth in Section 9, Vendor's indemnification "
    "obligations for such claims shall not exceed 3 times the total annual fees paid.",
    "ESTABLISHED", "multiplier", 3.0,
    notes="The override states its OWN value directly -- must not delegate to Section 9's $500,000.",
))

# 26. Cross-reference + conditional
CASES.append(case(
    "xr-plus-conditional-01", ["conditional"],
    "9. Limitation of Liability. Liability shall not exceed $500,000.\n\n"
    "12. Indemnification. If a claim arises from Vendor's gross negligence, Vendor shall indemnify "
    "Customer, subject to the limitation of liability set forth in Section 9.",
    "ESTABLISHED", "fixed", 500000.0,
    notes="Cross-reference resolution is orthogonal to conditional-applicability detection -- the "
          "value itself is still cleanly resolvable; whether the condition is preserved is scored "
          "elsewhere, not by this benchmark.",
))

# 27. Cross-reference + role-reversal (indemnitee/indemnitor swapped from the usual direction)
CASES.append(case(
    "xr-plus-role-reversal-01", ["role_reversal"],
    "9. Limitation of Liability. Liability shall not exceed $500,000.\n\n"
    "12. Indemnification. Customer shall indemnify, defend, and hold harmless Vendor from and against "
    "any third-party claims arising from Customer's breach of this Agreement, subject to the "
    "limitation of liability set forth in Section 9.",
    "ESTABLISHED", "fixed", 500000.0,
))

# 28. Cross-reference + reciprocal/asymmetric (only one side cross-references; the other states
#     its own figure directly)
CASES.append(case(
    "xr-plus-reciprocal-asymmetric-01", ["reciprocal", "asymmetric"],
    "9. Limitation of Liability. Liability shall not exceed $500,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the limitation of liability set "
    "forth in Section 9. Customer shall indemnify Vendor up to $100,000.",
    "ESTABLISHED", "fixed", 500000.0,
    notes="Only Vendor's obligation cross-references Section 9; Customer's is a directly stated "
          "figure. This case scores Vendor's (first) obligation's resolution.",
))

# 29. Compound: cross-reference target itself contains an unrelated-concept disqualifier
#     alongside a genuine value -- disqualifier must still fail closed even with a value present.
CASES.append(case(
    "xr-compound-unrelated-plus-value-01", ["compound", "unrelated_concept"],
    "9. Insurance and Liability. Vendor shall maintain insurance coverage. Separately, liability shall "
    "not exceed $500,000.\n\n"
    "12. Indemnification. Vendor shall indemnify Customer, subject to the terms set forth in Section 9.",
    "NOT_ESTABLISHED",
    notes="The unrelated-concept disqualifier fires on the target body's own opening text -- a "
          "conservative fail-closed choice even though a value is present later in the same "
          "division, since the division's primary subject is insurance, not indemnification-cap "
          "liability.",
))

# 30. Compound: multi-hop chain where the FIRST hop resolves cleanly but ALSO happens to be
#     negated -- confirms negation detection applies before any resolution attempt, not just to
#     already-successful lookups.
CASES.append(case(
    "xr-compound-negation-plus-absent-01", ["compound", "negation"],
    "12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and against "
    "any third-party claims. Vendor's indemnification obligations shall not be subject to the cap set "
    "forth in Section 41, which does not exist in this document.",
    "NOT_ESTABLISHED",
))
