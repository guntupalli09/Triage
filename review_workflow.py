"""
Review workflow — the merged findings+redlines review pass.

A "decision" is the one thing an attorney does per finding while reviewing a
contract: accept a redline, edit it, reject it (with a reason), or — for a
finding with no authored redline — flag it for manual drafting or dismiss it.
A comment can be attached alongside any of those. This module is pure logic
(no DB, no HTTP) over that decision map, deliberately separate from main.py
the same way rules_engine.py/clause_quality.py are: testable without the app,
reusable by any route that needs it.

Decisions are keyed by finding_key — NOT bare rule_id. A rule can fire more
than once in the same document (the same fee-shifting or liability language
showing up in two different clauses is common in real contracts), so rule_id
alone is not a unique identifier for a finding — deciding on one occurrence
would silently apply that decision to every occurrence of the same rule.
finding_key is "{rule_id}#{position in the findings list}", unique per
finding regardless of how many other findings share its rule_id. Decisions
are never recomputed from findings_json — a decision is a record of what the
attorney actually did, and has to survive even if a later rule-engine
version would classify the same clause differently.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

REDLINE_ACTIONS = {"accepted", "edited", "rejected"}
NO_REDLINE_ACTIONS = {"flagged", "dismissed"}
VALID_ACTIONS = REDLINE_ACTIONS | NO_REDLINE_ACTIONS

# Decisions that count as "resolved" for progress/finalize purposes — every
# action a finding can carry, since a comment alone is not a decision.
RESOLVING_ACTIONS = VALID_ACTIONS


class DecisionValidationError(Exception):
    pass


# Policy states whose recommendation is authoritative governance: blocked
# language, mandatory redlines, and escalations. Departing from one of
# these is an exception to policy and must carry a documented reason (UX
# walkthrough P0-5). Kept here, next to the validator every decision path
# goes through, so no route/template/JS handler can decide for itself
# whether a reason is required — templates/review.html mirrors this list
# for labelling only, never for enforcement.
GOVERNANCE_POLICY_STATES = frozenset({"PROHIBITED", "MUST_REDLINE", "ESCALATE"})

# Actions that follow the deterministic recommendation as-authored. Every
# other action on a governance finding overrides, excepts, or materially
# departs from it.
_POLICY_CONFORMING_ACTIONS = frozenset({"accepted"})


def requires_policy_exception_reason(
    action: str, policy_state: Optional[str], finding_type: Optional[str]
) -> bool:
    """True when this decision is a departure from an authoritative policy
    recommendation and therefore requires an explicit reason. The single
    server-side predicate — used by validate_decision, and by nothing that
    can be skipped from the client."""
    if finding_type != "policy_decision":
        return False
    if policy_state not in GOVERNANCE_POLICY_STATES:
        return False
    return action not in _POLICY_CONFORMING_ACTIONS


def finding_key(index: int, rule_id: str) -> str:
    """The stable identity of one finding *occurrence* — see module
    docstring for why rule_id alone can't be used as this key."""
    return f"{rule_id}#{index}"


def _rule_id_of(f: Any) -> str:
    return f["rule_id"] if isinstance(f, dict) else f.rule_id


def keyed_findings(findings: Sequence[Any]) -> List[Any]:
    """Every finding paired with its finding_key, in document order."""
    return [(finding_key(i, _rule_id_of(f)), f) for i, f in enumerate(findings)]


