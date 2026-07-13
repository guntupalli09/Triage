"""
Regression tests for proximity-rule evidence.

Proximity rules (anchor + nearby) used to report exact_snippet as just the
anchor span (e.g. "indemnify"), which is weak evidence — it doesn't show the
actual risky language that triggered the finding. The engine now returns a
combined evidence span covering both the anchor and the matched nearby
(risk-phrase) pattern, plus a structured `evidence` dict with the anchor,
the risk phrase, and the surrounding clause.
"""

import pytest
from rules_engine import RuleEngine, Severity


@pytest.fixture
def engine():
    return RuleEngine()


class TestProximityEvidenceStructure:
    def test_indemnification_evidence_includes_risk_phrase(self, engine):
        text = (
            "The Contractor shall indemnify the Client for all claims, "
            "notwithstanding any limitation of liability set forth elsewhere "
            "in this Agreement."
        )
        result = engine.analyze(text)
        indem = [f for f in result["findings"] if f.rule_id == "H_INDEM_01"]
        assert len(indem) == 1
        finding = indem[0]

        # exact_snippet must not be just the bare anchor keyword
        assert finding.exact_snippet != "indemnify"
        assert "indemnify" in finding.exact_snippet.lower()
        assert "limitation of liability" in finding.exact_snippet.lower()

        # evidence dict is present and structured as specified
        assert finding.evidence is not None
        assert finding.evidence["anchor"].lower() == "indemnify"
        assert "limitation of liability" in finding.evidence["risk_phrase"].lower()
        assert "indemnify" in finding.evidence["full_clause"].lower()

    def test_evidence_span_covers_anchor_and_risk_phrase(self, engine):
        text = (
            "The Contractor shall indemnify the Client for all claims, "
            "notwithstanding any limitation of liability set forth elsewhere "
            "in this Agreement."
        )
        result = engine.analyze(text)
        finding = [f for f in result["findings"] if f.rule_id == "H_INDEM_01"][0]

        # start_index/end_index must span from the earlier of (anchor, risk
        # phrase) to the later, not just the anchor's own span.
        assert text[finding.start_index:finding.end_index] == finding.exact_snippet
        anchor_pos = text.lower().index("indemnify")
        risk_pos_end = text.lower().index("limitation of liability") + len("limitation of liability")
        assert finding.start_index <= anchor_pos
        assert finding.end_index >= risk_pos_end

    def test_risk_phrase_precedes_anchor_still_captured(self, engine):
        # nearby pattern occurring before the anchor in the text
        text = (
            "Notwithstanding any limitation of liability elsewhere in this "
            "Agreement, the Supplier shall indemnify the Buyer for all losses."
        )
        result = engine.analyze(text)
        indem = [f for f in result["findings"] if f.rule_id == "H_INDEM_01"]
        assert len(indem) == 1
        finding = indem[0]
        assert "notwithstanding" in finding.exact_snippet.lower()
        assert "indemnify" in finding.exact_snippet.lower()
        assert text[finding.start_index:finding.end_index] == finding.exact_snippet

    def test_direct_pattern_rules_have_no_evidence_dict(self, engine):
        # H_ATTFEE_01 is a direct-pattern rule, not anchor+nearby
        text = "The losing party shall pay all attorneys' fees incurred by the prevailing party."
        result = engine.analyze(text)
        attfee = [f for f in result["findings"] if f.rule_id == "H_ATTFEE_01"]
        assert len(attfee) == 1
        assert attfee[0].evidence is None
