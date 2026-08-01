"""
Tests for the Negotiation Reasoning Chain — see reasoning_chains.py, and
its wiring into clause_quality.py's arbitration module (the only module
currently covered — see reasoning_chains.py's module docstring for why
this is a deliberate scope limit, not an oversight).
"""

from clause_quality import analyze_arbitration_clause
from reasoning_chains import covered_modules, get_reasoning_chain


class TestGetReasoningChain:
    def test_returns_chain_for_authored_arbitration_element(self):
        chain = get_reasoning_chain("arbitration", "seat")
        assert chain is not None
        assert "seat" in chain.issue.lower()

    def test_returns_none_for_unauthored_element(self):
        assert get_reasoning_chain("arbitration", "nonexistent_element") is None

    def test_returns_none_for_unauthored_module(self):
        # Liability/Confidentiality/etc. are not yet covered — must return
        # None, never fabricate content for an uncovered module.
        assert get_reasoning_chain("liability", "cap_present") is None
        assert get_reasoning_chain("confidentiality", "definition_present") is None

    def test_all_seven_arbitration_elements_are_covered(self):
        expected_keys = {
            "institution", "seat", "rules", "arbitrator_count",
            "language", "emergency_relief", "no_litigation_conflict",
        }
        for key in expected_keys:
            assert get_reasoning_chain("arbitration", key) is not None, f"missing chain for {key}"


class TestChainContentShape:
    def test_chain_as_dict_has_all_eight_fields(self):
        chain = get_reasoning_chain("arbitration", "institution")
        d = chain.as_dict()
        assert set(d.keys()) == {
            "issue", "legal_risk", "business_risk", "market_standard",
            "suggested_revision", "suggested_redline",
            "expected_counterparty_objection", "fallback_position",
        }

    def test_no_field_is_empty(self):
        for key in ("institution", "seat", "rules", "arbitrator_count", "language",
                    "emergency_relief", "no_litigation_conflict"):
            chain = get_reasoning_chain("arbitration", key)
            for field_name, value in chain.as_dict().items():
                assert value.strip(), f"{key}.{field_name} is empty"


class TestCoveredModules:
    def test_arbitration_is_covered(self):
        assert "arbitration" in covered_modules()

    def test_liability_is_not_yet_covered(self):
        assert "liability" not in covered_modules()


class TestWiringIntoArbitrationModule:
    def test_deficient_element_carries_its_reasoning_chain(self):
        text = "Any dispute shall be settled by binding arbitration."  # sparse — missing everything
        report = analyze_arbitration_clause(text)
        seat = next(e for e in report.elements if e.key == "seat")
        assert seat.present is False
        assert seat.reasoning_chain is not None
        assert seat.reasoning_chain["suggested_redline"]

    def test_present_element_does_not_carry_a_reasoning_chain(self):
        text = (
            "Any dispute shall be settled by mandatory arbitration administered by the "
            "American Arbitration Association."
        )
        report = analyze_arbitration_clause(text)
        institution = next(e for e in report.elements if e.key == "institution")
        assert institution.present is True
        assert institution.reasoning_chain is None

    def test_no_litigation_conflict_chain_appears_only_when_conflict_found(self):
        conflicting_text = (
            "Disputes shall be settled by binding arbitration. The parties also submit to the "
            "exclusive jurisdiction of the courts of Delaware."
        )
        report = analyze_arbitration_clause(conflicting_text)
        conflict_element = next(e for e in report.elements if e.key == "no_litigation_conflict")
        assert conflict_element.present is False
        assert conflict_element.reasoning_chain is not None

        clean_text = "Disputes shall be settled by binding arbitration administered by JAMS."
        report2 = analyze_arbitration_clause(clean_text)
        conflict_element2 = next(e for e in report2.elements if e.key == "no_litigation_conflict")
        assert conflict_element2.present is True
        assert conflict_element2.reasoning_chain is None

    def test_as_dict_includes_reasoning_chain_key_for_every_element(self):
        text = "Any dispute shall be settled by binding arbitration."
        report = analyze_arbitration_clause(text)
        d = report.as_dict()
        for element in d["elements"]:
            assert "reasoning_chain" in element


class TestEndToEndIntegration:
    def test_analyze_result_carries_reasoning_chains_through(self, rule_engine):
        text = "Any dispute shall be settled by binding arbitration."
        result = rule_engine.analyze(text)
        arb = result["clause_quality"]["arbitration"]
        seat = next(e for e in arb["elements"] if e["key"] == "seat")
        assert seat["reasoning_chain"] is not None
