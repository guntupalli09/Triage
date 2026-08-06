"""Tests for playbook/migration.py — the legacy Playbook -> PolicySet
backfill, and its idempotency."""
from models import User, Playbook
from playbook.db_models import Firm, PolicySet, PolicyRule
from playbook.migration import run_legacy_playbook_migration


def test_migration_wraps_playbook_as_published_policy_set(db_session):
    user = User(email="mig@example.com", name="Mig User")
    db_session.add(user); db_session.commit()

    playbook = Playbook(
        user_id=user.id, name="Standard NDA", contract_type="NDA",
        template_text="sample",
        template_findings_json=[
            {"rule_id": "H_INDEM_01", "title": "Indemnification", "severity": "high"},
            {"rule_id": "M_LOL_02", "title": "Liability Cap", "severity": "medium"},
        ],
    )
    db_session.add(playbook); db_session.commit()

    run_legacy_playbook_migration(db_session)

    db_session.refresh(user)
    assert user.default_firm_id is not None

    ps = db_session.query(PolicySet).filter(PolicySet.legacy_playbook_id == playbook.id).first()
    assert ps is not None
    assert ps.status == "published"
    assert ps.version_major == 1 and ps.version_minor == 0

    rules = db_session.query(PolicyRule).filter(PolicyRule.policy_set_id == ps.id).all()
    topics = {r.policy_topic for r in rules}
    assert topics == {"INDEM", "LOL"}
    for r in rules:
        assert r.status == "acceptable"  # present-in-template => tolerated baseline


def test_migration_is_idempotent(db_session):
    user = User(email="mig2@example.com", name="Mig User 2")
    db_session.add(user); db_session.commit()
    playbook = Playbook(
        user_id=user.id, name="Standard MSA", template_text="sample",
        template_findings_json=[{"rule_id": "H_INDEM_01", "title": "Indemnification", "severity": "high"}],
    )
    db_session.add(playbook); db_session.commit()

    run_legacy_playbook_migration(db_session)
    first_count = db_session.query(PolicySet).filter(PolicySet.legacy_playbook_id == playbook.id).count()

    run_legacy_playbook_migration(db_session)
    second_count = db_session.query(PolicySet).filter(PolicySet.legacy_playbook_id == playbook.id).count()

    assert first_count == 1
    assert second_count == 1


def test_migration_never_modifies_the_original_playbook_row(db_session):
    user = User(email="mig3@example.com", name="Mig User 3")
    db_session.add(user); db_session.commit()
    playbook = Playbook(
        user_id=user.id, name="Standard SaaS", template_text="original text",
        template_findings_json=[{"rule_id": "H_INDEM_01", "title": "Indemnification", "severity": "high"}],
        template_risk="medium",
    )
    db_session.add(playbook); db_session.commit()
    original_text = playbook.template_text
    original_findings = list(playbook.template_findings_json)

    run_legacy_playbook_migration(db_session)

    refreshed = db_session.query(Playbook).filter(Playbook.id == playbook.id).first()
    assert refreshed.template_text == original_text
    assert refreshed.template_findings_json == original_findings
