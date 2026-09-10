"""Extract ContractCommercialFacts once from contract text.

Single source for annual fees and payment-due terms. Downstream consumers
(EvaluationContext ACV resolution, payment_terms_json UI, commercial policy)
must read these facts rather than re-parsing with independent regexes.

ACV provenance: this module establishes CONTRACT_ANNUAL_FEES only. It never
writes EvaluationContext.annual_contract_value. Callers use
resolve_annual_contract_value(reviewer_deal_value=..., contract_annual_fees=...).
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from contract_facts.commercial import (
    BillingFrequency,
    ContractCommercialFacts,
    PaymentDueBasis,
    PaymentDueTerms,
)
from contract_facts.evidence import EvidenceSpan
from contract_facts.fact import EstablishedFact
from policy_engine_core import WORD_NUMBERS
from policy_grammar.money import MoneyAmount

_WORD_ALT = "|".join(sorted(WORD_NUMBERS.keys(), key=len, reverse=True))

# Anchor near annual/subscription fee language, then require an explicit
# dollar figure (bare "$600,000" or parenthetical "($600,000)"). Word-form
# amounts without digits are not treated as established fees.
_ANNUAL_FEES_ANCHOR_RE = re.compile(
    r"(?:annual(?:ly)?\s+(?:subscription\s+)?fees?|subscription\s+fees?(?:\s+per\s+year)?|"
    r"annual(?:ly)?\s+(?:recurring\s+)?(?:revenue|fees?|amount))",
    re.I,
)
_DOLLAR_AMOUNT_RE = re.compile(
    r"\(\s*\$\s*([\d,]+(?:\.\d+)?)\s*\)|\$\s*([\d,]+(?:\.\d+)?)",
    re.I,
)

_CURRENCY_CODE_RE = re.compile(r"\b(USD|EUR|GBP|CAD|AUD)\b")

# Payable-within with word-numbers and parenthetical digits; bare "after receipt"
# is treated as invoice_receipt when the sentence is about invoices.
_PAYMENT_DUE_RE = re.compile(
    rf"(?:invoices?\s+are\s+)?payable\s+within\s+"
    rf"(?:(\d{{1,3}})|({_WORD_ALT}))\s*(?:\(\s*(\d{{1,3}})\s*\))?\s*days?"
    rf"\s+(?:of|after|from)\s+(?:the\s+)?"
    rf"(?:receipt(?:\s+of\s+(?:the\s+|an?\s+)?invoice)?|invoice(?:\s+date)?|"
    rf"delivery|acceptance|execution)"
    rf"|"
    rf"\bnet\s+(\d{{1,3}})\b"
    rf"|"
    rf"(?:due|payable)\s+within\s+(?:(\d{{1,3}})|({_WORD_ALT}))\s*(?:\(\s*(\d{{1,3}})\s*\))?\s*days?",
    re.I,
)

_BILLING_PATTERNS = (
    (re.compile(r"\bmonthly\b", re.I), BillingFrequency.MONTHLY),
    (re.compile(r"\bquarterly\b", re.I), BillingFrequency.QUARTERLY),
    (re.compile(r"\bannual(?:ly)?\b|\byearly\b", re.I), BillingFrequency.ANNUALLY),
    (re.compile(r"\bweekly\b", re.I), BillingFrequency.WEEKLY),
    (re.compile(r"\bone[-\s]?time\b", re.I), BillingFrequency.ONE_TIME),
    (re.compile(r"\brecurring\b", re.I), BillingFrequency.RECURRING),
)


def _parse_amount(*candidates: Optional[str]) -> Optional[float]:
    for raw in candidates:
        if not raw:
            continue
        cleaned = raw.replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            n = WORD_NUMBERS.get(cleaned.lower())
            if n is not None:
                # "six hundred thousand" handled via parenthetical; bare "thousand" scale
                return float(n)
    return None


def _parse_days(digit: Optional[str], word: Optional[str], paren: Optional[str]) -> Optional[int]:
    if paren:
        try:
            return int(paren)
        except ValueError:
            pass
    if digit:
        try:
            return int(digit)
        except ValueError:
            pass
    if word:
        n = WORD_NUMBERS.get(word.lower())
        if n is not None:
            return int(n)
    return None


def _span(text: str, start: int, end: int) -> EvidenceSpan:
    return EvidenceSpan(excerpt=text[start:end], start_index=start, end_index=end)


def extract_commercial_facts(text: str) -> ContractCommercialFacts:
    """Deterministic commercial extraction → ContractCommercialFacts."""
    if not text or not text.strip():
        return ContractCommercialFacts()

    annual_fees: EstablishedFact[MoneyAmount] = EstablishedFact.unknown(
        "no annual/subscription fee amount established",
    )
    m_anchor = _ANNUAL_FEES_ANCHOR_RE.search(text)
    if m_anchor:
        # Search the fee clause window (anchor → end of sentence / 120 chars).
        window_end = text.find(".", m_anchor.start())
        if window_end == -1 or window_end - m_anchor.start() > 160:
            window_end = min(len(text), m_anchor.start() + 160)
        window = text[m_anchor.start():window_end]
        m_amt = _DOLLAR_AMOUNT_RE.search(window)
        if m_amt:
            amount = _parse_amount(m_amt.group(1), m_amt.group(2))
            if amount is not None:
                currency = "USD"
                code = _CURRENCY_CODE_RE.search(window) or _CURRENCY_CODE_RE.search(
                    text[window_end: window_end + 12],
                )
                if code:
                    currency = code.group(1).upper()
                abs_start = m_anchor.start() + m_amt.start()
                abs_end = m_anchor.start() + m_amt.end()
                annual_fees = EstablishedFact.present(
                    MoneyAmount.from_number(
                        str(int(amount) if amount == int(amount) else amount),
                        currency,
                    ),
                    _span(text, m_anchor.start(), abs_end),
                )

    currency_fact: EstablishedFact[str] = EstablishedFact.unknown("currency not evaluated")
    if annual_fees.is_known and annual_fees.value is not None:
        currency_fact = EstablishedFact.present(
            annual_fees.value.currency,
            annual_fees.evidence,
        )
    else:
        code = _CURRENCY_CODE_RE.search(text)
        if code:
            currency_fact = EstablishedFact.present(code.group(1).upper(), _span(text, code.start(), code.end()))
        elif re.search(r"\$\s?[\d,]", text):
            currency_fact = EstablishedFact.present("USD")

    billing: EstablishedFact[BillingFrequency] = EstablishedFact.unknown(
        "billing frequency not evaluated",
    )
    for pattern, label in _BILLING_PATTERNS:
        bm = pattern.search(text)
        if bm:
            billing = EstablishedFact.present(label, _span(text, bm.start(), bm.end()))
            break

    payment_due: EstablishedFact[PaymentDueTerms] = EstablishedFact.unknown(
        "payment due not established",
    )
    invoice_trigger: EstablishedFact[str] = EstablishedFact.unknown(
        "invoice trigger not evaluated",
    )
    m_pay = _PAYMENT_DUE_RE.search(text)
    if m_pay:
        g = m_pay.groups()
        # Patterns produce overlapping optional groups; collect non-None.
        days = None
        basis = PaymentDueBasis.UNKNOWN
        raw = m_pay.group(0).lower()
        if "net" in raw and re.search(r"\bnet\s+\d+", raw):
            days = _parse_days(g[3] if len(g) > 3 else None, None, None)
            # net group is group index 3 in the combined regex — re-parse safely
            nm = re.search(r"\bnet\s+(\d{1,3})\b", m_pay.group(0), re.I)
            if nm:
                days = int(nm.group(1))
            basis = PaymentDueBasis.NET
        else:
            # payable within … days after receipt [of invoice]
            days = _parse_days(g[0], g[1], g[2])
            if days is None:
                days = _parse_days(g[4] if len(g) > 4 else None, g[5] if len(g) > 5 else None, g[6] if len(g) > 6 else None)
            if "receipt" in raw and "invoice" in raw:
                basis = PaymentDueBasis.INVOICE_RECEIPT
            elif "receipt" in raw:
                basis = PaymentDueBasis.INVOICE_RECEIPT
            elif "invoice" in raw:
                basis = PaymentDueBasis.INVOICE_DATE
            elif "delivery" in raw:
                basis = PaymentDueBasis.DELIVERY
            elif "acceptance" in raw:
                basis = PaymentDueBasis.ACCEPTANCE
            elif "execution" in raw:
                basis = PaymentDueBasis.EXECUTION
        if days is not None:
            payment_due = EstablishedFact.present(
                PaymentDueTerms(days=days, basis=basis),
                _span(text, m_pay.start(), m_pay.end()),
            )
            if basis == PaymentDueBasis.INVOICE_RECEIPT:
                invoice_trigger = EstablishedFact.present("receipt", payment_due.evidence)
            elif basis == PaymentDueBasis.INVOICE_DATE:
                invoice_trigger = EstablishedFact.present("invoice", payment_due.evidence)

    return ContractCommercialFacts(
        annual_fees=annual_fees,
        currency=currency_fact,
        billing_frequency=billing,
        payment_due=payment_due,
        invoice_trigger=invoice_trigger,
    )
