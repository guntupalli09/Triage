"""
Structured portfolio query over the canonical fact index.

Natural-language search (portfolio_nl.py) may *translate* a lawyer's
question into this AST. This module is the only thing that talks to the
database, and it never executes generated SQL.

Unknown fields, unknown operators, or type mismatches are rejected.
Tenant scoping is mandatory — callers pass the already-scoped tenant id.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Query, Session

from models import ContractFactIndex

ALLOWED_FIELDS = {
    "contract_type": {"type": "string", "column": ContractFactIndex.contract_type, "ops": {"eq", "neq", "in"}},
    "counterparty": {"type": "string", "column": ContractFactIndex.counterparty, "ops": {"eq", "neq", "contains"}},
    "governing_law": {"type": "string", "column": ContractFactIndex.governing_law, "ops": {"eq", "neq", "contains"}},
    "source": {"type": "string", "column": ContractFactIndex.source, "ops": {"eq", "in"}},
    "review_status": {"type": "string", "column": ContractFactIndex.review_status, "ops": {"eq", "in", "neq"}},
    "playbook_id": {"type": "integer", "column": ContractFactIndex.playbook_id, "ops": {"eq"}},
    "liability_cap": {"type": "number", "column": ContractFactIndex.liability_cap_amount, "ops": {"gt", "gte", "lt", "lte", "eq"}},
    "liability_unlimited": {"type": "boolean", "column": ContractFactIndex.liability_unlimited, "ops": {"eq"}},
    "payment_terms_days": {"type": "number", "column": ContractFactIndex.payment_terms_days, "ops": {"gt", "gte", "lt", "lte", "eq"}},
    "termination_for_convenience": {"type": "boolean", "column": ContractFactIndex.termination_for_convenience, "ops": {"eq"}},
    "assignment_requires_consent": {"type": "boolean", "column": ContractFactIndex.assignment_requires_consent, "ops": {"eq"}},
    "indemnification": {"type": "string", "column": ContractFactIndex.indemnification, "ops": {"eq"}},
    "highest_severity": {"type": "string", "column": ContractFactIndex.highest_severity, "ops": {"eq", "in"}},
    "has_unresolved": {"type": "boolean", "column": ContractFactIndex.has_unresolved, "ops": {"eq"}},
    "has_interactions": {"type": "boolean", "column": ContractFactIndex.has_interactions, "ops": {"eq"}},
    "overall_risk": {"type": "string", "column": ContractFactIndex.overall_risk, "ops": {"eq", "in"}},
}

ALLOWED_OPS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "contains"}
ALLOWED_COMBINATORS = {"and", "or"}


class PortfolioQueryError(ValueError):
    """Raised for malformed or unsupported structured queries. Callers map
    this to HTTP 400. Never a 500 — rejection is the correct behavior."""


@dataclass
class Filter:
    field: str
    op: str
    value: Any


@dataclass
class StructuredQuery:
    filters: List[Filter] = field(default_factory=list)
    combinator: str = "and"
    limit: int = 100
    offset: int = 0


def query_schema() -> Dict[str, Any]:
    return {
        "combinator": sorted(ALLOWED_COMBINATORS),
        "fields": {
            name: {"type": spec["type"], "ops": sorted(spec["ops"])}
            for name, spec in ALLOWED_FIELDS.items()
        },
    }


def _coerce_value(field_name: str, spec: Dict[str, Any], op: str, value: Any) -> Any:
    expected = spec["type"]
    if op == "in":
        if not isinstance(value, (list, tuple)) or not value:
            raise PortfolioQueryError(f"Operator 'in' on {field_name} requires a non-empty list.")
        return [_coerce_value(field_name, spec, "eq", v) for v in value]
    if expected == "string":
        if not isinstance(value, str) or not value.strip():
            raise PortfolioQueryError(f"Field {field_name} requires a non-empty string.")
        return value.strip()
    if expected == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
        raise PortfolioQueryError(f"Field {field_name} requires a boolean.")
    if expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise PortfolioQueryError(f"Field {field_name} requires a number.") from None
        return float(value)
    if expected == "integer":
        try:
            return int(value)
        except (TypeError, ValueError):
            raise PortfolioQueryError(f"Field {field_name} requires an integer.") from None
    raise PortfolioQueryError(f"Unsupported field type for {field_name}.")


def parse_structured_query(payload: Dict[str, Any]) -> StructuredQuery:
    if not isinstance(payload, dict):
        raise PortfolioQueryError("Query must be a JSON object.")
    if "sql" in payload or "raw_sql" in payload or "query_sql" in payload:
        raise PortfolioQueryError("Raw SQL is not permitted.")
    combinator = str(payload.get("combinator") or "and").lower()
    if combinator not in ALLOWED_COMBINATORS:
        raise PortfolioQueryError("combinator must be 'and' or 'or'.")
    raw_filters = payload.get("filters")
    if raw_filters is None:
        raise PortfolioQueryError("Query must include a 'filters' array.")
    if not isinstance(raw_filters, list):
        raise PortfolioQueryError("'filters' must be a list.")
    if len(raw_filters) > 25:
        raise PortfolioQueryError("A query may include at most 25 filters.")

    filters: List[Filter] = []
    for item in raw_filters:
        if not isinstance(item, dict):
            raise PortfolioQueryError("Each filter must be an object with field, op, and value.")
        extra = set(item.keys()) - {"field", "op", "value"}
        if extra:
            raise PortfolioQueryError(f"Unsupported filter keys: {sorted(extra)}")
        field_name = item.get("field")
        op = str(item.get("op") or "").lower()
        if field_name not in ALLOWED_FIELDS:
            raise PortfolioQueryError(
                f"Unsupported field {field_name!r}. Allowed fields: {sorted(ALLOWED_FIELDS)}."
            )
        spec = ALLOWED_FIELDS[field_name]
        if op not in ALLOWED_OPS or op not in spec["ops"]:
            raise PortfolioQueryError(
                f"Operator {op!r} is not allowed on {field_name}. Allowed: {sorted(spec['ops'])}."
            )
        value = _coerce_value(field_name, spec, op, item.get("value"))
        filters.append(Filter(field=field_name, op=op, value=value))

    try:
        limit = int(payload.get("limit", 100))
        offset = int(payload.get("offset", 0))
    except (TypeError, ValueError):
        raise PortfolioQueryError("limit and offset must be integers.") from None
    if limit < 1 or limit > 500:
        raise PortfolioQueryError("limit must be between 1 and 500.")
    if offset < 0:
        raise PortfolioQueryError("offset must be >= 0.")
    return StructuredQuery(filters=filters, combinator=combinator, limit=limit, offset=offset)


def _clause_for(filt: Filter):
    spec = ALLOWED_FIELDS[filt.field]
    col = spec["column"]
    op, value = filt.op, filt.value
    if op == "eq":
        return col == value
    if op == "neq":
        return col != value
    if op == "gt":
        return col > value
    if op == "gte":
        return col >= value
    if op == "lt":
        return col < value
    if op == "lte":
        return col <= value
    if op == "in":
        return col.in_(list(value))
    if op == "contains":
        return col.ilike(f"%{value}%")
    raise PortfolioQueryError(f"Operator {op} cannot be executed.")


def apply_structured_query(
    db: Session,
    *,
    tenant_id: int,
    query: StructuredQuery,
    workspace_id: Optional[int] = None,
    requester_user_id: Optional[int] = None,
) -> Tuple[List[ContractFactIndex], int]:
    """Execute a validated AST. ``tenant_id`` is required and is applied
    before any user-supplied filter. There is no path that omits it."""
    if not tenant_id:
        raise PortfolioQueryError("tenant_id is required.")
    q: Query = db.query(ContractFactIndex).filter(ContractFactIndex.tenant_id == tenant_id)
    if workspace_id is not None:
        q = q.filter(ContractFactIndex.workspace_id == workspace_id)
    if requester_user_id is not None:
        q = q.filter(ContractFactIndex.user_id == requester_user_id)

    clauses = [_clause_for(f) for f in query.filters]
    if clauses:
        if query.combinator == "or":
            from sqlalchemy import or_
            q = q.filter(or_(*clauses))
        else:
            for clause in clauses:
                q = q.filter(clause)

    total = q.count()
    rows = (
        q.order_by(ContractFactIndex.uploaded_at.desc(), ContractFactIndex.contract_id.desc())
        .offset(query.offset)
        .limit(query.limit)
        .all()
    )
    return rows, total


def serialize_index_row(row: ContractFactIndex) -> Dict[str, Any]:
    return {
        "contract_id": row.contract_id,
        "display_name": row.display_name,
        "original_filename": row.original_filename,
        "contract_type": row.contract_type,
        "counterparty": row.counterparty,
        "source": row.source,
        "review_status": row.review_status,
        "uploaded_at": row.uploaded_at.isoformat() if row.uploaded_at else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "playbook_id": row.playbook_id,
        "playbook_name": row.playbook_name,
        "playbook_revision": row.playbook_revision,
        "governing_law": row.governing_law,
        "liability_cap_amount": row.liability_cap_amount,
        "liability_cap_currency": row.liability_cap_currency,
        "liability_unlimited": row.liability_unlimited,
        "liability_cap_kind": row.liability_cap_kind,
        "payment_terms_days": row.payment_terms_days,
        "termination_for_convenience": row.termination_for_convenience,
        "assignment_requires_consent": row.assignment_requires_consent,
        "indemnification": row.indemnification,
        "highest_severity": row.highest_severity,
        "has_unresolved": row.has_unresolved,
        "has_interactions": row.has_interactions,
        "overall_risk": row.overall_risk,
        "exception_count": row.exception_count,
        "high_finding_count": row.high_finding_count,
        "medium_finding_count": row.medium_finding_count,
        "low_finding_count": row.low_finding_count,
    }
