"""Shared contract-language vocabulary normalization (Phase 5).

Liability / indemnification extractors, clause-quality inspectors, and
generic rules historically re-implemented the same surface forms
(will/shall, either/each/both party, patent/copyright/trademark → IP).
Normalize once here; consumers import these patterns instead of drifting.
"""
from __future__ import annotations

import re

# Party-mutual framing used by LoL caps and reciprocal indemnity.
MUTUAL_PARTY_PHRASE_RE = re.compile(
    r"\beither\s+part(?:y|ies)\b"
    r"|\beach\s+part(?:y|ies)\b"
    r"|\bboth\s+part(?:y|ies)\b"
    r"|\bneither\s+part(?:y|ies)\b"
    r"|\bthe\s+parties\b",
    re.IGNORECASE,
)

# Modal verbs that introduce obligations / caps in modern SaaS drafts.
OBLIGATION_MODAL_RE = re.compile(r"\b(?:shall|will|agrees?\s+to|must)\b", re.IGNORECASE)

# Cap ceiling verbs — "will not exceed" is as common as "shall not exceed".
CAP_CEILING_RE = re.compile(
    r"\b(?:shall|will)\s+not\s+exceed\b"
    r"|\bis\s+capped\s+at\b"
    r"|\bshall\s+be\s+capped\b"
    r"|\blimited\s+to\b",
    re.IGNORECASE,
)

# IP infringement including Northstar-style patent/copyright/trademark enums.
IP_INFRINGEMENT_RE = re.compile(
    r"\binfring\w+\b"
    r"|\bintellectual\s+property\b"
    r"|\b(?:patent|copyright|trademark)\b",
    re.IGNORECASE,
)

# Mutual LoL application — either/each party's liability / neither liable.
MUTUAL_LIABILITY_APPLICATION_RE = re.compile(
    r"\beither\s+party'?s?\s+(?:aggregate\s+)?liability\b"
    r"|\beach\s+party'?s?\s+(?:aggregate\s+)?liability\b"
    r"|\bboth\s+parties'?\s+liability\b"
    r"|\bneither\s+party\s+(?:shall|will)\s+be\s+liable\b",
    re.IGNORECASE,
)

# Mutual / reciprocal indemnification with shall|will|agrees to.
MUTUAL_INDEMNITY_RE = re.compile(
    r"\b(?:either|both|each)\s+part(?:y|ies)\s+(?:shall|will|agrees?\s+to)\s+"
    r"(?:defend,?\s+)?indemnif\w+\b"
    r"|\bmutual(?:ly)?\s+indemnif\w+\b",
    re.IGNORECASE,
)

# Defense obligation — shall|will defend.
DEFENSE_OBLIGATION_RE = re.compile(
    r"\b(?:shall|will)\s+defend\b"
    r"|\bdefend,?\s+indemnify\b"
    r"|\bindemnify,?\s+defend\b"
    r"|\bduty\s+to\s+defend\b",
    re.IGNORECASE,
)


def excerpt_signals_mutual_party(text: str) -> bool:
    """True when text uses either/each/both/neither party framing."""
    return bool(text and MUTUAL_PARTY_PHRASE_RE.search(text))


def excerpt_covers_ip_infringement(text: str) -> bool:
    return bool(text and IP_INFRINGEMENT_RE.search(text))
