"""
Assignment clause adapter, over policy_engine_core. Batch A, adapter 2 of
3. Deliberately the simplest reasoning shape of the three — a single
restriction (may a party assign the Agreement without consent), not a
catalog of independently-true facts (Termination) or a set of
exclusion/duration axes (Confidentiality). Chosen for breadth: not every
clause needs the more elaborate shapes the first three adapters required.

SEMANTIC MODEL: who -> is restricted from assigning this Agreement ->
without whose consent -> under what consent standard (sole discretion /
not unreasonably withheld / none required) -> subject to what standing
exceptions (assignment to an affiliate, in connection with a merger,
acquisition, or change of control).

Same directional concern as the other adapters: a restriction on the
COUNTERPARTY (they need our consent to assign) is protective for us; a
restriction on OURSELVES (we need their consent) is what a playbook wants
bounded — adequate standing exceptions, a reasonable consent standard.
A restriction stated mutually ("neither party may assign without the
other's consent") is subject to the same symmetry-verification concern as
Indemnification/Termination/Confidentiality's reciprocal clauses.
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

RULE_ID = "POLICY_ASSIGNMENT"

EXCEPTION_TOPICS = ["affiliate", "change_of_control", "merger_acquisition"]

_ANCHOR_RE = re.compile(r"assign\w*", re.I)

_NAMED_RESTRICTION_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,25}))\s+(?i:may\s+not|shall\s+not)\s+assign\s+this\s+Agreement"
    r"(?i:\s+without\s+the\s+(?:prior\s+)?(?:written\s+)?consent\s+of)?",
    re.I,
)
_MUTUAL_RESTRICTION_RE = re.compile(
    r"neither\s+party\s+(?:may\s+not|shall\s+not|may)\s+assign\s+this\s+Agreement",
    re.I,
)
_NO_RESTRICTION_RE = re.compile(
    r"either\s+party\s+may\s+freely\s+assign|either\s+party\s+may\s+assign\s+this\s+Agreement\s+without\s+(?:the\s+)?(?:prior\s+)?consent",
    re.I,
)
_GENERIC_ROLE_WORDS = {"either", "each", "neither", "both", "the", "any", "such", "this", "that", "party", "parties"}

_CONSENT_SOLE_DISCRETION_RE = re.compile(r"in\s+its\s+sole\s+discretion|sole\s+and\s+absolute\s+discretion", re.I)
_CONSENT_REASONABLE_RE = re.compile(r"not\s+(?:to\s+be\s+|be\s+)?unreasonably\s+withheld(?:,?\s+conditioned,?\s+or\s+delayed)?", re.I)

_EXCEPTION_RE: Dict[str, re.Pattern] = {
    "affiliate": re.compile(r"\baffiliate", re.I),
    "change_of_control": re.compile(r"change\s+(?:of|in)\s+control", re.I),
    "merger_acquisition": re.compile(r"merger|acquisition|sale\s+of\s+(?:all\s+or\s+)?substantially\s+all\s+(?:of\s+its\s+)?assets", re.I),
}

_ROLE_ATTRIBUTION_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,25}))(?:'s)?\s+(?i:assignment\s+rights?|right\s+to\s+assign)\s+"
    r"(?i:under\s+this\s+(?:Section|Agreement)\s+)?",
    re.I,
)

_PROVISION_WINDOW_CHARS = 900


@dataclass
class AssignmentRestriction:
    restricted_role: str
    restricted_side: Optional[str]
    consent_required: bool
    consent_standard: str  # "sole_discretion" | "reasonable" | "not_stated"
    exceptions_present: Dict[str, bool]
    raw_excerpt: str
    start_index: int
    end_index: int
    section_label: Optional[str]
    is_mutual: bool = False
    asymmetry_reasons: List[str] = field(default_factory=list)

    def label(self) -> str:
        prefix = f"Section {self.section_label} — " if self.section_label else ""
        return f"{prefix}{self.restricted_role} restricted from assigning without consent"


@dataclass
class AssignmentFacts:
    clause_found: bool
    restrictions: List[AssignmentRestriction] = field(default_factory=list)
    unrestricted_assignment: bool = False

    # Fact-admission architecture — mirrors confidentiality_policy_engine.
    # ConfidentialityFacts.absence_state. evaluate_assignment_policy's
    # existing `if not facts.restrictions and not facts.
    # unrestricted_assignment` branch already routes to REQUIRES_REVIEW
    # regardless of the reason, so RECOGNITION_UNCERTAIN never needs its
    # own separate branch there.
    absence_state: str = "CONFIRMED_ABSENT"
    semantic_discovery_error: Optional[str] = None
    ai_identified_condition: Optional[str] = None
    ai_identified_exception: Optional[str] = None
    ai_identified_definition_or_reference: Optional[str] = None


class AssignmentPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]
    required_exceptions_json: Optional[List[str]]
    prohibit_sole_discretion_consent: bool
    require_consent_for_counterparty_assignment: bool


# _excerpt / _section_label_before are imported from policy_engine_core
# (promoted — see policy_engine_core.excerpt / section_label_before).

def _classify_consent_standard(window: str) -> str:
    if _CONSENT_SOLE_DISCRETION_RE.search(window):
        return "sole_discretion"
    if _CONSENT_REASONABLE_RE.search(window):
        return "reasonable"
    return "not_stated"


def _classify_exceptions(window: str) -> Dict[str, bool]:
    return {topic: bool(rex.search(window)) for topic, rex in _EXCEPTION_RE.items()}


def _snapshot_restriction_attribution(local: str) -> Dict[str, Any]:
    return {
        "consent_standard": _classify_consent_standard(local),
        "exceptions": frozenset(t for t, present in _classify_exceptions(local).items() if present),
    }


def _compare_restriction_attribution(base_role: str, base: Dict[str, Any], role: str, snap: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    if base["consent_standard"] not in ("not_stated",) and snap["consent_standard"] not in ("not_stated",) and base["consent_standard"] != snap["consent_standard"]:
        reasons.append(f"{base_role} and {role} state different consent standards")
    if base["exceptions"] and snap["exceptions"] and base["exceptions"] != snap["exceptions"]:
        reasons.append(f"{base_role} and {role} have different standing exceptions")
    return reasons


def _any_restriction_dimension_established_equal(base: Dict[str, Any], snap: Dict[str, Any]) -> bool:
    """Step 4A.10.4 — real, positively-established agreement on the
    consent standard or standing exceptions stands down the structural
    fail-closed check. See
    indemnification_policy_engine._any_dimension_established_equal for
    the full rationale."""
    if base["consent_standard"] not in ("not_stated",) and snap["consent_standard"] not in ("not_stated",) and base["consent_standard"] == snap["consent_standard"]:
        return True
    if base["exceptions"] and snap["exceptions"] and base["exceptions"] == snap["exceptions"]:
        return True
    return False


def _detect_restriction_asymmetry(window: str) -> List[str]:
    """The scan/window/compare mechanics are shared (see policy_engine_core.
    detect_role_attributed_asymmetry, which also owns the next-attribution-
    bounded local window fix originally found and fixed here) — only the
    attribution regex, the generic-role stoplist, and the snapshot/compare
    functions stay adapter-owned."""
    return detect_role_attributed_asymmetry(
        window, _ROLE_ATTRIBUTION_RE, _GENERIC_ROLE_WORDS,
        _snapshot_restriction_attribution, _compare_restriction_attribution,
        established_equal_fn=_any_restriction_dimension_established_equal,
    )


# Off by default — same rollout discipline as every other adapter this
# session integrated.
ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED = False  # module-load-time default; immediately overridden below
import fact_admission as _fact_admission_env_check
ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED = _fact_admission_env_check.semantic_discovery_enabled("ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED")
del _fact_admission_env_check

_ASSIGNMENT_SEMANTIC_FOCUS = (
    "a restriction on one party's ability to assign, transfer, or delegate this agreement to "
    "another entity -- or a statement that assignment is unrestricted -- even if the wording is "
    "unusual and does not use the word 'assign' at all"
)
_ASSIGNMENT_SEMANTIC_PROPOSITION = (
    "This sentence or clause is operative language of this agreement that restricts, "
    "conditions, or permits a party's ability to assign, transfer, or delegate this agreement."
)


def _run_semantic_discovery(text: str) -> Tuple[List, Optional[str], Optional[str]]:
    """Mirrors liability_policy_engine._run_semantic_discovery exactly.
    Returns (admitted_candidates, unresolved_dependency_note, error)."""
    if not ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED:
        return [], None, None
    import fact_admission as _fa
    try:
        raw_candidates = _fa.discover_candidate_spans(text, "assignment", _ASSIGNMENT_SEMANTIC_FOCUS)
    except Exception as exc:  # noqa: BLE001 — provider unavailable, never "confirmed absent"
        return [], None, f"{type(exc).__name__}: {exc}"

    verified_candidates = [
        _fa.verify_and_ground(candidate, text, _ASSIGNMENT_SEMANTIC_PROPOSITION) for candidate in raw_candidates
    ]
    admitted = [c for c in verified_candidates if c.admission_status == _fa.ADMITTED]
    unresolved_dependency_note = _fa.first_unresolved_dependency_note(verified_candidates)
    return admitted, unresolved_dependency_note, None


def extract_assignment_facts(text: str) -> Optional[AssignmentFacts]:
    """Returns None only when no anchor exists at all AND semantic
    discovery also ran successfully and found nothing — a provider
    outage/error becomes RECOGNITION_UNCERTAIN instead (see
    absence_state)."""
    anchors = [m for m in _ANCHOR_RE.finditer(text) if not re.search(r"\bno\s+$", text[max(0, m.start() - 15):m.start()], re.I)]
    admitted_semantic: List = []
    unresolved_dependency_note: Optional[str] = None
    if not anchors:
        admitted_semantic, unresolved_dependency_note, semantic_error = _run_semantic_discovery(text)
        if semantic_error is not None:
            return AssignmentFacts(clause_found=True, restrictions=[], unrestricted_assignment=False, absence_state="RECOGNITION_UNCERTAIN", semantic_discovery_error=semantic_error)
        if not admitted_semantic and not unresolved_dependency_note:
            return None
        # A semantically-admitted candidate does not itself become a
        # restriction — it only earns this document a shot at the SAME
        # deterministic NAMED_RESTRICTION_RE/MUTUAL_RESTRICTION_RE
        # structuring below (which already scans the full document
        # unconditionally, not gated on `anchors`). If that structuring
        # still can't parse a restriction, this falls through to the
        # existing "restrictions=[]" REQUIRES_REVIEW path a few lines
        # down — never a fabricated restriction.

    restrictions: List[AssignmentRestriction] = []
    seen_spans: List[Tuple[int, int]] = []
    unrestricted = False

    if _NO_RESTRICTION_RE.search(text):
        unrestricted = True

    for m in _NAMED_RESTRICTION_RE.finditer(text):
        if any(abs(m.start() - s) < 30 for s, _ in seen_spans):
            continue
        role = m.group(1)
        if role.lower() in _GENERIC_ROLE_WORDS:
            continue
        window = text[m.start():min(len(text), m.start() + _PROVISION_WINDOW_CHARS)]
        restrictions.append(AssignmentRestriction(
            restricted_role=role, restricted_side=side_for_role(role),
            consent_required=True,
            consent_standard=_classify_consent_standard(window),
            exceptions_present=_classify_exceptions(window),
            raw_excerpt=_excerpt(text, m.start(), m.end()),
            start_index=m.start(), end_index=m.end(),
            section_label=_section_label_before(text, m.start()),
        ))
        seen_spans.append((m.start(), m.end()))

    for m in _MUTUAL_RESTRICTION_RE.finditer(text):
        if any(abs(m.start() - s) < 30 for s, _ in seen_spans):
            continue
        window = text[m.start():min(len(text), m.start() + _PROVISION_WINDOW_CHARS)]
        restrictions.append(AssignmentRestriction(
            restricted_role="Either Party", restricted_side=None,
            consent_required=True,
            consent_standard=_classify_consent_standard(window),
            exceptions_present=_classify_exceptions(window),
            raw_excerpt=_excerpt(text, m.start(), m.end()),
            start_index=m.start(), end_index=m.end(),
            section_label=_section_label_before(text, m.start()),
            is_mutual=True,
            asymmetry_reasons=_detect_restriction_asymmetry(window),
        ))
        seen_spans.append((m.start(), m.end()))

    # Final trust architecture (Phase 5/6) — see confidentiality_policy_
    # engine.py's identical composition for the full rationale.
    import fact_admission as _fa
    ai_identified_condition = None
    ai_identified_exception = None
    for candidate in admitted_semantic:
        ai_identified_condition = ai_identified_condition or candidate.condition
        ai_identified_exception = ai_identified_exception or candidate.exception
    ai_identified_definition_or_reference = _fa.first_resolved_dependency_note(admitted_semantic) or unresolved_dependency_note

    if not restrictions and not unrestricted:
        return AssignmentFacts(
            clause_found=True, restrictions=[], unrestricted_assignment=False,
            ai_identified_condition=ai_identified_condition, ai_identified_exception=ai_identified_exception,
            ai_identified_definition_or_reference=ai_identified_definition_or_reference,
        )

    restrictions.sort(key=lambda r: r.start_index)
    return AssignmentFacts(
        clause_found=True, restrictions=restrictions, unrestricted_assignment=unrestricted,
        ai_identified_condition=ai_identified_condition, ai_identified_exception=ai_identified_exception,
        ai_identified_definition_or_reference=ai_identified_definition_or_reference,
    )


def _build_ladder(policy: AssignmentPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", "Mutual consent requirement with standard exceptions"),
        ("ACCEPTABLE", "Auto-accept within acceptable assignment terms"),
        ("FALLBACK", "Negotiate assignment terms within fallback range"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Prohibited assignment terms"),
    ]
    return _core_build_ladder(state, step_specs)


def _resolve_restrictions_for_side(
    restrictions: List[AssignmentRestriction], contract_side: str,
) -> Tuple[Optional[AssignmentRestriction], Optional[AssignmentRestriction], List[str]]:
    """Resolves which restriction is OUR restriction (we need consent to
    assign) and which is the COUNTERPARTY's restriction (they need our
    consent — protective for us)."""
    reasons: List[str] = []
    our_restriction, their_restriction = None, None

    mutual = [r for r in restrictions if r.is_mutual]
    named = [r for r in restrictions if not r.is_mutual]

    if mutual and not named:
        restriction = mutual[0]
        if restriction.asymmetry_reasons:
            reasons.append(
                "clause opens with mutual ('neither party') assignment restriction language, but "
                "states materially different terms per named party (" + "; ".join(restriction.asymmetry_reasons) +
                ") — cannot confirm the restriction is actually symmetric"
            )
            return None, None, reasons
        return restriction, restriction, reasons

    if contract_side == "mutual":
        if named:
            reasons.append(
                "contract states directional (non-mutual) assignment restrictions, but this "
                "playbook is configured for a mutual position — cannot determine which restriction is ours"
            )
        return None, None, reasons

    def _consent_key(r: AssignmentRestriction):
        return (r.consent_standard, frozenset(t for t, present in r.exceptions_present.items() if present))

    for r in named:
        if r.restricted_side == contract_side:
            if our_restriction is not None and _consent_key(our_restriction) != _consent_key(r):
                reasons.append(
                    "multiple assignment restrictions found on our side, with different consent "
                    "standards or exceptions — cannot determine which governs"
                )
            elif our_restriction is None:
                our_restriction = r
        elif r.restricted_side is not None and r.restricted_side != contract_side:
            if their_restriction is not None and _consent_key(their_restriction) != _consent_key(r):
                reasons.append(
                    "multiple assignment restrictions found on the counterparty's side, with "
                    "different consent standards or exceptions — cannot determine which governs"
                )
            elif their_restriction is None:
                their_restriction = r
        else:
            reasons.append(
                f"an assignment restriction on \"{r.restricted_role}\" could not be mapped to our "
                f"configured contract side ({contract_side}) — unrecognized party name"
            )

    return our_restriction, their_restriction, reasons


def evaluate_assignment_policy(
    facts: Optional[AssignmentFacts],
    policy: AssignmentPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    if facts is None or not facts.clause_found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="assignment", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No assignment clause found",
            policy_limit_summary="N/A",
            required_action="None — this contract does not address assignment",
            explanation="No assignment clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="Assignment treatment",
            our_position_label="Our assignment restriction", counterparty_position_label="Counterparty's assignment restriction",
        )

    if not facts.restrictions and not facts.unrestricted_assignment:
        no_structure_unresolved = ["assignment restriction structure could not be parsed"]
        if facts.ai_identified_condition:
            no_structure_unresolved.append(
                f"a material condition was identified by contextual analysis and grounded against the "
                f"source document (\"{facts.ai_identified_condition}\")"
            )
        if facts.ai_identified_exception:
            no_structure_unresolved.append(
                f"a material exception was identified by contextual analysis and grounded against the "
                f"source document (\"{facts.ai_identified_exception}\")"
            )
        if facts.ai_identified_definition_or_reference:
            no_structure_unresolved.append(
                f"a material definition/cross-reference dependency was identified by contextual analysis "
                f"({facts.ai_identified_definition_or_reference})"
            )
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="assignment", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Assignment referenced but no restriction could be parsed",
            policy_limit_summary="N/A",
            required_action="Manual review required — assignment language present but structure unclear",
            explanation="The document references assignment but no parseable restriction or unrestricted-"
                        "assignment structure was found.",
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[],
            unresolved_facts=no_structure_unresolved,
            start_index=None, end_index=None, source=source, summary_label="Assignment treatment",
            our_position_label="Our assignment restriction", counterparty_position_label="Counterparty's assignment restriction",
        )

    if facts.ai_identified_condition or facts.ai_identified_exception or facts.ai_identified_definition_or_reference:
        # Final trust architecture (Phase 4 hard gate) — checked before
        # the unrestricted-assignment ACCEPT/NEGOTIATE path specifically
        # so a grounded AI-identified qualifier can never be outrun by a
        # clean ACCEPT, even in the one branch of this adapter that can
        # otherwise reach ACCEPT with zero structured restrictions.
        qualifier_unresolved = []
        if facts.ai_identified_condition:
            qualifier_unresolved.append(
                f"a material condition was identified by contextual analysis and grounded against the "
                f"source document (\"{facts.ai_identified_condition}\")"
            )
        if facts.ai_identified_exception:
            qualifier_unresolved.append(
                f"a material exception was identified by contextual analysis and grounded against the "
                f"source document (\"{facts.ai_identified_exception}\")"
            )
        if facts.ai_identified_definition_or_reference:
            qualifier_unresolved.append(
                f"a material definition/cross-reference dependency was identified by contextual analysis "
                f"({facts.ai_identified_definition_or_reference})"
            )
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="assignment", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Assignment terms established, but subject to a material qualifier",
            policy_limit_summary="N/A",
            required_action="Manual review required — a material condition/exception affecting assignment was identified",
            explanation="Contextual analysis identified and grounded a material condition or exception "
                        "affecting the assignment terms — this evaluation does not determine the qualifier's effect.",
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[],
            unresolved_facts=qualifier_unresolved,
            start_index=None, end_index=None, source=source, summary_label="Assignment treatment",
            our_position_label="Our assignment restriction", counterparty_position_label="Counterparty's assignment restriction",
        )

    if facts.unrestricted_assignment and not facts.restrictions:
        notes = []
        worst_state = ACCEPT
        if policy.require_consent_for_counterparty_assignment:
            notes.append("assignment is entirely unrestricted for both parties, but policy requires consent to be required")
            worst_state = NEGOTIATE
        required_action = "None — assignment terms meet policy" if worst_state == ACCEPT else "Negotiate — " + "; ".join(notes)
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="assignment", state=worst_state,
            contract_language="", extracted_summary="Assignment permitted without consent (either party)",
            policy_limit_summary="N/A", required_action=required_action,
            explanation=f"No consent requirement is stated for either party. Result: {worst_state}.",
            negotiation_ladder=_build_ladder(policy, worst_state), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="Assignment treatment",
            our_position_label="Our assignment restriction", counterparty_position_label="Counterparty's assignment restriction",
        )

    our_restriction, their_restriction, resolution_reasons = _resolve_restrictions_for_side(facts.restrictions, policy.contract_side)
    unresolved_facts = list(resolution_reasons)

    if unresolved_facts:
        controlling = our_restriction or their_restriction or facts.restrictions[0]
        explanation = requires_review_explanation("assignment structure", controlling.raw_excerpt, unresolved_facts)
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="assignment", state=REQUIRES_REVIEW,
            contract_language=controlling.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary="N/A",
            required_action=requires_review_required_action(unresolved_facts),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved_facts,
            start_index=controlling.start_index, end_index=controlling.end_index, source=source,
            controlling_provision={"label": controlling.label(), "excerpt": controlling.raw_excerpt,
                                    "start_index": controlling.start_index, "end_index": controlling.end_index},
            summary_label="Assignment treatment", our_position_label="Our assignment restriction",
            counterparty_position_label="Counterparty's assignment restriction",
        )

    notes: List[str] = []
    worst_state = ACCEPT

    def _worse(a: str, b: str) -> str:
        order = {ACCEPT: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, MUST_REDLINE: 3, ESCALATE: 4, PROHIBITED: 5}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    if our_restriction is not None:
        required_exceptions = list(policy.required_exceptions_json or [])
        missing = [t for t in required_exceptions if not our_restriction.exceptions_present.get(t)]
        if missing:
            notes.append(f"our assignment restriction is missing standard exception(s): {', '.join(missing)}")
            worst_state = _worse(worst_state, NEGOTIATE)
        if our_restriction.consent_standard == "sole_discretion" and policy.prohibit_sole_discretion_consent:
            notes.append("counterparty's consent to our assignment is at their sole discretion, prohibited by policy")
            worst_state = _worse(worst_state, NEGOTIATE)

    if policy.require_consent_for_counterparty_assignment and their_restriction is None and our_restriction is not None:
        notes.append("we are restricted from assigning without consent, but the counterparty faces no reciprocal restriction")
        worst_state = _worse(worst_state, NEGOTIATE)

    controlling = our_restriction or their_restriction or facts.restrictions[0]
    extracted_summary = (
        f"Our restriction: {'present' if our_restriction else 'not found'}; "
        f"Counterparty restriction: {'present' if their_restriction else 'not found'}"
    )
    if worst_state == ACCEPT and not notes:
        required_action = "None — assignment terms meet policy"
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
        rule_id=RULE_ID, clause_type="assignment", state=worst_state,
        contract_language=controlling.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary="Standard exceptions required" if policy.required_exceptions_json else "N/A",
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, worst_state),
        category_treatments=[
            {"category": t, "treatment": "covered" if present else "not_addressed", "cap_summary": None,
             "raw_excerpt": "", "established": True}
            for t, present in (our_restriction.exceptions_present.items() if our_restriction else [])
        ],
        unresolved_facts=[], start_index=controlling.start_index, end_index=controlling.end_index,
        escalate_to=escalate_to_for_state(worst_state, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(worst_state, policy.fallback_text, (NEGOTIATE, ESCALATE, PROHIBITED)),
        source=source,
        controlling_provision={"label": controlling.label(), "excerpt": controlling.raw_excerpt,
                                "start_index": controlling.start_index, "end_index": controlling.end_index},
        our_position={"role": our_restriction.restricted_role, "summary": our_restriction.consent_standard} if our_restriction else None,
        counterparty_position={"role": their_restriction.restricted_role, "summary": their_restriction.consent_standard} if their_restriction else None,
        summary_label="Assignment treatment", our_position_label="Our assignment restriction",
        counterparty_position_label="Counterparty's assignment restriction",
    )
