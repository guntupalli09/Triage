"""
Tests for the Deterministic Clause Quality Engine — Indemnification module.
See clause_quality.py's analyze_indemnification_clause().
"""

from clause_quality import analyze_indemnification_clause


class TestNotApplicable:
    def test_document_with_no_indemnification_topic_is_not_applicable(self):
        text = "This Agreement governs the provision of services between the parties."
        report = analyze_indemnification_clause(text)
        assert report.applicable is False
        assert report.score is None
        assert report.elements == []


class TestWellDraftedClause:
    def test_fully_specified_clause_scores_100(self):
        text = (
            "INDEMNIFICATION. Either party shall defend, indemnify, and hold harmless the other "
            "party from and against any third-party claims arising from infringement of "
            "intellectual property rights. The indemnified party shall provide prompt written "
            "notice of any claim. The indemnifying party shall have sole control of the defense, "
            "and shall not settle any claim without the prior written consent of the indemnified "
            "party."
        )
        report = analyze_indemnification_clause(text)
        assert report.applicable is True
        assert report.score == 100
        assert all(e.present for e in report.elements)

    def test_mutual_language_with_defend_inserted_is_recognized(self):
        # Regression: "Either party SHALL DEFEND, indemnify..." — the
        # original pattern required "shall" immediately followed by
        # "indemnify" and missed this extremely standard "shall defend,
        # indemnify, and hold harmless" phrasing.
        text = "INDEMNIFICATION. Either party shall defend, indemnify, and hold harmless the other party."
        report = analyze_indemnification_clause(text)
        mutual = next(e for e in report.elements if e.key == "mutual_or_reciprocal")
        assert mutual.present is True


class TestSparseClause:
    def test_bare_indemnification_mention_has_low_score(self):
        text = "The Contractor shall indemnify the Client for all claims."
        report = analyze_indemnification_clause(text)
        assert report.applicable is True
        assert report.score < 50


class TestIndividualElements:
    def test_one_sided_indemnity_is_not_mutual(self):
        text = "INDEMNIFICATION. Vendor shall indemnify Customer for all claims arising from this Agreement."
        report = analyze_indemnification_clause(text)
        mutual = next(e for e in report.elements if e.key == "mutual_or_reciprocal")
        assert mutual.present is False

    def test_ip_indemnity_is_detected(self):
        text = "INDEMNIFICATION. Vendor shall indemnify Customer for claims of intellectual property infringement."
        report = analyze_indemnification_clause(text)
        ip = next(e for e in report.elements if e.key == "ip_indemnity")
        assert ip.present is True

    def test_third_party_scope_is_detected(self):
        text = "INDEMNIFICATION. Vendor shall indemnify Customer against third-party claims."
        report = analyze_indemnification_clause(text)
        scope = next(e for e in report.elements if e.key == "third_party_claims_scope")
        assert scope.present is True

    def test_defense_obligation_is_detected(self):
        text = "INDEMNIFICATION. Vendor shall defend and indemnify Customer for all claims."
        report = analyze_indemnification_clause(text)
        defense = next(e for e in report.elements if e.key == "defense_obligation")
        assert defense.present is True

    def test_no_defense_obligation_is_not_flagged_present(self):
        text = "INDEMNIFICATION. Vendor shall indemnify Customer for all claims arising from this Agreement."
        report = analyze_indemnification_clause(text)
        defense = next(e for e in report.elements if e.key == "defense_obligation")
        assert defense.present is False


class TestAsDict:
    def test_as_dict_has_expected_shape(self):
        text = "INDEMNIFICATION. Vendor shall indemnify Customer for all claims."
        report = analyze_indemnification_clause(text)
        d = report.as_dict()
        assert set(d.keys()) == {"applicable", "score", "elements", "methodology_note"}
        assert len(d["elements"]) == 6

    def test_as_dict_for_not_applicable_case(self):
        d = analyze_indemnification_clause("This Agreement governs the services.").as_dict()
        assert d["applicable"] is False
        assert d["score"] is None


class TestEndToEndIntegration:
    def test_analyze_result_includes_indemnification_clause_quality(self, rule_engine):
        text = "INDEMNIFICATION. Either party shall defend, indemnify, and hold harmless the other party."
        result = rule_engine.analyze(text)
        assert "indemnification" in result["clause_quality"]
        assert result["clause_quality"]["indemnification"]["applicable"] is True

    def test_document_without_indemnification_topic_is_not_applicable_end_to_end(self, rule_engine):
        text = "This Agreement governs the provision of services between the parties."
        result = rule_engine.analyze(text)
        assert result["clause_quality"]["indemnification"]["applicable"] is False

    def test_overall_risk_is_unchanged(self, rule_engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        result = rule_engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert "clause_quality" in result

    def test_h_indem_01_still_fires_alongside_clause_quality(self, rule_engine):
        text = "The Contractor shall indemnify the Client without limit for all claims."
        result = rule_engine.analyze(text)
        rule_ids = {f.rule_id for f in result["findings"]}
        assert "H_INDEM_01" in rule_ids
