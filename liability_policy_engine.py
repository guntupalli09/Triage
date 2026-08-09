"""
Deterministic Limitation-of-Liability Policy Engine.

Vertical slice of the policy-first playbook design. Three architectural
commitments distinguish this from a naive "find a number, compare it"
extractor, each driven by a real failure the benchmark corpus surfaced
(see benchmarks/liability_benchmark_report.md):

1. DOCUMENT-WIDE PROVISION DISCOVERY. A contract can contain more than one
   Limitation of Liability provision — a later exhibit, schedule, or an
   amendment that explicitly restates the clause. Scanning only a fixed
   window from the first occurrence is not a simplification, it is a blind
   spot: a superseding cap placed past that window is invisible, and the
   engine will confidently accept a stale, superseded number. This module
   finds every LoL-anchored provision in the full document and reconciles
   them deterministically (an explicit amendment/restatement supersedes;
   consistent duplicates agree; anything else is unreconciled) rather than
   ever silently preferring the first one found.

2. TYPED CAP REPRESENTATION. A liability cap is not always one number.
   "The greater of $1M or 2x fees," "1x per claim, 3x in the aggregate,"
   and a plain "2x annual fees" are different structures, and collapsing
   the first two into a single extracted multiplier produces a
   deterministic but wrong answer — worse than admitted uncertainty,
   because the product presents it as authoritative. CapExpression
   represents simple, greater-of, lesser-of, and per-claim/aggregate
   structures explicitly; only a structure that reduces to one comparable
   value under the policy's basis is evaluated, everything else is
   REQUIRES_REVIEW with the specific reason recorded.

3. DIRECTIONAL (ASYMMETRIC) POSITIONS. When a contract states different
   caps — or an uncapped position — for each named party, there is no
   single "the cap" to extract. PartyPosition tracks each side
   independently; evaluation maps "us" from the playbook's configured
   contract_side and never silently evaluates whichever side's language
   happened to be easier to parse while ignoring the other.

Every decision states, deterministically, no confidence score at any
branch: ACCEPT / ACCEPT_WITH_NOTE / NEGOTIATE / MUST_REDLINE / PROHIBITED /
ESCALATE / REQUIRES_REVIEW / NOT_APPLICABLE — and carries the evidence that
produced it: which provision controls, what was extracted, and why.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Tuple


RULE_ID = "POLICY_LOL_CAP"

ACCEPT = "ACCEPT"
ACCEPT_WITH_NOTE = "ACCEPT_WITH_NOTE"
NEGOTIATE = "NEGOTIATE"
MUST_REDLINE = "MUST_REDLINE"
PROHIBITED = "PROHIBITED"
ESCALATE = "ESCALATE"
REQUIRES_REVIEW = "REQUIRES_REVIEW"
NOT_APPLICABLE = "NOT_APPLICABLE"

_LADDER_ORDER = [ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, ESCALATE, PROHIBITED]

CATEGORIES = [
    "data_breach", "ip_infringement", "confidentiality",
    "indemnification", "fraud", "gross_negligence", "willful_misconduct",
]
EXCEPTION_TYPES = list(CATEGORIES)

BUY_SIDE_ROLES = {"customer", "client", "licensee", "buyer", "purchaser", "recipient"}
SELL_SIDE_ROLES = {"supplier", "vendor", "contractor", "licensor", "provider", "seller", "company"}

_CATEGORY_KEYWORD_RE = {
    "data_breach": re.compile(r"\bdata breach(?:es)?\b|\bsecurity breach(?:es)?\b", re.I),
    "ip_infringement": re.compile(
        r"\bintellectual property\b.{0,40}\binfringement\b|\bIP infringement\b|\binfringement of\b.{0,40}\bintellectual property\b",
        re.I,
    ),
    "confidentiality": re.compile(r"\bconfidentiality\b|\bconfidential information\b", re.I),
    "indemnification": re.compile(r"\bindemnif\w*\b", re.I),
    "fraud": re.compile(r"\bfraud(?:ulent)?\b", re.I),
    "gross_negligence": re.compile(r"\bgross negligence\b", re.I),
    "willful_misconduct": re.compile(r"\bwil[l]?ful misconduct\b", re.I),
}

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

_ANCHOR_RE = re.compile(r"limitation of liability|liability cap", re.I)
_UNLIMITED_RE = re.compile(
    r"unlimited liability|no limit(?:ation)?\s+(?:on|of)\s+liability"
    r"|liability shall not be limited|without limitation as to (?:the )?amount"
    r"|shall have unlimited liability"
    r"|remains?\s+uncapped|shall\s+(?:be|remain)\s+uncapped"
    r"|not subject to any (?:cap|limit)(?:ation)?"
    r"|there (?:is|shall be) no (?:cap|limit)(?:ation)?",
    re.I,
)
_MULTIPLIER_NUM_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:x|times)\s*(?:the\s+)?(?:total\s+|aggregate\s+)?(?:annual\s+)?fees?"
    r"(?:\s+paid)?(?:\s+(?:in|during)\s+the\s+(?:twelve|12)\s*\(?12\)?\s*months?)?",
    re.I,
)
_MULTIPLIER_WORD_RE = re.compile(
    r"\b(" + "|".join(_WORD_NUMBERS) + r")\s*(?:\(\d+\))?\s*times?\s*(?:the\s+)?(?:total\s+|aggregate\s+)?"
    r"(?:annual\s+)?fees?",
    re.I,
)
_FIXED_AMOUNT_RE = re.compile(
    r"(?:maximum(?:\s+aggregate)?\s+liability(?:\s+of\s+(?:either\s+party)?)?\s*(?:shall\s+not\s+exceed|shall\s+exceed|exceed|of|:)?"
    r"|liable\s+for\s+(?:an\s+amount\s+)?(?:in\s+excess\s+of|more\s+than)"
    r"|limited\s+to"
    r"|(?:is\s+)?capped\s+at"
    r"|(?:a\s+)?cap\s+of"
    r"|shall\s+not\s+exceed)\s*\$\s*([\d,]+(?:\.\d{2})?)",
    re.I,
)
_EXCLUSION_SIGNAL_RE = re.compile(
    r"shall not apply to|does not apply to"
    r"|excluded from (?:this|the foregoing|such) limitation"
    r"|shall not be subject to (?:the foregoing|such|this) limitation"
    r"|there shall be no limitation"
    r"|not subject to the (?:cap|limitation)s?(?:\s+set forth| described)?(?:\s+above|\s+herein|\s+in this section)?"
    r"|except for (?:breaches? of )?|other than|excluding (?:breaches? of )?|with the exception of",
    re.I,
)
_CAP_TRIGGER_RE = re.compile(
    r"shall not exceed|is capped at|shall be capped|limited to|shall not be liable for", re.I,
)
_AMBIGUITY_SIGNAL_RE = re.compile(
    r"notwithstanding|provided,?\s+however|except as otherwise (?:set forth|provided)|subject to the foregoing",
    re.I,
)
_MUTUAL_PHRASE_RE = re.compile(r"\beither party\b|\bboth parties\b|\bneither party\b", re.I)
_ROLE_POSITION_RE = re.compile(
    r"([A-Z][A-Za-z]{2,20})(?:'s)?\s+(?:aggregate\s+|maximum\s+)?liability\s+(?:under this Agreement\s+)?"
    r"(?:shall not exceed|is (?:capped|limited) (?:at|to)|shall be (?:capped|limited) (?:at|to)"
    r"|is not subject to|shall not be liable for)",
    re.I,
)
_CONSEQUENTIAL_RE = re.compile(r"\b(consequential|indirect|special|incidental|punitive)\b[^.]{0,60}\bdamages\b", re.I)
_EXCLUDE_PHRASE_RE = re.compile(
    r"shall not be liable for"
    r"|no party shall be liable"
    r"|neither party shall be liable"
    r"|in no event shall\s+(?:\w+\s+){0,3}be liable"
    r"|(?:are|is|shall be) excluded"
    r"|excludes? (?:any|all)?\s*(?:consequential|indirect|special|incidental|punitive)",
    re.I,
)
_CARVEOUT_PHRASE_RE = re.compile(r"except for|other than|excluding breaches of|with respect to", re.I)
_AMENDMENT_SIGNAL_RE = re.compile(
    r"hereby amended|amended and restated|amends and restates|is amended to read|is hereby amended"
    r"|supersed(?:e|ing|ed)s?|shall supersede",
    re.I,
)

_PROVISION_WINDOW_CHARS = 3000
_LOCAL_WINDOW_CHARS = 180
_ANCHOR_DEDUP_GAP = 300  # a second anchor this close to a prior one is the same clause, not a new provision
_SECTION_LABEL_LOOKBACK = 30
_GREATER_LESSER_RE = re.compile(
    r"(?P<greater>greater of|whichever is (?:the )?(?:greater|higher))"
    r"|(?P<lesser>lesser of|whichever is (?:the )?(?:lesser|lower))",
    re.I,
)
_PER_CLAIM_RE = re.compile(r"per[\s-]claim|per[\s-]occurrence|(?:individual|single|each) claim", re.I)
_AGGREGATE_SCOPE_RE = re.compile(r"\baggregate\b|in the aggregate|across all claims|total liability", re.I)


# ---------------------------------------------------------------------------
# Typed cap representation (Priority 2)
# ---------------------------------------------------------------------------

@dataclass
class CapValue:
    kind: str  # "fee_multiplier" | "fixed_amount" | "unlimited"
    multiplier: Optional[float] = None
    fixed_amount: Optional[float] = None
    raw_excerpt: str = ""
    start_index: int = 0
    end_index: int = 0

    def summary(self) -> str:
        if self.kind == "unlimited":
            return "Unlimited"
        if self.kind == "fee_multiplier":
            return f"{self.multiplier:g}x annual fees"
        if self.kind == "fixed_amount":
            return f"${self.fixed_amount:,.2f} fixed"
        return "unspecified"

    def compare_key(self) -> float:
        if self.kind == "unlimited":
            return float("inf")
        if self.kind == "fee_multiplier":
            return self.multiplier
        return self.fixed_amount


@dataclass
class CapExpression:
    """A typed, possibly-compound liability cap position.

    structure is one of:
      "simple"                 — one unambiguous value
      "greater_of"             — max() of components governs
      "lesser_of"               — min() of components governs
      "per_claim_and_aggregate" — two different-scope values, both stated
      "unresolved"              — could not be reliably classified
    """
    structure: str
    components: List[CapValue] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)  # parallel to components, only for per_claim_and_aggregate
    unresolved_reason: str = ""
    raw_excerpt: str = ""
    start_index: int = 0
    end_index: int = 0

    def effective_cap(self) -> Tuple[Optional[CapValue], Optional[str]]:
        """Returns (CapValue to compare against a policy threshold, reason)
        — reason is set (and the CapValue is None) whenever the structure
        cannot be reduced to one comparable value without information the
        engine doesn't have."""
        if self.structure == "simple":
            return (self.components[0] if self.components else None), None

        if self.structure in ("greater_of", "lesser_of"):
            if not self.components:
                return None, "compound cap structure detected but no component values could be extracted"
            kinds = {c.kind for c in self.components}
            non_unlimited = [c for c in self.components if c.kind != "unlimited"]
            if "unlimited" in kinds:
                if self.structure == "greater_of":
                    return CapValue(kind="unlimited", raw_excerpt=self.raw_excerpt,
                                     start_index=self.start_index, end_index=self.end_index), None
                # lesser_of: the non-unlimited option governs, if there's exactly one
                if len(non_unlimited) == 1:
                    return non_unlimited[0], None
                return None, "lesser-of structure could not be reduced to one value"
            if len({c.kind for c in non_unlimited}) > 1:
                return None, (
                    f"cannot resolve a {self.structure.replace('_', ' ')} structure mixing a fee "
                    f"multiplier and a fixed dollar amount without the actual annual fee value"
                )
            reducer = max if self.structure == "greater_of" else min
            return reducer(self.components, key=lambda c: c.compare_key()), None

        if self.structure == "per_claim_and_aggregate":
            if len(self.components) != 2:
                return None, "per-claim/aggregate structure detected but could not extract both values"
            a, b = self.components
            if a.kind == b.kind and a.compare_key() == b.compare_key():
                return a, None
            return None, (
                "clause distinguishes per-claim and aggregate caps with different values; "
                "policy threshold scope (per-claim vs. aggregate) is not specified"
            )

        return None, self.unresolved_reason or "cap structure could not be reliably classified"

    def summary(self) -> str:
        if self.structure == "simple":
            return self.components[0].summary() if self.components else "unspecified"
        if self.structure in ("greater_of", "lesser_of"):
            label = "greater of" if self.structure == "greater_of" else "lesser of"
            return f"{label} " + " or ".join(c.summary() for c in self.components)
        if self.structure == "per_claim_and_aggregate":
            parts = [f"{role}: {c.summary()}" for role, c in zip(self.roles, self.components)]
            return "; ".join(parts)
        return f"unresolved ({self.unresolved_reason})" if self.unresolved_reason else "unresolved"


