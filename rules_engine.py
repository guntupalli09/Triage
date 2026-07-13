"""
Deterministic Rule Engine for Contract Risk Triage

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

logger = logging.getLogger(__name__)


class Severity(str, Enum):
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
    # Which precise claim this finding makes — see FindingType. Defaults to
    # "adverse_language_detected" since that's what a direct regex/proximity
    # hit actually proves; REQUIRED_SECTION rules override this when they
    # report a document-level absence instead.
    finding_type: str = FindingType.ADVERSE_LANGUAGE_DETECTED.value

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


def _chunk_text(text: str) -> List[Tuple[int, str]]:
    """
    Split into (start_offset, substring) chunks on blank lines. Contracts often
    separate sections this way. If blank lines aren't present, fall back to
    fixed-size chunks.

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


def _classify_party_direction(clause_text: str) -> Dict[str, str]:
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
    """
    if _MUTUAL_RE.search(clause_text):
        return {
            "obligor": "both_parties",
            "beneficiary": "both_parties",
            "applies_to": "both_parties",
            "mutuality_status": "mutual",
        }

    provider_hit = _PROVIDER_ROLE_RE.search(clause_text)
    customer_hit = _CUSTOMER_ROLE_RE.search(clause_text)

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
        - overall_risk = "high" if any finding.severity == "high"
        - else overall_risk = "medium" if count(medium) >= 2
        - else overall_risk = "low"
        
        This policy ensures that a single high-risk finding elevates the entire assessment,
        while multiple medium-risk findings also warrant elevated attention.
        """
        if counts["high"] > 0:
            return "high"
        elif counts["medium"] >= 2:
            return "medium"
        else:
            return "low"

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

    def _apply_suppression_rules(self, findings: List[Finding], text: str) -> Tuple[List[Finding], Dict[str, str]]:
        """
        Apply deterministic false-positive suppression rules.
        
        Suppression is explicit, deterministic, and explainable.
        NO probabilistic logic. NO ML.
        
        Rules:
        - If indemnity clause contains "to the extent required by law" → downgrade severity
        - If IP assignment contains "excluding pre-existing IP" → suppress assignment risk
        - If a "one-way"/unilateral rule's clause is actually mutual → downgrade
          severity and strip the one-way framing (see ONE_WAY_RULE_IDS)
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
                suppressed_finding = replace(
                    suppressed_finding,
                    severity=Severity.MEDIUM,
                    rationale=(
                        suppressed_finding.rationale
                        + " Note: Clause language ('either party'/'mutual'/'both parties') indicates "
                        "this obligation applies to both parties, not one-sided as the rule title suggests. "
                        "Confirm mutuality is intended and consistently drafted."
                    ),
                )
                reason = "Downgraded severity: party-direction analysis found mutual language, not one-way"

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
                pattern=r"\b(assigns?|transfer(s|red)?|hereby\s+assigns?)\b.*?\ball\s+right[s]?,\s*title,\s*and\s+interest\b",
            ),
            Rule(
                rule_id="H_PERSONAL_01",
                rule_name="personal_liability",
                title="Potential personal liability exposure",
                severity=Severity.HIGH,
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
                pattern=r"\b(work\s+product|deliverables?)\b.*?\b(owned\s+by|shall\s+be\s+the\s+property\s+of)\b",
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
                pattern=r"\b(may\s+(modify|amend|change|update|revise)\b.*?\b(at\s+any\s+time|in\s+its?\s+(sole\s+)?discretion|without\s+(prior\s+)?(written\s+)?consent|without\s+notice|unilateral))|(\breserves?\s+the\s+right\s+to\s+(modify|amend|change|update|revise)\b)",
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
                anchors=[r"\bterminate\b.*\bconvenience\b", r"\bterminate\b.*\bany\s+reason\b", r"\bterminate\b.*\bwithout\s+cause\b", r"\bterminate\b.*\bno\s+reason\b"],
                nearby=[
                    r"\bsole\s+discretion\b",
                    r"\bat\s+any\s+time\b",
                    r"\bupon\s+\d+\s+days?\b",
                    r"\bwritten\s+notice\b",
                ],
                window=350,
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
                severity=Severity.HIGH,
                rationale="A liability cap that applies to one party but not the other creates an imbalanced risk allocation that can leave you exposed.",
                anchors=[r"\b(vendor|provider|supplier|licensor)\b.*\bliabilit(y|ies)\b", r"\bliabilit(y|ies)\b.*\b(vendor|provider|supplier|licensor)\b"],
                nearby=[
                    r"\bshall\s+not\s+exceed\b",
                    r"\blimited\s+to\b",
                    r"\baggregate\s+liabilit(y|ies)\b",
                    r"\bmaximum\s+liabilit(y|ies)\b",
                ],
                window=400,
                aliases=["one_sided_liability_cap", "vendor_liability_cap"],
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
                anchors=[r"\bsuspend\w*\b", r"\bterminate\w*\b", r"\bdisable\w*\b", r"\baccess\b"],
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
                pattern=r"\b(confidential(ity|ly)?|non[-\s]?disclosure)\b.*?\b(perpetual|in\s+perpetuity|indefinite(ly)?|no\s+expiration)\b",
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
                pattern=r"\bnon[-\s]?compete\b|\bnon[-\s]?solicit\b|\brestrict(ion|ive)\b.*\bcompeti(t|tion|tor)\b",
            ),
            Rule(
                rule_id="M_DEV_RESTRICT_01",
                rule_name="dev_restriction_confidential",
                title="Development restriction tied to confidential information",
                severity=Severity.MEDIUM,
                rationale="Restrictions on developing competing or similar products, even when tied to confidential information, can limit future work and are commonly negotiated.",
                pattern=r"(not\s+to\s+develop|shall\s+not\s+develop|may\s+not\s+develop).*?(compete|substantially\s+similar).*?(based\s+on|derived\s+from)",
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
                pattern=r"\bshall\s+not\s+use\b.*?\bknowledge\b.*?\bretained\b",
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\bconfidential\w*\b"],
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
                anchors=[r"\bterminate\b", r"\bnotice\b"],
                nearby=[
                    r"\b(?:at\s+least\s+)?(?:10|15|20|30)\s+days?\b",
                    r"\b(?:at\s+least\s+)?(?:ten|fifteen|twenty|thirty)\s+days?\b",
                    r"\bless\s+than\s+\d+\s+days\b",
                ],
                window=300,
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
                pattern=r"\b(as[\s-]is|as[\s-]available)\b.*?\b(warrant|guarantee|condition)\b|\b(disclaim|exclude)[sd]?\b.*?\b(all\s+)?warrant(y|ies)\b|\b(without\s+warrant(y|ies)\s+of\s+any\s+kind)\b|\bno\s+(implied\s+)?warrant(y|ies)\b",
                aliases=["as_is_disclaimer", "no_warranty", "implied_warranty_waiver"],
            ),
            Rule(
                rule_id="M_BREACH_NOTIFY_01",
                rule_name="no_breach_notification",
                title="No data breach notification obligation",
                severity=Severity.MEDIUM,
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
                pattern=r"\b(no\s+(?:service\s+level|SLA|uptime)\s+(?:guarantee|commitment|obligation))\b|\b(does\s+not\s+(?:guarantee|warrant|commit)\b.*?\b(?:availability|uptime|service\s+level))\b|\b(?:availability|uptime)\b.*?\b(as[\s-]is|without\s+(?:any\s+)?guarantee)\b",
                aliases=["no_sla", "no_uptime_guarantee", "service_level_absent"],
                rule_class=RuleClass.REQUIRED_SECTION,
                topic_patterns=[r"\b(service|platform|software|application|system|SaaS)\b"],
                protective_patterns=[
                    r"\b(service\s+level|SLA|uptime)\b[^.]{0,80}\b(guarantee|commitment|%|percent)\b",
                    r"\d{2}(\.\d+)?\s?%\s+uptime\b",
                    r"\buptime\b[^.]{0,40}\d{2}(\.\d+)?\s?%",
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
                # Match interest rates and late fees - simple pattern matching percentages
                pattern=r"(late\s+fee|late\s+payments?|interest).*?\d+%|\d+%.*?(per\s+annum|per\s+year|interest)",
            ),
            Rule(
                rule_id="L_BROADDEF_01",
                rule_name="broad_definitions",
                title="Broad definitions may expand obligations",
                severity=Severity.LOW,
                rationale="Overly broad defined terms can expand confidentiality or scope beyond what you expect.",
                pattern=r"\bmeans\b.*?\b(including|without\s+limitation)\b",
            ),
            Rule(
                rule_id="L_GOVLAW_01",
                rule_name="governing_law_venue",
                title="Specific governing law or venue",
                severity=Severity.LOW,
                rationale="Governing law and venue choices can affect enforcement cost and strategy.",
                pattern=r"\bgoverned\s+by\b.*?\blaws?\b|\bexclusive\s+jurisdiction\b",
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
                severity=Severity.HIGH,
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
                title="Personal data processing without adequate protections",
                severity=Severity.HIGH,
                rationale="Agreements that involve processing personal data but lack references to DPA, GDPR, CCPA, subprocessors, or security measures leave you without contractual protections required by law.",
                anchors=[
                    r"\bpersonal\s+(data|information)\b",
                    r"\bpersonally\s+identifiable\s+information\b",
                    r"\bPII\b",
                ],
                nearby=[
                    r"\bprocess(es|ed|ing)?\b",
                    r"\bcollect(s|ed|ion)?\b",
                    r"\bstore(s|d)?\b",
                    r"\buse(s|d)?\b.*\bpersonal\b",
                ],
                window=500,
                aliases=["missing_dpa", "gdpr_obligations", "data_processing_without_protection"],
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
        # Normalize Unicode punctuation so regex patterns using ASCII quotes/dashes
        # match text extracted from PDFs and Word documents (smart quotes, em-dashes, etc.)
        text = (
            text
            .replace("‘", "'").replace("’", "'")   # left/right single quotes → '
            .replace("“", '"').replace("”", '"')   # left/right double quotes → "
            .replace("–", "-").replace("—", "-")   # en-dash / em-dash → -
            .replace("…", "...")                         # ellipsis → ...
            .replace("\r\n", "\n").replace("\r", "\n")   # normalize line endings once, up front
        )

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
                        # Get surrounding context (±200 chars)
                        context_start = max(0, absolute_start - 200)
                        context_end = min(len(text), absolute_end + 200)
                        surrounding_context = text[context_start:context_end]
                        clause_num = _extract_clause_number(text, absolute_start)
                        keywords = _extract_matched_keywords(matched_text, rule.pattern)
                        party_direction = (
                            _classify_party_direction(surrounding_context)
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
                        # Get surrounding context (±200 chars)
                        context_start = max(0, absolute_start - 200)
                        context_end = min(len(text), absolute_end + 200)
                        surrounding_context = text[context_start:context_end]
                        # For proximity matches, extract keywords from context
                        context_text = chunk[max(0, s-100):min(len(chunk), e+100)]
                        clause_num = _extract_clause_number(text, absolute_start)
                        keywords = _extract_matched_keywords(context_text)
                        party_direction = (
                            _classify_party_direction(surrounding_context)
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
        rank = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
        deduped.sort(key=lambda x: (rank.get(x.severity, 9), x.rule_id))

        # Phase 5: False-positive suppression layer (deterministic, explainable)
        if suppression_enabled:
            suppressed_findings, suppression_reasons = self._apply_suppression_rules(deduped, text)
            
            # Log suppressions for auditability
            if suppression_reasons:
                for finding_id, reason in suppression_reasons.items():
                    logger.info(f"SUPPRESSION: {finding_id} - {reason}")
        else:
            # Suppression disabled: use all findings without suppression
            suppressed_findings = deduped
            suppression_reasons = {}
            logger.info("Suppression disabled: all findings returned without suppression")

        counts = {"high": 0, "medium": 0, "low": 0}
        for f in suppressed_findings:
            counts[f.severity.value] += 1

        overall = self._compute_overall_risk(suppressed_findings, counts)

        return {
            "findings": suppressed_findings,
            "overall_risk": overall,
            "rule_counts": counts,
            "version": self.version,
            "ruleset_version_data": _RULESET_VERSION_DATA,
            "suppression_log": suppression_reasons,  # Audit trail
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