def validate_decision(
    finding_key: str, action: str, has_redline: bool, reason: Optional[str], edited_text: Optional[str],
    policy_state: Optional[str] = None, finding_type: Optional[str] = None,
) -> None:
    """Raises DecisionValidationError if this decision doesn't make sense for
    this finding. Never silently coerces an invalid action into a valid one —
    a bad request should fail loudly, not get reinterpreted.

    `policy_state`/`finding_type` describe the finding being decided on;
    when they identify a governance-grade policy recommendation, any
    departure from it requires a non-empty, non-whitespace reason. This is
    the ONLY place that decision is made — the previous behavior (reason
    required for "rejected" only) meant an ESCALATE/MUST_REDLINE finding
    with no fallback text could be excepted through the "flagged" path with
    no reason captured at all (UX walkthrough P0-5)."""
    if not finding_key:
        raise DecisionValidationError("finding_key is required")
    if action not in VALID_ACTIONS:
        raise DecisionValidationError(f"'{action}' is not a valid decision action")
    if has_redline and action in NO_REDLINE_ACTIONS:
        raise DecisionValidationError(
            f"'{action}' is only valid for a finding with no authored redline; {finding_key} has one"
        )
    if not has_redline and action in REDLINE_ACTIONS:
        raise DecisionValidationError(
            f"'{action}' requires an authored redline; {finding_key} has none — use 'flagged' or 'dismissed'"
        )
    if action == "rejected" and not (reason or "").strip():
        raise DecisionValidationError("a rejection requires a non-empty reason")
    if requires_policy_exception_reason(action, policy_state, finding_type) and not (reason or "").strip():
        raise DecisionValidationError(
            "This decision departs from an approved policy position, so it requires a written "
            "reason for the audit record. Enter why this exception is being granted."
        )
    if action == "edited" and not (edited_text or "").strip():
        raise DecisionValidationError("an edit requires non-empty edited_text")


@dataclass
class ReviewProgress:
    total: int
    resolved: int
    accepted: int
    edited: int
    rejected: int
    flagged: int
    dismissed: int
    is_complete: bool
    first_unresolved_key: Optional[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "resolved": self.resolved,
            "accepted": self.accepted,
            "edited": self.edited,
            "rejected": self.rejected,
            "flagged": self.flagged,
            "dismissed": self.dismissed,
            "is_complete": self.is_complete,
            "first_unresolved_key": self.first_unresolved_key,
        }


def compute_progress(findings: List[Any], decisions: Dict[str, Dict[str, Any]]) -> ReviewProgress:
    """findings: list of dicts (or Finding-like objects) with a `.rule_id` /
    `["rule_id"]`. Reads only `action`, never re-derives one from severity or
    redline presence — that's the whole point of a decision record.

    Phase 7: supplemental_generic findings (overlapping LoL/Indem generics
    when Active policy already covers that family) are excluded from
    `total` / completion — they remain on the finding list for transparency
    but do not block review finalization counts.
    """
    from contract_facts.finding_authority import actionable_findings

    decisions = decisions or {}
    countable = actionable_findings(findings)
    counts = {"accepted": 0, "edited": 0, "rejected": 0, "flagged": 0, "dismissed": 0}
    first_unresolved = None
    for key, _f in keyed_findings(countable):
        d = decisions.get(key)
        if d and d.get("action") in RESOLVING_ACTIONS:
            counts[d["action"]] += 1
        elif first_unresolved is None:
            first_unresolved = key

    resolved = sum(counts.values())
    return ReviewProgress(
        total=len(countable),
        resolved=resolved,
        accepted=counts["accepted"],
        edited=counts["edited"],
        rejected=counts["rejected"],
        flagged=counts["flagged"],
        dismissed=counts["dismissed"],
        is_complete=resolved == len(countable) and len(countable) > 0,
        first_unresolved_key=first_unresolved,
    )


