"""
One-off backfill: create a PolicyPosition (+ PolicyPositionField rows) for
every existing PolicyRule row, per docs/architecture/playbook_authoring_ux_
design.md §8.3. See playbook_authoring.migrate_legacy_policy_rule for the
actual mapping and the reasoning behind status=ACTIVE / source=MANUAL.

Not run automatically on startup (unlike database.py's schema migrations,
which only add columns/tables) — this is a data backfill an operator runs
once, after the PolicyPosition/PolicyPositionField/PlaybookSourceDocument/
PolicyPositionApproval tables exist (they're created automatically by
Base.metadata.create_all() the same way every other new table is).

Idempotent: re-running is a safe no-op for any playbook/clause_type that
already has a PolicyPosition (see migrate_legacy_policy_rule).

Usage:
    python migrate_policy_positions.py --dry-run
    python migrate_policy_positions.py
"""
from __future__ import annotations

import argparse
import logging

from database import SessionLocal
from models import PolicyPosition, PolicyRule
from playbook_authoring import migrate_legacy_policy_rule

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("migrate_policy_positions")


def run(*, dry_run: bool) -> dict:
    stats = {"total_rules": 0, "created": 0, "already_migrated": 0, "errors": 0}
    db = SessionLocal()
    try:
        rules = db.query(PolicyRule).order_by(PolicyRule.id).all()
        stats["total_rules"] = len(rules)
        for rule in rules:
            already = (
                db.query(PolicyPosition)
                .filter(PolicyPosition.playbook_id == rule.playbook_id, PolicyPosition.clause_type == rule.clause_type)
                .first()
            )
            if already:
                stats["already_migrated"] += 1
                continue
            try:
                migrate_legacy_policy_rule(db, rule)
                stats["created"] += 1
                logger.info(
                    f"playbook_id={rule.playbook_id} clause_type={rule.clause_type!r} "
                    f"-> PolicyPosition(status=ACTIVE){' [dry-run, not committed]' if dry_run else ''}"
                )
            except Exception:
                stats["errors"] += 1
                logger.exception(f"Failed migrating PolicyRule id={rule.id}")

        if dry_run:
            db.rollback()
        else:
            db.commit()
    finally:
        db.close()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report what would be migrated without writing")
    args = parser.parse_args()

    stats = run(dry_run=args.dry_run)
    logger.info(
        f"Done. total_rules={stats['total_rules']} created={stats['created']} "
        f"already_migrated={stats['already_migrated']} errors={stats['errors']}"
    )
    if stats["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
