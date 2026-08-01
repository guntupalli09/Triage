"""
Tests for the deterministic Rule-ID-to-Redline mapping — see
redline_templates.py.

Core invariant under test throughout: the same rule_id always produces
the same suggested_redline text — this module authors NO language at
render time, it only combines a reviewed static template with a
finding's dynamic data (severity, matched text, clause reference).
"""

from dataclasses import dataclass
from typing import Optional

from redline_templates import COVERED_RULE_IDS, render_redline
from rules_engine import Severity


@dataclass
class FakeFinding:
    rule_id: str
    severity: Severity
    exact_snippet: str = "sample matched text"
    matched_excerpt: str = "...sample matched text..."
    clause_number: Optional[str] = None


class TestCoverage:
    def test_covered_rule_ids_is_nonempty(self):
        assert len(COVERED_RULE_IDS) >= 10

    def test_unlimited_liability_rule_is_covered(self):
        assert "H_LOL_01" in COVERED_RULE_IDS

    def test_uncovered_rule_returns_none(self):
        finding = FakeFinding(rule_id="X_NOT_COVERED_01", severity=Severity.HIGH)
        assert render_redline(finding) is None


class TestDeterminism:
    def test_same_rule_id_always_produces_the_same_redline_text(self):
        finding_a = FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH, exact_snippet="text A")
        finding_b = FakeFinding(rule_id="H_LOL_01", severity=Severity.CRITICAL, exact_snippet="text B")
        redline_a = render_redline(finding_a)
        redline_b = render_redline(finding_b)
        # Different findings, different severity/current_language, but the
        # SAME rule_id must produce the identical suggested_redline text.
        assert redline_a["suggested_redline"] == redline_b["suggested_redline"]
        assert redline_a["issue"] == redline_b["issue"]

    def test_calling_twice_produces_byte_identical_output(self):
        finding = FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH)
        r1 = render_redline(finding)
        r2 = render_redline(finding)
        assert r1 == r2


class TestExactUserProvidedRedline:
    def test_h_lol_01_matches_the_exact_reviewed_text(self):
        # This is the literal, reviewed default redline for unlimited
        # liability -- verbatim, not paraphrased or regenerated.
        finding = FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH)
        redline = render_redline(finding)
        assert redline["suggested_redline"] == (
            "Except for liability arising from fraud, willful misconduct, confidentiality "
            "obligations, or indemnification obligations expressly provided under this "
            "Agreement, each party's aggregate liability shall not exceed the total fees "
            "paid under this Agreement during the twelve (12) months preceding the event "
            "giving rise to the claim."
        )


class TestOutputShape:
    def test_all_required_fields_are_present(self):
        finding = FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH, clause_number="4.2")
        redline = render_redline(finding)
        expected_keys = {
            "issue", "clause", "severity", "current_language", "problem", "legal_rationale",
            "business_impact", "recommended_change", "suggested_redline", "why_this_wording",
            "expected_counterparty_position", "negotiation_difficulty", "fallback_position",
            "confidence", "supporting_deterministic_rules",
        }
        assert set(redline.keys()) == expected_keys

    def test_no_field_is_empty(self):
        for rule_id in COVERED_RULE_IDS:
            finding = FakeFinding(rule_id=rule_id, severity=Severity.HIGH)
            redline = render_redline(finding)
            for key, value in redline.items():
                if key == "clause":
                    continue  # legitimately "Not specified" when absent
                assert value, f"{rule_id}.{key} is empty"

    def test_negotiation_difficulty_is_a_valid_value(self):
        for rule_id in COVERED_RULE_IDS:
            finding = FakeFinding(rule_id=rule_id, severity=Severity.HIGH)
            redline = render_redline(finding)
            assert redline["negotiation_difficulty"] in ("Low", "Medium", "High")

    def test_confidence_is_a_valid_value(self):
        for rule_id in COVERED_RULE_IDS:
            finding = FakeFinding(rule_id=rule_id, severity=Severity.HIGH)
            redline = render_redline(finding)
            assert redline["confidence"] in ("High", "Medium", "Low")

    def test_supporting_deterministic_rules_names_the_triggering_rule(self):
        finding = FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH)
        redline = render_redline(finding)
        assert redline["supporting_deterministic_rules"] == ["H_LOL_01"]


class TestDynamicFieldsReflectTheActualFinding:
    def test_severity_reflects_the_actual_finding_not_a_fixed_default(self):
        finding = FakeFinding(rule_id="H_ASYMMETRIC_LIABILITY_01", severity=Severity.CRITICAL)
        redline = render_redline(finding)
        assert redline["severity"] == "critical"

    def test_current_language_reflects_the_actual_matched_text(self):
        finding = FakeFinding(
            rule_id="H_LOL_01", severity=Severity.HIGH, exact_snippet="Vendor's liability shall not be limited",
        )
        redline = render_redline(finding)
        assert redline["current_language"] == "Vendor's liability shall not be limited"

    def test_clause_reflects_the_actual_clause_number_when_present(self):
        finding = FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH, clause_number="7.3")
        redline = render_redline(finding)
        assert redline["clause"] == "7.3"

    def test_clause_defaults_to_not_specified_when_absent(self):
        finding = FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH, clause_number=None)
        redline = render_redline(finding)
        assert redline["clause"] == "Not specified"

    def test_falls_back_to_matched_excerpt_when_exact_snippet_missing(self):
        finding = FakeFinding(rule_id="H_LOL_01", severity=Severity.HIGH)
        del_finding_dict = {
            "rule_id": "H_LOL_01", "severity": "high", "matched_excerpt": "...excerpt only...",
            "clause_number": None,
        }
        redline = render_redline(del_finding_dict)
        assert redline["current_language"] == "...excerpt only..."


class TestOneIssueOneSolutionPrinciple:
    """Every covered template targets a SINGLE clause/sentence, never a
    full-clause rewrite -- verified by checking the redline text is a
    bounded single sentence/short passage, not a multi-paragraph rewrite."""

    def test_no_redline_exceeds_a_reasonable_single_edit_length(self):
        for rule_id in COVERED_RULE_IDS:
            finding = FakeFinding(rule_id=rule_id, severity=Severity.HIGH)
            redline = render_redline(finding)
            # A single-sentence/short-passage edit, not a multi-clause
            # rewrite -- generous bound (500 chars) that would still catch
            # an accidental full-clause dump.
            assert len(redline["suggested_redline"]) < 500, (
                f"{rule_id}'s redline is {len(redline['suggested_redline'])} chars -- "
                "check it isn't rewriting more than one issue"
            )


class TestAcceptsRealEngineFindings:
    def test_against_real_engine_output(self, rule_engine):
        text = "In no event shall liability be limited under this Agreement, without limit."
        result = rule_engine.analyze(text)
        covered = [f for f in result["findings"] if f.rule_id in COVERED_RULE_IDS]
        assert covered, "expected at least one covered finding for this test to be meaningful"
        redline = render_redline(covered[0])
        assert redline is not None
        assert redline["supporting_deterministic_rules"] == [covered[0].rule_id]

    def test_uncovered_real_finding_returns_none_not_a_guess(self, rule_engine):
        text = "This Agreement includes a Statement of Work incorporated by reference."
        result = rule_engine.analyze(text)
        uncovered = [f for f in result["findings"] if f.rule_id not in COVERED_RULE_IDS]
        if uncovered:
            assert render_redline(uncovered[0]) is None
