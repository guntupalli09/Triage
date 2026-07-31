"""
Tests for the Lawyer Confidence Index — see confidence_index.py.

Unit tests exercise build_confidence_breakdown() directly against
synthetic finding-like dicts. Integration tests confirm it's wired into
main.py's findings_dict construction (not rules_engine.py — this is a
presentation-layer transform over already-computed finding attributes).
"""

from confidence_index import build_confidence_breakdown


def make_finding(**overrides):
    base = {
        "rule_id": "H_TEST_01",
        "start_index": 100,
        "finding_type": "adverse_language_detected",
        "confidence": "high",
        "confidence_reason": "Direct textual match.",
        "evidence_quality": "bounded",
        "party_direction": None,
    }
    base.update(overrides)
    return base


class TestDirectTextualMatch:
    def test_adverse_language_detected_meets_direct_match_item(self):
        finding = make_finding(finding_type="adverse_language_detected")
        bd = build_confidence_breakdown(finding)
        item = next(i for i in bd.checklist if "Direct textual match" in i.label)
        assert item.met is True

    def test_expected_protection_not_found_fails_direct_match_item(self):
        finding = make_finding(finding_type="expected_protection_not_found")
        bd = build_confidence_breakdown(finding)
        item = next(i for i in bd.checklist if "Direct textual match" in i.label)
        assert item.met is False

    def test_unable_to_determine_fails_direct_match_item(self):
        finding = make_finding(finding_type="unable_to_determine")
        bd = build_confidence_breakdown(finding)
        item = next(i for i in bd.checklist if "Direct textual match" in i.label)
        assert item.met is False


class TestPartyDirectionItem:
    def test_non_directional_finding_omits_party_direction_item(self):
        finding = make_finding(party_direction=None)
        bd = build_confidence_breakdown(finding)
        labels = [i.label for i in bd.checklist]
        assert not any("Party direction" in label for label in labels)

    def test_unambiguous_party_direction_meets_the_item(self):
        finding = make_finding(party_direction={"mutuality_status": "customer-only"})
        bd = build_confidence_breakdown(finding)
        item = next(i for i in bd.checklist if "Party direction" in i.label)
        assert item.met is True

    def test_ambiguous_party_direction_fails_the_item(self):
        finding = make_finding(party_direction={"mutuality_status": "ambiguous"})
        bd = build_confidence_breakdown(finding)
        item = next(i for i in bd.checklist if "Party direction" in i.label)
        assert item.met is False


class TestEvidenceQualityItem:
    def test_bounded_evidence_meets_the_item(self):
        finding = make_finding(evidence_quality="bounded")
        bd = build_confidence_breakdown(finding)
        item = next(i for i in bd.checklist if "Evidence span" in i.label)
        assert item.met is True

    def test_wide_span_fails_the_item(self):
        finding = make_finding(evidence_quality="wide_span_review_recommended")
        bd = build_confidence_breakdown(finding)
        item = next(i for i in bd.checklist if "Evidence span" in i.label)
        assert item.met is False

    def test_minimal_span_fails_the_item(self):
        finding = make_finding(evidence_quality="minimal_span")
        bd = build_confidence_breakdown(finding)
        item = next(i for i in bd.checklist if "Evidence span" in i.label)
        assert item.met is False


class TestContradictionLogItem:
    def test_finding_not_in_contradiction_log_meets_the_item(self):
        finding = make_finding(rule_id="H_TEST_01", start_index=100)
        bd = build_confidence_breakdown(finding, contradiction_log={})
        item = next(i for i in bd.checklist if "contradiction" in i.label)
        assert item.met is True

    def test_finding_in_contradiction_log_fails_the_item(self):
        finding = make_finding(rule_id="H_TEST_01", start_index=100)
        bd = build_confidence_breakdown(finding, contradiction_log={"H_TEST_01_100": "reconciled"})
        item = next(i for i in bd.checklist if "contradiction" in i.label)
        assert item.met is False

    def test_missing_contradiction_log_defaults_to_met(self):
        finding = make_finding()
        bd = build_confidence_breakdown(finding, contradiction_log=None)
        item = next(i for i in bd.checklist if "contradiction" in i.label)
        assert item.met is True


class TestConfidenceAndReasonPassThrough:
    def test_confidence_label_is_passed_through_unchanged(self):
        finding = make_finding(confidence="medium")
        bd = build_confidence_breakdown(finding)
        assert bd.confidence == "medium"

    def test_reason_text_is_passed_through_unchanged(self):
        finding = make_finding(confidence_reason="Some specific reason text.")
        bd = build_confidence_breakdown(finding)
        assert bd.reason == "Some specific reason text."


class TestAsDict:
    def test_as_dict_has_expected_keys(self):
        bd = build_confidence_breakdown(make_finding())
        d = bd.as_dict()
        assert set(d.keys()) == {"confidence", "checklist", "reason"}
        assert all({"label", "met"} <= set(item.keys()) for item in d["checklist"])


class TestAcceptsRealFindingObjects:
    """build_confidence_breakdown must work against actual rules_engine.py
    Finding objects, not just dicts — verified end-to-end against the real
    engine rather than only a hand-built stand-in."""

    def test_against_real_engine_output(self, rule_engine):
        text = "The Contractor shall indemnify the Client for all claims arising from this Agreement."
        result = rule_engine.analyze(text)
        assert result["findings"], "expected at least one finding for this test to be meaningful"
        finding = result["findings"][0]
        bd = build_confidence_breakdown(finding, result.get("contradiction_log", {}))
        assert bd.confidence in ("high", "medium", "low")
        assert len(bd.checklist) >= 3
