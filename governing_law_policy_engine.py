"""
Governing Law clause adapter, over policy_engine_core. Batch A, adapter 3
of 3. Deliberately the structurally simplest AND most different shape of
the four adapters built so far: governing law is not a comparative value
(Liability), a directed obligation/right/restriction graph
(Indemnification/Termination/Confidentiality/Assignment), or a reciprocal
claim needing symmetry verification. It applies UNIFORMLY to both
parties — there is no "our side vs. their side" to resolve at all. The
hard problem here is categorical: is the named jurisdiction on our
policy's preferred, acceptable, or prohibited list, is the dispute-
resolution mechanism (litigation vs. arbitration) what we want, and does
venue (which can differ from governing law) match.

SEMANTIC MODEL: what jurisdiction's substantive law governs -> what
venue/forum is designated (may differ from governing law) -> what dispute
resolution mechanism applies (litigation / arbitration / mediation-then-
arbitration) -> whether a jury trial is waived.

This is the first adapter that does NOT reuse the
resolve-directed-facts-into-ours-vs-theirs pattern the other four
independently converged on — a deliberate, honest architecture data
point: not every clause needs that shape, and forcing it here would be
exactly the kind of "fake universal abstraction" the project has
consistently avoided.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol

from policy_engine_core import (
    ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE,
    REQUIRES_REVIEW, NOT_APPLICABLE,
    LadderStep, PolicyDecision,
    build_ladder as _core_build_ladder,
    escalate_to_for_state, fallback_text_for_state,
    excerpt as _excerpt, section_label_before as _section_label_before,
)

RULE_ID = "POLICY_GOVERNING_LAW"

_ANCHOR_RE = re.compile(r"govern(?:ed|ing)\s+by|governing\s+law", re.I)

# No blanket re.I over the captured jurisdiction/venue name: [A-Z] must
# stay case-SENSITIVE, or Python's re.IGNORECASE would let a lowercase
# word be captured too, silently defeating the "must look like a
# capitalized proper-noun jurisdiction name" heuristic this pattern
# relies on -- the same re.I-over-[A-Z] hazard already fixed in
# liability_policy_engine.py's _ROLE_POSITION_RE, indemnification's
# _OBLIGATION_RE, and every other adapter's party-name capture. This
# file's capture group had never received the (?-i:...) reset, so
# "governed by the laws of the state of new york" (all lowercase)
# previously captured "new york" as a confidently-extracted jurisdiction.
_JURISDICTION_RE = re.compile(
    r"governed\s+by(?:,?\s+and\s+construed\s+in\s+accordance\s+with,)?\s+the\s+laws?\s+of\s+"
    r"(?:the\s+State\s+of\s+|the\s+Commonwealth\s+of\s+)?(?-i:([A-Z][A-Za-z\s]{2,30}?))(?:,|\.|;|\s+without)",
    re.I,
)
_VENUE_RE = re.compile(
    r"(?:(?:exclusive\s+)?venue\s+(?:shall\s+be\s+|for\s+any\s+(?:dispute|action|proceeding)\s+shall\s+be\s+)?(?:in\s+)?"
    r"|(?:the\s+parties\s+)?(?:submit|consent)\s+to\s+the\s+(?:exclusive\s+)?jurisdiction\s+of\s+)"
    r"(?:the\s+)?(?:state\s+and\s+federal\s+)?courts?\s+(?:located\s+)?in\s+"
    r"(?-i:([A-Z][A-Za-z\s]{2,30}?))(?:,|\.|;)",
    re.I,
)
_ARBITRATION_RE = re.compile(r"binding\s+arbitration|shall\s+be\s+(?:resolved|settled)\s+by\s+arbitration", re.I)
_MEDIATION_THEN_ARBITRATION_RE = re.compile(r"mediation.{0,40}?(?:if\s+unresolved|failing\s+which).{0,40}?arbitration", re.I)
_LITIGATION_ONLY_RE = re.compile(r"exclusive\s+jurisdiction\s+of\s+the\s+courts|submit\s+to\s+the\s+jurisdiction\s+of", re.I)
_JURY_WAIVER_RE = re.compile(r"waives?\s+(?:its\s+|their\s+)?right\s+to\s+(?:a\s+)?(?:trial\s+by\s+)?jury|jury\s+trial\s+is\s+(?:hereby\s+)?waived", re.I)


@dataclass
class GoverningLawFacts:
    clause_found: bool
    jurisdiction: Optional[str] = None
    venue: Optional[str] = None
    dispute_resolution: str = "not_stated"  # "litigation" | "arbitration" | "mediation_then_arbitration" | "not_stated"
    jury_trial_waived: bool = False
    raw_excerpt: str = ""
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    section_label: Optional[str] = None

    # Fact-admission architecture — mirrors confidentiality_policy_engine.
    # ConfidentialityFacts.absence_state. evaluate_governing_law_policy's
    # existing `if facts.jurisdiction is None` branch already routes to
    # REQUIRES_REVIEW regardless of the reason, so RECOGNITION_UNCERTAIN
    # never needs its own separate branch there.
    absence_state: str = "CONFIRMED_ABSENT"
    semantic_discovery_error: Optional[str] = None
    ai_identified_condition: Optional[str] = None
    ai_identified_exception: Optional[str] = None


class GoverningLawPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]
    preferred_jurisdictions_json: Optional[List[str]]
    acceptable_jurisdictions_json: Optional[List[str]]
    prohibited_jurisdictions_json: Optional[List[str]]
    required_dispute_resolution: Optional[str]  # "litigation" | "arbitration" | None (no preference)
    require_jury_trial_waiver: bool


# _excerpt / _section_label_before are imported from policy_engine_core
# (promoted — see policy_engine_core.excerpt / section_label_before). No
# other promoted primitive applies here: Governing Law has no
# directionality (detect_role_attributed_asymmetry doesn't apply — there
# is no reciprocal/mutual concept) and its REQUIRES_REVIEW branch is a
# fixed string, not the "unresolved facts" template
# (requires_review_explanation doesn't apply either). This is the negative
# control working as intended — only the primitives this adapter
# genuinely needs are consumed.

def _normalize_jurisdiction(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip()


def _classify_dispute_resolution(text: str) -> str:
    if _MEDIATION_THEN_ARBITRATION_RE.search(text):
        return "mediation_then_arbitration"
    if _ARBITRATION_RE.search(text):
        return "arbitration"
    if _LITIGATION_ONLY_RE.search(text) or _VENUE_RE.search(text):
        return "litigation"
    return "not_stated"


# Off by default — same rollout discipline as every other adapter this
# session integrated.
GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED = False  # module-load-time default; immediately overridden below
import fact_admission as _fact_admission_env_check
GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED = _fact_admission_env_check.semantic_discovery_enabled("GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED")
del _fact_admission_env_check

_GOVERNING_LAW_SEMANTIC_FOCUS = (
    "which jurisdiction's law governs this agreement, or where disputes must be brought -- "
    "even if the wording is unusual and does not use standard terms like 'governing law' or "
    "'governed by'"
)
_GOVERNING_LAW_SEMANTIC_PROPOSITION = (
    "This sentence or clause is operative language of this agreement that establishes which "
    "jurisdiction's law governs this agreement, or the venue/forum for disputes."
)


def _run_semantic_discovery(text: str) -> Tuple[List, Optional[str]]:
    """Mirrors liability_policy_engine._run_semantic_discovery exactly."""
    if not GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED:
        return [], None
    import fact_admission as _fa
    try:
        raw_candidates = _fa.discover_candidate_spans(text, "governing_law", _GOVERNING_LAW_SEMANTIC_FOCUS)
    except Exception as exc:  # noqa: BLE001 — provider unavailable, never "confirmed absent"
        return [], f"{type(exc).__name__}: {exc}"

    admitted = []
    for candidate in raw_candidates:
        verified = _fa.verify_and_ground(candidate, text, _GOVERNING_LAW_SEMANTIC_PROPOSITION)
        if verified.admission_status == _fa.ADMITTED:
            admitted.append(verified)
    return admitted, None


def extract_governing_law_facts(text: str) -> Optional[GoverningLawFacts]:
    """Returns None only when no anchor exists at all AND semantic
    discovery also ran successfully and found nothing — a provider
    outage/error becomes RECOGNITION_UNCERTAIN instead (see
    absence_state), which the existing `if facts.jurisdiction is None`
    REQUIRES_REVIEW branch in evaluate_governing_law_policy already
    safely absorbs."""
    anchors = [m for m in _ANCHOR_RE.finditer(text) if not re.search(r"\bno\s+$", text[max(0, m.start() - 15):m.start()], re.I)]
    admitted_semantic: List = []
    if not anchors:
        admitted_semantic, semantic_error = _run_semantic_discovery(text)
        if semantic_error is not None:
            return GoverningLawFacts(clause_found=True, jurisdiction=None, absence_state="RECOGNITION_UNCERTAIN", semantic_discovery_error=semantic_error)
        if not admitted_semantic:
            return None
        # A semantically-admitted candidate does not itself establish a
        # jurisdiction — it only earns this document a shot at the SAME
        # deterministic _JURISDICTION_RE parsing below (which already
        # scans the full document unconditionally, not gated on
        # `anchors`). If that parsing still can't find a jurisdiction,
        # this falls through to the existing "jurisdiction=None"
        # REQUIRES_REVIEW path — never a fabricated jurisdiction.

    # Final trust architecture (Phase 5/6) — see confidentiality_policy_
    # engine.py's identical composition for the full rationale.
    ai_identified_condition = None
    ai_identified_exception = None
    for candidate in admitted_semantic:
        ai_identified_condition = ai_identified_condition or candidate.condition
        ai_identified_exception = ai_identified_exception or candidate.exception

    m = _JURISDICTION_RE.search(text)
    if not m:
        return GoverningLawFacts(
            clause_found=True, jurisdiction=None, raw_excerpt="", start_index=None, end_index=None,
            ai_identified_condition=ai_identified_condition, ai_identified_exception=ai_identified_exception,
        )

    jurisdiction = _normalize_jurisdiction(m.group(1))
    venue_m = _VENUE_RE.search(text)
    venue = _normalize_jurisdiction(venue_m.group(1)) if venue_m else None

    return GoverningLawFacts(
        clause_found=True,
        jurisdiction=jurisdiction,
        venue=venue,
        dispute_resolution=_classify_dispute_resolution(text),
        jury_trial_waived=bool(_JURY_WAIVER_RE.search(text)),
        raw_excerpt=_excerpt(text, m.start(), m.end()),
        start_index=m.start(), end_index=m.end(),
        section_label=_section_label_before(text, m.start()),
        ai_identified_condition=ai_identified_condition, ai_identified_exception=ai_identified_exception,
    )


def _build_ladder(policy: GoverningLawPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", f"Preferred jurisdiction(s): {', '.join(policy.preferred_jurisdictions_json or []) or 'unspecified'}"),
        ("ACCEPTABLE", f"Acceptable jurisdiction(s): {', '.join(policy.acceptable_jurisdictions_json or []) or 'unspecified'}"),
        ("FALLBACK", "Negotiate an acceptable jurisdiction"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Prohibited jurisdiction"),
    ]
    return _core_build_ladder(state, step_specs)


def _classify_jurisdiction(jurisdiction: str, policy: GoverningLawPolicyRuleLike) -> str:
    j = jurisdiction.lower()
    prohibited = {p.lower() for p in (policy.prohibited_jurisdictions_json or [])}
    preferred = {p.lower() for p in (policy.preferred_jurisdictions_json or [])}
    acceptable = {p.lower() for p in (policy.acceptable_jurisdictions_json or [])}
    if j in prohibited:
        return PROHIBITED
    if j in preferred:
        return ACCEPT
    if j in acceptable:
        return ACCEPT_WITH_NOTE
    return NEGOTIATE


def evaluate_governing_law_policy(
    facts: Optional[GoverningLawFacts],
    policy: GoverningLawPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    if facts is None or not facts.clause_found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="governing_law", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No governing law clause found",
            policy_limit_summary="N/A",
            required_action="None — this contract does not address governing law",
            explanation="No governing law clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="Governing law treatment",
            our_position_label="N/A", counterparty_position_label="N/A",
        )

    if facts.jurisdiction is None:
        no_structure_unresolved = ["governing law jurisdiction could not be parsed"]
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
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="governing_law", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Governing law referenced but no jurisdiction could be parsed",
            policy_limit_summary="N/A",
            required_action="Manual review required — governing law language present but jurisdiction unclear",
            explanation="The document references governing law but no parseable jurisdiction was found — "
                        "the clause may be malformed or drafted in a form this extractor doesn't recognize.",
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[],
            unresolved_facts=no_structure_unresolved,
            start_index=None, end_index=None, source=source, summary_label="Governing law treatment",
            our_position_label="N/A", counterparty_position_label="N/A",
        )

    # Final trust architecture (Phase 4 hard gate) — this adapter's found-
    # jurisdiction path has no pre-existing "unresolved" concept to piggy-
    # back onto (it accumulates ACCEPT/NEGOTIATE/... notes, never
    # REQUIRES_REVIEW, once a jurisdiction is parsed) — an explicit early
    # branch is required so a grounded AI-identified qualifier is never
    # silently dropped merely because the jurisdiction ALSO happened to
    # parse successfully.
    if facts.ai_identified_condition or facts.ai_identified_exception:
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
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="governing_law", state=REQUIRES_REVIEW,
            contract_language=facts.raw_excerpt, extracted_summary="Governing law established, but subject to a material qualifier",
            policy_limit_summary="N/A",
            required_action="Manual review required — a material condition/exception affecting governing law was identified",
            explanation="Governing law was established, but contextual analysis identified and grounded a "
                        "material condition or exception affecting it — this evaluation does not determine "
                        "the qualifier's effect.",
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[],
            unresolved_facts=qualifier_unresolved,
            start_index=facts.start_index, end_index=facts.end_index, source=source,
            summary_label="Governing law treatment", our_position_label="N/A", counterparty_position_label="N/A",
        )

    notes: List[str] = []

    def _worse(a: str, b: str) -> str:
        order = {ACCEPT: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, MUST_REDLINE: 3, ESCALATE: 4, PROHIBITED: 5}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    worst_state = _classify_jurisdiction(facts.jurisdiction, policy)
    if worst_state == PROHIBITED:
        notes.append(f"governing law jurisdiction ({facts.jurisdiction}) is on our prohibited list")
    elif worst_state == NEGOTIATE:
        notes.append(f"governing law jurisdiction ({facts.jurisdiction}) is not on our preferred or acceptable list")
    elif worst_state == ACCEPT_WITH_NOTE:
        notes.append(f"governing law jurisdiction ({facts.jurisdiction}) is acceptable but not our preferred choice")

    if policy.required_dispute_resolution is not None:
        if facts.dispute_resolution == "not_stated":
            notes.append(f"dispute resolution mechanism not stated at all (policy requires {policy.required_dispute_resolution})")
            worst_state = _worse(worst_state, MUST_REDLINE)
        elif facts.dispute_resolution != policy.required_dispute_resolution and not (
            policy.required_dispute_resolution == "arbitration" and facts.dispute_resolution == "mediation_then_arbitration"
        ):
            notes.append(
                f"dispute resolution is {facts.dispute_resolution}, but policy requires {policy.required_dispute_resolution}"
            )
            worst_state = _worse(worst_state, NEGOTIATE)

    if policy.require_jury_trial_waiver and not facts.jury_trial_waived and facts.dispute_resolution != "arbitration":
        notes.append("no jury trial waiver stated, required by policy")
        worst_state = _worse(worst_state, NEGOTIATE)

    extracted_summary = f"Jurisdiction: {facts.jurisdiction}; Dispute resolution: {facts.dispute_resolution}"
    if worst_state == ACCEPT and not notes:
        required_action = "None — governing law terms meet policy"
        explanation = f"Contract language: \"{facts.raw_excerpt}\". No policy gaps found. Result: {ACCEPT}."
    else:
        if worst_state in (ESCALATE, PROHIBITED):
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — " + "; ".join(notes)
        elif worst_state == NEGOTIATE:
            required_action = "Negotiate — " + "; ".join(notes)
        else:
            required_action = "None — within acceptable range, note for the file: " + "; ".join(notes)
        explanation = f"Contract language: \"{facts.raw_excerpt}\". {'; '.join(notes)}. Result: {worst_state}."

    return PolicyDecision(
        rule_id=RULE_ID, clause_type="governing_law", state=worst_state,
        contract_language=facts.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary=", ".join(policy.preferred_jurisdictions_json or []) or "unspecified",
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, worst_state),
        category_treatments=[], unresolved_facts=[],
        start_index=facts.start_index, end_index=facts.end_index,
        escalate_to=escalate_to_for_state(worst_state, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(worst_state, policy.fallback_text, (NEGOTIATE, ESCALATE, PROHIBITED)),
        source=source,
        controlling_provision={"label": "Governing Law", "excerpt": facts.raw_excerpt,
                                "start_index": facts.start_index, "end_index": facts.end_index},
        summary_label="Governing law treatment", our_position_label="N/A", counterparty_position_label="N/A",
    )
