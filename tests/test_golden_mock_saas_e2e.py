"""Production-path golden E2E: Mock SaaS Liability + Indemnification oracle.

Exercises the same cutover orchestration as upload review:
  apply_policies_for_review → Active LoL v2 + Indemnification + interactions

Does NOT invent ACV from fees blindly — commercial extract establishes
annual_fees with provenance; resolve_annual_contract_value maps that to ACV
when reviewer deal_value is absent.
"""
from __future__ import annotations

import os
import uuid

os.environ.setdefault("DEV_MODE", "true")

import pytest

import policy_enforcement as pe
from clause_quality import analyze_liability_clause
from contract_facts.commercial_extract import extract_commercial_facts
from contract_facts.liability_bridge import canonical_liability_from_legacy
from database import SessionLocal, init_db
from models import Playbook, PolicyPosition, PolicyPositionField, User
from redline_templates import render_redline
from rules_engine import RuleEngine
from tests.fixtures.golden_mock_saas_contract import GOLDEN_MOCK_SAAS_CONTRACT
from tests.fixtures.liability_policy_v2_golden import FIRM_A
import liability_policy_engine as lpe
import playbook_authoring as pa


# Shared columns (contract_side / escalation / fallback) live on PolicyPosition,
# never inside config_json (playbook_authoring._SHARED_FIELDS).
INDEM_FALLBACK = (
    "Provider shall indemnify Customer for IP, confidentiality, law violations, "
    "bodily injury/property damage, and vendor-caused security incidents. "
    "Customer indemnity limited to Customer materials and unlawful use, third-party only."
)
INDEM_CONFIG = {
    "required_protection_triggers_json": [
        "ip_infringement",
        "confidentiality",
        "law_violations",
        "bodily_injury_property_damage",
        "vendor_security_incidents",
    ],
    "permitted_exposure_triggers_json": ["customer_materials", "unlawful_use"],
    "prohibited_exposure_triggers_json": [],
    "require_exposure_third_party_only": True,
    "require_defense_control_for_exposure": True,
    "require_notice_and_cooperation_for_exposure": False,
    "prohibit_uncapped_exposure": False,
    "exposure_preferred_multiplier": 1.0,
    "exposure_acceptable_max_multiplier": 2.0,
    "exposure_negotiate_max_multiplier": 3.0,
}


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema():
    init_db()


def _user(db) -> User:
    user = User(email=f"golden-{uuid.uuid4().hex}@test.com", password_hash="x", name="Golden")
    db.add(user)
    db.flush()
    return user


def _playbook_two_active(db, user_id) -> Playbook:
    pb = Playbook(user_id=user_id, name="Golden Active LoL+Indem", template_text="x")
    db.add(pb)
    db.flush()
    db.add(PolicyPosition(
        playbook_id=pb.id,
        clause_type="limitation_of_liability",
        status="ACTIVE",
        config_json={},
        policy_schema_version=2,
        rules_v2_json=FIRM_A,
    ))
    indem = PolicyPosition(
        playbook_id=pb.id,
        clause_type="indemnification",
        status="ACTIVE",
        config_json=dict(INDEM_CONFIG),
        policy_schema_version=1,
        contract_side="buy_side",
        escalation_approval_authority="Legal Director",
        fallback_text=INDEM_FALLBACK,
    )
    db.add(indem)
    db.flush()
    for field_name in pa.ACTIVATION_REQUIRED_FIELDS.get("indemnification", []):
        db.add(PolicyPositionField(
            policy_position_id=indem.id,
            field_name=field_name,
            value_json=INDEM_CONFIG.get(field_name),
            source="MANUAL",
            status="ESTABLISHED",
        ))
    db.commit()
    return pb


