"""
Build and refresh the queryable canonical-fact index.

Authority rules:
- Values come from persisted Contract analysis (document_facts_json,
  policy_decisions_json, metadata_json, findings, review/interaction
  snapshots). Nothing is invented here.
- UNKNOWN / missing stays NULL. Filters that require a known value will
  not match unknown rows — that is intentional, not a silent False.
- Historical reviews are never re-run through AI to populate the index.
  If a field was never established at review time, it stays unknown.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models import Contract, ContractFactIndex, Playbook


_SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
_ACTIONABLE_POLICY = {
    "PROHIBITED", "MUST_REDLINE", "ESCALATE", "NEGOTIATE", "REQUIRES_REVIEW", "EVALUATION_ERROR",
}
_ACTIONABLE_INTERACTION = {"ESCALATE", "NEGOTIATE", "REQUIRES_REVIEW", "EVALUATION_ERROR"}
_RESOLVED_REVIEW_ACTIONS = {"accepted", "edited", "rejected", "flagged", "dismissed"}


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _presence(fact: Optional[Dict[str, Any]]) -> Optional[str]:
    if not fact or not isinstance(fact, dict):
        return None
    return fact.get("presence")


def _known_value(fact: Optional[Dict[str, Any]]) -> Any:
    if _presence(fact) != "PRESENT":
        return None
    return fact.get("value")


def _normalize_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    text = str(raw).strip()
    if not text or text.lower() in ("unclassified", "unknown", "none"):
        return None
    upper = text.upper()
    aliases = {
        "MASTER SERVICES AGREEMENT": "MSA",
        "MASTER SERVICE AGREEMENT": "MSA",
        "MSA": "MSA",
        "NDA": "NDA",
        "NON-DISCLOSURE AGREEMENT": "NDA",
        "NONDISCLOSURE AGREEMENT": "NDA",
        "SAAS": "SaaS",
        "SOFTWARE AS A SERVICE": "SaaS",
    }
    return aliases.get(upper, text)


def _counterparty_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    parties = metadata.get("parties") or []
    names: List[str] = []
    for p in parties:
        if isinstance(p, dict):
            name = p.get("full_name") or p.get("name") or p.get("short_name")
        else:
            name = str(p)
        if name and str(name).strip():
            names.append(str(name).strip())
    if len(names) >= 2:
        return names[1][:255]
    if names:
        return names[0][:255]
    return None


def _cap_from_document_facts(document_facts: Dict[str, Any]) -> Tuple[Optional[float], Optional[str], Optional[bool], Optional[str]]:
    """Returns (amount, currency, unlimited, kind)."""
    liability = document_facts.get("liability") or {}
    provisions = liability.get("provisions") or []
    controlling_id = liability.get("controlling_provision_id")
    controlling = None
    if controlling_id:
        for p in provisions:
            if p.get("provision_id") == controlling_id:
                controlling = p
                break
    if controlling is None and provisions:
        controlling = provisions[0]
    if not controlling:
        return None, None, None, None

    cap = controlling.get("general_cap") or {}
    if _presence(cap) != "PRESENT":
        return None, None, None, None
    expr = cap.get("value") or {}
    operands = expr.get("operands") or []
    if not operands:
        return None, None, None, "unknown"
    kinds = [op.get("type") for op in operands if isinstance(op, dict)]
    if "unlimited" in kinds and len(kinds) == 1:
        return None, None, True, "unlimited"
    if "unlimited" in kinds:
        return None, None, True, "complex"
    if len(operands) == 1 and operands[0].get("type") == "fixed_amount":
        money = (operands[0].get("money") or {})
        try:
            amount = float(money.get("amount"))
        except (TypeError, ValueError):
            return None, money.get("currency"), None, "fixed"
        return amount, money.get("currency") or "USD", False, "fixed"
    if len(operands) == 1 and operands[0].get("type") == "annual_fee_multiple":
        commercial = document_facts.get("commercial") or {}
        fees = _known_value(commercial.get("annual_fees"))
        multiple = operands[0].get("multiple")
        try:
            multiple_f = float(multiple)
        except (TypeError, ValueError):
            return None, None, False, "fee_multiple"
        if isinstance(fees, dict) and fees.get("amount") is not None:
            try:
                acv = float(fees["amount"])
                return acv * multiple_f, fees.get("currency") or "USD", False, "fee_multiple"
            except (TypeError, ValueError):
                pass
        return None, None, False, "fee_multiple"
    if len(operands) == 1 and operands[0].get("type") == "fee_period":
        return None, None, False, "fee_period"
    return None, None, False, "complex"


_MONEY_SCALE = {
    "k": 1_000.0,
    "thousand": 1_000.0,
    "m": 1_000_000.0,
    "mm": 1_000_000.0,
    "million": 1_000_000.0,
    "b": 1_000_000_000.0,
    "bn": 1_000_000_000.0,
    "billion": 1_000_000_000.0,
}

# Engine summaries look like "$2,000,000.00 fixed". Contract language often
# says "shall not exceed $1,000,000" or "$1M". Fee multiples ("1x annual fees")
# are not dollar caps and must not be indexed as $1.
_DOLLAR_PREFIX_RE = re.compile(
    r"(?:usd|us\$|\$)\s*([0-9][\d,]*(?:\.\d+)?)\s*(million|billion|thousand|mm|bn|[kmb])?\b",
    re.IGNORECASE,
)
_DOLLAR_WORDS_RE = re.compile(
    r"\b([0-9][\d,]*(?:\.\d+)?)\s*(million|billion|thousand)\s*(?:usd|dollars|us\$)?\b",
    re.IGNORECASE,
)
_DOLLAR_SUFFIX_RE = re.compile(
    r"\b([0-9][\d,]*(?:\.\d+)?)\s*(?:usd|dollars)\b",
    re.IGNORECASE,
)
_FEE_MULTIPLE_RE = re.compile(r"\d+(?:\.\d+)?\s*x\b|\b(?:annual|monthly)\s+fees?\b", re.IGNORECASE)
_UNLIMITED_RE = re.compile(r"\bunlimited\b|\buncapped\b|\bno\s+(?:stated\s+)?cap\b", re.IGNORECASE)


def _scale_amount(raw: str, unit: Optional[str]) -> Optional[float]:
    try:
        amount = float(raw.replace(",", ""))
    except (TypeError, ValueError):
        return None
    if unit:
        scale = _MONEY_SCALE.get(unit.lower())
        if scale is None:
            return None
        amount *= scale
    if amount < 0:
        return None
    return amount


def parse_liability_cap_from_text(text: str) -> Tuple[Optional[float], Optional[str], Optional[bool], Optional[str]]:
    """Deterministic parse of a persisted policy summary / excerpt.

    Returns (amount, currency, unlimited, kind). Does not invent a cap when
    the text only describes a fees multiplier or says the cap was unknown.
    """
    if not text or not str(text).strip():
        return None, None, None, None
    blob = str(text)
    lowered = blob.lower()
    if "could not" in lowered or "no numeric general cap" in lowered or "no limitation-of-liability" in lowered:
        if _UNLIMITED_RE.search(blob) and "$" not in blob and "usd" not in lowered:
            return None, None, True, "unlimited"
        return None, None, None, None

    match = _DOLLAR_PREFIX_RE.search(blob) or _DOLLAR_WORDS_RE.search(blob) or _DOLLAR_SUFFIX_RE.search(blob)
    if match:
        amount = _scale_amount(match.group(1), match.group(2) if match.lastindex and match.lastindex >= 2 else None)
        if amount is not None:
            return amount, "USD", False, "fixed"

    if _FEE_MULTIPLE_RE.search(blob) and "$" not in blob and "usd" not in lowered:
        return None, None, False, "fee_multiple"

    if _UNLIMITED_RE.search(blob):
        return None, None, True, "unlimited"
    return None, None, None, None


def _cap_from_policy_decisions(policy_decisions: Dict[str, Any]) -> Tuple[Optional[float], Optional[str], Optional[bool], Optional[str]]:
    lol = policy_decisions.get("limitation_of_liability") or {}
    blob = " ".join([
        str(lol.get("extracted_summary") or ""),
        str(lol.get("contract_language") or ""),
        str(lol.get("explanation") or ""),
    ])
    return parse_liability_cap_from_text(blob)


def _payment_days(document_facts: Dict[str, Any], payment_terms: Any) -> Optional[int]:
    commercial = document_facts.get("commercial") or {}
    due = _known_value(commercial.get("payment_due"))
    if isinstance(due, dict) and due.get("days") is not None:
        try:
            return int(due["days"])
        except (TypeError, ValueError):
            pass
    if isinstance(payment_terms, dict):
        for key in ("days", "net_days", "payment_due_days"):
            if payment_terms.get(key) is not None:
                try:
                    return int(payment_terms[key])
                except (TypeError, ValueError):
                    continue
    return None


def _governing_law(policy_decisions: Dict[str, Any], metadata: Dict[str, Any]) -> Optional[str]:
    gl = policy_decisions.get("governing_law") or {}
    for candidate in (
        gl.get("extracted_summary"),
        (gl.get("controlling_provision") or {}).get("label") if isinstance(gl.get("controlling_provision"), dict) else None,
        metadata.get("governing_law"),
    ):
        if candidate and isinstance(candidate, str) and candidate.strip():
            # Keep short categorical labels, not full sentences.
            text = candidate.strip()
            if len(text) > 80:
                continue
            return text[:100]
    return None


def _bool_from_text(text: str, positive: Tuple[str, ...], negative: Tuple[str, ...]) -> Optional[bool]:
    lowered = text.lower()
    if any(p in lowered for p in positive) and not any(n in lowered for n in negative):
        return True
    if any(n in lowered for n in negative) and not any(p in lowered for p in positive):
        return False
    return None


def _termination_for_convenience(policy_decisions: Dict[str, Any]) -> Optional[bool]:
    term = policy_decisions.get("termination") or {}
    blob = " ".join([
        str(term.get("extracted_summary") or ""),
        str(term.get("contract_language") or ""),
        str(term.get("explanation") or ""),
    ])
    return _bool_from_text(
        blob,
        positive=("for convenience", "without cause", "for any reason"),
        negative=("no termination for convenience", "may not terminate for convenience"),
    )


def _assignment_requires_consent(policy_decisions: Dict[str, Any]) -> Optional[bool]:
    assignment = policy_decisions.get("assignment") or {}
    blob = " ".join([
        str(assignment.get("extracted_summary") or ""),
        str(assignment.get("contract_language") or ""),
        str(assignment.get("explanation") or ""),
    ])
    return _bool_from_text(
        blob,
        positive=("without the prior", "without prior written consent", "consent of the other", "may not assign"),
        negative=("freely assign", "may assign without consent", "no consent required"),
    )


def _indemnification_shape(document_facts: Dict[str, Any], policy_decisions: Dict[str, Any]) -> Optional[str]:
    indem = document_facts.get("indemnification") or {}
    obligations = indem.get("obligations") or []
    if len(obligations) >= 2:
        pairs = {(o.get("indemnifying_party"), o.get("indemnified_party")) for o in obligations if isinstance(o, dict)}
        reversed_pairs = {(b, a) for a, b in pairs}
        if pairs & reversed_pairs:
            return "mutual"
        return "one_sided"
    if len(obligations) == 1:
        return "one_sided"
    decision = policy_decisions.get("indemnification") or {}
    blob = (str(decision.get("extracted_summary") or "") + " " + str(decision.get("explanation") or "")).lower()
    if "mutual" in blob or "each party" in blob or "reciprocal" in blob:
        return "mutual"
    if blob.strip():
        return "one_sided"
    return None


def _severity_and_counts(findings: List[Any]) -> Tuple[Optional[str], int, int, int, int]:
    high = medium = low = exceptions = 0
    best = 0
    best_label = None
    for f in findings or []:
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity") or "").lower()
        rank = _SEVERITY_RANK.get(sev, 0)
        if rank > best:
            best = rank
            best_label = sev
        if sev == "high":
            high += 1
        elif sev == "medium":
            medium += 1
        elif sev == "low":
            low += 1
        if f.get("finding_type") == "policy_decision" and f.get("policy_state") in _ACTIONABLE_POLICY:
            exceptions += 1
        elif f.get("finding_type") == "interaction_decision" and f.get("policy_state") in _ACTIONABLE_INTERACTION:
            exceptions += 1
    return best_label, exceptions, high, medium, low


def _has_unresolved(contract: Contract, findings: List[Any]) -> bool:
    if contract.review_finalized_at:
        return False
    decisions = contract.review_decisions_json or {}
    actionable = 0
    resolved = 0
    for i, f in enumerate(findings or []):
        if not isinstance(f, dict):
            continue
        if f.get("finding_type") in ("policy_decision", "interaction_decision") or f.get("severity") == "high":
            actionable += 1
            key = f.get("finding_key") or f"{f.get('rule_id')}#{i}"
            entry = decisions.get(key) or {}
            if entry.get("action") in _RESOLVED_REVIEW_ACTIONS:
                resolved += 1
    if actionable == 0:
        return False
    return resolved < actionable


def _has_interactions(interaction_decisions: Optional[Dict[str, Any]]) -> bool:
    if not interaction_decisions:
        return False
    for decision in interaction_decisions.values():
        if isinstance(decision, dict) and decision.get("state") in _ACTIONABLE_INTERACTION:
            return True
    return False


def _playbook_revision(contract: Contract) -> Optional[str]:
    meta = contract.policy_revision_metadata_json or {}
    hashes = []
    for clause_meta in meta.values():
        if isinstance(clause_meta, dict) and clause_meta.get("config_hash"):
            hashes.append(str(clause_meta["config_hash"])[:12])
    if not hashes:
        return None
    return ",".join(hashes[:4])


def project_index_fields(db: Session, contract: Contract) -> Dict[str, Any]:
    document_facts = _as_dict(contract.document_facts_json)
    policy_decisions = _as_dict(contract.policy_decisions_json)
    metadata = _as_dict(contract.metadata_json)
    findings = contract.findings_json or []
    payment_terms = contract.payment_terms_json

    amount, currency, unlimited, kind = _cap_from_document_facts(document_facts)
    if unlimited is None and amount is None:
        amount2, currency2, unlimited2, kind2 = _cap_from_policy_decisions(policy_decisions)
        amount = amount if amount is not None else amount2
        currency = currency or currency2
        unlimited = unlimited2 if unlimited is None else unlimited
        kind = kind or kind2

    contract_type = _normalize_type(contract.contract_type or metadata.get("contract_type") or metadata.get("type"))
    counterparty = contract.counterparty or _counterparty_from_metadata(metadata)
    highest, exceptions, high, medium, low = _severity_and_counts(findings)

    playbook_name = None
    if contract.playbook_id:
        playbook = db.query(Playbook).filter(Playbook.id == contract.playbook_id).first()
        if playbook:
            playbook_name = playbook.name

    return {
        "tenant_id": contract.tenant_id,
        "workspace_id": contract.workspace_id,
        "contract_id": contract.id,
        "user_id": contract.user_id,
        "display_name": contract.display_name or contract.filename,
        "original_filename": contract.filename,
        "contract_type": contract_type,
        "counterparty": counterparty,
        "source": contract.source or "web",
        "review_status": contract.review_status or ("finalized" if contract.review_finalized_at else "in_review"),
        "uploaded_at": contract.created_at,
        "reviewed_at": contract.review_finalized_at,
        "playbook_id": contract.playbook_id,
        "playbook_name": playbook_name,
        "playbook_revision": _playbook_revision(contract),
        "governing_law": _governing_law(policy_decisions, metadata),
        "liability_cap_amount": amount,
        "liability_cap_currency": currency,
        "liability_unlimited": unlimited,
        "liability_cap_kind": kind,
        "payment_terms_days": _payment_days(document_facts, payment_terms),
        "termination_for_convenience": _termination_for_convenience(policy_decisions),
        "assignment_requires_consent": _assignment_requires_consent(policy_decisions),
        "indemnification": _indemnification_shape(document_facts, policy_decisions),
        "highest_severity": highest,
        "has_unresolved": _has_unresolved(contract, findings),
        "has_interactions": _has_interactions(contract.interaction_decisions_json),
        "overall_risk": contract.overall_risk,
        "exception_count": exceptions,
        "high_finding_count": high,
        "medium_finding_count": medium,
        "low_finding_count": low,
        "indexed_at": datetime.utcnow(),
    }


def upsert_fact_index(db: Session, contract: Contract) -> Optional[ContractFactIndex]:
    """Write or refresh the index row. No-op when the contract has no tenant
    yet (callers should stamp tenancy first)."""
    if not contract.id or not contract.tenant_id:
        return None
    fields = project_index_fields(db, contract)
    row = db.query(ContractFactIndex).filter(ContractFactIndex.contract_id == contract.id).first()
    if row is None:
        row = ContractFactIndex(**fields)
        db.add(row)
    else:
        for key, value in fields.items():
            setattr(row, key, value)
    db.flush()
    # Mirror a few listing fields onto Contract so history/repository UI
    # does not have to join the index for the common columns.
    if contract.contract_type is None and fields.get("contract_type"):
        contract.contract_type = fields["contract_type"]
    if contract.counterparty is None and fields.get("counterparty"):
        contract.counterparty = fields["counterparty"]
    if not contract.display_name:
        contract.display_name = fields.get("display_name")
    return row


def index_after_analysis(db: Session, contract: Contract, document_facts: Optional[Dict[str, Any]] = None) -> Optional[ContractFactIndex]:
    if document_facts is not None:
        contract.document_facts_json = document_facts
    return upsert_fact_index(db, contract)
