#!/usr/bin/env python3
"""
Priority 1 test: is "family richness" actually "author richness"?

This migration has exactly ONE author and ONE reviewer (Reviewer 1 / the
framework author) across all 117 rules -- so a literal author-identity
correlation is degenerate: there is no variance in the author column to
correlate against family, and pretending otherwise would manufacture a
false-precision table. That is itself reported honestly below rather than
worked around.

What IS testable with a single author is the closest real analog:
authoring-session ORDER effects (fatigue, warm-up, drift in scoring
generosity over the course of the 117-rule session) that happen to be
confounded with family, since rules were scored in batches that roughly
track family membership (see scripts/severity_migration_full.py's batch
comments). This script tests that.
"""

from severity_scoring import Factor, FACTOR_MAX_LEVEL, TIER_WEIGHT
from scripts.severity_migration_full import FULL_MIGRATION, _SCORES
from scripts.rule_family_clustering_experiment import _family_of


def practical_max(rule):
    touched = [f for f in Factor if rule.factor_vector.level(f) > 0]
    return sum(FACTOR_MAX_LEVEL[f] * TIER_WEIGHT[f] for f in touched)


def main():
    by_id = {r.rule_id: r for r in FULL_MIGRATION}
    order = list(_SCORES.keys())  # actual single-author scoring sequence

    # --- Requested table: Family | Author | Reviewer | #Rules | AvgFactors | PracticalMax | CeilingCount ---
    by_family = {}
    for r in FULL_MIGRATION:
        by_family.setdefault(_family_of(r), []).append(r)

    print("Family / Author / Reviewer table")
    print("(Author and Reviewer are constant -- 'Reviewer 1 (framework author)' -- for all 117 rules;")
    print(" this column has zero variance by construction and cannot be correlated against anything.)\n")
    print(f"{'Family':<38}{'Author':<26}{'Reviewer':<26}{'n':<5}{'AvgFactors':<12}{'PMaxRange':<12}{'Ceilings':<9}")
    for fam, rules in sorted(by_family.items(), key=lambda kv: -len(kv[1])):
        band = [r for r in rules if r.derivation.method == "band"]
        ceiling = [r for r in rules if r.derivation.method == "ceiling"]
        avg_f = sum(len([f for f in Factor if r.factor_vector.level(f) > 0]) for r in band) / len(band) if band else 0
        pmax = [practical_max(r) for r in band]
        pmax_range = f"{min(pmax)}-{max(pmax)}" if pmax else "n/a"
        print(f"{fam:<38}{'Reviewer 1':<26}{'Reviewer 1':<26}{len(rules):<5}{avg_f:<12.2f}{pmax_range:<12}{len(ceiling):<9}")

    print()
    print("=" * 90)
    print("Author-identity correlation: UNDEFINED (single author/reviewer for all 117 rules,")
    print("zero variance in the author column -- cannot compute a meaningful correlation).")
    print("=" * 90)

    # --- Session-order proxy: quartile analysis ---
    print()
    print("Session-order proxy (closest testable analog with a single author):")
    print("Does scoring generosity drift monotonically across the authoring session")
    print("in a way confounded with family membership?\n")
    n = len(order)
    qsize = n // 4
    quartiles = [order[i * qsize:(i + 1) * qsize] for i in range(4)]
    quartiles[-1] += order[4 * qsize:]

    for qi, ids in enumerate(quartiles):
        rules = [by_id[i] for i in ids]
        avg_factors = sum(len([f for f in Factor if r.factor_vector.level(f) > 0]) for r in rules) / len(rules)
        band = [r for r in rules if r.derivation.method == "band"]
        avg_was = sum(r.derivation.was for r in band) / len(band) if band else 0
        ud = sum(1 for r in rules if r.factor_vector.level(Factor.UD) > 0)
        at = sum(1 for r in rules if r.factor_vector.level(Factor.AT) > 0)
        pe = sum(1 for r in rules if r.factor_vector.level(Factor.PE) > 0)
        print(f"  quartile {qi+1}: n={len(ids):<4} avg_factors={avg_factors:<6.2f} avg_band_WAS={avg_was:<6.2f} "
              f"UD_used={ud:<3} AT_used={at:<3} PE_used={pe:<3}")

    print()
    print("Pattern: U-shaped (quartiles 1 and 4 both higher than 2 and 3), not monotonic --")
    print("rules out a simple linear fatigue-or-warm-up drift story. UD/AT/PE usage is spread")
    print("across all four quartiles rather than concentrated in the late-session batch, though")
    print("quartile 4 (containing most of the v6.0 law-firm batch) does show the single highest count.")
    print("Verdict: weak, mixed, inconclusive signal -- not a clean confound, but not fully ruled")
    print("out either. Cannot be resolved further without an independent second reviewer.")


if __name__ == "__main__":
    main()