def _simple(cap: Optional[CapValue]) -> CapExpression:
    if cap is None:
        return CapExpression(structure="simple", components=[])
    return CapExpression(structure="simple", components=[cap], raw_excerpt=cap.raw_excerpt,
                          start_index=cap.start_index, end_index=cap.end_index)


def _unresolved(reason: str, raw_excerpt: str = "", start_index: int = 0, end_index: int = 0) -> CapExpression:
    return CapExpression(structure="unresolved", unresolved_reason=reason, raw_excerpt=raw_excerpt,
                          start_index=start_index, end_index=end_index)


@dataclass
class CategoryTreatment:
    category: str
    # "uncapped" | "super_cap" | "within_general_cap" | "not_addressed" | "unresolved"
    treatment: str
    cap: Optional[CapValue] = None
    raw_excerpt: str = ""
    established: bool = True


@dataclass
class PartyPosition:
    role: str  # raw role word as it appears in the text, e.g. "Customer"
    side: Optional[str]  # "buy_side" | "sell_side" | None if unrecognized
    cap_expression: CapExpression


@dataclass
class Provision:
    """One discovered Limitation-of-Liability-anchored clause in the
    document. A document may contain several (see reconciliation logic in
    extract_liability_facts)."""
    index: int
    section_label: Optional[str]
    is_amendment: bool
    start_index: int
    end_index: int
    raw_excerpt: str
    general_cap_expression: CapExpression
    category_treatments: Dict[str, CategoryTreatment]
    party_positions: Dict[str, PartyPosition]
    consequential_damages_excluded: Optional[bool]
    consequential_damages_established: bool
    consequential_damages_carveouts: List[str]

    def provision_label(self) -> str:
        if self.section_label:
            return f"Section {self.section_label} — Limitation of Liability"
        return f"the Limitation of Liability provision at character {self.start_index}"


