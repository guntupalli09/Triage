"""Plan display and upgrade-nudge helpers for templates."""
from __future__ import annotations

from typing import Optional

# Plans that should not see Upgrade CTAs in the app shell.
_NO_UPGRADE_NUDGE_PLANS = frozenset({"professional", "team", "unlimited"})

_PLAN_LABELS = {
    "none": "Free",
    "free": "Free",
    "trial": "Trial",
    "starter": "Starter",
    "professional": "Professional",
    "team": "Team",
    "unlimited": "Unlimited",
}


def show_upgrade_nudge(plan: Optional[str]) -> bool:
    return (plan or "none") not in _NO_UPGRADE_NUDGE_PLANS


def plan_display_name(plan: Optional[str]) -> str:
    key = (plan or "none").lower()
    return _PLAN_LABELS.get(key, key.replace("_", " ").title())


def is_unlimited_usage(plan: Optional[str], monthly_limit: int) -> bool:
    return (plan or "") in ("unlimited", "team") or monthly_limit >= 999999
