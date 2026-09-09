"""Tests for v2 rules proposal from playbook section text."""

from liability_policy_v2_import import propose_liability_rules_v2_from_sections


COMMERCIAL_PLAYBOOK_SECTIONS = [
    (
        "Preferred Position: Vendor liability shall be limited to the greater of "
        "fees paid or payable under the agreement during the 12 months preceding the event giving rise to the claim, or\n"
        "$1,000,000."
    ),
    (
        "Acceptable Fallback: A general liability cap equal to 12 months of fees may be accepted without escalation for "
        "agreements with annual contract value below $250,000."
    ),
    (
        "Do not accept a liability cap of less than six months of fees."
    ),
    (
        "Super-cap: For confidentiality and data security breaches, liability may be capped at 2× the general liability cap."
    ),
]


class TestV2ImportProposal:
    def test_commercial_contract_review_playbook_patterns(self):
        rules = propose_liability_rules_v2_from_sections(COMMERCIAL_PLAYBOOK_SECTIONS)
        assert rules is not None
        assert rules["schema_version"] == 2
        kinds = {b["kind"] for b in rules["bands"]}
        assert "PREFERRED" in kinds
        assert "MINIMUM_ACCEPTABLE" in kinds
        assert "ACCEPTABLE_FALLBACK" in kinds
        preferred = next(b for b in rules["bands"] if b["kind"] == "PREFERRED")
        assert preferred["expression"]["operator"] == "GREATER_OF"
        assert rules["super_caps"][0]["expression"]["operands"][0]["type"] == "reference"
        assert rules["super_caps"][0]["expression"]["operands"][0]["ref"] == "GENERAL_CAP"

    def test_returns_none_without_preferred_band(self):
        assert propose_liability_rules_v2_from_sections(["No liability guidance here."]) is None

    def test_greater_of_without_explicit_fallback_adds_default_band(self):
        sections = [
            (
                "Preferred Position: Vendor liability shall be limited to the greater of "
                "fees paid or payable under the agreement during the 12 months preceding the event, or $1,000,000."
            ),
        ]
        rules = propose_liability_rules_v2_from_sections(sections)
        assert rules is not None
        fallback = next(b for b in rules["bands"] if b["kind"] == "ACCEPTABLE_FALLBACK")
        assert fallback["expression"]["operands"][0]["months"] == 12
        assert fallback["conditions"][0]["value"]["amount"] == "250000"
