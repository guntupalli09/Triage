"""
Deterministic Clause Quality Engine — Arbitration and Liability modules.

Product roadmap Feature 4 (the anchor feature; see the product memo, Rev.
2): generalizes "does an arbitration/liability clause exist" — the only
thing rules_engine.py's M_ARBITRATION_01/H_LOL_01 etc. currently check —
into "how complete is it." This is the same element-by-element checklist a
lawyer runs by habit on a first read. For arbitration: administering
institution, seat, governing rules, number of arbitrators, language, and
emergency/interim relief, plus a same-document conflict check against a
competing exclusive-litigation-jurisdiction clause. For liability: whether
a cap exists at all, whether it applies mutually, whether consequential
damages are excluded, whether standard high-severity carve-outs (IP,
confidentiality, indemnification) and a fraud/willful-misconduct exception
are present, and whether adverse "shall not be limited" language undermines
the cap the document otherwise states.

Scope, stated honestly:

- Each module only ever activates when that clause type is actually present
  in the document. A contract that chooses litigation over arbitration, or
  simply has no limitation-of-liability clause, is not scored or penalized
  — that is either a legitimate drafting choice or a separate, already-
  covered finding (rules_engine.py's H_LOL_01 flags an absent/weak cap on
  its own). Same "topic must be in scope before absence is a finding"
  principle rules_engine.py's REQUIRED_SECTION rules already use.
- Each element is detected via pattern matching for standard drafting
  language — not a legal-sufficiency judgment. Unconventional phrasing can
  be missed; a low score is a prompt to read the clause, not a certified
  defect.
- These are the first two modules of what the roadmap describes as a Clause
  Quality Engine intended to eventually generalize the same weighted-
  checklist pattern to other clause types (Indemnification, Confidentiality,
  IP, Termination, ...). Those modules are not built yet — see the roadmap
  for sequencing. Do not read the presence of these two modules as those
  other clause types being covered.
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


# ---------------------------------------------------------------------------
# Liability module
# ---------------------------------------------------------------------------

# Applicability gate: a limitation-of-liability topic is present at all —
# same detection concept as rules_engine.py's H_LOL_01 anchors.
_LIABILITY_TOPIC_RE = re.compile(
    r'\blimitation\s+of\s+liability\b|\bliability\s+cap\b|\baggregate\s+liability\b|'
    r'\bmaximum\s+liability\b', re.IGNORECASE,
)

_CAP_PRESENT_RE = re.compile(
    r'\bshall\s+not\s+exceed\b|\blimited\s+to\b.{0,60}?\b(?:fees|amounts?|damages?)\b|'
    r'\bin\s+no\s+event\s+shall\b.{0,80}?\bexceed\b',
    re.IGNORECASE | re.DOTALL,
)

_MUTUAL_APPLICATION_RE = re.compile(
    r"\beither\s+party'?s?\s+(?:aggregate\s+)?liability\b|\bboth\s+parties'?\s+liability\b|"
    r"\beach\s+party'?s\s+(?:aggregate\s+)?liability\b|\bneither\s+party\s+shall\s+be\s+liable\b",
    re.IGNORECASE,
)

_CONSEQUENTIAL_EXCLUDED_RE = re.compile(
    r'\b(?:consequential|indirect|special|incidental|punitive)\s+damages?\b.{0,100}?'
    r'\b(?:waive[sd]?|exclude[sd]?|shall\s+not\s+be\s+liable|no\s+liability|not\s+be\s+responsible)\b|'
    r'\b(?:waive[sd]?|exclude[sd]?|neither\s+party\s+shall\s+be\s+liable|'
    r'in\s+no\s+event\s+shall\b.{0,40}?\bbe\s+liable)\b.{0,100}?'
    r'\b(?:consequential|indirect|special|incidental|punitive)\s+damages?\b',
    re.IGNORECASE | re.DOTALL,
)

_HIGH_SEVERITY_CARVEOUTS_RE = re.compile(
    r'\bexcept(?:ion)?s?\s+(?:for|to)\b.{0,120}?\b(?:indemnif\w+|confidential\w*|intellectual\s+property|IP)\b|'
    r'\bshall\s+not\s+apply\s+to\b.{0,120}?\b(?:indemnif\w+|confidential\w*|intellectual\s+property)\b|'
    r'\bexcluding\b.{0,120}?\b(?:indemnif\w+|confidential\w*|intellectual\s+property)\b',
    re.IGNORECASE | re.DOTALL,
)

_FRAUD_EXCEPTION_RE = re.compile(
    r'\b(?:except|excluding|other\s+than)\b.{0,250}?\b(?:fraud|willful\s+misconduct|gross\s+negligence)\b|'
    r'\b(?:fraud|willful\s+misconduct|gross\s+negligence)\b.{0,80}?\b(?:not\s+(?:subject\s+to|limited)|excluded\s+from)\b.{0,40}?\blimitation\b',
    re.IGNORECASE | re.DOTALL,
)

# Adverse language that undermines/negates a cap the document otherwise
# states — same concept as rules_engine.py's H_LOL_01 nearby patterns.
_CAP_NEGATING_LANGUAGE_RE = re.compile(
    r'\bshall\s+not\s+be\s+limited\b|\bwithout\s+limit(?:ation)?\b|\bnot\s+be\s+limited\b',
    re.IGNORECASE,
)

_LIABILITY_ELEMENT_WEIGHT: Dict[str, int] = {
    "cap_present": 25,
    "mutual_application": 20,
    "consequential_damages_excluded": 20,
    "high_severity_carveouts": 15,
    "fraud_exception": 10,
    "no_cap_negating_language": 10,
}


@dataclass(frozen=True)
class LiabilityQualityReport:
    applicable: bool
    score: Optional[int]
    elements: List[ClauseElement]
    methodology_note: str = (
        "Only scored when a limitation-of-liability clause is present in this document. Each "
        "element is detected via pattern matching for standard drafting language, not a legal-"
        "sufficiency judgment; unconventional phrasing can be missed. Note: unlike the arbitration "
        "module, a low score here does not always mean \"add more language\" — for example, the "
        "absence of a cap at all is a separate, more direct finding already covered by rule "
        "H_LOL_01, and \"high_severity_carveouts\"/\"fraud_exception\" being present is the FAVORABLE "
        "state (it means catastrophic claims aren't artificially capped), not a defect to add "
        "elsewhere. Treat a low score as a prompt to read the clause, not a certified defect."
    )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "applicable": self.applicable,
            "score": self.score,
            "elements": [
                {"key": e.key, "label": e.label, "present": e.present, "weight": e.weight, "detail": e.detail}
                for e in self.elements
            ],
            "methodology_note": self.methodology_note,
        }


def analyze_liability_clause(text: str) -> LiabilityQualityReport:
    """Pure function: normalized contract text -> LiabilityQualityReport.

    Callers should pass already-normalized text, same convention as
    analyze_arbitration_clause / structure_checker.analyze_structure.
    """
    if not _LIABILITY_TOPIC_RE.search(text):
        return LiabilityQualityReport(applicable=False, score=None, elements=[])

    checks = [
        ("cap_present", "A liability cap is stated", _CAP_PRESENT_RE,
         "No specific cap amount, formula, or ceiling language (e.g. \"shall not exceed\") was found — "
         "a limitation-of-liability heading exists, but the actual limiting language may be missing or "
         "phrased unconventionally.",
         "A liability cap or ceiling is stated."),
        ("mutual_application", "Cap applies mutually to both parties", _MUTUAL_APPLICATION_RE,
         "No explicit mutual-application language (\"either party's liability\", \"neither party shall "
         "be liable\") was found — the cap may apply to only one party.",
         "The cap explicitly applies to both parties."),
        ("consequential_damages_excluded", "Consequential/indirect damages excluded",
         _CONSEQUENTIAL_EXCLUDED_RE,
         "No waiver or exclusion of consequential, indirect, special, incidental, or punitive damages "
         "was found.",
         "Consequential/indirect/special damages are excluded."),
        ("high_severity_carveouts", "Carve-outs for IP/confidentiality/indemnification claims",
         _HIGH_SEVERITY_CARVEOUTS_RE,
         "No carve-out excludes IP infringement, confidentiality breach, or indemnification "
         "obligations from the cap — if present, this cap may apply even to the most severe claim "
         "categories, which is a favorable state for a drafter benefiting from the cap but a risk to "
         "the party accepting it.",
         "The cap carves out IP, confidentiality, or indemnification claims."),
        ("fraud_exception", "Fraud/willful misconduct exception", _FRAUD_EXCEPTION_RE,
         "No exception for fraud, willful misconduct, or gross negligence was found — absent this, "
         "the cap may shield even bad-faith conduct.",
         "Fraud or willful misconduct is excepted from the cap."),
    ]

    elements: List[ClauseElement] = []
    for key, label, pattern, missing_detail, present_detail in checks:
        present = bool(pattern.search(text))
        elements.append(ClauseElement(
            key=key, label=label, present=present, weight=_LIABILITY_ELEMENT_WEIGHT[key],
            detail=present_detail if present else missing_detail,
        ))

    has_negating_language = bool(_CAP_NEGATING_LANGUAGE_RE.search(text))
    elements.append(ClauseElement(
        key="no_cap_negating_language", label="No language undermining the stated cap",
        weight=_LIABILITY_ELEMENT_WEIGHT["no_cap_negating_language"], present=not has_negating_language,
        detail=(
            "Adverse language elsewhere (\"shall not be limited\", \"without limit\") appears to "
            "undermine or negate the cap this document otherwise states."
            if has_negating_language else "No language undermining the stated cap was found."
        ),
    ))

    score = sum(e.weight for e in elements if e.present)
    return LiabilityQualityReport(applicable=True, score=score, elements=elements)


# ---------------------------------------------------------------------------
# Confidentiality module
# ---------------------------------------------------------------------------

_CONFIDENTIALITY_TOPIC_RE = re.compile(
    r'\bconfidential(?:ity)?\b|\bnon[-\s]?disclosure\b', re.IGNORECASE,
)

_CONF_DEFINITION_PRESENT_RE = re.compile(
    r'\bconfidential\s+information\b.{0,60}?\b(?:means|shall\s+mean|defined\s+as|refers?\s+to)\b|'
    r'\b(?:means|shall\s+mean)\b.{0,60}?\bconfidential\s+information\b',
    re.IGNORECASE | re.DOTALL,
)

# The four standard confidentiality exceptions. Checked individually so the
# "present" element can require a majority, not just any one — a
# confidentiality clause missing 3 of 4 standard exceptions is a materially
# different (and worse) document than one missing 1 of 4.
_EXCEPTION_PUBLIC_RE = re.compile(
    r'\bpublicly\s+available\b|\bpublic\s+domain\b|\balready\s+(?:known\s+to\s+the\s+)?public\b|'
    r'\bknown\s+to\s+the\s+public\b|\bpublic\s+through\s+no\s+fault\b',
    re.IGNORECASE,
)
_EXCEPTION_ALREADY_KNOWN_RE = re.compile(
    r'\balready\s+(?:in\s+(?:its|the\s+recipient\'?s)\s+possession|known\s+to)\b|'
    r'\brightfully\s+(?:possess|known)\b|\bprior\s+to\s+disclosure\b|'
    r'\bpossession\s+of\s+the\s+receiving\s+party\s+prior\s+to\b',
    re.IGNORECASE,
)
_EXCEPTION_INDEPENDENT_DEV_RE = re.compile(
    r'\bindependently\s+develop(?:ed)?\b', re.IGNORECASE,
)
# Verified against a real fixture ("has been properly obtained without
# restriction from a third party who is not bound by an obligation of
# confidentiality") where none of the original three phrasings matched —
# real drafting varies the verb ("received"/"obtained"/"disclosed") and the
# no-breach language ("without breach"/"who is not bound by an obligation")
# far more than the original narrow alternation covered.
_EXCEPTION_THIRD_PARTY_RE = re.compile(
    r'\b(?:received|obtained|disclosed|acquired)\b.{0,40}?\bfrom\s+a\s+third\s+part(?:y|ies)\b|'
    r'\bthird\s+part(?:y|ies)\b.{0,60}?\bwithout\s+(?:breach|violat\w+)\b|'
    r'\bwithout\s+(?:breach|violation)\s+of\s+(?:any\s+)?obligation\b|'
    r'\bthird\s+part(?:y|ies)\b.{0,40}?\bnot\s+bound\s+by\s+(?:an\s+)?obligation\b',
    re.IGNORECASE | re.DOTALL,
)

_DURATION_SPECIFIED_RE = re.compile(
    r'\bfor\s+a\s+period\s+of\s+\d+\s+years?\b|\bsurvive\b.{0,40}?\b\d+\s+years?\b|'
    r'\b\d+\s+years?\s+(?:from|after|following)\b.{0,40}?\btermination\b|'
    r'\bperiod\s+of\s+\d+\s*\(\d+\)?\s*years?\b',
    re.IGNORECASE | re.DOTALL,
)

_RETURN_DESTRUCTION_RE = re.compile(
    r'\breturn\s+or\s+destroy\b|\bdestroy\s+or\s+return\b|\bshall\s+return\b.{0,60}?\bconfidential\b|'
    r'\bdestroy\b.{0,60}?\bconfidential\b|\bcertificate\s+of\s+destruction\b',
    re.IGNORECASE | re.DOTALL,
)

_GOV_DISCLOSURE_CARVEOUT_RE = re.compile(
    r'\brequired\s+by\s+(?:law|court\s+order|subpoena)\b|\bcompelled\s+by\s+(?:law|legal\s+process)\b|'
    r'\bgovernmental\s+(?:authority|order)\b.{0,80}?\bdisclos\w+\b',
    re.IGNORECASE | re.DOTALL,
)

_RESIDUAL_KNOWLEDGE_RE = re.compile(
    r'\bresidual(?:s)?\b.{0,60}?\b(?:knowledge|information)\b|\bunaided\s+memory\b|\bmental\s+impressions\b',
    re.IGNORECASE | re.DOTALL,
)

_CONFIDENTIALITY_ELEMENT_WEIGHT: Dict[str, int] = {
    "definition_present": 20,
    "standard_exceptions": 25,
    "duration_specified": 15,
    "return_or_destruction": 20,
    "government_disclosure_carveout": 10,
    "residual_knowledge": 10,
}


@dataclass(frozen=True)
class ConfidentialityQualityReport:
    applicable: bool
    score: Optional[int]
    elements: List[ClauseElement]
    methodology_note: str = (
        "Only scored when a confidentiality/non-disclosure clause is present in this document. "
        "\"standard_exceptions\" requires at least 3 of the 4 conventional exceptions (public domain, "
        "already known, independently developed, received from a third party) to count as present — "
        "a clause missing most of them is materially weaker than one missing just one. Each element "
        "is detected via pattern matching for standard drafting language, not a legal-sufficiency "
        "judgment; unconventional phrasing can be missed. \"residual_knowledge\" (carve-out for "
        "information retained in unaided memory) is a real but less universal drafting choice — its "
        "absence is a lower-weight signal than the others. Treat a low score as a prompt to read the "
        "clause, not a certified defect."
    )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "applicable": self.applicable,
            "score": self.score,
            "elements": [
                {"key": e.key, "label": e.label, "present": e.present, "weight": e.weight, "detail": e.detail}
                for e in self.elements
            ],
            "methodology_note": self.methodology_note,
        }


def analyze_confidentiality_clause(text: str) -> ConfidentialityQualityReport:
    """Pure function: normalized contract text -> ConfidentialityQualityReport."""
    if not _CONFIDENTIALITY_TOPIC_RE.search(text):
        return ConfidentialityQualityReport(applicable=False, score=None, elements=[])

    exception_hits = sum(bool(p.search(text)) for p in (
        _EXCEPTION_PUBLIC_RE, _EXCEPTION_ALREADY_KNOWN_RE, _EXCEPTION_INDEPENDENT_DEV_RE, _EXCEPTION_THIRD_PARTY_RE,
    ))
    exceptions_present = exception_hits >= 3

    checks = [
        ("definition_present", "\"Confidential Information\" is defined", _CONF_DEFINITION_PRESENT_RE,
         "No definitional clause for \"Confidential Information\" was found.",
         "\"Confidential Information\" is defined."),
        ("duration_specified", "Duration of the obligation is specified", _DURATION_SPECIFIED_RE,
         "No specific duration (e.g. \"for a period of N years\") was found for the confidentiality "
         "obligation — it may be perpetual/indefinite, or simply unstated.",
         "A specific duration is stated for the confidentiality obligation."),
        ("return_or_destruction", "Return/destruction obligation on termination", _RETURN_DESTRUCTION_RE,
         "No obligation to return or destroy confidential information (e.g. on termination or request) "
         "was found.",
         "An obligation to return or destroy confidential information is stated."),
        ("government_disclosure_carveout", "Permitted disclosure if legally compelled",
         _GOV_DISCLOSURE_CARVEOUT_RE,
         "No carve-out permitting disclosure when required by law, court order, or subpoena was found.",
         "Disclosure required by law/court order/subpoena is addressed."),
        ("residual_knowledge", "Residual knowledge carve-out", _RESIDUAL_KNOWLEDGE_RE,
         "No carve-out for information retained in unaided memory (\"residual knowledge\") was found — "
         "a real but less universal drafting choice, lower-weight than the other elements.",
         "A residual-knowledge carve-out is present."),
    ]

    elements: List[ClauseElement] = [
        ClauseElement(
            key="standard_exceptions", label="Standard exceptions present (public/known/independent/third-party)",
            weight=_CONFIDENTIALITY_ELEMENT_WEIGHT["standard_exceptions"], present=exceptions_present,
            detail=(
                f"{exception_hits} of the 4 standard exceptions were found "
                f"({'meets' if exceptions_present else 'below'} the 3-of-4 threshold)."
            ),
        ),
    ]
    for key, label, pattern, missing_detail, present_detail in checks:
        present = bool(pattern.search(text))
        elements.append(ClauseElement(
            key=key, label=label, present=present, weight=_CONFIDENTIALITY_ELEMENT_WEIGHT[key],
            detail=present_detail if present else missing_detail,
        ))

    score = sum(e.weight for e in elements if e.present)
    return ConfidentialityQualityReport(applicable=True, score=score, elements=elements)


# ---------------------------------------------------------------------------
# Indemnification module
# ---------------------------------------------------------------------------

_INDEMNIFICATION_TOPIC_RE = re.compile(r'\bindemnif\w+\b', re.IGNORECASE)

_INDEM_MUTUAL_RE = re.compile(
    r'\b(?:either|both|each)\s+part(?:y|ies)\s+(?:shall|will|agrees?\s+to)\s+'
    r'(?:defend,?\s+)?indemnif\w+\b|'
    r'\bmutual(?:ly)?\s+indemnif\w+\b',
    re.IGNORECASE,
)

_INDEM_IP_RE = re.compile(
    r'\bindemnif\w+\b.{0,150}?\b(?:infring\w+|intellectual\s+property)\b|'
    r'\b(?:infring\w+|intellectual\s+property)\b.{0,150}?\bindemnif\w+\b',
    re.IGNORECASE | re.DOTALL,
)

_INDEM_THIRD_PARTY_SCOPE_RE = re.compile(
    r'\bthird[-\s]?part(?:y|ies)\s+claims?\b|\bclaims?\b.{0,40}?\b(?:brought|made|asserted)\s+by\s+a?\s*'
    r'third\s+part(?:y|ies)\b',
    re.IGNORECASE | re.DOTALL,
)

_INDEM_DEFENSE_OBLIGATION_RE = re.compile(
    r'\bshall\s+defend\b|\bdefend,?\s+indemnify\b|\bindemnify,?\s+defend\b|\bduty\s+to\s+defend\b',
    re.IGNORECASE,
)

_INDEM_NOTIFICATION_RE = re.compile(
    r'\bprompt(?:ly)?\s+(?:written\s+)?notif\w+\b|\bwritten\s+notice\s+of\s+(?:any\s+)?(?:such\s+)?claims?\b|'
    r'\bnotify\b.{0,60}?\bclaims?\b',
    re.IGNORECASE | re.DOTALL,
)

_INDEM_LIMITATIONS_PROCEDURE_RE = re.compile(
    r'\bsole\s+control\s+of\s+(?:the\s+)?defense\b|\bcontrol\s+(?:of\s+)?the\s+defense\b|'
    r'\breasonable\s+cooperation\b|\bsettle\b.{0,60}?\bwithout\s+(?:the\s+)?(?:prior\s+)?(?:written\s+)?consent\b',
    re.IGNORECASE | re.DOTALL,
)

_INDEMNIFICATION_ELEMENT_WEIGHT: Dict[str, int] = {
    "mutual_or_reciprocal": 20,
    "ip_indemnity": 20,
    "third_party_claims_scope": 15,
    "defense_obligation": 15,
    "notification_requirement": 15,
    "limitations_or_procedure": 15,
}


@dataclass(frozen=True)
class IndemnificationQualityReport:
    applicable: bool
    score: Optional[int]
    elements: List[ClauseElement]
    methodology_note: str = (
        "Only scored when an indemnification clause is present in this document. Each element is "
        "detected via pattern matching for standard drafting language, not a legal-sufficiency "
        "judgment; unconventional phrasing can be missed. \"mutual_or_reciprocal\" being absent does "
        "not by itself mean the clause is defective — a one-way indemnity can be an intentional, "
        "market-standard allocation depending on the parties' relative risk (e.g. a vendor "
        "indemnifying a customer for IP infringement); it is a signal worth checking, not an "
        "automatic defect. Treat a low score as a prompt to read the clause, not a certified defect."
    )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "applicable": self.applicable,
            "score": self.score,
            "elements": [
                {"key": e.key, "label": e.label, "present": e.present, "weight": e.weight, "detail": e.detail}
                for e in self.elements
            ],
            "methodology_note": self.methodology_note,
        }


def analyze_indemnification_clause(text: str) -> IndemnificationQualityReport:
    """Pure function: normalized contract text -> IndemnificationQualityReport."""
    if not _INDEMNIFICATION_TOPIC_RE.search(text):
        return IndemnificationQualityReport(applicable=False, score=None, elements=[])

    checks = [
        ("mutual_or_reciprocal", "Indemnification obligations are mutual", _INDEM_MUTUAL_RE,
         "No mutual/reciprocal indemnification language (\"either party shall indemnify\") was found — "
         "the obligation may run in only one direction.",
         "Indemnification obligations are stated as mutual/reciprocal."),
        ("ip_indemnity", "IP infringement indemnity addressed", _INDEM_IP_RE,
         "No indemnification specifically for intellectual property infringement claims was found.",
         "Indemnification for IP infringement claims is addressed."),
        ("third_party_claims_scope", "Scope explicitly covers third-party claims", _INDEM_THIRD_PARTY_SCOPE_RE,
         "No explicit reference to third-party claims was found — indemnification clauses exist "
         "specifically to cover claims BY third parties, not disputes between the two contracting "
         "parties; unclear scope here is a real gap.",
         "The clause explicitly covers third-party claims."),
        ("defense_obligation", "Obligation to defend (not just indemnify)", _INDEM_DEFENSE_OBLIGATION_RE,
         "No \"shall defend\" language was found — an indemnification obligation without a defense "
         "obligation may leave the indemnified party to fund its own defense while a claim is pending.",
         "An obligation to defend (not just indemnify) is stated."),
        ("notification_requirement", "Prompt notice of claims required", _INDEM_NOTIFICATION_RE,
         "No requirement that the indemnified party give prompt notice of a claim was found — absent "
         "this, disputes can arise over whether notice was timely.",
         "Prompt notice of claims is required."),
        ("limitations_or_procedure", "Defense/settlement control procedure specified",
         _INDEM_LIMITATIONS_PROCEDURE_RE,
         "No provision addresses who controls the defense or whether settlement requires consent — "
         "absent this, the indemnifying party could settle in a way that harms the indemnified party, "
         "or vice versa.",
         "Defense/settlement control is addressed."),
    ]

    elements: List[ClauseElement] = []
    for key, label, pattern, missing_detail, present_detail in checks:
        present = bool(pattern.search(text))
        elements.append(ClauseElement(
            key=key, label=label, present=present, weight=_INDEMNIFICATION_ELEMENT_WEIGHT[key],
            detail=present_detail if present else missing_detail,
        ))

    score = sum(e.weight for e in elements if e.present)
    return IndemnificationQualityReport(applicable=True, score=score, elements=elements)
