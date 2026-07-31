"""
Tests for the Deterministic Clause Quality Engine — Arbitration module.
See clause_quality.py.

Unit tests exercise analyze_arbitration_clause() directly against synthetic
text. Integration tests confirm the report is wired into
RuleEngine.analyze() as an additive layer, same pattern as
tests/test_risk_dashboard.py and tests/test_structure_checker.py.
"""

from clause_quality import analyze_arbitration_clause


class TestNotApplicable:
    def test_document_with_no_arbitration_clause_is_not_applicable(self):
        text = "This Agreement shall be governed by the laws of the State of Delaware."
        report = analyze_arbitration_clause(text)
        assert report.applicable is False
        assert report.score is None
        assert report.elements == []

    def test_litigation_only_contract_is_not_penalized(self):
        # Choosing litigation over arbitration is a legitimate drafting
        # choice, not a deficiency — score must be None, not 0.
        text = "The parties submit to the exclusive jurisdiction of the courts of New York."
        report = analyze_arbitration_clause(text)
        assert report.applicable is False
        assert report.score is None


class TestCompleteClause:
    def test_fully_specified_arbitration_clause_scores_100(self):
        text = (
            "Any dispute arising out of this Agreement shall be settled by mandatory arbitration "
            "administered by the American Arbitration Association in accordance with its Commercial "
            "Arbitration Rules. The arbitration shall be conducted by one arbitrator. The seat of "
            "arbitration shall be New York, New York. The language of the arbitration shall be English. "
            "The parties may seek emergency relief from an emergency arbitrator."
        )
        report = analyze_arbitration_clause(text)
        assert report.applicable is True
        assert report.score == 100
        assert all(e.present for e in report.elements)


class TestSparseClause:
    def test_bare_arbitration_mention_scores_only_no_conflict_credit(self):
        # No conflicting exclusive-litigation clause is itself an absent-
        # deficiency element (5 pts) — it's the one element that's "present"
        # by default whenever there's nothing contradicting the arbitration
        # clause, so even a bare mention scores 5, not 0.
        text = "Any dispute shall be settled by binding arbitration."
        report = analyze_arbitration_clause(text)
        assert report.applicable is True
        assert report.score == 5
        substantive_elements = [e for e in report.elements if e.key != "no_litigation_conflict"]
        assert not any(e.present for e in substantive_elements)

    def test_institution_named_but_nothing_else_scores_institution_plus_no_conflict(self):
        text = "Disputes shall be resolved by arbitration administered by the American Arbitration Association."
        report = analyze_arbitration_clause(text)
        assert report.applicable is True
        assert report.score == 25  # institution (20) + no_litigation_conflict (5)
        institution = next(e for e in report.elements if e.key == "institution")
        assert institution.present is True
        seat = next(e for e in report.elements if e.key == "seat")
        assert seat.present is False


class TestIndividualElements:
    def test_seat_language_is_detected(self):
        text = "Disputes shall be settled by arbitration. The seat of arbitration shall be London."
        report = analyze_arbitration_clause(text)
        seat = next(e for e in report.elements if e.key == "seat")
        assert seat.present is True

    def test_rules_reference_is_detected(self):
        text = (
            "Disputes shall be settled by arbitration in accordance with the ICC Rules of Arbitration."
        )
        report = analyze_arbitration_clause(text)
        rules = next(e for e in report.elements if e.key == "rules")
        assert rules.present is True

    def test_arbitrator_count_is_detected(self):
        text = "Disputes shall be settled by arbitration before a panel of three arbitrators."
        report = analyze_arbitration_clause(text)
        count = next(e for e in report.elements if e.key == "arbitrator_count")
        assert count.present is True

    def test_language_of_arbitration_is_detected(self):
        text = "Disputes shall be settled by arbitration. The language of the arbitration shall be French."
        report = analyze_arbitration_clause(text)
        lang = next(e for e in report.elements if e.key == "language")
        assert lang.present is True

    def test_emergency_relief_is_detected(self):
        text = "Disputes shall be settled by arbitration. Either party may seek interim relief from a court."
        report = analyze_arbitration_clause(text)
        er = next(e for e in report.elements if e.key == "emergency_relief")
        assert er.present is True


class TestLitigationConflict:
    def test_conflicting_exclusive_jurisdiction_clause_is_flagged(self):
        text = (
            "Disputes shall be settled by binding arbitration. Notwithstanding the foregoing, the "
            "parties submit to the exclusive jurisdiction of the courts of Delaware."
        )
        report = analyze_arbitration_clause(text)
        assert report.conflict_with_litigation_clause is True
        conflict_element = next(e for e in report.elements if e.key == "no_litigation_conflict")
        assert conflict_element.present is False

    def test_no_conflict_when_only_arbitration_is_present(self):
        text = "Disputes shall be settled by binding arbitration administered by JAMS."
        report = analyze_arbitration_clause(text)
        assert report.conflict_with_litigation_clause is False
        conflict_element = next(e for e in report.elements if e.key == "no_litigation_conflict")
        assert conflict_element.present is True


class TestAsDict:
    def test_as_dict_has_expected_shape(self):
        text = "Disputes shall be settled by binding arbitration administered by JAMS."
        report = analyze_arbitration_clause(text)
        d = report.as_dict()
        assert set(d.keys()) == {
            "applicable", "score", "elements", "conflict_with_litigation_clause", "methodology_note",
        }
        assert len(d["elements"]) == 7
        assert all({"key", "label", "present", "weight", "detail"} <= set(el.keys()) for el in d["elements"])

    def test_as_dict_for_not_applicable_case(self):
        d = analyze_arbitration_clause("This Agreement is governed by Delaware law.").as_dict()
        assert d["applicable"] is False
        assert d["score"] is None
        assert d["elements"] == []


class TestEndToEndIntegration:
    """clause_quality must be wired into RuleEngine.analyze() as an
    additive layer — never replacing overall_risk, rule_counts, or the
    existing M_ARBITRATION_01 presence-only finding."""

    def test_analyze_result_includes_clause_quality(self, rule_engine):
        text = (
            "Any dispute shall be settled by mandatory arbitration administered by the American "
            "Arbitration Association. The seat of arbitration shall be New York."
        )
        result = rule_engine.analyze(text)
        assert "clause_quality" in result
        arbitration = result["clause_quality"]["arbitration"]
        assert arbitration["applicable"] is True
        assert arbitration["score"] == 45  # institution (20) + seat (20) + no_litigation_conflict (5)

    def test_document_without_arbitration_is_not_applicable_end_to_end(self, rule_engine):
        text = "This Agreement is governed by the laws of the State of Delaware."
        result = rule_engine.analyze(text)
        assert result["clause_quality"]["arbitration"]["applicable"] is False

    def test_overall_risk_is_unchanged_by_clause_quality(self, rule_engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        result = rule_engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert "clause_quality" in result

    def test_m_arbitration_01_still_fires_alongside_clause_quality(self, rule_engine):
        text = "Any dispute shall be settled by mandatory arbitration administered by JAMS."
        result = rule_engine.analyze(text)
        rule_ids = {f.rule_id for f in result["findings"]}
        assert "M_ARBITRATION_01" in rule_ids
        assert result["clause_quality"]["arbitration"]["applicable"] is True
