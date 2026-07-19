"""
Regression suite for the v5.0 independent-audit hardening pass.

Every bug the audit identified is pinned here against the REAL contract
(tests/fixtures/briacell_contract.txt — the actual Prevail InfoWorks /
BriaCell Therapeutics Master Service and Technology Agreement, including its
literal "\\n" escape-sequence formatting, which is itself part of what's
under test — see TestParserAndChunking) plus synthetic edge cases isolating
each fix. If any of these regress, a previously-confirmed defect has come
back.
"""

import os

import pytest

from rules_engine import RuleEngine, Severity, normalize_contract_text, _chunk_text
from party_resolver import resolve_party_roles, VENDOR_ROLE, CUSTOMER_ROLE

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "briacell_contract.txt")


@pytest.fixture(scope="module")
def engine():
    return RuleEngine()


@pytest.fixture(scope="module")
def contract_text():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def result(engine, contract_text):
    return engine.analyze(contract_text)


@pytest.fixture(scope="module")
def findings_by_rule(result):
    by_rule = {}
    for f in result["findings"]:
        by_rule.setdefault(f.rule_id, []).append(f)
    return by_rule


def _one(findings_by_rule, rule_id):
    matches = findings_by_rule.get(rule_id, [])
    assert len(matches) == 1, f"expected exactly one {rule_id} finding, got {len(matches)}"
    return matches[0]


# ---------------------------------------------------------------------------
# Parser / chunking (escaped newlines, section boundaries)
# ---------------------------------------------------------------------------


class TestParserAndChunking:
    def test_fixture_uses_literal_escaped_newlines(self, contract_text):
        """Sanity check that the fixture actually exercises the bug this
        test class is about — if this ever stops being true (e.g. someone
        "cleans up" the fixture), the escaped-newline regression tests
        below would silently stop testing anything."""
        assert contract_text.count("\\n") > 100
        assert contract_text.count("\n") <= 2

    def test_normalize_unescapes_literal_newlines(self, contract_text):
        normalized = normalize_contract_text(contract_text)
        assert normalized.count("\n") > 100

    def test_chunker_produces_more_than_one_real_clause_chunk(self, contract_text):
        normalized = normalize_contract_text(contract_text)
        chunks = _chunk_text(normalized)
        assert len(chunks) > 2

    def test_evidence_spans_stay_bounded_on_real_contract(self, result):
        """No finding's evidence should bridge unrelated sections — bounded
        proximity windows and chunk boundaries together should keep every
        span well under a full section-to-section jump (verified bug: a
        1,242-char span once bridged a privacy clause to an IP clause three
        sections later)."""
        for f in result["findings"]:
            span = f.end_index - f.start_index
            assert span < 700, f"{f.rule_id} span={span} is suspiciously wide: {f.exact_snippet[:80]!r}"


# ---------------------------------------------------------------------------
# Confirmed false positives eliminated
# ---------------------------------------------------------------------------


class TestConfirmedFalsePositivesEliminated:
    def test_one_way_attorneys_fees_false(self, findings_by_rule):
        assert "H_ATTFEE_01" not in findings_by_rule

    def test_sole_discretion_suspension_false(self, findings_by_rule):
        assert "M_ACCOUNT_SUSPEND_01" not in findings_by_rule

    def test_sla_present_true(self, findings_by_rule):
        # M_SLA_01 only fires when the SLA is judged ABSENT — it must not
        # fire on a document with an explicit 99.9% uptime clause.
        assert "M_SLA_01" not in findings_by_rule

    def test_late_fee_false(self, findings_by_rule):
        assert "L_LATEFEE_01" not in findings_by_rule

    def test_data_privacy_missing_protections_false(self, findings_by_rule):
        # The contract expressly references HIPAA and GDPR — H_DATA_PRIVACY_01
        # (now REQUIRED_SECTION) must not contradict its own cited evidence.
        assert "H_DATA_PRIVACY_01" not in findings_by_rule

    def test_no_contradictory_findings_ship(self, result):
        assert result["contradiction_log"] == {}
        for f in result["findings"]:
            title_l = f.title.lower()
            rationale_l = f.rationale.lower()
            has_one_sided_title = any(w in title_l for w in ("one-sided", "one-way", "unilateral"))
            has_mutual_rationale = "applies to both parties" in rationale_l or "is mutual" in rationale_l
            assert not (has_one_sided_title and has_mutual_rationale), (
                f"{f.rule_id} title/rationale contradiction shipped: {f.title!r} / {f.rationale!r}"
            )


