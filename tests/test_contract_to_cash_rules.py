"""
Regression tests for the contract-to-cash rules added for Agree.com:
payment/invoice configuration, pricing ambiguity, signature/execution
defects, and termination-to-billing consequences.
"""

import pytest
from rules_engine import RuleEngine, Severity, FindingType, _extract_payment_terms


@pytest.fixture
def engine():
    return RuleEngine()


class TestStructuredPaymentTermsExtraction:
    def test_extracts_all_fields_from_well_specified_contract(self):
        text = (
            "Customer shall pay all invoiced amounts within Net 30 days in "
            "USD. Invoices shall be issued monthly following service activation."
        )
        terms = _extract_payment_terms(text)
        assert terms == {
            "due_days": 30,
            "currency": "USD",
            "billing_frequency": "monthly",
            "invoice_trigger": "activation",
        }

    def test_missing_fields_are_none_not_guessed(self):
        text = "This Agreement governs the provision of consulting services."
        terms = _extract_payment_terms(text)
        assert terms["due_days"] is None
        assert terms["currency"] is None
        assert terms["billing_frequency"] is None
        assert terms["invoice_trigger"] is None

    def test_bare_dollar_sign_defaults_to_usd(self):
        terms = _extract_payment_terms("The fee is $1,000 per month.")
        assert terms["currency"] == "USD"

    def test_euro_symbol_detected(self):
        terms = _extract_payment_terms("The fee is €1,000 per month.")
        assert terms["currency"] == "EUR"

    def test_payment_terms_available_via_analyze(self, engine):
        text = "Customer shall pay all fees within Net 15 days in EUR, billed quarterly."
        result = engine.analyze(text)
        assert result["payment_terms"]["due_days"] == 15
        assert result["payment_terms"]["currency"] == "EUR"
        assert result["payment_terms"]["billing_frequency"] == "quarterly"


