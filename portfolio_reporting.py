"""
Portfolio reporting over the same canonical fact index used for search.

Every aggregate is tenant-scoped. Drill-down returns the contract_ids that
produced the bucket so the UI can link back to persisted reviews rather
than re-running analysis.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models import ContractFactIndex
from portfolio_query import serialize_index_row


def _base_query(db: Session, tenant_id: int, workspace_id: Optional[int] = None, requester_user_id: Optional[int] = None):
    q = db.query(ContractFactIndex).filter(ContractFactIndex.tenant_id == tenant_id)
    if workspace_id is not None:
        q = q.filter(ContractFactIndex.workspace_id == workspace_id)
    if requester_user_id is not None:
        q = q.filter(ContractFactIndex.user_id == requester_user_id)
    return q


def _bucket(rows: List[ContractFactIndex], attr: str, empty_label: str = "(unknown)") -> List[Dict[str, Any]]:
    groups: Dict[str, List[int]] = defaultdict(list)
    for row in rows:
        value = getattr(row, attr)
        key = empty_label if value in (None, "") else str(value)
        groups[key].append(row.contract_id)
    out = [
        {"label": label, "count": len(ids), "contract_ids": ids}
        for label, ids in groups.items()
    ]
    out.sort(key=lambda b: (-b["count"], b["label"]))
    return out


def _liability_distribution(rows: List[ContractFactIndex]) -> List[Dict[str, Any]]:
    buckets = {
        "unlimited": [],
        "over_1m": [],
        "250k_to_1m": [],
        "under_250k": [],
        "unknown": [],
    }
    for row in rows:
        if row.liability_unlimited:
            buckets["unlimited"].append(row.contract_id)
        elif row.liability_cap_amount is None:
            buckets["unknown"].append(row.contract_id)
        elif row.liability_cap_amount > 1_000_000:
            buckets["over_1m"].append(row.contract_id)
        elif row.liability_cap_amount >= 250_000:
            buckets["250k_to_1m"].append(row.contract_id)
        else:
            buckets["under_250k"].append(row.contract_id)
    labels = {
        "unlimited": "Unlimited",
        "over_1m": "Cap over $1,000,000",
        "250k_to_1m": "Cap $250,000–$1,000,000",
        "under_250k": "Cap under $250,000",
        "unknown": "Cap not established",
    }
    return [
        {"label": labels[k], "key": k, "count": len(v), "contract_ids": v}
        for k, v in buckets.items()
    ]


def _payment_distribution(rows: List[ContractFactIndex]) -> List[Dict[str, Any]]:
    buckets = {"net_30_or_less": [], "net_31_to_45": [], "over_45": [], "unknown": []}
    for row in rows:
        days = row.payment_terms_days
        if days is None:
            buckets["unknown"].append(row.contract_id)
        elif days <= 30:
            buckets["net_30_or_less"].append(row.contract_id)
        elif days <= 45:
            buckets["net_31_to_45"].append(row.contract_id)
        else:
            buckets["over_45"].append(row.contract_id)
    labels = {
        "net_30_or_less": "≤ 30 days",
        "net_31_to_45": "31–45 days",
        "over_45": "> 45 days",
        "unknown": "Not established",
    }
    return [
        {"label": labels[k], "key": k, "count": len(v), "contract_ids": v}
        for k, v in buckets.items()
    ]


def build_portfolio_report(
    db: Session,
    *,
    tenant_id: int,
    workspace_id: Optional[int] = None,
    requester_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    rows = _base_query(db, tenant_id, workspace_id, requester_user_id).all()
    total = len(rows)
    high = sum(1 for r in rows if (r.highest_severity or "") == "high" or (r.overall_risk or "") == "high")
    unresolved = sum(1 for r in rows if r.has_unresolved)
    interactions = sum(1 for r in rows if r.has_interactions)
    finalized = sum(1 for r in rows if r.review_status == "finalized")
    compliance_rate = None
    if total:
        # Meaningful only as "finalized reviews with no unresolved items".
        compliant = sum(1 for r in rows if r.review_status == "finalized" and not r.has_unresolved)
        compliance_rate = round(100.0 * compliant / total, 1)

    return {
        "total_contracts": total,
        "finalized_reviews": finalized,
        "unresolved_legal_review_items": unresolved,
        "high_severity_contracts": high,
        "cross_policy_interaction_contracts": interactions,
        "playbook_compliance_rate_pct": compliance_rate,
        "by_type": _bucket(rows, "contract_type"),
        "by_counterparty": _bucket(rows, "counterparty"),
        "by_review_status": _bucket(rows, "review_status"),
        "by_governing_law": _bucket(rows, "governing_law"),
        "by_source": _bucket(rows, "source"),
        "liability_cap_distribution": _liability_distribution(rows),
        "payment_term_distribution": _payment_distribution(rows),
        "by_highest_severity": _bucket(rows, "highest_severity"),
        "most_common_exceptions": _exception_frequency(rows),
    }


def _exception_frequency(rows: List[ContractFactIndex]) -> List[Dict[str, Any]]:
    """Uses exception_count as a volume signal; per-policy-area frequency
    is not a first-class indexed column yet, so we only report what the
    index actually stores rather than fabricating clause-type histograms.
    """
    with_exceptions = [r for r in rows if (r.exception_count or 0) > 0]
    return [
        {
            "label": "Contracts with policy/interaction exceptions",
            "count": len(with_exceptions),
            "contract_ids": [r.contract_id for r in with_exceptions],
        }
    ]


def drilldown_contracts(db: Session, tenant_id: int, contract_ids: List[int], *, requester_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if not contract_ids:
        return []
    q = db.query(ContractFactIndex).filter(
        ContractFactIndex.tenant_id == tenant_id,
        ContractFactIndex.contract_id.in_(contract_ids[:200]),
    )
    if requester_user_id is not None:
        q = q.filter(ContractFactIndex.user_id == requester_user_id)
    return [serialize_index_row(r) for r in q.all()]
