"""
Tests for the Deterministic Clause Quality Engine — Confidentiality module.
See clause_quality.py's analyze_confidentiality_clause().
"""

from clause_quality import analyze_confidentiality_clause


class TestNotApplicable:
    def test_document_with_no_confidentiality_topic_is_not_applicable(self):
        text = "This Agreement governs the provision of services between the parties."
        report = analyze_confidentiality_clause(text)
        assert report.applicable is False
        assert report.score is None
        assert report.elements == []


class TestWellDraftedClause:
    def test_fully_specified_clause_scores_100(self):
        text = (
            'CONFIDENTIALITY. "Confidential Information" means any non-public information disclosed '
            'by either party. The obligations of confidentiality shall not apply to information that '
            'is publicly available, was already known to the Receiving Party prior to disclosure, is '
            'independently developed without use of Confidential Information, or is received from a '
            'third party without breach of any obligation. This obligation shall survive for a period '
            'of 5 years following termination. Upon termination, the Receiving Party shall return or '
            'destroy all Confidential Information. Nothing herein prohibits disclosure required by law '
            'or court order. The Receiving Party may retain residual knowledge in unaided memory.'
        )
        report = analyze_confidentiality_clause(text)
        assert report.applicable is True
        assert report.score == 100
        assert all(e.present for e in report.elements)

    def test_elements_survive_a_line_break_inside_the_proximity_window(self):
        text = (
            "CONFIDENTIALITY. \"Confidential Information\" means non-public information.\n"
            "The Receiving Party shall return or destroy all Confidential\n"
            "Information upon termination. Disclosure required by law or\n"
            "court order is permitted."
        )
        report = analyze_confidentiality_clause(text)
        return_destroy = next(e for e in report.elements if e.key == "return_or_destruction")
        gov = next(e for e in report.elements if e.key == "government_disclosure_carveout")
        assert return_destroy.present is True
        assert gov.present is True


class TestSparseClause:
    def test_bare_confidentiality_mention_has_zero_score(self):
        text = "The parties agree to keep information confidential."
        report = analyze_confidentiality_clause(text)
        assert report.applicable is True
        assert report.score == 0


class TestStandardExceptions:
    def test_all_four_exceptions_present_counts_as_present(self):
        text = (
            "CONFIDENTIALITY. Obligations do not apply to information that is publicly available, "
            "was already known to the Receiving Party prior to disclosure, is independently developed, "
            "or is received from a third party without breach of any obligation."
        )
        report = analyze_confidentiality_clause(text)
        exceptions = next(e for e in report.elements if e.key == "standard_exceptions")
        assert exceptions.present is True

    def test_only_one_of_four_exceptions_does_not_meet_threshold(self):
        text = "CONFIDENTIALITY. Obligations do not apply to information that is publicly available."
        report = analyze_confidentiality_clause(text)
        exceptions = next(e for e in report.elements if e.key == "standard_exceptions")
        assert exceptions.present is False
        assert "1 of the 4" in exceptions.detail

    def test_zero_exceptions_is_reported_in_detail(self):
        text = "CONFIDENTIALITY. The Receiving Party shall keep all information confidential."
        report = analyze_confidentiality_clause(text)
        exceptions = next(e for e in report.elements if e.key == "standard_exceptions")
        assert "0 of the 4" in exceptions.detail


class TestIndividualElements:
    def test_definition_is_detected(self):
        text = 'CONFIDENTIALITY. "Confidential Information" means any information disclosed under this Agreement.'
        report = analyze_confidentiality_clause(text)
        definition = next(e for e in report.elements if e.key == "definition_present")
        assert definition.present is True

    def test_duration_is_detected(self):
        text = "CONFIDENTIALITY. This obligation shall survive for a period of 3 years following termination."
        report = analyze_confidentiality_clause(text)
        duration = next(e for e in report.elements if e.key == "duration_specified")
        assert duration.present is True

    def test_no_duration_is_not_flagged_as_present(self):
        text = "CONFIDENTIALITY. The parties shall keep all information confidential indefinitely."
        report = analyze_confidentiality_clause(text)
        duration = next(e for e in report.elements if e.key == "duration_specified")
        assert duration.present is False


class TestAsDict:
    def test_as_dict_has_expected_shape(self):
        text = "CONFIDENTIALITY. The parties shall keep information confidential."
        report = analyze_confidentiality_clause(text)
        d = report.as_dict()
        assert set(d.keys()) == {"applicable", "score", "elements", "methodology_note"}
        assert len(d["elements"]) == 6


class TestEndToEndIntegration:
    def test_analyze_result_includes_confidentiality_clause_quality(self, rule_engine):
        text = (
            'CONFIDENTIALITY. "Confidential Information" means non-public information disclosed by '
            'either party.'
        )
        result = rule_engine.analyze(text)
        assert "confidentiality" in result["clause_quality"]
        assert result["clause_quality"]["confidentiality"]["applicable"] is True

    def test_document_without_confidentiality_topic_is_not_applicable_end_to_end(self, rule_engine):
        text = "This Agreement governs the provision of services between the parties."
        result = rule_engine.analyze(text)
        assert result["clause_quality"]["confidentiality"]["applicable"] is False

    def test_overall_risk_is_unchanged(self, rule_engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        result = rule_engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert "clause_quality" in result
