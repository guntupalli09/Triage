"""Regression tests for indemnification import: richer triggers and clause-specific fallback."""
from __future__ import annotations

import os

os.environ.setdefault("DEV_MODE", "true")

import indemnification_policy_engine as ipe
import playbook_ai_extraction as pai


class TestIndemnificationTriggerVocabulary:
    def test_new_trigger_keywords_classify(self):
        window = (
            "Vendor shall indemnify Customer for third-party claims arising from "
            "bodily injury or property damage, violations of applicable law, "
            "vendor's security breach, misuse of customer materials, and unlawful use."
        )
        treatments = ipe._classify_triggers(window)
        assert treatments["bodily_injury_property_damage"].treatment == "covered"
        assert treatments["law_violations"].treatment == "covered"
        assert treatments["vendor_security_incidents"].treatment == "covered"
        assert treatments["customer_materials"].treatment == "covered"
        assert treatments["unlawful_use"].treatment == "covered"

    def test_fraud_is_in_triggers(self):
        assert "fraud" in ipe.TRIGGERS


class TestClauseSpecificFallbackInference:
    def test_indemnification_rejects_liability_fallback_bleed(self):
        sections = [
            "Indemnification. Vendor must indemnify for IP infringement.\n"
            "Acceptable Fallback: A general liability cap equal to 12 months of fees may be accepted "
            "without escalation for deals below $250k ACV.",
        ]
        assert pai._infer_fallback_text(sections, "indemnification") == (None, None)

    def test_indemnification_accepts_indemnity_fallback(self):
        sections = [
            "Indemnification. Vendor must indemnify for IP infringement.\n"
            "Acceptable Indemnification Fallback: Vendor shall indemnify, defend, and hold harmless "
            "Customer from third-party claims arising from Vendor's negligence, capped at 1x fees.",
        ]
        result, evidence = pai._infer_fallback_text(sections, "indemnification")
        assert result is not None
        assert evidence is not None
        assert "indemnif" in result.lower()

    def test_indemnification_accepts_fallback_with_playbook_thresholds(self):
        """Numeric thresholds are playbook values — valid inside indemnification."""
        sections = [
            "3. Indemnification\n"
            "Preferred Position\n"
            "Vendor shall indemnify Customer for third-party claims.\n"
            "Acceptable Indemnification Fallback\n"
            "Vendor shall indemnify, defend, and hold harmless Customer from third-party claims. "
            "For agreements with annual contract value below $250,000, indemnification exposure "
            "capped at 12 months of fees is acceptable without escalation.\n\n"
            "4. Termination\n"
            "Either party may terminate with 30 days notice.\n",
        ]
        result, evidence = pai._infer_fallback_text(sections, "indemnification")
        assert result is not None
        assert evidence is not None
        assert "indemnif" in result.lower()
        assert "$250,000" in result or "250,000" in result
        assert "12 months" in result

    def test_indemnification_rejects_lol_semantics_even_with_indemnity_heading(self):
        """LoL subject matter must not attach even under an indemnification heading."""
        sections = [
            "3. Indemnification\n"
            "Acceptable Indemnification Fallback\n"
            "A general liability cap equal to 12 months of fees may be accepted without escalation "
            "for agreements with annual contract value below $250,000.\n",
        ]
        assert pai._infer_fallback_text(sections, "indemnification") == (None, None)

    def test_liability_still_accepts_acceptable_fallback(self):
        sections = [
            "Limitation of Liability. Preferred cap is 1x fees.\n"
            "Acceptable Fallback: A general liability cap equal to 12 months of fees may be accepted.",
        ]
        result, _ = pai._infer_fallback_text(sections, "limitation_of_liability")
        assert result is not None
        assert "general liability cap" in result.lower()
