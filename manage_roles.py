"""
Operator CLI for RBAC role assignments (P8) — there is no admin UI for
this yet, so granting/revoking roles (e.g. promoting a user to admin) is a
command-line operation against the running database.

Usage:
    python manage_roles.py list-roles
    python manage_roles.py list-users [--role admin]
    python manage_roles.py grant user@example.com admin
    python manage_roles.py revoke user@example.com admin
"""
from __future__ import annotations

import argparse
import sys

import rbac
from database import SessionLocal, init_db
from models import Role, User, UserRole


def _get_user_or_exit(db, email: str) -> User:
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user:
        print(f"No user found with email {email!r}", file=sys.stderr)
        sys.exit(1)
    return user


def cmd_list_roles(db, args) -> int:
    for role in db.query(Role).order_by(Role.name).all():
        perms = ", ".join(p.name for p in role.permissions) or "(no permissions)"
        print(f"{role.name}: {perms}")
    return 0


def cmd_list_users(db, args) -> int:
    query = db.query(UserRole).join(Role, UserRole.role_id == Role.id)
    if args.role:
        query = query.filter(Role.name == args.role)
    for assignment in query.order_by(Role.name).all():
        print(f"{assignment.user.email}\t{assignment.role.name}\tgranted_at={assignment.granted_at}")
    return 0


def cmd_grant(db, args) -> int:
    user = _get_user_or_exit(db, args.email)
    try:
        rbac.grant_role(db, user, args.role)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"Granted role {args.role!r} to {user.email}")
    return 0


def cmd_revoke(db, args) -> int:
    user = _get_user_or_exit(db, args.email)
    if rbac.revoke_role(db, user, args.role):
        print(f"Revoked role {args.role!r} from {user.email}")
        return 0
    print(f"{user.email} did not have role {args.role!r}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-roles")

    p_list_users = sub.add_parser("list-users")
    p_list_users.add_argument("--role", default=None)

    p_grant = sub.add_parser("grant")
    p_grant.add_argument("email")
    p_grant.add_argument("role")

    p_revoke = sub.add_parser("revoke")
    p_revoke.add_argument("email")
    p_revoke.add_argument("role")

    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        rbac.ensure_seed_roles_and_permissions(db)
        handlers = {
            "list-roles": cmd_list_roles,
            "list-users": cmd_list_users,
            "grant": cmd_grant,
            "revoke": cmd_revoke,
        }
        return handlers[args.command](db, args)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