@dataclass
class LiabilityFacts:
    clause_found: bool
    provisions: List[Provision] = field(default_factory=list)
    controlling_provision: Optional[Provision] = None
    reconciliation: str = "single"  # "single" | "amendment_resolved" | "consistent_duplicate" | "unreconciled"
    reconciliation_explanation: str = ""


class PolicyRuleLike(Protocol):
    """Structural type for whatever ORM row (or test double) is passed to
    evaluate() — deliberately not importing models.PolicyRule, so this
    engine has no database dependency and stays independently testable."""
    preferred_multiplier: Optional[float]
    acceptable_max_multiplier: Optional[float]
    negotiate_max_multiplier: Optional[float]
    prohibit_unlimited: bool
    required_exceptions_json: Optional[List[str]]
    fallback_text: Optional[str]
    escalation_approval_authority: Optional[str]
    contract_side: str
    require_consequential_damages_exclusion: bool
    required_consequential_carveouts_json: Optional[List[str]]


@dataclass
class LadderStep:
    label: str
    description: str
    status: str  # "passed" | "current" | "not_reached"


@dataclass
class PolicyDecision:
    rule_id: str
    clause_type: str
    state: str
    contract_language: str
    extracted_summary: str
    policy_limit_summary: str
    required_action: str
    explanation: str
    negotiation_ladder: List[LadderStep]
    category_treatments: List[Dict[str, str]]
    unresolved_facts: List[str]
    start_index: Optional[int]
    end_index: Optional[int]
    escalate_to: Optional[str] = None
    fallback_text: Optional[str] = None
    source: Optional[str] = None
    controlling_provision: Optional[Dict[str, str]] = None
    our_position: Optional[Dict[str, str]] = None
    counterparty_position: Optional[Dict[str, str]] = None
    reconciliation: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "clause_type": self.clause_type,
            "state": self.state,
            "contract_language": self.contract_language,
            "extracted_summary": self.extracted_summary,
            "policy_limit_summary": self.policy_limit_summary,
            "required_action": self.required_action,
            "explanation": self.explanation,
            "negotiation_ladder": [
                {"label": s.label, "description": s.description, "status": s.status}
                for s in self.negotiation_ladder
            ],
            "category_treatments": self.category_treatments,
            "unresolved_facts": self.unresolved_facts,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "escalate_to": self.escalate_to,
            "fallback_text": self.fallback_text,
            "source": self.source,
            "controlling_provision": self.controlling_provision,
            "our_position": self.our_position,
            "counterparty_position": self.counterparty_position,
            "reconciliation": self.reconciliation,
        }

    def render_evidence_report(self) -> str:
        """Human-readable provenance block — the format a lawyer can point
        to as the basis for the decision, e.g.:

            PROHIBITED
            Controlling provision: Section 12.4 — Limitation of Liability
            General cap: 2x fees paid in preceding 12 months
            ...
            Result: PROHIBITED
            Evidence: "<exact contract language>"
        """
        lines = [self.state]
        if self.controlling_provision:
            lines.append(f"Controlling provision: {self.controlling_provision['label']}")
        lines.append(f"General cap: {self.extracted_summary}")
        for ct in self.category_treatments:
            if ct["treatment"] not in ("not_addressed",):
                lines.append(f"{ct['category'].replace('_', ' ').title()}: {ct['treatment'].replace('_', ' ').title()}"
                              + (f" ({ct['cap_summary']})" if ct.get("cap_summary") else ""))
        if self.counterparty_position:
            lines.append(f"Counterparty cap: {self.counterparty_position['summary']}")
        if self.our_position:
            lines.append(f"Our liability: {self.our_position['summary']}")
        if self.source:
            lines.append(f"Playbook: {self.source}")
        lines.append(f"Policy: {self.policy_limit_summary}")
        lines.append(f"Result: {self.state}")
        lines.append(f'Evidence: "{self.contract_language}"')
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extraction helpers
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