class TestGoldenMockSaasE2E:
    def test_commercial_annual_fees_and_payment_due(self):
        commercial = extract_commercial_facts(GOLDEN_MOCK_SAAS_CONTRACT)
        assert commercial.annual_fees.is_known
        assert float(commercial.annual_fees.value.amount) == 600000.0
        assert commercial.due_days_or_none() == 30
        assert commercial.payment_due.value.basis.value == "invoice_receipt"

        payment_ui = commercial.legacy_payment_terms_dict()
        assert payment_ui["due_days"] == 30

    def test_production_path_oracle(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            user = _user(db)
            pb = _playbook_two_active(db, user.id)

            # Same analysis surface as upload (rules + payment + inspector).
            analysis = RuleEngine().analyze(GOLDEN_MOCK_SAAS_CONTRACT)
            findings = []
            for f in analysis["findings"]:
                findings.append({
                    "rule_id": f.rule_id,
                    "title": f.title,
                    "severity": f.severity.value,
                    "party_direction": f.party_direction,
                    "finding_type": getattr(f, "finding_type", "adverse_language_detected"),
                    "redline": render_redline(f, analysis.get("metadata") or {}),
                })

            # No reviewer deal_value — ACV must resolve from contract annual fees.
            result = pe.apply_policies_for_review(
                db, pb, GOLDEN_MOCK_SAAS_CONTRACT, findings, context={},
            )

            active = list((result.get("policy_decisions") or {}).keys())
            assert set(active) == {"limitation_of_liability", "indemnification"}

            lol = result["policy_decisions"]["limitation_of_liability"]
            assert lol["state"] == "ESCALATE"
            assert lol.get("escalate_to") == "Supervising Partner"
            # Exactly 6 months is not a hard-stop breach.
            assert lol["state"] != "PROHIBITED"
            assert (lol.get("interaction_facts") or {}).get("acv_source") == "contract_annual_fees"
            assert "indemnification" in (
                (lol.get("interaction_facts") or {}).get("policy_requires_outside_general_cap") or []
            )

            indem = result["policy_decisions"]["indemnification"]
            assert indem["state"] == "MUST_REDLINE"
            explain = (indem.get("explanation") or "") + " " + (indem.get("required_action") or "")
            assert "ip_infringement" not in explain.lower() or "missing required trigger(s)" in explain
            # IP present ⇒ not listed among missing protection triggers.
            if "protection missing required trigger(s):" in explain:
                missing_part = explain.split("protection missing required trigger(s):", 1)[1].split(";", 1)[0]
                assert "ip_infringement" not in missing_part
            assert "confidentiality" in explain
            assert "law_violations" in explain or "violation" in explain.lower()
            assert "defense" not in explain.lower() or "we do not control" not in explain.lower()
            assert "Must redline" in (indem.get("required_action") or "")
            assert "within acceptable range" not in (indem.get("required_action") or "")

            ix = result.get("interaction_decisions") or {}
            conflict = ix.get("IX_POLICY_INDEMNITY_OUTSIDE_CAP_CONFLICT")
            assert conflict is not None
            assert conflict["state"] == "ESCALATE"
            # Surfaced as actionable finding
            ix_findings = [
                f for f in findings
                if f.get("finding_type") == "interaction_decision"
                and f.get("interaction_id") == "IX_POLICY_INDEMNITY_OUTSIDE_CAP_CONFLICT"
            ]
            assert len(ix_findings) == 1

            # Consequential: mutual title, no one-sided redline.
            cons = [f for f in findings if f.get("rule_id") == "H_CONSEQUENTIAL_01"]
            assert cons
            assert cons[0]["title"].lower().startswith("mutual")
            assert cons[0].get("redline") is None

            # Payment due from analysis path (commercial single source).
            assert analysis.get("payment_terms", {}).get("due_days") == 30

            # Inspector agrees with canonical LoL facts (cap present, mutual, consequential).
            canonical = canonical_liability_from_legacy(
                lpe.extract_liability_facts(GOLDEN_MOCK_SAAS_CONTRACT),
            )
            report = analyze_liability_clause(
                GOLDEN_MOCK_SAAS_CONTRACT, canonical_liability=canonical,
            )
            by_key = {e.key: e.present for e in report.elements}
            assert by_key["cap_present"] is True
            assert by_key["mutual_application"] is True
            assert by_key["consequential_damages_excluded"] is True
            assert report.score is not None and report.score >= 55
        finally:
            db.rollback()
            db.close()
