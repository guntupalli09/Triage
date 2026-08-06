"""Tests for playbook/compliance_reporter.py — pure deterministic
aggregation over PolicyDecision/PolicyOverride, no LLM involved."""
from playbook.db_models import Firm, PolicySet, PolicyRule, PolicyEvaluation, PolicyDecision
from playbook import compliance_reporter, override_manager


def _seed(db):
    firm = Firm(name="Firm", slug="firm-cr"); db.add(firm); db.flush()
    ps = PolicySet(firm_id=firm.id, name="Set", status="published", version_major=1, version_minor=0)
    db.add(ps); db.flush()
    indem = PolicyRule(policy_set_id=ps.id, policy_topic="INDEM", title="Indem", status="prohibited", risk_score=80)
    lol = PolicyRule(policy_set_id=ps.id, policy_topic="LOL", title="LOL", status="negotiate", risk_score=40)
    db.add_all([indem, lol]); db.flush()

    evaluation = PolicyEvaluation(contract_id=1, rule_engine_version="7.2.0", resolved_policy_set_ids_json=[ps.id])
    db.add(evaluation); db.flush()

    decisions = [
        PolicyDecision(evaluation_id=evaluation.id, finding_key="H_INDEM_01#0", rule_id="H_INDEM_01", policy_rule_id=indem.id, policy_status="PROHIBITED", reason="x"),
        PolicyDecision(evaluation_id=evaluation.id, finding_key="H_INDEM_02#1", rule_id="H_INDEM_02", policy_rule_id=indem.id, policy_status="PROHIBITED", reason="x"),
        PolicyDecision(evaluation_id=evaluation.id, finding_key="M_LOL_01#2", rule_id="M_LOL_01", policy_rule_id=lol.id, policy_status="NEGOTIABLE", reason="x"),
        PolicyDecision(evaluation_id=evaluation.id, finding_key="L_X_01#3", rule_id="L_X_01", policy_rule_id=None, policy_status="NOT_APPLICABLE", reason="x"),
    ]
    db.add_all(decisions)
    db.commit()
    return firm, indem, lol, decisions


def test_counts_by_status(db_session):
    firm, indem, lol, decisions = _seed(db_session)
    counts = compliance_reporter.counts_by_status(db_session, firm.id)
    assert counts["PROHIBITED"] == 2
    assert counts["NEGOTIABLE"] == 1
    assert counts["NOT_APPLICABLE"] == 1
    assert counts["COMPLIANT"] == 0


def test_most_violated_policies(db_session):
    firm, indem, lol, decisions = _seed(db_session)
    result = compliance_reporter.most_violated_policies(db_session, firm.id)
    assert result[0]["policy_rule_id"] == indem.id
    assert result[0]["violation_count"] == 2


def test_average_negotiation_score_excludes_compliant_and_not_applicable(db_session):
    firm, indem, lol, decisions = _seed(db_session)
    # Non-compliant, non-N/A decisions: two PROHIBITED (risk_score 80 each) + one NEGOTIABLE (risk_score 40)
    avg = compliance_reporter.average_negotiation_score(db_session, firm.id)
    assert avg == round((80 + 80 + 40) / 3, 2)


def test_most_overridden_policies_reflects_recorded_overrides(db_session):
    firm, indem, lol, decisions = _seed(db_session)
    override_manager.record_override(
        db_session, firm_id=firm.id, policy_decision_id=decisions[0].id, attorney_user_id=1,
        reason="Client pushback.", overridden_status="NEGOTIABLE",
    )
    db_session.commit()

    result = compliance_reporter.most_overridden_policies(db_session, firm.id)
    assert result[0]["policy_rule_id"] == indem.id
    assert result[0]["override_count"] == 1


def test_summary_is_a_deterministic_aggregate_dict(db_session):
    firm, *_ = _seed(db_session)
    summary = compliance_reporter.summary(db_session, firm.id)
    assert set(summary.keys()) == {
        "counts_by_status", "most_violated_policies", "most_overridden_policies", "average_negotiation_score",
    }
