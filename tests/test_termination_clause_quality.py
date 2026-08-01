"""
Tests for the Deterministic Clause Quality Engine — Termination module.
See clause_quality.py's analyze_termination_clause().
"""

from clause_quality import analyze_termination_clause


class TestNotApplicable:
    def test_document_with_no_termination_topic_is_not_applicable(self):
        text = "This Agreement governs the provision of services between the parties."
        report = analyze_termination_clause(text)
        assert report.applicable is False
        assert report.score is None
        assert report.elements == []


class TestWellDraftedClause:
    def test_fully_specified_clause_scores_100(self):
        text = (
            "TERMINATION. Either party may terminate this Agreement for cause upon material breach "
            "by the other party, provided the breaching party fails to cure such breach within 30 "
            "days after written notice. Either party may terminate this Agreement for convenience "
            "upon 60 days prior written notice. Either party may terminate immediately upon the "
            "other party's bankruptcy or insolvency. Sections 5 (Confidentiality) and 8 (Limitation "
            "of Liability) shall survive termination."
        )
        report = analyze_termination_clause(text)
        assert report.applicable is True
        assert report.score == 100
        assert all(e.present for e in report.elements)

    def test_notice_period_after_notice_phrasing_is_recognized(self):
        # Regression: "30 days AFTER written notice" — the original
        # pattern only matched "N days [prior] [written] notice" and
        # missed the equally common "days after/following notice" form.
        text = "TERMINATION. The breaching party shall have 30 days after written notice to cure."
        report = analyze_termination_clause(text)
        notice = next(e for e in report.elements if e.key == "notice_period_specified")
        assert notice.present is True


class TestSparseClause:
    def test_bare_termination_mention_has_low_score(self):
        text = "This Agreement may be terminated by either party."
        report = analyze_termination_clause(text)
        assert report.applicable is True
        assert report.score < 50


class TestIndividualElements:
    def test_cure_period_is_detected(self):
        text = "TERMINATION. Upon breach, the non-breaching party may terminate if the breach is not cured within 15 days."
        report = analyze_termination_clause(text)
        cure = next(e for e in report.elements if e.key == "cure_period")
        assert cure.present is True

    def test_no_cure_period_is_not_flagged_present(self):
        text = "TERMINATION. This Agreement may be terminated for cause upon material breach."
        report = analyze_termination_clause(text)
        cure = next(e for e in report.elements if e.key == "cure_period")
        assert cure.present is False

    def test_survival_clause_is_detected(self):
        text = "TERMINATION. The confidentiality obligations shall survive termination of this Agreement."
        report = analyze_termination_clause(text)
        survival = next(e for e in report.elements if e.key == "survival_clause")
        assert survival.present is True

    def test_bankruptcy_termination_is_detected(self):
        text = "TERMINATION. Either party may terminate this Agreement upon the other party's bankruptcy."
        report = analyze_termination_clause(text)
        bankruptcy = next(e for e in report.elements if e.key == "bankruptcy_termination")
        assert bankruptcy.present is True

    def test_termination_for_convenience_is_detected(self):
        text = "TERMINATION. Either party may terminate this Agreement for convenience upon 30 days notice."
        report = analyze_termination_clause(text)
        convenience = next(e for e in report.elements if e.key == "termination_for_convenience")
        assert convenience.present is True


class TestAsDict:
    def test_as_dict_has_expected_shape(self):
        text = "TERMINATION. This Agreement may be terminated by either party."
        report = analyze_termination_clause(text)
        d = report.as_dict()
        assert set(d.keys()) == {"applicable", "score", "elements", "methodology_note"}
        assert len(d["elements"]) == 6

    def test_as_dict_for_not_applicable_case(self):
        d = analyze_termination_clause("This Agreement governs the services.").as_dict()
        assert d["applicable"] is False
        assert d["score"] is None


class TestEndToEndIntegration:
    def test_analyze_result_includes_termination_clause_quality(self, rule_engine):
        text = "TERMINATION. Either party may terminate this Agreement for cause upon material breach."
        result = rule_engine.analyze(text)
        assert "termination" in result["clause_quality"]
        assert result["clause_quality"]["termination"]["applicable"] is True

    def test_document_without_termination_topic_is_not_applicable_end_to_end(self, rule_engine):
        text = "This Agreement governs the provision of services between the parties."
        result = rule_engine.analyze(text)
        assert result["clause_quality"]["termination"]["applicable"] is False

    def test_overall_risk_is_unchanged(self, rule_engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        result = rule_engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert "clause_quality" in result
