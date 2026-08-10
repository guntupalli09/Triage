"""
Confidentiality clause adapter, over policy_engine_core. Batch A, adapter
1 of 3 (Confidentiality / Assignment / Governing Law) — built for breadth
after the architecture question was answered by three prior, deliberately
different-shaped adapters (Liability, Indemnification, Termination).

SEMANTIC MODEL: who -> is obligated to protect whose confidential
information -> defined how broadly (marking required or not) -> subject
to what standard exclusions (public knowledge, independently developed,
rightfully received from a third party, required by law) -> under what
standard of care -> for how long (fixed term, perpetual, or indefinite
for trade secrets) -> mutual or unilateral.

This reuses the same "directed obligation, possibly reciprocal" shape
Indemnification and Termination both independently arrived at:
confidentiality obligations run FROM a protecting party TO the party
whose information is protected, and a "each party shall protect the
other's information" opener is subject to the identical symmetry-
verification concern (a differentiated proviso can contradict a claimed-
mutual opener). Reimplemented locally per the established "reuse the
pattern, not the code" discipline — see the architecture report for the
running tally of how many adapters now independently need this.
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
    escalate_to_for_state, fallback_text_for_state,
    excerpt as _excerpt, section_label_before as _section_label_before,
    requires_review_explanation, requires_review_required_action,
    detect_role_attributed_asymmetry,
)

RULE_ID = "POLICY_CONFIDENTIALITY"

EXCLUSION_TOPICS = ["public_knowledge", "independently_developed", "third_party_rightful", "required_by_law"]

_ANCHOR_RE = re.compile(r"confidential\w*", re.I)

_NAMED_OBLIGATION_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,25}))\s+(?i:shall|will|agrees\s+to)\s+"
    r"(?i:protect|maintain\s+(?:the\s+)?confidentiality\s+of|not\s+disclose|hold\s+in\s+confidence)"
    r"(?i:\s+the\s+confidentiality\s+of)?\s+(?i:the\s+|any\s+)?"
    r"(?-i:([A-Z][A-Za-z]{2,25}))(?:'s)?\s+(?i:Confidential\s+Information)",
    re.I,
)
_MUTUAL_OBLIGATION_RE = re.compile(
    r"each\s+party\s+(?:shall|will|agrees\s+to)\s+(?:protect|maintain\s+(?:the\s+)?confidentiality\s+of|not\s+disclose|hold\s+in\s+confidence)"
    r"(?:\s+the\s+confidentiality\s+of)?\s+the\s+other\s+part(?:y|ies)(?:'s)?\s+Confidential\s+Information"
    r"|the\s+parties\s+shall\s+(?:mutually\s+)?protect\s+each\s+other'?s\s+Confidential\s+Information",
    re.I,
)
_GENERIC_ROLE_WORDS = {
    "each", "the", "any", "such", "this", "that", "both", "either", "all",
    "party", "parties", "receiving", "disclosing",
}

_EXCLUSION_RE: Dict[str, re.Pattern] = {
    "public_knowledge": re.compile(r"(?:is|becomes)\s+(?:publicly\s+known|generally\s+available|part\s+of\s+the\s+public\s+domain)|already\s+(?:known\s+to\s+the\s+public|public)", re.I),
    "independently_developed": re.compile(r"independently\s+develop(?:ed)?", re.I),
    "third_party_rightful": re.compile(r"rightfully\s+(?:received|obtained)\s+from\s+a\s+third\s+part(?:y|ies)|lawfully\s+(?:received|obtained)\s+from\s+(?:a\s+)?third\s+part(?:y|ies)", re.I),
    "required_by_law": re.compile(r"required\s+by\s+law|required\s+by\s+(?:a\s+)?(?:court\s+order|subpoena|governmental\s+authority)|compelled\s+by\s+legal\s+process", re.I),
}

_CARE_SAME_AS_OWN_RE = re.compile(r"same\s+degree\s+of\s+care|no\s+less\s+than\s+reasonable\s+care.{0,30}own", re.I)
_CARE_REASONABLE_RE = re.compile(r"reasonable\s+(?:degree\s+of\s+)?care", re.I)

_DURATION_YEARS_RE = re.compile(
    r"(?:for\s+a\s+period\s+of\s+|for\s+|last(?:s|ing)?\s+for\s+)?(\d+)\s*(?:\(\d+\)\s*)?years?\b",
    re.I,
)
_DURATION_PERPETUAL_RE = re.compile(r"perpetuity|perpetual(?:ly)?|indefinitely|no\s+time\s+limit", re.I)
_TRADE_SECRET_INDEFINITE_RE = re.compile(r"trade\s+secrets?.{0,60}?(?:perpetuity|indefinitely|for\s+as\s+long\s+as)", re.I)

_MARKING_REQUIRED_RE = re.compile(r"marked\s+(?:as\s+)?[\"']?confidential[\"']?|designated\s+(?:in\s+writing\s+)?as\s+confidential", re.I)
_BROAD_SCOPE_RE = re.compile(r"whether\s+or\s+not\s+marked|regardless\s+of\s+(?:whether\s+it\s+is\s+)?marked|orally\s+disclosed", re.I)

_ROLE_ATTRIBUTION_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,25}))(?:'s)?\s+(?i:confidentiality\s+obligations?)\s+"
    r"(?i:under\s+this\s+(?:Section|Agreement)\s+)?",
    re.I,
)

_PROVISION_WINDOW_CHARS = 1200


@dataclass
class ConfidentialityObligation:
    """One directional promise: protecting_role protects the confidential
    information belonging to protected_role."""
    protecting_role: str
    protecting_side: Optional[str]
    protected_role: str
    protected_side: Optional[str]
    exclusions_present: Dict[str, bool]
    standard_of_care: str  # "reasonable_care" | "same_as_own" | "not_stated"
    duration_years: Optional[int]
    duration_perpetual: bool
    marking_required: bool
    broad_scope: bool
    raw_excerpt: str
    start_index: int
    end_index: int
    section_label: Optional[str]
    is_mutual: bool = False
    asymmetry_reasons: List[str] = field(default_factory=list)

    def label(self) -> str:
        prefix = f"Section {self.section_label} — " if self.section_label else ""
        return f"{prefix}{self.protecting_role} protects {self.protected_role}'s Confidential Information"


@dataclass
class ConfidentialityFacts:
    clause_found: bool
    obligations: List[ConfidentialityObligation] = field(default_factory=list)


class ConfidentialityPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]
    required_exclusions_json: Optional[List[str]]
    min_protection_duration_years: Optional[int]
    max_exposure_duration_years: Optional[int]
    require_mutual_confidentiality: bool


# _excerpt / _section_label_before are imported from policy_engine_core
# (promoted — see policy_engine_core.excerpt / section_label_before).

def _classify_exclusions(window: str) -> Dict[str, bool]:
    return {topic: bool(rex.search(window)) for topic, rex in _EXCLUSION_RE.items()}


def _classify_care(window: str) -> str:
    if _CARE_SAME_AS_OWN_RE.search(window):
        return "same_as_own"
    if _CARE_REASONABLE_RE.search(window):
        return "reasonable_care"
    return "not_stated"


def _classify_duration(window: str) -> Tuple[Optional[int], bool]:
    if _DURATION_PERPETUAL_RE.search(window) or _TRADE_SECRET_INDEFINITE_RE.search(window):
        return None, True
    m = _DURATION_YEARS_RE.search(window)
    if m:
        return int(m.group(1)), False
    return None, False


def _snapshot_confidentiality_attribution(local: str) -> Dict[str, Any]:
    duration_years, perpetual = _classify_duration(local)
    return {"duration_years": duration_years, "perpetual": perpetual, "care": _classify_care(local)}


def _compare_confidentiality_attribution(base_role: str, base: Dict[str, Any], role: str, snap: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    if base["perpetual"] != snap["perpetual"]:
        reasons.append(f"{base_role} and {role} differ on whether the obligation is perpetual")
    elif (
        base["duration_years"] is not None and snap["duration_years"] is not None
        and base["duration_years"] != snap["duration_years"]
    ):
        reasons.append(f"{base_role} and {role} state different durations ({base['duration_years']} vs {snap['duration_years']} years)")
    if base["care"] not in ("not_stated",) and snap["care"] not in ("not_stated",) and base["care"] != snap["care"]:
        reasons.append(f"{base_role} and {role} state different standards of care")
    return reasons


def _detect_confidentiality_asymmetry(window: str) -> List[str]:
    """The scan/window/compare mechanics are shared (see policy_engine_core.
    detect_role_attributed_asymmetry, which also owns the next-attribution-
    bounded local window fix originally found and fixed here) — only the
    attribution regex, the generic-role stoplist, and the snapshot/compare
    functions stay adapter-owned."""
    return detect_role_attributed_asymmetry(
        window, _ROLE_ATTRIBUTION_RE, _GENERIC_ROLE_WORDS,
        _snapshot_confidentiality_attribution, _compare_confidentiality_attribution,
    )


def extract_confidentiality_facts(text: str) -> Optional[ConfidentialityFacts]:
    anchors = [m for m in _ANCHOR_RE.finditer(text) if not re.search(r"\bno\s+$", text[max(0, m.start() - 15):m.start()], re.I)]
    if not anchors:
        return None

    obligations: List[ConfidentialityObligation] = []
    seen_spans: List[Tuple[int, int]] = []

    for m in _NAMED_OBLIGATION_RE.finditer(text):
        if any(abs(m.start() - s) < 30 for s, _ in seen_spans):
            continue
        protecting_role, protected_role = m.group(1), m.group(2)
        if protecting_role.lower() == protected_role.lower():
            continue
        window = text[m.start():min(len(text), m.start() + _PROVISION_WINDOW_CHARS)]
        duration_years, perpetual = _classify_duration(window)
        obligations.append(ConfidentialityObligation(
            protecting_role=protecting_role, protecting_side=side_for_role(protecting_role),
            protected_role=protected_role, protected_side=side_for_role(protected_role),
            exclusions_present=_classify_exclusions(window),
            standard_of_care=_classify_care(window),
            duration_years=duration_years, duration_perpetual=perpetual,
            marking_required=bool(_MARKING_REQUIRED_RE.search(window)) and not bool(_BROAD_SCOPE_RE.search(window)),
            broad_scope=bool(_BROAD_SCOPE_RE.search(window)),
            raw_excerpt=_excerpt(text, m.start(), m.end()),
            start_index=m.start(), end_index=m.end(),
            section_label=_section_label_before(text, m.start()),
        ))
        seen_spans.append((m.start(), m.end()))

    for m in _MUTUAL_OBLIGATION_RE.finditer(text):
        if any(abs(m.start() - s) < 30 for s, _ in seen_spans):
            continue
        window = text[m.start():min(len(text), m.start() + _PROVISION_WINDOW_CHARS)]
        duration_years, perpetual = _classify_duration(window)
        obligations.append(ConfidentialityObligation(
            protecting_role="Each Party", protecting_side=None,
            protected_role="the Other Party", protected_side=None,
            exclusions_present=_classify_exclusions(window),
            standard_of_care=_classify_care(window),
            duration_years=duration_years, duration_perpetual=perpetual,
            marking_required=bool(_MARKING_REQUIRED_RE.search(window)) and not bool(_BROAD_SCOPE_RE.search(window)),
            broad_scope=bool(_BROAD_SCOPE_RE.search(window)),
            raw_excerpt=_excerpt(text, m.start(), m.end()),
            start_index=m.start(), end_index=m.end(),
            section_label=_section_label_before(text, m.start()),
            is_mutual=True,
            asymmetry_reasons=_detect_confidentiality_asymmetry(window),
        ))
        seen_spans.append((m.start(), m.end()))

    if not obligations:
        return ConfidentialityFacts(clause_found=True, obligations=[])

    obligations.sort(key=lambda o: o.start_index)
    return ConfidentialityFacts(clause_found=True, obligations=obligations)


def _build_ladder(policy: ConfidentialityPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", f"Preferred protection duration: {policy.min_protection_duration_years or 'unspecified'} years minimum"),
        ("ACCEPTABLE", "Auto-accept within acceptable confidentiality terms"),
        ("FALLBACK", "Negotiate confidentiality terms within fallback range"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Prohibited confidentiality terms"),
    ]
    return _core_build_ladder(state, step_specs)


def _resolve_obligations_for_side(
    obligations: List[ConfidentialityObligation], contract_side: str,
) -> Tuple[Optional[ConfidentialityObligation], Optional[ConfidentialityObligation], List[str]]:
    """Resolves which obligation is our EXPOSURE (we protect their info)
    and which is our PROTECTION (they protect our info)."""
    reasons: List[str] = []
    exposure, protection = None, None

    mutual = [o for o in obligations if o.is_mutual]
    named = [o for o in obligations if not o.is_mutual]

    if mutual and not named:
        obligation = mutual[0]
        if obligation.asymmetry_reasons:
            reasons.append(
                "clause opens with mutual ('each party') confidentiality language, but states "
                "materially different terms per named party (" + "; ".join(obligation.asymmetry_reasons) +
                ") — cannot confirm the obligation is actually symmetric"
            )
            return None, None, reasons
        return obligation, obligation, reasons

    if contract_side == "mutual":
        if named:
            reasons.append(
                "contract states directional (non-mutual) confidentiality obligations, but this "
                "playbook is configured for a mutual position — cannot determine which obligation is ours"
            )
        return None, None, reasons

    def _monetary_key(o: ConfidentialityObligation):
        return (o.duration_years, o.duration_perpetual)

    for o in named:
        if o.protecting_side == contract_side and o.protected_side is not None and o.protected_side != contract_side:
            if exposure is not None and _monetary_key(exposure) != _monetary_key(o):
                reasons.append("multiple obligations found where we protect the counterparty's information, with different terms — cannot determine which governs")
            elif exposure is None:
                exposure = o
        elif o.protected_side == contract_side and o.protecting_side is not None and o.protecting_side != contract_side:
            if protection is not None and _monetary_key(protection) != _monetary_key(o):
                reasons.append("multiple obligations found where the counterparty protects our information, with different terms — cannot determine which governs")
            elif protection is None:
                protection = o
        elif o.protecting_side is None or o.protected_side is None:
            reasons.append(
                f"obligation \"{o.protecting_role} protects {o.protected_role}\" could not be mapped "
                f"to our configured contract side ({contract_side}) — unrecognized party name(s)"
            )

    return exposure, protection, reasons


def evaluate_confidentiality_policy(
    facts: Optional[ConfidentialityFacts],
    policy: ConfidentialityPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    if facts is None or not facts.clause_found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="confidentiality", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No confidentiality clause found",
            policy_limit_summary="N/A",
            required_action="None — this contract does not address confidentiality",
            explanation="No confidentiality clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="Confidentiality treatment",
            our_position_label="Our confidentiality exposure", counterparty_position_label="Counterparty's protection of our information",
        )

    if not facts.obligations:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="confidentiality", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Confidentiality referenced but no directional obligation could be parsed",
            policy_limit_summary="N/A",
            required_action="Manual review required — confidentiality language present but structure unclear",
            explanation="The document references confidentiality but no parseable directional or mutual "
                        "structure was found — the clause may be malformed or drafted in a form this "
                        "extractor doesn't recognize.",
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[],
            unresolved_facts=["confidentiality obligation structure could not be parsed"],
            start_index=None, end_index=None, source=source, summary_label="Confidentiality treatment",
            our_position_label="Our confidentiality exposure", counterparty_position_label="Counterparty's protection of our information",
        )

    exposure, protection, resolution_reasons = _resolve_obligations_for_side(facts.obligations, policy.contract_side)
    unresolved_facts = list(resolution_reasons)

    if unresolved_facts:
        controlling = exposure or protection or facts.obligations[0]
        explanation = requires_review_explanation("confidentiality structure", controlling.raw_excerpt, unresolved_facts)
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="confidentiality", state=REQUIRES_REVIEW,
            contract_language=controlling.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary="N/A",
            required_action=requires_review_required_action(unresolved_facts),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved_facts,
            start_index=controlling.start_index, end_index=controlling.end_index, source=source,
            controlling_provision={"label": controlling.label(), "excerpt": controlling.raw_excerpt,
                                    "start_index": controlling.start_index, "end_index": controlling.end_index},
            summary_label="Confidentiality treatment", our_position_label="Our confidentiality exposure",
            counterparty_position_label="Counterparty's protection of our information",
        )

    notes: List[str] = []
    worst_state = ACCEPT

    def _worse(a: str, b: str) -> str:
        order = {ACCEPT: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, MUST_REDLINE: 3, ESCALATE: 4, PROHIBITED: 5}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    required_exclusions = list(policy.required_exclusions_json or [])
    if exposure is not None and required_exclusions:
        missing = [t for t in required_exclusions if not exposure.exclusions_present.get(t)]
        if missing:
            notes.append(f"our confidentiality obligation is missing standard exclusion(s): {', '.join(missing)}")
            worst_state = _worse(worst_state, NEGOTIATE)

    if protection is not None:
        if policy.min_protection_duration_years is not None:
            if protection.duration_perpetual:
                pass  # perpetual protection satisfies any minimum
            elif protection.duration_years is None:
                notes.append("counterparty's confidentiality obligation to us states no duration at all")
                worst_state = _worse(worst_state, MUST_REDLINE)
            elif protection.duration_years < policy.min_protection_duration_years:
                notes.append(
                    f"counterparty's confidentiality duration ({protection.duration_years} years) is below "
                    f"our required minimum ({policy.min_protection_duration_years} years)"
                )
                worst_state = _worse(worst_state, NEGOTIATE)

    if exposure is not None and policy.max_exposure_duration_years is not None:
        if exposure.duration_perpetual and policy.max_exposure_duration_years is not None:
            notes.append("our confidentiality obligation is perpetual, exceeding our preferred maximum")
            worst_state = _worse(worst_state, ESCALATE)
        elif exposure.duration_years is not None and exposure.duration_years > policy.max_exposure_duration_years:
            notes.append(
                f"our confidentiality duration ({exposure.duration_years} years) exceeds our preferred "
                f"maximum ({policy.max_exposure_duration_years} years)"
            )
            worst_state = _worse(worst_state, NEGOTIATE)

    if policy.require_mutual_confidentiality and protection is None and exposure is not None:
        notes.append("we are obligated to protect the counterparty's information, but no reciprocal obligation runs the other way")
        worst_state = _worse(worst_state, NEGOTIATE)

    controlling = exposure or protection or facts.obligations[0]
    extracted_summary = (
        f"Our exposure duration: {'perpetual' if exposure and exposure.duration_perpetual else (exposure.duration_years if exposure else 'n/a')}; "
        f"Counterparty protection: {'present' if protection else 'not found'}"
    )
    if worst_state == ACCEPT and not notes:
        required_action = "None — confidentiality terms meet policy"
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
        rule_id=RULE_ID, clause_type="confidentiality", state=worst_state,
        contract_language=controlling.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary=f"{policy.min_protection_duration_years or 'unspecified'} years minimum",
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, worst_state),
        category_treatments=[
            {"category": t, "treatment": "covered" if present else "not_addressed", "cap_summary": None,
             "raw_excerpt": "", "established": True}
            for t, present in (exposure.exclusions_present.items() if exposure else [])
        ],
        unresolved_facts=[], start_index=controlling.start_index, end_index=controlling.end_index,
        escalate_to=escalate_to_for_state(worst_state, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(worst_state, policy.fallback_text, (NEGOTIATE, ESCALATE, PROHIBITED)),
        source=source,
        controlling_provision={"label": controlling.label(), "excerpt": controlling.raw_excerpt,
                                "start_index": controlling.start_index, "end_index": controlling.end_index},
        our_position={"role": exposure.protecting_role, "summary": "perpetual" if exposure.duration_perpetual else f"{exposure.duration_years} years"} if exposure else None,
        counterparty_position={"role": protection.protecting_role, "summary": "perpetual" if protection.duration_perpetual else f"{protection.duration_years} years"} if protection else None,
        summary_label="Confidentiality treatment", our_position_label="Our confidentiality exposure",
        counterparty_position_label="Counterparty's protection of our information",
    )
