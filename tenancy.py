"""
Tenant / workspace isolation helpers.

TriageCounsel historically scoped every resource to ``User.id``. Portfolio
search, Word/Google clients, and intake require a real tenant boundary so
that a user from Tenant A can never read Tenant B's contracts, facts,
search results, reports, evidence, or documents.

Backwards compatibility: every existing user is lazily provisioned a
personal tenant + default workspace. Ownership checks that previously
filtered ``Contract.user_id == user.id`` now filter by tenant, then apply
role restrictions (requesters see only their own submissions).
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, Query

from models import (
    Contract,
    IntakeRequest,
    Playbook,
    Tenant,
    User,
    Workspace,
)
import rbac

# Permissions used by the workflow layer. Seeded in rbac.DEFAULT_ROLES.
PERM_PLAYBOOK_MODIFY = "playbook.modify"
PERM_CONTRACT_REVIEW = "contract.review"
PERM_CONTRACT_INTAKE = "contract.intake"
PERM_PORTFOLIO_SEARCH = "portfolio.search"
PERM_PORTFOLIO_REPORT = "portfolio.report"
PERM_TENANT_MANAGE = "tenant.manage"
PERM_INTEGRATION_USE = "integration.use"


def ensure_user_tenant(db: Session, user: User) -> Tenant:
    """Idempotent: attach ``user`` to a personal tenant if they have none.

    Called from register, guest-account creation, login-adjacent API paths,
    and any query helper that needs a tenant id. Never creates a second
    tenant for a user who already has one.
    """
    if user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if tenant is not None:
            if not user.workspace_id:
                ws = (
                    db.query(Workspace)
                    .filter(Workspace.tenant_id == tenant.id)
                    .order_by(Workspace.id.asc())
                    .first()
                )
                if ws is None:
                    ws = Workspace(tenant_id=tenant.id, name="Default")
                    db.add(ws)
                    db.flush()
                user.workspace_id = ws.id
                db.flush()
            return tenant

    name = (user.company or user.name or user.email or "Personal workspace").strip()
    tenant = Tenant(name=name[:255], created_by_user_id=user.id)
    db.add(tenant)
    db.flush()
    workspace = Workspace(tenant_id=tenant.id, name="Default")
    db.add(workspace)
    db.flush()
    user.tenant_id = tenant.id
    user.workspace_id = workspace.id
    db.flush()
    return tenant


def user_tenant_id(db: Session, user: User) -> int:
    tenant = ensure_user_tenant(db, user)
    return tenant.id


def is_requester_only(db: Session, user: User) -> bool:
    """True when the user may submit intake but must not review others'
    contracts, modify playbooks, or see the full tenant portfolio.

    Account owners still holding the historical ``user`` role are *not*
    requester-only — that would lock existing lawyers out of their own
    reviews.
    """
    roles = set(rbac.get_user_roles(db, user))
    if "requester" in roles and not roles.intersection({"user", "legal_reviewer", "legal_admin", "admin"}):
        return True
    return False


def can_modify_playbooks(db: Session, user: User) -> bool:
    if rbac.user_has_permission(db, user, PERM_PLAYBOOK_MODIFY):
        return True
    # Historical default: a logged-in account owner with no extra roles
    # could always edit their own playbooks.
    roles = set(rbac.get_user_roles(db, user))
    return not roles or "user" in roles or "admin" in roles


def can_review_contracts(db: Session, user: User) -> bool:
    if is_requester_only(db, user):
        return False
    if rbac.user_has_permission(db, user, PERM_CONTRACT_REVIEW):
        return True
    roles = set(rbac.get_user_roles(db, user))
    return not roles or "user" in roles or "admin" in roles


def can_search_portfolio(db: Session, user: User) -> bool:
    if is_requester_only(db, user):
        return False
    if rbac.user_has_permission(db, user, PERM_PORTFOLIO_SEARCH):
        return True
    roles = set(rbac.get_user_roles(db, user))
    return not roles or "user" in roles or "admin" in roles


def require_permission(db: Session, user: User, permission_name: str, *, allow_account_owner: bool = True) -> None:
    if rbac.user_has_permission(db, user, permission_name):
        return
    if allow_account_owner:
        roles = set(rbac.get_user_roles(db, user))
        if not roles or "user" in roles or "admin" in roles:
            if permission_name != PERM_PLAYBOOK_MODIFY or not is_requester_only(db, user):
                if permission_name == PERM_PLAYBOOK_MODIFY and is_requester_only(db, user):
                    raise HTTPException(status_code=403, detail="Business users cannot modify legal playbooks.")
                return
    if permission_name == PERM_PLAYBOOK_MODIFY:
        raise HTTPException(status_code=403, detail="Business users cannot modify legal playbooks.")
    raise HTTPException(status_code=403, detail="You do not have permission to perform this action.")


def scoped_contracts(db: Session, user: User) -> Query:
    """Every contract listing/search/report starts here. Never omit tenant_id
    for rows that have one. Pre-tenancy rows (tenant_id IS NULL) remain
    visible only to their owning user_id so historical tests and unmigrated
    data keep working without leaking across tenants."""
    tenant_id = user_tenant_id(db, user)
    from sqlalchemy import or_ as _or, and_ as _and
    q = db.query(Contract).filter(
        _or(
            Contract.tenant_id == tenant_id,
            _and(Contract.tenant_id.is_(None), Contract.user_id == user.id),
        )
    )
    if is_requester_only(db, user):
        q = q.filter(Contract.user_id == user.id)
    return q


def scoped_playbooks(db: Session, user: User) -> Query:
    tenant_id = user_tenant_id(db, user)
    from sqlalchemy import or_ as _or, and_ as _and
    return db.query(Playbook).filter(
        _or(
            Playbook.tenant_id == tenant_id,
            _and(Playbook.tenant_id.is_(None), Playbook.user_id == user.id),
        )
    )


def scoped_intake(db: Session, user: User) -> Query:
    tenant_id = user_tenant_id(db, user)
    q = db.query(IntakeRequest).filter(IntakeRequest.tenant_id == tenant_id)
    if is_requester_only(db, user):
        q = q.filter(IntakeRequest.requester_user_id == user.id)
    return q


def get_accessible_contract(db: Session, user: User, contract_id: int) -> Contract:
    contract = scoped_contracts(db, user).filter(Contract.id == contract_id).first()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


def get_accessible_playbook(db: Session, user: User, playbook_id: int) -> Playbook:
    playbook = scoped_playbooks(db, user).filter(Playbook.id == playbook_id).first()
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return playbook


def stamp_new_contract(db: Session, user: User, contract: Contract) -> Contract:
    """Fill tenant/workspace on a Contract that is about to be inserted."""
    ensure_user_tenant(db, user)
    contract.tenant_id = user.tenant_id
    contract.workspace_id = contract.workspace_id or user.workspace_id
    contract.user_id = contract.user_id or user.id
    return contract


def stamp_new_playbook(db: Session, user: User, playbook: Playbook) -> Playbook:
    ensure_user_tenant(db, user)
    playbook.tenant_id = user.tenant_id
    playbook.workspace_id = playbook.workspace_id or user.workspace_id
    playbook.user_id = playbook.user_id or user.id
    return playbook


def workspaces_for_user(db: Session, user: User):
    tenant_id = user_tenant_id(db, user)
    return db.query(Workspace).filter(Workspace.tenant_id == tenant_id).order_by(Workspace.id.asc()).all()


def select_workspace(db: Session, user: User, workspace_id: Optional[int]) -> Workspace:
    tenant_id = user_tenant_id(db, user)
    if workspace_id is None:
        ws = db.query(Workspace).filter(Workspace.id == user.workspace_id, Workspace.tenant_id == tenant_id).first()
        if ws is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return ws
    ws = db.query(Workspace).filter(Workspace.id == workspace_id, Workspace.tenant_id == tenant_id).first()
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws
