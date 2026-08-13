"""
Labeled adversarial corpus for the Payment Terms / Commercial Terms
policy engine benchmark (see benchmarks/run_payment_terms_benchmark.py).
Adapter #10 — fourth adapter added after the original six.

Labels here were written from the policy semantics and the drafting
pattern alone, reasoning directly from payment_terms_policy_engine.py's
evaluate_payment_policy logic, never by running the implementation and
copying whatever it happened to output.

DEFAULT_POLICY requires NOTHING by default (every require_* field is
False, every numeric minimum/maximum is None) — the corrected
convention established with insurance_corpus.py after benchmarking
ip_ownership_corpus.py revealed that an always-on, MUST_REDLINE-severity
default requirement silently dominated dozens of single-dimension test
cases that never addressed it. Each case here explicitly turns on only
the dimension(s) it means to test via policy_overrides.

Several cases are deliberate NEGATIVE CONTROLS: text containing a
numbered period, percentage, or currency mention that belongs to an
unrelated clause (termination notice, price-increase cap, a schedule
elsewhere) and must NOT be picked up as a net-payment-period, late-fee
rate, or currency fact — several of these were caught as genuine
extraction bugs during benchmarking and are recorded in the module
docstring of payment_terms_policy_engine.py.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "sell_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: Net 30 from receipt of invoice, undisputed amounts remain "
                      "payable during any dispute, no set-off, 1.5%/month late fee capped at statutory "
                      "maximum, price increases limited to 5%/year on 60 days' notice, pre-approved "
                      "expenses with receipts, counterparty bears its own taxes, payment in USD.",
    "require_counterparty_is_payor": False,
    "preferred_net_days": None, "acceptable_max_net_days": None,
    "required_payment_trigger": None,
    "require_undisputed_amounts_still_payable": False,
    "prohibit_disputed_amount_withholding": False,
    "minimum_dispute_notice_days": None,
    "prohibit_set_off": False,
    "maximum_late_interest_rate_percent": None,
    "prohibit_unilateral_price_increase": False,
    "maximum_price_increase_percent": None,
    "minimum_price_increase_notice_days": None,
    "require_expense_preapproval": False,
    "require_tax_responsibility_counterparty": False,
    "required_currency": None,
    "require_refund_entitlement": False,
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
    "11. Payment Terms. Customer shall pay Vendor all undisputed amounts within Net 30 days of "
    "receipt of a valid invoice. Vendor shall invoice Customer monthly. Customer may dispute any "
    "invoice in good faith within 15 days of receipt by providing written notice; undisputed "
    "amounts shall continue to be paid notwithstanding any such dispute, and Customer shall not "
    "withhold payment of disputed amounts pending resolution. Amounts not paid when due shall "
    "accrue interest at the rate of 1.5% per month, subject to a 10-day grace period. Vendor shall "
    "have no right of set-off against amounts owed to Customer. Prices are fixed for the Initial "
    "Term; Vendor may increase prices thereafter upon 60 days' prior written notice, provided that "
    "any such increase shall not exceed 5% per year and shall be linked to the Consumer Price "
    "Index. Customer shall reimburse Vendor for reasonable pre-approved travel expenses supported "
    "by receipts. Customer shall be responsible for all applicable sales, use, and value-added "
    "taxes. All payments shall be made in United States Dollars. Vendor shall provide refunds for "
    "any pre-paid but undelivered Services."
)
FULLY_COMPLIANT_POLICY = {
    "require_counterparty_is_payor": True,
    "acceptable_max_net_days": 30.0,
    "require_undisputed_amounts_still_payable": True,
    "prohibit_disputed_amount_withholding": True,
    "minimum_dispute_notice_days": 10.0,
    "prohibit_set_off": True,
    "maximum_late_interest_rate_percent": 25.0,
    "maximum_price_increase_percent": 5.0,
    "minimum_price_increase_notice_days": 60.0,
    "require_expense_preapproval": True,
    "require_tax_responsibility_counterparty": True,
    "required_currency": "USD",
    "require_refund_entitlement": True,
}

CASES += [
    case("clean-01", ["clean_all"], FULLY_COMPLIANT_TEXT, "ACCEPT",
         policy_overrides=dict(FULLY_COMPLIANT_POLICY),
         notes="Every configured dimension satisfied at the preferred tier."),
]

# ---------------------------------------------------------------------------
# Net day variants.
# ---------------------------------------------------------------------------
CASES += [
    case("net-15", ["net_days", "clean"],
         "9. Payment Terms. Customer shall pay Vendor within Net 15 days of receipt of invoice.",
         "ACCEPT", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="Net 15 is within the acceptable maximum of 30."),
    case("net-30", ["net_days", "clean"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of invoice.",
         "ACCEPT", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="Net 30 exactly equals the acceptable maximum."),
    case("net-45", ["net_days", "above_maximum"],
         "9. Payment Terms. Customer shall pay Vendor within Net 45 days of receipt of invoice.",
         "NEGOTIATE", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="Net 45 exceeds the acceptable maximum of 30."),
    case("net-60", ["net_days", "above_maximum"],
         "9. Payment Terms. Customer shall pay Vendor within Net 60 days of receipt of invoice.",
         "NEGOTIATE", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="Net 60 exceeds the acceptable maximum of 30."),
    case("net-90", ["net_days", "above_maximum"],
         "9. Payment Terms. Customer shall pay Vendor within Net 90 days of receipt of invoice.",
         "NEGOTIATE", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="Net 90 exceeds the acceptable maximum of 30."),
    case("within-x-days-invoice", ["net_days", "within_x_days", "invoice_trigger"],
         "9. Payment Terms. Customer shall pay Vendor within 30 days of the date of the invoice.",
         "ACCEPT", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="'Within 30 days of the invoice' phrasing (not literal 'Net 30') still resolves to "
               "30 net days."),
    case("within-x-days-receipt", ["net_days", "within_x_days", "receipt_trigger"],
         "9. Payment Terms. Customer shall pay Vendor within 45 days of receipt of the "
         "Deliverables.",
         "NEGOTIATE", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="'Within 45 days of receipt of the Deliverables' exceeds the 30-day maximum."),
    case("net-days-missing", ["net_days", "missing"],
         "9. Payment Terms. Customer shall pay Vendor all invoiced amounts.",
         "NEGOTIATE", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="No payment period stated at all — policy requires one within the maximum."),
]

# ---------------------------------------------------------------------------
# Payment trigger: invoice-date vs receipt-date, acceptance, milestone.
# ---------------------------------------------------------------------------
CASES += [
    case("trigger-invoice", ["payment_trigger", "invoice"],
         "9. Payment Terms. Customer shall pay Vendor within 30 days of the date of the invoice.",
         "ACCEPT", policy_overrides={"required_payment_trigger": "invoice"},
         notes="Invoice-date trigger satisfies an invoice-trigger requirement."),
    case("trigger-receipt", ["payment_trigger", "receipt"],
         "9. Payment Terms. Customer shall pay Vendor within 30 days of receipt of the "
         "Deliverables.",
         "ACCEPT", policy_overrides={"required_payment_trigger": "receipt"},
         notes="Receipt-of-goods trigger satisfies a receipt-trigger requirement."),
    case("trigger-acceptance", ["payment_trigger", "acceptance"],
         "9. Payment Terms. Customer shall pay Vendor within 30 days following acceptance of "
         "the Deliverables.",
         "ACCEPT", policy_overrides={"required_payment_trigger": "acceptance"},
         notes="Acceptance trigger satisfies an acceptance-trigger requirement."),
    case("trigger-milestone", ["payment_trigger", "milestone"],
         "9. Payment Terms. Customer shall pay Vendor upon completion of each milestone as set "
         "forth in the Statement of Work.",
         "ACCEPT", policy_overrides={"required_payment_trigger": "milestone"},
         notes="Milestone payment trigger satisfies a milestone-trigger requirement."),
    case("trigger-mismatch", ["payment_trigger", "mismatch"],
         "9. Payment Terms. Customer shall pay Vendor within 30 days of the date of the invoice.",
         "NEGOTIATE", policy_overrides={"required_payment_trigger": "acceptance"},
         notes="Clause states an invoice trigger but policy requires acceptance."),
    case("trigger-conflict", ["payment_trigger", "conflict"],
         "9. Payment Terms. Customer shall pay Vendor within 30 days of the date of the "
         "invoice. Notwithstanding the foregoing, payment shall not be due until Customer's "
         "written acceptance of the Deliverables.",
         "REQUIRES_REVIEW",
         notes="Invoice-date and acceptance-based triggers are both stated for the same "
               "payment obligation — genuine conflict between invoice and acceptance "
               "provisions."),
]

# ---------------------------------------------------------------------------
# Prepayment / advance payment / milestone payment.
# ---------------------------------------------------------------------------
CASES += [
    case("prepayment-01", ["prepayment", "advance"],
         "9. Payment Terms. Customer shall pay Vendor 50% of the total fees as an advance "
         "payment prior to commencement of the Services.",
         "ACCEPT", notes="Prepayment/advance-payment presence extracted; not gated by a "
                          "dedicated policy toggle in this adapter."),
    case("milestone-01", ["milestone_payment"],
         "9. Payment Terms. Customer shall make milestone payments to Vendor upon completion "
         "of each milestone set forth in Exhibit A.",
         "ACCEPT", notes="Milestone-payment presence extracted; informational."),
]

# ---------------------------------------------------------------------------
# Conflicting payment periods.
# ---------------------------------------------------------------------------
CASES += [
    case("net-days-conflict-01", ["conflict", "net_days"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice. Notwithstanding the foregoing, Customer shall pay Vendor within Net 60 "
         "days of receipt of invoice.",
         "REQUIRES_REVIEW", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="Two different Net-day periods stated for the same payment obligation — "
               "genuine conflict, must abstain."),
]

# ---------------------------------------------------------------------------
# Disputed-invoice withholding / undisputed-payment continuation.
# ---------------------------------------------------------------------------
CASES += [
    case("dispute-01", ["dispute", "undisputed_continues"],
         "9. Payment Terms. Undisputed amounts shall continue to be paid notwithstanding any "
         "dispute raised by Customer in good faith.",
         "ACCEPT", policy_overrides={"require_undisputed_amounts_still_payable": True},
         notes="Undisputed-continuation commitment satisfied."),
    case("dispute-02", ["dispute", "undisputed_missing"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.",
         "NEGOTIATE", policy_overrides={"require_undisputed_amounts_still_payable": True},
         notes="No undisputed-continuation commitment stated — required by policy."),
    case("dispute-03", ["dispute", "withholding_permitted_prohibited"],
         "9. Payment Terms. Customer shall not withhold payment of disputed amounts pending "
         "resolution of any dispute.",
         "ACCEPT", policy_overrides={"prohibit_disputed_amount_withholding": True},
         notes="Explicit prohibition on withholding satisfies the policy prohibition."),
    case("dispute-04", ["dispute", "withholding_allowed"],
         "9. Payment Terms. Customer may withhold payment of the disputed amounts pending "
         "resolution of any good-faith dispute.",
         "MUST_REDLINE", policy_overrides={"prohibit_disputed_amount_withholding": True},
         notes="Clause expressly permits withholding disputed amounts, prohibited by policy."),
    case("dispute-05", ["dispute", "notice_period"],
         "9. Payment Terms. Customer may dispute any invoice within 15 days of receipt by "
         "providing written notice to Vendor.",
         "ACCEPT", policy_overrides={"minimum_dispute_notice_days": 10.0},
         notes="15-day dispute-notice period exceeds the 10-day minimum."),
    case("dispute-06", ["dispute", "notice_below_minimum"],
         "9. Payment Terms. Customer may dispute any invoice within 5 days of receipt by "
         "providing written notice to Vendor.",
         "NEGOTIATE", policy_overrides={"minimum_dispute_notice_days": 10.0},
         notes="5-day dispute-notice period is below the required 10-day minimum."),
]

# ---------------------------------------------------------------------------
# Late fees: monthly, annual, statutory maximum, grace periods.
# ---------------------------------------------------------------------------
CASES += [
    case("late-fee-monthly-01", ["late_fee", "monthly"],
         "9. Payment Terms. Amounts not paid when due shall accrue interest at the rate of "
         "1.5% per month.",
         "ACCEPT", policy_overrides={"maximum_late_interest_rate_percent": 25.0},
         notes="1.5%/month annualizes to 18%, within the 25% annual maximum."),
    case("late-fee-monthly-02", ["late_fee", "monthly", "above_maximum"],
         "9. Payment Terms. Amounts not paid when due shall accrue interest at the rate of "
         "3% per month.",
         "NEGOTIATE", policy_overrides={"maximum_late_interest_rate_percent": 25.0},
         notes="3%/month annualizes to 36%, exceeding the 25% annual maximum."),
    case("late-fee-annual-01", ["late_fee", "annual"],
         "9. Payment Terms. Amounts not paid when due shall accrue interest at the rate of "
         "18% per annum.",
         "ACCEPT", policy_overrides={"maximum_late_interest_rate_percent": 25.0},
         notes="18% annual is within the 25% annual maximum."),
    case("late-fee-annual-02", ["late_fee", "annual", "above_maximum"],
         "9. Payment Terms. Amounts not paid when due shall accrue interest at the rate of "
         "30% per annum.",
         "NEGOTIATE", policy_overrides={"maximum_late_interest_rate_percent": 25.0},
         notes="30% annual exceeds the 25% annual maximum."),
    case("late-fee-statutory-01", ["late_fee", "statutory_max"],
         "9. Payment Terms. Amounts not paid when due shall accrue interest at the lesser of "
         "1.5% per month or the maximum rate permitted by applicable law.",
         "ACCEPT", notes="Statutory-maximum reference extracted as an informational fact; no "
                          "policy dimension gates it directly, and the stated 1.5%/month "
                          "resolves normally (18% annualized) with no maximum configured "
                          "here."),
    case("grace-period-01", ["late_fee", "grace_period"],
         "9. Payment Terms. Amounts not paid when due shall accrue interest at the rate of "
         "1.5% per month, subject to a 10-day grace period.",
         "ACCEPT", notes="Grace period extracted as an informational fact (10 days); no "
                          "dedicated policy gate."),
    case("late-fee-missing", ["late_fee", "missing"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.",
         "NEGOTIATE", policy_overrides={"maximum_late_interest_rate_percent": 25.0},
         notes="No late-fee/interest provision stated at all, but policy configures a maximum "
               "rate — the same 'a configured ceiling implies the dimension must be "
               "addressed at all' rule data_security's breach-notification-hours check uses: "
               "silence is a gap, not a pass."),
]

# ---------------------------------------------------------------------------
# Set-off / deductions.
# ---------------------------------------------------------------------------
CASES += [
    case("setoff-prohibited-01", ["setoff", "prohibited"],
         "9. Payment Terms. Customer shall have no right of set-off against amounts owed to "
         "Vendor.",
         "ACCEPT", policy_overrides={"prohibit_set_off": True},
         notes="Explicit set-off prohibition satisfies the policy prohibition."),
    case("setoff-permitted-01", ["setoff", "permitted"],
         "9. Payment Terms. Customer shall have the right to set-off any amounts owed by "
         "Vendor against amounts payable to Vendor hereunder.",
         "MUST_REDLINE", policy_overrides={"prohibit_set_off": True},
         notes="Clause expressly grants a set-off right, prohibited by policy."),
    case("setoff-not-addressed-01", ["setoff", "not_required"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.",
         "ACCEPT", notes="Set-off never addressed; prohibition not configured, so nothing to "
                          "flag."),
    case("deduction-01", ["setoff", "unilateral_deduction"],
         "9. Payment Terms. Customer may unilaterally deduct amounts from any invoice without "
         "Vendor's prior written consent.",
         "ACCEPT", notes="Unilateral-deduction right extracted as an informational fact; no "
                          "dedicated policy gate in this adapter."),
]

# ---------------------------------------------------------------------------
# Pricing: unilateral increases, capped increases, CPI/index-linked,
# annual increase limits.
# ---------------------------------------------------------------------------
CASES += [
    case("price-unilateral-01", ["pricing", "unilateral_permitted"],
         "9. Payment Terms. Vendor may unilaterally increase prices at its sole discretion "
         "upon notice to Customer.",
         "MUST_REDLINE", policy_overrides={"prohibit_unilateral_price_increase": True},
         notes="Unilateral price-increase right, prohibited by policy."),
    case("price-unilateral-02", ["pricing", "unilateral_not_stated"],
         "9. Payment Terms. Vendor may increase prices upon 60 days' prior written notice, "
         "provided that any such increase shall not exceed 5% per year.",
         "ACCEPT", policy_overrides={"prohibit_unilateral_price_increase": True},
         notes="A capped, noticed increase right is not stated as unilateral/sole-discretion "
               "— does not trigger the unilateral-increase prohibition."),
    case("price-cap-01", ["pricing", "capped", "within_maximum"],
         "9. Payment Terms. Vendor may increase prices upon notice, provided that any such "
         "increase shall not exceed 5% per year.",
         "ACCEPT", policy_overrides={"maximum_price_increase_percent": 7.0},
         notes="5% cap is within the 7% policy maximum."),
    case("price-cap-02", ["pricing", "capped", "above_maximum"],
         "9. Payment Terms. Vendor may increase prices upon notice, provided that any such "
         "increase shall not exceed 10% per year.",
         "NEGOTIATE", policy_overrides={"maximum_price_increase_percent": 7.0},
         notes="10% cap exceeds the 7% policy maximum."),
    case("price-cap-missing-01", ["pricing", "right_no_cap"],
         "9. Payment Terms. Vendor may increase prices upon 60 days' prior written notice.",
         "NEGOTIATE", policy_overrides={"maximum_price_increase_percent": 7.0},
         notes="Price-increase right granted with no stated cap — policy requires one."),
    case("price-cpi-01", ["pricing", "cpi_linked"],
         "9. Payment Terms. Annual price increases shall be linked to the Consumer Price "
         "Index (CPI).",
         "ACCEPT", notes="CPI/index-linked increase presence extracted; informational."),
    case("price-notice-01", ["pricing", "notice_period"],
         "9. Payment Terms. Vendor may increase prices upon 60 days' prior written notice, "
         "provided that any such increase shall not exceed 5% per year.",
         "ACCEPT", policy_overrides={"minimum_price_increase_notice_days": 30.0},
         notes="60-day notice exceeds the 30-day minimum."),
    case("price-notice-02", ["pricing", "notice_below_minimum"],
         "9. Payment Terms. Vendor may increase prices upon 15 days' prior written notice, "
         "provided that any such increase shall not exceed 5% per year.",
         "NEGOTIATE", policy_overrides={"minimum_price_increase_notice_days": 30.0},
         notes="15-day notice is below the required 30-day minimum."),
    case("price-fixed-01", ["pricing", "fixed"],
         "9. Payment Terms. Prices shall be fixed for the Initial Term of this Agreement.",
         "ACCEPT", notes="Fixed-price commitment extracted as an informational fact."),
]

# ---------------------------------------------------------------------------
# Expenses: reimbursable, pre-approved, documentation.
# ---------------------------------------------------------------------------
CASES += [
    case("expense-01", ["expenses", "preapproval_present"],
         "9. Payment Terms. Customer shall reimburse Vendor for reasonable travel expenses, "
         "subject to Customer's prior written approval of such expenses.",
         "ACCEPT", policy_overrides={"require_expense_preapproval": True},
         notes="Pre-approval requirement satisfied."),
    case("expense-02", ["expenses", "preapproval_missing"],
         "9. Payment Terms. Customer shall reimburse Vendor for reasonable travel expenses.",
         "NEGOTIATE", policy_overrides={"require_expense_preapproval": True},
         notes="No pre-approval requirement stated — required by policy."),
    case("expense-03", ["expenses", "documentation"],
         "9. Payment Terms. Customer shall reimburse Vendor for reasonable expenses supported "
         "by receipts and documentation.",
         "ACCEPT", notes="Documentation requirement extracted as an informational fact."),
    case("expense-04", ["expenses", "not_reimbursable"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.",
         "ACCEPT", notes="Expenses never mentioned; pre-approval not required, so nothing to "
                          "flag."),
]

# ---------------------------------------------------------------------------
# Taxes: responsibility, withholding.
# ---------------------------------------------------------------------------
CASES += [
    case("tax-01", ["taxes", "counterparty_responsible"],
         "9. Payment Terms. Customer shall be responsible for all applicable sales, use, and "
         "value-added taxes.",
         "ACCEPT", policy_overrides={"contract_side": "sell_side", "require_tax_responsibility_counterparty": True},
         notes="We are Vendor (sell_side); Customer (buy_side) is correctly resolved as the "
               "counterparty bearing tax responsibility."),
    case("tax-02", ["taxes", "we_responsible"],
         "9. Payment Terms. Vendor shall be responsible for all applicable sales, use, and "
         "value-added taxes.",
         "MUST_REDLINE", policy_overrides={"contract_side": "sell_side", "require_tax_responsibility_counterparty": True},
         notes="We are Vendor (sell_side); the clause attributes tax responsibility to us, "
               "not the counterparty."),
    case("tax-03", ["taxes", "withholding"],
         "9. Payment Terms. Any withholding tax imposed on payments hereunder shall be "
         "addressed in accordance with applicable law.",
         "ACCEPT", notes="Withholding-tax presence extracted as an informational fact."),
    case("tax-04", ["taxes", "missing"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.",
         "NEGOTIATE", policy_overrides={"require_tax_responsibility_counterparty": True},
         notes="No tax-responsibility statement at all — required by policy."),
    case("tax-05", ["taxes", "conflicting"],
         "9. Payment Terms. Customer shall be responsible for all applicable taxes. "
         "Notwithstanding the foregoing, Vendor shall be responsible for all applicable "
         "taxes.",
         "REQUIRES_REVIEW", policy_overrides={"require_tax_responsibility_counterparty": True},
         notes="Tax responsibility attributed to both parties in different places — genuine "
               "conflict."),
]

# ---------------------------------------------------------------------------
# Currency: single, multiple/conflicting.
# ---------------------------------------------------------------------------
CASES += [
    case("currency-01", ["currency", "usd"],
         "9. Payment Terms. All payments shall be made in United States Dollars.",
         "ACCEPT", policy_overrides={"required_currency": "USD"},
         notes="USD currency stated matches the required currency."),
    case("currency-02", ["currency", "mismatch"],
         "9. Payment Terms. All payments shall be made in Euros.",
         "MUST_REDLINE", policy_overrides={"required_currency": "USD"},
         notes="Clause states EUR but policy requires USD."),
    case("currency-03", ["currency", "missing"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.",
         "NEGOTIATE", policy_overrides={"required_currency": "USD"},
         notes="No currency stated at all — required by policy."),
    case("currency-04", ["currency", "conflict"],
         "9. Payment Terms. All payments shall be made in United States Dollars. "
         "Notwithstanding the foregoing, payments for European operations shall be made in "
         "Euros.",
         "REQUIRES_REVIEW",
         notes="Two different currencies stated — genuine conflict, cannot safely determine "
               "the payment currency."),
]

# ---------------------------------------------------------------------------
# Refunds / credits.
# ---------------------------------------------------------------------------
CASES += [
    case("refund-01", ["refund", "present"],
         "9. Payment Terms. Vendor shall provide Customer with a refund for any pre-paid but "
         "undelivered Services.",
         "ACCEPT", policy_overrides={"require_refund_entitlement": True},
         notes="Refund entitlement satisfied."),
    case("refund-02", ["refund", "missing"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.",
         "NEGOTIATE", policy_overrides={"require_refund_entitlement": True},
         notes="No refund language present — required by policy."),
    case("credit-01", ["service_credit", "present"],
         "9. Payment Terms. In the event Vendor fails to meet the Service Levels, Customer "
         "shall be entitled to a service credit against future invoices.",
         "ACCEPT", notes="Service-credit presence extracted as an informational fact — full "
                          "SLA reasoning is out of scope for this adapter (a separate SLA "
                          "adapter will own that)."),
]

# ---------------------------------------------------------------------------
# Order Form / SOW / Schedule cross-references; amendments.
# ---------------------------------------------------------------------------
CASES += [
    case("crossref-01", ["schedule_crossref", "nothing_else"],
         "9. Payment Terms. Payment terms, including pricing, invoicing, and payment periods, "
         "shall be as set forth in the applicable Order Form.",
         "REQUIRES_REVIEW",
         notes="Material payment terms are delegated wholesale to an external Order Form with "
               "no dimension independently established in-clause."),
    case("crossref-02", ["schedule_crossref", "supplementing"],
         FULLY_COMPLIANT_TEXT + " This Section is further supplemented by the applicable "
         "Order Form.",
         "ACCEPT", policy_overrides=dict(FULLY_COMPLIANT_POLICY),
         notes="An Order Form cross-reference that supplements (rather than replaces) an "
               "otherwise-complete in-clause treatment does not block evaluation."),
    case("amendment-01", ["amendment", "consistent"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.\n\n18. Amendment to Payment Terms. For the avoidance of doubt, Customer "
         "confirms payment remains due within Net 30 days of receipt of invoice, consistent "
         "with Section 9.",
         "ACCEPT", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="Two anchored windows restate the SAME net-days period — no conflict, values "
               "merge cleanly."),
    case("amendment-02", ["amendment", "changes_net_days"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.\n\n18. First Amendment. Section 9 is hereby amended to require payment "
         "within Net 60 days of receipt of invoice.",
         "REQUIRES_REVIEW", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="The original clause and the amendment state two DIFFERENT Net-day periods — "
               "cannot determine which one controls without legal interpretation."),
]

# ---------------------------------------------------------------------------
# No payment clause -> NOT_APPLICABLE.
# ---------------------------------------------------------------------------
CASES += [
    case("not-applicable-01", ["not_applicable"],
         "9. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware, without regard to its conflicts of laws principles.",
         "NOT_APPLICABLE", notes="No payment terms clause anchor at all."),
    case("not-applicable-02", ["not_applicable", "ip_only"],
         "9. Intellectual Property. Vendor shall retain all right, title and interest in its "
         "pre-existing intellectual property.",
         "NOT_APPLICABLE", notes="Ordinary IP clause, no payment content."),
]

# ---------------------------------------------------------------------------
# Malformed / degenerate clauses.
# ---------------------------------------------------------------------------
CASES += [
    case("malformed-01", ["malformed", "fragment"],
         "9. Payment Terms. Amounts.",
         "NEGOTIATE", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="Anchor matches ('payment terms') but the fragment establishes nothing — no "
               "net-days figure at all, so the acceptable-maximum check falls through to its "
               "'no payment period found' NEGOTIATE branch."),
    case("malformed-02", ["malformed", "heading_only"],
         "9. Payment Terms.",
         "ACCEPT",
         notes="The section heading itself ('Payment Terms') matches the anchor, so "
               "clause_found=True even with no body — with nothing required by default "
               "policy, no notes fire -> ACCEPT, not a fabricated NOT_APPLICABLE."),
    case("malformed-03", ["malformed", "ocr_noise"],
         "9.  Payment   Terms .   Customer  shall   pay   Vendor   within   Net   30   days  "
         "of   receipt   of   invoice .",
         "ACCEPT", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="Irregular whitespace (OCR-style artifact) should not defeat the anchor or "
               "net-days regexes, which tolerate \\s+ throughout."),
]

# ---------------------------------------------------------------------------
# Ambiguous pronouns.
# ---------------------------------------------------------------------------
CASES += [
    case("ambiguous-pronoun-01", ["ambiguous_pronoun"],
         "9. Payment Terms. Each party shall pay the other within 30 days of receipt of an "
         "invoice for amounts properly due and owing.",
         "NEGOTIATE",
         policy_overrides={"require_counterparty_is_payor": True, "acceptable_max_net_days": 30.0},
         notes="CORRECTED after benchmark run: no named-party payor/payee statement is "
               "extractable here at all (generic 'each party'/'the other' pronouns, no "
               "resolvable party name) — payment_direction_attributions stays empty, so "
               "payor_side is None. require_counterparty_is_payor's top-level check fires "
               "whenever payor_side is None (regardless of whether that's because "
               "attributions never existed or because they were unresolvable), noting 'no "
               "payor/payee statement was found' at NEGOTIATE severity. net_days (30) is "
               "independently satisfied, but the unresolved-payor note still applies — "
               "original label (ACCEPT) incorrectly assumed the top-level payor check only "
               "fires when attributions exist, but it fires whenever payor_side is None."),
]

# ---------------------------------------------------------------------------
# Multiple payment provisions in one clause (consistent, not conflicting).
# ---------------------------------------------------------------------------
CASES += [
    case("multi-provision-01", ["multi_provision", "consistent"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice for Services fees. Customer shall also reimburse Vendor for pre-approved "
         "expenses within Net 30 days of receipt of invoice.",
         "ACCEPT", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="Two separate payment obligations (fees and expenses) both stating the SAME "
               "Net 30 period — no conflict, consistent values."),
]

# ---------------------------------------------------------------------------
# Explicit negations.
# ---------------------------------------------------------------------------
CASES += [
    case("negation-01", ["negation", "no_undisputed_continuation"],
         "9. Payment Terms. Customer shall not be obligated to pay any amounts, disputed or "
         "undisputed, during the pendency of a good-faith dispute.",
         "NEGOTIATE", policy_overrides={"require_undisputed_amounts_still_payable": True},
         notes="Explicit negation does not match the undisputed-continuation presence regex "
               "(which only detects an affirmative commitment) — treated as a gap, the same "
               "conservative behavior established in the prior three adapters for explicit "
               "negations."),
    case("negation-02", ["negation", "no_setoff_right"],
         "9. Payment Terms. Customer shall not have any right of set-off, deduction, or "
         "counterclaim against amounts owed to Vendor.",
         "ACCEPT", policy_overrides={"prohibit_set_off": True},
         notes="Explicit set-off negation satisfies the policy prohibition."),
    case("negation-03", ["negation", "no_price_increase"],
         "9. Payment Terms. Vendor shall not increase prices during the Initial Term.",
         "ACCEPT", policy_overrides={"prohibit_unilateral_price_increase": True},
         notes="An explicit prohibition on any increase does not trigger the "
               "unilateral-increase note (no increase right, let alone a unilateral one, is "
               "granted)."),
]

# ---------------------------------------------------------------------------
# Directionality (payor/payee, who pays whom).
# ---------------------------------------------------------------------------
CASES += [
    case("direction-01", ["directionality", "counterparty_payor_clean"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.",
         "ACCEPT",
         policy_overrides={"contract_side": "sell_side", "require_counterparty_is_payor": True,
                            "acceptable_max_net_days": 30.0},
         notes="We are Vendor (sell_side); Customer (buy_side) is correctly resolved as the "
               "counterparty obligated to pay."),
    case("direction-02", ["directionality", "wrong_payor"],
         "9. Payment Terms. Vendor shall pay Customer within Net 30 days of receipt of "
         "invoice.",
         "MUST_REDLINE",
         policy_overrides={"contract_side": "sell_side", "require_counterparty_is_payor": True,
                            "acceptable_max_net_days": 30.0},
         notes="We are Vendor (sell_side); the clause obligates US to pay, not the "
               "counterparty — wrong direction for a policy requiring the counterparty to be "
               "the payor."),
    case("direction-03", ["directionality", "conflicting"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice. Vendor shall pay Customer a rebate within Net 30 days of the end of each "
         "quarter.",
         "REQUIRES_REVIEW",
         policy_overrides={"require_counterparty_is_payor": True},
         notes="Two DIFFERENT payment obligations run in opposite directions (fees one way, "
               "rebate the other) — the payor/payee relationship cannot be safely attributed "
               "to a single direction."),
    case("direction-04", ["directionality", "mutual"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.",
         "REQUIRES_REVIEW",
         policy_overrides={"contract_side": "mutual", "require_counterparty_is_payor": True},
         notes="Directional payor/payee statement under a mutual-position playbook — cannot "
               "determine whether Customer is 'us' or 'counterparty'."),
    case("direction-05", ["directionality", "not_required"],
         "9. Payment Terms. Vendor shall pay Customer within Net 30 days of receipt of "
         "invoice.",
         "ACCEPT",
         policy_overrides={"contract_side": "sell_side", "require_counterparty_is_payor": False,
                            "acceptable_max_net_days": 30.0},
         notes="require_counterparty_is_payor is off — payment period satisfied regardless of "
               "which party is named as payor."),
]

# ---------------------------------------------------------------------------
# Negative controls: numbers elsewhere in the contract must not be
# accidentally claimed as payment periods, rates, prices, or currencies.
# ---------------------------------------------------------------------------
CASES += [
    case("negative-control-01", ["negative_control", "termination_notice_not_net_days"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice.\n\n14. Termination. Either party may terminate this Agreement upon 90 "
         "days' prior written notice.",
         "ACCEPT", policy_overrides={"acceptable_max_net_days": 30.0},
         notes="A 90-day TERMINATION notice period in an unrelated clause must not be read "
               "as a conflicting net-payment period — net_days resolves cleanly to 30 with no "
               "conflict."),
    case("negative-control-02", ["negative_control", "dispute_notice_not_net_days"],
         "9. Payment Terms. Customer shall pay Vendor within Net 30 days of receipt of "
         "invoice. Customer may dispute any invoice within 15 days of receipt by providing "
         "written notice.",
         "ACCEPT", policy_overrides={"acceptable_max_net_days": 30.0, "minimum_dispute_notice_days": 10.0},
         notes="The dispute-notice period (15 days) is a DIFFERENT fact from the net-payment "
               "period (30 days) — both must resolve independently and correctly, not "
               "collide into a false net_days conflict. (This exact collision was caught as "
               "a real extraction bug during benchmarking — see module docstring.)"),
    case("negative-control-03", ["negative_control", "price_increase_not_late_fee"],
         "9. Payment Terms. Amounts not paid when due shall accrue interest at the rate of "
         "1.5% per month. Vendor may increase prices upon notice, provided that any such "
         "increase shall not exceed 5% per year.",
         "ACCEPT", policy_overrides={"maximum_late_interest_rate_percent": 25.0, "maximum_price_increase_percent": 10.0},
         notes="A price-increase cap ('5% per year') must not be misread as a late-payment "
               "interest rate, and vice versa — both use identical 'N% per year/month' "
               "phrasing but belong to different economic facts. (This exact collision was "
               "caught as a real extraction bug during benchmarking.)"),
    case("negative-control-04", ["negative_control", "unrelated_currency_mention"],
         "9. Payment Terms. All payments shall be made in United States Dollars.\n\n15. "
         "Limitation of Liability. In no event shall either party's aggregate liability "
         "exceed the fees paid in the twelve months preceding the claim, converted from Euros "
         "where applicable to intercompany invoicing.",
         "ACCEPT", policy_overrides={"required_currency": "USD"},
         notes="An incidental 'Euros' mention inside an unrelated liability clause must not "
               "be read as establishing a second, conflicting payment currency — currency "
               "resolves cleanly to USD from the Payment Terms section alone (the liability "
               "clause is outside this adapter's anchored window)."),
    case("negative-control-05", ["negative_control", "expense_percent_not_late_fee"],
         "9. Payment Terms. Amounts not paid when due shall accrue interest at the rate of "
         "1.5% per month. Customer shall reimburse Vendor for 100% of reasonable, "
         "pre-approved travel expenses.",
         "ACCEPT", policy_overrides={"maximum_late_interest_rate_percent": 25.0},
         notes="A '100%' expense-reimbursement figure must not be picked up as a second, "
               "conflicting late-fee rate."),
]
