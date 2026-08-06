"""Integration test for playbook/decision_engine.py — Finding list in,
PolicyEvaluation + PolicyDecision rows out, ties Inheritance Resolver +
Topic Binding + Policy Engine together end to end."""
from types import SimpleNamespace

from playbook.db_models import Firm, PolicySet, PolicyRule
from playbook.decision_engine import DecisionEngine


def _finding(rule_id, severity="medium", finding_type="adverse_language_detected"):
    return SimpleNamespace(rule_id=rule_id, severity=severity, finding_type=finding_type)


def test_evaluate_produces_one_decision_per_finding_never_drops_any(db_session):
    firm = Firm(name="Firm", slug="firm-dec"); db_session.add(firm); db_session.flush()
    ps = PolicySet(firm_id=firm.id, name="Firm Default", status="published", version_major=1, version_minor=0)
    db_session.add(ps); db_session.flush()
    db_session.add(PolicyRule(policy_set_id=ps.id, policy_topic="INDEM", title="Indemnification", status="prohibited"))
    db_session.commit()

    findings = [
        _finding("H_INDEM_01"),
        _finding("L_UNKNOWN_TOPIC_01"),  # no policy authored for this topic
        _finding("M_SOMETHING_02", finding_type="unable_to_determine"),  # also unbound
    ]

    evaluation = DecisionEngine.evaluate(
        db_session, contract_id=1, findings=findings, firm_id=firm.id, rule_engine_version="7.2.0",
    )
    db_session.commit()

    assert len(evaluation.decisions) == 3
    statuses = {d.rule_id: d.policy_status for d in evaluation.decisions}
    assert statuses["H_INDEM_01"] == "PROHIBITED"
    assert statuses["L_UNKNOWN_TOPIC_01"] == "NOT_APPLICABLE"
    assert statuses["M_SOMETHING_02"] == "NOT_APPLICABLE"  # unbound topic, even though UNABLE_TO_DETERMINE

    # finding_key is unique per occurrence, not per rule_id
    keys = [d.finding_key for d in evaluation.decisions]
    assert keys == ["H_INDEM_01#0", "L_UNKNOWN_TOPIC_01#1", "M_SOMETHING_02#2"]


def test_evaluate_works_with_dict_findings_too(db_session):
    firm = Firm(name="Firm", slug="firm-dec2"); db_session.add(firm); db_session.flush()
    ps = PolicySet(firm_id=firm.id, name="Firm Default", status="published", version_major=1, version_minor=0)
    db_session.add(ps); db_session.flush()
    db_session.add(PolicyRule(policy_set_id=ps.id, policy_topic="LOL", title="Liability Cap", status="negotiate"))
    db_session.commit()

    findings = [{"rule_id": "M_LOL_01", "severity": "medium", "finding_type": "adverse_language_detected"}]
    evaluation = DecisionEngine.evaluate(
        db_session, contract_id=2, findings=findings, firm_id=firm.id, rule_engine_version="7.2.0",
    )
    db_session.commit()
    assert evaluation.decisions[0].policy_status == "NEGOTIABLE"
