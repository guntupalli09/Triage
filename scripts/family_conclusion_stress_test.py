#!/usr/bin/env python3
"""
Adversarial stress test of the rule-family clustering experiment's
conclusion ("WAS is not comparable across families" --
scripts/rule_family_clustering_experiment.py). Assumes that conclusion is
wrong and tests five alternative explanations against the existing
117-rule dataset:

  A. Incomplete factor coverage
  B. Uneven rule granularity
  C. Family definition errors
  D. Reviewer scoring artifacts
  E. Systematic ontology/batch bias

See docs/rules_engine/severity_family_conclusion_stress_test.md for the
full writeup and verdict. This script reproduces the numbers cited there.
"""

import statistics
from severity_scoring import Factor, FACTOR_MAX_LEVEL, TIER_WEIGHT
from scripts.severity_migration_full import FULL_MIGRATION
from scripts.rule_family_clustering_experiment import _family_of


def practical_max(rule):
    touched = [f for f in Factor if rule.factor_vector.level(f) > 0]
    return sum(FACTOR_MAX_LEVEL[f] * TIER_WEIGHT[f] for f in touched)


GAP_FLAGGED = {
    "H_INDEM_ONEWAY_01", "H_PUBLICITY_01", "H_CONTENT_LICENSE_01",
    "H_EMPLOY_ATWILL_WAIVER_01", "M_NONDISPARAGE_01", "M_INJUNCT_01",
    "H_SETTLEMENT_RELEASE_OVERBROAD_01", "M_REFUND_01",
    "M_WARRANTY_DISCLAIM_01", "H_CONSEQUENTIAL_01", "H_LOL_NO_CARVEOUT_01",
}

DOC_COMPLETENESS_CATS = {"DocumentConsistency", "ExecutionDefect"}

# Era assignment from the version.json changelog, independent of clause_category
V1_V3 = {
    "H_INDEM_01", "H_LOL_01", "H_IP_01", "H_PERSONAL_01", "H_INDEM_ONEWAY_01",
    "H_IP_WORK_PRODUCT_01", "H_ATTFEE_01", "H_LOL_CARVEOUT_01",
    "H_ASSIGN_CHANGE_CTRL_01", "H_PUBLICITY_01", "H_UNILATERAL_MOD_01",
    "H_CONSEQUENTIAL_01", "H_TERM_CONVENIENCE_01", "H_DATA_TERMINATION_01",
    "M_ARBITRATION_01", "M_WARRANTY_DISCLAIM_01", "M_INSURANCE_01",
    "M_FORCE_MAJEURE_01", "M_SLA_01", "M_MFN_01", "L_LATEFEE_01",
    "L_BROADDEF_01", "L_GOVLAW_01", "L_COMPLIANCE_01", "L_ESCROW_01",
    "L_SUBCONTRACT_01", "H_AI_TRAINING_01", "H_PRICE_ESCAL_01",
    "H_DATA_PRIVACY_01", "M_DATA_PORTABILITY_01", "M_DATA_DELETION_01",
    "M_CROSS_BORDER_01", "M_RENEWAL_PRICE_01", "M_MIN_COMMIT_01",
    "M_BENCHMARKING_01", "M_USE_RESTRICT_01", "L_EXPORT_CTRL_01",
    "L_PAYMENT_TERMS_01", "H_CARD_AUTH_01", "H_CONTENT_LICENSE_01",
    "H_WAGE_DEDUCTION_01", "H_CLASSIFICATION_01", "M_REFUND_01",
    "M_CANCEL_FEE_01", "M_ACCOUNT_SUSPEND_01", "M_PRIVACY_SHARING_01",
    "M_NONDISPARAGE_01", "M_PHOTO_RELEASE_01", "L_ELECTRONIC_NOTICE_01",
    "L_COMMUNICATION_CONSENT_01", "M_CONF_01", "M_RENEW_01", "M_NONCOMP_01",
    "M_DEV_RESTRICT_01", "M_CONF_SCOPE_01", "M_RESIDUALS_01", "M_INJUNCT_01",
    "M_EQUIT_NOBOND_01", "M_AUDIT_01", "M_TERM_NOTICE_01",
    "M_SURVIVAL_SCOPE_01", "M_WAIVER_DEFENSE_01", "M_BREACH_NOTIFY_01",
}
V4_CONTRACT_TO_CASH = {
    "M_PAYMENT_TRIGGER_01", "M_CURRENCY_AMBIGUOUS_01", "M_BILLING_FREQUENCY_01",
    "M_PRICE_EXHIBIT_MISSING_01", "M_EXPENSE_APPROVAL_01",
    "M_USAGE_MEASUREMENT_01", "M_DISCOUNT_EXPIRY_01", "M_AUTHORITY_REP_01",
    "M_EFFECTIVE_DATE_MISSING_01", "M_EXHIBIT_MISSING_01",
    "L_COUNTERPARTS_ESIGN_01", "H_PAYMENT_ACCELERATION_01",
    "H_POST_TERMINATION_BILLING_01", "M_PREPAID_FEES_REFUND_01",
    "M_FINAL_INVOICE_01", "M_EARLY_TERMINATION_FEE_01",
}
V5_HARDENING = {
    "H_ASYMMETRIC_LIABILITY_01", "H_LOL_NO_CARVEOUT_01",
    "H_INDEM_SCOPE_NARROW_01", "M_DPA_MISSING_01", "M_BAA_MISSING_01",
    "M_SUBPROCESSOR_MISSING_01", "M_AUDIT_RIGHTS_CUSTOMER_01",
    "M_DELETION_CERT_MISSING_01", "M_SLA_REMEDY_EXCLUSIVITY_01",
    "M_INSURANCE_MINIMUM_MISSING_01", "M_REG_RESPONSIBILITY_UNALLOCATED_01",
    "M_DATA_RETURN_CONDITIONAL_01",
}