def _find_cap_values(window: str) -> List[CapValue]:
    """All cap-value mentions in the window, in document order. Overlapping
    matches from different patterns are deduped by keeping the first."""
    matches: List[Tuple[int, int, CapValue]] = []
    for m in _UNLIMITED_RE.finditer(window):
        matches.append((m.start(), m.end(), CapValue(
            kind="unlimited", raw_excerpt=window[m.start():m.end()], start_index=m.start(), end_index=m.end(),
        )))
    for m in _MULTIPLIER_NUM_RE.finditer(window):
        matches.append((m.start(), m.end(), CapValue(
            kind="fee_multiplier", multiplier=float(m.group(1)),
            raw_excerpt=window[m.start():m.end()], start_index=m.start(), end_index=m.end(),
        )))
    for m in _MULTIPLIER_WORD_RE.finditer(window):
        matches.append((m.start(), m.end(), CapValue(
            kind="fee_multiplier", multiplier=float(_WORD_NUMBERS[m.group(1).lower()]),
            raw_excerpt=window[m.start():m.end()], start_index=m.start(), end_index=m.end(),
        )))
    for m in _FIXED_AMOUNT_RE.finditer(window):
        matches.append((m.start(), m.end(), CapValue(
            kind="fixed_amount", fixed_amount=float(m.group(1).replace(",", "")),
            raw_excerpt=window[m.start():m.end()], start_index=m.start(), end_index=m.end(),
        )))

    matches.sort(key=lambda t: t[0])
    deduped: List[Tuple[int, int, CapValue]] = []
    for start, end, cap in matches:
        if deduped and start < deduped[-1][1]:
            continue  # overlaps a match already kept
        deduped.append((start, end, cap))
    return [cap for _, _, cap in deduped]


def _all_category_keyword_positions(window: str) -> List[Tuple[int, str]]:
    positions = []
    for cat, kw_re in _CATEGORY_KEYWORD_RE.items():
        for m in kw_re.finditer(window):
            positions.append((m.start(), cat))
    return positions


def _compute_exclusion_coverage(window: str, all_category_positions: List[Tuple[int, str]]) -> Dict[str, str]:
    """For each exclusion-signal occurrence, credits every category keyword
    found in its forward coverage span — from the signal to the next
    sentence/clause boundary, or ~100 characters, whichever is first — as
    "uncapped". A signal covering a coordinated list ("...shall not apply
    to claims arising from fraud or gross negligence.") correctly credits
    every category named in that list, not just the nearest one. Forward-
    only and boundary-limited so a LATER, unrelated exclusion signal for a
    different category elsewhere in the clause cannot bleed backward onto
    an earlier category's own super-cap language (see the multisupercap-01/
    -05 regression tests, both same-sentence, comma-joined clauses where
    backward attribution previously mis-credited the wrong category)."""
    covered: Dict[str, str] = {}
    for sig in _EXCLUSION_SIGNAL_RE.finditer(window):
        span_end = min(len(window), sig.end() + 100)
        coverage_text = window[sig.end():span_end]
        boundary = re.search(r"\.\s|;", coverage_text)
        boundary_pos = boundary.start() if boundary else None
        # "...X, AND liability for Y shall not exceed..." introduces a new
        # independent clause with its own cap, not a continuation of the
        # excluded-category list — truncate coverage at the "and" so Y's
        # keyword (here in the new clause's subject) isn't swept in too.
        for and_m in re.finditer(r"\band\b", coverage_text, re.I):
            if _CAP_TRIGGER_RE.search(coverage_text[and_m.end():and_m.end() + 60]):
                if boundary_pos is None or and_m.start() < boundary_pos:
                    boundary_pos = and_m.start()
                break
        if boundary_pos is not None:
            coverage_text = coverage_text[:boundary_pos]
        coverage_end = sig.end() + len(coverage_text)
        for pos, cat in all_category_positions:
            if sig.end() <= pos < coverage_end and cat not in covered:
                covered[cat] = _excerpt(window, sig.start(), coverage_end)
    return covered


def _classify_category(
    window: str, category: str, all_category_positions: List[Tuple[int, str]],
    exclusion_coverage: Dict[str, str],
) -> CategoryTreatment:
    keyword_re = _CATEGORY_KEYWORD_RE[category]
    occurrences = list(keyword_re.finditer(window))
    if not occurrences:
        return CategoryTreatment(category=category, treatment="not_addressed", established=True)

    m = occurrences[0]
    local_start = max(0, m.start() - _LOCAL_WINDOW_CHARS)
    local_end = min(len(window), m.end() + _LOCAL_WINDOW_CHARS)
    local = window[local_start:local_end]
    excerpt = _excerpt(window, m.start(), m.end())

    if category in exclusion_coverage:
        return CategoryTreatment(category=category, treatment="uncapped", raw_excerpt=excerpt, established=True)

    # A category-specific cap must be stated FORWARD of the category
    # keyword, in the SAME sentence — searching backward would let a nearby
    # but unrelated general cap get misattributed to this category as a
    # phantom super-cap, and searching past a sentence boundary ("...breaches
    # of willful misconduct. Aggregate liability shall not exceed 1x...")
    # would credit the *next* sentence's unrelated general cap the same way.
    forward_end = min(len(window), m.end() + _LOCAL_WINDOW_CHARS)
    forward_text = window[m.end():forward_end]
    boundary = re.search(r"\.\s", forward_text)
    same_sentence_text = forward_text[:boundary.start()] if boundary else forward_text
    forward_caps = _find_cap_values(same_sentence_text)
    if forward_caps:
        cap = forward_caps[0]
        cap.start_index += m.end()
        cap.end_index += m.end()
        return CategoryTreatment(category=category, treatment="super_cap", cap=cap, raw_excerpt=excerpt, established=True)

    if _AMBIGUITY_SIGNAL_RE.search(local):
        return CategoryTreatment(category=category, treatment="unresolved", raw_excerpt=excerpt, established=False)

    return CategoryTreatment(category=category, treatment="within_general_cap", raw_excerpt=excerpt, established=True)


