# [ARCHIVED — v1.0 absolute mode] Full Migration Report

**This is a historical snapshot**, generated under the v1.0 absolute
band mode (`compute_severity(mode="absolute")`) before v1.1 shipped.
It is preserved as the calibration record that motivated the v1.1
threshold change — see `docs/rules_engine/severity_v1_1_release_notes.md`
for what changed and why, and `docs/rules_engine/severity_migration_report_full_117.md`
for the current (v1.1 relative, default) report. Reproducible via
`python3 -m scripts.generate_full_migration_report` after temporarily
pinning `compute_severity`'s default back to `"absolute"`, or by calling
`build_report` with explicit `mode="absolute"` derivations.

---

# Full Migration Report -- Reviewer 1 (Framework Author) Migration

117/117 rules scored. 93/117 changed tier.

## Summary

- Unchanged: 24
- Upgraded (framework > legacy): 7
- Downgraded (framework < legacy): 86

- High confidence: 23
- Medium confidence: 94
- Low confidence (boundary cases, deferred): 0

## Full comparison table

| Rule ID | Legacy | New | Changed? | Direction | Reason | Confidence | Recommendation |
|---|---|---|---|---|---|---|---|
| `H_INDEM_01` | HIGH | HIGH | No | unchanged | ceiling rule fired: FB == 3 | high | no action |
| `H_LOL_01` | HIGH | HIGH | No | unchanged | ceiling rule fired: FB == 3 | high | no action |
| `H_IP_01` | HIGH | HIGH | No | unchanged | ceiling rule fired: AT == 3 and REV == 3 | high | no action |
| `H_PERSONAL_01` | CRITICAL | CRITICAL | No | unchanged | ceiling rule fired: PE == 3 | high | no action |
| `H_INDEM_ONEWAY_01` | HIGH | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_IP_WORK_PRODUCT_01` | HIGH | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_ATTFEE_01` | HIGH | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_LOL_CARVEOUT_01` | HIGH | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_ASSIGN_CHANGE_CTRL_01` | HIGH | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_PUBLICITY_01` | HIGH | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_UNILATERAL_MOD_01` | HIGH | HIGH | No | unchanged | ceiling rule fired: UD == 3 and (OC == 2 or FB >= 2) | high | no action |
| `H_CONSEQUENTIAL_01` | HIGH | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_TERM_CONVENIENCE_01` | HIGH | HIGH | No | unchanged | ceiling rule fired: UD == 3 and (OC == 2 or FB >= 2) | high | no action |
| `H_DATA_TERMINATION_01` | HIGH | LOW | Yes | downgrade | WAS=4, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_ASYMMETRIC_LIABILITY_01` | CRITICAL | HIGH | Yes | downgrade | ceiling rule fired: FB == 3 | high | adopt new severity (re-verify factor vector first) |
| `H_LOL_NO_CARVEOUT_01` | CRITICAL | LOW | Yes | downgrade | WAS=6, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_INDEM_SCOPE_NARROW_01` | HIGH | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_DPA_MISSING_01` | MEDIUM | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_BAA_MISSING_01` | MEDIUM | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_SUBPROCESSOR_MISSING_01` | MEDIUM | LOW | Yes | downgrade | WAS=4, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_AUDIT_RIGHTS_CUSTOMER_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_DELETION_CERT_MISSING_01` | MEDIUM | LOW | Yes | downgrade | WAS=4, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_SLA_REMEDY_EXCLUSIVITY_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_INSURANCE_MINIMUM_MISSING_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_REG_RESPONSIBILITY_UNALLOCATED_01` | MEDIUM | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_DATA_RETURN_CONDITIONAL_01` | MEDIUM | LOW | Yes | downgrade | WAS=2, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_CARD_AUTH_01` | HIGH | LOW | Yes | downgrade | WAS=7, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_CONTENT_LICENSE_01` | HIGH | LOW | Yes | downgrade | WAS=8, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_WAGE_DEDUCTION_01` | HIGH | HIGH | No | unchanged | ceiling rule fired: FB == 3 | high | no action |
| `H_CLASSIFICATION_01` | HIGH | LOW | Yes | downgrade | WAS=9, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_REFUND_01` | MEDIUM | LOW | Yes | downgrade | WAS=2, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_CANCEL_FEE_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_ACCOUNT_SUSPEND_01` | MEDIUM | HIGH | Yes | upgrade | ceiling rule fired: UD == 3 and (OC == 2 or FB >= 2) | high | adopt new severity |
| `M_PRIVACY_SHARING_01` | MEDIUM | LOW | Yes | downgrade | WAS=6, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_NONDISPARAGE_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_PHOTO_RELEASE_01` | MEDIUM | LOW | Yes | downgrade | WAS=4, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `L_ELECTRONIC_NOTICE_01` | LOW | LOW | No | unchanged | WAS=1, band=LOW (<18) | medium | no action |
| `L_COMMUNICATION_CONSENT_01` | LOW | LOW | No | unchanged | WAS=3, band=LOW (<18) | medium | no action |
| `M_CONF_01` | MEDIUM | LOW | Yes | downgrade | WAS=2, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_RENEW_01` | MEDIUM | LOW | Yes | downgrade | WAS=0, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_NONCOMP_01` | MEDIUM | LOW | Yes | downgrade | WAS=4, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_DEV_RESTRICT_01` | MEDIUM | LOW | Yes | downgrade | WAS=4, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_CONF_SCOPE_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_RESIDUALS_01` | MEDIUM | LOW | Yes | downgrade | WAS=2, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_INJUNCT_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_EQUIT_NOBOND_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_AUDIT_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_TERM_NOTICE_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_SURVIVAL_SCOPE_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_WAIVER_DEFENSE_01` | MEDIUM | HIGH | Yes | upgrade | ceiling rule fired: FB == 3 | high | adopt new severity |
| `M_ARBITRATION_01` | MEDIUM | LOW | Yes | downgrade | WAS=9, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_WARRANTY_DISCLAIM_01` | MEDIUM | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_BREACH_NOTIFY_01` | HIGH | LOW | Yes | downgrade | WAS=8, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_INSURANCE_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_FORCE_MAJEURE_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_SLA_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_MFN_01` | MEDIUM | LOW | Yes | downgrade | WAS=0, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `L_LATEFEE_01` | LOW | LOW | No | unchanged | WAS=3, band=LOW (<18) | medium | no action |
| `L_BROADDEF_01` | LOW | LOW | No | unchanged | WAS=1, band=LOW (<18) | medium | no action |
| `L_GOVLAW_01` | LOW | LOW | No | unchanged | WAS=0, band=LOW (<18) | medium | no action |
| `L_COMPLIANCE_01` | LOW | LOW | No | unchanged | WAS=9, band=LOW (<18) | medium | no action |
| `L_ESCROW_01` | LOW | LOW | No | unchanged | WAS=1, band=LOW (<18) | medium | no action |
| `L_SUBCONTRACT_01` | LOW | LOW | No | unchanged | WAS=5, band=LOW (<18) | medium | no action |
| `H_AI_TRAINING_01` | CRITICAL | HIGH | Yes | downgrade | ceiling rule fired: AT == 3 and REV == 3 | high | adopt new severity (re-verify factor vector first) |
| `H_PRICE_ESCAL_01` | HIGH | HIGH | No | unchanged | ceiling rule fired: UD == 3 and (OC == 2 or FB >= 2) | high | no action |
| `H_DATA_PRIVACY_01` | CRITICAL | HIGH | Yes | downgrade | ceiling rule fired: RS == 3 and SC == 3 | high | adopt new severity (re-verify factor vector first) |
| `M_DATA_PORTABILITY_01` | MEDIUM | LOW | Yes | downgrade | WAS=2, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_DATA_DELETION_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_CROSS_BORDER_01` | MEDIUM | LOW | Yes | downgrade | WAS=6, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_RENEWAL_PRICE_01` | MEDIUM | LOW | Yes | downgrade | WAS=9, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_MIN_COMMIT_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_BENCHMARKING_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_USE_RESTRICT_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `L_EXPORT_CTRL_01` | LOW | LOW | No | unchanged | WAS=5, band=LOW (<18) | medium | no action |
| `L_PAYMENT_TERMS_01` | LOW | LOW | No | unchanged | WAS=1, band=LOW (<18) | medium | no action |
| `M_PAYMENT_TRIGGER_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_CURRENCY_AMBIGUOUS_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_BILLING_FREQUENCY_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_PRICE_EXHIBIT_MISSING_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_EXPENSE_APPROVAL_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_USAGE_MEASUREMENT_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_DISCOUNT_EXPIRY_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_AUTHORITY_REP_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_EFFECTIVE_DATE_MISSING_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_EXHIBIT_MISSING_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `L_COUNTERPARTS_ESIGN_01` | LOW | LOW | No | unchanged | WAS=0, band=LOW (<18) | medium | no action |
| `H_PAYMENT_ACCELERATION_01` | HIGH | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_POST_TERMINATION_BILLING_01` | HIGH | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_PREPAID_FEES_REFUND_01` | MEDIUM | LOW | Yes | downgrade | WAS=4, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_FINAL_INVOICE_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_EARLY_TERMINATION_FEE_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_LEASE_PERSONAL_GUARANTY_01` | HIGH | CRITICAL | Yes | upgrade | ceiling rule fired: PE == 3 | high | adopt new severity |
| `H_LEASE_ASSIGN_SUBLET_01` | HIGH | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_LEASE_HOLDOVER_01` | HIGH | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_LEASE_RELOCATION_01` | HIGH | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_LEASE_CAM_UNCAPPED_01` | MEDIUM | HIGH | Yes | upgrade | ceiling rule fired: FB == 3 | high | adopt new severity |
| `M_LEASE_ESCALATION_UNCAPPED_01` | MEDIUM | HIGH | Yes | upgrade | ceiling rule fired: FB == 3 | high | adopt new severity |
| `H_LOAN_CONFESSION_JUDGMENT_01` | CRITICAL | CRITICAL | No | unchanged | ceiling rule fired: RW == 3 | high | no action |
| `H_LOAN_GUARANTY_WAIVER_01` | CRITICAL | CRITICAL | No | unchanged | ceiling rule fired: PE == 3 | high | no action |
| `M_LOAN_CROSS_DEFAULT_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_LOAN_PREPAY_PENALTY_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_LOAN_RATE_DISCRETION_01` | MEDIUM | LOW | Yes | downgrade | WAS=9, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_EMPLOY_ATWILL_WAIVER_01` | HIGH | LOW | Yes | downgrade | WAS=2, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_EMPLOY_IP_ASSIGN_OVERBROAD_01` | HIGH | HIGH | No | unchanged | ceiling rule fired: AT == 3 and REV == 3 | high | no action |
| `M_EMPLOY_SEVERANCE_RELEASE_01` | MEDIUM | LOW | Yes | downgrade | WAS=12, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_EMPLOY_NONSOLICIT_EMPLOYEE_01` | MEDIUM | LOW | Yes | downgrade | WAS=4, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_FRANCHISE_TERMINATION_CAUSE_01` | HIGH | HIGH | No | unchanged | ceiling rule fired: UD == 3 and (OC == 2 or FB >= 2) | high | no action |
| `M_FRANCHISE_TERRITORY_01` | MEDIUM | LOW | Yes | downgrade | WAS=1, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_MA_INDEM_BASKET_MISSING_01` | HIGH | LOW | Yes | downgrade | WAS=5, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_MA_EARNOUT_DISCRETION_01` | MEDIUM | HIGH | Yes | upgrade | ceiling rule fired: UD == 3 and (OC == 2 or FB >= 2) | high | adopt new severity |
| `M_PARTNERSHIP_DEADLOCK_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_PARTNERSHIP_CAPITAL_CALL_01` | MEDIUM | HIGH | Yes | upgrade | ceiling rule fired: AT == 3 and REV == 3 | high | adopt new severity |
| `H_SETTLEMENT_RELEASE_OVERBROAD_01` | HIGH | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_SETTLEMENT_LIQUIDATED_DAMAGES_01` | MEDIUM | LOW | Yes | downgrade | WAS=3, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `H_CONSTR_PAY_IF_PAID_01` | HIGH | HIGH | No | unchanged | ceiling rule fired: FB == 3 | high | no action |
| `M_CONSTR_LIEN_WAIVER_01` | MEDIUM | LOW | Yes | downgrade | WAS=10, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |
| `M_CONSTR_RETAINAGE_01` | MEDIUM | LOW | Yes | downgrade | WAS=7, band=LOW (<18) | medium | recommend adopting new severity; flag for attorney spot-check |

**93/117 rules changed tier** under the v1.0 framework.

## Findings from scoring all 117 rules


0. HEADLINE FINDING -- MEDIUM is structurally unreachable via aggregation
   across the real ruleset. 93 of 117 rules (79%) changed tier; 86 of 117
   (74%) downgraded. Of the 94 rules scored via the WAS band path (no
   ceiling fired), the WAS values range from 0 to 12 -- EVERY ONE landed
   in the LOW band (<18). Not a single band-scored rule reached MEDIUM
   (18-35) or HIGH (36+) through aggregation alone anywhere in the actual
   117-rule set; every HIGH/CRITICAL result in this migration came from a
   named ceiling rule, never from the weighted sum. This is the single
   most important number in this migration and should be read before any
   individual row: it means the v1.0 threshold table (architecture doc
   §6.3, "18/36" as ~35%/70% of a ~52-point theoretical max) was
   calibrated against a hand-picked 40-clause stress test biased toward
   clauses deliberately chosen to be severe, not against the real
   distribution of how actual deployed rules score. Two live hypotheses,
   deliberately left both live rather than picked between (framework is
   frozen; this is exactly what architecture doc §12 Phase 3 exists to
   resolve with real attorney review, not a unilateral engineering call):
     (a) legacy severity is systematically over-escalated (plausible --
         it was assigned by analogy with no downward pressure, so
         "worth mentioning at all" tended to become "at least MEDIUM"),
         and the framework's much lower distribution is closer to correct; OR
     (b) the WAS thresholds (18 for MEDIUM, 36 for HIGH) are set too high
         relative to how real single/double-factor commercial clauses
         actually score under the weighted formula, and Tier C's weight-1
         contribution in particular is too small to ever move a
         REV/SC/OC/DUR-only fact out of LOW regardless of how many of
         those factors are present.
   Recommend this be the FIRST item reviewed in Phase 3, before any
   individual rule's disagreement -- if the threshold table needs
   adjustment, that is a single governed change (architecture doc §9)
   that would resolve dozens of the individual disagreements below at
   once, rather than reviewing 86 rows independently.

1. SYSTEMIC: the v1.0 CRITICAL tier is narrower than legacy's. Legacy's
   v5.0 pass elevated 5 rules to CRITICAL: H_ASYMMETRIC_LIABILITY_01,
   H_LOL_NO_CARVEOUT_01, H_PERSONAL_01, H_DATA_PRIVACY_01, H_AI_TRAINING_01.
   Under the frozen v1.0 ceiling rules, CRITICAL is reachable ONLY via
   PE==3, RW==3, CR==2, or FB==3-and-PE==2 (architecture doc §6.1's hard
   invariant). Of the 5: H_PERSONAL_01 still computes CRITICAL (PE==3).
   The other 4 -- H_ASYMMETRIC_LIABILITY_01, H_LOL_NO_CARVEOUT_01,
   H_DATA_PRIVACY_01, H_AI_TRAINING_01 -- all compute HIGH, not CRITICAL,
   because their underlying facts (uncapped-but-entity-level liability,
   overbroad cap carve-outs, regulatory/breadth exposure, irreversible
   data ingestion) don't touch personal liability, a forum-rights waiver,
   or criminal exposure. This is the single largest, most consistent
   disagreement pattern in the migration and merits explicit governance
   discussion: is legacy's broader CRITICAL concept (severe + irreversible,
   regardless of personal/rights/criminal facts) correct, and the frozen
   ceiling rules too narrow? Or is the frozen design's insistence that
   CRITICAL be reserved for personal/rights/criminal facts specifically
   correct, and legacy over-escalated these 4? Recorded as the top
   candidate for Phase 3 attorney review and/or a v2.0 ceiling-rule
   discussion -- NOT resolved here.

2. INCONSISTENCY FOUND IN LEGACY: H_LEASE_PERSONAL_GUARANTY_01 (legacy
   HIGH) and H_PERSONAL_01 / H_LOAN_GUARANTY_WAIVER_01 (legacy CRITICAL)
   detect the same underlying fact -- an unconditional personal guaranty
   with no cap qualifier -- but were scored two different legacy tiers.
   The v1.0 framework computes CRITICAL for all three uniformly via the
   PE==3 ceiling, which is applied without regard to practice area by
   design. This is exactly the kind of pre-existing legacy inconsistency
   the framework's uniform, rule-independent ceiling logic is supposed to
   surface -- a positive validation of the architecture, not a defect in
   it.

3. DOCUMENTATION INCONSISTENCY FOUND IN THE ARCHITECTURE DOC ITSELF:
   H_LEASE_RELOCATION_01 was cited in the architecture doc's Refinement
   Log #2/#4 narrative as an example that "correctly return[s] HIGH" after
   the UD factor and mutuality-gate fixes. That is inconsistent with the
   doc's own §2 factor rubric, which explicitly names "relocation within
   the same building" as the canonical UD=2 example -- and UD=2 can never
   reach the UD==3-gated ceiling. Scored here as UD=2 (LOW) per the
   literal, frozen rubric text, contradicting the Refinement Log's prose
   claim. Recorded as a documentation defect for correction alongside any
   future v1.x doc maintenance, not resolved by picking whichever answer
   matches the narrative.

4. RECURRING FACTOR-COVERAGE GAPS (rules that don't cleanly map onto any
   of the 11 factors, each scored conservatively and landing LOW as a
   result): H_INDEM_ONEWAY_01 (asymmetry of an obligation, distinct from
   its magnitude), H_PUBLICITY_01 (brand/reputational control),
   H_CONTENT_LICENSE_01 (loss of control over personal identity/likeness
   -- a license, not a title transfer, so AT=0 by definition),
   H_EMPLOY_ATWILL_WAIVER_01 (unintended contract formation),
   M_NONDISPARAGE_01 (speech restriction, not a forum/process right),
   M_INJUNCT_01 (expanded remedy access for the counterparty, not a
   waiver by the restrained party), H_SETTLEMENT_RELEASE_OVERBROAD_01 and
   several substantive-remedy-reduction rules (M_REFUND_01,
   M_WARRANTY_DISCLAIM_01, H_CONSEQUENTIAL_01, H_LOL_NO_CARVEOUT_01) where
   REV alone (weight x1) cannot carry a clause to HIGH and no other factor
   is cleanly implicated. None of these were patched by inflating a
   factor to "make the math work" -- each is flagged inline above with
   its specific reasoning. Worth a dedicated v2-candidates discussion on
   whether a "substantive remedy reduction" factor, distinct from RW's
   narrow forum-rights scope, belongs in a future version.

5. RUBRIC GRANULARITY GAP: M_TERM_NOTICE_01 revealed that OC's definition
   ("0: a specific notice period ... is stated") does not graduate for a
   notice period that is stated but very short (e.g. 5 days) -- it scores
   identically to a fully adequate notice period. A future version might
   want an intermediate OC level for "notice stated but below a
   commercially reasonable minimum," but that reintroduces exactly the
   kind of judgment-call ambiguity the framework was built to eliminate,
   so this is flagged as a genuine tension, not an obvious fix.

6. LIKELY DUPLICATE RULE PAIRS (flagged for the not-yet-implemented
   duplicate-detection validator, architecture doc §9.3):
   M_INSURANCE_01 / M_INSURANCE_MINIMUM_MISSING_01 (near-identical
   rationale and detection); H_DATA_TERMINATION_01 / M_DATA_DELETION_01
   (same underlying fact -- no data return/deletion on termination -- at
   different legacy severities and rule_class).

7. UPGRADE RECOMMENDATIONS (framework computes HIGHER than legacy, not
   just lower -- listed explicitly so the report isn't read as "the
   framework only downgrades"): M_LEASE_CAM_UNCAPPED_01 (MEDIUM->HIGH),
   M_LEASE_ESCALATION_UNCAPPED_01 (MEDIUM->HIGH),
   M_PARTNERSHIP_CAPITAL_CALL_01 (MEDIUM->HIGH),
   M_MA_EARNOUT_DISCRETION_01 (MEDIUM->HIGH), M_WAIVER_DEFENSE_01
   (MEDIUM->HIGH), M_ACCOUNT_SUSPEND_01 (MEDIUM->HIGH),
   H_LEASE_PERSONAL_GUARANTY_01 (HIGH->CRITICAL, see finding #2).

None of the above were "fixed" in this file -- the frozen rubric was
applied as written in every case, and the resulting disagreement was
recorded rather than smoothed over, per the explicit instruction not to
optimize for matching legacy severity.

