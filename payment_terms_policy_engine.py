"""
Payment Terms / Commercial Terms clause adapter, over policy_engine_core.
Adapter #10 — the fourth added after the original six (following
data_security_policy_engine.py, adapter #7; ip_ownership_policy_engine.py,
adapter #8; insurance_policy_engine.py, adapter #9). Built by directly
mirroring the established adapter shape rather than inventing a new one;
policy_engine_core.py was not modified — every primitive this adapter
needs already existed and fit without change. classify_by_threshold was
NOT used: payment-timing/pricing dimensions here are either "lower is
better" ceilings (net days, price-increase rate) checked with a simple
minimum/maximum comparison, or category/presence facts with no natural
banded-tier shape — none of them are the three-tier preferred/acceptable/
negotiate structure classify_by_threshold models, so a direct comparison
was used instead, consistent with how insurance's minimum-limit checks
and ip_ownership's boolean gates were built without forcing that helper
either.

SEMANTIC MODEL: a payment/commercial-terms clause is a CATALOG of
independent economic facts across eleven distinct groups — payment
timing, invoice mechanics, disputed amounts, late payment, set-off,
pricing, expenses, taxes, currency, and refunds/credits — never
collapsed into one payment_terms=acceptable classification. Several
groups (invoice mechanics, refunds/credits, statutory-rate references)
are modeled as informational facts surfaced via category_treatments with
no dedicated policy gate, the same precedent data_security's DPA cross-
reference and insurance's deductible/SIR established: not every
deterministically-extractable fact needs its own accept/reject toggle,
only the ones that are genuine negotiated positions.

DIRECTIONALITY: payment terms are strongly directional — "who pays whom
what when." Rather than inverting every single numeric/boolean field's
sense depending on whether we are payor or payee (which would double
the field count and doesn't match how lawyers actually configure a
playbook — a liability cap ladder doesn't flip meaning by contract_side
either), this adapter separates the directional question into ONE
gate (require_counterparty_is_payor) resolved the same side-agnostic-
attribution-then-evaluate-time pattern data_security uses for
controller/processor role and insurance uses for the obligated insured
party. Every other numeric/boolean field (net days, dispute rights,
set-off, price-increase caps, tax responsibility, ...) is a direct
ceiling/floor/presence check the lawyer configures to their own
playbook's position, independent of who happens to be paying.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

from policy_engine_core import (
    ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE,
    REQUIRES_REVIEW, NOT_APPLICABLE,
    LadderStep, build_ladder as _core_build_ladder,
    escalate_to_for_state, fallback_text_for_state, side_for_role, resolve_role_side,
    excerpt, section_label_before,
    requires_review_explanation, requires_review_required_action,
    PolicyDecision,
)

RULE_ID = "POLICY_PAYMENT_TERMS"
_PROVISION_WINDOW_CHARS = 2600

_GENERIC_WORDS = {"each", "the", "any", "such", "this", "that", "both", "either", "party", "parties", "all", "it"}

# --- Anchor -----------------------------------------------------------------
_ANCHOR_RE = re.compile(
    r"payment\s+terms|invoices?|shall\s+pay|payable|remit(?:tance)?"
    r"|late\s+(?:fee|payment|charge)|set-?off|offset|price\s+increase|reimburs\w*|withholding\s+tax"
    r"|sales\s+tax|value[\s-]added\s+tax|\bVAT\b|\bGST\b|service\s+credit|net\s+\d{1,3}\s+days",
    re.I,
)

# --- Payment direction (who pays whom) ---------------------------------------
_PAY_DIRECTION_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,30}))\s+shall\s+pay\s+(?-i:([A-Z][A-Za-z]{2,30}))\b", re.I,
)

# --- Net days / payment period ------------------------------------------------
_NET_DAYS_RE = re.compile(r"\bnet\s+(\d{1,3})\b", re.I)
_WITHIN_DAYS_PAYMENT_RE = re.compile(
    r"within\s+(\d{1,3})\s+days\s+(?:of|after|from)\s+(?:the\s+date\s+of\s+)?(?:receipt\s+of\s+)?(?:the\s+|an?\s+)?invoice"
    r"|within\s+(\d{1,3})\s+days\s+(?:of|after|from)\s+receipt\s+of\s+(?:the\s+)?(?:goods|services|deliverables)"
    r"|within\s+(\d{1,3})\s+days\s+(?:of|after|from)\s+(?:the\s+date\s+of\s+)?(?:written\s+)?acceptance"
    r"|shall\s+pay[^.]{0,60}?within\s+(\d{1,3})\s+days"
    r"|payment\s+(?:shall\s+be\s+)?due\s+within\s+(\d{1,3})\s+days", re.I,
)

# --- Payment trigger ------------------------------------------------------------
_TRIGGER_INVOICE_RE = re.compile(r"(?:from|after|of)\s+(?:the\s+date\s+of\s+)?(?:receipt\s+of\s+)?(?:the\s+|an?\s+)?invoice\b|invoice\s+date", re.I)
_TRIGGER_RECEIPT_RE = re.compile(r"receipt\s+of\s+(?:the\s+)?(?:goods|services|deliverables)|date\s+of\s+receipt", re.I)
_TRIGGER_ACCEPTANCE_RE = re.compile(r"(?:upon|after|following)\s+(?:written\s+)?acceptance|acceptance\s+of\s+(?:the\s+)?(?:deliverables|services)", re.I)
_TRIGGER_MILESTONE_RE = re.compile(r"upon\s+completion\s+of\s+(?:each\s+|the\s+)?milestone|milestone\s+payment", re.I)

_PREPAYMENT_RE = re.compile(r"prepay(?:ment)?|pay(?:ment)?\s+in\s+advance|advance\s+payment", re.I)
_MILESTONE_RE = re.compile(r"milestone\s+payment|payment\s+(?:shall\s+be\s+)?(?:due|made)\s+(?:upon|at)\s+(?:each\s+)?milestone", re.I)

# --- Invoice mechanics (informational) ------------------------------------------
_INVOICE_FREQUENCY_RE = re.compile(r"invoice\s+(?:Customer|Client)?\s*(?:monthly|quarterly|annually|upon\s+completion|upon\s+delivery)", re.I)
_INVOICE_SUBMISSION_RE = re.compile(r"invoices?\s+(?:shall|must)\s+(?:be\s+)?(?:submitted|sent|delivered)", re.I)
_INVOICE_DEFECT_TOLL_RE = re.compile(r"incomplete\s+or\s+incorrect\s+invoice|invalid\s+invoice[^.]{0,60}?(?:toll|suspend|reset|not\s+(?:begin|start))", re.I)

# --- Disputes ---------------------------------------------------------------------
_DISPUTE_RIGHT_RE = re.compile(r"(?:may|right\s+to)\s+dispute|good\s+faith\s+dispute", re.I)
_DISPUTE_NOTICE_DAYS_RE = re.compile(
    r"dispute[^.]{0,40}?within\s+(\d{1,3})\s+days|within\s+(\d{1,3})\s+days[^.]{0,40}?dispute", re.I,
)
_UNDISPUTED_PAYABLE_RE = re.compile(
    r"undisputed\s+(?:amounts?|portion)[^.]{0,60}?(?:shall|must)\s+(?:continue\s+to\s+)?(?:be\s+)?paid"
    r"|shall\s+(?:continue\s+to\s+)?pay\s+(?:all\s+)?undisputed", re.I,
)
_DISPUTED_WITHHOLD_RE = re.compile(
    r"withhold\s+payment\s+of\s+(?:the\s+)?disputed|disputed\s+(?:amounts?|portion)\s+may\s+be\s+withheld", re.I,
)
_DISPUTED_NO_WITHHOLD_RE = re.compile(r"shall\s+not\s+withhold|may\s+not\s+withhold", re.I)

# --- Late payment -------------------------------------------------------------------
# Scoped to a local sentence anchored on "interest"/"late fee"/"late charge"
# (see _local_window use in extract_payment_facts) so a price-increase
# cap's "5% per year" in a DIFFERENT sentence is never misread as a
# late-payment interest rate — both use identical "N% per year" phrasing.
_INTEREST_ANCHOR_RE = re.compile(r"interest|late\s+(?:fee|payment|charge)", re.I)
_LATE_FEE_MONTHLY_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:per\s+month|monthly|a\s+month)", re.I)
_LATE_FEE_ANNUAL_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:per\s+annum|annually|a\s+year|per\s+year)", re.I)
_GRACE_PERIOD_RE = re.compile(
    r"grace\s+period\s+of\s+(\d{1,3})\s+days|(\d{1,3})\s+days[^.]{0,20}?grace\s+period"
    r"|(\d{1,3})-days?\s+grace\s+period", re.I,
)
_STATUTORY_MAX_RE = re.compile(r"maximum\s+rate\s+permitted\s+by\s+(?:applicable\s+)?law|lesser\s+of[^.]{0,60}?(?:permitted\s+by\s+)?law", re.I)

# --- Set-off ------------------------------------------------------------------------
# Step 4A.3: "offset" is a synonym family for "set-off"/"setoff" — the
# identical legal right in commercial contracts (British/formal "set-off"
# vs. American/colloquial "offset"), not a case-specific addition. Every
# set-off pattern below recognizes both spellings.
_SETOFF_TERM_FRAGMENT = r"(?:set[\s-]?off|offset)"
_SETOFF_PERMIT_RE = re.compile(
    r"(?:(?<!not\s)(?<!not\shave\s)(?<!not\shave\sany\s)right\s+(?:to|of)|may|entitled\s+to)\s+" + _SETOFF_TERM_FRAGMENT,
    re.I,
)
_SETOFF_PROHIBIT_RE = re.compile(
    r"shall\s+not\s+" + _SETOFF_TERM_FRAGMENT
    # "right of deduction, counterclaim, or set-off" — an enumerated list
    # between "right of" and the set-off term must not break the match;
    # up to 3 intervening list items (", word"), each optionally preceded
    # by "or", is tolerated. Covers both "no right of X" and "shall not
    # have any right of X" framings.
    + r"|(?:no|shall\s+not\s+have\s+(?:any\s+)?)\s*right\s+(?:of|to)\s+(?:[\w-]+,\s*){0,3}(?:or\s+)?" + _SETOFF_TERM_FRAGMENT
    + r"|without\s+(?:any\s+)?(?:right\s+of\s+)?(?:[\w-]+,\s*){0,3}(?:or\s+)?" + _SETOFF_TERM_FRAGMENT,
    re.I,
)
_UNILATERAL_DEDUCTION_RE = re.compile(
    r"unilaterally\s+deduct|deduct[^.]{0,30}?without\s+(?:prior\s+)?(?:written\s+)?(?:consent|approval)", re.I,
)

# Step 4A.5 — Priority 1 (SM-CRITICAL fix). The legal concept behind
# "set-off"/"offset" is mutual-debt netting: one party satisfies (or is
# barred from satisfying) an amount it owes by reference to an amount the
# OTHER party owes it — however that's phrased ("withhold", "deduct",
# "reduce", "net", "retain", "recoup", "debit", "apply as a credit", ...).
# The Step 4A.4 held-out corpus (A4-K-07) demonstrated this concept
# silently disappearing — NOT_APPLICABLE — when drafted without the
# literal words "set-off"/"offset". Recognizing the WORD is not the same
# as recognizing the CONCEPT.
#
# The two-part test below requires BOTH:
#   (1) a satisfaction/reduction verb governing a payment-shaped object
#       ("amount", "sum", "payment", "invoice", "royalt(y/ies)",
#       "commission", "fee(s)", "rent", "freight", "hire", "charge(s)"),
#   (2) an explicit "owe(s)/owed/owing" reference elsewhere in the same
#       sentence — the deterministic signal that a SECOND, counterparty-
#       held debt is what justifies the reduction.
# "Due"/"payable" alone (part 1's own object) is NOT itself sufficient for
# part 2 — every ordinary invoice is "due" or "payable"; only "owe(s)/
# owed/owing" reliably signals a debt attributed to a specific party
# rather than an ordinary payment obligation. This is why plain tax
# withholding ("shall be responsible for... withholding taxes"), service
# credits, refunds, rebates, billing corrections, and accounting net
# presentation do not match: none of them describe an amount the RECIPIENT
# of a payment owes the payor — see benchmarks/setoff_concept_benchmark.py
# for the 30 negative controls this was validated against, including
# "withhold DELIVERY pending payment" (a performance-leverage right, not a
# payment-netting right) and "retain its OWN commission" (compensation,
# not netting against a debt owed BY the other party).
_DEBT_SATISFACTION_VERB_RE = re.compile(
    r"\b(?:withhold\w*|deduct\w*|reduc\w*|net(?:s|ted|ting)?|retain\w*|recoup\w*|debit\w*"
    r"|apply|applying|applied|credit(?:ing|ed)?)\b",
    re.I,
)
_PAYMENT_OBJECT_FRAGMENT = (
    r"(?:amounts?|sums?|payments?|invoices?|royalt(?:y|ies)|commissions?|fees?|rent|freight|hire|charges?)"
)
_DEBT_SATISFACTION_ACTION_RE = re.compile(
    _DEBT_SATISFACTION_VERB_RE.pattern + r"[^.;]{0,80}?" + _PAYMENT_OBJECT_FRAGMENT,
    re.I,
)
_COUNTERPARTY_OWES_RE = re.compile(r"\bowe[sd]?\b|\bowing\b", re.I)
_DEBT_SATISFACTION_LOCAL_CHARS = 150


_MUTUAL_DEBT_NEGATION_RE = re.compile(
    r"shall\s+not\s+(?:have\s+(?:any\s+)?right|be\s+entitled)|no\s+right|without\s+(?:any\s+)?right"
    r"|shall\s+not\s+" + _DEBT_SATISFACTION_VERB_RE.pattern,
    re.I,
)


def _find_mutual_debt_netting_span(text: str) -> Optional[Tuple[int, int]]:
    """Returns the (start, end) span of the first payment-reduction
    action (withhold/deduct/reduce/net/retain/recoup/debit/apply-as-
    credit, governing a payment-shaped object) that has an explicit
    "owe(s)/owed/owing" reference within a bounded local window of it —
    scoped locally (not whole-window) so an unrelated "owe" elsewhere in
    a large provision window can't combine with an unrelated deduction
    verb elsewhere in the same window to produce a false match. None if
    no such pairing exists."""
    for m in _DEBT_SATISFACTION_ACTION_RE.finditer(text):
        lo = max(0, m.start() - _DEBT_SATISFACTION_LOCAL_CHARS)
        hi = min(len(text), m.end() + _DEBT_SATISFACTION_LOCAL_CHARS)
        if _COUNTERPARTY_OWES_RE.search(text[lo:hi]):
            return m.start(), m.end()
    return None


def _has_mutual_debt_netting(text: str) -> bool:
    return _find_mutual_debt_netting_span(text) is not None

# --- Pricing --------------------------------------------------------------------------
_FIXED_PRICE_RE = re.compile(r"(?:prices?|fees?)\s+(?:shall\s+be\s+|are\s+)?fixed|fixed[\s-](?:price|fee)", re.I)
_PRICE_INCREASE_RIGHT_RE = re.compile(r"(?:may|right\s+to)\s+increase\s+(?:the\s+)?(?:prices?|fees?)", re.I)
_PRICE_INCREASE_UNILATERAL_RE = re.compile(r"unilaterally\s+increase[^.]{0,20}?(?:prices?|fees?)|sole\s+discretion[^.]{0,40}?increase[^.]{0,20}?(?:prices?|fees?)", re.I)
_PRICE_INCREASE_NOTICE_RE = re.compile(
    r"(\d{1,3})\s+days[’']?\s+(?:prior\s+)?(?:written\s+)?notice[^.]{0,60}?increase"
    r"|notice\s+of[^.]{0,20}?increase[^.]{0,50}?(\d{1,3})\s+days", re.I,
)
# Scoped to a local sentence anchored on an actual price/fee-increase
# mention (see _PRICE_INCREASE_ANCHOR_RE below) — otherwise "N% per
# year" is textually identical to a late-payment interest rate and the
# two get cross-contaminated.
_PRICE_INCREASE_ANCHOR_RE = re.compile(r"increase\s+(?:the\s+)?(?:prices?|fees?)|price\s+increase|fee\s+increase|increase\s+prices?", re.I)
_PRICE_INCREASE_PERCENT_RE = re.compile(
    r"(?:by\s+)?(?:more\s+than\s+)?(\d+(?:\.\d+)?)\s*%(?:\s+(?:per|each)\s+(?:year|annum))?", re.I,
)
_PRICE_INDEX_RE = re.compile(r"\bCPI\b|consumer\s+price\s+index|index[- ]linked", re.I)

# --- Expenses --------------------------------------------------------------------------
_EXPENSES_RE = re.compile(r"reimburs\w*[^.]{0,60}?expenses|expenses\s+shall\s+be\s+reimbursed", re.I)
_EXPENSE_PREAPPROVAL_RE = re.compile(r"prior\s+written\s+approval[^.]{0,40}?expenses|pre-?approv\w*[^.]{0,20}?expenses|expenses[^.]{0,30}?pre-?approv", re.I)
_EXPENSE_DOCS_RE = re.compile(r"(?:receipts?|documentation)[^.]{0,30}?expenses|expenses[^.]{0,30}?(?:receipts?|documentation)", re.I)

# --- Taxes -------------------------------------------------------------------------------
_TAX_RESPONSIBILITY_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,30}))\s+(?:shall\s+be\s+)?responsible\s+for\s+(?:all\s+)?(?:applicable\s+)?[^.]{0,40}?taxes", re.I,
)
_WITHHOLDING_TAX_RE = re.compile(r"withholding\s+tax", re.I)
# Engagement-only (Step 4A.3): _TAX_RESPONSIBILITY_RE requires a
# CAPITALIZED role word immediately before "responsible for...taxes" so
# it can ATTRIBUTE the obligation to a specific party — "Each party
# shall be responsible for taxes..." has no attributable single party
# (an extra common noun sits between the determiner and the verb) but
# is still unambiguously a supported tax-responsibility clause that
# must engage the adapter, even though it correctly yields no
# attribution.
_TAX_RESPONSIBILITY_TOPIC_RE = re.compile(
    r"responsible\s+for\s+(?:all\s+)?(?:applicable\s+)?[^.]{0,40}?taxes", re.I,
)

# --- Currency -----------------------------------------------------------------------------
# Scoped to a local sentence anchored on an actual payment-currency
# statement ("paid in.../payable in.../denominated in...") — otherwise
# any incidental currency mention anywhere in the same anchored window
# (e.g. a liability cap expressed cross-referencing a different
# currency in an unrelated clause) is misread as establishing a second,
# conflicting payment currency.
_CURRENCY_CONTEXT_RE = re.compile(
    # Allow a short object between the payment verb and "in" ("shall pay
    # Vendor in United States Dollars") — active-voice phrasing routinely
    # places the payee between the verb and the currency, not just the
    # passive "amounts payable in X" form already covered.
    r"(?:pay|paid|payable|made|denominated|invoiced)(?:\s+\w+){0,3}?\s+in\b", re.I,
)
_CURRENCY_RE = re.compile(
    r"\b(USD|EUR|GBP|CAD|AUD|JPY|CHF)\b|United\s+States\s+Dollars|US\s+Dollars|Euros?\b|British\s+Pounds?|Pounds\s+Sterling",
    re.I,
)
_CURRENCY_NORMALIZE = {
    "usd": "USD", "united states dollars": "USD", "us dollars": "USD",
    "eur": "EUR", "euro": "EUR", "euros": "EUR",
    "gbp": "GBP", "british pound": "GBP", "british pounds": "GBP", "pounds sterling": "GBP",
    "cad": "CAD", "aud": "AUD", "jpy": "JPY", "chf": "CHF",
}

# --- Refunds / credits -----------------------------------------------------------------------
_REFUND_RE = re.compile(r"\brefunds?\b", re.I)
_SERVICE_CREDIT_RE = re.compile(r"service\s+credits?", re.I)

# --- Schedule / Order Form cross-reference ------------------------------------------------------
_SCHEDULE_CROSSREF_RE = re.compile(
    r"as\s+(?:set\s+forth|described|specified)\s+in\s+the\s+(?:applicable\s+)?(?:Order\s+Form|SOW|Statement\s+of\s+Work|Schedule|Exhibit)"
    r"|governed\s+by\s+(?:the\s+)?(?:applicable\s+)?(?:Order\s+Form|SOW|Schedule)", re.I,
)


_SENTENCE_END_RE = re.compile(r"(?<!\d)\.(?!\d)|;")


def _local_window(text: str, start: int, other_anchor_positions: List[int], max_radius: int = 400) -> str:
    """Scopes forward from `start` to the nearest real sentence boundary
    (a period NOT immediately between two digits, so "1.5%" is never
    mistaken for two sentences) or the next other-anchor position,
    whichever comes first."""
    end = min(len(text), start + max_radius)
    m = _SENTENCE_END_RE.search(text, start, end)
    if m:
        end = min(end, m.end())
    for pos in other_anchor_positions:
        if pos > start:
            end = min(end, pos)
    return text[start:end]


@dataclass
class PaymentFacts:
    clause_found: bool
    raw_excerpt: str = ""
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    section_label: Optional[str] = None

    # Directionality: payor_name -> {payee_name,...}, side-agnostic.
    payment_direction_attributions: Dict[str, set] = field(default_factory=dict)
    payment_direction_conflict: bool = False

    # Timing
    net_days: Optional[float] = None
    net_days_conflict: bool = False
    payment_trigger: Optional[str] = None  # "invoice" | "receipt" | "acceptance" | "milestone"
    payment_trigger_conflict: bool = False
    prepayment_required: Optional[bool] = None
    milestone_payment_present: Optional[bool] = None

    # Invoice mechanics (informational only)
    invoice_frequency_stated: Optional[bool] = None
    invoice_submission_requirements_stated: Optional[bool] = None
    invoice_defect_tolls_payment: Optional[bool] = None

    # Disputes
    dispute_right_present: Optional[bool] = None
    dispute_notice_days: Optional[float] = None
    dispute_notice_conflict: bool = False
    undisputed_amounts_still_payable: Optional[bool] = None
    disputed_amounts_withholdable: Optional[bool] = None

    # Late payment
    late_fee_rate_percent: Optional[float] = None
    late_fee_period: Optional[str] = None  # "monthly" | "annual"
    late_fee_conflict: bool = False
    grace_period_days: Optional[float] = None
    statutory_max_reference: Optional[bool] = None

    # Set-off
    setoff_permitted: Optional[bool] = None
    unilateral_deduction_permitted: Optional[bool] = None

    # Pricing
    pricing_fixed: Optional[bool] = None
    price_increase_right: Optional[bool] = None
    price_increase_unilateral: Optional[bool] = None
    price_increase_notice_days: Optional[float] = None
    price_increase_percent: Optional[float] = None
    price_increase_percent_conflict: bool = False
    price_increase_index_linked: Optional[bool] = None

    # Expenses
    expenses_reimbursable: Optional[bool] = None
    expense_preapproval_required: Optional[bool] = None
    expense_documentation_required: Optional[bool] = None

    # Taxes
    tax_responsibility_attributions: Dict[str, bool] = field(default_factory=dict)
    tax_responsibility_conflict: bool = False
    withholding_tax_addressed: Optional[bool] = None

    # Step 4A: {role_name: reason} for every role named in
    # payment_direction_attributions/tax_responsibility_attributions whose
    # generic side_for_role() mapping conflicts with the document's own
    # definition of that role (see policy_engine_core.resolve_role_side).
    # A name present here must never be treated as confidently mapped to
    # either side, regardless of what the generic vocabulary alone says.
    role_side_conflicts: Dict[str, str] = field(default_factory=dict)

    # Currency
    currency: Optional[str] = None
    currency_conflict: bool = False

    # Refunds / credits
    refund_entitlement_present: Optional[bool] = None
    service_credit_present: Optional[bool] = None

    schedule_cross_reference: bool = False


class PaymentPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]

    require_counterparty_is_payor: bool
    preferred_net_days: Optional[float]
    acceptable_max_net_days: Optional[float]
    required_payment_trigger: Optional[str]  # "invoice" | "receipt" | "acceptance" | "milestone"
    require_undisputed_amounts_still_payable: bool
    prohibit_disputed_amount_withholding: bool
    minimum_dispute_notice_days: Optional[float]
    prohibit_set_off: bool
    maximum_late_interest_rate_percent: Optional[float]
    prohibit_unilateral_price_increase: bool
    maximum_price_increase_percent: Optional[float]
    minimum_price_increase_notice_days: Optional[float]
    require_expense_preapproval: bool
    require_tax_responsibility_counterparty: bool
    required_currency: Optional[str]
    require_refund_entitlement: bool


def _classify_trigger(window: str) -> set:
    found = set()
    if _TRIGGER_MILESTONE_RE.search(window):
        found.add("milestone")
    if _TRIGGER_ACCEPTANCE_RE.search(window):
        found.add("acceptance")
    if _TRIGGER_RECEIPT_RE.search(window):
        found.add("receipt")
    if _TRIGGER_INVOICE_RE.search(window):
        found.add("invoice")
    return found


def _annualize_late_fee(rate: float, period: Optional[str]) -> float:
    """Normalizes a stated late-fee rate to an annualized percentage for
    comparison against a configured annual maximum — documented
    assumption: a monthly rate is treated as compounding-free x12 for
    comparison purposes only (not a re-derivation of the contract's own
    compounding mechanics, which this adapter does not model)."""
    if period == "monthly":
        return rate * 12
    return rate


# Step 4A.3 — the decomposed set of concept-specific recognizers that can
# independently engage the adapter, each already used elsewhere in this
# module for its own field-level extraction (never a new pattern
# invented solely to widen the gate). Deliberately excludes
# _CURRENCY_RE/_PRICE_INCREASE_PERCENT_RE-style bare-value regexes,
# which match on numbers/short tokens alone and would engage on
# unrelated numeric mentions — only regexes that already require
# concept-specific surrounding language are used as engagement signals.
_CONCEPT_ENGAGEMENT_RES = [
    _TAX_RESPONSIBILITY_RE, _TAX_RESPONSIBILITY_TOPIC_RE, _WITHHOLDING_TAX_RE,
    _SETOFF_PERMIT_RE, _SETOFF_PROHIBIT_RE, _UNILATERAL_DEDUCTION_RE, _DEBT_SATISFACTION_ACTION_RE,
    _DISPUTE_RIGHT_RE, _UNDISPUTED_PAYABLE_RE, _DISPUTED_WITHHOLD_RE, _DISPUTED_NO_WITHHOLD_RE,
    _LATE_FEE_MONTHLY_RE, _LATE_FEE_ANNUAL_RE, _STATUTORY_MAX_RE,
    _PRICE_INCREASE_RIGHT_RE, _PRICE_INCREASE_UNILATERAL_RE, _FIXED_PRICE_RE,
    _EXPENSES_RE, _EXPENSE_PREAPPROVAL_RE, _CURRENCY_CONTEXT_RE,
]


def extract_payment_facts(text: str) -> Optional[PaymentFacts]:
    # Step 4A.3 — Failure Family 2 hardening. Step 4A.2's held-out corpus
    # found that engagement for the ENTIRE adapter depended on one
    # monolithic _ANCHOR_RE — a genuine tax-responsibility, set-off, or
    # dispute-payment clause using ordinary phrasing outside that single
    # regex's vocabulary produced NOT_APPLICABLE ("no payment terms
    # clause found"), silently hiding the clause from policy evaluation
    # entirely (18 of Step 4A.2's 29 wrong-clean decisions traced here,
    # including a role-reversal case that would have been a genuine
    # false-safe had recognition engaged at all).
    #
    # Recognition is decomposed by supported policy concept: engagement
    # now fires on _ANCHOR_RE OR any of the field-specific extraction
    # regexes this module ALREADY ships (tax responsibility, withholding,
    # set-off/offset, dispute-payment, late-fee/interest, price-increase,
    # expense reimbursement) — each of those is already more precise than
    # a generic keyword (e.g. _TAX_RESPONSIBILITY_RE requires a named
    # party + "responsible for...taxes", not just the word "tax"
    # anywhere), so reusing them as engagement signals doesn't trade
    # recall for false engagement on unrelated clauses (see
    # benchmarks/payment_recognition_benchmark.py's 20 negative controls,
    # none of which mention taxes/set-off/disputes in a supported-concept
    # way). This directly answers "why does one narrow anchor gate the
    # whole adapter" — it no longer does; any independently-recognized
    # concept is sufficient to engage.
    concept_matches: List[re.Match] = []
    for concept_re in _CONCEPT_ENGAGEMENT_RES:
        concept_matches.extend(concept_re.finditer(text))
    matches = sorted(list(_ANCHOR_RE.finditer(text)) + concept_matches, key=lambda m: m.start())
    if not matches:
        return None

    windows: List[Tuple[int, int]] = []
    for m in matches:
        s = max(0, m.start() - 200)
        e = min(len(text), m.end() + _PROVISION_WINDOW_CHARS)
        if windows and s - windows[-1][1] < 200:
            windows[-1] = (windows[-1][0], max(windows[-1][1], e))
        else:
            windows.append((s, e))

    first_match = matches[0]
    start_index = max(0, first_match.start() - 200)
    end_index = min(len(text), first_match.end() + 400)
    raw_excerpt = excerpt(text, start_index, end_index)
    section_label = section_label_before(text, first_match.start())

    facts = PaymentFacts(clause_found=True, raw_excerpt=raw_excerpt, start_index=start_index,
                          end_index=end_index, section_label=section_label)

    net_days_values: set = set()
    trigger_tokens: set = set()
    dispute_notice_values: set = set()
    late_fee_values: set = set()  # (rate, period) tuples, annualized-comparable
    price_increase_percent_values: set = set()
    currency_tokens: set = set()

    for (ws, we) in windows:
        window = text[ws:we]

        for m in _NET_DAYS_RE.finditer(window):
            net_days_values.add(int(m.group(1)))
        for m in _WITHIN_DAYS_PAYMENT_RE.finditer(window):
            raw = next((g for g in m.groups() if g), None)
            if raw:
                net_days_values.add(int(raw))

        trigger_tokens |= _classify_trigger(window)

        if _PREPAYMENT_RE.search(window):
            facts.prepayment_required = True
        if _MILESTONE_RE.search(window):
            facts.milestone_payment_present = True

        if _INVOICE_FREQUENCY_RE.search(window):
            facts.invoice_frequency_stated = True
        if _INVOICE_SUBMISSION_RE.search(window):
            facts.invoice_submission_requirements_stated = True
        if _INVOICE_DEFECT_TOLL_RE.search(window):
            facts.invoice_defect_tolls_payment = True

        if _DISPUTE_RIGHT_RE.search(window):
            facts.dispute_right_present = True
        for m in _DISPUTE_NOTICE_DAYS_RE.finditer(window):
            raw = m.group(1) or m.group(2)
            if raw:
                dispute_notice_values.add(int(raw))
        if _UNDISPUTED_PAYABLE_RE.search(window):
            facts.undisputed_amounts_still_payable = True
        if _DISPUTED_WITHHOLD_RE.search(window) and not _DISPUTED_NO_WITHHOLD_RE.search(window):
            facts.disputed_amounts_withholdable = True
        elif _DISPUTED_NO_WITHHOLD_RE.search(window):
            facts.disputed_amounts_withholdable = False

        for am in _INTEREST_ANCHOR_RE.finditer(window):
            local = _local_window(window, am.end(), [])
            for m in _LATE_FEE_MONTHLY_RE.finditer(local):
                late_fee_values.add((float(m.group(1)), "monthly"))
            for m in _LATE_FEE_ANNUAL_RE.finditer(local):
                late_fee_values.add((float(m.group(1)), "annual"))
        for m in _GRACE_PERIOD_RE.finditer(window):
            raw = m.group(1) or m.group(2) or m.group(3)
            if raw:
                facts.grace_period_days = float(raw)
        if _STATUTORY_MAX_RE.search(window):
            facts.statutory_max_reference = True

        if _SETOFF_PERMIT_RE.search(window) and not _SETOFF_PROHIBIT_RE.search(window):
            facts.setoff_permitted = True
        elif _SETOFF_PROHIBIT_RE.search(window):
            facts.setoff_permitted = False
        else:
            netting_span = _find_mutual_debt_netting_span(window)
            if netting_span is not None:
                # Step 4A.5: the mutual-debt-netting concept is present
                # but phrased without "set-off"/"offset" — a negation cue
                # ("shall not", "no right", "without any right") found
                # near the SAME match (not merely anywhere in a large
                # provision window) still controls; otherwise this is a
                # permitted mutual-debt-netting right.
                lo = max(0, netting_span[0] - _DEBT_SATISFACTION_LOCAL_CHARS)
                hi = min(len(window), netting_span[1] + _DEBT_SATISFACTION_LOCAL_CHARS)
                facts.setoff_permitted = not bool(_MUTUAL_DEBT_NEGATION_RE.search(window[lo:hi]))
        if _UNILATERAL_DEDUCTION_RE.search(window):
            facts.unilateral_deduction_permitted = True

        if _FIXED_PRICE_RE.search(window):
            facts.pricing_fixed = True
        if _PRICE_INCREASE_RIGHT_RE.search(window):
            facts.price_increase_right = True
        if _PRICE_INCREASE_UNILATERAL_RE.search(window):
            facts.price_increase_unilateral = True
        for m in _PRICE_INCREASE_NOTICE_RE.finditer(window):
            raw = m.group(1) or m.group(2)
            if raw:
                facts.price_increase_notice_days = float(raw)
        for am in _PRICE_INCREASE_ANCHOR_RE.finditer(window):
            local = _local_window(window, am.end(), [])
            for m in _PRICE_INCREASE_PERCENT_RE.finditer(local):
                if m.group(1):
                    price_increase_percent_values.add(float(m.group(1)))
        if _PRICE_INDEX_RE.search(window):
            facts.price_increase_index_linked = True

        if _EXPENSES_RE.search(window):
            facts.expenses_reimbursable = True
        if _EXPENSE_PREAPPROVAL_RE.search(window):
            facts.expense_preapproval_required = True
        if _EXPENSE_DOCS_RE.search(window):
            facts.expense_documentation_required = True

        for m in _TAX_RESPONSIBILITY_RE.finditer(window):
            name = m.group(1)
            if name and name.lower() not in _GENERIC_WORDS:
                facts.tax_responsibility_attributions[name] = True
        if _WITHHOLDING_TAX_RE.search(window):
            facts.withholding_tax_addressed = True

        for am in _CURRENCY_CONTEXT_RE.finditer(window):
            # A short, tight radius: real "paid/payable/made in <currency>"
            # phrasing states the currency immediately afterward. A wider
            # radius risks false positives like "fees paid in the twelve
            # months preceding the claim ... Euros" — "paid in" used in a
            # TIME sense, not a currency sense, with an unrelated currency
            # word appearing later in the same sentence.
            local = _local_window(window, am.end(), [], max_radius=30)
            for m in _CURRENCY_RE.finditer(local):
                token = (m.group(1) or m.group(0)).strip().lower()
                normalized = _CURRENCY_NORMALIZE.get(token)
                if normalized:
                    currency_tokens.add(normalized)

        if _REFUND_RE.search(window):
            facts.refund_entitlement_present = True
        if _SERVICE_CREDIT_RE.search(window):
            facts.service_credit_present = True

        if _SCHEDULE_CROSSREF_RE.search(window):
            facts.schedule_cross_reference = True

        for m in _PAY_DIRECTION_RE.finditer(window):
            payor, payee = m.group(1), m.group(2)
            if payor.lower() in _GENERIC_WORDS or payee.lower() in _GENERIC_WORDS:
                continue
            facts.payment_direction_attributions.setdefault(payor, set()).add(payee)

    if len(net_days_values) == 1:
        facts.net_days = float(next(iter(net_days_values)))
    elif len(net_days_values) > 1:
        facts.net_days_conflict = True

    if len(trigger_tokens) == 1:
        facts.payment_trigger = next(iter(trigger_tokens))
    elif len(trigger_tokens) > 1:
        facts.payment_trigger_conflict = True

    if len(dispute_notice_values) == 1:
        facts.dispute_notice_days = float(next(iter(dispute_notice_values)))
    elif len(dispute_notice_values) > 1:
        facts.dispute_notice_conflict = True

    if len(late_fee_values) == 1:
        rate, period = next(iter(late_fee_values))
        facts.late_fee_rate_percent = rate
        facts.late_fee_period = period
    elif len(late_fee_values) > 1:
        facts.late_fee_conflict = True

    if len(price_increase_percent_values) == 1:
        facts.price_increase_percent = next(iter(price_increase_percent_values))
    elif len(price_increase_percent_values) > 1:
        facts.price_increase_percent_conflict = True

    if len(currency_tokens) == 1:
        facts.currency = next(iter(currency_tokens))
    elif len(currency_tokens) > 1:
        facts.currency_conflict = True

    if len(set(facts.tax_responsibility_attributions)) > 1:
        facts.tax_responsibility_conflict = True

    if any(len(payees) > 1 for payees in facts.payment_direction_attributions.values()) or len(facts.payment_direction_attributions) > 1:
        facts.payment_direction_conflict = True

    # Step 4A: verify every role name this extraction attributed
    # responsibility to (payor or tax) against the document's own
    # definition of that role, not just the generic buy/sell vocabulary.
    role_names = set(facts.tax_responsibility_attributions) | set(facts.payment_direction_attributions) | {
        payee for payees in facts.payment_direction_attributions.values() for payee in payees
    }
    for name in role_names:
        _, conflict_reason = resolve_role_side(name, text)
        if conflict_reason:
            facts.role_side_conflicts[name] = conflict_reason

    return facts


def _resolve_payor_side(facts: PaymentFacts, contract_side: str) -> Tuple[Optional[str], bool]:
    """Resolves whether "us" or "counterparty" is the payor, from the
    side-agnostic payment_direction_attributions gathered at extraction
    time. Mirrors data_security._resolve_our_role / insurance.
    _resolve_obligated_party."""
    if not facts.payment_direction_attributions:
        return None, False
    if contract_side == "mutual":
        return None, True
    sides: set = set()
    for payor_name in facts.payment_direction_attributions:
        # Step 4A: a role whose document-specific definition conflicts
        # with the generic vocabulary (facts.role_side_conflicts) must
        # never be trusted as mapped to either side, even though
        # side_for_role() alone would happily return one.
        mapped = None if payor_name in facts.role_side_conflicts else side_for_role(payor_name)
        if mapped == contract_side:
            sides.add("us")
        elif mapped is not None:
            sides.add("counterparty")
    if len(sides) == 1:
        return next(iter(sides)), False
    return None, True


def _resolve_tax_responsibility(facts: PaymentFacts, contract_side: str) -> Tuple[Optional[str], bool]:
    if not facts.tax_responsibility_attributions:
        return None, False
    if contract_side == "mutual":
        return None, True
    sides: set = set()
    for name in facts.tax_responsibility_attributions:
        mapped = None if name in facts.role_side_conflicts else side_for_role(name)
        if mapped == contract_side:
            sides.add("us")
        elif mapped is not None:
            sides.add("counterparty")
    if len(sides) == 1:
        return next(iter(sides)), False
    return None, True


def _build_ladder(policy: PaymentPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", "Preferred payment terms met in full"),
        ("ACCEPTABLE", "Auto-accept within acceptable payment terms"),
        ("FALLBACK", "Negotiate payment terms within fallback range"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Prohibited payment terms"),
    ]
    return _core_build_ladder(state, step_specs)


_WORST_ORDER = {ACCEPT: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, MUST_REDLINE: 3, ESCALATE: 4, PROHIBITED: 5}


def _worse(a: str, b: str) -> str:
    return a if _WORST_ORDER.get(a, 0) >= _WORST_ORDER.get(b, 0) else b


def evaluate_payment_policy(
    facts: Optional[PaymentFacts],
    policy: PaymentPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    common = dict(
        rule_id=RULE_ID, clause_type="payment_terms", source=source,
        summary_label="Payment terms treatment",
        our_position_label="Our payment requirements",
        counterparty_position_label="Counterparty's payment commitments",
    )

    if facts is None or not facts.clause_found:
        return PolicyDecision(
            **common, state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No payment terms clause found",
            policy_limit_summary="N/A",
            required_action="None — this contract does not address payment terms",
            explanation="No payment terms clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None,
            interaction_facts={"disputed_amounts_withholdable": None, "service_credit_present": None},
        )

    payor_side, payor_unresolved = _resolve_payor_side(facts, policy.contract_side)
    tax_side, tax_unresolved = _resolve_tax_responsibility(facts, policy.contract_side)

    unresolved: List[str] = []
    if facts.net_days_conflict:
        unresolved.append("multiple conflicting Net payment periods are stated")
    if facts.payment_trigger_conflict:
        unresolved.append("the payment trigger (invoice/receipt/acceptance/milestone) is stated inconsistently — invoice and acceptance provisions establish conflicting triggers")
    if facts.payment_direction_conflict:
        unresolved.append("the payor/payee relationship is stated inconsistently — cannot safely attribute who pays whom")
    elif policy.require_counterparty_is_payor and facts.payment_direction_attributions and payor_unresolved:
        payor_conflicts = [r for n, r in facts.role_side_conflicts.items() if n in facts.payment_direction_attributions
                           or any(n in payees for payees in facts.payment_direction_attributions.values())]
        if payor_conflicts:
            unresolved.extend(payor_conflicts)
        else:
            unresolved.append("the party obligated to pay could not be confidently mapped to our configured contract side, "
                               "or this playbook is configured for a mutual position — cannot determine who pays whom")
    if facts.dispute_notice_conflict:
        unresolved.append("the dispute-notice period is stated inconsistently across the document")
    if facts.late_fee_conflict:
        unresolved.append("multiple conflicting late-payment rates or bases are stated")
    if facts.price_increase_percent_conflict:
        unresolved.append("the price-increase formula/percentage cannot be deterministically resolved — conflicting values are stated")
    if facts.currency_conflict:
        unresolved.append("multiple conflicting payment currencies are stated")
    if facts.tax_responsibility_conflict:
        unresolved.append("tax responsibility is stated inconsistently — attributed to different parties in different places")
    elif policy.require_tax_responsibility_counterparty and facts.tax_responsibility_attributions and tax_unresolved:
        tax_conflicts = [r for n, r in facts.role_side_conflicts.items() if n in facts.tax_responsibility_attributions]
        if tax_conflicts:
            unresolved.extend(tax_conflicts)
        else:
            unresolved.append("tax responsibility is stated by named party but could not be confidently mapped to our "
                               "configured contract side, or this playbook is configured for a mutual position")

    established_dimension_count = sum(1 for v in (
        facts.net_days, facts.payment_trigger, facts.prepayment_required, facts.milestone_payment_present,
        facts.dispute_right_present, facts.dispute_notice_days, facts.undisputed_amounts_still_payable,
        facts.disputed_amounts_withholdable, facts.late_fee_rate_percent, facts.grace_period_days,
        facts.setoff_permitted, facts.unilateral_deduction_permitted, facts.pricing_fixed,
        facts.price_increase_right, facts.price_increase_percent, facts.expenses_reimbursable,
        facts.withholding_tax_addressed, facts.currency, facts.refund_entitlement_present,
        facts.service_credit_present,
    ) if v is not None) + (1 if facts.payment_direction_attributions else 0) + (1 if facts.tax_responsibility_attributions else 0)
    if facts.schedule_cross_reference and established_dimension_count == 0:
        unresolved.append("material payment terms are delegated to a referenced Order Form/SOW/Schedule not included in this text")

    if unresolved:
        explanation = requires_review_explanation("payment terms clause", facts.raw_excerpt, unresolved)
        return PolicyDecision(
            **common, state=REQUIRES_REVIEW,
            contract_language=facts.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary="N/A", required_action=requires_review_required_action(unresolved),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved,
            start_index=facts.start_index, end_index=facts.end_index,
            controlling_provision={"label": f"Section {facts.section_label} — Payment Terms" if facts.section_label else "Payment Terms", "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
            interaction_facts={
                "disputed_amounts_withholdable": facts.disputed_amounts_withholdable,
                "service_credit_present": facts.service_credit_present,
            },
        )

    notes: List[str] = []
    worst = ACCEPT
    category_treatments: List[Dict[str, Any]] = []

    def _note(msg: str, state: str) -> None:
        nonlocal worst
        notes.append(msg)
        worst = _worse(worst, state)

    # --- Directionality ---------------------------------------------------
    if policy.require_counterparty_is_payor:
        if payor_side is None:
            _note("policy requires the counterparty to be the payor, but no payor/payee statement was found", NEGOTIATE)
        elif payor_side != "counterparty":
            _note("policy requires the counterparty to be the payor, but the clause obligates us instead", MUST_REDLINE)
    category_treatments.append({"category": "payor", "treatment": payor_side or "not_addressed", "cap_summary": None, "raw_excerpt": "", "established": payor_side is not None})

    # --- Net days -----------------------------------------------------------
    if policy.acceptable_max_net_days is not None:
        if facts.net_days is None:
            _note("policy requires a stated payment period within the acceptable maximum, but none was found", NEGOTIATE)
        elif facts.net_days > policy.acceptable_max_net_days:
            _note(f"payment period of Net {int(facts.net_days)} exceeds policy's acceptable maximum of Net {int(policy.acceptable_max_net_days)}", NEGOTIATE)
    category_treatments.append({"category": "net_days", "treatment": (f"Net {int(facts.net_days)}" if facts.net_days is not None else "not_addressed"), "cap_summary": None, "raw_excerpt": "", "established": facts.net_days is not None})

    # --- Payment trigger --------------------------------------------------------
    if policy.required_payment_trigger:
        if facts.payment_trigger != policy.required_payment_trigger:
            _note(f"policy requires a {policy.required_payment_trigger} payment trigger, but the clause states "
                  f"{facts.payment_trigger or 'no stated trigger'}", NEGOTIATE)

    # --- Disputes ----------------------------------------------------------------
    if policy.require_undisputed_amounts_still_payable and not facts.undisputed_amounts_still_payable:
        _note("policy requires undisputed amounts to remain payable during a dispute, but no such commitment was found", NEGOTIATE)
    if policy.prohibit_disputed_amount_withholding and facts.disputed_amounts_withholdable:
        _note("clause permits withholding of disputed amounts, prohibited by policy", MUST_REDLINE)
    if policy.minimum_dispute_notice_days is not None:
        if facts.dispute_notice_days is None:
            _note("policy requires a minimum dispute-notice period, but none was found", NEGOTIATE)
        elif facts.dispute_notice_days < policy.minimum_dispute_notice_days:
            _note(f"dispute-notice period of {int(facts.dispute_notice_days)} days is below policy's required minimum of {int(policy.minimum_dispute_notice_days)} days", NEGOTIATE)

    # --- Set-off -------------------------------------------------------------------
    if policy.prohibit_set_off and facts.setoff_permitted:
        _note("clause permits set-off, prohibited by policy", MUST_REDLINE)

    # --- Late payment ----------------------------------------------------------------
    if policy.maximum_late_interest_rate_percent is not None:
        if facts.late_fee_rate_percent is None:
            _note("policy configures a maximum late-payment rate, but no late fee/interest provision was found at all", NEGOTIATE)
        else:
            annualized = _annualize_late_fee(facts.late_fee_rate_percent, facts.late_fee_period)
            if annualized > policy.maximum_late_interest_rate_percent:
                _note(f"late-payment rate of {facts.late_fee_rate_percent:g}% ({facts.late_fee_period or 'stated'}) exceeds "
                      f"policy's maximum permitted annualized rate of {policy.maximum_late_interest_rate_percent:g}%", NEGOTIATE)

    # --- Pricing -----------------------------------------------------------------------
    if policy.prohibit_unilateral_price_increase and facts.price_increase_unilateral:
        _note("clause permits unilateral price increases, prohibited by policy", MUST_REDLINE)
    if policy.maximum_price_increase_percent is not None:
        if facts.price_increase_percent is None and facts.price_increase_right:
            _note("policy caps price increases, but the clause grants an increase right with no stated percentage/formula", NEGOTIATE)
        elif facts.price_increase_percent is not None and facts.price_increase_percent > policy.maximum_price_increase_percent:
            _note(f"price-increase cap of {facts.price_increase_percent:g}% exceeds policy's maximum permitted {policy.maximum_price_increase_percent:g}%", NEGOTIATE)
    if policy.minimum_price_increase_notice_days is not None:
        if facts.price_increase_right and facts.price_increase_notice_days is None:
            _note("policy requires minimum notice before a price increase, but none was found", NEGOTIATE)
        elif facts.price_increase_notice_days is not None and facts.price_increase_notice_days < policy.minimum_price_increase_notice_days:
            _note(f"price-increase notice of {int(facts.price_increase_notice_days)} days is below policy's required minimum of {int(policy.minimum_price_increase_notice_days)} days", NEGOTIATE)

    # --- Expenses ------------------------------------------------------------------------
    if policy.require_expense_preapproval and not facts.expense_preapproval_required:
        _note("policy requires expense pre-approval, but no such requirement was found", NEGOTIATE)

    # --- Taxes ---------------------------------------------------------------------------------
    if policy.require_tax_responsibility_counterparty:
        if tax_side is None:
            _note("policy requires the counterparty to bear tax responsibility, but no tax-responsibility statement was found", NEGOTIATE)
        elif tax_side != "counterparty":
            _note("policy requires the counterparty to bear tax responsibility, but the clause attributes it to us", MUST_REDLINE)

    # --- Currency -------------------------------------------------------------------------------
    if policy.required_currency:
        if facts.currency is None:
            _note(f"policy requires payment in {policy.required_currency}, but no currency was stated", NEGOTIATE)
        elif facts.currency != policy.required_currency:
            _note(f"policy requires payment in {policy.required_currency}, but the clause states {facts.currency}", MUST_REDLINE)

    # --- Refunds / credits -----------------------------------------------------------------------
    if policy.require_refund_entitlement and not facts.refund_entitlement_present:
        _note("policy requires a refund entitlement, but none was found", NEGOTIATE)

    extracted_summary_parts = []
    if facts.net_days is not None:
        extracted_summary_parts.append(f"Net {int(facts.net_days)}")
    if facts.payment_trigger:
        extracted_summary_parts.append(f"Trigger: {facts.payment_trigger}")
    if facts.currency:
        extracted_summary_parts.append(f"Currency: {facts.currency}")
    extracted_summary = "; ".join(extracted_summary_parts) or "Payment terms clause found; limited structured detail extractable"

    if worst == ACCEPT and not notes:
        required_action = "None — payment terms meet policy"
        explanation = f"Contract language: \"{facts.raw_excerpt}\". No policy gaps found. Result: {ACCEPT}."
    else:
        if worst in (ESCALATE, PROHIBITED):
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — " + "; ".join(notes)
        elif worst == MUST_REDLINE:
            required_action = "Replace clause — apply the approved fallback payment terms language: " + "; ".join(notes)
        else:
            required_action = "Negotiate — " + "; ".join(notes)
        explanation = f"Contract language: \"{facts.raw_excerpt}\". {'; '.join(notes)}. Result: {worst}."

    return PolicyDecision(
        **common, state=worst,
        contract_language=facts.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary="See configured policy",
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, worst),
        category_treatments=category_treatments, unresolved_facts=[],
        start_index=facts.start_index, end_index=facts.end_index,
        escalate_to=escalate_to_for_state(worst, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(worst, policy.fallback_text, (NEGOTIATE, MUST_REDLINE, PROHIBITED)),
        controlling_provision={"label": f"Section {facts.section_label} — Payment Terms" if facts.section_label else "Payment Terms", "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
        interaction_facts={
            "disputed_amounts_withholdable": facts.disputed_amounts_withholdable,
            "service_credit_present": facts.service_credit_present,
        },
    )
