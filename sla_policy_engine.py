"""
SLA / Service Levels clause adapter, over policy_engine_core. Adapter
#12 — built per the resolved design in
docs/architecture/sla_adapter_design.md; the four design decisions
recorded there are treated as fixed inputs to this implementation, not
reopened here.

SEMANTIC MODEL: three independent fact families, deliberately never
collapsed into one sla_compliant classification (mirroring the
discipline established by payment_terms's ten independent dimensions and
warranties' three-way obligation/disclaimer/remedy split):

  A. AVAILABILITY -- uptime/availability percentage, measurement period,
     and four independently-present/absent exclusion categories
     (scheduled maintenance, emergency maintenance, customer-caused,
     force majeure) that modify the nominal commitment's real-world
     meaning without this adapter ever attempting to compute an
     "effective" percentage from them (design doc S1/S5: that requires
     information -- how much downtime each exclusion actually covers --
     that is not extractable from contract text).

  B. SEVERITY TARGETS -- four canonical internal levels (P1_CRITICAL
     through P4_LOW, design doc S2.3), each independently carrying a
     response-time ceiling and a restoration-time ceiling, each of those
     in turn carrying its own BASIS (calendar or business). Response and
     restoration are captured via explicit named regex groups from a
     single match wherever the drafting states them together, never by
     two independently-scoped searches over a shared window -- the
     highest-risk extraction pattern this adapter has, per the design
     doc, is exactly the response/restoration cross-attribution a shared
     window would risk.

  C. REMEDY MECHANICS -- service-credit entitlement, trigger, percentage
     and basis, minimum credit cap, cumulative/tiered schedule presence,
     claim-submission deadline, chronic-failure definition, a
     termination right tied to chronic failure, and exclusive-remedy
     language. Deliberately independent of payment_terms_policy_engine:
     no import, no shared resolver, no cross-module function call.
     payment_terms.service_credit_present stays a presence-only flag in
     its own module; this adapter owns the full credit mechanism as its
     own facts. Reconciling the two is left to a future Interaction
     Engine operating on independently-extracted spans, never wired
     inside either extractor (design doc S7/S8, decision 4).

COMPARISON DIRECTION (design doc S4, decision 3 -- encoded explicitly,
never inferred from a field name): availability is a FLOOR (higher
stated uptime is stronger; violation is actual < policy minimum).
Response and restoration times are CEILINGS (lower stated hours is
stronger; violation is actual > policy maximum). Credit percentage and
credit cap are FLOORS (higher stated percentage/cap is more protective
of the credit recipient; violation is actual < policy minimum) --
minimum_credit_cap_percent_of_fees was deliberately named as a minimum,
not a maximum, for exactly this reason (a low cap is the unfavorable
direction, the opposite of every "maximum_*" ceiling field elsewhere in
this codebase).

BUSINESS HOURS (design doc S5/S8, decision 2 -- never reopened here):
this adapter never converts a business-hours or business-day value into
calendar hours. Every SeverityTarget response/restoration value carries
a `basis` of "calendar" or "business", set from the contract text alone.
Only two conversions are ever performed, both pure calendar arithmetic
with zero external dependency: minutes -> hours (/60) and CALENDAR days
-> calendar hours (x24). A BUSINESS day is never converted to business
hours, because that requires an assumed business-day length this
adapter has no basis to invent -- a business-day value with no
convertible hours figure is tracked as `hours=None,
unconvertible=True` and, if a policy ceiling for that severity/dimension
is configured, that comparison abstains (REQUIRES_REVIEW) rather than
guessing a business-day length. A same-basis comparison (contract
"business", policy configured as "business" for that same
severity/dimension) is allowed; a cross-basis comparison always
abstains, full stop -- there is no silent default basis assumed on
either side of the comparison.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

from policy_engine_core import (
    ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE,
    REQUIRES_REVIEW, NOT_APPLICABLE,
    LadderStep, build_ladder as _core_build_ladder,
    excerpt as _excerpt, section_label_before as _section_label_before,
    requires_review_explanation, requires_review_required_action,
    PolicyDecision,
    is_operative_context as _core_is_operative_context,
)

RULE_ID = "POLICY_SLA"

_PROVISION_WINDOW_CHARS = 3000

SEVERITY_LEVELS: Tuple[str, ...] = ("P1_CRITICAL", "P2_HIGH", "P3_MEDIUM", "P4_LOW")

MAINTENANCE_EXCLUSION_TYPES: Tuple[str, ...] = (
    "scheduled_maintenance", "emergency_maintenance", "customer_caused", "force_majeure",
)

# --- Clause presence ---------------------------------------------------------------------------
_ANCHOR_RE = re.compile(r"service\s+level|\bSLA\b|\buptime\b|availability\s+commitment", re.I)

# --- Sentence-boundary-safe local window (decimal-safe -- reused verbatim from
# payment_terms_policy_engine._local_window, per the same "copy the proven fix,
# don't reintroduce the naive version" discipline already applied when fixing
# insurance_policy_engine.py during the pre-#11 hardening pass). ---------------
_SENTENCE_END_RE = re.compile(r"(?<!\d)\.(?!\d)|;")


def _local_window(text: str, start: int, other_anchor_positions: List[int], max_radius: int = 300) -> str:
    end = min(len(text), start + max_radius)
    m = _SENTENCE_END_RE.search(text, start, end)
    if m:
        end = min(end, m.end())
    for pos in other_anchor_positions:
        if pos > start:
            end = min(end, pos)
    return text[start:end]


# --- Availability -------------------------------------------------------------------------------
_UPTIME_ANCHOR_RE = re.compile(r"uptime|availability", re.I)
# Percent can appear either before ("99.9% uptime") or after ("uptime
# commitment of 99.9%") the anchor word -- a single combined regex with
# two alternative capture groups handles both orders explicitly, rather
# than a forward-only local-window search that would silently miss
# whichever order isn't scoped for.
_UPTIME_WITH_PERCENT_RE = re.compile(
    r"(\d{2,3}(?:\.\d+)?)\s*%\s*(?:uptime|availability)"
    r"|(?:uptime|availability)[^.;\n]{0,40}?(\d{2,3}(?:\.\d+)?)\s*%",
    re.I,
)
_UPTIME_NEGATION_RE = re.compile(r"\bno\s+(?:uptime|availability)\s+(?:commitment|guarantee|warranty)", re.I)

_MEASUREMENT_PERIOD_RE = re.compile(
    r"\b(monthly|calendar\s+month|quarterly|calendar\s+quarter|annual(?:ly)?|calendar\s+year)\b", re.I,
)
_MEASUREMENT_PERIOD_NORMALIZE = {
    "monthly": "monthly", "calendar month": "monthly",
    "quarterly": "quarterly", "calendar quarter": "quarterly",
    "annually": "annual", "annual": "annual", "calendar year": "annual",
}

_SCHEDULED_MAINT_RE = re.compile(r"scheduled\s+maintenance", re.I)
_EMERGENCY_MAINT_RE = re.compile(r"emergency\s+maintenance", re.I)
_CUSTOMER_CAUSED_RE = re.compile(
    r"customer[- ]caused|caused\s+by\s+(?:the\s+)?Customer|Customer'?s?\s+acts?\s+or\s+omissions", re.I,
)
_FORCE_MAJEURE_RE = re.compile(r"force\s+majeure", re.I)
_METHODOLOGY_RE = re.compile(r"measured\s+(?:at|by|as)|calculated\s+as\s+follows|methodology\s+(?:for|is)", re.I)

# --- Severity label anchoring and normalization -------------------------------------------------
_SEVERITY_DECLARED_RE = re.compile(
    # The capture group intentionally accepts any 1-2 digit number
    # (P?\d{1,2}), not just 1-4 -- a declared "Sev 5" or "Priority 9"
    # must still be recognized as a severity-label MENTION so it can be
    # routed to REQUIRES_REVIEW by _normalize_severity_label's failure to
    # map it, rather than silently never being seen as a severity label
    # at all (which would make an out-of-range level indistinguishable
    # from ordinary prose containing "severity").
    r"(?:severity|priority|sev)\.?\s*(?:level\s*)?[:\-#]?\s*(P?\d{1,2}|critical|high|medium|low)\b", re.I,
)
_SEVERITY_BARE_P_RE = re.compile(r"\bP([1-4])\b")
# A bare severity word used AS a label ("Critical issues:", "High -")
# requires immediate label-shaped punctuation/context, not just the word
# appearing anywhere -- avoids matching "critical" used as an ordinary
# adjective ("a critical issue for both parties") elsewhere in an SLA
# section.
_SEVERITY_BARE_WORD_RE = re.compile(r"\b(Critical|High|Medium|Low)\b\s*(?:issues?|priority|severity)?\s*[:\-]", re.I)

_SEVERITY_LABEL_NORMALIZE: Dict[str, str] = {
    "1": "P1_CRITICAL", "p1": "P1_CRITICAL", "critical": "P1_CRITICAL",
    "2": "P2_HIGH", "p2": "P2_HIGH", "high": "P2_HIGH",
    "3": "P3_MEDIUM", "p3": "P3_MEDIUM", "medium": "P3_MEDIUM",
    "4": "P4_LOW", "p4": "P4_LOW", "low": "P4_LOW",
}


def _normalize_severity_label(raw: str) -> Optional[str]:
    key = raw.strip().lower()
    if key in _SEVERITY_LABEL_NORMALIZE:
        return _SEVERITY_LABEL_NORMALIZE[key]
    stripped = key.lstrip("p")
    if stripped in _SEVERITY_LABEL_NORMALIZE:
        return _SEVERITY_LABEL_NORMALIZE[stripped]
    return None


# --- Response / restoration time --------------------------------------------------------------
_TIME_UNIT = r"business\s+days?|calendar\s+days?|days?|business\s+hours?|calendar\s+hours?|hours?|hrs?|minutes?|mins?"

# Explicit named captures, never a shared/generic window search -- the single
# highest-risk extraction pattern named in the design doc (S2/S5): response and
# restoration routinely appear in the same sentence or table row, and must
# never be resolved by two independent scoped searches that could silently
# swap which number belongs to which dimension.
_TABLE_ROW_RE = re.compile(
    rf"(?P<level>P[1-4]|Sev(?:erity)?\.?\s*[1-4]|Critical|High|Medium|Low)\s*[|:]\s*"
    rf"(?P<response_value>\d+(?:\.\d+)?)\s*(?P<response_unit>{_TIME_UNIT})\s*[|,]\s*"
    rf"(?P<restoration_value>\d+(?:\.\d+)?)\s*(?P<restoration_unit>{_TIME_UNIT})",
    re.I,
)
_COMBINED_TRAILING_LABEL_RE = re.compile(
    rf"(?P<response_value>\d+(?:\.\d+)?)\s*(?P<response_unit>{_TIME_UNIT})\s*response"
    rf"[^.;\n]{{0,80}}?"
    rf"(?P<restoration_value>\d+(?:\.\d+)?)\s*(?P<restoration_unit>{_TIME_UNIT})\s*(?:restoration|resolution)",
    re.I,
)
_COMBINED_LEADING_LABEL_RE = re.compile(
    rf"response\s*(?:time)?\s*(?:of\s*)?[:\-]?\s*(?P<response_value>\d+(?:\.\d+)?)\s*(?P<response_unit>{_TIME_UNIT})"
    rf"[^.;\n]{{0,80}}?"
    rf"(?:restoration|resolution)\s*(?:time)?\s*(?:of\s*)?[:\-]?\s*(?P<restoration_value>\d+(?:\.\d+)?)\s*(?P<restoration_unit>{_TIME_UNIT})",
    re.I,
)
_RESPONSE_ONLY_RE = re.compile(
    rf"(?P<response_value>\d+(?:\.\d+)?)\s*(?P<response_unit>{_TIME_UNIT})\s*response"
    rf"|response\s*(?:time)?\s*(?:of\s*)?[:\-]?\s*(?P<response_value2>\d+(?:\.\d+)?)\s*(?P<response_unit2>{_TIME_UNIT})",
    re.I,
)
_RESTORATION_ONLY_RE = re.compile(
    rf"(?P<restoration_value>\d+(?:\.\d+)?)\s*(?P<restoration_unit>{_TIME_UNIT})\s*(?:restoration|resolution)"
    rf"|(?:restoration|resolution)\s*(?:time)?\s*(?:of\s*)?[:\-]?\s*(?P<restoration_value2>\d+(?:\.\d+)?)\s*(?P<restoration_unit2>{_TIME_UNIT})",
    re.I,
)

_BUSINESS_DAY_HOURS_DEFINITION_RE = re.compile(
    r"business\s+day\s+shall\s+(?:be\s+deemed\s+to\s+)?consist(?:s)?\s+of\s+(\d+(?:\.\d+)?)\s*(?:\(\d+\)\s*)?business\s+hours", re.I,
)

# --- Support hours / channels -------------------------------------------------------------------
_SUPPORT_24X7_RE = re.compile(r"24\s*[x×/]\s*7|twenty[- ]four\s+hours?[,\s]+seven\s+days|around[- ]the[- ]clock", re.I)
_SUPPORT_BUSINESS_HOURS_RE = re.compile(r"business[\s-]hours?[\s-](?:support|only)|support\s+(?:is\s+)?(?:available\s+)?(?:during\s+)?business[\s-]hours?", re.I)

# --- Remedy mechanics ----------------------------------------------------------------------------
_CREDIT_ANCHOR_RE = re.compile(r"service\s+credit|credits?\s+(?:equal\s+to|of)|\bcredits?\b", re.I)
_CREDIT_PERCENT_WITH_BASIS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*of\s+(?:the\s+)?(monthly|total|annual|quarterly)\s+fees?", re.I,
)
_CREDIT_PERCENT_BARE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%", re.I)
_CREDIT_TRIGGER_RE = re.compile(r"if\s+(?:the\s+)?(?:availability|uptime)\s+falls?\s+below|failure\s+to\s+meet\s+(?:the\s+)?(?:applicable\s+)?service\s+level", re.I)
_CREDIT_CAP_RE = re.compile(
    r"(?:capped\s+at|not\s+to\s+exceed|maximum\s+(?:aggregate\s+)?credit(?:s)?\s+(?:of|shall\s+not\s+exceed))\s*(\d+(?:\.\d+)?)\s*%", re.I,
)
_CUMULATIVE_CREDIT_RE = re.compile(
    r"(?:first|second|third|subsequent)\s+(?:breach|failure|occurrence)|cumulative\s+credits?|escalat\w*\s+credit", re.I,
)
_CLAIM_DEADLINE_RE = re.compile(
    r"(?:claim|request)\s+(?:for\s+(?:a\s+)?(?:service\s+)?credit\s+)?(?:must\s+be\s+)?submitted\s+within\s+(\d{1,3})\s+days"
    r"|within\s+(\d{1,3})\s+days\s+of\s+(?:the\s+)?(?:qualifying\s+)?(?:event|incident|breach)", re.I,
)
_CHRONIC_FAILURE_RE = re.compile(
    r"chronic\s+(?:failure|breach)|repeated\s+(?:failure|breach)"
    r"|three\s+(?:or\s+more\s+)?(?:consecutive\s+)?(?:months?|breaches?|failures?)", re.I,
)
_SLA_TERMINATION_RIGHT_RE = re.compile(
    r"(?:right\s+to\s+terminate|may\s+terminate|shall\s+have\s+the\s+right\s+to\s+terminate)[^.]{0,200}?chronic"
    r"|chronic[^.]{0,200}?(?:right\s+to\s+terminate|may\s+terminate)"
    r"|terminate\s+this\s+Agreement[^.]{0,150}?(?:repeated|chronic)\s+(?:failure|breach)", re.I,
)
_SLA_EXCLUSIVE_REMEDY_RE = re.compile(
    r"sole\s+and\s+exclusive\s+remedy|exclusive\s+remedy\s+(?:for|of)"
    r"|(?:customer|client)'?s?\s+sole\s+(?:and\s+exclusive\s+)?remedy", re.I,
)

_SCHEDULE_CROSSREF_RE = re.compile(
    r"as\s+(?:set\s+forth|described|specified)\s+in\s+(?:the\s+)?(?:applicable\s+)?"
    r"(?:Service\s+Level\s+)?(?:Schedule|Exhibit|SLA\s+Exhibit|Statement\s+of\s+Work|SOW)"
    r"|service\s+levels?\s+(?:set\s+forth|specified)\s+in\s+(?:the\s+)?(?:applicable\s+)?(?:Schedule|Exhibit)", re.I,
)


def _basis_from_unit(unit: str) -> str:
    return "business" if "business" in unit.lower() else "calendar"


def _to_hours(value: float, unit: str, basis: str) -> Tuple[Optional[float], bool]:
    """Returns (hours, unconvertible). Only pure-arithmetic conversions are
    ever performed (minutes -> hours, CALENDAR days -> calendar hours); a
    business day is never converted to business hours without an explicit,
    contract-stated ratio (applied by the caller, not here) -- see module
    docstring."""
    unit = unit.lower()
    if "minute" in unit or "min" in unit:
        return value / 60.0, False
    if "hour" in unit or "hr" in unit:
        return value, False
    if "day" in unit:
        if basis == "calendar":
            return value * 24.0, False
        return None, True  # business day, no safe conversion
    return None, True


@dataclass
class SeverityTarget:
    canonical_level: str
    raw_label: str
    response_hours: Optional[float] = None
    response_basis: str = "not_stated"
    response_unconvertible: bool = False
    restoration_hours: Optional[float] = None
    restoration_basis: str = "not_stated"
    restoration_unconvertible: bool = False
    raw_excerpt: str = ""
    start_index: int = 0
    end_index: int = 0


@dataclass
class SLAFacts:
    clause_found: bool
    raw_excerpt: str = ""
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    section_label: Optional[str] = None

    # Availability
    uptime_percent: Optional[float] = None
    uptime_conflict: bool = False
    measurement_period: Optional[str] = None
    measurement_period_conflict: bool = False
    scheduled_maintenance_excluded: Optional[bool] = None
    emergency_maintenance_excluded: Optional[bool] = None
    customer_caused_excluded: Optional[bool] = None
    force_majeure_excluded: Optional[bool] = None
    measurement_methodology_stated: Optional[bool] = None

    # Severity
    severity_targets: Dict[str, SeverityTarget] = field(default_factory=dict)
    severity_ambiguous_labels: List[str] = field(default_factory=list)
    severity_response_conflict_levels: List[str] = field(default_factory=list)
    severity_restoration_conflict_levels: List[str] = field(default_factory=list)
    business_day_hours_definition: Optional[float] = None

    required_support_hours: Optional[str] = None
    required_support_hours_conflict: bool = False

    # Remedy
    service_credit_present: Optional[bool] = None
    credit_trigger_present: Optional[bool] = None
    credit_percent: Optional[float] = None
    credit_percent_conflict: bool = False
    credit_basis: Optional[str] = None
    credit_cap_percent: Optional[float] = None
    credit_cap_conflict: bool = False
    cumulative_credit_schedule_present: Optional[bool] = None
    claim_deadline_days: Optional[float] = None
    claim_deadline_conflict: bool = False
    chronic_failure_present: Optional[bool] = None
    termination_right_present: Optional[bool] = None
    exclusive_remedy_present: Optional[bool] = None

    schedule_cross_reference: bool = False

    # Fact-admission architecture — mirrors warranties_policy_engine.
    # WarrantiesFacts.absence_state. This adapter's "anchor fired but
    # nothing structured" gate also returns None/NOT_APPLICABLE (see
    # `if not found_anything: return None`), so RECOGNITION_UNCERTAIN on
    # the NO-anchor path needs its own explicit branch in
    # evaluate_sla_policy.
    absence_state: str = "CONFIRMED_ABSENT"
    semantic_discovery_error: Optional[str] = None
    ai_identified_condition: Optional[str] = None
    ai_identified_exception: Optional[str] = None
    ai_identified_definition_or_reference: Optional[str] = None


class SLAPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]

    require_uptime_commitment: bool
    preferred_uptime_percent: Optional[float]
    minimum_acceptable_uptime_percent: Optional[float]
    permitted_maintenance_exclusions_json: Optional[List[str]]

    require_severity_tiers: bool
    p1_max_response_hours: Optional[float]
    p1_response_basis: Optional[str]
    p1_max_restoration_hours: Optional[float]
    p1_restoration_basis: Optional[str]
    p2_max_response_hours: Optional[float]
    p2_response_basis: Optional[str]
    p2_max_restoration_hours: Optional[float]
    p2_restoration_basis: Optional[str]
    p3_max_response_hours: Optional[float]
    p3_response_basis: Optional[str]
    p3_max_restoration_hours: Optional[float]
    p3_restoration_basis: Optional[str]
    p4_max_response_hours: Optional[float]
    p4_response_basis: Optional[str]
    p4_max_restoration_hours: Optional[float]
    p4_restoration_basis: Optional[str]

    required_support_hours: Optional[str]

    require_service_credits: bool
    minimum_credit_percent_of_fees: Optional[float]
    minimum_credit_cap_percent_of_fees: Optional[float]
    require_chronic_failure_remedy: bool
    require_termination_right_for_chronic_failure: bool
    prohibit_service_credits_as_exclusive_remedy: bool
    minimum_claim_submission_days: Optional[float]


_SEVERITY_POLICY_FIELD_MAP = {
    "P1_CRITICAL": ("p1_max_response_hours", "p1_response_basis", "p1_max_restoration_hours", "p1_restoration_basis"),
    "P2_HIGH": ("p2_max_response_hours", "p2_response_basis", "p2_max_restoration_hours", "p2_restoration_basis"),
    "P3_MEDIUM": ("p3_max_response_hours", "p3_response_basis", "p3_max_restoration_hours", "p3_restoration_basis"),
    "P4_LOW": ("p4_max_response_hours", "p4_response_basis", "p4_max_restoration_hours", "p4_restoration_basis"),
}


# Off by default — same rollout discipline as every other adapter this
# session integrated.
SLA_SEMANTIC_DISCOVERY_ENABLED = False  # module-load-time default; immediately overridden below
import fact_admission as _fact_admission_env_check
SLA_SEMANTIC_DISCOVERY_ENABLED = _fact_admission_env_check.semantic_discovery_enabled("SLA_SEMANTIC_DISCOVERY_ENABLED")
del _fact_admission_env_check

_SLA_SEMANTIC_FOCUS = (
    "a service-level commitment -- an uptime/availability target, a severity-based response "
    "or restoration time, or a service-credit remedy for failing to meet a commitment -- even "
    "if the wording is unusual and does not use standard terms like 'SLA' or 'uptime'"
)
_SLA_SEMANTIC_PROPOSITION = (
    "This sentence or clause is operative language of this agreement that establishes a "
    "service-level commitment (an availability target, a response/restoration time "
    "commitment, or a service-credit remedy)."
)


def _run_semantic_discovery(text: str) -> Tuple[List, Optional[str], Optional[str]]:
    """Mirrors liability_policy_engine._run_semantic_discovery exactly.
    Returns (admitted_candidates, unresolved_dependency_note, error)."""
    if not SLA_SEMANTIC_DISCOVERY_ENABLED:
        return [], None, None
    import fact_admission as _fa
    try:
        raw_candidates = _fa.discover_candidate_spans(text, "sla", _SLA_SEMANTIC_FOCUS)
    except Exception as exc:  # noqa: BLE001 — provider unavailable, never "confirmed absent"
        return [], None, f"{type(exc).__name__}: {exc}"

    verified_candidates = [
        _fa.verify_and_ground(candidate, text, _SLA_SEMANTIC_PROPOSITION) for candidate in raw_candidates
    ]
    admitted = [c for c in verified_candidates if c.admission_status == _fa.ADMITTED]
    unresolved_dependency_note = _fa.first_unresolved_dependency_note(verified_candidates)
    return admitted, unresolved_dependency_note, None


def extract_sla_facts(text: str) -> Optional[SLAFacts]:
    anchors = list(_ANCHOR_RE.finditer(text))
    semantic_error: Optional[str] = None
    admitted_semantic: List = []
    unresolved_dependency_note: Optional[str] = None
    # Candidate 3 remediation (Root Cause 2): contextual discovery is no
    # longer gated behind "deterministic anchor discovery found zero
    # matches" -- see confidentiality_policy_engine.py's identical fix.
    admitted_semantic, unresolved_dependency_note, semantic_error = _run_semantic_discovery(text)
    if not anchors:
        if semantic_error is not None:
            return SLAFacts(clause_found=True, absence_state="RECOGNITION_UNCERTAIN", semantic_discovery_error=semantic_error)
        if not admitted_semantic and not unresolved_dependency_note:
            return None
        if not admitted_semantic:
            # See warranties_policy_engine.py's identical fix: a genuine
            # candidate was found (competing readings, or an unresolved
            # definition/cross-reference) but never resolved to something
            # admissible -- never the same as "nothing here at all."
            return SLAFacts(clause_found=True, ai_identified_definition_or_reference=unresolved_dependency_note)
    elif semantic_error is not None:
        admitted_semantic = []

    anchor_spans = sorted(
        [(m.start(), m.end()) for m in anchors] + [(c.start_offset, c.end_offset) for c in admitted_semantic]
    )
    windows: List[Tuple[int, int]] = []
    for (m_start, m_end) in anchor_spans:
        s = max(0, m_start - 200)
        e = min(len(text), m_end + _PROVISION_WINDOW_CHARS)
        if windows and s - windows[-1][1] < 200:
            windows[-1] = (windows[-1][0], max(windows[-1][1], e))
        else:
            windows.append((s, e))

    first_start, first_end = anchor_spans[0]
    start_index = max(0, first_start - 200)
    end_index = min(len(text), first_end + 400)
    raw_excerpt = _excerpt(text, start_index, end_index)
    section_label = _section_label_before(text, first_start)

    facts = SLAFacts(clause_found=True, raw_excerpt=raw_excerpt, start_index=start_index,
                      end_index=end_index, section_label=section_label)

    found_anything = False
    uptime_values: Set[float] = set()
    period_values: Set[str] = set()
    response_values: Dict[str, Set[Tuple[Optional[float], str, bool]]] = {lvl: set() for lvl in SEVERITY_LEVELS}
    restoration_values: Dict[str, Set[Tuple[Optional[float], str, bool]]] = {lvl: set() for lvl in SEVERITY_LEVELS}
    raw_labels: Dict[str, str] = {}
    excerpts: Dict[str, Tuple[str, int, int]] = {}
    support_hours_tokens: Set[str] = set()
    credit_percent_values: Set[Tuple[float, Optional[str]]] = set()
    credit_cap_values: Set[float] = set()
    claim_deadline_values: Set[float] = set()

    for (ws, we) in windows:
        window = text[ws:we]

        # --- Availability ---------------------------------------------------------------------
        for m in _UPTIME_WITH_PERCENT_RE.finditer(window):
            if _UPTIME_NEGATION_RE.search(window[max(0, m.start() - 20):m.start() + 20]):
                continue
            # Root-cause fix (Candidate 2, false-operative -> clean): the
            # SAME shared-primitive gap found in insurance_policy_engine
            # -- a percentage figure inside descriptive/background prose
            # ("SaaS agreements typically commit to 99.9% uptime ...
            # although the parties have not yet negotiated specific
            # service levels") was previously admitted as this
            # Agreement's own established commitment. Reuses the shared
            # is_operative_context primitive (now covering this
            # industry-norm-plus-not-yet-agreed pattern at the source),
            # not an adapter-local blacklist.
            if not _core_is_operative_context(text, ws + m.start(), ws + m.end()):
                continue
            raw = m.group(1) or m.group(2)
            if raw:
                uptime_values.add(float(raw))
                found_anything = True

        for m in _MEASUREMENT_PERIOD_RE.finditer(window):
            # Candidate 3 final gap-closure fix (Root Cause A, sla-202):
            # this match was never gated by is_operative_context at all --
            # a hypothetical/illustrative sentence ("if a vendor committed
            # to an SLA, ... with monthly measurement would be typical")
            # could still establish a real measurement-period fact via
            # THIS regex even after the uptime-percent match immediately
            # above was correctly suppressed, letting the decision reach a
            # clean ACCEPT anyway. Same shared primitive, same gate.
            if not _core_is_operative_context(text, ws + m.start(), ws + m.end()):
                continue
            token = m.group(1).lower()
            normalized = _MEASUREMENT_PERIOD_NORMALIZE.get(token)
            if normalized:
                period_values.add(normalized)
                found_anything = True

        if _SCHEDULED_MAINT_RE.search(window):
            facts.scheduled_maintenance_excluded = True
            found_anything = True
        if _EMERGENCY_MAINT_RE.search(window):
            facts.emergency_maintenance_excluded = True
            found_anything = True
        if _CUSTOMER_CAUSED_RE.search(window):
            facts.customer_caused_excluded = True
            found_anything = True
        if _FORCE_MAJEURE_RE.search(window):
            facts.force_majeure_excluded = True
            found_anything = True
        if _METHODOLOGY_RE.search(window):
            facts.measurement_methodology_stated = True
            found_anything = True

        # --- Severity: table rows first (most disambiguated form) -----------------------------
        covered_spans: List[Tuple[int, int]] = []
        for m in _TABLE_ROW_RE.finditer(window):
            level = _normalize_severity_label(m.group("level"))
            covered_spans.append((m.start(), m.end()))
            if level is None:
                facts.severity_ambiguous_labels.append(m.group("level"))
                found_anything = True
                continue
            raw_labels.setdefault(level, m.group("level"))
            excerpts.setdefault(level, (_excerpt(window, m.start(), m.end()), ws + m.start(), ws + m.end()))
            rbasis = _basis_from_unit(m.group("response_unit"))
            rhours, runconv = _to_hours(float(m.group("response_value")), m.group("response_unit"), rbasis)
            response_values[level].add((rhours, rbasis, runconv))
            sbasis = _basis_from_unit(m.group("restoration_unit"))
            shours, sunconv = _to_hours(float(m.group("restoration_value")), m.group("restoration_unit"), sbasis)
            restoration_values[level].add((shours, sbasis, sunconv))
            found_anything = True

        # --- Severity: declared/bare-P label anchors, prose form -------------------------------
        label_matches = [(m.start(), m.end(), m.group(1)) for m in _SEVERITY_DECLARED_RE.finditer(window)]
        label_matches += [(m.start(), m.end(), m.group(1)) for m in _SEVERITY_BARE_P_RE.finditer(window)]
        label_matches += [(m.start(), m.start() + len(m.group(1)), m.group(1)) for m in _SEVERITY_BARE_WORD_RE.finditer(window)]
        for (ls, le, raw_tok) in label_matches:
            if any(cs <= ls < ce for (cs, ce) in covered_spans):
                continue
            level = _normalize_severity_label(raw_tok)
            local = _local_window(window, le, [])

            combined = _COMBINED_TRAILING_LABEL_RE.search(local) or _COMBINED_LEADING_LABEL_RE.search(local)
            if combined:
                if level is None:
                    facts.severity_ambiguous_labels.append(raw_tok)
                    found_anything = True
                    continue
                raw_labels.setdefault(level, raw_tok)
                excerpts.setdefault(level, (_excerpt(window, ls, le + len(local)), ws + ls, ws + le + len(local)))
                rbasis = _basis_from_unit(combined.group("response_unit"))
                rhours, runconv = _to_hours(float(combined.group("response_value")), combined.group("response_unit"), rbasis)
                response_values[level].add((rhours, rbasis, runconv))
                sbasis = _basis_from_unit(combined.group("restoration_unit"))
                shours, sunconv = _to_hours(float(combined.group("restoration_value")), combined.group("restoration_unit"), sbasis)
                restoration_values[level].add((shours, sbasis, sunconv))
                found_anything = True
                continue

            resp = _RESPONSE_ONLY_RE.search(local)
            rest = _RESTORATION_ONLY_RE.search(local)
            if resp or rest:
                if level is None:
                    facts.severity_ambiguous_labels.append(raw_tok)
                    found_anything = True
                    continue
                raw_labels.setdefault(level, raw_tok)
                excerpts.setdefault(level, (_excerpt(window, ls, le + len(local)), ws + ls, ws + le + len(local)))
                if resp:
                    rv = resp.group("response_value") or resp.group("response_value2")
                    ru = resp.group("response_unit") or resp.group("response_unit2")
                    rbasis = _basis_from_unit(ru)
                    rhours, runconv = _to_hours(float(rv), ru, rbasis)
                    response_values[level].add((rhours, rbasis, runconv))
                    found_anything = True
                if rest:
                    sv = rest.group("restoration_value") or rest.group("restoration_value2")
                    su = rest.group("restoration_unit") or rest.group("restoration_unit2")
                    sbasis = _basis_from_unit(su)
                    shours, sunconv = _to_hours(float(sv), su, sbasis)
                    restoration_values[level].add((shours, sbasis, sunconv))
                    found_anything = True

        dm = _BUSINESS_DAY_HOURS_DEFINITION_RE.search(window)
        if dm:
            facts.business_day_hours_definition = float(dm.group(1))
            found_anything = True

        # --- Support hours ----------------------------------------------------------------------
        if _SUPPORT_24X7_RE.search(window):
            support_hours_tokens.add("24x7")
            found_anything = True
        if _SUPPORT_BUSINESS_HOURS_RE.search(window):
            support_hours_tokens.add("business_hours")
            found_anything = True

        # --- Remedy -------------------------------------------------------------------------------
        for m in _CREDIT_ANCHOR_RE.finditer(window):
            if re.search(r"\bno\s+(?:service\s+)?$", window[max(0, m.start() - 25):m.start()], re.I):
                continue
            if not _core_is_operative_context(text, ws + m.start(), ws + m.end()):
                continue
            facts.service_credit_present = True
            found_anything = True
            local = _local_window(window, m.end(), [])
            wb = _CREDIT_PERCENT_WITH_BASIS_RE.search(local)
            if wb:
                credit_percent_values.add((float(wb.group(1)), wb.group(2).lower()))
            else:
                bare = _CREDIT_PERCENT_BARE_RE.search(local)
                if bare:
                    credit_percent_values.add((float(bare.group(1)), None))

        if _CREDIT_TRIGGER_RE.search(window):
            facts.credit_trigger_present = True
            found_anything = True

        for m in _CREDIT_CAP_RE.finditer(window):
            credit_cap_values.add(float(m.group(1)))
            found_anything = True

        if _CUMULATIVE_CREDIT_RE.search(window):
            facts.cumulative_credit_schedule_present = True
            found_anything = True

        for m in _CLAIM_DEADLINE_RE.finditer(window):
            val = m.group(1) or m.group(2)
            if val:
                claim_deadline_values.add(float(val))
                found_anything = True

        if _CHRONIC_FAILURE_RE.search(window):
            facts.chronic_failure_present = True
            found_anything = True
        if _SLA_TERMINATION_RIGHT_RE.search(window):
            facts.termination_right_present = True
            found_anything = True
        if _SLA_EXCLUSIVE_REMEDY_RE.search(window):
            facts.exclusive_remedy_present = True
            found_anything = True
        if _SCHEDULE_CROSSREF_RE.search(window):
            facts.schedule_cross_reference = True
            found_anything = True

    # --- Resolve accumulated values --------------------------------------------------------------
    if len(uptime_values) == 1:
        facts.uptime_percent = next(iter(uptime_values))
    elif len(uptime_values) > 1:
        facts.uptime_conflict = True

    if len(period_values) == 1:
        facts.measurement_period = next(iter(period_values))
    elif len(period_values) > 1:
        facts.measurement_period_conflict = True

    for level in SEVERITY_LEVELS:
        rvals = response_values[level]
        svals = restoration_values[level]
        if not rvals and not svals:
            continue
        target = SeverityTarget(
            canonical_level=level, raw_label=raw_labels.get(level, level),
            raw_excerpt=excerpts.get(level, ("", 0, 0))[0],
            start_index=excerpts.get(level, ("", 0, 0))[1],
            end_index=excerpts.get(level, ("", 0, 0))[2],
        )
        if len(rvals) == 1:
            hours, basis, unconv = next(iter(rvals))
            target.response_hours, target.response_basis, target.response_unconvertible = hours, basis, unconv
        elif len(rvals) > 1:
            facts.severity_response_conflict_levels.append(level)
        if len(svals) == 1:
            hours, basis, unconv = next(iter(svals))
            target.restoration_hours, target.restoration_basis, target.restoration_unconvertible = hours, basis, unconv
        elif len(svals) > 1:
            facts.severity_restoration_conflict_levels.append(level)
        facts.severity_targets[level] = target

    if len(support_hours_tokens) == 1:
        facts.required_support_hours = next(iter(support_hours_tokens))
    elif len(support_hours_tokens) > 1:
        facts.required_support_hours_conflict = True

    if len(credit_percent_values) == 1:
        pct, basis = next(iter(credit_percent_values))
        facts.credit_percent = pct
        facts.credit_basis = basis
    elif len(credit_percent_values) > 1:
        facts.credit_percent_conflict = True

    if len(credit_cap_values) == 1:
        facts.credit_cap_percent = next(iter(credit_cap_values))
    elif len(credit_cap_values) > 1:
        facts.credit_cap_conflict = True

    if len(claim_deadline_values) == 1:
        facts.claim_deadline_days = next(iter(claim_deadline_values))
    elif len(claim_deadline_values) > 1:
        facts.claim_deadline_conflict = True

    if not found_anything:
        # Candidate 3 remediation (Root Cause 1): an admitted AI candidate
        # exists but no SLA dimension could be deterministically
        # structured from it -- never silently discard as "nothing here
        # at all" (see warranties_policy_engine.py's identical fix).
        if admitted_semantic:
            facts.absence_state = "PRESENT_BUT_UNRESOLVED"
            import fact_admission as _fa
            for candidate in admitted_semantic:
                facts.ai_identified_condition = facts.ai_identified_condition or candidate.condition
                facts.ai_identified_exception = facts.ai_identified_exception or candidate.exception
            facts.ai_identified_definition_or_reference = _fa.first_resolved_dependency_note(admitted_semantic)
            return facts
        return None

    # Final trust architecture (Phase 5/6) — reached only when
    # found_anything is True (the base SLA structure DID resolve
    # deterministically, so this candidate already passed the negative-
    # control gate above). See confidentiality_policy_engine.py's
    # identical composition for the full rationale.
    import fact_admission as _fa
    for candidate in admitted_semantic:
        facts.ai_identified_condition = facts.ai_identified_condition or candidate.condition
        facts.ai_identified_exception = facts.ai_identified_exception or candidate.exception
    facts.ai_identified_definition_or_reference = _fa.first_resolved_dependency_note(admitted_semantic)

    return facts


def _build_ladder(policy: SLAPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", "Required availability, severity targets, and service credits all established at or better than policy"),
        ("ACCEPTABLE", "Auto-accept within acceptable SLA terms"),
        ("FALLBACK", "Negotiate SLA terms within fallback range"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Prohibited SLA terms"),
    ]
    return _core_build_ladder(state, step_specs)


def evaluate_sla_policy(
    facts: Optional[SLAFacts],
    policy: SLAPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    if facts is None or not facts.clause_found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="sla", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No SLA/service-level clause found",
            policy_limit_summary="N/A",
            required_action="None — this contract does not address service levels",
            explanation="No SLA/service-level clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="SLA treatment",
            our_position_label="Our SLA commitments", counterparty_position_label="Counterparty's SLA commitments",
            interaction_facts={"service_credit_present": None},
        )

    if facts.absence_state == "RECOGNITION_UNCERTAIN":
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="sla", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Could not determine whether an SLA/service-level clause is present",
            policy_limit_summary="N/A",
            required_action="Manual review required — automated recognition was unavailable for this document.",
            explanation=(
                "Deterministic pattern matching found no SLA/service-level clause, and semantic "
                f"verification could not confirm its absence ({facts.semantic_discovery_error or 'unavailable'}). "
                "This is not the same as confirming the contract has no such clause."
            ),
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="SLA treatment",
            our_position_label="Our SLA commitments", counterparty_position_label="Counterparty's SLA commitments",
            interaction_facts={"service_credit_present": None},
        )

    if facts.absence_state == "PRESENT_BUT_UNRESOLVED":
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="sla", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="An SLA-relevant clause was found and verified, but no specific service-level dimension could be structured from it",
            policy_limit_summary="N/A",
            required_action="Manual review required — a candidate clause was discovered and verified but could not be deterministically structured into a specific SLA term.",
            explanation=(
                "Contextual discovery identified and verified SLA-relevant language in this contract, but "
                "deterministic extraction could not structure it into a specific uptime/response/credit term. "
                "This is not the same as confirming no SLA provision exists, and must not be treated as a clean "
                "result."
            ),
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="SLA treatment",
            our_position_label="Our SLA commitments", counterparty_position_label="Counterparty's SLA commitments",
            interaction_facts={"service_credit_present": None},
        )

    unresolved_facts: List[str] = []

    # Final trust architecture (Phase 4 hard gate) — a material condition/
    # exception the AI/context layer identified and grounded must not be
    # silently dropped merely because the SLA otherwise resolved cleanly.
    if facts.ai_identified_condition:
        unresolved_facts.append(
            f"a material condition was identified by contextual analysis and grounded against the source "
            f"document (\"{facts.ai_identified_condition}\")"
        )
    if facts.ai_identified_exception:
        unresolved_facts.append(
            f"a material exception was identified by contextual analysis and grounded against the source "
            f"document (\"{facts.ai_identified_exception}\")"
        )
    if facts.ai_identified_definition_or_reference:
        unresolved_facts.append(
            f"a material definition/cross-reference dependency was identified by contextual analysis "
            f"({facts.ai_identified_definition_or_reference})"
        )

    if facts.uptime_conflict:
        unresolved_facts.append("multiple, conflicting uptime/availability percentages stated")
    if facts.measurement_period_conflict:
        unresolved_facts.append("multiple, conflicting measurement periods stated")
    if facts.severity_ambiguous_labels:
        unresolved_facts.append(
            "one or more severity labels could not be safely normalized to P1-P4 ("
            + ", ".join(sorted(set(facts.severity_ambiguous_labels))) + ")"
        )
    if facts.severity_response_conflict_levels:
        unresolved_facts.append(
            "conflicting response-time values for: " + ", ".join(sorted(set(facts.severity_response_conflict_levels)))
        )
    if facts.severity_restoration_conflict_levels:
        unresolved_facts.append(
            "conflicting restoration-time values for: " + ", ".join(sorted(set(facts.severity_restoration_conflict_levels)))
        )
    if facts.required_support_hours_conflict:
        unresolved_facts.append("conflicting support-hours commitments stated (both 24x7 and business-hours-only)")
    if facts.credit_percent_conflict:
        unresolved_facts.append("conflicting service-credit percentages stated")
    if facts.credit_cap_conflict:
        unresolved_facts.append("conflicting service-credit caps stated")
    if facts.claim_deadline_conflict:
        unresolved_facts.append("conflicting claim-submission deadlines stated")
    for level, (resp_field, resp_basis_field, rest_field, rest_basis_field) in _SEVERITY_POLICY_FIELD_MAP.items():
        target = facts.severity_targets.get(level)
        if target is None:
            continue
        max_response = getattr(policy, resp_field)
        response_basis_policy = getattr(policy, resp_basis_field)
        max_restoration = getattr(policy, rest_field)
        restoration_basis_policy = getattr(policy, rest_basis_field)

        if max_response is not None:
            if target.response_unconvertible:
                unresolved_facts.append(f"{level} response time stated in business days with no contract-defined conversion to hours — cannot be compared to a configured policy ceiling")
            elif target.response_hours is not None and response_basis_policy is not None and target.response_basis != response_basis_policy:
                unresolved_facts.append(f"{level} response time is stated in {target.response_basis} hours, but policy's ceiling is configured in {response_basis_policy} hours — cross-basis comparison must abstain")

        if max_restoration is not None:
            if target.restoration_unconvertible:
                unresolved_facts.append(f"{level} restoration time stated in business days with no contract-defined conversion to hours — cannot be compared to a configured policy ceiling")
            elif target.restoration_hours is not None and restoration_basis_policy is not None and target.restoration_basis != restoration_basis_policy:
                unresolved_facts.append(f"{level} restoration time is stated in {target.restoration_basis} hours, but policy's ceiling is configured in {restoration_basis_policy} hours — cross-basis comparison must abstain")

    if unresolved_facts:
        explanation = requires_review_explanation("SLA structure", facts.raw_excerpt, unresolved_facts)
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="sla", state=REQUIRES_REVIEW,
            contract_language=facts.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary="N/A",
            required_action=requires_review_required_action(unresolved_facts),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved_facts,
            start_index=facts.start_index, end_index=facts.end_index, source=source,
            controlling_provision={"label": f"Section {facts.section_label} — SLA" if facts.section_label else "SLA",
                                    "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
            summary_label="SLA treatment", our_position_label="Our SLA commitments",
            counterparty_position_label="Counterparty's SLA commitments",
            interaction_facts={"service_credit_present": facts.service_credit_present},
        )

    notes: List[str] = []
    worst_state = ACCEPT

    def _worse(a: str, b: str) -> str:
        order = [ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, ESCALATE, PROHIBITED]
        return a if order.index(a) >= order.index(b) else b

    def _note(text: str, state: str) -> None:
        nonlocal worst_state
        notes.append(text)
        worst_state = _worse(worst_state, state)

    # --- Availability (floor: higher stated uptime is stronger) ---------------------------------
    if policy.require_uptime_commitment and facts.uptime_percent is None:
        _note("policy requires an uptime/availability commitment, but none was found", NEGOTIATE)
    if policy.minimum_acceptable_uptime_percent is not None:
        if facts.uptime_percent is None:
            _note("policy configures a minimum acceptable uptime, but no uptime commitment was stated", NEGOTIATE)
        elif facts.uptime_percent < policy.minimum_acceptable_uptime_percent:
            _note(f"stated uptime of {facts.uptime_percent:g}% is below the policy's minimum of {policy.minimum_acceptable_uptime_percent:g}%", NEGOTIATE)

    if policy.permitted_maintenance_exclusions_json is not None:
        present = {
            "scheduled_maintenance": facts.scheduled_maintenance_excluded,
            "emergency_maintenance": facts.emergency_maintenance_excluded,
            "customer_caused": facts.customer_caused_excluded,
            "force_majeure": facts.force_majeure_excluded,
        }
        for token, is_present in present.items():
            if is_present and token not in policy.permitted_maintenance_exclusions_json:
                _note(f"the contract excludes {token.replace('_', ' ')} from the availability commitment, which is not in policy's list of permitted exclusions", NEGOTIATE)

    # --- Severity targets (ceilings: lower stated hours is stronger) ----------------------------
    if policy.require_severity_tiers and not facts.severity_targets:
        _note("policy requires severity-tiered response/restoration commitments, but none were found", NEGOTIATE)

    for level, (resp_field, resp_basis_field, rest_field, rest_basis_field) in _SEVERITY_POLICY_FIELD_MAP.items():
        max_response = getattr(policy, resp_field)
        response_basis_policy = getattr(policy, resp_basis_field)
        max_restoration = getattr(policy, rest_field)
        restoration_basis_policy = getattr(policy, rest_basis_field)
        target = facts.severity_targets.get(level)

        # Basis mismatches and unconvertible business-day values were
        # already checked above (before the unresolved_facts gate) and
        # would have routed to REQUIRES_REVIEW before reaching this
        # point -- by construction, any target.response_hours/
        # restoration_hours surviving to here is either basis-agnostic
        # (no policy basis configured) or already basis-matched.
        if max_response is not None:
            if target is None or target.response_hours is None:
                _note(f"policy configures a maximum {level} response time, but no {level} response commitment was found", NEGOTIATE)
            elif target.response_hours > max_response:
                _note(f"{level} response time of {target.response_hours:g} hours exceeds the policy's maximum of {max_response:g} hours", NEGOTIATE)

        if max_restoration is not None:
            if target is None or target.restoration_hours is None:
                _note(f"policy configures a maximum {level} restoration time, but no {level} restoration commitment was found", NEGOTIATE)
            elif target.restoration_hours > max_restoration:
                _note(f"{level} restoration time of {target.restoration_hours:g} hours exceeds the policy's maximum of {max_restoration:g} hours", NEGOTIATE)

    if policy.required_support_hours is not None and facts.required_support_hours != policy.required_support_hours:
        _note(f"required support hours ({policy.required_support_hours}) not confirmed — contract states {facts.required_support_hours or 'no support-hours commitment'}", NEGOTIATE)

    # --- Remedy mechanics -------------------------------------------------------------------------
    if policy.require_service_credits and not facts.service_credit_present:
        _note("policy requires a service-credit remedy, but none was found", NEGOTIATE)

    if policy.minimum_credit_percent_of_fees is not None:
        if facts.credit_percent is None:
            _note("policy configures a minimum service-credit percentage, but no credit percentage was stated", NEGOTIATE)
        elif facts.credit_percent < policy.minimum_credit_percent_of_fees:
            _note(f"stated service-credit percentage of {facts.credit_percent:g}% is below the policy's minimum of {policy.minimum_credit_percent_of_fees:g}%", NEGOTIATE)

    if policy.minimum_credit_cap_percent_of_fees is not None:
        if facts.credit_cap_percent is None:
            _note("policy configures a minimum service-credit cap, but no cap was stated", NEGOTIATE)
        elif facts.credit_cap_percent < policy.minimum_credit_cap_percent_of_fees:
            _note(f"stated service-credit cap of {facts.credit_cap_percent:g}% is below the policy's minimum of {policy.minimum_credit_cap_percent_of_fees:g}%", NEGOTIATE)

    if policy.require_chronic_failure_remedy and not facts.chronic_failure_present:
        _note("policy requires a chronic/repeated-failure remedy, but none was found", NEGOTIATE)
    if policy.require_termination_right_for_chronic_failure and not facts.termination_right_present:
        _note("policy requires a termination right tied to chronic SLA failure, but none was found", NEGOTIATE)
    if policy.prohibit_service_credits_as_exclusive_remedy and facts.exclusive_remedy_present:
        _note("service credits are stated as the exclusive remedy for SLA breach, which policy prohibits", ESCALATE)
    if policy.minimum_claim_submission_days is not None:
        if facts.claim_deadline_days is None:
            _note("policy configures a minimum claim-submission window, but no claim-submission deadline was stated", NEGOTIATE)
        elif facts.claim_deadline_days < policy.minimum_claim_submission_days:
            _note(f"claim-submission deadline of {facts.claim_deadline_days:g} days is below the policy's minimum of {policy.minimum_claim_submission_days:g} days", NEGOTIATE)

    if facts.schedule_cross_reference and not facts.severity_targets and facts.uptime_percent is None:
        _note("SLA terms appear to be delegated to a referenced Schedule/Exhibit that could not be resolved from the contract text alone", ESCALATE)

    extracted_summary_parts = []
    if facts.uptime_percent is not None:
        extracted_summary_parts.append(f"uptime {facts.uptime_percent:g}%")
    for level in SEVERITY_LEVELS:
        t = facts.severity_targets.get(level)
        if t:
            extracted_summary_parts.append(
                f"{level}: response {t.response_hours if t.response_hours is not None else '?'}h/{t.response_basis}, "
                f"restoration {t.restoration_hours if t.restoration_hours is not None else '?'}h/{t.restoration_basis}"
            )
    extracted_summary = "; ".join(extracted_summary_parts) or "No availability/severity commitments established"

    required_action = "None — SLA terms meet policy" if worst_state == ACCEPT else (
        f"{'Escalate' if worst_state in (ESCALATE, PROHIBITED) else 'Negotiate'} — " + "; ".join(notes)
    )

    return PolicyDecision(
        rule_id=RULE_ID, clause_type="sla", state=worst_state,
        contract_language=facts.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary="; ".join(notes) if notes else "Meets policy",
        required_action=required_action,
        explanation=f"SLA commitments: {extracted_summary}. Result: {worst_state}."
                    + (" Notes: " + "; ".join(notes) if notes else ""),
        negotiation_ladder=_build_ladder(policy, worst_state),
        category_treatments=[
            {"category": level, "treatment": "established" if level in facts.severity_targets else "not_established",
             "raw_excerpt": facts.severity_targets[level].raw_excerpt if level in facts.severity_targets else "",
             "established": str(level in facts.severity_targets)}
            for level in SEVERITY_LEVELS
        ],
        unresolved_facts=[],
        start_index=facts.start_index, end_index=facts.end_index, source=source,
        controlling_provision={"label": f"Section {facts.section_label} — SLA" if facts.section_label else "SLA",
                                "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
        summary_label="SLA treatment", our_position_label="Our SLA commitments",
        counterparty_position_label="Counterparty's SLA commitments",
        interaction_facts={"service_credit_present": facts.service_credit_present},
    )