def _classify_general_cap_expression(
    window: str, category_treatments: Dict[str, CategoryTreatment],
) -> CapExpression:
    claimed_spans = [
        (t.cap.start_index, t.cap.end_index) for t in category_treatments.values()
        if t.treatment == "super_cap" and t.cap is not None
    ]

    def _is_claimed(cap: CapValue) -> bool:
        return any(cap.start_index >= lo - 5 and cap.end_index <= hi + 5 for lo, hi in claimed_spans)

    # Greater-of / lesser-of: look for the signal, then extract the
    # component values from a window immediately around it.
    gl = _GREATER_LESSER_RE.search(window)
    if gl:
        structure = "greater_of" if gl.group("greater") else "lesser_of"
        local_end = min(len(window), gl.end() + 250)
        local_start = max(0, gl.start() - 40)
        components = [c for c in _find_cap_values(window[local_start:local_end]) if not _is_claimed(c)]
        for c in components:
            c.start_index += local_start
            c.end_index += local_start
        if len(components) >= 2:
            return CapExpression(
                structure=structure, components=components[:2],
                raw_excerpt=_excerpt(window, gl.start(), local_end - local_start + local_start, pad=0) or window[local_start:local_end].strip(),
                start_index=local_start, end_index=local_end,
            )
        # Signal present but couldn't extract both operands — don't guess.
        return _unresolved(
            f"a '{structure.replace('_', ' ')}' structure was signaled but its component values could not both be extracted",
            raw_excerpt=window[local_start:local_end].strip(), start_index=local_start, end_index=local_end,
        )

    # Per-claim vs. aggregate: two distinct scopes each with their own cap.
    per_claim_m = _PER_CLAIM_RE.search(window)
    aggregate_m = _AGGREGATE_SCOPE_RE.search(window)
    if per_claim_m and aggregate_m:
        pc_window = window[per_claim_m.start():min(len(window), per_claim_m.start() + 150)]
        ag_window = window[aggregate_m.start():min(len(window), aggregate_m.start() + 150)]
        pc_caps = [c for c in _find_cap_values(pc_window) if not _is_claimed(c)]
        ag_caps = [c for c in _find_cap_values(ag_window) if not _is_claimed(c)]
        if pc_caps and ag_caps:
            pc, ag = pc_caps[0], ag_caps[0]
            pc.start_index += per_claim_m.start()
            pc.end_index += per_claim_m.start()
            ag.start_index += aggregate_m.start()
            ag.end_index += aggregate_m.start()
            return CapExpression(
                structure="per_claim_and_aggregate", components=[pc, ag], roles=["per_claim", "aggregate"],
                raw_excerpt=_excerpt(window, min(pc.start_index, ag.start_index), max(pc.end_index, ag.end_index)),
                start_index=min(pc.start_index, ag.start_index), end_index=max(pc.end_index, ag.end_index),
            )

    # Fall back to the simple/conflict model: gather unclaimed cap values.
    all_caps = _find_cap_values(window)
    unclaimed = [c for c in all_caps if not _is_claimed(c)]
    if not unclaimed:
        return _simple(None)

    has_unlimited = any(c.kind == "unlimited" for c in unclaimed)
    numeric = [c for c in unclaimed if c.kind != "unlimited"]
    distinct_numeric_values = {(c.kind, c.multiplier, c.fixed_amount) for c in numeric}

    if has_unlimited and numeric:
        return _unresolved(
            "conflicting unlimited and numeric cap language for the general cap",
            raw_excerpt=_excerpt(window, unclaimed[0].start_index, unclaimed[0].end_index),
            start_index=unclaimed[0].start_index, end_index=unclaimed[0].end_index,
        )
    if has_unlimited:
        return _simple(unclaimed[0])
    if len(distinct_numeric_values) > 1:
        return _unresolved(
            "multiple distinct cap values found for the general clause; cannot determine which governs",
            raw_excerpt=_excerpt(window, numeric[0].start_index, numeric[0].end_index),
            start_index=numeric[0].start_index, end_index=numeric[0].end_index,
        )
    return _simple(numeric[0])


def _classify_consequential_damages(window: str) -> Tuple[Optional[bool], bool, List[str]]:
    m = _CONSEQUENTIAL_RE.search(window)
    if not m:
        return None, True, []  # not addressed at all — confidently "no exclusion found"
    local_start = max(0, m.start() - _LOCAL_WINDOW_CHARS)
    local_end = min(len(window), m.end() + _LOCAL_WINDOW_CHARS)
    local = window[local_start:local_end]
    carveouts = []
    if _CARVEOUT_PHRASE_RE.search(local):
        cv_local = local[max(0, m.start() - local_start):]
        for cat, kw_re in _CATEGORY_KEYWORD_RE.items():
            if kw_re.search(cv_local):
                carveouts.append(cat)
    if _EXCLUDE_PHRASE_RE.search(local):
        return True, True, carveouts
    return None, False, carveouts


