"""Authority separation for generic vs policy/interaction findings (Phase 7).

Decision (explicit, preserved Active/Draft boundary):

1. **Authoritative** — `finding_type` in {policy_decision, interaction_decision}
   produced from ACTIVE PolicyPositions / Interaction Engine. These drive
   document triage (`document_aggregation`), finalization attention, and
   playbook enforcement.

2. **Supplemental generic** — rule-engine findings whose rule_id overlaps
   Liability / Indemnification families **when** an Active policy decision
   already exists for that family (state not NOT_APPLICABLE / EVALUATION_ERROR).
   They remain visible for transparency but do **not** contribute to:
   - risk_dashboard scores
   - signature blocking / workflow blocking lists
   - review progress `total` / completion (counted separately as supplemental)

3. **Standalone generic** — all other rule-engine findings (no Active policy
   coverage for that family). Full weight in risk, blocking, and review counts.

4. **UNKNOWN stays UNKNOWN** — never promote supplemental generics to ACCEPT
   or clear a REQUIRES_REVIEW policy decision. Active/Draft: only ACTIVE
   positions create authoritative policy findings
   (`snapshot_active_positions`).

5. Draft / NEEDS_REVIEW / APPROVED positions never enforce and never flip
   overlapping generics to supplemental via this module.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# Generic rule_ids that overlap Liability / Indemnification adapters.
LIABILITY_OVERLAP_RULE_IDS: frozenset = frozenset({
    "H_LOL_01",
    "H_LOL_CARVEOUT_01",
    "H_LOL_NO_CARVEOUT_01",
    "H_ASYMMETRIC_LIABILITY_01",
    "H_CONSEQUENTIAL_01",
})

INDEMNIFICATION_OVERLAP_RULE_IDS: frozenset = frozenset({
    "H_INDEM_01",
    "H_INDEM_ONEWAY_01",
})

OVERLAP_RULE_IDS = LIABILITY_OVERLAP_RULE_IDS | INDEMNIFICATION_OVERLAP_RULE_IDS

_UNSAFE_POLICY_STATES = frozenset({
    "NOT_APPLICABLE", "EVALUATION_ERROR", None, "",
})

AUTHORITY_AUTHORITATIVE = "authoritative"
AUTHORITY_SUPPLEMENTAL = "supplemental_generic"
AUTHORITY_STANDALONE = "standalone_generic"


def _get(finding: Any, key: str, default=None):
    if isinstance(finding, dict):
        return finding.get(key, default)
    return getattr(finding, key, default)


def _set_authority(finding: Any, authority: str) -> Any:
    if isinstance(finding, dict):
        out = dict(finding)
        out["authority_layer"] = authority
        return out
    # Finding dataclasses are typically frozen; callers should annotate dicts.
    return finding


def policy_families_with_active_authority(
    policy_decisions: Optional[Dict[str, Any]],
) -> Set[str]:
    """Clause families where Active policy produced a usable decision."""
    if not policy_decisions:
        return set()
    active: Set[str] = set()
    for clause_type, decision in policy_decisions.items():
        if not isinstance(decision, dict):
            continue
        state = decision.get("state")
        if state in _UNSAFE_POLICY_STATES:
            continue
        if clause_type in ("limitation_of_liability", "indemnification"):
            active.add(clause_type)
    return active


def classify_authority(
    finding: Any,
    *,
    active_families: Optional[Set[str]] = None,
) -> str:
    finding_type = _get(finding, "finding_type")
    if finding_type in ("policy_decision", "interaction_decision"):
        return AUTHORITY_AUTHORITATIVE
    rule_id = _get(finding, "rule_id") or ""
    families = active_families or set()
    if "limitation_of_liability" in families and rule_id in LIABILITY_OVERLAP_RULE_IDS:
        return AUTHORITY_SUPPLEMENTAL
    if "indemnification" in families and rule_id in INDEMNIFICATION_OVERLAP_RULE_IDS:
        return AUTHORITY_SUPPLEMENTAL
    return AUTHORITY_STANDALONE


def annotate_findings_authority(
    findings: Sequence[Any],
    policy_decisions: Optional[Dict[str, Any]],
) -> List[Any]:
    """Return findings with authority_layer set (dict findings only mutated via copy)."""
    active = policy_families_with_active_authority(policy_decisions)
    out: List[Any] = []
    for f in findings:
        authority = classify_authority(f, active_families=active)
        out.append(_set_authority(f, authority))
    return out


def is_supplemental(finding: Any) -> bool:
    return _get(finding, "authority_layer") == AUTHORITY_SUPPLEMENTAL


def actionable_findings(findings: Sequence[Any]) -> List[Any]:
    """Findings that count for review progress / blocking / risk."""
    return [f for f in findings if not is_supplemental(f)]


def supplemental_findings(findings: Sequence[Any]) -> List[Any]:
    return [f for f in findings if is_supplemental(f)]


def partition_findings(
    findings: Sequence[Any],
    policy_decisions: Optional[Dict[str, Any]],
) -> Tuple[List[Any], List[Any], List[Any]]:
    """Return (authoritative, standalone_generic, supplemental_generic)."""
    annotated = annotate_findings_authority(findings, policy_decisions)
    auth, stand, supp = [], [], []
    for f in annotated:
        layer = _get(f, "authority_layer")
        if layer == AUTHORITY_AUTHORITATIVE:
            auth.append(f)
        elif layer == AUTHORITY_SUPPLEMENTAL:
            supp.append(f)
        else:
            stand.append(f)
    return auth, stand, supp


def apply_authority_separation(
    findings: List[Any],
    policy_decisions: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Annotate findings and recompute risk/blocking from non-supplemental ones.

    Returns dict with annotated findings plus risk_dashboard and blocking lists
    suitable for persisting on Contract after policy cutover.
    """
    from risk_dashboard import compute_risk_dashboard

    annotated = annotate_findings_authority(findings, policy_decisions)
    # Phase 6: strip mutuality redlines on supplemental / already-mutual findings.
    try:
        from redline_templates import render_redline
    except ImportError:  # pragma: no cover
        render_redline = None  # type: ignore

    cleaned: List[Any] = []
    for f in annotated:
        if not isinstance(f, dict):
            cleaned.append(f)
            continue
        out = dict(f)
        if render_redline is not None and (
            out.get("authority_layer") == AUTHORITY_SUPPLEMENTAL
            or (out.get("party_direction") or {}).get("mutuality_status") == "mutual"
        ):
            # Re-render so mutuality templates become None when inappropriate.
            out["redline"] = render_redline(out)
        cleaned.append(out)

    actionable = actionable_findings(cleaned)
    # Risk scores ignore supplemental overlap when Active policy owns the family.
    dashboard = compute_risk_dashboard(actionable)

    blocking = [
        _get(f, "rule_id") for f in actionable
        if (_get(f, "severity") in ("high", "critical") or getattr(_get(f, "severity"), "value", None) in ("high", "critical"))
        and _get(f, "finding_type") not in ("policy_decision", "interaction_decision")
    ]
    # Keep policy/interaction actionable signals separate — document_aggregation
    # already owns triage from policy_decisions_json.
    return {
        "findings": cleaned,
        "risk_dashboard": dashboard.as_dict() if hasattr(dashboard, "as_dict") else dashboard,
        "supplemental_count": len(supplemental_findings(cleaned)),
        "actionable_count": len(actionable),
        "blocking_findings": blocking,
    }
