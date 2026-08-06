"""Tests for playbook/override_manager.py — overrides are append-only and
must never mutate the original PolicyDecision, PolicyRule, or PolicySet."""
import pytest

from playbook.db_models import Firm, PolicySet, PolicyRule, PolicyEvaluation, PolicyDecision
from playbook import override_manager


def _seed_decision(db):
    firm = Firm(name="Firm", slug="firm-ovr"); db.add(firm); db.flush()
    ps = PolicySet(firm_id=firm.id, name="Set", status="published", version_major=1, version_minor=0)
    db.add(ps); db.flush()
    rule = PolicyRule(policy_set_id=ps.id, policy_topic="INDEM", title="Indem", status="prohibited")
    db.add(rule); db.flush()
    evaluation = PolicyEvaluation(contract_id=1, rule_engine_version="7.2.0", resolved_policy_set_ids_json=[ps.id])
    db.add(evaluation); db.flush()
    decision = PolicyDecision(
        evaluation_id=evaluation.id, finding_key="H_INDEM_01#0", rule_id="H_INDEM_01",
        policy_rule_id=rule.id, policy_status="PROHIBITED", reason="Prohibited by policy.",
    )
    db.add(decision); db.flush()
    db.commit()
    return firm, decision


def test_record_override_does_not_mutate_original_decision(db_session):
    firm, decision = _seed_decision(db_session)
    original_status = decision.policy_status

    override_manager.record_override(
        db_session, firm_id=firm.id, policy_decision_id=decision.id, attorney_user_id=1,
        reason="Client insisted on broader indemnity for IP claims.", overridden_status="NEGOTIABLE",
    )
    db_session.commit()

    refreshed = db_session.query(PolicyDecision).filter_by(id=decision.id).first()
    assert refreshed.policy_status == original_status == "PROHIBITED"


def test_effective_status_reflects_latest_override(db_session):
    firm, decision = _seed_decision(db_session)
    assert override_manager.effective_status_for(db_session, decision.id) == "PROHIBITED"

    override_manager.record_override(
        db_session, firm_id=firm.id, policy_decision_id=decision.id, attorney_user_id=1,
        reason="First override.", overridden_status="NEGOTIABLE",
    )
    db_session.commit()
    assert override_manager.effective_status_for(db_session, decision.id) == "NEGOTIABLE"

    override_manager.record_override(
        db_session, firm_id=firm.id, policy_decision_id=decision.id, attorney_user_id=1,
        reason="Second override supersedes the first.", overridden_status="COMPLIANT",
    )
    db_session.commit()
    assert override_manager.effective_status_for(db_session, decision.id) == "COMPLIANT"

    # Both overrides remain on record — nothing was deleted or edited.
    assert len(override_manager.overrides_for_decision(db_session, decision.id)) == 2


def test_override_requires_non_empty_reason(db_session):
    firm, decision = _seed_decision(db_session)
    with pytest.raises(override_manager.OverrideValidationError):
        override_manager.record_override(
            db_session, firm_id=firm.id, policy_decision_id=decision.id, attorney_user_id=1,
            reason="   ", overridden_status="NEGOTIABLE",
        )


def test_override_requires_valid_status(db_session):
    firm, decision = _seed_decision(db_session)
    with pytest.raises(override_manager.OverrideValidationError):
        override_manager.record_override(
            db_session, firm_id=firm.id, policy_decision_id=decision.id, attorney_user_id=1,
            reason="Valid reason.", overridden_status="NOT_A_REAL_STATUS",
        )
