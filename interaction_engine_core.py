"""
Interaction Engine V1 — shared model.

See docs/architecture/interaction_engine_v1_design.md for the approved
architecture this module implements. Three non-negotiable boundaries,
enforced structurally by this module's own shape (not by convention):

  1. The Interaction Engine consumes ONLY policy_engine_core.PolicyDecision
     objects already produced by policy_enforcement.evaluate_active_policies
     — never raw contract text, never a call into any extract_*_facts /
     evaluate_*_policy function, never an LLM. A predicate function's only
     input is Dict[clause_type, PolicyDecision]; nothing in this module
     imports re, requests an LLM client, or takes a contract_text argument.
  2. An InteractionDecision never mutates or wraps a participating
     PolicyDecision — it only references one (by clause_type + a revision
     snapshot for staleness detection, see participating_decision_snapshot).
  3. Evaluation is a pure function of its inputs: same decisions + same
     registered rules -> byte-identical InteractionDecision list, checked
     the same way policy_engine_core.check_deterministic checks a single
     adapter.

Architecture: Contract -> 12 adapters -> PolicyDecisions -> [this module]
-> InteractionDecisions -> review queue (see review_queue.py).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from policy_engine_core import PolicyDecision

# ---------------------------------------------------------------------------
# Interaction-state vocabulary — deliberately separate from PolicyDecision's
# own state vocabulary (policy_engine_core.ACCEPT/NEGOTIATE/...), per design
# doc S3/S4: an interaction is a relationship between two already-resolved
# clause-level states, not a clause-level state itself. Reusing the same
# string values (rather than inventing new ones) lets review_queue.py's
# existing TIER_RANK table classify interaction findings without a second
# ranking table, while `kind` (below) keeps CONFLICT/DEPENDENCY explicit and
# never collapses into one generic "interaction warning."
# ---------------------------------------------------------------------------

CONFLICT = "CONFLICT"
DEPENDENCY = "DEPENDENCY"
_KINDS = (CONFLICT, DEPENDENCY)

# States an InteractionDecision may carry. Reused verbatim from
# policy_engine_core's vocabulary (no MUST_REDLINE/PROHIBITED — an
# interaction never offers a redline of its own, it points at two clauses
# a lawyer must reconcile) plus two interaction-specific states that have
# no clause-level equivalent:
#   NOT_TRIGGERED       — every participant present and resolved; the rule's
#                          predicate did not match. Recorded (not silently
#                          dropped), analogous to PolicyDecision's ACCEPT.
#   INSUFFICIENT_FACTS  — one or more participating clause types has no
#                          PolicyDecision at all this review (no ACTIVE
#                          position) or is itself in a state the rule
#                          cannot safely read (REQUIRES_REVIEW /
#                          EVALUATION_ERROR). The rule never guesses past
#                          this — see _gate_participants below.
ESCALATE = "ESCALATE"
NEGOTIATE = "NEGOTIATE"
REQUIRES_REVIEW = "REQUIRES_REVIEW"
ACCEPT_WITH_NOTE = "ACCEPT_WITH_NOTE"
NOT_TRIGGERED = "NOT_TRIGGERED"
INSUFFICIENT_FACTS = "INSUFFICIENT_FACTS"
# One rule's predicate raising an unexpected exception is isolated exactly
# like policy_enforcement.evaluate_active_policies isolates one clause
# type's extractor/evaluator raising (see interaction_enforcement.py) —
# recorded as a visible, auditable error state, every other rule's
# evaluation proceeds unaffected, and no fabricated decision is ever
# substituted for a failed one.
EVALUATION_ERROR = "EVALUATION_ERROR"

# States that surface as an actionable finding in the review queue —
# mirrors policy_enforcement._ACTIONABLE_STATES exactly in spirit (NOT_
# TRIGGERED and INSUFFICIENT_FACTS are recorded for audit/completeness but
# never shown as something needing attention; INSUFFICIENT_FACTS in
# particular must never be mistaken for "clean," which is why it is its
# own state rather than being folded into NOT_TRIGGERED).
ACTIONABLE_STATES = {ESCALATE, NEGOTIATE, REQUIRES_REVIEW, EVALUATION_ERROR}

# A clause-level PolicyDecision.state the Interaction Engine may safely
# treat as "this participant's facts are resolved enough to reason over."
# NOT_APPLICABLE (no clause at all) and REQUIRES_REVIEW/EVALUATION_ERROR
# (facts themselves are unresolved or evaluation failed) are excluded on
# purpose — an interaction rule must never read category_treatments or
# interaction_facts off a decision in one of those states as if they were
# trustworthy signal. See _gate_participants.
_UNSAFE_PARTICIPANT_STATES = {"NOT_APPLICABLE", "REQUIRES_REVIEW", "EVALUATION_ERROR"}


def _worse(a: str, b: str) -> str:
    """Ceiling combiner for interaction states — same shape as the
    independently-duplicated _worse() helpers already living in
    indemnification_policy_engine.py/termination_policy_engine.py/
    sla_policy_engine.py, promoted once here rather than re-implemented an
    eighth time (design doc S2.1's own recommendation)."""
    order = {NOT_TRIGGERED: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, REQUIRES_REVIEW: 3, ESCALATE: 4}
    return a if order.get(a, 0) >= order.get(b, 0) else b


@dataclass
class InteractionRule:
    """A single registered interaction predicate. See interaction_rules.py
    for the seven launch-catalog instances. `predicate` is a pure function:
    Dict[clause_type, PolicyDecision] (already gated to only the
    participating clause types that are present and resolved — see
    evaluate() below) -> InteractionFinding | None. None means "the
    predicate looked and found nothing to flag" (-> NOT_TRIGGERED, not an
    error and not silently dropped)."""
    interaction_id: str
    label: str
    kind: str  # CONFLICT | DEPENDENCY
    participating_clause_types: Tuple[str, ...]
    ceiling_state: str  # the worst state this rule may ever produce when it fires
    predicate: Callable[[Dict[str, PolicyDecision]], Optional["InteractionFinding"]]
    version: str = "v1"

    def __post_init__(self) -> None:
        if self.kind not in _KINDS:
            raise ValueError(f"{self.interaction_id}: kind must be one of {_KINDS}, got {self.kind!r}")
        if len(self.participating_clause_types) < 2:
            raise ValueError(f"{self.interaction_id}: needs 2+ participating_clause_types")
        if self.ceiling_state not in (ESCALATE, NEGOTIATE, REQUIRES_REVIEW, ACCEPT_WITH_NOTE):
            raise ValueError(f"{self.interaction_id}: invalid ceiling_state {self.ceiling_state!r}")


@dataclass
class InteractionFinding:
    """What a firing predicate returns — the rule-specific half of an
    InteractionDecision. Deliberately narrow: only what the predicate
    itself determined (why it fired, at what severity, referencing which
    already-established facts) — everything else (participating evidence,
    revision snapshot, escalate_to) is assembled generically by evaluate()
    from the participating PolicyDecisions themselves, never duplicated
    here."""
    state: str  # ESCALATE | NEGOTIATE | REQUIRES_REVIEW | ACCEPT_WITH_NOTE — must be <= rule.ceiling_state
    explanation: str
    required_action: str
    matched_facts: Dict[str, str] = field(default_factory=dict)  # short, clause_type-keyed "what matched" notes


@dataclass
class InteractionDecision:
    """The independent output layer — never mutates or wraps a
    participating PolicyDecision (design doc S11). Fully reproducible from
    already-audited inputs: participating_decision_snapshot is enough to
    replay this exact decision (see interaction_enforcement.
    verify_interaction_finding)."""
    interaction_id: str
    label: str
    kind: str
    state: str  # ESCALATE | NEGOTIATE | REQUIRES_REVIEW | ACCEPT_WITH_NOTE | NOT_TRIGGERED | INSUFFICIENT_FACTS
    participating_clause_types: Tuple[str, ...]
    participating_provisions: Dict[str, Optional[Dict[str, str]]]  # clause_type -> controlling_provision dict (verbatim)
    participating_decision_snapshot: Dict[str, Dict[str, Any]]  # clause_type -> {"state":..., "decision_hash":...}
    explanation: str
    required_action: str
    escalate_to: Optional[str] = None
    matched_facts: Dict[str, str] = field(default_factory=dict)
    missing_clause_types: Tuple[str, ...] = ()
    version: str = "v1"
    stale: bool = False
    stale_reason: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "interaction_id": self.interaction_id,
            "label": self.label,
            "kind": self.kind,
            "state": self.state,
            "participating_clause_types": list(self.participating_clause_types),
            "participating_provisions": self.participating_provisions,
            "participating_decision_snapshot": self.participating_decision_snapshot,
            "explanation": self.explanation,
            "required_action": self.required_action,
            "escalate_to": self.escalate_to,
            "matched_facts": self.matched_facts,
            "missing_clause_types": list(self.missing_clause_types),
            "version": self.version,
            "stale": self.stale,
            "stale_reason": self.stale_reason,
        }

    def render_evidence_report(self) -> str:
        """Mirrors PolicyDecision.render_evidence_report()'s shape — see
        design doc S6 for the exact target format this reproduces:
        one block per participating clause type (its controlling_provision
        label + excerpt), then the rule's own explanation/required_action.
        Every line is drawn from data already produced by the participating
        adapters plus this rule's static template text — never a generated
        legal conclusion."""
        lines = [f"Interaction {'requires attention' if self.state in ACTIONABLE_STATES else self.state}", ""]
        for ct in self.participating_clause_types:
            provision = self.participating_provisions.get(ct)
            if provision:
                lines.append(provision["label"])
                lines.append(provision["excerpt"])
                lines.append("")
        lines.append("Why this matters")
        lines.append(self.explanation)
        lines.append("")
        lines.append("Required action")
        lines.append(self.required_action)
        return "\n".join(lines).rstrip()


