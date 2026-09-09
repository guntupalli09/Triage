"""Regression: Workbench routes must render base_app.html without UndefinedError."""
from __future__ import annotations

import os
import re
import uuid

os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi.testclient import TestClient

import app_templates
import main


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


def _register(client: TestClient) -> tuple[str, int]:
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    email = f"tpl-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/register",
        data={
            "email": email,
            "password": "Str0ngP@ssw0rd!",
            "confirm_password": "Str0ngP@ssw0rd!",
            "name": "Firm",
            "company": "",
            "accept_terms": "on",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    return client.cookies.get("csrf_token"), r.status_code


def _create_playbook(client: TestClient, token: str) -> int:
    r = client.post(
        "/playbooks/new",
        data={
            "name": "Template Globals Test",
            "contract_type": "",
            "description": "",
            "lol_enabled": "",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    m = re.search(r"/playbooks/(\d+)", r.headers.get("location", ""))
    assert m
    return int(m.group(1))


def test_app_templates_registers_base_app_globals():
    env = app_templates.templates.env
    for name in (
        "csrf_token",
        "show_upgrade_nudge",
        "plan_display_name",
        "is_unlimited_usage",
        "google_signin_enabled",
        "legal",
    ):
        assert name in env.globals, f"missing Jinja global: {name}"


def test_workbench_setup_routes_render_without_500(client):
    token, _ = _register(client)
    pb_id = _create_playbook(client, token)

    for path in (
        f"/playbooks/{pb_id}/workbench",
        f"/playbooks/{pb_id}/import",
        f"/playbooks/{pb_id}/ai-import",
    ):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
        assert "Something went wrong" not in r.text
        assert "AI-assisted playbook import" in r.text if "ai-import" in path else True
