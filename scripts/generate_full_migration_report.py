#!/usr/bin/env python3
"""
Full 117-rule migration report -- Reviewer 1 (Framework Author) Migration.

Reads scripts/severity_migration_full.py and produces the same comparison
columns as scripts/generate_migration_report.py (legacy/new/changed/
reason/confidence/recommendation), plus a summary and the FINDINGS log.

Read-only w.r.t. rules_engine.py -- no rule's live `severity` is modified.
"""

import sys
from collections import Counter

from scripts.generate_migration_report import build_report, render_markdown
from scripts.severity_migration_full import FULL_MIGRATION, FINDINGS
from severity_scoring import validate_ruleset


def main():
    validation = validate_ruleset(FULL_MIGRATION)
    if validation["errors"]:
        print("VALIDATION ERRORS:", file=sys.stderr)
        for e in validation["errors"]:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    rows = build_report(FULL_MIGRATION)
    print(f"# Full Migration Report -- Reviewer 1 (Framework Author) Migration\n")
    print(f"117/117 rules scored. {sum(1 for r in rows if r.changed)}/117 changed tier.\n")

    direction_counts = Counter(r.direction for r in rows)
    print("## Summary\n")
    print(f"- Unchanged: {direction_counts['unchanged']}")
    print(f"- Upgraded (framework > legacy): {direction_counts['upgrade']}")
    print(f"- Downgraded (framework < legacy): {direction_counts['downgrade']}\n")

    confidence_counts = Counter(r.confidence for r in rows)
    print(f"- High confidence: {confidence_counts['high']}")
    print(f"- Medium confidence: {confidence_counts['medium']}")
    print(f"- Low confidence (boundary cases, deferred): {confidence_counts['low']}\n")

    print("## Full comparison table\n")
    print(render_markdown(rows))
    print()
    print("## Findings from scoring all 117 rules\n")
    print(FINDINGS)


if __name__ == "__main__":
    main()
