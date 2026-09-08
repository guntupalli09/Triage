"""Shared Jinja2 template environment for the app.

playbook_workbench.py must not maintain a second Jinja2Templates instance —
base_app.html depends on globals (show_upgrade_nudge, plan_display_name, etc.)
that drifted once already and caused 500s on Workbench routes including
/playbooks/{id}/ai-import. One module, one templates object.
"""
from __future__ import annotations

from fastapi.templating import Jinja2Templates

import google_oauth
import legal_config
import plan_utils
from csrf import get_csrf_token

templates = Jinja2Templates(directory="templates")
templates.env.globals["google_signin_enabled"] = google_oauth.is_configured()
templates.env.globals["csrf_token"] = get_csrf_token
templates.env.globals["legal"] = legal_config.legal_context
templates.env.globals["show_upgrade_nudge"] = plan_utils.show_upgrade_nudge
templates.env.globals["plan_display_name"] = plan_utils.plan_display_name
templates.env.globals["is_unlimited_usage"] = plan_utils.is_unlimited_usage