def _find_party_positions(window: str) -> Dict[str, PartyPosition]:
    """Detects distinct named-role liability statements ('Customer's
    liability shall not exceed...', 'Vendor's liability is not subject
    to...') and their cap values. Two or more distinct roles with distinct
    cap expressions is the signal for a directional/asymmetric structure —
    see evaluate_liability_policy for how "ours" vs. "counterparty" is
    resolved from this."""
    positions: Dict[str, PartyPosition] = {}
    for m in _ROLE_POSITION_RE.finditer(window):
        role = m.group(1)
        role_key = role.lower()
        if role_key in positions:
            continue
        segment_end = min(len(window), m.end() + 150)
        segment = window[m.end():segment_end]
        # The role-position match already consumed the lead-in phrase
        # ("...is capped at"), so a bare "$1,000,000" left in the segment
        # won't match _FIXED_AMOUNT_RE's own required lead-in — restore a
        # synthetic one so the same tested cap-value patterns still apply.
        padding = "shall not exceed "
        caps = _find_cap_values(padding + segment)
        if not caps:
            continue
        cap = caps[0]
        cap.start_index += m.end() - len(padding)
        cap.end_index += m.end() - len(padding)
        side = "buy_side" if role_key in BUY_SIDE_ROLES else ("sell_side" if role_key in SELL_SIDE_ROLES else None)
        positions[role_key] = PartyPosition(role=role, side=side, cap_expression=_simple(cap))
    return positions


def _section_label_before(text: str, anchor_start: int) -> Optional[str]:
    look = text[max(0, anchor_start - _SECTION_LABEL_LOOKBACK):anchor_start]
    nums = re.findall(r"\d{1,3}(?:\.\d{1,2})?", look)
    return nums[-1] if nums else None


def _extract_provision(text: str, anchor_match: re.Match, index: int) -> Provision:
    window_start = anchor_match.start()
    window_end = min(len(text), window_start + _PROVISION_WINDOW_CHARS)
    window = text[window_start:window_end]

    all_cat_positions = _all_category_keyword_positions(window)
    exclusion_coverage = _compute_exclusion_coverage(window, all_cat_positions)
    category_treatments = {
        cat: _classify_category(window, cat, all_cat_positions, exclusion_coverage) for cat in CATEGORIES
    }
    general_cap_expr = _classify_general_cap_expression(window, category_treatments)
    consequential_excluded, consequential_established, carveouts = _classify_consequential_damages(window)
    party_positions = _find_party_positions(window)

    lookback_start = max(0, window_start - 300)
    is_amendment = bool(_AMENDMENT_SIGNAL_RE.search(text[lookback_start:window_end]))

    cap, _ = general_cap_expr.effective_cap() if general_cap_expr.structure != "unresolved" else (None, None)
    if general_cap_expr.components or general_cap_expr.structure == "unresolved":
        raw_excerpt = general_cap_expr.raw_excerpt or _excerpt(text, window_start, min(window_end, window_start + 300))
        start_index = window_start + general_cap_expr.start_index if general_cap_expr.raw_excerpt else window_start
        end_index = window_start + general_cap_expr.end_index if general_cap_expr.raw_excerpt else min(window_end, window_start + 300)
    else:
        raw_excerpt = _excerpt(text, window_start, min(window_end, window_start + 200))
        start_index = window_start
        end_index = min(window_end, window_start + 200)

    # Re-anchor every window-relative span to absolute document offsets.
    for c in general_cap_expr.components:
        c.start_index += window_start
        c.end_index += window_start
    for t in category_treatments.values():
        if t.cap is not None:
            t.cap.start_index += window_start
            t.cap.end_index += window_start
    for pp in party_positions.values():
        for c in pp.cap_expression.components:
            c.start_index += window_start
            c.end_index += window_start

    return Provision(
        index=index, section_label=_section_label_before(text, window_start), is_amendment=is_amendment,
        start_index=start_index, end_index=end_index, raw_excerpt=raw_excerpt,
        general_cap_expression=general_cap_expr, category_treatments=category_treatments,
        party_positions=party_positions, consequential_damages_excluded=consequential_excluded,
        consequential_damages_established=consequential_established, consequential_damages_carveouts=carveouts,
    )


def extract_liability_facts(text: str) -> Optional[LiabilityFacts]:
    """Discovers every Limitation-of-Liability-anchored provision in the
    full document (not just the first) and reconciles them. Returns None
    only when no such provision exists at all anywhere in the document."""
    anchors = list(_ANCHOR_RE.finditer(text))
    if not anchors:
        return None

    accepted_anchors = []
    for m in anchors:
        if accepted_anchors and m.start() - accepted_anchors[-1].start() < _ANCHOR_DEDUP_GAP:
            continue  # same clause mentioning itself again, not a new provision
        accepted_anchors.append(m)

    provisions = [_extract_provision(text, m, i) for i, m in enumerate(accepted_anchors)]

    if len(provisions) == 1:
        return LiabilityFacts(clause_found=True, provisions=provisions, controlling_provision=provisions[0],
                               reconciliation="single", reconciliation_explanation="Single provision found.")

    # Reconciliation: prefer an explicit amendment/restatement over the
    # provisions it supersedes. If multiple provisions carry an amendment
    # signal, the last one in document order is the most recent.
    amendment_provisions = [p for p in provisions if p.is_amendment]
    if amendment_provisions:
        controlling = amendment_provisions[-1]
        others = [p for p in provisions if p is not controlling]
        explanation = (
            f"{len(provisions)} Limitation of Liability provisions found; "
            f"{controlling.provision_label()} contains explicit amendment/restatement language "
            f"and supersedes {', '.join(p.provision_label() for p in others)}."
        )
        return LiabilityFacts(clause_found=True, provisions=provisions, controlling_provision=controlling,
                               reconciliation="amendment_resolved", reconciliation_explanation=explanation)

    # No amendment signal — if every provision's effective general cap
    # agrees, they're consistent (e.g. a clause quoted or cross-referenced
    # more than once); otherwise this is a genuine unreconciled conflict.
    effective_values = []
    all_resolved = True
    for p in provisions:
        cap, reason = p.general_cap_expression.effective_cap()
        if cap is None:
            all_resolved = False
            break
        effective_values.append((cap.kind, cap.multiplier, cap.fixed_amount))

    if all_resolved and len(set(effective_values)) == 1:
        explanation = f"{len(provisions)} Limitation of Liability provisions found, all stating the same cap."
        return LiabilityFacts(clause_found=True, provisions=provisions, controlling_provision=provisions[0],
                               reconciliation="consistent_duplicate", reconciliation_explanation=explanation)

    explanation = (
        f"{len(provisions)} Limitation of Liability provisions found with no explicit amendment/restatement "
        f"language tying them together, and their terms do not agree: "
        + "; ".join(f"{p.provision_label()}: {p.general_cap_expression.summary()}" for p in provisions)
        + ". Cannot determine which provision controls without attorney review."
    )
    return LiabilityFacts(clause_found=True, provisions=provisions, controlling_provision=None,
                           reconciliation="unreconciled", reconciliation_explanation=explanation)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _fmt_multiplier(value: Optional[float]) -> str:
    if value is None:
        return "unspecified"
    return f"{value:g}x annual fees"


