"""
Contract review exception queue — P0 remediation of
docs/architecture/contract_review_exception_ux.md.

Computes the review page's queue/summary view-model server-side, in
Python, rather than in review.html's <script> block — specifically so
the correctness-critical distinction between "passed" and "not
evaluated" / "not applicable" / "evaluation failed" is unit-testable
directly against real PolicyDecision output, and is never inferred in
JavaScript from the mere absence of a finding.

Two structures already carry everything this module reads (no new
persistence, no new policy-engine call):

  - findings (Contract.findings_json): one entry per actionable
    (NEGOTIATE/MUST_REDLINE/PROHIBITED/ESCALATE/REQUIRES_REVIEW) policy
    decision that could be anchored to text, plus a
    policy_state="EVALUATION_ERROR" entry for any clause whose
    evaluation raised (see policy_enforcement.py's
    _finding_from_decision / _error_finding), plus every ordinary
    rule-engine finding.
  - policy_decisions (Contract.policy_decisions_json): one entry PER
    EVALUATED CLAUSE TYPE, keyed by clause_type, including the states
    that never produce a finding at all — ACCEPT, ACCEPT_WITH_NOTE,
    NOT_APPLICABLE. This is the only place a clause's PASS outcome is
    recorded. A clause type with no entry here at all (no ACTIVE policy
    covers it, or legacy/shadow mode only ever evaluates
    limitation_of_liability) was never evaluated — a materially
    different claim from "passed," and this module never conflates the
    two.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import playbook_authoring as pa

# Ordering within the exception queue — deterministic and explicit, never
# inferred from severity text or document position. Lower rank sorts
# first. A policy_state not listed here (i.e. one that never occurs on
# an actionable/error finding — ACCEPT/ACCEPT_WITH_NOTE/NOT_APPLICABLE
# never reach build_review_queue's tier-ranking step at all, see below)
# sorts last defensively rather than raising.
TIER_RANK: Dict[str, int] = {
    "PROHIBITED": 0,
    "MUST_REDLINE": 0,
    "ESCALATE": 0,
    "NEGOTIATE": 1,
    "REQUIRES_REVIEW": 2,
    "EVALUATION_ERROR": 2,
}
_DEFAULT_TIER_RANK = 3

TOP_TIER_STATES = ("PROHIBITED", "MUST_REDLINE", "ESCALATE")
# The only two PolicyDecision states that mean "evaluated and acceptable"
# — the sole source of truth for what "passed" means in this module.
PASSED_STATES = ("ACCEPT", "ACCEPT_WITH_NOTE")

# Interaction Engine V1 (see docs/architecture/interaction_engine_v1_design.md
# S9, interaction_engine_core.py). finding_type == "interaction_decision"
# findings reuse the exact same TIER_RANK table above (ESCALATE/NEGOTIATE/
# REQUIRES_REVIEW/EVALUATION_ERROR are the same strings at both layers by
# design — see interaction_engine_core.py's state-vocabulary docstring) but
# are bucketed into their own list, never merged into policy_exception_
# indices, so a lawyer scanning the queue can never mistake a cross-policy
# interaction for an ordinary single-clause exception.
INTERACTION_ACTIONABLE_STATES = ("ESCALATE", "NEGOTIATE", "REQUIRES_REVIEW", "EVALUATION_ERROR")


def tier_rank(policy_state: Optional[str]) -> int:
    return TIER_RANK.get(policy_state, _DEFAULT_TIER_RANK)


def _clause_label(clause_type: str) -> str:
    return pa.CLAUSE_TYPE_LABELS.get(clause_type, clause_type.replace("_", " ").title())


@dataclass
class PassedCheck:
    clause_type: str
    label: str
    extracted_summary: str
    policy_limit_summary: str


@dataclass
class NotApplicableCheck:
    clause_type: str
    label: str


@dataclass
class ReviewQueueSummary:
    needs_attention: int
    top_tier: int
    negotiate: int
    requires_review: int
    evaluation_error: int
    passed: int
    not_applicable: int
    interactions_needing_attention: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "needs_attention": self.needs_attention, "top_tier": self.top_tier,
            "negotiate": self.negotiate, "requires_review": self.requires_review,
            "evaluation_error": self.evaluation_error, "passed": self.passed,
            "not_applicable": self.not_applicable,
            "interactions_needing_attention": self.interactions_needing_attention,
        }


@dataclass
class ReviewQueue:
    policy_exception_indices: List[int]
    other_finding_indices: List[int]
    summary: ReviewQueueSummary
    passed_checks: List[PassedCheck]
    not_applicable_checks: List[NotApplicableCheck]
    interaction_exception_indices: List[int] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "policy_exception_indices": self.policy_exception_indices,
            "other_finding_indices": self.other_finding_indices,
            "interaction_exception_indices": self.interaction_exception_indices,
            "summary": self.summary.as_dict(),
            "passed_checks": [
                {"clause_type": c.clause_type, "label": c.label,
                 "extracted_summary": c.extracted_summary, "policy_limit_summary": c.policy_limit_summary}
                for c in self.passed_checks
            ],
            "not_applicable_checks": [
                {"clause_type": c.clause_type, "label": c.label} for c in self.not_applicable_checks
            ],
        }


def build_review_queue(findings: List[Dict[str, Any]], policy_decisions: Optional[Dict[str, Any]]) -> ReviewQueue:
    """The single source of truth for how the review page's exception
    queue orders and classifies everything. Pure function — no DB, no
    HTTP, no I/O — so it is directly unit-testable against fixture
    findings/policy_decisions dicts without spinning up a request.

    Ordering rule (documented and tested — see
    tests/test_review_queue.py::TestOrdering): other_finding_indices
    keeps the original findings-array order unchanged (existing
    rule-engine behavior, untouched). policy_exception_indices is
    sorted by (tier_rank(policy_state), original index) — i.e. a stable
    sort keyed primarily on the explicit TIER_RANK table above, with the
    original array index as the deterministic tie-break within a tier.
    Both inputs are already deterministic (policy_state is an
    authoritative engine output; array order is guaranteed deterministic
    by policy_enforcement.py's own ordering contract — see Phase 4's
    "deterministic ordering" requirement), so the same findings list
    always produces the same queue order.
    """
    policy_decisions = policy_decisions or {}

    policy_idxs: List[int] = []
    interaction_idxs: List[int] = []
    other_idxs: List[int] = []
    for i, f in enumerate(findings):
        finding_type = f.get("finding_type")
        if finding_type == "policy_decision":
            policy_idxs.append(i)
        elif finding_type == "interaction_decision":
            interaction_idxs.append(i)
        else:
            other_idxs.append(i)

    policy_idxs.sort(key=lambda i: (tier_rank(findings[i].get("policy_state")), i))
    interaction_idxs.sort(key=lambda i: (tier_rank(findings[i].get("policy_state")), i))
    interactions_needing_attention = sum(
        1 for i in interaction_idxs if findings[i].get("policy_state") in INTERACTION_ACTIONABLE_STATES
    )

    top_tier = sum(1 for i in policy_idxs if findings[i].get("policy_state") in TOP_TIER_STATES)
    negotiate = sum(1 for i in policy_idxs if findings[i].get("policy_state") == "NEGOTIATE")
    requires_review = sum(1 for i in policy_idxs if findings[i].get("policy_state") == "REQUIRES_REVIEW")
    evaluation_error = sum(1 for i in policy_idxs if findings[i].get("policy_state") == "EVALUATION_ERROR")

    # Clause types already represented by an EVALUATION_ERROR finding are
    # excluded from the passed/not-applicable scan below entirely — never
    # double-counted, and never silently absorbed into "passed" merely
    # because an evaluation failure is never written into
    # policy_decisions_json (see policy_enforcement.apply_active_policies:
    # a clause with an error is omitted from policy_decisions on purpose).
    evaluation_error_clause_types = {
        findings[i].get("clause_type") for i in policy_idxs
        if findings[i].get("policy_state") == "EVALUATION_ERROR"
    }

    passed_checks: List[PassedCheck] = []
    not_applicable_checks: List[NotApplicableCheck] = []
    for clause_type, decision in policy_decisions.items():
        if clause_type in evaluation_error_clause_types:
            continue
        decision = decision or {}
        state = decision.get("state")
        label = _clause_label(clause_type)
        if state in PASSED_STATES:
            passed_checks.append(PassedCheck(
                clause_type=clause_type, label=label,
                extracted_summary=decision.get("extracted_summary") or "",
                policy_limit_summary=decision.get("policy_limit_summary") or "",
            ))
        elif state == "NOT_APPLICABLE":
            not_applicable_checks.append(NotApplicableCheck(clause_type=clause_type, label=label))
        # Any other state here (NEGOTIATE/MUST_REDLINE/PROHIBITED/
        # ESCALATE/REQUIRES_REVIEW) is already represented by its own
        # row in policy_exception_indices — intentionally not re-listed
        # here, so a clause is never shown as both "needs attention" and
        # "passed."

    summary = ReviewQueueSummary(
        needs_attention=top_tier + negotiate + requires_review + evaluation_error,
        top_tier=top_tier, negotiate=negotiate, requires_review=requires_review,
        evaluation_error=evaluation_error, passed=len(passed_checks),
        not_applicable=len(not_applicable_checks),
        interactions_needing_attention=interactions_needing_attention,
    )

    return ReviewQueue(
        policy_exception_indices=policy_idxs, other_finding_indices=other_idxs,
        summary=summary, passed_checks=passed_checks, not_applicable_checks=not_applicable_checks,
        interaction_exception_indices=interaction_idxs,
    )
