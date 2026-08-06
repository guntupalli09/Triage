"""Tests for playbook/inheritance.py — the resolution algorithm merges
PolicySets from least to most specific, overwriting only on a shared
(policy_topic) key, and stays deterministic even with only Firm-level
defaults present."""
import pytest

from playbook.db_models import (
    Firm, Organization, PracticeGroup, Client, Matter, ContractType, PolicySet, PolicyRule,
)
from playbook.inheritance import InheritanceResolver


def _build_hierarchy(db):
    firm = Firm(name="Test Firm", slug="test-firm")
    db.add(firm); db.flush()
    org = Organization(firm_id=firm.id, name="Org"); db.add(org); db.flush()
    pg = PracticeGroup(organization_id=org.id, name="Commercial Practice"); db.add(pg); db.flush()
    client = Client(practice_group_id=pg.id, name="Client XYZ"); db.add(client); db.flush()
    matter = Matter(client_id=client.id, name="Matter 103"); db.add(matter); db.flush()
    ct = ContractType(firm_id=firm.id, name="Vendor Agreements", slug="vendor-agreements"); db.add(ct); db.flush()
    db.commit()
    return firm, org, pg, client, matter, ct


def _published_set(db, **kwargs):
    ps = PolicySet(status="published", version_major=1, version_minor=0, **kwargs)
    db.add(ps); db.flush()
    return ps


def test_resolves_firm_level_default_with_no_ancestors(db_session):
    firm, *_ = _build_hierarchy(db_session)
    ps = _published_set(db_session, firm_id=firm.id, name="Firm Default")
    db_session.add(PolicyRule(policy_set_id=ps.id, policy_topic="INDEM", title="Firm Indem", status="prohibited"))
    db_session.commit()

    effective = InheritanceResolver.resolve(db_session, firm.id)
    assert effective.get("INDEM").title == "Firm Indem"
    assert effective.policy_set_ids == [ps.id]


def test_matter_level_overrides_firm_level_for_same_topic(db_session):
    firm, org, pg, client, matter, ct = _build_hierarchy(db_session)

    firm_ps = _published_set(db_session, firm_id=firm.id, name="Firm Default")
    db_session.add(PolicyRule(policy_set_id=firm_ps.id, policy_topic="INDEM", title="Firm Indem", status="prohibited"))
    db_session.add(PolicyRule(policy_set_id=firm_ps.id, policy_topic="LOL", title="Firm LOL", status="negotiate"))
    db_session.flush()

    matter_ps = _published_set(db_session, firm_id=firm.id, matter_id=matter.id, name="Matter Override")
    db_session.add(PolicyRule(policy_set_id=matter_ps.id, policy_topic="INDEM", title="Matter Indem", status="negotiate"))
    db_session.commit()

    effective = InheritanceResolver.resolve(db_session, firm.id, matter_id=matter.id)

    # INDEM: matter-level wins (same topic key, more specific)
    assert effective.get("INDEM").title == "Matter Indem"
    # LOL: only defined at firm level, untouched by the matter-level set
    assert effective.get("LOL").title == "Firm LOL"
    assert set(effective.policy_set_ids) == {firm_ps.id, matter_ps.id}


def test_contract_type_specific_set_preferred_over_level_wide_set(db_session):
    firm, org, pg, client, matter, ct = _build_hierarchy(db_session)

    level_wide = _published_set(db_session, firm_id=firm.id, matter_id=matter.id, name="Matter Wide")
    db_session.add(PolicyRule(policy_set_id=level_wide.id, policy_topic="INDEM", title="Wide Indem", status="negotiate"))
    db_session.flush()

    specific = _published_set(db_session, firm_id=firm.id, matter_id=matter.id, contract_type_id=ct.id, name="Matter Vendor-Specific")
    db_session.add(PolicyRule(policy_set_id=specific.id, policy_topic="INDEM", title="Vendor Indem", status="prohibited"))
    db_session.commit()

    effective = InheritanceResolver.resolve(db_session, firm.id, matter_id=matter.id, contract_type_id=ct.id)
    assert effective.get("INDEM").title == "Vendor Indem"


def test_deprecated_policy_set_is_ignored(db_session):
    firm, *_ = _build_hierarchy(db_session)
    ps = _published_set(db_session, firm_id=firm.id, name="Deprecated Set")
    ps.deprecated = True
    ps.status = "deprecated"
    db_session.add(PolicyRule(policy_set_id=ps.id, policy_topic="INDEM", title="Old Indem", status="prohibited"))
    db_session.commit()

    effective = InheritanceResolver.resolve(db_session, firm.id)
    assert effective.get("INDEM") is None


def test_no_policy_sets_at_all_resolves_to_empty_but_valid(db_session):
    firm, *_ = _build_hierarchy(db_session)
    effective = InheritanceResolver.resolve(db_session, firm.id, matter_id=None)
    assert effective.topics == {}
    assert effective.policy_set_ids == []
