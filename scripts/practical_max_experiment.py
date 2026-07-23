#!/usr/bin/env python3
"""
Experiment: for every migrated rule, compute the PRACTICAL maximum WAS --
not the theoretical 11-factor maximum, but the maximum achievable using
only the factors that rule's own clause TYPE structurally implicates.

Method: "which factors are structurally possible for this clause category"
is not re-guessed fresh here (that would just be a second round of
reviewer judgment layered on the first). It is read directly off the
factor set Reviewer 1 already identified as relevant when scoring the rule
in scripts/severity_migration_full.py -- i.e. every factor that rule
scored non-zero. Practical max = what WAS would that SAME set of factors
produce if each one were drafted as badly as possible (set to its own
FACTOR_MAX_LEVEL), holding every other factor at 0 because it was already
judged not implicated by this clause type at all.

This directly tests two competing explanations for last turn's finding
(94 rules never reached WAS 18):
  (a) each rule's own practical ceiling is inherently low (few relevant
      factors x modest weights) -- meaning even a worst-case draft of
      that exact clause type couldn't reach MEDIUM under the current
      weights/thresholds; or
  (b) each rule's own practical ceiling is actually much higher than 18,
      and the rule was simply scored well below its own worst-case --
      meaning reviewer conservatism, not architecture, explains most of
      the gap.

No thresholds are used or referenced below -- per instruction, this
experiment ignores them entirely and reports raw WAS numbers and
percentages only.
"""

from severity_scoring import Factor, FACTOR_MAX_LEVEL, TIER_WEIGHT
from scripts.severity_migration_full import FULL_MIGRATION


def practical_max_was(rule):
    """WAS if every factor this rule's own scoring touched (level > 0)
    were instead set to that factor's maximum possible level."""
    touched = [f for f in Factor if rule.factor_vector.level(f) > 0]
    return touched, sum(FACTOR_MAX_LEVEL[f] * TIER_WEIGHT[f] for f in touched)


def main():
    rows = []
    zero_touch = []
    for rule in FULL_MIGRATION:
        touched, pmax = practical_max_was(rule)
        actual = rule.derivation.was
        if pmax == 0:
            zero_touch.append(rule.rule_id)
            continue
        pct = round(100 * actual / pmax, 1)
        rows.append((rule.rule_id, rule.legacy_severity.value, rule.derivation.tier.value,
                      [f.value for f in touched], actual, pmax, pct))

    print(f"{'rule_id':<38}{'legacy':<10}{'new':<10}{'factors':<22}{'actual':<8}{'pmax':<7}{'pct':<8}")
    for r in sorted(rows, key=lambda x: x[6]):
        print(f"{r[0]:<38}{r[1]:<10}{r[2]:<10}{','.join(r[3]):<22}{r[4]:<8}{r[5]:<7}{r[6]:<8}")

    print()
    print(f"Rules with zero touched factors (practical max = 0, excluded from %): {len(zero_touch)}")
    print(f"  {zero_touch}")
    print()
    pcts = [r[6] for r in rows]
    print(f"n = {len(pcts)}")
    print(f"mean % of own practical max: {sum(pcts)/len(pcts):.1f}%")
    pcts_sorted = sorted(pcts)
    mid = len(pcts_sorted) // 2
    median = pcts_sorted[mid] if len(pcts_sorted) % 2 else (pcts_sorted[mid-1] + pcts_sorted[mid]) / 2
    print(f"median % of own practical max: {median:.1f}%")
    print(f"min: {min(pcts)}%  max: {max(pcts)}%")

    # distribution buckets
    buckets = {"0-25%": 0, "25-50%": 0, "50-75%": 0, "75-99%": 0, "100%": 0}
    for p in pcts:
        if p >= 100:
            buckets["100%"] += 1
        elif p >= 75:
            buckets["75-99%"] += 1
        elif p >= 50:
            buckets["50-75%"] += 1
        elif p >= 25:
            buckets["25-50%"] += 1
        else:
            buckets["0-25%"] += 1
    print()
    for k, v in buckets.items():
        print(f"  {k}: {v} rules")

    by_id = {rule.rule_id: rule for rule in FULL_MIGRATION}
    print()
    print("Ceiling-fired rules only (already CRITICAL/HIGH regardless of WAS number):")
    ceiling_rows = [r for r in rows if by_id[r[0]].derivation.method == "ceiling"]
    for r in sorted(ceiling_rows, key=lambda x: x[6]):
        print(f"  {r[0]:<38} actual={r[4]:<5} pmax={r[5]:<5} pct={r[6]}%")

    print()
    print("Band-scored rules only (severity currently determined by WAS/threshold):")
    band_rows = [r for r in rows if by_id[r[0]].derivation.method == "band"]
    band_pcts = [r[6] for r in band_rows]
    print(f"  n = {len(band_pcts)}, mean = {sum(band_pcts)/len(band_pcts):.1f}%, "
          f"median = {sorted(band_pcts)[len(band_pcts)//2]}%, "
          f"min = {min(band_pcts)}%, max = {max(band_pcts)}%")


if __name__ == "__main__":
    main()