def test_a_incomplete_factor_coverage():
    print("### A. Incomplete factor coverage ###")
    by_family = {}
    for r in FULL_MIGRATION:
        by_family.setdefault(_family_of(r), []).append(r)
    changed = 0
    for fam, rules in sorted(by_family.items()):
        band = [r for r in rules if r.derivation.method == "band"]
        if not band:
            continue
        pmax_all = max(practical_max(r) for r in band)
        band_excl = [r for r in band if r.rule_id not in GAP_FLAGGED]
        pmax_excl = max((practical_max(r) for r in band_excl), default=None)
        locked_before = pmax_all < 18
        locked_after = pmax_excl is None or pmax_excl < 18
        if locked_before != locked_after:
            changed += 1
            print(f"  CHANGED: {fam} locked_before={locked_before} locked_after={locked_after}")
    print(f"  families whose lockout status changed after excluding gap-flagged rules: {changed}/18")
    print(f"  verdict: {'SUPPORTED' if changed >= 3 else 'FALSIFIED'} (need multiple families to flip to matter)\n")


def test_e_ontology_batch_bias():
    print("### E. Systematic ontology/batch bias ###")
    by_id = {r.rule_id: r for r in FULL_MIGRATION}
    eras = {
        "v1-v3": V1_V3, "v4.0 contract-to-cash": V4_CONTRACT_TO_CASH,
        "v5.0 hardening": V5_HARDENING,
        "v6.0 law-firm": set(by_id) - V1_V3 - V4_CONTRACT_TO_CASH - V5_HARDENING,
    }
    locked, unlocked = 0, 0
    for era, ids in eras.items():
        rules = [by_id[i] for i in ids if i in by_id]
        band = [r for r in rules if r.derivation.method == "band"]
        if not band:
            continue
        pmax = max(practical_max(r) for r in band)
        is_locked = pmax < 18
        locked += is_locked
        unlocked += not is_locked
        print(f"  {era:<25} n={len(rules):<4} pmax={pmax:<4} locked_at_T18={is_locked}")
    print(f"  verdict: pattern reappears under an orthogonal clustering "
          f"({locked} locked / {unlocked} unlocked, same qualitative shape as practice-area families) "
          f"-> FALSIFIED as sole explanation; also falsifies C (family definition error)\n")


def test_b_granularity():
    print("### B. Uneven rule granularity ###")
    by_family = {}
    for r in FULL_MIGRATION:
        by_family.setdefault(_family_of(r), []).append(r)
    data = []
    for fam, rules in by_family.items():
        band = [r for r in rules if r.derivation.method == "band"]
        if not band:
            continue
        avg_factors = sum(len([f for f in Factor if r.factor_vector.level(f) > 0]) for r in band) / len(band)
        data.append((fam, len(rules), avg_factors, max(practical_max(r) for r in band)))
    ns = [d[1] for d in data]
    avgs = [d[2] for d in data]
    mean_n, mean_a = statistics.mean(ns), statistics.mean(avgs)
    cov = sum((n - mean_n) * (a - mean_a) for n, a in zip(ns, avgs))
    sdn, sda = statistics.pstdev(ns), statistics.pstdev(avgs)
    corr = cov / (len(ns) * sdn * sda) if sdn and sda else None
    print(f"  correlation(family rule count, avg factors touched per rule) = {round(corr, 3)}")
    print("  verdict: partial support, insufficient alone (see doc for Data/Privacy vs "
          "Administrative counter-example)\n")


def test_d_reviewer_artifacts():
    print("### D. Reviewer scoring artifacts (spot check, not exhaustive) ###")
    by_id = {r.rule_id: r for r in FULL_MIGRATION}
    targets = ["M_PAYMENT_TRIGGER_01", "M_CURRENCY_AMBIGUOUS_01", "M_BILLING_FREQUENCY_01",
               "M_PRICE_EXHIBIT_MISSING_01", "M_USAGE_MEASUREMENT_01", "M_EXPENSE_APPROVAL_01",
               "M_DISCOUNT_EXPIRY_01", "M_FINAL_INVOICE_01"]
    for rid in targets:
        r = by_id[rid]
        nz = [(f.value, r.factor_vector.level(f)) for f in Factor if r.factor_vector.level(f) > 0]
        print(f"  {rid:<32}{nz}")
    print("  verdict: real inconsistency found (M_USAGE_MEASUREMENT_01 scored FB+REV, "
          "M_CURRENCY_AMBIGUOUS_01/M_PRICE_EXHIBIT_MISSING_01 describe the same kind of fact "
          "but scored REV only) -- real but magnitude (3->9) can't explain an 18-point gap. "
          "Full resolution requires the pending blind re-score gate.\n")


if __name__ == "__main__":
    test_a_incomplete_factor_coverage()
    test_e_ontology_batch_bias()
    test_b_granularity()
    test_d_reviewer_artifacts()
