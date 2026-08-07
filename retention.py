"""
Data lifecycle: configurable contract retention + secure scheduled
cleanup (P9).

Retention is OFF by default (CONTRACT_RETENTION_DAYS unset) — this ships
without changing behavior for any existing deployment; an operator opts in
by setting CONTRACT_RETENTION_DAYS to enable automatic deletion of
contracts older than that many days since upload (Contract.created_at).

Cleanup deliberately does NOT run as an in-process background loop: with
multiple Gunicorn workers (WEB_WORKERS), an in-process timer would fire
once per worker and race on the same rows. Two supported ways to actually
run it on a schedule instead:
  1. run_retention_cleanup.py via cron / systemd timer / Kubernetes
     CronJob (the Docker deployment) — see
     docs/security/data_retention_infra.md.
  2. POST /internal/retention/cleanup, bearer-token protected via
     CRON_SECRET, for platforms that trigger jobs over HTTP rather than a
     shell (Vercel Cron Jobs, for the serverless deployment path — see
     vercel.json / VERCEL_DEPLOYMENT.md).

Both call run_cleanup() below, which reuses the exact same deletion
semantics as the user-facing per-contract delete (P4, main.py's POST
/contract/{id}/delete): the whole Contract row (and cascading
ContractEvent rows) is removed — not a soft delete/flag — and every
deletion is audit-logged.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

import audit_log
from models import Contract

logger = logging.getLogger(__name__)


def get_retention_days() -> Optional[int]:
    """None means retention is disabled (the default)."""
    raw = os.getenv("CONTRACT_RETENTION_DAYS", "").strip()
    if not raw:
        return None
    try:
        days = int(raw)
    except ValueError:
        logger.error(f"CONTRACT_RETENTION_DAYS={raw!r} is not a valid integer; retention is disabled")
        return None
    if days < 1:
        logger.error(f"CONTRACT_RETENTION_DAYS={raw!r} must be >= 1; retention is disabled")
        return None
    return days


def find_expired_contracts(db: Session, *, retention_days: int, now: Optional[datetime] = None) -> List[Contract]:
    cutoff = (now or datetime.utcnow()) - timedelta(days=retention_days)
    return db.query(Contract).filter(Contract.created_at < cutoff).all()


def delete_contract_for_retention(db: Session, contract: Contract) -> None:
    """Same deletion semantics as the user-facing per-contract delete: the
    whole row, cascading ContractEvent rows, is gone — never a soft
    delete/flag. actor_user_id is None on the audit record since this is a
    system action, not something the owning user did."""
    contract_id, filename, owner_user_id = contract.id, contract.filename, contract.user_id
    db.delete(contract)
    db.commit()
    audit_log.record_event(
        db, "contract_auto_deleted", actor_user_id=None,
        target_type="contract", target_id=contract_id, success=True,
        detail="retention_policy_expired",
        metadata={"filename": filename, "owner_user_id": owner_user_id},
    )


def run_cleanup(db: Session, *, dry_run: bool = False) -> dict:
    """Returns {"retention_days": int|None, "found": int, "deleted": int, "errors": int}.
    retention_days is None (found/deleted/errors all 0) when retention isn't configured."""
    retention_days = get_retention_days()
    if retention_days is None:
        logger.info("CONTRACT_RETENTION_DAYS not configured — retention cleanup is a no-op")
        return {"retention_days": None, "found": 0, "deleted": 0, "errors": 0}

    expired = find_expired_contracts(db, retention_days=retention_days)
    stats = {"retention_days": retention_days, "found": len(expired), "deleted": 0, "errors": 0}

    for contract in expired:
        if dry_run:
            logger.info(f"[dry-run] would delete contract id={contract.id} (past {retention_days}-day retention)")
            continue
        try:
            delete_contract_for_retention(db, contract)
            stats["deleted"] += 1
        except Exception:
            logger.exception(f"Failed to delete contract id={contract.id} during retention cleanup")
            stats["errors"] += 1
            db.rollback()

    return stats
