#!/usr/bin/env python3
"""
Experiment: cluster the 117 migrated rules into rule FAMILIES (broader
than clause_category -- practice-area/doctrinal groupings a human would
recognize, e.g. "Lease," "Employment," "Rights Waiver") and ask whether a
single global WAS threshold can meaningfully work across all of them.

Family assignment is derived mechanically from each rule's rule_id prefix
and clause_category (see _FAMILY_RULES below) -- not re-scored, not
re-judged; it is a re-grouping of the SAME 117 already-scored rules from
scripts/severity_migration_full.py, so this experiment adds no new
subjective judgment about severity, only about which family label a rule
belongs to (a much lower-stakes classification than a factor score).

For each family this reports:
  - rule count, how many hit a ceiling vs. band-scored
  - the ACTUAL WAS range among its band-scored rules
  - the PRACTICAL max WAS range among its band-scored rules (from
    scripts/practical_max_experiment.py's method -- each rule's own
    already-identified factors maxed to their own ceiling)

Then it tests candidate single thresholds against every family to see
whether one number can ever discriminate meaningfully within EVERY
family, or whether some families are structurally locked out of ever
exceeding a given threshold regardless of clause severity.
"""

from collections import defaultdict

from severity_scoring import Factor, FACTOR_MAX_LEVEL, TIER_WEIGHT
from scripts.severity_migration_full import FULL_MIGRATION


def _family_of(rule):
    rid = rule.rule_id
    cat = rule.clause_category

    # Practice-area families (rule_id prefix is unambiguous for v6.0 rules)
    if rid.startswith(("H_LEASE", "M_LEASE")):
        return "Lease"
    if rid.startswith(("H_LOAN", "M_LOAN")):
        return "Loan"
    if rid.startswith(("H_EMPLOY", "M_EMPLOY")) or cat in ("WorkerClassification", "ImpliedContractFormation"):
        return "Employment"
    if rid.startswith(("H_FRANCHISE", "M_FRANCHISE")):
        return "Franchise"
    if rid.startswith(("H_MA_", "M_MA_")) or cat in ("OwnershipDilution", "GovernanceGap"):
        return "M&A / Partnership"
    if rid.startswith(("H_SETTLEMENT", "M_SETTLEMENT")):
        return "Settlement"
    if rid.startswith(("H_CONSTR", "M_CONSTR")):
        return "Construction"
    if cat in ("InsuranceBackstop",):
        return "Insurance"
    if cat in ("PersonalGuaranty",):
        return "Personal Liability"
    if cat in ("RightsWaiver", "RemedyElimination", "RemedyExpansion", "FeeShifting"):
        return "Rights Waiver / Remedy"
    if cat in ("PaymentContingency", "PaymentObligation", "FeeStructure", "FeeCap"):
        return "Financial"
    if cat in ("DocumentConsistency", "ExecutionDefect", "NoticeMechanics", "Boilerplate"):
        return "Administrative"
    if cat in ("DataProtectionProcedural", "DataRetention", "DataUsageRights"):
        return "Data / Privacy"
    if cat in ("IPAssignment", "ContentLicense"):
        return "IP / Ownership"
    if cat in ("RestrictiveCovenant",):
        return "Restrictive Covenant"
    if cat in ("UnilateralDiscretion", "Termination", "AssignmentRestriction"):
        return "Unilateral Discretion / Termination"
    if cat in ("RegulatoryCompliance", "RegulatoryAllocation"):
        return "Regulatory Compliance"
    if cat in ("Indemnification", "LiabilityCap"):
        return "Indemnification / Liability Cap"
    return "Other / Commercial Terms"


def practical_max(rule):
    touched = [f for f in Factor if rule.factor_vector.level(f) > 0]
    return sum(FACTOR_MAX_LEVEL[f] * TIER_WEIGHT[f] for f in touched)


def main():
    families = defaultdict(list)
    for rule in FULL_MIGRATION:
        families[_family_of(rule)].append(rule)

    print(f"{'Family':<38}{'n':<5}{'ceiling':<9}{'band':<6}{'actualWAS':<14}{'practicalMax':<16}")
    summary = {}
    for fam, rules in sorted(families.items(), key=lambda kv: -len(kv[1])):
        ceiling_rules = [r for r in rules if r.derivation.method == "ceiling"]
        band_rules = [r for r in rules if r.derivation.method == "band"]
        actual = [r.derivation.was for r in band_rules]
        pmax = [practical_max(r) for r in band_rules]
        actual_range = f"{min(actual)}-{max(actual)}" if actual else "n/a"
        pmax_range = f"{min(pmax)}-{max(pmax)}" if pmax else "n/a"
        summary[fam] = {
            "n": len(rules), "ceiling": len(ceiling_rules), "band": len(band_rules),
            "actual_min": min(actual) if actual else None, "actual_max": max(actual) if actual else None,
            "pmax_min": min(pmax) if pmax else None, "pmax_max": max(pmax) if pmax else None,
        }
        print(f"{fam:<38}{len(rules):<5}{len(ceiling_rules):<9}{len(band_rules):<6}{actual_range:<14}{pmax_range:<16}")

    print()
    print("=" * 90)
    print("Testing candidate single global thresholds against every family's PRACTICAL MAX range")
    print("(a family is 'locked out' at threshold T if even its highest-practical-max band-scored")
    print(" rule cannot reach T -- meaning NO clause of that family/type could ever cross T via")
    print(" aggregation, no matter how severely drafted, as long as it stays a band-scored rule)")
    print("=" * 90)
    for T in (6, 9, 12, 15, 18, 21, 24, 36):
        locked_out = [fam for fam, s in summary.items() if s["band"] > 0 and s["pmax_max"] < T]
        reachable = [fam for fam, s in summary.items() if s["band"] > 0 and s["pmax_max"] >= T]
        print(f"\nThreshold T={T}:")
        print(f"  families where SOME band-scored rule could reach T: {len(reachable)} -> {reachable}")
        print(f"  families structurally LOCKED OUT of ever reaching T: {len(locked_out)} -> {locked_out}")


if __name__ == "__main__":
    main()
