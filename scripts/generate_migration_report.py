#!/usr/bin/env python3
"""
Migration comparison report generator (architecture doc §12 Phase 2/3,
Task 5). Reads scripts/severity_migration_sample.py, computes each rule's
v1.0 severity, and prints the comparison table: legacy severity, new
severity, changed?, reason, confidence, and a recommendation -- never
overwriting legacy_severity anywhere, per §12's "fully reversible" mandate.

Usage:
    python3 scripts/generate_migration_report.py [--format md|csv]

This script is READ-ONLY with respect to rules_engine.py -- it does not
modify any Rule's `severity` field. Phase 5 cutover (making `severity` a
generated property) is a separate, later change gated on the full 117-rule
Phase 2/3 pass and Phase 4 shadow-mode bake period, not on this report.
"""

import argparse
import sys
from dataclasses import dataclass
from typing import List

from rules_engine import Severity
from severity_scoring import ScoredRule, validate_ruleset
from scripts.severity_migration_sample import MIGRATION_SAMPLE

_TIER_RANK = {Severity.LOW: 0, Severity.MEDIUM: 1, Severity.HIGH: 2, Severity.CRITICAL: 3}


@dataclass
class ComparisonRow:
    rule_id: str
    legacy: Severity
    new: Severity
    changed: bool
    direction: str          # "upgrade" | "downgrade" | "unchanged"
    method: str
    reason: str
    confidence: str
    recommendation: str


def _confidence(rule: ScoredRule) -> str:
    """Confidence in the NEW severity's correctness, not to be confused with
    the engine's separate finding-match confidence (severity_scoring.py's
    docstring is explicit these are different axes). Deterministic, derived
    from how the derivation was produced:
      - "high": ceiling-derived (a named, citable legal fact fired it)
      - "medium": band-derived and >= 6 WAS points from the nearest
        threshold boundary
      - "low": band-derived and within 6 WAS points of a boundary -- exactly
        the boundary cases architecture doc §5.1 flagged for attorney review
        rather than resolving unilaterally.
    """
    if rule.known_contestable:
        return "low"
    d = rule.derivation
    if d.method == "ceiling":
        return "high"
    # Only 18 (LOW/MEDIUM) and 36 (MEDIUM/HIGH) are actual decision lines --
    # WAS=0 is just the floor of the LOW band, not a boundary a small
    # scoring disagreement could tip across, so it must not count here.
    decision_lines = (18, 36)
    nearest_gap = min(abs(d.was - b) for b in decision_lines)
    return "medium" if nearest_gap >= 6 else "low"


def _reason(rule: ScoredRule) -> str:
    d = rule.derivation
    if d.method == "ceiling":
        return f"ceiling rule fired: {d.ceiling_rule}"
    return f"WAS={d.was}, band={d.band}"


def _recommendation(row_direction: str, confidence: str) -> str:
    if row_direction == "unchanged":
        return "no action"
    if confidence == "high":
        return "adopt new severity" if row_direction == "upgrade" else "adopt new severity (re-verify factor vector first)"
    if confidence == "medium":
        return "recommend adopting new severity; flag for attorney spot-check"
    return "defer to Phase 3 attorney calibration -- boundary case, do not resolve unilaterally"


def build_report(rules: List[ScoredRule]) -> List[ComparisonRow]:
    rows = []
    for rule in rules:
        if rule.legacy_severity is None:
            continue
        new = rule.severity
        changed = new != rule.legacy_severity
        if not changed:
            direction = "unchanged"
        elif _TIER_RANK[new] > _TIER_RANK[rule.legacy_severity]:
            direction = "upgrade"
        else:
            direction = "downgrade"
        confidence = _confidence(rule)
        rows.append(
            ComparisonRow(
                rule_id=rule.rule_id,
                legacy=rule.legacy_severity,
                new=new,
                changed=changed,
                direction=direction,
                method=rule.derivation.method,
                reason=_reason(rule),
                confidence=confidence,
                recommendation=_recommendation(direction, confidence),
            )
        )
    return rows


def render_markdown(rows: List[ComparisonRow]) -> str:
    lines = [
        "| Rule ID | Legacy | New | Changed? | Direction | Reason | Confidence | Recommendation |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r.rule_id}` | {r.legacy.value.upper()} | {r.new.value.upper()} | "
            f"{'Yes' if r.changed else 'No'} | {r.direction} | {r.reason} | {r.confidence} | {r.recommendation} |"
        )
    changed_count = sum(1 for r in rows if r.changed)
    lines.append("")
    lines.append(f"**{changed_count}/{len(rows)} rules changed tier** under the v1.0 framework.")
    return "\n".join(lines)


def render_csv(rows: List[ComparisonRow]) -> str:
    lines = ["rule_id,legacy,new,changed,direction,reason,confidence,recommendation"]
    for r in rows:
        reason = r.reason.replace(",", ";")
        rec = r.recommendation.replace(",", ";")
        lines.append(f"{r.rule_id},{r.legacy.value},{r.new.value},{r.changed},{r.direction},{reason},{r.confidence},{rec}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["md", "csv"], default="md")
    args = parser.parse_args()

    validation = validate_ruleset(MIGRATION_SAMPLE)
    if validation["errors"]:
        print("VALIDATION ERRORS (must fail loudly, per architecture doc §9):", file=sys.stderr)
        for e in validation["errors"]:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    if validation["warnings"]:
        print("Validation warnings:", file=sys.stderr)
        for w in validation["warnings"]:
            print(f"  - {w}", file=sys.stderr)
        print(file=sys.stderr)

    rows = build_report(MIGRATION_SAMPLE)
    output = render_markdown(rows) if args.format == "md" else render_csv(rows)
    print(output)


if __name__ == "__main__":
    main()
