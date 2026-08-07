"""
RBAC tests (P8): seeding idempotency, permission checks, grant/revoke,
initial-admin bootstrap, and end-to-end that a granted "admin" role (not
an email string) is what controls access to /admin.
"""
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DEV_MODE", "true")

import rbac
from database import Base
from models import Permission, Role, User, UserRole
import analytics_models  # noqa: F401


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'rbac_test.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_user(db, email="user@example.com") -> User:
    user = User(email=email, password_hash="x")
    db.add(user)
    db.commit()
    return user


# --- Seeding ---

def test_seeding_creates_default_roles_and_permissions(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    role_names = {r.name for r in db_session.query(Role).all()}
    assert "admin" in role_names
    assert "user" in role_names
    perm_names = {p.name for p in db_session.query(Permission).all()}
    assert "admin.dashboard.view" in perm_names


def test_seeding_is_idempotent(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    rbac.ensure_seed_roles_and_permissions(db_session)
    rbac.ensure_seed_roles_and_permissions(db_session)
    assert db_session.query(Role).filter(Role.name == "admin").count() == 1
    assert db_session.query(Permission).filter(Permission.name == "admin.dashboard.view").count() == 1


def test_admin_role_has_dashboard_permission_after_seeding(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    assert "admin.dashboard.view" in {p.name for p in admin_role.permissions}


def test_user_role_has_no_permissions_by_default(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    user_role = db_session.query(Role).filter(Role.name == "user").first()
    assert user_role.permissions == []


# --- Permission checks ---

def test_user_without_role_lacks_permission(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session)
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is False


def test_user_with_admin_role_has_permission(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session)
    rbac.grant_role(db_session, user, "admin")
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is True


def test_user_with_only_user_role_lacks_admin_permission(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session)
    rbac.grant_role(db_session, user, "user")
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is False


def test_none_user_has_no_permission(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    assert rbac.user_has_permission(db_session, None, "admin.dashboard.view") is False


def test_unknown_permission_name_returns_false(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session)
    rbac.grant_role(db_session, user, "admin")
    assert rbac.user_has_permission(db_session, user, "nonexistent.permission") is False


# --- Grant / revoke ---

def test_grant_role_is_idempotent(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session)
    rbac.grant_role(db_session, user, "admin")
    rbac.grant_role(db_session, user, "admin")
    assert db_session.query(UserRole).filter(UserRole.user_id == user.id).count() == 1


def test_grant_unknown_role_raises(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session)
    with pytest.raises(ValueError):
        rbac.grant_role(db_session, user, "superuser")


def test_revoke_role_removes_assignment(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session)
    rbac.grant_role(db_session, user, "admin")
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is True

    revoked = rbac.revoke_role(db_session, user, "admin")
    assert revoked is True
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is False


def test_revoke_role_user_never_had_returns_false(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session)
    assert rbac.revoke_role(db_session, user, "admin") is False


def test_get_user_roles(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session)
    rbac.grant_role(db_session, user, "user")
    rbac.grant_role(db_session, user, "admin")
    assert set(rbac.get_user_roles(db_session, user)) == {"user", "admin"}


def test_grant_role_records_granted_by(db_session):
    rbac.ensure_seed_roles_and_permissions(db_session)
    granter = _make_user(db_session, "granter@example.com")
    grantee = _make_user(db_session, "grantee@example.com")
    assignment = rbac.grant_role(db_session, grantee, "admin", granted_by_user_id=granter.id)
    assert assignment.granted_by_user_id == granter.id


# --- Initial admin bootstrap ---

def test_bootstrap_grants_admin_when_configured_user_exists(db_session, monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", "bootstrap-admin@example.com")
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session, "bootstrap-admin@example.com")

    rbac.bootstrap_initial_admin(db_session)
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is True


def test_bootstrap_does_nothing_without_env_var(db_session, monkeypatch):
    monkeypatch.delenv("INITIAL_ADMIN_EMAIL", raising=False)
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session, "nobody-special@example.com")

    rbac.bootstrap_initial_admin(db_session)
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is False


def test_bootstrap_does_nothing_if_user_does_not_exist_yet(db_session, monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", "not-registered-yet@example.com")
    rbac.ensure_seed_roles_and_permissions(db_session)
    rbac.bootstrap_initial_admin(db_session)  # must not raise
    assert db_session.query(UserRole).count() == 0


def test_bootstrap_only_grants_once_even_if_admin_later_revoked(db_session, monkeypatch):
    """Once ANY admin exists, bootstrap never grants again — including
    after an operator explicitly revokes the bootstrapped admin. This is a
    one-time convenience, not a standing authorization rule."""
    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", "bootstrap-admin@example.com")
    rbac.ensure_seed_roles_and_permissions(db_session)
    user = _make_user(db_session, "bootstrap-admin@example.com")

    rbac.bootstrap_initial_admin(db_session)
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is True

    rbac.revoke_role(db_session, user, "admin")
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is False

    # A later startup must not silently re-grant it.
    rbac.bootstrap_initial_admin(db_session)
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is False


def test_bootstrap_does_not_grant_to_a_different_user_once_any_admin_exists(db_session, monkeypatch):
    rbac.ensure_seed_roles_and_permissions(db_session)
    first_admin = _make_user(db_session, "first-admin@example.com")
    rbac.grant_role(db_session, first_admin, "admin")

    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", "second-user@example.com")
    second_user = _make_user(db_session, "second-user@example.com")
    rbac.bootstrap_initial_admin(db_session)
    assert rbac.user_has_permission(db_session, second_user, "admin.dashboard.view") is False
