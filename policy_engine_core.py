"""
Shared deterministic Policy Engine Core.

Clause-agnostic decision model, abstention semantics, evidence/provenance,
escalation routing, negotiation ladder, directional-position resolution,
and benchmark safety metrics — everything a policy-rule engine needs that
has no idea what a "liability cap" or an "indemnification obligation" is.

A clause adapter (see liability_policy_engine.py for the first one) owns
all clause-specific work: what counts as the relevant provision in a
document, what facts to extract from it, and how to turn those facts into
one of the states defined here. This module never parses contract text and
never imports a clause adapter — the dependency runs one way.

Architecture:

    Contract -> Clause Adapter -> Structured Facts -> [this module]
             -> Decision -> Evidence -> Redline / Escalation / Audit

Extracted from liability_policy_engine.py's first working adapter rather
than designed up front — every piece here already had one real consumer
before being generalized, and the LoL adapter's benchmark results (0
false-safe, 0 false-escalation, 98.2% policy-state accuracy, 100%
determinism on the 109-case corpus) are the regression test for this
refactor: they must be exactly unchanged after extraction.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Hashable, List, Optional, Protocol, Tuple

# ---------------------------------------------------------------------------
# Decision states — shared vocabulary across every clause type.
# ---------------------------------------------------------------------------

ACCEPT = "ACCEPT"
ACCEPT_WITH_NOTE = "ACCEPT_WITH_NOTE"
NEGOTIATE = "NEGOTIATE"
MUST_REDLINE = "MUST_REDLINE"
PROHIBITED = "PROHIBITED"
ESCALATE = "ESCALATE"
REQUIRES_REVIEW = "REQUIRES_REVIEW"
NOT_APPLICABLE = "NOT_APPLICABLE"

# Order along the negotiation ladder — REQUIRES_REVIEW and NOT_APPLICABLE
# are deliberately excluded: they mean "no ladder position was reached
# yet," not a point along it.
LADDER_ORDER = [ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, ESCALATE, PROHIBITED]


# Party-role vocabulary: which named roles conventionally sit on which
# side of a commercial contract. Genuinely clause-agnostic — a "Customer"
# is buy-side whether the clause in question is Limitation of Liability or
# Indemnification — so it lives here rather than being duplicated per
# adapter. An adapter maps a role word found in its own clause-specific
# text extraction through this vocabulary to resolve "ours vs. theirs";
# the vocabulary itself has no opinion about what kind of position the
# role holds.
BUY_SIDE_ROLES = {"customer", "client", "licensee", "buyer", "purchaser", "recipient"}
SELL_SIDE_ROLES = {"supplier", "vendor", "contractor", "licensor", "provider", "seller", "company"}


def side_for_role(role: str) -> Optional[str]:
    role_key = role.lower()
    if role_key in BUY_SIDE_ROLES:
        return "buy_side"
    if role_key in SELL_SIDE_ROLES:
        return "sell_side"
    return None


class BasePolicyRuleLike(Protocol):
    """The minimum any clause-specific PolicyRule-like object must expose
    for the shared core to route escalation and fallback language. Clause
    adapters define their own richer Protocol (thresholds, required
    exceptions, whatever else the clause needs) that structurally includes
    these three fields — see liability_policy_engine.PolicyRuleLike."""
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]


# ---------------------------------------------------------------------------
# Negotiation ladder
# ---------------------------------------------------------------------------

@dataclass
class LadderStep:
    label: str
    description: str
    status: str  # "passed" | "current" | "not_reached"


def build_ladder(state: str, step_specs: List[Tuple[str, str]]) -> List[LadderStep]:
    """step_specs is a list of (label, description) pairs already in
    LADDER_ORDER sequence (5 entries: ACCEPT/ACCEPT_WITH_NOTE/NEGOTIATE/
    ESCALATE/PROHIBITED positions) — the adapter builds the descriptions
    (which reference clause-specific language like "annual fees"), this
    function only marks passed/current/not_reached from `state`. A state
    outside LADDER_ORDER (REQUIRES_REVIEW, NOT_APPLICABLE) marks nothing
    as current — those states mean no ladder position was reached."""
    steps = [LadderStep(label, description, "not_reached") for label, description in step_specs]
    if state not in LADDER_ORDER:
        return steps
    idx = LADDER_ORDER.index(state)
    for i, step in enumerate(steps):
        step.status = "passed" if i < idx else ("current" if i == idx else "not_reached")
    return steps


# ---------------------------------------------------------------------------
# Threshold classification — the common "three-tier band" pattern behind
# any policy expressed as preferred / acceptable-max / negotiate-max.
# ---------------------------------------------------------------------------

def classify_by_threshold(
    value: float,
    preferred_max: Optional[float],
    acceptable_max: Optional[float],
    negotiate_max: Optional[float],
) -> str:
    """value <= preferred_max -> ACCEPT; <= acceptable_max -> ACCEPT_WITH_NOTE;
    <= negotiate_max -> NEGOTIATE; otherwise ESCALATE. Any threshold left
    None is treated as "not set" (that band is skipped, not treated as
    unlimited) — mirrors the original inline LoL state machine exactly."""
    if preferred_max is not None and value <= preferred_max:
        return ACCEPT
    if acceptable_max is not None and value <= acceptable_max:
        return ACCEPT_WITH_NOTE
    if negotiate_max is not None and value <= negotiate_max:
        return NEGOTIATE
    return ESCALATE


def escalate_to_for_state(state: str, escalation_authority: Optional[str]) -> Optional[str]:
    """Which states carry a named escalation contact — ESCALATE and
    PROHIBITED route to approval; everything else has no escalation target."""
    return escalation_authority if state in (ESCALATE, PROHIBITED) else None


def fallback_text_for_state(state: str, fallback_text: Optional[str], applicable_states: Tuple[str, ...]) -> Optional[str]:
    """Fallback/redline language is only offered for states the adapter
    designates as redline-eligible (e.g. LoL uses MUST_REDLINE, PROHIBITED,
    NEGOTIATE) — passed in by the adapter since which states warrant a
    redline is a clause-specific policy decision, not a core one."""
    return fallback_text if state in applicable_states else None


# ---------------------------------------------------------------------------
# Directional (asymmetric) position resolution
# ---------------------------------------------------------------------------

@dataclass
class PositionCandidate:
    """One named party's position on a clause, reduced to whatever the
    adapter considers comparable. `dedup_key` must be a hashable value two
    equal positions share (e.g. (kind, numeric value) for a cap) — None
    means "no comparable value was extracted for this role" and the
    candidate participates in role-counting but not in the distinctness
    check, mirroring how an unparsed role is still counted but can't prove
    asymmetry on its own."""
    role: str
    side: Optional[str]  # e.g. "buy_side" | "sell_side" | None if unmapped
    dedup_key: Optional[Hashable]
    summary: str


def resolve_directional_position(
    candidates: List[PositionCandidate], contract_side: str,
    *, position_label: str = "asymmetric positions", value_label: str = "position",
) -> Tuple[Optional[PositionCandidate], Optional[Dict[str, str]], Optional[Dict[str, str]], Optional[str]]:
    """Given every named-role position found in a provision, determines
    which one is "ours" per the playbook's configured contract_side.
    Returns (our_candidate, our_position_dict, counterparty_position_dict,
    unresolved_reason).

    `position_label`/`value_label` let an adapter phrase the abstention
    reason in clause-specific terms (e.g. LoL passes position_label=
    "asymmetric liability positions", value_label="cap") without the core
    algorithm knowing anything about liability, indemnification, or any
    other clause concept.

    Never silently returns only the recognized side: fewer than two
    distinct positions means there's no asymmetry to resolve (not an
    error — returns all-None, caller proceeds with the clause's plain
    general position); a mutual policy facing genuine asymmetry, or an
    unmappable role pair under a directional policy, both return a
    specific reason instead of guessing."""
    if len(candidates) < 2:
        return None, None, None, None

    distinct_values = {c.dedup_key for c in candidates if c.dedup_key is not None}
    if len(distinct_values) <= 1:
        return None, None, None, None  # all sides state the same position — not asymmetric

    if contract_side == "mutual":
        return None, None, None, (
            f"contract defines {position_label} by party, but this playbook is configured "
            f"for a mutual position — cannot determine which {value_label} applies to us"
        )

    ours = [c for c in candidates if c.side == contract_side]
    theirs = [c for c in candidates if c.side is not None and c.side != contract_side]
    if len(ours) != 1 or len(theirs) != 1:
        return None, None, None, (
            f"contract defines {position_label} but the named parties "
            "(" + ", ".join(c.role for c in candidates) + ") could not be confidently mapped "
            f"to our configured contract side ({contract_side})"
        )

    our_c, their_c = ours[0], theirs[0]
    our_dict = {"role": our_c.role, "summary": our_c.summary}
    their_dict = {"role": their_c.role, "summary": their_c.summary}
    return our_c, our_dict, their_dict, None


# ---------------------------------------------------------------------------
# Decision + evidence
# ---------------------------------------------------------------------------

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
    category_treatments: List[Dict[str, str]]  # clause-agnostic list of sub-treatments (carve-outs, etc.)
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
    # Evidence-report labels — default values reproduce the original LoL
    # wording exactly; other adapters override these rather than the core
    # ever guessing what to call a clause-specific concept ("liability",
    # "exposure", "cap", ...).
    summary_label: str = "General cap"
    our_position_label: str = "Our liability"
    counterparty_position_label: str = "Counterparty cap"

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
        lines.append(f"{self.summary_label}: {self.extracted_summary}")
        for ct in self.category_treatments:
            if ct["treatment"] not in ("not_addressed",):
                lines.append(f"{ct['category'].replace('_', ' ').title()}: {ct['treatment'].replace('_', ' ').title()}"
                              + (f" ({ct['cap_summary']})" if ct.get("cap_summary") else ""))
        if self.counterparty_position:
            lines.append(f"{self.counterparty_position_label}: {self.counterparty_position['summary']}")
        if self.our_position:
            lines.append(f"{self.our_position_label}: {self.our_position['summary']}")
        if self.source:
            lines.append(f"Playbook: {self.source}")
        lines.append(f"Policy: {self.policy_limit_summary}")
        lines.append(f"Result: {self.state}")
        lines.append(f'Evidence: "{self.contract_language}"')
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Benchmark safety metrics — shared by every clause adapter's benchmark
# harness (see benchmarks/run_liability_benchmark.py for the first use).
# ---------------------------------------------------------------------------

FALSE_SAFE_EXPECTED_STATES = {NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE, REQUIRES_REVIEW}
FALSE_SAFE_ACTUAL_STATES = {ACCEPT, ACCEPT_WITH_NOTE}


def is_false_safe(expected_state: str, actual_state: str) -> bool:
    """The catastrophic failure mode: the correct answer required attorney
    attention but the engine returned ACCEPT/ACCEPT_WITH_NOTE."""
    return expected_state in FALSE_SAFE_EXPECTED_STATES and actual_state in FALSE_SAFE_ACTUAL_STATES


def is_false_escalation(expected_state: str, actual_state: str) -> bool:
    """The "annoying automation" failure mode: the correct answer was
    clear-cut but the engine sent it to REQUIRES_REVIEW anyway. A system
    that hits zero false-safe by refusing to ever decide isn't safe, it's
    just unhelpful — this is the metric that would catch that."""
    return expected_state != REQUIRES_REVIEW and actual_state == REQUIRES_REVIEW


def decision_hash(decision: PolicyDecision) -> str:
    """Stable hash of a decision's full output — used to verify the
    reproducibility guarantee (same input -> byte-identical output)."""
    return hashlib.sha256(json.dumps(decision.as_dict(), sort_keys=True).encode()).hexdigest()


def check_deterministic(evaluate_once: Callable[[], PolicyDecision], repeats: int = 5) -> bool:
    """Calls `evaluate_once` `repeats` times and confirms every call
    produces a byte-identical decision (via decision_hash)."""
    hashes = {decision_hash(evaluate_once()) for _ in range(repeats)}
    return len(hashes) == 1
