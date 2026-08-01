"""
Tests for the Defined-Terms & Cross-Reference Integrity Checker — see
structure_checker.py.

Unit tests exercise analyze_structure() directly against synthetic contract
text. Integration tests exercise RuleEngine.analyze() end-to-end to confirm
the report is wired in as an additive layer, same pattern as
tests/test_workflow_decision.py and tests/test_risk_dashboard.py.
"""

from structure_checker import analyze_structure


class TestDefinitionClauseDetection:
    def test_defined_term_via_means_clause_is_counted(self):
        text = '"Confidential Information" means any information disclosed under this Agreement.'
        report = analyze_structure(text)
        assert report.defined_term_count == 1

    def test_short_form_name_is_counted_as_defined(self):
        text = 'This Agreement is between Acme Inc. ("Company") and the undersigned.'
        report = analyze_structure(text)
        assert report.defined_term_count == 1


class TestUnusedTerms:
    def test_term_defined_but_never_referenced_again_is_flagged(self):
        text = '"Widget" means a small mechanical device sold by the Company.'
        report = analyze_structure(text)
        assert any(i.term == "Widget" for i in report.unused_terms)

    def test_term_defined_and_referenced_elsewhere_is_not_flagged(self):
        text = (
            '"Confidential Information" means any information disclosed under this Agreement. '
            'The Receiving Party shall protect all Confidential Information from disclosure.'
        )
        report = analyze_structure(text)
        assert not any(i.term == "Confidential Information" for i in report.unused_terms)


class TestDuplicateDefinitions:
    def test_same_term_defined_twice_via_means_clause_is_flagged(self):
        text = (
            '"Effective Date" means the date first written above. '
            'Later in this document, "Effective Date" means the date of countersignature.'
        )
        report = analyze_structure(text)
        assert any(i.term == "Effective Date" for i in report.duplicate_definitions)

    def test_short_form_naming_used_twice_is_not_flagged_as_duplicate(self):
        # Two different parties each getting a short-form name is normal
        # drafting, not a duplicate definition.
        text = 'Between Acme Inc. ("Vendor") and Beta Corp ("Customer"), the parties agree...'
        report = analyze_structure(text)
        assert report.duplicate_definitions == []


class TestUsedButUndefined:
    def test_repeated_quoted_capitalized_phrase_with_no_definition_is_flagged(self):
        text = (
            'The parties shall exchange "Deliverables" as described herein. '
            'All "Deliverables" must be provided in writing.'
        )
        report = analyze_structure(text)
        assert any(i.term == "Deliverables" for i in report.used_but_undefined)

    def test_quoted_phrase_used_only_once_is_not_flagged(self):
        text = 'The parties shall exchange "Deliverables" as described herein.'
        report = analyze_structure(text)
        assert not any(i.term == "Deliverables" for i in report.used_but_undefined)

    def test_properly_defined_term_is_not_flagged_as_used_but_undefined(self):
        text = (
            '"Confidential Information" means any information disclosed under this Agreement. '
            'The Receiving Party shall protect all "Confidential Information" from disclosure.'
        )
        report = analyze_structure(text)
        assert not any(i.term == "Confidential Information" for i in report.used_but_undefined)


class TestCrossReferences:
    def test_reference_to_missing_section_is_flagged(self):
        text = 'The Receiving Party shall comply with the terms of Section 4.2.'
        report = analyze_structure(text)
        assert any(r.reference_text == "Section 4.2" for r in report.broken_cross_references)

    def test_reference_to_existing_section_is_not_flagged(self):
        text = (
            '4.2. Confidentiality Obligations. The Receiving Party shall protect all information.\n\n'
            'As described in Section 4.2, the obligations survive termination.'
        )
        report = analyze_structure(text)
        assert not any(r.reference_text == "Section 4.2" for r in report.broken_cross_references)

    def test_reference_to_missing_exhibit_is_flagged(self):
        text = 'Pricing shall be as set forth in Exhibit A.'
        report = analyze_structure(text)
        assert any(r.reference_text == "Exhibit A" for r in report.broken_cross_references)

    def test_reference_to_existing_exhibit_is_not_flagged(self):
        text = (
            'Pricing shall be as set forth in Exhibit A.\n\n'
            'EXHIBIT A\nPricing Schedule\n$500/month.'
        )
        report = analyze_structure(text)
        assert not any(r.reference_text == "Exhibit A" for r in report.broken_cross_references)

    def test_section_and_attachment_namespaces_are_independent(self):
        # A heading "EXHIBIT A" must not satisfy a reference to "Section A"
        # (nonsensical) or vice versa — the two are different namespaces.
        text = 'See Schedule 1 for details.\n\n1. Definitions. This is section one.'
        report = analyze_structure(text)
        assert any(r.reference_text == "Schedule 1" for r in report.broken_cross_references)


class TestEmptyAndCleanInput:
    def test_empty_document_has_no_issues(self):
        report = analyze_structure("")
        assert report.total_issue_count == 0
        assert report.defined_term_count == 0

    def test_well_drafted_snippet_has_no_issues(self):
        text = (
            '1. Definitions. "Confidential Information" means any non-public information disclosed '
            'by either party.\n\n'
            '2. Obligations. The Receiving Party shall protect all Confidential Information as '
            'described in Section 1.'
        )
        report = analyze_structure(text)
        assert report.total_issue_count == 0


class TestAsDict:
    def test_as_dict_has_expected_keys(self):
        report = analyze_structure('"Widget" means a device.')
        d = report.as_dict()
        assert set(d.keys()) == {
            "defined_term_count", "unused_terms", "duplicate_definitions",
            "used_but_undefined", "broken_cross_references", "total_issue_count",
            "methodology_note",
        }


class TestEndToEndIntegration:
    """The structure report must be wired into RuleEngine.analyze() as an
    additive layer — never replacing overall_risk or rule_counts."""

    def test_analyze_result_includes_structure_report(self, rule_engine):
        text = 'The Receiving Party shall comply with the terms of Section 4.2.'
        result = rule_engine.analyze(text)
        assert "structure_report" in result
        report = result["structure_report"]
        assert "broken_cross_references" in report
        assert any(r["reference_text"] == "Section 4.2" for r in report["broken_cross_references"])

    def test_overall_risk_is_unchanged_by_the_structure_report(self, rule_engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        result = rule_engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert "structure_report" in result

    def test_empty_document_has_zero_structure_issues(self, rule_engine):
        result = rule_engine.analyze("")
        assert result["structure_report"]["total_issue_count"] == 0