def build_cover_memo_text(filename: str, findings: List[Dict[str, Any]], decisions: Dict[str, Dict[str, Any]],
                           document_state: Optional[str] = None) -> str:
    """One-page-equivalent plain-text memo: everything that did NOT get a
    clean accept, with the attorney's stated reason — for a partner or client
    who won't open the redlined document line by line.

    Candidate 3 final pre-freeze blocker remediation (Blocker 5) --
    `document_state` is the SAME aggregated, policy/interaction-aware
    signal the dashboard/history/review/full-report/PDF surfaces already
    read (document_aggregation.aggregate_document_state); when it
    indicates a material policy or interaction issue, that must be
    visible on this memo too, never silently absent merely because every
    rule-engine finding individually got a clean decision."""
    decisions = decisions or {}
    lines = [
        f"Negotiation Package — Cover Memo",
        f"Contract: {filename}",
        "=" * 60,
        "",
    ]
    if document_state in ("HAS_CRITICAL_INTERACTION", "HAS_POLICY_VIOLATION", "REQUIRES_REVIEW", "CONFIGURATION_UNRESOLVED"):
        lines.append(
            "NEEDS ATTENTION — deterministic policy/interaction review found a material issue "
            "not reflected in the rule-engine findings below. Consult the full report before "
            "relying on this package alone."
        )
        lines.append("")
    kf = keyed_findings(findings)
    rejected = [(f, decisions[k]) for k, f in kf if decisions.get(k, {}).get("action") == "rejected"]
    flagged = [(f, decisions[k]) for k, f in kf if decisions.get(k, {}).get("action") in ("flagged", "dismissed")]
    accepted = [(f, decisions[k]) for k, f in kf if decisions.get(k, {}).get("action") in ("accepted", "edited")]

    lines.append(f"{len(accepted)} accepted, {len(rejected)} rejected, {len(flagged)} flagged for manual drafting.")
    lines.append("")

    if rejected:
        lines.append("REJECTED — reviewer did not accept the suggested redline")
        lines.append("-" * 60)
        for f, d in rejected:
            lines.append(f"[{f['rule_id']}] {f['title']}")
            lines.append(f"  Reason: {d.get('reason', '(no reason given)')}")
            lines.append("")

    if flagged:
        lines.append("FLAGGED FOR MANUAL DRAFTING — no deterministic redline exists for these")
        lines.append("-" * 60)
        for f, d in flagged:
            status = "Dismissed" if d.get("action") == "dismissed" else "Needs manual drafting"
            lines.append(f"[{f['rule_id']}] {f['title']} — {status}")
            lines.append(f"  {f.get('rationale', '')}")
            lines.append("")

    if not rejected and not flagged:
        lines.append("Every finding was accepted as suggested — nothing requires further attention.")

    return "\n".join(lines)


def build_audit_trail_text(filename: str, rule_engine_version: str, findings: List[Dict[str, Any]], decisions: Dict[str, Dict[str, Any]]) -> str:
    """Malpractice-insurance-grade record: every rule that fired and what the
    attorney did about it, timestamped. Plain text, not fabricated
    step-timing — see review_workflow.py's docstring and main.py's audit
    route for what this deliberately does NOT claim (no per-stage pipeline
    timestamps; the engine doesn't record those)."""
    decisions = decisions or {}
    lines = [
        f"Audit Trail — {filename}",
        f"Rule Engine: v{rule_engine_version}",
        "=" * 60,
        "",
    ]
    for key, f in keyed_findings(findings):
        d = decisions.get(key, {})
        lines.append(f"[{f['rule_id']}] {f['title']} ({f['severity'].upper()})")
        lines.append(f"  Matched: {f.get('exact_snippet') or f.get('matched_excerpt', '')}")
        if d:
            if d.get("policy_original_recommendation"):
                # Policy overrides must never be silent in the exported
                # record either — this is the original deterministic
                # recommendation this decision overrode, not what was
                # decided (see main.py's submit_review_decision).
                lines.append(f"  Original policy recommendation: {d['policy_original_recommendation']}")
            lines.append(f"  Decision: {d.get('action', 'unresolved')}")
            if d.get("reason"):
                lines.append(f"  Reason: {d['reason']}")
            if d.get("decided_by"):
                lines.append(f"  Decided by: {d['decided_by']}")
            if d.get("decided_at"):
                lines.append(f"  Decided at: {d['decided_at']}")
        else:
            lines.append("  Decision: UNRESOLVED")
        lines.append("")
    return "\n".join(lines)
