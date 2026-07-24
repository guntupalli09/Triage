"""
Deterministic Rule Engine for Contract Risk TriageCounsel

- Purely deterministic: regex + proximity logic only.
- Designed for Commercial NDAs / MSAs triage (not legal advice).
- Produces auditable findings with matched excerpts.
- Conservative detection: false positives acceptable, silence not acceptable.

Neural-Symbolic Architecture with Deterministic Control Plane:
- All risk detection is deterministic and rule-based
- LLM layer ONLY explains pre-identified findings
- LLM NEVER sees full contract text or invents risks
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterable

from party_resolver import (
    PartyRoleMap,
    VENDOR_ROLE,
    CUSTOMER_ROLE,
    UNKNOWN_ROLE,
    resolve_party_roles,
)

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    # CRITICAL is reserved for the top tier of the severity framework:
    # unbounded/asymmetric financial exposure, missing liability-cap
    # carve-outs, and personal/privacy/security/regulatory exposure that
    # falls on an individual or triggers statutory liability outside the
    # ordinary contract-risk envelope. Everything else uses HIGH/MEDIUM/LOW
    # as before — this is an addition, not a replacement, of the existing
    # three-tier scale.
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RuleClass(str, Enum):
    """
    PRESENCE_RISK: the rule detects adverse language that is actually present
    in the document (e.g. "no obligation to notify"). A regex hit is direct
    evidence of the claim.

    REQUIRED_SECTION: the rule's title claims to detect the ABSENCE of a
    protective clause (e.g. "No breach notification obligation"). A regex
    miss is not evidence of absence — regex can only prove a phrase is
    present, never that a topic is missing document-wide. These rules run a
    document-level check (topic relevance + protective-language search)
    after the normal chunked pass, and are only reported as "protection not
    found" when the topic is actually in scope for this document and no
    protective language was found anywhere in it.
    """
    PRESENCE_RISK = "presence_risk"
    REQUIRED_SECTION = "required_section"


class FindingType(str, Enum):
    """
    Precise, non-interchangeable claims a Finding can make. The report must
    show which one applies — "adverse language present" and "expected
    protection absent" are different claims with different evidentiary
    weight and must never be presented identically.
    """
    ADVERSE_LANGUAGE_DETECTED = "adverse_language_detected"
    EXPECTED_PROTECTION_NOT_FOUND = "expected_protection_not_found"
    UNABLE_TO_DETERMINE = "unable_to_determine"


FINDING_TYPE_LABELS: Dict[str, str] = {
    FindingType.ADVERSE_LANGUAGE_DETECTED.value: "Adverse language detected",
    FindingType.EXPECTED_PROTECTION_NOT_FOUND.value: "Expected protection not found",
    FindingType.UNABLE_TO_DETERMINE.value: "Unable to determine",
}


@dataclass
class Finding:
    """
    Clause-level anchored finding with exact position tracking.
    
    Neural-Symbolic Architecture: All findings are anchored to exact text positions
    for full auditability and reproducibility.
    
    All findings must have:
    - start_index, end_index: Exact character positions in original text
    - exact_snippet: The exact matched text (not excerpt with context)
    - surrounding_context: ±200 chars around match for display
    """
    rule_id: str
    rule_name: str
    title: str
    severity: Severity
    rationale: str
    matched_excerpt: str  # Display excerpt with context
    position: int  # Start position (kept for backward compatibility)
    context: str  # Surrounding context (±200 chars)
    # Clause-level anchoring fields (MANDATORY for enterprise trust)
    start_index: int  # Exact start character position in original text
    end_index: int  # Exact end character position in original text
    exact_snippet: str  # Exact matched text (no context, no ellipsis)
    clause_number: Optional[str] = None
    matched_keywords: List[str] = None
    aliases: List[str] = None
    # For proximity (anchor + nearby) rules: the anchor trigger word, the
    # actual risky phrase found near it, and the surrounding clause text.
    # None for direct-pattern rules, where exact_snippet already is the full match.
    evidence: Optional[Dict[str, str]] = None
    # For rules whose title claims one-sided/unilateral treatment (see
    # ONE_WAY_RULE_IDS): who the clause binds vs. who it protects, and
    # whether that asymmetry is actually established in the text.
    # Keys: obligor, beneficiary, applies_to, mutuality_status
    # (mutuality_status in {"mutual", "customer-only", "provider-only", "ambiguous"}).
    # None for rules that don't claim directionality.
    party_direction: Optional[Dict[str, str]] = None
    # Perspective framing relative to the reviewing party (default:
    # customer — see party_resolver.py). Only set alongside party_direction
    # for ONE_WAY_RULE_IDS findings. Keys: reviewing_role, beneficiary_role,
    # favorability ("favorable" | "unfavorable" | "neutral" | "unclear"),
    # note (human-readable sentence naming the actual contract parties when
    # resolved). A one-sided clause is not automatically a "risk" — e.g. a
    # customer-only termination right is favorable to a customer-side
    # review and unfavorable to the vendor, not a neutral "one-sided" flag.
    perspective: Optional[Dict[str, str]] = None
    # Populated only on a synthesized parent finding produced by
    # _group_related_findings: the rule_ids of the individual findings that
    # were folded into this one because they share a single underlying root
    # cause (e.g. one missing SOW/Schedule attachment manifesting as
    # separately-firing billing-frequency/invoice-trigger/pricing gaps).
    # None for every other finding.
    related_findings: Optional[List[str]] = None
    # Which precise claim this finding makes — see FindingType. Defaults to
    # "adverse_language_detected" since that's what a direct regex/proximity
    # hit actually proves; REQUIRED_SECTION rules override this when they
    # report a document-level absence instead.
    finding_type: str = FindingType.ADVERSE_LANGUAGE_DETECTED.value
    # Deterministic confidence scoring (see _score_confidence) — a
    # transparent, rule-based classification of how much independent
    # verification a reader should apply, computed purely from already-known
    # attributes of this finding (finding_type, evidence span length, party-
    # direction ambiguity). This is NOT a new detection signal and never
    # changes which findings are reported, only how they're labeled.
    confidence: str = "high"
    confidence_reason: str = ""
    evidence_quality: str = "bounded"

    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []
        if self.aliases is None:
            self.aliases = []
        # Validate anchoring fields are set
        assert isinstance(self.start_index, int), "start_index must be int"
        assert isinstance(self.end_index, int), "end_index must be int"
        assert isinstance(self.exact_snippet, str) and len(self.exact_snippet) > 0, "exact_snippet must be non-empty string"
        assert self.start_index <= self.end_index, "start_index must be <= end_index"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    rule_name: str
    title: str
    severity: Severity
    rationale: str

    # Either direct pattern OR (anchors + nearby)
    pattern: Optional[str] = None
    anchors: Optional[List[str]] = None
    nearby: Optional[List[str]] = None
    window: int = 350
    
    # Explicit aliases for LLM output validation
    # These are alternative names/titles the LLM might use for this rule
    aliases: List[str] = None

    # PRESENCE_RISK (default): pattern/anchors+nearby above are adverse
    # language whose presence IS the finding.
    #
    # REQUIRED_SECTION: pattern/anchors+nearby above still detect adverse
    # language if present (e.g. an explicit "no obligation to notify"
    # clause), but if no adverse language is found, the rule additionally
    # checks whether the topic is even in scope for this document
    # (topic_patterns — ALL must match somewhere) and, if so, whether any
    # protective language for it exists anywhere in the document
    # (protective_patterns — ANY match suffices). Only when the topic is in
    # scope AND no protective language is found does the rule report
    # "expected protection not found" — regex silence alone is never treated
    # as proof of absence.
    rule_class: RuleClass = RuleClass.PRESENCE_RISK
    topic_patterns: Optional[List[str]] = None
    protective_patterns: Optional[List[str]] = None

    def __post_init__(self):
        # Ensure aliases is a list (dataclass frozen=True requires this pattern)
        if self.aliases is None:
            object.__setattr__(self, 'aliases', [])
        if self.rule_class == RuleClass.REQUIRED_SECTION:
            assert self.topic_patterns, f"{self.rule_id}: REQUIRED_SECTION rules must define topic_patterns"
            assert self.protective_patterns, f"{self.rule_id}: REQUIRED_SECTION rules must define protective_patterns"


def _looks_like_escaped_newlines(text: str) -> bool:
    """
    Detect source text that uses literal two-character "\\n" (and "\\r\\n")
    escape sequences instead of real line breaks — e.g. a JSON/CSV export
    that was decoded but never unescaped. Real contract text is
    overwhelmingly multi-line; if there are many literal backslash-n
    substrings but almost no real newline characters, the document was not
    properly decoded and clause boundaries are invisible to the chunker.
    """
    literal_n = text.count("\\n")
    real_newlines = text.count("\n")
    return literal_n >= 10 and real_newlines <= max(2, literal_n // 10)


def normalize_contract_text(text: str) -> str:
    """
    Deterministic, pure text-level normalization applied once, up front,
    before chunking or matching. Two responsibilities:

    1. Unicode punctuation normalization (smart quotes/dashes/ellipsis) so
       regex patterns written with ASCII punctuation still match text
       extracted from PDFs/Word documents.
    2. Un-escaping literal "\\n"/"\\r\\n" sequences when the document is
       clearly using them in place of real line breaks (see
       _looks_like_escaped_newlines). Without this, _chunk_text() never
       finds a real "\n\n" paragraph break and silently falls back to blind
       fixed-size slicing, which is what allows evidence spans to bridge
       unrelated clauses.

    All downstream position math (start_index/end_index) is relative to the
    string this function returns, not the raw input — this function must
    run exactly once, before any offset is recorded.
    """
    text = (
        text
        .replace("‘", "'").replace("’", "'")   # left/right single quotes -> '
        .replace("“", '"').replace("”", '"')   # left/right double quotes -> "
        .replace("–", "-").replace("—", "-")   # en-dash / em-dash -> -
        .replace("…", "...")                          # ellipsis -> ...
        .replace("\r\n", "\n").replace("\r", "\n")        # normalize real line endings first
    )
    if _looks_like_escaped_newlines(text):
        text = (
            text
            .replace("\\r\\n", "\n")
            .replace("\\n", "\n")
            .replace("\\t", "\t")
        )
    return text


# Matches the start of a TOP-LEVEL numbered section header ("7. PREVAIL'S
# OBLIGATIONS", "10. INTELLECTUAL PROPERTY") but deliberately NOT a
# sub-clause ("7.1", "10.2") — \d{1,2}\.\s+ requires whitespace immediately
# after the single trailing period, which a sub-clause number never has.
# This keeps all sub-clauses of one section in a single chunk (so rules
# that legitimately reason about one section, e.g. 7.4-7.6's SLA language,
# stay together) while still cutting between unrelated top-level sections
# (so a match can no longer bridge, say, section 7 to section 10).
_SECTION_BOUNDARY_RE = re.compile(r"\n(?=\d{1,2}\.\s+[A-Z])")


def _chunk_text(text: str) -> List[Tuple[int, str]]:
    """
    Split into (start_offset, substring) chunks, preferring real clause
    structure over blind slicing:

    1. Blank-line ("\n\n") paragraph breaks, if present — contracts often
       separate sections this way.
    2. Top-level numbered-section boundaries (see _SECTION_BOUNDARY_RE), if
       present — handles single-newline documents where every clause is on
       its own line but sections aren't blank-line separated.
    3. Fixed-size chunks, only as a last resort when neither structural cue
       is available.

    Chunks are verbatim slices of `text` (only outer whitespace is trimmed,
    tracked via offset) — internal whitespace is never altered. This keeps
    `chunk_start + match.span()` exactly equal to the position in `text`,
    so start_index/end_index never drift from the source document.
    """
    if "\n\n" in text:
        chunks: List[Tuple[int, str]] = []
        pos = 0
        for part in text.split("\n\n"):
            stripped = part.strip()
            if stripped:
                local_offset = part.find(stripped)
                chunks.append((pos + local_offset, stripped))
            pos += len(part) + 2  # +2 for the "\n\n" separator consumed by split
        if chunks:
            return chunks

    boundary_matches = list(_SECTION_BOUNDARY_RE.finditer(text))
    if boundary_matches:
        starts = [0] + [m.start() + 1 for m in boundary_matches]  # +1 skips the "\n" itself
        chunks = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(text)
            piece = text[start:end]
            stripped = piece.strip()
            if stripped:
                local_offset = piece.find(stripped)
                chunks.append((start + local_offset, stripped))
        if chunks:
            return chunks

    size = 3000
    return [(i, text[i : i + size]) for i in range(0, len(text), size)]


def _excerpt(text: str, start: int, end: int, radius: int = 140) -> str:
    s = max(0, start - radius)
    e = min(len(text), end + radius)
    return f"...{text[s:e].strip()}..."


def _extract_clause_number(text: str, position: int, window: int = 500) -> Optional[str]:
    """
    Attempt to extract clause number near the match position.
    Looks for patterns like: "1.6", "Section 4.2", "§7", "Clause 3.1"
    """
    start = max(0, position - window)
    end = min(len(text), position + window)
    context = text[start:end]
    
    # Patterns to match clause numbers
    patterns = [
        r'\b(?:section|clause|article|paragraph)\s+(\d+(?:\.\d+)*)',
        r'\b(\d+\.\d+(?:\.\d+)*)\b',  # e.g., 1.6, 4.2.1
        r'§\s*(\d+(?:\.\d+)*)',
        r'\((\d+)\)',  # e.g., (1), (2)
    ]
    
    for pattern in patterns:
        matches = list(re.finditer(pattern, context, re.IGNORECASE))
        if matches:
            # Return the closest match to the center of the context
            center = len(context) // 2
            closest = min(matches, key=lambda m: abs(m.start() - center))
            return closest.group(1) if closest.groups() else closest.group(0)
    
    return None


def _extract_matched_keywords(match_text: str, pattern: Optional[str] = None) -> List[str]:
    """
    Extract key phrases from matched text that likely triggered the rule.
    Returns a list of short, meaningful keyword phrases.
    """
    keywords = []
    
    # Extract quoted phrases
    quoted = re.findall(r'"([^"]+)"', match_text)
    keywords.extend(quoted[:3])  # Limit to 3
    
    # Extract key phrases (2-4 words) that match common risk terms
    risk_terms = [
        r'\b(?:not\s+to|shall\s+not|may\s+not|must\s+not)\s+\w+(?:\s+\w+){0,2}',
        r'\b(?:unlimited|without\s+limit|no\s+limit)',
        r'\b(?:indemnif\w+|liability|damages?)',
        r'\b(?:assign|transfer|ownership)',
        r'\b(?:confidential|proprietary)',
        r'\b(?:perpetual|indefinite|forever)',
    ]
    
    for term_pattern in risk_terms:
        matches = re.findall(term_pattern, match_text, re.IGNORECASE)
        keywords.extend(matches[:2])  # Limit to 2 per pattern
    
    # Deduplicate and limit
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen and len(kw) > 5:  # Filter very short matches
            seen.add(kw_lower)
            unique_keywords.append(kw)
            if len(unique_keywords) >= 5:  # Max 5 keywords
                break

    return unique_keywords[:5]


def _score_confidence(finding: "Finding") -> Dict[str, str]:
    """
    Deterministic confidence/evidence-quality scoring.

    Pure function of attributes the finding already carries — finding_type,
    evidence span length, party-direction ambiguity. This is NOT a new
    detection mechanism and never changes which findings are reported or
    their severity; it labels how much independent verification a reader
    should apply before relying on a given finding, using the same logic
    every time for the same inputs (fully deterministic, no ML/heuristic
    randomness).

    - ADVERSE_LANGUAGE_DETECTED: the quoted evidence IS the adverse
      language — highest confidence.
    - EXPECTED_PROTECTION_NOT_FOUND: an absence claim, inherently softer
      than a direct textual match even when correctly gated by a
      document-wide protective-language search — medium confidence.
    - UNABLE_TO_DETERMINE: the engine explicitly could not confirm absence
      (document too short) — low confidence.
    - Ambiguous party-direction on a directional finding downgrades
      confidence one level, since the engine could not confirm which party
      the clause favors from the text alone.
    - evidence_quality flags spans wide enough that a reader should
      re-verify the excerpt actually supports the finding at a glance,
      rather than asserting the span itself is wrong.
    """
    span = finding.end_index - finding.start_index

    if finding.finding_type == FindingType.UNABLE_TO_DETERMINE.value:
        confidence = "low"
        reason = "Document too short to reliably confirm this protection is absent."
    elif finding.finding_type == FindingType.EXPECTED_PROTECTION_NOT_FOUND.value:
        confidence = "medium"
        reason = (
            "Absence claim: topic confirmed in scope, no protective language found after a "
            "full-document search."
        )
    else:
        confidence = "high"
        reason = "Direct textual match: the quoted evidence is itself the adverse language supporting this finding."

    if finding.party_direction and finding.party_direction.get("mutuality_status") == "ambiguous":
        confidence = "medium" if confidence == "high" else "low"
        reason += (
            " Party-direction analysis found both parties named without conclusively establishing "
            "which one this clause favors — confirm manually."
        )

    if finding.related_findings:
        reason += f" Root-cause parent finding grouping {len(finding.related_findings)} related sub-findings."

    if span > 500:
        evidence_quality = "wide_span_review_recommended"
    elif span < 2:
        evidence_quality = "minimal_span"
    else:
        evidence_quality = "bounded"

    return {"confidence": confidence, "confidence_reason": reason, "evidence_quality": evidence_quality}


# Rules whose title/rationale claims one-sided, unilateral, or asymmetric
# treatment between the two contracting parties. For these — and only
# these — the engine must establish actual directionality before the
# "one-way" label is allowed to stick; see _classify_party_direction.
ONE_WAY_RULE_IDS = frozenset({
    "H_ATTFEE_01",
    "H_CONSEQUENTIAL_01",
    "H_ASYMMETRIC_LIABILITY_01",
    "H_TERM_CONVENIENCE_01",
    "H_INDEM_ONEWAY_01",
})


# Groups of rule_ids whose findings, when 2+ fire on the SAME document,
# share a single underlying root cause rather than representing
# independent risks — verified: a document missing SOW 1/Schedule 1
# independently triggered four separate Medium findings (billing
# frequency, invoice trigger, price-exhibit, exhibit-missing), all
# traceable to the one fact that the attachment isn't included. Counting
# that as four risks inflates the report; _group_related_findings collapses
# each group into a single parent finding listing the affected sub-topics.
ROOT_CAUSE_GROUPS: Dict[str, Dict[str, object]] = {
    "missing_sow_schedule": {
        "rule_ids": frozenset({
            "M_BILLING_FREQUENCY_01",
            "M_EXHIBIT_MISSING_01",
            "M_PAYMENT_TRIGGER_01",
            "M_PRICE_EXHIBIT_MISSING_01",
        }),
        "rule_name": "missing_sow_schedule_attachment",
        "title": "SOW / Schedule referenced but not attached — pricing, billing, and deliverables undefined",
        "rationale": (
            "The Agreement repeatedly references a Statement of Work and/or Schedule for pricing, billing "
            "frequency, invoice triggers, and deliverables, but the referenced attachment is not included in "
            "this document. This is ONE root cause, not several independent risks — attaching the actual SOW/"
            "Schedule resolves every sub-topic listed below at once."
        ),
    },
}


class SignatureReadiness(str, Enum):
    """
    Workflow decision layer, separate from and additive to Severity/
    overall_risk. Severity answers "how risky is this clause"; this answers
    "what should happen to this contract next." A contract with a single
    publicity clause and a contract with uncapped liability + uncapped
    indemnification can both be overall_risk="high" while needing very
    different handling — this layer is what makes that distinction.
    """
    READY_TO_SEND = "ready_to_send"
    COMMERCIAL_REVIEW_RECOMMENDED = "commercial_review_recommended"
    LEGAL_REVIEW_REQUIRED = "legal_review_required"
    BLOCKED_BY_POLICY = "blocked_by_policy"


# Business-policy classification of which HIGH findings are severe enough to
# require legal counsel before signature, vs. which are worth flagging but
# fine to route through ordinary commercial negotiation. This is a workflow
# policy call, not a legal determination — reviewable and adjustable per
# organization, but it must be explicit and auditable rather than inferred
# from raw severity counts.
#
# A finding only counts toward blocking if its FINAL severity (after
# suppression/mutuality downgrades) is still HIGH — a downgraded finding
# (e.g. a mutual attorneys' fee clause, or an indemnity limited "to the
# extent required by law") has already had its risk contained and should
# not force legal review on its own.

# Hard policy blockers: exposure most organizations treat as non-negotiable
# without executive/legal sign-off, regardless of what else is in the contract.
POLICY_BLOCK_RULE_IDS = frozenset({
    "H_PERSONAL_01",       # personal liability exposure outside the company
    "H_DATA_PRIVACY_01",   # personal data processed with no DPA/GDPR/CCPA protections
    "H_AI_TRAINING_01",    # customer data usable to train third-party AI/ML models
})

# Other HIGH findings serious enough to warrant legal (not just commercial)
# review before signature.
BLOCKING_RULE_IDS = frozenset({
    "H_INDEM_01",
    "H_LOL_01",
    "H_LOL_CARVEOUT_01",
    "H_INDEM_ONEWAY_01",
    "H_IP_01",
    "H_IP_WORK_PRODUCT_01",
    "H_ASSIGN_CHANGE_CTRL_01",
    "H_CONSEQUENTIAL_01",
    "H_ASYMMETRIC_LIABILITY_01",
    "H_UNILATERAL_MOD_01",
    "H_PRICE_ESCAL_01",
}) | POLICY_BLOCK_RULE_IDS

_MUTUAL_RE = re.compile(
    r"\b(either\s+party|either\s+of\s+the\s+parties|both\s+parties|each\s+party|mutual(ly)?|"
    r"reciprocal(ly)?|prevailing\s+party|non-?prevailing\s+party)\b",
    re.IGNORECASE,
)
_PROVIDER_ROLE_RE = re.compile(
    r"\b(vendor|provider|supplier|licensor|contractor|company|disclosing\s+party)\b",
    re.IGNORECASE,
)
_CUSTOMER_ROLE_RE = re.compile(
    r"\b(customer|client|licensee|buyer|purchaser|receiving\s+party)\b",
    re.IGNORECASE,
)


def _classify_party_direction(
    clause_text: str, party_map: Optional[PartyRoleMap] = None
) -> Dict[str, str]:
    """
    Deterministically classify whether a clause establishes one-way treatment
    between the two contracting parties, based on explicit party-scoping
    language in the clause text.

    Returns a dict with:
    - obligor: the party bound by / performing under the clause
      ("provider" | "customer" | "both_parties" | "unknown")
    - beneficiary: the party the clause protects or favors
      ("provider" | "customer" | "both_parties" | "unknown")
    - applies_to: which party role(s) the clause text names
      ("provider" | "customer" | "both_parties" | "ambiguous" | "unknown")
    - mutuality_status: "mutual" | "customer-only" | "provider-only" | "ambiguous"

    This is intentionally conservative: without explicit "either party" /
    "both parties" / role-only language, the clause is classified "ambiguous"
    rather than guessed as one-way. A rule may only be reported/labeled as
    one-way when mutuality_status is "customer-only" or "provider-only".

    `party_map`, if provided (see party_resolver.py), supplies regexes built
    from the CONTRACT'S OWN defined party names (e.g. "Prevail", "Company"),
    resolved to vendor/customer roles by reading the contract's own
    recitals — not by matching generic role words. When a role resolves via
    party_map, its regex is used INSTEAD OF (not in addition to) the generic
    word list for that role, because the generic list is exactly what
    misreads a contract whose defined term "Company" denotes the customer
    (verified: the generic list's inclusion of the bare word "company" as a
    vendor-role synonym misclassified a real customer-only right as
    "provider-only"). Falls back to the generic word list only when
    party_map has no resolution for that role (e.g. it's None, or the
    contract never defines short party names at all).
    """
    if _MUTUAL_RE.search(clause_text):
        return {
            "obligor": "both_parties",
            "beneficiary": "both_parties",
            "applies_to": "both_parties",
            "mutuality_status": "mutual",
        }

    provider_re = (party_map.role_pattern(VENDOR_ROLE) if party_map else None) or _PROVIDER_ROLE_RE
    customer_re = (party_map.role_pattern(CUSTOMER_ROLE) if party_map else None) or _CUSTOMER_ROLE_RE

    provider_hit = provider_re.search(clause_text)
    customer_hit = customer_re.search(clause_text)

    if provider_hit and customer_hit:
        # Both roles are named without explicit mutual language — could be a
        # genuinely two-sided clause described per-party, or a one-way clause
        # that merely mentions the other party. Regex can't disambiguate
        # reliably, so this stays "ambiguous" rather than asserting either way.
        return {
            "obligor": "ambiguous",
            "beneficiary": "ambiguous",
            "applies_to": "ambiguous",
            "mutuality_status": "ambiguous",
        }
    if provider_hit:
        return {
            "obligor": "provider",
            "beneficiary": "unknown",
            "applies_to": "provider",
            "mutuality_status": "provider-only",
        }
    if customer_hit:
        return {
            "obligor": "customer",
            "beneficiary": "unknown",
            "applies_to": "customer",
            "mutuality_status": "customer-only",
        }
    return {
        "obligor": "unknown",
        "beneficiary": "unknown",
        "applies_to": "unknown",
        "mutuality_status": "ambiguous",
    }


def _build_perspective(
    party_direction: Optional[Dict[str, str]],
    party_map: Optional[PartyRoleMap],
    reviewing_role: str = CUSTOMER_ROLE,
) -> Optional[Dict[str, str]]:
    """
    Translate a party_direction result into an explicit favorable/
    unfavorable framing relative to the reviewing party, naming the actual
    contract parties when resolved (see party_resolver.py).

    A one-sided clause is not automatically a "risk" to the reviewing
    party — a customer-only termination-for-convenience right, for
    example, is favorable to a customer-side review and unfavorable to the
    vendor. Blanket "one-sided" labeling without this framing was flagged
    as a defect (a real customer-favorable right was reported identically
    to a genuinely adverse vendor-only right).
    """
    if not party_direction:
        return None

    status = party_direction.get("mutuality_status")
    other_role = VENDOR_ROLE if reviewing_role == CUSTOMER_ROLE else CUSTOMER_ROLE
    reviewer_name = (party_map.name_for_role(reviewing_role) if party_map else None) or (
        "the customer" if reviewing_role == CUSTOMER_ROLE else "the vendor"
    )
    other_name = (party_map.name_for_role(other_role) if party_map else None) or (
        "the vendor" if reviewing_role == CUSTOMER_ROLE else "the customer"
    )

    if status == "mutual":
        return {
            "reviewing_role": reviewing_role,
            "beneficiary_role": "both",
            "favorability": "neutral",
            "note": f"This applies equally to both {reviewer_name} and {other_name}.",
        }

    if status == "customer-only":
        beneficiary_role = CUSTOMER_ROLE
    elif status == "provider-only":
        beneficiary_role = VENDOR_ROLE
    else:
        return {
            "reviewing_role": reviewing_role,
            "beneficiary_role": "unclear",
            "favorability": "unclear",
            "note": (
                "The clause text names both parties without establishing which one this "
                "specifically favors — confirm manually."
            ),
        }

    favorability = "favorable" if beneficiary_role == reviewing_role else "unfavorable"
    beneficiary_name = reviewer_name if beneficiary_role == reviewing_role else other_name
    burdened_name = other_name if beneficiary_role == reviewing_role else reviewer_name
    return {
        "reviewing_role": reviewing_role,
        "beneficiary_role": beneficiary_role,
        "favorability": favorability,
        "note": (
            f"This right/obligation applies only to {beneficiary_name}, not {burdened_name} — "
            f"{favorability} to the reviewing party ({reviewer_name})."
        ),
    }


# IP-assignment clauses are inherently directional ("X assigns ... TO Y")
# rather than "mutual vs. one-way obligation" — the generic
# _classify_party_direction / ONE_WAY_RULE_IDS framework (built around
# "either party" mutuality language) doesn't fit them. This targets the
# actual grammatical assignee — a KNOWN party name appearing after "to" —
# directly. A generic "\bto\s+(\w+)\b" capture is not enough: boilerplate
# like "assigns, and agrees TO ASSIGN, to Company ..." has a closer,
# non-party "to <verb>" that a generic capture matches first.


def _infer_ip_assignment_perspective(
    exact_snippet: str, party_map: Optional[PartyRoleMap], reviewing_role: str = CUSTOMER_ROLE
) -> Optional[Dict[str, str]]:
    """
    For an IP-assignment finding (H_IP_01 / H_IP_WORK_PRODUCT_01), determine
    who the assignment actually runs TO using the contract's own resolved
    party names, and frame favorability accordingly. An assignment INTO the
    reviewing party's ownership is favorable, not a risk — verified case:
    "Prevail hereby ... assigns ... to Company all of its right, title, and
    interest" transfers IP to the customer, the opposite of a risk to a
    customer-side review, but the un-directional rule title ("Broad IP
    assignment") would otherwise report it identically to IP flowing away
    from the reviewing party.
    """
    if not party_map or not party_map.has_resolution():
        return None
    known_names = sorted(party_map.name_to_role.keys(), key=len, reverse=True)
    if not known_names:
        return None
    assigns_to_known_party_re = re.compile(
        r"\bassigns?\b.{0,80}?\bto\s+(" + "|".join(re.escape(n) for n in known_names) + r")\b",
        re.IGNORECASE | re.DOTALL,
    )
    m = assigns_to_known_party_re.search(exact_snippet)
    if not m:
        return None
    assignee_role = party_map.role_of(m.group(1))
    if assignee_role == UNKNOWN_ROLE:
        return None

    other_role = VENDOR_ROLE if reviewing_role == CUSTOMER_ROLE else CUSTOMER_ROLE
    favorability = "favorable" if assignee_role == reviewing_role else "unfavorable"
    assignee_name = party_map.name_for_role(assignee_role) or m.group(1)
    reviewer_name = party_map.name_for_role(reviewing_role) or "the reviewing party"
    return {
        "reviewing_role": reviewing_role,
        "beneficiary_role": assignee_role,
        "favorability": favorability,
        "note": (
            f"This assignment transfers ownership TO {assignee_name} — "
            f"{favorability} to the reviewing party ({reviewer_name})."
        ),
    }


def _extract_payment_terms(text: str) -> Dict[str, Optional[object]]:
    """
    Extract structured payment terms so a contract-to-cash consumer (e.g.
    Agree's invoicing) can compare them against an actual invoice
    configuration, rather than only getting a "Net 30 mentioned" flag.

    Best-effort / first-match extraction — deterministic regex, not NLU.
    Any field that can't be confidently identified is None rather than guessed.
    """
    due_days: Optional[int] = None
    m = re.search(r"\bnet\s+(\d{1,3})\b", text, re.IGNORECASE)
    if not m:
        m = re.search(r"\bdue\s+(?:within|in)\s+(\d{1,3})\s+days?\b", text, re.IGNORECASE)
    if m:
        due_days = int(m.group(1))

    currency: Optional[str] = None
    m = re.search(r"\b(USD|EUR|GBP|CAD|AUD|United\s+States\s+Dollars?)\b", text, re.IGNORECASE)
    if m:
        raw = m.group(1).upper()
        currency = "USD" if "DOLLAR" in raw else raw
    elif re.search(r"€", text):
        currency = "EUR"
    elif re.search(r"£", text):
        currency = "GBP"
    elif re.search(r"\$\s?[\d,]", text):
        currency = "USD"  # heuristic: bare "$" with no explicit code, assume USD

    billing_frequency: Optional[str] = None
    for pattern, label in (
        (r"\bmonthly\b", "monthly"),
        (r"\bquarterly\b", "quarterly"),
        (r"\bannual(?:ly)?\b|\byearly\b", "annually"),
        (r"\bweekly\b", "weekly"),
        (r"\bone[-\s]?time\b", "one_time"),
        (r"\brecurring\b", "recurring"),
    ):
        if re.search(pattern, text, re.IGNORECASE):
            billing_frequency = label
            break

    invoice_trigger: Optional[str] = None
    m = re.search(
        r"\binvoic\w*\b[^.]{0,60}\b(?:upon|following|after|within)\b[^.]{0,60}"
        r"\b(activation|delivery|execution|go-live|commencement|acceptance)\b",
        text,
        re.IGNORECASE,
    )
    if m:
        invoice_trigger = m.group(1).lower()

    return {
        "due_days": due_days,
        "currency": currency,
        "billing_frequency": billing_frequency,
        "invoice_trigger": invoice_trigger,
    }


def _find_all(pattern: str, text: str) -> Iterable[re.Match]:
    return re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class ProximityMatch:
    """Anchor span, matched nearby (risk-phrase) span, and their combined span."""
    anchor_start: int
    anchor_end: int
    nearby_start: int
    nearby_end: int
    combined_start: int
    combined_end: int


def _proximity_spans(
    anchors: List[str], nearby: List[str], text: str, window: int
) -> List[ProximityMatch]:
    """
    Find spans where an anchor occurs and any 'nearby' (risk-phrase) pattern
    occurs within +/- window. Returns the anchor span, the matched nearby
    span, and a combined span covering both — so callers can surface the
    actual risky language, not just the trigger word.
    """
    matches: List[ProximityMatch] = []
    anchor_matches: List[re.Match] = []
    for a in anchors:
        anchor_matches.extend(list(_find_all(a, text)))

    if not anchor_matches:
        return []

    for am in anchor_matches:
        a_start, a_end = am.span()
        left = max(0, a_start - window)
        right = min(len(text), a_end + window)
        neighborhood = text[left:right]

        for n in nearby:
            nm = re.search(n, neighborhood, flags=re.IGNORECASE | re.DOTALL)
            if nm:
                n_start = left + nm.start()
                n_end = left + nm.end()
                combined_start = min(a_start, n_start)
                combined_end = max(a_end, n_end)
                matches.append(
                    ProximityMatch(a_start, a_end, n_start, n_end, combined_start, combined_end)
                )
                break

    # De-dup by combined span (the evidence span callers actually anchor on)
    seen = set()
    deduped: List[ProximityMatch] = []
    for pm in sorted(matches, key=lambda m: (m.combined_start, m.combined_end)):
        key = (pm.combined_start, pm.combined_end)
        if key not in seen:
            seen.add(key)
            deduped.append(pm)
    return deduped


# Rule Engine Version - loaded from rules/version.json for transparency and trust
def _load_ruleset_version() -> Dict:
    """Load ruleset version metadata from version.json file."""
    version_path = Path(__file__).parent / "rules" / "version.json"
    if version_path.exists():
        try:
            with open(version_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            # Fallback to hardcoded version if file read fails
            return {"version": "1.0.3", "released": "2026-01-14", "scope": "Commercial NDAs and MSAs", "changes": []}
    else:
        # Fallback if version.json doesn't exist
        return {"version": "1.0.3", "released": "2026-01-14", "scope": "Commercial NDAs and MSAs", "changes": []}

_RULESET_VERSION_DATA = _load_ruleset_version()
RULE_ENGINE_VERSION = _RULESET_VERSION_DATA.get("version", "1.0.3")


class RuleEngine:
    """
    Deterministic engine producing:
      - findings (list[Finding])
      - overall_risk ("high"|"medium"|"low")
      - rule_counts
      - version (rule engine version)
    """

    def __init__(self) -> None:
        self.rules: List[Rule] = self._build_rules()
        self.version = RULE_ENGINE_VERSION

    def _compute_overall_risk(self, findings: List[Finding], counts: Dict[str, int]) -> str:
        """
        Compute overall risk level from findings.

        Policy (MANDATORY):
        - overall_risk = "critical" if any finding.severity == "critical"
        - else overall_risk = "high" if any finding.severity == "high"
        - else overall_risk = "medium" if count(medium) >= 2
        - else overall_risk = "low"

        This policy ensures that a single critical- or high-risk finding elevates the entire
        assessment, while multiple medium-risk findings also warrant elevated attention.
        """
        if counts.get("critical", 0) > 0:
            return "critical"
        elif counts["high"] > 0:
            return "high"
        elif counts["medium"] >= 2:
            return "medium"
        else:
            return "low"

    def _compute_workflow_decision(self, findings: List[Finding]) -> Dict:
        """
        Business workflow decision layer, additive to (never replacing)
        overall_risk/severity. Classifies findings as policy-blocking,
        legal-review-blocking, or non-blocking, and derives a single
        signature_readiness recommendation from that classification —
        rather than from raw severity/medium-count thresholds, which treat a
        publicity clause and uncapped liability as equally "high".
        """
        policy_blocked: List[str] = []
        blocking: List[str] = []
        non_blocking: List[str] = []
        seen_policy, seen_blocking, seen_non_blocking = set(), set(), set()

        for f in findings:
            # Only a still-HIGH-or-CRITICAL-severity finding counts as
            # blocking — a finding downgraded by suppression/mutuality
            # analysis has already had its risk contained.
            is_high = f.severity in (Severity.HIGH, Severity.CRITICAL)
            if is_high and f.rule_id in POLICY_BLOCK_RULE_IDS:
                if f.rule_id not in seen_policy:
                    policy_blocked.append(f.rule_id)
                    seen_policy.add(f.rule_id)
            elif is_high and f.rule_id in BLOCKING_RULE_IDS:
                if f.rule_id not in seen_blocking:
                    blocking.append(f.rule_id)
                    seen_blocking.add(f.rule_id)
            else:
                if f.rule_id not in seen_non_blocking:
                    non_blocking.append(f.rule_id)
                    seen_non_blocking.add(f.rule_id)

        if policy_blocked:
            signature_readiness = SignatureReadiness.BLOCKED_BY_POLICY.value
        elif blocking:
            signature_readiness = SignatureReadiness.LEGAL_REVIEW_REQUIRED.value
        elif non_blocking:
            signature_readiness = SignatureReadiness.COMMERCIAL_REVIEW_RECOMMENDED.value
        else:
            signature_readiness = SignatureReadiness.READY_TO_SEND.value

        return {
            "signature_readiness": signature_readiness,
            # blocking_findings includes policy-blocked rule_ids too (a
            # policy block is still a blocking finding); policy_blocked_findings
            # additionally isolates which ones triggered the hardest tier.
            "blocking_findings": policy_blocked + blocking,
            "policy_blocked_findings": policy_blocked,
            "non_blocking_findings": non_blocking,
        }

    def _check_required_section(self, rule: Rule, text: str) -> Optional[Finding]:
        """
        Document-level absence check for a REQUIRED_SECTION rule that found
        no adverse language. Only called when the chunked adverse-language
        pass produced nothing for this rule.

        - Topic not in scope for this document (all of topic_patterns must
          match somewhere for the topic to be "in scope" — mirrors
          classify-then-check) -> no finding; the requirement doesn't apply
          here, which is not the same claim as "protection is missing".
        - Topic in scope and protective language found anywhere -> no
          finding; the protection exists.
        - Topic in scope, no protective language found, but the document is
          too short/sparse to reliably conclude it's truly absent (rather
          than just not yet written/extracted) -> "unable to determine".
        - Topic in scope, no protective language found, document long enough
          to trust the negative result -> "expected protection not found".
        """
        _MIN_RELIABLE_DOC_LENGTH = 150

        topic_in_scope = all(re.search(p, text, re.IGNORECASE | re.DOTALL) for p in rule.topic_patterns)
        if not topic_in_scope:
            return None  # requirement doesn't apply to this document; not a finding

        protective_match = None
        for p in rule.protective_patterns:
            protective_match = re.search(p, text, re.IGNORECASE | re.DOTALL)
            if protective_match:
                break
        if protective_match is not None:
            return None  # protective language exists; no finding

        if len(text.strip()) < _MIN_RELIABLE_DOC_LENGTH:
            return Finding(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                title=rule.title,
                severity=Severity.LOW,
                rationale=rule.rationale + " Document is too short to reliably determine whether this protection is truly absent.",
                matched_excerpt=f"...{text.strip()}...",
                position=0,
                context=text,
                start_index=0,
                end_index=max(1, len(text)),
                exact_snippet=text.strip() or "(empty document)",
                aliases=rule.aliases or [],
                finding_type=FindingType.UNABLE_TO_DETERMINE.value,
            )

        # Topic is in scope and no protective language was found anywhere in
        # the document. Anchor the finding to the first topic mention so it
        # still has a real, auditable position rather than a fabricated one.
        anchor_match = None
        for p in rule.topic_patterns:
            anchor_match = re.search(p, text, re.IGNORECASE | re.DOTALL)
            if anchor_match:
                break
        anchor_start, anchor_end = anchor_match.span()
        excerpt = _excerpt(text, anchor_start, anchor_end)

        return Finding(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            title=rule.title,
            severity=rule.severity,
            rationale=rule.rationale + " No protective language for this topic was found anywhere in the document.",
            matched_excerpt=excerpt,
            position=anchor_start,
            context=text[max(0, anchor_start - 200):min(len(text), anchor_end + 200)],
            start_index=anchor_start,
            end_index=anchor_end,
            exact_snippet=text[anchor_start:anchor_end],
            aliases=rule.aliases or [],
            finding_type=FindingType.EXPECTED_PROTECTION_NOT_FOUND.value,
        )

    def _make_document_finding(
        self, rule_id: str, rule_name: str, title: str, severity: Severity,
        rationale: str, text: str, anchor_match: Optional[re.Match],
    ) -> Finding:
        """
        Build a Finding for a document-wide consistency check (conflicting
        values found in different places in the document, not a single
        clause) rather than a single regex/proximity match. Anchored to the
        first occurrence found so it still has a real, auditable position.
        """
        if anchor_match is not None:
            s, e = anchor_match.span()
        else:
            s, e = 0, min(1, len(text))
        return Finding(
            rule_id=rule_id,
            rule_name=rule_name,
            title=title,
            severity=severity,
            rationale=rationale,
            matched_excerpt=_excerpt(text, s, e),
            position=s,
            context=text[max(0, s - 200):min(len(text), e + 200)],
            start_index=s,
            end_index=max(e, s + 1),
            exact_snippet=text[s:e] if e > s else "(document-wide inconsistency; no single anchor)",
            aliases=[],
            finding_type=FindingType.ADVERSE_LANGUAGE_DETECTED.value,
        )

    def _check_cross_document_conflicts(self, text: str) -> List[Finding]:
        """
        Contract-to-cash correctness checks that require comparing values
        found in different parts of the document, rather than a single
        clause — no single regex/proximity match can prove "these two
        numbers disagree" or "this entity is named two different ways."
        """
        findings: List[Finding] = []

        # H_BILLING_CONFLICT_01: multiple distinct "Net X days" payment terms
        net_days = sorted(set(re.findall(r"\bnet\s+(\d{1,3})\s*days?\b", text, re.IGNORECASE)), key=int)
        if len(net_days) > 1:
            findings.append(self._make_document_finding(
                rule_id="H_BILLING_CONFLICT_01",
                rule_name="billing_terms_conflict",
                title="Conflicting payment due-date terms",
                severity=Severity.HIGH,
                rationale=(
                    "The contract states multiple different payment due-date terms "
                    f"({', '.join('Net ' + d for d in net_days)}), which will not match a "
                    "single invoice configuration and may prevent successful billing."
                ),
                text=text,
                anchor_match=re.search(r"\bnet\s+\d{1,3}\s*days?\b", text, re.IGNORECASE),
            ))

        # H_PRICE_CONFLICT_01: multiple distinct total contract price/fee amounts
        amounts = sorted(set(re.findall(
            r"\btotal\s+(?:contract\s+)?(?:price|fee|value|amount)\D{0,20}\$\s?([\d,]+(?:\.\d{2})?)",
            text, re.IGNORECASE,
        )))
        if len(amounts) > 1:
            findings.append(self._make_document_finding(
                rule_id="H_PRICE_CONFLICT_01",
                rule_name="price_conflict",
                title="Conflicting contract price or fee amounts",
                severity=Severity.HIGH,
                rationale=(
                    "The contract states conflicting total price/fee amounts "
                    f"(${', $'.join(amounts)}), which must be reconciled before invoicing."
                ),
                text=text,
                anchor_match=re.search(
                    r"\btotal\s+(?:contract\s+)?(?:price|fee|value|amount)\D{0,20}\$\s?[\d,]+(?:\.\d{2})?",
                    text, re.IGNORECASE,
                ),
            ))

        # H_PARTY_IDENTITY_CONFLICT_01: same entity referred to with an
        # inconsistent legal name/suffix in different places in the document
        # (e.g. "Acme Corp" in the preamble vs. "Acme Corporation, Inc." in
        # the signature block) — ambiguous as to which entity is bound.
        entity_matches = re.findall(
            r"\b((?:[A-Z][\w&.]*\s+){1,5}[A-Z][\w&.]*),?\s+(?:a|an)\s+[A-Za-z\s]{2,30}?\s+"
            r"(?:corporation|company|limited liability company|LLC|Inc\.?|Ltd\.?|Corporation)\b",
            text,
        )
        variants_by_root: Dict[str, set] = {}
        for name in entity_matches:
            cleaned = name.strip().rstrip(",")
            first_word = cleaned.split()[0] if cleaned.split() else ""
            root = re.sub(r"[^a-z0-9]", "", first_word.lower())
            if not root:
                continue
            variants_by_root.setdefault(root, set()).add(cleaned)
        conflicting = {root: v for root, v in variants_by_root.items() if len(v) > 1}
        if conflicting:
            variants = sorted(next(iter(conflicting.values())))
            findings.append(self._make_document_finding(
                rule_id="H_PARTY_IDENTITY_CONFLICT_01",
                rule_name="party_identity_conflict",
                title="Inconsistent legal entity name for the same party",
                severity=Severity.HIGH,
                rationale=(
                    "The contract refers to what appears to be the same party using "
                    f"inconsistent legal names ({', '.join(variants)}), creating ambiguity "
                    "as to which entity is actually bound."
                ),
                text=text,
                anchor_match=re.search(re.escape(variants[0]), text),
            ))

        # H_SIGNATURE_PARTY_MISSING_01: an execution/signature section exists
        # ("IN WITNESS WHEREOF") but fewer than two "By:" signature lines are
        # present — one party's signature block appears to be missing.
        if re.search(r"\bIN\s+WITNESS\s+WHEREOF\b", text, re.IGNORECASE):
            by_lines = re.findall(r"\bBy\s*:\s*(?:_{2,}|/s/|\n|[A-Z][a-z]+\s+[A-Z][a-z]+)", text)
            if len(by_lines) < 2:
                findings.append(self._make_document_finding(
                    rule_id="H_SIGNATURE_PARTY_MISSING_01",
                    rule_name="signature_party_missing",
                    title="Signature block appears to be missing for one party",
                    severity=Severity.HIGH,
                    rationale=(
                        "The document contains an execution/signature section but fewer than "
                        "two 'By:' signature lines were found — one party's signature block "
                        "may be missing, which would prevent full execution."
                    ),
                    text=text,
                    anchor_match=re.search(r"\bIN\s+WITNESS\s+WHEREOF\b", text, re.IGNORECASE),
                ))

        return findings

    # A liability-cap clause naming one side by role words alone
    # ("vendor's liability", "provider's maximum liability") is already
    # covered by H_ASYMMETRIC_LIABILITY_01's static anchors. This method
    # covers the case those anchors structurally cannot: a cap stated using
    # the CONTRACT'S OWN defined party name (e.g. "PREVAIL'S MAXIMUM
    # LIABILITY ... SHALL IN NO EVENT EXCEED ..."), which requires knowing
    # which defined name is which role — exactly what party_resolver.py
    # resolves. Verified: this exact pattern, on a real contract, was
    # previously undetected entirely (the anchors never matched "Prevail").
    _CAP_PHRASE_RE = re.compile(
        r"\b(?:maximum\s+liabilit(?:y|ies)|aggregate\s+liabilit(?:y|ies)\s+(?:shall\s+not\s+exceed|of)|"
        r"liabilit(?:y|ies)\s+shall\s+(?:in\s+no\s+event\s+)?(?:not\s+)?exceed)\b",
        re.IGNORECASE,
    )

    def _check_liability_cap_asymmetry(self, text: str, party_map: Optional[PartyRoleMap]) -> List[Finding]:
        findings: List[Finding] = []
        if not party_map or not party_map.has_resolution():
            return findings
        vendor_name = party_map.name_for_role(VENDOR_ROLE)
        customer_name = party_map.name_for_role(CUSTOMER_ROLE)
        if not vendor_name or not customer_name:
            return findings
        vendor_re = re.compile(rf"\b{re.escape(vendor_name)}\b", re.IGNORECASE)
        customer_re = re.compile(rf"\b{re.escape(customer_name)}\b", re.IGNORECASE)

        for m in self._CAP_PHRASE_RE.finditer(text):
            # Who does THIS cap belong to? Look at the short span immediately
            # before the cap phrase for the grammatical subject/possessive
            # (e.g. "PREVAIL'S MAXIMUM LIABILITY..."), not the whole document
            # — a document-wide search would find both names somewhere and
            # never resolve which one this specific cap actually names.
            subject_window = text[max(0, m.start() - 60) : m.start()]
            vendor_named = bool(vendor_re.search(subject_window))
            customer_named = bool(customer_re.search(subject_window))
            if vendor_named == customer_named:
                continue  # both or neither named as the subject -> not clearly one-sided from this anchor

            capped_role = VENDOR_ROLE if vendor_named else CUSTOMER_ROLE
            capped_name = vendor_name if vendor_named else customer_name
            uncapped_name = customer_name if vendor_named else vendor_name

            # Confirm the OTHER party's liability isn't separately capped
            # elsewhere in the document — if it is, this is a symmetric
            # cap stated in two places, not an asymmetric one.
            other_cap_re = re.compile(
                rf"\b{re.escape(uncapped_name)}\b.{{0,120}}"
                rf"\b(?:maximum\s+liabilit(?:y|ies)|liabilit(?:y|ies)\s+shall\s+not\s+exceed)\b"
                rf"|\b(?:maximum\s+liabilit(?:y|ies)|liabilit(?:y|ies)\s+shall\s+not\s+exceed)\b.{{0,120}}"
                rf"\b{re.escape(uncapped_name)}\b",
                re.IGNORECASE | re.DOTALL,
            )
            if other_cap_re.search(text):
                continue

            finding = self._make_document_finding(
                rule_id="H_ASYMMETRIC_LIABILITY_01",
                rule_name="asymmetric_liability_cap",
                title="Asymmetric liability cap",
                severity=Severity.CRITICAL,
                rationale=(
                    f"The liability cap in this clause applies only to {capped_name}'s liability. "
                    f"{uncapped_name}'s liability is not capped anywhere else in this document, so this "
                    f"asymmetry favors {capped_name} and leaves {uncapped_name} exposed to uncapped "
                    "liability while the other side's downside is bounded."
                ),
                text=text,
                anchor_match=m,
            )
            # Party direction is already known directly from which name was
            # found as the cap's subject — no need to run the generic
            # _classify_party_direction heuristic. Uses the same
            # "provider"/"customer" labels as _classify_party_direction's
            # schema (not party_resolver's VENDOR_ROLE="vendor") because
            # this rule is in ONE_WAY_RULE_IDS, and _apply_suppression_rules
            # recomputes `perspective` from `party_direction` via
            # _build_perspective, which matches against that schema's
            # literal "provider-only"/"customer-only" values.
            schema_role = "provider" if capped_role == VENDOR_ROLE else "customer"
            finding = replace(
                finding,
                party_direction={
                    "obligor": schema_role,
                    "beneficiary": schema_role,
                    "applies_to": schema_role,
                    "mutuality_status": f"{schema_role}-only",
                },
            )
            findings.append(finding)
            break  # one clause, one finding — avoid duplicates from repeated cap-phrase wording

        return findings

    # A finding whose TITLE asserts one-sided/unilateral treatment while
    # its own RATIONALE states the obligation applies to both parties is
    # self-contradictory and must never ship as-is — verified: this exact
    # combination (title "One-sided termination for convenience" next to
    # rationale text "applies to both parties, not one-sided as the rule
    # title suggests") shipped in a real report.
    _CONTRADICTORY_TITLE_RE = re.compile(r"\bone[-\s]?sided\b|\bone[-\s]?way\b|\bunilateral\b", re.IGNORECASE)
    _CONTRADICTORY_RATIONALE_RE = re.compile(
        r"\bapplies?\s+(?:equally\s+)?to\s+both\s+parties\b|\bis\s+mutual\b|\bmutually\b|"
        r"\bboth\s+parties\s+equally\b",
        re.IGNORECASE,
    )

    def _detect_contradictions(self, findings: List[Finding]) -> Tuple[List[Finding], Dict[str, str]]:
        """
        Deterministic consistency pass, run after suppression: reconciles
        any finding whose title and rationale contradict each other on
        directionality. This is a structural safety net, not a fix for a
        currently-known bug — Suppression Rule 4 in _apply_suppression_rules
        already reconciles the specific ONE_WAY_RULE_IDS/mutuality case
        (including the title) at its source. This pass catches the same
        contradiction pattern from any other source deterministically,
        rather than relying on every individual rule/suppression author to
        remember to keep title and rationale in sync.
        """
        reconciled: List[Finding] = []
        contradiction_log: Dict[str, str] = {}
        for f in findings:
            if self._CONTRADICTORY_TITLE_RE.search(f.title) and self._CONTRADICTORY_RATIONALE_RE.search(
                f.rationale
            ):
                original_title = f.title
                new_title = self._CONTRADICTORY_TITLE_RE.sub("Mutual", f.title)
                contradiction_log[f"{f.rule_id}_{f.start_index}"] = (
                    f"Title reconciled from '{original_title}' — rationale states the clause is mutual, "
                    "which contradicted the one-sided/unilateral framing in the original title"
                )
                f = replace(f, title=new_title)
            reconciled.append(f)
        return reconciled, contradiction_log

    def _group_related_findings(self, findings: List[Finding]) -> List[Finding]:
        """
        Collapse findings that share a single underlying root cause (see
        ROOT_CAUSE_GROUPS) into one parent finding, so the report doesn't
        count one missing attachment as several independent risks.

        Only collapses when 2+ members of a group actually fired — a
        single member is left as-is (nothing to group). The parent takes
        the highest severity and earliest position among its members, so
        it remains fully anchored/auditable, and lists every folded
        rule_id in `related_findings` for traceability.
        """
        severity_rank = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
        consumed_ids = set()
        grouped: List[Finding] = []

        for group_def in ROOT_CAUSE_GROUPS.values():
            members = [f for f in findings if f.rule_id in group_def["rule_ids"]]
            if len(members) < 2:
                continue
            members_sorted = sorted(members, key=lambda f: (severity_rank.get(f.severity, 9), f.start_index))
            best = members_sorted[0]
            sub_bullets = "; ".join(f"{m.title} ({m.rule_id})" for m in members_sorted)
            parent = replace(
                best,
                rule_id=f"GROUP_{group_def['rule_name']}",
                rule_name=group_def["rule_name"],
                title=group_def["title"],
                rationale=f"{group_def['rationale']} Affected sub-topics: {sub_bullets}.",
                related_findings=[m.rule_id for m in members_sorted],
            )
            grouped.append(parent)
            consumed_ids.update(id(m) for m in members)

        for f in findings:
            if id(f) not in consumed_ids:
                grouped.append(f)
        return grouped

    def _apply_suppression_rules(
        self, findings: List[Finding], text: str, party_map: Optional[PartyRoleMap] = None
    ) -> Tuple[List[Finding], Dict[str, str]]:
        """
        Apply deterministic false-positive suppression rules.

        Suppression is explicit, deterministic, and explainable.
        NO probabilistic logic. NO ML.

        Rules:
        - If indemnity clause contains "to the extent required by law" → downgrade severity
        - If IP assignment contains "excluding pre-existing IP" → suppress assignment risk
        - If a "one-way"/unilateral rule's clause is actually mutual → downgrade
          severity and strip the one-way framing (see ONE_WAY_RULE_IDS)
        - If attorneys'/legal fees language is part of an indemnification
          defense-cost provision → suppress (different legal concept)
        - If a one-sided clause is favorable to the reviewing party →
          downgrade severity and attach a perspective note instead of
          reporting it identically to a genuinely adverse one-sided clause
        - Record WHY suppression happened for auditability

        Returns:
        - (suppressed_findings, suppression_reasons_dict)
        """
        suppressed = []
        suppression_reasons = {}

        for finding in findings:
            # Get context around the finding for suppression checks
            context_start = max(0, finding.start_index - 300)
            context_end = min(len(text), finding.end_index + 300)
            context = text[context_start:context_end].lower()

            suppressed_finding = finding
            reason = None

            # Suppression Rule 1: Indemnity with "to the extent required by law"
            if finding.rule_id == "H_INDEM_01" and "to the extent required by law" in context:
                # Downgrade severity instead of suppressing. replace() carries
                # over every other field (including evidence/party_direction)
                # so downgrading never silently drops anchoring data.
                suppressed_finding = replace(
                    finding,
                    severity=Severity.MEDIUM,  # Downgrade from HIGH to MEDIUM
                    rationale=finding.rationale + " Note: Limited by 'to the extent required by law' language.",
                )
                reason = "Downgraded severity: indemnity limited by 'to the extent required by law'"

            # Suppression Rule 2: IP assignment with "excluding pre-existing IP"
            if finding.rule_id in ("H_IP_01", "H_IP_WORK_PRODUCT_01") and ("excluding pre-existing" in context or "excluding pre existing" in context or "excludes pre-existing" in context):
                # Suppress entirely (no finding)
                reason = "Suppressed: IP assignment excludes pre-existing IP"
                suppression_reasons[f"{finding.rule_id}_{finding.start_index}"] = reason
                continue  # Skip this finding

            # Suppression Rule 3: Liability cap with explicit carve-out language
            if finding.rule_id == "H_LOL_CARVEOUT_01" and "except as required by applicable law" in context:
                # Downgrade severity
                suppressed_finding = replace(
                    finding,
                    severity=Severity.MEDIUM,
                    rationale=finding.rationale + " Note: Carve-out may be required by law.",
                )
                reason = "Downgraded severity: carve-out may be required by applicable law"

            # Suppression Rule 4: "One-way"/unilateral rules whose clause text
            # actually establishes mutual treatment (e.g. "either party shall
            # be entitled to attorneys' fees"). A rule titled "one-way" must
            # not stay HIGH severity with one-way framing when the engine's
            # own party-direction classification says the clause is mutual.
            if (
                finding.rule_id in ONE_WAY_RULE_IDS
                and finding.party_direction
                and finding.party_direction.get("mutuality_status") == "mutual"
            ):
                # The title itself is rewritten, not just the rationale —
                # a title still reading "One-sided X" next to a rationale
                # stating the clause "applies to both parties" is a live
                # self-contradiction (this exact pattern shipped
                # previously), not just a nuance buried in body text.
                reconciled_title = re.sub(
                    r"\bone[-\s]?sided\b|\bone[-\s]?way\b|\bunilateral\b",
                    "Mutual",
                    suppressed_finding.title,
                    flags=re.IGNORECASE,
                )
                suppressed_finding = replace(
                    suppressed_finding,
                    title=reconciled_title,
                    severity=Severity.MEDIUM,
                    rationale=(
                        suppressed_finding.rationale
                        + " Note: Clause language ('either party'/'mutual'/'both parties') indicates "
                        "this obligation applies to both parties — the title has been corrected from "
                        "one-sided/unilateral framing to reflect this. Confirm mutuality is intended and "
                        "consistently drafted."
                    ),
                )
                reason = "Downgraded severity and corrected title: party-direction analysis found mutual language, not one-way"

            # Suppression Rule 5: "attorneys' fees"/"legal fees" language
            # that is embedded in an indemnification defense-cost provision
            # (a party reimbursing legal costs incurred defending against a
            # THIRD-PARTY claim) is a different legal concept from a
            # prevailing-party fee-shifting clause (one party pays the
            # OTHER's litigation costs in a direct two-party dispute
            # "regardless of outcome") — the latter is what H_ATTFEE_01's
            # title and rationale actually describe. Verified false
            # positive: this fired HIGH on a bare "legal fees" match inside
            # an indemnification clause covering IP-infringement/data-misuse
            # third-party claims, where no fee-shifting language of any kind
            # was present.
            if finding.rule_id == "H_ATTFEE_01" and re.search(
                r"\b(indemnif\w+|hold\s+harmless|indemnified\s+part(y|ies)|third[-\s]?party\s+claim)\b",
                context,
                re.IGNORECASE,
            ):
                reason = "Suppressed: attorneys'/legal fees language is part of an indemnification defense-cost provision, not a prevailing-party fee-shifting clause"
                suppression_reasons[f"{finding.rule_id}_{finding.start_index}"] = reason
                continue  # Skip this finding — not a fee-shifting clause at all

            # Suppression Rule 6: perspective-aware reframing. A one-sided
            # clause is not automatically a risk TO THE REVIEWING PARTY —
            # e.g. a customer-only termination-for-convenience right is
            # favorable to a customer-side review (verified: this exact
            # scenario was previously reported identically to a genuinely
            # adverse vendor-only right, with no perspective distinction at
            # all). Attach an explicit favorable/unfavorable framing naming
            # the actual contract parties, and downgrade severity when the
            # asymmetry actually favors the reviewing party.
            if finding.rule_id in ONE_WAY_RULE_IDS and suppressed_finding.party_direction:
                perspective = _build_perspective(suppressed_finding.party_direction, party_map)
                if perspective:
                    annotated_rationale = suppressed_finding.rationale + " Perspective: " + perspective["note"]
                    if perspective["favorability"] == "favorable":
                        suppressed_finding = replace(
                            suppressed_finding,
                            severity=Severity.LOW,
                            rationale=annotated_rationale,
                            perspective=perspective,
                        )
                        favorable_reason = f"Downgraded severity: {perspective['note']}"
                        reason = f"{reason}; {favorable_reason}" if reason else favorable_reason
                    elif perspective["favorability"] == "unfavorable":
                        suppressed_finding = replace(
                            suppressed_finding, rationale=annotated_rationale, perspective=perspective
                        )
                    else:
                        suppressed_finding = replace(suppressed_finding, perspective=perspective)

            # Suppression Rule 7: IP-assignment direction. Assignment
            # clauses are directional, not "one-way vs. mutual" — see
            # _infer_ip_assignment_perspective. An assignment INTO the
            # reviewing party's ownership is favorable and downgraded;
            # verified case: "Prevail hereby ... assigns ... to Company
            # all of its right, title, and interest" (Study Inventions)
            # was previously reported as a flat HIGH-severity risk to the
            # customer, when it in fact transfers IP TO the customer.
            if finding.rule_id in ("H_IP_01", "H_IP_WORK_PRODUCT_01"):
                ip_perspective = _infer_ip_assignment_perspective(suppressed_finding.exact_snippet, party_map)
                if ip_perspective:
                    annotated_rationale = suppressed_finding.rationale + " Perspective: " + ip_perspective["note"]
                    if ip_perspective["favorability"] == "favorable":
                        suppressed_finding = replace(
                            suppressed_finding,
                            severity=Severity.LOW,
                            rationale=annotated_rationale,
                            perspective=ip_perspective,
                        )
                        favorable_reason = f"Downgraded severity: {ip_perspective['note']}"
                        reason = f"{reason}; {favorable_reason}" if reason else favorable_reason
                    else:
                        suppressed_finding = replace(
                            suppressed_finding, rationale=annotated_rationale, perspective=ip_perspective
                        )

            # Suppression Rule 8: H_ASYMMETRIC_LIABILITY_01 findings from
            # the generic-role-word anchors (as opposed to the party-name-
            # aware _check_liability_cap_asymmetry path, which already
            # checks this) have no way to confirm the OTHER party isn't
            # separately capped elsewhere in the document — the anchors
            # only prove a cap phrase co-occurs with a role word, not that
            # only one party has one. If a second cap phrase exists
            # anywhere else in the document, this is likely a symmetric
            # cap stated per-party, not a proven asymmetry.
            if (
                finding.rule_id == "H_ASYMMETRIC_LIABILITY_01"
                and finding.party_direction
                and finding.party_direction.get("mutuality_status") not in ("provider-only", "customer-only")
                and len(self._CAP_PHRASE_RE.findall(text)) >= 2
            ):
                reason = "Suppressed: a second liability-cap phrase exists elsewhere in the document — likely a symmetric cap stated per-party, not a proven asymmetry"
                suppression_reasons[f"{finding.rule_id}_{finding.start_index}"] = reason
                continue

            if reason:
                suppression_reasons[f"{finding.rule_id}_{finding.start_index}"] = reason

            suppressed.append(suppressed_finding)

        return suppressed, suppression_reasons

    def _build_rules(self) -> List[Rule]:
        return [
            # ---------------- HIGH ----------------
            Rule(
                rule_id="H_INDEM_01",
                rule_name="unlimited_indemnification",
                title="Potentially unlimited indemnification",
                severity=Severity.HIGH,
                rationale="Indemnity obligations may be uncapped, which can expose you to costs far beyond the contract value.",
                anchors=[r"\bindemnif\w+\b", r"\bhold\s+harmless\b"],
                nearby=[
                    r"\bno\s+limit\b",
                    r"\bwithout\s+limit\b",
                    r"\bunlimited\b",
                    r"\bnotwithstanding\b.*\blimitation\s+of\s+liability\b",
                    r"\bnot\s+be\s+limited\b",
                ],
                window=300,  # Reduced from 400 to avoid false positives in separate sentences
                aliases=["uncapped_indemnification", "unlimited_indemnity", "no_limit_indemnification"],
            ),
            Rule(
                rule_id="H_LOL_01",
                rule_name="liability_uncapped_or_weakened",
                title="Liability may be uncapped or cap may be weakened",
                severity=Severity.HIGH,
                rationale="If liability is not capped (or key categories are carved out), downside risk can exceed expected exposure.",
                anchors=[r"\blimitation\s+of\s+liability\b", r"\bliabilit(y|ies)\b"],
                nearby=[
                    r"\bno\s+event\b.*\bshall\b.*\bbe\s+limited\b",
                    r"\bnot\s+be\s+limited\b",
                    r"\bwithout\s+limitation\b",
                    r"\bexclude(s|d)?\b.*\blimitation\b",
                    r"\bcarve[-\s]?out\b.*\blimitation\b",
                ],
                window=450,
            ),
            Rule(
                rule_id="H_IP_01",
                rule_name="broad_ip_assignment",
                title="Broad IP assignment / ownership transfer language",
                severity=Severity.HIGH,
                rationale="Assignment language may transfer ownership of work product or IP rather than granting a limited license.",
                # Bounded to 180 chars between the assignment verb and the
                # "right, title, and interest" phrase so the match stays
                # inside one assignment sentence instead of an unbounded
                # DOTALL scan that can bridge into an unrelated clause
                # elsewhere in the same chunk. The target phrase also allows
                # a possessive filler ("all OF ITS right, title, and
                # interest"), which real assignment sentences use and the
                # original bare "all right(s), title, and interest" pattern
                # missed.
                pattern=r"\b(assigns?|transfer(s|red)?|hereby\s+assigns?)\b.{0,180}?\ball\s+(?:of\s+(?:its|his|her|their)\s+)?right[s]?,\s*title,?\s*and\s+interest\b",
            ),
            Rule(
                rule_id="H_PERSONAL_01",
                rule_name="personal_liability",
                title="Potential personal liability exposure",
                severity=Severity.CRITICAL,
                rationale="Language may create obligations that extend beyond the company (e.g., personal guarantees or individual responsibility).",
                anchors=[r"\bpersonally\b", r"\bguarant(y|ee)\b", r"\bguarantor\b"],
                nearby=[r"\bobligation(s)?\b", r"\bliabilit(y|ies)\b", r"\bresponsible\b"],
                window=350,
            ),
            Rule(
                rule_id="H_INDEM_ONEWAY_01",
                rule_name="one_way_indemnity",
                title="One-way indemnification obligation",
                severity=Severity.HIGH,
                rationale="Indemnification obligations that apply to only one party can create asymmetric risk exposure.",
                anchors=[r"\bindemnif\w+\b"],
                nearby=[
                    r"\breceiving\s+party\b.*\bindemnif",
                    r"\bshall\s+indemnify\b.*\bdisclosing\s+party\b",
                ],
                window=350,
            ),
            Rule(
                rule_id="H_IP_WORK_PRODUCT_01",
                rule_name="ip_assignment_work_product",
                title="IP ownership via work product language",
                severity=Severity.HIGH,
                rationale="Work product ownership language can effectively transfer IP even if assignment wording is indirect.",
                pattern=r"\b(work\s+product|deliverables?)\b.{0,200}?\b(owned\s+by|shall\s+be\s+the\s+property\s+of)\b",
            ),
            Rule(
                rule_id="H_ATTFEE_01",
                rule_name="one_way_attorneys_fees",
                title="One-way attorneys' fees",
                severity=Severity.HIGH,
                rationale="One-sided fee-shifting clauses can dramatically increase downside risk by forcing one party to pay all legal costs regardless of outcome.",
                # Match attorneys' fees - handle apostrophe explicitly
                pattern=r"\battorneys?['']?\s+fees?\b|\battorneys?['']fees?\b|\battorney['']?s\s+fees?\b|\blegal\s+fees?\b",
                aliases=["one_way_attorneys_fees", "unilateral_fee_shifting"],
            ),
            Rule(
                rule_id="H_LOL_CARVEOUT_01",
                rule_name="liability_cap_carveout",
                title="Liability cap carve-outs may negate protection",
                severity=Severity.HIGH,
                rationale="Liability caps that exclude indemnity, confidentiality, or IP claims often negate the practical benefit of the cap entirely.",
                anchors=[r"\blimitation\s+of\s+liability\b", r"\bliability\s+cap\b"],
                nearby=[
                    r"\bexcept\s+for\b.*\b(indemnif\w+|confidential|intellectual\s+property|IP)\b",
                    r"\bexcluding\b.*\b(indemnif\w+|confidential|intellectual\s+property|IP)\b",
                    r"\bshall\s+not\s+apply\s+to\b.*\b(indemnif\w+|confidential|intellectual\s+property|IP)\b",
                    r"\bnot\s+apply\s+to\b.*\b(indemnif\w+|confidential|intellectual\s+property|IP)\b",
                ],
                window=450,
                aliases=["liability_cap_carveout", "cap_exclusion"],
            ),
            Rule(
                rule_id="H_ASSIGN_CHANGE_CTRL_01",
                rule_name="assignment_change_control",
                title="Assignment restricted on change of control",
                severity=Severity.HIGH,
                rationale="Restrictions on assignment during a merger, acquisition, or change of control can block fundraising or exits.",
                anchors=[r"\bmay\s+not\s+assign\b", r"\bassignment\s+prohibited\b", r"\bshall\s+not\s+assign\b"],
                nearby=[
                    r"\bchange\s+of\s+control\b",
                    r"\bmerger\b",
                    r"\bacquisition\b",
                    r"\bsale\s+of\s+assets\b",
                    r"\breorganization\b",
                ],
                window=400,
                aliases=["assignment_change_control", "anti_assignment_mna"],
            ),
            Rule(
                rule_id="H_PUBLICITY_01",
                rule_name="publicity_rights",
                title="Publicity or disclosure rights",
                severity=Severity.HIGH,
                rationale="Publicity clauses may allow one party to disclose the relationship or use branding without consent.",
                anchors=[r"\bpress\s+release\b", r"\bpublic\s+announcement\b", r"\buse\s+of\s+name\b", r"\buse\s+of\s+logo\b"],
                nearby=[
                    r"\bmay\s+disclose\b",
                    r"\bpermitted\s+to\b",
                    r"\bwithout\s+consent\b",
                    r"\bwithout\s+prior\s+written\s+consent\b",
                ],
                window=350,
                aliases=["publicity_rights", "disclosure_of_relationship"],
            ),
            Rule(
                rule_id="H_UNILATERAL_MOD_01",
                rule_name="unilateral_modification",
                title="Unilateral right to modify terms",
                severity=Severity.HIGH,
                rationale="Language allowing one party to modify terms, pricing, or scope without mutual consent can fundamentally alter the deal post-signing.",
                pattern=r"\b(may\s+(modify|amend|change|update|revise)\b.{0,150}?\b(at\s+any\s+time|in\s+its?\s+(sole\s+)?discretion|without\s+(prior\s+)?(written\s+)?consent|without\s+notice|unilateral))|(\breserves?\s+the\s+right\s+to\s+(modify|amend|change|update|revise)\b)",
                aliases=["unilateral_amendment", "right_to_modify", "change_terms_unilaterally"],
            ),
            Rule(
                rule_id="H_CONSEQUENTIAL_01",
                rule_name="consequential_damages_waiver",
                title="One-sided consequential damages waiver",
                severity=Severity.HIGH,
                rationale="Waiver of indirect, consequential, or special damages that applies to only one party removes a critical remedy for the other side.",
                anchors=[r"\b(consequential|indirect|special|incidental|punitive)\s+damages?\b"],
                nearby=[
                    r"\bin\s+no\s+event\b.*\bliable\b",
                    r"\bshall\s+not\s+be\s+liable\b",
                    r"\bno\s+liability\b",
                    r"\bunder\s+no\s+circumstances\b",
                    r"\bwaive[sd]?\b",
                    r"\bexclude[sd]?\b",
                    r"\bnot\s+be\s+responsible\b",
                ],
                window=400,
                aliases=["consequential_damages_exclusion", "indirect_damages_waiver"],
            ),
            Rule(
                rule_id="H_TERM_CONVENIENCE_01",
                rule_name="one_sided_termination_convenience",
                title="One-sided termination for convenience",
                severity=Severity.HIGH,
                rationale="Termination for convenience rights that apply to only one party allow that party to exit the deal at will while the other remains bound.",
                # The old anchors were themselves unbounded two-part DOTALL
                # patterns (e.g. "\bterminate\b.*\bany\s+reason\b"), so the
                # "anchor" alone could already span from one numbered
                # sub-clause to a completely different one before the
                # nearby/window search even started (verified: it bridged a
                # MUTUAL termination-for-breach clause to an unrelated
                # sub-clause 640+ characters away, misreading a fully
                # mutual clause as if it were part of the one-sided match).
                # Anchors require "may terminate" (an entitlement to end
                # the agreement), not bare "terminate" — the latter also
                # matches unrelated later references like "...notice(s) to
                # terminate work on the SOW" (an ancillary consequence of
                # exercising the right, not a second termination right),
                # which produced a spurious duplicate finding (verified).
                # The actual convenience-termination signal is required via
                # `nearby` within a tight window, so a match stays inside
                # one sub-clause.
                anchors=[r"\bmay\s+terminate\b"],
                nearby=[
                    r"\bfor\s+convenience\b",
                    r"\bwithout\s+cause\b",
                    r"\bfor\s+any\s+reason\b",
                    r"\bfor\s+no\s+reason\b",
                    r"\bsole\s+discretion\b",
                    r"\bat\s+any\s+time\b",
                    r"\bupon\s+\d+\s+days?\b",
                    r"\bwritten\s+notice\b",
                ],
                window=200,
                aliases=["termination_for_convenience", "unilateral_termination"],
            ),
            Rule(
                rule_id="H_DATA_TERMINATION_01",
                rule_name="no_data_portability",
                title="No data return or deletion on termination",
                severity=Severity.HIGH,
                rationale="Absence of data return, export, or deletion obligations on termination can leave your data locked in a vendor's system with no recourse.",
                anchors=[r"\btermination\b", r"\bexpiration\b"],
                nearby=[
                    r"\bdata\b.*\b(retain|retained|retention)\b",
                    r"\bno\s+obligation\b.*\b(return|delete|destroy)\b",
                    r"\bshall\s+have\s+no\s+(duty|obligation)\b.*\bdata\b",
                    r"\bdata\b.*\b(destroyed|deleted)\b.*\b(not|no)\b",
                ],
                window=450,
                aliases=["no_data_return", "data_lock_in", "no_data_deletion"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(terminat\w+|expir\w+)\b", r"\bdata\b"],
                protective_patterns=[
                    r"\b(return\w*|export\w*|delet\w+|destroy\w+)\b[^.]{0,80}\bdata\b",
                    r"\bdata\b[^.]{0,80}\b(return\w*|export\w*|delet\w+|destroy\w+)\b",
                ],
            ),
            Rule(
                rule_id="H_ASYMMETRIC_LIABILITY_01",
                rule_name="asymmetric_liability_cap",
                title="Asymmetric liability cap",
                severity=Severity.CRITICAL,
                rationale="A liability cap that applies to one party but not the other creates an imbalanced risk allocation that can leave you exposed.",
                # Anchors only recognize generic role words (vendor/
                # provider/supplier/licensor) — a cap stated using the
                # contract's own defined party name (e.g. "PREVAIL'S
                # MAXIMUM LIABILITY...") never matches these at all
                # (verified: this rule did not fire on a real contract
                # whose liability cap names only the vendor by its defined
                # term, missing the single largest financial-exposure term
                # in the document). See RuleEngine._check_liability_cap_asymmetry
                # for the party-name-aware document-level check that covers
                # that case using party_resolver.py; these anchors remain
                # as the generic-word fallback for contracts that use
                # role words directly instead of defined names.
                anchors=[r"\b(vendor|provider|supplier|licensor)\b.{0,120}\bliabilit(y|ies)\b", r"\bliabilit(y|ies)\b.{0,120}\b(vendor|provider|supplier|licensor)\b"],
                nearby=[
                    r"\bshall\s+not\s+exceed\b",
                    r"\blimited\s+to\b",
                    r"\baggregate\s+liabilit(y|ies)\b",
                    r"\bmaximum\s+liabilit(y|ies)\b",
                ],
                window=400,
                aliases=["one_sided_liability_cap", "vendor_liability_cap"],
            ),
            Rule(
                rule_id="H_LOL_NO_CARVEOUT_01",
                rule_name="liability_cap_missing_carveouts",
                title="Liability cap lacks carve-outs for high-severity claims",
                severity=Severity.CRITICAL,
                rationale=(
                    "A liability cap with no stated exceptions can limit recovery even for indemnification, "
                    "confidentiality breaches, data-security incidents, gross negligence, willful misconduct, "
                    "or fraud — categories conventionally carved out of a liability cap. A cap this broad can "
                    "mean catastrophic harm is still bounded at ordinary contract-value damages."
                ),
                # No standalone adverse phrase is meaningful here (a
                # contract never explicitly states "this cap has no
                # carve-outs") — this rule is designed to fire through the
                # REQUIRED_SECTION absence path below. The anchors/nearby
                # here only catch the rare explicit case.
                anchors=[r"\bmaximum\s+liabilit(?:y|ies)\b", r"\baggregate\s+liabilit(?:y|ies)\b"],
                nearby=[r"\bwithout\s+(?:any\s+)?(?:exception|limitation|carve[-\s]?out)\b"],
                window=200,
                aliases=["liability_cap_no_exceptions", "cap_missing_carveouts", "uncarved_liability_cap"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[
                    r"\b(?:maximum\s+liabilit(?:y|ies)|aggregate\s+liabilit(?:y|ies)\s+(?:shall\s+not\s+exceed|of)|"
                    r"liabilit(?:y|ies)\s+shall\s+(?:in\s+no\s+event\s+)?(?:not\s+)?exceed)\b",
                ],
                protective_patterns=[
                    r"\b(except(?:ion)?s?\s+for|excluding|shall\s+not\s+apply\s+to|does\s+not\s+apply\s+to|other\s+than)\b"
                    r"(?:[^.]|\.(?=\d)){0,200}"
                    r"\b(indemnif\w+|confidential\w*|gross\s+negligence|willful\s+misconduct|wilful\s+misconduct|"
                    r"fraud|data\s+breach|security\s+incident|intellectual\s+property)\b",
                ],
            ),
            Rule(
                rule_id="H_INDEM_SCOPE_NARROW_01",
                rule_name="narrow_indemnification_scope",
                title="Indemnification scope may be too narrow",
                severity=Severity.HIGH,
                rationale=(
                    "An indemnification obligation limited to a short enumerated list of triggers (e.g. IP "
                    "infringement, unauthorized data use) leaves other major risk categories — data breach, "
                    "negligence, confidentiality breach, security incidents, regulatory violations — without "
                    "indemnification coverage, even though those are often the more likely real-world failure modes."
                ),
                anchors=[r"\bindemnif\w+\b", r"\bhold\s+harmless\b"],
                nearby=[r"\bonly\b", r"\bsolely\b", r"\blimited\s+to\b"],
                window=250,
                aliases=["narrow_indemnity", "limited_indemnification_scope"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bindemnif\w+\b"],
                protective_patterns=[
                    r"\bindemnif\w+\b(?:[^.]|\.(?=\d)){0,250}\b(?:negligence|data\s+breach|security\s+incident|"
                    r"confidential\w*\s+(?:breach|information)|regulatory\s+violation|breach\s+of\s+(?:this\s+)?"
                    r"Agreement)\b",
                ],
            ),
            Rule(
                rule_id="M_DPA_MISSING_01",
                rule_name="dpa_execution_missing",
                title="No Data Processing Agreement (DPA) execution requirement",
                severity=Severity.MEDIUM,
                rationale=(
                    "Referring to GDPR concepts (e.g. Data Controller/Data Processor roles) without requiring "
                    "execution of a formal Data Processing Agreement leaves subprocessor authorization, audit "
                    "rights, and breach-assistance obligations unenforceable as distinct contractual commitments."
                ),
                anchors=[r"\bData\s+(?:Controller|Processor)\b", r"\bGDPR\b"],
                nearby=[r"\bno\s+(?:separate\s+)?(?:DPA|data\s+processing\s+agreement)\s+(?:is\s+)?required\b"],
                window=250,
                aliases=["missing_dpa", "no_data_processing_agreement"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(?:Data\s+(?:Controller|Processor)|GDPR|personal\s+data)\b"],
                protective_patterns=[r"\b(?:DPA|Data\s+Processing\s+Agreement)\b"],
            ),
            Rule(
                rule_id="M_BAA_MISSING_01",
                rule_name="baa_execution_missing",
                title="No Business Associate Agreement (BAA) execution requirement",
                severity=Severity.MEDIUM,
                rationale=(
                    "A general HIPAA-compliance representation is not the same as a Business Associate "
                    "Agreement — without a BAA, HIPAA's specific breach-notification, safeguard, and "
                    "subcontractor flow-down obligations for protected health information are not established."
                ),
                anchors=[r"\bHIPAA\b", r"\bprotected\s+health\s+information\b"],
                nearby=[r"\bno\s+(?:separate\s+)?(?:BAA|business\s+associate\s+agreement)\s+(?:is\s+)?required\b"],
                window=250,
                aliases=["missing_baa", "no_business_associate_agreement"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(?:HIPAA|protected\s+health\s+information|PHI)\b"],
                protective_patterns=[r"\b(?:BAA|Business\s+Associate\s+Agreement)\b"],
            ),
            Rule(
                rule_id="M_SUBPROCESSOR_MISSING_01",
                rule_name="subprocessor_terms_missing",
                title="No subprocessor authorization or flow-down terms",
                severity=Severity.MEDIUM,
                rationale=(
                    "A vendor processing personal data without any subprocessor terms (authorization, "
                    "notice of changes, flow-down of equivalent data-protection obligations) means you have "
                    "no visibility or contractual control over who else may handle your data."
                ),
                anchors=[r"\bsub[-\s]?processor\w*\b", r"\bsub[-\s]?contractor\w*\b"],
                nearby=[r"\bwithout\s+(?:any\s+)?(?:notice|authorization|consent)\b"],
                window=250,
                aliases=["missing_subprocessor_terms", "no_subprocessor_flowdown"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(?:Data\s+Processor|personal\s+data|GDPR)\b"],
                protective_patterns=[r"\bsub[-\s]?processor\w*\b"],
            ),
            Rule(
                rule_id="M_AUDIT_RIGHTS_CUSTOMER_01",
                rule_name="customer_audit_rights_missing",
                title="No customer audit or inspection rights over vendor security practices",
                severity=Severity.MEDIUM,
                rationale=(
                    "A vendor holding your data with no customer-side audit, inspection, or compliance-"
                    "verification right means you have no contractual mechanism to confirm the security "
                    "measures, certifications, or subprocessor practices the vendor represents are actually followed."
                ),
                anchors=[r"\bsecurity\s+measures?\b", r"\bData\s+Processor\b"],
                nearby=[r"\bno\s+right\s+to\s+audit\b", r"\baudit\s+rights?\s+(?:are\s+)?(?:waived|excluded)\b"],
                window=250,
                aliases=["missing_customer_audit_rights", "no_audit_or_inspection_right"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(?:security\s+measures?|Data\s+Processor|personal\s+data)\b"],
                protective_patterns=[r"\b(?:audit|inspect\w*)\b"],
            ),
            Rule(
                rule_id="M_DELETION_CERT_MISSING_01",
                rule_name="deletion_certification_missing",
                title="No deletion certification on termination",
                severity=Severity.MEDIUM,
                rationale=(
                    "Data return/deletion language without a certification requirement (a written confirmation "
                    "that deletion actually occurred, e.g. a certificate of destruction) leaves no auditable "
                    "proof that your data was actually removed from the vendor's systems and backups."
                ),
                anchors=[r"\b(?:return|delet\w*|dispos\w*|destroy\w*)\b"],
                nearby=[r"\bwithout\s+(?:any\s+)?(?:certification|confirmation)\b"],
                window=250,
                aliases=["missing_deletion_certification", "no_certificate_of_destruction"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\btermin\w*\b", r"\b(?:return|delet\w*|dispos\w*|destroy\w*)\b.{0,60}\bdata\b"],
                protective_patterns=[
                    r"\bcertif\w*\b(?:[^.]|\.(?=\d)){0,120}\b(?:deletion|destruction|dispos\w*)\b",
                    r"\bcertificate\s+of\s+destruction\b",
                    r"\bconfirm\w*\s+in\s+writing\b(?:[^.]|\.(?=\d)){0,120}\b(?:delet\w*|destroy\w*)\b",
                ],
            ),
            Rule(
                rule_id="M_SLA_REMEDY_EXCLUSIVITY_01",
                rule_name="sla_remedy_exclusivity_undefined",
                title="SLA service credits: exclusive-remedy and chronic-failure terms undefined",
                severity=Severity.MEDIUM,
                rationale=(
                    "A service-level clause with credits but no statement of whether credits are your SOLE "
                    "remedy (versus one of several available remedies), and no right to terminate for repeated/"
                    "chronic SLA failures, can leave you locked into a chronically underperforming service with "
                    "only small, capped credits and no exit right."
                ),
                anchors=[r"\bservice\s+credit\b"],
                nearby=[r"\bsole\s+and\s+exclusive\s+remedy\b"],
                window=250,
                aliases=["sla_exclusive_remedy_undefined", "no_chronic_failure_termination"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bservice\s+credit\b"],
                protective_patterns=[
                    r"\b(?:sole|exclusive)\s+remedy\b",
                    r"\brepeated\s+failure\b|\bchronic\b|\bconsecutive\s+months?\b",
                ],
            ),
            Rule(
                rule_id="M_INSURANCE_MINIMUM_MISSING_01",
                rule_name="insurance_minimum_missing",
                title="Insurance obligation lacks minimum coverage amounts",
                severity=Severity.MEDIUM,
                rationale=(
                    "An insurance obligation with no stated minimum coverage amount (e.g. '$1,000,000 per "
                    "occurrence') is effectively unenforceable as a financial backstop — 'adequate' or "
                    "'commercially reasonable' insurance could mean any amount, including none that would "
                    "actually cover a material claim."
                ),
                anchors=[r"\binsurance\b"],
                nearby=[r"\bno\s+(?:minimum|specific)\s+(?:coverage\s+)?amount\b"],
                window=200,
                aliases=["no_insurance_minimum", "vague_insurance_amount"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\binsurance\b"],
                protective_patterns=[
                    r"\binsurance\b(?:[^.]|\.(?=\d)){0,150}\$\s?[\d,]+",
                    r"\$\s?[\d,]+(?:[^.]|\.(?=\d)){0,150}\binsurance\b",
                ],
            ),
            Rule(
                rule_id="M_REG_RESPONSIBILITY_UNALLOCATED_01",
                rule_name="regulatory_responsibility_conditional",
                title="Regulatory responsibility allocation depends on an unattached SOW",
                severity=Severity.MEDIUM,
                rationale=(
                    "Regulatory obligations that remain with you except to the extent 'expressly transferred' "
                    "under a Statement of Work mean that, until that SOW is executed and actually names what "
                    "transfers, you retain ALL regulatory responsibility by default — even for functions the "
                    "vendor is operationally performing."
                ),
                anchors=[r"\bregulatory\s+obligations?\b"],
                nearby=[
                    r"\bnot\s+(?:specifically\s+)?(?:and\s+)?expressly\s+transferred\b",
                    r"\bremain\w*\s+responsible\b",
                ],
                window=200,
                aliases=["conditional_regulatory_allocation", "regulatory_responsibility_default_to_customer"],
            ),
            Rule(
                rule_id="M_DATA_RETURN_CONDITIONAL_01",
                rule_name="data_return_conditional_on_customer_instruction",
                title="Data return/deletion depends on customer-initiated instructions, no default",
                severity=Severity.MEDIUM,
                rationale=(
                    "Data return or deletion that only happens after you proactively send written instructions "
                    "within a deadline — with no stated default if you don't — risks the vendor retaining your "
                    "data indefinitely by inaction, and can shift the cost of disposal to you."
                ),
                anchors=[r"\b(?:return|dispos\w*)\b.{0,120}\b(?:Company|Customer)\s+Data\b"],
                nearby=[r"\bwritten\s+instructions?\b"],
                window=200,
                aliases=["conditional_data_return", "no_default_data_disposition"],
            ),
            # ---------------- HIGH (v3.0 broader-audience additions) ----------------
            Rule(
                rule_id="H_CARD_AUTH_01",
                rule_name="stored_payment_card_broad_charges",
                title="Broad stored-card or automatic charge authorization",
                severity=Severity.HIGH,
                rationale="Broad permission to store a payment method and charge future fees can surprise individuals, freelancers, and small businesses with unexpected costs.",
                anchors=[r"\b(charge|debit|bill)\w*\b", r"\bpayment\s+method\b", r"\bcredit\s+card\b", r"\bcard\s+on\s+file\b"],
                nearby=[
                    r"\bautomatically\b",
                    r"\brecurring\b",
                    r"\bfrom\s+time\s+to\s+time\b",
                    r"\bwithout\s+(?:further\s+)?(?:notice|authorization|approval)\b",
                    r"\bauthori[sz]e\w*\b.*\bfuture\s+charges\b",
                ],
                window=400,
                aliases=["automatic_charges", "stored_card_authorization", "recurring_billing"],
            ),
            Rule(
                rule_id="H_CONTENT_LICENSE_01",
                rule_name="perpetual_content_license",
                title="Perpetual license to use your content",
                severity=Severity.HIGH,
                rationale="A perpetual, worldwide, sublicensable license to user content can allow long-term use of creative work, likeness, reviews, photos, or uploads beyond the original purpose.",
                anchors=[r"\b(content|user\s+content|submission|photo|image|review|feedback|likeness)\b"],
                nearby=[
                    r"\bperpetual\b",
                    r"\birrevocable\b",
                    r"\bworldwide\b",
                    r"\bsublicensable\b",
                    r"\broyalty[-\s]?free\b",
                ],
                window=500,
                aliases=["user_content_license", "ugc_license", "likeness_license"],
            ),
            Rule(
                rule_id="H_WAGE_DEDUCTION_01",
                rule_name="wage_or_payment_deduction",
                title="Unilateral wage, payout, or invoice deductions",
                severity=Severity.HIGH,
                rationale="Terms allowing unilateral deductions, chargebacks, offsets, or withheld payouts can materially affect workers, creators, contractors, and small vendors.",
                anchors=[r"\b(deduct|deduction|offset|set[-\s]?off|withhold|chargeback)\w*\b"],
                nearby=[
                    r"\bwages?\b",
                    r"\bpay(?:ment|out)?s?\b",
                    r"\bcompensation\b",
                    r"\binvoice\w*\b",
                    r"\bearnings?\b",
                ],
                window=400,
                aliases=["payment_deductions", "chargebacks", "withheld_payouts"],
            ),
            Rule(
                rule_id="H_CLASSIFICATION_01",
                rule_name="worker_classification_shift",
                title="Worker classification risk shifted to individual",
                severity=Severity.HIGH,
                rationale="Clauses that label a worker as an independent contractor while shifting tax, benefit, and classification responsibility to the individual can create significant employment and tax exposure.",
                anchors=[r"\bindependent\s+contractor\b", r"\bnot\s+an\s+employee\b"],
                nearby=[
                    r"\bresponsible\s+for\s+(?:all\s+)?tax",
                    r"\bno\s+benefits\b",
                    r"\bwithholding\b",
                    r"\bclassification\b",
                    r"\bindemnif\w+\b.*\b(employee|employment|tax)\b",
                ],
                window=500,
                aliases=["independent_contractor_classification", "misclassification", "tax_withholding_shift"],
            ),

            # ---------------- MEDIUM (v3.0 broader-audience additions) ----------------
            Rule(
                rule_id="M_REFUND_01",
                rule_name="no_refunds_or_all_sales_final",
                title="No refund or all-sales-final policy",
                severity=Severity.MEDIUM,
                rationale="Strict no-refund language can leave consumers and small buyers without a practical remedy if a product, service, event, or subscription does not meet expectations.",
                pattern=r"\b(no\s+refunds?|non[-\s]?refundable|all\s+sales\s+final|refunds?\s+will\s+not\s+be\s+provided)\b",
                aliases=["no_refunds", "all_sales_final", "non_refundable"],
            ),
            Rule(
                rule_id="M_CANCEL_FEE_01",
                rule_name="cancellation_fees_or_notice",
                title="Cancellation fee or strict cancellation window",
                severity=Severity.MEDIUM,
                rationale="Cancellation fees and short notice windows can create avoidable costs for consumers, freelancers, and small teams if plans change.",
                anchors=[r"\bcancell?ation\b", r"\bcancel\w*\b"],
                nearby=[
                    r"\bfee\b",
                    r"\bpenalt(y|ies)\b",
                    r"\bnon[-\s]?refundable\b",
                    r"\b(?:24|48|72)\s+hours?\b",
                    r"\b(?:7|14|30)\s+days?\b",
                ],
                window=350,
                aliases=["cancellation_fee", "strict_cancellation_window"],
            ),
            Rule(
                rule_id="M_ACCOUNT_SUSPEND_01",
                rule_name="unilateral_account_suspension",
                title="Account suspension or access loss at sole discretion",
                severity=Severity.MEDIUM,
                rationale="A broad right to suspend accounts, services, or access at sole discretion can interrupt work, payments, communications, or access to purchased services.",
                # "terminate" and bare "access" were removed from the anchor
                # list: they made this rule indistinguishable from ordinary
                # contract termination language (verified: it fired on
                # "Company may terminate this Agreement ... at any time
                # ... for any reason", a termination-for-convenience clause,
                # with no suspension of any kind involved). Suspension and
                # termination are different legal concepts — termination
                # ends the agreement; suspension interrupts access while the
                # agreement continues — and only the former belongs in a
                # rule titled "account suspension."
                anchors=[r"\bsuspend\w*\b", r"\bdisable\w*\b", r"\bdeactivat\w*\b", r"\block(?:s|ed|ing)?\s+(?:out|access)\b"],
                nearby=[
                    r"\baccount\b",
                    r"\bservice\b",
                    r"\bsole\s+discretion\b",
                    r"\bwithout\s+notice\b",
                    r"\bfor\s+any\s+reason\b",
                ],
                window=400,
                aliases=["account_suspension", "access_termination", "sole_discretion_suspension"],
            ),
            Rule(
                rule_id="M_PRIVACY_SHARING_01",
                rule_name="broad_personal_information_sharing",
                title="Broad sharing or sale of personal information",
                severity=Severity.MEDIUM,
                rationale="Broad rights to sell, share, rent, or disclose personal information can affect privacy expectations for consumers, employees, applicants, and customers.",
                anchors=[r"\bpersonal\s+(?:information|data)\b", r"\bPII\b"],
                nearby=[
                    r"\bsell\w*\b",
                    r"\bshare\w*\b",
                    r"\brent\w*\b",
                    r"\bdisclose\w*\b",
                    r"\bmarketing\s+partners?\b",
                    r"\bthird\s+part(?:y|ies)\b",
                ],
                window=450,
                aliases=["personal_info_sharing", "data_sale", "third_party_marketing"],
            ),
            Rule(
                rule_id="M_NONDISPARAGE_01",
                rule_name="non_disparagement",
                title="Non-disparagement or review restriction",
                severity=Severity.MEDIUM,
                rationale="Non-disparagement and review restrictions can limit honest feedback, public reviews, or discussion of workplace and service experiences.",
                pattern=r"\bnon[-\s]?disparagement\b|\bshall\s+not\s+disparage\b|\bmay\s+not\s+(?:post|publish|leave)\b.{0,80}\b(review|rating|comment)\b|\bnegative\s+(?:review|rating|comment)\b",
                aliases=["review_restriction", "non_disparagement", "gag_clause"],
            ),
            Rule(
                rule_id="M_PHOTO_RELEASE_01",
                rule_name="photo_video_likeness_release",
                title="Photo, video, voice, or likeness release",
                severity=Severity.MEDIUM,
                rationale="Media releases can permit use of a person's image, voice, name, or likeness in marketing or promotional materials beyond the immediate event or service.",
                anchors=[r"\b(photo|video|image|voice|name|likeness|recording)\b"],
                nearby=[
                    r"\brelease\b",
                    r"\bconsent\b",
                    r"\bmarketing\b",
                    r"\bpromotional\b",
                    r"\badvertising\b",
                    r"\bpublicity\b",
                ],
                window=400,
                aliases=["media_release", "likeness_release", "photo_release"],
            ),

            # ---------------- LOW (v3.0 broader-audience additions) ----------------
            Rule(
                rule_id="L_ELECTRONIC_NOTICE_01",
                rule_name="electronic_notice_deemed_received",
                title="Electronic notice deemed received",
                severity=Severity.LOW,
                rationale="Email, portal, or in-app notices deemed received immediately can cause missed deadlines if the address changes or messages are filtered.",
                anchors=[r"\bnotice\b", r"\bemail\b", r"\belectronic\b", r"\bin[-\s]?app\b", r"\bportal\b"],
                nearby=[
                    r"\bdeemed\s+(?:received|given|delivered)\b",
                    r"\bupon\s+sending\b",
                    r"\bwhen\s+sent\b",
                ],
                window=350,
                aliases=["electronic_notice", "notice_deemed_received"],
            ),
            Rule(
                rule_id="L_COMMUNICATION_CONSENT_01",
                rule_name="marketing_communications_consent",
                title="Marketing or SMS communication consent",
                severity=Severity.LOW,
                rationale="Consent to calls, texts, emails, or automated messages can create unwanted communications unless opt-out rights are clear.",
                anchors=[r"\b(text|SMS|call|email|message|autodial|automated)\w*\b"],
                nearby=[
                    r"\bmarketing\b",
                    r"\bpromotional\b",
                    r"\bconsent\b",
                    r"\bopt[-\s]?out\b",
                    r"\btelephone\s+consumer\s+protection\s+act\b",
                    r"\bTCPA\b",
                ],
                window=350,
                aliases=["sms_consent", "marketing_emails", "automated_calls"],
            ),

            # ---------------- MEDIUM ----------------
            Rule(
                rule_id="M_CONF_01",
                rule_name="indefinite_confidentiality",
                title="Confidentiality may be perpetual / indefinite",
                severity=Severity.MEDIUM,
                rationale="Indefinite confidentiality can create long-term compliance burden and uncertainty around retention and disclosure.",
                pattern=r"\b(confidential(ity|ly)?|non[-\s]?disclosure)\b.{0,350}?\b(perpetual|in\s+perpetuity|indefinite(ly)?|no\s+expiration)\b",
                aliases=["perpetual_confidentiality", "indefinite_confidentiality", "no_expiration_confidentiality"],
            ),
            Rule(
                rule_id="M_RENEW_01",
                rule_name="auto_renewal",
                title="Auto-renewal may lock you in",
                severity=Severity.MEDIUM,
                rationale="Auto-renewal terms may require notice within a specific window to avoid renewal.",
                anchors=[r"\bauto[-\s]?renew(al)?\b", r"\bautomatically\s+renew(s|ed)?\b"],
                nearby=[
                    r"\bunless\b.*\bnotice\b",
                    r"\bprior\s+written\s+notice\b",
                    r"\bnot\s+to\s+renew\b",
                    r"\bunless\s+terminated\b",  # Added to catch "automatically renews...unless terminated"
                ],
                window=400,
            ),
            Rule(
                rule_id="M_NONCOMP_01",
                rule_name="non_compete_non_solicit",
                title="Non-compete / non-solicit style restriction",
                severity=Severity.MEDIUM,
                rationale="Restrictive covenants can limit future business activity; enforceability varies and is commonly negotiated.",
                pattern=r"\bnon[-\s]?compete\b|\bnon[-\s]?solicit\b|\brestrict(ion|ive)\b.{0,150}\bcompeti(t|tion|tor)\b",
            ),
            Rule(
                rule_id="M_DEV_RESTRICT_01",
                rule_name="dev_restriction_confidential",
                title="Development restriction tied to confidential information",
                severity=Severity.MEDIUM,
                rationale="Restrictions on developing competing or similar products, even when tied to confidential information, can limit future work and are commonly negotiated.",
                pattern=r"(not\s+to\s+develop|shall\s+not\s+develop|may\s+not\s+develop).{0,120}?(compete|substantially\s+similar).{0,120}?(based\s+on|derived\s+from)",
                aliases=["development_restrictions", "product_development_restrictions", "competing_product_restrictions"],
            ),
            Rule(
                rule_id="M_CONF_SCOPE_01",
                rule_name="confidentiality_scope_overbroad",
                title="Confidentiality scope may be overbroad",
                severity=Severity.MEDIUM,
                rationale="Confidentiality obligations that lack standard carve-outs may apply too broadly.",
                anchors=[r"\bconfidential\b"],
                nearby=[
                    r"\bwithout\s+regard\s+to\b",
                    r"\bregardless\s+of\b",
                    r"\bpublic\b.*\bexcluded\b",
                ],
                window=350,
            ),
            Rule(
                rule_id="M_RESIDUALS_01",
                rule_name="no_residuals_clause",
                title="No residuals / knowledge carve-out",
                severity=Severity.MEDIUM,
                rationale="Absence of a residuals clause can restrict use of general knowledge gained during discussions.",
                pattern=r"\bshall\s+not\s+use\b.{0,100}?\bknowledge\b.{0,100}?\bretained\b",
                rule_class=RuleClass.REQUIRED_SECTION,
                # "\bconfidential\w*\b" alone matches a bare cover-page/
                # header banner like "Confidential – Fully Executed" (no
                # actual confidentiality clause involved), which the
                # absence-check then anchored the finding to — a real,
                # correct "no residuals language" result pointing at an
                # embarrassingly wrong location (verified). "confidential
                # information" specifically targets the defined term used
                # throughout an actual confidentiality clause.
                topic_patterns=[r"\bconfidential\s+information\b"],
                protective_patterns=[
                    r"\bresiduals?\b",
                    r"\bunaided\s+memory\b",
                    r"\bgeneral\s+knowledge\b[^.]{0,80}\bretain\w*\b",
                ],
            ),
            Rule(
                rule_id="M_INJUNCT_01",
                rule_name="injunctive_relief",
                title="Broad injunctive relief language",
                severity=Severity.MEDIUM,
                rationale="Broad injunctive relief provisions can bypass standard dispute resolution safeguards.",
                pattern=r"\binjunctive\s+relief\b|\bequitable\s+relief\b",
            ),
            Rule(
                rule_id="M_EQUIT_NOBOND_01",
                rule_name="equitable_relief_without_bond",
                title="Equitable relief without bond requirement",
                severity=Severity.MEDIUM,
                rationale="Equitable relief (injunctions, specific performance) without a bond requirement can expose you to immediate enforcement without financial safeguards typically required by courts.",
                anchors=[
                    r"\binjunctive\s+relief\b",
                    r"\bequitable\s+relief\b",
                    r"\bspecific\s+performance\b",
                ],
                nearby=[
                    r"\bwithout\s+(?:the\s+)?(?:requirement\s+of\s+)?posting\s+(?:a\s+)?bond\b",
                    r"\bwithout\s+(?:a\s+)?bond\b",
                    r"\bno\s+bond\s+shall\s+be\s+required\b",
                    r"\bno\s+bond\s+is\s+required\b",
                    r"\bnot\s+required\s+to\s+post\s+(?:a\s+)?bond\b",
                    r"\bwithout\s+posting\s+(?:a\s+)?bond\s+(?:or\s+other\s+security)?\b",
                ],
                window=400,
                aliases=["no_bond_injunction", "injunctive_relief_no_bond", "equitable_relief_no_bond", "no_bond_requirement"],
            ),
            Rule(
                rule_id="M_AUDIT_01",
                rule_name="audit_rights",
                title="Audit or inspection rights",
                severity=Severity.MEDIUM,
                rationale="Audit rights can impose operational burden and expose sensitive internal systems.",
                anchors=[r"\baudit\b", r"\binspect\b", r"\bexamine\s+records\b"],
                nearby=[
                    r"\bupon\s+notice\b",
                    r"\bduring\s+normal\s+business\s+hours\b",
                    r"\bwith\s+reasonable\s+notice\b",
                    r"\brecords?\b",  # Added to catch "inspect records" even without explicit notice
                ],
                window=350,
                aliases=["audit_rights", "inspection_rights"],
            ),
            Rule(
                rule_id="M_TERM_NOTICE_01",
                rule_name="termination_notice_window",
                title="Short termination or notice windows",
                severity=Severity.MEDIUM,
                rationale="Short or strict notice windows can lead to accidental renewals or unintended termination.",
                # The old nearby list treated 20 AND 30 days as "short" —
                # 30 days is a standard, market-typical cure/notice period
                # (verified: it fired on this exact language in a real
                # contract's mutual 30-day breach-cure clause and separate
                # 30-day convenience-termination notice, mislabeling both
                # as "short" — neither is). Only genuinely short windows
                # (under 15 days) or an outright absence of notice now
                # qualify. Window also tightened so a match can't drift
                # into an adjacent, unrelated sub-clause.
                anchors=[r"\bterminate\b", r"\bnotice\b"],
                nearby=[
                    r"\b(?:[1-9]|1[0-4])\s+days?\b",
                    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen)\s+days?\b",
                    r"\bless\s+than\s+(?:1[0-4]|[1-9])\s+days?\b",
                    r"\bwithout\s+(?:any\s+)?(?:prior\s+)?notice\b",
                    r"\beffective\s+immediately\b",
                    r"\bimmediately\s+without\s+notice\b",
                ],
                window=200,
                aliases=["termination_notice_window", "short_notice_period"],
            ),
            Rule(
                rule_id="M_SURVIVAL_SCOPE_01",
                rule_name="survival_clause_scope",
                title="Overbroad survival of obligations",
                severity=Severity.MEDIUM,
                rationale="Survival clauses that extend many obligations beyond termination can create indefinite exposure.",
                anchors=[r"\bshall\s+survive\s+termination\b", r"\bsurvive\s+the\s+termination\b"],
                nearby=[
                    r"\bincluding\s+but\s+not\s+limited\s+to\b",
                    r"\bsections?\s+\d+\s+and\s+\d+\b",
                    r"\ball\s+obligations?\b",
                ],
                window=400,
                aliases=["survival_clause_scope", "post_termination_obligations"],
            ),
            Rule(
                rule_id="M_WAIVER_DEFENSE_01",
                rule_name="waiver_of_defenses",
                title="Waiver of defenses or rights",
                severity=Severity.MEDIUM,
                rationale="Clauses waiving defenses can remove legal safeguards and shift risk unexpectedly.",
                anchors=[r"\bwaives?\s+any\s+defenses?\b", r"\birrevocably\s+waives?\b"],
                nearby=[
                    r"\bregardless\s+of\s+fault\b",
                    r"\bwithout\s+limitation\b",
                    r"\ball\s+defenses?\b",
                ],
                window=350,
                aliases=["waiver_of_defenses", "rights_waiver"],
            ),
            Rule(
                rule_id="M_ARBITRATION_01",
                rule_name="mandatory_arbitration",
                title="Mandatory arbitration or class action waiver",
                severity=Severity.MEDIUM,
                rationale="Mandatory arbitration clauses remove access to courts, and class action waivers eliminate collective remedies. Both can significantly limit your enforcement options.",
                pattern=r"\b(mandatory\s+arbitration|binding\s+arbitration|shall\s+be\s+(settled|resolved)\s+by\s+arbitration)\b|\b(waive[sd]?\s+(?:any\s+)?(?:right\s+to\s+)?(?:a\s+)?(?:class\s+action|jury\s+trial))\b",
                aliases=["binding_arbitration", "class_action_waiver", "jury_trial_waiver"],
            ),
            Rule(
                rule_id="M_WARRANTY_DISCLAIM_01",
                rule_name="warranty_disclaimer",
                title="Blanket warranty disclaimer",
                severity=Severity.MEDIUM,
                rationale="Broad warranty disclaimers ('AS IS', no implied warranties) shift all quality and fitness risk to the buyer with no recourse for defects.",
                pattern=r"\b(as[\s-]is|as[\s-]available)\b.{0,150}?\b(warrant|guarantee|condition)\b|\b(disclaim|exclude)[sd]?\b.{0,150}?\b(all\s+)?warrant(y|ies)\b|\b(without\s+warrant(y|ies)\s+of\s+any\s+kind)\b|\bno\s+(implied\s+)?warrant(y|ies)\b",
                aliases=["as_is_disclaimer", "no_warranty", "implied_warranty_waiver"],
            ),
            Rule(
                rule_id="M_BREACH_NOTIFY_01",
                rule_name="no_breach_notification",
                title="No data breach notification obligation",
                # Raised from Medium: for any contract involving regulated
                # personal data (PHI, financial data, EU personal data),
                # not knowing about a breach promptly is a materially more
                # serious gap than most Medium-tier findings in this
                # ruleset — the reviewing party's own downstream regulatory
                # notification clocks depend on learning about it quickly.
                severity=Severity.HIGH,
                rationale="Absence of a data breach notification requirement means you may not learn about compromises affecting your data until significant damage has occurred.",
                anchors=[r"\bdata\b", r"\bpersonal\s+(?:data|information)\b", r"\bsecurity\b"],
                nearby=[
                    r"\bno\s+obligation\s+to\s+notify\b",
                    r"\bnot\s+(?:be\s+)?(?:required|obligated)\s+to\s+(?:notify|inform|disclose)\b",
                    r"\bshall\s+not\s+(?:be\s+required\s+to\s+)?notify\b",
                ],
                window=400,
                aliases=["no_breach_notice", "data_breach_notification"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[
                    r"\b(personal\s+(?:data|information)|PII|data\s+breach|security\s+incident)\b",
                ],
                protective_patterns=[
                    r"\bnotify\b[^.]{0,80}\b(breach|incident|compromise)\b",
                    r"\b(breach|incident|compromise)\b[^.]{0,80}\bnotify\b",
                    r"\bwithout\s+undue\s+delay\b[^.]{0,80}\bnotify\b",
                    r"\bnotify\b[^.]{0,60}\bwithin\s+\d+\s+(hours?|days?)\b",
                ],
            ),
            Rule(
                rule_id="M_INSURANCE_01",
                rule_name="no_insurance_requirement",
                title="No minimum insurance requirements",
                severity=Severity.MEDIUM,
                rationale="Lack of insurance requirements means the counterparty may not have financial backing to cover claims, leaving indemnity and liability protections hollow.",
                anchors=[r"\binsurance\b"],
                # Adverse language only — genuinely protective phrasing ("shall
                # maintain", "commercially reasonable ... insurance") used to be
                # listed here too, which flagged good insurance clauses as risks.
                # Protective language now lives in protective_patterns below.
                nearby=[
                    r"\bnot\s+required\b",
                    r"\bno\s+obligation\b",
                    r"\bwaive[sd]?\b",
                ],
                window=350,
                aliases=["insurance_requirements", "no_insurance"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(vendor|provider|supplier|contractor|services?)\b"],
                protective_patterns=[
                    r"\bshall\s+maintain\b[^.]{0,80}\binsurance\b",
                    r"\binsurance\b[^.]{0,80}\bshall\s+maintain\b",
                    r"\bcommercially?\s+reasonable\b[^.]{0,40}\binsurance\b",
                    r"\bcertificate\s+of\s+insurance\b",
                    r"\binsurance\b[^.]{0,60}\$[\d,]+",
                ],
            ),
            Rule(
                rule_id="M_FORCE_MAJEURE_01",
                rule_name="broad_force_majeure",
                title="Overly broad force majeure clause",
                severity=Severity.MEDIUM,
                rationale="Force majeure clauses that include broad catch-alls like 'any event beyond control' or excuse all performance obligations can be used to avoid accountability.",
                anchors=[r"\bforce\s+majeure\b"],
                nearby=[
                    r"\bany\s+(event|cause|circumstance)\s+beyond\b",
                    r"\bincluding\s+but\s+not\s+limited\s+to\b",
                    r"\bexcused?\s+from\s+(?:all\s+)?performance\b",
                    r"\bno\s+liability\b.*\bperformance\b",
                    r"\bwithout\s+limitation\b",
                ],
                window=450,
                aliases=["force_majeure_scope", "broad_force_majeure"],
            ),
            Rule(
                rule_id="M_SLA_01",
                rule_name="no_sla_uptime",
                title="No service level or uptime commitment",
                severity=Severity.MEDIUM,
                rationale="Absence of defined service levels, uptime commitments, or remedies for downtime means you have no contractual recourse for service failures.",
                pattern=r"\b(no\s+(?:service\s+level|SLA|uptime)\s+(?:guarantee|commitment|obligation))\b|\b(does\s+not\s+(?:guarantee|warrant|commit)\b.{0,100}?\b(?:availability|uptime|service\s+level))\b|\b(?:availability|uptime)\b.{0,100}?\b(as[\s-]is|without\s+(?:any\s+)?guarantee)\b",
                aliases=["no_sla", "no_uptime_guarantee", "service_level_absent"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(service|platform|software|application|system|SaaS)\b"],
                # The "same sentence" heuristic below is (?:[^.]|\.(?=\d)),
                # not a bare [^.] character class: a bare [^.] treats the
                # decimal point INSIDE a percentage like "99.9%" as a
                # sentence boundary, which made it structurally impossible
                # for these patterns to ever reach a real uptime percentage
                # (verified against a real 99.9% SLA clause). "\.(?=\d)"
                # allows a period through only when it's a decimal point
                # (followed by a digit), so real sentence periods still
                # stop the scan. The percentage patterns also no longer
                # require a trailing \b immediately after "%", since "%" is
                # a non-word character and is essentially never itself
                # followed by a word character in real prose (it's
                # followed by a space, parenthesis, or punctuation) — the
                # old trailing \b made the "%" alternative effectively
                # unmatchable.
                protective_patterns=[
                    r"\b(service\s+level|SLA|uptime)\b(?:[^.]|\.(?=\d)){0,100}"
                    r"(?:\b(?:guarantee|commitment|percent)\b|\d{1,3}(?:\.\d+)?\s?%)",
                    r"\d{1,3}(?:\.\d+)?\s?%(?:[^.]|\.(?=\d)){0,60}\b(uptime|availability)\b",
                    r"\b(uptime|availability)\b(?:[^.]|\.(?=\d)){0,60}\d{1,3}(?:\.\d+)?\s?%",
                ],
            ),
            Rule(
                rule_id="M_MFN_01",
                rule_name="most_favored_nation",
                title="Most favored nation / price protection clause",
                severity=Severity.MEDIUM,
                rationale="MFN clauses require you to offer the same or better terms given to any other customer, which can constrain your pricing flexibility and deal structures.",
                pattern=r"\bmost\s+favored\s+(?:nation|customer|pricing)\b|\bprice\s+protection\b|\b(?:no\s+less\s+favorable|at\s+least\s+as\s+favorable)\s+(?:terms?|pricing|rates?)\b",
                aliases=["mfn_clause", "price_protection", "most_favored_customer"],
            ),
            # ---------------- LOW ----------------
            Rule(
                rule_id="L_LATEFEE_01",
                rule_name="late_fees_interest",
                title="Late fees / high interest",
                severity=Severity.LOW,
                rationale="Penalty terms can increase costs if payment timing slips.",
                # The old pattern used bare "interest" as an anchor, which
                # is polysemous: "right, title, and interest" (ownership,
                # extremely common in IP/data clauses) matches the word
                # "interest" just as well as a financial interest rate
                # does. Combined with an unbounded DOTALL ".*?", this let
                # an ownership clause bridge, via document-wide search, to
                # an unrelated percentage anywhere later in the same chunk
                # (verified: it fired on "...title, and interest..." to a
                # later SLA uptime percentage with no financial relationship
                # between them). This version requires a specific late-fee/
                # interest-RATE phrase (not bare "interest") tightly bound
                # to a percentage or a "per annum/year/month" period.
                pattern=(
                    r"\blate\s+(?:fees?|payments?|charges?)\b(?:[^.]|\.(?=\d)){0,80}?\d{1,3}(?:\.\d+)?\s?%"
                    r"|\d{1,3}(?:\.\d+)?\s?%(?:[^.]|\.(?=\d)){0,80}?\bper\s+(?:annum|year|month)\b"
                    r"|\binterest\s+rate\b(?:[^.]|\.(?=\d)){0,60}?\d{1,3}(?:\.\d+)?\s?%"
                    r"|\bfinance\s+charges?\b"
                    r"|\bpenalty\s+interest\b"
                ),
            ),
            Rule(
                rule_id="L_BROADDEF_01",
                rule_name="broad_definitions",
                title="Broad definitions may expand obligations",
                severity=Severity.LOW,
                rationale="Overly broad defined terms can expand confidentiality or scope beyond what you expect.",
                pattern=r"\bmeans\b.{0,150}?\b(including|without\s+limitation)\b",
            ),
            Rule(
                rule_id="L_GOVLAW_01",
                rule_name="governing_law_venue",
                title="Specific governing law or venue",
                severity=Severity.LOW,
                rationale="Governing law and venue choices can affect enforcement cost and strategy.",
                pattern=r"\bgoverned\s+by\b.{0,80}?\blaws?\b|\bexclusive\s+jurisdiction\b",
                aliases=["governing_law_and_venue"],
            ),
            Rule(
                rule_id="L_COMPLIANCE_01",
                rule_name="compliance_obligations",
                title="Regulatory compliance obligations",
                severity=Severity.LOW,
                rationale="Anti-bribery, export control, or sanctions compliance obligations can create reporting and operational burdens worth reviewing.",
                pattern=r"\b(anti[-\s]?bribery|anti[-\s]?corruption|FCPA|export\s+control|sanctions?\s+compliance|trade\s+compliance)\b",
                aliases=["anti_bribery", "export_control", "sanctions_compliance"],
            ),
            Rule(
                rule_id="L_ESCROW_01",
                rule_name="source_code_escrow",
                title="Source code escrow provisions",
                severity=Severity.LOW,
                rationale="Source code escrow clauses for critical software dependencies ensure business continuity if the vendor fails, but may carry costs and conditions.",
                pattern=r"\b(source\s+code\s+escrow|software\s+escrow|escrow\s+agent)\b",
                aliases=["code_escrow", "software_escrow"],
            ),
            Rule(
                rule_id="L_SUBCONTRACT_01",
                rule_name="subcontracting_rights",
                title="Subcontracting without consent",
                severity=Severity.LOW,
                rationale="Rights to subcontract without your consent mean unknown third parties may perform critical obligations, affecting quality and security.",
                anchors=[r"\bsubcontract\w*\b", r"\bsub[-\s]?contract\w*\b"],
                nearby=[
                    r"\bwithout\s+(prior\s+)?(written\s+)?consent\b",
                    r"\bat\s+its?\s+(sole\s+)?discretion\b",
                    r"\bwithout\s+(?:prior\s+)?(?:approval|notification)\b",
                ],
                window=300,
                aliases=["subcontracting", "third_party_delegation"],
            ),

            # ---------------- HIGH (v2.1 additions) ----------------
            Rule(
                rule_id="H_AI_TRAINING_01",
                rule_name="ai_model_training_on_data",
                title="Customer data may be used to train AI/ML models",
                severity=Severity.CRITICAL,
                rationale="Vendor rights to train AI or ML models on your data can permanently embed proprietary or sensitive information into third-party systems with no practical remedy.",
                anchors=[r"\btrain\w*\b", r"\bmachine\s+learning\b", r"\bartificial\s+intelligence\b", r"\bAI\s+model\b", r"\bML\s+model\b"],
                nearby=[
                    r"\bcustomer\s+data\b",
                    r"\byour\s+data\b",
                    r"\buser\s+content\b",
                    r"\binput\s+data\b",
                    r"\bsubmissions?\b",
                ],
                window=400,
                aliases=["ai_training", "ml_training_on_customer_data", "model_training"],
            ),
            Rule(
                rule_id="H_PRICE_ESCAL_01",
                rule_name="unilateral_price_escalation",
                title="Unilateral price escalation without consent",
                severity=Severity.HIGH,
                rationale="Unilateral rights to increase fees or rates at any time or upon notice alone can materially alter the economics of the deal after signing.",
                anchors=[r"\b(may|reserves?\s+the\s+right\s+to)\b"],
                nearby=[
                    r"\b(increase|adjust|change|modify|raise)\b.*\b(price|fee|rate|charge|cost)\b",
                    r"\b(price|fee|rate|charge|cost)\b.*\b(increase|adjustment|change|modification|raise)\b",
                ],
                window=350,
                aliases=["price_increase", "fee_escalation", "unilateral_rate_change"],
            ),
            Rule(
                rule_id="H_DATA_PRIVACY_01",
                rule_name="missing_data_processing_obligations",
                title="Personal data processing without any privacy/security protections",
                severity=Severity.CRITICAL,
                rationale="Agreements that involve processing personal data but contain no reference to any data-protection law, security measures, or controller/processor allocation leave you without contractual protections required by law.",
                # Originally PRESENCE_RISK (fired on the mere proximity of
                # "personal data" to "process/collect/store/use"), with a
                # rationale that claimed an ABSENCE ("lack references to
                # DPA, GDPR, CCPA..."). That mismatch meant the rule could
                # — and did — fire HIGH on a clause that explicitly quotes
                # HIPAA and GDPR by name, with cited evidence that directly
                # contradicts the finding's own claim (verified). Converted
                # to REQUIRED_SECTION: it now only reports "no protections"
                # when no privacy-law/security-measure/controller-processor
                # language exists ANYWHERE in the document. The narrower,
                # real gaps this contract actually has (no DPA/BAA execution
                # requirement, no subprocessor terms, no audit rights, no
                # deletion certification) are covered by their own,
                # separately-scoped rules — see M_DPA_MISSING_01,
                # M_BAA_MISSING_01, M_SUBPROCESSOR_MISSING_01,
                # M_AUDIT_RIGHTS_CUSTOMER_01, M_DELETION_CERT_MISSING_01.
                anchors=[
                    r"\bpersonal\s+(data|information)\b",
                    r"\bpersonally\s+identifiable\s+information\b",
                    r"\bPII\b",
                ],
                nearby=[
                    r"\bwithout\s+(?:any\s+)?restriction\b",
                    r"\bfor\s+any\s+purpose\b",
                    r"\bno\s+(?:obligation|duty)\s+to\s+protect\b",
                    r"\bwithout\s+(?:regard\s+to\s+)?(?:privacy|security)\b",
                ],
                window=300,
                aliases=["missing_dpa", "gdpr_obligations", "data_processing_without_protection"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(personal\s+(data|information)|personally\s+identifiable\s+information|PII)\b"],
                protective_patterns=[
                    r"\b(GDPR|CCPA|CPRA|HIPAA)\b",
                    r"\b(DPA|data\s+processing\s+agreement|data\s+protection\s+(law|act|regulation))\b",
                    r"\b(security\s+measures?|technical\s+and\s+organi[sz]ational\s+measures?|industry[-\s]?standard\s+security)\b",
                    r"\bData\s+(Controller|Processor)\b",
                ],
            ),

            # ---------------- MEDIUM (v2.1 additions) ----------------
            Rule(
                rule_id="M_DATA_PORTABILITY_01",
                rule_name="no_data_portability_rights",
                title="No data portability or export rights on exit",
                severity=Severity.MEDIUM,
                rationale="Without explicit data portability or export rights, you may be unable to retrieve your data in a usable format after the relationship ends.",
                anchors=[r"\bterminat\w+\b", r"\bexpir\w+\b", r"\bend\s+of\s+(the\s+)?(agreement|term|contract)\b"],
                nearby=[
                    r"\bno\s+(right\s+to\s+)?(export|portab|migrat)\b",
                    r"\b(data|content)\s+(will\s+be\s+)?(deleted|destroyed|removed)\b",
                    r"\bnot\s+(obligated|required)\b.*\b(export|return|provide)\b.*\bdata\b",
                ],
                window=500,
                aliases=["data_export_rights", "portability_on_termination"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(terminat\w+|expir\w+)\b", r"\bdata\b"],
                protective_patterns=[
                    r"\bexport\w*\b[^.]{0,60}\bdata\b",
                    r"\bdata\s+portability\b",
                    r"\bmigrat\w+\b[^.]{0,60}\bdata\b",
                    r"\breturn\w*\b[^.]{0,60}\bdata\b",
                ],
            ),
            Rule(
                rule_id="M_DATA_DELETION_01",
                rule_name="no_data_deletion_obligation",
                title="No data deletion or return obligation on termination",
                severity=Severity.MEDIUM,
                rationale="Without a contractual obligation to delete or return your data after termination, vendors may retain it indefinitely, creating privacy and competitive risk.",
                anchors=[r"\bterminat\w+\b", r"\bexpir\w+\b"],
                nearby=[
                    r"\b(customer\s+data|your\s+data|personal\s+(data|information))\b",
                ],
                window=600,
                aliases=["data_deletion_on_termination", "no_purge_obligation", "data_retention_after_termination"],
            ),
            Rule(
                rule_id="M_CROSS_BORDER_01",
                rule_name="cross_border_data_transfer",
                title="Cross-border data transfer without adequate safeguards",
                severity=Severity.MEDIUM,
                rationale="Transferring personal data across borders without SCCs, adequacy decisions, or equivalent safeguards violates GDPR and similar regulations.",
                anchors=[
                    r"\btransfer\w*\b.*\b(personal\s+data|personal\s+information|PII)\b",
                    r"\b(personal\s+data|personal\s+information|PII)\b.*\btransfer\w*\b",
                ],
                nearby=[
                    r"\bcross[-\s]?border\b",
                    r"\binternational\s+transfer\b",
                    r"\bthird\s+countr\w+\b",
                    r"\boutside\s+(the\s+)?(EU|EEA|United\s+States|UK)\b",
                ],
                window=450,
                aliases=["international_data_transfer", "cross_border_transfer", "sccs"],
            ),
            Rule(
                rule_id="M_RENEWAL_PRICE_01",
                rule_name="renewal_price_increase",
                title="Renewal pricing may increase without cap",
                severity=Severity.MEDIUM,
                rationale="Renewal terms that allow uncapped fee increases at renewal can materially alter the total cost of the relationship after the initial term.",
                anchors=[r"\brenew\w+\b", r"\brenewal\s+term\b"],
                nearby=[
                    r"\b(increase|adjust|change|modify|raise)\b.*\b(price|fee|rate|charge)\b",
                    r"\bCPI\b",
                    r"\binflation\b",
                    r"\bprevailing\s+(rate|price)\b",
                ],
                window=400,
                aliases=["renewal_fee_increase", "auto_renewal_price_change"],
            ),
            Rule(
                rule_id="M_MIN_COMMIT_01",
                rule_name="minimum_purchase_commitment",
                title="Minimum purchase commitment or take-or-pay obligation",
                severity=Severity.MEDIUM,
                rationale="Minimum commitment or take-or-pay clauses obligate you to pay for services you may not use, creating financial exposure regardless of actual usage.",
                anchors=[
                    r"\bminimum\s+(purchase|commit\w*|order|spend|volume)\b",
                    r"\btake[-\s]?or[-\s]?pay\b",
                ],
                nearby=[
                    r"\bshortfall\b",
                    r"\bregardless\s+of\s+(actual\s+)?(use|usage|volume|consumption)\b",
                    r"\bobligation\b",
                ],
                window=400,
                aliases=["minimum_commitment", "take_or_pay", "volume_commitment"],
            ),
            Rule(
                rule_id="M_BENCHMARKING_01",
                rule_name="benchmarking_restrictions",
                title="Benchmarking or competitive analysis restrictions",
                severity=Severity.MEDIUM,
                rationale="Restrictions on benchmarking prevent you from independently evaluating performance or comparing against alternatives, limiting your negotiating leverage at renewal.",
                pattern=r"\b(no|not|prohibit\w*|restrict\w*)\b.{0,60}\bbenchmark\w*\b|\bbenchmark\w*\b.{0,60}\b(prohibit\w*|not\s+permit\w*|restrict\w*|may\s+not)\b",
                aliases=["benchmark_prohibition", "competitive_testing_restriction"],
            ),
            Rule(
                rule_id="M_USE_RESTRICT_01",
                rule_name="permitted_use_restrictions",
                title="Narrow permitted use restrictions",
                severity=Severity.MEDIUM,
                rationale="Strict limitations on permitted use can prevent legitimate business activities and create breach exposure for activities you consider routine.",
                anchors=[
                    r"\bpermitted\s+use\b",
                    r"\bauthorized\s+use\b",
                    r"\buse\s+of\s+the\s+(service|platform|software|product)\b",
                    r"\blicense\s+grant\b",
                ],
                nearby=[
                    r"\bonly\b",
                    r"\bsolely\b",
                    r"\bexclusively\b",
                    r"\bmay\s+not\b",
                    r"\bprohibited\b",
                    r"\brestrict\w+\b",
                ],
                window=350,
                aliases=["use_restrictions", "limited_license_scope"],
            ),

            # ---------------- LOW (v2.1 additions) ----------------
            Rule(
                rule_id="L_EXPORT_CTRL_01",
                rule_name="export_control_obligations",
                title="Export control and trade compliance obligations",
                severity=Severity.LOW,
                rationale="Export control compliance clauses impose certification and monitoring burdens that can affect your ability to work with certain customers or in certain countries.",
                anchors=[r"\bexport\s+control\b", r"\bexport\s+law\b", r"\bEAR\b", r"\bITAR\b", r"\btrade\s+compliance\b"],
                nearby=[
                    r"\bcomply\b",
                    r"\bobligation\b",
                    r"\brestrict\w*\b",
                    r"\bsanction\w*\b",
                ],
                window=350,
                aliases=["export_control", "itar", "ear_compliance", "trade_restrictions"],
            ),
            Rule(
                rule_id="L_PAYMENT_TERMS_01",
                rule_name="payment_terms",
                title="Payment terms / net days",
                severity=Severity.LOW,
                rationale="Short payment windows or unfavorable payment terms can create cash flow pressure, especially if combined with late fee provisions.",
                pattern=r"\bnet\s+\d+\b|\bdue\s+(within|in)\s+\d+\s+days?\b|\bpayment\s+(is\s+)?due\b|\binvoice\w*\s+(within|in)\s+\d+\s+days?\b",
                aliases=["payment_due", "net_days", "invoice_terms"],
            ),

            # ---------------- Contract-to-cash: payment/invoice configuration ----------------
            # H_BILLING_CONFLICT_01, H_PRICE_CONFLICT_01, H_PARTY_IDENTITY_CONFLICT_01,
            # and H_SIGNATURE_PARTY_MISSING_01 are document-wide consistency checks, not
            # single-clause matches — see RuleEngine._check_cross_document_conflicts().
            Rule(
                rule_id="M_PAYMENT_TRIGGER_01",
                rule_name="invoice_trigger_missing",
                title="No invoice trigger event specified",
                severity=Severity.MEDIUM,
                rationale="Without a defined invoicing trigger (e.g. upon execution, service activation, or delivery), it is unclear when billing may begin, which can cause invoice timing mismatches.",
                pattern=r"\binvoic\w*\b[^.]{0,40}\b(?:to\s+be\s+determined|TBD|to\s+be\s+agreed)\b",
                aliases=["invoice_trigger_undefined", "billing_start_undefined"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(invoic\w*|bill\w*|payment)\b"],
                protective_patterns=[
                    r"\binvoic\w*\b[^.]{0,60}\b(?:upon|following|after|within)\b[^.]{0,60}"
                    r"\b(activation|delivery|execution|go-live|commencement|acceptance)\b",
                    r"\bbilling\s+shall\s+(?:begin|commence)\b",
                ],
            ),
            Rule(
                rule_id="M_CURRENCY_AMBIGUOUS_01",
                rule_name="currency_ambiguous",
                title="Payment currency not specified",
                severity=Severity.MEDIUM,
                rationale="Amounts stated without an explicit currency designation are ambiguous and can cause invoicing and payment reconciliation errors, especially in cross-border deals.",
                pattern=r"\bcurrency\s+(?:to\s+be\s+determined|TBD)\b",
                aliases=["currency_undefined", "ambiguous_currency"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\$\s?[\d,]+(?:\.\d{2})?"],
                protective_patterns=[
                    r"\b(USD|EUR|GBP|CAD|AUD|United\s+States\s+Dollars?)\b",
                    r"€|£",
                ],
            ),
            Rule(
                rule_id="M_BILLING_FREQUENCY_01",
                rule_name="billing_frequency_missing",
                title="Billing frequency not specified",
                severity=Severity.MEDIUM,
                rationale="Fees mentioned without a stated billing frequency (monthly, quarterly, annual, one-time) can't be reliably configured as recurring or one-time invoices.",
                pattern=r"\bbilling\s+frequency\s+(?:to\s+be\s+determined|TBD)\b",
                aliases=["billing_cadence_missing", "recurring_billing_undefined"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(fee|payment|invoic\w*|price)\b"],
                protective_patterns=[
                    r"\b(monthly|quarterly|annual(?:ly)?|yearly|weekly|one[-\s]?time|recurring|"
                    r"per\s+month|per\s+year)\b",
                ],
            ),
            Rule(
                rule_id="M_PRICE_EXHIBIT_MISSING_01",
                rule_name="price_exhibit_missing",
                title="Pricing referenced in an exhibit that isn't included",
                severity=Severity.MEDIUM,
                rationale="Pricing that is only defined by reference to an exhibit or schedule is unusable for invoicing if that exhibit isn't actually attached or included in the document.",
                pattern=r"\bpricing\b[^.]{0,60}\bnot\s+attached\b",
                aliases=["exhibit_pricing_missing", "unattached_pricing_exhibit"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[
                    r"\b(pricing|fees?|price)\b",
                    # (?-i:...) keeps the identifier case-sensitive even
                    # though this pattern is matched with re.IGNORECASE —
                    # without it, [A-Z0-9]+ matches ANY letters/digits
                    # case-insensitively (i.e. effectively any word), which
                    # let ordinary prose satisfy what was meant to require
                    # an actual exhibit letter/number label like "A" or "1".
                    r"\b(exhibit|schedule|appendix)\s+(?-i:[A-Z0-9]+)\b",
                ],
                protective_patterns=[
                    r"\b(exhibit|schedule|appendix)\s+(?-i:[A-Z0-9]+)\b[\s\S]{0,300}\b(exhibit|schedule|appendix)\s+(?-i:[A-Z0-9]+)\b",
                ],
                window=350,
            ),
            Rule(
                rule_id="M_EXPENSE_APPROVAL_01",
                rule_name="expense_approval_missing",
                title="Reimbursable expenses lack an approval limit",
                severity=Severity.MEDIUM,
                rationale="Reimbursable expense language without a pre-approval requirement or cap can result in unbounded, unbudgeted costs.",
                anchors=[r"\breimburs\w*\b", r"\bexpense\w*\b"],
                nearby=[r"\bwithout\s+(?:any\s+)?(?:limit|cap|approval)\b"],
                window=300,
                aliases=["unbounded_expense_reimbursement", "no_expense_cap"],
                rule_class=RuleClass.REQUIRED_SECTION,
                # Bare "expense\w*" put the termination wind-down settlement
                # clause ("Company shall pay Prevail all direct expenses and
                # fees for Services completed ... as of the date of
                # termination") in scope for this rule, which is about
                # discretionary reimbursable-expense approval limits, a
                # different concept from a termination cost settlement
                # (verified false positive). Requiring "reimburs\w*"
                # specifically targets the actual reimbursement concept.
                topic_patterns=[r"\breimburs\w*\b"],
                protective_patterns=[
                    r"\bprior\s+written\s+approval\b",
                    r"\bnot\s+to\s+exceed\s+\$",
                    r"\bpre[-\s]?approved\b",
                    r"\bapproved\s+in\s+advance\b",
                ],
            ),
            Rule(
                rule_id="M_USAGE_MEASUREMENT_01",
                rule_name="usage_measurement_missing",
                title="Usage-based charges lack a measurement method",
                severity=Severity.MEDIUM,
                rationale="Usage-based or overage charges without a defined measurement method leave the billing amount effectively undeterminable and disputable.",
                anchors=[r"\busage\s+charges?\b", r"\boverage\s+(?:fees?|charges?)\b"],
                nearby=[r"\bsole\s+discretion\b"],
                window=300,
                aliases=["undefined_usage_metric", "usage_billing_undefined"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(usage|overage|metered|per[-\s]?unit)\b[^.]{0,20}\b(charge|fee|billing)\b"],
                protective_patterns=[
                    r"\bmeasured\s+by\b",
                    r"\bmetered\b",
                    r"\bcalculated\s+based\s+on\b",
                    r"\busage\s+report\b",
                    r"\bmeter\w*\s+reading\b",
                ],
            ),
            Rule(
                rule_id="M_DISCOUNT_EXPIRY_01",
                rule_name="discount_expiry_missing",
                title="Discount lacks a clear expiration",
                severity=Severity.MEDIUM,
                rationale="A discount stated without a clear expiration or duration is ambiguous as to when standard pricing resumes, risking under-billing or customer disputes.",
                pattern=r"\bdiscount\w*\b[^.]{0,40}\bno\s+expiration\b",
                aliases=["discount_duration_undefined", "open_ended_discount"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bdiscount\w*\b"],
                protective_patterns=[
                    r"\bdiscount\w*\b[^.]{0,80}\b(expir\w*|through\s+\d{4}|for\s+the\s+first\s+\d+|"
                    r"for\s+\d+\s+(?:months?|years?)|until\s+\w+\s+\d{1,2},?\s+\d{4})\b",
                ],
            ),

            # ---------------- Contract-to-cash: signature & execution defects ----------------
            Rule(
                rule_id="M_AUTHORITY_REP_01",
                rule_name="signatory_authority_missing",
                title="Signatory title or authority representation missing",
                severity=Severity.MEDIUM,
                rationale="A signature block without a stated title or 'duly authorized' representation leaves it unclear whether the signer had authority to bind the entity.",
                pattern=r"\bTitle\s*:\s*(?:_{2,}|\[\s*\])",
                aliases=["blank_signatory_title", "signatory_authority_undefined"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bIN\s+WITNESS\s+WHEREOF\b"],
                protective_patterns=[r"\bTitle\s*:\s*\S", r"\bduly\s+authorized\b"],
            ),
            Rule(
                rule_id="M_EFFECTIVE_DATE_MISSING_01",
                rule_name="effective_date_blank",
                title="Effective Date left blank",
                severity=Severity.MEDIUM,
                rationale="A blank or placeholder Effective Date means the contract term, renewal dates, and payment schedule cannot be reliably calculated.",
                pattern=r"\bEffective\s+Date\s*[:\s]*(?:_{2,}|\[\s*\]|\bTBD\b|\bXX+\b)",
                aliases=["blank_effective_date", "effective_date_placeholder"],
            ),
            Rule(
                rule_id="M_EXHIBIT_MISSING_01",
                rule_name="exhibit_referenced_missing",
                title="Exhibit, schedule, or SOW referenced but not found",
                severity=Severity.MEDIUM,
                rationale="A contract that refers to an exhibit, schedule, SOW, or appendix that isn't actually included leaves material terms undefined.",
                pattern=r"\b(?:exhibit|schedule|appendix)\s+[A-Z0-9]+\b[^.]{0,40}\b(?:not\s+attached|to\s+be\s+provided|forthcoming)\b",
                aliases=["missing_exhibit", "unattached_schedule", "missing_sow"],
                rule_class=RuleClass.REQUIRED_SECTION,
                # The bare "exhibit N" pattern matched a document's own SEC
                # filing provenance line ("Source: SEC EDGAR - 8-K, Exhibit
                # 10.1, Period ...") as if it were a substantive in-contract
                # cross-reference (verified). Requiring "attached hereto" /
                # "attached as" / "set forth in" nearby targets an actual
                # attachment reference instead, and adds SOW/Statement of
                # Work — the term this contract actually uses for its
                # missing attachment, which the original pattern omitted.
                topic_patterns=[
                    r"\b(?:SOW|Statement\s+of\s+Work|Schedule|Exhibit|Appendix)\s+(?:No\.?\s*)?(?-i:[A-Z0-9]+)\b"
                    r"(?:[^.]|\.(?=\d)){0,40}\b(?:attached\s+hereto|attached\s+as|set\s+forth\s+in)\b"
                ],
                # (?-i:[A-Z0-9]+) keeps the exhibit/SOW identifier
                # case-sensitive under the module's IGNORECASE match call —
                # without it, a bare later mention like "the SOW shall be
                # governed by..." satisfies [A-Z0-9]+ against "shall"
                # (case-insensitively equivalent to letters), which made
                # this "protective" check pass even though no second,
                # actually-numbered SOW/Schedule reference (let alone real
                # attached content) exists anywhere in the document
                # (verified false suppression on the real contract).
                protective_patterns=[
                    r"\b(SOW|Statement\s+of\s+Work|Schedule|exhibit|appendix)\s+(?:No\.?\s*)?(?-i:[A-Z0-9]+)\b"
                    r"[\s\S]{0,400}\b(SOW|Statement\s+of\s+Work|Schedule|exhibit|appendix)\s+(?:No\.?\s*)?(?-i:[A-Z0-9]+)\b",
                ],
            ),
            Rule(
                rule_id="L_COUNTERPARTS_ESIGN_01",
                rule_name="counterparts_esignature",
                title="Execution in counterparts / electronic signature language",
                severity=Severity.LOW,
                rationale="Counterparts and e-signature language is standard and generally favorable for execution speed, but worth confirming it references a valid e-signature method (e.g. ESIGN/UETA compliant).",
                pattern=r"\bcounterparts?\b[^.]{0,60}\b(?:execute[sd]?|signed)\b|\belectronic\s+signature\b|\bDocuSign\b|\belectronically\s+executed\b",
                aliases=["esignature_language", "counterparts_clause"],
            ),

            # ---------------- Contract-to-cash: termination-to-billing consequences ----------------
            Rule(
                rule_id="H_PAYMENT_ACCELERATION_01",
                rule_name="payment_acceleration",
                title="Payment obligations accelerate upon termination or breach",
                severity=Severity.HIGH,
                rationale="Acceleration clauses that make all remaining fees immediately due upon termination or breach can create a large, unexpected lump-sum payment obligation.",
                anchors=[r"\bterminat\w*\b", r"\bbreach\w*\b"],
                nearby=[
                    r"\baccelerat\w*\b",
                    r"\bimmediately\s+due\s+and\s+payable\b",
                    r"\bbecome\s+due\s+and\s+payable\b",
                ],
                window=350,
                aliases=["fee_acceleration_on_termination", "accelerated_payment_obligation"],
            ),
            Rule(
                rule_id="H_POST_TERMINATION_BILLING_01",
                rule_name="post_termination_billing",
                title="Billing continues after termination",
                severity=Severity.HIGH,
                rationale="Language that continues billing or fee liability after termination or expiration can result in charges for a service that is no longer being provided.",
                anchors=[r"\btermination\b", r"\bexpir\w*\b"],
                nearby=[
                    r"\bcontinue\s+to\s+(?:bill|charge|invoice)\b",
                    r"\bremain\s+liable\s+for\s+(?:fees|payments|charges)\b",
                    r"\bshall\s+continue\s+to\s+accrue\b",
                ],
                window=350,
                aliases=["continued_billing_post_termination", "post_termination_fee_liability"],
            ),
            Rule(
                rule_id="M_PREPAID_FEES_REFUND_01",
                rule_name="prepaid_fees_refund_missing",
                title="Prepaid fees non-refundable / refund terms unclear on termination",
                severity=Severity.MEDIUM,
                rationale="Prepaid fees without pro-rata refund language on early termination mean the customer loses the unused, already-paid portion of the contract.",
                anchors=[r"\bprepaid\b|\bpre[-\s]paid\b"],
                nearby=[r"\bnon[-\s]?refundable\b"],
                window=300,
                aliases=["prepaid_fees_not_refundable", "no_prorata_refund"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bprepaid\b|\bpre[-\s]paid\b", r"\btermin\w*\b"],
                protective_patterns=[
                    r"\brefund\w*\b[^.]{0,80}\b(?:pro[-\s]?rata|upon\s+termination)\b",
                    r"\bpro[-\s]?rata\s+refund\b",
                ],
            ),
            Rule(
                rule_id="M_FINAL_INVOICE_01",
                rule_name="final_invoice_timing_missing",
                title="Final invoice timing on termination not specified",
                severity=Severity.MEDIUM,
                rationale="Without a defined timeline for issuing a final invoice after termination, billing close-out and reconciliation can be delayed indefinitely.",
                pattern=r"\bfinal\s+invoice\b[^.]{0,40}\bsole\s+discretion\b",
                aliases=["final_invoice_undefined", "termination_billing_close_out_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\btermin\w*\b", r"\binvoic\w*\b"],
                protective_patterns=[r"\bfinal\s+invoice\b"],
            ),
            Rule(
                rule_id="M_EARLY_TERMINATION_FEE_01",
                rule_name="early_termination_fee",
                title="Early termination fee or penalty",
                severity=Severity.MEDIUM,
                rationale="Early termination fees add a direct cost to exiting the contract before term end and should be confirmed as reasonable and clearly calculated.",
                anchors=[r"\bearly\s+terminat\w*\b"],
                nearby=[r"\bfee\b", r"\bpenalt(?:y|ies)\b", r"\bcharge\b"],
                window=300,
                aliases=["early_termination_penalty", "termination_charge"],
            ),

            # --- v6.0: small/midsize law firm broad-practice expansion ---
            # Commercial leases, loans/guaranties, employment offer/severance,
            # franchise/distribution, M&A/partnership, settlement agreements,
            # and construction contracts — document types a generalist small
            # or midsize firm reviews far more often than SaaS/vendor MSAs.
            # All patterns use \s+/\.{0,N} tolerant spacing (not literal
            # spaces) so a match survives PDF line-wraps, hyphenation, and
            # inconsistent whitespace from OCR or copy-paste extraction.

            # -- Commercial leases --
            Rule(
                rule_id="H_LEASE_PERSONAL_GUARANTY_01",
                rule_name="lease_personal_guaranty",
                title="Personal guaranty of lease obligations",
                severity=Severity.HIGH,
                rationale="An individual guaranty of a commercial lease extends the tenant entity's default exposure to the signer personally, often for the full remaining lease term and without a defined cap.",
                anchors=[r"\bpersonally\s+guarant\w*\b", r"\bguarantor\b"],
                nearby=[r"\blease\b", r"\btenant\b", r"\blandlord\b", r"\bpremises\b"],
                window=300,
                aliases=["personal_lease_guaranty", "individual_lease_guaranty"],
            ),
            Rule(
                rule_id="H_LEASE_ASSIGN_SUBLET_01",
                rule_name="lease_assignment_sublet_consent",
                title="Landlord assignment/sublet consent lacks reasonableness standard",
                severity=Severity.HIGH,
                rationale="Requiring landlord consent to assign or sublet without a 'not unreasonably withheld' standard lets the landlord block a sale, merger, or space downsize for any reason, including no reason at all.",
                anchors=[r"\bassign\w*\b", r"\bsublet\w*\b|\bsub-?leas\w*\b"],
                nearby=[
                    r"\bsole\s+(?:and\s+absolute\s+)?discretion\b",
                    r"\bconsent\s+of\s+(?:the\s+)?landlord\b.{0,60}\brequired\b",
                ],
                window=300,
                aliases=["lease_assignment_consent", "sublet_consent_discretion"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[
                    r"\bassign\w*\b|\bsublet\w*\b|\bsub-?leas\w*\b",
                    r"\blandlord'?s?\s+(?:prior\s+)?(?:written\s+)?consent\b",
                ],
                protective_patterns=[
                    r"\bconsent\b(?:[^.]|\.(?=\d)){0,100}\bnot\s+be\s+unreasonably\s+withheld\b",
                    r"\bnot\s+(?:be\s+)?unreasonably\s+withheld,?\s*(?:conditioned,?\s*)?(?:or\s+delayed)?\b",
                ],
            ),
            Rule(
                rule_id="H_LEASE_HOLDOVER_01",
                rule_name="lease_holdover_penalty",
                title="Holdover rent penalty",
                severity=Severity.HIGH,
                rationale="Holdover clauses that charge a large multiple of rent (often 150-200%) for remaining in the premises past lease expiration can create a significant unplanned cost if move-out is even briefly delayed.",
                anchors=[r"\bhold-?over\b|\bholding\s+over\b"],
                nearby=[
                    r"\b1\.5x\b|\b150\s*%|\b200\s*%|\bdouble\b|\btwice\b|\btwo\s+times\b|\bone[-\s]and[-\s]a[-\s]half\b",
                ],
                window=250,
                aliases=["holdover_penalty", "holdover_rent_multiplier"],
            ),
            Rule(
                rule_id="H_LEASE_RELOCATION_01",
                rule_name="lease_relocation_right",
                title="Landlord relocation right",
                severity=Severity.HIGH,
                rationale="A landlord right to relocate the tenant to different space, often at the landlord's sole discretion, can disrupt operations, signage, and customer goodwill without the tenant's agreement.",
                anchors=[r"\brelocat\w*\b"],
                nearby=[
                    r"\blandlord'?s?\s+(?:sole\s+)?discretion\b",
                    r"\bwithout\s+(?:tenant'?s?\s+)?consent\b",
                    r"\bat\s+landlord'?s?\s+option\b",
                ],
                window=300,
                aliases=["landlord_relocation_right", "forced_relocation"],
            ),
            Rule(
                rule_id="M_LEASE_CAM_UNCAPPED_01",
                rule_name="lease_cam_charges_uncapped",
                title="Common area maintenance (CAM) charges lack a cap",
                severity=Severity.MEDIUM,
                rationale="Common area maintenance (CAM) charges without an annual cap or increase limit let the landlord pass through rising operating costs unpredictably, on top of base rent.",
                anchors=[r"\bcommon\s+area\s+maintenance\b|\bCAM\s+charges?\b"],
                nearby=[r"\bin\s+landlord'?s?\s+(?:sole\s+)?discretion\b", r"\bwithout\s+limitation\b"],
                window=300,
                aliases=["cam_charges_uncapped", "operating_expense_uncapped"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bcommon\s+area\s+maintenance\b|\bCAM\s+charges?\b"],
                protective_patterns=[
                    r"\bCAM\b(?:[^.]|\.(?=\d)){0,120}\b(?:cap|capped|not\s+to\s+exceed|shall\s+not\s+increase\s+more\s+than|limited\s+to)\b",
                    r"\b(?:cap|capped|not\s+to\s+exceed)\b(?:[^.]|\.(?=\d)){0,120}\bCAM\b",
                    r"\bcommon\s+area\s+maintenance\b(?:[^.]|\.(?=\d)){0,120}\b(?:cap|capped|not\s+to\s+exceed)\b",
                ],
            ),
            Rule(
                rule_id="M_LEASE_ESCALATION_UNCAPPED_01",
                rule_name="lease_rent_escalation_uncapped",
                title="Rent escalation lacks a percentage cap",
                severity=Severity.MEDIUM,
                rationale="Annual rent escalation without a stated maximum percentage increase makes future occupancy costs unpredictable and can compound significantly over a multi-year term.",
                anchors=[r"\brent\b.{0,40}\b(?:increase|escalat\w*)\b"],
                nearby=[r"\bannually\b", r"\beach\s+(?:lease\s+)?year\b"],
                window=250,
                aliases=["rent_escalation_uncapped", "annual_rent_increase_uncapped"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\brent\b.{0,40}\b(?:increase|escalat\w*)\b"],
                protective_patterns=[
                    r"\b(?:increase|escalat\w*)\b(?:[^.]|\.(?=\d)){0,100}\b(?:shall\s+not\s+exceed|capped\s+at|no\s+more\s+than|not\s+to\s+exceed)\b\s*\d",
                ],
            ),

            # -- Loans / promissory notes / personal guaranties --
            Rule(
                rule_id="H_LOAN_CONFESSION_JUDGMENT_01",
                rule_name="confession_of_judgment",
                title="Confession of judgment / cognovit clause",
                severity=Severity.CRITICAL,
                rationale="A confession-of-judgment (cognovit) clause lets the lender obtain a judgment against the borrower or guarantor without notice or a hearing, waiving fundamental due-process rights — this is banned or heavily restricted in many states and should be flagged regardless of jurisdiction.",
                pattern=r"\bconfession\s+of\s+judgment\b|\bcognovit\b|\bwarrant\s+of\s+attorney\b.{0,80}\bconfess\w*\s+judgment\b|\bconfess\w*\s+judgment\b",
                aliases=["cognovit_clause", "confess_judgment"],
            ),
            Rule(
                rule_id="H_LOAN_GUARANTY_WAIVER_01",
                rule_name="loan_guaranty_defense_waiver",
                title="Guaranty waives standard borrower/surety defenses",
                severity=Severity.CRITICAL,
                rationale="An 'absolute and unconditional' guaranty that waives notice, demand, and suretyship defenses exposes the guarantor personally for the full debt with almost no ability to contest enforcement.",
                anchors=[r"\bguarant\w*\b"],
                nearby=[
                    r"\bwaives?\b.{0,60}\b(?:defenses?|notice|demand|presentment|suretyship)\b",
                    r"\bunconditional(?:ly)?\s+and\s+irrevocabl(?:e|y)\b",
                    r"\babsolute\s+and\s+unconditional\b",
                ],
                window=300,
                aliases=["unconditional_guaranty", "suretyship_defense_waiver"],
            ),
            Rule(
                rule_id="M_LOAN_CROSS_DEFAULT_01",
                rule_name="loan_cross_default",
                title="Cross-default provision",
                severity=Severity.MEDIUM,
                rationale="A cross-default clause means a default on any other loan or obligation automatically triggers default here too, so an unrelated financial problem can accelerate this debt as well.",
                anchors=[r"\bdefault\b"],
                nearby=[
                    r"\bcross[-\s]?default\b",
                    r"\bany\s+other\s+(?:agreement|indebtedness|obligation)\b.{0,60}\bdefault\b",
                    r"\bdefault\s+under\s+any\s+other\b",
                ],
                window=300,
                aliases=["cross_default_clause"],
            ),
            Rule(
                rule_id="M_LOAN_PREPAY_PENALTY_01",
                rule_name="loan_prepayment_penalty",
                title="Prepayment penalty",
                severity=Severity.MEDIUM,
                rationale="A prepayment penalty adds a direct cost to paying off the loan early, which can discourage refinancing or an early payoff even when it would otherwise save money.",
                anchors=[r"\bprepay\w*\b|\bpre-?pay\w*\b"],
                nearby=[r"\bpenalt(?:y|ies)\b", r"\bpremium\b", r"\bfee\b"],
                window=250,
                aliases=["prepayment_fee", "early_payoff_penalty"],
            ),
            Rule(
                rule_id="M_LOAN_RATE_DISCRETION_01",
                rule_name="loan_interest_rate_discretion",
                title="Interest rate subject to lender discretion",
                severity=Severity.MEDIUM,
                rationale="Interest rate language that lets the lender adjust the rate at its discretion, without a defined index, formula, or cap, creates unpredictable borrowing costs.",
                anchors=[r"\binterest\s+rate\b"],
                nearby=[
                    r"\blender'?s?\s+(?:sole\s+)?discretion\b",
                    r"\bmay\s+adjust\b.{0,60}\bwithout\s+notice\b",
                    r"\bmay\s+be\s+(?:increased|changed)\b.{0,60}\bdiscretion\b",
                ],
                window=300,
                aliases=["variable_rate_discretion", "uncapped_interest_rate"],
            ),

            # -- Employment offer letters / severance --
            Rule(
                rule_id="H_EMPLOY_ATWILL_WAIVER_01",
                rule_name="employment_atwill_waiver",
                title="Language may undermine at-will employment status",
                severity=Severity.HIGH,
                rationale="Promises of continued employment tied to performance or a stated duration can be read as an implied contract overriding at-will status, limiting the employer's ability to terminate without cause.",
                pattern=r"\b(?:guarantee[ds]?|assur\w+|promis\w+)\b.{0,60}\b(?:continued\s+)?employment\b.{0,80}\b(?:satisfactory\s+performance|as\s+long\s+as|for\s+(?:a|the)\s+(?:period|term|duration)\s+of)\b",
                aliases=["implied_employment_contract", "atwill_status_undermined"],
            ),
            Rule(
                rule_id="H_EMPLOY_IP_ASSIGN_OVERBROAD_01",
                rule_name="employment_ip_assignment_overbroad",
                title="Invention assignment may lack statutory own-time carve-out",
                severity=Severity.HIGH,
                rationale="A broad 'assigns all inventions' clause with no carve-out for inventions developed entirely on the employee's own time, without company resources, and unrelated to the business can sweep in personal projects — several states (e.g. California Labor Code §2870) render such overbroad assignments unenforceable, but only if the required carve-out notice is actually present.",
                anchors=[r"\bassign\w*\b|\bhereby\s+assigns?\b"],
                nearby=[r"\ball\s+inventions\b", r"\bwork\s+product\b", r"\bideas\b.{0,20}\bdiscoveries\b"],
                window=300,
                aliases=["overbroad_invention_assignment", "missing_2870_carveout"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[
                    r"\binvention\w*\b.{0,100}\bassign\w*\b|\bassign\w*\b.{0,100}\binvention\w*\b",
                    r"\ball\s+(?:inventions|works|ideas)\b",
                ],
                protective_patterns=[
                    r"\bdoes\s+not\s+apply\b(?:[^.]|\.(?=\d)){0,150}\bown\s+time\b",
                    r"\bexcept\b(?:[^.]|\.(?=\d)){0,150}\bown\s+time\b(?:[^.]|\.(?=\d)){0,150}\bwithout\s+using\b",
                    r"\bnot\s+relate\s+to\s+(?:the\s+)?(?:Company'?s?\s+)?business\b",
                ],
            ),
            Rule(
                rule_id="M_EMPLOY_SEVERANCE_RELEASE_01",
                rule_name="employment_severance_release_overbroad",
                title="Severance release may lack statutory rights carve-out",
                severity=Severity.MEDIUM,
                rationale="A severance release conditioned on a general waiver of all claims, without carve-outs preserving the right to file an EEOC/agency charge, whistleblower protections, or unemployment benefits, can be overbroad and, for age-related waivers, non-compliant with the OWBPA's specific requirements.",
                anchors=[r"\bsever\w*\b"],
                nearby=[r"\breleas\w*\b.{0,60}\b(?:any\s+and\s+)?all\s+claims\b", r"\bwaive[sd]?\b.{0,60}\bclaims\b"],
                window=300,
                aliases=["severance_release_overbroad", "missing_release_carveout"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bsever\w*\b", r"\breleas\w*\b.{0,60}\bclaims\b"],
                protective_patterns=[
                    r"\bnothing\s+in\s+this\s+(?:releas\w*|agreement)\b(?:[^.]|\.(?=\d)){0,150}\b(?:right\s+to\s+file|EEOC|agency\s+charge|whistleblow\w*)\b",
                    r"\bright\s+to\s+file\s+a\s+charge\b",
                ],
            ),
            Rule(
                rule_id="M_EMPLOY_NONSOLICIT_EMPLOYEE_01",
                rule_name="employment_no_hire_covenant",
                title="No-solicit / no-hire covenant for employees",
                severity=Severity.MEDIUM,
                rationale="A covenant not to solicit or hire the other party's employees can restrict future hiring even when the restriction isn't labeled 'non-compete' or 'non-solicit', and enforceability varies by state.",
                anchors=[r"\bsolicit\w*\b|\bhire\b|\binduce\w*\b"],
                nearby=[r"\bemployees?\b", r"\bpersonnel\b", r"\bstaff\b"],
                window=250,
                aliases=["no_hire_covenant", "employee_solicitation_restriction"],
            ),

            # -- Franchise / distribution agreements --
            Rule(
                rule_id="H_FRANCHISE_TERMINATION_CAUSE_01",
                rule_name="franchise_termination_no_cure",
                title="Franchisor termination right lacks cure period",
                severity=Severity.HIGH,
                rationale="A franchisor right to terminate immediately or at its sole discretion, without a defined cure period for the franchisee, can end the relationship (and the franchisee's investment) with little warning.",
                anchors=[r"\bfranchisor\b"],
                nearby=[
                    r"\bterminate\b.{0,80}\b(?:sole\s+discretion|without\s+cause|immediately\s+upon\s+notice)\b",
                    r"\bwithout\s+(?:an\s+)?opportunity\s+to\s+cure\b",
                ],
                window=350,
                aliases=["franchise_termination_at_will", "no_cure_period"],
            ),
            Rule(
                rule_id="M_FRANCHISE_TERRITORY_01",
                rule_name="franchise_territory_not_exclusive",
                title="No exclusive or protected territory",
                severity=Severity.MEDIUM,
                rationale="Without an exclusive or protected territory, the franchisor may license or open competing locations near the franchisee, diluting the value of the franchisee's investment.",
                anchors=[r"\bterritor(?:y|ies|ial)\b"],
                nearby=[r"\bfranchisor\b", r"\bfranchisee\b"],
                window=250,
                aliases=["no_protected_territory", "territory_not_exclusive"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bterritor(?:y|ies|ial)\b", r"\bfranchis\w*\b"],
                protective_patterns=[r"\bexclusive\s+territor\w*\b", r"\bprotected\s+territor\w*\b"],
            ),

            # -- M&A / partnership & operating agreements --
            Rule(
                rule_id="H_MA_INDEM_BASKET_MISSING_01",
                rule_name="ma_indemnification_basket_missing",
                title="Indemnification for reps and warranties lacks a basket/threshold",
                severity=Severity.HIGH,
                rationale="Indemnification tied to representations and warranties with no basket, deductible, or minimum-claim threshold means the buyer can pursue the seller for even trivial breaches, and the seller bears first-dollar risk on every claim.",
                anchors=[r"\bindemnif\w*\b"],
                nearby=[r"\brepresentations?\s+and\s+warrant\w*\b", r"\bbreach\s+of\s+(?:any\s+)?representation\b"],
                window=350,
                aliases=["missing_indemnification_basket", "no_deductible_indemnity"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bindemnif\w*\b", r"\brepresentations?\s+and\s+warrant\w*\b"],
                protective_patterns=[
                    r"\bbasket\b",
                    r"\bdeductible\b",
                    r"\bthreshold\b(?:[^.]|\.(?=\d)){0,60}\bindemnif\w*\b",
                    r"\bde\s+minimis\b(?:[^.]|\.(?=\d)){0,80}\bindemnif\w*\b",
                ],
            ),
            Rule(
                rule_id="M_MA_EARNOUT_DISCRETION_01",
                rule_name="ma_earnout_discretion",
                title="Earn-out payment subject to buyer's discretion",
                severity=Severity.MEDIUM,
                rationale="An earn-out whose triggering metrics or payment determination is left to the buyer's discretion, rather than objective and auditable criteria, gives the buyer effective control over whether the seller is ever paid.",
                anchors=[r"\bearn-?out\b"],
                nearby=[r"\bbuyer'?s?\s+(?:sole\s+)?discretion\b", r"\bsole\s+discretion\b"],
                window=300,
                aliases=["earnout_buyer_discretion", "subjective_earnout_metrics"],
            ),
            Rule(
                rule_id="M_PARTNERSHIP_DEADLOCK_01",
                rule_name="partnership_deadlock_missing",
                title="No deadlock-resolution mechanism",
                severity=Severity.MEDIUM,
                rationale="Without a defined deadlock mechanism (buy-sell/shotgun, mediation, or a tie-breaking vote), a disagreement between equally-held owners can freeze company decisions indefinitely with no contractual path to resolution.",
                anchors=[r"\b50\s*[/-]\s*50\b|\bequally\s+held\b|\bequal\s+(?:ownership|voting)\b"],
                nearby=[r"\bmember\w*\b|\bpartner\w*\b|\bshareholder\w*\b"],
                window=250,
                aliases=["no_deadlock_mechanism", "missing_buysell_provision"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b50\s*[/-]\s*50\b|\bequally\s+held\b|\bequal\s+(?:ownership|voting)\b"],
                protective_patterns=[
                    r"\bdeadlock\b(?:[^.]|\.(?=\d)){0,150}\b(?:buy-?sell|shotgun|mediation|arbitration|third\s+(?:member|director|arbitrator))\b",
                ],
            ),
            Rule(
                rule_id="M_PARTNERSHIP_CAPITAL_CALL_01",
                rule_name="partnership_capital_call_dilution",
                title="Capital call default triggers dilution penalty",
                severity=Severity.MEDIUM,
                rationale="Mandatory capital calls with a dilution or forfeiture penalty for a partner who cannot contribute can permanently and disproportionately reduce that partner's ownership stake.",
                anchors=[r"\bcapital\s+call\b"],
                nearby=[r"\bdilut\w*\b", r"\bdefault\b", r"\bpenalt(?:y|ies)\b", r"\bforfeit\w*\b"],
                window=300,
                aliases=["capital_call_dilution_penalty", "capital_call_default"],
            ),

            # -- Settlement agreements --
            Rule(
                rule_id="H_SETTLEMENT_RELEASE_OVERBROAD_01",
                rule_name="settlement_release_overbroad",
                title="Release sweeps in unknown/unanticipated claims",
                severity=Severity.HIGH,
                rationale="A release covering all claims 'known and unknown' can waive future claims the releasing party doesn't yet know about, so the scope should be confirmed against what was actually negotiated and disclosed.",
                pattern=r"\b(?:any\s+and\s+all|all)\s+claims\b.{0,120}\b(?:known\s+(?:and|or)\s+unknown|whether\s+(?:now\s+)?known\s+or\s+unknown|unknown\s+and\s+unanticipated)\b",
                aliases=["overbroad_release", "unknown_claims_release"],
            ),
            Rule(
                rule_id="M_SETTLEMENT_LIQUIDATED_DAMAGES_01",
                rule_name="settlement_liquidated_damages",
                title="Liquidated damages for breach of settlement",
                severity=Severity.MEDIUM,
                rationale="A liquidated damages clause stacked on top of a settlement agreement can create an outsized penalty for a minor or technical breach; confirm the amount bears a reasonable relationship to actual anticipated harm.",
                anchors=[r"\bliquidated\s+damages\b"],
                nearby=[r"\bsettlement\b", r"\bbreach\s+of\s+this\s+(?:agreement|settlement)\b", r"\bin\s+addition\s+to\b"],
                window=300,
                aliases=["settlement_liquidated_damages_penalty"],
            ),

            # -- Construction contracts --
            Rule(
                rule_id="H_CONSTR_PAY_IF_PAID_01",
                rule_name="construction_pay_if_paid",
                title="Pay-if-paid clause shifts owner non-payment risk to subcontractor",
                severity=Severity.HIGH,
                rationale="A pay-if-paid clause makes the owner's payment to the general contractor a condition precedent to the subcontractor being paid at all, shifting the owner's credit risk onto the subcontractor.",
                pattern=r"\bpay-?if-?paid\b|\bcondition\s+precedent\b.{0,100}\bpayment\s+(?:by|from)\s+(?:the\s+)?owner\b",
                aliases=["pay_if_paid_clause", "condition_precedent_payment"],
            ),
            Rule(
                rule_id="M_CONSTR_LIEN_WAIVER_01",
                rule_name="construction_lien_waiver_premature",
                title="Lien waiver required before payment is received",
                severity=Severity.MEDIUM,
                rationale="Signing a lien waiver before payment is actually received gives up the statutory lien remedy without any assurance the payment will follow.",
                anchors=[r"\blien\s+waiver\b"],
                nearby=[r"\bprior\s+to\s+payment\b", r"\bbefore\s+payment\b", r"\bin\s+advance\s+of\s+payment\b"],
                window=250,
                aliases=["premature_lien_waiver", "lien_waiver_before_payment"],
            ),
            Rule(
                rule_id="M_CONSTR_RETAINAGE_01",
                rule_name="construction_retainage_release_missing",
                title="Retainage release conditions not specified",
                severity=Severity.MEDIUM,
                rationale="Retainage withheld from progress payments without a clear trigger for release (e.g. substantial completion) can leave a significant percentage of earned payment held indefinitely.",
                anchors=[r"\bretainage\b"],
                nearby=[r"\bwithhold\w*\b", r"\bpercent\b|%"],
                window=250,
                aliases=["retainage_release_missing", "retainage_terms_unclear"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bretainage\b|\bretention\b.{0,40}\bpercent\b"],
                protective_patterns=[
                    r"\bretainage\b(?:[^.]|\.(?=\d)){0,150}\breleas\w*\b(?:[^.]|\.(?=\d)){0,80}\b(?:substantial\s+completion|final\s+completion|final\s+payment)\b",
                    r"\breleas\w*\b(?:[^.]|\.(?=\d)){0,80}\bretainage\b",
                ],
            ),

            # --- v7.0: broad small/midsize law firm coverage expansion ---
            # Real estate purchase & sale, insurance policies/COI, lending/
            # financial services, government contracts, healthcare, IP
            # licensing, plus deeper franchise/settlement/employment/
            # construction coverage. Same messy-document-tolerant regex
            # discipline as v6.0 (\s+ not literal spaces, bounded DOTALL
            # windows, anchors+nearby proximity matching).

            # -- Real estate purchase & sale --
            Rule(
                rule_id="H_REALESTATE_TITLE_DEFECT_01",
                rule_name="realestate_title_defect_no_cure",
                title="No cure or termination right for title/survey defects",
                severity=Severity.MEDIUM,
                rationale="Without a defined right to object to title or survey defects and either require a cure or terminate, the buyer can be forced to close subject to encumbrances discovered during due diligence.",
                anchors=[r"\btitle\s+defect\b|\bsurvey\s+defect\b|\bencumbrance\b"],
                nearby=[r"\bno\s+right\s+to\s+(?:object|terminate)\b", r"\bwithout\s+(?:the\s+)?(?:right|ability)\s+to\s+cure\b"],
                window=300,
                aliases=["title_defect_no_remedy", "survey_objection_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\btitle\b.{0,60}\b(?:defect|objection|exception)\b|\bsurvey\b.{0,60}\bdefect\b"],
                protective_patterns=[
                    r"\b(?:objection|cure)\s+period\b",
                    r"\bright\s+to\s+(?:object|terminate|cure)\b(?:[^.]|\.(?=\d)){0,100}\btitle\b",
                ],
            ),
            Rule(
                rule_id="M_REALESTATE_EARNEST_FORFEIT_01",
                rule_name="realestate_earnest_money_forfeiture",
                title="Earnest money forfeited on buyer default with no cap",
                severity=Severity.MEDIUM,
                rationale="Earnest money deposits forfeited on buyer default without a stated cap relative to the purchase price create disproportionate downside if the deal falls through.",
                anchors=[r"\bearnest\s+money\b"],
                nearby=[r"\bforfeit\w*\b", r"\bliquidated\s+damages\b", r"\bretain\w*\b.{0,20}\bdeposit\b"],
                window=300,
                aliases=["earnest_money_forfeiture", "deposit_liquidated_damages"],
            ),
            Rule(
                rule_id="H_REALESTATE_AS_IS_NO_INSPECTION_01",
                rule_name="realestate_as_is_no_inspection",
                title="'As-is' sale with no inspection contingency",
                severity=Severity.MEDIUM,
                rationale="An 'as-is' purchase with no inspection period or contingency shifts the entire risk of latent defects to the buyer with no opportunity to discover or price for them before closing.",
                anchors=[r"\bas[-\s]is\b.{0,60}\bwhere[-\s]is\b|\bas[-\s]is\b"],
                nearby=[r"\bno\s+inspection\b", r"\bwaives?\b.{0,40}\binspection\b", r"\bwithout\s+(?:any\s+)?(?:right\s+to\s+)?inspect\b"],
                window=300,
                aliases=["as_is_sale_no_inspection", "waived_inspection_contingency"],
            ),
            Rule(
                rule_id="M_REALESTATE_CLOSING_EXTENSION_SOLE_01",
                rule_name="realestate_closing_extension_unilateral",
                title="Seller unilateral right to extend closing",
                severity=Severity.MEDIUM,
                rationale="A seller's unilateral, unbounded right to extend the closing date leaves the buyer unable to plan financing, occupancy, or a competing purchase with any certainty.",
                anchors=[r"\bextend\w*\b.{0,40}\bclosing\b"],
                nearby=[r"\bsole\s+discretion\b", r"\bat\s+seller'?s?\s+option\b", r"\bwithout\s+(?:buyer'?s?\s+)?consent\b"],
                window=300,
                aliases=["unilateral_closing_extension", "seller_sole_discretion_closing"],
            ),
            Rule(
                rule_id="M_REALESTATE_EASEMENT_UNDISCLOSED_01",
                rule_name="realestate_easement_no_warranty",
                title="No warranty against undisclosed easements/encumbrances",
                severity=Severity.MEDIUM,
                rationale="Conveying title without a warranty against undisclosed easements, liens, or encumbrances leaves the buyer with no recourse if a defect surfaces after closing.",
                anchors=[r"\beasement\b|\brestrictive\s+covenant\b|\b(?:title|real\s+property)\b.{0,40}\bencumbrance\b|\bencumbrance\b.{0,40}\b(?:title|real\s+property)\b"],
                nearby=[r"\bsubject\s+to\b", r"\bwithout\s+warrant\w*\b", r"\bas\s+of\s+record\b"],
                window=300,
                aliases=["undisclosed_easement_risk", "no_title_warranty"],
            ),
            Rule(
                rule_id="M_REALESTATE_PRORATION_UNDEFINED_01",
                rule_name="realestate_proration_method_missing",
                title="Tax/utility proration method not specified",
                severity=Severity.LOW,
                rationale="Without a defined proration method and date for property taxes, utilities, and assessments, closing statement disputes and post-closing reconciliation costs are common.",
                pattern=r"\bprorat\w*\b[^.]{0,60}\b(?:to\s+be\s+determined|TBD|to\s+be\s+agreed)\b",
                aliases=["proration_method_undefined", "closing_proration_ambiguous"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bprorat\w*\b", r"\btax\w*\b|\butilit\w*\b"],
                protective_patterns=[r"\bprorat\w*\b(?:[^.]|\.(?=\d)){0,100}\b(?:closing\s+date|as\s+of\s+the\s+date)\b"],
            ),
            Rule(
                rule_id="H_REALESTATE_SELLER_FINANCING_BALLOON_01",
                rule_name="realestate_seller_financing_balloon",
                title="Seller-financed balloon payment with acceleration, no cure",
                severity=Severity.MEDIUM,
                rationale="A seller-financed note with a balloon payment that accelerates the entire remaining balance upon a single missed payment, with no stated cure period, can trigger foreclosure or forfeiture from a minor timing lapse.",
                anchors=[r"\bballoon\s+payment\b"],
                nearby=[r"\baccelerat\w*\b", r"\bimmediately\s+due\s+and\s+payable\b", r"\bwithout\s+(?:notice|cure)\b"],
                window=300,
                aliases=["seller_financing_balloon_acceleration", "no_cure_balloon_default"],
            ),

            # -- Insurance policies / certificates of insurance --
            Rule(
                rule_id="H_INSURANCE_CLAIMS_MADE_GAP_01",
                rule_name="insurance_claims_made_no_tail",
                title="Claims-made policy with no tail coverage requirement",
                severity=Severity.MEDIUM,
                rationale="A claims-made insurance policy with no requirement to maintain tail (extended reporting period) coverage after termination leaves claims arising from the engagement but reported later completely uninsured.",
                anchors=[r"\bclaims[-\s]made\b"],
                nearby=[r"\bno\s+(?:requirement|obligation)\b.{0,40}\btail\b", r"\bwithout\s+(?:extended\s+reporting|tail)\b"],
                window=300,
                aliases=["claims_made_no_tail_coverage", "extended_reporting_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bclaims[-\s]made\b"],
                protective_patterns=[r"\btail\b.{0,60}\bcoverage\b|\bextended\s+reporting\s+period\b"],
            ),
            Rule(
                rule_id="M_INSURANCE_SUBROGATION_WAIVER_MISSING_01",
                rule_name="insurance_subrogation_waiver_missing",
                title="No waiver of subrogation required",
                severity=Severity.LOW,
                rationale="Without a required waiver of subrogation, a party's own insurer can pursue the other contracting party for losses the insurer already paid, defeating the practical benefit of carrying insurance in the first place.",
                anchors=[r"\binsurance\b|\binsurer\b"],
                nearby=[r"\bretains?\s+(?:all\s+)?rights?\s+of\s+subrogation\b", r"\bno\s+waiver\s+of\s+subrogation\b", r"\bnot\s+waive\w*\b.{0,30}\bsubrogation\b"],
                window=250,
                aliases=["subrogation_waiver_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(?:commercial\s+general\s+liability|general\s+liability|property\s+insurance|workers[’']?\s+compensation\s+insurance)\b"],
                protective_patterns=[r"\bwaiv\w*\b.{0,60}\bsubrogation\b"],
            ),
            Rule(
                rule_id="M_INSURANCE_ADDITIONAL_INSURED_MISSING_01",
                rule_name="insurance_additional_insured_missing",
                title="No additional insured endorsement required",
                severity=Severity.LOW,
                rationale="Without a required additional insured endorsement, the counterparty's own liability coverage does not extend to claims arising from the other party's operations, leaving a coverage gap on shared risk.",
                anchors=[r"\binsurance\b"],
                nearby=[r"\bnot\s+(?:be\s+)?(?:named|added)\s+as\s+(?:an\s+)?additional\s+insured\b", r"\bno\s+additional\s+insured\b"],
                window=250,
                aliases=["additional_insured_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(?:commercial\s+general\s+liability|general\s+liability|property\s+insurance|workers[’']?\s+compensation\s+insurance)\b"],
                protective_patterns=[r"\badditional\s+insured\b"],
            ),
            Rule(
                rule_id="H_INSURANCE_SELF_INSURANCE_UNCAPPED_01",
                rule_name="insurance_self_insurance_uncapped",
                title="Self-insurance permitted with no minimum net worth or cap",
                severity=Severity.MEDIUM,
                rationale="Permitting a counterparty to self-insure with no minimum net worth requirement or dollar cap means the financial backstop insurance is meant to provide may not actually exist if a claim arises.",
                anchors=[r"\bself[-\s]insur\w*\b"],
                nearby=[r"\bpermitted\b", r"\bmay\s+self[-\s]insure\b"],
                window=250,
                aliases=["uncapped_self_insurance", "self_insurance_no_minimum"],
            ),
            Rule(
                rule_id="M_INSURANCE_NOTICE_CANCELLATION_SHORT_01",
                rule_name="insurance_cancellation_notice_missing",
                title="No notice of cancellation to counterparty required",
                severity=Severity.MEDIUM,
                rationale="Without a requirement that the insurer or insured notify the counterparty before a policy is cancelled or materially changed, coverage can lapse without the relying party ever finding out until a claim is denied.",
                anchors=[r"\bcancel\w*\b.{0,40}\bpolicy\b|\bpolicy\b.{0,40}\bcancel\w*\b"],
                nearby=[r"\bwithout\s+notice\b", r"\bno\s+notice\b"],
                window=300,
                aliases=["cancellation_notice_missing", "policy_lapse_no_notice"],
            ),
            Rule(
                rule_id="M_INSURANCE_DEDUCTIBLE_UNCAPPED_01",
                rule_name="insurance_deductible_uncapped",
                title="Deductible or retention amount uncapped or unspecified",
                severity=Severity.LOW,
                rationale="An insurance requirement with no stated maximum deductible or self-insured retention means a policy could technically satisfy the coverage requirement while leaving a very large first-dollar exposure to the insured.",
                anchors=[r"\bdeductible\b|\bself[-\s]insured\s+retention\b"],
                nearby=[r"\bno\s+(?:maximum|limit)\b", r"\bany\s+amount\b"],
                window=250,
                aliases=["uncapped_deductible", "retention_amount_unspecified"],
            ),

            # -- Lending / financial services --
            Rule(
                rule_id="M_LENDING_TILA_DISCLOSURE_MISSING_01",
                rule_name="lending_tila_disclosure_missing",
                title="Consumer lending disclosure (TILA/Reg Z) not referenced",
                severity=Severity.MEDIUM,
                rationale="A consumer-facing loan with no reference to Truth in Lending Act / Regulation Z disclosures (APR, finance charge, payment schedule) may be missing a legally required disclosure framework.",
                anchors=[r"\bconsumer\s+loan\b|\bpersonal\s+loan\b"],
                nearby=[r"\bno\s+(?:TILA|Truth[-\s]in[-\s]Lending|Regulation\s+Z)\s+disclosure\b", r"\bwithout\s+(?:a\s+)?(?:TILA|Truth\s+in\s+Lending)\s+disclosure\b"],
                window=300,
                aliases=["tila_disclosure_missing", "reg_z_reference_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bconsumer\s+loan\b|\bpersonal\s+loan\b"],
                protective_patterns=[r"\bTruth\s+in\s+Lending\b|\bTILA\b|\bRegulation\s+Z\b"],
            ),
            Rule(
                rule_id="H_LENDING_BALLOON_PAYMENT_01",
                rule_name="lending_balloon_payment_no_refi_right",
                title="Balloon payment due with no refinancing right",
                severity=Severity.MEDIUM,
                rationale="A loan structured with a large balloon payment at maturity and no stated right to refinance or extend leaves the borrower exposed to being unable to pay off the balance if refinancing isn't available at that time.",
                anchors=[r"\bballoon\s+payment\b"],
                nearby=[r"\bmatur\w*\b", r"\bdue\s+in\s+full\b"],
                window=300,
                aliases=["balloon_payment_no_refinance_right"],
            ),
            Rule(
                rule_id="M_LENDING_CROSS_COLLATERAL_01",
                rule_name="lending_cross_collateralization",
                title="Cross-collateralization across unrelated loans",
                severity=Severity.LOW,
                rationale="Cross-collateralization clauses let the lender apply collateral pledged for one loan to secure a completely separate loan, so a default on an unrelated obligation can put unrelated collateral at risk.",
                anchors=[r"\bcross[-\s]collateral\w*\b"],
                nearby=[r"\ball\s+(?:other\s+)?(?:loans|obligations|indebtedness)\b"],
                window=300,
                aliases=["cross_collateralization_clause"],
            ),
            Rule(
                rule_id="H_LENDING_DEFAULT_INTEREST_PUNITIVE_01",
                rule_name="lending_default_interest_punitive",
                title="Default interest rate increase with no stated cap",
                severity=Severity.MEDIUM,
                rationale="A default interest rate that spikes upon any default with no stated maximum can dramatically increase the cost of a loan from a single missed or late payment, well beyond ordinary late fees.",
                anchors=[r"\bdefault\s+rate\b|\bdefault\s+interest\b"],
                nearby=[r"\bincrease\w*\b", r"\badditional\s+\d+(?:\.\d+)?\s*%"],
                window=300,
                aliases=["punitive_default_interest_rate"],
            ),
            Rule(
                rule_id="M_LENDING_FINANCIAL_COVENANT_VAGUE_01",
                rule_name="lending_financial_covenant_vague",
                title="Financial covenants undefined or lack a cure period",
                severity=Severity.MEDIUM,
                rationale="Financial covenants (e.g. debt service coverage, leverage ratios) stated without a precise calculation method or a cure period before default is declared can trigger technical defaults over routine fluctuations.",
                anchors=[r"\bfinancial\s+covenant\w*\b|\bdebt\s+service\s+coverage\b|\bleverage\s+ratio\b"],
                nearby=[r"\bwithout\s+(?:a\s+)?cure\b", r"\bimmediately\s+(?:in\s+)?default\b"],
                window=300,
                aliases=["vague_financial_covenants", "no_covenant_cure_period"],
            ),
            Rule(
                rule_id="H_LENDING_PERSONAL_PROPERTY_LIEN_ALL_ASSETS_01",
                rule_name="lending_blanket_lien_all_assets",
                title="Blanket lien on all personal/business assets, no carve-outs",
                severity=Severity.HIGH,
                rationale="A security interest in 'all assets, now owned or hereafter acquired' with no carve-outs for exempt or unrelated property gives the lender collateral rights far broader than the loan itself may warrant.",
                anchors=[r"\ball\s+assets\b|\ball\s+personal\s+property\b"],
                nearby=[r"\bnow\s+owned\s+or\s+hereafter\s+acquired\b", r"\bsecurity\s+interest\b"],
                window=300,
                aliases=["blanket_lien_all_assets", "uncarved_security_interest"],
            ),
            Rule(
                rule_id="M_LENDING_ACH_AUTODEBIT_UNLIMITED_01",
                rule_name="lending_ach_autodebit_unlimited",
                title="Unlimited ACH auto-debit authorization",
                severity=Severity.MEDIUM,
                rationale="An open-ended authorization for the lender to auto-debit a bank account for 'any amount owed' at any time, without a defined schedule or amount, creates cash-flow risk and disputes over unauthorized debits.",
                anchors=[r"\bACH\b|\bautomatic(?:ally)?\s+debit\b"],
                nearby=[r"\bany\s+amount\b", r"\bwithout\s+(?:further\s+)?authorization\b"],
                window=300,
                aliases=["unlimited_ach_authorization"],
            ),

            # -- Government contracts --
            Rule(
                rule_id="H_GOVCON_TERMINATION_CONVENIENCE_NO_COMP_01",
                rule_name="govcon_termination_convenience_no_compensation",
                title="Government termination for convenience without adequate settlement terms",
                severity=Severity.LOW,
                rationale="A termination-for-convenience clause with no defined settlement methodology (costs incurred, reasonable profit on completed work) can leave a contractor unable to recover legitimate costs when the government ends the contract early.",
                anchors=[r"\bgovernment\b.{0,80}\btermination\s+for\s+convenience\b|\btermination\s+for\s+convenience\b.{0,80}\bgovernment\b"],
                nearby=[r"\bno\s+(?:right\s+to\s+)?(?:compensation|settlement)\b", r"\bwithout\s+(?:any\s+)?(?:payment|compensation)\b"],
                window=300,
                aliases=["govcon_termination_no_settlement"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bgovernment\b.{0,80}\btermination\s+for\s+convenience\b|\btermination\s+for\s+convenience\b.{0,80}\bgovernment\b"],
                protective_patterns=[r"\bsettlement\s+(?:proposal|costs)\b|\breasonable\s+profit\b"],
            ),
            Rule(
                rule_id="M_GOVCON_FLOWDOWN_MISSING_01",
                rule_name="govcon_flowdown_clauses_missing",
                title="Required FAR flow-down clauses not incorporated",
                severity=Severity.MEDIUM,
                rationale="A government subcontract that references prime contract compliance but doesn't actually incorporate the required FAR/DFARS flow-down clauses can leave the subcontractor out of compliance with obligations it never agreed to in writing.",
                anchors=[r"\bprime\s+contract\b|\bgovernment\s+contract\b"],
                nearby=[r"\bno\s+FAR\b", r"\bwithout\s+incorporat\w*\b.{0,40}\bFAR\b", r"\bnot\s+incorporat\w*\b.{0,40}\b(?:FAR|flow[-\s]down)\b"],
                window=300,
                aliases=["far_flowdown_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bprime\s+contract\b|\bgovernment\s+contract\b"],
                protective_patterns=[r"\bFAR\b.{0,60}\bincorporat\w*\b|\bincorporat\w*\b.{0,60}\bFAR\b|\bflow[-\s]down\s+clauses?\b"],
            ),
            Rule(
                rule_id="M_GOVCON_DCAA_AUDIT_UNLIMITED_01",
                rule_name="govcon_audit_rights_unlimited",
                title="Government audit rights with no time limit",
                severity=Severity.MEDIUM,
                rationale="Audit rights (e.g. DCAA-style) with no stated time limit after contract completion can require a contractor to retain records and remain subject to audit indefinitely, well beyond typical statutory retention periods.",
                anchors=[r"\b(?:DCAA|government|federal)\b.{0,60}\baudit\b|\baudit\b.{0,60}\b(?:DCAA|government|federal)\b"],
                nearby=[r"\bat\s+any\s+time\b", r"\bno\s+(?:time\s+)?limit\b", r"\bindefinitely\b"],
                window=300,
                aliases=["unlimited_audit_period"],
            ),
            Rule(
                rule_id="M_GOVCON_SMALL_BUSINESS_SUBK_PLAN_MISSING_01",
                rule_name="govcon_small_business_subcontracting_plan_missing",
                title="Small business subcontracting plan referenced but not attached",
                severity=Severity.LOW,
                rationale="A government contract requiring a small business subcontracting plan that isn't actually attached or defined leaves subcontracting goals and compliance obligations unclear, risking a compliance finding.",
                pattern=r"\bsmall\s+business\s+subcontracting\s+plan\b[^.]{0,60}\b(?:not\s+attached|to\s+be\s+provided|forthcoming)\b",
                aliases=["subcontracting_plan_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bsmall\s+business\s+subcontracting\b"],
                protective_patterns=[r"\bsubcontracting\s+plan\b.{0,60}\battached\b|\bexhibit\b.{0,60}\bsubcontracting\s+plan\b"],
            ),
            Rule(
                rule_id="M_GOVCON_CHANGES_CLAUSE_UNILATERAL_01",
                rule_name="govcon_changes_clause_no_equitable_adjustment",
                title="Unilateral changes clause with no equitable adjustment right",
                severity=Severity.MEDIUM,
                rationale="A changes clause letting the government (or prime) unilaterally modify scope without a corresponding right to an equitable price/schedule adjustment can force a contractor to absorb the cost of expanded work.",
                anchors=[r"\bchanges\s+clause\b|\bunilateral\s+change\b"],
                nearby=[r"\bwithout\s+(?:an?\s+)?(?:equitable\s+)?adjustment\b", r"\bno\s+(?:right\s+to\s+)?(?:price|schedule)\s+adjustment\b"],
                window=300,
                aliases=["no_equitable_adjustment_right"],
            ),

            # -- Healthcare --
            Rule(
                rule_id="H_HEALTHCARE_STARK_KICKBACK_RISK_01",
                rule_name="healthcare_referral_compensation_risk",
                title="Compensation tied to referral volume (Stark Law / Anti-Kickback risk)",
                severity=Severity.CRITICAL,
                rationale="Compensation arrangements tied to the volume or value of referrals between healthcare providers implicate the Stark Law and Anti-Kickback Statute directly -- both carry civil penalties, program exclusion, and potential criminal liability, regardless of the parties' intent.",
                anchors=[r"\breferral\w*\b"],
                nearby=[r"\bcompensation\b.{0,40}\bvolume\b", r"\bbased\s+on\b.{0,40}\breferrals\b", r"\bper\s+referral\b"],
                window=300,
                aliases=["stark_law_risk", "anti_kickback_risk", "referral_based_compensation"],
            ),
            Rule(
                rule_id="M_HEALTHCARE_CREDENTIALING_DELAY_01",
                rule_name="healthcare_credentialing_timeline_missing",
                title="No defined credentialing timeline; provider unpaid until credentialed",
                severity=Severity.LOW,
                rationale="A healthcare services agreement conditioning payment on credentialing with no stated timeline can leave a provider delivering services for months without compensation while credentialing is pending.",
                anchors=[r"\b(?:provider|physician|practitioner)\b.{0,60}\bcredential\w*\b|\bcredential\w*\b.{0,60}\b(?:provider|physician|practitioner)\b"],
                nearby=[r"\bno\s+(?:payment|compensation)\s+until\b", r"\bcondition\w*\s+(?:upon|on)\b.{0,20}\bcredential\w*\b"],
                window=300,
                aliases=["credentialing_delay_no_pay"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(?:provider|physician|practitioner)\b.{0,60}\bcredential\w*\b|\bcredential\w*\b.{0,60}\b(?:provider|physician|practitioner)\b"],
                protective_patterns=[r"\bcredential\w*\b(?:[^.]|\.(?=\d)){0,100}\b(?:\d+\s+days?|\d+\s+business\s+days?)\b"],
            ),
            Rule(
                rule_id="H_HEALTHCARE_EXCLUSIVE_DEALING_01",
                rule_name="healthcare_exclusive_dealing_no_carveout",
                title="Exclusive dealing arrangement with no carve-out",
                severity=Severity.MEDIUM,
                rationale="An exclusive dealing requirement between a healthcare provider and a facility or payor, with no carve-out for emergency care, patient choice, or existing relationships, can restrict a provider's practice far more broadly than clinically necessary.",
                anchors=[r"\bexclusiv(?:e|ely)\b"],
                nearby=[r"\bprovide\s+services\s+(?:solely|only)\s+(?:to|for)\b", r"\bshall\s+not\s+provide\s+services\s+to\s+any\s+other\b"],
                window=300,
                aliases=["healthcare_exclusivity_no_carveout"],
            ),
            Rule(
                rule_id="M_HEALTHCARE_TERMINATION_WITHOUT_CAUSE_SHORT_01",
                rule_name="healthcare_short_termination_notice",
                title="Short unilateral termination notice for healthcare services",
                severity=Severity.MEDIUM,
                rationale="A short (e.g. under 30 days) unilateral termination-without-cause right in a healthcare services agreement can disrupt patient continuity of care and leave a provider unable to arrange alternative coverage in time.",
                anchors=[r"\bterminat\w*\b.{0,40}\bwithout\s+cause\b"],
                nearby=[r"\b(?:[1-9]|1[0-4])\s+days?\b|\bimmediately\b"],
                window=300,
                aliases=["healthcare_short_notice_termination"],
            ),
            Rule(
                rule_id="M_HEALTHCARE_LICENSURE_REP_MISSING_01",
                rule_name="healthcare_licensure_exclusion_rep_missing",
                title="No representation of continued licensure / exclusion screening",
                severity=Severity.MEDIUM,
                rationale="Without an ongoing representation that a provider remains licensed and is not excluded from federal healthcare programs (OIG/SAM exclusion lists), a facility has no contractual basis to act quickly if a provider's status changes mid-engagement.",
                anchors=[r"\blicens\w*\b"],
                nearby=[r"\bno\s+representation\b.{0,40}\blicens\w*\b", r"\bwithout\s+(?:any\s+)?representation\b.{0,40}\b(?:licens\w*|exclu\w*)\b"],
                window=300,
                aliases=["licensure_representation_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bhealth\s*care\s+provider\b|\blicensed\s+(?:physician|professional)\b"],
                protective_patterns=[r"\brepresent\w*\b(?:[^.]|\.(?=\d)){0,100}\b(?:licens\w*|exclu\w*)\b"],
            ),
            Rule(
                rule_id="H_HEALTHCARE_PATIENT_DATA_SALE_01",
                rule_name="healthcare_patient_data_monetization",
                title="Sale or monetization of patient data beyond treatment purposes",
                severity=Severity.HIGH,
                rationale="Language permitting the sale, licensing, or other monetization of patient health information for purposes beyond treatment, payment, or healthcare operations raises direct HIPAA compliance exposure and patient trust risk.",
                anchors=[r"\bpatient\s+(?:data|information|records)\b|\bhealth\s+information\b"],
                nearby=[r"\bsell\w*\b", r"\blicense\w*\b.{0,20}\bthird\s+part\w*\b", r"\bmonetiz\w*\b"],
                window=300,
                aliases=["patient_data_sale", "phi_monetization"],
            ),

            # -- IP licensing (distinct from assignment) --
            Rule(
                rule_id="H_IPLICENSE_NO_QUALITY_CONTROL_01",
                rule_name="iplicense_trademark_no_quality_control",
                title="Trademark license lacks quality control provisions",
                severity=Severity.MEDIUM,
                rationale="A trademark license with no quality control standards or inspection rights risks being deemed a 'naked license,' which can result in the trademark owner losing enforceable rights in the mark entirely.",
                anchors=[r"\btrademark\s+license\b|\blicense\b.{0,30}\btrademark\b"],
                nearby=[r"\bno\s+quality\s+control\b|\bwithout\s+quality\s+(?:control|standards)\b"],
                window=300,
                aliases=["naked_license_risk", "trademark_no_quality_control"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\btrademark\s+license\b|\blicense\b.{0,30}\btrademark\b"],
                protective_patterns=[r"\bquality\s+(?:control|standards)\b", r"\binspect\w*\b.{0,60}\bquality\b"],
            ),
            Rule(
                rule_id="M_IPLICENSE_ROYALTY_AUDIT_MISSING_01",
                rule_name="iplicense_royalty_audit_missing",
                title="No royalty audit rights for licensor",
                severity=Severity.LOW,
                rationale="Without royalty audit rights, a licensor has no contractual mechanism to verify that reported sales or usage -- and the royalties calculated from them -- are accurate.",
                anchors=[r"\broyalt\w*\b"],
                nearby=[r"\bno\s+(?:right\s+to\s+)?audit\b", r"\bwithout\s+(?:the\s+)?(?:right\s+to\s+)?audit\b"],
                window=250,
                aliases=["royalty_audit_rights_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\broyalt\w*\b"],
                protective_patterns=[r"\baudit\b.{0,60}\broyalt\w*\b|\broyalt\w*\b.{0,60}\baudit\b"],
            ),
            Rule(
                rule_id="H_IPLICENSE_PERPETUAL_EXCLUSIVE_NO_TERMINATION_01",
                rule_name="iplicense_perpetual_exclusive_no_termination",
                title="Perpetual exclusive license with no termination right",
                severity=Severity.HIGH,
                rationale="A perpetual, exclusive license with no termination right (even for breach or non-performance) permanently locks the licensor out of its own IP with no way to recover rights if the licensee stops performing.",
                anchors=[r"\bperpetual\b.{0,60}\bexclusive\b|\bexclusive\b.{0,60}\bperpetual\b"],
                nearby=[r"\bno\s+(?:right\s+to\s+)?terminat\w*\b", r"\birrevocabl\w*\b"],
                window=300,
                aliases=["perpetual_exclusive_no_termination"],
            ),
            Rule(
                rule_id="M_IPLICENSE_SUBLICENSE_UNRESTRICTED_01",
                rule_name="iplicense_unrestricted_sublicense",
                title="Unrestricted sublicensing rights",
                severity=Severity.MEDIUM,
                rationale="A license grant that allows unrestricted sublicensing, with no consent right or flow-down of license restrictions, means the licensor loses control over who ultimately uses its IP and on what terms.",
                anchors=[r"\bsublicens\w*\b"],
                nearby=[r"\bwithout\s+(?:the\s+)?(?:licensor'?s?\s+)?consent\b", r"\bany\s+third\s+part\w*\b"],
                window=300,
                aliases=["unrestricted_sublicensing"],
            ),
            Rule(
                rule_id="H_IPLICENSE_IMPROVEMENTS_ASSIGNED_01",
                rule_name="iplicense_improvements_auto_assigned",
                title="Licensee improvements automatically assigned to licensor",
                severity=Severity.HIGH,
                rationale="A clause automatically assigning any improvements, modifications, or derivative works the licensee creates back to the licensor -- with no compensation or license-back -- can capture the licensee's own independent innovation.",
                anchors=[r"\bimprovements?\b|\bmodifications?\b|\bderivative\s+works?\b"],
                nearby=[r"\bshall\s+(?:be\s+)?(?:owned\s+by|assigned\s+to)\b.{0,30}\blicensor\b", r"\bhereby\s+assigns?\b.{0,40}\blicensor\b|\blicensor\b.{0,40}\bhereby\s+assigns?\b"],
                window=300,
                aliases=["improvements_assigned_to_licensor"],
            ),
            Rule(
                rule_id="M_IPLICENSE_TERMINATION_NO_WINDDOWN_01",
                rule_name="iplicense_no_winddown_period",
                title="No wind-down or sell-off period on license termination",
                severity=Severity.MEDIUM,
                rationale="Without a wind-down or sell-off period after license termination, a licensee with existing inventory, committed orders, or integrated products has no transition time to stop use in an orderly way.",
                anchors=[r"\btermination\b.{0,40}\blicense\b"],
                nearby=[r"\bimmediately\s+cease\b", r"\bno\s+(?:wind[-\s]down|sell[-\s]off)\b"],
                window=300,
                aliases=["no_license_winddown_period"],
            ),

            # -- Franchise (deeper coverage) --
            Rule(
                rule_id="H_FRANCHISE_ENCROACHMENT_01",
                rule_name="franchise_encroachment_no_protection",
                title="No protection against franchisor encroachment",
                severity=Severity.LOW,
                rationale="Without protection against the franchisor opening competing units, brands, or online/delivery channels within the franchisee's territory, the franchisor can dilute the value of the franchisee's investment from within its own network.",
                anchors=[r"\bencroach\w*\b"],
                nearby=[r"\bno\s+(?:right\s+to\s+)?(?:object|protection)\b"],
                window=300,
                aliases=["franchise_encroachment_risk"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bterritor(?:y|ies)\b", r"\bfranchisor\b"],
                protective_patterns=[r"\bencroach\w*\b.{0,100}\b(?:prohibit\w*|restrict\w*|not\s+permit\w*)\b"],
            ),
            Rule(
                rule_id="M_FRANCHISE_ROYALTY_AUDIT_ONE_SIDED_01",
                rule_name="franchise_royalty_audit_one_sided",
                title="Franchisor royalty audit rights with no reciprocal dispute mechanism",
                severity=Severity.MEDIUM,
                rationale="Broad franchisor audit rights over franchisee royalty reporting, with no corresponding right for the franchisee to dispute an audit finding or seek an independent review, creates a one-sided compliance mechanism.",
                anchors=[r"\baudit\b.{0,40}\broyalt\w*\b|\broyalt\w*\b.{0,40}\baudit\b"],
                nearby=[r"\bfranchisor'?s?\s+(?:sole\s+)?discretion\b", r"\bfinal\s+and\s+binding\b"],
                window=300,
                aliases=["franchise_audit_one_sided"],
            ),
            Rule(
                rule_id="H_FRANCHISE_PERSONAL_GUARANTY_UNCAPPED_01",
                rule_name="franchise_principal_personal_guaranty",
                title="Franchisee principal personal guaranty, uncapped",
                severity=Severity.CRITICAL,
                rationale="A personal guaranty from the franchisee's principal covering all obligations under the franchise agreement, with no stated cap, exposes the individual's personal assets to the full scope of the business's obligations.",
                anchors=[r"\bpersonally\s+guarant\w*\b", r"\bguarantor\b"],
                nearby=[r"\bfranchisee\b|\bfranchisor\b|\bfranchise\s+agreement\b|\bfranchise\s+fee\b"],
                window=300,
                aliases=["franchise_personal_guaranty"],
            ),
            Rule(
                rule_id="M_FRANCHISE_NONCOMPETE_POST_TERM_BROAD_01",
                rule_name="franchise_noncompete_overbroad",
                title="Overly broad post-termination non-compete",
                severity=Severity.MEDIUM,
                rationale="A post-termination non-compete with an unusually broad geographic radius or long duration can prevent a former franchisee from earning a living in their trained field well beyond what's needed to protect the franchisor's system.",
                anchors=[r"\bnon[-\s]?compete\b"],
                nearby=[r"\bpost[-\s]termination\b|\bafter\s+termination\b", r"\b\d{2,}\s*(?:mile|miles)\b|\b(?:two|three|five)\s+years?\b"],
                window=300,
                aliases=["franchise_noncompete_broad"],
            ),
            Rule(
                rule_id="M_FRANCHISE_TRANSFER_FEE_UNCAPPED_01",
                rule_name="franchise_transfer_fee_uncapped",
                title="Uncapped transfer/assignment fee on franchise sale",
                severity=Severity.LOW,
                rationale="A franchise transfer fee with no stated cap, charged whenever the franchisee wants to sell the business, can consume a large and unpredictable share of the sale proceeds.",
                anchors=[r"\btransfer\s+fee\b|\bassignment\s+fee\b"],
                nearby=[r"\bfranchis\w*\b"],
                window=250,
                aliases=["franchise_transfer_fee_uncapped"],
            ),

            # -- Settlement (deeper coverage) --
            Rule(
                rule_id="H_SETTLEMENT_STRUCTURED_PAYMENT_ACCELERATION_01",
                rule_name="settlement_structured_payment_acceleration",
                title="Structured settlement default accelerates full remaining balance",
                severity=Severity.MEDIUM,
                rationale="A structured settlement where a single missed payment accelerates the entire remaining balance, without a notice-and-cure period, can convert a minor timing issue into an immediate full-balance judgment.",
                anchors=[r"\bsettlement\s+payment\w*\b|\bstructured\s+settlement\b"],
                nearby=[r"\baccelerat\w*\b", r"\bentire\s+(?:remaining\s+)?balance\b"],
                window=300,
                aliases=["settlement_payment_acceleration"],
            ),
            Rule(
                rule_id="M_SETTLEMENT_TAX_CHARACTERIZATION_MISSING_01",
                rule_name="settlement_tax_characterization_missing",
                title="No tax characterization of settlement payment",
                severity=Severity.LOW,
                rationale="A settlement agreement with no stated tax characterization or allocation (e.g. wages vs. damages vs. attorneys' fees) can leave both parties exposed to unexpected tax reporting positions and IRS disputes later.",
                anchors=[r"\bsettlement\s+(?:payment|amount)\b.{0,150}\b(?:Plaintiff|Defendant|claims?|lawsuit|litigation|dispute)\b|\b(?:Plaintiff|Defendant|claims?|lawsuit|litigation|dispute)\b.{0,150}\bsettlement\s+(?:payment|amount)\b"],
                nearby=[r"\bno\s+tax\s+(?:characterization|allocation)\b", r"\bwithout\s+(?:any\s+)?tax\s+(?:characterization|allocation)\b"],
                window=300,
                aliases=["settlement_tax_allocation_missing"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bsettlement\s+(?:payment|amount)\b.{0,150}\b(?:Plaintiff|Defendant|claims?|lawsuit|litigation|dispute)\b|\b(?:Plaintiff|Defendant|claims?|lawsuit|litigation|dispute)\b.{0,150}\bsettlement\s+(?:payment|amount)\b"],
                protective_patterns=[r"\ballocat\w*\b.{0,60}\btax\b|\btax\w*\b.{0,60}\b(?:characteriz\w*|allocat\w*)\b"],
            ),
            Rule(
                rule_id="H_SETTLEMENT_MUTUAL_RELEASE_ASYMMETRIC_01",
                rule_name="settlement_release_asymmetric_despite_mutual_label",
                title="Release labeled 'mutual' but only binds one party",
                severity=Severity.HIGH,
                rationale="A release captioned as 'mutual' that, on its actual operative terms, only releases one side's claims leaves the other party still exposed to suit despite believing the dispute was fully resolved.",
                anchors=[r"\bmutual\s+release\b"],
                nearby=[r"\bReleasor\s+releases\b(?![^.]*\bReleasee\s+releases\b)"],
                window=400,
                aliases=["asymmetric_mutual_release"],
            ),
            Rule(
                rule_id="M_SETTLEMENT_NONDISPARAGEMENT_PERPETUAL_01",
                rule_name="settlement_nondisparagement_perpetual",
                title="Non-disparagement obligation with no time limit",
                severity=Severity.HIGH,
                rationale="A non-disparagement obligation in a settlement with no stated duration can create an open-ended speech restriction that outlives any legitimate need to protect the settlement's finality.",
                pattern=r"\bnon[-\s]?disparage\w*\b.{0,300}\b(?:perpetual|in\s+perpetuity|indefinite(?:ly)?|no\s+expiration)\b",
                aliases=["perpetual_nondisparagement"],
            ),
            Rule(
                rule_id="M_SETTLEMENT_ENFORCEMENT_FEE_SHIFT_01",
                rule_name="settlement_enforcement_fee_shift_one_sided",
                title="One-way attorneys' fees for settlement enforcement",
                severity=Severity.LOW,
                rationale="A one-way fee-shifting provision for enforcing the settlement (only one party can recover fees if they have to sue to enforce it) creates an asymmetric incentive and cost burden if a dispute over compliance arises.",
                anchors=[r"\benforc\w*\b.{0,40}\bsettlement\b"],
                nearby=[r"\battorneys?['']?\s+fees?\b"],
                window=300,
                aliases=["settlement_enforcement_fee_asymmetric"],
            ),

            # -- Employment (deeper coverage) --
            Rule(
                rule_id="M_EMPLOY_ARBITRATION_CLASS_WAIVER_01",
                rule_name="employment_arbitration_class_waiver",
                title="Mandatory arbitration with class/collective action waiver",
                severity=Severity.MEDIUM,
                rationale="Mandatory arbitration combined with a class/collective action waiver in an employment agreement removes both court access and the ability to join with coworkers in a shared claim, significantly limiting an employee's practical recourse.",
                pattern=r"\b(?:mandatory|binding)\s+arbitration\b.{0,250}\b(?:class|collective)\s+action\s+waiver\b|\b(?:class|collective)\s+action\s+waiver\b.{0,250}\b(?:mandatory|binding)\s+arbitration\b",
                aliases=["employment_arbitration_class_waiver"],
            ),
            Rule(
                rule_id="H_EMPLOY_COMMISSION_CLAWBACK_01",
                rule_name="employment_commission_clawback_broad",
                title="Broad commission clawback beyond returns/cancellations",
                severity=Severity.HIGH,
                rationale="A commission clawback provision that reaches beyond legitimate returns or cancellations (e.g. clawing back commissions on any account that later becomes unprofitable, or upon the employee's departure for any reason) can turn already-earned pay into an unpredictable liability.",
                anchors=[r"\bclawback\b|\bclaw[-\s]back\b"],
                nearby=[r"\bcommission\w*\b"],
                window=250,
                aliases=["commission_clawback_broad"],
            ),
            Rule(
                rule_id="M_EMPLOY_GARDEN_LEAVE_UNPAID_01",
                rule_name="employment_garden_leave_unpaid",
                title="Extended notice/garden leave period with reduced or no pay",
                severity=Severity.MEDIUM,
                rationale="A long garden leave or notice period during which the employee cannot work elsewhere, but receives reduced or no pay, effectively extends a non-compete's practical restriction without the corresponding compensation.",
                anchors=[r"\bgarden\s+leave\b|\bnotice\s+period\b"],
                nearby=[r"\bwithout\s+pay\b", r"\breduced\s+(?:pay|compensation|salary)\b"],
                window=300,
                aliases=["unpaid_garden_leave"],
            ),
            Rule(
                rule_id="H_EMPLOY_FORCED_STOCK_REPURCHASE_01",
                rule_name="employment_forced_equity_repurchase_below_value",
                title="Company may force equity repurchase below fair value",
                severity=Severity.HIGH,
                rationale="A right to force repurchase of an employee's vested equity at a formula price below fair market value (e.g. original cost, not current valuation) upon termination can strip departing employees of equity they earned.",
                anchors=[r"\brepurchase\b.{0,40}\b(?:shares?|equity|stock|units?)\b"],
                nearby=[r"\boriginal\s+(?:cost|purchase\s+price)\b", r"\bbook\s+value\b"],
                window=300,
                aliases=["below_value_equity_repurchase"],
            ),
            Rule(
                rule_id="M_EMPLOY_RELOCATION_MANDATORY_01",
                rule_name="employment_mandatory_relocation",
                title="Employer may mandate relocation with no consent or compensation",
                severity=Severity.MEDIUM,
                rationale="A clause allowing the employer to require relocation to any location at its discretion, with no relocation assistance or right to decline, can impose a significant unplanned burden on the employee's personal life.",
                anchors=[r"\bemployee\b.{0,60}\brelocat\w*\b|\brelocat\w*\b.{0,60}\bemployee\b"],
                nearby=[r"\bsole\s+discretion\b", r"\bany\s+location\b", r"\bwithout\s+(?:employee'?s?\s+)?consent\b"],
                window=300,
                aliases=["mandatory_relocation_no_compensation"],
            ),
            Rule(
                rule_id="M_EMPLOY_PTO_FORFEITURE_01",
                rule_name="employment_pto_forfeiture_on_termination",
                title="Accrued PTO forfeited on termination",
                severity=Severity.LOW,
                rationale="A clause forfeiting all accrued but unused paid time off upon termination, with no payout, may conflict with state wage laws that treat accrued PTO as earned wages in many jurisdictions.",
                anchors=[r"\bPTO\b|\bpaid\s+time\s+off\b|\baccrued\s+vacation\b"],
                nearby=[r"\bforfeit\w*\b", r"\bno\s+payout\b"],
                window=300,
                aliases=["pto_forfeiture_termination"],
            ),

            # -- M&A / partnership (deeper coverage) --
            Rule(
                rule_id="H_MA_MAC_CLAUSE_BROAD_01",
                rule_name="ma_mac_clause_overbroad",
                title="Material adverse change clause defined overly broadly",
                severity=Severity.HIGH,
                rationale="A material adverse change (MAC) clause defined broadly enough to include ordinary market or industry-wide events gives the buyer an easy escape hatch from a signed deal, undermining deal certainty for the seller.",
                anchors=[r"\bmaterial\s+adverse\s+(?:change|effect)\b"],
                nearby=[r"\bincluding\s+but\s+not\s+limited\s+to\b", r"\bany\s+(?:change|event|circumstance)\b"],
                window=300,
                aliases=["mac_clause_overbroad"],
            ),
            Rule(
                rule_id="M_MA_WORKING_CAPITAL_ADJUSTMENT_UNDEFINED_01",
                rule_name="ma_working_capital_adjustment_undefined",
                title="Working capital adjustment mechanism not clearly defined",
                severity=Severity.LOW,
                rationale="A purchase price adjustment tied to closing-date working capital, without a clearly defined calculation methodology and target, is a frequent and expensive source of post-closing disputes between buyer and seller.",
                anchors=[r"\bworking\s+capital\s+adjustment\b"],
                nearby=[r"\bto\s+be\s+determined\b|\bTBD\b|\bmutually\s+agreed\b"],
                window=300,
                aliases=["working_capital_adjustment_undefined"],
            ),
            Rule(
                rule_id="H_MA_NONCOMPETE_SELLER_INDEFINITE_01",
                rule_name="ma_seller_noncompete_indefinite",
                title="Seller non-compete with no stated duration",
                severity=Severity.MEDIUM,
                rationale="A post-sale non-compete restricting the seller with no stated end date can be found unenforceable in many states for lacking a reasonable time limit, and even if enforced, imposes an open-ended restriction disproportionate to the transaction.",
                pattern=r"\bnon[-\s]?compete\b.{0,200}\b(?:seller|selling\s+(?:shareholder|member|party))\b.{0,150}\b(?:perpetual|indefinite(?:ly)?|no\s+expiration)\b",
                aliases=["seller_noncompete_indefinite"],
            ),
            Rule(
                rule_id="M_MA_DRAG_ALONG_NO_MINIMUM_PRICE_01",
                rule_name="ma_drag_along_no_minimum_price",
                title="Drag-along right with no minimum price protection",
                severity=Severity.MEDIUM,
                rationale="A drag-along right that forces minority owners to sell alongside a majority-approved transaction, with no minimum price or valuation protection, can force a sale at an undervalued price with no recourse.",
                anchors=[r"\bdrag[-\s]along\b"],
                nearby=[r"\bno\s+minimum\s+price\b", r"\bany\s+price\b"],
                window=300,
                aliases=["drag_along_no_price_floor"],
            ),
            Rule(
                rule_id="H_MA_ESCROW_RELEASE_SOLE_DISCRETION_01",
                rule_name="ma_escrow_release_buyer_discretion",
                title="Indemnification escrow release subject to buyer's sole discretion",
                severity=Severity.HIGH,
                rationale="An indemnification escrow that releases to the seller only at the buyer's sole discretion, rather than on a fixed schedule or upon expiration of the claims period, gives the buyer unilateral control over money that is, by default, the seller's.",
                anchors=[r"\bescrow\b"],
                nearby=[r"\bbuyer'?s?\s+sole\s+discretion\b", r"\brelease\b.{0,40}\bdiscretion\b"],
                window=300,
                aliases=["escrow_release_buyer_discretion"],
            ),
            Rule(
                rule_id="M_PARTNERSHIP_FIDUCIARY_DUTY_WAIVER_01",
                rule_name="partnership_fiduciary_duty_waiver",
                title="Broad waiver of managing member/partner fiduciary duties",
                severity=Severity.LOW,
                rationale="A broad waiver of the managing member's or general partner's fiduciary duties (care, loyalty, good faith) removes a key legal protection minority owners otherwise rely on to constrain self-dealing by whoever controls the entity.",
                anchors=[r"\bfiduciary\s+dut(?:y|ies)\b"],
                nearby=[r"\bwaive[sd]?\b", r"\bno\s+fiduciary\s+dut(?:y|ies)\b", r"\bdisclaim\w*\b"],
                window=300,
                aliases=["fiduciary_duty_waiver"],
            ),

            # -- Construction (deeper coverage) --
            Rule(
                rule_id="H_CONSTR_NO_DAMAGES_FOR_DELAY_01",
                rule_name="construction_no_damages_for_delay",
                title="'No damages for delay' clause bars recovery for owner-caused delay",
                severity=Severity.MEDIUM,
                rationale="A 'no damages for delay' clause that bars a contractor from recovering costs even when the OWNER causes the delay (not just excusable third-party events) shifts an unusual amount of schedule risk onto the contractor.",
                pattern=r"\bno\s+damages?\s+for\s+delay\b",
                aliases=["no_damages_for_delay_clause"],
            ),
            Rule(
                rule_id="M_CONSTR_CHANGE_ORDER_UNILATERAL_PRICING_01",
                rule_name="construction_change_order_unilateral_pricing",
                title="Owner sets change order pricing unilaterally",
                severity=Severity.MEDIUM,
                rationale="A change order process where the owner unilaterally determines the price of extra work, with no negotiated markup schedule or dispute mechanism, leaves the contractor with no leverage to be paid fairly for expanded scope.",
                anchors=[r"\bchange\s+order\b"],
                nearby=[r"\bowner'?s?\s+sole\s+discretion\b", r"\bowner\s+shall\s+determine\b"],
                window=300,
                aliases=["change_order_unilateral_pricing"],
            ),
            Rule(
                rule_id="H_CONSTR_INDEMNITY_SOLE_NEGLIGENCE_01",
                rule_name="construction_indemnity_covers_owner_sole_negligence",
                title="Contractor indemnifies owner even for owner's sole negligence",
                severity=Severity.MEDIUM,
                rationale="An indemnification clause requiring the contractor to indemnify the owner even for claims arising from the owner's own sole negligence is void or unenforceable in many states' anti-indemnity statutes, and imposes liability the contractor never actually caused.",
                anchors=[r"\bindemnif\w+\b"],
                nearby=[r"\bsole\s+negligence\b.{0,40}\bowner\b|\bowner'?s?\s+sole\s+negligence\b"],
                window=300,
                aliases=["indemnity_sole_negligence_owner"],
            ),
            Rule(
                rule_id="M_CONSTR_WARRANTY_PERIOD_EXTENDED_01",
                rule_name="construction_warranty_period_extended",
                title="Warranty period extended well beyond standard 1-year",
                severity=Severity.MEDIUM,
                rationale="A workmanship warranty period extending well beyond the industry-standard one year, with no corresponding adjustment to price or scope, increases the contractor's long-tail liability exposure on a fixed-price job.",
                anchors=[r"\bwarrant\w*\s+period\b|\bwarrant\w*\b.{0,30}\byears?\b"],
                nearby=[r"\b(?:three|four|five|[3-9])\s*[-\s]?years?\b"],
                window=300,
                aliases=["extended_warranty_period"],
            ),

            # --- v7.1: gaps surfaced by real-document validation against the
            # 63-document SEC EDGAR corpus (tests/fixtures/real_contracts/) ---
            Rule(
                rule_id="M_LENDING_BORROWING_BASE_REDETERMINATION_01",
                rule_name="lending_borrowing_base_redetermination_sole_discretion",
                title="Lender may redetermine borrowing base in its sole discretion, no floor",
                severity=Severity.MEDIUM,
                rationale="A reserve-based/asset-based loan whose borrowing base the lender may redetermine downward in its sole discretion, with a resulting deficiency triggering mandatory prepayment and no stated floor or cure period, can force the borrower into a large, unplanned repayment with little notice.",
                anchors=[r"\bborrowing\s+base\b"],
                nearby=[r"\bsole\s+discretion\b", r"\bmandatory\s+prepay\w*\b", r"\bdeficiency\b"],
                window=350,
                aliases=["borrowing_base_redetermination_sole_discretion", "reserve_based_lending_redetermination"],
            ),
            Rule(
                rule_id="M_CONSTR_LIQUIDATED_DAMAGES_UNCAPPED_01",
                rule_name="construction_liquidated_damages_uncapped",
                title="Liquidated damages for late completion with no aggregate cap",
                severity=Severity.MEDIUM,
                rationale="A per-day liquidated damages rate for late completion with no stated aggregate maximum means the contractor's delay exposure grows without limit the longer a project runs late, rather than being bounded to a known worst case.",
                anchors=[r"\bliquidated\s+damages\b"],
                nearby=[r"\bno\s+(?:maximum|cap|limit)\b", r"\bwithout\s+(?:limitation|cap)\b", r"\buncapped\b"],
                window=300,
                aliases=["construction_ld_no_cap"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bliquidated\s+damages\b.{0,150}\b(?:substantial\s+completion|delay|per\s+day|each\s+day)\b|\b(?:substantial\s+completion|delay|per\s+day|each\s+day)\b.{0,150}\bliquidated\s+damages\b"],
                protective_patterns=[r"\bliquidated\s+damages\b(?:[^.]|\.(?=\d)){0,150}\b(?:not\s+to\s+exceed|maximum\s+(?:of|amount)|cap(?:ped)?\s+at|shall\s+not\s+exceed)\b"],
            ),
            Rule(
                rule_id="M_FRANCHISE_ADFUND_NO_ACCOUNTING_01",
                rule_name="franchise_advertising_fund_no_accounting",
                title="Advertising/marketing fund contribution with no accounting or audit rights",
                severity=Severity.LOW,
                rationale="Franchisees are required to fund an advertising or marketing fund the franchisor administers, but without a required accounting or audit right over how that fund is spent, franchisees have no way to verify their mandatory contributions are actually used for advertising rather than the franchisor's own benefit.",
                anchors=[r"\badvertising\s+fund\b|\bmarketing\s+fund\b"],
                nearby=[r"\bfranchisor\s+shall\s+administer\b", r"\bsole\s+discretion\b"],
                window=300,
                aliases=["ad_fund_no_accounting", "marketing_fund_no_audit_rights"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\badvertising\s+fund\b|\bmarketing\s+fund\b"],
                protective_patterns=[r"\b(?:accounting|audit)\b.{0,80}\bfund\b|\bfund\b.{0,80}\b(?:accounting|audit)\b"],
            ),
            Rule(
                rule_id="M_EMPLOY_MANDATORY_ARBITRATION_01",
                rule_name="employment_mandatory_arbitration",
                title="Mandatory arbitration of employment disputes",
                severity=Severity.LOW,
                rationale="A mandatory, binding arbitration requirement for employment disputes replaces court access with a private forum chosen in advance by the employer, even where no class/collective-action waiver is also present -- a narrower but still real reduction in the employee's dispute-resolution options.",
                pattern=r"\bmandatory\s+arbitration\b|\bbinding\s+arbitration\b|\bsettled\s+exclusively\s+by\s+arbitration\b|\bresolved\s+exclusively\s+by\s+arbitration\b",
                aliases=["employment_arbitration_no_waiver"],
            ),
            Rule(
                rule_id="M_GOVCON_OCI_TERMINATION_01",
                rule_name="govcon_oci_unilateral_termination",
                title="Organizational conflict of interest clause allows unilateral termination, no mitigation process",
                severity=Severity.MEDIUM,
                rationale="An organizational conflict of interest (OCI) clause that lets either party terminate the subcontract at its sole discretion upon determining an OCI exists, with no defined mitigation process, cure opportunity, or wind-down compensation, creates a termination trigger largely outside the subcontractor's control.",
                anchors=[r"\borganizational\s+conflict\s+of\s+interest\b"],
                nearby=[r"\bsole\s+discretion\b", r"\bmay\s+be\s+terminated\b|\bmay\s+terminate\b"],
                window=350,
                aliases=["oci_unilateral_termination", "organizational_conflict_of_interest_termination"],
            ),
        ]

    def analyze(self, text: str, suppression_enabled: bool = True) -> Dict:
        """
        Analyze contract text using deterministic rule engine.
        
        Neural-Symbolic Architecture: This method is the deterministic control plane.
        All risk detection happens here - LLM never participates in detection.
        
        Process:
        1. Chunk text for efficient processing
        2. Apply all rules (pattern or proximity matching)
        3. Extract clause-level anchors (start_index, end_index, exact_snippet)
        4. Deduplicate findings by (rule_id, clause_number)
        5. Apply false-positive suppression rules (if enabled)
        6. Compute overall risk from findings
        7. Return findings with ruleset version metadata
        
        Args:
            text: Contract text to analyze
            suppression_enabled: If True, apply false-positive suppression rules.
                                If False, return all findings without suppression.
                                Default: True (production behavior)
        
        Returns:
            Dict with:
            - findings: List[Finding] (with clause-level anchoring)
            - overall_risk: "high" | "medium" | "low"
            - rule_counts: Dict[str, int] by severity
            - version: str (ruleset version)
            - ruleset_version_data: Dict (full version metadata)
            - suppression_log: Dict[str, str] (audit trail of suppressions, empty if disabled)
        """
        # Normalize Unicode punctuation and (if present) literal "\n" escape
        # sequences so regex patterns match text extracted from PDFs/Word
        # documents and so _chunk_text() can find real clause boundaries.
        # See normalize_contract_text() docstring for details.
        text = normalize_contract_text(text)

        # Resolve the contract's own defined party names to vendor/customer
        # roles once per document (see party_resolver.py) so party-direction
        # classification below can use them instead of guessing from
        # generic role words alone.
        party_map = resolve_party_roles(text)

        chunks = _chunk_text(text)

        findings: List[Finding] = []
        for chunk_start, chunk in chunks:
            for rule in self.rules:
                if rule.pattern:
                    for m in _find_all(rule.pattern, chunk):
                        s, e = m.span()
                        absolute_start = chunk_start + s
                        absolute_end = chunk_start + e
                        ex = _excerpt(chunk, s, e)
                        matched_text = m.group(0)
                        # Get surrounding context (±200 chars, for display)
                        context_start = max(0, absolute_start - 200)
                        context_end = min(len(text), absolute_end + 200)
                        surrounding_context = text[context_start:context_end]
                        # Party direction uses a MUCH tighter window (±70)
                        # than the display context: a ±200 window on a real
                        # two-party contract very often pulls in an
                        # incidental mention of the OTHER party (e.g. "...
                        # written notice to Prevail" right after a
                        # Company-only right), which made a cleanly one-
                        # sided clause register as "ambiguous" (both roles
                        # present) purely from window width, not from the
                        # clause's actual grammar. The window is
                        # deliberately asymmetric: English SVO clauses state
                        # WHO holds a right immediately before the verb
                        # ("Company may terminate..."), while a same-
                        # sentence mention of the other party is usually the
                        # ADDRESSEE, further after the match ("...notice to
                        # Prevail") — so look back further than forward.
                        party_context_start = max(0, absolute_start - 120)
                        party_context_end = min(len(text), absolute_end + 20)
                        party_context = text[party_context_start:party_context_end]
                        clause_num = _extract_clause_number(text, absolute_start)
                        keywords = _extract_matched_keywords(matched_text, rule.pattern)
                        party_direction = (
                            _classify_party_direction(party_context, party_map)
                            if rule.rule_id in ONE_WAY_RULE_IDS
                            else None
                        )
                        findings.append(
                            Finding(
                                rule_id=rule.rule_id,
                                rule_name=rule.rule_name,
                                title=rule.title,
                                severity=rule.severity,
                                rationale=rule.rationale,
                                matched_excerpt=ex,
                                position=absolute_start,  # Kept for backward compatibility
                                context=surrounding_context,
                                # Clause-level anchoring (MANDATORY)
                                start_index=absolute_start,
                                end_index=absolute_end,
                                exact_snippet=matched_text,
                                clause_number=clause_num,
                                matched_keywords=keywords,
                                aliases=rule.aliases or [],
                                party_direction=party_direction,
                            )
                        )
                else:
                    assert rule.anchors and rule.nearby
                    spans = _proximity_spans(rule.anchors, rule.nearby, chunk, rule.window)
                    for pm in spans:
                        # Evidence spans, relative to `chunk`
                        s, e = pm.combined_start, pm.combined_end
                        absolute_start = chunk_start + s
                        absolute_end = chunk_start + e
                        ex = _excerpt(chunk, s, e)
                        # exact_snippet covers the FULL evidence span (anchor -> risk
                        # phrase), not just the anchor trigger word, so readers see the
                        # actual dangerous language rather than a bare keyword.
                        exact_matched = chunk[s:e]
                        anchor_text = chunk[pm.anchor_start:pm.anchor_end]
                        risk_phrase = chunk[pm.nearby_start:pm.nearby_end]
                        # Get surrounding context (±200 chars, for display)
                        context_start = max(0, absolute_start - 200)
                        context_end = min(len(text), absolute_end + 200)
                        surrounding_context = text[context_start:context_end]
                        # Party direction uses an asymmetric window — see
                        # the matching comment in the direct-pattern branch
                        # above for why (look back further than forward).
                        party_context_start = max(0, absolute_start - 120)
                        party_context_end = min(len(text), absolute_end + 20)
                        party_context = text[party_context_start:party_context_end]
                        # For proximity matches, extract keywords from context
                        context_text = chunk[max(0, s-100):min(len(chunk), e+100)]
                        clause_num = _extract_clause_number(text, absolute_start)
                        keywords = _extract_matched_keywords(context_text)
                        party_direction = (
                            _classify_party_direction(party_context, party_map)
                            if rule.rule_id in ONE_WAY_RULE_IDS
                            else None
                        )
                        findings.append(
                            Finding(
                                rule_id=rule.rule_id,
                                rule_name=rule.rule_name,
                                title=rule.title,
                                severity=rule.severity,
                                rationale=rule.rationale,
                                matched_excerpt=ex,
                                position=absolute_start,  # Kept for backward compatibility
                                context=surrounding_context,
                                # Clause-level anchoring (MANDATORY)
                                start_index=absolute_start,
                                end_index=absolute_end,
                                exact_snippet=exact_matched,
                                clause_number=clause_num,
                                matched_keywords=keywords,
                                aliases=rule.aliases or [],
                                evidence={
                                    "anchor": anchor_text,
                                    "risk_phrase": risk_phrase,
                                    "full_clause": surrounding_context,
                                },
                                party_direction=party_direction,
                            )
                        )

        # REQUIRED_SECTION rules: for any such rule that found no adverse
        # language above, run a document-level absence check instead of
        # silently producing nothing. This can never happen inside the
        # per-chunk loop above, because "the topic never appears anywhere in
        # the document" is not something a chunk-local regex match can prove.
        adverse_rule_ids_found = {f.rule_id for f in findings}
        for rule in self.rules:
            if rule.rule_class != RuleClass.REQUIRED_SECTION:
                continue
            if rule.rule_id in adverse_rule_ids_found:
                continue  # adverse language already found; that's the finding
            required_section_finding = self._check_required_section(rule, text)
            if required_section_finding is not None:
                findings.append(required_section_finding)

        # Document-wide consistency checks (conflicting values across
        # different parts of the document, missing signature blocks) — see
        # _check_cross_document_conflicts for why these can't be single
        # regex/proximity matches.
        findings.extend(self._check_cross_document_conflicts(text))

        # Party-name-aware liability cap asymmetry check — see
        # _check_liability_cap_asymmetry docstring. Skipped when
        # H_ASYMMETRIC_LIABILITY_01 already fired via the generic-word
        # anchors above; dedup below would collapse an exact duplicate
        # anyway, but this avoids the extra work.
        if "H_ASYMMETRIC_LIABILITY_01" not in {f.rule_id for f in findings}:
            findings.extend(self._check_liability_cap_asymmetry(text, party_map))

        # Deduplicate by (rule_id, clause_number) to prevent inflated counts
        # If clause_number exists, use (rule_id, clause_number) as key; otherwise use (rule_id, None)
        # Keep the "best" match: prefer longer matched_excerpt, or earliest position
        deduped: List[Finding] = []
        seen_keys: Dict[Tuple[str, Optional[str]], Finding] = {}
        
        for f in findings:
            key = (f.rule_id, f.clause_number)
            if key in seen_keys:
                # Keep the better match: longer excerpt or earlier position
                existing = seen_keys[key]
                if len(f.matched_excerpt) > len(existing.matched_excerpt) or (
                    len(f.matched_excerpt) == len(existing.matched_excerpt) and f.position < existing.position
                ):
                    seen_keys[key] = f
            else:
                seen_keys[key] = f
        
        deduped = list(seen_keys.values())

        # Sort by severity then stable by rule_id
        rank = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
        deduped.sort(key=lambda x: (rank.get(x.severity, 9), x.rule_id))

        # Phase 5: False-positive suppression layer (deterministic, explainable)
        if suppression_enabled:
            suppressed_findings, suppression_reasons = self._apply_suppression_rules(deduped, text, party_map)
            
            # Log suppressions for auditability
            if suppression_reasons:
                for finding_id, reason in suppression_reasons.items():
                    logger.info(f"SUPPRESSION: {finding_id} - {reason}")
        else:
            # Suppression disabled: use all findings without suppression
            suppressed_findings = deduped
            suppression_reasons = {}
            logger.info("Suppression disabled: all findings returned without suppression")

        # Phase 6: Contradiction detection (deterministic consistency
        # check) — see _detect_contradictions. Always runs, independent of
        # suppression_enabled: a self-contradictory title/rationale pair is
        # a report-quality defect, not a suppression decision.
        suppressed_findings, contradiction_log = self._detect_contradictions(suppressed_findings)
        if contradiction_log:
            for finding_id, reason in contradiction_log.items():
                logger.warning(f"CONTRADICTION RECONCILED: {finding_id} - {reason}")

        # Phase 7: Root-cause grouping — see _group_related_findings /
        # ROOT_CAUSE_GROUPS. Runs last, after severity/title are final, so
        # the parent finding's severity reflects any suppression downgrades
        # already applied to its members.
        suppressed_findings = self._group_related_findings(suppressed_findings)

        # Phase 8: Deterministic confidence/evidence-quality scoring — see
        # _score_confidence. Runs last so it reflects final finding_type,
        # party_direction, and related_findings (post-grouping) state.
        suppressed_findings = [replace(f, **_score_confidence(f)) for f in suppressed_findings]

        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in suppressed_findings:
            counts[f.severity.value] += 1

        overall = self._compute_overall_risk(suppressed_findings, counts)
        workflow = self._compute_workflow_decision(suppressed_findings)

        return {
            "findings": suppressed_findings,
            "overall_risk": overall,  # Severity signal — unchanged, not replaced.
            "rule_counts": counts,
            "version": self.version,
            "ruleset_version_data": _RULESET_VERSION_DATA,
            "suppression_log": suppression_reasons,  # Audit trail
            "contradiction_log": contradiction_log,  # Audit trail — see _detect_contradictions
            # Business workflow decision layer, additive to overall_risk:
            # what should happen to this contract next, not just how risky it is.
            "signature_readiness": workflow["signature_readiness"],
            "blocking_findings": workflow["blocking_findings"],
            "policy_blocked_findings": workflow["policy_blocked_findings"],
            "non_blocking_findings": workflow["non_blocking_findings"],
            # Structured contract-to-cash terms, for comparison against an
            # actual invoice configuration (not just "Net 30 mentioned").
            "payment_terms": _extract_payment_terms(text),
        }

    def build_missing_sections(self, findings: List[Finding]) -> List[str]:
        """
        Build rule-based recommendations for possible missing sections.
        
        This is a conservative, deterministic recommender that suggests sections
        based on triggered rules. Phrased as "You may want to confirm..." to avoid
        legal advice claims.
        """
        recommendations = []
        rule_ids = {f.rule_id for f in findings}

        # Baseline recommendations, keyed by topic. A baseline item is only
        # shown when no rule-based recommendation already covers its topic —
        # otherwise the report lists near-duplicate entries side by side.
        baseline_by_topic = {
            "liability": "Limitation of liability (confirm it exists and covers key categories)",
            "indemn": "Indemnification scope (confirm it is mutual and reasonably capped)",
            "termination": "Termination / term (confirm notice windows and renewal terms)",
            "ip ": "IP ownership / license scope (confirm no unintended assignment)",
        }
        
        # Rule-based recommendations
        if "H_LOL_01" in rule_ids or "H_INDEM_01" in rule_ids:
            recommendations.append("Explicit liability cap / limitation of liability clause (You may want to confirm whether liability is capped and which categories are included)")
        
        if "H_IP_01" in rule_ids or "H_IP_WORK_PRODUCT_01" in rule_ids:
            recommendations.append("License-back / IP carve-out / ownership clarification (You may want to confirm whether you retain rights to pre-existing IP and general knowledge)")
        
        if "H_INDEM_ONEWAY_01" in rule_ids:
            recommendations.append("Mutual indemnity / indemnity cap / scope limitation (You may want to confirm whether indemnification obligations are mutual and reasonably scoped)")
        
        if "M_CONF_01" in rule_ids:
            recommendations.append("Confidentiality term + survival limits (You may want to confirm whether confidentiality obligations have a defined term or expiration)")
        
        if "M_EQUIT_NOBOND_01" in rule_ids:
            recommendations.append("Bond requirement for equitable relief (You may want to confirm whether equitable relief provisions require posting a bond or other security)")
        
        if "H_ATTFEE_01" in rule_ids:
            recommendations.append("Mutual attorneys' fees / fee-shifting (You may want to confirm whether fee-shifting applies to both parties or only one)")
        
        if "H_LOL_CARVEOUT_01" in rule_ids:
            recommendations.append("Liability cap scope (You may want to confirm which categories are included in the liability cap and which are excluded)")
        
        if "H_ASSIGN_CHANGE_CTRL_01" in rule_ids:
            recommendations.append("Assignment rights on change of control (You may want to confirm whether assignment is permitted in connection with mergers, acquisitions, or change of control)")
        
        if "H_PUBLICITY_01" in rule_ids:
            recommendations.append("Publicity and disclosure controls (You may want to confirm whether either party can disclose the relationship or use branding without consent)")
        
        if "M_AUDIT_01" in rule_ids:
            recommendations.append("Audit rights scope and limitations (You may want to confirm the scope, frequency, and notice requirements for any audit or inspection rights)")
        
        if "M_TERM_NOTICE_01" in rule_ids:
            recommendations.append("Termination notice requirements (You may want to confirm the notice period required for termination and any renewal windows)")
        
        if "M_SURVIVAL_SCOPE_01" in rule_ids:
            recommendations.append("Survival clause scope (You may want to confirm which obligations survive termination and for how long)")
        
        if "M_WAIVER_DEFENSE_01" in rule_ids:
            recommendations.append("Waiver of defenses scope (You may want to confirm whether any defenses or rights are waived and the scope of such waivers)")

        if "H_UNILATERAL_MOD_01" in rule_ids:
            recommendations.append("Amendment and modification controls (You may want to confirm that changes to terms require mutual written consent)")

        if "H_CONSEQUENTIAL_01" in rule_ids:
            recommendations.append("Damages remedies (You may want to confirm whether consequential and indirect damages waivers are mutual)")

        if "H_TERM_CONVENIENCE_01" in rule_ids:
            recommendations.append("Termination rights parity (You may want to confirm whether termination for convenience is available to both parties)")

        if "H_DATA_TERMINATION_01" in rule_ids:
            recommendations.append("Data portability and exit (You may want to confirm obligations for data return, export, or deletion on termination)")

        if "H_ASYMMETRIC_LIABILITY_01" in rule_ids:
            recommendations.append("Mutual liability cap (You may want to confirm whether liability caps apply equally to both parties)")

        if "M_ARBITRATION_01" in rule_ids:
            recommendations.append("Dispute resolution (You may want to confirm the dispute resolution mechanism and whether class action rights are preserved)")

        if "M_WARRANTY_DISCLAIM_01" in rule_ids:
            recommendations.append("Warranty protections (You may want to confirm whether warranty disclaimers are appropriate for the services or products received)")

        if "M_FORCE_MAJEURE_01" in rule_ids:
            recommendations.append("Force majeure scope (You may want to confirm that force majeure is narrowly defined and includes termination rights for extended events)")

        if "H_CARD_AUTH_01" in rule_ids:
            recommendations.append("Billing authorization controls (You may want to confirm future charges require clear notice, renewal reminders, and easy cancellation)")

        if "H_CONTENT_LICENSE_01" in rule_ids or "M_PHOTO_RELEASE_01" in rule_ids:
            recommendations.append("Content and likeness permissions (You may want to confirm licenses are limited by purpose, duration, channel, and withdrawal rights)")

        if "H_WAGE_DEDUCTION_01" in rule_ids or "H_CLASSIFICATION_01" in rule_ids:
            recommendations.append("Worker/payment protections (You may want to confirm classification, payout timing, deductions, offsets, and tax responsibilities are clear and fair)")

        if "M_REFUND_01" in rule_ids or "M_CANCEL_FEE_01" in rule_ids:
            recommendations.append("Refund and cancellation terms (You may want to confirm refund rights, cancellation windows, and fees are reasonable and easy to understand)")

        if "M_ACCOUNT_SUSPEND_01" in rule_ids:
            recommendations.append("Account access and service continuity (You may want to confirm notice, cure rights, data export access, and appeal paths before suspension)")

        if "M_PRIVACY_SHARING_01" in rule_ids or "L_COMMUNICATION_CONSENT_01" in rule_ids:
            recommendations.append("Privacy and communications choices (You may want to confirm opt-out rights, purpose limits, and third-party sharing disclosures)")

        # Rule-based recommendations are contextual, so they lead; baseline
        # items fill in only for topics no rule-based entry already covers.
        covered = " ".join(recommendations).lower()
        baseline = [text for topic, text in baseline_by_topic.items() if topic not in covered]
        all_recommendations = recommendations + baseline
        return all_recommendations[:8]
