"""
Regression tests for AI-assisted Limitation of Liability import mapping.

Protects fee-period normalization (months -> annual-fee multiples), super-cap
guards, ladder-field reassignment, customer-side orientation, and silence on
unstated consequential-damages policy.
"""
import json
import os

os.environ.setdefault("DEV_MODE", "true")

import pytest

import playbook_ai_extraction as pai
import playbook_extraction as pex


def _section(text, start=0):
    return pai.DiscoveredSection(
        clause_type="limitation_of_liability", start=start, end=start + len(text), text=text,
    )


def _verify(field_name, value, quote, basis="EXTRACTED", text=None):
    text = text or quote
    raw = pai.RawCandidate(field_name=field_name, value=value, quote=quote, basis=basis)
    raw = pai._reassign_ladder_field(raw)
    return pai.verify_and_classify_candidate("limitation_of_liability", raw, _section(text))


class TestPrimaryCapNormalization:
    """A. Primary cap — greater of 12 months fees OR $1M."""

    def test_twelve_months_not_twelve_x(self):
        quote = (
            "Vendor liability should be capped at the greater of fees paid during the "
            "preceding 12 months or $1,000,000."
        )
        result = _verify("preferred_multiplier", 12.0, quote)
        assert result.status == "REQUIRES_LAWYER_INTERPRETATION"
        assert result.value is None
        assert "greater-of" in (result.reason or "").lower()

    def test_explicit_one_x_annual_fees_unchanged(self):
        quote = "Our preferred liability cap is 1x annual fees."
        result = _verify("preferred_multiplier", 1.0, quote)
        assert result.status == "ESTABLISHED"
        assert result.value == 1.0


class TestFallbackNormalization:
    """B. Fallback — 12 months acceptable with ACV condition."""

    def test_fallback_twelve_months_normalizes_to_one(self):
        quote = (
            "A cap equal to 12 months of fees may be accepted without escalation for "
            "agreements with annual contract value below $250,000."
        )
        result = _verify("acceptable_max_multiplier", 12.0, quote)
        assert result.status == "ESTABLISHED"
        assert result.value == 1.0

    def test_fallback_reassigned_from_preferred(self):
        quote = (
            "Acceptable Fallback: A general liability cap equal to 12 months of fees may be "
            "accepted without escalation for agreements with annual contract value below $250,000."
        )
        raw = pai.RawCandidate("preferred_multiplier", 12.0, quote, "EXTRACTED")
        reassigned = pai._reassign_ladder_field(raw)
        assert reassigned.field_name == "acceptable_max_multiplier"


class TestHardStop:
    """C. Hard stop — minimum six months of fees."""

    def test_six_month_hard_stop_not_preferred_cap(self):
        quote = "Do not accept a liability cap of less than six months of fees."
        result = _verify("preferred_multiplier", 6.0, quote)
        assert result.status == "REQUIRES_LAWYER_INTERPRETATION"
        assert result.value is None
        assert "hard-stop" in (result.reason or "").lower()

    def test_six_months_normalizes_when_not_hard_stop(self):
        quote = "Vendor liability may not exceed six months of fees without approval."
        result = _verify("negotiate_max_multiplier", 6.0, quote)
        assert result.status == "ESTABLISHED"
        assert result.value == 0.5


class TestSuperCap:
    """D. Super-cap — 2× general cap must not become primary multiplier."""

    def test_super_cap_rejected_for_preferred(self):
        quote = (
            "For confidentiality and data-security claims, a super-cap of at least 2× the "
            "general liability cap is acceptable."
        )
        result = _verify("preferred_multiplier", 2.0, quote)
        assert result.status == "REQUIRES_LAWYER_INTERPRETATION"
        assert result.value is None
        assert "super-cap" in (result.reason or "").lower()


class TestRoles:
    """E. Customer-side vendor-liability playbook."""

    def test_vendor_liability_playbook_infers_buy_side(self):
        text = (
            "Limitation of Liability. Preferred Position. Vendor liability should be capped. "
            "Do not accept a complete exclusion of vendor liability."
        )
        side = pai._infer_contract_side([text], "Commercial Contract Review Playbook — customer-side SaaS guidance.")
        assert side == "buy_side"

    def test_mutual_language_not_overridden(self):
        text = "Each party's liability shall be mutual and capped equally."
        side = pai._infer_contract_side([text], text)
        assert side is None


class TestCarveOuts:
    """F. Carve-outs — role-aware vendor indemnification."""

    def test_vendor_indemnification_carve_out_established(self):
        quote = "vendor indemnification obligations"
        text = "The following should not be subject to the ordinary general liability cap: vendor indemnification obligations;"
        raw = pai.RawCandidate(
            "required_exceptions_json", ["indemnification"], quote, "EXTRACTED",
        )
        result = pai.verify_and_classify_candidate("limitation_of_liability", raw, _section(text))
        assert result.status == "ESTABLISHED"
        assert "indemnification" in result.value


