"""Tests for playbook/version_manager.py — clone/publish/rollback/compare
round-trip correctly and every transition is audited."""
import pytest

from playbook.db_models import Firm, PolicySet, PolicyRule
from playbook import version_manager, audit_engine
from playbook.repository import NotFoundError


def _seed_published_set(db, firm_id):
    ps = PolicySet(firm_id=firm_id, name="Base Set", status="published", version_major=1, version_minor=0)
    db.add(ps); db.flush()
    db.add(PolicyRule(policy_set_id=ps.id, policy_topic="INDEM", title="Indem", status="prohibited"))
    db.commit()
    return ps


def test_clone_creates_draft_copy_of_rules(db_session):
    firm = Firm(name="Firm", slug="firm-vm1"); db_session.add(firm); db_session.flush()
    original = _seed_published_set(db_session, firm.id)

    draft = version_manager.clone(db_session, firm.id, original.id, actor_user_id=1)
    db_session.commit()

    assert draft.status == "draft"
    assert draft.version_minor == original.version_minor + 1
    assert draft.previous_version_id == original.id
    assert len(draft.rules) == 1
    assert draft.rules[0].policy_topic == "INDEM"
    assert draft.rules[0].id != original.rules[0].id  # a real copy, not a shared row


def test_publish_deprecates_previous_version_and_writes_changelog(db_session):
    firm = Firm(name="Firm", slug="firm-vm2"); db_session.add(firm); db_session.flush()
    original = _seed_published_set(db_session, firm.id)
    draft = version_manager.clone(db_session, firm.id, original.id, actor_user_id=1)
    db_session.commit()

    published = version_manager.publish(db_session, firm.id, draft.id, approved_by_user_id=1)
    db_session.commit()

    assert published.status == "published"
    assert published.approved_by_user_id == 1
    refreshed_original = db_session.query(PolicySet).filter_by(id=original.id).first()
    assert refreshed_original.deprecated is True
    assert len(published.change_logs) == 1


def test_publish_rejects_non_draft_set(db_session):
    firm = Firm(name="Firm", slug="firm-vm3"); db_session.add(firm); db_session.flush()
    original = _seed_published_set(db_session, firm.id)
    with pytest.raises(ValueError):
        version_manager.publish(db_session, firm.id, original.id, approved_by_user_id=1)


def test_rollback_republishes_target_and_deprecates_current(db_session):
    firm = Firm(name="Firm", slug="firm-vm4"); db_session.add(firm); db_session.flush()
    v1 = _seed_published_set(db_session, firm.id)
    draft = version_manager.clone(db_session, firm.id, v1.id, actor_user_id=1)
    db_session.commit()
    v2 = version_manager.publish(db_session, firm.id, draft.id, approved_by_user_id=1)
    db_session.commit()

    # v1 is currently deprecated (superseded by v2); roll back to it.
    rolled_back = version_manager.rollback(db_session, firm.id, v2.id, v1.id, actor_user_id=1)
    db_session.commit()

    assert rolled_back.id == v1.id
    assert rolled_back.status == "published"
    refreshed_v2 = db_session.query(PolicySet).filter_by(id=v2.id).first()
    assert refreshed_v2.deprecated is True


def test_compare_versions_reports_added_removed_changed(db_session):
    firm = Firm(name="Firm", slug="firm-vm5"); db_session.add(firm); db_session.flush()
    a = PolicySet(firm_id=firm.id, name="A", status="published", version_major=1, version_minor=0)
    db_session.add(a); db_session.flush()
    db_session.add(PolicyRule(policy_set_id=a.id, policy_topic="INDEM", title="Indem", status="prohibited"))
    db_session.add(PolicyRule(policy_set_id=a.id, policy_topic="LOL", title="LOL", status="negotiate"))
    db_session.flush()

    b = PolicySet(firm_id=firm.id, name="B", status="published", version_major=1, version_minor=1)
    db_session.add(b); db_session.flush()
    db_session.add(PolicyRule(policy_set_id=b.id, policy_topic="INDEM", title="Indem", status="negotiate"))  # changed
    db_session.add(PolicyRule(policy_set_id=b.id, policy_topic="DPA", title="DPA", status="prohibited"))     # added
    db_session.commit()  # LOL removed (present in A, absent in B)

    diff = version_manager.compare_versions(db_session, firm.id, a.id, b.id)
    assert diff["added_topics"] == ["DPA"]
    assert diff["removed_topics"] == ["LOL"]
    assert len(diff["changed_topics"]) == 1
    assert diff["changed_topics"][0]["policy_topic"] == "INDEM"
    assert diff["changed_topics"][0]["diffs"]["status"] == {"from": "prohibited", "to": "negotiate"}


def test_export_import_round_trip(db_session):
    firm = Firm(name="Firm", slug="firm-vm6"); db_session.add(firm); db_session.flush()
    original = _seed_published_set(db_session, firm.id)

    exported = version_manager.export_policy_set(db_session, firm.id, original.id)
    imported = version_manager.import_policy_set(db_session, firm.id, exported, actor_user_id=1)
    db_session.commit()

    assert imported.status == "draft"  # import never silently publishes
    assert imported.name == original.name
    assert len(imported.rules) == len(original.rules)
    assert imported.rules[0].policy_topic == original.rules[0].policy_topic


def test_operations_are_firm_scoped(db_session):
    firm_a = Firm(name="Firm A", slug="firm-a-vm"); db_session.add(firm_a); db_session.flush()
    firm_b = Firm(name="Firm B", slug="firm-b-vm"); db_session.add(firm_b); db_session.flush()
    ps = _seed_published_set(db_session, firm_a.id)

    with pytest.raises(NotFoundError):
        version_manager.clone(db_session, firm_b.id, ps.id, actor_user_id=1)
