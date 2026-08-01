"""
Tests for Deterministic Party, Effective-Date & Contract-Type Extraction —
see metadata_extractor.py.

Unit tests exercise the three extractors directly against synthetic
preamble text. Integration tests confirm the combined report is wired into
RuleEngine.analyze() as an additive layer, same pattern as
tests/test_risk_dashboard.py, tests/test_structure_checker.py, and
tests/test_clause_quality.py.
"""

from metadata_extractor import (
    classify_contract_type,
    extract_effective_date,
    extract_metadata,
    extract_parties,
)


class TestPartyExtraction:
    def test_two_parties_with_full_and_short_names_are_extracted(self):
        text = (
            'THIS AGREEMENT is made and entered into by and between '
            'Prevail InfoWorks, Inc., a Delaware corporation ("Prevail") and '
            'BriaCell Therapeutics Corp., a British Columbia corporation ("Company").'
        )
        parties = extract_parties(text)
        names = {p.short_name: p.full_name for p in parties}
        assert names["Prevail"] == "Prevail InfoWorks, Inc."
        assert names["Company"] == "BriaCell Therapeutics Corp."

    def test_full_name_does_not_swallow_preceding_boilerplate(self):
        # Regression: an earlier version captured "January 15, 2024 by and
        # between Prevail InfoWorks, Inc." as the "full name".
        text = (
            'THIS AGREEMENT is made and entered into as of January 15, 2024 '
            'by and between Prevail InfoWorks, Inc. ("Prevail") and Acme Corp. ("Acme").'
        )
        parties = extract_parties(text)
        prevail = next(p for p in parties if p.short_name == "Prevail")
        assert "January" not in prevail.full_name
        assert "between" not in prevail.full_name.lower()
        assert prevail.full_name == "Prevail InfoWorks, Inc."

    def test_entity_descriptor_clause_is_stripped_from_full_name(self):
        text = 'Between Acme Corp., a Delaware corporation ("Acme") and Beta LLC ("Beta").'
        parties = extract_parties(text)
        acme = next(p for p in parties if p.short_name == "Acme")
        assert "Delaware" not in acme.full_name
        assert acme.full_name == "Acme Corp."

    def test_no_parties_found_returns_empty_list(self):
        parties = extract_parties("This document contains no defined party names in quotes.")
        assert parties == []

    def test_generic_stop_words_are_not_treated_as_party_names(self):
        text = 'The parties agree that this document (the "Agreement") governs their relationship.'
        parties = extract_parties(text)
        assert parties == []

    def test_role_is_resolved_when_vendor_customer_cues_are_unambiguous(self):
        # Short defined names are conventionally single words ("Company",
        # "Vendor") — same convention party_resolver.py's own
        # _DEFINED_NAME_RE follows; a multi-word short name like "Vendor
        # Co" is not realistic drafting and correctly isn't matched.
        text = (
            'Between Acme Supply Co. ("Supplier") and Beta Buyer Inc. ("Purchaser"). '
            'Supplier shall provide and deliver goods. '
            'Purchaser shall purchase and agrees to pay the purchase price.'
        )
        parties = extract_parties(text)
        roles = {p.short_name: p.role for p in parties}
        assert roles["Supplier"] == "vendor"
        assert roles["Purchaser"] == "customer"

    def test_role_is_unknown_when_no_cues_present(self):
        text = 'Between Acme Corp. ("Acme") and Beta LLC ("Beta"), the parties agree as follows.'
        parties = extract_parties(text)
        assert all(p.role == "unknown" for p in parties)


