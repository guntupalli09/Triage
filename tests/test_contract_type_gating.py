"""
Regression tests for the contract-type-blindness defects found while
test-driving the tool on a real executive employment agreement (see
rules_engine.py's _find_stated_currency_code and
_rule_applies_to_contract_type, and party_resolver.py's
VENDOR_CUSTOMER_CONTRACT_TYPES gate).

Three findings, one root cause: signals meaningful for one contract shape
(vendor/customer relationships, M&A-style rep-and-warranty indemnification)
were being applied to every document regardless of what it actually is.
Each test below pins the exact failure that was observed, not just the
mechanism, so a future refactor that reintroduces the underlying bug shape
fails loudly here instead of surfacing again on a customer's document.
"""

import pytest

from rules_engine import (
    RuleEngine,
    _extract_payment_terms,
    _find_stated_currency_code,
    _rule_applies_to_contract_type,
    Rule,
    Severity,
)
from metadata_extractor import classify_contract_type
from party_resolver import resolve_party_roles, UNKNOWN_ROLE, VENDOR_CUSTOMER_CONTRACT_TYPES


@pytest.fixture(scope="module")
def engine():
    return RuleEngine()


@pytest.fixture(scope="module")
def messy_employment_agreement():
    with open(
        "sample_contracts/messy_executive_employment_agreement.txt",
        encoding="utf-8",
    ) as f:
        return f.read()


class TestCurrencyGuard:
    """_find_stated_currency_code / _extract_payment_terms must not read a
    document's own defined-term abbreviation as a stated currency code."""

    def test_quoted_defined_term_is_not_read_as_currency(self):
        text = (
            'the Disclosing Party\'s customer drawings and/or Computer Aided '
            'Designs ("CAD"), Company employee information'
        )
        assert _find_stated_currency_code(text) is None

    def test_payment_terms_currency_is_none_for_the_same_text(self):
        text = (
            'confidential and proprietary information, including customer '
            'drawings and/or Computer Aided Designs ("CAD"), shall not be disclosed.'
        )
        terms = _extract_payment_terms(text)
        assert terms["currency"] is None

    def test_real_currency_mention_still_extracted(self):
        # A currency code actually used as a currency — no surrounding quote
        # marks around the token — must still be picked up. The guard is
        # specifically about the quoted-defined-term shape, not currency
        # detection in general.
        text = "All fees under this Agreement are payable in USD."
        assert _find_stated_currency_code(text) == "USD"

    def test_dollar_sign_amount_without_a_code_still_infers_usd(self):
        terms = _extract_payment_terms("Executive's base salary shall be $350,000 per year.")
        assert terms["currency"] == "USD"

    def test_full_pipeline_does_not_misread_cad_acronym_as_currency(self, engine):
        """End-to-end regression through the real engine.analyze() pipeline
        (normalization + extraction), not just the helper in isolation —
        this is the exact clause shape (a confidentiality clause listing
        "Computer Aided Designs" among protected information categories)
        that originally produced a CAD-as-Canadian-dollars misread."""
        text = (
            'MUTUAL NON-DISCLOSURE AGREEMENT\n\n'
            '1. Confidentiality. Confidential Information includes financial '
            'and marketing data, customer drawings and/or Computer Aided '
            'Designs ("CAD"), and other proprietary information disclosed by '
            'either party.\n\n'
            '2. Term. This Agreement remains in effect for two years.\n'
        )
        result = engine.analyze(text)
        assert result["payment_terms"]["currency"] is None