# ---------------------------------------------------------------------------
# Confirmed missed critical findings now detected
# ---------------------------------------------------------------------------


class TestConfirmedMissedFindingsNowDetected:
    def test_liability_cap_asymmetrical_true(self, findings_by_rule):
        f = _one(findings_by_rule, "H_ASYMMETRIC_LIABILITY_01")
        assert f.severity == Severity.CRITICAL
        assert "prevail" in f.rationale.lower()
        assert "company" in f.rationale.lower()

    def test_liability_cap_missing_carveouts_true(self, findings_by_rule):
        f = _one(findings_by_rule, "H_LOL_NO_CARVEOUT_01")
        assert f.severity == Severity.CRITICAL

    def test_vendor_indemnity_narrow_true(self, findings_by_rule):
        assert "H_INDEM_SCOPE_NARROW_01" in findings_by_rule

    def test_breach_notification_missing_true(self, findings_by_rule):
        f = _one(findings_by_rule, "M_BREACH_NOTIFY_01")
        assert f.severity == Severity.HIGH

    def test_missing_sow_grouped(self, findings_by_rule):
        f = _one(findings_by_rule, "GROUP_missing_sow_schedule_attachment")
        for rule_id in ("M_BILLING_FREQUENCY_01", "M_EXHIBIT_MISSING_01", "M_PAYMENT_TRIGGER_01", "M_PRICE_EXHIBIT_MISSING_01"):
            assert rule_id in f.related_findings
        # None of the individual members should ALSO ship as standalone
        # top-level findings once grouped.
        for rule_id in ("M_BILLING_FREQUENCY_01", "M_EXHIBIT_MISSING_01", "M_PAYMENT_TRIGGER_01", "M_PRICE_EXHIBIT_MISSING_01"):
            assert rule_id not in findings_by_rule

    def test_dpa_baa_subprocessor_audit_deletion_cert_all_present(self, findings_by_rule):
        for rule_id in (
            "M_DPA_MISSING_01",
            "M_BAA_MISSING_01",
            "M_SUBPROCESSOR_MISSING_01",
            "M_AUDIT_RIGHTS_CUSTOMER_01",
            "M_DELETION_CERT_MISSING_01",
            "M_SLA_REMEDY_EXCLUSIVITY_01",
            "M_INSURANCE_MINIMUM_MISSING_01",
            "M_REG_RESPONSIBILITY_UNALLOCATED_01",
            "M_DATA_RETURN_CONDITIONAL_01",
        ):
            assert rule_id in findings_by_rule, f"expected {rule_id} to fire on the real contract"

    def test_confidentiality_indefinite_true(self, findings_by_rule):
        f = _one(findings_by_rule, "M_CONF_01")
        assert "indefinitely" in f.exact_snippet.lower()


# ---------------------------------------------------------------------------
# Party resolution and perspective
# ---------------------------------------------------------------------------


