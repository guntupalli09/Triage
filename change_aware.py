"""
Change-aware reconfirmation of policy / interaction decisions.

If a lawyer (or a counterparty revision) changes a provision that a
policy decision or cross-policy interaction depended on, the old
conclusion must not silently remain valid.

Detection is deterministic: each persisted policy decision carries an
evidence excerpt (contract_language) and optional start/end indexes.
If that excerpt no longer appears in the current document text, the
clause type is affected.

Unaffected clause-type decisions are left intact. Affected clause types
are marked stale (and dependent interactions are marked stale via the
existing interaction_enforcement helpers). Optional re-evaluation runs
only the affected adapters through the existing policy_enforcement path
and merges results back into the frozen snapshot.

This module never asks an LLM whether a decision is still valid.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from models import Contract
import interaction_enforcement as ixe
import playbook_authoring as pa


def _normalize(text: str) -> str:
    return " ".join((text or "").split())


def evidence_still_present(contract_text: str, excerpt: Optional[str], start: Optional[int] = None, end: Optional[int] = None) -> bool:
    if not excerpt or not excerpt.strip():
        return True  # no anchored evidence → cannot claim it vanished
    excerpt_n = _normalize(excerpt)
    text_n = _normalize(contract_text)
    if excerpt_n and excerpt_n in text_n:
        return True
    raw = excerpt.strip()
    if raw and raw in (contract_text or ""):
        return True
    if start is not None and end is not None and 0 <= start < end <= len(contract_text or ""):
        window = contract_text[start:end]
        if _normalize(window) == excerpt_n:
            return True
    return False


def affected_clause_types(contract: Contract, new_text: str) -> List[str]:
    """Clause types whose controlling evidence is no longer in ``new_text``."""
    decisions = contract.policy_decisions_json or {}
    affected: List[str] = []
    for clause_type, decision in decisions.items():
        if not isinstance(decision, dict):
            continue
        excerpt = decision.get("contract_language") or ""
        if not excerpt:
            controlling = decision.get("controlling_provision") or {}
            excerpt = controlling.get("excerpt") or controlling.get("text") or ""
        if not evidence_still_present(new_text, excerpt, decision.get("start_index"), decision.get("end_index")):
            affected.append(clause_type)
    return affected


def mark_decisions_stale(contract: Contract, clause_types: List[str], *, reason: str) -> Dict[str, Any]:
    """Records staleness without mutating the original policy_decisions_json
    snapshot (same convention as interaction_staleness_json). Policy
    decision staleness lives under a reserved key on
    interaction_staleness_json so we do not need a new encrypted column
    for a system-computed flag that never embeds contract text."""
    newly = []
    for ct in clause_types:
        label = pa.CLAUSE_TYPE_LABELS.get(ct, ct.replace("_", " ").title())
        ixe.mark_dependent_interactions_stale(contract, ct, label)
        newly.append(ct)
    merged = dict(contract.interaction_staleness_json or {})
    policy_stale = dict(merged.get("_policy_decision_staleness") or {})
    for ct in clause_types:
        if policy_stale.get(ct, {}).get("stale"):
            continue
        label = pa.CLAUSE_TYPE_LABELS.get(ct, ct.replace("_", " ").title())
        policy_stale[ct] = {"stale": True, "stale_reason": reason.format(label=label)}
    merged["_policy_decision_staleness"] = policy_stale
    contract.interaction_staleness_json = merged
    return {"newly_stale_clause_types": newly, "policy_staleness": policy_stale}


def preserved_clause_types(contract: Contract, affected: List[str]) -> List[str]:
    decisions = contract.policy_decisions_json or {}
    affected_set = set(affected)
    return [ct for ct in decisions.keys() if ct not in affected_set]


def reconfirm_against_text(
    db: Session,
    contract: Contract,
    new_text: str,
    *,
    reevaluate_affected: bool = False,
) -> Dict[str, Any]:
    """Compare ``new_text`` to persisted evidence. Marks affected decisions
    stale. When ``reevaluate_affected`` is True and a playbook is attached,
    re-runs policy_enforcement for the whole document then *restores*
    unaffected clause decisions from the frozen snapshot so unrelated
    conclusions are not rewritten by a non-deterministic discovery pass.
    """
    original_decisions = dict(contract.policy_decisions_json or {})
    original_interactions = dict(contract.interaction_decisions_json or {})
    original_revision_meta = dict(contract.policy_revision_metadata_json or {})
    affected = affected_clause_types(contract, new_text)
    preserved = preserved_clause_types(contract, affected)
    stale_info = mark_decisions_stale(
        contract, affected,
        reason="The controlling language for {label} changed. This decision must be reconfirmed.",
    )

    reevaluated = None
    if reevaluate_affected and affected and contract.playbook_id:
        from models import Playbook
        import policy_enforcement
        playbook = db.query(Playbook).filter(Playbook.id == contract.playbook_id).first()
        if playbook is not None:
            findings = list(contract.findings_json or [])
            result = policy_enforcement.apply_policies_for_review(
                db, playbook, new_text, findings,
                contract_id=contract.id,
                context={
                    "business_unit": contract.review_business_unit,
                    "customer_type": contract.review_customer_type,
                    "deal_value": contract.review_deal_value,
                },
            )
            new_decisions = dict(result.get("policy_decisions") or {})
            # Restore unaffected frozen decisions — they remain the historical
            # source of truth for unchanged language.
            merged = dict(new_decisions)
            for ct in preserved:
                if ct in original_decisions:
                    merged[ct] = original_decisions[ct]
            contract.policy_decisions_json = merged
            new_meta = dict(result.get("policy_revision_metadata") or {})
            merged_meta = dict(new_meta)
            for ct in preserved:
                if ct in original_revision_meta:
                    merged_meta[ct] = original_revision_meta[ct]
            contract.policy_revision_metadata_json = merged_meta
            contract.interaction_decisions_json = result.get("interaction_decisions") or original_interactions
            if result.get("document_facts") is not None:
                contract.document_facts_json = result["document_facts"]
            reevaluated = {
                "affected_requiring_reconfirm": affected,
                "preserved": preserved,
            }

    return {
        "affected_clause_types": affected,
        "preserved_clause_types": preserved,
        "stale": stale_info,
        "reevaluated": reevaluated,
        "text_unchanged": not affected and _normalize(new_text) == _normalize(contract.contract_text or ""),
    }


def policy_staleness_map(contract: Contract) -> Dict[str, Any]:
    existing = contract.interaction_staleness_json or {}
    return dict(existing.get("_policy_decision_staleness") or {})
