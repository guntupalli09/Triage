"""
Playbook Repository — firm-scoped CRUD for the hierarchy entities and
PolicySet/PolicyRule.

Every read/write here takes firm_id explicitly and filters by it (directly
or via a join through the parent chain), never `get(id)` alone — that
discipline is what makes cross-tenant access a type error at the call site
instead of a bug that has to be remembered. This module is pure
SQLAlchemy-session-in / ORM-object-out; no HTTP, no policy classification
logic (see playbook/policy_engine.py for that).
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from playbook.db_models import (
    Firm, FirmMembership, Organization, PracticeGroup, Client, Matter,
    ContractType, PolicySet, PolicyRule,
)


class NotFoundError(Exception):
    pass


# ---------------------------------------------------------------------------
# Hierarchy entities
# ---------------------------------------------------------------------------

def get_firm(db: Session, firm_id: int) -> Firm:
    firm = db.query(Firm).filter(Firm.id == firm_id).first()
    if not firm:
        raise NotFoundError(f"Firm {firm_id} not found")
    return firm


def get_matter(db: Session, firm_id: int, matter_id: int) -> Matter:
    """Walks Matter -> Client -> PracticeGroup -> Organization -> Firm to
    confirm the Matter actually belongs to firm_id before returning it."""
    matter = (
        db.query(Matter)
        .join(Client, Matter.client_id == Client.id)
        .join(PracticeGroup, Client.practice_group_id == PracticeGroup.id)
        .join(Organization, PracticeGroup.organization_id == Organization.id)
        .filter(Matter.id == matter_id, Organization.firm_id == firm_id)
        .first()
    )
    if not matter:
        raise NotFoundError(f"Matter {matter_id} not found for firm {firm_id}")
    return matter


def get_contract_type(db: Session, firm_id: int, contract_type_id: int) -> ContractType:
    ct = db.query(ContractType).filter(
        ContractType.id == contract_type_id, ContractType.firm_id == firm_id
    ).first()
    if not ct:
        raise NotFoundError(f"ContractType {contract_type_id} not found for firm {firm_id}")
    return ct


def create_matter(db: Session, firm_id: int, client_id: int, name: str, matter_number: Optional[str] = None) -> Matter:
    client = (
        db.query(Client)
        .join(PracticeGroup, Client.practice_group_id == PracticeGroup.id)
        .join(Organization, PracticeGroup.organization_id == Organization.id)
        .filter(Client.id == client_id, Organization.firm_id == firm_id)
        .first()
    )
    if not client:
        raise NotFoundError(f"Client {client_id} not found for firm {firm_id}")
    matter = Matter(client_id=client_id, name=name, matter_number=matter_number)
    db.add(matter)
    db.flush()
    return matter


def create_contract_type(db: Session, firm_id: int, name: str, slug: str) -> ContractType:
    ct = ContractType(firm_id=firm_id, name=name, slug=slug)
    db.add(ct)
    db.flush()
    return ct


def list_hierarchy(db: Session, firm_id: int) -> dict:
    """Full tree for a firm — organizations -> practice groups -> clients ->
    matters, plus the firm's contract types. Read-only convenience for the
    "current user's firm" API endpoint; not paginated (expected to stay
    small relative to policy_sets/policy_decisions volume)."""
    orgs = db.query(Organization).filter(Organization.firm_id == firm_id).all()
    tree = []
    for org in orgs:
        pgs = db.query(PracticeGroup).filter(PracticeGroup.organization_id == org.id).all()
        pg_nodes = []
        for pg in pgs:
            clients = db.query(Client).filter(Client.practice_group_id == pg.id).all()
            client_nodes = []
            for client in clients:
                matters = db.query(Matter).filter(Matter.client_id == client.id).all()
                client_nodes.append({"id": client.id, "name": client.name, "matters": matters})
            pg_nodes.append({"id": pg.id, "name": pg.name, "clients": client_nodes})
        tree.append({"id": org.id, "name": org.name, "practice_groups": pg_nodes})
    contract_types = db.query(ContractType).filter(ContractType.firm_id == firm_id).all()
    return {"organizations": tree, "contract_types": contract_types}


# ---------------------------------------------------------------------------
# PolicySet / PolicyRule
# ---------------------------------------------------------------------------

def get_policy_set(db: Session, firm_id: int, policy_set_id: int) -> PolicySet:
    ps = db.query(PolicySet).filter(PolicySet.id == policy_set_id, PolicySet.firm_id == firm_id).first()
    if not ps:
        raise NotFoundError(f"PolicySet {policy_set_id} not found for firm {firm_id}")
    return ps


def list_policy_sets(
    db: Session, firm_id: int,
    organization_id: Optional[int] = None, practice_group_id: Optional[int] = None,
    client_id: Optional[int] = None, matter_id: Optional[int] = None,
    contract_type_id: Optional[int] = None, status: Optional[str] = None,
) -> List[PolicySet]:
    q = db.query(PolicySet).filter(PolicySet.firm_id == firm_id)
    if organization_id is not None:
        q = q.filter(PolicySet.organization_id == organization_id)
    if practice_group_id is not None:
        q = q.filter(PolicySet.practice_group_id == practice_group_id)
    if client_id is not None:
        q = q.filter(PolicySet.client_id == client_id)
    if matter_id is not None:
        q = q.filter(PolicySet.matter_id == matter_id)
    if contract_type_id is not None:
        q = q.filter(PolicySet.contract_type_id == contract_type_id)
    if status is not None:
        q = q.filter(PolicySet.status == status)
    return q.order_by(PolicySet.updated_at.desc()).all()


def create_draft_policy_set(
    db: Session, firm_id: int, name: str, author_user_id: Optional[int] = None,
    description: Optional[str] = None, organization_id: Optional[int] = None,
    practice_group_id: Optional[int] = None, client_id: Optional[int] = None,
    matter_id: Optional[int] = None, contract_type_id: Optional[int] = None,
) -> PolicySet:
    ps = PolicySet(
        firm_id=firm_id, name=name, description=description, author_user_id=author_user_id,
        organization_id=organization_id, practice_group_id=practice_group_id,
        client_id=client_id, matter_id=matter_id, contract_type_id=contract_type_id,
        status="draft", version_major=1, version_minor=0,
    )
    db.add(ps)
    db.flush()
    return ps


def add_rule(db: Session, firm_id: int, policy_set_id: int, **rule_fields) -> PolicyRule:
    ps = get_policy_set(db, firm_id, policy_set_id)
    rule = PolicyRule(policy_set_id=ps.id, **rule_fields)
    db.add(rule)
    db.flush()
    return rule


def get_rule(db: Session, firm_id: int, rule_id: int) -> PolicyRule:
    rule = (
        db.query(PolicyRule)
        .join(PolicySet, PolicyRule.policy_set_id == PolicySet.id)
        .filter(PolicyRule.id == rule_id, PolicySet.firm_id == firm_id)
        .first()
    )
    if not rule:
        raise NotFoundError(f"PolicyRule {rule_id} not found for firm {firm_id}")
    return rule


def update_rule(db: Session, firm_id: int, rule_id: int, **fields) -> PolicyRule:
    rule = get_rule(db, firm_id, rule_id)
    ps = rule.policy_set
    if ps.status != "draft":
        raise ValueError(f"PolicyRule {rule_id} belongs to a {ps.status} PolicySet — only draft sets can be edited")
    for key, value in fields.items():
        if value is not None and hasattr(rule, key):
            setattr(rule, key, value)
    db.flush()
    return rule