class TestSilence:
    """G. Unstated consequential damages stays not decided."""

    def test_consequential_not_inferred_from_silence(self):
        merged = pai.merge_candidates_for_clause("limitation_of_liability", [])
        assert merged["require_consequential_damages_exclusion"].status == "NOT_ESTABLISHED"


class TestUnitNormalizationTable:
    """Explicit months/years -> annual-fee multiple conversions."""

    @pytest.mark.parametrize("quote,value,expected", [
        ("12 months of fees", 12.0, 1.0),
        ("six months of fees", 6.0, 0.5),
        ("24 months of fees", 24.0, 2.0),
        ("one year of fees", 1.0, 1.0),
        ("2x annual fees", 2.0, 2.0),
        ("two times fees", 2.0, 2.0),
    ])
    def test_normalization(self, quote, value, expected):
        norm, reason = pai._normalize_fee_multiplier_value(value, quote)
        assert reason is None
        assert norm == expected


class TestEscalationInference:
    def test_partner_escalation(self):
        text = "For contracts above $250,000 in annual value, a cap below 12 months of fees requires partner approval."
        assert pai._infer_escalation_authority([text]) == "Supervising partner"


class TestCommercialPlaybookEndToEnd:
    """Simulated LLM output for the Commercial Contract Review Playbook LoL section."""

    LOL_SECTION = (
        "2. Limitation of Liability\n"
        "Preferred Position\n"
        "Vendor liability should be capped at the greater of:\n"
        "fees paid or payable under the agreement during the 12 months preceding the event giving rise to the claim, or\n"
        "$1,000,000.\n"
        "Acceptable Fallback\n"
        "A general liability cap equal to 12 months of fees may be accepted without escalation for agreements with annual contract value below $250,000.\n"
        "For contracts above $250,000 in annual value, a cap below 12 months of fees requires partner approval.\n"
        "Exclusions From the General Cap\n"
        "breach of confidentiality; infringement or misappropriation of intellectual property rights; "
        "vendor indemnification obligations; fraud; gross negligence or willful misconduct; "
        "violations of applicable data-protection laws caused by the vendor.\n"
        "For confidentiality and data-security claims, a super-cap of at least 2× the general liability cap is acceptable.\n"
        "Hard Stop\n"
        "Do not accept a liability cap of less than six months of fees.\n"
    )

    def test_simulated_import_values(self):
        section = _section(self.LOL_SECTION)
        llm_output = json.dumps({"candidates": [
            {"field_name": "acceptable_max_multiplier", "value": 12.0,
             "quote": "A general liability cap equal to 12 months of fees may be accepted without escalation for agreements with annual contract value below $250,000.",
             "basis": "EXTRACTED"},
            {"field_name": "preferred_multiplier", "value": 12.0,
             "quote": "fees paid or payable under the agreement during the 12 months preceding the event giving rise to the claim, or $1,000,000.",
             "basis": "EXTRACTED"},
            {"field_name": "prohibit_unlimited", "value": True,
             "quote": "Do not accept a complete exclusion of vendor liability for security incidents caused by the vendor",
             "basis": "EXTRACTED"},
            {"field_name": "required_exceptions_json",
             "value": ["confidentiality", "ip_infringement", "indemnification", "fraud", "gross_negligence", "willful_misconduct", "data_breach"],
             "quote": "breach of confidentiality; infringement or misappropriation of intellectual property rights; vendor indemnification obligations; fraud; gross negligence or willful misconduct; violations of applicable data-protection laws caused by the vendor.",
             "basis": "EXTRACTED"},
            {"field_name": "preferred_multiplier", "value": 2.0,
             "quote": "For confidentiality and data-security claims, a super-cap of at least 2× the general liability cap is acceptable.",
             "basis": "EXTRACTED"},
        ]})
        candidates, _ = pai.parse_llm_response("limitation_of_liability", llm_output)
        classified = []
        for raw in candidates:
            raw = pai._reassign_ladder_field(raw)
            classified.append((raw, pai.verify_and_classify_candidate("limitation_of_liability", raw, section)))
        merged = pai.merge_candidates_for_clause("limitation_of_liability", classified)

        assert merged["acceptable_max_multiplier"].status == "ESTABLISHED"
        assert merged["acceptable_max_multiplier"].value == 1.0

        pref = merged["preferred_multiplier"]
        assert pref.status in ("REQUIRES_LAWYER_INTERPRETATION", "CONFLICTING")
        if pref.status == "REQUIRES_LAWYER_INTERPRETATION":
            assert pref.value is None

        assert merged["require_consequential_damages_exclusion"].status == "NOT_ESTABLISHED"

        side = pai._infer_contract_side([self.LOL_SECTION], self.LOL_SECTION)
        assert side == "buy_side"
        assert pai._infer_escalation_authority([self.LOL_SECTION]) == "Supervising partner"
