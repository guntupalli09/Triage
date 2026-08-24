"""
Warranties clause adapter, over policy_engine_core. Adapter #11 — the
first added after the ten-adapter scalability review
(docs/architecture/ten_adapter_scalability_review.md).

SEMANTIC MODEL: a directed catalog of representations/warranties, not one
warranties = acceptable classification and not a flat checklist. Three
independent things are kept distinct, per the review's explicit
instruction not to collapse "Vendor warrants X" and "Customer's sole
remedy is Y" into one field:

  1. WARRANTY CATEGORIES (who warrants what, to whom) -- ten enumerable,
     independently-established/negated facts (authority, compliance with
     law, professional/workmanlike standard, conformity to documentation,
     non-infringement, malware-free, security, performance, title, third-
     party rights), each resolved to a warranting SIDE independently, plus
     one shared duration fact. This mirrors insurance_policy_engine's
     per-coverage-type CoverageRequirement dict (a proven, reviewed
     pattern from adapter #9) -- WarrantyCategoryFacts is deliberately the
     same shape (established / negated-vs-affirmed conflict /
     per-attribution warranting-party resolution) applied to warranty
     categories instead of insurance coverage types.
  2. DISCLAIMER language ("AS IS", "no other warranties except as
     expressly stated") -- independent of which categories were
     affirmatively warranted; a disclaimer can coexist with an express
     warranty (the disclaimer covers everything NOT expressly warranted).
  3. REMEDY language (exclusive remedy, repair/replace/reperform, refund/
     credit) -- never folded into a warranty category. A category can be
     warranted with no stated remedy at all, and remedy language can
     exist with no category established (a bare "customer's sole remedy
     is X" sentence, orphaned from any warranty statement).

DIRECTIONALITY: like payment_terms and insurance, directionality is
resolved per-fact rather than doubling every field. Each warranty
CATEGORY independently resolves which side gave it (via the same
document-wide attribution pattern insurance_policy_engine uses for "who
must carry this coverage"), rather than the adapter picking one overall
"warranting side" for the whole clause -- a B2B warranties section
routinely warrants different things from different sides (vendor warrants
non-infringement; customer warrants it has authority to enter the
Agreement), and collapsing that to one side would lose real information.
"To whom" is deliberately NOT separately resolved to a side (unlike the
warranting party) -- in practice a warranty's beneficiary is always "the
other party", and modeling it as a second directional axis would double
field count for no discriminating value, the same simplification
payment_terms's docstring makes explicit for its own directionality axis.

MUTUAL-OPENER ASYMMETRY: "Each party represents and warrants that it has
full corporate power and authority..." is extremely common drafting for
the authority category specifically. Reuses the promoted core primitive
policy_engine_core.detect_role_attributed_asymmetry (already used by
indemnification/termination/confidentiality/assignment) to verify a
mutual opener isn't contradicted by asymmetric per-party subclauses
later in the same provision; unresolved asymmetry routes to
REQUIRES_REVIEW rather than guessing which party's terms actually govern.

EXTRACTION SAFETY -- clause_found requires more than a bare "warrant"
mention: per the ten-adapter review's explicit negative-control
requirement, a stray "warrant"/"warranty"/"guarantee"/"represents" token
in an unrelated context (a search warrant, an unrelated dispute-notice
clause mentioning "warranty claims", "represents 10% of revenue", an SLA
section that "guarantees" uptime) must never trigger REQUIRES_REVIEW.
_ANCHOR_RE intentionally never anchors on bare "represents" or
"guarantee" at all -- only "warrant"-root tokens -- and even then,
extract_warranties_facts only sets clause_found=True when at least one
concrete category/disclaimer/remedy/mutual-opener signal was actually
found somewhere in an anchored window; a document where the anchor fires
but nothing structured is ever found is treated as NOT_APPLICABLE (no
clause), never as a low-signal REQUIRES_REVIEW.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

from policy_engine_core import (
    ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE,
    REQUIRES_REVIEW, NOT_APPLICABLE,
    LadderStep, build_ladder as _core_build_ladder,
    side_for_role, detect_role_attributed_asymmetry,
    excerpt as _excerpt, section_label_before as _section_label_before,
    requires_review_explanation, requires_review_required_action,
    PolicyDecision,
    detect_condition_in_text as _core_detect_condition_in_text,
)

RULE_ID = "POLICY_WARRANTIES"

_PROVISION_WINDOW_CHARS = 2200
_GENERIC_ROLE_WORDS = {"each", "the", "any", "such", "this", "that", "both", "either", "party", "parties", "all", "it"}

WARRANTY_CATEGORIES: Tuple[str, ...] = (
    "authority",
    "compliance_with_law",
    "professional_workmanlike",
    "conformity_to_documentation",
    "non_infringement",
    "malware_free",
    "security",
    "performance",
    "title",
    "third_party_rights",
)

# --- Clause presence -----------------------------------------------------------------------
# Deliberately narrow: bare "warrant" root only. No blanket "represents"
# or "guarantee" anchor -- see module docstring's negative-control note.
_ANCHOR_RE = re.compile(r"warrant(?:s|y|ies|ed|ing)?\b", re.I)

# --- Warranting-party attribution -----------------------------------------------------------
# Case-sensitive name capture nested in an overall re.I compile: the
# (?-i:...) reset is required or re.IGNORECASE would let [A-Z] match
# lowercase too, defeating the "must look like a capitalized defined
# term" heuristic -- the same hazard already fixed in every other
# adapter's party-name capture (liability, indemnification, termination,
# confidentiality, assignment, insurance, payment_terms, and, as of this
# hardening pass, governing_law).
_WARRANTING_PARTY_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,30}))\s+(?:hereby\s+|further\s+|also\s+|additionally\s+)?"
    r"(?:represents\s+and\s+warrants|warrants|represents)\s+"
    r"(?:to\s+(?:the\s+other\s+party|[A-Za-z]{2,30})\s+)?that\b",
    re.I,
)
_MUTUAL_OPENER_RE = re.compile(
    r"each\s+party\s+(?:hereby\s+)?(?:represents\s+and\s+warrants|warrants|represents)"
    r"|both\s+parties\s+(?:represent\s+and\s+)?warrant"
    r"|the\s+parties\s+each\s+(?:represent\s+and\s+)?warrant",
    re.I,
)
_ROLE_ATTRIBUTION_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,30}))(?:'s)?\s+warrant(?:y|ies)\s+(?:obligations?|under\s+this\s+(?:Section|Agreement))",
    re.I,
)

# --- Category noun phrases, used to build both affirmative and negation ----------------------
# regexes per category from one source of truth, reducing duplication
# within this file (an adapter-local convention, not shared with other
# adapters -- see the ten-adapter review's finding that vocabulary,
# unlike windowing mechanics, should stay adapter-local).
_CATEGORY_NOUN_PHRASES: Dict[str, str] = {
    "authority": r"(?:power|right|authority)\s+(?:and\s+authority\s+)?to\s+(?:enter\s+into|execute)\s+(?:this\s+)?Agreement",
    "compliance_with_law": r"compliance\s+with\s+(?:applicable\s+)?laws?",
    "professional_workmanlike": r"(?:professional|workmanlike)\s+(?:manner|standard)",
    "conformity_to_documentation": r"conformity\s+(?:to|with)\s+the\s+(?:Documentation|specifications?)",
    "non_infringement": r"(?:non-?)?infringement",
    "malware_free": r"(?:viruses|malware|malicious\s+code)",
    "security": r"security",
    "performance": r"performance",
    "title": r"title",
    "third_party_rights": r"third[- ]part(?:y|ies)\s+rights?",
}

_CATEGORY_AFFIRMATIVE_RE: Dict[str, "re.Pattern"] = {
    "authority": re.compile(
        r"(?:has|have)\s+(?:the\s+)?(?:full\s+)?(?:legal\s+|corporate\s+)?(?:power|right|authority)"
        r"(?:\s+and\s+authority)?\s+to\s+(?:enter\s+into|execute\s+and\s+deliver|execute|perform)\s+this\s+Agreement"
        r"|duly\s+authorized\s+to\s+(?:enter\s+into|execute)", re.I,
    ),
    "compliance_with_law": re.compile(
        r"compl(?:y|iance)\s+with\s+all\s+applicable\s+laws?|shall\s+comply\s+with\s+applicable\s+law", re.I,
    ),
    "professional_workmanlike": re.compile(
        r"(?:in\s+a\s+)?professional(?:\s+and\s+workmanlike)?\s+manner|workmanlike\s+manner"
        r"|consistent\s+with\s+(?:generally\s+accepted\s+)?industry\s+standards", re.I,
    ),
    "conformity_to_documentation": re.compile(
        r"conform[s]?\s+(?:in\s+all\s+material\s+respects\s+)?to\s+the\s+(?:applicable\s+)?(?:Documentation|specifications?)", re.I,
    ),
    "non_infringement": re.compile(
        r"non-?infringement|(?:does|do|shall|will)\s+not\s+infringe"
        r"|free\s+(?:of|from)\s+(?:any\s+)?infringement", re.I,
    ),
    "malware_free": re.compile(
        r"free\s+(?:of|from)\s+(?:any\s+)?(?:computer\s+)?(?:viruses|malware|malicious\s+code|disabling\s+(?:code|device)s?|trojan)", re.I,
    ),
    "security": re.compile(
        r"(?:it\s+)?(?:maintains?|has\s+implemented)\s+(?:commercially\s+reasonable\s+)?"
        r"(?:(?:administrative|technical|physical)[,\s]+(?:and\s+)?)*security", re.I,
    ),
    "performance": re.compile(
        r"will\s+perform\s+(?:substantially\s+)?in\s+accordance\s+with|will\s+materially\s+conform\s+to"
        r"|will\s+operate\s+substantially\s+as\s+described", re.I,
    ),
    "title": re.compile(
        r"(?:good\s+and\s+(?:valid|marketable)\s+)?title\s+to\s+the|owns?\s+all\s+right,?\s+title\s+and\s+interest", re.I,
    ),
    "third_party_rights": re.compile(
        r"(?:does\s+not|shall\s+not|will\s+not)\s+violate\s+(?:the\s+rights\s+of\s+)?(?:any\s+)?third[- ]part(?:y|ies)", re.I,
    ),
}

_CATEGORY_NEGATION_RE: Dict[str, "re.Pattern"] = {
    cat: re.compile(
        rf"(?:makes?\s+no\s+warrant(?:y|ies)|disclaims?\s+(?:any\s+)?(?:and\s+all\s+)?warrant(?:y|ies)"
        rf"|no\s+warranty\s+is\s+made)\s+(?:of|regarding|with\s+respect\s+to|as\s+to)\s+{phrase}",
        re.I,
    )
    for cat, phrase in _CATEGORY_NOUN_PHRASES.items()
}

# --- Duration --------------------------------------------------------------------------------
_DURATION_DAYS_RE = re.compile(r"(?:(?:for|to)\s+a\s+period\s+of\s+|warrant(?:y|ies)\s+period\s+of\s+)(\d{1,4})\s+days?", re.I)
_DURATION_MONTHS_RE = re.compile(r"(?:(?:for|to)\s+a\s+period\s+of\s+|warrant(?:y|ies)\s+period\s+of\s+)(\d{1,3})\s+months?", re.I)
_DURATION_YEARS_RE = re.compile(r"(?:(?:for|to)\s+a\s+period\s+of\s+|warrant(?:y|ies)\s+period\s+of\s+)(\d{1,2})\s+years?", re.I)
_DURATION_PERPETUAL_RE = re.compile(
    r"warrant(?:y|ies)\s+shall\s+(?:be\s+)?(?:perpetual|continue\s+indefinitely)"
    r"|no\s+expiration\s+of\s+(?:the\s+)?warrant(?:y|ies)", re.I,
)

# --- Disclaimer / "as is" ----------------------------------------------------------------------
_AS_IS_RE = re.compile(r"\"?AS[\s-]IS\"?\s*(?:basis|and\s+\"?AS\s+AVAILABLE\"?)?|provided\s+on\s+an\s+\"?as[\s-]is\"?\s+basis", re.I)
_DISCLAIMER_RE = re.compile(
    r"except\s+as\s+(?:expressly\s+)?(?:set\s+forth|provided|stated)\s+(?:herein|in\s+this\s+(?:Section|Agreement))"
    r"[^.]{0,200}?no\s+(?:other\s+)?warrant(?:y|ies)"
    r"|disclaims?\s+all\s+other\s+warrant(?:y|ies)"
    r"|makes?\s+no\s+other\s+warrant(?:y|ies)"
    r"|no\s+warranties?\s+of\s+any\s+kind,?\s+(?:whether\s+)?express\s+or\s+implied", re.I,
)
_DISCLAIMER_CARVEOUT_RE = re.compile(
    r"other\s+than\s+(?:the\s+)?warrant(?:y|ies)\s+(?:expressly\s+)?(?:set\s+forth|stated|provided)"
    r"|except\s+for\s+the\s+(?:express\s+)?warrant(?:y|ies)\s+(?:set\s+forth|stated)\s+(?:herein|above|in\s+this\s+Section)", re.I,
)

# --- Remedy ------------------------------------------------------------------------------------
_EXCLUSIVE_REMEDY_RE = re.compile(
    r"sole\s+and\s+exclusive\s+remedy|exclusive\s+remedy\s+(?:for|of)"
    r"|(?:customer|licensee|buyer|client)'?s?\s+sole\s+(?:and\s+exclusive\s+)?remedy", re.I,
)
_REPAIR_REPLACE_RE = re.compile(
    r"repair(?:\s+or)?\s*,?\s*replace(?:ment)?(?:\s+or)?\s*,?\s*re-?perform(?:ance)?"
    r"|repair\s+or\s+replace(?:ment)?", re.I,
)
_REFUND_CREDIT_RE = re.compile(
    r"refund\s+(?:of\s+)?(?:the\s+)?(?:fees|purchase\s+price|amounts?\s+paid)"
    r"|(?:issue|provide)\s+(?:a\s+)?(?:refund|credit)", re.I,
)

# --- Survival / cross-reference -----------------------------------------------------------------
_SURVIVAL_RE = re.compile(r"warrant(?:y|ies)\s+shall\s+survive|survives?\s+(?:the\s+)?(?:termination|expiration)", re.I)
_SCHEDULE_CROSSREF_RE = re.compile(
    r"as\s+(?:set\s+forth|described|specified)\s+in\s+(?:the\s+)?(?:applicable\s+)?"
    r"(?:Statement\s+of\s+Work|SOW|Schedule|Exhibit)"
    r"|warrant(?:y|ies)\s+(?:set\s+forth|specified)\s+in\s+(?:the\s+)?(?:applicable\s+)?(?:SOW|Statement\s+of\s+Work|Schedule)",
    re.I,
)

_SENTENCE_END_RE = re.compile(r"(?<!\d)\.(?!\d)|;")


def _local_window(text: str, start: int, other_anchor_positions: List[int], max_radius: int = 400) -> str:
    """Scopes a warranting-party statement to just its own sentence, so
    multiple statements in one provision never bleed one party's
    category/duration facts into another's. Sentence boundary is a period
    NOT immediately between two digits (so a decimal like "99.9%" is never
    mistaken for a sentence end) or a semicolon -- the same fix already
    proven in payment_terms_policy_engine._local_window and copied,
    verbatim, into insurance_policy_engine._local_window during this
    hardening pass; reused here from the start rather than reintroducing
    the naive text.find(".") version a fourth time."""
    end = min(len(text), start + max_radius)
    m = _SENTENCE_END_RE.search(text, start, end)
    if m:
        end = min(end, m.end())
    for pos in other_anchor_positions:
        if pos > start:
            end = min(end, pos)
    return text[start:end]


def _parse_days(raw: str) -> float:
    return float(raw)


@dataclass
class WarrantyCategoryFacts:
    established: bool = False
    negated: bool = False
    conflict: bool = False  # established AND negated somewhere in the document
    warranting_party_attributions: Dict[str, bool] = field(default_factory=dict)
    warranting_party_conflict: bool = False
    established_mutually: bool = False
    raw_excerpt: str = ""


@dataclass
class WarrantiesFacts:
    clause_found: bool
    raw_excerpt: str = ""
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    section_label: Optional[str] = None

    categories: Dict[str, WarrantyCategoryFacts] = field(default_factory=dict)

    mutual_opener_present: bool = False
    mutual_asymmetry_reasons: List[str] = field(default_factory=list)

    duration_days: Optional[float] = None
    duration_perpetual: Optional[bool] = None
    duration_conflict: bool = False

    as_is_disclaimer_present: Optional[bool] = None
    disclaimer_present: Optional[bool] = None
    disclaimer_carveout_present: Optional[bool] = None

    exclusive_remedy_present: Optional[bool] = None
    repair_replace_reperform_present: Optional[bool] = None
    refund_credit_remedy_present: Optional[bool] = None

    warranty_survival_present: Optional[bool] = None
    schedule_cross_reference: bool = False

    # Fact-admission architecture — mirrors data_security_policy_engine.
    # DataSecurityFacts.absence_state. This adapter's "anchor fired but
    # nothing structured" gate deliberately returns None/NOT_APPLICABLE
    # (see the module docstring's negative-control discipline) rather
    # than REQUIRES_REVIEW the way confidentiality/termination do — so a
    # provider outage on the NO-anchor path needs its own explicit
    # RECOGNITION_UNCERTAIN branch in evaluate_warranties_policy, it
    # cannot rely on falling through to an existing safe branch.
    absence_state: str = "CONFIRMED_ABSENT"
    semantic_discovery_error: Optional[str] = None
    ai_identified_condition: Optional[str] = None
    ai_identified_exception: Optional[str] = None
    ai_identified_definition_or_reference: Optional[str] = None
    deterministic_condition_established: bool = False
    deterministic_condition_excerpt: Optional[str] = None


class WarrantiesPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]

    required_warranty_categories_json: Optional[List[str]]
    prohibited_warranty_categories_json: Optional[List[str]]
    require_mutual_warranties: bool
    minimum_warranty_duration_days: Optional[float]
    prohibit_as_is_disclaimer: bool
    prohibit_exclusive_remedy: bool
    required_remedy_type: Optional[str]  # "repair_replace_reperform" | "refund_credit" | None
    require_non_infringement_warranty: bool
    require_compliance_with_law_warranty: bool
    require_professional_standard: bool
    require_malware_free_warranty: bool
    require_title_warranty: bool
    require_warranty_survival: bool


def _attribute_warranting_party(cat: WarrantyCategoryFacts, name: str) -> None:
    cat.warranting_party_attributions[name] = True
    if len(cat.warranting_party_attributions) > 1:
        cat.warranting_party_conflict = True


def _snapshot_warranty_attribution(local: str) -> Dict[str, Any]:
    categories = frozenset(
        cat for cat, rex in _CATEGORY_AFFIRMATIVE_RE.items() if rex.search(local)
    )
    duration = None
    dm = _DURATION_DAYS_RE.search(local)
    if dm:
        duration = _parse_days(dm.group(1))
    return {"categories": categories, "duration_days": duration}


def _compare_warranty_attribution(base_role: str, base: Dict[str, Any], role: str, snap: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    if base["categories"] and snap["categories"] and base["categories"] != snap["categories"]:
        reasons.append(f"{base_role} and {role} warrant different categories despite the mutual opener")
    if base["duration_days"] is not None and snap["duration_days"] is not None and base["duration_days"] != snap["duration_days"]:
        reasons.append(f"{base_role} and {role} state different warranty durations despite the mutual opener")
    return reasons


def _any_warranty_dimension_established_equal(base: Dict[str, Any], snap: Dict[str, Any]) -> bool:
    """Step 4A.10.4 — real, positively-established agreement on warranted
    categories or duration stands down the structural fail-closed check.
    See indemnification_policy_engine._any_dimension_established_equal
    for the full rationale."""
    if base["categories"] and snap["categories"] and base["categories"] == snap["categories"]:
        return True
    if base["duration_days"] is not None and snap["duration_days"] is not None and base["duration_days"] == snap["duration_days"]:
        return True
    return False


def _detect_warranty_asymmetry(window: str) -> List[str]:
    """Mirrors confidentiality_policy_engine._detect_confidentiality_asymmetry
    and assignment_policy_engine._detect_restriction_asymmetry -- reuses
    the shared core scan/window/compare mechanics
    (policy_engine_core.detect_role_attributed_asymmetry); only the
    attribution regex and snapshot/compare functions are adapter-owned."""
    return detect_role_attributed_asymmetry(
        window, _ROLE_ATTRIBUTION_RE, _GENERIC_ROLE_WORDS,
        _snapshot_warranty_attribution, _compare_warranty_attribution,
        established_equal_fn=_any_warranty_dimension_established_equal,
    )


# Off by default — same rollout discipline as every other adapter this
# session integrated.
WARRANTIES_SEMANTIC_DISCOVERY_ENABLED = False  # module-load-time default; immediately overridden below
import fact_admission as _fact_admission_env_check
WARRANTIES_SEMANTIC_DISCOVERY_ENABLED = _fact_admission_env_check.semantic_discovery_enabled("WARRANTIES_SEMANTIC_DISCOVERY_ENABLED")
del _fact_admission_env_check

_WARRANTIES_SEMANTIC_FOCUS = (
    "one party making an express commitment/representation about the quality, performance, "
    "legality, or non-infringement of goods or services under this agreement -- a warranty "
    "concept -- even if the wording is unusual and does not use any 'warrant'-root word at all "
    "(e.g. 'represents and confirms', 'commits that', 'assures')"
)
_WARRANTIES_SEMANTIC_PROPOSITION = (
    "This sentence or clause is operative language of this agreement that establishes an "
    "express warranty or representation about the quality, performance, legality, or "
    "non-infringement of goods or services under this agreement."
)


def _run_semantic_discovery(text: str) -> Tuple[List, Optional[str], bool, Optional[str]]:
    """Mirrors liability_policy_engine._run_semantic_discovery exactly.
    Returns (admitted_candidates, unresolved_dependency_note, error)."""
    if not WARRANTIES_SEMANTIC_DISCOVERY_ENABLED:
        return [], None, False, None
    import fact_admission as _fa
    try:
        raw_candidates = _fa.discover_candidate_spans(text, "warranties", _WARRANTIES_SEMANTIC_FOCUS)
    except Exception as exc:  # noqa: BLE001 — provider unavailable, never "confirmed absent"
        return [], None, False, f"{type(exc).__name__}: {exc}"

    verified_candidates = [
        _fa.verify_and_ground(candidate, text, _WARRANTIES_SEMANTIC_PROPOSITION) for candidate in raw_candidates
    ]
    admitted = [c for c in verified_candidates if c.admission_status == _fa.ADMITTED]
    # Zero-silent-loss (gap-closure pass): this adapter's own negative-
    # control discipline (found_anything gate, below) is meant to guard
    # against an anchor firing on stray noise with nothing structured --
    # it was never meant to also swallow a genuine competing-reading
    # candidate the AI actually found and grounded. A candidate blocked
    # ONLY for that reason (or an unresolved definition/cross-reference)
    # must still surface, not silently collapse into NOT_APPLICABLE.
    unresolved_dependency_note = _fa.first_unresolved_dependency_note(verified_candidates)
    note_is_unconditional = _fa.first_unresolved_dependency_note_is_unconditional(verified_candidates)
    return admitted, unresolved_dependency_note, note_is_unconditional, None


def extract_warranties_facts(text: str) -> Optional[WarrantiesFacts]:
    # Unlike other adapters' anchor pre-filters, a "no " lookback is
    # deliberately NOT applied here: "Vendor makes no warranty of X" is
    # itself a first-class, meaningful fact this adapter needs to detect
    # (via _CATEGORY_NEGATION_RE below), not noise to filter out before
    # extraction even starts. Pre-filtering it here would silently discard
    # exactly the negation statements the module is built to catch. Safety
    # against a bare, meaningless "warrant" mention is still provided
    # downstream by the found_anything gate.
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
            facts = WarrantiesFacts(clause_found=True, absence_state="RECOGNITION_UNCERTAIN", semantic_discovery_error=semantic_error)
            for cat in WARRANTY_CATEGORIES:
                facts.categories[cat] = WarrantyCategoryFacts()
            return facts
        if not admitted_semantic and not unresolved_dependency_note:
            return None
        if not admitted_semantic:
            # A genuine candidate was found (competing readings, or an
            # unresolved definition/cross-reference), just never resolved
            # to something admissible -- never the same as "nothing here
            # at all" (found_anything's own negative-control case).
            facts = WarrantiesFacts(clause_found=True, ai_identified_definition_or_reference=unresolved_dependency_note)
            for cat in WARRANTY_CATEGORIES:
                facts.categories[cat] = WarrantyCategoryFacts()
            return facts
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

    facts = WarrantiesFacts(clause_found=True, raw_excerpt=raw_excerpt, start_index=start_index,
                             end_index=end_index, section_label=section_label)
    for cat in WARRANTY_CATEGORIES:
        facts.categories[cat] = WarrantyCategoryFacts()

    found_anything = False
    # Candidate 3 remediation (Root Cause 1): track whether a category's
    # deterministic structure was ACTUALLY found, separate from
    # found_anything (which, after Root Cause 2's fix, may become True on
    # an admitted AI candidate's account alone if we broaden it -- but we
    # deliberately do NOT broaden found_anything itself here, preserving
    # the negative-control discipline this gate's docstring already
    # documents; instead an admitted-but-unstructured candidate is
    # surfaced via the separate PRESENT_BUT_UNRESOLVED absence_state
    # below, never by lowering the found_anything bar).
    duration_values: Set[float] = set()
    perpetual_found = False

    for (ws, we) in windows:
        window = text[ws:we]

        warranting_positions = [m.start() for m in _WARRANTING_PARTY_RE.finditer(window)]
        mutual_positions = [m.start() for m in _MUTUAL_OPENER_RE.finditer(window)]
        all_positions = sorted(warranting_positions + mutual_positions)

        for m in _WARRANTING_PARTY_RE.finditer(window):
            name = m.group(1)
            if name.lower() in _GENERIC_ROLE_WORDS:
                continue
            other_positions = [p for p in all_positions if p != m.start()]
            local = _local_window(window, m.end(), other_positions)
            for cat, rex in _CATEGORY_AFFIRMATIVE_RE.items():
                if rex.search(local):
                    facts.categories[cat].established = True
                    _attribute_warranting_party(facts.categories[cat], name)
                    facts.categories[cat].raw_excerpt = facts.categories[cat].raw_excerpt or _excerpt(window, m.start(), min(len(window), m.end() + len(local)))
                    found_anything = True
        for m in _MUTUAL_OPENER_RE.finditer(window):
            facts.mutual_opener_present = True
            other_positions = [p for p in all_positions if p != m.start()]
            local = _local_window(window, m.end(), other_positions)
            for cat, rex in _CATEGORY_AFFIRMATIVE_RE.items():
                if rex.search(local):
                    facts.categories[cat].established = True
                    facts.categories[cat].established_mutually = True
                    facts.categories[cat].raw_excerpt = facts.categories[cat].raw_excerpt or _excerpt(window, m.start(), min(len(window), m.end() + len(local)))
                    found_anything = True

        if facts.mutual_opener_present and not facts.mutual_asymmetry_reasons:
            facts.mutual_asymmetry_reasons = _detect_warranty_asymmetry(window)

        for cat, rex in _CATEGORY_NEGATION_RE.items():
            if rex.search(window):
                facts.categories[cat].negated = True
                found_anything = True

        # Duration is frequently its own sentence, independent of any one
        # warranting-party statement ("This warranty shall be valid for a
        # period of 90 days from delivery.") -- scanned at the whole-window
        # level, accumulating every distinct value found so a second,
        # conflicting duration statement anywhere in the document is
        # detected as a conflict rather than the first one silently
        # governing (or a later one silently overwriting it).
        for dm in _DURATION_DAYS_RE.finditer(window):
            duration_values.add(_parse_days(dm.group(1)))
            found_anything = True
        for mm in _DURATION_MONTHS_RE.finditer(window):
            duration_values.add(float(mm.group(1)) * 30)
            found_anything = True
        for ym in _DURATION_YEARS_RE.finditer(window):
            duration_values.add(float(ym.group(1)) * 365)
            found_anything = True

        if _DURATION_PERPETUAL_RE.search(window):
            perpetual_found = True
            found_anything = True

        if _AS_IS_RE.search(window):
            facts.as_is_disclaimer_present = True
            found_anything = True
        if _DISCLAIMER_RE.search(window):
            facts.disclaimer_present = True
            found_anything = True
            if _DISCLAIMER_CARVEOUT_RE.search(window):
                facts.disclaimer_carveout_present = True
        if _EXCLUSIVE_REMEDY_RE.search(window):
            facts.exclusive_remedy_present = True
            found_anything = True
        if _REPAIR_REPLACE_RE.search(window):
            facts.repair_replace_reperform_present = True
            found_anything = True
        if _REFUND_CREDIT_RE.search(window):
            facts.refund_credit_remedy_present = True
            found_anything = True
        if _SURVIVAL_RE.search(window):
            facts.warranty_survival_present = True
            found_anything = True
        if _SCHEDULE_CROSSREF_RE.search(window):
            facts.schedule_cross_reference = True
            found_anything = True

    for cat in WARRANTY_CATEGORIES:
        cf = facts.categories[cat]
        if cf.established and cf.negated:
            cf.conflict = True

    if len(duration_values) == 1:
        facts.duration_days = next(iter(duration_values))
    elif len(duration_values) > 1:
        facts.duration_conflict = True

    if perpetual_found:
        if duration_values:
            facts.duration_conflict = True
        else:
            facts.duration_perpetual = True

    if not found_anything:
        # Anchor fired (a "warrant"-root token exists somewhere) but no
        # concrete warranty structure was ever found -- e.g. a stray
        # "warranty claims must be submitted within 10 days" inside an
        # unrelated dispute-notice clause. Per the module docstring's
        # negative-control discipline, this is NOT_APPLICABLE (no real
        # warranties clause) UNLESS an admitted AI candidate independently
        # verified operative warranty-relevant language here -- in that
        # case, never silently discard the finding as "nothing here at
        # all" (Candidate 3 remediation, Root Cause 1); force review
        # instead via PRESENT_BUT_UNRESOLVED.
        if admitted_semantic or unresolved_dependency_note is not None:
            facts.absence_state = "PRESENT_BUT_UNRESOLVED"
            import fact_admission as _fa
            for candidate in admitted_semantic:
                facts.ai_identified_condition = facts.ai_identified_condition or candidate.condition
                facts.ai_identified_exception = facts.ai_identified_exception or candidate.exception
            # Zero-silent-loss mission follow-up (data_security-139 general
            # failure class) -- a candidate whose OWN semantic verification
            # reported genuine uncertainty (never admitted) must not be
            # silently discarded merely because the anchor's local text
            # also failed to structure a concrete warranty.
            facts.ai_identified_definition_or_reference = (
                _fa.first_resolved_dependency_note(admitted_semantic) or unresolved_dependency_note
            )
            return facts
        return None

    # Final trust architecture (Phase 5/6) — reached only when
    # found_anything is True (the base warranty structure DID resolve
    # deterministically, so this candidate already passed the negative-
    # control gate above, not merely an anchor firing on a stray word).
    # See confidentiality_policy_engine.py's identical composition for
    # the full rationale.
    import fact_admission as _fa
    for candidate in admitted_semantic:
        facts.ai_identified_condition = facts.ai_identified_condition or candidate.condition
        facts.ai_identified_exception = facts.ai_identified_exception or candidate.exception
    facts.ai_identified_definition_or_reference = _fa.first_resolved_dependency_note(admitted_semantic)

    # Candidate 3 zero-silent-loss mission — a deterministically-detected
    # condition/proviso attached to the local warranty clause, using the
    # same shared primitive liability/insurance already use.
    for (ws, we) in windows:
        cond = _core_detect_condition_in_text(text[ws:we])
        if cond.status == "ESTABLISHED":
            facts.deterministic_condition_established = True
            facts.deterministic_condition_excerpt = cond.evidence_span
            break

    return facts


def _build_ladder(policy: WarrantiesPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", "Required warranty categories established with adequate duration and no unfavorable disclaimer/remedy limits"),
        ("ACCEPTABLE", "Auto-accept within acceptable warranty terms"),
        ("FALLBACK", "Negotiate warranty terms within fallback range"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Prohibited warranty terms"),
    ]
    return _core_build_ladder(state, step_specs)


def _resolve_warranting_side(cat: WarrantyCategoryFacts, contract_side: str) -> Tuple[Optional[str], bool]:
    """Returns (resolved_side, unresolved). Mirrors
    insurance_policy_engine._resolve_obligated_party exactly -- both
    solve "which side does this per-item fact belong to" the same way:
    map the single attributed name via side_for_role, compare to
    contract_side, and refuse to guess on conflict or an unmappable name."""
    if cat.established_mutually and not cat.warranting_party_attributions:
        return "mutual", False
    if not cat.warranting_party_attributions:
        return None, False
    if cat.warranting_party_conflict:
        return None, True
    (name,) = cat.warranting_party_attributions.keys()
    side = side_for_role(name)
    if side is None:
        return None, True
    return side, False


def evaluate_warranties_policy(
    facts: Optional[WarrantiesFacts],
    policy: WarrantiesPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    if facts is None or not facts.clause_found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="warranties", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No warranties clause found",
            policy_limit_summary="N/A",
            required_action="None — this contract does not address warranties",
            explanation="No warranties clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="Warranties treatment",
            our_position_label="Our warranties", counterparty_position_label="Counterparty's warranties",
        )

    if facts.absence_state == "RECOGNITION_UNCERTAIN":
        # Fact-admission architecture (Step 5/6): unlike the "anchor
        # fired but nothing structured" case (deliberately NOT_APPLICABLE
        # per this module's negative-control discipline), a provider
        # outage/error on the NO-anchor path must never be reported as
        # "this contract does not address warranties" — it must escalate.
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="warranties", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Could not determine whether a warranties clause is present",
            policy_limit_summary="N/A",
            required_action="Manual review required — automated recognition was unavailable for this document.",
            explanation=(
                "Deterministic pattern matching found no warranties clause, and semantic verification could "
                f"not confirm its absence ({facts.semantic_discovery_error or 'unavailable'}). This is not "
                "the same as confirming the contract has no such clause."
            ),
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="Warranties treatment",
            our_position_label="Our warranties", counterparty_position_label="Counterparty's warranties",
        )

    if facts.absence_state == "PRESENT_BUT_UNRESOLVED":
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="warranties", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="A warranties-relevant clause was found and verified, but no specific warranty category could be structured from it",
            policy_limit_summary="N/A",
            required_action="Manual review required — a candidate clause was discovered and verified but could not be deterministically structured into a specific warranty.",
            explanation=(
                "Contextual discovery identified and verified warranties-relevant language in this contract, but "
                "deterministic extraction could not structure it into a specific warranty category. This is not "
                "the same as confirming no warranty provision exists, and must not be treated as a clean result."
            ),
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="Warranties treatment",
            our_position_label="Our warranties", counterparty_position_label="Counterparty's warranties",
        )

    unresolved_facts: List[str] = []

    # Candidate 3 zero-silent-loss mission — a deterministically-detected
    # condition/proviso attached to the local warranty clause.
    if facts.deterministic_condition_established:
        unresolved_facts.append(
            f"the warranty is stated as conditional (\"{facts.deterministic_condition_excerpt}\") — this "
            f"evaluation does not determine whether the stated condition is satisfied"
        )

    # Final trust architecture (Phase 4 hard gate) — a material condition/
    # exception the AI/context layer identified and grounded must not be
    # silently dropped merely because a warranty category otherwise
    # resolved deterministically.
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

    if facts.mutual_opener_present and facts.mutual_asymmetry_reasons:
        unresolved_facts.append(
            "clause opens with mutual ('each party') warranty language, but states materially "
            "different terms per named party (" + "; ".join(facts.mutual_asymmetry_reasons) +
            ") — cannot confirm the warranty is actually symmetric"
        )

    if facts.duration_conflict:
        unresolved_facts.append("conflicting or ambiguous warranty duration statements found (numeric duration and perpetual/indefinite language, or multiple different numeric durations)")

    resolved_categories: Dict[str, Optional[str]] = {}
    for cat_name in WARRANTY_CATEGORIES:
        cat = facts.categories[cat_name]
        if cat.conflict:
            unresolved_facts.append(f"warranty category '{cat_name}' is both affirmatively warranted and expressly disclaimed/negated elsewhere in the document — cannot determine which governs")
            continue
        if not cat.established:
            continue
        side, cat_unresolved = _resolve_warranting_side(cat, policy.contract_side)
        if cat_unresolved:
            unresolved_facts.append(f"warranty category '{cat_name}' could not be reliably attributed to a side — conflicting or unrecognized party name(s)")
            continue
        resolved_categories[cat_name] = side

    if unresolved_facts:
        explanation = requires_review_explanation("warranties structure", facts.raw_excerpt, unresolved_facts)
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="warranties", state=REQUIRES_REVIEW,
            contract_language=facts.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary="N/A",
            required_action=requires_review_required_action(unresolved_facts),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved_facts,
            start_index=facts.start_index, end_index=facts.end_index, source=source,
            controlling_provision={"label": f"Section {facts.section_label} — Warranties" if facts.section_label else "Warranties",
                                    "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
            summary_label="Warranties treatment", our_position_label="Our warranties",
            counterparty_position_label="Counterparty's warranties",
        )

    def _their_side(side: Optional[str]) -> bool:
        """True if `side` names the counterparty (i.e. not us, and not
        unresolved/mutual)."""
        if side is None:
            return False
        if side == "mutual":
            return True  # mutual warranties are, by definition, also given by the counterparty
        return side != policy.contract_side

    def _our_side(side: Optional[str]) -> bool:
        if side is None:
            return False
        if side == "mutual":
            return True
        return side == policy.contract_side

    notes: List[str] = []
    worst_state = ACCEPT

    def _worse(a: str, b: str) -> str:
        order = [ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, ESCALATE, PROHIBITED]
        return a if order.index(a) >= order.index(b) else b

    def _note(text: str, state: str) -> None:
        nonlocal worst_state
        notes.append(text)
        worst_state = _worse(worst_state, state)

    # --- Required warranty categories (must be established, given TO us by the counterparty) ---
    if policy.required_warranty_categories_json:
        for cat_name in policy.required_warranty_categories_json:
            side = resolved_categories.get(cat_name)
            if not _their_side(side):
                _note(f"required warranty category '{cat_name}' was not established as given by the counterparty", NEGOTIATE)

    # --- Prohibited warranty categories (must never be given BY us) -----------------------------
    if policy.prohibited_warranty_categories_json:
        for cat_name in policy.prohibited_warranty_categories_json:
            side = resolved_categories.get(cat_name)
            if _our_side(side):
                _note(f"prohibited warranty category '{cat_name}' was found as a warranty we give to the counterparty", ESCALATE)

    # --- Mutuality ---------------------------------------------------------------------------
    if policy.require_mutual_warranties and not facts.mutual_opener_present:
        _note("policy requires mutual warranty language, but no mutual ('each party') opener was found", NEGOTIATE)

    # --- Duration -----------------------------------------------------------------------------
    if policy.minimum_warranty_duration_days is not None:
        if facts.duration_days is None and not facts.duration_perpetual:
            _note("policy requires a minimum warranty duration, but no duration was stated", NEGOTIATE)
        elif facts.duration_days is not None and facts.duration_days < policy.minimum_warranty_duration_days:
            _note(f"warranty duration of {facts.duration_days:g} days is below the policy's minimum of {policy.minimum_warranty_duration_days:g} days", NEGOTIATE)

    # --- Disclaimer ---------------------------------------------------------------------------
    if policy.prohibit_as_is_disclaimer and facts.as_is_disclaimer_present:
        _note("an \"AS IS\" disclaimer was found, which policy prohibits", ESCALATE)

    # --- Remedy -------------------------------------------------------------------------------
    if policy.prohibit_exclusive_remedy and facts.exclusive_remedy_present:
        _note("exclusive-remedy language was found, which policy prohibits", ESCALATE)

    if policy.required_remedy_type == "repair_replace_reperform" and not facts.repair_replace_reperform_present:
        _note("policy requires repair/replace/reperform remedy language, but none was found", NEGOTIATE)
    elif policy.required_remedy_type == "refund_credit" and not facts.refund_credit_remedy_present:
        _note("policy requires refund/credit remedy language, but none was found", NEGOTIATE)

    # --- Specific required categories --------------------------------------------------------
    if policy.require_non_infringement_warranty and not _their_side(resolved_categories.get("non_infringement")):
        _note("policy requires a non-infringement warranty from the counterparty, but none was established", NEGOTIATE)
    if policy.require_compliance_with_law_warranty and not _their_side(resolved_categories.get("compliance_with_law")):
        _note("policy requires a compliance-with-law warranty from the counterparty, but none was established", NEGOTIATE)
    if policy.require_professional_standard and not _their_side(resolved_categories.get("professional_workmanlike")):
        _note("policy requires a professional/workmanlike standard warranty from the counterparty, but none was established", NEGOTIATE)
    if policy.require_malware_free_warranty and not _their_side(resolved_categories.get("malware_free")):
        _note("policy requires a malware/malicious-code-free warranty from the counterparty, but none was established", NEGOTIATE)
    if policy.require_title_warranty and not _their_side(resolved_categories.get("title")):
        _note("policy requires a title warranty from the counterparty, but none was established", NEGOTIATE)
    if policy.require_warranty_survival and not facts.warranty_survival_present:
        _note("policy requires the warranty to expressly survive termination, but no survival language was found", NEGOTIATE)

    if facts.schedule_cross_reference and not resolved_categories:
        _note("warranties appear to be delegated to a referenced Statement of Work/Schedule that could not be resolved from the contract text alone", ESCALATE)

    extracted_summary = "; ".join(
        f"{cat}: {side}" for cat, side in resolved_categories.items()
    ) or "No warranty categories established"

    required_action = "None — warranty terms meet policy" if worst_state == ACCEPT else (
        f"{'Escalate' if worst_state in (ESCALATE, PROHIBITED) else 'Negotiate'} — " + "; ".join(notes)
    )

    return PolicyDecision(
        rule_id=RULE_ID, clause_type="warranties", state=worst_state,
        contract_language=facts.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary="; ".join(notes) if notes else "Meets policy",
        required_action=required_action,
        explanation=f"Warranty categories established: {extracted_summary}. Result: {worst_state}."
                    + (" Notes: " + "; ".join(notes) if notes else ""),
        negotiation_ladder=_build_ladder(policy, worst_state),
        category_treatments=[
            {"category": cat, "treatment": resolved_categories.get(cat) or "not_established", "raw_excerpt": facts.categories[cat].raw_excerpt, "established": str(facts.categories[cat].established)}
            for cat in WARRANTY_CATEGORIES
        ],
        unresolved_facts=[],
        start_index=facts.start_index, end_index=facts.end_index, source=source,
        controlling_provision={"label": f"Section {facts.section_label} — Warranties" if facts.section_label else "Warranties",
                                "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
        summary_label="Warranties treatment", our_position_label="Our warranties",
        counterparty_position_label="Counterparty's warranties",
    )
