"""
Insurance clause adapter, over policy_engine_core. Adapter #9 — the
third added after the original six (following data_security_policy_
engine.py, adapter #7, and ip_ownership_policy_engine.py, adapter #8).
Built by directly mirroring the established adapter shape rather than
inventing a new one; policy_engine_core.py was not modified — every
primitive this adapter needs already existed and fit without change.
classify_by_threshold was NOT used: required insurance limits are a
"higher is better" minimum-floor comparison (a $2M CGL limit satisfies
a $1M requirement), the opposite direction from classify_by_threshold's
"lower is better" band — forcing it through that helper would invert
its semantics rather than fit them, so a simple local minimum-floor
comparison is used instead.

SEMANTIC MODEL: an insurance clause is a CATALOG of independent
coverage-type requirements (Commercial General Liability, Professional
Liability/E&O, Cyber Liability, Workers' Compensation, Employer's
Liability, Automobile Liability), each with its own limits and
obligated party — never collapsed into a single "covered/not covered"
fact, and never allowed to leak into one another (a dollar figure
belongs to whichever coverage type it is textually attached to, tracked
via a local sub-window per coverage-type mention, not a single
clause-wide category guess — real insurance clauses routinely list
several coverage types with different limits in one sentence or
sub-itemized list, unlike the single-statement ownership clauses
ip_ownership_policy_engine.py's nearest-category search was built for).

For every coverage type, ownership-style separation is preserved
between:
  - coverage type (which policy this is)
  - required limit (per-occurrence vs aggregate, tracked independently)
  - coverage conditions (additional insured, waiver of subrogation,
    primary/non-contributory, claims-made/occurrence basis and tail)
  - proof/administration requirements (certificate of insurance, insurer
    rating, notice of cancellation, evidence-of-coverage timing)
never collapsed into one field, matching the same "who owns vs who may
use" separation discipline ip_ownership_policy_engine.py established.

Which party is obligated to carry each coverage type is resolved the
same side-agnostic-attribution-then-evaluate-time-resolution way
data_security resolves controller/processor role: extraction records
which named party a "shall maintain/carry/obtain" statement attaches to
(side-agnostic), and evaluate_insurance_policy resolves it against
contract_side, abstaining via REQUIRES_REVIEW when the obligated party
cannot be confidently determined (never guessed) — this is the "insured
party unclear" abstention criterion.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

from policy_engine_core import (
    ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE,
    REQUIRES_REVIEW, NOT_APPLICABLE,
    LadderStep, build_ladder as _core_build_ladder,
    escalate_to_for_state, fallback_text_for_state, side_for_role,
    excerpt, section_label_before,
    requires_review_explanation, requires_review_required_action,
    PolicyDecision,
    is_operative_context as _core_is_operative_context,
    EXTERNAL_DEFINITION_NOT_ATTACHED_RE as _EXTERNAL_DEFINITION_NOT_ATTACHED_RE,
    document_wide_conflict_detected as _document_wide_conflict_detected,
    unreconciled_ambiguity_marker_present as _unreconciled_ambiguity_marker_present,
    detect_condition_in_text as _core_detect_condition_in_text,
    cross_section_carveout_referencing as _cross_section_carveout_referencing,
)

RULE_ID = "POLICY_INSURANCE"
_PROVISION_WINDOW_CHARS = 2600

_GENERIC_WORDS = {"each", "the", "any", "such", "this", "that", "both", "either", "party", "parties", "all", "it"}

COVERAGE_TYPES = ("cgl", "professional_liability", "cyber_liability", "workers_comp", "employers_liability", "auto_liability")

# --- Anchor -----------------------------------------------------------------
_ANCHOR_RE = re.compile(
    r"commercial\s+general\s+liability|general\s+liability\s+insurance|\bCGL\b"
    r"|professional\s+liability|errors\s+(?:and|&)\s+omissions|\bE\s*&\s*O\b"
    r"|cyber\s+liability|cyber\s+insurance|data\s+breach\s+insurance|network\s+security"
    r"|workers[’']?\s+compensation|workman'?s\s+compensation"
    r"|employer'?s\s+liability"
    r"|automobile\s+liability|commercial\s+auto\s+(?:liability|insurance)|business\s+auto"
    r"|certificate[s]?\s+of\s+insurance|additional\s+insured|waiver\s+of\s+subrogation"
    r"|insurance\s+requirements|maintain\s+insurance|policy\s+of\s+insurance|shall\s+maintain[^.]{0,20}insurance"
    r"|\binsurance\b",
    re.I,
)

# --- Coverage-type anchors ---------------------------------------------------
_COVERAGE_RES: Dict[str, "re.Pattern"] = {
    "cgl": re.compile(r"commercial\s+general\s+liability|general\s+liability\s+insurance|\bCGL\b", re.I),
    "professional_liability": re.compile(r"professional\s+liability|errors\s+(?:and|&)\s+omissions|\bE\s*&\s*O\b", re.I),
    "cyber_liability": re.compile(r"cyber\s+liability|cyber\s+insurance|data\s+breach\s+insurance|network\s+security(?:\s+and\s+privacy)?\s+liability", re.I),
    "workers_comp": re.compile(r"workers[’']?\s+compensation|workman'?s\s+compensation", re.I),
    "employers_liability": re.compile(r"employer'?s\s+liability", re.I),
    "auto_liability": re.compile(r"automobile\s+liability|commercial\s+auto\s+(?:liability|insurance)|business\s+auto\s+liability", re.I),
}

# --- Dollar amounts and qualifiers -------------------------------------------
_DOLLAR_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)\s*(million|M\b)?", re.I)
_PER_OCCURRENCE_RE = re.compile(r"per\s+occurrence|each\s+occurrence|per\s+claim|each\s+claim|per\s+incident|each\s+accident", re.I)
_AGGREGATE_RE = re.compile(r"aggregate", re.I)

# --- Deductible / SIR ---------------------------------------------------------
_DEDUCTIBLE_RE = re.compile(
    r"(?:deductible|self-?insured\s+retention|\bSIR\b)[^.]{0,40}?\$\s?([\d,]+(?:\.\d+)?)\s*(million|M\b)?", re.I,
)

# --- Obligated party (who must carry the insurance) --------------------------
_OBLIGATED_PARTY_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,30}))\s+(?:shall|will|must)\s+(?:maintain|carry|obtain|procure)\b", re.I,
)

# --- Coverage conditions & administration ------------------------------------
_ADDITIONAL_INSURED_RE = re.compile(r"additional\s+insured", re.I)
_ADDITIONAL_INSURED_NEGATION_RE = re.compile(
    r"shall\s+not\s+be\s+named\s+as\s+(?:an\s+)?additional\s+insured"
    r"|shall\s+not\s+name[^.]{0,30}as\s+(?:an\s+)?additional\s+insured", re.I,
)
_WAIVER_SUBROGATION_RE = re.compile(r"waiver\s+of\s+subrogation|waive[s]?\s+(?:all\s+)?rights?\s+of\s+subrogation", re.I)
_WAIVER_SUBROGATION_NEGATION_RE = re.compile(
    r"shall\s+not\s+be\s+required\s+to\s+waive[^.]{0,40}?subrogation|shall\s+not\s+waive[^.]{0,40}?subrogation", re.I,
)
_PRIMARY_NONCONTRIB_RE = re.compile(r"primary\s+(?:and\s+)?non-?contributory|primary\s+and\s+not\s+contributory", re.I)
_COI_RE = re.compile(r"certificate[s]?\s+of\s+insurance", re.I)
_COI_NEGATION_RE = re.compile(r"shall\s+not\s+be\s+required\s+to\s+provide[^.]{0,40}?certificate", re.I)
_RATING_RE = re.compile(
    r"A\.?M\.?\s*Best|rated\s+(?:at\s+least\s+)?[A-Z][+-]?(?:\s*(?:VII|VIII|IX|X))?|rating\s+of\s+(?:at\s+least\s+)?[A-Z][+-]?"
    r"|insurer\s+(?:financial\s+strength\s+)?rating|financial\s+strength\s+rating", re.I,
)
_CANCELLATION_RE = re.compile(r"cancellation|material\s+change", re.I)
_CANCELLATION_DAYS_RE = re.compile(
    r"(\d{1,3})\s+days[’']?\s+(?:prior\s+)?(?:written\s+)?notice[^.]{0,50}?(?:cancellation|material\s+change)"
    r"|notice\s+of\s+cancellation[^.]{0,50}?(\d{1,3})\s+days", re.I,
)
_MAINTENANCE_RE = re.compile(
    r"maintain(?:ed)?[^.]{0,80}?(?:throughout|for\s+the\s+(?:duration|term))"
    r"|shall\s+keep\s+(?:such\s+)?insurance\s+in\s+(?:full\s+)?force", re.I,
)
_CLAIMS_MADE_RE = re.compile(r"claims-?made\s*(?:basis|form|policy)?|on\s+a\s+claims-?made\s+basis", re.I)
_OCCURRENCE_BASIS_RE = re.compile(r"occurrence\s*(?:-|\s)?(?:basis|form)|on\s+an\s+occurrence\s+basis", re.I)
_TAIL_RE = re.compile(r"extended\s+reporting\s+period|tail\s+coverage|tail\s+period", re.I)
_SUBCONTRACTOR_RE = re.compile(
    r"subcontractors?\s+(?:shall|must|will)\s+(?:maintain|carry|obtain)"
    r"|require\s+(?:its\s+|their\s+)?subcontractors?\s+to\s+maintain", re.I,
)
_SUBCONTRACTOR_NEGATION_RE = re.compile(
    r"no\s+obligation\s+to\s+require[^.]{0,40}?subcontractors|shall\s+not\s+require[^.]{0,40}?subcontractors", re.I,
)
_EVIDENCE_BEFORE_RE = re.compile(
    r"prior\s+to\s+(?:the\s+)?commencement|before\s+(?:commenc\w*|beginning)"
    r"|evidence\s+of\s+(?:such\s+)?insurance\s+(?:shall\s+be\s+)?(?:provided|furnished)\s+prior\s+to", re.I,
)
_SCHEDULE_CROSSREF_RE = re.compile(
    r"as\s+(?:set\s+forth|described|specified)\s+in\s+(?:the\s+)?(?:attached\s+)?(?:Schedule|Exhibit|Insurance\s+Schedule|Annex)"
    r"|governed\s+by\s+(?:the\s+)?(?:attached\s+)?(?:Schedule|Exhibit)", re.I,
)


def _parse_dollar(raw: str, suffix: Optional[str]) -> float:
    value = float(raw.replace(",", ""))
    if suffix and suffix.strip().lower().startswith("m"):
        value *= 1_000_000
    return value


@dataclass
class CoverageRequirement:
    established: bool = False
    per_occurrence_limit: Optional[float] = None
    aggregate_limit: Optional[float] = None
    limit_conflict: bool = False
    basis_ambiguous: bool = False
    obligated_party_attributions: Dict[str, bool] = field(default_factory=dict)
    obligated_party_conflict: bool = False
    raw_excerpt: str = ""


@dataclass
class InsuranceFacts:
    clause_found: bool
    raw_excerpt: str = ""
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    section_label: Optional[str] = None

    coverages: Dict[str, CoverageRequirement] = field(default_factory=dict)

    deductible_or_sir: Optional[float] = None
    additional_insured_required: Optional[bool] = None
    waiver_of_subrogation_required: Optional[bool] = None
    primary_non_contributory: Optional[bool] = None
    certificate_of_insurance_required: Optional[bool] = None
    insurer_rating_stated: Optional[bool] = None
    notice_of_cancellation_days: Optional[float] = None
    notice_of_cancellation_conflict: bool = False
    policy_maintenance_required: Optional[bool] = None
    claims_made_or_occurrence: Optional[str] = None  # "claims_made" | "occurrence"
    claims_made_occurrence_conflict: bool = False
    claims_made_tail_required: Optional[bool] = None
    subcontractor_coverage_required: Optional[bool] = None
    evidence_before_commencement: Optional[bool] = None
    schedule_cross_reference: bool = False

    # Fact-admission architecture — mirrors data_security_policy_engine.
    # DataSecurityFacts.absence_state exactly, for the same reason: this
    # adapter's per-dimension evaluate logic can resolve an all-None facts
    # object to ACCEPT when a playbook requires no specific coverage.
    absence_state: str = "CONFIRMED_ABSENT"
    semantic_discovery_error: Optional[str] = None
    ai_identified_condition: Optional[str] = None
    ai_identified_exception: Optional[str] = None
    ai_identified_definition_or_reference: Optional[str] = None
    # Candidate 3 zero-silent-loss mission — a separate statement
    # elsewhere in the document broadly negates/supersedes an established
    # coverage requirement, or the document explicitly self-declares an
    # unreconciled ambiguity (see policy_engine_core.document_wide_
    # conflict_detected / unreconciled_ambiguity_marker_present).
    document_wide_conflict: bool = False
    # Candidate 3 zero-silent-loss mission — a deterministically-detected
    # condition/proviso ("provided that...", "except in jurisdictions
    # where...") attached to the local coverage clause, found via the
    # SAME shared primitive liability already uses
    # (policy_engine_core.detect_condition_in_text), not a new adapter-
    # local regex.
    deterministic_condition_established: bool = False
    deterministic_condition_excerpt: Optional[str] = None


class InsurancePolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]

    require_cgl: bool
    cgl_minimum_per_occurrence: Optional[float]
    cgl_minimum_aggregate: Optional[float]
    require_professional_liability: bool
    professional_liability_minimum_limit: Optional[float]
    require_cyber_liability: bool
    cyber_liability_minimum_limit: Optional[float]
    require_workers_comp: bool
    require_employers_liability: bool
    employers_liability_minimum_limit: Optional[float]
    require_auto_liability: bool
    auto_liability_minimum_limit: Optional[float]
    require_counterparty_obligated: bool
    require_additional_insured: bool
    require_waiver_of_subrogation: bool
    require_primary_non_contributory: bool
    require_certificate_of_insurance: bool
    require_minimum_insurer_rating: bool
    require_notice_of_cancellation: bool
    minimum_cancellation_notice_days: Optional[float]
    require_policy_maintenance_through_term: bool
    require_claims_made_tail: bool
    require_subcontractor_coverage: bool
    require_evidence_before_commencement: bool


def _attribute_obligated_party(cov: CoverageRequirement, name: str) -> None:
    cov.obligated_party_attributions[name] = True
    if len(cov.obligated_party_attributions) > 1:
        cov.obligated_party_conflict = True


_SENTENCE_END_RE = re.compile(r"(?<!\d)\.(?!\d)|;")


def _local_window(text: str, start: int, other_anchor_positions: List[int], max_radius: int = 400) -> str:
    """Scopes a coverage-type mention to just its own sub-item, so a
    document listing several coverage types with different limits in one
    clause never bleeds one coverage type's dollar figures into
    another's.

    Sentence boundary is a period NOT immediately between two digits (so
    a decimal dollar figure like "$2.5 million" is never mistaken for a
    sentence end and used to prematurely truncate the window before the
    "million" multiplier or a later aggregate/per-occurrence qualifier is
    reached) or a semicolon — same fix already proven in
    payment_terms_policy_engine._local_window, reused verbatim here after
    the naive text.find(".") version was found to truncate exactly this
    way."""
    end = min(len(text), start + max_radius)
    m = _SENTENCE_END_RE.search(text, start, end)
    if m:
        end = min(end, m.end())
    for pos in other_anchor_positions:
        if pos > start:
            end = min(end, pos)
    return text[start:end]


def _extract_dollar_amounts(local_window: str) -> Tuple[List[Tuple[float, str]], List[float]]:
    """Returns (qualified, unqualified) where qualified is a list of
    (amount, "per_occurrence"|"aggregate") and unqualified is a list of
    bare amounts with no nearby qualifier found."""
    qualified: List[Tuple[float, str]] = []
    unqualified: List[float] = []
    for m in _DOLLAR_RE.finditer(local_window):
        amount = _parse_dollar(m.group(1), m.group(2))
        tail = local_window[m.end():m.end() + 40]
        if _PER_OCCURRENCE_RE.search(tail):
            qualified.append((amount, "per_occurrence"))
        elif _AGGREGATE_RE.search(tail):
            qualified.append((amount, "aggregate"))
        else:
            unqualified.append(amount)
    return qualified, unqualified


def _resolve_coverage_amounts(cov: CoverageRequirement, qualified: List[Tuple[float, str]], unqualified: List[float]) -> None:
    """Resolves final per-occurrence/aggregate limits from EVERY dollar
    amount found for this coverage type across the entire document (the
    caller accumulates qualified/unqualified across all windows and all
    mentions before calling this once) — resolving per-mention instead
    would let a second, conflicting mention silently overwrite the first
    rather than being detected as a conflict."""
    per_occ = {amt for amt, q in qualified if q == "per_occurrence"}
    agg = {amt for amt, q in qualified if q == "aggregate"}
    if len(per_occ) > 1 or len(agg) > 1:
        cov.limit_conflict = True
    if len(per_occ) == 1:
        cov.per_occurrence_limit = next(iter(per_occ))
    if len(agg) == 1:
        cov.aggregate_limit = next(iter(agg))

    if not qualified:
        distinct_unqualified = set(unqualified)
        if len(distinct_unqualified) == 1:
            cov.per_occurrence_limit = next(iter(distinct_unqualified))
        elif len(distinct_unqualified) >= 2:
            cov.basis_ambiguous = True


# Off by default — same rollout discipline as every other adapter this
# session integrated.
INSURANCE_SEMANTIC_DISCOVERY_ENABLED = False  # module-load-time default; immediately overridden below
import fact_admission as _fact_admission_env_check
INSURANCE_SEMANTIC_DISCOVERY_ENABLED = _fact_admission_env_check.semantic_discovery_enabled("INSURANCE_SEMANTIC_DISCOVERY_ENABLED")
del _fact_admission_env_check

_INSURANCE_SEMANTIC_FOCUS = (
    "one party being required to maintain, provide evidence of, or name the other party as "
    "an additional insured under, an insurance policy -- even if the wording is unusual and "
    "does not use standard terms like 'insurance' or 'coverage'"
)
_INSURANCE_SEMANTIC_PROPOSITION = (
    "This sentence or clause is operative language of this agreement that establishes an "
    "insurance-coverage obligation (required coverage, limits, additional insured status, "
    "certificate/evidence of insurance, or a related insurance requirement)."
)


def _run_semantic_discovery(text: str) -> Tuple[List, Optional[str], bool, Optional[str]]:
    """Mirrors liability_policy_engine._run_semantic_discovery exactly.
    Returns (admitted_candidates, unresolved_dependency_note, error)."""
    if not INSURANCE_SEMANTIC_DISCOVERY_ENABLED:
        return [], None, False, None
    import fact_admission as _fa
    try:
        raw_candidates = _fa.discover_candidate_spans(text, "insurance", _INSURANCE_SEMANTIC_FOCUS)
    except Exception as exc:  # noqa: BLE001 — provider unavailable, never "confirmed absent"
        return [], None, False, f"{type(exc).__name__}: {exc}"

    verified_candidates = [
        _fa.verify_and_ground(candidate, text, _INSURANCE_SEMANTIC_PROPOSITION) for candidate in raw_candidates
    ]
    admitted = [c for c in verified_candidates if c.admission_status == _fa.ADMITTED]
    unresolved_dependency_note = _fa.first_unresolved_dependency_note(verified_candidates)
    note_is_unconditional = _fa.first_unresolved_dependency_note_is_unconditional(verified_candidates)
    return admitted, unresolved_dependency_note, note_is_unconditional, None


def extract_insurance_facts(text: str) -> Optional[InsuranceFacts]:
    """Returns None only when no anchor exists at all AND semantic
    discovery also ran successfully and found nothing — a provider
    outage/error becomes RECOGNITION_UNCERTAIN instead (see
    absence_state)."""
    matches = list(_ANCHOR_RE.finditer(text))
    semantic_error: Optional[str] = None
    admitted_semantic: List = []
    unresolved_dependency_note: Optional[str] = None
    # Candidate 3 remediation (Root Cause 2): contextual discovery is no
    # longer gated behind "deterministic anchor discovery found zero
    # matches." It now always runs (when semantic discovery is enabled for
    # this adapter), so AI can supplement/corroborate an ALREADY-matched
    # clause too -- not just propose a candidate when regex found nothing
    # at all. When deterministic anchors already exist, a semantic-
    # discovery error is recorded but does not abort extraction (the
    # deterministic side still has something to work with); when no
    # anchors exist at all, a semantic-discovery error still means
    # RECOGNITION_UNCERTAIN, exactly as before.
    admitted_semantic, unresolved_dependency_note, note_is_unconditional, semantic_error = _run_semantic_discovery(text)
    if not matches:
        if semantic_error is not None:
            return InsuranceFacts(clause_found=True, absence_state="RECOGNITION_UNCERTAIN", semantic_discovery_error=semantic_error)
        if not admitted_semantic and not unresolved_dependency_note:
            return None
        if not admitted_semantic:
            dependency_only_facts = InsuranceFacts(clause_found=True, ai_identified_definition_or_reference=unresolved_dependency_note)
            for ct in COVERAGE_TYPES:
                dependency_only_facts.coverages[ct] = CoverageRequirement()
            return dependency_only_facts
    elif semantic_error is not None:
        # Deterministic anchors exist; the AI channel independently
        # errored. Never silently drop this -- best-effort proceed with
        # the deterministic anchors, but the error is preserved so it
        # can inform the PRESENT_BUT_UNRESOLVED decision below if the
        # deterministic side also fails to establish anything.
        admitted_semantic = []

    anchor_spans = sorted(
        [(m.start(), m.end()) for m in matches] + [(c.start_offset, c.end_offset) for c in admitted_semantic]
    )
    windows: List[Tuple[int, int]] = []
    for (m_start, m_end) in anchor_spans:
        s = max(0, m_start - 200)
        e = min(len(text), m_end + _PROVISION_WINDOW_CHARS)
        if windows and s - windows[-1][1] < 200:
            windows[-1] = (windows[-1][0], max(windows[-1][1], e))
        else:
            windows.append((s, e))

    first_start, first_end = anchor_spans[0]
    start_index = max(0, first_start - 200)
    end_index = min(len(text), first_end + 400)
    raw_excerpt = excerpt(text, start_index, end_index)
    section_label = section_label_before(text, first_start)

    facts = InsuranceFacts(clause_found=True, raw_excerpt=raw_excerpt, start_index=start_index,
                            end_index=end_index, section_label=section_label)
    for ct in COVERAGE_TYPES:
        facts.coverages[ct] = CoverageRequirement()

    cancellation_days_values: set = set()
    claims_basis_tokens: set = set()
    accumulated_qualified: Dict[str, List[Tuple[float, str]]] = {ct: [] for ct in COVERAGE_TYPES}
    accumulated_unqualified: Dict[str, List[float]] = {ct: [] for ct in COVERAGE_TYPES}

    # Root-cause fix (Candidate 2, false-operative -> clean): the
    # is_operative_context wiring above stops a purely descriptive/
    # background coverage mention from being marked `established`, but
    # extract_insurance_facts still unconditionally returned a
    # clause_found=True InsuranceFacts even when NOTHING was structurally
    # established -- evaluate_insurance_policy only treats
    # `facts is None or not facts.clause_found` as NOT_APPLICABLE, so a
    # wholly non-operative clause (nothing established, no ancillary term
    # found) fell through to ACCEPT ("no policy gaps found") instead of
    # NOT_APPLICABLE. Mirrors the same found_anything negative-control
    # gate warranties/sla already use for exactly this reason. An AI-
    # discovered candidate that already survived verify_and_ground (i.e.
    # is in admitted_semantic) is itself a real, grounded finding -- not
    # subject to this deterministic-regex gate, exactly like sla's
    # identical composition. Also true when ANY top-level anchor match is
    # itself operative, even if it never resolves to one of the specific
    # NAMED coverage types below (e.g. "Vendor shall maintain insurance
    # coverage as set forth in Exhibit D" -- a real, operative, but
    # underspecified obligation that the existing schedule_cross_reference/
    # "policy requires X but clause doesn't address it" machinery further
    # down is specifically designed to catch as MUST_REDLINE/REQUIRES_
    # REVIEW, not silently discard as "nothing here at all").
    # Candidate 3 remediation (Root Cause 1: an admitted AI candidate must
    # not be silently discarded merely because it doesn't ALSO satisfy the
    # narrow, named-coverage-type regexes below). `found_anything` alone
    # (which an admitted semantic candidate already satisfies) is not
    # enough to know whether a genuine, structured coverage value was
    # established -- track that separately so a document where AI found
    # and verified an insurance-relevant span, but no coverage type/limit
    # could be deterministically structured from it, is distinguishable
    # from a document where a real coverage type WAS structured. See
    # PRESENT_BUT_UNRESOLVED handling at the end of this function.
    deterministic_value_found = False
    found_anything = bool(admitted_semantic) or any(
        _core_is_operative_context(text, m.start(), m.end()) for m in matches
    )

    for (ws, we) in windows:
        window = text[ws:we]

        # Coverage-type-specific extraction: scope each mention to its own
        # local sub-window so multiple coverage types in one clause never
        # cross-contaminate each other's limits. Every mention's amounts
        # are accumulated (never resolved per-mention) so a second,
        # conflicting mention of the same coverage type — anywhere in the
        # document — is detected as a conflict rather than silently
        # overwriting the first.
        # Root-cause fix (Candidate 2, false-operative -> clean): a
        # coverage-type mention inside descriptive/background/recital
        # prose ("It is common practice for a services vendor to carry
        # Commercial General Liability insurance, though the specific
        # coverage requirements ... remain to be negotiated") was
        # previously marked `established=True` purely because the
        # anchor phrase appeared anywhere in the window, with no check
        # that this is actually THIS document's own operative
        # commitment. Reuses the SAME shared `is_operative_context`
        # primitive liability/indemnification/payment_terms already
        # trust for this exact class of defect, rather than a new,
        # adapter-local descriptive-language blacklist.
        anchor_matches: Dict[str, List["re.Match"]] = {ct: list(rx.finditer(window)) for ct, rx in _COVERAGE_RES.items()}
        all_positions_flat = [m.start() for matches in anchor_matches.values() for m in matches]

        for ct, matches in anchor_matches.items():
            cov = facts.coverages[ct]
            for m in matches:
                if not _core_is_operative_context(text, ws + m.start(), ws + m.end()):
                    continue
                pos = m.start()
                cov.established = True
                found_anything = True
                deterministic_value_found = True
                other_positions = [p for p in all_positions_flat if p != pos]
                local = _local_window(window, pos, other_positions)
                qualified, unqualified = _extract_dollar_amounts(local)
                accumulated_qualified[ct].extend(qualified)
                accumulated_unqualified[ct].extend(unqualified)

        # Obligated party: resolved once per parent window (the party
        # named before a list of coverage types governs the whole list in
        # standard drafting), then attributed to every coverage type
        # established within this window.
        obligated_names = {m.group(1) for m in _OBLIGATED_PARTY_RE.finditer(window) if m.group(1).lower() not in _GENERIC_WORDS}
        if obligated_names:
            covered_here = [ct for ct, matches in anchor_matches.items() if matches]
            for ct in covered_here:
                cov = facts.coverages[ct]
                for name in obligated_names:
                    _attribute_obligated_party(cov, name)

        if _DEDUCTIBLE_RE.search(window):
            dm = _DEDUCTIBLE_RE.search(window)
            facts.deductible_or_sir = _parse_dollar(dm.group(1), dm.group(2))
            found_anything = True
            deterministic_value_found = True
        if _ADDITIONAL_INSURED_RE.search(window) and not _ADDITIONAL_INSURED_NEGATION_RE.search(window):
            facts.additional_insured_required = True
            found_anything = True
            deterministic_value_found = True
        if _WAIVER_SUBROGATION_RE.search(window) and not _WAIVER_SUBROGATION_NEGATION_RE.search(window):
            facts.waiver_of_subrogation_required = True
            found_anything = True
            deterministic_value_found = True
        if _PRIMARY_NONCONTRIB_RE.search(window):
            facts.primary_non_contributory = True
            found_anything = True
            deterministic_value_found = True
        if _COI_RE.search(window) and not _COI_NEGATION_RE.search(window):
            facts.certificate_of_insurance_required = True
            found_anything = True
            deterministic_value_found = True
        if _RATING_RE.search(window):
            facts.insurer_rating_stated = True
            found_anything = True
            deterministic_value_found = True
        if _MAINTENANCE_RE.search(window):
            facts.policy_maintenance_required = True
            found_anything = True
            deterministic_value_found = True
        if _TAIL_RE.search(window):
            facts.claims_made_tail_required = True
            found_anything = True
            deterministic_value_found = True
        if _SUBCONTRACTOR_RE.search(window) and not _SUBCONTRACTOR_NEGATION_RE.search(window):
            facts.subcontractor_coverage_required = True
            found_anything = True
            deterministic_value_found = True
        if _EVIDENCE_BEFORE_RE.search(window):
            facts.evidence_before_commencement = True
            found_anything = True
            deterministic_value_found = True
        if _SCHEDULE_CROSSREF_RE.search(window) or _EXTERNAL_DEFINITION_NOT_ATTACHED_RE.search(window):
            facts.schedule_cross_reference = True
            found_anything = True
            deterministic_value_found = True

        if _CLAIMS_MADE_RE.search(window):
            claims_basis_tokens.add("claims_made")
            found_anything = True
            deterministic_value_found = True
        if _OCCURRENCE_BASIS_RE.search(window):
            claims_basis_tokens.add("occurrence")
            found_anything = True
            deterministic_value_found = True

        for m in _CANCELLATION_DAYS_RE.finditer(window):
            raw = m.group(1) or m.group(2)
            if raw:
                cancellation_days_values.add(int(raw))
                found_anything = True
                deterministic_value_found = True

    if len(cancellation_days_values) == 1:
        facts.notice_of_cancellation_days = float(next(iter(cancellation_days_values)))
    elif len(cancellation_days_values) > 1:
        facts.notice_of_cancellation_conflict = True

    if len(claims_basis_tokens) > 1:
        facts.claims_made_occurrence_conflict = True
    elif len(claims_basis_tokens) == 1:
        facts.claims_made_or_occurrence = next(iter(claims_basis_tokens))

    for ct in COVERAGE_TYPES:
        _resolve_coverage_amounts(facts.coverages[ct], accumulated_qualified[ct], accumulated_unqualified[ct])

    if not found_anything:
        return None

    # Candidate 3 remediation (Root Cause 1): an admitted AI candidate
    # exists but no coverage type/limit or ancillary term could be
    # deterministically structured from it -- this must never silently
    # reach ACCEPT ("no policy gaps found") merely because nothing was
    # established. Scoped specifically to the AI-admitted-candidate case
    # (bool(admitted_semantic)), NOT to a bare deterministic anchor match
    # with nothing else in the document (e.g. a lone "9. Insurance."
    # heading) -- that is the pre-existing, correct "operative but
    # nothing required by policy" ACCEPT path Candidate 2 already
    # established and must not be touched by this remediation. See
    # CANONICAL_PRIMARY_FACT_SCHEMA.md's PRESENT_BUT_UNRESOLVED state.
    if not deterministic_value_found and admitted_semantic:
        facts.absence_state = "PRESENT_BUT_UNRESOLVED"

    # Zero-silent-loss mission follow-up (data_security-139 general failure
    # class) -- a candidate was discovered but its OWN semantic
    # verification reported genuine uncertainty (not a disproven claim),
    # so it was never admitted, yet a deterministic anchor also exists
    # elsewhere in the document (found_anything is True via an operative
    # top-level match). Previously silently discarded because the block
    # above is gated on `admitted_semantic` being non-empty.
    # Candidate 3 final pre-freeze blocker remediation (Blocker 2) -- a
    # definition/cross-reference dependency or competing-reading note is
    # always structurally material and must never be suppressed merely
    # because some other insurance dimension was established elsewhere.
    if not admitted_semantic and unresolved_dependency_note is not None and (
        note_is_unconditional or not deterministic_value_found
    ):
        facts.absence_state = "PRESENT_BUT_UNRESOLVED"
        facts.ai_identified_definition_or_reference = (
            facts.ai_identified_definition_or_reference or unresolved_dependency_note
        )

    # Final trust architecture (Phase 5/6) — reached only when
    # found_anything is True (the base insurance structure DID resolve
    # deterministically, so this candidate already passed the negative-
    # control gate above). See confidentiality_policy_engine.py's
    # identical composition for the full rationale.
    import fact_admission as _fa
    for candidate in admitted_semantic:
        facts.ai_identified_condition = facts.ai_identified_condition or candidate.condition
        facts.ai_identified_exception = facts.ai_identified_exception or candidate.exception
    facts.ai_identified_definition_or_reference = (
        _fa.first_resolved_dependency_note(admitted_semantic) or facts.ai_identified_definition_or_reference
    )

    # Candidate 3 zero-silent-loss mission — a document-wide contradiction
    # (a separate, later statement broadly negating/superseding the
    # established coverage requirement) or a self-declared unreconciled
    # ambiguity must never be silently dropped just because the local
    # anchor window it lives outside of already established a clean value.
    if (_document_wide_conflict_detected(text, facts.start_index, facts.end_index)
            or _unreconciled_ambiguity_marker_present(text)
            or _cross_section_carveout_referencing(text, facts.section_label)):
        facts.document_wide_conflict = True

    if deterministic_value_found:
        for (ws, we) in windows:
            cond = _core_detect_condition_in_text(text[ws:we])
            if cond.status == "ESTABLISHED":
                facts.deterministic_condition_established = True
                facts.deterministic_condition_excerpt = cond.evidence_span
                break

    return facts


def _resolve_obligated_party(cov: CoverageRequirement, contract_side: str) -> Tuple[Optional[str], bool]:
    """Mirrors data_security._resolve_our_role, generalized to any
    coverage type's obligated-party attributions."""
    if not cov.obligated_party_attributions:
        return None, False
    if contract_side == "mutual":
        return None, True
    sides: set = set()
    for name in cov.obligated_party_attributions:
        mapped = side_for_role(name)
        if mapped == contract_side:
            sides.add("us")
        elif mapped is not None:
            sides.add("counterparty")
    if len(sides) == 1:
        return next(iter(sides)), False
    return None, True


