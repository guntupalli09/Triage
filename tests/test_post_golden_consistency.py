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
