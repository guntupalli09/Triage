"""
Deterministic Limitation-of-Liability Policy Engine.

Vertical slice of the policy-first playbook design: extracts the liability
POSITION actually stated in a contract — not a single number — then
evaluates it against a PolicyRule's positions to produce one authoritative
decision state. Policy enforcement is a yes/no/escalate question, never a
confidence score.

Real limitation-of-liability clauses are rarely one number. They commonly
combine:
  - a general cap (fee multiplier or fixed dollar amount)
  - category-specific carve-outs that raise, remove, or otherwise change
    the cap for particular claim types (data breach, IP infringement,
    confidentiality, indemnification, fraud, gross negligence, willful
    misconduct)
  - a consequential/indirect-damages exclusion, itself sometimes carved
    back out for certain breaches
  - asymmetric (unilateral) caps that differ by named party

Collapsing that into a single multiplier and comparing it against policy
produces a deterministic answer that can be confidently wrong — worse than
an uncertain one, because the product presents it as authoritative. So this
module extracts a structured LiabilityFacts record with an explicit
per-fact established/unresolved flag, and the evaluator refuses to reach a
policy verdict when a fact it needs cannot be reliably established: it
returns REQUIRES_REVIEW naming exactly what couldn't be determined, instead
of guessing.

States (mirrors the negotiation ladder a lawyer actually works through):
    ACCEPT               — at or better than the preferred position
    ACCEPT_WITH_NOTE      — within the auto-accept range, but not the ideal ask
    NEGOTIATE             — above auto-accept but within the negotiable range
    MUST_REDLINE          — no enforceable general cap stated; policy requires one
    PROHIBITED            — unlimited liability, and policy prohibits it
    ESCALATE              — above the negotiable range; requires named approval
    REQUIRES_REVIEW       — a fact needed for the decision could not be reliably
                            established (ambiguous/conflicting clause language)
    NOT_APPLICABLE         — no limitation-of-liability clause found at all

Every decision carries the deterministic evidence that produced it (rule id,
extracted contract language, the exact policy thresholds compared against,
and — for REQUIRES_REVIEW — exactly which facts and why) so it can be
explained the same way twice, and an attorney can see exactly why before
accepting or overriding it.
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
# Stable public identifiers — used by callers (e.g. the playbook form) to
# render/validate required-exception checkboxes.
EXCEPTION_TYPES = list(CATEGORIES)

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
    r"|shall have unlimited liability",
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
_AMBIGUITY_SIGNAL_RE = re.compile(
    r"notwithstanding|provided,?\s+however|except as otherwise (?:set forth|provided)|subject to the foregoing",
    re.I,
)
_MUTUAL_PHRASE_RE = re.compile(r"\beither party\b|\bboth parties\b|\bneither party\b", re.I)
_ROLE_LIABILITY_RE = re.compile(r"\b([A-Z][A-Za-z]{2,20})(?:'s| shall not be)\b[^.]{0,30}\bliab", re.I)
_CONSEQUENTIAL_RE = re.compile(r"\b(consequential|indirect|special|incidental|punitive)\b[^.]{0,60}\bdamages\b", re.I)
_EXCLUDE_PHRASE_RE = re.compile(
    r"shall not be liable for|no party shall be liable|in no event shall (?:either|any) part(?:y|ies) be liable",
    re.I,
)
_CARVEOUT_PHRASE_RE = re.compile(r"except for|other than|excluding breaches of|with respect to", re.I)

_WINDOW_CHARS = 3000
_LOCAL_WINDOW_CHARS = 180


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


@dataclass
class CategoryTreatment:
    category: str
    # "uncapped" | "super_cap" | "within_general_cap" | "not_addressed" | "unresolved"
    treatment: str
    cap: Optional[CapValue] = None
    raw_excerpt: str = ""
    established: bool = True


@dataclass
class LiabilityFacts:
    clause_found: bool
    general_cap: Optional[CapValue] = None
    general_cap_established: bool = True
    general_cap_unresolved_reason: str = ""
    category_treatments: Dict[str, CategoryTreatment] = field(default_factory=dict)
    consequential_damages_excluded: Optional[bool] = None  # None = not addressed / can't tell
    consequential_damages_established: bool = True
    consequential_damages_carveouts: List[str] = field(default_factory=list)
    mutuality: str = "unresolved"  # "mutual" | "unilateral" | "unresolved"
    raw_clause_excerpt: str = ""
    start_index: Optional[int] = None
    end_index: Optional[int] = None


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
        }


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


def _classify_category(window: str, category: str) -> CategoryTreatment:
    keyword_re = _CATEGORY_KEYWORD_RE[category]
    occurrences = list(keyword_re.finditer(window))
    if not occurrences:
        return CategoryTreatment(category=category, treatment="not_addressed", established=True)

    # Use the first occurrence's local context — later ones are typically
    # cross-references to the same treatment already established.
    m = occurrences[0]
    local_start = max(0, m.start() - _LOCAL_WINDOW_CHARS)
    local_end = min(len(window), m.end() + _LOCAL_WINDOW_CHARS)
    local = window[local_start:local_end]
    excerpt = _excerpt(window, m.start(), m.end())

    if _EXCLUSION_SIGNAL_RE.search(local):
        return CategoryTreatment(category=category, treatment="uncapped", raw_excerpt=excerpt, established=True)

    # A category-specific cap must be stated FORWARD of the category
    # keyword ("...in the event of a data breach, liability shall not
    # exceed 2x...") — searching backward as well would let a nearby but
    # unrelated general cap ("...exceed 1x... notwithstanding fraud...")
    # get misattributed to this category as a phantom super-cap.
    forward_end = min(len(window), m.end() + _LOCAL_WINDOW_CHARS)
    forward_caps = _find_cap_values(window[m.end():forward_end])
    if forward_caps:
        cap = forward_caps[0]
        cap.start_index += m.end()
        cap.end_index += m.end()
        return CategoryTreatment(category=category, treatment="super_cap", cap=cap, raw_excerpt=excerpt, established=True)

    if _AMBIGUITY_SIGNAL_RE.search(local):
        return CategoryTreatment(
            category=category, treatment="unresolved", raw_excerpt=excerpt, established=False,
        )

    return CategoryTreatment(category=category, treatment="within_general_cap", raw_excerpt=excerpt, established=True)


def _classify_general_cap(window: str, category_treatments: Dict[str, CategoryTreatment]) -> Tuple[Optional[CapValue], bool, str]:
    """Determines the general (non-category-specific) cap by excluding any
    cap-value span already claimed as a category super-cap. Returns
    (cap_or_none, established, unresolved_reason)."""
    claimed_spans = [
        (t.cap.start_index, t.cap.end_index) for t in category_treatments.values()
        if t.treatment == "super_cap" and t.cap is not None
    ]
    all_caps = _find_cap_values(window)

    def _is_claimed(cap: CapValue) -> bool:
        return any(cap.start_index >= lo - 5 and cap.end_index <= hi + 5 for lo, hi in claimed_spans)

    unclaimed = [c for c in all_caps if not _is_claimed(c)]
    if not unclaimed:
        return None, True, ""

    has_unlimited = any(c.kind == "unlimited" for c in unclaimed)
    numeric = [c for c in unclaimed if c.kind != "unlimited"]
    distinct_numeric_values = {
        (c.kind, c.multiplier, c.fixed_amount) for c in numeric
    }

    if has_unlimited and numeric:
        return None, False, "conflicting unlimited and numeric cap language for the general cap"
    if has_unlimited:
        return unclaimed[0], True, ""
    if len(distinct_numeric_values) > 1:
        return None, False, "multiple distinct cap values found for the general clause; cannot determine which governs"
    return numeric[0], True, ""


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
    # Consequential damages are discussed but neither a clear exclusion nor
    # inclusion phrase was found nearby — genuinely ambiguous.
    return None, False, carveouts


def _classify_mutuality(window: str) -> str:
    if _MUTUAL_PHRASE_RE.search(window):
        return "mutual"
    roles = {m.group(1) for m in _ROLE_LIABILITY_RE.finditer(window)}
    if len(roles) >= 2:
        return "unilateral"
    return "unresolved"


def extract_liability_facts(text: str) -> Optional[LiabilityFacts]:
    """Locates the limitation-of-liability clause (if any) and extracts a
    structured LiabilityFacts record. Returns None when no such clause
    exists at all — the caller should treat that as NOT_APPLICABLE."""
    anchor = _ANCHOR_RE.search(text)
    if not anchor:
        return None

    window_start = anchor.start()
    window_end = min(len(text), window_start + _WINDOW_CHARS)
    window = text[window_start:window_end]

    category_treatments = {cat: _classify_category(window, cat) for cat in CATEGORIES}
    general_cap, general_established, general_reason = _classify_general_cap(window, category_treatments)
    consequential_excluded, consequential_established, carveouts = _classify_consequential_damages(window)
    mutuality = _classify_mutuality(window)

    if general_cap is not None:
        raw_clause_excerpt = general_cap.raw_excerpt
        start_index = window_start + general_cap.start_index
        end_index = window_start + general_cap.end_index
    elif not general_established:
        # Ambiguous — anchor the excerpt on the clause opening so the
        # reviewer sees the actual conflicting language, not a guess.
        raw_clause_excerpt = _excerpt(text, window_start, min(window_end, window_start + 300))
        start_index = window_start
        end_index = min(window_end, window_start + 300)
    else:
        raw_clause_excerpt = _excerpt(text, window_start, min(window_end, window_start + 200))
        start_index = window_start
        end_index = min(window_end, window_start + 200)

    # Re-anchor category/general excerpts and super-cap spans to absolute
    # document offsets now that window-relative extraction is complete.
    for t in category_treatments.values():
        if t.cap is not None:
            t.cap.start_index += window_start
            t.cap.end_index += window_start

    return LiabilityFacts(
        clause_found=True,
        general_cap=general_cap, general_cap_established=general_established,
        general_cap_unresolved_reason=general_reason,
        category_treatments=category_treatments,
        consequential_damages_excluded=consequential_excluded,
        consequential_damages_established=consequential_established,
        consequential_damages_carveouts=carveouts,
        mutuality=mutuality,
        raw_clause_excerpt=raw_clause_excerpt, start_index=start_index, end_index=end_index,
    )


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
        # REQUIRES_REVIEW / NOT_APPLICABLE / MUST_REDLINE haven't reached a
        # ladder position yet — nothing "passed", nothing "current".
        return steps
    idx = _LADDER_ORDER.index(state)
    for i, step in enumerate(steps):
        step.status = "passed" if i < idx else ("current" if i == idx else "not_reached")
    return steps


def _category_treatments_dict(facts: LiabilityFacts) -> List[Dict[str, str]]:
    return [
        {
            "category": t.category, "treatment": t.treatment,
            "cap_summary": t.cap.summary() if t.cap else None,
            "raw_excerpt": t.raw_excerpt, "established": t.established,
        }
        for t in facts.category_treatments.values()
    ]


def evaluate_liability_policy(
    facts: Optional[LiabilityFacts],
    policy: PolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    """Deterministic state machine: structured contract facts x PolicyRule
    thresholds -> one authoritative PolicyDecision — or REQUIRES_REVIEW when
    a fact the decision depends on could not be reliably established. No
    confidence score at any branch: every path is a rule comparison or an
    explicit refusal to guess, never a probability estimate."""
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

    required_exceptions = list(policy.required_exceptions_json or [])
    unresolved_facts: List[str] = []

    if not facts.general_cap_established:
        unresolved_facts.append(f"general liability cap ({facts.general_cap_unresolved_reason})")

    for cat in required_exceptions:
        treatment = facts.category_treatments.get(cat)
        if treatment is not None and treatment.treatment == "unresolved":
            unresolved_facts.append(f"{cat} treatment (ambiguous carve-out language)")

    if unresolved_facts:
        state = REQUIRES_REVIEW
        explanation = (
            f"Contract language: \"{facts.raw_clause_excerpt}\". This clause could not be evaluated "
            f"deterministically — the following fact(s) required for a policy decision could not be "
            f"reliably established: {'; '.join(unresolved_facts)}. Result: {state}."
        )
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="limitation_of_liability", state=state,
            contract_language=facts.raw_clause_excerpt,
            extracted_summary="Could not be reliably established",
            policy_limit_summary=_fmt_multiplier(policy.negotiate_max_multiplier),
            required_action="Manual review required — " + "; ".join(unresolved_facts),
            explanation=explanation,
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=_category_treatments_dict(facts), unresolved_facts=unresolved_facts,
            start_index=facts.start_index, end_index=facts.end_index, source=source,
        )

    missing_exceptions = [
        cat for cat in required_exceptions
        if facts.category_treatments.get(cat) is not None
        and facts.category_treatments[cat].treatment not in ("uncapped", "super_cap")
    ]

    if facts.general_cap is None:
        state = MUST_REDLINE
        extracted_summary = "Limitation-of-liability clause present but no numeric general cap stated"
        required_action = "Redline — insert the approved cap language"
        explanation = (
            f"Contract language: \"{facts.raw_clause_excerpt}\". A limitation-of-liability clause exists but "
            f"states no enforceable numeric general cap. Company policy requires a stated cap. Result: {state}."
        )
    elif facts.general_cap.kind == "unlimited":
        state = PROHIBITED if policy.prohibit_unlimited else ESCALATE
        extracted_summary = "Unlimited liability"
        required_action = "Replace clause — apply the approved fallback cap" if state == PROHIBITED else "Escalate for approval — unlimited liability exceeds policy"
        explanation = (
            f"Contract language: \"{facts.raw_clause_excerpt}\". Extracted value: Unlimited. "
            f"Company policy: unlimited liability is {'prohibited' if policy.prohibit_unlimited else 'permitted only with escalation'}. "
            f"Result: {state}."
        )
    elif facts.general_cap.kind == "fixed_amount":
        state = ESCALATE
        extracted_summary = facts.general_cap.summary()
        required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — cap is a fixed dollar amount, not a fees multiplier; compare manually against policy"
        explanation = (
            f"Contract language: \"{facts.raw_clause_excerpt}\". Extracted value: {facts.general_cap.summary()}. "
            f"Policy is defined as a multiplier of annual fees, so this cannot be compared automatically. Result: {state}."
        )
    else:  # fee_multiplier
        value = facts.general_cap.multiplier
        extracted_summary = facts.general_cap.summary()
        if policy.preferred_multiplier is not None and value <= policy.preferred_multiplier:
            state = ACCEPT
        elif policy.acceptable_max_multiplier is not None and value <= policy.acceptable_max_multiplier:
            state = ACCEPT_WITH_NOTE
        elif policy.negotiate_max_multiplier is not None and value <= policy.negotiate_max_multiplier:
            state = NEGOTIATE
        else:
            state = ESCALATE

        if state in (ACCEPT, ACCEPT_WITH_NOTE) and missing_exceptions:
            state = NEGOTIATE

        if state == ACCEPT:
            required_action = "None — clause meets preferred position"
        elif state == ACCEPT_WITH_NOTE:
            required_action = "None — within acceptable range, note for the file"
        elif state == NEGOTIATE:
            required_action = "Negotiate down to preferred position" + (
                f"; missing required exception(s): {', '.join(missing_exceptions)}" if missing_exceptions else ""
            )
        else:
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — exceeds negotiable range"

        explanation = (
            f"Contract language: \"{facts.raw_clause_excerpt}\". Extracted value: {facts.general_cap.summary()}. "
            f"Policy — preferred: {_fmt_multiplier(policy.preferred_multiplier)}, "
            f"acceptable up to: {_fmt_multiplier(policy.acceptable_max_multiplier)}, "
            f"negotiable up to: {_fmt_multiplier(policy.negotiate_max_multiplier)}. "
            f"Result: {state}."
        )
        if missing_exceptions and state == NEGOTIATE:
            explanation += f" Required exception(s) not satisfied in clause: {', '.join(missing_exceptions)}."

    return PolicyDecision(
        rule_id=RULE_ID, clause_type="limitation_of_liability", state=state,
        contract_language=facts.raw_clause_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary=_fmt_multiplier(policy.negotiate_max_multiplier),
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, state),
        category_treatments=_category_treatments_dict(facts), unresolved_facts=unresolved_facts,
        start_index=facts.start_index, end_index=facts.end_index,
        escalate_to=policy.escalation_approval_authority if state in (ESCALATE, PROHIBITED) else None,
        fallback_text=policy.fallback_text if state in (MUST_REDLINE, PROHIBITED, NEGOTIATE) else None,
        source=source,
    )


# Backward-compatible aliases for the pre-hardening single-fact API name.
extract_liability_cap = extract_liability_facts
