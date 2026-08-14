"""
Labeled adversarial corpus for the SLA / Service Levels policy engine
benchmark (see benchmarks/run_sla_benchmark.py). Adapter #12 — built per
the resolved design in docs/architecture/sla_adapter_design.md.

Labels here were written from the policy semantics and the drafting
pattern alone, reasoning directly from sla_policy_engine.py's
evaluate_sla_policy logic, never by running the implementation and
copying whatever it happened to output. Where a label was corrected
after a benchmark run, the correction and its reasoning are recorded in
the case's `notes` field, per the discipline established with payment_
terms and warranties.

DEFAULT_POLICY requires NOTHING by default (every require_*/prohibit_*
field is False, every threshold/basis is None). Each case here
explicitly turns on only the dimension(s) it means to test via
policy_overrides.

contract_side is "buy_side" by default (we are "Customer"); individual
cases override this only where directionality itself matters (SLA has
no directional facts of its own -- unlike payment_terms/insurance/
warranties, availability/severity/remedy facts are not attributed to a
"side" -- so contract_side mostly only affects escalation/fallback
plumbing here, not evaluation logic).

Several cases are deliberate NEGATIVE CONTROLS: "P1"/"P2" used as
non-severity labels (project phases), percentages belonging to an
unrelated clause (equity ownership, price increases), and "guarantee"/
"critical" used in ordinary, non-SLA senses -- these must resolve
NOT_APPLICABLE or leave the relevant fact unestablished, never
contaminate an SLA fact.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "buy_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: 99.9% uptime measured monthly, excluding scheduled "
                      "maintenance; P1 1hr response/4hr restoration, P2 4hr/1 business day, "
                      "P3 1 business day response; 24x7 support for P1/P2; 5% monthly-fee service "
                      "credit per breach capped at 25% of monthly fees; chronic-failure "
                      "termination right; credits not exclusive remedy.",
    "require_uptime_commitment": False,
    "preferred_uptime_percent": None,
    "minimum_acceptable_uptime_percent": None,
    "permitted_maintenance_exclusions_json": None,
    "require_severity_tiers": False,
    "p1_max_response_hours": None, "p1_response_basis": None,
    "p1_max_restoration_hours": None, "p1_restoration_basis": None,
    "p2_max_response_hours": None, "p2_response_basis": None,
    "p2_max_restoration_hours": None, "p2_restoration_basis": None,
    "p3_max_response_hours": None, "p3_response_basis": None,
    "p3_max_restoration_hours": None, "p3_restoration_basis": None,
    "p4_max_response_hours": None, "p4_response_basis": None,
    "p4_max_restoration_hours": None, "p4_restoration_basis": None,
    "required_support_hours": None,
    "require_service_credits": False,
    "minimum_credit_percent_of_fees": None,
    "minimum_credit_cap_percent_of_fees": None,
    "require_chronic_failure_remedy": False,
    "require_termination_right_for_chronic_failure": False,
    "prohibit_service_credits_as_exclusive_remedy": False,
    "minimum_claim_submission_days": None,
}


def case(
    id: str,
    tags: List[str],
    text: str,
    expected_state: str,
    policy_overrides: Optional[Dict[str, Any]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "expected_state": expected_state,
        "policy_overrides": policy_overrides or {},
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Fully-compliant baseline.
# ---------------------------------------------------------------------------
FULLY_COMPLIANT_TEXT = (
    "14. Service Levels. Provider shall maintain an availability commitment of 99.95% uptime, "
    "measured monthly, excluding scheduled maintenance and force majeure events. P1 | 1 hour | "
    "4 hours. P2 | 4 hours | 8 hours. Support is available 24x7 for Severity 1 and Severity 2 "
    "issues. If Provider fails to meet the applicable service level, Customer shall receive a "
    "service credit equal to 5% of the monthly fees, capped at 25% of monthly fees. Claims for "
    "service credit must be submitted within 30 days of the qualifying event. In the case of "
    "chronic failure, defined as three consecutive months of Severity 1 breach, Customer shall "
    "have the right to terminate this Agreement."
)
FULLY_COMPLIANT_POLICY = {
    "minimum_acceptable_uptime_percent": 99.9,
    "p1_max_response_hours": 2.0, "p1_response_basis": "calendar",
    "p1_max_restoration_hours": 8.0, "p1_restoration_basis": "calendar",
    "minimum_credit_percent_of_fees": 3.0,
    "minimum_credit_cap_percent_of_fees": 10.0,
    "require_chronic_failure_remedy": True,
    "require_termination_right_for_chronic_failure": True,
    "minimum_claim_submission_days": 15.0,
}
CASES.append(case(
    "clean-01", ["baseline", "fully_compliant"], FULLY_COMPLIANT_TEXT, "ACCEPT",
    policy_overrides=FULLY_COMPLIANT_POLICY,
    notes="Every configured requirement is satisfied: 99.95% clears the 99.9% floor, P1 "
          "1h/4h clears the 2h/8h calendar ceilings, 5% credit clears the 3% floor, 25% cap "
          "clears the 10% floor, chronic failure + termination right both present, 30-day "
          "claim deadline clears the 15-day floor.",
))

# ---------------------------------------------------------------------------
# Uptime percentages.
# ---------------------------------------------------------------------------
for pct, cid in [(99.0, "99"), (99.9, "99-9"), (99.95, "99-95"), (99.99, "99-99")]:
    CASES.append(case(
        f"uptime-{cid}-01", ["uptime", "percentage"],
        f"Service Levels. Provider commits to {pct}% uptime, measured monthly.",
        "ACCEPT", policy_overrides={"minimum_acceptable_uptime_percent": pct - 0.5 if pct > 99.0 else 98.0},
        notes=f"{pct}% clears a floor set half a point below it.",
    ))
CASES.append(case(
    "uptime-below-floor-01", ["uptime", "gap"],
    "Service Levels. Provider commits to 99.5% uptime, measured monthly.",
    "NEGOTIATE", policy_overrides={"minimum_acceptable_uptime_percent": 99.9},
    notes="99.5% is below the 99.9% policy floor -- NEGOTIATE (availability is a floor, "
          "violation is actual < policy value).",
))
CASES.append(case(
    "uptime-missing-01", ["uptime", "gap"],
    "Service Levels. P1 | 1 hour | 4 hours.",
    "NEGOTIATE", policy_overrides={"minimum_acceptable_uptime_percent": 99.9},
    notes="No uptime percentage stated at all despite a severity table -- policy configures a "
          "floor, silence is a gap not automatic satisfaction.",
))
CASES.append(case(
    "uptime-conflict-01", ["uptime", "conflict"],
    "Service Levels. Availability shall be 99.9% uptime, measured monthly. Notwithstanding the "
    "foregoing, in Section 14.4, availability shall instead be 99.5% uptime, measured monthly.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Two different uptime percentages stated for the same commitment -- genuine conflict.",
))

# ---------------------------------------------------------------------------
# Measurement period.
# ---------------------------------------------------------------------------
CASES.append(case(
    "period-monthly-01", ["measurement_period"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly.",
    "ACCEPT", policy_overrides={},
    notes="No policy dimension targets measurement_period directly (presence-only fact); ACCEPT.",
))
CASES.append(case(
    "period-quarterly-01", ["measurement_period"],
    "Service Levels. Provider commits to 99.9% uptime, measured quarterly.",
    "ACCEPT", policy_overrides={},
))
CASES.append(case(
    "period-annual-01", ["measurement_period"],
    "Service Levels. Provider commits to 99.9% uptime, measured annually.",
    "ACCEPT", policy_overrides={},
))

# ---------------------------------------------------------------------------
# Maintenance exclusions.
# ---------------------------------------------------------------------------
CASES.append(case(
    "exclusion-scheduled-permitted-01", ["exclusion", "scheduled_maintenance"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly, excluding scheduled maintenance.",
    "ACCEPT", policy_overrides={"permitted_maintenance_exclusions_json": ["scheduled_maintenance"]},
    notes="Scheduled maintenance exclusion is in the permitted list -- ACCEPT.",
))
CASES.append(case(
    "exclusion-emergency-not-permitted-01", ["exclusion", "emergency_maintenance", "gap"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly, excluding scheduled and emergency maintenance.",
    "NEGOTIATE", policy_overrides={"permitted_maintenance_exclusions_json": ["scheduled_maintenance"]},
    notes="Emergency maintenance is excluded by the contract but not in the policy's permitted list -- NEGOTIATE.",
))
CASES.append(case(
    "exclusion-customer-caused-01", ["exclusion", "customer_caused"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly, excluding downtime caused by Customer's acts or omissions.",
    "ACCEPT", policy_overrides={"permitted_maintenance_exclusions_json": ["customer_caused"]},
))
CASES.append(case(
    "exclusion-force-majeure-01", ["exclusion", "force_majeure"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly, excluding force majeure events.",
    "ACCEPT", policy_overrides={"permitted_maintenance_exclusions_json": ["force_majeure"]},
))

# ---------------------------------------------------------------------------
# Measurement methodology.
# ---------------------------------------------------------------------------
CASES.append(case(
    "methodology-stated-01", ["methodology"],
    "Service Levels. Availability shall be measured at the network edge and calculated as follows: total minutes in the period minus excluded downtime, divided by total minutes.",
    "ACCEPT", policy_overrides={},
    notes="Presence-only fact, no dedicated policy field -- ACCEPT.",
))

# ---------------------------------------------------------------------------
# Severity taxonomy variants.
# ---------------------------------------------------------------------------
CASES.append(case(
    "severity-p-labels-01", ["severity", "p_labels"],
    "Service Levels. P1 | 1 hour | 4 hours. P2 | 4 hours | 8 hours. P3 | 1 business day | 3 business days.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 2.0, "p1_response_basis": "calendar"},
    notes="P1/P2/P3 table-row labels normalize directly (P1_CRITICAL etc.); P1 1h clears the 2h ceiling.",
))
CASES.append(case(
    "severity-sev-labels-01", ["severity", "sev_labels"],
    "Service Levels. Sev 1 issues: response 30 minutes, restoration 2 hours. Sev 2 issues: response 2 hours, restoration 8 hours.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 1.0, "p1_response_basis": "calendar"},
    notes="'Sev 1'/'Sev 2' normalize to P1_CRITICAL/P2_HIGH; 30 minutes (0.5h) clears the 1h ceiling.",
))
CASES.append(case(
    "severity-priority-labels-01", ["severity", "priority_labels"],
    "Service Levels. Priority 1 issues: response 1 hour, restoration 4 hours.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 2.0, "p1_response_basis": "calendar"},
    notes="'Priority 1' normalizes to P1_CRITICAL.",
))
CASES.append(case(
    "severity-word-labels-01", ["severity", "word_labels"],
    "Service Levels. Critical: response 30 minutes, restoration 2 hours. High: response 2 hours, restoration 8 hours. Medium: response 1 business day, restoration 3 business days. Low: response 2 business days, restoration 5 business days.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 1.0, "p1_response_basis": "calendar"},
    notes="Critical/High/Medium/Low normalize to P1_CRITICAL-P4_LOW respectively.",
))
CASES.append(case(
    "severity-ambiguous-01", ["severity", "ambiguous"],
    "Service Levels. Sev 5 issues: response 1 hour, restoration 4 hours.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="'Sev 5' does not normalize to any of the four canonical levels -- ambiguous taxonomy, REQUIRES_REVIEW rather than a guess.",
))

# ---------------------------------------------------------------------------
# Response vs. restoration same-row disambiguation.
# ---------------------------------------------------------------------------
CASES.append(case(
    "response-restoration-table-row-01", ["response_restoration", "table"],
    "Service Levels. P1 | 1 hour | 4 hours.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 2.0, "p1_response_basis": "calendar",
                                 "p1_max_restoration_hours": 8.0, "p1_restoration_basis": "calendar"},
    notes="Table row: response=1h (col 2), restoration=4h (col 3) -- disambiguated by explicit named captures in one match, not a shared search.",
))
CASES.append(case(
    "response-restoration-trailing-label-01", ["response_restoration", "prose"],
    "Service Levels. P1 issues shall have a 1 hour response and a 4 hour restoration.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 2.0, "p1_response_basis": "calendar",
                                 "p1_max_restoration_hours": 8.0, "p1_restoration_basis": "calendar"},
    notes="Trailing-label prose form: 'N hour response ... M hour restoration'.",
))
CASES.append(case(
    "response-restoration-leading-label-01", ["response_restoration", "prose"],
    "Service Levels. For P1 issues: response time of 1 hour, restoration time of 4 hours.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 2.0, "p1_response_basis": "calendar",
                                 "p1_max_restoration_hours": 8.0, "p1_restoration_basis": "calendar"},
    notes="Leading-label prose form: 'response time of N hour, restoration time of M hour'.",
))
CASES.append(case(
    "response-only-no-restoration-01", ["response_restoration", "partial"],
    "Service Levels. P3 issues: response time of 1 business day.",
    "NEGOTIATE", policy_overrides={"p3_max_restoration_hours": 24.0, "p3_restoration_basis": "calendar"},
    notes="Only response is stated; policy configures a restoration ceiling that has nothing to compare against -- NEGOTIATE (target exists but restoration_hours is None).",
))
CASES.append(case(
    "restoration-only-no-response-01", ["response_restoration", "partial"],
    "Service Levels. P3 issues: restoration time of 3 business days.",
    "NEGOTIATE", policy_overrides={"p3_max_response_hours": 24.0, "p3_response_basis": "calendar"},
    notes="Only restoration is stated; policy configures a response ceiling with nothing to compare -- NEGOTIATE.",
))

# ---------------------------------------------------------------------------
# Minutes / hours / days conversions.
# ---------------------------------------------------------------------------
CASES.append(case(
    "conversion-minutes-01", ["conversion", "minutes"],
    "Service Levels. P1 | 15 minutes | 2 hours.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 1.0, "p1_response_basis": "calendar"},
    notes="15 minutes = 0.25 hours (pure arithmetic, basis-agnostic) -- clears the 1h ceiling.",
))
CASES.append(case(
    "conversion-calendar-days-01", ["conversion", "calendar_days"],
    "Service Levels. P4 | 2 calendar days | 5 calendar days.",
    "ACCEPT", policy_overrides={"p4_max_response_hours": 72.0, "p4_response_basis": "calendar"},
    notes="2 calendar days = 48 hours (safe pure-calendar conversion, x24) -- clears the 72h ceiling.",
))
CASES.append(case(
    "conversion-business-days-unconvertible-01", ["conversion", "business_days"],
    "Service Levels. P3 | 1 business day | 3 business days.",
    "REQUIRES_REVIEW", policy_overrides={"p3_max_response_hours": 24.0, "p3_response_basis": "calendar"},
    notes="1 business day has no safe conversion to hours (no assumed business-day length) -- "
          "policy configures a response ceiling for P3, so the incomparability is an actionable "
          "REQUIRES_REVIEW, not silently skipped.",
))
CASES.append(case(
    "conversion-business-days-no-policy-01", ["conversion", "business_days"],
    "Service Levels. P3 | 1 business day | 3 business days.",
    "ACCEPT", policy_overrides={},
    notes="Same unconvertible business-day value, but no policy ceiling is configured for P3 at "
          "all -- the incomparability never becomes actionable, ACCEPT.",
))

# ---------------------------------------------------------------------------
# Calendar vs. business hours (basis matching).
# ---------------------------------------------------------------------------
CASES.append(case(
    "basis-match-calendar-01", ["basis", "calendar"],
    "Service Levels. P1 | 1 calendar hour | 4 calendar hours.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 2.0, "p1_response_basis": "calendar"},
    notes="Contract states calendar hours explicitly; policy ceiling is also calendar-basis -- same basis, comparable.",
))
CASES.append(case(
    "basis-match-business-01", ["basis", "business"],
    "Service Levels. P1 | 1 business hour | 4 business hours.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 2.0, "p1_response_basis": "business"},
    notes="Contract states business hours; policy ceiling is ALSO configured as business-basis -- same basis, comparable directly (business hours are not converted, just compared as stated numbers when both sides agree on basis).",
))
CASES.append(case(
    "basis-mismatch-01", ["basis", "mismatch"],
    "Service Levels. P1 | 1 business hour | 4 business hours.",
    "REQUIRES_REVIEW", policy_overrides={"p1_max_response_hours": 2.0, "p1_response_basis": "calendar"},
    notes="Contract states business-hours P1 response; policy ceiling is calendar-basis -- "
          "cross-basis comparison, must abstain per decision 2, never silently compared.",
))
CASES.append(case(
    "basis-not-stated-default-calendar-01", ["basis", "default"],
    "Service Levels. P1 | 1 hour | 4 hours.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 2.0, "p1_response_basis": "calendar"},
    notes="Bare 'hour' with no qualifier defaults to calendar basis -- matches a calendar-basis policy ceiling.",
))

# ---------------------------------------------------------------------------
# Support hours.
# ---------------------------------------------------------------------------
CASES.append(case(
    "support-24x7-01", ["support_hours"],
    "Service Levels. Support is available 24x7 for all Severity levels.",
    "ACCEPT", policy_overrides={"required_support_hours": "24x7"},
))
CASES.append(case(
    "support-business-hours-01", ["support_hours"],
    "Service Levels. Support is available during business hours only.",
    "ACCEPT", policy_overrides={"required_support_hours": "business_hours"},
))
CASES.append(case(
    "support-mismatch-01", ["support_hours", "gap"],
    "Service Levels. Support is available during business hours only.",
    "NEGOTIATE", policy_overrides={"required_support_hours": "24x7"},
    notes="Contract states business-hours-only support; policy requires 24x7 -- NEGOTIATE.",
))
CASES.append(case(
    "support-conflict-01", ["support_hours", "conflict"],
    "Service Levels. Support is available 24x7. Notwithstanding the foregoing, support for standard issues is available during business hours only.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Both 24x7 and business-hours-only support tokens found -- genuine conflict.",
))

# ---------------------------------------------------------------------------
# Conflicting SLA tables.
# ---------------------------------------------------------------------------
CASES.append(case(
    "conflicting-table-01", ["conflict", "severity_table"],
    "Service Levels. P1 | 1 hour | 4 hours. Notwithstanding the foregoing, in Exhibit C, P1 shall instead have a response time of 2 hours and a restoration time of 8 hours.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Two different P1 response/restoration value sets stated in the document -- conflict.",
))

# ---------------------------------------------------------------------------
# Service-credit formulas.
# ---------------------------------------------------------------------------
CASES.append(case(
    "credit-percent-of-monthly-fees-01", ["credit", "percentage"],
    "Service Levels. If Provider fails to meet the Service Level, Customer shall receive a service credit equal to 5% of the monthly fees.",
    "ACCEPT", policy_overrides={"minimum_credit_percent_of_fees": 3.0},
    notes="5% clears the 3% floor.",
))
CASES.append(case(
    "credit-below-floor-01", ["credit", "gap"],
    "Service Levels. If Provider fails to meet the Service Level, Customer shall receive a service credit equal to 1% of the monthly fees.",
    "NEGOTIATE", policy_overrides={"minimum_credit_percent_of_fees": 3.0},
    notes="1% is below the 3% policy floor -- NEGOTIATE.",
))
CASES.append(case(
    "credit-trigger-01", ["credit", "trigger"],
    "Service Levels. If the availability falls below the committed Service Level, Customer shall be entitled to a service credit equal to 5% of the monthly fees.",
    "ACCEPT", policy_overrides={},
    notes="Credit trigger presence-only fact -- ACCEPT.",
))
CASES.append(case(
    "credit-missing-01", ["credit", "gap"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly.",
    "NEGOTIATE", policy_overrides={"require_service_credits": True},
    notes="No service-credit language at all despite policy requiring one -- NEGOTIATE.",
))
CASES.append(case(
    "credit-cap-01", ["credit", "cap"],
    "Service Levels. Service credits shall be capped at 25% of monthly fees.",
    "ACCEPT", policy_overrides={"minimum_credit_cap_percent_of_fees": 10.0},
    notes="25% cap clears the 10% policy minimum -- higher cap is more protective (floor semantics).",
))
CASES.append(case(
    "credit-cap-below-floor-01", ["credit", "cap", "gap"],
    "Service Levels. Service credits shall be capped at 5% of monthly fees.",
    "NEGOTIATE", policy_overrides={"minimum_credit_cap_percent_of_fees": 10.0},
    notes="5% cap is below the 10% policy minimum -- too low a cap is the unfavorable direction, NEGOTIATE.",
))
CASES.append(case(
    "credit-cumulative-01", ["credit", "cumulative"],
    "Service Levels. Customer shall receive a service credit of 5% for the first breach in a "
    "calendar quarter, 10% for the second breach, and 15% for any subsequent breach, subject to "
    "a cumulative cap of 25% of quarterly fees.",
    "ACCEPT", policy_overrides={},
    notes="Cumulative/tiered schedule presence-only fact -- ACCEPT, detect-don't-over-parse.",
))
CASES.append(case(
    "credit-conflict-01", ["credit", "conflict"],
    "Service Levels. Customer shall receive a service credit equal to 5% of the monthly fees. "
    "Notwithstanding the foregoing, in Section 14.6, the service credit shall instead be 10% of "
    "the monthly fees.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Two different credit percentages stated -- conflict.",
))

# ---------------------------------------------------------------------------
# Claim submission deadline.
# ---------------------------------------------------------------------------
CASES.append(case(
    "claim-deadline-present-01", ["claim_deadline"],
    "Service Levels. Claims for service credit must be submitted within 30 days of the qualifying event.",
    "ACCEPT", policy_overrides={"minimum_claim_submission_days": 15.0},
    notes="30 days clears the 15-day floor.",
))
CASES.append(case(
    "claim-deadline-below-floor-01", ["claim_deadline", "gap"],
    "Service Levels. Claims for service credit must be submitted within 5 days of the qualifying event.",
    "NEGOTIATE", policy_overrides={"minimum_claim_submission_days": 15.0},
    notes="5 days is below the 15-day policy floor -- too short a window, NEGOTIATE.",
))
CASES.append(case(
    "claim-deadline-missing-01", ["claim_deadline", "gap"],
    "Service Levels. Customer shall receive a service credit equal to 5% of the monthly fees.",
    "NEGOTIATE", policy_overrides={"minimum_claim_submission_days": 15.0},
    notes="No claim-submission deadline stated at all -- NEGOTIATE.",
))

# ---------------------------------------------------------------------------
# Chronic failure.
# ---------------------------------------------------------------------------
CASES.append(case(
    "chronic-failure-defined-01", ["chronic_failure"],
    "Service Levels. Chronic failure is defined as three consecutive months of Severity 1 breach.",
    "ACCEPT", policy_overrides={"require_chronic_failure_remedy": True},
))
CASES.append(case(
    "chronic-failure-missing-01", ["chronic_failure", "gap"],
    "Service Levels. Customer shall receive a service credit equal to 5% of the monthly fees.",
    "NEGOTIATE", policy_overrides={"require_chronic_failure_remedy": True},
    notes="No chronic-failure provision at all despite policy requiring one -- NEGOTIATE.",
))

# ---------------------------------------------------------------------------
# Termination triggers.
# ---------------------------------------------------------------------------
CASES.append(case(
    "termination-chronic-01", ["termination"],
    "Service Levels. In the case of chronic failure, defined as three consecutive months of "
    "Severity 1 breach, Customer shall have the right to terminate this Agreement.",
    "ACCEPT", policy_overrides={"require_termination_right_for_chronic_failure": True},
))
CASES.append(case(
    "termination-missing-01", ["termination", "gap"],
    "Service Levels. Chronic failure is defined as three consecutive months of Severity 1 breach. Customer shall receive additional service credits.",
    "NEGOTIATE", policy_overrides={"require_termination_right_for_chronic_failure": True},
    notes="Chronic failure defined, but no termination right attached to it -- only credits -- NEGOTIATE.",
))

# ---------------------------------------------------------------------------
# Exclusive remedy.
# ---------------------------------------------------------------------------
CASES.append(case(
    "exclusive-remedy-prohibited-01", ["remedy", "exclusive", "prohibited"],
    "Service Levels. Customer's sole and exclusive remedy for any failure to meet the Service "
    "Levels shall be the service credits described in this Section. Provider commits to 99.9% uptime.",
    "ESCALATE", policy_overrides={"prohibit_service_credits_as_exclusive_remedy": True},
    notes="Exclusive-remedy language present, policy prohibits it -- ESCALATE.",
))
CASES.append(case(
    "exclusive-remedy-allowed-01", ["remedy", "exclusive"],
    "Service Levels. Customer's sole and exclusive remedy for any failure to meet the Service "
    "Levels shall be the service credits described in this Section. Provider commits to 99.9% uptime.",
    "ACCEPT", policy_overrides={},
    notes="Exclusive-remedy language present but not prohibited by policy -- ACCEPT.",
))

# ---------------------------------------------------------------------------
# Cross-referenced schedules.
# ---------------------------------------------------------------------------
CASES.append(case(
    "crossref-nothing-else-01", ["cross_reference"],
    "Service Levels. Service levels are as set forth in the applicable Service Level Schedule.",
    "ESCALATE", policy_overrides={},
    notes="Material SLA terms delegated to an unresolved Schedule with nothing else established in the visible text -- ESCALATE.",
))
CASES.append(case(
    "crossref-supplementing-01", ["cross_reference"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly. Additional service "
    "level details for specific Deliverables are as set forth in the applicable Service Level Schedule.",
    "ACCEPT", policy_overrides={},
    notes="Uptime IS independently established; the Schedule reference only supplements it -- the cross-reference gate does not fire since something else was established.",
))

# ---------------------------------------------------------------------------
# Amendments.
# ---------------------------------------------------------------------------
CASES.append(case(
    "amendment-consistent-01", ["amendment"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly. This Agreement is "
    "hereby amended to restate that the availability commitment referenced above is 99.9% "
    "uptime, measured monthly.",
    "ACCEPT", policy_overrides={"minimum_acceptable_uptime_percent": 99.5},
    notes="Amendment restates the identical value -- no conflict, single accumulated value, clears the floor.",
))
CASES.append(case(
    "amendment-changes-uptime-01", ["amendment", "conflict"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly. This Agreement is "
    "hereby amended to restate that the availability commitment referenced above shall instead "
    "be 99.5% uptime, measured monthly.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Amendment changes the uptime value -- no amendment-aware 'last mention wins' logic in "
          "this adapter (matches every adapter except liability per the ten-adapter review) -- "
          "generic conflict machinery correctly and safely routes to REQUIRES_REVIEW.",
))

# ---------------------------------------------------------------------------
# Malformed / no SLA.
# ---------------------------------------------------------------------------
CASES.append(case(
    "malformed-placeholder-01", ["malformed"],
    "14. [SERVICE LEVELS -- TBD, SEE ATTACHED EXHIBIT]",
    "NOT_APPLICABLE", policy_overrides={},
    notes="Placeholder/bracketed drafting-note text, no structured signal -- NOT_APPLICABLE.",
))
CASES.append(case(
    "malformed-garbled-01", ["malformed"],
    "Service Level Service Level the the SLA shall shall be be applicable applicable under this this Section 14 hereof notwithstanding.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="Garbled/repeated-word drafting, anchor fires but no coherent structure found -- NOT_APPLICABLE.",
))
CASES.append(case(
    "no-sla-01", ["not_applicable"],
    "This Agreement shall be governed by the laws of the State of Delaware.",
    "NOT_APPLICABLE", policy_overrides={"require_uptime_commitment": True},
    notes="No SLA-related anchor at all -- NOT_APPLICABLE.",
))
CASES.append(case(
    "no-sla-negation-01", ["not_applicable", "negation"],
    "This Agreement contains no service level commitments of any kind.",
    "NOT_APPLICABLE", policy_overrides={"require_uptime_commitment": True},
    notes="Explicit negation with no structured SLA content -- NOT_APPLICABLE.",
))

# ---------------------------------------------------------------------------
# Negative controls: cross-dimension numeric contamination.
# ---------------------------------------------------------------------------
CASES.append(case(
    "negative-control-p1-p2-phases-01", ["negative_control"],
    "The Project shall proceed in two phases. P1 shall commence upon execution of this "
    "Agreement, and P2 shall commence upon Customer's written approval of the P1 deliverables.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="'P1'/'P2' used as project-phase labels, not severity levels -- no SLA anchor at all, "
          "and even if scanned, no response/restoration language nearby -- NOT_APPLICABLE.",
))
CASES.append(case(
    "negative-control-equity-percent-01", ["negative_control"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly. Separately, upon the "
    "Closing, Buyer shall own 99.5% of the outstanding shares of the Company.",
    "ACCEPT", policy_overrides={"minimum_acceptable_uptime_percent": 99.5},
    notes="An unrelated 99.5% equity-ownership percentage appears after the uptime commitment; "
          "the uptime match is anchored on 'uptime'/'availability' via a combined bidirectional "
          "regex, not a broad percent scan, so the equity percentage is never picked up as a "
          "second, conflicting uptime value -- uptime stays 99.9%, clears the floor, ACCEPT.",
))
CASES.append(case(
    "negative-control-price-increase-percent-01", ["negative_control"],
    "Service Levels and Fees. Fees may increase by up to 5% per year upon 60 days notice. "
    "Availability shall be measured monthly and Provider commits to 99.95% uptime.",
    "ACCEPT", policy_overrides={"minimum_acceptable_uptime_percent": 99.9},
    notes="An unrelated 5% price-increase figure precedes the uptime commitment in the same "
          "section -- forward-only local-window scoping from the uptime/availability anchor "
          "never reaches backward to the earlier price-increase percentage -- uptime resolves "
          "cleanly to 99.95%.",
))
CASES.append(case(
    "negative-control-critical-adjective-01", ["negative_control"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly. This is a critical "
    "component of the parties' overall commercial relationship. P1 | 1 hour | 4 hours.",
    "ACCEPT", policy_overrides={"p1_max_response_hours": 2.0, "p1_response_basis": "calendar"},
    notes="'critical' used as an ordinary adjective, not a severity label -- the bare-severity-word "
          "regex requires immediate label-shaped punctuation ('Critical:' or 'Critical -'), which "
          "'a critical component of' does not have -- P1 still resolves correctly from the table row.",
))
CASES.append(case(
    "negative-control-guarantee-unrelated-01", ["negative_control"],
    "We guarantee a response within 24 hours for all customer support inquiries submitted "
    "through the general contact form, separate from the Service Levels described in Section 14.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="'guarantee'/'response within 24 hours' used in an ordinary customer-support sense with "
          "no SLA/uptime/availability anchor present at all -- NOT_APPLICABLE.",
))
CASES.append(case(
    "negative-control-response-time-payment-context-01", ["negative_control"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly. Separately, Customer "
    "shall respond to any invoice dispute within 15 days of receipt.",
    "ACCEPT", policy_overrides={},
    notes="A 15-day 'response' window in a payment-dispute sense, textually distinct from SLA "
          "severity response times -- no severity label anchors it, so it is never captured as a "
          "severity response time at all.",
))

# ---------------------------------------------------------------------------
# Multiple severity levels, mixed units, realistic table.
# ---------------------------------------------------------------------------
CASES.append(case(
    "full-four-tier-table-01", ["severity", "full_table"],
    "Service Levels. P1 | 1 hour | 4 hours. P2 | 4 hours | 8 hours. P3 | 1 business day | 3 "
    "business days. P4 | 2 business days | 5 business days.",
    "ACCEPT", policy_overrides={
        "p1_max_response_hours": 2.0, "p1_response_basis": "calendar",
        "p2_max_response_hours": 8.0, "p2_response_basis": "calendar",
    },
    notes="Full four-tier table; only P1/P2 policy ceilings configured (calendar basis) match "
          "the P1/P2 calendar-hour values; P3/P4's business-day values are never compared since "
          "no P3/P4 policy ceiling exists.",
))

# ---------------------------------------------------------------------------
# Additional coverage to round out the corpus.
# ---------------------------------------------------------------------------
CASES.append(case(
    "severity-response-exceeds-ceiling-01", ["severity", "gap"],
    "Service Levels. P1 | 3 hours | 8 hours.",
    "NEGOTIATE", policy_overrides={"p1_max_response_hours": 1.0, "p1_response_basis": "calendar"},
    notes="3 hours exceeds the 1-hour policy ceiling -- NEGOTIATE (response is a ceiling, "
          "violation is actual > policy value).",
))
CASES.append(case(
    "severity-restoration-exceeds-ceiling-01", ["severity", "gap"],
    "Service Levels. P1 | 1 hour | 12 hours.",
    "NEGOTIATE", policy_overrides={"p1_max_restoration_hours": 4.0, "p1_restoration_basis": "calendar"},
    notes="12 hours exceeds the 4-hour restoration ceiling -- NEGOTIATE.",
))
CASES.append(case(
    "severity-tiers-required-missing-01", ["severity", "activation_shape"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly.",
    "NEGOTIATE", policy_overrides={"require_severity_tiers": True},
    notes="Policy requires severity-tiered commitments, but no severity table was found at all -- NEGOTIATE.",
))
CASES.append(case(
    "credit-basis-total-fees-01", ["credit", "basis"],
    "Service Levels. Customer shall receive a service credit equal to 10% of the total fees paid in the affected period.",
    "ACCEPT", policy_overrides={"minimum_credit_percent_of_fees": 5.0},
    notes="Credit basis is 'total fees' rather than 'monthly fees' -- percentage still extracted and compared independent of basis wording.",
))
CASES.append(case(
    "p3-response-only-basis-business-day-with-ceiling-mismatch-01", ["conversion", "basis"],
    "Service Levels. P3 | 1 business day | 3 business days.",
    "REQUIRES_REVIEW", policy_overrides={"p3_max_response_hours": 24.0, "p3_response_basis": "calendar",
                                          "p3_max_restoration_hours": 72.0, "p3_restoration_basis": "calendar"},
    notes="Both response and restoration stated as unconvertible business days, both policy "
          "ceilings configured -- two separate unresolved facts, still a single REQUIRES_REVIEW state.",
))
CASES.append(case(
    "multiple-availability-commitments-conflict-01", ["conflict", "availability"],
    "Service Levels. Provider commits to 99.9% uptime. In a separate section, Provider commits "
    "to 99.5% uptime for the same Services.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Two different, non-amendment-labeled uptime commitments for the same services -- "
          "conflict, same mechanism as uptime-conflict-01 but without 'notwithstanding' framing.",
))
CASES.append(case(
    "credit-schedule-conflict-01", ["conflict", "credit_schedule"],
    "Service Levels. Customer shall receive a service credit capped at 25% of monthly fees. "
    "Elsewhere in this Agreement, the service credit cap is stated as 15% of monthly fees.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Two different credit cap values stated -- conflict.",
))
CASES.append(case(
    "negative-control-unrelated-time-period-01", ["negative_control"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly. This Agreement shall "
    "remain in effect for an initial term of 3 years.",
    "ACCEPT", policy_overrides={"minimum_acceptable_uptime_percent": 99.5},
    notes="A 3-year initial term is an unrelated time period with no severity label or response/"
          "restoration keyword nearby -- never captured as a severity target.",
))
CASES.append(case(
    "negative-control-decimal-percent-unrelated-01", ["negative_control"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly. Late payments accrue "
    "interest at a rate of 1.5% per month.",
    "ACCEPT", policy_overrides={"minimum_acceptable_uptime_percent": 99.5},
    notes="An unrelated 1.5% late-fee rate appears after the uptime commitment -- the uptime "
          "match is anchored on the combined bidirectional uptime/availability regex, not a bare "
          "percent scan, so the late-fee percentage is never picked up as a conflicting uptime value.",
))

# ---------------------------------------------------------------------------
# Explicit negation, mixed-unit tables, and rounding out to corpus size.
# ---------------------------------------------------------------------------
CASES.append(case(
    "negation-no-severity-target-01", ["negation"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly. No response or "
    "restoration time commitments are made for Severity 4 issues.",
    "ACCEPT", policy_overrides={},
    notes="Explicit negation of a P4 commitment with no policy dimension requiring one -- ACCEPT; "
          "no P4 SeverityTarget is created since no response/restoration language follows.",
))
CASES.append(case(
    "negation-no-credit-remedy-01", ["negation"],
    "Service Levels. Provider commits to 99.9% uptime, measured monthly. No service credits or "
    "other financial remedies are available for any failure to meet the Service Levels.",
    "NEGOTIATE", policy_overrides={"require_service_credits": True},
    notes="Explicit negation of any credit remedy -- no 'credit' anchor establishes "
          "service_credit_present, so the require_service_credits gate correctly fires NEGOTIATE.",
))
CASES.append(case(
    "mixed-units-same-table-01", ["conversion", "mixed_units"],
    "Service Levels. P1 | 30 minutes | 2 hours. P2 | 2 hours | 1 calendar day.",
    "ACCEPT", policy_overrides={
        "p1_max_response_hours": 1.0, "p1_response_basis": "calendar",
        "p2_max_restoration_hours": 30.0, "p2_restoration_basis": "calendar",
    },
    notes="P1 response in minutes (0.5h) and P2 restoration in calendar days (24h) both convert "
          "via pure arithmetic and both clear their respective ceilings within one table.",
))
CASES.append(case(
    "malformed-ocr-mangled-01", ["malformed"],
    "S3rv1c3 L3v3ls. Pr0v1d3r c0mm1ts t0 99.9% upt1m3.",
    "NOT_APPLICABLE", policy_overrides={},
    notes="OCR-mangled text with substituted characters -- no recognizable anchor or structure "
          "matches at all -- NOT_APPLICABLE (this adapter does not attempt OCR-error correction).",
))
CASES.append(case(
    "severity-required-support-hours-per-tier-01", ["support_hours", "severity"],
    "Service Levels. P1 issues receive 24x7 support. P3 issues receive business-hours-only support.",
    "REQUIRES_REVIEW", policy_overrides={},
    notes="Both 24x7 and business-hours-only support tokens are present in the same document "
          "(per-tier, not conflicting in the drafter's intent, but this adapter's presence-only "
          "required_support_hours fact cannot distinguish per-tier support commitments from a "
          "genuine conflict) -- correctly and safely routes to REQUIRES_REVIEW rather than "
          "picking one arbitrarily; a future adapter revision could model support hours per-tier "
          "the same way response/restoration are modeled, but that is out of scope for this build.",
))


