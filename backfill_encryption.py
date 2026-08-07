"""
One-off backfill: encrypt any legacy-plaintext contract_text/template_text
rows under the current ENCRYPTION_KEYS/ENCRYPTION_KEY_CURRENT (see
encryption.py). Not run automatically — operators run this on their own
schedule after configuring encryption, and again after rotating to a new
current key if they want old rows re-encrypted under it (existing encrypted
rows keep decrypting fine under a retired key either way; this script is
about intentional re-encryption, not a correctness requirement).

Idempotent: a row whose stored value already starts with the "enc:v1:"
envelope prefix is left untouched (counted as "already encrypted", not
re-encrypted) — running this script twice in a row is a safe no-op on the
second run. Uses raw parameterized SQL (not the ORM) deliberately: reading
through the mapped Column would transparently decrypt already-encrypted
rows via EncryptedText.process_result_value, and re-assigning that decrypted
value back would encrypt it again under a fresh nonce — which is not wrong,
exactly, but makes "did this actually change anything" impossible to answer
for --dry-run reporting. Reading the true raw stored string here makes the
already-encrypted check exact.

Usage:
    python backfill_encryption.py --dry-run
    python backfill_encryption.py
    python backfill_encryption.py --table contracts
    python backfill_encryption.py --batch-size 200
"""
from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import text

import encryption
from database import engine

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_encryption")

_TARGETS = {
    "contracts": "contract_text",
    "playbooks": "template_text",
}


def _backfill_table(table: str, column: str, *, dry_run: bool, batch_size: int) -> dict:
    stats = {"total": 0, "encrypted": 0, "already_encrypted": 0, "empty": 0, "errors": 0}

    with engine.connect() as conn:
        rows = conn.execute(text(f"SELECT id, {column} FROM {table} ORDER BY id")).fetchall()

    logger.info(f"{table}.{column}: {len(rows)} row(s) to inspect")

    batch: list[tuple[int, str]] = []

    def _flush(batch_rows: list[tuple[int, str]]):
        if not batch_rows or dry_run:
            return
        with engine.begin() as conn:
            for row_id, new_value, original_value in batch_rows:
                # Optimistic guard: only overwrite if the raw value hasn't
                # changed since we read it (e.g. the app re-saved the row
                # concurrently), so this never clobbers a fresher write.
                result = conn.execute(
                    text(f"UPDATE {table} SET {column} = :new_value WHERE id = :id AND {column} = :original_value"),
                    {"new_value": new_value, "id": row_id, "original_value": original_value},
                )
                if result.rowcount != 1:
                    logger.warning(f"{table}.id={row_id}: skipped (row changed since it was read; re-run to retry)")

    pending: list[tuple[int, str, str]] = []
    for row_id, raw_value in rows:
        stats["total"] += 1
        try:
            if not raw_value:
                stats["empty"] += 1
                continue
            if encryption.is_encrypted(raw_value):
                stats["already_encrypted"] += 1
                continue

            new_value = encryption.encrypt(raw_value)
            stats["encrypted"] += 1
            logger.info(f"{table}.id={row_id}: {'would encrypt' if dry_run else 'encrypting'}")
            pending.append((row_id, new_value, raw_value))

            if len(pending) >= batch_size:
                _flush(pending)
                pending = []
        except Exception:
            stats["errors"] += 1
            logger.exception(f"{table}.id={row_id}: failed to encrypt")

    _flush(pending)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing anything")
    parser.add_argument("--table", choices=["contracts", "playbooks", "all"], default="all")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    targets = _TARGETS if args.table == "all" else {args.table: _TARGETS[args.table]}

    overall_errors = 0
    for table, column in targets.items():
        stats = _backfill_table(table, column, dry_run=args.dry_run, batch_size=args.batch_size)
        overall_errors += stats["errors"]
        logger.info(
            f"{table}: total={stats['total']} "
            f"{'would_encrypt' if args.dry_run else 'encrypted'}={stats['encrypted']} "
            f"already_encrypted={stats['already_encrypted']} empty={stats['empty']} errors={stats['errors']}"
        )

    if args.dry_run:
        logger.info("Dry run complete — no changes were written.")
    return 1 if overall_errors else 0


if __name__ == "__main__":
    sys.exit(main())
