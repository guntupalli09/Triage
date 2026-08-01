"""
Tests for the Deterministic Clause Quality Engine — Intellectual Property
module. See clause_quality.py's analyze_ip_clause().
"""

from clause_quality import analyze_ip_clause


class TestNotApplicable:
    def test_document_with_no_ip_topic_is_not_applicable(self):
        text = "This Agreement governs the provision of services between the parties."
        report = analyze_ip_clause(text)
        assert report.applicable is False
        assert report.score is None
        assert report.elements == []


class TestWellDraftedClause:
    def test_fully_specified_clause_scores_100(self):
        text = (
            "INTELLECTUAL PROPERTY. All work product created under this Agreement shall be owned "
            "by Client. Contractor hereby assigns all right, title, and interest in the work "
            "product to Client. Each party's background intellectual property that pre-exists this "
            "Agreement shall remain the property of that party. Client hereby grants Contractor a "
            "non-exclusive license to use Client's pre-existing materials solely to perform the "
            "Services. Any derivative works based on Contractor's background IP shall be owned by "
            "Contractor. The parties acknowledge that source code developed hereunder shall be "
            "delivered to Client."
        )
        report = analyze_ip_clause(text)
        assert report.applicable is True
        assert report.score == 100
        assert all(e.present for e in report.elements)


class TestSparseClause:
    def test_bare_ip_mention_has_low_score(self):
        text = "The parties acknowledge that intellectual property may be created under this Agreement."
        report = analyze_ip_clause(text)
        assert report.applicable is True
        assert report.score < 50


class TestIndividualElements:
    def test_ownership_statement_is_detected(self):
        text = "INTELLECTUAL PROPERTY. All work product shall be owned by Client."
        report = analyze_ip_clause(text)
        ownership = next(e for e in report.elements if e.key == "ownership_clearly_stated")
        assert ownership.present is True

    def test_background_ip_reservation_is_detected(self):
        text = "INTELLECTUAL PROPERTY. Each party's background intellectual property shall remain its own property."
        report = analyze_ip_clause(text)
        background = next(e for e in report.elements if e.key == "background_ip_reserved")
        assert background.present is True

    def test_no_background_ip_reservation_is_not_flagged_present(self):
        text = "INTELLECTUAL PROPERTY. All work product shall be owned by Client."
        report = analyze_ip_clause(text)
        background = next(e for e in report.elements if e.key == "background_ip_reserved")
        assert background.present is False

    def test_assignment_language_is_detected(self):
        text = "INTELLECTUAL PROPERTY. Contractor hereby assigns all right, title, and interest to Client."
        report = analyze_ip_clause(text)
        assignment = next(e for e in report.elements if e.key == "assignment_language_present")
        assert assignment.present is True

    def test_license_grant_is_detected(self):
        text = "INTELLECTUAL PROPERTY. Client hereby grants Contractor a non-exclusive license to use the Software."
        report = analyze_ip_clause(text)
        license_grant = next(e for e in report.elements if e.key == "license_grant_present")
        assert license_grant.present is True

    def test_source_code_is_lower_weight_and_context_specific(self):
        text = "INTELLECTUAL PROPERTY. All work product shall be owned by Client."
        report = analyze_ip_clause(text)
        source_code = next(e for e in report.elements if e.key == "source_code_ownership_addressed")
        assert source_code.present is False
        assert source_code.weight == 10


class TestAsDict:
    def test_as_dict_has_expected_shape(self):
        text = "INTELLECTUAL PROPERTY. All work product shall be owned by Client."
        report = analyze_ip_clause(text)
        d = report.as_dict()
        assert set(d.keys()) == {"applicable", "score", "elements", "methodology_note"}
        assert len(d["elements"]) == 6

    def test_as_dict_for_not_applicable_case(self):
        d = analyze_ip_clause("This Agreement governs the services.").as_dict()
        assert d["applicable"] is False
        assert d["score"] is None


class TestEndToEndIntegration:
    def test_analyze_result_includes_ip_clause_quality(self, rule_engine):
        text = "INTELLECTUAL PROPERTY. All work product shall be owned by Client."
        result = rule_engine.analyze(text)
        assert "ip" in result["clause_quality"]
        assert result["clause_quality"]["ip"]["applicable"] is True

    def test_document_without_ip_topic_is_not_applicable_end_to_end(self, rule_engine):
        text = "This Agreement governs the provision of services between the parties."
        result = rule_engine.analyze(text)
        assert result["clause_quality"]["ip"]["applicable"] is False

    def test_overall_risk_is_unchanged(self, rule_engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        result = rule_engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert "clause_quality" in result
