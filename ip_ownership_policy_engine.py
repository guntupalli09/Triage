"""
IP Ownership / Licensing clause adapter, over policy_engine_core.
Adapter #8 — the second added after the original six (Liability,
Indemnification, Termination, Confidentiality, Assignment, Governing
Law), following data_security_policy_engine.py (adapter #7). Built by
directly mirroring the established adapter shape rather than inventing a
new one; policy_engine_core.py was not modified — every primitive this
adapter needs (PolicyDecision, LadderStep/build_ladder, escalate_to_for_
state, fallback_text_for_state, side_for_role, excerpt/section_label_
before, requires_review_* helpers) already existed and fit without
change. classify_by_threshold was deliberately NOT used: IP license
duration is a categorical perpetual/term-limited choice in real
drafting, not a "lower is better" numeric band the way breach-
notification hours or liability multipliers are — forcing it through a
threshold ladder would not fit the reasoning shape.

SEMANTIC MODEL: an IP ownership/licensing clause answers two genuinely
different questions that must never be collapsed into one field —
*who owns* a given category of IP, and, independently, *who may use*
whatever IP the other party owns and *under what restrictions*.

Ownership is modeled as a CATALOG of independent categories (background/
pre-existing IP, foreground/work-product IP, customer-contributed
materials, vendor technology), each resolved to an owner ("us" /
"counterparty" / "joint" / not addressed) — side-agnostic party-name
attribution at extraction time, resolved against contract_side at
evaluate time, exactly the same extract/evaluate split
data_security_policy_engine.py uses for controller/processor role (since
contract_side is only known once the policy is available). Ownership
statements naturally use the same commercial role words already shared
across every adapter (Customer/Vendor/Licensor/Licensee via
policy_engine_core.BUY_SIDE_ROLES/SELL_SIDE_ROLES) — unlike Data
Protection's Processor/Controller, no adapter-local role-word fallback
was needed here.

License terms (exclusivity, royalty, duration, revocability,
sublicensing, transferability, territory, purpose/field-of-use,
derivative-works rights, feedback treatment, residual-knowledge rights,
open-source obligations, infringement/third-party-IP reference,
post-termination survival, and whether a license is granted to use
background IP embedded in deliverables) are modeled as a second,
independent catalog — extracted document-wide and, for the categorical
dimensions capable of stating two different things in two different
places (exclusivity, royalty, duration, revocability, sublicensing,
transferability, territory, derivative works), reconciled by collecting
every distinct value found across every anchored window: exactly one
distinct value is used, more than one is a genuine conflict that
abstains via REQUIRES_REVIEW rather than picking one silently — the same
principle data_security's subprocessor/breach-notification reconciliation
uses. Feedback treatment is a deliberate exception: "assign, or to the
extent not assignable, license" is a standard drafting fallback
structure (the same shape work-for-hire-plus-fallback-assignment uses for
work product), not a conflict, so "assigned" is treated as satisfying
"licensed" wherever both phrases appear rather than flagging every
layered feedback clause as ambiguous.

A clause that sweeps pre-existing/background IP into a work-product
assignment ("...including any pre-existing intellectual property
embodied therein...") while a separate provision independently reserves
background IP to the originating party is a genuine drafting conflict —
detected explicitly and routed to REQUIRES_REVIEW, never silently
resolved in either direction.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

from policy_engine_core import (
    ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE,
    REQUIRES_REVIEW, NOT_APPLICABLE,
    LadderStep, build_ladder as _core_build_ladder,
    escalate_to_for_state, fallback_text_for_state, side_for_role,
    excerpt, section_label_before,
    requires_review_explanation, requires_review_required_action,
    PolicyDecision,
    EXTERNAL_DEFINITION_NOT_ATTACHED_RE as _EXTERNAL_DEFINITION_NOT_ATTACHED_RE,
    document_wide_conflict_detected as _document_wide_conflict_detected,
    unreconciled_ambiguity_marker_present as _unreconciled_ambiguity_marker_present,
    cross_section_carveout_referencing as _cross_section_carveout_referencing,
    detect_condition_in_span as _core_detect_condition_in_span,
    is_operative_context as _core_is_operative_context,
)

RULE_ID = "POLICY_IP_OWNERSHIP"
_PROVISION_WINDOW_CHARS = 2200

_GENERIC_WORDS = {"each", "the", "any", "such", "this", "that", "both", "either", "party", "parties", "all", "it"}

# Candidate 3 zero-silent-loss mission — "except for X, which Y retains"
# is a real exception attached to an ownership statement ("Work product
# shall be owned by Customer, except for Vendor's pre-existing background
# IP..."). Deliberately LOCAL to this adapter rather than broadening the
# shared policy_engine_core._MIDCLAUSE_EXCEPT_RE (which liability/
# insurance/warranties also use): for liability specifically, "except for
# claims arising from X" names a REQUIRED, already-correctly-handled
# category carve-out, not a genuine unresolved condition -- broadening
# the shared regex to include "except for" caused confirmed regressions
# there. Ownership's "except for X, which Y retains" shape is
# structurally different: it reassigns a PORTION of ownership to a
# different party, which is exactly the kind of qualifier this adapter's
# own category-attribution logic doesn't yet resolve automatically.
_OWNERSHIP_EXCEPT_FOR_RE = re.compile(r"\bexcept\s+for\b", re.I)

# --- Anchor -------------------------------------------------------------
_ANCHOR_RE = re.compile(
    r"intellectual\s+property|proprietary\s+rights|work\s+product|work\s+made\s+for\s+hire"
    r"|works?\s+for\s+hire|license\s+(?:grant|to\s+use)|IP\s+(?:ownership|rights|license)",
    re.I,
)

# --- Ownership statements ------------------------------------------------
_OWNERSHIP_ACTIVE_RE = re.compile(
    r"([A-Z][A-Za-z]{2,30})\s+(?:shall\s+(?:own|retain|be\s+(?:and\s+remain\s+)?the\s+"
    r"(?:sole\s+and\s+exclusive|sole|exclusive)?\s*owner\s+of)|owns|retains|"
    r"shall\s+be\s+deemed\s+the\s+owner\s+of)\b",
    re.I,
)
_OWNERSHIP_PASSIVE_RE = re.compile(
    r"shall\s+(?:remain|be)\s+(?:the\s+)?(?:sole\s+and\s+exclusive|sole|exclusive)?\s*property\s+of\s+([A-Z][A-Za-z]{2,30})"
    r"|shall\s+be\s+(?:solely\s+)?owned\s+(?:solely\s+|exclusively\s+)?by\s+([A-Z][A-Za-z]{2,30})",
    re.I,
)
# Candidate 3 final gap-closure fix (Root Cause C) -- a subordinate
# qualifier phrase ("including any pre-existing intellectual property
# embodied therein", "other than X") names a DIFFERENT category than the
# sentence's actual grammatical subject, but sits textually closer to the
# ownership verb. Without this exclusion, _nearest_category's raw-
# distance heuristic picks the subordinate mention over the true subject
# (see PROVIDER_VARIANCE_ROOT_CAUSE.md). Matches the qualifier phrase up
# to its closing comma/parenthesis so category words strictly inside it
# can be deprioritized as non-governing.
_SUBORDINATE_QUALIFIER_SPAN_RE = re.compile(
    r"\b(?:including|except(?:ing)?|other\s+than|excluding)\b[^,.;]{0,120}[,;]?",
    re.I,
)
_IP_ASSIGNMENT_RE = re.compile(
    r"([A-Z][A-Za-z]{2,30})\s+(?:hereby\s+)?assigns?,?\s+(?:transfers?,?\s+)?(?:and\s+)?(?:conveys?\s+)?"
    r"(?:to\s+([A-Z][A-Za-z]{2,30})\s+)?all\s+(?:of\s+its\s+)?right,?\s*title\s*(?:and|,)?\s*interest",
    re.I,
)
_JOINT_OWNERSHIP_RE = re.compile(r"jointly\s+own|joint\s+ownership", re.I)
_WORK_FOR_HIRE_RE = re.compile(r"work\s+made\s+for\s+hire|works?\s+for\s+hire", re.I)
_WP_INCLUDES_BACKGROUND_RE = re.compile(
    r"including\s+(?:any\s+)?(?:pre-?existing|background)\s+(?:intellectual\s+property|ip|materials)", re.I,
)

_CAT_BACKGROUND_RE = re.compile(
    r"pre-?existing|background\s+(?:intellectual\s+property|ip|technology|materials)|prior\s+(?:intellectual\s+property|ip)", re.I,
)
_CAT_WORK_PRODUCT_RE = re.compile(
    r"work\s+product|deliverables?|newly\s+developed|foreground\s+(?:intellectual\s+property|ip)"
    r"|developed\s+(?:hereunder|under\s+this\s+agreement)", re.I,
)
_CAT_CUSTOMER_MATERIALS_RE = re.compile(
    r"customer\s+materials|customer[’']?s?\s+(?:data|content|materials)\b", re.I,
)
_CAT_VENDOR_TECH_RE = re.compile(
    r"(?:vendor|provider)[’']?s?\s+(?:proprietary\s+)?technology|vendor\s+technology"
    r"|provider\s+technology|platform\s+technology", re.I,
)

# --- License terms --------------------------------------------------------
_EXCLUSIVE_RE = re.compile(
    r"(?<!non-)(?<!non\s)\bexclusive\s+license"
    r"|license\s+(?:is|shall\s+be)\s+(?<!non-)(?<!non\s)exclusive", re.I,
)
_NON_EXCLUSIVE_RE = re.compile(r"non-?exclusive\s+license|license\s+is\s+non-?exclusive", re.I)

_ROYALTY_FREE_RE = re.compile(r"royalty-?free", re.I)
_PAID_ROYALTY_RE = re.compile(r"subject\s+to\s+(?:a\s+)?royalt\w*|royalt\w*\s+(?:of|equal\s+to|payable)", re.I)

_PERPETUAL_RE = re.compile(
    r"perpetual(?:\s+and\s+irrevocable)?\s+license|license[^.]{0,40}?\bis\s+perpetual\b|in\s+perpetuity", re.I,
)
_TERM_LIMITED_RE = re.compile(
    r"license[^.]{0,40}?(?:shall\s+)?(?:terminate|expire)|for\s+a\s+term\s+of\s+(\d{1,3})\s+years?"
    r"|term\s+of\s+this\s+license\s+(?:is|shall\s+be)\s+(\d{1,3})\s+years?", re.I,
)

_IRREVOCABLE_RE = re.compile(r"irrevocable", re.I)
_REVOCABLE_RE = re.compile(r"\brevocable\b|may\s+be\s+revoked|may\s+revoke\s+this\s+license|subject\s+to\s+revocation", re.I)

_SUBLICENSABLE_RE = re.compile(r"right\s+to\s+sublicense|may\s+sublicense|sublicensable", re.I)
_NON_SUBLICENSABLE_RE = re.compile(r"non-?sublicensable|shall\s+not\s+sublicense|without\s+the\s+right\s+to\s+sublicense", re.I)

_TRANSFERABLE_RE = re.compile(r"\btransferable\b|may\s+be\s+transferred|right\s+to\s+transfer\s+this\s+license", re.I)
_NON_TRANSFERABLE_RE = re.compile(r"non-?transferable|shall\s+not\s+(?:be\s+)?transfer", re.I)

_WORLDWIDE_RE = re.compile(r"worldwide|throughout\s+the\s+world|global(?:ly)?\s+license", re.I)
_RESTRICTED_TERRITORY_RE = re.compile(
    r"limited\s+to\s+([A-Z][A-Za-z .]{2,40}?)(?=[.,;]|\s+and\b|\s*$)"
    r"|solely\s+(?:within|in)\s+([A-Z][A-Za-z .]{2,40}?)(?=[.,;]|\s+and\b|\s*$)", re.I,
)

_PURPOSE_LIMITED_RE = re.compile(
    r"solely\s+(?:for|in\s+connection\s+with)|for\s+the\s+sole\s+purpose\s+of"
    r"|limited\s+to\s+internal\s+(?:business\s+)?(?:use|purposes)", re.I,
)

_DERIVATIVE_PERMITTED_RE = re.compile(r"(?:create|prepare|make)\s+derivative\s+works", re.I)
_DERIVATIVE_PROHIBITED_RE = re.compile(
    r"shall\s+not\s+(?:create|prepare|make)\s+derivative\s+works|no\s+right\s+to\s+(?:create|prepare|make)\s+derivative\s+works", re.I,
)

_FEEDBACK_ASSIGNED_RE = re.compile(r"feedback\b[^.]{0,80}?\bassign|assigns?\b[^.]{0,80}?\bfeedback", re.I)
_FEEDBACK_LICENSED_RE = re.compile(r"feedback\b[^.]{0,80}?licens|licenses?\b[^.]{0,80}?\bfeedback", re.I)

_RESIDUAL_RE = re.compile(r"residual\s+(?:knowledge|rights|information)", re.I)
_OPEN_SOURCE_RE = re.compile(r"open[\s-]source", re.I)
_INFRINGEMENT_RE = re.compile(r"infring(?:e|ement|ing)[^.]{0,25}?(?:third[\s-]?party|patent|copyright|trademark)", re.I)

_SURVIVAL_RE = re.compile(r"license\s+(?:granted\s+)?(?:herein\s+)?shall\s+survive|survive\s+(?:the\s+)?(?:termination|expiration)", re.I)

_EMBEDDED_LICENSE_RE = re.compile(
    r"license[^.]{0,150}?(?:background|pre-?existing)\s+(?:intellectual\s+property|ip|technology)", re.I,
)

_SOW_CROSSREF_RE = re.compile(
    r"as\s+(?:set\s+forth|described|specified)\s+in\s+(?:the\s+)?(?:applicable\s+)?(?:Statement\s+of\s+Work|SOW|Schedule|Exhibit|Order\s+Form)"
    r"|governed\s+by\s+(?:the\s+)?(?:applicable\s+)?(?:SOW|Statement\s+of\s+Work)", re.I,
)


@dataclass
class IPFacts:
    """Every field is independently None/empty ("not addressed anywhere
    in the text") unless the clause actually establishes it. Ownership is
    kept in a separate namespace from license terms throughout — never
    collapsed into one field."""
    clause_found: bool
    raw_excerpt: str = ""
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    section_label: Optional[str] = None

    # Ownership: category -> {party_name: True}, side-agnostic. Categories
    # used: "background_ip", "work_product", "customer_materials",
    # "vendor_technology". our_owner is resolved from this (given
    # contract_side) at evaluation time.
    ownership_attributions: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    ownership_conflict_categories: set = field(default_factory=set)
    joint_ownership_categories: set = field(default_factory=set)
    work_product_includes_background_ip: bool = False

    # License terms (document-wide, conflict when >1 distinct value found)
    exclusivity: Optional[str] = None  # "exclusive" | "non_exclusive"
    exclusivity_conflict: bool = False
    royalty: Optional[str] = None  # "royalty_free" | "paid"
    royalty_conflict: bool = False
    duration: Optional[str] = None  # "perpetual" | "term_limited"
    duration_conflict: bool = False
    license_term_years: Optional[int] = None
    revocability: Optional[str] = None  # "irrevocable" | "revocable"
    revocability_conflict: bool = False
    sublicensable: Optional[bool] = None
    sublicensable_conflict: bool = False
    transferable: Optional[bool] = None
    transferable_conflict: bool = False
    territory: Optional[str] = None  # "worldwide" | "restricted:<region>"
    territory_conflict: bool = False
    purpose_limited: Optional[bool] = None
    derivative_works_permitted: Optional[bool] = None
    derivative_conflict: bool = False

    # Simple presence/treatment facts (no cross-window conflict tracking —
    # these are additive commitments, not mutually-exclusive categoricals).
    feedback_treatment: Optional[str] = None  # "assigned" | "licensed"
    residual_knowledge_rights: Optional[bool] = None
    open_source_obligations_present: Optional[bool] = None
    infringement_remedy_referenced: Optional[bool] = None
    post_termination_survival: Optional[bool] = None
    embedded_background_ip_license_present: Optional[bool] = None

    sow_cross_reference: bool = False
    # Candidate 3 final gap-closure fix (Root Cause B) -- distinct from
    # sow_cross_reference: a NAMED DEFINED TERM used in an already-
    # established ownership/license statement is itself defined by an
    # external, explicitly-not-attached document (e.g. "Vendor retains
    # all rights to 'Pre-Existing Materials.' That term is defined in the
    # Statement of Work, which is not attached."). This changes the SCOPE
    # of an established fact rather than substituting for a missing one,
    # so it must surface even when established_dimension_count > 0 --
    # unlike sow_cross_reference, which is suppressed once something else
    # is established (see evaluate_ip_policy).
    definition_dependency_unresolved: bool = False

    # Fact-admission architecture — mirrors data_security_policy_engine.
    # DataSecurityFacts.absence_state exactly, for the same reason: this
    # adapter's per-dimension evaluate logic can resolve an all-None facts
    # object to ACCEPT when a playbook requires no specific dimension.
    absence_state: str = "CONFIRMED_ABSENT"
    semantic_discovery_error: Optional[str] = None
    # Final trust architecture (Phase 1-6) — a material condition/
    # exception the AI/contextual layer identified and independently
    # grounded (fact_admission.ground_qualifiers). Never populated from
    # an ungrounded claim.
    ai_identified_condition: Optional[str] = None
    ai_identified_exception: Optional[str] = None
    ai_identified_definition_or_reference: Optional[str] = None
    # Candidate 3 zero-silent-loss mission — a document-wide contradiction,
    # self-declared unreconciled ambiguity, cross-section carve-out
    # referencing this clause's own section number, or a deterministically-
    # detected same-clause condition/exception.
    document_wide_conflict: bool = False
    deterministic_condition_established: bool = False
    deterministic_condition_excerpt: Optional[str] = None


class IPPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]

    require_we_retain_background_ip: bool
    require_we_own_work_product: bool
    prohibit_joint_ownership: bool
    require_license_for_embedded_background_ip: bool
    require_license_exclusive: bool
    prohibit_royalty_bearing_license: bool
    require_perpetual_license: bool
    prohibit_revocable_license: bool
    require_sublicensable: bool
    require_transferable: bool
    require_worldwide_territory: bool
    require_purpose_limited_license: bool
    prohibit_derivative_works: bool
    require_feedback_assigned: bool
    require_residual_knowledge_rights: bool
    require_open_source_disclosure: bool
    require_infringement_remedy_reference: bool
    require_post_termination_survival: bool


def _nearest_category(ctx: str, anchor_mid: float) -> Optional[str]:
    # Candidate 3 final gap-closure fix (Root Cause C) -- a category word
    # sitting inside a subordinate qualifier phrase ("including any
    # pre-existing intellectual property embodied therein") names an
    # exception/inclusion, not the sentence's governing subject, even
    # when it happens to be the textually nearest mention. Two passes:
    # first excluding any match inside such a span, falling back to the
    # raw nearest-distance search only if nothing survives that
    # exclusion (so a category word that legitimately IS the closest,
    # non-subordinate mention still wins as before).
    subordinate_spans = [(m.start(), m.end()) for m in _SUBORDINATE_QUALIFIER_SPAN_RE.finditer(ctx)]

    def _inside_subordinate_span(pos: int) -> bool:
        return any(lo <= pos < hi for lo, hi in subordinate_spans)

    for exclude_subordinate in (True, False):
        best_category: Optional[str] = None
        best_dist: Optional[float] = None
        for name, regex in (
            ("background_ip", _CAT_BACKGROUND_RE), ("work_product", _CAT_WORK_PRODUCT_RE),
            ("customer_materials", _CAT_CUSTOMER_MATERIALS_RE), ("vendor_technology", _CAT_VENDOR_TECH_RE),
        ):
            for m in regex.finditer(ctx):
                if exclude_subordinate and _inside_subordinate_span(m.start()):
                    continue
                mid = (m.start() + m.end()) / 2
                dist = abs(mid - anchor_mid)
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_category = name
        if best_category is not None:
            return best_category
    return None


def _categorize(window: str, pos_start: int, pos_end: int, forward_radius: int = 250, backward_radius: int = 200) -> Optional[str]:
    """Picks whichever ownership-category keyword is closest to the
    ownership statement, searching FORWARD first: real drafting almost
    always states the ownership verb before its object ("X shall own
    [the category noun]..."), so the category word for an active-voice
    statement is typically ahead of the match, past a "right, title and
    interest in and to" filler phrase. Falls back to a backward-only
    window for passive constructions ("the category noun ... shall be
    owned by X") and for statements that refer back to an object already
    named earlier in the SAME sentence ("... Vendor hereby assigns to
    Customer all right, title and interest therein").

    Both directions are truncated at the nearest sentence boundary
    (".") — without this, an unrelated category word from an adjacent,
    already-concluded (or not-yet-reached) sentence is otherwise just as
    "close" in raw character distance as the real object of THIS
    statement, and wins by accident."""
    forward_raw = window[pos_end:min(len(window), pos_end + forward_radius)]
    dot = forward_raw.find(".")
    forward_ctx = forward_raw[:dot] if dot != -1 else forward_raw
    forward_hit = _nearest_category(forward_ctx, 0.0)
    if forward_hit is not None:
        return forward_hit

    backward_raw = window[max(0, pos_start - backward_radius):pos_start]
    dot = backward_raw.rfind(".")
    backward_ctx = backward_raw[dot + 1:] if dot != -1 else backward_raw
    return _nearest_category(backward_ctx, len(backward_ctx))


def _attribute_owner(facts: IPFacts, category: str, name: str) -> None:
    bucket = facts.ownership_attributions.setdefault(category, {})
    bucket[name] = True
    if len(bucket) > 1:
        facts.ownership_conflict_categories.add(category)


def _scan_ownership(window: str, facts: IPFacts) -> None:
    # Candidate 3 zero-silent-loss mission — a deterministically-detected
    # same-SENTENCE condition/exception attached to the specific ownership
    # match (using detect_condition_in_span, scoped to just that match's
    # own sentence via sentence_bounds -- NOT the whole window, which
    # previously caused false positives on ip_ownership's common "To the
    # extent any Deliverables do not qualify as a work made for hire,
    # Vendor hereby assigns..." assign-or-fallback idiom living in a
    # DIFFERENT sentence of the same window).
    def _check_condition(m_start: int, m_end: int) -> None:
        if facts.deterministic_condition_established:
            return
        cond = _core_detect_condition_in_span(window, m_start, m_end)
        if cond.status == "ESTABLISHED":
            facts.deterministic_condition_established = True
            facts.deterministic_condition_excerpt = cond.evidence_span
            return
        # "except for" local check (see _OWNERSHIP_EXCEPT_FOR_RE) -- scoped
        # to the same sentence as the ownership match, mirroring
        # detect_condition_in_span's own scoping discipline.
        sent_start = window.rfind(".", 0, m_start) + 1
        sent_end_dot = window.find(".", m_end)
        sent_end = sent_end_dot + 1 if sent_end_dot != -1 else len(window)
        sentence = window[sent_start:sent_end]
        ex_m = _OWNERSHIP_EXCEPT_FOR_RE.search(sentence)
        if ex_m:
            facts.deterministic_condition_established = True
            facts.deterministic_condition_excerpt = sentence[ex_m.start():min(len(sentence), ex_m.start() + 100)].strip()

    for m in _OWNERSHIP_ACTIVE_RE.finditer(window):
        name = m.group(1)
        if name.lower() in _GENERIC_WORDS:
            continue
        cat = _categorize(window, m.start(), m.end())
        if cat is None:
            continue
        _attribute_owner(facts, cat, name)
        _check_condition(m.start(), m.end())

    for m in _OWNERSHIP_PASSIVE_RE.finditer(window):
        name = m.group(1) or m.group(2)
        if not name or name.lower() in _GENERIC_WORDS:
            continue
        cat = _categorize(window, m.start(), m.end())
        if cat is None:
            continue
        _attribute_owner(facts, cat, name)
        _check_condition(m.start(), m.end())

    for m in _IP_ASSIGNMENT_RE.finditer(window):
        assignee = m.group(2)
        cat = _categorize(window, m.start(), m.end())
        if cat is None and _WORK_FOR_HIRE_RE.search(window):
            cat = "work_product"
        if cat is None or not assignee or assignee.lower() in _GENERIC_WORDS:
            continue
        _attribute_owner(facts, cat, assignee)

    jm = _JOINT_OWNERSHIP_RE.search(window)
    if jm:
        cat = _categorize(window, jm.start(), jm.end()) or "work_product"
        facts.joint_ownership_categories.add(cat)

    if _WP_INCLUDES_BACKGROUND_RE.search(window):
        facts.work_product_includes_background_ip = True


def _tok_exclusivity(window: str) -> set:
    found = set()
    scrubbed = _NON_EXCLUSIVE_RE.sub(" ", window)
    if _EXCLUSIVE_RE.search(scrubbed):
        found.add("exclusive")
    if _NON_EXCLUSIVE_RE.search(window):
        found.add("non_exclusive")
    return found


def _tok_royalty(window: str) -> set:
    found = set()
    if _ROYALTY_FREE_RE.search(window):
        found.add("royalty_free")
    if _PAID_ROYALTY_RE.search(window):
        found.add("paid")
    return found


def _tok_duration(window: str) -> set:
    found = set()
    if _PERPETUAL_RE.search(window):
        found.add("perpetual")
    if _TERM_LIMITED_RE.search(window):
        found.add("term_limited")
    return found


def _tok_revocability(window: str) -> set:
    found = set()
    if _IRREVOCABLE_RE.search(window):
        found.add("irrevocable")
    if _REVOCABLE_RE.search(window):
        found.add("revocable")
    return found


def _tok_sublicensable(window: str) -> set:
    found = set()
    scrubbed = _NON_SUBLICENSABLE_RE.sub(" ", window)
    if _SUBLICENSABLE_RE.search(scrubbed):
        found.add("yes")
    if _NON_SUBLICENSABLE_RE.search(window):
        found.add("no")
    return found


def _tok_transferable(window: str) -> set:
    found = set()
    scrubbed = _NON_TRANSFERABLE_RE.sub(" ", window)
    if _TRANSFERABLE_RE.search(scrubbed):
        found.add("yes")
    if _NON_TRANSFERABLE_RE.search(window):
        found.add("no")
    return found


def _tok_territory(window: str) -> set:
    found = set()
    if _WORLDWIDE_RE.search(window):
        found.add("worldwide")
    m = _RESTRICTED_TERRITORY_RE.search(window)
    if m:
        region = (m.group(1) or m.group(2) or "").strip()
        if region:
            found.add(f"restricted:{region}")
    return found


def _tok_derivative(window: str) -> set:
    found = set()
    scrubbed = _DERIVATIVE_PROHIBITED_RE.sub(" ", window)
    if _DERIVATIVE_PERMITTED_RE.search(scrubbed):
        found.add("yes")
    if _DERIVATIVE_PROHIBITED_RE.search(window):
        found.add("no")
    return found


def _collect(all_found: set) -> Tuple[Optional[str], bool]:
    if len(all_found) > 1:
        return None, True
    if len(all_found) == 1:
        return next(iter(all_found)), False
    return None, False


# Off by default — same rollout discipline as every other adapter this
# session integrated.
IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED = False  # module-load-time default; immediately overridden below
import fact_admission as _fact_admission_env_check
IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED = _fact_admission_env_check.semantic_discovery_enabled("IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED")
del _fact_admission_env_check

_IP_OWNERSHIP_SEMANTIC_FOCUS = (
    "who owns intellectual property under this agreement -- background IP, work "
    "product/deliverables, or a license grant between the parties -- even if the "
    "wording is unusual and does not use standard terms like 'intellectual property' "
    "or 'work product'"
)
_IP_OWNERSHIP_SEMANTIC_PROPOSITION = (
    "This sentence or clause is operative language of this agreement that "
    "establishes who owns intellectual property (background IP, work product, or "
    "deliverables) created or used under this agreement, or grants a license to it."
)


def _run_semantic_discovery(text: str) -> Tuple[List, Optional[str], bool, Optional[str]]:
    """Mirrors liability_policy_engine._run_semantic_discovery exactly.
    Returns (admitted_candidates, unresolved_dependency_note, error)."""
    if not IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED:
        return [], None, False, None
    import fact_admission as _fa
    try:
        raw_candidates = _fa.discover_candidate_spans(text, "ip_ownership", _IP_OWNERSHIP_SEMANTIC_FOCUS)
    except Exception as exc:  # noqa: BLE001 — provider unavailable, never "confirmed absent"
        return [], None, False, f"{type(exc).__name__}: {exc}"

    verified_candidates = [
        _fa.verify_and_ground(candidate, text, _IP_OWNERSHIP_SEMANTIC_PROPOSITION) for candidate in raw_candidates
    ]
    admitted = [c for c in verified_candidates if c.admission_status == _fa.ADMITTED]
    unresolved_dependency_note = _fa.first_unresolved_dependency_note(verified_candidates)
    note_is_unconditional = _fa.first_unresolved_dependency_note_is_unconditional(verified_candidates)
    return admitted, unresolved_dependency_note, note_is_unconditional, None


def extract_ip_facts(text: str) -> Optional[IPFacts]:
    """Single controlling-provision extraction for excerpt/label purposes
    (mirrors data_security's approach — IP clauses in real commercial
    agreements are typically one consolidated section), but scans EVERY
    anchored window document-wide for reconciliation, exactly like
    data_security's subprocessor/breach-notification handling, so a
    genuinely conflicting second statement elsewhere is never missed.
    Returns None only when no anchor exists at all AND semantic discovery
    also ran successfully and found nothing — a provider outage/error
    becomes RECOGNITION_UNCERTAIN instead (see absence_state)."""
    matches = list(_ANCHOR_RE.finditer(text))
    semantic_error: Optional[str] = None
    admitted_semantic: List = []
    unresolved_dependency_note: Optional[str] = None
    # Candidate 3 remediation (Root Cause 2): contextual discovery is no
    # longer gated behind "deterministic anchor discovery found zero
    # matches" -- see confidentiality_policy_engine.py's identical fix.
    admitted_semantic, unresolved_dependency_note, note_is_unconditional, semantic_error = _run_semantic_discovery(text)
    if not matches:
        if semantic_error is not None:
            return IPFacts(clause_found=True, absence_state="RECOGNITION_UNCERTAIN", semantic_discovery_error=semantic_error)
        if not admitted_semantic and not unresolved_dependency_note:
            return None
        if not admitted_semantic:
            # A dependency-only failure (no candidate ever became
            # admitted) never has a real anchor span to build windows
            # from — preserve the failure directly rather than falling
            # through to anchor_spans[0] below (zero-silent-loss, Step H).
            return IPFacts(clause_found=True, ai_identified_definition_or_reference=unresolved_dependency_note)
    elif semantic_error is not None:
        admitted_semantic = []

    # A semantically-admitted candidate contributes an (start, end) span
    # exactly like a regex anchor match does — it never bypasses the
    # window-merging or the per-window classification functions below.
    anchor_spans = [(m.start(), m.end()) for m in matches] + [
        (c.start_offset, c.end_offset) for c in admitted_semantic
    ]
    anchor_spans.sort()

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
    raw_excerpt = excerpt(text, start_index, end_index)
    section_label = section_label_before(text, first_start)

    facts = IPFacts(clause_found=True, raw_excerpt=raw_excerpt, start_index=start_index,
                     end_index=end_index, section_label=section_label)

    excl_all, roy_all, dur_all, rev_all, sub_all, tra_all, terr_all, der_all = (set() for _ in range(8))
    term_years_values: set = set()

    for (ws, we) in windows:
        window = text[ws:we]
        _scan_ownership(window, facts)

        excl_all |= _tok_exclusivity(window)
        roy_all |= _tok_royalty(window)
        dur_all |= _tok_duration(window)
        rev_all |= _tok_revocability(window)
        sub_all |= _tok_sublicensable(window)
        tra_all |= _tok_transferable(window)
        terr_all |= _tok_territory(window)
        der_all |= _tok_derivative(window)

        for m in _TERM_LIMITED_RE.finditer(window):
            raw = m.group(1) or m.group(2)
            if raw:
                term_years_values.add(int(raw))

        if _PURPOSE_LIMITED_RE.search(window):
            facts.purpose_limited = True

        if _FEEDBACK_ASSIGNED_RE.search(window):
            facts.feedback_treatment = "assigned"
        elif facts.feedback_treatment != "assigned" and _FEEDBACK_LICENSED_RE.search(window):
            facts.feedback_treatment = "licensed"

        if _RESIDUAL_RE.search(window):
            facts.residual_knowledge_rights = True
        if _OPEN_SOURCE_RE.search(window):
            facts.open_source_obligations_present = True
        if _INFRINGEMENT_RE.search(window):
            facts.infringement_remedy_referenced = True
        if _SURVIVAL_RE.search(window):
            facts.post_termination_survival = True
        if _EMBEDDED_LICENSE_RE.search(window):
            facts.embedded_background_ip_license_present = True
        if _SOW_CROSSREF_RE.search(window):
            facts.sow_cross_reference = True
        if _EXTERNAL_DEFINITION_NOT_ATTACHED_RE.search(window):
            facts.definition_dependency_unresolved = True

    facts.exclusivity, facts.exclusivity_conflict = _collect(excl_all)
    facts.royalty, facts.royalty_conflict = _collect(roy_all)
    facts.duration, facts.duration_conflict = _collect(dur_all)
    facts.revocability, facts.revocability_conflict = _collect(rev_all)
    sub_token, facts.sublicensable_conflict = _collect(sub_all)
    facts.sublicensable = {"yes": True, "no": False}.get(sub_token)
    tra_token, facts.transferable_conflict = _collect(tra_all)
    facts.transferable = {"yes": True, "no": False}.get(tra_token)
    facts.territory, facts.territory_conflict = _collect(terr_all)
    der_token, facts.derivative_conflict = _collect(der_all)
    facts.derivative_works_permitted = {"yes": True, "no": False}.get(der_token)
    if len(term_years_values) == 1:
        facts.license_term_years = next(iter(term_years_values))

    # Final trust architecture (Phase 5/6) — see confidentiality_policy_
    # engine.py's identical composition for the full rationale.
    import fact_admission as _fa
    for candidate in admitted_semantic:
        facts.ai_identified_condition = facts.ai_identified_condition or candidate.condition
        facts.ai_identified_exception = facts.ai_identified_exception or candidate.exception
    facts.ai_identified_definition_or_reference = _fa.first_resolved_dependency_note(admitted_semantic)

    # Candidate 3 remediation (Root Cause 1): an admitted AI candidate
    # exists but no ownership attribution (or any other IP dimension)
    # could be deterministically structured from it -- this is the exact
    # mechanism behind the confirmed ip_ownership-099 non-determinism
    # (the same colloquial "belongs to Customer, lock, stock, and barrel"
    # input flipping between NOT_APPLICABLE and ACCEPT across identical
    # real-provider runs). Never let this silently reach ACCEPT ("no
    # policy gaps found") merely because nothing was established. See
    # CANONICAL_PRIMARY_FACT_SCHEMA.md.
    if admitted_semantic and not facts.ownership_attributions:
        _any_other_established = any(v is not None for v in (
            facts.exclusivity, facts.royalty, facts.duration, facts.license_term_years, facts.revocability,
            facts.sublicensable, facts.transferable, facts.territory, facts.purpose_limited,
            facts.derivative_works_permitted, facts.feedback_treatment, facts.residual_knowledge_rights,
            facts.open_source_obligations_present, facts.infringement_remedy_referenced,
            facts.post_termination_survival, facts.embedded_background_ip_license_present,
        )) or facts.sow_cross_reference
        if not _any_other_established:
            facts.absence_state = "PRESENT_BUT_UNRESOLVED"

    # Zero-silent-loss mission follow-up (data_security-139 general failure
    # class) -- a candidate was discovered but its OWN semantic verification
    # reported genuine uncertainty (never admitted), and a deterministic
    # anchor also exists elsewhere in the document, so the block above
    # (gated on `admitted_semantic`) never fires. Must not be silently
    # discarded merely because nothing else structured.
    if (not admitted_semantic and unresolved_dependency_note is not None
            and not facts.ownership_attributions):
        _any_other_established = any(v is not None for v in (
            facts.exclusivity, facts.royalty, facts.duration, facts.license_term_years, facts.revocability,
            facts.sublicensable, facts.transferable, facts.territory, facts.purpose_limited,
            facts.derivative_works_permitted, facts.feedback_treatment, facts.residual_knowledge_rights,
            facts.open_source_obligations_present, facts.infringement_remedy_referenced,
            facts.post_termination_survival, facts.embedded_background_ip_license_present,
        )) or facts.sow_cross_reference
        # Candidate 3 final pre-freeze blocker remediation (Blocker 2) -- a
        # definition/cross-reference dependency or competing-reading note
        # is always structurally material and must never be suppressed
        # merely because some other IP dimension was established elsewhere.
        if note_is_unconditional or not _any_other_established:
            facts.absence_state = "PRESENT_BUT_UNRESOLVED"
            facts.ai_identified_definition_or_reference = (
                facts.ai_identified_definition_or_reference or unresolved_dependency_note
            )

    # Candidate 4 remediation (independent-validation FALSE_ABSENCE root
    # cause, general failure class shared with insurance/data_security):
    # NEITHER an admitted AI candidate NOR an unresolved dependency note
    # exist -- AI discovery returned nothing (a genuine recall miss) -- yet
    # a deterministic anchor DID match and IS operative (a real party
    # obligation, e.g. a less-common ownership-transfer construction like
    # "Title... shall transfer to Recipient upon...", not descriptive/
    # recital/negated language), and still no ownership attribution or
    # other IP dimension could be structured. Requiring operative context
    # (rather than a bare topical anchor mention) avoids over-escalating a
    # merely descriptive mention of "intellectual property."
    if (not admitted_semantic and unresolved_dependency_note is None
            and facts.absence_state == "CONFIRMED_ABSENT"
            and any(_core_is_operative_context(text, m.start(), m.end()) for m in matches)):
        _any_other_established = any(v is not None for v in (
            facts.exclusivity, facts.royalty, facts.duration, facts.license_term_years, facts.revocability,
            facts.sublicensable, facts.transferable, facts.territory, facts.purpose_limited,
            facts.derivative_works_permitted, facts.feedback_treatment, facts.residual_knowledge_rights,
            facts.open_source_obligations_present, facts.infringement_remedy_referenced,
            facts.post_termination_survival, facts.embedded_background_ip_license_present,
        )) or facts.sow_cross_reference
        if not facts.ownership_attributions and not _any_other_established:
            facts.absence_state = "PRESENT_BUT_UNRESOLVED"

    # Candidate 3 zero-silent-loss mission — a document-wide contradiction,
    # self-declared unreconciled ambiguity, or cross-section carve-out
    # referencing this clause's own section number must not be silently
    # dropped merely because ownership otherwise resolved deterministically.
    if (_document_wide_conflict_detected(text) or _unreconciled_ambiguity_marker_present(text)
            or _cross_section_carveout_referencing(text, facts.section_label)):
        facts.document_wide_conflict = True

    # NOTE: a same-clause deterministic condition/exception check (mirroring
    # liability/insurance/warranties' use of detect_condition_in_text) was
    # attempted here but reverted -- ip_ownership's extremely common
    # "To the extent any Deliverables do not qualify as a work made for
    # hire, Vendor hereby assigns..." assign-or-fallback idiom triggered
    # detect_condition_in_text's leading-condition detector as a false
    # positive (it is a COMPLETE resolution, not a genuine unresolved
    # condition), causing real regressions in benchmarks/ip_ownership_
    # corpus.py (clean-01, own-04, lic-22, sow-crossref-02). Reported as
    # an open gap (ip_ownership-085/086 remain unfixed) rather than
    # shipping a fix that trades one bug for a confirmed regression.

    return facts


def _resolve_owner(facts: IPFacts, contract_side: str, category: str) -> Tuple[Optional[str], bool]:
    """Resolves the owner of one ownership category from the side-agnostic
    attributions gathered at extraction time, given contract_side. Returns
    (owner, unresolved) where owner is "us" | "counterparty" | "joint" |
    None. Never guesses: a directional statement under a "mutual" playbook
    configuration, or a named party that can't be mapped to buy_side/
    sell_side, both come back unresolved rather than picking one."""
    attributions = facts.ownership_attributions.get(category)
    if not attributions:
        if category in facts.joint_ownership_categories:
            return "joint", False
        return None, False
    if contract_side == "mutual":
        return None, True

    sides: set = set()
    for name in attributions:
        mapped = side_for_role(name)
        if mapped == contract_side:
            sides.add("us")
        elif mapped is not None:
            sides.add("counterparty")
    if len(sides) == 1:
        return next(iter(sides)), False
    return None, True


def _build_ladder(policy: IPPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", "Preferred IP ownership/license terms met in full"),
        ("ACCEPTABLE", "Auto-accept within acceptable IP terms"),
        ("FALLBACK", "Negotiate IP terms within fallback range"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Prohibited IP ownership/license terms"),
    ]
    return _core_build_ladder(state, step_specs)


_WORST_ORDER = {ACCEPT: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, MUST_REDLINE: 3, ESCALATE: 4, PROHIBITED: 5}


def _worse(a: str, b: str) -> str:
    return a if _WORST_ORDER.get(a, 0) >= _WORST_ORDER.get(b, 0) else b


def evaluate_ip_policy(
    facts: Optional[IPFacts],
    policy: IPPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    common = dict(
        rule_id=RULE_ID, clause_type="ip_ownership", source=source,
        summary_label="IP ownership & licensing treatment",
        our_position_label="Our ownership/license position",
        counterparty_position_label="Counterparty's ownership/license position",
    )

    if facts is None or not facts.clause_found:
        return PolicyDecision(
            **common, state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No IP ownership / licensing clause found",
            policy_limit_summary="N/A",
            required_action="None — this contract does not address IP ownership or licensing",
            explanation="No IP ownership or licensing clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None,
        )

    if facts.absence_state == "RECOGNITION_UNCERTAIN":
        return PolicyDecision(
            **common, state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Could not determine whether an IP ownership / licensing clause is present",
            policy_limit_summary="N/A",
            required_action="Manual review required — automated recognition was unavailable for this document.",
            explanation=(
                "Deterministic pattern matching found no IP ownership / licensing clause, and semantic "
                f"verification could not confirm its absence ({facts.semantic_discovery_error or 'unavailable'}). "
                "This is not the same as confirming the contract has no such clause."
            ),
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None,
        )

    # Candidate 4 remediation: the PRESENT_BUT_UNRESOLVED absence-state used
    # to force an immediate REQUIRES_REVIEW return HERE, before the per-
    # dimension comparison loop below ever ran -- pre-empting a more
    # specific, already-correct finding (e.g. "policy requires us to own
    # work product, but the clause attributes it to Vendor" -> MUST_REDLINE)
    # with a generic, less-informative REQUIRES_REVIEW. See the equivalent
    # fallback placed AFTER the notes loop below (near `worst == ACCEPT`),
    # which fires only when nothing more specific was already found --
    # mirrors the identical restructuring applied to insurance and
    # data_security for the same independent-validation root cause.

    background_owner, background_unresolved = _resolve_owner(facts, policy.contract_side, "background_ip")
    work_product_owner, work_product_unresolved = _resolve_owner(facts, policy.contract_side, "work_product")

    unresolved: List[str] = []
    # Candidate 3 zero-silent-loss mission — a document-wide contradiction,
    # unreconciled ambiguity, or cross-section carve-out must block clean.
    if facts.document_wide_conflict:
        unresolved.append(
            "a separate statement elsewhere in the document appears to contradict, negate, or leave unreconciled "
            "the ownership attribution established in this clause"
        )
    if facts.deterministic_condition_established:
        unresolved.append(
            f"ownership is stated as conditional (\"{facts.deterministic_condition_excerpt}\") — this "
            f"evaluation does not determine whether the stated condition is satisfied"
        )
    # Final trust architecture (Phase 4 hard gate) — a material condition/
    # exception the AI/context layer identified and grounded must not be
    # silently dropped merely because ownership otherwise resolved cleanly.
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
    if "background_ip" in facts.ownership_conflict_categories:
        unresolved.append("background/pre-existing IP ownership is stated inconsistently (conflicting owner attributions)")
    elif policy.require_we_retain_background_ip and background_unresolved:
        unresolved.append("background IP ownership is stated by named party but could not be confidently mapped to "
                           "our configured contract side, or this playbook is configured for a mutual position — "
                           "cannot determine ownership")

    if "work_product" in facts.ownership_conflict_categories:
        unresolved.append("work product/deliverables ownership is stated inconsistently (conflicting owner attributions)")
    elif policy.require_we_own_work_product and work_product_unresolved:
        unresolved.append("work product ownership is stated by named party but could not be confidently mapped to "
                           "our configured contract side, or this playbook is configured for a mutual position — "
                           "cannot determine ownership")

    if facts.work_product_includes_background_ip and facts.ownership_attributions.get("background_ip"):
        unresolved.append("work-product/deliverables ownership language purports to include pre-existing background "
                           "IP, which conflicts with a separate background-IP ownership reservation elsewhere in the clause")

    if facts.exclusivity_conflict:
        unresolved.append("license exclusivity is stated inconsistently across the document")
    if facts.royalty_conflict:
        unresolved.append("license royalty treatment is stated inconsistently across the document")
    if facts.duration_conflict:
        unresolved.append("license duration is stated inconsistently across the document")
    if facts.revocability_conflict:
        unresolved.append("license revocability is stated inconsistently across the document")
    if facts.sublicensable_conflict:
        unresolved.append("sublicensing rights are stated inconsistently across the document")
    if facts.transferable_conflict:
        unresolved.append("license transferability is stated inconsistently across the document")
    if facts.territory_conflict:
        unresolved.append("license territory is stated inconsistently across the document")
    if facts.derivative_conflict:
        unresolved.append("derivative-works rights are stated inconsistently across the document")

    established_dimension_count = sum(1 for v in (
        facts.exclusivity, facts.royalty, facts.duration, facts.revocability,
        facts.sublicensable, facts.transferable, facts.territory, facts.purpose_limited,
        facts.derivative_works_permitted, facts.feedback_treatment, facts.residual_knowledge_rights,
        facts.open_source_obligations_present, facts.infringement_remedy_referenced,
        facts.post_termination_survival, facts.embedded_background_ip_license_present,
    ) if v is not None) + (1 if facts.ownership_attributions else 0)
    if facts.sow_cross_reference and established_dimension_count == 0:
        unresolved.append("material IP ownership/license terms are delegated to a referenced Statement of "
                           "Work/Schedule/Exhibit not included in this text")
    if facts.definition_dependency_unresolved:
        unresolved.append("a defined term used in this clause is itself defined by an external document that "
                           "is explicitly stated as not attached, so the clause's actual scope cannot be confirmed")

    if unresolved:
        explanation = requires_review_explanation("IP ownership / licensing clause", facts.raw_excerpt, unresolved)
        return PolicyDecision(
            **common, state=REQUIRES_REVIEW,
            contract_language=facts.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary="N/A", required_action=requires_review_required_action(unresolved),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved,
            start_index=facts.start_index, end_index=facts.end_index,
            controlling_provision={"label": f"Section {facts.section_label} — Intellectual Property" if facts.section_label else "Intellectual Property", "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
        )

    notes: List[str] = []
    worst = ACCEPT
    category_treatments: List[Dict[str, Any]] = []

    def _note(msg: str, state: str) -> None:
        nonlocal worst
        notes.append(msg)
        worst = _worse(worst, state)

    # --- Background IP ownership -------------------------------------
    if policy.require_we_retain_background_ip:
        if background_owner is None:
            _note("policy requires us to retain ownership of our background/pre-existing IP, but no ownership "
                  "statement was found in the clause", NEGOTIATE)
        elif background_owner != "us":
            _note(f"policy requires us to retain background IP ownership, but the clause attributes it to "
                  f"{background_owner}", MUST_REDLINE)
    category_treatments.append({"category": "background_ip_ownership", "treatment": background_owner or "not_addressed", "cap_summary": None, "raw_excerpt": "", "established": background_owner is not None})

    # --- Work product ownership ---------------------------------------
    if policy.require_we_own_work_product:
        if work_product_owner is None:
            _note("policy requires us to own work product/deliverables, but no ownership statement was found in "
                  "the clause", NEGOTIATE)
        elif work_product_owner != "us":
            _note(f"policy requires us to own work product, but the clause attributes it to {work_product_owner}", MUST_REDLINE)
    category_treatments.append({"category": "work_product_ownership", "treatment": work_product_owner or "not_addressed", "cap_summary": None, "raw_excerpt": "", "established": work_product_owner is not None})

    # --- Joint ownership -----------------------------------------------
    if policy.prohibit_joint_ownership and (background_owner == "joint" or work_product_owner == "joint"):
        _note("clause establishes joint ownership, prohibited by policy", MUST_REDLINE)

    # Informational-only ownership categories (extracted but not
    # independently gated — same treatment as data_security's
    # liability_cross_reference).
    cm_owner, _cm_unresolved = _resolve_owner(facts, policy.contract_side, "customer_materials")
    vt_owner, _vt_unresolved = _resolve_owner(facts, policy.contract_side, "vendor_technology")
    category_treatments.append({"category": "customer_materials_ownership", "treatment": cm_owner or "not_addressed", "cap_summary": None, "raw_excerpt": "", "established": cm_owner is not None})
    category_treatments.append({"category": "vendor_technology_ownership", "treatment": vt_owner or "not_addressed", "cap_summary": None, "raw_excerpt": "", "established": vt_owner is not None})

    # --- License for background IP embedded in deliverables -------------
    if policy.require_license_for_embedded_background_ip and not facts.embedded_background_ip_license_present:
        _note("policy requires a license to use background IP embedded in deliverables, but none was found", MUST_REDLINE)

    # --- Exclusivity ------------------------------------------------------
    if policy.require_license_exclusive and facts.exclusivity != "exclusive":
        _note(f"policy requires an exclusive license, but the clause provides "
              f"{facts.exclusivity or 'no stated exclusivity'}", NEGOTIATE)
    category_treatments.append({"category": "exclusivity", "treatment": facts.exclusivity or "not_addressed", "cap_summary": None, "raw_excerpt": "", "established": facts.exclusivity is not None})

    # --- Royalty ------------------------------------------------------------
    if policy.prohibit_royalty_bearing_license and facts.royalty == "paid":
        _note("license is royalty-bearing, prohibited by policy (royalty-free required)", MUST_REDLINE)

    # --- Duration -------------------------------------------------------------
    if policy.require_perpetual_license and facts.duration != "perpetual":
        _note(f"policy requires a perpetual license, but the clause provides {facts.duration or 'no stated duration'}", NEGOTIATE)

    # --- Revocability ---------------------------------------------------------
    if policy.prohibit_revocable_license:
        if facts.revocability == "revocable":
            _note("license is expressly revocable, prohibited by policy (irrevocable required)", NEGOTIATE)
        elif facts.revocability is None:
            _note("policy requires an irrevocable license, but revocability is not addressed in the clause", NEGOTIATE)

    # --- Sublicensable ----------------------------------------------------------
    if policy.require_sublicensable and facts.sublicensable is not True:
        _note("policy requires sublicensing rights, but none are stated (or are expressly denied)", NEGOTIATE)

    # --- Transferable -------------------------------------------------------------
    if policy.require_transferable and facts.transferable is not True:
        _note("policy requires transferability, but the license is not stated as transferable (or is expressly non-transferable)", NEGOTIATE)

    # --- Territory -----------------------------------------------------------------
    if policy.require_worldwide_territory and facts.territory != "worldwide":
        _note(f"policy requires a worldwide territory, but the clause provides {facts.territory or 'no stated territory'}", NEGOTIATE)

    # --- Purpose-limited -------------------------------------------------------------
    if policy.require_purpose_limited_license and not facts.purpose_limited:
        _note("policy requires a purpose-limited (field-of-use restricted) license, but none was found", NEGOTIATE)

    # --- Derivative works -----------------------------------------------------------
    if policy.prohibit_derivative_works and facts.derivative_works_permitted is True:
        _note("clause permits derivative works, prohibited by policy", MUST_REDLINE)

    # --- Feedback -------------------------------------------------------------------
    if policy.require_feedback_assigned and facts.feedback_treatment != "assigned":
        _note(f"policy requires feedback to be assigned outright, but the clause provides "
              f"{facts.feedback_treatment or 'no stated feedback treatment'}", NEGOTIATE)

    # --- Residual knowledge -----------------------------------------------------------
    if policy.require_residual_knowledge_rights and not facts.residual_knowledge_rights:
        _note("policy requires residual-knowledge rights, but none were found", NEGOTIATE)

    # --- Open source ------------------------------------------------------------------
    if policy.require_open_source_disclosure and not facts.open_source_obligations_present:
        _note("policy requires open-source disclosure/obligations to be addressed, but none were found", NEGOTIATE)

    # --- Infringement reference --------------------------------------------------------
    if policy.require_infringement_remedy_reference and not facts.infringement_remedy_referenced:
        _note("policy requires the clause to at least reference infringement/third-party IP treatment, but none was found", NEGOTIATE)

    # --- Post-termination survival -------------------------------------------------------
    if policy.require_post_termination_survival and not facts.post_termination_survival:
        _note("policy requires the license to survive termination, but no survival commitment was found", NEGOTIATE)

    extracted_summary_parts = []
    if background_owner:
        extracted_summary_parts.append(f"Background IP: {background_owner}")
    if work_product_owner:
        extracted_summary_parts.append(f"Work product: {work_product_owner}")
    if facts.exclusivity:
        extracted_summary_parts.append(f"Exclusivity: {facts.exclusivity}")
    if facts.duration:
        extracted_summary_parts.append(f"Duration: {facts.duration}")
    extracted_summary = "; ".join(extracted_summary_parts) or "IP ownership/licensing clause found; limited structured detail extractable"

    if worst == ACCEPT and facts.absence_state == "PRESENT_BUT_UNRESOLVED" and established_dimension_count == 0:
        worst = REQUIRES_REVIEW
        notes.append(
            "contextual discovery identified and verified IP-ownership-relevant language in this contract, but "
            "deterministic extraction could not structure it into a specific ownership attribution or licensing "
            "term — this is not the same as confirming no IP ownership provision exists"
        )

    if worst == ACCEPT and not notes:
        required_action = "None — IP ownership and license terms meet policy"
        explanation = f"Contract language: \"{facts.raw_excerpt}\". No policy gaps found. Result: {ACCEPT}."
    elif worst == REQUIRES_REVIEW:
        required_action = "Manual review required — " + "; ".join(notes)
        explanation = f"Contract language: \"{facts.raw_excerpt}\". {'; '.join(notes)}. Result: {worst}."
    else:
        if worst in (ESCALATE, PROHIBITED):
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — " + "; ".join(notes)
        elif worst == MUST_REDLINE:
            required_action = "Replace clause — apply the approved fallback IP ownership/license language: " + "; ".join(notes)
        else:
            required_action = "Negotiate — " + "; ".join(notes)
        explanation = f"Contract language: \"{facts.raw_excerpt}\". {'; '.join(notes)}. Result: {worst}."

    return PolicyDecision(
        **common, state=worst,
        contract_language=facts.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary="See configured policy",
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, worst),
        category_treatments=category_treatments, unresolved_facts=[],
        start_index=facts.start_index, end_index=facts.end_index,
        escalate_to=escalate_to_for_state(worst, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(worst, policy.fallback_text, (NEGOTIATE, MUST_REDLINE, PROHIBITED)),
        controlling_provision={"label": f"Section {facts.section_label} — Intellectual Property" if facts.section_label else "Intellectual Property", "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
    )
