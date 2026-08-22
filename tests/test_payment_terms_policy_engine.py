"""
Unit test suite for payment_terms_policy_engine.py.

Created for Step 4A of the TriageCounsel counsel-audit: prior to this,
payment_terms had corpus/benchmark coverage (benchmarks/payment_terms_corpus.py,
tests/test_payment_terms_benchmark_gate.py) but no dedicated unit-test file
independent of the benchmark corpus. This file starts with the permanent
regression for the Step 2 defined-term/party-role reversal failure
(PAY-C-01) and basic sanity coverage around it.
"""
from dataclasses import dataclass
from typing import Optional

import payment_terms_policy_engine as pte
import policy_engine_core as core


@dataclass
class FakePolicy:
    """Matches the codebase's established convention (see
    benchmarks/payment_terms_corpus.py DEFAULT_POLICY docstring): nothing
    required by default — every require_* is False, every numeric
    minimum/maximum is None — so each test opts in only to the
    dimension(s) it means to exercise."""
    contract_side: str = "buy_side"
    escalation_approval_authority: Optional[str] = "Legal Director"
    fallback_text: Optional[str] = "Approved fallback payment terms."
    require_counterparty_is_payor: bool = False
    preferred_net_days: Optional[float] = None
    acceptable_max_net_days: Optional[float] = None
    required_payment_trigger: Optional[str] = None
    require_undisputed_amounts_still_payable: bool = False
    prohibit_disputed_amount_withholding: bool = False
    minimum_dispute_notice_days: Optional[float] = None
    prohibit_set_off: bool = False
    maximum_late_interest_rate_percent: Optional[float] = None
    prohibit_unilateral_price_increase: bool = False
    maximum_price_increase_percent: Optional[float] = None
    minimum_price_increase_notice_days: Optional[float] = None
    require_expense_preapproval: bool = False
    require_tax_responsibility_counterparty: bool = False
    required_currency: Optional[str] = None
    require_refund_entitlement: bool = False


def evaluate(text: str, **policy_kwargs) -> core.PolicyDecision:
    policy = FakePolicy(**policy_kwargs)
    facts = pte.extract_payment_facts(text)
    return pte.evaluate_payment_policy(facts, policy, source="Test Playbook v1")


class TestNoClause:
    def test_no_payment_terms_language_is_not_applicable(self):
        d = evaluate("9. Governing Law. This Agreement is governed by Delaware law.")
        assert d.state == core.NOT_APPLICABLE


class TestOrdinaryPaymentTerms:
    def test_conventional_net_30_within_policy_accepts(self):
        d = evaluate("5. Payment Terms. Customer shall pay all invoices within Net 30 days.")
        assert d.state == core.ACCEPT
        assert d.unresolved_facts == []


class TestStep4ARoleReversal:
    """PAY-C-01 (Step 2). Document redefines 'Customer'/'Vendor' opposite
    to their conventional buy/sell mapping: 'Customer' means the entity
    that develops and provides the Software (the real seller), 'Vendor'
    means the entity that purchases a subscription (the real buyer, i.e.
    us, given contract_side="buy_side"). The clause places tax
    responsibility on 'Vendor'. Before Step 4A: side_for_role("Vendor")
    mapped to sell_side (the literal, generic reading), which is NOT our
    configured contract_side, so the engine concluded the COUNTERPARTY
    bore the tax burden and returned a clean ACCEPT — a genuine false-safe:
    per the document's own definitions, WE (the real buyer, "Vendor" in
    this document) actually bear the tax responsibility, violating the
    configured policy."""

    def test_defined_term_reversal_no_longer_silently_accepts(self):
        text = (
            "1. Definitions. In this Agreement, 'Customer' means Initech LLC, the entity "
            "that develops and provides the Software, and 'Vendor' means Umbrella Corp, the "
            "entity that purchases a subscription to the Software from Customer for its own "
            "internal use.\n\n"
            "7. Taxes. Vendor shall be responsible for all sales, use, and value-added taxes "
            "arising from this Agreement."
        )
        d = evaluate(text, contract_side="buy_side", require_tax_responsibility_counterparty=True)
        # PREVIOUS WRONG BEHAVIOR being prevented: a clean ACCEPT with
        # unresolved_facts == [] and explanation "No policy gaps found" —
        # a genuine false-safe under the benchmark suite's own definition
        # (a materially adverse term reaching ACCEPT).
        assert d.state != core.ACCEPT, (
            "role-reversal must not silently reach ACCEPT when the document's own "
            f"definitions put tax responsibility on us — got state={d.state} "
            f"unresolved_facts={d.unresolved_facts}"
        )
        if d.state == core.REQUIRES_REVIEW:
            assert d.unresolved_facts

    def test_ordinary_customer_vendor_tax_attribution_is_unaffected(self):
        # Positive control: conventional roles, no redefinition — Customer
        # (us, buy_side) bearing tax responsibility must still be flagged
        # exactly as before (MUST_REDLINE, per the existing logic), not
        # newly escalated to REQUIRES_REVIEW by the verification layer.
        text = (
            "6. Taxes. Customer shall be responsible for all sales, use, and value-added "
            "taxes arising from this Agreement."
        )
        d = evaluate(text, contract_side="buy_side", require_tax_responsibility_counterparty=True)
        assert d.state == core.MUST_REDLINE
        assert d.unresolved_facts == []
