"""Post-golden consistency: inspector UX + consequential provenance + authority framing.

Does not change Active playbook LoL/Indemnification policy configuration.
"""
from __future__ import annotations

from clause_quality import analyze_indemnification_clause, analyze_liability_clause
from contract_facts.liability_bridge import canonical_liability_from_legacy
from liability_policy_engine import extract_liability_facts
from tests.fixtures.golden_mock_saas_contract import GOLDEN_MOCK_SAAS_CONTRACT


def test_consequential_evidence_cites_waiver_not_fee_period():
    facts = extract_liability_facts(GOLDEN_MOCK_SAAS_CONTRACT)
    canon = canonical_liability_from_legacy(facts)
    cons = canon.controlling.consequential_damages_excluded
    assert cons.is_known and cons.value is True
    excerpt = (cons.evidence.excerpt if cons.evidence else "").lower()
    assert "consequential" in excerpt
    assert "six (6) months" not in excerpt
    assert "fee" not in excerpt or "liable" in excerpt


def test_liability_inspector_labels_inside_cap_not_as_missing_carveout():
    facts = extract_liability_facts(GOLDEN_MOCK_SAAS_CONTRACT)
    canon = canonical_liability_from_legacy(facts)
    report = analyze_liability_clause(GOLDEN_MOCK_SAAS_CONTRACT, canonical_liability=canon)
    by_key = {e.key: e for e in report.elements}
    assert by_key["consequential_damages_excluded"].present is True
    carve = by_key["high_severity_carveouts"]
    fraud = by_key["fraud_exception"]
    assert carve.present is False
    assert fraud.present is False
    assert carve.display_tone == "info"
    assert fraud.display_tone == "info"
    assert "inside the general liability cap" in carve.detail.lower()
    assert "inside the general liability cap" in fraud.detail.lower()
    assert "silent omission" in carve.detail.lower() or "expressly places" in carve.detail.lower()


def test_indemnification_inspector_accepts_split_reciprocal_and_states_checklist_role():
    report = analyze_indemnification_clause(GOLDEN_MOCK_SAAS_CONTRACT)
    by_key = {e.key: e for e in report.elements}
    assert by_key["mutual_or_reciprocal"].present is True
    assert report.score == 100
    assert "playbook" in report.methodology_note.lower() or "drafting-completeness" in report.methodology_note.lower()


def test_raw_mutual_regex_accepts_each_partys_total_aggregate():
    text = (
        "LIMITATION OF LIABILITY. EACH PARTY'S TOTAL AGGREGATE LIABILITY SHALL NOT EXCEED "
        "THE FEES PAID DURING THE PRIOR TWELVE MONTHS."
    )
    report = analyze_liability_clause(text)
    mutual = next(e for e in report.elements if e.key == "mutual_application")
    assert mutual.present is True


# Live 55 fingerprint: soft §6.2 exclusion that legacy extract leaves unestablished.
_SOFT_CONSEQUENTIAL_LOL = """
6. Limitation of Liability.
6.1 Cap. EACH PARTY'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT SHALL NOT EXCEED THE FEES PAID OR PAYABLE BY CUSTOMER TO PROVIDER DURING THE SIX (6) MONTHS PRECEDING THE CLAIM.
6.2 Exclusion of Damages. Neither party will have any liability for consequential, indirect, incidental, special, or punitive damages, regardless of the form of action.
6.3 Applicability. THE LIMITATIONS IN THIS SECTION 6 SHALL APPLY TO INDEMNIFICATION OBLIGATIONS, CONFIDENTIALITY, SECURITY INCIDENTS, DATA PROTECTION, INTELLECTUAL PROPERTY, GROSS NEGLIGENCE, WILLFUL MISCONDUCT, AND FRAUD.
""".strip()

_CAP_AND_SECTION_ONLY_LOL = """
6. Limitation of Liability.
6.1 Cap. EACH PARTY'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT SHALL NOT EXCEED THE FEES PAID OR PAYABLE BY CUSTOMER TO PROVIDER DURING THE SIX (6) MONTHS PRECEDING THE CLAIM.
6.3 Applicability. THE LIMITATIONS IN THIS SECTION 6 SHALL APPLY TO INDEMNIFICATION OBLIGATIONS, CONFIDENTIALITY, SECURITY INCIDENTS, DATA PROTECTION, INTELLECTUAL PROPERTY, GROSS NEGLIGENCE, WILLFUL MISCONDUCT, AND FRAUD.
""".strip()

# Live 65 fingerprint: defend-and-indemnify order + "claims by a third party".
_DEFEND_AND_INDEMNIFY_RECIPROCAL = """
5. Indemnification.
5.1 Provider Indemnity. Provider shall defend and indemnify Customer against any claims by a third party arising out of infringement of intellectual property rights.
5.2 Customer Indemnity. Customer shall defend and indemnify Provider against any claims arising out of Customer's breach.
5.3 Defense. The indemnifying party will control the defense and settlement of any claim. The indemnified party shall give prompt written notice of any claim.
""".strip()


def test_bridge_admits_soft_consequential_exclusion_when_legacy_unestablished():
    facts = extract_liability_facts(_SOFT_CONSEQUENTIAL_LOL)
    assert facts.controlling_provision.consequential_damages_established is False
    canon = canonical_liability_from_legacy(facts)
    cons = canon.controlling.consequential_damages_excluded
    assert cons.is_known and cons.value is True
    report = analyze_liability_clause(_SOFT_CONSEQUENTIAL_LOL, canonical_liability=canon)
    by_key = {e.key: e for e in report.elements}
    assert by_key["consequential_damages_excluded"].present is True
    assert by_key["high_severity_carveouts"].display_tone == "info"
    assert report.score == 75


def test_bridge_does_not_invent_consequential_from_cap_and_section_only():
    facts = extract_liability_facts(_CAP_AND_SECTION_ONLY_LOL)
    canon = canonical_liability_from_legacy(facts)
    cons = canon.controlling.consequential_damages_excluded
    assert not (cons.is_known and cons.value is True)
    report = analyze_liability_clause(_CAP_AND_SECTION_ONLY_LOL, canonical_liability=canon)
    by_key = {e.key: e for e in report.elements}
    assert by_key["consequential_damages_excluded"].present is False
    assert by_key["high_severity_carveouts"].display_tone == "info"
    assert report.score == 55


def test_indemnification_inspector_recognizes_defend_and_indemnify_reciprocal():
    report = analyze_indemnification_clause(_DEFEND_AND_INDEMNIFY_RECIPROCAL)
    by_key = {e.key: e for e in report.elements}
    assert by_key["mutual_or_reciprocal"].present is True
    assert by_key["third_party_claims_scope"].present is True
    assert report.score == 100
