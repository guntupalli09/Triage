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
from severity_scoring import FRAMEWORK_VERSION, validate_ruleset


def main():
    validation = validate_ruleset(FULL_MIGRATION)
    if validation["errors"]:
        print("VALIDATION ERRORS:", file=sys.stderr)
        for e in validation["errors"]:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    rows = build_report(FULL_MIGRATION)
    print(f"# Full Migration Report -- Reviewer 1 (Framework Author) Migration\n")
    print(f"Framework version: {FRAMEWORK_VERSION} (band mode: relative, the v1.1 default). "
          f"\"New\" severity below reflects the current default. For the historical v1.0 "
          f"absolute-mode comparison (93/117 changed, 0 MEDIUM results) that motivated the "
          f"v1.1 threshold change, see docs/rules_engine/severity_v1_1_release_notes.md and "
          f"the archived report referenced there.\n")
    print(f"117/117 rules scored. {sum(1 for r in rows if r.changed)}/117 changed tier "
          f"(vs. legacy — a separate question from the v1.0-vs-v1.1 comparison above).\n")

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
    print("(Recorded during v1.0 absolute-mode analysis -- this is the calibration record "
          "that led to the v1.1 relative-mode default now shown in the table above, not a "
          "re-description of the current default's behavior. See "
          "docs/rules_engine/severity_v1_1_release_notes.md for what changed and why.)\n")
    print(FINDINGS)


if __name__ == "__main__":
    main()