def _build_ladder(policy: InsurancePolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", "Preferred insurance terms met in full"),
        ("ACCEPTABLE", "Auto-accept within acceptable insurance terms"),
        ("FALLBACK", "Negotiate insurance terms within fallback range"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Prohibited insurance terms"),
    ]
    return _core_build_ladder(state, step_specs)


_WORST_ORDER = {ACCEPT: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, MUST_REDLINE: 3, ESCALATE: 4, PROHIBITED: 5}


def _worse(a: str, b: str) -> str:
    return a if _WORST_ORDER.get(a, 0) >= _WORST_ORDER.get(b, 0) else b


_COVERAGE_LABELS = {
    "cgl": "Commercial General Liability", "professional_liability": "Professional Liability / E&O",
    "cyber_liability": "Cyber Liability", "workers_comp": "Workers' Compensation",
    "employers_liability": "Employer's Liability", "auto_liability": "Automobile Liability",
}


def evaluate_insurance_policy(
    facts: Optional[InsuranceFacts],
    policy: InsurancePolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    common = dict(
        rule_id=RULE_ID, clause_type="insurance", source=source,
        summary_label="Insurance treatment",
        our_position_label="Our insurance requirements",
        counterparty_position_label="Counterparty's insurance commitments",
    )

    if facts is None or not facts.clause_found:
        return PolicyDecision(
            **common, state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No insurance clause found",
            policy_limit_summary="N/A",
            required_action="None — this contract does not address insurance",
            explanation="No insurance clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None,
        )

    if facts.absence_state == "RECOGNITION_UNCERTAIN":
        return PolicyDecision(
            **common, state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Could not determine whether an insurance clause is present",
            policy_limit_summary="N/A",
            required_action="Manual review required — automated recognition was unavailable for this document.",
            explanation=(
                "Deterministic pattern matching found no insurance clause, and semantic verification could "
                f"not confirm its absence ({facts.semantic_discovery_error or 'unavailable'}). This is not "
                "the same as confirming the contract has no such clause."
            ),
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None,
        )

    required_map = {
        "cgl": policy.require_cgl, "professional_liability": policy.require_professional_liability,
        "cyber_liability": policy.require_cyber_liability, "workers_comp": policy.require_workers_comp,
        "employers_liability": policy.require_employers_liability, "auto_liability": policy.require_auto_liability,
    }
    minimum_per_occurrence = {
        "cgl": policy.cgl_minimum_per_occurrence, "professional_liability": policy.professional_liability_minimum_limit,
        "cyber_liability": policy.cyber_liability_minimum_limit, "workers_comp": None,
        "employers_liability": policy.employers_liability_minimum_limit, "auto_liability": policy.auto_liability_minimum_limit,
    }

    unresolved: List[str] = []
    # Candidate 3 zero-silent-loss mission — a document-wide contradiction
    # or self-declared unreconciled ambiguity must block clean regardless
    # of what the local anchor window otherwise established.
    if facts.document_wide_conflict:
        unresolved.append(
            "a separate statement elsewhere in the document appears to contradict, negate, or leave unreconciled "
            "the insurance requirement established in this clause"
        )
    if facts.deterministic_condition_established:
        unresolved.append(
            f"the insurance requirement is stated as conditional (\"{facts.deterministic_condition_excerpt}\") — "
            f"this evaluation does not determine whether the stated condition is satisfied"
        )
    # Final trust architecture (Phase 4 hard gate) — a material condition/
    # exception the AI/context layer identified and grounded must not be
    # silently dropped merely because coverage otherwise resolved cleanly.
    if facts.ai_identified_condition:
        unresolved.append(
            f"a material condition was identified by contextual analysis and grounded against the source "
            f"document (\"{facts.ai_identified_condition}\")"
        )
    if facts.ai_identified_exception:
        unresolved.append(
            f"a material exception was identified by contextual analysis and grounded against the source "
            f"document (\"{facts.ai_identified_exception}\")"
        )
    if facts.ai_identified_definition_or_reference:
        unresolved.append(
            f"a material definition/cross-reference dependency was identified by contextual analysis "
            f"({facts.ai_identified_definition_or_reference})"
        )
    party_resolution: Dict[str, Tuple[Optional[str], bool]] = {}
    for ct in COVERAGE_TYPES:
        cov = facts.coverages[ct]
        label = _COVERAGE_LABELS[ct]
        if cov.limit_conflict:
            unresolved.append(f"{label}: multiple conflicting dollar limits are stated")
        if cov.basis_ambiguous:
            unresolved.append(f"{label}: it cannot be determined whether the stated amount(s) are per-occurrence or aggregate")
        party_resolution[ct] = _resolve_obligated_party(cov, policy.contract_side)
        _owner, unresolved_directional = party_resolution[ct]
        if cov.obligated_party_conflict:
            unresolved.append(f"{label}: the party obligated to carry this coverage is stated inconsistently")
        elif required_map[ct] and policy.require_counterparty_obligated and cov.established and unresolved_directional:
            unresolved.append(f"{label}: the obligated party could not be confidently mapped to our configured contract "
                               f"side, or this playbook is configured for a mutual position — cannot determine who must carry it")

    if facts.claims_made_occurrence_conflict:
        unresolved.append("claims-made vs. occurrence basis is stated inconsistently across the document")
    if facts.notice_of_cancellation_conflict:
        unresolved.append("notice-of-cancellation period is stated inconsistently across the document")

    established_dimension_count = sum(1 for ct in COVERAGE_TYPES if facts.coverages[ct].established) + sum(
        1 for v in (
            facts.deductible_or_sir, facts.additional_insured_required, facts.waiver_of_subrogation_required,
            facts.primary_non_contributory, facts.certificate_of_insurance_required, facts.insurer_rating_stated,
            facts.notice_of_cancellation_days, facts.policy_maintenance_required, facts.claims_made_or_occurrence,
            facts.claims_made_tail_required, facts.subcontractor_coverage_required, facts.evidence_before_commencement,
        ) if v is not None
    )
    if facts.schedule_cross_reference and established_dimension_count == 0:
        unresolved.append("material insurance requirements are delegated to a referenced Schedule/Exhibit not included in this text")

    # Candidate 3 remediation (Root Cause 1): a candidate that contextual
    # discovery identified and verified (ESTABLISHED, grounded, ADMITTED)
    # exists for this document, but nothing could be deterministically
    # structured from it into a specific coverage type/limit/ancillary
    # term. Never let this fall through to a bare "no policy gaps found"
    # ACCEPT merely because no policy field happened to be requiring a
    # coverage type -- the material finding itself must still surface.
    if facts.absence_state == "PRESENT_BUT_UNRESOLVED" and established_dimension_count == 0 and not facts.schedule_cross_reference:
        unresolved.append(
            "contextual discovery identified and verified insurance-relevant language in this contract, but "
            "deterministic extraction could not structure it into a specific coverage type, limit, or other "
            "requirement — this is not the same as confirming no insurance requirement exists"
        )

    if unresolved:
        explanation = requires_review_explanation("insurance clause", facts.raw_excerpt, unresolved)
        return PolicyDecision(
            **common, state=REQUIRES_REVIEW,
            contract_language=facts.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary="N/A", required_action=requires_review_required_action(unresolved),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved,
            start_index=facts.start_index, end_index=facts.end_index,
            controlling_provision={"label": f"Section {facts.section_label} — Insurance" if facts.section_label else "Insurance", "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
        )

    notes: List[str] = []
    worst = ACCEPT
    category_treatments: List[Dict[str, Any]] = []

    def _note(msg: str, state: str) -> None:
        nonlocal worst
        notes.append(msg)
        worst = _worse(worst, state)

    for ct in COVERAGE_TYPES:
        cov = facts.coverages[ct]
        label = _COVERAGE_LABELS[ct]
        if required_map[ct]:
            if not cov.established:
                _note(f"policy requires {label} coverage, but the clause does not address it", MUST_REDLINE)
            else:
                min_occ = minimum_per_occurrence.get(ct)
                if min_occ is not None:
                    if cov.per_occurrence_limit is None:
                        _note(f"policy requires a minimum {label} limit of {int(min_occ):,}, but no limit was stated", NEGOTIATE)
                    elif cov.per_occurrence_limit < min_occ:
                        _note(f"{label} limit of {int(cov.per_occurrence_limit):,} is below policy's required minimum of {int(min_occ):,}", NEGOTIATE)
                if ct == "cgl" and policy.cgl_minimum_aggregate is not None:
                    if cov.aggregate_limit is None:
                        _note("policy requires a minimum CGL aggregate limit, but none was stated", NEGOTIATE)
                    elif cov.aggregate_limit < policy.cgl_minimum_aggregate:
                        _note(f"CGL aggregate limit of {int(cov.aggregate_limit):,} is below policy's required minimum of {int(policy.cgl_minimum_aggregate):,}", NEGOTIATE)
                if policy.require_counterparty_obligated:
                    owner, _ = party_resolution[ct]
                    if owner is None:
                        _note(f"policy requires the counterparty to carry {label}, but no obligated party was stated", NEGOTIATE)
                    elif owner != "counterparty":
                        _note(f"policy requires the counterparty to carry {label}, but the clause obligates us instead", MUST_REDLINE)
        category_treatments.append({"category": ct, "treatment": ("established" if cov.established else "not_addressed"), "cap_summary": (f"{int(cov.per_occurrence_limit):,} per occurrence" if cov.per_occurrence_limit else None), "raw_excerpt": "", "established": cov.established})

    if policy.require_additional_insured and not facts.additional_insured_required:
        _note("policy requires additional insured status, but none was found", NEGOTIATE)
    if policy.require_waiver_of_subrogation and not facts.waiver_of_subrogation_required:
        _note("policy requires a waiver of subrogation, but none was found", NEGOTIATE)
    if policy.require_primary_non_contributory and not facts.primary_non_contributory:
        _note("policy requires primary and non-contributory language, but none was found", NEGOTIATE)
    if policy.require_certificate_of_insurance and not facts.certificate_of_insurance_required:
        _note("policy requires a certificate of insurance, but none was found", NEGOTIATE)
    if policy.require_minimum_insurer_rating and not facts.insurer_rating_stated:
        _note("policy requires a minimum insurer rating (e.g. A.M. Best), but none was found", NEGOTIATE)
    if policy.require_notice_of_cancellation:
        if facts.notice_of_cancellation_days is None:
            _note("policy requires advance notice of cancellation, but no notice period was found", NEGOTIATE)
        elif policy.minimum_cancellation_notice_days is not None and facts.notice_of_cancellation_days < policy.minimum_cancellation_notice_days:
            _note(f"notice-of-cancellation period of {int(facts.notice_of_cancellation_days)} days is below policy's required minimum of {int(policy.minimum_cancellation_notice_days)} days", NEGOTIATE)
    if policy.require_policy_maintenance_through_term and not facts.policy_maintenance_required:
        _note("policy requires insurance to be maintained throughout the term, but no such commitment was found", NEGOTIATE)
    if policy.require_claims_made_tail and not facts.claims_made_tail_required:
        _note("policy requires extended-reporting/tail coverage for claims-made policies, but none was found", NEGOTIATE)
    if policy.require_subcontractor_coverage and not facts.subcontractor_coverage_required:
        _note("policy requires subcontractors to carry equivalent insurance, but no such obligation was found", NEGOTIATE)
    if policy.require_evidence_before_commencement and not facts.evidence_before_commencement:
        _note("policy requires evidence of coverage before commencement, but no such timing commitment was found", NEGOTIATE)

    extracted_summary_parts = []
    for ct in COVERAGE_TYPES:
        cov = facts.coverages[ct]
        if cov.established and cov.per_occurrence_limit:
            extracted_summary_parts.append(f"{_COVERAGE_LABELS[ct]}: {int(cov.per_occurrence_limit):,}")
        elif cov.established:
            extracted_summary_parts.append(f"{_COVERAGE_LABELS[ct]}: addressed")
    extracted_summary = "; ".join(extracted_summary_parts) or "Insurance clause found; limited structured detail extractable"

    if worst == ACCEPT and not notes:
        required_action = "None — insurance terms meet policy"
        explanation = f"Contract language: \"{facts.raw_excerpt}\". No policy gaps found. Result: {ACCEPT}."
    else:
        if worst in (ESCALATE, PROHIBITED):
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — " + "; ".join(notes)
        elif worst == MUST_REDLINE:
            required_action = "Replace clause — apply the approved fallback insurance language: " + "; ".join(notes)
        else:
            required_action = "Negotiate — " + "; ".join(notes)
        explanation = f"Contract language: \"{facts.raw_excerpt}\". {'; '.join(notes)}. Result: {worst}."

    return PolicyDecision(
        **common, state=worst,
        contract_language=facts.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary="See configured policy",
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, worst),
        category_treatments=category_treatments, unresolved_facts=[],
        start_index=facts.start_index, end_index=facts.end_index,
        escalate_to=escalate_to_for_state(worst, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(worst, policy.fallback_text, (NEGOTIATE, MUST_REDLINE, PROHIBITED)),
        controlling_provision={"label": f"Section {facts.section_label} — Insurance" if facts.section_label else "Insurance", "excerpt": facts.raw_excerpt, "start_index": facts.start_index, "end_index": facts.end_index},
    )
