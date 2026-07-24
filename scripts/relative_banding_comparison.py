#!/usr/bin/env python3
"""
Compares absolute (v1.0 default) vs. relative (v1.1 candidate) band modes
across all 117 migrated rules -- reproduces the numbers cited in
docs/rules_engine/severity_threshold_v1_1_candidate.md.
"""

from collections import Counter

from rules_engine import Severity
from severity_scoring import compute_severity
from scripts.severity_migration_full import FULL_MIGRATION
from scripts.rule_family_clustering_experiment import _family_of


def main():
    abs_tiers, rel_tiers = Counter(), Counter()
    agree_abs = agree_rel = differ = 0
    for r in FULL_MIGRATION:
        d_abs = compute_severity(r.factor_vector, mode="absolute")
        d_rel = compute_severity(r.factor_vector, mode="relative")
        abs_tiers[d_abs.tier.value] += 1
        rel_tiers[d_rel.tier.value] += 1
        agree_abs += d_abs.tier == r.legacy_severity
        agree_rel += d_rel.tier == r.legacy_severity
        differ += d_abs.tier != d_rel.tier

    print(f"Overall tier distribution (n=117):")
    print(f"  absolute: {dict(abs_tiers)}")
    print(f"  relative: {dict(rel_tiers)}")
    print(f"  rules where the two modes disagree: {differ}/117")
    print(f"  legacy agreement -- absolute: {agree_abs}/117, relative: {agree_rel}/117")
    print()

    by_family = {}
    for r in FULL_MIGRATION:
        by_family.setdefault(_family_of(r), []).append(r)

    print(f"{'family':<38}{'n':<5}{'LOW':<6}{'MED':<6}{'HIGH':<6}{'CRIT':<6}")
    for fam, rules in sorted(by_family.items(), key=lambda kv: -len(kv[1])):
        tiers = [compute_severity(r.factor_vector, mode="relative").tier for r in rules]
        c = {t.value: tiers.count(t) for t in Severity}
        print(f"{fam:<38}{len(rules):<5}{c['low']:<6}{c['medium']:<6}{c['high']:<6}{c['critical']:<6}")

    all_low_families = []
    for fam, rules in by_family.items():
        tiers = [compute_severity(r.factor_vector, mode="relative").tier for r in rules]
        if all(t == Severity.LOW for t in tiers):
            all_low_families.append(fam)
    print()
    print(f"Families still 100% LOW under relative banding: {all_low_families}")


if __name__ == "__main__":
    main()