def decision_snapshot(decision: PolicyDecision) -> Dict[str, Any]:
    """The minimal, stable fingerprint of one participating PolicyDecision
    needed for staleness detection (design doc S5/S7): its state plus a
    content hash of its full as_dict() output. Two snapshots differing in
    either field means that participant's decision changed since the
    interaction was computed — see interaction_enforcement.
    verify_interaction_finding."""
    payload = json.dumps(decision.as_dict(), sort_keys=True, default=str)
    return {"state": decision.state, "decision_hash": hashlib.sha256(payload.encode()).hexdigest()}


def _gate_participants(
    rule: InteractionRule, decisions: Dict[str, PolicyDecision],
) -> Tuple[Optional[Dict[str, PolicyDecision]], Tuple[str, ...]]:
    """Returns (safe_decisions, missing_or_unsafe_clause_types). safe_decisions
    is None (never a partial dict) unless every participating clause type has
    a PolicyDecision AND that decision's state is safe to reason over (see
    _UNSAFE_PARTICIPANT_STATES) — a predicate function is never called with
    a partially-gated input, so it can never accidentally read an unresolved
    or absent participant as if it were resolved."""
    missing: List[str] = []
    safe: Dict[str, PolicyDecision] = {}
    for ct in rule.participating_clause_types:
        decision = decisions.get(ct)
        if decision is None or decision.state in _UNSAFE_PARTICIPANT_STATES:
            missing.append(ct)
        else:
            safe[ct] = decision
    if missing:
        return None, tuple(missing)
    return safe, ()