class TestBillingAndPriceConflicts:
    def test_conflicting_net_days_flagged_high(self, engine):
        text = (
            "Payment shall be due Net 30 days from invoice. Notwithstanding "
            "the foregoing, all invoices are due Net 60 days from receipt."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_BILLING_CONFLICT_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH
        assert "30" in findings[0].rationale and "60" in findings[0].rationale

    def test_single_net_days_term_does_not_conflict(self, engine):
        text = "Payment shall be due Net 30 days from invoice date."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_BILLING_CONFLICT_01"]
        assert len(findings) == 0

    def test_conflicting_total_price_flagged_high(self, engine):
        text = (
            "The total contract price is $50,000. Elsewhere, the total "
            "contract fee is $75,000, payable in full."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_PRICE_CONFLICT_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_single_price_does_not_conflict(self, engine):
        text = "The total contract price is $50,000, payable in full upon signature."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_PRICE_CONFLICT_01"]
        assert len(findings) == 0


class TestPartyIdentityAndSignatureDefects:
    def test_inconsistent_entity_name_flagged(self, engine):
        text = (
            "This Agreement is entered into by Acme Corp, a Delaware "
            "corporation (\"Vendor\"). IN WITNESS WHEREOF, the parties have "
            "executed this Agreement. By: ____ Name: John Smith Title: CEO "
            "Company: Acme Corporation, a Delaware corporation. "
            "By: ____ Name: Jane Doe Title: CFO"
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_PARTY_IDENTITY_CONFLICT_01"]
        assert len(findings) == 1
        assert "Acme Corp" in findings[0].rationale

    def test_consistent_entity_name_does_not_flag(self, engine):
        text = (
            "This Agreement is entered into by Acme Corp, a Delaware "
            "corporation (\"Vendor\"). IN WITNESS WHEREOF, the parties have "
            "executed this Agreement. By: ____ Name: John Smith Title: CEO "
            "Company: Acme Corp, a Delaware corporation. "
            "By: ____ Name: Jane Doe Title: CFO"
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_PARTY_IDENTITY_CONFLICT_01"]
        assert len(findings) == 0

    def test_missing_second_signature_block_flagged(self, engine):
        text = (
            "IN WITNESS WHEREOF, the parties have executed this Agreement "
            "as of the date first written above. By: ____ Name: John Smith"
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_SIGNATURE_PARTY_MISSING_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_two_signature_blocks_does_not_flag(self, engine):
        text = (
            "IN WITNESS WHEREOF, the parties have executed this Agreement. "
            "By: ____ Name: John Smith Title: CEO "
            "By: ____ Name: Jane Doe Title: CFO"
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_SIGNATURE_PARTY_MISSING_01"]
        assert len(findings) == 0

    def test_blank_effective_date_flagged(self, engine):
        text = "This Agreement is entered into as of the Effective Date: ____, by and between the parties hereto."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_EFFECTIVE_DATE_MISSING_01"]
        assert len(findings) == 1

    def test_filled_effective_date_does_not_flag(self, engine):
        text = "This Agreement is entered into as of the Effective Date: January 1, 2026, by and between the parties hereto."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_EFFECTIVE_DATE_MISSING_01"]
        assert len(findings) == 0

    def test_blank_signatory_title_flagged(self, engine):
        text = "IN WITNESS WHEREOF, the parties execute this Agreement. By: ____ Name: John Smith Title: ____"
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_AUTHORITY_REP_01"]
        assert len(findings) == 1

    def test_present_title_does_not_flag(self, engine):
        text = "IN WITNESS WHEREOF, the parties execute this Agreement by their duly authorized representatives. By: ____ Name: John Smith Title: CEO"
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_AUTHORITY_REP_01"]
        assert len(findings) == 0

    def test_counterparts_esign_language_detected(self, engine):
        text = "This Agreement may be executed in counterparts, each of which shall be deemed an original, and delivered via electronic signature."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "L_COUNTERPARTS_ESIGN_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.LOW


class TestTerminationToBillingConsequences:
    def test_payment_acceleration_on_breach_flagged(self, engine):
        text = (
            "Upon termination of this Agreement for breach, all remaining "
            "fees shall immediately become due and payable in full."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_PAYMENT_ACCELERATION_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_post_termination_billing_flagged(self, engine):
        text = (
            "Following termination of this Agreement, Customer shall remain "
            "liable for fees and Provider shall continue to bill Customer monthly."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_POST_TERMINATION_BILLING_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_prepaid_fees_non_refundable_flagged(self, engine):
        text = "All prepaid fees paid by Customer are non-refundable upon early termination of this Agreement for any reason."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_PREPAID_FEES_REFUND_01"]
        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.ADVERSE_LANGUAGE_DETECTED.value

    def test_prorata_refund_language_does_not_flag(self, engine):
        text = "All prepaid fees shall be refunded on a pro-rata basis upon early termination of this Agreement."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_PREPAID_FEES_REFUND_01"]
        assert len(findings) == 0

    def test_early_termination_fee_flagged(self, engine):
        text = "In the event of early termination by Customer, Customer shall pay an early termination fee equal to 50% of remaining fees."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_EARLY_TERMINATION_FEE_01"]
        assert len(findings) == 1


class TestPricingAmbiguityRules:
    def test_price_referenced_only_in_unattached_exhibit_flagged(self, engine):
        text = "Pricing for the Services is set forth in Exhibit A attached hereto, which governs all fees due under this Agreement."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_PRICE_EXHIBIT_MISSING_01"]
        assert len(findings) == 1

    def test_exhibit_actually_included_does_not_flag(self, engine):
        text = (
            "Pricing for the Services is set forth in Exhibit A attached "
            "hereto. EXHIBIT A - PRICING SCHEDULE: Monthly fee is $500 per "
            "user as described in Exhibit A."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_PRICE_EXHIBIT_MISSING_01"]
        assert len(findings) == 0

    def test_unbounded_expense_reimbursement_flagged(self, engine):
        text = "Customer shall reimburse Provider for all reasonable travel expenses incurred without any limit or approval requirement."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_EXPENSE_APPROVAL_01"]
        assert len(findings) == 1

    def test_capped_reimbursement_with_approval_does_not_flag(self, engine):
        text = "Customer shall reimburse Provider for travel expenses, not to exceed $500 per trip, with prior written approval required."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_EXPENSE_APPROVAL_01"]
        assert len(findings) == 0

    def test_usage_charges_without_measurement_method_flagged(self, engine):
        text = "Usage charges shall apply as determined in Provider's sole discretion for the applicable billing period."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_USAGE_MEASUREMENT_01"]
        assert len(findings) == 1

    def test_usage_charges_with_measurement_method_does_not_flag(self, engine):
        text = "Usage charges shall apply and are measured by the number of API calls made during the applicable billing period."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_USAGE_MEASUREMENT_01"]
        assert len(findings) == 0

    def test_open_ended_discount_flagged(self, engine):
        text = "Customer shall receive a 20% discount on all fees, with no expiration, for the duration of this Agreement."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_DISCOUNT_EXPIRY_01"]
        assert len(findings) == 1

    def test_time_bound_discount_does_not_flag(self, engine):
        text = "Customer shall receive a 20% discount on fees for the first 12 months of this Agreement."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_DISCOUNT_EXPIRY_01"]
        assert len(findings) == 0


class TestInvoiceConfigurationRules:
    def test_missing_invoice_trigger_flagged(self, engine):
        text = (
            "Customer shall pay Provider a monthly fee for the Services. "
            "Invoicing shall commence at a date to be determined."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_PAYMENT_TRIGGER_01"]
        assert len(findings) == 1

    def test_defined_invoice_trigger_does_not_flag(self, engine):
        text = (
            "Customer shall pay Provider a monthly fee. Invoicing shall "
            "commence following service activation for the Services "
            "described herein."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_PAYMENT_TRIGGER_01"]
        assert len(findings) == 0

    def test_missing_billing_frequency_flagged(self, engine):
        text = "Customer shall pay Provider a fee of $5,000 for the Services described herein under this Agreement executed by the parties."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_BILLING_FREQUENCY_01"]
        assert len(findings) == 1

    def test_defined_billing_frequency_does_not_flag(self, engine):
        text = "Customer shall pay Provider a fee of $5,000 monthly for the Services described in this Agreement."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_BILLING_FREQUENCY_01"]
        assert len(findings) == 0

    def test_ambiguous_currency_flagged(self, engine):
        text = "The total fee is $10,000 payable upon signature. This Agreement governs the services described herein and remains subject to review."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_CURRENCY_AMBIGUOUS_01"]
        assert len(findings) == 1

    def test_explicit_currency_does_not_flag(self, engine):
        text = "The total fee is $10,000 USD payable upon signature of this Agreement by the parties hereto."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_CURRENCY_AMBIGUOUS_01"]
        assert len(findings) == 0


class TestFindingTypesAreCorrectlyDistinguished:
    def test_conflict_findings_are_adverse_language_detected(self, engine):
        text = "Payment shall be due Net 30 days from invoice. Notwithstanding the foregoing, all invoices are due Net 60 days from receipt."
        result = engine.analyze(text)
        f = [f for f in result["findings"] if f.rule_id == "H_BILLING_CONFLICT_01"][0]
        assert f.finding_type == FindingType.ADVERSE_LANGUAGE_DETECTED.value

    def test_silent_currency_gap_is_expected_protection_not_found(self, engine):
        # Long enough document to trust the negative result.
        text = (
            "This is a Software as a Service Agreement between Provider and "
            "Customer for the license and use of the Provider's platform. "
            "Customer shall pay Provider a fee of $10,000 for the Services "
            "described in this Agreement, in consideration for access to the "
            "platform throughout the term hereof, subject to the terms and "
            "conditions set forth herein."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_CURRENCY_AMBIGUOUS_01"]
        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.EXPECTED_PROTECTION_NOT_FOUND.value
