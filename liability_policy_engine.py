"""
Deterministic Limitation-of-Liability Policy Engine.

Vertical slice of the policy-first playbook design: extracts the liability
cap actually stated in a contract (as a multiplier of annual fees, a fixed
dollar amount, "unlimited", or "not stated"), then evaluates it against a
PolicyRule's positions to produce one authoritative decision state — never
a confidence score. Policy enforcement is a yes/no/escalate question, not a
probability.

States (mirrors the negotiation ladder a lawyer actually works through):
    ACCEPT              — at or better than the preferred position
    ACCEPT_WITH_NOTE     — within the auto-accept range, but not the ideal ask
    NEGOTIATE            — above auto-accept but within the negotiable range
    MUST_REDLINE         — no enforceable cap stated; policy requires one
    PROHIBITED           — unlimited liability, and policy prohibits it
    ESCALATE             — above the negotiable range; requires named approval
    NOT_APPLICABLE        — no limitation-of-liability clause found at all

Every decision carries the deterministic evidence that produced it (rule id,
extracted contract language, the exact policy thresholds compared against)
so it can be explained the same way twice, and an attorney can see exactly
why before accepting or overriding it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Protocol


RULE_ID = "POLICY_LOL_CAP"

# States, in ladder order — used both for evaluation and for rendering the
# negotiation ladder (IDEAL -> ACCEPTABLE -> FALLBACK -> ESCALATE -> WALK-AWAY).
ACCEPT = "ACCEPT"
ACCEPT_WITH_NOTE = "ACCEPT_WITH_NOTE"
NEGOTIATE = "NEGOTIATE"
MUST_REDLINE = "MUST_REDLINE"
PROHIBITED = "PROHIBITED"
ESCALATE = "ESCALATE"
NOT_APPLICABLE = "NOT_APPLICABLE"

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

_EXCEPTION_KEYWORDS = {
    "fraud": r"\bfraud\b",
    "gross_negligence": r"\bgross negligence\b|\bwillful misconduct\b",
    "ip_infringement": r"\bintellectual property\b.{0,40}\binfringement\b|\bIP infringement\b",
    "confidentiality": r"\bconfidentiality\b.{0,40}\bbreach\b|\bbreach of confidentiality\b",
    "indemnification": r"\bindemnif",
    "data_breach": r"\bdata breach\b|\bsecurity breach\b",
}

# Public, stable identifiers for the exception types above — used by callers
# (e.g. the playbook form) to validate/render checkboxes without reaching
# into the module's private regex table.
EXCEPTION_TYPES = list(_EXCEPTION_KEYWORDS.keys())

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
    r"(?:maximum(?:\s+aggregate)?\s+liability(?:\s+of\s+(?:either\s+party)?)?\s*(?:shall\s+not\s+exceed|of|:)?"
    r"|liable\s+for\s+(?:an\s+amount\s+)?(?:in\s+excess\s+of|more\s+than)"
    r"|shall\s+not\s+exceed)\s*\$\s*([\d,]+(?:\.\d{2})?)",
    re.I,
)
_WINDOW_CHARS = 3000


@dataclass
class LiabilityCapExtraction:
    found: bool
    cap_type: str  # "multiplier" | "fixed_amount" | "unlimited" | "not_stated"
    multiplier: Optional[float] = None
    fixed_amount: Optional[float] = None
    raw_excerpt: str = ""
    start_index: int = 0
    end_index: int = 0
    exceptions_found: List[str] = field(default_factory=list)


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
            "start_index": self.start_index,
            "end_index": self.end_index,
            "escalate_to": self.escalate_to,
            "fallback_text": self.fallback_text,
            "source": self.source,
        }


def _find_exceptions(window: str) -> List[str]:
    return [name for name, pattern in _EXCEPTION_KEYWORDS.items() if re.search(pattern, window, re.I)]


def _excerpt(text: str, start: int, end: int, pad: int = 60) -> str:
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    # Widen to the nearest word boundary so the excerpt doesn't open/close
    # mid-word — cosmetic, but this text is quoted verbatim as "contract
    # language" evidence in the decision explanation.
    if lo > 0:
        space = text.rfind(" ", 0, lo)
        if space != -1:
            lo = space + 1
    if hi < len(text):
        space = text.find(" ", hi)
        if space != -1:
            hi = space
    return text[lo:hi].strip()


def extract_liability_cap(text: str) -> Optional[LiabilityCapExtraction]:
    """Locates the limitation-of-liability clause (if any) and extracts a
    normalized cap value. Returns None when no such clause exists at all
    (the caller should treat that as NOT_APPLICABLE, not "not stated" —
    a contract with no liability section isn't silently missing a cap, it
    simply doesn't address the topic)."""
    anchor = _ANCHOR_RE.search(text)
    if not anchor:
        return None

    window_start = anchor.start()
    window_end = min(len(text), window_start + _WINDOW_CHARS)
    window = text[window_start:window_end]
    exceptions = _find_exceptions(window)

    m = _UNLIMITED_RE.search(window)
    if m:
        abs_start, abs_end = window_start + m.start(), window_start + m.end()
        return LiabilityCapExtraction(
            found=True, cap_type="unlimited",
            raw_excerpt=_excerpt(text, abs_start, abs_end),
            start_index=abs_start, end_index=abs_end, exceptions_found=exceptions,
        )

    m = _MULTIPLIER_NUM_RE.search(window)
    if m:
        abs_start, abs_end = window_start + m.start(), window_start + m.end()
        return LiabilityCapExtraction(
            found=True, cap_type="multiplier", multiplier=float(m.group(1)),
            raw_excerpt=_excerpt(text, abs_start, abs_end),
            start_index=abs_start, end_index=abs_end, exceptions_found=exceptions,
        )

    m = _MULTIPLIER_WORD_RE.search(window)
    if m:
        abs_start, abs_end = window_start + m.start(), window_start + m.end()
        return LiabilityCapExtraction(
            found=True, cap_type="multiplier", multiplier=float(_WORD_NUMBERS[m.group(1).lower()]),
            raw_excerpt=_excerpt(text, abs_start, abs_end),
            start_index=abs_start, end_index=abs_end, exceptions_found=exceptions,
        )

    m = _FIXED_AMOUNT_RE.search(window)
    if m:
        abs_start, abs_end = window_start + m.start(), window_start + m.end()
        return LiabilityCapExtraction(
            found=True, cap_type="fixed_amount", fixed_amount=float(m.group(1).replace(",", "")),
            raw_excerpt=_excerpt(text, abs_start, abs_end),
            start_index=abs_start, end_index=abs_end, exceptions_found=exceptions,
        )

    # A limitation-of-liability heading/clause exists but no extractable
    # numeric cap was found in it — genuinely different from "no clause at
    # all" (NOT_APPLICABLE): the topic is addressed, the position isn't clear.
    return LiabilityCapExtraction(
        found=True, cap_type="not_stated",
        raw_excerpt=_excerpt(text, window_start, min(window_end, window_start + 200)),
        start_index=anchor.start(), end_index=min(window_end, anchor.start() + 200),
        exceptions_found=exceptions,
    )


def _fmt_multiplier(value: Optional[float]) -> str:
    if value is None:
        return "unspecified"
    return f"{value:g}x annual fees"


def _build_ladder(policy: PolicyRuleLike, state: str) -> List[LadderStep]:
    order = [ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, ESCALATE, PROHIBITED]
    steps = [
        LadderStep("IDEAL", f"Preferred position: {_fmt_multiplier(policy.preferred_multiplier)}", "not_reached"),
        LadderStep("ACCEPTABLE", f"Auto-accept up to {_fmt_multiplier(policy.acceptable_max_multiplier)}", "not_reached"),
        LadderStep("FALLBACK", f"Negotiate up to {_fmt_multiplier(policy.negotiate_max_multiplier)}", "not_reached"),
        LadderStep("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}", "not_reached"),
        LadderStep("WALK-AWAY", "Unlimited liability — prohibited by policy" if policy.prohibit_unlimited else "Unlimited liability", "not_reached"),
    ]
    idx = order.index(state) if state in order else len(order) - 1
    for i, step in enumerate(steps):
        step.status = "passed" if i < idx else ("current" if i == idx else "not_reached")
    return steps


def evaluate_liability_policy(
    extraction: Optional[LiabilityCapExtraction],
    policy: PolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    """Deterministic state machine: contract-extracted cap x PolicyRule
    thresholds -> one authoritative PolicyDecision. No confidence score —
    every branch is a rule comparison, not a probability estimate."""
    if extraction is None or not extraction.found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="limitation_of_liability", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No limitation-of-liability clause found",
            policy_limit_summary=_fmt_multiplier(policy.preferred_multiplier),
            required_action="None — this contract does not address liability caps",
            explanation="No limitation-of-liability clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), start_index=None, end_index=None,
            source=source,
        )

    required_exceptions = list(policy.required_exceptions_json or [])
    missing_exceptions = [e for e in required_exceptions if e not in extraction.exceptions_found]

    if extraction.cap_type == "unlimited":
        state = PROHIBITED if policy.prohibit_unlimited else ESCALATE
        extracted_summary = "Unlimited liability"
        required_action = "Replace clause — apply the approved fallback cap" if state == PROHIBITED else "Escalate for approval — unlimited liability exceeds policy"
        explanation = (
            f"Contract language: \"{extraction.raw_excerpt}\". Extracted value: Unlimited. "
            f"Company policy: unlimited liability is {'prohibited' if policy.prohibit_unlimited else 'permitted only with escalation'}. "
            f"Result: {state}."
        )
    elif extraction.cap_type == "not_stated":
        state = MUST_REDLINE
        extracted_summary = "Limitation-of-liability clause present but no numeric cap stated"
        required_action = "Redline — insert the approved cap language"
        explanation = (
            f"Contract language: \"{extraction.raw_excerpt}\". A limitation-of-liability clause exists but states no "
            f"enforceable numeric cap. Company policy requires a stated cap. Result: {state}."
        )
    elif extraction.cap_type == "fixed_amount":
        # A fixed dollar figure can't be deterministically normalized to a
        # fees-multiplier without a known contract value — escalate for
        # manual comparison rather than guessing at a conversion.
        state = ESCALATE
        extracted_summary = f"Fixed cap of ${extraction.fixed_amount:,.2f}"
        required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — cap is a fixed dollar amount, not a fees multiplier; compare manually against policy"
        explanation = (
            f"Contract language: \"{extraction.raw_excerpt}\". Extracted value: ${extraction.fixed_amount:,.2f} fixed cap. "
            f"Policy is defined as a multiplier of annual fees, so this cannot be compared automatically. Result: {state}."
        )
    else:  # multiplier
        value = extraction.multiplier
        extracted_summary = _fmt_multiplier(value)
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
            f"Contract language: \"{extraction.raw_excerpt}\". Extracted value: {_fmt_multiplier(value)}. "
            f"Policy — preferred: {_fmt_multiplier(policy.preferred_multiplier)}, "
            f"acceptable up to: {_fmt_multiplier(policy.acceptable_max_multiplier)}, "
            f"negotiable up to: {_fmt_multiplier(policy.negotiate_max_multiplier)}. "
            f"Result: {state}."
        )
        if missing_exceptions and state == NEGOTIATE:
            explanation += f" Required exception(s) not found in clause: {', '.join(missing_exceptions)}."

    return PolicyDecision(
        rule_id=RULE_ID, clause_type="limitation_of_liability", state=state,
        contract_language=extraction.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary=_fmt_multiplier(policy.negotiate_max_multiplier),
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, state),
        start_index=extraction.start_index, end_index=extraction.end_index,
        escalate_to=policy.escalation_approval_authority if state in (ESCALATE, PROHIBITED) else None,
        fallback_text=policy.fallback_text if state in (MUST_REDLINE, PROHIBITED, NEGOTIATE) else None,
        source=source,
    )
