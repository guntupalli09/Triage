"""
Indemnification clause adapter, over policy_engine_core.

This is the second clause adapter — built specifically to test whether
policy_engine_core.py's boundary (extracted from Limitation of Liability
alone) is genuinely reusable or was accidentally shaped around LoL's
specifics. See the "Architecture findings" section at the bottom of this
docstring for what that test found.

SEMANTIC MODEL. Indemnification's hard problem is not a number to compare
against a threshold — that's secondary, and plugs into the shared
threshold machinery once everything else is settled. The hard problem is
topology:

    who -> indemnifies whom -> for what (triggering conduct/claims)
        -> subject to what scope (third-party only vs. also first-party)
        -> subject to what procedure (defense control, notice, cooperation)
        -> subject to what exclusions
        -> subject to what monetary treatment

A single document can state this topology more than once: a reciprocal
clause states it TWICE, once in each direction, and both directions are
simultaneously valid — this is fundamentally different from Limitation of
Liability, where multiple provisions describing the same single "general
cap" concept are competing candidates to be reconciled into one. Two
indemnification obligations pointing in different directions are not in
conflict; they are two different facts about two different promises. This
adapter tracks each directional IndemnityObligation independently rather
than trying to reconcile them into one controlling provision.

Because a lawyer's actual question is directional ("is the counterparty's
promise to us adequate," "is our promise to them excessive"), evaluation
resolves TWO roles from the document — our exposure obligation (we
indemnify them) and our protection obligation (they indemnify us) — and
evaluates each independently against the policy, using the same
REQUIRES_REVIEW-first abstention discipline as Limitation of Liability:
an unmappable role, an ambiguous trigger, or an unresolved monetary
structure always routes to REQUIRES_REVIEW rather than a guessed ACCEPT.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

from policy_engine_core import (
    ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE,
    REQUIRES_REVIEW, NOT_APPLICABLE,
    LadderStep, PolicyDecision,
    BUY_SIDE_ROLES, SELL_SIDE_ROLES, side_for_role,
    build_ladder as _core_build_ladder,
    classify_by_threshold, escalate_to_for_state, fallback_text_for_state,
)

RULE_ID = "POLICY_INDEMNIFICATION"

TRIGGERS = [
    "ip_infringement", "data_breach", "confidentiality",
    "negligence", "gross_negligence", "willful_misconduct",
]

_TRIGGER_KEYWORD_RE = {
    "ip_infringement": re.compile(
        r"\bintellectual property\b.{0,40}\binfringement\b|\bIP infringement\b|\binfringement of\b.{0,40}\bintellectual property\b",
        re.I,
    ),
    "data_breach": re.compile(r"\bdata breach(?:es)?\b|\bsecurity breach(?:es)?\b", re.I),
    "confidentiality": re.compile(r"\bconfidentiality\b|\bconfidential information\b", re.I),
    "gross_negligence": re.compile(r"\bgross negligence\b", re.I),
    "willful_misconduct": re.compile(r"\bwil[l]?ful misconduct\b", re.I),
    # Checked after gross_negligence so "gross negligence" doesn't also
    # register as a bare "negligence" match at a different span.
    "negligence": re.compile(r"\bnegligence\b(?!\s*(?:,|and|or)?\s*gross)", re.I),
}

_ANCHOR_RE = re.compile(r"indemnif\w*", re.I)
# An explicit, document-wide statement that no indemnification obligation
# exists at all. Distinct from the anchor-negation guard below (which only
# filters an anchor match immediately preceded by "no " — i.e. the SAME
# mention being negated): this catches the common drafting pattern where
# the word "indemnification" is used once in passing (e.g. acknowledging
# the concept exists) and a SEPARATE sentence elsewhere unambiguously
# states no obligation was created. Only used when no directional
# obligation could otherwise be parsed — it never overrides a real,
# parsed obligation.
_EXPLICIT_NO_OBLIGATION_RE = re.compile(
    r"no\s+part(?:y|ies)\s+shall\s+have\s+any\s+indemnification\s+obligation"
    r"|no\s+indemnification\s+obligation\s+(?:is|shall\s+be|exists|is\s+created|shall\s+arise)"
    r"|shall\s+not\s+have\s+any\s+indemnification\s+obligation",
    re.I,
)
_OBLIGATION_RE = re.compile(
    # No blanket re.I: [A-Z] must stay case-SENSITIVE, or it silently
    # matches lowercase too (Python re applies IGNORECASE to character
    # classes, not just literals) and captures garbage role names like
    # "party"/"the" out of "Each party shall indemnify ... the other
    # party." The verb phrase alone is wrapped in a scoped (?i:...) so
    # "Shall"/"SHALL"/"shall" all still match.
    r"([A-Z][A-Za-z]{2,25})(?:\s*\([^)]{0,40}\))?\s+(?i:shall|will|agrees to)\s+"
    r"(?i:defend,?\s*(?:and\s+)?indemnify|indemnify,?\s*(?:and\s+)?defend|indemnify)"
    r"(?i:,?\s*(?:and\s+)?(?:defend\s+and\s+)?hold\s+harmless)?\s+"
    r"([A-Z][A-Za-z]{2,25})\b"
)
_MUTUAL_RECIPROCAL_RE = re.compile(
    r"each\s+party\s+shall\s+indemnify(?:,?\s*defend,?)?(?:\s+and\s+hold\s+harmless)?\s+the\s+other(?:\s+party)?"
    r"|the\s+parties\s+shall\s+(?:mutually\s+)?indemnify\s+each\s+other"
    r"|mutual\s+indemnification",
    re.I,
)

_THIRD_PARTY_ONLY_RE = re.compile(r"third[\s-]part(?:y|ies)\s+claims?", re.I)
_FIRST_PARTY_SIGNAL_RE = re.compile(
    r"first[\s-]part(?:y|ies)\s+claims?|whether\s+or\s+not\s+(?:asserted\s+by\s+)?a\s+third\s+party"
    r"|regardless\s+of\s+whether\s+.{0,30}third\s+party|direct\s+claims?\s+between\s+the\s+parties"
    r"|whether\s+direct\s+or\s+third[\s-]part(?:y|ies)"
    # [A-Z] deliberately kept case-sensitive within the overall re.I
    # compile via (?-i:...) — role names in contracts are capitalized
    # defined terms, and this is the same re.I-over-[A-Z] hazard already
    # fixed elsewhere in this file's _OBLIGATION_RE.
    r"|(?i:claims?\s+by\s+)(?-i:[A-Z][A-Za-z]{2,25})(?i:\s+against\s+)(?-i:[A-Z][A-Za-z]{2,25})",
    re.I,
)

_EXCLUSION_SIGNAL_RE = re.compile(
    r"shall not apply to|does not apply to|excluded from (?:this|the foregoing|such) indemn\w*"
    r"|except for (?:claims? )?(?:arising from |related to )?|other than|excluding|with the exception of",
    re.I,
)
_CAP_TRIGGER_RE = re.compile(r"shall not exceed|is capped at|shall be capped|limited to", re.I)

_DEFENSE_INDEMNIFYING_RE = re.compile(
    r"indemnifying\s+part(?:y|ies)?\s+shall\s+(?:have\s+the\s+right\s+to\s+)?control(?:\s+the)?\s+(?:the\s+)?defense"
    r"|shall\s+(?:have\s+the\s+right\s+to\s+)?(?:assume\s+and\s+)?control\s+(?:the\s+)?defense.{0,60}?at\s+its\s+(?:own\s+)?(?:sole\s+)?(?:cost|expense)",
    re.I,
)
_DEFENSE_INDEMNIFIED_RE = re.compile(
    r"indemnified\s+part(?:y|ies)?\s+(?:may|shall\s+have\s+the\s+right\s+to)\s+control(?:\s+the)?\s+(?:the\s+)?defense"
    r"|indemnified\s+part(?:y|ies)?\s+shall\s+control\s+its\s+own\s+defense",
    re.I,
)
_DEFENSE_SHARED_RE = re.compile(r"jointly\s+control|participate\s+in\s+(?:the\s+)?defense\s+with", re.I)

_NOTICE_RE = re.compile(r"prompt(?:ly)?\s+(?:written\s+)?notice|notify\s+.{0,20}\s+in\s+writing|written\s+notice\s+of\s+(?:any\s+)?claim", re.I)
_COOPERATION_RE = re.compile(r"reasonable\s+cooperation|shall\s+cooperate|cooperate\s+(?:fully\s+)?with", re.I)

_MONETARY_UNLIMITED_RE = re.compile(
    r"shall\s+not\s+be\s+(?:subject\s+to\s+)?(?:any\s+)?(?:cap|limit)(?:ation)?"
    r"|shall\s+be\s+uncapped|uncapped\s+(?:obligation|indemnification)"
    r"|no\s+(?:cap|limit)(?:ation)?\s+shall\s+apply",
    re.I,
)
_MONETARY_MULTIPLIER_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:x|times)\s*(?:the\s+)?(?:total\s+|aggregate\s+)?(?:annual\s+)?fees?",
    re.I,
)
_MONETARY_FIXED_RE = re.compile(
    r"(?:shall\s+not\s+exceed|(?:is\s+)?capped\s+at|limited\s+to)\s*\$\s*([\d,]+(?:\.\d{2})?)",
    re.I,
)
_MONETARY_CROSS_REF_RE = re.compile(
    r"subject\s+to\s+the\s+(?:limitation\s+of\s+liability|liability\s+cap)\s+(?:set\s+forth\s+)?in\s+(Section\s+\d+(?:\.\d+)?)",
    re.I,
)

# A mutual/reciprocal ("each party"/"the parties shall mutually indemnify")
# match claims symmetric treatment. This finds sub-clauses that attribute
# terms to one SPECIFIC named party within that same window ("Vendor's
# indemnification obligations...", "Customer's obligations under this
# Section...") so those per-party terms can be compared against each other
# — see _detect_reciprocal_asymmetry. [A-Z] is deliberately kept case-
# sensitive within the overall re.I compile via (?-i:...), the same
# re.I-over-[A-Z] hazard already fixed elsewhere in this file.
_ROLE_ATTRIBUTION_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,25}))(?:'s)?\s+(?i:indemnification\s+)?(?i:obligations?)\s+"
    r"(?i:under\s+this\s+(?:Section|Agreement)\s+)?",
    re.I,
)
_GENERIC_ROLE_WORDS = {
    "each", "the", "any", "such", "this", "that", "both", "either", "all",
    "party", "parties", "indemnifying", "indemnified", "other",
}
_BROAD_BENEFICIARY_RE = re.compile(r"affiliates|officers|directors|employees|agents", re.I)

_PROVISION_WINDOW_CHARS = 2000
_LOCAL_WINDOW_CHARS = 160
_ROLE_ATTRIBUTION_LOCAL_CHARS = 220


# ---------------------------------------------------------------------------
# Structured facts
# ---------------------------------------------------------------------------

@dataclass
class MonetaryTreatment:
    kind: str  # "multiplier" | "fixed" | "unlimited" | "cross_reference" | "not_stated"
    multiplier: Optional[float] = None
    fixed_amount: Optional[float] = None
    cross_reference_label: Optional[str] = None
    raw_excerpt: str = ""

    def summary(self) -> str:
        if self.kind == "unlimited":
            return "Uncapped"
        if self.kind == "multiplier":
            return f"{self.multiplier:g}x annual fees"
        if self.kind == "fixed":
            return f"${self.fixed_amount:,.2f} fixed"
        if self.kind == "cross_reference":
            return f"per {self.cross_reference_label}"
        return "unspecified"


@dataclass
class TriggerTreatment:
    trigger: str
    treatment: str  # "covered" | "excluded" | "not_addressed" | "unresolved"
    raw_excerpt: str = ""
    established: bool = True


@dataclass
class IndemnityObligation:
    """One directional promise: indemnifying_role indemnifies indemnified_role."""
    indemnifying_role: str
    indemnifying_side: Optional[str]
    indemnified_role: str
    indemnified_side: Optional[str]
    trigger_treatments: Dict[str, TriggerTreatment]
    scope: str  # "third_party_only" | "includes_first_party" | "not_addressed" | "unresolved"
    defense_control: str  # "indemnifying_party" | "indemnified_party" | "shared" | "not_addressed" | "unresolved"
    notice_required: Optional[bool]
    cooperation_required: Optional[bool]
    monetary: MonetaryTreatment
    raw_excerpt: str
    start_index: int
    end_index: int
    section_label: Optional[str]
    is_mutual_reciprocal: bool = False
    # Only ever populated for is_mutual_reciprocal=True obligations — see
    # _detect_reciprocal_asymmetry. A non-empty list means the clause opens
    # with symmetric ("each party"/"mutual") language but states materially
    # different terms per named party somewhere in the same window, so the
    # opener's symmetry claim could not be verified.
    asymmetry_reasons: List[str] = field(default_factory=list)

    def label(self) -> str:
        prefix = f"Section {self.section_label} — " if self.section_label else ""
        return f"{prefix}{self.indemnifying_role} indemnifies {self.indemnified_role}"


@dataclass
class IndemnificationFacts:
    clause_found: bool
    obligations: List[IndemnityObligation] = field(default_factory=list)


class IndemnificationPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]
    required_protection_triggers_json: Optional[List[str]]
    prohibited_exposure_triggers_json: Optional[List[str]]
    require_exposure_third_party_only: bool
    require_defense_control_for_exposure: bool
    require_notice_and_cooperation_for_exposure: bool
    prohibit_uncapped_exposure: bool
    exposure_preferred_multiplier: Optional[float]
    exposure_acceptable_max_multiplier: Optional[float]
    exposure_negotiate_max_multiplier: Optional[float]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _excerpt(text: str, start: int, end: int, pad: int = 60) -> str:
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    if lo > 0:
        space = text.rfind(" ", 0, lo)
        if space != -1:
            lo = space + 1
    if hi < len(text):
        space = text.find(" ", hi)
        if space != -1:
            hi = space
    return text[lo:hi].strip()


def _section_label_before(text: str, anchor_start: int) -> Optional[str]:
    look = text[max(0, anchor_start - 30):anchor_start]
    nums = re.findall(r"\d{1,3}(?:\.\d{1,2})?", look)
    return nums[-1] if nums else None


def _classify_triggers(window: str) -> Dict[str, TriggerTreatment]:
    """Mirrors liability_policy_engine's forward-coverage-span exclusion
    model (same class of bug it was built to avoid: an exclusion signal
    for one trigger bleeding onto an unrelated nearby trigger). Deliberately
    reimplemented here rather than imported — the category *vocabulary* is
    clause-specific (indemnification triggers are conduct that CREATES an
    obligation; LoL categories are carve-outs FROM a cap — opposite
    polarity, not the same concept wearing a different name)."""
    positions = []
    for trig, kw_re in _TRIGGER_KEYWORD_RE.items():
        for m in kw_re.finditer(window):
            positions.append((m.start(), trig))

    covered_by_exclusion: Dict[str, str] = {}
    for sig in _EXCLUSION_SIGNAL_RE.finditer(window):
        span_end = min(len(window), sig.end() + 100)
        coverage_text = window[sig.end():span_end]
        boundary = re.search(r"\.\s|;", coverage_text)
        boundary_pos = boundary.start() if boundary else None
        for and_m in re.finditer(r"\band\b", coverage_text, re.I):
            if _CAP_TRIGGER_RE.search(coverage_text[and_m.end():and_m.end() + 60]):
                if boundary_pos is None or and_m.start() < boundary_pos:
                    boundary_pos = and_m.start()
                break
        if boundary_pos is not None:
            coverage_text = coverage_text[:boundary_pos]
        coverage_end = sig.end() + len(coverage_text)
        for pos, trig in positions:
            if sig.end() <= pos < coverage_end and trig not in covered_by_exclusion:
                covered_by_exclusion[trig] = _excerpt(window, sig.start(), coverage_end)

    treatments = {}
    for trig, kw_re in _TRIGGER_KEYWORD_RE.items():
        occurrences = list(kw_re.finditer(window))
        if not occurrences:
            treatments[trig] = TriggerTreatment(trigger=trig, treatment="not_addressed")
            continue
        m = occurrences[0]
        excerpt = _excerpt(window, m.start(), m.end())
        if trig in covered_by_exclusion:
            treatments[trig] = TriggerTreatment(trigger=trig, treatment="excluded", raw_excerpt=excerpt)
            continue
        local_start = max(0, m.start() - _LOCAL_WINDOW_CHARS)
        local_end = min(len(window), m.end() + _LOCAL_WINDOW_CHARS)
        local = window[local_start:local_end]
        if re.search(r"notwithstanding|provided,?\s+however|except as otherwise", local, re.I):
            treatments[trig] = TriggerTreatment(trigger=trig, treatment="unresolved", raw_excerpt=excerpt, established=False)
            continue
        treatments[trig] = TriggerTreatment(trigger=trig, treatment="covered", raw_excerpt=excerpt)
    return treatments


def _classify_scope(window: str) -> str:
    has_third = bool(_THIRD_PARTY_ONLY_RE.search(window))
    has_first = bool(_FIRST_PARTY_SIGNAL_RE.search(window))
    if has_first:
        return "includes_first_party"
    if has_third:
        return "third_party_only"
    return "not_addressed"


def _classify_defense_control(window: str) -> str:
    has_indemnifying = bool(_DEFENSE_INDEMNIFYING_RE.search(window))
    has_indemnified = bool(_DEFENSE_INDEMNIFIED_RE.search(window))
    has_shared = bool(_DEFENSE_SHARED_RE.search(window))
    signals = sum([has_indemnifying, has_indemnified, has_shared])
    if signals > 1:
        return "shared"
    if has_shared:
        return "shared"
    if has_indemnifying:
        return "indemnifying_party"
    if has_indemnified:
        return "indemnified_party"
    return "not_addressed"


def _classify_monetary(window: str, obligation_start: int) -> MonetaryTreatment:
    xref = _MONETARY_CROSS_REF_RE.search(window)
    unlimited = _MONETARY_UNLIMITED_RE.search(window)
    mult = _MONETARY_MULTIPLIER_RE.search(window)
    fixed = _MONETARY_FIXED_RE.search(window)

    candidates = [c for c in (xref, unlimited, mult, fixed) if c is not None]
    if not candidates:
        return MonetaryTreatment(kind="not_stated")
    # Earliest mention in the obligation's own window governs — consistent
    # with "closest stated position wins" used throughout the LoL adapter.
    first = min(candidates, key=lambda m: m.start())
    if first is xref:
        return MonetaryTreatment(kind="cross_reference", cross_reference_label=xref.group(1), raw_excerpt=_excerpt(window, xref.start(), xref.end()))
    if first is unlimited:
        return MonetaryTreatment(kind="unlimited", raw_excerpt=_excerpt(window, unlimited.start(), unlimited.end()))
    if first is mult:
        return MonetaryTreatment(kind="multiplier", multiplier=float(mult.group(1)), raw_excerpt=_excerpt(window, mult.start(), mult.end()))
    return MonetaryTreatment(kind="fixed", fixed_amount=float(fixed.group(1).replace(",", "")), raw_excerpt=_excerpt(window, fixed.start(), fixed.end()))


def _monetary_key(m: MonetaryTreatment) -> Tuple[str, Optional[float], Optional[float]]:
    return (m.kind, m.multiplier, m.fixed_amount)


def _local_clause_window(text: str, start: int, max_chars: int = _ROLE_ATTRIBUTION_LOCAL_CHARS) -> str:
    hi = min(len(text), start + max_chars)
    boundary = re.search(r"\.\s|;", text[start:hi])
    if boundary:
        hi = start + boundary.start() + 1
    return text[start:hi]


def _detect_reciprocal_asymmetry(window: str) -> List[str]:
    """A mutual/reciprocal match ("each party shall indemnify... the other
    party" / "the parties shall mutually indemnify each other") claims
    symmetric treatment. Real drafting sometimes layers differentiated,
    per-party-NAMED terms on top of that symmetric opener — a proviso that
    states different monetary caps, different covered triggers, different
    claim scope, different defense-control terms, or a different
    indemnified-party group for one named role than another. A genuinely
    reciprocal clause never does this; when it happens, the opener's
    symmetry claim cannot be trusted and must not be treated as
    established fact.

    Scans the window for sub-clauses attributing terms to a SPECIFIC named
    role ("Vendor's indemnification obligations...", not "each party's" or
    "the indemnifying party's" — those are generic, not asymmetry
    evidence) and compares those role-local snapshots pairwise. Returns a
    list of human-readable disagreement reasons; empty means either no
    per-party attribution was found (nothing to compare — not itself
    evidence of asymmetry) or all attributed roles agree.
    """
    snapshots: Dict[str, Dict[str, Any]] = {}
    for m in _ROLE_ATTRIBUTION_RE.finditer(window):
        role = m.group(1)
        if role.lower() in _GENERIC_ROLE_WORDS:
            continue
        local = _local_clause_window(window, m.end())
        # Later mentions of the same role in the same window (rare) don't
        # overwrite an earlier snapshot — first mention governs, matching
        # the "earliest stated position wins" convention used elsewhere.
        snapshots.setdefault(role, {
            "monetary": _classify_monetary(local, 0),
            "scope": _classify_scope(local),
            "defense_control": _classify_defense_control(local),
            "triggers": frozenset(
                trig for trig, kw_re in _TRIGGER_KEYWORD_RE.items() if kw_re.search(local)
            ),
            "broad_beneficiary": bool(_BROAD_BENEFICIARY_RE.search(local)),
        })

    roles = list(snapshots.keys())
    if len(roles) < 2:
        return []

    reasons: List[str] = []
    base_role = roles[0]
    base = snapshots[base_role]
    for role in roles[1:]:
        snap = snapshots[role]
        if (
            base["monetary"].kind != "not_stated" and snap["monetary"].kind != "not_stated"
            and _monetary_key(base["monetary"]) != _monetary_key(snap["monetary"])
        ):
            reasons.append(
                f"{base_role} and {role} state different monetary terms "
                f"({base['monetary'].summary()} vs {snap['monetary'].summary()})"
            )
        if base["triggers"] and snap["triggers"] and base["triggers"] != snap["triggers"]:
            reasons.append(f"{base_role} and {role} cover different trigger sets")
        if (
            base["scope"] not in ("not_addressed", "unresolved")
            and snap["scope"] not in ("not_addressed", "unresolved")
            and base["scope"] != snap["scope"]
        ):
            reasons.append(f"{base_role} and {role} state different claim scope")
        if (
            base["defense_control"] not in ("not_addressed", "unresolved")
            and snap["defense_control"] not in ("not_addressed", "unresolved")
            and base["defense_control"] != snap["defense_control"]
        ):
            reasons.append(f"{base_role} and {role} state different defense-control terms")
        if base["broad_beneficiary"] != snap["broad_beneficiary"]:
            reasons.append(f"{base_role} and {role} name different indemnified-party groups")

    return reasons


def _extract_obligation_window(text: str, start: int, end: int) -> str:
    return text[start:min(len(text), start + _PROVISION_WINDOW_CHARS)]


def extract_indemnification_facts(text: str) -> Optional[IndemnificationFacts]:
    """Finds every directional indemnification obligation stated in the
    full document. Unlike Limitation of Liability's single controlling
    provision, obligations are NOT reconciled into one — a reciprocal
    clause legitimately states two simultaneously valid obligations, one
    per direction, and both are evaluated independently."""
    # "No indemnification provision is included..." mentions the word but
    # explicitly negates it — a bare substring search would treat that
    # sentence as evidence a clause exists. Require at least one anchor
    # occurrence NOT immediately preceded by a negation cue.
    anchors = [m for m in _ANCHOR_RE.finditer(text) if not re.search(r"\bno\s+$", text[max(0, m.start() - 15):m.start()], re.I)]
    if not anchors:
        return None

    obligations: List[IndemnityObligation] = []
    seen_spans: List[Tuple[int, int]] = []

    for m in _OBLIGATION_RE.finditer(text):
        if any(abs(m.start() - s) < 50 for s, _ in seen_spans):
            continue
        indemnifying_role, indemnified_role = m.group(1), m.group(2)
        if indemnifying_role.lower() == indemnified_role.lower():
            continue  # regex false-positive guard, e.g. matched the same word twice
        window = _extract_obligation_window(text, m.start(), min(len(text), m.start() + _PROVISION_WINDOW_CHARS))
        obligations.append(IndemnityObligation(
            indemnifying_role=indemnifying_role, indemnifying_side=side_for_role(indemnifying_role),
            indemnified_role=indemnified_role, indemnified_side=side_for_role(indemnified_role),
            trigger_treatments=_classify_triggers(window),
            scope=_classify_scope(window),
            defense_control=_classify_defense_control(window),
            notice_required=True if _NOTICE_RE.search(window) else None,
            cooperation_required=True if _COOPERATION_RE.search(window) else None,
            monetary=_classify_monetary(window, m.start()),
            raw_excerpt=_excerpt(text, m.start(), m.end()),
            start_index=m.start(), end_index=m.end(),
            section_label=_section_label_before(text, m.start()),
        ))
        seen_spans.append((m.start(), m.end()))

    for m in _MUTUAL_RECIPROCAL_RE.finditer(text):
        if any(abs(m.start() - s) < 50 for s, _ in seen_spans):
            continue
        window = _extract_obligation_window(text, m.start(), min(len(text), m.start() + _PROVISION_WINDOW_CHARS))
        # A mutual/reciprocal clause names no specific roles — represented
        # as a single symmetric obligation; the evaluator applies its terms
        # to both directions rather than picking one.
        obligations.append(IndemnityObligation(
            indemnifying_role="Each Party", indemnifying_side=None,
            indemnified_role="the Other Party", indemnified_side=None,
            trigger_treatments=_classify_triggers(window),
            scope=_classify_scope(window),
            defense_control=_classify_defense_control(window),
            notice_required=True if _NOTICE_RE.search(window) else None,
            cooperation_required=True if _COOPERATION_RE.search(window) else None,
            monetary=_classify_monetary(window, m.start()),
            raw_excerpt=_excerpt(text, m.start(), m.end()),
            start_index=m.start(), end_index=m.end(),
            section_label=_section_label_before(text, m.start()),
            is_mutual_reciprocal=True,
            asymmetry_reasons=_detect_reciprocal_asymmetry(window),
        ))
        seen_spans.append((m.start(), m.end()))

    if not obligations:
        if _EXPLICIT_NO_OBLIGATION_RE.search(text):
            # No directional promise was parsed, AND the document contains
            # an unambiguous statement that no obligation exists — treat
            # this the same as no clause being present at all, rather than
            # an unparseable-but-present clause. Deliberately narrow (fixed
            # phrases only): this must not fire on an ordinary "indemnif..."
            # mention that simply failed to parse for an unrelated reason.
            return None
        # "indemnif..." appears somewhere (e.g. a heading or a cross-
        # reference to an indemnification section elsewhere) but no
        # directional promise could be parsed from it.
        return IndemnificationFacts(clause_found=True, obligations=[])

    obligations.sort(key=lambda o: o.start_index)
    return IndemnificationFacts(clause_found=True, obligations=obligations)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _fmt_multiplier(value: Optional[float]) -> str:
    if value is None:
        return "unspecified"
    return f"{value:g}x annual fees"


def _build_ladder(policy: IndemnificationPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", f"Preferred exposure cap: {_fmt_multiplier(policy.exposure_preferred_multiplier)}"),
        ("ACCEPTABLE", f"Auto-accept exposure up to {_fmt_multiplier(policy.exposure_acceptable_max_multiplier)}"),
        ("FALLBACK", f"Negotiate exposure up to {_fmt_multiplier(policy.exposure_negotiate_max_multiplier)}"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Uncapped exposure — prohibited by policy" if policy.prohibit_uncapped_exposure else "Uncapped exposure"),
    ]
    return _core_build_ladder(state, step_specs)


def _resolve_obligations_for_side(
    obligations: List[IndemnityObligation], contract_side: str,
) -> Tuple[Optional[IndemnityObligation], Optional[IndemnityObligation], List[str]]:
    """Resolves which obligation (if any) is our EXPOSURE (we indemnify
    them) and which is our PROTECTION (they indemnify us). Returns
    (exposure_obligation, protection_obligation, unresolved_reasons).
    Never guesses: an obligation whose roles can't be mapped to our
    configured contract_side contributes a reason instead of being
    silently treated as exposure or protection."""
    reasons: List[str] = []
    exposure, protection = None, None

    reciprocal = [o for o in obligations if o.is_mutual_reciprocal]
    named = [o for o in obligations if not o.is_mutual_reciprocal]

    if reciprocal and not named:
        obligation = reciprocal[0]
        if obligation.asymmetry_reasons:
            # The clause opens with symmetric ("each party"/"mutual")
            # language, but states materially different terms for at
            # least one named party elsewhere in the same provision — the
            # opener's symmetry claim could not be verified, so it must
            # not be trusted as both our exposure AND our protection.
            # Never guess which named party's terms are actually ours;
            # route to REQUIRES_REVIEW instead of ACCEPT. See
            # tests/test_indemnification_policy_engine.py::
            # TestReciprocalSymmetryVerification and
            # benchmarks/indemnification_benchmark_report.md.
            reasons.append(
                "clause opens with reciprocal ('each party'/'mutual') language, but states "
                "materially different terms per named party (" + "; ".join(obligation.asymmetry_reasons) +
                ") — cannot confirm the clause is actually symmetric, so which named party's terms "
                "are ours cannot be determined from this opener alone"
            )
            return None, None, reasons
        # A symmetric mutual clause applies the same terms in both
        # directions — usable as both exposure and protection regardless
        # of contract_side, since the terms don't differ by party.
        return obligation, obligation, reasons

    if contract_side == "mutual":
        if named:
            reasons.append(
                "contract states directional (non-mutual) indemnification obligations, but this playbook "
                "is configured for a mutual position — cannot determine which obligation is ours"
            )
        return None, None, reasons

    for o in named:
        if o.indemnifying_side == contract_side and o.indemnified_side is not None and o.indemnified_side != contract_side:
            if exposure is not None and _monetary_key(exposure.monetary) != _monetary_key(o.monetary):
                reasons.append("multiple obligations found where we are the indemnifying party, with different monetary terms — cannot determine which governs")
            elif exposure is None:
                exposure = o
        elif o.indemnified_side == contract_side and o.indemnifying_side is not None and o.indemnifying_side != contract_side:
            if protection is not None and _monetary_key(protection.monetary) != _monetary_key(o.monetary):
                reasons.append("multiple obligations found where we are the indemnified party, with different monetary terms — cannot determine which governs")
            elif protection is None:
                protection = o
        elif o.indemnifying_side is None or o.indemnified_side is None:
            reasons.append(
                f"obligation \"{o.indemnifying_role} indemnifies {o.indemnified_role}\" could not be mapped "
                f"to our configured contract side ({contract_side}) — unrecognized party name(s)"
            )

    return exposure, protection, reasons


def evaluate_indemnification_policy(
    facts: Optional[IndemnificationFacts],
    policy: IndemnificationPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    """Deterministic state machine over indemnification topology. Evaluates
    our EXPOSURE obligation (do we promise too much) and our PROTECTION
    obligation (does the counterparty promise us enough) independently,
    then combines them — REQUIRES_REVIEW wins if either side has an
    unresolved fact, otherwise the more severe of the two resolved states
    governs (ESCALATE/PROHIBITED > NEGOTIATE > ACCEPT_WITH_NOTE > ACCEPT)."""
    if facts is None or not facts.clause_found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="indemnification", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No indemnification clause found",
            policy_limit_summary=_fmt_multiplier(policy.exposure_preferred_multiplier),
            required_action="None — this contract does not address indemnification",
            explanation="No indemnification clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="Indemnification treatment", our_position_label="Our exposure",
        counterparty_position_label="Counterparty protection",
        )

    if not facts.obligations:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="indemnification", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Indemnification referenced but no directional obligation could be parsed",
            policy_limit_summary=_fmt_multiplier(policy.exposure_preferred_multiplier),
            required_action="Manual review required — indemnification language present but structure unclear",
            explanation="The document references indemnification but no parseable 'X shall indemnify Y' or mutual "
                        "reciprocal structure was found — the clause may be malformed, cross-referenced elsewhere, "
                        "or drafted in a form this extractor doesn't recognize.",
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[],
            unresolved_facts=["indemnification obligation structure could not be parsed"],
            start_index=None, end_index=None, source=source, summary_label="Indemnification treatment", our_position_label="Our exposure",
        counterparty_position_label="Counterparty protection",
        )

    exposure, protection, resolution_reasons = _resolve_obligations_for_side(facts.obligations, policy.contract_side)
    unresolved_facts = list(resolution_reasons)

    required_protection = list(policy.required_protection_triggers_json or [])
    prohibited_exposure = list(policy.prohibited_exposure_triggers_json or [])

    # --- Protection-side unresolved facts ---
    # A missing protection obligation (protection is None with no
    # resolution_reason) is NOT treated as unresolved here — that's a
    # confidently-observed gap, handled below as a NEGOTIATE finding, not
    # an ambiguity requiring review.
    if protection is not None:
        for trig in required_protection:
            t = protection.trigger_treatments.get(trig)
            if t is not None and t.treatment == "unresolved":
                unresolved_facts.append(f"protection coverage for {trig} (ambiguous carve-out language)")

    # --- Exposure-side unresolved facts ---
    exposure_monetary_value = None
    if exposure is not None:
        for trig in prohibited_exposure:
            t = exposure.trigger_treatments.get(trig)
            if t is not None and t.treatment == "unresolved":
                unresolved_facts.append(f"exposure coverage for {trig} (ambiguous carve-out language)")
        if policy.require_exposure_third_party_only and exposure.scope == "unresolved":
            unresolved_facts.append("exposure scope (third-party vs. first-party ambiguous)")
        if exposure.monetary.kind == "cross_reference":
            unresolved_facts.append(
                f"exposure monetary treatment (delegates to {exposure.monetary.cross_reference_label}, not resolved by this evaluation)"
            )

    if unresolved_facts:
        controlling = exposure or protection or facts.obligations[0]
        explanation = (
            f"Contract language: \"{controlling.raw_excerpt}\". This indemnification structure could not be "
            f"evaluated deterministically — the following fact(s) required for a policy decision could not be "
            f"reliably established: {'; '.join(unresolved_facts)}. Result: {REQUIRES_REVIEW}."
        )
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="indemnification", state=REQUIRES_REVIEW,
            contract_language=controlling.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary=_fmt_multiplier(policy.exposure_negotiate_max_multiplier),
            required_action="Manual review required — " + "; ".join(unresolved_facts),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved_facts,
            start_index=controlling.start_index, end_index=controlling.end_index, source=source,
            controlling_provision={"label": controlling.label(), "excerpt": controlling.raw_excerpt,
                                    "start_index": controlling.start_index, "end_index": controlling.end_index},
            summary_label="Indemnification treatment", our_position_label="Our exposure",
        counterparty_position_label="Counterparty protection",
        )

    # --- Resolved: determine severity-ranked findings from each side ---
    notes: List[str] = []
    worst_state = ACCEPT

    def _worse(a: str, b: str) -> str:
        order = {ACCEPT: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, MUST_REDLINE: 3, ESCALATE: 4, PROHIBITED: 5}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    if required_protection:
        if protection is None:
            notes.append(f"no protection obligation found covering required trigger(s): {', '.join(required_protection)}")
            worst_state = _worse(worst_state, NEGOTIATE)
        else:
            missing = [
                t for t in required_protection
                if protection.trigger_treatments.get(t) is None
                or protection.trigger_treatments[t].treatment != "covered"
            ]
            if missing:
                notes.append(f"protection missing required trigger(s): {', '.join(missing)}")
                worst_state = _worse(worst_state, NEGOTIATE)

    if exposure is not None:
        prohibited_hit = [
            t for t in prohibited_exposure
            if exposure.trigger_treatments.get(t) is not None
            and exposure.trigger_treatments[t].treatment == "covered"
        ]
        if prohibited_hit:
            notes.append(f"exposure covers prohibited trigger(s): {', '.join(prohibited_hit)}")
            worst_state = _worse(worst_state, NEGOTIATE)

        # A scope that was never affirmatively confirmed as third-party-only
        # ("not_addressed" — the text simply never said "third-party
        # claims") is not the same fact as a confirmed third-party-only
        # limitation, and must not be silently treated as satisfying a
        # policy that specifically requires that limitation to be stated.
        # See tests/test_indemnification_policy_engine.py::
        # TestThirdPartyOnlyScopeSilence and benchmarks/
        # indemnification_benchmark_report.md's scope-05 finding.
        if policy.require_exposure_third_party_only and exposure.scope != "third_party_only":
            notes.append("exposure is not affirmatively limited to third-party claims")
            worst_state = _worse(worst_state, NEGOTIATE)

        if policy.require_defense_control_for_exposure and exposure.defense_control not in ("indemnifying_party", "shared"):
            notes.append("we do not control (or share control of) the defense of claims we must indemnify")
            worst_state = _worse(worst_state, NEGOTIATE)

        if policy.require_notice_and_cooperation_for_exposure and not (exposure.notice_required and exposure.cooperation_required):
            notes.append("exposure obligation lacks a notice-and-cooperation precondition")
            worst_state = _worse(worst_state, NEGOTIATE)

        if exposure.monetary.kind == "unlimited":
            if policy.prohibit_uncapped_exposure:
                notes.append("exposure is uncapped, prohibited by policy")
                worst_state = _worse(worst_state, PROHIBITED)
            else:
                notes.append("exposure is uncapped")
                worst_state = _worse(worst_state, ESCALATE)
        elif exposure.monetary.kind == "fixed":
            notes.append(f"exposure cap is a fixed dollar amount ({exposure.monetary.summary()}), not a fees multiplier — compare manually")
            worst_state = _worse(worst_state, ESCALATE)
        elif exposure.monetary.kind == "multiplier":
            threshold_state = classify_by_threshold(
                exposure.monetary.multiplier, policy.exposure_preferred_multiplier,
                policy.exposure_acceptable_max_multiplier, policy.exposure_negotiate_max_multiplier,
            )
            if threshold_state != ACCEPT:
                notes.append(f"exposure cap {exposure.monetary.summary()} exceeds preferred position")
            worst_state = _worse(worst_state, threshold_state)
        elif exposure.monetary.kind == "not_stated":
            notes.append("exposure obligation states no monetary treatment at all")
            worst_state = _worse(worst_state, MUST_REDLINE)

    controlling = exposure or protection or facts.obligations[0]
    extracted_summary = (
        f"Exposure: {exposure.monetary.summary() if exposure else 'n/a'}; "
        f"Protection: {'present' if protection else 'not found'}"
    )
    if worst_state == ACCEPT and not notes:
        required_action = "None — indemnification terms meet policy"
        explanation = f"Contract language: \"{controlling.raw_excerpt}\". No policy gaps found. Result: {ACCEPT}."
    else:
        if worst_state in (ESCALATE, PROHIBITED):
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — " + "; ".join(notes)
        elif worst_state == NEGOTIATE:
            required_action = "Negotiate — " + "; ".join(notes)
        else:
            required_action = "None — within acceptable range, note for the file: " + "; ".join(notes)
        explanation = (
            f"Contract language: \"{controlling.raw_excerpt}\". {'; '.join(notes)}. Result: {worst_state}."
        )

    return PolicyDecision(
        rule_id=RULE_ID, clause_type="indemnification", state=worst_state,
        contract_language=controlling.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary=_fmt_multiplier(policy.exposure_negotiate_max_multiplier),
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, worst_state),
        category_treatments=[
            {"category": t.trigger, "treatment": t.treatment, "cap_summary": None,
             "raw_excerpt": t.raw_excerpt, "established": t.established}
            for t in (exposure.trigger_treatments.values() if exposure else [])
        ],
        unresolved_facts=[], start_index=controlling.start_index, end_index=controlling.end_index,
        escalate_to=escalate_to_for_state(worst_state, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(worst_state, policy.fallback_text, (NEGOTIATE, ESCALATE, PROHIBITED)),
        source=source,
        controlling_provision={"label": controlling.label(), "excerpt": controlling.raw_excerpt,
                                "start_index": controlling.start_index, "end_index": controlling.end_index},
        our_position={"role": exposure.indemnifying_role, "summary": exposure.monetary.summary()} if exposure else None,
        counterparty_position={"role": protection.indemnifying_role, "summary": protection.monetary.summary()} if protection else None,
        summary_label="Indemnification treatment", our_position_label="Our exposure",
        counterparty_position_label="Counterparty protection",
    )
