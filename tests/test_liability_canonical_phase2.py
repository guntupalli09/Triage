"""Phase 2: fee-period extraction → canonical liability facts → LoL v2."""

import os
import uuid

os.environ.setdefault("DEV_MODE", "true")

import pytest

import liability_policy_engine as lpe
import playbook_authoring as pa
import policy_enforcement as pe
from contract_facts.liability_bridge import (
    canonical_liability_from_legacy,
    contract_cap_from_canonical,
)
from contract_facts.presence import Presence
from database import SessionLocal, init_db
from liability_evaluator_v2 import contract_cap_from_legacy
from models import Playbook, PolicyPosition, User
from policy_grammar.cap_operands import FeeRelativeCap
from policy_grammar.evaluation_context import (
    AcvSource,
    evaluation_context_from_review_context,
    resolve_annual_contract_value,
)
from policy_grammar.money import MoneyAmount
from tests.fixtures.liability_policy_v2_golden import FIRM_A


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema():
    init_db()


def _user(db) -> User:
    user = User(email=f"p2-{uuid.uuid4().hex}@test.com", password_hash="x", name="Test")
    db.add(user)
    db.flush()
    return user


def _playbook(db, user_id) -> Playbook:
    pb = Playbook(user_id=user_id, name="Phase2 LoL Playbook", template_text="x")
    db.add(pb)
    db.flush()
    return pb


# Heading + filler so a 200-char truncated excerpt from the window start
# cannot reach the SIX (6) MONTH language — the audit failure mode.
CONTRACT_6MO_PADDED = (
    "6. LIMITATION OF LIABILITY\n"
    + ("This section addresses allocation of risk between the parties. " * 8)
    + "6.1 Cap. EACH PARTY'S AGGREGATE LIABILITY UNDER THIS AGREEMENT WILL NOT EXCEED THE FEES "
    "PAID OR PAYABLE BY CUSTOMER UNDER THIS AGREEMENT DURING THE SIX (6) MONTH PERIOD IMMEDIATELY "
    "PRECEDING THE CLAIM."
)

CONTRACT_12MO_FEES = (
    "12. Limitation of Liability. Provider's aggregate liability shall not exceed fees paid or payable "
    "during the twelve (12) months preceding the claim."
)


class TestFeePeriodExtractionFirstClass:
    def test_find_cap_values_emits_fee_period_for_trailing_months(self):
        caps = lpe._find_cap_values(
            "shall not exceed fees paid or payable during the six (6) months preceding the claim"
        )
        assert len(caps) == 1
        assert caps[0].kind == "fee_period"
        assert caps[0].months == 6.0

    def test_padded_layout_does_not_depend_on_truncated_excerpt(self):
        facts = lpe.extract_liability_facts(CONTRACT_6MO_PADDED)
        provision = facts.controlling_provision
        assert provision is not None
        comps = provision.general_cap_expression.components
        assert len(comps) == 1
        assert comps[0].kind == "fee_period"
        assert comps[0].months == 6.0
        # Excerpt is the component span, not the heading+filler truncate.
        assert "SIX (6) MONTH" in provision.raw_excerpt.upper()
        assert "allocation of risk" not in provision.raw_excerpt.lower()

    def test_canonical_bridge_preserves_symbolic_months(self):
        facts = lpe.extract_liability_facts(CONTRACT_6MO_PADDED)
        canonical = canonical_liability_from_legacy(facts)
        assert canonical.clause_presence is Presence.PRESENT
        controlling = canonical.controlling
        assert controlling is not None
        assert controlling.fee_period_months() == 6.0
        expr = controlling.general_cap.value
        assert isinstance(expr.operands[0], FeeRelativeCap)
        assert expr.operands[0].months == 6.0

        cap_facts = contract_cap_from_canonical(canonical)
        assert cap_facts is not None
        assert cap_facts.fee_period_months == 6.0
        # No money conversion — still FeeRelativeCap.
        assert isinstance(cap_facts.expression.operands[0], FeeRelativeCap)

    def test_contract_cap_from_legacy_uses_components_not_excerpt(self):
        facts = lpe.extract_liability_facts(CONTRACT_6MO_PADDED)
        # Even if excerpt were corrupt, components drive the bridge.
        facts.controlling_provision.raw_excerpt = "6. LIMITATION OF LIABILITY\n" + ("x" * 200)
        cap = contract_cap_from_legacy(facts)
        assert cap is not None
        assert cap.fee_period_months == 6.0


