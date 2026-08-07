"""
Tests for manage_roles.py (P8): the operator CLI for granting/revoking
roles — there is no admin UI for this, so this script is the only way to
promote a user to admin (besides INITIAL_ADMIN_EMAIL's one-time bootstrap).
"""
import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DEV_MODE", "true")

import manage_roles
import rbac
from database import Base
from models import User
import analytics_models  # noqa: F401


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'manage_roles_test.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    rbac.ensure_seed_roles_and_permissions(session)
    yield session
    session.close()


def _make_user(db, email="user@example.com") -> User:
    user = User(email=email, password_hash="x")
    db.add(user)
    db.commit()
    return user


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_grant_promotes_user_to_admin(db_session, capsys):
    user = _make_user(db_session, "promote-me@example.com")
    rc = manage_roles.cmd_grant(db_session, _Args(email=user.email, role="admin"))
    assert rc == 0
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is True
    assert "Granted role" in capsys.readouterr().out


def test_grant_unknown_email_exits_nonzero(db_session):
    with pytest.raises(SystemExit) as exc_info:
        manage_roles.cmd_grant(db_session, _Args(email="ghost@example.com", role="admin"))
    assert exc_info.value.code == 1


def test_grant_unknown_role_returns_nonzero(db_session):
    user = _make_user(db_session, "someone@example.com")
    rc = manage_roles.cmd_grant(db_session, _Args(email=user.email, role="superuser"))
    assert rc == 1


def test_revoke_removes_admin_access(db_session):
    user = _make_user(db_session, "demote-me@example.com")
    rbac.grant_role(db_session, user, "admin")
    rc = manage_roles.cmd_revoke(db_session, _Args(email=user.email, role="admin"))
    assert rc == 0
    assert rbac.user_has_permission(db_session, user, "admin.dashboard.view") is False


def test_revoke_role_not_held_returns_nonzero(db_session):
    user = _make_user(db_session, "never-admin@example.com")
    rc = manage_roles.cmd_revoke(db_session, _Args(email=user.email, role="admin"))
    assert rc == 1


def test_list_roles_prints_seeded_roles(db_session, capsys):
    rc = manage_roles.cmd_list_roles(db_session, _Args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "admin" in out
    assert "user" in out


def test_list_users_shows_granted_roles(db_session, capsys):
    user = _make_user(db_session, "listed-admin@example.com")
    rbac.grant_role(db_session, user, "admin")
    rc = manage_roles.cmd_list_users(db_session, _Args(role=None))
    assert rc == 0
    assert "listed-admin@example.com" in capsys.readouterr().out


def test_list_users_filters_by_role(db_session, capsys):
    admin_user = _make_user(db_session, "filtered-admin@example.com")
    plain_user = _make_user(db_session, "filtered-user@example.com")
    rbac.grant_role(db_session, admin_user, "admin")
    rbac.grant_role(db_session, plain_user, "user")

    rc = manage_roles.cmd_list_users(db_session, _Args(role="admin"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "filtered-admin@example.com" in out
    assert "filtered-user@example.com" not in out