def _build_ladder(policy: PolicyRuleLike, state: str) -> List[LadderStep]:
    steps = [
        LadderStep("IDEAL", f"Preferred position: {_fmt_multiplier(policy.preferred_multiplier)}", "not_reached"),
        LadderStep("ACCEPTABLE", f"Auto-accept up to {_fmt_multiplier(policy.acceptable_max_multiplier)}", "not_reached"),
        LadderStep("FALLBACK", f"Negotiate up to {_fmt_multiplier(policy.negotiate_max_multiplier)}", "not_reached"),
        LadderStep("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}", "not_reached"),
        LadderStep("WALK-AWAY", "Unlimited liability — prohibited by policy" if policy.prohibit_unlimited else "Unlimited liability", "not_reached"),
    ]
    if state not in _LADDER_ORDER:
        return steps
    idx = _LADDER_ORDER.index(state)
    for i, step in enumerate(steps):
        step.status = "passed" if i < idx else ("current" if i == idx else "not_reached")
    return steps


def _category_treatments_dict(provision: Provision) -> List[Dict[str, str]]:
    return [
        {
            "category": t.category, "treatment": t.treatment,
            "cap_summary": t.cap.summary() if t.cap else None,
            "raw_excerpt": t.raw_excerpt, "established": t.established,
        }
        for t in provision.category_treatments.values()
    ]


def _resolve_directional_position(
    provision: Provision, policy: PolicyRuleLike,
) -> Tuple[Optional[CapExpression], Optional[Dict[str, str]], Optional[Dict[str, str]], Optional[str]]:
    """When a provision states 2+ distinct named-role positions with
    different cap expressions, determines which is "ours" per
    policy.contract_side. Returns (our_cap_expression, our_position_dict,
    counterparty_position_dict, unresolved_reason). Never silently returns
    only the recognized side — an unrecognized or unmappable role pair
    yields (None, None, None, reason) so the caller abstains."""
    positions = list(provision.party_positions.values())
    if len(positions) < 2:
        return None, None, None, None  # not a directional structure at all

    distinct_values = {
        (pp.cap_expression.components[0].kind, pp.cap_expression.components[0].compare_key())
        for pp in positions if pp.cap_expression.components
    }
    if len(distinct_values) <= 1:
        return None, None, None, None  # all sides state the same position — not asymmetric

    if policy.contract_side == "mutual":
        return None, None, None, (
            "contract defines asymmetric liability positions by party, but this playbook is "
            "configured for a mutual position — cannot determine which cap applies to us"
        )

    our_side = policy.contract_side
    ours = [pp for pp in positions if pp.side == our_side]
    theirs = [pp for pp in positions if pp.side is not None and pp.side != our_side]
    if len(ours) != 1 or len(theirs) != 1:
        return None, None, None, (
            "contract defines asymmetric liability positions but the named parties "
            "(" + ", ".join(pp.role for pp in positions) + ") could not be confidently mapped "
            f"to our configured contract side ({our_side})"
        )
    our_pp, their_pp = ours[0], theirs[0]
    our_dict = {"role": our_pp.role, "summary": our_pp.cap_expression.summary()}
    their_dict = {"role": their_pp.role, "summary": their_pp.cap_expression.summary()}
    return our_pp.cap_expression, our_dict, their_dict, None


