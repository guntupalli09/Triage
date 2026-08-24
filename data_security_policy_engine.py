"""
Data Protection / Security clause adapter, over policy_engine_core.
Adapter #7 — the first added after the original six (Liability,
Indemnification, Termination, Confidentiality, Assignment, Governing
Law). Built by directly mirroring the established adapter shape (see
assignment_policy_engine.py / confidentiality_policy_engine.py) rather
than inventing a new one; policy_engine_core.py was not modified — every
primitive this adapter needs (PolicyDecision, LadderStep/build_ladder,
classify_by_threshold, escalate_to_for_state, fallback_text_for_state,
side_for_role, excerpt/section_label_before, requires_review_* helpers)
already existed and fit without change.

SEMANTIC MODEL: a data-protection/security clause is a CATALOG of
largely independent commercial dimensions, not one reciprocal promise —
unlike Confidentiality/Assignment/Termination, a vendor's processor
obligations toward a customer's personal data are not naturally
symmetric, so this adapter does NOT reuse the reciprocal-symmetry
detection machinery those three adapters share (detect_role_attributed_
asymmetry) — it would have nothing meaningful to compare. Each dimension
below is extracted independently and, if the fact is genuinely absent
from the text, is treated as "not addressed" (never guessed) — a
required policy dimension with no corresponding fact in the contract
downgrades the decision (the same "silence never satisfies a
requirement" rule Liability/Indemnification/Assignment already use for
required exceptions), it never manufactures an obligation the clause
doesn't state.

Dimensions modeled (see DataSecurityFacts): controller/processor role,
subprocessor treatment (unrestricted / notice / consent / prohibited),
breach-notification timing (fixed-hours or "without undue delay"),
international-transfer safeguard (SCC / adequacy / none stated /
prohibited), data residency, deletion-or-return vs. retention,
retention period, audit rights, security-standard specificity (named
certification vs. vague "industry standard"), cooperation obligations
(data-subject-request assistance and regulatory cooperation are modeled
as one combined dimension — see DataSecurityFacts.cooperation_obligation
docstring for why), and confidentiality-of-personal-data. Liability
treatment referenced from within this clause (e.g. "breach of this
Section is excluded from the liability cap") is captured as a plain
cross-reference note in unresolved_facts/category_treatments when
present — this adapter never re-evaluates the Limitation of Liability
clause itself; that stays liability_policy_engine's job exclusively.

classify_by_threshold IS reused for breach-notification hours (a
three-tier "preferred/acceptable/negotiate maximum hours" band is
exactly its shape — lower hours are more protective, same "lower is
better" direction as a liability multiplier) but is NOT forced onto any
other dimension here: role, subprocessor treatment, transfer mechanism,
residency, deletion/retention, audit rights, security-standard
specificity, and cooperation are each categorical/tristate, not
threshold bands, and are evaluated with adapter-local comparisons
instead.
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
    classify_by_threshold,
    escalate_to_for_state, fallback_text_for_state,
    excerpt as _excerpt, section_label_before as _section_label_before,
    requires_review_explanation, requires_review_required_action,
    word_number_alternation as _word_number_alternation, parse_multiplier_token as _parse_number_token,
    EXTERNAL_DEFINITION_NOT_ATTACHED_RE as _EXTERNAL_DEFINITION_NOT_ATTACHED_RE,
)

RULE_ID = "POLICY_DATA_SECURITY"

_PROVISION_WINDOW_CHARS = 2200

_ANCHOR_RE = re.compile(
    r"data\s+protection|personal\s+data|data\s+privacy|processing\s+of\s+(?:the\s+)?personal\s+data"
    r"|\bDPA\b|\bGDPR\b|\bCCPA\b|security\s+incident|data\s+security",
    re.I,
)

# --- Controller / processor role -------------------------------------------
_ROLE_STATEMENT_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,30}))\s+(?:is|shall\s+be|acts\s+as|will\s+act\s+as|shall\s+act\s+as)\s+(?:a|the)\s+"
    r"(?:data\s+)?(controller|processor)(?:\s+of\s+(?:the\s+)?personal\s+data)?",
    re.I,
)
_JOINT_CONTROLLER_RE = re.compile(r"joint\s+controllers?", re.I)
_ROLE_GENERIC_WORDS = {"each", "the", "any", "such", "this", "that", "both", "either", "party", "parties"}

# --- Subprocessors -----------------------------------------------------------
_SUBPROCESSOR_ANCHOR_RE = re.compile(r"sub-?processors?", re.I)
_SUBPROCESSOR_PROHIBIT_RE = re.compile(
    r"shall\s+not\s+(?:engage|use|appoint)\s+(?:any\s+)?sub-?processors?"
    r"|no\s+sub-?processors?\s+(?:shall|may|will)\s+be\s+(?:engaged|used|appointed)",
    re.I,
)
_SUBPROCESSOR_CONSENT_RE = re.compile(
    r"(?:prior\s+)?(?:written\s+)?consent\s+of\s+(?:the\s+)?(?:customer|controller|client)\s+"
    r"(?:is\s+required\s+)?(?:to|before|prior\s+to)\s+engag(?:e|ing)\s+(?:any\s+)?sub-?processors?"
    r"|shall\s+obtain\s+(?:the\s+)?(?:customer's\s+)?(?:prior\s+)?(?:written\s+)?consent\s+"
    r"(?:before|prior\s+to)\s+engaging\s+(?:any\s+)?sub-?processors?",
    re.I,
)
_SUBPROCESSOR_NOTICE_RE = re.compile(
    r"(?:shall|will)\s+(?:provide|give)\s+(?:prior\s+)?(?:written\s+)?notice\s+.{0,60}?sub-?processors?"
    r"|notify\s+(?:the\s+)?customer\s+.{0,60}?(?:prior\s+to\s+)?(?:engag(?:e|ing)|appointing)\s+(?:any\s+)?sub-?processors?",
    re.I,
)
_SUBPROCESSOR_UNRESTRICTED_RE = re.compile(
    r"may\s+engage\s+sub-?processors?\s+(?:at\s+its\s+(?:sole\s+)?discretion|without\s+(?:prior\s+)?(?:notice|consent)|freely)",
    re.I,
)

# --- Breach / security-incident notification --------------------------------
_BREACH_ANCHOR_RE = re.compile(r"security\s+incident|personal\s+data\s+breach|data\s+breach", re.I)
# A bare digit run OR a spelled-out number word (the shared, closed
# word-number vocabulary every duration/multiplier regex in this
# codebase already uses -- see policy_engine_core.WORD_NUMBERS) --
# "thirty days" must be recognized exactly like "30 days", not only the
# digit form, per Candidate 2's "prove the class, not the fixture"
# requirement.
_NUM = r"(?:\d{1,3}|" + _word_number_alternation() + r")"
_BREACH_HOURS_RE = re.compile(
    r"(?:notify|notification|notice)[^.]{0,80}?within\s+(" + _NUM + r")\s+hours"
    r"|within\s+(" + _NUM + r")\s+hours\s+(?:of|after)\s+(?:becoming\s+aware|discovery|discovering|learning)"
    r"|(?:no\s+(?:later|event\s+later)\s+than|not\s+later\s+than)\s+(" + _NUM + r")\s+hours\s+(?:after|of|following)"
    r"\s+(?:becoming\s+aware|discovery|discovering|learning)",
    re.I,
)
# Root-cause fix (Candidate 2, time normalization): calendar-day phrasing
# is CANONICALIZED to hours (days * 24) so it participates in the SAME
# comparable hour_values set _BREACH_HOURS_RE already populates -- a
# 30-day commitment must be comparable against a 72-hour policy maximum,
# not silently invisible to it. "business days" is a DIFFERENT, narrower
# pattern checked separately below and is deliberately never matched
# here (the literal word "business" between the digit and "days" means
# this pattern's `(?:calendar\s+)?days` alternative never lines up), and
# is never converted to hours -- a business day's wall-clock length is
# not well-defined enough to canonicalize without manufacturing false
# precision (mission's explicit instruction).
_BREACH_CALENDAR_DAYS_RE = re.compile(
    r"(?:notify|notification|notice)[^.]{0,80}?within\s+(" + _NUM + r")\s+(?:calendar\s+)?days\b"
    r"|within\s+(" + _NUM + r")\s+(?:calendar\s+)?days\s+(?:of|after)\s+(?:becoming\s+aware|discovery|discovering|learning)"
    r"|(?:no\s+(?:later|event\s+later)\s+than|not\s+later\s+than)\s+(" + _NUM + r")\s+(?:calendar\s+)?days\s+(?:after|of|following)"
    r"\s+(?:becoming\s+aware|discovery|discovering|learning)",
    re.I,
)
# Business-day phrasing is recognized but NEVER converted to a comparable
# hour figure -- deliberately ambiguous (a business day's length depends
# on the recipient's business calendar, which this deterministic engine
# has no way to know), so its presence forces REQUIRES_REVIEW (see
# `_classify_breach_notification`'s ambiguous_unit return) rather than
# failing silently in either direction.
_BREACH_BUSINESS_DAYS_RE = re.compile(
    r"(?:notify|notification|notice)[^.]{0,80}?within\s+" + _NUM + r"\s+business\s+days"
    r"|within\s+" + _NUM + r"\s+business\s+days\s+(?:of|after)\s+(?:becoming\s+aware|discovery|discovering|learning)",
    re.I,
)
_BREACH_UNDUE_DELAY_RE = re.compile(r"without\s+undue\s+delay", re.I)
_HOURS_PER_CALENDAR_DAY = 24
# Root-cause fix (Candidate 2, negated obligation): an EXPLICIT denial
# that any breach-notification obligation exists at all must never be
# treated identically to the obligation simply never being mentioned --
# "Vendor shall have no obligation to notify..." is a confidently-
# observed NON-COMPLIANT fact (the obligation was considered and
# rejected), not an absence. A closed, generalized set of negation verb
# phrases (mirrors the polarity vocabulary warranties_policy_engine's
# own _CATEGORY_NEGATION_RE already established for this exact class of
# defect), not a single literal sentence match.
_BREACH_NOTIFICATION_NEGATION_RE = re.compile(
    r"(?:shall\s+have\s+no\s+obligation\s+to\s+notify|shall\s+not\s+be\s+(?:obligated|required)\s+to\s+notify"
    r"|(?:is|are)\s+under\s+no\s+obligation\s+to\s+notify|no\s+obligation\s+to\s+notify"
    r"|shall\s+not\s+(?:be\s+required\s+to\s+)?notify|will\s+not\s+notify|need\s+not\s+notify)"
    r"\b.{0,100}?(?:of\s+any\s+)?(?:data\s+breach(?:es)?|security\s+incident|personal\s+data\s+breach)",
    re.I,
)

# --- International transfers -------------------------------------------------
_TRANSFER_ANCHOR_RE = re.compile(
    r"international\s+transfer|cross-?border\s+transfer|transfer\s+(?:of\s+)?personal\s+data\s+outside"
    r"|transfer\s+personal\s+data\s+(?:to\s+a\s+)?(?:third\s+)?countr",
    re.I,
)
_TRANSFER_PROHIBIT_RE = re.compile(r"shall\s+not\s+transfer\s+personal\s+data\s+outside", re.I)
_TRANSFER_EXCEPTION_RE = re.compile(r"\bexcept\b|\bunless\b|\bprovided\s+that\b", re.I)
_TRANSFER_SCC_RE = re.compile(r"standard\s+contractual\s+clauses|\bSCCs?\b", re.I)
_TRANSFER_ADEQUACY_RE = re.compile(r"adequacy\s+decision|adequate\s+level\s+of\s+protection", re.I)

# --- Data residency -----------------------------------------------------------
_RESIDENCY_RE = re.compile(
    r"(?:data\s+)?resid(?:ency|e)\s+(?:shall\s+be\s+)?(?:in|within)\s+([A-Z][A-Za-z .]{2,40}?)(?=[.,;]|\s+and\b|\s*$)"
    r"|(?:stored|maintained|hosted)\s+(?:solely\s+|exclusively\s+)?within\s+([A-Z][A-Za-z .]{2,40}?)(?=[.,;]|\s+and\b|\s*$)",
    re.I,
)

# --- Deletion / return / retention -------------------------------------------
_DELETION_RE = re.compile(
    r"shall\s+(?:delete|destroy)\s+(?:or\s+return\s+)?(?:all\s+)?(?:the\s+)?personal\s+data"
    r"|delete\s+or\s+return\s+(?:all\s+)?(?:the\s+)?personal\s+data",
    re.I,
)
_RETENTION_DAYS_RE = re.compile(
    r"retain\s+(?:the\s+)?personal\s+data\s+for\s+(?:up\s+to\s+)?(\d{1,4})\s+days"
    r"|retention\s+period\s+of\s+(\d{1,4})\s+days",
    re.I,
)
_RETAIN_INDEFINITE_RE = re.compile(r"retain[^.]{0,40}indefinitely|no\s+obligation\s+to\s+delete", re.I)

# --- Audit rights --------------------------------------------------------------
_AUDIT_PRESENT_RE = re.compile(
    r"right\s+to\s+audit|audit\s+rights?|shall\s+permit[^.]{0,50}audit|subject\s+to\s+(?:an\s+)?annual\s+audit"
    r"|may\s+audit|entitled\s+to\s+audit",
    re.I,
)
_AUDIT_ABSENT_RE = re.compile(
    r"no\s+audit\s+rights?"
    r"|shall\s+not\s+(?:have|be\s+entitled\s+to)\s+(?:the\s+right\s+to\s+)?audit",
    re.I,
)

# --- Security standard ----------------------------------------------------------
_SECURITY_ANCHOR_RE = re.compile(
    r"security\s+measures|technical\s+and\s+organizational\s+measures|\bTOMs?\b|information\s+security"
    r"|(?:administrative|technical|physical)(?:,?\s*(?:and|,)\s*(?:administrative|technical|physical)){1,2}\s+safeguards"
    r"|security\s+safeguards|security\s+controls",
    re.I,
)
_SECURITY_CERT_RE = re.compile(
    r"ISO\s*/?\s*IEC\s*27001|ISO\s*27001|SOC\s*2(?:\s*Type\s*(?:I{1,2}|1|2))?|NIST\s+800-53|NIST\s+Cybersecurity\s+Framework",
    re.I,
)
_SECURITY_VAGUE_RE = re.compile(
    r"industry[\s-]standard\s+security|commercially\s+reasonable\s+security|reasonable\s+security\s+measures",
    re.I,
)

# --- Cooperation (DSR assistance + regulatory cooperation, combined — see
# DataSecurityFacts.cooperation_obligation) --------------------------------
_COOPERATION_RE = re.compile(
    r"(?:shall\s+)?(?:provide\s+)?(?:reasonable\s+)?(?:assistance|cooperat\w*)"
    r"(?:\s+with\s+\w+)?[^.]{0,60}?"
    r"(?:data\s+subject\s+requests?|regulatory\s+(?:inquiries|investigations)|(?:a\s+)?supervisory\s+authorit\w*)",
    re.I,
)

# --- Confidentiality of personal data -------------------------------------
_PD_CONFIDENTIALITY_RE = re.compile(
    r"personal\s+data\s+(?:shall\s+be\s+)?(?:kept\s+|treated\s+as\s+)?confidential|confidentiality\s+of\s+personal\s+data",
    re.I,
)

# --- Delegation to an external DPA/Schedule/Exhibit -------------------------
_DPA_CROSSREF_RE = re.compile(
    r"as\s+(?:set\s+forth|described|specified)\s+in\s+(?:the\s+)?(?:attached\s+)?"
    r"(?:Data\s+Processing\s+(?:Agreement|Addendum)|DPA|Schedule|Exhibit|Annex)"
    r"|subject\s+to\s+(?:the\s+)?terms\s+of\s+(?:the\s+)?(?:attached\s+)?(?:DPA|Data\s+Processing\s+(?:Agreement|Addendum))"
    r"|governed\s+by\s+(?:the\s+)?(?:attached\s+)?(?:DPA|Data\s+Processing\s+(?:Agreement|Addendum))",
    re.I,
)

# --- Liability cross-reference (informational only — never re-evaluated here) --
_LIABILITY_CROSSREF_RE = re.compile(
    r"(?:excluded\s+from|not\s+subject\s+to|outside\s+of)\s+the\s+limitation\s+of\s+liability"
    r"|liability\s+(?:arising\s+from|for)\s+(?:a\s+)?(?:data\s+)?breach\s+(?:of\s+this\s+Section\s+)?shall\s+not\s+be\s+(?:capped|limited)",
    re.I,
)


@dataclass
class DataSecurityFacts:
    """Every field is independently None ("not addressed anywhere in the
    text") unless the clause actually establishes it — this dataclass is
    evidence extraction, not policy completion (same rule Phase 2's
    deterministic import already enforces at the authoring layer: a
    template establishing a 2x cap does not establish what's acceptable;
    a data-protection clause establishing 72-hour breach notice does not
    establish anything about, say, audit rights)."""
    clause_found: bool
    raw_excerpt: str = ""
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    section_label: Optional[str] = None

    # Role attribution: {party_name: {"controller"|"processor", ...}} merged
    # across every anchored window — raw extraction only, side-agnostic.
    # our_role is resolved from this (given contract_side) at evaluation
    # time, since extraction has no policy/contract_side to resolve
    # against yet. joint_controllers=True means the clause states the
    # parties are joint controllers (role is inherently shared, not
    # per-side). role_conflict=True means a SINGLE named party was
    # attributed two different roles — a genuine ambiguity, never guessed
    # past regardless of which policy dimensions are configured.
    role_attributions: Dict[str, set] = field(default_factory=dict)
    joint_controllers: bool = False
    role_conflict: bool = False

    # Subprocessors: "unrestricted" | "notice" | "consent" | "prohibited" | None
    subprocessor_treatment: Optional[str] = None
    subprocessor_conflict: bool = False

    # Breach notification
    breach_notification_hours: Optional[int] = None
    breach_notification_conflict: bool = False
    # Root-cause fix (Candidate 2, time normalization) -- a business-day
    # notification commitment was found that cannot be safely
    # canonicalized to a comparable hour figure (see
    # _classify_breach_notification). Never silently treated as
    # "notification timing not addressed."
    breach_notification_ambiguous_unit: bool = False
    # Root-cause fix (Candidate 2, negation) -- an EXPLICIT denial that any
    # notification obligation exists ("Vendor shall have no obligation to
    # notify..."). NEGATED, never conflated with POSITIVE evidence nor
    # with the obligation simply never being mentioned.
    breach_notification_explicitly_disclaimed: bool = False
    breach_without_undue_delay: bool = False

    # International transfers: "scc" | "adequacy" | "prohibited" | "unaddressed_transfer" | None
    transfer_mechanism: Optional[str] = None

    # Data residency
    data_residency_region: Optional[str] = None

    # Deletion / retention
    deletion_or_return_required: Optional[bool] = None
    retention_days: Optional[int] = None
    retention_indefinite: bool = False

    # Audit rights: True | False | None (None = not addressed)
    audit_rights: Optional[bool] = None

    # Security standard: "named_certification" | "vague" | None
    security_standard: Optional[str] = None

    # Cooperation obligations (data-subject-request assistance + regulatory
    # cooperation) — modeled as ONE combined dimension rather than two,
    # because the drafting patterns that establish either one in real DPAs
    # are near-identical ("shall provide reasonable assistance in connection
    # with data subject requests and regulatory inquiries") and splitting
    # them would require guessing which specific sub-obligation a single
    # sentence covering both was "really" about — not a genuine second
    # deterministic fact, just relabeling the same evidence twice.
    cooperation_obligation: Optional[bool] = None

    confidentiality_of_personal_data: Optional[bool] = None

    dpa_cross_reference: bool = False
    liability_cross_reference: bool = False

    # Fact-admission architecture — mirrors liability_policy_engine.
    # LiabilityFacts.absence_state. Unlike confidentiality (whose existing
    # `if not obligations` branch already absorbs RECOGNITION_UNCERTAIN
    # safely), this adapter's per-dimension evaluate logic can reach
    # ACCEPT on an all-None facts object when a playbook requires nothing
    # specific — so evaluate_data_security_policy checks this field
    # explicitly and early, the same way liability's evaluate function
    # does, rather than relying on side effects of the unresolved-facts list.
    absence_state: str = "CONFIRMED_ABSENT"
    semantic_discovery_error: Optional[str] = None
    ai_identified_condition: Optional[str] = None
    ai_identified_exception: Optional[str] = None
    ai_identified_definition_or_reference: Optional[str] = None


class DataSecurityPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]

    require_processor_role: bool
    prohibit_unrestricted_subprocessors: bool
    require_subprocessor_notice_or_consent: str  # "not_required" | "notice" | "consent"
    preferred_breach_notification_hours: Optional[float]
    acceptable_max_breach_notification_hours: Optional[float]
    negotiate_max_breach_notification_hours: Optional[float]
    require_fixed_breach_notification_period: bool
    require_international_transfer_safeguard: bool
    require_data_residency: bool
    required_data_residency_regions_json: Optional[List[str]]
    require_deletion_or_return: bool
    max_retention_days: Optional[float]
    require_audit_rights: bool
    require_named_security_certification: bool
    require_cooperation_obligation: bool
    require_confidentiality_of_personal_data: bool


def _role_attributions(window: str) -> Tuple[Dict[str, set], bool]:
    """Pure extraction, side-agnostic: which named party was attributed
    which role word(s) in this window, plus whether any single named
    party was attributed BOTH controller and processor within it (an
    internal conflict regardless of which side that party is on)."""
    attributions: Dict[str, set] = {}
    for m in _ROLE_STATEMENT_RE.finditer(window):
        role_name, role_word = m.group(1), m.group(2).lower()
        if role_name.lower() in _ROLE_GENERIC_WORDS:
            continue
        attributions.setdefault(role_name, set()).add(role_word)
    conflict = any(len(roles) > 1 for roles in attributions.values())
    return attributions, conflict


def _classify_subprocessors(window: str) -> Tuple[Optional[str], bool]:
    if not _SUBPROCESSOR_ANCHOR_RE.search(window):
        return None, False
    found = set()
    if _SUBPROCESSOR_PROHIBIT_RE.search(window):
        found.add("prohibited")
    if _SUBPROCESSOR_CONSENT_RE.search(window):
        found.add("consent")
    if _SUBPROCESSOR_NOTICE_RE.search(window):
        found.add("notice")
    if _SUBPROCESSOR_UNRESTRICTED_RE.search(window):
        found.add("unrestricted")
    if len(found) > 1:
        return None, True
    if not found:
        return None, False
    return next(iter(found)), False


def _classify_breach_notification(window: str, negation_scan_text: Optional[str] = None) -> Tuple[Optional[int], bool, bool, bool, bool]:
    """Returns (hours, conflict, without_undue_delay, ambiguous_unit, explicitly_disclaimed).

    ambiguous_unit=True means a business-day commitment was found that
    cannot be safely canonicalized to hours -- callers must treat this
    the same as a conflict (fail closed to REQUIRES_REVIEW), never
    silently drop it or treat the notification dimension as unaddressed.

    explicitly_disclaimed=True means the document affirmatively denies
    any notification obligation exists -- NEGATED, never treated as
    POSITIVE evidence nor as mere absence. Checked against
    `negation_scan_text` (a backward-widened slice) when given, since
    the negation verb phrase commonly precedes the anchor word that
    `window` itself starts at."""
    if _BREACH_NOTIFICATION_NEGATION_RE.search(negation_scan_text if negation_scan_text is not None else window):
        return None, False, False, False, True
    if not _BREACH_ANCHOR_RE.search(window):
        return None, False, False, False, False
    hour_values = set()
    for m in _BREACH_HOURS_RE.finditer(window):
        raw = m.group(1) or m.group(2) or m.group(3)
        value = _parse_number_token(raw) if raw else None
        if value is not None:
            hour_values.add(int(value))
    for m in _BREACH_CALENDAR_DAYS_RE.finditer(window):
        raw = m.group(1) or m.group(2) or m.group(3)
        value = _parse_number_token(raw) if raw else None
        if value is not None:
            hour_values.add(int(value) * _HOURS_PER_CALENDAR_DAY)
    ambiguous_unit = bool(_BREACH_BUSINESS_DAYS_RE.search(window))
    undue_delay = bool(_BREACH_UNDUE_DELAY_RE.search(window))
    if len(hour_values) > 1:
        return None, True, undue_delay, ambiguous_unit, False
    hours = next(iter(hour_values)) if hour_values else None
    return hours, False, undue_delay, ambiguous_unit, False


def _classify_transfer(window: str) -> Optional[str]:
    if not _TRANSFER_ANCHOR_RE.search(window):
        return None
    prohibit_match = _TRANSFER_PROHIBIT_RE.search(window)
    if prohibit_match:
        # An outright "shall not transfer ... outside X" is only an
        # absolute prohibition if it is NOT immediately qualified by a
        # carve-out ("... except pursuant to SCCs"). A qualified
        # prohibition is really a named-mechanism requirement, not a ban
        # on international transfer altogether — fall through to look for
        # the named mechanism instead of overstating this as "prohibited".
        tail = window[prohibit_match.end():prohibit_match.end() + 150]
        if not _TRANSFER_EXCEPTION_RE.search(tail):
            return "prohibited"
    if _TRANSFER_SCC_RE.search(window):
        return "scc"
    if _TRANSFER_ADEQUACY_RE.search(window):
        return "adequacy"
    if prohibit_match:
        # Qualified prohibition with no extractable named mechanism —
        # still transfer-restrictive, but the specific safeguard is not
        # deterministically identifiable from this window.
        return "unaddressed_transfer"
    return "unaddressed_transfer"


def _classify_residency(window: str) -> Optional[str]:
    m = _RESIDENCY_RE.search(window)
    if not m:
        return None
    region = (m.group(1) or m.group(2) or "").strip()
    return region or None


def _classify_deletion_retention(window: str) -> Tuple[Optional[bool], Optional[int], bool]:
    deletion = True if _DELETION_RE.search(window) else None
    indefinite = bool(_RETAIN_INDEFINITE_RE.search(window))
    days_values = set()
    for m in _RETENTION_DAYS_RE.finditer(window):
        raw = m.group(1) or m.group(2)
        if raw:
            days_values.add(int(raw))
    days = next(iter(days_values)) if len(days_values) == 1 else None
    if indefinite and deletion is None:
        deletion = False
    return deletion, days, indefinite


def _classify_audit(window: str) -> Optional[bool]:
    if _AUDIT_ABSENT_RE.search(window):
        return False
    if _AUDIT_PRESENT_RE.search(window):
        return True
    return None


def _classify_security_standard(window: str) -> Optional[str]:
    if not _SECURITY_ANCHOR_RE.search(window):
        return None
    if _SECURITY_CERT_RE.search(window):
        return "named_certification"
    if _SECURITY_VAGUE_RE.search(window):
        return "vague"
    return None


# Off by default — same rollout discipline as liability/confidentiality.
DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = False  # module-load-time default; immediately overridden below
import fact_admission as _fact_admission_env_check
DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED = _fact_admission_env_check.semantic_discovery_enabled("DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED")
del _fact_admission_env_check

_DATA_SECURITY_SEMANTIC_FOCUS = (
    "one party being obligated to protect personal or customer data, notify the "
    "other party of a security incident or data breach, restrict subprocessors, "
    "or otherwise address data protection/security under this agreement -- even if "
    "the wording is unusual and does not use standard terms like 'data breach' or "
    "'security incident'"
)
_DATA_SECURITY_SEMANTIC_PROPOSITION = (
    "This sentence or clause is operative language of this agreement that "
    "establishes a data-protection or security obligation (e.g. safeguarding data, "
    "breach notification, subprocessor restrictions, or data handling standards)."
)


def _run_semantic_discovery(text: str) -> Tuple[List, Optional[str], bool, Optional[str]]:
    """Mirrors liability_policy_engine._run_semantic_discovery exactly.
    Returns (admitted_candidates, unresolved_dependency_note, error)."""
    if not DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED:
        return [], None, False, None
    import fact_admission as _fa
    try:
        raw_candidates = _fa.discover_candidate_spans(text, "data_security", _DATA_SECURITY_SEMANTIC_FOCUS)
    except Exception as exc:  # noqa: BLE001 — provider unavailable, never "confirmed absent"
        return [], None, False, f"{type(exc).__name__}: {exc}"

    verified_candidates = [
        _fa.verify_and_ground(candidate, text, _DATA_SECURITY_SEMANTIC_PROPOSITION) for candidate in raw_candidates
    ]
    admitted = [c for c in verified_candidates if c.admission_status == _fa.ADMITTED]
    unresolved_dependency_note = _fa.first_unresolved_dependency_note(verified_candidates)
    note_is_unconditional = _fa.first_unresolved_dependency_note_is_unconditional(verified_candidates)
    return admitted, unresolved_dependency_note, note_is_unconditional, None


def extract_data_security_facts(text: str) -> Optional[DataSecurityFacts]:
    """Deterministic, single-provision extraction (data-protection clauses
    in real SaaS/DPA drafting are typically one consolidated section or
    exhibit, not scattered independent provisions the way liability caps
    can be — so unlike Liability's document-wide multi-provision
    reconciliation, this adapter takes the FIRST anchored window as the
    controlling provision and reports a conflict, never a silent pick,
    whenever two DIFFERENT windows in the document disagree on the same
    dimension). Returns None only when no anchor exists at all AND
    semantic discovery (see _run_semantic_discovery) also ran successfully
    and found nothing — a provider outage/error becomes
    RECOGNITION_UNCERTAIN instead (see absence_state)."""
    anchors = list(_ANCHOR_RE.finditer(text))
    semantic_error: Optional[str] = None
    admitted_semantic: List = []
    unresolved_dependency_note: Optional[str] = None
    # Candidate 3 remediation (Root Cause 2): contextual discovery is no
    # longer gated behind "deterministic anchor discovery found zero
    # matches" -- see confidentiality_policy_engine.py's identical fix.
    admitted_semantic, unresolved_dependency_note, note_is_unconditional, semantic_error = _run_semantic_discovery(text)
    if not anchors:
        if semantic_error is not None:
            return DataSecurityFacts(clause_found=True, absence_state="RECOGNITION_UNCERTAIN", semantic_discovery_error=semantic_error)
        if not admitted_semantic and not unresolved_dependency_note:
            return None
        if not admitted_semantic:
            return DataSecurityFacts(clause_found=True, ai_identified_definition_or_reference=unresolved_dependency_note)
    elif semantic_error is not None:
        admitted_semantic = []

    # Use every anchored window (deduplicated by proximity) so a genuine
    # cross-provision conflict (e.g. Section 9 says 72 hours, Section 14
    # says 24 hours) is detected rather than only ever seeing the first.
    # A semantically-admitted candidate contributes a window exactly like
    # a regex anchor does — it never bypasses the classification functions
    # below, it only earns a shot at them (see AUTHORITY_BOUNDARY.md §3).
    candidate_starts = [m.start() for m in anchors] + [c.start_offset for c in admitted_semantic]
    windows: List[Tuple[int, int, str]] = []
    seen_starts: List[int] = []
    for start in candidate_starts:
        if any(abs(start - s) < 200 for s in seen_starts):
            continue
        end = min(len(text), start + _PROVISION_WINDOW_CHARS)
        windows.append((start, end, text[start:end]))
        seen_starts.append(start)

    if not windows:
        return None

    first_start, first_end, _ = windows[0]
    facts = DataSecurityFacts(
        clause_found=True,
        raw_excerpt=_excerpt(text, first_start, min(first_end, first_start + 300)),
        start_index=first_start, end_index=first_end,
        section_label=_section_label_before(text, first_start),
    )

    role_results, subprocessor_results, breach_results, transfer_results = [], [], [], []
    residency_results, security_results = [], []

    for _win_start, _win_end, window in windows:
        if _JOINT_CONTROLLER_RE.search(window):
            facts.joint_controllers = True
        attributions, role_conflict = _role_attributions(window)
        if role_conflict:
            facts.role_conflict = True
        for name, roles in attributions.items():
            existing = facts.role_attributions.setdefault(name, set())
            existing |= roles
            if len(existing) > 1:
                facts.role_conflict = True
        subp, subp_conflict = _classify_subprocessors(window)
        if subp is not None:
            subprocessor_results.append(subp)
        if subp_conflict:
            facts.subprocessor_conflict = True
        # Root-cause fix (Candidate 2, negation): the anchor-forward
        # `window` starts AT the anchor match itself (e.g. "personal
        # data breach..."), which discards any negation verb phrase
        # that PRECEDES the anchor in the natural sentence order
        # ("Vendor shall have no obligation to notify Customer of any
        # personal data breach...") -- the negation was previously
        # invisible to this classifier for exactly that reason, not
        # because the pattern itself was wrong. Widen the scan used
        # for polarity detection specifically to include a backward
        # margin, without changing any other classifier's window.
        _negation_scan = text[max(0, _win_start - 200):_win_end]
        hours, hr_conflict, undue, ambiguous_unit, disclaimed = _classify_breach_notification(window, _negation_scan)
        if hours is not None:
            breach_results.append(hours)
        if hr_conflict:
            facts.breach_notification_conflict = True
        if ambiguous_unit:
            facts.breach_notification_ambiguous_unit = True
        if disclaimed:
            facts.breach_notification_explicitly_disclaimed = True
        if undue:
            facts.breach_without_undue_delay = True
        transfer = _classify_transfer(window)
        if transfer:
            transfer_results.append(transfer)
        residency = _classify_residency(window)
        if residency:
            residency_results.append(residency)
        deletion, days, indefinite = _classify_deletion_retention(window)
        if deletion is not None:
            facts.deletion_or_return_required = (facts.deletion_or_return_required or False) or deletion
        if days is not None:
            facts.retention_days = days
        if indefinite:
            facts.retention_indefinite = True
        audit = _classify_audit(window)
        if audit is not None:
            facts.audit_rights = audit if facts.audit_rights is None else (facts.audit_rights or audit)
        sec = _classify_security_standard(window)
        if sec:
            security_results.append(sec)
        if _COOPERATION_RE.search(window):
            facts.cooperation_obligation = True
        if _PD_CONFIDENTIALITY_RE.search(window):
            facts.confidentiality_of_personal_data = True
        if _DPA_CROSSREF_RE.search(window) or _EXTERNAL_DEFINITION_NOT_ATTACHED_RE.search(window):
            facts.dpa_cross_reference = True
        if _LIABILITY_CROSSREF_RE.search(window):
            facts.liability_cross_reference = True

    # Cross-window conflict detection: two windows disagreeing on the same
    # categorical dimension is exactly as much a conflict as two clauses
    # disagreeing within one window.
    if len(set(subprocessor_results)) > 1:
        facts.subprocessor_conflict = True
    elif subprocessor_results:
        facts.subprocessor_treatment = subprocessor_results[0]

    if len(set(breach_results)) > 1:
        facts.breach_notification_conflict = True
    elif breach_results:
        facts.breach_notification_hours = breach_results[0]

    if transfer_results:
        # "prohibited" is the most protective/restrictive finding and wins
        # over an unaddressed/weaker classification from another window
        # discussing the same transfer topic differently; two genuinely
        # different affirmative mechanisms (scc vs adequacy) in different
        # windows is reported as-is (not a conflict — both can be true).
        facts.transfer_mechanism = "prohibited" if "prohibited" in transfer_results else transfer_results[0]

    if residency_results:
        facts.data_residency_region = residency_results[0]

    if security_results:
        facts.security_standard = "named_certification" if "named_certification" in security_results else security_results[0]

    # Final trust architecture (Phase 5/6) — see confidentiality_policy_
    # engine.py's identical composition for the full rationale.
    import fact_admission as _fa
    for candidate in admitted_semantic:
        facts.ai_identified_condition = facts.ai_identified_condition or candidate.condition
        facts.ai_identified_exception = facts.ai_identified_exception or candidate.exception
    facts.ai_identified_definition_or_reference = _fa.first_resolved_dependency_note(admitted_semantic)

    # Candidate 3 remediation (Root Cause 1): an admitted AI candidate
    # exists but no data-security dimension could be deterministically
    # structured from it -- never let this silently reach ACCEPT merely
    # because nothing was established. See CANONICAL_PRIMARY_FACT_SCHEMA.md.
    if admitted_semantic and facts.absence_state == "CONFIRMED_ABSENT":
        _any_established = any(v is not None and v is not False for v in (
            facts.breach_notification_hours, facts.transfer_mechanism, facts.data_residency_region,
            facts.security_standard, facts.subprocessor_treatment, facts.deletion_or_return_required,
            facts.retention_days, facts.audit_rights, facts.cooperation_obligation,
            facts.confidentiality_of_personal_data,
        )) or bool(facts.role_attributions) or facts.breach_notification_explicitly_disclaimed \
            or facts.breach_notification_ambiguous_unit or facts.breach_without_undue_delay \
            or facts.retention_indefinite or facts.dpa_cross_reference or facts.liability_cross_reference
        if not _any_established:
            facts.absence_state = "PRESENT_BUT_UNRESOLVED"

    # Zero-silent-loss mission -- a candidate was discovered but its OWN
    # semantic verification reported genuine uncertainty (not a confident,
    # disproven claim -- see fact_admission.first_unresolved_dependency_
    # note's docstring), so admitted_semantic ends up empty even though
    # real, material content was found. Previously this note was only
    # consulted in the "no anchors at all" branch above; when a
    # deterministic anchor DOES exist (as here), the note was silently
    # discarded, letting the case fall through to a bare CONFIRMED_ABSENT/
    # ACCEPT purely because the model's own verification confidence
    # varied run-to-run for a genuinely colloquial/boundary-line clause
    # (found via the real-provider repeatability test: data_security-139
    # varied ACCEPT/REQUIRES_REVIEW across 5 identical runs).
    if (not admitted_semantic and unresolved_dependency_note is not None
            and facts.absence_state == "CONFIRMED_ABSENT"):
        _any_established = any(v is not None and v is not False for v in (
            facts.breach_notification_hours, facts.transfer_mechanism, facts.data_residency_region,
            facts.security_standard, facts.subprocessor_treatment, facts.deletion_or_return_required,
            facts.retention_days, facts.audit_rights, facts.cooperation_obligation,
            facts.confidentiality_of_personal_data,
        )) or bool(facts.role_attributions) or facts.breach_notification_explicitly_disclaimed \
            or facts.breach_notification_ambiguous_unit or facts.breach_without_undue_delay \
            or facts.retention_indefinite or facts.dpa_cross_reference or facts.liability_cross_reference
        # Candidate 3 final pre-freeze blocker remediation (Blocker 2) -- a
        # definition/cross-reference dependency or competing-reading note
        # (note_is_unconditional=True) is always structurally material and
        # must never be suppressed merely because SOME other data-security
        # dimension happened to be established elsewhere in the document.
        if note_is_unconditional or not _any_established:
            facts.absence_state = "PRESENT_BUT_UNRESOLVED"
            facts.ai_identified_definition_or_reference = (
                facts.ai_identified_definition_or_reference or unresolved_dependency_note
            )

    return facts


def _resolve_our_role(facts: DataSecurityFacts, contract_side: str) -> Tuple[Optional[str], bool, bool]:
    """Resolves our_role from the side-agnostic role_attributions gathered
    at extraction time, given the policy's configured contract_side.
    Returns (our_role, unresolved_directional, is_joint). Never guesses:
    a directional role statement under a "mutual" playbook configuration,
    or a named party that can't be mapped to buy_side/sell_side, both
    come back unresolved rather than picking one."""
    if facts.joint_controllers and not facts.role_attributions:
        return "joint", False, True
    if not facts.role_attributions:
        return None, False, False
    if contract_side == "mutual":
        return None, True, False

    # Data-protection drafting overwhelmingly uses "Processor"/"Controller"
    # themselves as the defined-term subject ("Processor shall act as a
    # data processor ..."), the same way the rest of this codebase already
    # treats "Vendor"/"Customer" as fixed conventional sell_side/buy_side
    # role-words (see BUY_SIDE_ROLES/SELL_SIDE_ROLES in policy_engine_core).
    # By the same near-universal commercial-services convention, "Processor"
    # is the service-provider (sell_side) and "Controller" is the customer
    # (buy_side) — kept local to this adapter since it is DP-specific, not
    # a clause-agnostic addition to the shared role vocabulary.
    _LOCAL_ROLE_SIDE = {"processor": "sell_side", "controller": "buy_side"}

    our_roles: set = set()
    for name, roles in facts.role_attributions.items():
        mapped_side = side_for_role(name) or _LOCAL_ROLE_SIDE.get(name.strip().lower())
        if mapped_side == contract_side:
            our_roles |= roles
    if len(our_roles) == 1:
        return next(iter(our_roles)), False, False
    if len(our_roles) > 1:
        return None, True, False
    # No named party mapped to our configured side at all.
    return None, True, False


def _build_ladder(policy: DataSecurityPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", "Preferred data-protection terms met in full"),
        ("ACCEPTABLE", "Auto-accept within acceptable data-protection terms"),
        ("FALLBACK", "Negotiate data-protection terms within fallback range"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Prohibited data-protection terms"),
    ]
    return _core_build_ladder(state, step_specs)


_WORST_ORDER = {ACCEPT: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, MUST_REDLINE: 3, ESCALATE: 4, PROHIBITED: 5}


def _worse(a: str, b: str) -> str:
    return a if _WORST_ORDER.get(a, 0) >= _WORST_ORDER.get(b, 0) else b


def evaluate_data_security_policy(
    facts: Optional[DataSecurityFacts],
    policy: DataSecurityPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    common = dict(
        rule_id=RULE_ID, clause_type="data_security", source=source,
        summary_label="Data protection treatment",
        our_position_label="Our data-protection obligations",
        counterparty_position_label="Counterparty's data-protection commitments",
    )

    if facts is None or not facts.clause_found:
        return PolicyDecision(
            **common, state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No data protection / security clause found",
            policy_limit_summary="N/A",
            required_action="None — this contract does not address data protection or security",
            explanation="No data protection or security clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None,
        )

    if facts.absence_state == "RECOGNITION_UNCERTAIN":
        # Fact-admission architecture (Step 5/6): a semantic-discovery
        # provider outage/error must never be reported as "this contract
        # does not address data protection" (NOT_APPLICABLE) NOR silently
        # evaluated as an all-None facts object, which this adapter's
        # per-dimension logic could otherwise resolve to ACCEPT for a
        # playbook that doesn't require any specific dimension. Escalate
        # explicitly instead.
        return PolicyDecision(
            **common, state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Could not determine whether a data protection / security clause is present",
            policy_limit_summary="N/A",
            required_action="Manual review required — automated recognition was unavailable for this document.",
            explanation=(
                "Deterministic pattern matching found no data protection / security clause, and semantic "
                f"verification could not confirm its absence ({facts.semantic_discovery_error or 'unavailable'}). "
                "This is not the same as confirming the contract has no such clause."
            ),
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None,
        )

    our_role, role_unresolved_directional, _is_joint = _resolve_our_role(facts, policy.contract_side)

    unresolved: List[str] = []
    # Final trust architecture (Phase 4 hard gate) — a material condition/
    # exception the AI/context layer identified and grounded must not be
    # silently dropped merely because the clause otherwise resolved cleanly.
    if facts.ai_identified_condition:
        unresolved.append(
            f"a material condition was identified by contextual analysis and grounded against the source "
            f"document (\"{facts.ai_identified_condition}\")"
        )
    if facts.ai_identified_exception:
        unresolved.append(
            f"a material exception was identified by contextual analysis and grounded against the source "
            f"document (\"{facts.ai_identified_exception}\")"
        )
    if facts.ai_identified_definition_or_reference:
        unresolved.append(
            f"a material definition/cross-reference dependency was identified by contextual analysis "
            f"({facts.ai_identified_definition_or_reference})"
        )
    if facts.role_conflict:
        unresolved.append("controller/processor role is stated inconsistently (conflicting role attributions)")
    elif policy.require_processor_role and role_unresolved_directional:
        unresolved.append("the clause states controller/processor roles by named party, but they could not be "
                           "confidently mapped to our configured contract side, or this playbook is configured "
                           "for a mutual position — cannot determine our role")
    if facts.subprocessor_conflict:
        unresolved.append("subprocessor treatment is stated inconsistently across the document")
    if facts.breach_notification_conflict:
        unresolved.append("breach/security-incident notification timing is stated inconsistently across the document")
    if facts.breach_notification_ambiguous_unit:
        unresolved.append(
            "breach/security-incident notification timing is stated in business days, which cannot be "
            "reliably compared to policy's hour-based threshold without knowing the recipient's business "
            "calendar — this evaluation does not manufacture a conversion"
        )

    # Material obligation delegated to an unresolved external DPA/Schedule
    # AND essentially nothing else in this document independently
    # establishes the substantive terms — the spec explicitly requires
    # abstaining here rather than treating the cross-reference as either
    # satisfying or failing the policy.
    established_dimension_count = sum(1 for v in (
        facts.subprocessor_treatment, facts.breach_notification_hours,
        (facts.transfer_mechanism if facts.transfer_mechanism != "unaddressed_transfer" else None),
        facts.data_residency_region, facts.deletion_or_return_required, facts.audit_rights,
        facts.security_standard, facts.cooperation_obligation, facts.confidentiality_of_personal_data,
    ) if v is not None) + (1 if facts.breach_without_undue_delay else 0)
    if facts.dpa_cross_reference and established_dimension_count == 0:
        unresolved.append("material data-protection obligations are delegated to a referenced DPA/Schedule/Exhibit not included in this text")

    # Candidate 3 remediation (Root Cause 1): an admitted AI candidate
    # exists but no data-security dimension could be deterministically
    # structured from it -- never let this silently reach ACCEPT merely
    # because no policy field happened to require anything. See
    # CANONICAL_PRIMARY_FACT_SCHEMA.md.
    if (facts.absence_state == "PRESENT_BUT_UNRESOLVED" and established_dimension_count == 0
            and not facts.dpa_cross_reference):
        unresolved.append(
            "contextual discovery identified and verified data-security-relevant language in this contract, but "
            "deterministic extraction could not structure it into a specific requirement — this is not the same "
            "as confirming no data security provision exists"
        )

    if unresolved:
        explanation = requires_review_explanation("data protection / security clause", facts.raw_excerpt, unresolved)
        return PolicyDecision(
            **common, state=REQUIRES_REVIEW,
            contract_language=facts.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary="N/A", required_action=requires_review_required_action(unresolved),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved,
            start_index=facts.start_index, end_index=facts.end_index,
            controlling_provision={"label": f"Section {facts.section_label} — Data Protection" if facts.section_label else "Data Protection", "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
        )

    notes: List[str] = []
    worst = ACCEPT
    category_treatments: List[Dict[str, Any]] = []

    def _note(msg: str, state: str) -> None:
        nonlocal worst
        notes.append(msg)
        worst = _worse(worst, state)

    # --- Role -----------------------------------------------------------
    if policy.require_processor_role:
        if our_role is None and facts.role_conflict:
            pass  # already handled above via unresolved
        elif our_role is None:
            _note("policy requires us to be identified as Processor, but no role statement was found in the clause", NEGOTIATE)
        elif our_role != "processor":
            _note(f"policy requires us to be identified as Processor, but the clause states our role as {our_role}", MUST_REDLINE)

    # --- Subprocessors ----------------------------------------------------
    if facts.subprocessor_treatment == "unrestricted" and policy.prohibit_unrestricted_subprocessors:
        _note("subprocessors may be engaged without notice or consent, prohibited by policy", MUST_REDLINE)
    required_sp = policy.require_subprocessor_notice_or_consent
    if required_sp and required_sp != "not_required":
        rank = {"notice": 1, "consent": 2}
        found_rank = rank.get(facts.subprocessor_treatment or "", 0)
        if facts.subprocessor_treatment == "prohibited":
            pass  # stricter than any requirement — satisfies policy
        elif found_rank < rank.get(required_sp, 0):
            _note(f"policy requires subprocessor {required_sp}, but the clause provides for "
                  f"{facts.subprocessor_treatment or 'no stated subprocessor safeguard'}", NEGOTIATE)
    category_treatments.append({"category": "subprocessors", "treatment": facts.subprocessor_treatment or "not_addressed", "cap_summary": None, "raw_excerpt": "", "established": facts.subprocessor_treatment is not None})

    # --- Breach notification ----------------------------------------------
    if facts.breach_notification_explicitly_disclaimed:
        # Root-cause fix (Candidate 2, negation): a confidently-observed
        # NON-COMPLIANT fact (the obligation was considered and denied),
        # never conflated with the obligation simply never being
        # mentioned -- forces the same MUST_REDLINE severity as any other
        # deterministically-confirmed policy violation in this adapter.
        #
        # Candidate 3 final gap-closure fix: this was previously gated
        # behind at least one specific breach-notification-hours field
        # being configured, using that as a proxy for "does this policy
        # care about breach notification at all." Found via burned-corpus
        # re-verification (data_security-130) to let a policy
        # configuration with no notification-hours field set at all
        # silently reach a clean ACCEPT despite an explicit, deterministically-
        # confirmed disclaimer of the obligation -- independently confirmed
        # as the correct fix (not a fixture-specific patch) by an
        # already-existing, differently-configured regression test
        # (test_negation_shall_have_no_obligation in
        # tests/test_candidate2_data_security_time_and_negation.py) that
        # already expects MUST_REDLINE for this exact clause text, and
        # only passed previously because ITS policy fixture happened to
        # set a notification-hours field. An explicit denial of any
        # notification duty is inherently adverse to a policy that uses
        # this adapter at all, independent of which specific numeric
        # threshold happens to be configured.
        _note("the document explicitly disclaims any breach/security-incident notification obligation",
              MUST_REDLINE)
    elif facts.breach_notification_hours is not None:
        state = classify_by_threshold(
            float(facts.breach_notification_hours),
            policy.preferred_breach_notification_hours,
            policy.acceptable_max_breach_notification_hours,
            policy.negotiate_max_breach_notification_hours,
        )
        if state != ACCEPT:
            _note(f"breach notification is {facts.breach_notification_hours} hours, exceeding policy's preferred threshold", state)
    elif facts.breach_without_undue_delay:
        if policy.require_fixed_breach_notification_period:
            _note("breach notification is stated only as \"without undue delay\" with no fixed maximum, but policy requires a fixed period", NEGOTIATE)
    elif policy.preferred_breach_notification_hours is not None or policy.require_fixed_breach_notification_period:
        _note("no breach/security-incident notification timing is stated in the clause, but policy requires one", NEGOTIATE)
    category_treatments.append({"category": "breach_notification", "treatment": (f"{facts.breach_notification_hours}h" if facts.breach_notification_hours is not None else ("without_undue_delay" if facts.breach_without_undue_delay else "not_addressed")), "cap_summary": None, "raw_excerpt": "", "established": facts.breach_notification_hours is not None or facts.breach_without_undue_delay})

    # --- International transfer -------------------------------------------
    if policy.require_international_transfer_safeguard:
        if facts.transfer_mechanism == "prohibited":
            pass  # no transfer at all trivially satisfies "safeguard required"
        elif facts.transfer_mechanism in ("scc", "adequacy"):
            pass
        elif facts.transfer_mechanism == "unaddressed_transfer":
            _note("international transfers are contemplated but no SCC/adequacy safeguard is stated, required by policy", MUST_REDLINE)
        # transfer_mechanism is None (topic never addressed at all) — silence
        # is not itself evidence transfers occur; not held against the clause.

    # --- Data residency -----------------------------------------------------
    if policy.require_data_residency:
        allowed = set(r.lower() for r in (policy.required_data_residency_regions_json or []))
        if facts.data_residency_region is None:
            _note("policy requires a stated data-residency commitment, but none was found in the clause", NEGOTIATE)
        elif allowed and facts.data_residency_region.lower() not in allowed:
            _note(f"clause commits to data residency in {facts.data_residency_region}, not within policy's approved region(s)", NEGOTIATE)

    # --- Deletion / return / retention ---------------------------------------
    if policy.require_deletion_or_return:
        if facts.deletion_or_return_required is False or (facts.retention_indefinite and facts.deletion_or_return_required is not True):
            _note("clause allows indefinite retention with no deletion/return commitment, required by policy", MUST_REDLINE)
        elif facts.deletion_or_return_required is None:
            _note("policy requires deletion or return of personal data on termination, but no such commitment was found", NEGOTIATE)
    if policy.max_retention_days is not None and facts.retention_days is not None:
        if facts.retention_days > policy.max_retention_days:
            _note(f"clause permits retention of {facts.retention_days} days, exceeding policy's maximum of {int(policy.max_retention_days)} days", NEGOTIATE)

    # --- Audit rights -----------------------------------------------------
    if policy.require_audit_rights:
        if facts.audit_rights is False:
            _note("audit rights are expressly excluded, required by policy", MUST_REDLINE)
        elif facts.audit_rights is None:
            _note("policy requires audit rights, but none are stated in the clause", NEGOTIATE)

    # --- Security standard --------------------------------------------------
    if policy.require_named_security_certification:
        if facts.security_standard == "vague":
            _note("security commitment is stated only as vague \"industry standard\"/\"commercially reasonable\" language, but policy requires a named certification (e.g. ISO 27001, SOC 2)", NEGOTIATE)
        elif facts.security_standard is None:
            _note("policy requires a named security certification, but no security-standard commitment was found", NEGOTIATE)
    category_treatments.append({"category": "security_standard", "treatment": facts.security_standard or "not_addressed", "cap_summary": None, "raw_excerpt": "", "established": facts.security_standard is not None})

    # --- Cooperation --------------------------------------------------------
    if policy.require_cooperation_obligation and not facts.cooperation_obligation:
        _note("policy requires cooperation with data-subject requests and regulatory inquiries, but no such commitment was found", NEGOTIATE)

    # --- Confidentiality of personal data ------------------------------------
    if policy.require_confidentiality_of_personal_data and not facts.confidentiality_of_personal_data:
        _note("policy requires an explicit confidentiality commitment for personal data, but none was found", NEGOTIATE)

    extracted_summary_parts = []
    if our_role:
        extracted_summary_parts.append(f"Role: {our_role}")
    if facts.subprocessor_treatment:
        extracted_summary_parts.append(f"Subprocessors: {facts.subprocessor_treatment}")
    if facts.breach_notification_hours is not None:
        extracted_summary_parts.append(f"Breach notice: {facts.breach_notification_hours}h")
    elif facts.breach_without_undue_delay:
        extracted_summary_parts.append("Breach notice: without undue delay")
    extracted_summary = "; ".join(extracted_summary_parts) or "Data protection clause found; limited structured detail extractable"

    if worst == ACCEPT and not notes:
        required_action = "None — data protection terms meet policy"
        explanation = f"Contract language: \"{facts.raw_excerpt}\". No policy gaps found. Result: {ACCEPT}."
    else:
        if worst in (ESCALATE, PROHIBITED):
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — " + "; ".join(notes)
        elif worst == MUST_REDLINE:
            required_action = "Replace clause — apply the approved fallback data-protection language: " + "; ".join(notes)
        else:
            required_action = "Negotiate — " + "; ".join(notes)
        explanation = f"Contract language: \"{facts.raw_excerpt}\". {'; '.join(notes)}. Result: {worst}."

    if facts.liability_cross_reference:
        category_treatments.append({"category": "liability_cross_reference", "treatment": "referenced", "cap_summary": None, "raw_excerpt": "", "established": True})

    return PolicyDecision(
        **common, state=worst,
        contract_language=facts.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary=(f"Preferred breach notice ≤{int(policy.preferred_breach_notification_hours)}h" if policy.preferred_breach_notification_hours else "See configured policy"),
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, worst),
        category_treatments=category_treatments, unresolved_facts=[],
        start_index=facts.start_index, end_index=facts.end_index,
        escalate_to=escalate_to_for_state(worst, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(worst, policy.fallback_text, (NEGOTIATE, MUST_REDLINE, PROHIBITED)),
        controlling_provision={"label": f"Section {facts.section_label} — Data Protection" if facts.section_label else "Data Protection", "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
    )
