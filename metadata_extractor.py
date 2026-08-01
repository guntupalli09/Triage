"""
Deterministic Party, Effective-Date & Contract-Type Extraction.

Product roadmap Feature 1 (see the product memo, Rev. 2) — the last
unfinished Phase-1 foundation item. If the product can't correctly state
who the parties are, when a contract starts, and what kind of agreement it
is, nothing else it says is trusted on first look; this closes that gap.

Three independent, deterministic extractors:

1. Parties — full legal entity names paired with their short defined name
   ("Prevail InfoWorks, Inc." / "Prevail"), reusing party_resolver.py's
   already-proven vendor/customer role resolution rather than duplicating
   it. Only extracts what the document's own preamble states; never
   guesses a party from context.
2. Effective date — pattern matching around "Effective Date"/"dated as of"
   anchors in the preamble. None if no confident match, never a best-guess
   date.
3. Contract type — keyword-weighted classification against known contract
   categories (NDA, MSA, SaaS, Employment, Franchise, Credit/Loan, Real
   Estate PSA, Insurance/MGA, Construction, License, Lease, Government
   Subcontract, Healthcare, Settlement, LLC Operating, Asset/Stock
   Purchase). This is the least certain of the three: a labeling aid, not
   an authoritative legal classification — a hybrid or unusually drafted
   agreement can score close between two categories or fall into
   "Unclassified." Confidence is reported so callers/UI can show
   uncertainty rather than assert a single label as fact.

All three are pure functions of already-normalized contract text (see
rules_engine.normalize_contract_text), independent of rules_engine.py
itself (rules_engine imports and calls this module, not the other way
around) — same dependency direction as risk_dashboard.py,
structure_checker.py, and clause_quality.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from party_resolver import resolve_party_roles

# --- Party extraction -----------------------------------------------------

# Short defined name in parentheses — e.g. ("Prevail"), (the "Company") —
# same quote-pattern convention party_resolver.py's _DEFINED_NAME_RE
# already uses. The full legal name is recovered separately (see
# extract_parties), rather than captured directly in one regex: a single
# greedy pattern spanning back to the full name has no natural stopping
# point short of another party's own short-name parenthetical or a
# preamble connector word, and will otherwise swallow unrelated preceding
# text (verified: an earlier version of this pattern captured "January 15,
# 2024 by and between Prevail InfoWorks,
# Inc." as the "full name" for short name "Prevail").
_SHORT_NAME_RE = re.compile(r'\(\s*(?:the\s+)?["“]([A-Z][A-Za-z0-9]{1,30})["”]\s*\)')

_PARTY_STOP_WORDS = {
    "party", "parties", "agreement", "effective", "date", "confidential", "contract",
    "exhibit", "schedule", "addendum", "amendment", "notice", "notices", "services",
    "work", "premises", "property",
}

# Preamble connector words that reliably introduce a PARTY-LISTING
# sentence — deliberately does NOT include bare "and", which is far too
# common a word (an ordinary list conjunction, or even part of a document
# title — verified: "MASTER SERVICE AND TECHNOLOGY AGREEMENT" made "and"
# match as if it were a party-introducing connector) to signal a party
# introduction on its own. Only used to find the FIRST party in a preamble;
# subsequent parties are found structurally (see _extract_parties_from_short_names).
_STRICT_PREAMBLE_CONNECTOR_RE = re.compile(
    r'\b(?:by\s+and\s+between|between|among)\b', re.IGNORECASE,
)

# A trailing entity-description clause ("a Delaware corporation", "a
# limited liability company") is a description of the party, not its name.
_ENTITY_DESCRIPTOR_RE = re.compile(
    r',?\s*a(?:n)?\s+[A-Za-z\s]+?(?:corporation|company|partnership|LLC|L\.L\.C\.|'
    r'limited liability company|limited partnership|trust)\s*$',
    re.IGNORECASE,
)

# A leading list conjunction/punctuation ("and ", ", ") on a gap-extracted
# name between two consecutive short-name parentheticals.
_LEADING_CONJUNCTION_RE = re.compile(r'^(?:,?\s*and\s+|,\s*)', re.IGNORECASE)

# Common entity-name suffixes. A single legitimate party name essentially
# never contains two of these — if it does, the gap-extraction window
# spanned across two DIFFERENT parties' names rather than isolating one.
_ENTITY_SUFFIX_RE = re.compile(
    r'\b(?:Inc\.?|Incorporated|Corp\.?|Corporation|LLC|L\.L\.C\.|Ltd\.?|Co\.|L\.P\.|LP)\b',
    re.IGNORECASE,
)


def _clean_name(raw: str) -> Optional[str]:
    name = _LEADING_CONJUNCTION_RE.sub('', raw)
    name = _ENTITY_DESCRIPTOR_RE.sub('', name)
    name = re.sub(r'\s+', ' ', name).strip().strip(',').strip()
    if not name or not name[0].isupper():
        return None
    # A date, or any other digit, means the window spilled past a real
    # boundary (e.g. landed on "...entered into as of June 4, 2002" rather
    # than an actual name) — not a usable name.
    if any(ch.isdigit() for ch in name):
        return None
    # Two-or-more entity suffixes in one "name" — verified against a real
    # fixture ("Genoptix, Inc. (\"Genoptix\" or the \"Laboratory\") and
    # Pacific Medical Consultants, Inc.") where an alternate short-name
    # naming the SAME party ("Genoptix" or "Laboratory") caused the gap
    # window to span across into the NEXT party's name entirely, producing
    # a merged, misleading string rather than either party's actual name.
    if len(_ENTITY_SUFFIX_RE.findall(name)) >= 2:
        return None
    return name


@dataclass(frozen=True)
class Party:
    full_name: str
    short_name: str
    role: str  # "vendor" | "customer" | "unknown" — see party_resolver.py


def extract_parties(text: str) -> List[Party]:
    """Full legal party names paired with defined short names and resolved
    role.

    Deliberately scans a MUCH shorter window (~1000 chars) than
    party_resolver.py's own 3000-char defined-name search: the genuine
    "THIS AGREEMENT is made ... by and between A (\"X\") and B (\"Y\")"
    party-introduction sentence is essentially always within the first
    handful of hundred characters. A wider window pulls in unrelated
    glossary-style definitions elsewhere in a long preamble that happen to
    sit near an ordinary list "and" — verified against a real construction-
    contract fixture where "...Change Directives, and Notices of
    Clarification (\"NOC\")" was misread as a second party purely because
    "and" (a plain list conjunction, not a party-introducing connector) fell
    inside a wider lookback window.
    """
    preamble = text[:1000]
    role_map = resolve_party_roles(text)

    matches = [
        m for m in _SHORT_NAME_RE.finditer(preamble)
        if m.group(1).lower() not in _PARTY_STOP_WORDS
    ]

    parties: List[Party] = []
    seen_short_names: Dict[str, None] = {}
    prev_end = 0
    for i, m in enumerate(matches):
        short_name = m.group(1)
        if short_name.lower() in seen_short_names:
            prev_end = m.end()
            continue

        if i == 0:
            # First party: require a genuine "between X (...)" / "among A, B
            # (...)" connector in the lookback — not just any preceding text
            # — so an unrelated definition earlier in the preamble isn't
            # mistaken for the first party.
            window_start = max(0, m.start() - 150)
            window = preamble[window_start:m.start()]
            connector_matches = list(_STRICT_PREAMBLE_CONNECTOR_RE.finditer(window))
            raw_name = window[connector_matches[-1].end():] if connector_matches else None
        else:
            # Subsequent parties: the name is structurally bounded by the
            # end of the PREVIOUS party's short-name parenthetical and the
            # start of this one ("... (\"Prevail\") and BriaCell Corp.
            # (\"Company\")") — far more precise than searching for another
            # connector word, and immune to an unrelated "and" elsewhere.
            raw_name = preamble[prev_end:m.start()]

        prev_end = m.end()
        full_name = _clean_name(raw_name) if raw_name is not None else None
        if not full_name:
            continue

        seen_short_names[short_name.lower()] = None
        parties.append(Party(full_name=full_name, short_name=short_name, role=role_map.role_of(short_name)))

    return parties


# --- Effective date extraction --------------------------------------------

_MONTH_DAY_YEAR_RE = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
_NUMERIC_DATE_RE = r'\d{1,2}/\d{1,2}/\d{2,4}'
_ISO_DATE_RE = r'\d{4}-\d{2}-\d{2}'
_ANY_DATE_RE = rf'({_MONTH_DAY_YEAR_RE}|{_NUMERIC_DATE_RE}|{_ISO_DATE_RE})'

# Ranked most-confident-first: an explicit "Effective Date" anchor beats a
# bare "dated as of", which beats a bare "made and entered into as of".
_EFFECTIVE_DATE_PATTERNS: Tuple[str, ...] = (
    rf'Effective\s+Date[^.\n]{{0,40}}?{_ANY_DATE_RE}',
    rf'effective\s+as\s+of\s+{_ANY_DATE_RE}',
    rf'dated\s+as\s+of\s+{_ANY_DATE_RE}',
    rf'dated\s+{_ANY_DATE_RE}',
    rf'made\s+and\s+entered\s+into\s+(?:as\s+of\s+)?{_ANY_DATE_RE}',
)


def extract_effective_date(text: str) -> Optional[str]:
    """Returns the matched date text verbatim (e.g. "January 5, 2024") or
    None if no confident match — never a best-guess or a parsed/normalized
    date that could silently misrepresent an ambiguous format (is
    "03/04/2024" March 4th or April 3rd? this function does not guess)."""
    preamble = text[:3000]
    for pattern in _EFFECTIVE_DATE_PATTERNS:
        m = re.search(pattern, preamble, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


# --- Contract type classification ------------------------------------------

# type label -> [(keyword/phrase pattern, weight), ...]. Weights are higher
# for phrases that are near-unambiguous signatures of that contract type
# (e.g. "franchise agreement" almost never appears in a non-franchise
# contract) and lower for words that are suggestive but common across types.
_CONTRACT_TYPE_SIGNATURES: Dict[str, List[Tuple[str, int]]] = {
    "Non-Disclosure / Confidentiality Agreement": [
        (r'\bnon-?disclosure\s+agreement\b', 5), (r'\bconfidentiality\s+agreement\b', 4),
        (r'\bmutual\s+non-?disclosure\b', 5), (r'\bdisclosing\s+party\b', 2), (r'\breceiving\s+party\b', 2),
    ],
    "Master Services Agreement": [
        (r'\bmaster\s+servi(?:ce|ces)\s+agreement\b', 5), (r'\bstatement\s+of\s+work\b', 2),
        (r'\border\s+form\b', 1),
    ],
    "SaaS / Subscription Agreement": [
        (r'\bsoftware\s+as\s+a\s+service\b', 5), (r'\bsaas\b', 4), (r'\bsubscription\s+agreement\b', 4),
        (r'\bhosted\s+service\b', 2), (r'\buptime\b', 1),
    ],
    "Employment Agreement": [
        (r'\bemployment\s+agreement\b', 5), (r'\bat-will\s+employment\b', 4), (r'\bseverance\b', 2),
        (r'\bjob\s+title\b', 2),
    ],
    "Franchise Agreement": [
        (r'\bfranchise\s+agreement\b', 5), (r'\bfranchisor\b', 4), (r'\bfranchisee\b', 4),
        (r'\broyalty\s+fee\b', 2),
    ],
    "Credit / Loan Agreement": [
        (r'\bcredit\s+agreement\b', 5), (r'\bloan\s+agreement\b', 5), (r'\bpromissory\s+note\b', 4),
        (r'\bborrower\b', 2), (r'\blender\b', 2), (r'\bguaranty\s+agreement\b', 3),
    ],
    "Real Estate Purchase & Sale Agreement": [
        (r'\bpurchase\s+and\s+sale\s+agreement\b', 5), (r'\breal\s+property\b', 2),
        (r'\bclosing\s+date\b', 2), (r'\btitle\s+company\b', 3), (r'\bescrow\s+agent\b', 2),
    ],
    "Insurance / MGA Agreement": [
        (r'\bmanaging\s+general\s+agent\b', 5), (r'\breinsurance\b', 4), (r'\bunderwriting\b', 3),
        (r'\bceding\s+company\b', 4), (r'\bloss\s+portfolio\s+transfer\b', 5),
    ],
    "Construction Contract": [
        (r'\bgeneral\s+contractor\b', 4), (r'\bconstruction\s+contract\b', 5), (r'\bAIA\s+document\b', 4),
        (r'\bgeneral\s+conditions\b', 2), (r'\bchange\s+order\b', 2),
    ],
    "License Agreement": [
        (r'\blicense\s+agreement\b', 5), (r'\blicensor\b', 3), (r'\blicensee\b', 3),
        (r'\broyalt(?:y|ies)\b', 1),
    ],
    "Lease Agreement": [
        (r'\blease\s+agreement\b', 5), (r'\blandlord\b', 3), (r'\btenant\b', 3), (r'\bpremises\b', 2),
    ],
    "Government Contract / Subcontract": [
        (r'\bprime\s+contract\b', 4), (r'\bsubcontract\b', 3), (r'\bfar\s+52\.', 5),
        (r'\bDCAA\b', 4), (r'\bsmall\s+business\s+subcontracting\s+plan\b', 5),
    ],
    "Healthcare Provider Agreement": [
        (r'\bhealthcare\s+provider\s+agreement\b', 5), (r'\bcredentialing\b', 4), (r'\bHIPAA\b', 2),
        (r'\bpatient\b', 1),
    ],
    "Settlement Agreement": [
        (r'\bsettlement\s+agreement\b', 5), (r'\brelease\s+of\s+claims\b', 3), (r'\bclass\s+action\b', 2),
    ],
    "LLC Operating Agreement": [
        (r'\boperating\s+agreement\b', 5), (r'\blimited\s+liability\s+company\b', 3), (r'\bmembers\b', 1),
    ],
    "Asset / Stock Purchase Agreement": [
        (r'\basset\s+purchase\s+agreement\b', 5), (r'\bstock\s+purchase\s+agreement\b', 5),
        (r'\bpurchase\s+price\b', 1),
    ],
}


@dataclass(frozen=True)
class ContractTypeResult:
    contract_type: Optional[str]  # None if no type scored above the confidence floor
    confidence: str  # "high" | "medium" | "low"
    scores: Dict[str, int]  # every type's raw score, for transparency

    def as_dict(self) -> Dict[str, Any]:
        return {"contract_type": self.contract_type, "confidence": self.confidence, "scores": self.scores}


_MIN_SCORE_TO_CLASSIFY = 3


def classify_contract_type(text: str) -> ContractTypeResult:
    """Keyword-weighted classification — a labeling aid, not an
    authoritative legal determination. A hybrid or unusually drafted
    agreement can score close between two categories or fall below the
    confidence floor into "Unclassified" (contract_type=None)."""
    # Title/opening carries a stronger signal than a stray keyword deep in
    # boilerplate — weight matches in the first 1500 chars double.
    head = text[:1500]
    scores: Dict[str, int] = {}
    for label, signatures in _CONTRACT_TYPE_SIGNATURES.items():
        score = 0
        for pattern, weight in signatures:
            score += weight * len(re.findall(pattern, text, re.IGNORECASE))
            score += weight * len(re.findall(pattern, head, re.IGNORECASE))  # head counted twice total
        scores[label] = score

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_label, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if top_score < _MIN_SCORE_TO_CLASSIFY:
        return ContractTypeResult(contract_type=None, confidence="low", scores=scores)

    if second_score > 0 and top_score < second_score * 2:
        confidence = "medium"  # close race with the runner-up
    else:
        confidence = "high"

    return ContractTypeResult(contract_type=top_label, confidence=confidence, scores=scores)


# --- Combined extraction ----------------------------------------------------

@dataclass(frozen=True)
class ContractMetadata:
    parties: List[Party]
    effective_date: Optional[str]
    contract_type_result: ContractTypeResult

    def as_dict(self) -> Dict[str, Any]:
        return {
            "parties": [
                {"full_name": p.full_name, "short_name": p.short_name, "role": p.role} for p in self.parties
            ],
            "effective_date": self.effective_date,
            "contract_type": self.contract_type_result.contract_type,
            "contract_type_confidence": self.contract_type_result.confidence,
        }


def extract_metadata(text: str) -> ContractMetadata:
    """Pure function: normalized contract text -> ContractMetadata."""
    return ContractMetadata(
        parties=extract_parties(text),
        effective_date=extract_effective_date(text),
        contract_type_result=classify_contract_type(text),
    )