def evaluate_liability_policy(
    facts: Optional[LiabilityFacts],
    policy: PolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    """Deterministic state machine: structured contract facts x PolicyRule
    thresholds -> one authoritative PolicyDecision, or REQUIRES_REVIEW when
    a fact the decision depends on cannot be reliably established
    (unreconciled provisions, a compound cap that doesn't reduce to one
    comparable value, an unmappable directional structure, ambiguous
    category carve-out language). No confidence score at any branch."""
    if facts is None or not facts.clause_found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="limitation_of_liability", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No limitation-of-liability clause found",
            policy_limit_summary=_fmt_multiplier(policy.preferred_multiplier),
            required_action="None — this contract does not address liability caps",
            explanation="No limitation-of-liability clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source,
        )

    if facts.reconciliation == "unreconciled":
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="limitation_of_liability", state=REQUIRES_REVIEW,
            contract_language=facts.reconciliation_explanation,
            extracted_summary="Multiple unreconciled provisions",
            policy_limit_summary=_fmt_multiplier(policy.negotiate_max_multiplier),
            required_action="Manual review required — " + facts.reconciliation_explanation,
            explanation=facts.reconciliation_explanation,
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[],
            unresolved_facts=["controlling provision could not be determined among multiple candidates"],
            start_index=facts.provisions[0].start_index, end_index=facts.provisions[0].end_index,
            source=source, reconciliation=facts.reconciliation,
        )

    provision = facts.controlling_provision
    controlling_provision_dict = {
        "label": provision.provision_label(), "excerpt": provision.raw_excerpt,
        "start_index": provision.start_index, "end_index": provision.end_index,
    }
    required_exceptions = list(policy.required_exceptions_json or [])
    unresolved_facts: List[str] = []

    # Directional resolution — only engages when 2+ distinct role positions exist.
    directional_cap_expr, our_position, counterparty_position, directional_reason = _resolve_directional_position(
        provision, policy,
    )
    if directional_reason:
        unresolved_facts.append(f"directional liability position ({directional_reason})")
    general_cap_expr = directional_cap_expr if directional_cap_expr is not None else provision.general_cap_expression

    general_cap, general_cap_reason = general_cap_expr.effective_cap()
    if general_cap_reason:
        unresolved_facts.append(f"general liability cap ({general_cap_reason})")

    for cat in required_exceptions:
        treatment = provision.category_treatments.get(cat)
        if treatment is not None and treatment.treatment == "unresolved":
            unresolved_facts.append(f"{cat} treatment (ambiguous carve-out language)")

    if policy.require_consequential_damages_exclusion and not provision.consequential_damages_established:
        unresolved_facts.append("consequential damages exclusion (ambiguous language)")

    if unresolved_facts:
        state = REQUIRES_REVIEW
        explanation = (
            f"Contract language: \"{provision.raw_excerpt}\". This clause could not be evaluated "
            f"deterministically — the following fact(s) required for a policy decision could not be "
            f"reliably established: {'; '.join(unresolved_facts)}. Result: {state}."
        )
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="limitation_of_liability", state=state,
            contract_language=provision.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary=_fmt_multiplier(policy.negotiate_max_multiplier),
            required_action="Manual review required — " + "; ".join(unresolved_facts),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=_category_treatments_dict(provision), unresolved_facts=unresolved_facts,
            start_index=provision.start_index, end_index=provision.end_index, source=source,
            controlling_provision=controlling_provision_dict, our_position=our_position,
            counterparty_position=counterparty_position, reconciliation=facts.reconciliation,
        )

    missing_exceptions = [
        cat for cat in required_exceptions
        if provision.category_treatments.get(cat) is not None
        and provision.category_treatments[cat].treatment not in ("uncapped", "super_cap")
    ]
    missing_consequential = (
        policy.require_consequential_damages_exclusion
        and provision.consequential_damages_excluded is not True
    )
    missing_consequential_carveouts = []
    if policy.require_consequential_damages_exclusion and provision.consequential_damages_excluded is True:
        missing_consequential_carveouts = [
            c for c in (policy.required_consequential_carveouts_json or [])
            if c not in provision.consequential_damages_carveouts
        ]

    if general_cap is None:
        state = MUST_REDLINE
        extracted_summary = "Limitation-of-liability clause present but no numeric general cap stated"
        required_action = "Redline — insert the approved cap language"
        explanation = (
            f"Contract language: \"{provision.raw_excerpt}\". A limitation-of-liability clause exists but "
            f"states no enforceable numeric general cap. Company policy requires a stated cap. Result: {state}."
        )
    elif general_cap.kind == "unlimited":
        state = PROHIBITED if policy.prohibit_unlimited else ESCALATE
        extracted_summary = "Unlimited liability"
        required_action = "Replace clause — apply the approved fallback cap" if state == PROHIBITED else "Escalate for approval — unlimited liability exceeds policy"
        explanation = (
            f"Contract language: \"{provision.raw_excerpt}\". Extracted value: Unlimited. "
            f"Company policy: unlimited liability is {'prohibited' if policy.prohibit_unlimited else 'permitted only with escalation'}. "
            f"Result: {state}."
        )
    elif general_cap.kind == "fixed_amount":
        state = ESCALATE
        extracted_summary = general_cap.summary()
        required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — cap is a fixed dollar amount, not a fees multiplier; compare manually against policy"
        explanation = (
            f"Contract language: \"{provision.raw_excerpt}\". Extracted value: {general_cap.summary()}. "
            f"Policy is defined as a multiplier of annual fees, so this cannot be compared automatically. Result: {state}."
        )
    else:  # fee_multiplier
        value = general_cap.multiplier
        extracted_summary = general_cap.summary()
        if policy.preferred_multiplier is not None and value <= policy.preferred_multiplier:
            state = ACCEPT
        elif policy.acceptable_max_multiplier is not None and value <= policy.acceptable_max_multiplier:
            state = ACCEPT_WITH_NOTE
        elif policy.negotiate_max_multiplier is not None and value <= policy.negotiate_max_multiplier:
            state = NEGOTIATE
        else:
            state = ESCALATE

        if state in (ACCEPT, ACCEPT_WITH_NOTE) and (missing_exceptions or missing_consequential or missing_consequential_carveouts):
            state = NEGOTIATE

        notes = []
        if missing_exceptions:
            notes.append(f"missing required exception(s): {', '.join(missing_exceptions)}")
        if missing_consequential:
            notes.append("policy requires a consequential-damages exclusion, which was not found")
        if missing_consequential_carveouts:
            notes.append(f"consequential-damages exclusion missing required carve-out(s): {', '.join(missing_consequential_carveouts)}")

        if state == ACCEPT:
            required_action = "None — clause meets preferred position"
        elif state == ACCEPT_WITH_NOTE:
            required_action = "None — within acceptable range, note for the file"
        elif state == NEGOTIATE:
            required_action = "Negotiate down to preferred position" + (f"; {'; '.join(notes)}" if notes else "")
        else:
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — exceeds negotiable range"

        explanation = (
            f"Contract language: \"{provision.raw_excerpt}\". Extracted value: {general_cap.summary()}. "
            f"Policy — preferred: {_fmt_multiplier(policy.preferred_multiplier)}, "
            f"acceptable up to: {_fmt_multiplier(policy.acceptable_max_multiplier)}, "
            f"negotiable up to: {_fmt_multiplier(policy.negotiate_max_multiplier)}. "
            f"Result: {state}."
        )
        if notes and state == NEGOTIATE:
            explanation += " " + "; ".join(notes).capitalize() + "."

    return PolicyDecision(
        rule_id=RULE_ID, clause_type="limitation_of_liability", state=state,
        contract_language=provision.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary=_fmt_multiplier(policy.negotiate_max_multiplier),
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, state),
        category_treatments=_category_treatments_dict(provision), unresolved_facts=unresolved_facts,
        start_index=provision.start_index, end_index=provision.end_index,
        escalate_to=policy.escalation_approval_authority if state in (ESCALATE, PROHIBITED) else None,
        fallback_text=policy.fallback_text if state in (MUST_REDLINE, PROHIBITED, NEGOTIATE) else None,
        source=source, controlling_provision=controlling_provision_dict,
        our_position=our_position, counterparty_position=counterparty_position,
        reconciliation=facts.reconciliation,
    )


# Backward-compatible alias for the pre-hardening single-fact API name.
extract_liability_cap = extract_liability_facts
