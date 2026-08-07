"""
Role-based access control (P8) — replaces the previous single hardcoded-
admin-email check (`user.email.lower() == ADMIN_EMAIL.lower()`) with
data-driven roles, permissions, and role assignments (see models.py: Role,
Permission, UserRole).

Seed data (DEFAULT_ROLES) is applied idempotently at startup by
ensure_seed_roles_and_permissions(). The only bootstrap concession to the
old hardcoded-email model is bootstrap_initial_admin(): if INITIAL_ADMIN_EMAIL
is configured and no admin role has ever been assigned to anyone yet, the
matching user (if they've already registered) is granted the admin role
once — this exists purely so a fresh deployment isn't locked out of its own
admin dashboard with no way in, not as a permanent authorization check.
Every authorization decision after that first grant is role-data-driven;
operators manage further assignments with manage_roles.py.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from models import AuditLog, Permission, Role, User, UserRole, role_permissions

logger = logging.getLogger(__name__)

# role name -> set of permission names granted to it.
DEFAULT_ROLES = {
    "admin": {"admin.dashboard.view"},
    "user": set(),
}

PERMISSION_DESCRIPTIONS = {
    "admin.dashboard.view": "View the admin analytics dashboard",
}


def ensure_seed_roles_and_permissions(db: Session) -> None:
    """Idempotent: creates any missing roles/permissions from DEFAULT_ROLES
    and makes sure each role has exactly the permissions listed there. Safe
    to call on every startup."""
    all_permission_names = {p for perms in DEFAULT_ROLES.values() for p in perms}
    permissions_by_name = {p.name: p for p in db.query(Permission).all()}
    for name in all_permission_names:
        if name not in permissions_by_name:
            perm = Permission(name=name, description=PERMISSION_DESCRIPTIONS.get(name))
            db.add(perm)
            permissions_by_name[name] = perm
    db.flush()

    roles_by_name = {r.name: r for r in db.query(Role).all()}
    for role_name, permission_names in DEFAULT_ROLES.items():
        role = roles_by_name.get(role_name)
        if role is None:
            role = Role(name=role_name)
            db.add(role)
            db.flush()
            roles_by_name[role_name] = role
        current = {p.name for p in role.permissions}
        for permission_name in permission_names - current:
            role.permissions.append(permissions_by_name[permission_name])

    db.commit()


def user_has_permission(db: Session, user: Optional[User], permission_name: str) -> bool:
    if user is None:
        return False
    match = (
        db.query(UserRole)
        .join(Role, UserRole.role_id == Role.id)
        .join(role_permissions, role_permissions.c.role_id == Role.id)
        .join(Permission, Permission.id == role_permissions.c.permission_id)
        .filter(UserRole.user_id == user.id, Permission.name == permission_name)
        .first()
    )
    return match is not None


def get_user_roles(db: Session, user: User) -> list[str]:
    return [
        ur.role.name for ur in
        db.query(UserRole).join(Role, UserRole.role_id == Role.id).filter(UserRole.user_id == user.id).all()
    ]


def grant_role(db: Session, user: User, role_name: str, *, granted_by_user_id: Optional[int] = None) -> UserRole:
    role = db.query(Role).filter(Role.name == role_name).first()
    if role is None:
        raise ValueError(f"Unknown role: {role_name!r}")
    existing = db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first()
    if existing:
        return existing
    assignment = UserRole(user_id=user.id, role_id=role.id, granted_by_user_id=granted_by_user_id)
    db.add(assignment)
    db.commit()
    logger.info(f"Granted role {role_name!r} to user_id={user.id}")
    return assignment


def revoke_role(db: Session, user: User, role_name: str) -> bool:
    role = db.query(Role).filter(Role.name == role_name).first()
    if role is None:
        return False
    assignment = db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first()
    if not assignment:
        return False
    db.delete(assignment)
    db.commit()
    logger.info(f"Revoked role {role_name!r} from user_id={user.id}")
    return True


_BOOTSTRAP_MARKER_EVENT = "rbac_admin_bootstrapped"


def _bootstrap_already_ran(db: Session) -> bool:
    """A permanent marker in the (immutable) audit log — distinct from
    "does an admin currently exist", which would go back to false the
    moment an operator revokes the bootstrapped admin, letting this
    function silently re-grant it on the next restart. Once bootstrap has
    fired, it must never fire again, revoked or not."""
    return db.query(AuditLog).filter(AuditLog.event_type == _BOOTSTRAP_MARKER_EVENT).first() is not None


def bootstrap_initial_admin(db: Session) -> None:
    """One-time convenience: grants the admin role to INITIAL_ADMIN_EMAIL's
    user if (a) that env var is set, (b) the user already exists, and
    (c) this has never successfully run before and no admin is already
    assigned. This is a bootstrap for a brand-new deployment with no way
    in otherwise — not an ongoing authorization check — and it never fires
    a second time, including after an operator revokes the admin it
    granted."""
    initial_admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
    if not initial_admin_email:
        return

    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role is None:
        return  # seeding hasn't run yet; nothing to bootstrap onto

    if _bootstrap_already_ran(db):
        return

    any_admin_exists = db.query(UserRole).filter(UserRole.role_id == admin_role.id).first() is not None
    if any_admin_exists:
        return

    user = db.query(User).filter(User.email == initial_admin_email).first()
    if user is None:
        logger.info(
            f"INITIAL_ADMIN_EMAIL={initial_admin_email!r} is configured but no matching user "
            "exists yet — will grant the admin role automatically once they register, "
            "on a later startup, unless an admin has been assigned in the meantime."
        )
        return

    grant_role(db, user, "admin")
    db.add(AuditLog(
        event_type=_BOOTSTRAP_MARKER_EVENT, actor_user_id=user.id,
        target_type="user", target_id=user.id, success=True,
        detail=initial_admin_email,
    ))
    db.commit()
    logger.info(f"Bootstrapped initial admin: {initial_admin_email}")
