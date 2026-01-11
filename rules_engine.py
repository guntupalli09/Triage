"""
Deterministic Rule Engine for Contract Risk Triage

- Purely deterministic: regex + proximity logic only.
- Designed for Commercial NDAs / MSAs triage (not legal advice).
- Produces auditable findings with matched excerpts.
- Conservative detection: false positives acceptable, silence not acceptable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Iterable


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Finding:
    rule_id: str
    rule_name: str
    title: str
    severity: Severity
    rationale: str
    matched_excerpt: str
    position: int
    context: str
    clause_number: Optional[str] = None
    matched_keywords: List[str] = None
    aliases: List[str] = None
    
    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []
        if self.aliases is None:
            self.aliases = []


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
    
    def __post_init__(self):
        # Ensure aliases is a list (dataclass frozen=True requires this pattern)
        if self.aliases is None:
            object.__setattr__(self, 'aliases', [])


_WS_RE = re.compile(r"\s+")


def _normalize_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _chunk_text(raw: str) -> List[str]:
    """
    Preserve some structure by chunking on blank lines. Contracts often separate sections.
    If blank lines not present, fallback to fixed-size chunks.
    """
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    parts = [p.strip() for p in raw.split("\n\n") if p.strip()]
    if parts:
        return [_normalize_whitespace(p) for p in parts]

    cleaned = _normalize_whitespace(raw)
    size = 3000
    return [cleaned[i : i + size] for i in range(0, len(cleaned), size)]


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


def _find_all(pattern: str, text: str) -> Iterable[re.Match]:
    return re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL)


def _proximity_spans(
    anchors: List[str], nearby: List[str], text: str, window: int
) -> List[Tuple[int, int]]:
    """
    Find spans where an anchor occurs and any 'nearby' occurs within +/- window.
    Returns spans around the anchor match (auditable anchor-based excerpt).
    """
    spans: List[Tuple[int, int]] = []
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
            if re.search(n, neighborhood, flags=re.IGNORECASE | re.DOTALL):
                spans.append((a_start, a_end))
                break

    # De-dup spans
    return sorted(set(spans))


# Rule Engine Version - for transparency and trust
RULE_ENGINE_VERSION = "1.0.3"


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
                window=400,
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
            # ---------------- MEDIUM ----------------
            Rule(
                rule_id="M_CONF_01",
                rule_name="indefinite_confidentiality",
                title="Confidentiality may be perpetual / indefinite",
                severity=Severity.MEDIUM,
                rationale="Indefinite confidentiality can create long-term compliance burden and uncertainty around retention and disclosure.",
                pattern=r"\b(confidentiality|non[-\s]?disclosure)\b.*?\b(perpetual|in\s+perpetuity|indefinite(ly)?|no\s+expiration)\b",
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
            ),
            Rule(
                rule_id="M_INJUNCT_01",
                rule_name="injunctive_relief",
                title="Broad injunctive relief language",
                severity=Severity.MEDIUM,
                rationale="Broad injunctive relief provisions can bypass standard dispute resolution safeguards.",
                pattern=r"\binjunctive\s+relief\b|\bequitable\s+relief\b",
            ),
            # ---------------- LOW ----------------
            Rule(
                rule_id="L_LATEFEE_01",
                rule_name="late_fees_interest",
                title="Late fees / high interest",
                severity=Severity.LOW,
                rationale="Penalty terms can increase costs if payment timing slips.",
                pattern=r"\b(late\s+fee|interest)\b.*?\b(\d{2,}%|\d+\.\d+%)\b",
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
        ]

    def analyze(self, text: str) -> Dict:
        chunks = _chunk_text(text)

        findings: List[Finding] = []
        chunk_offset = 0
        for chunk in chunks:
            for rule in self.rules:
                if rule.pattern:
                    for m in _find_all(rule.pattern, chunk):
                        s, e = m.span()
                        absolute_pos = chunk_offset + s
                        ex = _excerpt(chunk, s, e)
                        matched_text = m.group(0)
                        clause_num = _extract_clause_number(text, absolute_pos)
                        keywords = _extract_matched_keywords(matched_text, rule.pattern)
                        findings.append(
                            Finding(
                                rule_id=rule.rule_id,
                                rule_name=rule.rule_name,
                                title=rule.title,
                                severity=rule.severity,
                                rationale=rule.rationale,
                                matched_excerpt=ex,
                                position=absolute_pos,
                                context=ex,
                                clause_number=clause_num,
                                matched_keywords=keywords,
                                aliases=rule.aliases or [],
                            )
                        )
                else:
                    assert rule.anchors and rule.nearby
                    spans = _proximity_spans(rule.anchors, rule.nearby, chunk, rule.window)
                    for (s, e) in spans:
                        absolute_pos = chunk_offset + s
                        ex = _excerpt(chunk, s, e)
                        # For proximity matches, extract keywords from context
                        context_text = chunk[max(0, s-100):min(len(chunk), e+100)]
                        clause_num = _extract_clause_number(text, absolute_pos)
                        keywords = _extract_matched_keywords(context_text)
                        findings.append(
                            Finding(
                                rule_id=rule.rule_id,
                                rule_name=rule.rule_name,
                                title=rule.title,
                                severity=rule.severity,
                                rationale=rule.rationale,
                                matched_excerpt=ex,
                                position=absolute_pos,
                                context=ex,
                                clause_number=clause_num,
                                matched_keywords=keywords,
                                aliases=rule.aliases or [],
                            )
                        )
            # Update chunk offset for next iteration
            chunk_offset += len(chunk) + 1  # +1 for newline separator

        # Deduplicate by rule_id to prevent inflated counts
        # Keep only the first occurrence of each rule_id
        deduped: List[Finding] = []
        seen_rule_ids = set()
        for f in findings:
            if f.rule_id in seen_rule_ids:
                continue
            seen_rule_ids.add(f.rule_id)
            deduped.append(f)

        # Sort by severity then stable by rule_id
        rank = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
        deduped.sort(key=lambda x: (rank.get(x.severity, 9), x.rule_id))

        counts = {"high": 0, "medium": 0, "low": 0}
        for f in deduped:
            counts[f.severity.value] += 1

        if counts["high"] > 0:
            overall = "high"
        elif counts["medium"] >= 2:
            overall = "medium"
        else:
            overall = "low"

        return {
            "findings": deduped,
            "overall_risk": overall,
            "rule_counts": counts,
            "version": self.version,
        }
