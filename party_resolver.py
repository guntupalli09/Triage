"""
Deterministic party/role resolution.

Problem this fixes: rules_engine.py's original party-direction classifier
(_PROVIDER_ROLE_RE / _CUSTOMER_ROLE_RE) matched only generic role WORDS
("vendor", "provider", "company", "customer", ...). That silently assumes
"Company" always means "the vendor" — a common convention in some NDA
templates, but wrong whenever a contract's own defined term "Company"
happens to be the CUSTOMER's short name (verified on a real contract: the
Master Service and Technology Agreement between Prevail InfoWorks, Inc.
("Prevail") and BriaCell Therapeutics Corp. ("Company") defines "Company"
as the paying customer, not the vendor — the generic word-list classifier
got this backwards).

This module resolves roles from what the contract itself says, not from a
fixed word list:

1. Find each short defined name in quotes in the preamble/PARTIES section
   (e.g. ("Prevail"), ("Company")).
2. For each defined name, scan the sentences that mention it — concentrated
   in the BACKGROUND/RECITALS, but not limited to it — for vendor-indicating
   verbs ("provides", "makes available", "licensor", ...) versus
   customer-indicating verbs ("wishes to use", "shall pay", "licensee", ...).
3. Assign the role with the higher cue count. Ties or no signal -> unknown
   (never guessed).

Pure regex + counting. No ML, no network calls: identical input text always
produces an identical PartyRoleMap, preserving the engine's determinism
guarantee.

If no defined-name role can be resolved (e.g. the contract already uses
role words directly as its defined terms, like an NDA that just says
"Disclosing Party" / "Receiving Party"), callers fall back to the existing
generic role-word matching — this module is additive, not a replacement for
that fallback path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern

VENDOR_ROLE = "vendor"
CUSTOMER_ROLE = "customer"
UNKNOWN_ROLE = "unknown"

# Generic contract words that are sometimes used AS the defined short name
# but never tell us anything about role on their own — excluded so we don't
# treat "Party" or "Agreement" as if it were a resolvable party name.
_STOP_WORDS = {
    "party", "parties", "agreement", "effective", "date", "confidential",
    "services", "software", "documentation", "term", "schedule", "exhibit",
}

# A short defined name in quotes, e.g. ("Prevail") or ("Company").
_DEFINED_NAME_RE = re.compile(r'\(\s*(?:the\s+)?["“]([A-Z][A-Za-z0-9]{1,30})["”]\s*\)')

_VENDOR_CUE_RE = re.compile(
    r"\b(provides?|shall\s+provide|providing|makes?\s+available|has\s+developed|develops?|"
    r"licensor|shall\s+deliver|delivers?|supplier|vendor|contractor|discloses?|"
    r"disclosing\s+part(?:y|ies)|shall\s+perform|performs?\s+the\s+services)\b",
    re.IGNORECASE,
)
_CUSTOMER_CUE_RE = re.compile(
    r"\b(wishes?\s+to\s+use|shall\s+pay|agreed\s+to\s+pay|agrees?\s+to\s+pay|purchases?|"
    r"licensee|customer|client|buyer|receiving\s+part(?:y|ies)|shall\s+use|agrees?\s+to\s+use|"
    r"subscri(?:bes?|ption)|shall\s+own\b)\b",
    re.IGNORECASE,
)

# Sentence splitter — deliberately simple (terminal punctuation, optional
# trailing quote/paren, then whitespace); good enough for cue-counting,
# which only needs rough sentence-level locality, not exact clause
# boundaries. The optional trailing quote/paren matters: a sentence ending
# in a quoted defined term, e.g. the "Parties." — has the period BEFORE the
# closing quote mark, which a bare lookbehind on [.!?] would miss entirely,
# silently merging that sentence with everything up to the next period.
_SENTENCE_SPLIT_RE = re.compile(r"[.!?][\"'”)]*\s+")


@dataclass(frozen=True)
class PartyRoleMap:
    """
    Resolved role of each of a contract's own defined party names, plus
    ready-to-use regexes for substituting into party-direction analysis.

    name_to_role: lowercased defined short name -> "vendor" | "customer" | "unknown"
    reviewing_party_name: the defined short name resolved to CUSTOMER_ROLE,
      used as the default "whose perspective are we reviewing from" — None
      if no customer-role name could be resolved.
    """

    name_to_role: Dict[str, str] = field(default_factory=dict)
    reviewing_party_name: Optional[str] = None
    # lowercased name -> original-case spelling as it appears in the
    # contract (e.g. "briacell" -> "BriaCell"), for human-readable output.
    display_names: Dict[str, str] = field(default_factory=dict)

    def role_of(self, name: str) -> str:
        return self.name_to_role.get(name.strip().lower(), UNKNOWN_ROLE)

    def has_resolution(self) -> bool:
        return any(r != UNKNOWN_ROLE for r in self.name_to_role.values())

    def _names_for_role(self, role: str) -> List[str]:
        return [n for n, r in self.name_to_role.items() if r == role]

    def name_for_role(self, role: str) -> Optional[str]:
        """Display-cased defined name resolved to `role`, or None."""
        names = self._names_for_role(role)
        if not names:
            return None
        return self.display_names.get(names[0], names[0])

    def role_pattern(self, role: str) -> Optional[Pattern]:
        """
        Compile a regex matching any defined name resolved to `role`, for
        drop-in use alongside (or instead of) the generic
        _PROVIDER_ROLE_RE/_CUSTOMER_ROLE_RE word lists. Returns None if no
        name resolved to that role (caller should fall back to the generic
        word list in that case).
        """
        names = self._names_for_role(role)
        if not names:
            return None
        alternation = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
        return re.compile(rf"\b(?:{alternation})\b", re.IGNORECASE)

    def perspective_of(self, role: str, reviewing_role: str = CUSTOMER_ROLE) -> str:
        """
        Translate a clause's beneficiary/obligor role into a plain-English
        favorable/unfavorable/neutral label relative to the reviewing
        party's role (defaults to customer, per standard review posture).
        """
        if role == UNKNOWN_ROLE:
            return "unclear"
        return "favorable" if role == reviewing_role else "unfavorable"


def resolve_party_roles(text: str) -> PartyRoleMap:
    """
    Deterministically resolve each defined party name in `text` to a
    vendor/customer role. See module docstring for the method.
    """
    # Defined names are declared early in the document (PARTIES/preamble);
    # restrict the search so a coincidental parenthetical quote deep in the
    # contract body doesn't get treated as a party definition.
    preamble = text[:3000]
    seen: Dict[str, None] = {}
    for m in _DEFINED_NAME_RE.finditer(preamble):
        name = m.group(1)
        if name.lower() in _STOP_WORDS:
            continue
        seen.setdefault(name, None)

    if not seen:
        return PartyRoleMap()

    name_to_role: Dict[str, str] = {}
    for name in seen:
        name_re = re.compile(rf"\b{re.escape(name)}\b")
        vendor_hits = 0
        customer_hits = 0
        for sentence in _SENTENCE_SPLIT_RE.split(text):
            if not name_re.search(sentence):
                continue
            vendor_hits += len(_VENDOR_CUE_RE.findall(sentence))
            customer_hits += len(_CUSTOMER_CUE_RE.findall(sentence))
        if vendor_hits > customer_hits:
            name_to_role[name.lower()] = VENDOR_ROLE
        elif customer_hits > vendor_hits:
            name_to_role[name.lower()] = CUSTOMER_ROLE
        else:
            name_to_role[name.lower()] = UNKNOWN_ROLE

    customer_names = [n for n, r in name_to_role.items() if r == CUSTOMER_ROLE]
    reviewing_party_name = customer_names[0] if len(customer_names) == 1 else None
    display_names = {name.lower(): name for name in seen}

    return PartyRoleMap(
        name_to_role=name_to_role,
        reviewing_party_name=reviewing_party_name,
        display_names=display_names,
    )
