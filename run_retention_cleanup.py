"""
Scheduled retention cleanup entrypoint (P9). Run this from an external
scheduler — cron, a systemd timer, or a Kubernetes CronJob — NOT as an
in-process background task (see retention.py's module docstring for why:
multiple Gunicorn workers would race on the same rows).

No-op unless CONTRACT_RETENTION_DAYS is configured.

Usage:
    python run_retention_cleanup.py           # deletes contracts past retention
    python run_retention_cleanup.py --dry-run # reports what would be deleted

Example crontab entry (daily at 3am):
    0 3 * * * cd /app && python run_retention_cleanup.py >> /var/log/triage-retention.log 2>&1
"""
from __future__ import annotations

import argparse
import logging
import sys

from database import SessionLocal, init_db
import retention

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("run_retention_cleanup")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        stats = retention.run_cleanup(db, dry_run=args.dry_run)
        logger.info(f"Retention cleanup complete: {stats}")
        return 1 if stats["errors"] else 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
