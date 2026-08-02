"""
Review workflow — the merged findings+redlines review pass.

A "decision" is the one thing an attorney does per finding while reviewing a
contract: accept a redline, edit it, reject it (with a reason), or — for a
finding with no authored redline — flag it for manual drafting or dismiss it.
A comment can be attached alongside any of those. This module is pure logic
(no DB, no HTTP) over that decision map, deliberately separate from main.py
the same way rules_engine.py/clause_quality.py are: testable without the app,
reusable by any route that needs it.

Decisions are keyed by rule_id and never recomputed from findings_json — a
decision is a record of what the attorney actually did, and has to survive
even if a later rule-engine version would classify the same clause
differently.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

REDLINE_ACTIONS = {"accepted", "edited", "rejected"}
NO_REDLINE_ACTIONS = {"flagged", "dismissed"}
VALID_ACTIONS = REDLINE_ACTIONS | NO_REDLINE_ACTIONS

# Decisions that count as "resolved" for progress/finalize purposes — every
# action a finding can carry, since a comment alone is not a decision.
RESOLVING_ACTIONS = VALID_ACTIONS


class DecisionValidationError(Exception):
    pass


def validate_decision(
    rule_id: str, action: str, has_redline: bool, reason: Optional[str], edited_text: Optional[str]
) -> None:
    """Raises DecisionValidationError if this decision doesn't make sense for
    this finding. Never silently coerces an invalid action into a valid one —
    a bad request should fail loudly, not get reinterpreted."""
    if not rule_id:
        raise DecisionValidationError("rule_id is required")
    if action not in VALID_ACTIONS:
        raise DecisionValidationError(f"'{action}' is not a valid decision action")
    if has_redline and action in NO_REDLINE_ACTIONS:
        raise DecisionValidationError(
            f"'{action}' is only valid for a finding with no authored redline; {rule_id} has one"
        )
    if not has_redline and action in REDLINE_ACTIONS:
        raise DecisionValidationError(
            f"'{action}' requires an authored redline; {rule_id} has none — use 'flagged' or 'dismissed'"
        )
    if action == "rejected" and not (reason or "").strip():
        raise DecisionValidationError("a rejection requires a non-empty reason")
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
    first_unresolved_rule_id: Optional[str]

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
            "first_unresolved_rule_id": self.first_unresolved_rule_id,
        }


def compute_progress(findings: List[Any], decisions: Dict[str, Dict[str, Any]]) -> ReviewProgress:
    """findings: list of dicts (or Finding-like objects) with a `.rule_id` /
    `["rule_id"]`. Reads only `action`, never re-derives one from severity or
    redline presence — that's the whole point of a decision record."""
    decisions = decisions or {}
    counts = {"accepted": 0, "edited": 0, "rejected": 0, "flagged": 0, "dismissed": 0}
    first_unresolved = None
    for f in findings:
        rule_id = f["rule_id"] if isinstance(f, dict) else f.rule_id
        d = decisions.get(rule_id)
        if d and d.get("action") in RESOLVING_ACTIONS:
            counts[d["action"]] += 1
        elif first_unresolved is None:
            first_unresolved = rule_id

    resolved = sum(counts.values())
    return ReviewProgress(
        total=len(findings),
        resolved=resolved,
        accepted=counts["accepted"],
        edited=counts["edited"],
        rejected=counts["rejected"],
        flagged=counts["flagged"],
        dismissed=counts["dismissed"],
        is_complete=resolved == len(findings) and len(findings) > 0,
        first_unresolved_rule_id=first_unresolved,
    )


def build_cover_memo_text(filename: str, findings: List[Dict[str, Any]], decisions: Dict[str, Dict[str, Any]]) -> str:
    """One-page-equivalent plain-text memo: everything that did NOT get a
    clean accept, with the attorney's stated reason — for a partner or client
    who won't open the redlined document line by line."""
    decisions = decisions or {}
    lines = [
        f"Negotiation Package — Cover Memo",
        f"Contract: {filename}",
        "=" * 60,
        "",
    ]
    rejected = [(f, decisions[f["rule_id"]]) for f in findings if decisions.get(f["rule_id"], {}).get("action") == "rejected"]
    flagged = [
        (f, decisions[f["rule_id"]])
        for f in findings
        if decisions.get(f["rule_id"], {}).get("action") in ("flagged", "dismissed")
    ]
    accepted = [
        (f, decisions[f["rule_id"]])
        for f in findings
        if decisions.get(f["rule_id"], {}).get("action") in ("accepted", "edited")
    ]

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
    for f in findings:
        d = decisions.get(f["rule_id"], {})
        lines.append(f"[{f['rule_id']}] {f['title']} ({f['severity'].upper()})")
        lines.append(f"  Matched: {f.get('exact_snippet') or f.get('matched_excerpt', '')}")
        if d:
            lines.append(f"  Decision: {d.get('action', 'unresolved')}")
            if d.get("reason"):
                lines.append(f"  Reason: {d['reason']}")
            if d.get("decided_at"):
                lines.append(f"  Decided at: {d['decided_at']}")
        else:
            lines.append("  Decision: UNRESOLVED")
        lines.append("")
    return "\n".join(lines)