class TestContractTypeGate:
    """_rule_applies_to_contract_type must suppress vertical-specific rules
    (M&A, vendor/SaaS) on a document classified as something else, while
    never suppressing a general-purpose rule or an unclassified/low-
    confidence document."""

    def test_general_purpose_rule_always_applies(self):
        rule = Rule(
            rule_id="TEST_GENERAL_01", rule_name="test_general", title="t",
            severity=Severity.HIGH, rationale="r", pattern=r"x",
        )
        assert _rule_applies_to_contract_type(rule, "Employment Agreement", "high") is True
        assert _rule_applies_to_contract_type(rule, None, "low") is True

    def test_scoped_rule_applies_to_its_own_contract_type(self):
        rule = Rule(
            rule_id="TEST_SCOPED_01", rule_name="test_scoped", title="t",
            severity=Severity.HIGH, rationale="r", pattern=r"x",
            contract_types=("Asset / Stock Purchase Agreement",),
        )
        assert _rule_applies_to_contract_type(rule, "Asset / Stock Purchase Agreement", "high") is True

    def test_scoped_rule_suppressed_on_a_different_confidently_classified_type(self):
        rule = Rule(
            rule_id="TEST_SCOPED_02", rule_name="test_scoped", title="t",
            severity=Severity.HIGH, rationale="r", pattern=r"x",
            contract_types=("Asset / Stock Purchase Agreement",),
        )
        assert _rule_applies_to_contract_type(rule, "Employment Agreement", "high") is False

    def test_scoped_rule_not_suppressed_when_classification_is_unknown(self):
        rule = Rule(
            rule_id="TEST_SCOPED_03", rule_name="test_scoped", title="t",
            severity=Severity.HIGH, rationale="r", pattern=r"x",
            contract_types=("Asset / Stock Purchase Agreement",),
        )
        assert _rule_applies_to_contract_type(rule, None, "low") is True

    def test_scoped_rule_not_suppressed_when_confidence_is_low(self):
        rule = Rule(
            rule_id="TEST_SCOPED_04", rule_name="test_scoped", title="t",
            severity=Severity.HIGH, rationale="r", pattern=r"x",
            contract_types=("Asset / Stock Purchase Agreement",),
        )
        # Classified as something else, but with low confidence — under-
        # reporting is preferred to a confident wrong suppression.
        assert _rule_applies_to_contract_type(rule, "Employment Agreement", "low") is True

    def test_ma_indemnification_rule_is_scoped_away_from_employment_agreements(self, engine):
        """The exact regression: H_MA_INDEM_BASKET_MISSING_01 is an M&A
        rep-and-warranty rule that used to fire against an employment
        agreement's severance release because both of its topic phrases
        ("indemnif*", "representations and warranties") are common
        boilerplate independent of contract type."""
        ma_rule = next(r for r in engine.rules if r.rule_id == "H_MA_INDEM_BASKET_MISSING_01")
        assert ma_rule.contract_types is not None
        assert "Employment Agreement" not in ma_rule.contract_types

    def test_messy_employment_agreement_has_no_ma_indemnification_finding(self, engine, messy_employment_agreement):
        result = engine.analyze(messy_employment_agreement)
        fired_rule_ids = {f.rule_id for f in result["findings"]}
        assert "H_MA_INDEM_BASKET_MISSING_01" not in fired_rule_ids


class TestPartyRoleGate:
    """resolve_party_roles must not assign vendor/customer labels to a
    contract type that isn't shaped like a vendor/customer relationship —
    the exact regression was both parties in an employment agreement
    getting labeled "Vendor"."""

    def test_employment_agreement_type_is_outside_the_vendor_customer_allowlist(self):
        assert "Employment Agreement" not in VENDOR_CUSTOMER_CONTRACT_TYPES

    def test_employment_agreement_parties_resolve_to_unknown_role(self):
        text = (
            'This EMPLOYMENT AGREEMENT is made between Acme Holdings, Inc. '
            '(the "Company") and Jane Doe (the "Executive"). The Company '
            'shall provide certain benefits to the Executive, and the '
            'Executive shall perform his duties as an officer of the Company.'
        )
        role_map = resolve_party_roles(text, contract_type="Employment Agreement")
        assert role_map.role_of("Company") == UNKNOWN_ROLE
        assert role_map.role_of("Executive") == UNKNOWN_ROLE

    def test_vendor_customer_contract_type_still_resolves_roles(self):
        # The gate must not have become a blanket "never resolve roles" —
        # only non-vendor/customer-shaped types are exempted.
        text = (
            'This MASTER SERVICES AGREEMENT is between Provider Inc. (the '
            '"Vendor") and Client Corp (the "Customer"). Vendor shall provide '
            'the Services, and Customer shall pay all invoiced fees.'
        )
        role_map = resolve_party_roles(text, contract_type="Master Services Agreement")
        assert role_map.has_resolution()

    def test_messy_employment_agreement_has_no_vendor_or_customer_role(self, messy_employment_agreement):
        contract_type_result = classify_contract_type(messy_employment_agreement)
        role_map = resolve_party_roles(messy_employment_agreement, contract_type_result.contract_type)
        assert set(role_map.name_to_role.values()) <= {UNKNOWN_ROLE}
