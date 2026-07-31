"""
Deterministic Clause Quality Engine — Arbitration module.

Product roadmap Feature 4 (the anchor feature; see the product memo, Rev.
2): generalizes "does an arbitration clause exist" — the only thing
rules_engine.py's M_ARBITRATION_01 currently checks — into "how complete is
it." This is the same element-by-element checklist an arbitrator or
international-disputes lawyer runs by habit on a first read: administering
institution, seat, governing rules, number of arbitrators, language, and
emergency/interim relief, plus a same-document conflict check against a
competing exclusive-litigation-jurisdiction clause.

Scope, stated honestly:

- This module only ever activates when an arbitration clause is actually
  present in the document. A contract that chooses litigation over
  arbitration is not scored or penalized here — that is a legitimate
  drafting choice, not a deficiency. Same "topic must be in scope before
  absence is a finding" principle rules_engine.py's REQUIRED_SECTION rules
  already use.
- Each element is detected via pattern matching for standard drafting
  language (named institutions, "seat of arbitration", "language of the
  arbitration," etc.) — not a legal-sufficiency judgment. Unconventional
  phrasing can be missed; a low score is a prompt to read the clause, not a
  certified defect.
- This is the FIRST module of what the roadmap describes as a Clause
  Quality Engine intended to eventually generalize the same weighted-
  checklist pattern to other clause types (Liability, Indemnification,
  Confidentiality, IP, Termination, ...). Those modules are not built yet —
  see the roadmap for sequencing. Do not read the presence of only an
  arbitration module here as those other modules existing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Same detection as rules_engine.py's M_ARBITRATION_01 rule (kept
# independent, not imported, so this module has no dependency on
# rules_engine — same pattern as risk_dashboard.py / structure_checker.py).
_ARBITRATION_PRESENT_RE = re.compile(
    r'\b(mandatory\s+arbitration|binding\s+arbitration|shall\s+be\s+(?:settled|resolved)\s+by\s+arbitration|'
    r'submit(?:ted)?\s+to\s+arbitration|arbitration\s+proceedings?)\b', re.IGNORECASE,
)

_INSTITUTION_RE = re.compile(
    r'\b(American Arbitration Association|AAA|JAMS|International Chamber of Commerce|ICC|'
    r'London Court of International Arbitration|LCIA|Singapore International Arbitration Centre|SIAC|'
    r'Hong Kong International Arbitration Centre|HKIAC|International Centre for Dispute Resolution|ICDR|'
    r'International Institute for Conflict Prevention(?:\s+and\s+Resolution)?|CPR Institute|'
    r'Stockholm Chamber of Commerce|SCC)\b',
)

_SEAT_RE = re.compile(
    r'\b(?:seat|situs|place)\s+of\s+(?:the\s+)?arbitration\b|'
    r'\barbitration\s+shall\s+(?:take\s+place|be\s+(?:held|conducted))\s+in\b',
    re.IGNORECASE,
)

_RULES_RE = re.compile(
    r'\bCommercial Arbitration Rules\b|\bRules of Arbitration\b|\bArbitration Rules\b|'
    r'\bUNCITRAL(?:\s+Arbitration)?\s+Rules\b|\bInternational Arbitration Rules\b',
    re.IGNORECASE,
)

_ARBITRATOR_COUNT_RE = re.compile(
    r'\b(?:one|1|single|sole)\s+arbitrator\b|\b(?:three|3)\s+arbitrators\b|'
    r'\bpanel\s+of\s+(?:three|3)\s+arbitrators\b',
    re.IGNORECASE,
)

_LANGUAGE_RE = re.compile(
    r'\blanguage\s+of\s+(?:the\s+)?arbitration\b|'
    r'\barbitration(?:\s+proceedings?)?\s+(?:shall\s+be\s+)?conducted\s+in\s+the\s+\w+\s+language\b',
    re.IGNORECASE,
)

_EMERGENCY_RELIEF_RE = re.compile(
    r'\bemergency\s+arbitrator\b|\bemergency\s+relief\b|\binterim\s+(?:relief|measures?)\b|'
    r'\bprovisional\s+measures?\b',
    re.IGNORECASE,
)

_EXCLUSIVE_LITIGATION_RE = re.compile(
    r'\bexclusive\s+jurisdiction\s+of\s+the\s+courts?\b|'
    r'\bsubmits?\s+to\s+the\s+(?:exclusive\s+)?jurisdiction\s+of\s+(?:the\s+)?courts?\b',
    re.IGNORECASE,
)

_ELEMENT_WEIGHT: Dict[str, int] = {
    "institution": 20,
    "seat": 20,
    "rules": 20,
    "arbitrator_count": 15,
    "language": 10,
    "emergency_relief": 10,
    "no_litigation_conflict": 5,
}


@dataclass(frozen=True)
class ClauseElement:
    key: str
    label: str
    present: bool
    weight: int
    detail: str


@dataclass(frozen=True)
class ArbitrationQualityReport:
    applicable: bool  # False if no arbitration clause was found at all
    score: Optional[int]  # 0-100, None if not applicable (not "0/bad")
    elements: List[ClauseElement]
    conflict_with_litigation_clause: bool
    methodology_note: str = (
        "Only scored when an arbitration clause is present in this document — a contract that "
        "chooses litigation over arbitration is not penalized here, that is a legitimate drafting "
        "choice. Each element is detected via pattern matching for standard drafting language "
        "(named institutions, \"seat of arbitration\", \"language of the arbitration\", etc.), not a "
        "legal-sufficiency judgment; unconventional phrasing can be missed. Treat a low score as a "
        "prompt to read the clause, not a certified defect."
    )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "applicable": self.applicable,
            "score": self.score,
            "elements": [
                {"key": e.key, "label": e.label, "present": e.present, "weight": e.weight, "detail": e.detail}
                for e in self.elements
            ],
            "conflict_with_litigation_clause": self.conflict_with_litigation_clause,
            "methodology_note": self.methodology_note,
        }


def analyze_arbitration_clause(text: str) -> ArbitrationQualityReport:
    """Pure function: normalized contract text -> ArbitrationQualityReport.

    Callers should pass already-normalized text (see
    rules_engine.normalize_contract_text), same convention as
    structure_checker.analyze_structure.
    """
    if not _ARBITRATION_PRESENT_RE.search(text):
        return ArbitrationQualityReport(
            applicable=False, score=None, elements=[], conflict_with_litigation_clause=False,
        )

    has_conflict = bool(_EXCLUSIVE_LITIGATION_RE.search(text))

    checks = [
        ("institution", "Administering institution named", _INSTITUTION_RE,
         "No recognized arbitral institution (e.g. AAA, ICC, JAMS, LCIA, SIAC) is named.",
         "An arbitral institution is named."),
        ("seat", "Seat/place of arbitration specified", _SEAT_RE,
         "The legal seat (place) of arbitration is not specified — this determines which national "
         "arbitration law and courts have supervisory jurisdiction over the proceedings.",
         "A seat/place of arbitration is specified."),
        ("rules", "Governing arbitration rules specified", _RULES_RE,
         "No specific arbitration rules (e.g. AAA Commercial Arbitration Rules, ICC Rules, UNCITRAL "
         "Rules) are referenced.",
         "Specific arbitration rules are referenced."),
        ("arbitrator_count", "Number of arbitrators specified", _ARBITRATOR_COUNT_RE,
         "The number of arbitrators (e.g. one, or a panel of three) is not specified.",
         "The number of arbitrators is specified."),
        ("language", "Language of arbitration specified", _LANGUAGE_RE,
         "The language in which arbitration proceedings will be conducted is not specified.",
         "The language of the arbitration is specified."),
        ("emergency_relief", "Emergency/interim relief addressed", _EMERGENCY_RELIEF_RE,
         "No provision addresses emergency arbitrator procedures or interim/provisional relief "
         "pending constitution of the tribunal.",
         "Emergency or interim relief is addressed."),
    ]

    elements: List[ClauseElement] = []
    for key, label, pattern, missing_detail, present_detail in checks:
        present = bool(pattern.search(text))
        elements.append(ClauseElement(
            key=key, label=label, present=present, weight=_ELEMENT_WEIGHT[key],
            detail=present_detail if present else missing_detail,
        ))

    elements.append(ClauseElement(
        key="no_litigation_conflict", label="No conflicting exclusive-litigation clause",
        weight=_ELEMENT_WEIGHT["no_litigation_conflict"], present=not has_conflict,
        detail=(
            "This document also contains an exclusive court-jurisdiction clause elsewhere, which "
            "conflicts with the arbitration clause and creates real ambiguity about which forum governs."
            if has_conflict else "No conflicting exclusive-litigation clause was found."
        ),
    ))

    score = sum(e.weight for e in elements if e.present)
    return ArbitrationQualityReport(
        applicable=True, score=score, elements=elements, conflict_with_litigation_clause=has_conflict,
    )
