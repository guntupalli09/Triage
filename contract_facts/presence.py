"""Tri-state presence for contract-side facts.

Absence of detection must never silently become False. Consumers that need
a boolean must branch on Presence explicitly; helper methods refuse to
guess.
"""
from __future__ import annotations

from enum import Enum


class Presence(str, Enum):
    """Whether a legal fact was established from the contract.

    PRESENT  — affirmative evidence establishes the fact's value
    ABSENT   — affirmative evidence establishes the fact is not present
               (e.g. the clause explicitly omits a cap, or a topic scan
               confirmed the concept is not addressed)
    UNKNOWN  — the system could not determine presence or value
               (parse failure, unsupported expression, gated confidence,
               missing subsection attachment, etc.)
    """

    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"

    @property
    def is_resolved(self) -> bool:
        return self in (Presence.PRESENT, Presence.ABSENT)

    @property
    def is_unknown(self) -> bool:
        return self is Presence.UNKNOWN


def presence_from_optional_bool(value: bool | None, *, established: bool) -> Presence:
    """Map legacy Optional[bool] + established flag onto Presence.

    Legacy engines often used (None, established=False) for UNKNOWN and
    (None, established=True) for ABSENT/"not addressed". This helper is the
    only sanctioned translation of that pattern into Presence.
    """
    if not established:
        return Presence.UNKNOWN
    if value is None:
        return Presence.ABSENT
    return Presence.PRESENT