class TestPartyResolutionAndPerspective:
    def test_party_roles_resolved_correctly(self, contract_text):
        party_map = resolve_party_roles(normalize_contract_text(contract_text))
        assert party_map.role_of("Prevail") == VENDOR_ROLE
        assert party_map.role_of("Company") == CUSTOMER_ROLE

    def test_company_only_termination_favorable(self, findings_by_rule):
        f = _one(findings_by_rule, "H_TERM_CONVENIENCE_01")
        assert f.party_direction["mutuality_status"] == "customer-only"
        assert f.perspective["favorability"] == "favorable"
        assert f.severity == Severity.LOW  # downgraded — favorable to the reviewing party, not a risk

    def test_mutual_breach_termination_not_flagged_one_sided(self, result):
        """Section 14.2 (mutual termination for material breach) must never
        be reported as a one-sided/unilateral finding — verified bug:
        H_TERM_CONVENIENCE_01 used to bridge 14.2's mutual language into
        the same finding as 14.3's one-sided right."""
        for f in result["findings"]:
            if f.rule_id != "H_TERM_CONVENIENCE_01":
                continue
            assert "either party" not in f.exact_snippet.lower() or f.party_direction.get("mutuality_status") == "mutual"

    def test_ip_assignment_favorable_to_customer(self, findings_by_rule):
        f = _one(findings_by_rule, "H_IP_01")
        assert f.perspective is not None
        assert f.perspective["favorability"] == "favorable"
        assert f.severity == Severity.LOW


# ---------------------------------------------------------------------------
# Evidence grounding
# ---------------------------------------------------------------------------


class TestEvidenceGrounding:
    def test_asymmetric_cap_evidence_points_to_section_12(self, findings_by_rule):
        f = _one(findings_by_rule, "H_ASYMMETRIC_LIABILITY_01")
        assert "liabilit" in f.exact_snippet.lower()

    def test_no_finding_evidence_is_empty(self, result):
        for f in result["findings"]:
            assert f.exact_snippet and f.exact_snippet.strip()

    def test_residuals_evidence_not_anchored_on_cover_page(self, findings_by_rule):
        """Verified bug: M_RESIDUALS_01 used to anchor on the cover-page
        banner "Confidential – Fully Executed" instead of the actual
        confidentiality clause."""
        f = _one(findings_by_rule, "M_RESIDUALS_01")
        assert "fully executed" not in f.exact_snippet.lower()


# ---------------------------------------------------------------------------
# Confidence / evidence-quality fields
# ---------------------------------------------------------------------------


class TestConfidenceFields:
    def test_every_finding_has_confidence_fields(self, result):
        for f in result["findings"]:
            assert f.confidence in ("high", "medium", "low")
            assert f.confidence_reason
            assert f.evidence_quality

    def test_direct_match_findings_are_high_confidence(self, findings_by_rule):
        f = _one(findings_by_rule, "H_ASYMMETRIC_LIABILITY_01")
        assert f.confidence == "high"

    def test_absence_findings_are_medium_confidence(self, findings_by_rule):
        f = _one(findings_by_rule, "H_LOL_NO_CARVEOUT_01")
        assert f.confidence == "medium"


# ---------------------------------------------------------------------------
# Determinism / reproducibility
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_repeated_runs_produce_identical_findings(self, engine, contract_text):
        run1 = engine.analyze(contract_text)
        run2 = engine.analyze(contract_text)
        sig1 = [(f.rule_id, f.severity.value, f.start_index, f.end_index, f.title, f.confidence) for f in run1["findings"]]
        sig2 = [(f.rule_id, f.severity.value, f.start_index, f.end_index, f.title, f.confidence) for f in run2["findings"]]
        assert sig1 == sig2
        assert run1["overall_risk"] == run2["overall_risk"]

    def test_overall_risk_is_critical(self, result):
        assert result["overall_risk"] == "critical"


# ---------------------------------------------------------------------------
# Synthetic edge cases isolating individual fixes
# ---------------------------------------------------------------------------


