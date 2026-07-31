"""
Tests for the Deterministic Clause Quality Engine — Liability module.
See clause_quality.py's analyze_liability_clause().

Unit tests exercise the function directly against synthetic text.
Integration tests confirm the report is wired into RuleEngine.analyze() as
an additive layer, same pattern as tests/test_clause_quality.py
(arbitration) and the other additive-layer test suites.
"""

from clause_quality import analyze_liability_clause


class TestNotApplicable:
    def test_document_with_no_liability_clause_is_not_applicable(self):
        text = "This Agreement governs the provision of services between the parties."
        report = analyze_liability_clause(text)
        assert report.applicable is False
        assert report.score is None
        assert report.elements == []


class TestWellDraftedClause:
    def test_fully_specified_liability_clause_scores_100(self):
        text = (
            "LIMITATION OF LIABILITY. IN NO EVENT SHALL either party's liability exceed the fees "
            "paid in the preceding twelve months. Neither party shall be liable for consequential, "
            "indirect, or special damages, except for indemnification obligations, confidentiality "
            "breaches, or intellectual property infringement, or claims arising from fraud or "
            "willful misconduct."
        )
        report = analyze_liability_clause(text)
        assert report.applicable is True
        assert report.score == 100
        assert all(e.present for e in report.elements)

    def test_element_gaps_survive_a_line_break_inside_the_proximity_window(self):
        # Regression: an earlier version's proximity regexes lacked
        # re.DOTALL, so a line break between "except for X" and "fraud"
        # inside one real carve-out list caused a false "absent" — verified
        # against a real fixture-shaped clause spanning multiple lines.
        text = (
            "LIMITATION OF LIABILITY. Shall not exceed fees paid.\n"
            "Except for indemnification obligations, confidentiality breaches,\n"
            "or claims arising from fraud or willful misconduct."
        )
        report = analyze_liability_clause(text)
        carveouts = next(e for e in report.elements if e.key == "high_severity_carveouts")
        fraud = next(e for e in report.elements if e.key == "fraud_exception")
        assert carveouts.present is True
        assert fraud.present is True


class TestSparseClause:
    def test_bare_cap_mention_has_low_score(self):
        # cap_present (25) + no_cap_negating_language (10), which is
        # present by default whenever nothing undermines the cap — same
        # "absent-deficiency defaults present" pattern as arbitration's
        # no_litigation_conflict element.
        text = "LIMITATION OF LIABILITY. Liability shall not exceed the fees paid."
        report = analyze_liability_clause(text)
        assert report.applicable is True
        assert report.score == 35
        substantive = [e for e in report.elements if e.key not in ("cap_present", "no_cap_negating_language")]
        assert not any(e.present for e in substantive)


class TestIndividualElements:
    def test_one_sided_cap_is_not_mutual(self):
        text = "LIMITATION OF LIABILITY. Vendor's liability shall not exceed the fees paid under this Agreement."
        report = analyze_liability_clause(text)
        mutual = next(e for e in report.elements if e.key == "mutual_application")
        assert mutual.present is False

    def test_mutual_cap_is_detected(self):
        text = "LIMITATION OF LIABILITY. Neither party shall be liable for damages exceeding fees paid."
        report = analyze_liability_clause(text)
        mutual = next(e for e in report.elements if e.key == "mutual_application")
        assert mutual.present is True

    def test_consequential_damages_waiver_is_detected(self):
        text = (
            "LIMITATION OF LIABILITY. Liability shall not exceed fees paid. In no event shall "
            "either party be liable for consequential or indirect damages."
        )
        report = analyze_liability_clause(text)
        consequential = next(e for e in report.elements if e.key == "consequential_damages_excluded")
        assert consequential.present is True

    def test_ip_and_confidentiality_carveouts_are_detected(self):
        text = (
            "LIMITATION OF LIABILITY. Liability shall not exceed fees paid, except for claims "
            "arising from confidentiality breaches or intellectual property infringement."
        )
        report = analyze_liability_clause(text)
        carveouts = next(e for e in report.elements if e.key == "high_severity_carveouts")
        assert carveouts.present is True


class TestCapNegatingLanguage:
    def test_undermining_language_is_flagged(self):
        text = (
            "LIMITATION OF LIABILITY. Liability shall not exceed fees paid. Notwithstanding the "
            "foregoing, Vendor's liability for confidentiality breaches shall not be limited."
        )
        report = analyze_liability_clause(text)
        no_negation = next(e for e in report.elements if e.key == "no_cap_negating_language")
        assert no_negation.present is False

    def test_no_undermining_language_is_the_default(self):
        text = "LIMITATION OF LIABILITY. Liability shall not exceed fees paid."
        report = analyze_liability_clause(text)
        no_negation = next(e for e in report.elements if e.key == "no_cap_negating_language")
        assert no_negation.present is True


class TestAsDict:
    def test_as_dict_has_expected_shape(self):
        text = "LIMITATION OF LIABILITY. Liability shall not exceed fees paid."
        report = analyze_liability_clause(text)
        d = report.as_dict()
        assert set(d.keys()) == {"applicable", "score", "elements", "methodology_note"}
        assert len(d["elements"]) == 6
        assert all({"key", "label", "present", "weight", "detail"} <= set(el.keys()) for el in d["elements"])

    def test_as_dict_for_not_applicable_case(self):
        d = analyze_liability_clause("This Agreement governs the services.").as_dict()
        assert d["applicable"] is False
        assert d["score"] is None
        assert d["elements"] == []


class TestEndToEndIntegration:
    """The liability module must be wired into RuleEngine.analyze()'s
    clause_quality key alongside arbitration — never replacing overall_risk,
    rule_counts, or the existing H_LOL_01 presence finding."""

    def test_analyze_result_includes_liability_clause_quality(self, rule_engine):
        text = (
            "LIMITATION OF LIABILITY. Neither party shall be liable for damages exceeding fees "
            "paid under this Agreement."
        )
        result = rule_engine.analyze(text)
        assert "clause_quality" in result
        liability = result["clause_quality"]["liability"]
        assert liability["applicable"] is True
        assert isinstance(liability["score"], int)

    def test_arbitration_and_liability_both_present_when_applicable(self, rule_engine):
        text = (
            "LIMITATION OF LIABILITY. Neither party shall be liable for damages exceeding fees paid. "
            "Any dispute shall be settled by mandatory arbitration administered by JAMS."
        )
        result = rule_engine.analyze(text)
        cq = result["clause_quality"]
        assert cq["arbitration"]["applicable"] is True
        assert cq["liability"]["applicable"] is True

    def test_document_without_liability_clause_is_not_applicable_end_to_end(self, rule_engine):
        text = "This Agreement governs the provision of services between the parties."
        result = rule_engine.analyze(text)
        assert result["clause_quality"]["liability"]["applicable"] is False

    def test_overall_risk_is_unchanged_by_liability_clause_quality(self, rule_engine):
        text = (
            "The parties agree that either party may issue a press release "
            "regarding this Agreement without prior written consent."
        )
        result = rule_engine.analyze(text)
        assert result["overall_risk"] == "high"
        assert "clause_quality" in result

    def test_h_lol_01_still_fires_alongside_clause_quality(self, rule_engine):
        text = "In no event shall liability be limited under this limitation of liability clause."
        result = rule_engine.analyze(text)
        rule_ids = {f.rule_id for f in result["findings"]}
        assert "H_LOL_01" in rule_ids
