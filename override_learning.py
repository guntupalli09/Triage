"""
Override-pattern detection.

Every time a reviewer overrides a governance-grade policy recommendation
(PROHIBITED/MUST_REDLINE/ESCALATE), review_workflow.requires_policy_
exception_reason already forces a written reason and main.py's
submit_review_decision already stamps the decision entry with
policy_exception=True + policy_original_recommendation — so nothing here
changes what gets recorded. This module is the piece that was missing:
noticing when the SAME override recurs across enough distinct contracts
that it looks less like a one-off exception and more like the playbook's
stated position no longer matching what the firm actually does, and
turning that into an explicit, reviewable suggestion instead of leaving
each override to happen again, silently, next time.

Detection only. This module never edits a PolicyPosition, never creates a
PolicyPosition revision, and never auto-applies anything — a lawyer
decides whether a surfaced pattern should become a playbook change, the
same way every other authoring action in this codebase requires an
explicit human step (see playbook_authoring.py's activation lifecycle).

Pure aggregation logic (detect_override_patterns / extract_override_
occurrences) takes already-loaded Contract rows and touches no DB itself
— same convention review_workflow.py and interaction_engine_core.py
follow, so the clustering rules are unit-testable without a database.
patterns_for_playbook is the one DB-facing wrapper, kept thin.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field as dataclass_field
from typing import Any, Dict, List, Optional, Tuple

# A cluster must recur across at least this many DISTINCT contracts before
# it is surfaced — one override is a documented exception (that's what the
# required reason is for); the same override on three or more separate
# contracts is a pattern worth a lawyer's attention. Never counts multiple
# decisions on the same contract toward the threshold (see
# detect_override_patterns).
DEFAULT_MIN_OCCURRENCES = 3


@dataclass
class OverrideOccurrence:
    """One recorded departure from a governance recommendation, read
    straight off a Contract's review_decisions_json entry — nothing here
    is re-derived or re-judged, only re-surfaced."""
    contract_id: int
    finding_key: str
    rule_id: str
    clause_type: Optional[str]
    original_recommendation: str
    action: str
    reason: Optional[str]
    decided_at: Optional[str]
    decided_by: Optional[str]
    business_unit: Optional[str]
    customer_type: Optional[str]
    deal_value: Optional[float]


@dataclass
class OverridePattern:
    """One recurring departure — same rule_id, same original
    recommendation, same resulting action, seen across >= min_occurrences
    distinct contracts.

    segment_context is set only when every occurrence in the cluster
    shares the same (business_unit, customer_type) pair — a narrower,
    more actionable signal ("this only happens for Enterprise deals," see
    the segment conditionality feature in models.PolicyPosition) than
    "reviewers override this rule sometimes." A mixed cluster (different
    business units/customer types) leaves segment_context as None rather
    than guessing at a scope the data doesn't actually support."""
    clause_type: Optional[str]
    rule_id: str
    original_recommendation: str
    overriding_action: str
    occurrences: List[OverrideOccurrence] = dataclass_field(default_factory=list)
    segment_context: Optional[Dict[str, Any]] = None

    @property
    def count(self) -> int:
        return len({o.contract_id for o in self.occurrences})

    @property
    def contract_ids(self) -> List[int]:
        return sorted({o.contract_id for o in self.occurrences})

    def suggestion_text(self) -> str:
        scope = ""
        if self.segment_context:
            bits = [f"{k}={v}" for k, v in self.segment_context.items() if v is not None]
            if bits:
                scope = f" for {', '.join(bits)}"
        clause_label = self.clause_type or "this clause"
        return (
            f"Reviewers overrode the {self.original_recommendation} recommendation on "
            f"{self.rule_id!r} to {self.overriding_action!r} in {self.count} separate "
            f"contracts{scope}. Consider updating the {clause_label} playbook position so "
            f"this is the standard outcome instead of a recorded exception every time."
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "clause_type": self.clause_type,
            "rule_id": self.rule_id,
            "original_recommendation": self.original_recommendation,
            "overriding_action": self.overriding_action,
            "count": self.count,
            "contract_ids": self.contract_ids,
            "segment_context": self.segment_context,
            "suggestion": self.suggestion_text(),
        }


