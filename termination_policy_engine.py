"""
Termination clause adapter, over policy_engine_core.

Third clause adapter — authorized specifically to stress the architecture
along a reasoning shape neither Liability nor Indemnification exercises.
Liability is a comparative-value problem (two parties, one concept, which
value is ours). Indemnification is a directed-obligation-graph problem
(a promise pointing from one named role to another, possibly stated
reciprocally). Termination is neither: it is a CATALOG OF CONTINGENT
RIGHTS.

SEMANTIC MODEL:

    who -> holds a right to terminate -> under what trigger
        (convenience / material breach / insolvency / non-payment)
        -> subject to what conditions (cure period, notice period,
           or immediate/no-cure)
        -> with what consequence (termination fee, survival of other
           obligations, post-termination transition assistance)

A single document typically states SEVERAL distinct rights, not one
controlling provision and not one directed edge: "either party may
terminate for convenience on 90 days' notice" AND "either party may
terminate for cause if the other party breaches and fails to cure within
30 days" AND "either party may terminate immediately upon the other
party's insolvency" can all coexist, each independently evaluable. This
adapter tracks each TerminationRight independently, the same
non-reconciliation discipline Indemnification uses for its obligations.

DIRECTIONALITY: a termination right is not a promise TO someone (unlike
indemnification); it is a privilege HELD BY someone, exercisable against
the agreement itself. But it still has a directional consequence for a
playbook: a right WE hold is generally favorable (more optionality for
us); a right the COUNTERPARTY holds against us is a risk (they can end
the deal on us) that a playbook wants bounded — adequate notice, adequate
cure. This adapter resolves rights into "ours" and "the counterparty's
against us" using an adapter-local function structurally similar to
Indemnification's exposure/protection split, deliberately NOT sharing
code with it (see the architecture report for whether this recurring
shape is evidence of a real, not-yet-extracted core primitive).

A right can also be stated reciprocally ("either party may terminate...").
Reciprocal termination rights are subject to the SAME symmetry-
verification problem Indemnification's reciprocal clauses are: a "either
party" opener can be followed by differentiated per-party notice/cure
terms that contradict the claimed symmetry. This adapter reuses that
exact verification PATTERN (not code) for the same reason.
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
    excerpt as _excerpt, section_label_before as _section_label_before,
    requires_review_explanation, requires_review_required_action,
    detect_role_attributed_asymmetry,
)

RULE_ID = "POLICY_TERMINATION"

TRIGGER_TYPES = ["convenience", "material_breach", "insolvency", "non_payment", "automatic"]

SURVIVAL_TOPICS = [
    "confidentiality", "payment_obligations", "limitation_of_liability",
    "indemnification", "ip_ownership", "audit_rights",
]

_ANCHOR_RE = re.compile(r"terminat\w*", re.I)

# Rights attributed to a SPECIFIC named role vs. a generic reciprocal
# opener are extracted with two separate patterns, mirroring
# indemnification_policy_engine's _OBLIGATION_RE / _MUTUAL_RECIPROCAL_RE
# split. [A-Z] deliberately kept case-sensitive within the overall re.I
# compile via (?-i:...) — the same re.I-over-[A-Z] hazard already fixed
# twice in indemnification_policy_engine.py and once in
# liability_policy_engine.py.
_NAMED_RIGHT_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,25}))\s+(?i:may|shall\s+have\s+the\s+right\s+to)\s+terminate\s+this\s+Agreement",
    re.I,
)
_MUTUAL_RIGHT_RE = re.compile(
    r"(?:either\s+party|each\s+party|both\s+parties)\s+(?:may|shall\s+have\s+the\s+right\s+to)\s+terminate\s+this\s+Agreement",
    re.I,
)
_GENERIC_ROLE_WORDS = {
    "either", "each", "both", "the", "any", "such", "this", "that",
    "party", "parties",
}

_TRIGGER_CONVENIENCE_RE = re.compile(
    r"for\s+convenience|without\s+cause|for\s+any\s+reason\s+or\s+no\s+reason"
    r"|for\s+any\s+reason\s+in\s+its\s+sole\s+discretion|at\s+any\s+time\s+for\s+any\s+reason",
    re.I,
)
_TRIGGER_CAUSE_RE = re.compile(
    r"for\s+cause|material\s+breach|breach\s+of\s+(?:this\s+Agreement|any\s+(?:material\s+)?(?:term|provision|obligation))",
    re.I,
)
_TRIGGER_INSOLVENCY_RE = re.compile(
    r"insolven\w*|bankrupt\w*|receivership|assignment\s+for\s+the\s+benefit\s+of\s+creditors"
    r"|ceases\s+to\s+do\s+business|liquidat\w*",
    re.I,
)
_TRIGGER_NONPAYMENT_RE = re.compile(
    r"fails?\s+to\s+pay|non[\s-]?payment|payment\s+default|fails?\s+to\s+make\s+(?:any\s+)?payment",
    re.I,
)

_NOTICE_DAYS_RE = re.compile(
    r"(\d+)\s*(?:calendar\s+|business\s+)?days?[’']?\s*(?:prior\s+)?(?:written\s+)?notice",
    re.I,
)
_CURE_DAYS_RE = re.compile(
    r"(?:fails?\s+to\s+)?(?:cure|remed(?:y|ies))\w*.{0,40}?(\d+)\s*(?:calendar\s+|business\s+)?days?"
    r"|(\d+)\s*(?:calendar\s+|business\s+)?days?.{0,40}?(?:to\s+)?(?:cure|remed(?:y|ies))\w*",
    re.I,
)
_IMMEDIATE_RE = re.compile(
    r"\bimmediately\b|without\s+(?:prior\s+)?notice|without\s+(?:the\s+)?opportunity\s+to\s+cure"
    r"|without\s+(?:any\s+)?cure\s+period",
    re.I,
)

_SURVIVAL_ANCHOR_RE = re.compile(
    r"surviv\w*\s+(?:the\s+|any\s+)?(?:termination|expiration)|shall\s+survive\s+(?:any\s+)?termination",
    re.I,
)
_SURVIVAL_TOPIC_RE: Dict[str, re.Pattern] = {
    "confidentiality": re.compile(r"confidentiality", re.I),
    "payment_obligations": re.compile(r"payment\s+obligations|accrued\s+(?:but\s+unpaid\s+)?(?:fees|payment|amounts)", re.I),
    "limitation_of_liability": re.compile(r"limitation\s+of\s+liability", re.I),
    "indemnification": re.compile(r"indemnification", re.I),
    "ip_ownership": re.compile(r"intellectual\s+property|ownership\s+of\s+work\s+product", re.I),
    "audit_rights": re.compile(r"audit\s+rights?", re.I),
}

_FEE_MENTION_RE = re.compile(r"termination\s+fee|early\s+termination\s+(?:fee|charge)", re.I)
_FEE_UNLIMITED_RE = re.compile(
    r"termination\s+fee\b[^.]{0,30}?shall\s+not\s+be\s+(?:subject\s+to\s+)?(?:any\s+)?(?:cap|limit)(?:ation)?"
    r"|termination\s+fee\b[^.]{0,30}?shall\s+be\s+uncapped"
    r"|uncapped\s+termination\s+(?:fee|obligation)",
    re.I,
)
_FEE_MULTIPLIER_RE = re.compile(
    r"termination\s+fee[^.]{0,60}?(\d+(?:\.\d+)?)\s*(?:x|times)\s*(?:the\s+)?(?:total\s+|aggregate\s+)?(?:annual\s+)?fees?"
    r"|(\d+(?:\.\d+)?)\s*(?:x|times)\s*(?:the\s+)?(?:total\s+|aggregate\s+)?(?:annual\s+)?fees?[^.]{0,20}?termination\s+fee",
    re.I,
)
_FEE_FIXED_RE = re.compile(r"termination\s+fee[^.]{0,40}?\$\s*([\d,]+(?:\.\d{2})?)", re.I)

_TRANSITION_ASSISTANCE_RE = re.compile(
    r"transition\s+assistance|post[\s-]termination\s+(?:assistance|support|services)"
    r"|wind[\s-]down\s+(?:services|assistance)",
    re.I,
)

# Reciprocal-symmetry verification: same-shape pattern as
# indemnification_policy_engine._ROLE_ATTRIBUTION_RE / _detect_reciprocal_
# asymmetry, reimplemented locally since a "termination right" and an
# "indemnity obligation" are different fact shapes (trigger/notice/cure
# vs. trigger/scope/monetary), even though the underlying verification
# LOGIC (does a named-party attribution disagree with a symmetric opener)
# is the same idea. See the architecture report for whether recurring
# implementations of this idea are evidence of an unextracted core
# primitive.
_ROLE_ATTRIBUTION_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,25}))(?:'s)?\s+(?i:right\s+to\s+terminate|termination\s+rights?)\s+"
    r"(?i:under\s+this\s+(?:Section|Agreement)\s+)?",
    re.I,
)

_PROVISION_WINDOW_CHARS = 800
_ROLE_ATTRIBUTION_LOCAL_CHARS = 220


def _right_window(text: str, start: int, max_chars: int = _PROVISION_WINDOW_CHARS) -> str:
    """A single termination right is conventionally stated within one
    sentence. Termination clauses commonly stack several rights
    (convenience/cause/insolvency) as consecutive sentences in the same
    paragraph — a fixed-size window large enough to hold one right's own
    trailing clause is ALSO large enough to swallow the next right's
    sentence, and its trigger keywords (e.g. "insolvency") then leak into
    THIS right's classification. Cutting at the first sentence-ending
    period avoids that; max_chars is only a fallback for a right's own
    sentence running unusually long.

    Deliberately cuts at ". " only, NOT at ";" — a differentiated proviso
    naming specific parties' terms ("...for convenience; provided, that
    Vendor's right requires 90 days notice, and Customer's...") is
    conventionally punctuated as one semicolon-joined sentence, and an
    asymmetry-verification scan (_detect_right_asymmetry) needs to see
    that whole clause, not just the text before the semicolon. A ";" cut
    was tried and found to truncate exactly the differentiated-terms text
    this window exists to let the asymmetry check examine."""
    hi = min(len(text), start + max_chars)
    boundary = re.search(r"\.\s", text[start:hi])
    if boundary:
        hi = start + boundary.start() + 1
    return text[start:hi]


# ---------------------------------------------------------------------------
# Structured facts
# ---------------------------------------------------------------------------

@dataclass
class TerminationRight:
    """One right: holder_role may terminate the agreement under
    trigger_type, subject to notice/cure conditions."""
    holder_role: str
    holder_side: Optional[str]
    trigger_type: str  # "convenience" | "material_breach" | "insolvency" | "non_payment" | "automatic"
    notice_period_days: Optional[int]
    cure_period_days: Optional[int]
    immediate: bool
    raw_excerpt: str
    start_index: int
    end_index: int
    section_label: Optional[str]
    is_mutual: bool = False
    asymmetry_reasons: List[str] = field(default_factory=list)

    def label(self) -> str:
        prefix = f"Section {self.section_label} — " if self.section_label else ""
        return f"{prefix}{self.holder_role} may terminate ({self.trigger_type})"


@dataclass
class SurvivalTreatment:
    topic: str
    present: bool


@dataclass
class TerminationFee:
    kind: str  # "multiplier" | "fixed" | "unlimited" | "not_stated" | "not_mentioned"
    multiplier: Optional[float] = None
    fixed_amount: Optional[float] = None
    raw_excerpt: str = ""

    def summary(self) -> str:
        if self.kind == "unlimited":
            return "Uncapped"
        if self.kind == "multiplier":
            return f"{self.multiplier:g}x annual fees"
        if self.kind == "fixed":
            return f"${self.fixed_amount:,.2f} fixed"
        if self.kind == "not_mentioned":
            return "No termination fee"
        return "unspecified"


@dataclass
class TerminationFacts:
    clause_found: bool
    rights: List[TerminationRight] = field(default_factory=list)
    survival_topics: Dict[str, SurvivalTreatment] = field(default_factory=dict)
    survival_clause_found: bool = False
    fee: TerminationFee = field(default_factory=lambda: TerminationFee(kind="not_mentioned"))
    transition_assistance: bool = False

    # Fact-admission architecture — mirrors confidentiality_policy_engine.
    # ConfidentialityFacts.absence_state. evaluate_termination_policy's
    # existing `if not facts.rights` branch already routes empty rights to
    # REQUIRES_REVIEW regardless of the reason, so RECOGNITION_UNCERTAIN
    # never needs its own separate branch there (same as confidentiality).
    absence_state: str = "CONFIRMED_ABSENT"
    semantic_discovery_error: Optional[str] = None


class TerminationPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]
    require_mutual_convenience_termination: bool
    min_notice_days_against_us: Optional[int]
    min_cure_days_against_us: Optional[int]
    prohibit_immediate_termination_for_cause: bool
    required_survival_topics_json: Optional[List[str]]
    prohibit_uncapped_termination_fee: bool
    fee_preferred_multiplier: Optional[float]
    fee_acceptable_max_multiplier: Optional[float]
    fee_negotiate_max_multiplier: Optional[float]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

# _excerpt / _section_label_before are imported from policy_engine_core
# (promoted — see policy_engine_core.excerpt / section_label_before).

def _classify_trigger_type(window: str) -> str:
    # Insolvency and non-payment are checked first: they're the most
    # specific signals and can co-occur with generic "material breach"
    # language (e.g. "insolvency shall be deemed a material breach").
    if _TRIGGER_INSOLVENCY_RE.search(window):
        return "insolvency"
    if _TRIGGER_NONPAYMENT_RE.search(window):
        return "non_payment"
    if _TRIGGER_CONVENIENCE_RE.search(window):
        return "convenience"
    if _TRIGGER_CAUSE_RE.search(window):
        return "material_breach"
    return "automatic"


def _extract_notice_days(window: str) -> Optional[int]:
    m = _NOTICE_DAYS_RE.search(window)
    return int(m.group(1)) if m else None


def _extract_cure_days(window: str) -> Optional[int]:
    m = _CURE_DAYS_RE.search(window)
    if not m:
        return None
    return int(m.group(1) or m.group(2))


def _is_immediate(window: str, trigger_type: str) -> bool:
    if trigger_type == "insolvency":
        # Insolvency triggers are conventionally immediate/no-cure by
        # design — not itself a red flag, so don't require the explicit
        # "immediately" wording to classify it as such.
        return True
    return bool(_IMMEDIATE_RE.search(window))


def _monetary_key_fee(f: TerminationFee) -> Tuple[str, Optional[float], Optional[float]]:
    return (f.kind, f.multiplier, f.fixed_amount)


def _snapshot_right_attribution(local: str) -> Dict[str, Any]:
    return {
        "notice": _extract_notice_days(local),
        "cure": _extract_cure_days(local),
        "immediate": bool(_IMMEDIATE_RE.search(local)),
    }


def _compare_right_attribution(base_role: str, base: Dict[str, Any], role: str, snap: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    if base["notice"] is not None and snap["notice"] is not None and base["notice"] != snap["notice"]:
        reasons.append(f"{base_role} and {role} state different notice periods ({base['notice']} vs {snap['notice']} days)")
    if base["cure"] is not None and snap["cure"] is not None and base["cure"] != snap["cure"]:
        reasons.append(f"{base_role} and {role} state different cure periods ({base['cure']} vs {snap['cure']} days)")
    if base["immediate"] != snap["immediate"]:
        reasons.append(f"{base_role} and {role} differ on whether termination is immediate")
    return reasons


def _any_right_dimension_established_equal(base: Dict[str, Any], snap: Dict[str, Any]) -> bool:
    """Step 4A.10.4 — real, positively-established agreement on notice or
    cure period stands down the structural fail-closed check. `immediate`
    is deliberately excluded: it is a bool that is always "established"
    (never not-stated), so False==False would trivially satisfy this for
    every clause; it already compares unconditionally in
    _compare_right_attribution above. See
    indemnification_policy_engine._any_dimension_established_equal for
    the full rationale."""
    if base["notice"] is not None and snap["notice"] is not None and base["notice"] == snap["notice"]:
        return True
    if base["cure"] is not None and snap["cure"] is not None and base["cure"] == snap["cure"]:
        return True
    return False


def _detect_right_asymmetry(window: str) -> List[str]:
    """Same verification idea as indemnification_policy_engine's
    _detect_reciprocal_asymmetry: a mutual ("either party"/"each party")
    right claims symmetric treatment. This scans for sub-clauses
    attributing terms to a SPECIFIC named role ("Vendor's right to
    terminate...", not generic "either party's") within the same window
    and flags disagreement on notice period, cure period, or immediacy.

    The scan/window/compare mechanics are shared (see policy_engine_core.
    detect_role_attributed_asymmetry) — only the attribution regex, the
    generic-role stoplist, and the snapshot/compare functions stay
    adapter-owned."""
    return detect_role_attributed_asymmetry(
        window, _ROLE_ATTRIBUTION_RE, _GENERIC_ROLE_WORDS,
        _snapshot_right_attribution, _compare_right_attribution,
        max_chars=_ROLE_ATTRIBUTION_LOCAL_CHARS,
        established_equal_fn=_any_right_dimension_established_equal,
    )


# Off by default — same rollout discipline as every other adapter this
# session integrated.
TERMINATION_SEMANTIC_DISCOVERY_ENABLED = False

_TERMINATION_SEMANTIC_FOCUS = (
    "one party's right to end this agreement -- for convenience, for cause, upon insolvency, "
    "or otherwise -- even if the wording is unusual and does not use the word 'terminate' at all"
)
_TERMINATION_SEMANTIC_PROPOSITION = (
    "This sentence or clause is operative language of this agreement that establishes a "
    "party's right to end this agreement."
)


def _run_semantic_discovery(text: str) -> Tuple[List, Optional[str]]:
    """Mirrors liability_policy_engine._run_semantic_discovery exactly."""
    if not TERMINATION_SEMANTIC_DISCOVERY_ENABLED:
        return [], None
    import fact_admission as _fa
    try:
        raw_candidates = _fa.discover_candidate_spans(text, "termination", _TERMINATION_SEMANTIC_FOCUS)
    except Exception as exc:  # noqa: BLE001 — provider unavailable, never "confirmed absent"
        return [], f"{type(exc).__name__}: {exc}"

    admitted = []
    for candidate in raw_candidates:
        verified = _fa.verify_and_ground(candidate, text, _TERMINATION_SEMANTIC_PROPOSITION)
        if verified.admission_status == _fa.ADMITTED:
            admitted.append(verified)
    return admitted, None


def extract_termination_facts(text: str) -> Optional[TerminationFacts]:
    """Finds every termination right stated in the full document. Like
    Indemnification's obligations, rights are NOT reconciled into one
    controlling provision — a contract legitimately states several
    independently-true rights (convenience, cause, insolvency, ...).
    Returns None only when no anchor exists at all AND semantic discovery
    also ran successfully and found nothing — a provider outage/error
    becomes RECOGNITION_UNCERTAIN instead (see absence_state)."""
    anchors = [m for m in _ANCHOR_RE.finditer(text) if not re.search(r"\bno\s+$", text[max(0, m.start() - 15):m.start()], re.I)]
    if not anchors:
        admitted_semantic, semantic_error = _run_semantic_discovery(text)
        if semantic_error is not None:
            return TerminationFacts(clause_found=True, absence_state="RECOGNITION_UNCERTAIN", semantic_discovery_error=semantic_error)
        if not admitted_semantic:
            return None
        # A semantically-admitted candidate does not itself become a
        # right — it only earns this document a shot at the SAME
        # deterministic NAMED_RIGHT_RE/MUTUAL_RIGHT_RE structuring below
        # (which already scans the full document unconditionally, not
        # gated on `anchors`). If that structuring still can't parse a
        # right, this falls through to the existing "rights=[]"
        # REQUIRES_REVIEW path a few lines down — never a fabricated right.

    rights: List[TerminationRight] = []
    seen_spans: List[Tuple[int, int]] = []

    for m in _NAMED_RIGHT_RE.finditer(text):
        if any(abs(m.start() - s) < 30 for s, _ in seen_spans):
            continue
        holder_role = m.group(1)
        if holder_role.lower() in _GENERIC_ROLE_WORDS:
            continue
        window = _right_window(text, m.start())
        trigger_type = _classify_trigger_type(window)
        rights.append(TerminationRight(
            holder_role=holder_role, holder_side=side_for_role(holder_role),
            trigger_type=trigger_type,
            notice_period_days=_extract_notice_days(window),
            cure_period_days=_extract_cure_days(window),
            immediate=_is_immediate(window, trigger_type),
            raw_excerpt=_excerpt(text, m.start(), m.end()),
            start_index=m.start(), end_index=m.end(),
            section_label=_section_label_before(text, m.start()),
        ))
        seen_spans.append((m.start(), m.end()))

    for m in _MUTUAL_RIGHT_RE.finditer(text):
        if any(abs(m.start() - s) < 30 for s, _ in seen_spans):
            continue
        window = _right_window(text, m.start())
        trigger_type = _classify_trigger_type(window)
        rights.append(TerminationRight(
            holder_role="Either Party", holder_side=None,
            trigger_type=trigger_type,
            notice_period_days=_extract_notice_days(window),
            cure_period_days=_extract_cure_days(window),
            immediate=_is_immediate(window, trigger_type),
            raw_excerpt=_excerpt(text, m.start(), m.end()),
            start_index=m.start(), end_index=m.end(),
            section_label=_section_label_before(text, m.start()),
            is_mutual=True,
            asymmetry_reasons=_detect_right_asymmetry(window),
        ))
        seen_spans.append((m.start(), m.end()))

    survival_topics: Dict[str, SurvivalTreatment] = {}
    survival_clause_found = bool(_SURVIVAL_ANCHOR_RE.search(text))
    if survival_clause_found:
        anchor_m = _SURVIVAL_ANCHOR_RE.search(text)
        survival_window = text[max(0, anchor_m.start() - 100):min(len(text), anchor_m.start() + 800)]
        for topic, topic_re in _SURVIVAL_TOPIC_RE.items():
            survival_topics[topic] = SurvivalTreatment(topic=topic, present=bool(topic_re.search(survival_window)))
    else:
        for topic in SURVIVAL_TOPICS:
            survival_topics[topic] = SurvivalTreatment(topic=topic, present=False)

    fee = TerminationFee(kind="not_mentioned")
    if _FEE_MENTION_RE.search(text):
        if _FEE_UNLIMITED_RE.search(text):
            fee = TerminationFee(kind="unlimited")
        else:
            mult = _FEE_MULTIPLIER_RE.search(text)
            fixed = _FEE_FIXED_RE.search(text)
            candidates = [c for c in (mult, fixed) if c is not None]
            if not candidates:
                fee = TerminationFee(kind="not_stated")
            else:
                first = min(candidates, key=lambda m: m.start())
                if first is mult:
                    value = mult.group(1) or mult.group(2)
                    fee = TerminationFee(kind="multiplier", multiplier=float(value), raw_excerpt=_excerpt(text, mult.start(), mult.end()))
                else:
                    fee = TerminationFee(kind="fixed", fixed_amount=float(fixed.group(1).replace(",", "")), raw_excerpt=_excerpt(text, fixed.start(), fixed.end()))

    transition_assistance = bool(_TRANSITION_ASSISTANCE_RE.search(text))

    if not rights:
        return TerminationFacts(
            clause_found=True, rights=[], survival_topics=survival_topics,
            survival_clause_found=survival_clause_found, fee=fee,
            transition_assistance=transition_assistance,
        )

    rights.sort(key=lambda r: r.start_index)
    return TerminationFacts(
        clause_found=True, rights=rights, survival_topics=survival_topics,
        survival_clause_found=survival_clause_found, fee=fee,
        transition_assistance=transition_assistance,
    )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _fmt_days(value: Optional[int]) -> str:
    return "unspecified" if value is None else f"{value} days"


def _build_ladder(policy: TerminationPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", f"Preferred termination fee: {_fmt_days(None) if policy.fee_preferred_multiplier is None else f'{policy.fee_preferred_multiplier:g}x annual fees'}"),
        ("ACCEPTABLE", "Auto-accept within acceptable termination terms"),
        ("FALLBACK", "Negotiate termination terms within fallback range"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Prohibited termination terms" if policy.prohibit_uncapped_termination_fee else "Uncapped termination fee"),
    ]
    return _core_build_ladder(state, step_specs)


def _resolve_rights_for_side(
    rights: List[TerminationRight], contract_side: str,
) -> Tuple[List[TerminationRight], List[TerminationRight], List[str]]:
    """Resolves rights into (our_rights, counterparty_rights,
    unresolved_reasons). A mutual right without asymmetry applies to
    both lists (it's simultaneously ours and theirs). Never guesses: an
    unmappable holder role under a directional policy, or a directional
    right under a mutual policy, contributes a reason instead of being
    silently assigned to a side."""
    reasons: List[str] = []
    our_rights: List[TerminationRight] = []
    their_rights: List[TerminationRight] = []

    mutual = [r for r in rights if r.is_mutual]
    named = [r for r in rights if not r.is_mutual]

    for r in mutual:
        if r.asymmetry_reasons:
            reasons.append(
                f"a termination right (trigger: {r.trigger_type}) opens with reciprocal ('either party'/'each "
                f"party') language, but states materially different terms per named party ("
                + "; ".join(r.asymmetry_reasons) +
                ") — cannot confirm the right is actually symmetric"
            )
            continue
        our_rights.append(r)
        their_rights.append(r)

    if contract_side == "mutual":
        if named:
            reasons.append(
                "contract states directional (non-mutual) termination rights, but this playbook "
                "is configured for a mutual position — cannot determine which right is ours"
            )
        return our_rights, their_rights, reasons

    for r in named:
        if r.holder_side == contract_side:
            our_rights.append(r)
        elif r.holder_side is not None and r.holder_side != contract_side:
            their_rights.append(r)
        else:
            reasons.append(
                f"a termination right held by \"{r.holder_role}\" could not be mapped to our "
                f"configured contract side ({contract_side}) — unrecognized party name"
            )

    return our_rights, their_rights, reasons


def evaluate_termination_policy(
    facts: Optional[TerminationFacts],
    policy: TerminationPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    """Deterministic state machine over termination topology. Evaluates
    the counterparty's rights held AGAINST us (adequate notice, adequate
    cure — a risk to bound) and our own rights (do we have at least the
    same optionality, e.g. a mutual convenience-termination right)
    independently, then combines with the negotiation ladder for the
    termination fee — REQUIRES_REVIEW wins if any fact is unresolved,
    otherwise the most severe resolved finding governs."""
    if facts is None or not facts.clause_found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="termination", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No termination clause found",
            policy_limit_summary="N/A",
            required_action="None — this contract does not address termination",
            explanation="No termination clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="Termination treatment",
            our_position_label="Our termination rights", counterparty_position_label="Counterparty's termination rights against us",
        )

    if not facts.rights:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="termination", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Termination referenced but no right could be parsed",
            policy_limit_summary="N/A",
            required_action="Manual review required — termination language present but structure unclear",
            explanation="The document references termination but no parseable 'X may terminate this Agreement' "
                        "or reciprocal structure was found — the clause may be malformed, cross-referenced "
                        "elsewhere, or drafted in a form this extractor doesn't recognize.",
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[],
            unresolved_facts=["termination right structure could not be parsed"],
            start_index=None, end_index=None, source=source, summary_label="Termination treatment",
            our_position_label="Our termination rights", counterparty_position_label="Counterparty's termination rights against us",
        )

    our_rights, their_rights, resolution_reasons = _resolve_rights_for_side(facts.rights, policy.contract_side)
    unresolved_facts = list(resolution_reasons)

    required_survival = list(policy.required_survival_topics_json or [])
    for topic in required_survival:
        if topic in facts.survival_topics and not facts.survival_topics[topic].present:
            pass  # handled below as a confidently-observed gap, not an ambiguity

    if unresolved_facts:
        controlling = (their_rights or our_rights or facts.rights)[0]
        explanation = requires_review_explanation("termination structure", controlling.raw_excerpt, unresolved_facts)
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="termination", state=REQUIRES_REVIEW,
            contract_language=controlling.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary="N/A",
            required_action=requires_review_required_action(unresolved_facts),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved_facts,
            start_index=controlling.start_index, end_index=controlling.end_index, source=source,
            controlling_provision={"label": controlling.label(), "excerpt": controlling.raw_excerpt,
                                    "start_index": controlling.start_index, "end_index": controlling.end_index},
            summary_label="Termination treatment", our_position_label="Our termination rights",
            counterparty_position_label="Counterparty's termination rights against us",
        )

    notes: List[str] = []
    worst_state = ACCEPT

    def _worse(a: str, b: str) -> str:
        order = {ACCEPT: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, MUST_REDLINE: 3, ESCALATE: 4, PROHIBITED: 5}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    # --- Counterparty's rights against us: bound notice/cure adequacy ---
    for r in their_rights:
        if r.trigger_type == "convenience":
            if r.notice_period_days is None:
                notes.append("counterparty's convenience-termination right states no notice period at all")
                worst_state = _worse(worst_state, MUST_REDLINE)
            elif policy.min_notice_days_against_us is not None and r.notice_period_days < policy.min_notice_days_against_us:
                notes.append(
                    f"counterparty's convenience-termination notice period ({r.notice_period_days} days) is "
                    f"below our required minimum ({policy.min_notice_days_against_us} days)"
                )
                worst_state = _worse(worst_state, NEGOTIATE)
        elif r.trigger_type == "material_breach":
            if r.immediate and policy.prohibit_immediate_termination_for_cause:
                notes.append("counterparty may terminate us immediately for cause with no cure opportunity, prohibited by policy")
                worst_state = _worse(worst_state, PROHIBITED)
            elif r.immediate:
                notes.append("counterparty may terminate us immediately for cause with no cure opportunity")
                worst_state = _worse(worst_state, ESCALATE)
            elif r.cure_period_days is None:
                notes.append("counterparty's for-cause termination right states no cure period at all")
                worst_state = _worse(worst_state, MUST_REDLINE)
            elif policy.min_cure_days_against_us is not None and r.cure_period_days < policy.min_cure_days_against_us:
                notes.append(
                    f"counterparty's cure period ({r.cure_period_days} days) is below our required minimum "
                    f"({policy.min_cure_days_against_us} days)"
                )
                worst_state = _worse(worst_state, NEGOTIATE)
        # insolvency/non-payment immediate termination against us is a
        # conventional, expected risk allocation — not itself flagged.

    # --- Our own rights: do we have equivalent optionality? ---
    our_has_convenience = any(r.trigger_type == "convenience" for r in our_rights)
    their_has_convenience = any(r.trigger_type == "convenience" for r in their_rights)
    if policy.require_mutual_convenience_termination and their_has_convenience and not our_has_convenience:
        notes.append("counterparty holds a convenience-termination right but we do not — policy requires mutuality")
        worst_state = _worse(worst_state, NEGOTIATE)

    # --- Survival clause completeness ---
    if not facts.survival_clause_found and required_survival:
        notes.append("no survival clause found at all, though the policy requires specific obligations to survive termination")
        worst_state = _worse(worst_state, NEGOTIATE)
    else:
        missing_survival = [t for t in required_survival if not facts.survival_topics.get(t, SurvivalTreatment(t, False)).present]
        if missing_survival:
            notes.append(f"survival clause missing required topic(s): {', '.join(missing_survival)}")
            worst_state = _worse(worst_state, NEGOTIATE)

    # --- Termination fee ---
    if facts.fee.kind == "unlimited":
        if policy.prohibit_uncapped_termination_fee:
            notes.append("termination fee is uncapped, prohibited by policy")
            worst_state = _worse(worst_state, PROHIBITED)
        else:
            notes.append("termination fee is uncapped")
            worst_state = _worse(worst_state, ESCALATE)
    elif facts.fee.kind == "fixed":
        notes.append(f"termination fee is a fixed dollar amount ({facts.fee.summary()}), not a fees multiplier — compare manually")
        worst_state = _worse(worst_state, ESCALATE)
    elif facts.fee.kind == "multiplier":
        threshold_state = classify_by_threshold(
            facts.fee.multiplier, policy.fee_preferred_multiplier,
            policy.fee_acceptable_max_multiplier, policy.fee_negotiate_max_multiplier,
        )
        if threshold_state != ACCEPT:
            notes.append(f"termination fee {facts.fee.summary()} exceeds preferred position")
        worst_state = _worse(worst_state, threshold_state)
    elif facts.fee.kind == "not_stated":
        notes.append("a termination fee is referenced but no amount is stated")
        worst_state = _worse(worst_state, MUST_REDLINE)
    # "not_mentioned" (no termination fee at all) is the common case and
    # is never itself penalized.

    controlling = (their_rights or our_rights or facts.rights)[0]
    extracted_summary = (
        f"Our rights: {len(our_rights)}; Counterparty rights against us: {len(their_rights)}; "
        f"Fee: {facts.fee.summary()}"
    )
    if worst_state == ACCEPT and not notes:
        required_action = "None — termination terms meet policy"
        explanation = f"Contract language: \"{controlling.raw_excerpt}\". No policy gaps found. Result: {ACCEPT}."
    else:
        if worst_state in (ESCALATE, PROHIBITED):
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — " + "; ".join(notes)
        elif worst_state == NEGOTIATE:
            required_action = "Negotiate — " + "; ".join(notes)
        else:
            required_action = "None — within acceptable range, note for the file: " + "; ".join(notes)
        explanation = f"Contract language: \"{controlling.raw_excerpt}\". {'; '.join(notes)}. Result: {worst_state}."

    return PolicyDecision(
        rule_id=RULE_ID, clause_type="termination", state=worst_state,
        contract_language=controlling.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary=_fmt_days(policy.min_notice_days_against_us),
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, worst_state),
        category_treatments=[
            {"category": r.trigger_type, "treatment": "immediate" if r.immediate else "notice_and_cure",
             "cap_summary": None, "raw_excerpt": r.raw_excerpt, "established": True}
            for r in their_rights
        ],
        unresolved_facts=[], start_index=controlling.start_index, end_index=controlling.end_index,
        escalate_to=escalate_to_for_state(worst_state, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(worst_state, policy.fallback_text, (NEGOTIATE, ESCALATE, PROHIBITED)),
        source=source,
        controlling_provision={"label": controlling.label(), "excerpt": controlling.raw_excerpt,
                                "start_index": controlling.start_index, "end_index": controlling.end_index},
        our_position={"role": our_rights[0].holder_role, "summary": f"{len(our_rights)} right(s)"} if our_rights else None,
        counterparty_position={"role": their_rights[0].holder_role, "summary": f"{len(their_rights)} right(s)"} if their_rights else None,
        summary_label="Termination treatment", our_position_label="Our termination rights",
        counterparty_position_label="Counterparty's termination rights against us",
    )