class TestAcvProvenance:
    def test_reviewer_deal_value_precedes_contract_annual_fees(self):
        money, source = resolve_annual_contract_value(
            reviewer_deal_value=250000,
            contract_annual_fees=MoneyAmount.from_number("600000"),
        )
        assert float(money.amount) == 250000.0
        assert source is AcvSource.REVIEWER_DEAL_VALUE

    def test_contract_annual_fees_when_no_deal_value(self):
        money, source = resolve_annual_contract_value(
            reviewer_deal_value=None,
            contract_annual_fees=MoneyAmount.from_number("600000"),
        )
        assert float(money.amount) == 600000.0
        assert source is AcvSource.CONTRACT_ANNUAL_FEES

    def test_trailing_fees_never_become_acv(self):
        ctx = evaluation_context_from_review_context({})
        assert ctx.annual_contract_value is None
        assert ctx.acv_source is AcvSource.UNSPECIFIED
        # Explicit trailing field is separate and unused for ACV.
        ctx2 = evaluation_context_from_review_context(
            {"deal_value": 100000},
            contract_annual_fees=MoneyAmount.from_number("600000"),
        )
        assert ctx2.acv_source is AcvSource.REVIEWER_DEAL_VALUE
        assert float(ctx2.annual_contract_value.amount) == 100000.0
        assert ctx2.annual_fees is not None
        assert float(ctx2.annual_fees.amount) == 600000.0

    def test_context_contract_annual_fees_key(self):
        ctx = evaluation_context_from_review_context({"contract_annual_fees": 600000})
        assert ctx.acv_source is AcvSource.CONTRACT_ANNUAL_FEES
        assert float(ctx.annual_contract_value.amount) == 600000.0


class TestLoLV2SymbolicEscalate:
    def test_firm_a_escalates_6_month_symbolically_with_high_acv(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            user = _user(db)
            pb = _playbook(db, user.id)
            position = PolicyPosition(
                playbook_id=pb.id,
                clause_type="limitation_of_liability",
                status="ACTIVE",
                config_json={},
                policy_schema_version=2,
                rules_v2_json=FIRM_A,
            )
            db.add(position)
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(
                db, pb, CONTRACT_6MO_PADDED, findings, context={"deal_value": 600000},
            )
            decision = result["policy_decisions"]["limitation_of_liability"]
            assert decision["state"] == "ESCALATE"
            # Cap language from component evidence, not truncated filler.
            assert "SIX (6) MONTH" in decision["contract_language"].upper()
        finally:
            db.rollback()
            db.close()

    def test_firm_a_accepts_12_month_low_acv_via_fallback(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            user = _user(db)
            pb = _playbook(db, user.id)
            position = PolicyPosition(
                playbook_id=pb.id,
                clause_type="limitation_of_liability",
                status="ACTIVE",
                config_json={},
                policy_schema_version=2,
                rules_v2_json=FIRM_A,
            )
            db.add(position)
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(
                db, pb, CONTRACT_12MO_FEES, findings, context={"deal_value": 100000},
            )
            decision = result["policy_decisions"]["limitation_of_liability"]
            assert decision["state"] == "ACCEPT_WITH_NOTE"
        finally:
            db.rollback()
            db.close()

    def test_acv_from_contract_annual_fees_triggers_escalate(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            user = _user(db)
            pb = _playbook(db, user.id)
            position = PolicyPosition(
                playbook_id=pb.id,
                clause_type="limitation_of_liability",
                status="ACTIVE",
                config_json={},
                policy_schema_version=2,
                rules_v2_json=FIRM_A,
            )
            db.add(position)
            db.commit()

            findings = []
            # No deal_value — ACV from contract_annual_fees with provenance.
            result = pe.apply_policies_for_review(
                db, pb, CONTRACT_6MO_PADDED, findings,
                context={"contract_annual_fees": 600000},
            )
            decision = result["policy_decisions"]["limitation_of_liability"]
            assert decision["state"] == "ESCALATE"
        finally:
            db.rollback()
            db.close()