class TestEffectiveDateExtraction:
    def test_explicit_effective_date_anchor_is_found(self):
        text = 'The Effective Date of this Agreement is January 5, 2024.'
        assert extract_effective_date(text) == "January 5, 2024"

    def test_effective_as_of_phrasing_is_found(self):
        text = 'This Agreement is effective as of March 12, 2023 between the parties.'
        assert extract_effective_date(text) == "March 12, 2023"

    def test_dated_as_of_phrasing_is_found(self):
        text = 'This Agreement, dated as of June 1, 2022, is between the parties.'
        assert extract_effective_date(text) == "June 1, 2022"

    def test_numeric_date_format_is_found(self):
        text = 'This Agreement is dated as of 03/04/2024.'
        assert extract_effective_date(text) == "03/04/2024"

    def test_no_date_present_returns_none(self):
        text = 'This Agreement governs the relationship between the parties.'
        assert extract_effective_date(text) is None

    def test_ambiguous_numeric_date_is_returned_verbatim_not_parsed(self):
        # 03/04/2024 could be March 4th or April 3rd — this function must
        # never silently resolve that ambiguity, only report the raw text.
        text = 'Dated 03/04/2024.'
        result = extract_effective_date(text)
        assert result == "03/04/2024"


class TestContractTypeClassification:
    def test_nda_is_classified_with_high_confidence(self):
        text = (
            "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
            "This Non-Disclosure Agreement governs the Disclosing Party and Receiving Party's "
            "exchange of confidential information."
        )
        result = classify_contract_type(text)
        assert result.contract_type == "Non-Disclosure / Confidentiality Agreement"
        assert result.confidence == "high"

    def test_franchise_agreement_is_classified(self):
        text = (
            "FRANCHISE AGREEMENT\n\nThis Franchise Agreement is between Franchisor and Franchisee. "
            "Franchisee shall pay a royalty fee to Franchisor."
        )
        result = classify_contract_type(text)
        assert result.contract_type == "Franchise Agreement"

    def test_credit_agreement_is_classified(self):
        text = (
            "CREDIT AGREEMENT\n\nThis Credit Agreement is between Borrower and Lender, evidenced by "
            "a Promissory Note."
        )
        result = classify_contract_type(text)
        assert result.contract_type == "Credit / Loan Agreement"

    def test_generic_text_with_no_signature_phrases_is_unclassified(self):
        text = "The parties agree to the following terms and conditions regarding their relationship."
        result = classify_contract_type(text)
        assert result.contract_type is None
        assert result.confidence == "low"

    def test_scores_dict_includes_every_known_type(self):
        result = classify_contract_type("Some contract text.")
        assert "Non-Disclosure / Confidentiality Agreement" in result.scores
        assert "Franchise Agreement" in result.scores
        assert len(result.scores) >= 15


class TestCombinedExtraction:
    def test_extract_metadata_returns_all_three(self):
        text = (
            'MASTER SERVICES AGREEMENT\n\n'
            'This Master Services Agreement is made and entered into as of January 15, 2024 '
            'by and between Prevail InfoWorks, Inc. ("Prevail") and Acme Corp. ("Acme").'
        )
        md = extract_metadata(text)
        assert len(md.parties) == 2
        assert md.effective_date == "January 15, 2024"
        assert md.contract_type_result.contract_type == "Master Services Agreement"

    def test_as_dict_has_expected_shape(self):
        md = extract_metadata("This Agreement governs the parties' relationship.")
        d = md.as_dict()
        assert set(d.keys()) == {"parties", "effective_date", "contract_type", "contract_type_confidence"}
        assert isinstance(d["parties"], list)


class TestEndToEndIntegration:
    """metadata must be wired into RuleEngine.analyze() as an additive
    layer — never replacing overall_risk, rule_counts, or any existing key."""

    def test_analyze_result_includes_metadata(self, rule_engine):
        text = (
            'MASTER SERVICES AGREEMENT\n\n'
            'This Master Services Agreement is made and entered into as of January 15, 2024 '
            'by and between Prevail InfoWorks, Inc. ("Prevail") and Acme Corp. ("Acme").'
        )
        result = rule_engine.analyze(text)
        assert "metadata" in result
        md = result["metadata"]
        assert md["contract_type"] == "Master Services Agreement"
        assert md["effective_date"] == "January 15, 2024"
        assert len(md["parties"]) == 2

    def test_overall_risk_is_unchanged_by_metadata(self, rule_engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        result = rule_engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert "metadata" in result

    def test_document_with_no_extractable_metadata_returns_empty_not_error(self, rule_engine):
        result = rule_engine.analyze("")
        md = result["metadata"]
        assert md["parties"] == []
        assert md["effective_date"] is None
        assert md["contract_type"] is None
