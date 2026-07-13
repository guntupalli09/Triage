"""
Regression tests for the PresenceRiskRule / RequiredSectionRule split.

Several rules are titled as detecting the ABSENCE of a protection (e.g.
M_BREACH_NOTIFY_01: "No data breach notification obligation"), but their
underlying regex only detected adverse language being PRESENT (e.g. "no
obligation to notify"). A document that is completely silent on breach
notification — never mentioning it at all — produced zero findings, even
though the title promises to catch exactly that case.

RuleClass.REQUIRED_SECTION rules now run a document-level check when no
adverse language is found:
- topic not in scope for this document -> no finding (not applicable)
- topic in scope, protective language found -> no finding (protected)
- topic in scope, no protective language, document long enough to trust
  the negative result -> FindingType.EXPECTED_PROTECTION_NOT_FOUND
- topic in scope, no protective language, document too short/sparse to
  trust -> FindingType.UNABLE_TO_DETERMINE

PresenceRiskRule findings (and REQUIRED_SECTION findings where adverse
language IS present) are tagged FindingType.ADVERSE_LANGUAGE_DETECTED.
"""

import pytest
from rules_engine import RuleEngine, Severity, RuleClass, FindingType, FINDING_TYPE_LABELS

REQUIRED_SECTION_RULE_IDS = {
    "H_DATA_TERMINATION_01",
    "M_RESIDUALS_01",
    "M_BREACH_NOTIFY_01",
    "M_INSURANCE_01",
    "M_SLA_01",
    "M_DATA_PORTABILITY_01",
}


@pytest.fixture
def engine():
    return RuleEngine()


class TestRuleClassificationIsCorrect:
    def test_required_section_rules_are_tagged(self, engine):
        by_id = {r.rule_id: r for r in engine.rules}
        for rid in REQUIRED_SECTION_RULE_IDS:
            assert by_id[rid].rule_class == RuleClass.REQUIRED_SECTION
            assert by_id[rid].topic_patterns
            assert by_id[rid].protective_patterns

    def test_other_rules_default_to_presence_risk(self, engine):
        by_id = {r.rule_id: r for r in engine.rules}
        assert by_id["H_INDEM_01"].rule_class == RuleClass.PRESENCE_RISK
        assert by_id["H_ATTFEE_01"].rule_class == RuleClass.PRESENCE_RISK


class TestTrueSilenceIsNowDetected:
    """The core bug: a document that never mentions the topic at all used
    to produce zero findings for rules literally titled 'No X'."""

    def test_breach_notification_silence_is_flagged(self, engine):
        text = (
            "This is a Software as a Service Agreement between Provider and Customer. "
            "Provider shall process Customer's personal data solely to provide the "
            "Service, in accordance with applicable law and this Agreement. "
            "This Agreement may be terminated by either party upon 30 days written "
            "notice. Fees are due monthly in advance. This Agreement is governed by "
            "the laws of the State of Delaware."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_BREACH_NOTIFY_01"]
        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.EXPECTED_PROTECTION_NOT_FOUND.value

    def test_residuals_silence_is_flagged_in_confidentiality_context(self, engine):
        text = (
            "This Non-Disclosure Agreement governs confidential information "
            "exchanged between the parties. Confidential Information means any "
            "non-public technical or business information disclosed by either "
            "party. This Agreement shall remain in effect for three years from "
            "the Effective Date and may be terminated by either party."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_RESIDUALS_01"]
        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.EXPECTED_PROTECTION_NOT_FOUND.value


class TestAdverseLanguageStillDetected:
    def test_explicit_no_notify_clause_is_adverse(self, engine):
        text = (
            "Provider shall have no obligation to notify Customer of any data "
            "security incident affecting personal data processed hereunder, "
            "regardless of severity or scope."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_BREACH_NOTIFY_01"]
        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.ADVERSE_LANGUAGE_DETECTED.value


class TestProtectiveLanguageSuppressesFinding:
    def test_good_breach_notification_clause_does_not_fire(self, engine):
        text = (
            "This is a Software as a Service Agreement. Provider processes "
            "Customer's personal data to provide the Service. In the event of a "
            "data security breach affecting Customer's personal data, Provider "
            "shall notify Customer without undue delay and in any case within "
            "72 hours of becoming aware of the breach."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_BREACH_NOTIFY_01"]
        assert len(findings) == 0

    def test_good_insurance_clause_does_not_fire(self, engine):
        # This clause used to be a false positive: the old "nearby" list for
        # M_INSURANCE_01 treated "shall maintain" / "commercially reasonable"
        # as ADVERSE trigger phrases instead of protective ones.
        text = (
            "Vendor shall maintain commercially reasonable insurance coverage, "
            "including general liability insurance of at least $1,000,000 per "
            "occurrence, throughout the term of this Agreement and provide a "
            "certificate of insurance upon request."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_INSURANCE_01"]
        assert len(findings) == 0

    def test_good_sla_clause_does_not_fire(self, engine):
        text = (
            "This Software as a Service Agreement includes the following "
            "service level commitment: Provider guarantees 99.9% uptime for "
            "the Service, measured monthly, with service credits for any "
            "shortfall."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_SLA_01"]
        assert len(findings) == 0


class TestTopicNotInScopeProducesNoFinding:
    def test_irrelevant_contract_does_not_flag_missing_breach_notification(self, engine):
        text = (
            "This Agreement governs the sale of office furniture between Buyer "
            "and Seller. Payment is due within 30 days of delivery. Title "
            "passes upon full payment. This Agreement is governed by the laws "
            "of the State of New York and may be terminated by either party "
            "upon written notice."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_BREACH_NOTIFY_01"]
        assert len(findings) == 0

    def test_irrelevant_contract_does_not_flag_missing_residuals(self, engine):
        text = (
            "This Agreement governs the sale of office furniture between Buyer "
            "and Seller. Payment is due within 30 days of delivery. Title "
            "passes upon full payment. This Agreement is governed by the laws "
            "of the State of New York and may be terminated by either party "
            "upon written notice."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_RESIDUALS_01"]
        assert len(findings) == 0


class TestUnableToDetermineForShortDocuments:
    def test_short_snippet_with_topic_but_no_verdict_is_unable_to_determine(self, engine):
        text = "Provider shall process personal data."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "M_BREACH_NOTIFY_01"]
        assert len(findings) == 1
        assert findings[0].finding_type == FindingType.UNABLE_TO_DETERMINE.value
        assert findings[0].severity == Severity.LOW


class TestReportWordingIsDistinct:
    def test_finding_type_labels_are_precise_and_distinct(self):
        assert FINDING_TYPE_LABELS[FindingType.ADVERSE_LANGUAGE_DETECTED.value] == "Adverse language detected"
        assert FINDING_TYPE_LABELS[FindingType.EXPECTED_PROTECTION_NOT_FOUND.value] == "Expected protection not found"
        assert FINDING_TYPE_LABELS[FindingType.UNABLE_TO_DETERMINE.value] == "Unable to determine"
        assert len(set(FINDING_TYPE_LABELS.values())) == 3

    def test_presence_risk_findings_are_always_adverse_language_detected(self, engine):
        text = "The Contractor shall indemnify the Client for all claims, notwithstanding any limitation of liability."
        result = engine.analyze(text)
        indem = [f for f in result["findings"] if f.rule_id == "H_INDEM_01"]
        assert len(indem) == 1
        assert indem[0].finding_type == FindingType.ADVERSE_LANGUAGE_DETECTED.value