def extract_override_occurrences(contract: Any) -> List[OverrideOccurrence]:
    """Every governance-policy-exception decision recorded on one
    Contract. Reads only review_decisions_json + findings_json — both
    already-decrypted attributes on a loaded Contract, same as every
    other reader of these columns (build_audit_trail_text, the review
    route, etc.). "Is this an override" is never re-decided here: it is
    exactly entry["policy_exception"], the flag review_workflow.
    requires_policy_exception_reason already computed once, at decision
    time, in main.py's submit_review_decision."""
    decisions = contract.review_decisions_json or {}
    findings = contract.findings_json or []
    occurrences: List[OverrideOccurrence] = []
    for key, entry in decisions.items():
        if not entry.get("policy_exception"):
            continue
        original = entry.get("policy_original_recommendation")
        rule_id = entry.get("rule_id")
        action = entry.get("action")
        if not original or not rule_id or not action:
            continue

        clause_type = None
        try:
            index = int(key.rsplit("#", 1)[1])
            clause_type = findings[index].get("clause_type")
        except (IndexError, ValueError, TypeError):
            pass

        occurrences.append(OverrideOccurrence(
            contract_id=contract.id, finding_key=key, rule_id=rule_id,
            clause_type=clause_type, original_recommendation=original, action=action,
            reason=entry.get("reason"), decided_at=entry.get("decided_at"),
            decided_by=entry.get("decided_by"),
            business_unit=getattr(contract, "review_business_unit", None),
            customer_type=getattr(contract, "review_customer_type", None),
            deal_value=getattr(contract, "review_deal_value", None),
        ))
    return occurrences


def _cluster_key(o: OverrideOccurrence) -> Tuple[str, str, str]:
    return (o.rule_id, o.original_recommendation, o.action)


def _shared_segment_context(occurrences: List[OverrideOccurrence]) -> Optional[Dict[str, Any]]:
    business_units = {o.business_unit for o in occurrences}
    customer_types = {o.customer_type for o in occurrences}
    if len(business_units) == 1 and len(customer_types) == 1:
        bu, ct = next(iter(business_units)), next(iter(customer_types))
        if bu is not None or ct is not None:
            return {"business_unit": bu, "customer_type": ct}
    return None


def detect_override_patterns(
    contracts: List[Any], *, min_occurrences: int = DEFAULT_MIN_OCCURRENCES,
) -> List[OverridePattern]:
    """The core aggregation: every governance override across `contracts`
    (already scoped by the caller — patterns_for_playbook scopes to one
    playbook; this function does no DB querying itself), grouped by
    (rule_id, original_recommendation, resulting action), kept only when
    a cluster recurs across >= min_occurrences DISTINCT contracts —
    OverridePattern.count deliberately counts distinct contract ids, not
    raw occurrences, so a single contract can never manufacture a
    "pattern" on its own no matter how many findings it has (and a
    decision that gets overwritten in place — see review_workflow.py —
    can never double-count either, since only the current entry for a
    finding_key is ever read). Sorted by count descending, then rule_id,
    for a stable, most-actionable-first ordering."""
    all_occurrences: List[OverrideOccurrence] = []
    for contract in contracts:
        all_occurrences.extend(extract_override_occurrences(contract))

    clusters: Dict[Tuple[str, str, str], List[OverrideOccurrence]] = defaultdict(list)
    for o in all_occurrences:
        clusters[_cluster_key(o)].append(o)

    patterns: List[OverridePattern] = []
    for (rule_id, original, action), occurrences in clusters.items():
        distinct_contracts = {o.contract_id for o in occurrences}
        if len(distinct_contracts) < min_occurrences:
            continue
        patterns.append(OverridePattern(
            clause_type=occurrences[0].clause_type, rule_id=rule_id,
            original_recommendation=original, overriding_action=action,
            occurrences=occurrences, segment_context=_shared_segment_context(occurrences),
        ))

    patterns.sort(key=lambda p: (-p.count, p.rule_id))
    return patterns


def patterns_for_playbook(db, playbook_id: int, *, min_occurrences: int = DEFAULT_MIN_OCCURRENCES) -> List[OverridePattern]:
    """DB-facing wrapper: every Contract ever reviewed against this
    playbook, aggregated through detect_override_patterns. The one
    function routes should call — kept thin and separate from the pure
    aggregation above so the clustering rules stay testable without a
    database (see tests/test_override_learning.py)."""
    from models import Contract  # local import: avoids a module-load-time
    # dependency on models.py for callers that only need the pure functions.
    contracts = db.query(Contract).filter(Contract.playbook_id == playbook_id).all()
    return detect_override_patterns(contracts, min_occurrences=min_occurrences)