def _invoke_predicate(predicate, decisions: Dict[str, PolicyDecision], document_facts=None):
    """Call a rule predicate with optional document_facts when it accepts them.

    Launch-catalog rules remain `(decisions) -> Optional[Finding]`. Phase 4
    rules may declare a second parameter for structured ContractDocumentFacts.
    """
    import inspect

    try:
        params = list(inspect.signature(predicate).parameters.values())
    except (TypeError, ValueError):
        return predicate(decisions)
    if len(params) >= 2:
        return predicate(decisions, document_facts)
    return predicate(decisions)


def evaluate(
    decisions: Dict[str, PolicyDecision],
    rules: List[InteractionRule],
    *,
    document_facts=None,
) -> List[InteractionDecision]:
    """Pure function — no I/O, no randomness, no LLM. Evaluates every
    registered rule against `decisions` (the same Dict[clause_type,
    PolicyDecision] policy_enforcement.evaluate_active_policies already
    assembles for one review) and returns one InteractionDecision per rule,
    in `rules`' given order (callers pass a fixed, deterministic list —
    see interaction_rules.LAUNCH_CATALOG) — always one entry per rule,
    never silently omitted, so NOT_TRIGGERED/INSUFFICIENT_FACTS outcomes
    are as auditable as a firing CONFLICT/DEPENDENCY.

    Phase 4: optional `document_facts` (ContractDocumentFacts) hydrates
    lossy/empty category_treatments before gating and is passed to
    predicates that accept a second argument. Predicates still never
    extract from raw contract text.
    """
    if document_facts is not None:
        from contract_facts.interaction_hydration import hydrate_decisions_from_document_facts

        hydrate_decisions_from_document_facts(decisions, document_facts)

    results: List[InteractionDecision] = []
    for rule in rules:
        safe_decisions, missing = _gate_participants(rule, decisions)

        if safe_decisions is None:
            results.append(InteractionDecision(
                interaction_id=rule.interaction_id, label=rule.label, kind=rule.kind,
                state=INSUFFICIENT_FACTS,
                participating_clause_types=rule.participating_clause_types,
                participating_provisions={
                    ct: (decisions[ct].controlling_provision if ct in decisions else None)
                    for ct in rule.participating_clause_types
                },
                participating_decision_snapshot={
                    ct: decision_snapshot(decisions[ct]) for ct in rule.participating_clause_types if ct in decisions
                },
                explanation=(
                    f"This interaction could not be evaluated because the following participating clause "
                    f"type(s) have no established decision to reason over this review: {', '.join(missing)}."
                ),
                required_action="None — insufficient facts to evaluate this interaction",
                missing_clause_types=missing, version=rule.version,
            ))
            continue

        try:
            finding = _invoke_predicate(rule.predicate, safe_decisions, document_facts)
        except Exception as exc:  # noqa: BLE001 — isolation boundary, see EVALUATION_ERROR docstring
            results.append(InteractionDecision(
                interaction_id=rule.interaction_id, label=rule.label, kind=rule.kind,
                state=EVALUATION_ERROR,
                participating_clause_types=rule.participating_clause_types,
                participating_provisions={ct: d.controlling_provision for ct, d in safe_decisions.items()},
                participating_decision_snapshot={ct: decision_snapshot(d) for ct, d in safe_decisions.items()},
                explanation=(
                    f"This interaction could not be evaluated: the deterministic rule engine raised an "
                    f"unexpected error ({type(exc).__name__}). This has not been assessed and requires manual review."
                ),
                required_action="Manual review required — automated interaction evaluation failed.",
                version=rule.version,
            ))
            continue

        if finding is None:
            results.append(InteractionDecision(
                interaction_id=rule.interaction_id, label=rule.label, kind=rule.kind,
                state=NOT_TRIGGERED,
                participating_clause_types=rule.participating_clause_types,
                participating_provisions={ct: d.controlling_provision for ct, d in safe_decisions.items()},
                participating_decision_snapshot={ct: decision_snapshot(d) for ct, d in safe_decisions.items()},
                explanation="Conditions for this interaction rule were not met.",
                required_action="None", version=rule.version,
            ))
            continue

        order = {ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, REQUIRES_REVIEW: 3, ESCALATE: 4}
        if order.get(finding.state, 0) > order.get(rule.ceiling_state, 0):
            raise ValueError(
                f"{rule.interaction_id}: predicate returned state {finding.state!r} above its declared "
                f"ceiling_state {rule.ceiling_state!r} — a rule may never produce a state worse than what "
                f"it was registered to be capable of."
            )

        escalate_to = None
        if finding.state == ESCALATE:
            for d in safe_decisions.values():
                if d.escalate_to:
                    escalate_to = d.escalate_to
                    break

        results.append(InteractionDecision(
            interaction_id=rule.interaction_id, label=rule.label, kind=rule.kind,
            state=finding.state,
            participating_clause_types=rule.participating_clause_types,
            participating_provisions={ct: d.controlling_provision for ct, d in safe_decisions.items()},
            participating_decision_snapshot={ct: decision_snapshot(d) for ct, d in safe_decisions.items()},
            explanation=finding.explanation, required_action=finding.required_action,
            escalate_to=escalate_to, matched_facts=finding.matched_facts, version=rule.version,
        ))
    return results


def interaction_decision_hash(decision: InteractionDecision) -> str:
    """Same pattern as policy_engine_core.decision_hash, one layer up —
    used by the interaction benchmark's determinism gate."""
    return hashlib.sha256(json.dumps(decision.as_dict(), sort_keys=True).encode()).hexdigest()


def check_deterministic(evaluate_once: Callable[[], List[InteractionDecision]], repeats: int = 5) -> bool:
    hashes = {
        tuple(interaction_decision_hash(d) for d in evaluate_once())
        for _ in range(repeats)
    }
    return len(hashes) == 1