class TestSyntheticEdgeCases:
    def test_indemnification_defense_costs_do_not_trigger_attfee(self, engine):
        text = (
            "Vendor shall indemnify, defend, and hold harmless Customer from and against any "
            "losses, damages, and costs (including reasonable legal fees) incurred by an "
            "Indemnified Party resulting from any third-party claim caused by Vendor's breach."
        )
        result = engine.analyze(text)
        assert not [f for f in result["findings"] if f.rule_id == "H_ATTFEE_01"]

    def test_genuine_prevailing_party_fee_shifting_still_detected(self, engine):
        text = "In any action to enforce this Agreement, the prevailing party shall be entitled to recover its attorneys' fees."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_ATTFEE_01"]
        assert len(findings) == 1

    def test_decimal_percentage_sla_not_flagged_missing(self, engine):
        text = (
            "This is a hosted Software as a Service Agreement. Provider shall make the Service "
            "available in accordance with the following service level: Availability for any "
            "given month shall be at least 99.9% (\"Availability\"). Provider will provide a "
            "Service Credit for any shortfall."
        )
        result = engine.analyze(text)
        assert not [f for f in result["findings"] if f.rule_id == "M_SLA_01"]

    def test_ownership_interest_not_confused_with_financial_interest(self, engine):
        text = (
            "Customer shall solely own all rights, title, and interest in and to all of Customer "
            "Data. Provider shall make the Software available with at least 99.9% uptime."
        )
        result = engine.analyze(text)
        assert not [f for f in result["findings"] if f.rule_id == "L_LATEFEE_01"]

    def test_termination_right_not_confused_with_suspension(self, engine):
        text = "Customer may terminate this Agreement at any time for any reason upon 30 days prior written notice to Provider."
        result = engine.analyze(text)
        assert not [f for f in result["findings"] if f.rule_id == "M_ACCOUNT_SUSPEND_01"]

    def test_asymmetric_cap_detected_with_named_parties_only(self, engine):
        text = (
            'This Agreement is between Acme Corp ("Vendor") and Globex Inc ("Client"). '
            "Vendor provides software services to Client for a fee. Client wishes to use Vendor's "
            "services. VENDOR'S MAXIMUM LIABILITY FOR ANY DAMAGES SHALL IN NO EVENT EXCEED THE "
            "FEES PAID IN THE PRIOR TWELVE MONTHS."
        )
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if f.rule_id == "H_ASYMMETRIC_LIABILITY_01"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_symmetric_cap_named_both_parties_not_flagged(self, engine):
        text = (
            'This Agreement is between Acme Corp ("Vendor") and Globex Inc ("Client"). '
            "Vendor provides software services to Client for a fee. Client wishes to use Vendor's "
            "services. VENDOR'S MAXIMUM LIABILITY SHALL IN NO EVENT EXCEED THE FEES PAID IN THE "
            "PRIOR TWELVE MONTHS. CLIENT'S MAXIMUM LIABILITY SHALL IN NO EVENT EXCEED THE FEES "
            "PAID IN THE PRIOR TWELVE MONTHS."
        )
        result = engine.analyze(text)
        assert not [f for f in result["findings"] if f.rule_id == "H_ASYMMETRIC_LIABILITY_01"]

    def test_root_cause_grouping_collapses_two_members(self, engine):
        text = (
            "Pricing for the Services is set forth in Exhibit A attached hereto, which governs "
            "all fees due under this Agreement."
        )
        result = engine.analyze(text)
        grouped = [f for f in result["findings"] if f.rule_id == "GROUP_missing_sow_schedule_attachment"]
        assert len(grouped) == 1
        assert len(grouped[0].related_findings) >= 2

    def test_contradiction_reconciled_when_forced(self, engine):
        text = "Either party may terminate this Agreement for convenience at any time upon 30 days written notice to the other party."
        result = engine.analyze(text)
        findings = [f for f in result["findings"] if "termination" in f.rule_name]
        assert findings
        for f in findings:
            assert "one-sided" not in f.title.lower()
            assert "one-way" not in f.title.lower()
            assert "unilateral" not in f.title.lower()
