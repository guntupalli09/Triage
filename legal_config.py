"""Legal-entity and policy metadata for Terms, Privacy, and footers.

Set these env vars after LLC formation (see .env.example):
  LEGAL_ENTITY_NAME, LEGAL_ENTITY_STATE, LEGAL_ENTITY_ADDRESS, GOVERNING_LAW_STATE
"""
from __future__ import annotations

import os
from typing import Any, Dict


def _clean(value: str | None) -> str:
    return (value or "").strip()


def legal_context() -> Dict[str, Any]:
    entity_name = _clean(os.getenv("LEGAL_ENTITY_NAME"))
    entity_state = _clean(os.getenv("LEGAL_ENTITY_STATE"))
    entity_address = _clean(os.getenv("LEGAL_ENTITY_ADDRESS"))
    governing_law_state = _clean(os.getenv("GOVERNING_LAW_STATE")) or "Delaware"
    trade_name = "TriageCounsel"

    if entity_name and entity_state:
        entity_display = f"{entity_name}, a {entity_state} limited liability company"
    elif entity_name:
        entity_display = entity_name
    else:
        entity_display = trade_name

    return {
        "trade_name": trade_name,
        "entity_name": entity_name,
        "entity_state": entity_state,
        "entity_address": entity_address,
        "governing_law_state": governing_law_state,
        "entity_display": entity_display,
        "is_incorporated": bool(entity_name),
    }
