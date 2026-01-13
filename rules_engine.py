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
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterable


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


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

    def _apply_suppression_rules(self, findings: List[Finding], text: str) -> Tuple[List[Finding], Dict[str, str]]:
        """
        Apply deterministic false-positive suppression rules.
        
        Suppression is explicit, deterministic, and explainable.
        NO probabilistic logic. NO ML.
        
        Rules:
        - If indemnity clause contains "to the extent required by law" → downgrade severity
        - If IP assignment contains "excluding pre-existing IP" → suppress assignment risk
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
                # Downgrade severity instead of suppressing
                suppressed_finding = Finding(
                    rule_id=finding.rule_id,
                    rule_name=finding.rule_name,
                    title=finding.title,
                    severity=Severity.MEDIUM,  # Downgrade from HIGH to MEDIUM
                    rationale=finding.rationale + " Note: Limited by 'to the extent required by law' language.",
                    matched_excerpt=finding.matched_excerpt,
                    position=finding.position,
                    context=finding.context,
                    start_index=finding.start_index,
                    end_index=finding.end_index,
                    exact_snippet=finding.exact_snippet,
                    clause_number=finding.clause_number,
                    matched_keywords=finding.matched_keywords,
                    aliases=finding.aliases,
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
                suppressed_finding = Finding(
                    rule_id=finding.rule_id,
                    rule_name=finding.rule_name,
                    title=finding.title,
                    severity=Severity.MEDIUM,
                    rationale=finding.rationale + " Note: Carve-out may be required by law.",
                    matched_excerpt=finding.matched_excerpt,
                    position=finding.position,
                    context=finding.context,
                    start_index=finding.start_index,
                    end_index=finding.end_index,
                    exact_snippet=finding.exact_snippet,
                    clause_number=finding.clause_number,
                    matched_keywords=finding.matched_keywords,
                    aliases=finding.aliases,
                )
                reason = "Downgraded severity: carve-out may be required by applicable law"
            
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
                pattern=r"\battorneys?['\s]?fees?\b|\battorney['\s]?s\s+fees?\b|\blegal\s+fees?\b",
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
        ]

    def analyze(self, text: str) -> Dict:
        """
        Analyze contract text using deterministic rule engine.
        
        Neural-Symbolic Architecture: This method is the deterministic control plane.
        All risk detection happens here - LLM never participates in detection.
        
        Process:
        1. Chunk text for efficient processing
        2. Apply all rules (pattern or proximity matching)
        3. Extract clause-level anchors (start_index, end_index, exact_snippet)
        4. Deduplicate findings by (rule_id, clause_number)
        5. Apply false-positive suppression rules
        6. Compute overall risk from suppressed findings
        7. Return findings with ruleset version metadata
        
        Returns:
            Dict with:
            - findings: List[Finding] (with clause-level anchoring)
            - overall_risk: "high" | "medium" | "low"
            - rule_counts: Dict[str, int] by severity
            - version: str (ruleset version)
            - ruleset_version_data: Dict (full version metadata)
            - suppression_log: Dict[str, str] (audit trail of suppressions)
        """
        chunks = _chunk_text(text)

        findings: List[Finding] = []
        chunk_offset = 0
        for chunk in chunks:
            for rule in self.rules:
                if rule.pattern:
                    for m in _find_all(rule.pattern, chunk):
                        s, e = m.span()
                        absolute_start = chunk_offset + s
                        absolute_end = chunk_offset + e
                        ex = _excerpt(chunk, s, e)
                        matched_text = m.group(0)
                        # Get surrounding context (±200 chars)
                        context_start = max(0, absolute_start - 200)
                        context_end = min(len(text), absolute_end + 200)
                        surrounding_context = text[context_start:context_end]
                        clause_num = _extract_clause_number(text, absolute_start)
                        keywords = _extract_matched_keywords(matched_text, rule.pattern)
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
                            )
                        )
                else:
                    assert rule.anchors and rule.nearby
                    spans = _proximity_spans(rule.anchors, rule.nearby, chunk, rule.window)
                    for (s, e) in spans:
                        absolute_start = chunk_offset + s
                        absolute_end = chunk_offset + e
                        ex = _excerpt(chunk, s, e)
                        # Extract exact matched snippet from chunk
                        exact_matched = chunk[s:e] if s < len(chunk) and e <= len(chunk) else chunk[max(0, s):min(len(chunk), e)]
                        # Get surrounding context (±200 chars)
                        context_start = max(0, absolute_start - 200)
                        context_end = min(len(text), absolute_end + 200)
                        surrounding_context = text[context_start:context_end]
                        # For proximity matches, extract keywords from context
                        context_text = chunk[max(0, s-100):min(len(chunk), e+100)]
                        clause_num = _extract_clause_number(text, absolute_start)
                        keywords = _extract_matched_keywords(context_text)
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
                            )
                        )
            # Update chunk offset for next iteration
            chunk_offset += len(chunk) + 1  # +1 for newline separator

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
        suppressed_findings, suppression_reasons = self._apply_suppression_rules(deduped, text)
        
        # Log suppressions for auditability
        if suppression_reasons:
            for finding_id, reason in suppression_reasons.items():
                logger.info(f"SUPPRESSION: {finding_id} - {reason}")

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
        
        # Baseline recommendations (always shown)
        baseline = [
            "Limitation of liability (confirm it exists and covers key categories)",
            "Indemnification scope (confirm it is mutual and reasonably capped)",
            "Termination / term (confirm notice windows and renewal terms)",
            "IP ownership / license scope (confirm no unintended assignment)",
        ]
        
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
        
        # Combine baseline with rule-based recommendations (limit total)
        all_recommendations = baseline + recommendations
        return all_recommendations[:6]  # Max 6 recommendations
